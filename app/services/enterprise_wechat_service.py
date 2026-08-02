from __future__ import annotations

import json
import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import settings
from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json
from app.services.run_record_service import sanitize_metadata


WECHAT_API_BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"
_ACCESS_TOKEN: str | None = None
_ACCESS_TOKEN_EXPIRES_AT = 0.0
_ACCESS_TOKEN_CACHE_KEY = ""
_API_TRACE_LIMIT = 20


class EnterpriseWechatApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        errcode: int | None = None,
        errmsg: str | None = None,
        path: str | None = None,
        diagnostic: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.errcode = errcode
        self.errmsg = errmsg
        self.path = path
        self.diagnostic = diagnostic or {}


@dataclass(frozen=True)
class EnterpriseWechatAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"


def _missing_enterprise_wechat_config_fields(effective: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not _normalize_optional_text(effective.get("corp_id")):
        missing.append("corp_id")
    if not _normalize_optional_text(effective.get("agent_id")):
        missing.append("agent_id")
    if not _normalize_optional_text(effective.get("secret")):
        missing.append("secret")
    if not bool(effective.get("real_send_enabled")):
        missing.append("real_send_enabled")
    return missing


def _enterprise_wechat_setup_steps(effective: dict[str, Any]) -> list[dict[str, Any]]:
    configured = bool(effective.get("configured"))
    real_send_enabled = bool(effective.get("real_send_enabled"))
    return [
        _guide_item(
            "corp_id",
            "复制企业 ID",
            "登录企业微信管理后台，在“我的企业”里复制 Corp ID。",
            bool(_normalize_optional_text(effective.get("corp_id"))),
        ),
        _guide_item(
            "agent",
            "创建自建应用",
            "在“应用管理”里创建自建应用，复制 AgentId 和 Secret。",
            bool(_normalize_optional_text(effective.get("agent_id")) and _normalize_optional_text(effective.get("secret"))),
        ),
        _guide_item(
            "visible_scope",
            "设置应用可见范围",
            "把测试接收人放进应用可见范围，第一条真实发送建议先发给自己。",
            configured,
        ),
        _guide_item(
            "save_settings",
            "保存到后台配置",
            "在本页保存 Corp ID、Agent ID、Secret 和超时时间。",
            configured,
        ),
        _guide_item(
            "sync_contacts",
            "同步通讯录",
            "保存后先同步通讯录，确认能搜到自己的姓名；找不到时可手动填 userid。",
            bool(effective.get("last_sync_at")),
        ),
        _guide_item(
            "enable_real_send",
            "打开真实发送开关",
            "确认配置和接收人无误后，再打开真实发送开关。",
            real_send_enabled,
        ),
        _guide_item(
            "chat_demo",
            "在聊天里演示",
            "发送“生成这个月工资表和财务报表，并通过企业微信发给我”，预览确认后发送。",
            configured and real_send_enabled,
        ),
    ]


def _enterprise_wechat_demo_checklist(effective: dict[str, Any]) -> list[dict[str, Any]]:
    configured = bool(effective.get("configured"))
    real_send_enabled = bool(effective.get("real_send_enabled"))
    synced = bool(effective.get("last_sync_at"))
    return [
        _guide_item("demo_config", "企业微信应用参数已保存", "Corp ID、Agent ID、Secret 已填写。", configured),
        _guide_item("demo_scope", "应用可见范围包含自己", "企业微信后台的自建应用需要能给测试账号发消息。", configured),
        _guide_item("demo_contacts", "通讯录已同步或准备好 userid", "优先姓名搜索，找不到时聊天确认卡支持手动输入 userid。", synced),
        _guide_item("demo_group", "群聊可手动填 chat_id", "第一版群聊不强依赖同步，管理员可手动维护 chat_id。", True),
        _guide_item("demo_toggle", "真实发送开关已开启", "开关未开启时，用户只会看到等待管理员配置的提示。", real_send_enabled),
        _guide_item("demo_flow", "聊天里完成确认发送", "面试演示链路：生成工资表 + 财务报表 -> 预览确认 -> 企业微信发给自己。", configured and real_send_enabled),
    ]


def _guide_item(key: str, label: str, description: str, completed: bool) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "description": description,
        "status": "completed" if completed else "pending",
    }


def ensure_enterprise_wechat_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS enterprise_wechat_settings (
            id TEXT PRIMARY KEY DEFAULT 'default' CHECK (id = 'default'),
            corp_id TEXT,
            agent_id TEXT,
            secret TEXT,
            real_send_enabled BOOLEAN,
            timeout_seconds INTEGER NOT NULL DEFAULT 12 CHECK (timeout_seconds BETWEEN 1 AND 120),
            last_health_status TEXT,
            last_health_message TEXT,
            last_sync_at TIMESTAMPTZ,
            last_sync_result JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        INSERT INTO enterprise_wechat_settings (id)
        VALUES ('default')
        ON CONFLICT (id) DO NOTHING;

        CREATE TABLE IF NOT EXISTS enterprise_wechat_contacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            object_type TEXT NOT NULL
                CHECK (object_type IN ('user', 'group', 'department')),
            name TEXT NOT NULL,
            alias TEXT,
            wechat_userid TEXT,
            chat_id TEXT,
            department_id TEXT,
            department TEXT,
            phone TEXT,
            avatar_url TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_enterprise_wechat_contacts_search
        ON enterprise_wechat_contacts(active, object_type, name);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_enterprise_wechat_contacts_unique_target
        ON enterprise_wechat_contacts(
            object_type,
            name,
            COALESCE(wechat_userid, ''),
            COALESCE(chat_id, ''),
            COALESCE(department_id, '')
        );
        """
    )


def is_enterprise_wechat_configured() -> bool:
    return bool(get_enterprise_wechat_effective_settings()["configured"])


def enterprise_wechat_config_status() -> dict[str, Any]:
    effective = get_enterprise_wechat_effective_settings()
    configured = bool(effective["configured"])
    missing_fields = _missing_enterprise_wechat_config_fields(effective)
    return {
        "configured": configured,
        "real_send_enabled": bool(effective["real_send_enabled"]),
        "status": "configured" if configured else "not_configured",
        "message": (
            "企业微信应用参数已配置。"
            if configured
            else "缺少 WECHAT_WORK_CORP_ID / WECHAT_WORK_AGENT_ID / WECHAT_WORK_SECRET。"
        ),
        "config_source": effective["config_source"],
        "missing_fields": missing_fields,
        "setup_steps": _enterprise_wechat_setup_steps(effective),
    }


def get_enterprise_wechat_effective_settings() -> dict[str, Any]:
    ensure_enterprise_wechat_schema()
    row = _get_enterprise_wechat_settings_row()
    db_corp_id = _row_value(row, 1)
    db_agent_id = _row_value(row, 2)
    db_secret = _row_value(row, 3)
    db_real_send_enabled = _row_value(row, 4)
    db_timeout_seconds = _row_value(row, 5)
    corp_id = _normalize_optional_text(db_corp_id) or _normalize_optional_text(settings.wechat_work_corp_id)
    agent_id = _normalize_optional_text(db_agent_id) or _normalize_optional_text(settings.wechat_work_agent_id)
    secret = _normalize_optional_text(db_secret) or _normalize_optional_text(settings.wechat_work_secret)
    real_send_enabled = (
        bool(db_real_send_enabled)
        if db_real_send_enabled is not None
        else bool(settings.message_sender_real_send_enabled)
    )
    timeout_seconds = int(db_timeout_seconds or settings.wechat_work_timeout_seconds or 12)
    has_database_config = any(
        value is not None
        for value in (db_corp_id, db_agent_id, db_secret, db_real_send_enabled)
    )
    return {
        "corp_id": corp_id,
        "agent_id": agent_id,
        "secret": secret,
        "real_send_enabled": real_send_enabled,
        "timeout_seconds": max(1, min(timeout_seconds, 120)),
        "configured": bool(corp_id and agent_id and secret),
        "has_database_config": has_database_config,
        "config_source": "database" if has_database_config else "environment",
        "last_health_status": _row_value(row, 6),
        "last_health_message": _row_value(row, 7),
        "last_sync_at": _to_iso(_row_value(row, 8)),
        "last_sync_result": sanitize_metadata(_row_value(row, 9) or {}),
        "updated_at": _to_iso(_row_value(row, 11)),
    }


def get_enterprise_wechat_settings_public() -> dict[str, Any]:
    effective = get_enterprise_wechat_effective_settings()
    status = "configured" if effective["configured"] else "not_configured"
    if effective["configured"] and effective["real_send_enabled"]:
        status = "ready"
    elif effective["configured"]:
        status = "configured_waiting_real_send"

    return {
        "configured": bool(effective["configured"]),
        "real_send_enabled": bool(effective["real_send_enabled"]),
        "status": status,
        "message": _settings_public_message(effective),
        "config_source": effective["config_source"],
        "has_database_config": bool(effective["has_database_config"]),
        "timeout_seconds": effective["timeout_seconds"],
        "last_health_status": effective["last_health_status"],
        "last_health_message": effective["last_health_message"],
        "last_sync_at": effective["last_sync_at"],
        "last_sync_result": effective["last_sync_result"],
        "missing_fields": _missing_enterprise_wechat_config_fields(effective),
        "setup_steps": _enterprise_wechat_setup_steps(effective),
        "demo_checklist": _enterprise_wechat_demo_checklist(effective),
        "config_fields": [
            _public_config_field("corp_id", effective["corp_id"], False, "企业微信 Corp ID"),
            _public_config_field("agent_id", effective["agent_id"], True, "企业微信应用 Agent ID"),
            _public_config_field("secret", effective["secret"], True, "企业微信应用 Secret"),
        ],
    }


def update_enterprise_wechat_settings(
    *,
    corp_id: str | None = None,
    agent_id: str | None = None,
    secret: str | None = None,
    real_send_enabled: bool | None = None,
    timeout_seconds: int | None = None,
    clear_secret: bool = False,
) -> dict[str, Any]:
    ensure_enterprise_wechat_schema()
    row = _get_enterprise_wechat_settings_row()
    current_corp_id = _normalize_optional_text(_row_value(row, 1))
    current_agent_id = _normalize_optional_text(_row_value(row, 2))
    current_secret = _normalize_optional_text(_row_value(row, 3))
    current_real_send_enabled = _row_value(row, 4)
    next_corp_id = _normalize_optional_text(corp_id) or current_corp_id
    next_agent_id = _normalize_optional_text(agent_id) or current_agent_id
    next_secret = None if clear_secret else (_normalize_optional_text(secret) or current_secret)
    next_real_send_enabled = real_send_enabled if real_send_enabled is not None else current_real_send_enabled
    next_timeout = max(1, min(int(timeout_seconds or _row_value(row, 5) or settings.wechat_work_timeout_seconds or 12), 120))
    execute(
        """
        INSERT INTO enterprise_wechat_settings (
            id, corp_id, agent_id, secret, real_send_enabled, timeout_seconds, updated_at
        )
        VALUES ('default', %s, %s, %s, %s, %s, now())
        ON CONFLICT (id) DO UPDATE
        SET corp_id = EXCLUDED.corp_id,
            agent_id = EXCLUDED.agent_id,
            secret = EXCLUDED.secret,
            real_send_enabled = EXCLUDED.real_send_enabled,
            timeout_seconds = EXCLUDED.timeout_seconds,
            updated_at = now();
        """,
        (
            next_corp_id,
            next_agent_id,
            next_secret,
            next_real_send_enabled,
            next_timeout,
        ),
    )
    _clear_access_token_cache()
    return get_enterprise_wechat_settings_public()


def search_enterprise_wechat_recipients(
    query: str,
    *,
    object_types: list[str] | None = None,
    limit: int = 8,
    current_user: dict | None = None,
) -> dict[str, Any]:
    ensure_enterprise_wechat_schema()
    normalized_query = _normalize_search_query(query)
    requested_types = _normalize_object_types(object_types)
    if not normalized_query:
        return {
            "query": "",
            "items": [],
            "matched_count": 0,
            "needs_selection": True,
            "message": "请先输入要搜索的企业微信联系人、群聊或部门名称。",
        }

    rows = _search_cached_contacts(
        normalized_query,
        object_types=requested_types,
        limit=limit,
    )
    items = [_contact_row_to_public(row) for row in rows]

    if not items:
        items = _fallback_user_contacts(normalized_query, limit=limit)

    exact_items = [
        item
        for item in items
        if item["name"] == normalized_query or normalized_query in item.get("aliases", [])
    ]
    selected_item = exact_items[0] if len(exact_items) == 1 else None
    needs_selection = not bool(selected_item) and len(items) != 1

    return {
        "query": normalized_query,
        "items": items,
        "matched_count": len(items),
        "needs_selection": needs_selection,
        "selected_item": selected_item,
        "message": _candidate_message(normalized_query, items, selected_item=selected_item, needs_selection=needs_selection),
        "source": "enterprise_wechat_contacts" if rows else "users_fallback",
        "display_fields": ["头像", "姓名", "对象类型", "部门", "手机号后四位"],
        "llm_direct_execution_allowed": False,
    }


def get_enterprise_wechat_contact(contact_id: str) -> dict[str, Any] | None:
    ensure_enterprise_wechat_schema()
    row = fetch_one(
        """
        SELECT id, object_type, name, alias, wechat_userid, chat_id, department_id,
               department, phone, avatar_url, metadata, active, created_at, updated_at
        FROM enterprise_wechat_contacts
        WHERE id = %s AND active = TRUE
        LIMIT 1;
        """,
        (contact_id,),
    )
    return _contact_row_to_public(row) if row else None


def upsert_enterprise_wechat_contact(
    *,
    object_type: str,
    name: str,
    wechat_userid: str | None = None,
    chat_id: str | None = None,
    department_id: str | None = None,
    alias: str | None = None,
    department: str | None = None,
    phone: str | None = None,
    avatar_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_enterprise_wechat_schema()
    normalized_type = _normalize_object_type(object_type)
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("联系人名称不能为空。")

    normalized_wechat_userid = str(wechat_userid or "").strip() or None
    normalized_chat_id = str(chat_id or "").strip() or None
    normalized_department_id = str(department_id or "").strip() or None
    metadata_json = dumps_json(sanitize_metadata(metadata or {}))
    existing = fetch_one(
        """
        SELECT id
        FROM enterprise_wechat_contacts
        WHERE object_type = %s
          AND name = %s
          AND COALESCE(wechat_userid, '') = COALESCE(%s, '')
          AND COALESCE(chat_id, '') = COALESCE(%s, '')
          AND COALESCE(department_id, '') = COALESCE(%s, '')
        LIMIT 1;
        """,
        (
            normalized_type,
            normalized_name,
            normalized_wechat_userid,
            normalized_chat_id,
            normalized_department_id,
        ),
    )
    if existing:
        row = fetch_one(
            """
            UPDATE enterprise_wechat_contacts
            SET alias = %s,
                department = %s,
                phone = %s,
                avatar_url = %s,
                metadata = %s::jsonb,
                active = TRUE,
                updated_at = now()
            WHERE id = %s
            RETURNING id, object_type, name, alias, wechat_userid, chat_id, department_id,
                      department, phone, avatar_url, metadata, active, created_at, updated_at;
            """,
            (
                alias,
                department,
                phone,
                avatar_url,
                metadata_json,
                existing[0],
            ),
        )
    else:
        row = fetch_one(
            """
            INSERT INTO enterprise_wechat_contacts (
                object_type, name, alias, wechat_userid, chat_id, department_id,
                department, phone, avatar_url, metadata, active, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, TRUE, now())
            RETURNING id, object_type, name, alias, wechat_userid, chat_id, department_id,
                      department, phone, avatar_url, metadata, active, created_at, updated_at;
            """,
            (
                normalized_type,
                normalized_name,
                alias,
                normalized_wechat_userid,
                normalized_chat_id,
                normalized_department_id,
                department,
                phone,
                avatar_url,
                metadata_json,
            ),
        )
    return _contact_row_to_public(row)


def list_enterprise_wechat_contacts(
    *,
    query: str = "",
    object_type: str = "all",
    limit: int = 50,
) -> dict[str, Any]:
    ensure_enterprise_wechat_schema()
    requested_types = _normalize_object_types([] if object_type in {"", "all"} else [object_type])
    normalized_query = _normalize_search_query(query)
    rows = _list_cached_contacts(
        normalized_query,
        object_types=requested_types,
        limit=max(1, min(limit, 100)),
    )
    items = [_contact_row_to_public(row) for row in rows]
    return {
        "query": normalized_query,
        "object_type": object_type or "all",
        "items": items,
        "matched_count": len(items),
        "summary": enterprise_wechat_contacts_summary(),
    }


def enterprise_wechat_contacts_summary() -> dict[str, Any]:
    ensure_enterprise_wechat_schema()
    rows = fetch_all(
        """
        SELECT object_type, COUNT(*)
        FROM enterprise_wechat_contacts
        WHERE active = TRUE
        GROUP BY object_type;
        """
    )
    counts = {str(row[0]): int(row[1] or 0) for row in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "users": counts.get("user", 0),
        "departments": counts.get("department", 0),
        "groups": counts.get("group", 0),
    }


def upsert_enterprise_wechat_manual_group(*, name: str, chat_id: str) -> dict[str, Any]:
    normalized_name = name.strip()
    normalized_chat_id = chat_id.strip()
    if not normalized_name:
        raise ValueError("群聊名称不能为空。")
    if not normalized_chat_id:
        raise ValueError("群聊 chat_id 不能为空。")
    return upsert_enterprise_wechat_contact(
        object_type="group",
        name=normalized_name,
        chat_id=normalized_chat_id,
        metadata={
            "source": "admin.manual_group",
            "note": "管理员在连接器中心手动录入的企业微信群聊。",
        },
    )


def get_enterprise_wechat_admin_state() -> dict[str, Any]:
    settings_public = get_enterprise_wechat_settings_public()
    contacts = list_enterprise_wechat_contacts(limit=20)
    return {
        "settings": settings_public,
        "contacts": contacts,
        "diagnostics": build_enterprise_wechat_diagnostics(settings_public),
    }


def build_enterprise_wechat_diagnostics(settings_public: dict[str, Any] | None = None) -> dict[str, Any]:
    settings_payload = settings_public or get_enterprise_wechat_settings_public()
    last_sync_result = settings_payload.get("last_sync_result") if isinstance(settings_payload.get("last_sync_result"), dict) else {}
    steps = last_sync_result.get("steps") if isinstance(last_sync_result.get("steps"), list) else []
    if not steps:
        steps = [
            _diagnostic_step("取 token", "pending", "等待管理员点击一键同步或测试发送。"),
            _diagnostic_step("拉部门", "pending", "等待同步企业微信部门。"),
            _diagnostic_step("拉成员", "pending", "等待同步企业微信成员。"),
            _diagnostic_step("写入缓存", "pending", "等待写入本地候选缓存。"),
            _diagnostic_step("发送测试", "pending", "等待管理员选择接收对象发送安全测试文件。"),
        ]
    return {
        "status": settings_payload.get("last_health_status") or settings_payload.get("status") or "pending",
        "message": settings_payload.get("last_health_message") or settings_payload.get("message") or "",
        "steps": steps,
        "last_sync_at": settings_payload.get("last_sync_at"),
    }


def sync_enterprise_wechat_departments_and_users(limit_departments: int = 200) -> dict[str, Any]:
    steps = [
        _diagnostic_step("取 token", "pending", "准备获取企业微信 access_token。"),
        _diagnostic_step("拉部门", "pending", "等待读取企业微信部门。"),
        _diagnostic_step("拉成员", "pending", "等待按部门读取成员。"),
        _diagnostic_step("写入缓存", "pending", "等待写入本地候选缓存。"),
        _diagnostic_step("发送测试", "pending", "同步阶段不会发送测试文件。"),
    ]

    if not is_enterprise_wechat_configured():
        steps[0] = _diagnostic_step("取 token", "failed", enterprise_wechat_config_status()["message"])
        result = {
            "ok": False,
            "status": "not_configured",
            "message": enterprise_wechat_config_status()["message"],
            "synced_count": 0,
            "steps": steps,
        }
        _update_enterprise_wechat_runtime_status(result)
        return {
            **result,
            "contacts_summary": enterprise_wechat_contacts_summary(),
        }

    try:
        _access_token()
        steps[0] = _diagnostic_step("取 token", "completed", "access_token 获取成功。")
        departments = _wechat_api_request("GET", "/department/list")
        department_items = departments.get("department") if isinstance(departments.get("department"), list) else []
        steps[1] = _diagnostic_step("拉部门", "completed", f"读取到 {len(department_items)} 个部门。")
    except EnterpriseWechatApiError as error:
        failed_index = 1 if steps[0]["status"] == "completed" else 0
        steps[failed_index] = _diagnostic_step(steps[failed_index]["label"], "failed", str(error))
        error_payload = _enterprise_wechat_api_error_payload(error)
        result = {
            "ok": False,
            "status": "failed",
            "message": str(error),
            "synced_count": 0,
            "steps": steps,
            **error_payload,
        }
        _update_enterprise_wechat_runtime_status(result)
        return {
            **result,
            "contacts_summary": enterprise_wechat_contacts_summary(),
        }

    department_items = departments.get("department") if isinstance(departments.get("department"), list) else []
    synced_count = 0
    department_count = 0
    user_count = 0
    user_errors: list[str] = []
    for department in department_items[: max(1, min(limit_departments, 200))]:
        if not isinstance(department, dict):
            continue
        department_id = str(department.get("id") or "").strip()
        department_name = str(department.get("name") or "").strip()
        if department_name and department_id:
            upsert_enterprise_wechat_contact(
                object_type="department",
                name=department_name,
                department_id=department_id,
                metadata={"source": "wechat_api.department.list"},
            )
            synced_count += 1
            department_count += 1
        if department_id:
            try:
                synced_users = _sync_department_users(department_id, department_name)
                synced_count += synced_users
                user_count += synced_users
            except EnterpriseWechatApiError as error:
                user_errors.append(f"{department_name or department_id}：{error}")

    if user_errors:
        steps[2] = _diagnostic_step("拉成员", "degraded", f"部分部门成员读取失败：{user_errors[0]}")
    else:
        steps[2] = _diagnostic_step("拉成员", "completed", f"同步 {user_count} 个成员。")
    steps[3] = _diagnostic_step("写入缓存", "completed", f"写入 {department_count} 个部门、{user_count} 个成员。")

    summary = enterprise_wechat_contacts_summary()
    result_status = "degraded" if user_errors else "completed"
    result = {
        "ok": not user_errors,
        "status": result_status,
        "message": f"企业微信通讯录已同步 {synced_count} 个对象。",
        "synced_count": synced_count,
        "department_count": department_count,
        "user_count": user_count,
        "group_count": summary["groups"],
        "contacts_summary": summary,
        "steps": steps,
        "errors": user_errors[:5],
    }
    _update_enterprise_wechat_runtime_status(result)

    return result


def send_enterprise_wechat_test_file(*, recipient: dict[str, Any]) -> dict[str, Any]:
    steps = [
        _diagnostic_step("取 token", "pending", "准备获取企业微信 access_token。"),
        _diagnostic_step("拉部门", "skipped", "测试发送不需要重新拉取部门。"),
        _diagnostic_step("拉成员", "skipped", "测试发送使用已选择的通讯录候选。"),
        _diagnostic_step("写入缓存", "skipped", "测试发送不会修改通讯录缓存。"),
        _diagnostic_step("发送测试", "pending", "准备发送安全测试文件。"),
    ]
    if not is_enterprise_wechat_configured():
        steps[0] = _diagnostic_step("取 token", "failed", enterprise_wechat_config_status()["message"])
        result = {
            "ok": False,
            "status": "not_configured",
            "message": enterprise_wechat_config_status()["message"],
            "steps": steps,
            "sent": False,
        }
        _update_enterprise_wechat_runtime_status(result)
        return result
    if not get_enterprise_wechat_effective_settings()["real_send_enabled"]:
        steps[4] = _diagnostic_step("发送测试", "blocked", "真实发送开关未启用，测试文件没有发出。")
        result = {
            "ok": True,
            "status": "waiting_executor",
            "message": "真实发送开关未启用，已完成测试发送预检但没有真正发出文件。",
            "steps": steps,
            "sent": False,
        }
        _update_enterprise_wechat_runtime_status(result)
        return result

    try:
        _access_token()
        steps[0] = _diagnostic_step("取 token", "completed", "access_token 获取成功。")
        execution = send_enterprise_wechat_file(
            recipient=recipient,
            attachments=[
                EnterpriseWechatAttachment(
                    filename="企业微信连接器安全测试.txt",
                    content=(
                        "这是一份由 AI automated back-end management system 生成的安全测试文件，"
                        "用于验证企业微信文件发送链路。"
                    ).encode("utf-8"),
                    mime_type="text/plain",
                )
            ],
            confirmed=True,
            sensitive_confirmed=True,
        )
        steps[4] = _diagnostic_step(
            "发送测试",
            "completed" if execution.get("sent") else str(execution.get("status") or "completed"),
            str(execution.get("message") or "测试发送完成。"),
        )
        result = {
            **execution,
            "steps": steps,
        }
        _update_enterprise_wechat_runtime_status(result)
        return result
    except EnterpriseWechatApiError as error:
        steps[4] = _diagnostic_step("发送测试", "failed", str(error))
        error_payload = _enterprise_wechat_api_error_payload(error)
        result = {
            "ok": False,
            "status": "failed",
            "message": str(error),
            "steps": steps,
            "sent": False,
            **error_payload,
        }
        _update_enterprise_wechat_runtime_status(result)
        return result


def send_enterprise_wechat_file(
    *,
    recipient: dict[str, Any],
    attachments: list[EnterpriseWechatAttachment],
    confirmed: bool,
    sensitive_confirmed: bool,
    safe: int = 0,
) -> dict[str, Any]:
    if not confirmed:
        return {
            "ok": False,
            "status": "waiting_confirmation",
            "message": "发送前需要确认企业微信接收对象。",
            "requires_confirmation": True,
        }
    if not sensitive_confirmed:
        return {
            "ok": False,
            "status": "waiting_confirmation",
            "message": "文件包含工资或财务敏感数据，发送前需要确认。",
            "requires_sensitive_confirmation": True,
        }
    if not attachments:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "没有可发送的文件附件。",
        }
    effective_settings = get_enterprise_wechat_effective_settings()
    if not effective_settings["real_send_enabled"]:
        return {
            "ok": True,
            "status": "waiting_executor",
            "message": "文件已生成，等待管理员配置企业微信真实发送",
            "channel": "enterprise_wechat",
            "recipient": _recipient_public_for_send(recipient),
            "attachment_count": len(attachments),
            "api_diagnostics": [],
            "request_response_trace": [],
            "sent": False,
        }
    if not effective_settings["configured"]:
        return {
            "ok": False,
            "status": "not_configured",
            "message": enterprise_wechat_config_status()["message"],
            "channel": "enterprise_wechat",
            "recipient": _recipient_public_for_send(recipient),
            "missing_fields": _missing_enterprise_wechat_config_fields(effective_settings),
            "setup_steps": _enterprise_wechat_setup_steps(effective_settings),
            "api_diagnostics": [],
            "request_response_trace": [],
            "sent": False,
        }

    uploaded_media = []
    for attachment in attachments:
        uploaded_media.append(_upload_media_file(attachment))

    send_results = []
    for media, attachment in zip(uploaded_media, attachments):
        send_results.append(
            _send_file_media(
                recipient=recipient,
                media_id=str(media["media_id"]),
                safe=safe,
                filename=attachment.filename,
            )
        )
    request_response_trace = _collect_request_response_trace(
        [
            *(item.get("_diagnostic") for item in uploaded_media if isinstance(item, dict)),
            *(item.get("_diagnostic") for item in send_results if isinstance(item, dict)),
        ]
    )

    return {
        "ok": True,
        "status": "completed",
        "message": "企业微信文件已发送。",
        "channel": "enterprise_wechat",
        "recipient": _recipient_public_for_send(recipient),
        "attachment_count": len(attachments),
        "message_ids": [
            item.get("msgid")
            for item in send_results
            if isinstance(item, dict) and item.get("msgid")
        ],
        "send_results": [_strip_internal_diagnostics(item) for item in send_results],
        "api_diagnostics": request_response_trace,
        "request_response_trace": request_response_trace,
        "sent": True,
    }


def attachment_from_storage_reference(storage_reference: dict[str, Any]) -> EnterpriseWechatAttachment:
    path = Path(str(storage_reference["storage_path"]))
    return EnterpriseWechatAttachment(
        filename=str(storage_reference.get("filename") or path.name),
        content=path.read_bytes(),
        mime_type=str(storage_reference.get("mime_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream"),
    )


def recipient_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    object_type = _normalize_object_type(str(candidate.get("object_type") or "user"))
    return {
        "id": str(candidate.get("id") or ""),
        "object_type": object_type,
        "name": str(candidate.get("name") or ""),
        "wechat_userid": candidate.get("wechat_userid"),
        "chat_id": candidate.get("chat_id"),
        "department_id": candidate.get("department_id"),
        "department": candidate.get("department"),
        "avatar_url": candidate.get("avatar_url"),
        "phone_last4": candidate.get("phone_last4"),
    }


def _sync_department_users(department_id: str, department_name: str) -> int:
    data = _wechat_api_request(
        "GET",
        "/user/list",
        query={
            "department_id": department_id,
            "fetch_child": 0,
        },
    )

    users = data.get("userlist") if isinstance(data.get("userlist"), list) else []
    synced_count = 0
    for user in users:
        if not isinstance(user, dict):
            continue
        userid = str(user.get("userid") or "").strip()
        name = str(user.get("name") or "").strip()
        if not userid or not name:
            continue
        upsert_enterprise_wechat_contact(
            object_type="user",
            name=name,
            wechat_userid=userid,
            alias=str(user.get("alias") or "").strip() or None,
            department=department_name,
            phone=str(user.get("mobile") or "").strip() or None,
            avatar_url=str(user.get("avatar") or "").strip() or None,
            metadata={
                "source": "wechat_api.user.list",
                "department_id": department_id,
                "email": user.get("email"),
                "position": user.get("position"),
            },
        )
        synced_count += 1
    return synced_count


def _search_cached_contacts(query: str, *, object_types: list[str], limit: int):
    like = f"%{query}%"
    rows = fetch_all(
        """
        SELECT id, object_type, name, alias, wechat_userid, chat_id, department_id,
               department, phone, avatar_url, metadata, active, created_at, updated_at
        FROM enterprise_wechat_contacts
        WHERE active = TRUE
          AND object_type = ANY(%s)
          AND (
              name ILIKE %s
              OR COALESCE(alias, '') ILIKE %s
              OR COALESCE(department, '') ILIKE %s
              OR COALESCE(wechat_userid, '') ILIKE %s
              OR COALESCE(chat_id, '') ILIKE %s
              OR COALESCE(department_id, '') ILIKE %s
          )
        ORDER BY
          CASE WHEN name = %s THEN 0 WHEN name ILIKE %s THEN 1 ELSE 2 END,
          object_type,
          name
        LIMIT %s;
        """,
        (
            object_types,
            like,
            like,
            like,
            like,
            like,
            like,
            query,
            f"{query}%",
            max(1, min(limit, 20)),
        ),
    )
    return rows


def _fallback_user_contacts(query: str, *, limit: int) -> list[dict[str, Any]]:
    like = f"%{query}%"
    rows = fetch_all(
        """
        SELECT id, username, display_name, email, department, position
        FROM users
        WHERE COALESCE(display_name, username, '') ILIKE %s
           OR username ILIKE %s
           OR COALESCE(email, '') ILIKE %s
        ORDER BY CASE WHEN COALESCE(display_name, username) = %s THEN 0 ELSE 1 END,
                 COALESCE(display_name, username)
        LIMIT %s;
        """,
        (like, like, like, query, max(1, min(limit, 20))),
    )
    items = []
    for row in rows:
        display_name = str(row[2] or row[1] or "")
        items.append({
            "id": f"user-fallback:{row[0]}",
            "object_type": "user",
            "object_type_label": "成员",
            "name": display_name,
            "aliases": [str(row[1] or "")],
            "wechat_userid": str(row[1] or ""),
            "chat_id": None,
            "department_id": None,
            "department": row[4],
            "avatar_url": None,
            "avatar_text": display_name[:1] or "人",
            "phone_last4": "",
            "masked_phone": "",
            "source": "users_fallback",
            "send_target": {
                "kind": "user",
                "value": str(row[1] or ""),
            },
        })
    return items


def _contact_row_to_public(row) -> dict[str, Any]:
    metadata = row[10] or {}
    aliases = [
        item
        for item in [
            row[3],
            metadata.get("pinyin") if isinstance(metadata, dict) else None,
            metadata.get("english_name") if isinstance(metadata, dict) else None,
        ]
        if item
    ]
    object_type = str(row[1])
    name = str(row[2])
    return {
        "id": str(row[0]),
        "object_type": object_type,
        "object_type_label": _object_type_label(object_type),
        "name": name,
        "aliases": aliases,
        "wechat_userid": row[4],
        "chat_id": row[5],
        "department_id": row[6],
        "department": row[7],
        "avatar_url": row[9],
        "avatar_text": name[:1] or _object_type_label(object_type)[:1],
        "phone_last4": _phone_last4(row[8]),
        "masked_phone": _masked_phone(row[8]),
        "source": "enterprise_wechat_contacts",
        "send_target": _send_target_for_contact(
            object_type=object_type,
            wechat_userid=row[4],
            chat_id=row[5],
            department_id=row[6],
        ),
        "metadata": sanitize_metadata(metadata),
    }


def _candidate_message(
    query: str,
    items: list[dict[str, Any]],
    *,
    selected_item: dict[str, Any] | None = None,
    needs_selection: bool = True,
) -> str:
    if not items:
        return f"没有在企业微信通讯录中找到“{query}”。你可以直接手动输入 userid / chat_id / department_id 后继续。"
    if selected_item and not needs_selection:
        return f"已找到最匹配的企业微信接收对象：{selected_item['name']}。发送前仍需要你确认。"
    if len(items) == 1:
        return f"已找到 1 个企业微信接收对象，发送前仍需要你确认。"
    return f"找到 {len(items)} 个可能的接收对象，请先选择正确的人、群聊或部门。若都不对，可手动输入 userid / chat_id / department_id。"


def _send_target_for_contact(
    *,
    object_type: str,
    wechat_userid: str | None,
    chat_id: str | None,
    department_id: str | None,
) -> dict[str, str | None]:
    if object_type == "group":
        return {"kind": "group", "value": chat_id}
    if object_type == "department":
        return {"kind": "department", "value": department_id}
    return {"kind": "user", "value": wechat_userid}


def _recipient_public_for_send(recipient: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": recipient.get("id"),
        "object_type": recipient.get("object_type"),
        "object_type_label": _object_type_label(str(recipient.get("object_type") or "")),
        "name": recipient.get("name"),
        "department": recipient.get("department"),
        "phone_last4": recipient.get("phone_last4"),
        "avatar_url": recipient.get("avatar_url"),
    }


def _upload_media_file(attachment: EnterpriseWechatAttachment) -> dict[str, Any]:
    boundary = f"----company-rag-{uuid4().hex}"
    payload = _multipart_file_payload(boundary=boundary, attachment=attachment)
    data = _wechat_api_request(
        "POST",
        "/media/upload",
        query={"type": "file"},
        raw_body=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    media_id = data.get("media_id")
    if not media_id:
        raise EnterpriseWechatApiError(
            "企业微信上传文件后没有返回 media_id。",
            path="/media/upload",
            diagnostic=data.get("_diagnostic") if isinstance(data.get("_diagnostic"), dict) else None,
        )
    return {
        "media_id": str(media_id),
        "filename": attachment.filename,
        "_diagnostic": data.get("_diagnostic"),
    }


def _send_file_media(
    *,
    recipient: dict[str, Any],
    media_id: str,
    safe: int,
    filename: str,
) -> dict[str, Any]:
    object_type = _normalize_object_type(str(recipient.get("object_type") or "user"))
    if object_type == "group":
        chat_id = str(recipient.get("chat_id") or "").strip()
        if not chat_id:
            raise EnterpriseWechatApiError("企业微信群聊缺少 chat_id。")
        return _wechat_api_request(
            "POST",
            "/appchat/send",
            body={
                "chatid": chat_id,
                "msgtype": "file",
                "file": {"media_id": media_id},
                "safe": safe,
            },
        )

    effective_settings = get_enterprise_wechat_effective_settings()
    try:
        agent_id = int(effective_settings["agent_id"])
    except (TypeError, ValueError) as error:
        raise EnterpriseWechatApiError("企业微信 Agent ID 必须是数字。") from error
    body: dict[str, Any] = {
        "msgtype": "file",
        "agentid": agent_id,
        "file": {"media_id": media_id},
        "safe": safe,
        "enable_duplicate_check": 0,
    }
    if object_type == "department":
        department_id = str(recipient.get("department_id") or "").strip()
        if not department_id:
            raise EnterpriseWechatApiError("企业微信部门缺少 department_id。")
        body["toparty"] = department_id
    else:
        userid = str(recipient.get("wechat_userid") or "").strip()
        if not userid:
            raise EnterpriseWechatApiError("企业微信成员缺少 userid。")
        body["touser"] = userid

    result = _wechat_api_request("POST", "/message/send", body=body)
    result["filename"] = filename
    return result


def _wechat_api_request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    query_params = dict(query or {})
    if path != "/gettoken":
        query_params["access_token"] = _access_token()
    url = f"{WECHAT_API_BASE_URL}{path}"
    if query_params:
        url = f"{url}?{urlencode(query_params)}"

    request_headers = {
        "Content-Type": "application/json; charset=utf-8",
        **(headers or {}),
    }
    payload = raw_body
    if payload is None and body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

    diagnostic = _wechat_api_diagnostic(
        method=method,
        path=path,
        query_params=query_params,
        body=body,
        raw_body=raw_body,
        headers=request_headers,
    )
    request = Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=get_enterprise_wechat_effective_settings()["timeout_seconds"]) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        diagnostic.update({
            "ok": False,
            "http_status": error.code,
            "response": _redact_enterprise_wechat_value(_safe_json_or_text(error_body)),
        })
        raise EnterpriseWechatApiError(
            f"企业微信 HTTP 调用失败：status={error.code}",
            path=path,
            diagnostic=diagnostic,
        ) from error
    except URLError as error:
        diagnostic.update({"ok": False, "network_error": str(error.reason)})
        raise EnterpriseWechatApiError(
            f"企业微信网络调用失败：{error.reason}",
            path=path,
            diagnostic=diagnostic,
        ) from error

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError as error:
        diagnostic.update({
            "ok": False,
            "response": _redact_enterprise_wechat_value(response_body[:300]),
        })
        raise EnterpriseWechatApiError(
            f"企业微信响应不是合法 JSON：{response_body[:300]}",
            path=path,
            diagnostic=diagnostic,
        ) from error

    diagnostic.update({
        "ok": True,
        "errcode": result.get("errcode"),
        "errmsg": result.get("errmsg"),
        "response": _redact_enterprise_wechat_value(result),
    })

    errcode = int(result.get("errcode", 0) or 0)
    if errcode != 0:
        errmsg = result.get("errmsg") or "unknown error"
        diagnostic["ok"] = False
        raise EnterpriseWechatApiError(
            f"企业微信 API 调用失败：errcode={errcode}, errmsg={errmsg}, path={path}",
            errcode=errcode,
            errmsg=str(errmsg),
            path=path,
            diagnostic=diagnostic,
        )
    result["_diagnostic"] = diagnostic
    return result


def _access_token() -> str:
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRES_AT, _ACCESS_TOKEN_CACHE_KEY
    effective_settings = get_enterprise_wechat_effective_settings()
    cache_key = f"{effective_settings['corp_id']}:{effective_settings['secret']}"
    now = time.time()
    if _ACCESS_TOKEN and _ACCESS_TOKEN_CACHE_KEY == cache_key and now < _ACCESS_TOKEN_EXPIRES_AT - 60:
        return _ACCESS_TOKEN
    if not effective_settings["configured"]:
        status_payload = enterprise_wechat_config_status()
        raise EnterpriseWechatApiError(
            status_payload["message"],
            path="/gettoken",
            diagnostic={
                "ok": False,
                "method": "GET",
                "path": "/gettoken",
                "missing_fields": status_payload.get("missing_fields"),
                "setup_steps": status_payload.get("setup_steps"),
            },
        )

    url = f"{WECHAT_API_BASE_URL}/gettoken?{urlencode({'corpid': effective_settings['corp_id'], 'corpsecret': effective_settings['secret']})}"
    diagnostic = _wechat_api_diagnostic(
        method="GET",
        path="/gettoken",
        query_params={"corpid": effective_settings["corp_id"], "corpsecret": effective_settings["secret"]},
    )
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=effective_settings["timeout_seconds"]) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        diagnostic.update({
            "ok": False,
            "http_status": error.code,
            "response": _redact_enterprise_wechat_value(_safe_json_or_text(error_body)),
        })
        raise EnterpriseWechatApiError(
            f"企业微信 access_token 获取失败：status={error.code}",
            path="/gettoken",
            diagnostic=diagnostic,
        ) from error
    except URLError as error:
        diagnostic.update({"ok": False, "network_error": str(error.reason)})
        raise EnterpriseWechatApiError(
            f"企业微信 access_token 网络失败：{error.reason}",
            path="/gettoken",
            diagnostic=diagnostic,
        ) from error

    try:
        result = json.loads(response_body)
    except json.JSONDecodeError as error:
        diagnostic.update({
            "ok": False,
            "response": _redact_enterprise_wechat_value(response_body[:300]),
        })
        raise EnterpriseWechatApiError(
            f"企业微信 access_token 响应不是合法 JSON：{response_body[:300]}",
            path="/gettoken",
            diagnostic=diagnostic,
        ) from error
    diagnostic.update({
        "ok": True,
        "errcode": result.get("errcode"),
        "errmsg": result.get("errmsg"),
        "response": _redact_enterprise_wechat_value(result),
    })
    errcode = int(result.get("errcode", 0) or 0)
    if errcode != 0:
        errmsg = str(result.get("errmsg") or "unknown error")
        diagnostic["ok"] = False
        raise EnterpriseWechatApiError(
            f"企业微信 access_token 获取失败：errcode={errcode}, errmsg={errmsg}",
            errcode=errcode,
            errmsg=errmsg,
            path="/gettoken",
            diagnostic=diagnostic,
        )
    token = result.get("access_token")
    if not token:
        diagnostic["ok"] = False
        raise EnterpriseWechatApiError(
            "企业微信没有返回 access_token。",
            path="/gettoken",
            diagnostic=diagnostic,
        )
    _ACCESS_TOKEN = str(token)
    _ACCESS_TOKEN_CACHE_KEY = cache_key
    _ACCESS_TOKEN_EXPIRES_AT = now + int(result.get("expires_in", 7200) or 7200)
    return _ACCESS_TOKEN


def _multipart_file_payload(*, boundary: str, attachment: EnterpriseWechatAttachment) -> bytes:
    filename = attachment.filename or "attachment"
    mime_type = attachment.mime_type or "application/octet-stream"
    chunks = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8"),
        attachment.content,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(chunks)


def _wechat_api_diagnostic(
    *,
    method: str,
    path: str,
    query_params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    raw_body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    query = query_params or {}
    return {
        "method": method.upper(),
        "path": path,
        "url": _redacted_wechat_url(path, query),
        "query": _redact_enterprise_wechat_value(query),
        "headers": _redact_enterprise_wechat_value(headers or {}),
        "request": (
            _redact_enterprise_wechat_value(body)
            if body is not None
            else {
                "body_type": "multipart" if raw_body else "empty",
                "bytes": len(raw_body or b""),
            }
        ),
    }


def _redacted_wechat_url(path: str, query_params: dict[str, Any] | None = None) -> str:
    query = _redact_enterprise_wechat_value(query_params or {})
    url = f"{WECHAT_API_BASE_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return re.sub(r"(?i)(access_token|corpsecret)=([^&]+)", r"\1=[REDACTED]", url)


def _redact_enterprise_wechat_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_enterprise_wechat_secret_key(key_text):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = _redact_enterprise_wechat_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_enterprise_wechat_value(item) for item in value[:_API_TRACE_LIMIT]]
    if isinstance(value, tuple):
        return [_redact_enterprise_wechat_value(item) for item in value[:_API_TRACE_LIMIT]]
    if isinstance(value, bytes):
        return {"body_type": "bytes", "bytes": len(value)}
    if isinstance(value, str):
        text = value
        patterns = [
            r"(?i)(access_token|corpsecret|secret|token|password|api_key|apikey)=([^&\s]+)",
            r"(?i)(\"(?:access_token|corpsecret|secret|token|password|api_key|apikey)\"\s*:\s*\")([^\"]+)(\")",
        ]
        text = re.sub(patterns[0], r"\1=[REDACTED]", text)
        text = re.sub(patterns[1], r"\1[REDACTED]\3", text)
        return text[:1200]
    return value


def _is_enterprise_wechat_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        keyword in lowered
        for keyword in [
            "secret",
            "token",
            "access_token",
            "corpsecret",
            "password",
            "authorization",
            "cookie",
            "api_key",
            "apikey",
        ]
    )


def _safe_json_or_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text[:1200]


def _extract_wechat_error(value: dict[str, Any] | None) -> dict[str, Any]:
    payload = value if isinstance(value, dict) else {}
    diagnostic = payload.get("_diagnostic") if isinstance(payload.get("_diagnostic"), dict) else {}
    errcode = payload.get("errcode", diagnostic.get("errcode"))
    errmsg = payload.get("errmsg", diagnostic.get("errmsg"))
    return {
        "wechat_error_code": errcode,
        "wechat_error_message": errmsg,
        "api_diagnostics": _collect_request_response_trace([diagnostic]),
        "request_response_trace": _collect_request_response_trace([diagnostic]),
    }


def _collect_request_response_trace(items: list[Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        traces.append(_redact_enterprise_wechat_value(item))
        if len(traces) >= _API_TRACE_LIMIT:
            break
    return traces


def _strip_internal_diagnostics(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return value
    return {
        key: item
        for key, item in value.items()
        if key != "_diagnostic"
    }


def _enterprise_wechat_api_error_payload(error: EnterpriseWechatApiError) -> dict[str, Any]:
    return {
        "wechat_error_code": error.errcode,
        "wechat_error_message": error.errmsg,
        "api_diagnostics": _collect_request_response_trace([error.diagnostic]),
        "request_response_trace": _collect_request_response_trace([error.diagnostic]),
    }


def _get_enterprise_wechat_settings_row():
    return fetch_one(
        """
        SELECT id, corp_id, agent_id, secret, real_send_enabled, timeout_seconds,
               last_health_status, last_health_message, last_sync_at, last_sync_result,
               created_at, updated_at
        FROM enterprise_wechat_settings
        WHERE id = 'default'
        LIMIT 1;
        """
    )


def _row_value(row, index: int) -> Any:
    if not row:
        return None
    try:
        return row[index]
    except IndexError:
        return None


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _to_iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _public_config_field(name: str, value: str | None, secret: bool, description: str) -> dict[str, Any]:
    configured = bool(value)
    return {
        "name": name,
        "configured": configured,
        "secret": secret,
        "value_preview": _mask_secret(value) if secret else _preview_plain(value),
        "description": description,
    }


def _settings_public_message(effective: dict[str, Any]) -> str:
    if not effective["configured"]:
        return "企业微信参数未配置完整。普通用户仍可生成文件，但发送状态会停留在等待管理员配置。"
    if not effective["real_send_enabled"]:
        return "企业微信参数已配置，真实发送开关未启用。"
    return "企业微信参数已配置，真实发送开关已启用。"


def _preview_plain(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 10:
        return value
    return f"{value[:4]}...{value[-4:]}"


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 6:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _clear_access_token_cache() -> None:
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRES_AT, _ACCESS_TOKEN_CACHE_KEY
    _ACCESS_TOKEN = None
    _ACCESS_TOKEN_EXPIRES_AT = 0.0
    _ACCESS_TOKEN_CACHE_KEY = ""


def _update_enterprise_wechat_runtime_status(result: dict[str, Any]) -> None:
    execute(
        """
        UPDATE enterprise_wechat_settings
        SET last_health_status = %s,
            last_health_message = %s,
            last_sync_at = now(),
            last_sync_result = %s::jsonb,
            updated_at = now()
        WHERE id = 'default';
        """,
        (
            str(result.get("status") or "unknown"),
            str(result.get("message") or ""),
            dumps_json(sanitize_metadata(result)),
        ),
    )


def _diagnostic_step(label: str, status_value: str, message: str) -> dict[str, Any]:
    return {
        "key": label,
        "label": label,
        "status": status_value,
        "message": message,
    }


def _list_cached_contacts(query: str, *, object_types: list[str], limit: int):
    params: list[Any] = [object_types]
    where = ["active = TRUE", "object_type = ANY(%s)"]
    if query:
        like = f"%{query}%"
        where.append(
            """
            (
                name ILIKE %s
                OR COALESCE(alias, '') ILIKE %s
                OR COALESCE(department, '') ILIKE %s
                OR COALESCE(wechat_userid, '') ILIKE %s
                OR COALESCE(chat_id, '') ILIKE %s
                OR COALESCE(department_id, '') ILIKE %s
            )
            """
        )
        params.extend([like, like, like, like, like, like])
    params.append(limit)
    return fetch_all(
        f"""
        SELECT id, object_type, name, alias, wechat_userid, chat_id, department_id,
               department, phone, avatar_url, metadata, active, created_at, updated_at
        FROM enterprise_wechat_contacts
        WHERE {' AND '.join(where)}
        ORDER BY updated_at DESC, object_type, name
        LIMIT %s;
        """,
        tuple(params),
    )


def _normalize_search_query(value: str) -> str:
    return " ".join(str(value or "").strip().split())[:80]


def _normalize_object_types(values: list[str] | None) -> list[str]:
    normalized = [_normalize_object_type(item) for item in values or [] if item]
    return normalized or ["user", "group", "department"]


def _normalize_object_type(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"group", "chat", "群", "群聊"}:
        return "group"
    if text in {"department", "party", "部门"}:
        return "department"
    return "user"


def _object_type_label(value: str) -> str:
    return {
        "user": "成员",
        "group": "群聊",
        "department": "部门",
    }.get(value, "成员")


def _phone_last4(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""


def _masked_phone(value: Any) -> str:
    last4 = _phone_last4(value)
    return f"****{last4}" if last4 else ""
