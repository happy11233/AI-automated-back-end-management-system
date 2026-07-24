from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one, transaction
from app.json_utils import dumps_json
from app.services.automation_flow_service import FLOW_VERSION, TOOL_PARAMETER_SPECS, default_tool_parameters_for_tools, get_flow_config
from app.services.logging_service import write_audit_log


VERSION_STATUSES = {"draft", "reviewing", "approved", "published", "deprecated", "rejected", "rolled_back"}
PUBLICATION_ENVIRONMENTS = {"dev", "staging", "production"}
PUBLICATION_STATUSES = {"active", "paused", "rolled_back"}
VERIFICATION_EVIDENCE_STATUSES = {"passed", "failed"}
EDITABLE_DRAFT_FIELDS = {
    "change_summary",
    "approval_policy",
    "failure_strategy",
    "publish_notes",
    "prompt_summary",
    "prompt_template_preview",
    "input_schema",
    "output_schema",
    "tool_parameters",
    "allowed_tools",
    "allowed_erp_resources",
    "steps",
}
DEFAULT_VERIFICATION_EVIDENCE_TTL_HOURS = 168
STEP_ORDER_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("validate_position_task", "build_prompt"),
    ("build_prompt", "llm_chat"),
    ("llm_chat", "record_run"),
    ("position_guard", "intent_recognition"),
    ("intent_recognition", "erp_salary_query"),
    ("erp_salary_query", "write_workbook"),
    ("validate_file", "read_excel"),
    ("validate_erp_resources", "query_erp_context"),
    ("read_excel", "build_finance_summary"),
    ("query_erp_context", "llm_finance_suggestion"),
    ("build_finance_summary", "llm_finance_suggestion"),
    ("llm_finance_suggestion", "write_workbook"),
    ("validate_files", "read_workbooks"),
    ("read_workbooks", "detect_fields"),
    ("detect_fields", "match_order_sku"),
    ("match_order_sku", "calculate_profit"),
    ("calculate_profit", "detect_anomalies"),
    ("detect_anomalies", "write_workbook"),
    ("write_workbook", "record_artifact"),
    ("create_message", "classify_intent_and_risk"),
    ("classify_intent_and_risk", "erp_permission_query"),
    ("classify_intent_and_risk", "rag_policy_lookup"),
    ("erp_permission_query", "generate_reply_draft"),
    ("rag_policy_lookup", "generate_reply_draft"),
    ("generate_reply_draft", "route_decision"),
    ("route_decision", "record_timeline"),
    ("resolve_resource", "permission_check"),
    ("permission_check", "provider_query"),
    ("provider_query", "record_run"),
    ("position_guard", "load_context"),
    ("load_context", "intent_detection"),
    ("intent_detection", "tool_or_rag"),
    ("tool_or_rag", "answer_generation"),
    ("answer_generation", "record_run"),
    ("validate_upload", "load_document"),
    ("load_document", "ingest_chunks"),
)
SUPPORTED_SCHEMA_TYPES = {
    "file",
    "file_list",
    "json",
    "json_array",
    "markdown_text",
    "multi_select",
    "number",
    "select",
    "sheet",
    "text",
    "textarea",
    "uuid",
    "xlsx",
}
FORBIDDEN_SECRET_MARKERS = (
    "authorization",
    "bearer ",
    "api_key",
    "api secret",
    "api_secret",
    "access_token",
    "callback_token",
    "client_secret",
    "database_url",
    "password",
    "private_key",
    "refresh_token",
    "secret_key",
    "jwt",
)
FORBIDDEN_VERIFICATION_MARKERS = (
    "monkeypatch.",
    "monkeypatch.setattr",
    "unittest.mock",
    "from mock import",
    "import mock",
    "responses.activate",
)

REGRESSION_BINDINGS_BY_FLOW_KEY = {
    "automation:customer_service:message-loop": [
        {
            "label": "客服消息自动化闭环真实 API/DB/ERP/RAG/LLM 回归",
            "command": ".venv/bin/python scripts/verify_customer_service_automation.py",
            "script": "scripts/verify_customer_service_automation.py",
            "profile": "api",
            "critical": True,
        },
        {
            "label": "客服退款审批权限和真实退款流水回归",
            "command": ".venv/bin/python scripts/verify_customer_service_refund_approvals.py",
            "script": "scripts/verify_customer_service_refund_approvals.py",
            "profile": "api",
            "critical": True,
        }
    ],
    "automation:finance:excel-file-transform": [
        {
            "label": "财务 Excel 上传、ERP 查询和 workbook 检查回归",
            "command": ".venv/bin/python scripts/verify_finance_excel_transform.py",
            "script": "scripts/verify_finance_excel_transform.py",
            "profile": "api",
        }
    ],
    "automation:finance:reconciliation": [
        {
            "label": "财务对账多文件上传、利润表和异常账单回归",
            "command": ".venv/bin/python scripts/verify_finance_reconciliation.py",
            "script": "scripts/verify_finance_reconciliation.py",
            "profile": "api",
        }
    ],
    "automation:finance:salary-export": [
        {
            "label": "工资导出真实 ERP Salary Slip 和 Excel 检查回归",
            "command": ".venv/bin/python scripts/verify_finance_salary_export.py",
            "script": "scripts/verify_finance_salary_export.py",
            "profile": "api",
            "critical": True,
        },
        {
            "label": "聊天入口工资导出和岗位越权守卫回归",
            "command": ".venv/bin/python scripts/verify_chat_react_guardrails.py",
            "script": "scripts/verify_chat_react_guardrails.py",
            "profile": "api",
            "critical": True,
        },
    ],
    "automation:platform:knowledge-upload": [
        {
            "label": "RAG 岗位 scope 真实 PostgreSQL 检索隔离回归",
            "command": ".venv/bin/python scripts/verify_rag_position_scope.py",
            "script": "scripts/verify_rag_position_scope.py",
            "profile": "api",
        },
        {
            "label": "RAG 授权管理 API 与审计回归",
            "command": ".venv/bin/python scripts/verify_rag_authorization_admin_api.py",
            "script": "scripts/verify_rag_authorization_admin_api.py",
            "profile": "api",
        },
    ],
}
REGRESSION_BINDINGS_BY_SUFFIX = {
    ":erp-query": [
        {
            "label": "ERP 查询和岗位资源权限回归",
            "command": ".venv/bin/python scripts/verify_position_permissions.py",
            "script": "scripts/verify_position_permissions.py",
            "profile": "api",
        },
        {
            "label": "ERP 对话真实引用回归",
            "command": ".venv/bin/python scripts/verify_erp_chat.py",
            "script": "scripts/verify_erp_chat.py",
            "profile": "api",
        },
    ],
    ":chat-agent": [
        {
            "label": "聊天守卫、流式输出、工资导出和会话隔离回归",
            "command": ".venv/bin/python scripts/verify_chat_react_guardrails.py",
            "script": "scripts/verify_chat_react_guardrails.py",
            "profile": "api",
        },
        {
            "label": "ERP 对话真实引用回归",
            "command": ".venv/bin/python scripts/verify_erp_chat.py",
            "script": "scripts/verify_erp_chat.py",
            "profile": "api",
        },
    ],
}
REGRESSION_BINDINGS_BY_PREFIX = {
    "automation:operations:": [
        {
            "label": "运营 Listing 草稿真实生成和平台草稿回归",
            "command": ".venv/bin/python scripts/verify_platform_draft_automation.py",
            "script": "scripts/verify_platform_draft_automation.py",
            "profile": "api",
        },
        {
            "label": "AI 工作流运营任务、运行记录和脱敏回归",
            "command": ".venv/bin/python scripts/verify_ai_workflows.py",
            "script": "scripts/verify_ai_workflows.py",
            "profile": "api",
        },
    ],
    "automation:customer_service:": [
        {
            "label": "客服自动化任务、ERP 步骤和脱敏回归",
            "command": ".venv/bin/python scripts/verify_ai_workflows.py",
            "script": "scripts/verify_ai_workflows.py",
            "profile": "api",
        },
        {
            "label": "岗位越权权限回归",
            "command": ".venv/bin/python scripts/verify_position_permissions.py",
            "script": "scripts/verify_position_permissions.py",
            "profile": "api",
        },
    ],
    "automation:finance:": [
        {
            "label": "财务岗位越权和文件流程权限回归",
            "command": ".venv/bin/python scripts/verify_position_permissions.py",
            "script": "scripts/verify_position_permissions.py",
            "profile": "api",
        },
        {
            "label": "AI 工作流财务任务、运行记录和脱敏回归",
            "command": ".venv/bin/python scripts/verify_ai_workflows.py",
            "script": "scripts/verify_ai_workflows.py",
            "profile": "api",
        },
    ],
}


def ensure_automation_flow_version_schema() -> None:
    sql_dir = Path(__file__).resolve().parents[2] / "sql"
    for migration_name in (
        "016_automation_flow_versions.sql",
        "018_automation_flow_preflight_runs.sql",
        "019_automation_flow_verification_evidence.sql",
    ):
        execute((sql_dir / migration_name).read_text(encoding="utf-8"))


def list_flow_versions(*, flow_id: str, current_user: dict) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    flow = ensure_flow_projection(flow_id=flow_id, current_user=current_user)
    rows = fetch_all(
        """
        SELECT
            v.id,
            v.flow_id,
            f.flow_key,
            v.version,
            v.version_number,
            v.status,
            v.change_summary,
            v.trigger_type,
            v.entrypoint,
            v.approval_policy,
            v.failure_strategy,
            v.publish_notes,
            v.created_by,
            creator.username AS created_by_username,
            v.approved_by,
            approver.username AS approved_by_username,
            v.published_by,
            publisher.username AS published_by_username,
            v.created_at,
            v.updated_at,
            v.approved_at,
            v.published_at,
            p.id AS active_publication_id,
            p.environment AS active_publication_environment
        FROM automation_flow_versions v
        JOIN automation_flows f ON f.id = v.flow_id
        LEFT JOIN users creator ON creator.id = v.created_by
        LEFT JOIN users approver ON approver.id = v.approved_by
        LEFT JOIN users publisher ON publisher.id = v.published_by
        LEFT JOIN automation_flow_publications p
          ON p.version_id = v.id
         AND p.status = 'active'
        WHERE v.flow_id = %s
        ORDER BY v.version_number DESC, v.created_at DESC;
        """,
        (flow["id"],),
    )
    items = [_version_summary_from_row(row) for row in rows]
    return {"items": items, "total": len(items)}


def create_flow_version(
    *,
    flow_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    flow = ensure_flow_projection(flow_id=flow_id, current_user=current_user)
    projection = get_flow_config(flow["flow_key"], current_user)
    _assert_no_secret_payload(projection)
    _assert_no_secret_payload(payload)
    change_summary = _normalize_optional_text(payload.get("change_summary"), 1000) or "从当前代码投影创建草稿版本"

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(MAX(version_number), 0) + 1
                FROM automation_flow_versions
                WHERE flow_id = %s;
                """,
                (flow["id"],),
            )
            version_number = int(cur.fetchone()[0])
            version = payload.get("version") or _build_version_label(version_number)
            cur.execute(
                """
                INSERT INTO automation_flow_versions (
                    flow_id,
                    version,
                    version_number,
                    status,
                    change_summary,
                    trigger_type,
                    entrypoint,
                    input_schema,
                    output_schema,
                    prompt_template,
                    prompt_summary,
                    model_config,
                    allowed_tools,
                    allowed_erp_resources,
                    allowed_rag_scopes,
                    permission_rules,
                    approval_policy,
                    failure_strategy,
                    steps,
                    publish_notes,
                    created_by
                )
                VALUES (
                    %s, %s, %s, 'draft', %s, %s, %s, %s::jsonb, %s::jsonb,
                    %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                    %s::jsonb, %s, %s, %s::jsonb, %s, %s
                )
                RETURNING id;
                """,
                (
                    flow["id"],
                    version,
                    version_number,
                    change_summary,
                    projection["trigger_type"],
                    projection["entrypoint"],
                    dumps_json(projection["input_schema"]),
                    dumps_json(projection["output_schema"]),
                    projection.get("prompt_template_preview") or projection.get("prompt_summary"),
                    projection.get("prompt_summary"),
                    dumps_json(projection.get("model_config") or {}),
                    dumps_json(projection.get("allowed_tools") or []),
                    dumps_json(projection.get("allowed_erp_resources") or []),
                    dumps_json({}),
                    dumps_json(projection.get("permission_rules") or []),
                    str(payload.get("approval_policy") or projection.get("approval_policy") or "不需要审批。"),
                    str(payload.get("failure_strategy") or projection.get("failure_strategy") or "失败时写入运行记录。"),
                    dumps_json(projection.get("steps") or []),
                    _normalize_optional_text(payload.get("publish_notes"), 1000),
                    current_user.get("id"),
                ),
            )
            version_id = str(cur.fetchone()[0])

    item = get_flow_version(version_id=version_id, current_user=current_user)
    _audit(
        current_user,
        "admin.automation_flow_version.create",
        "automation_flow_version",
        item["id"],
        {"flow_id": flow["id"], "flow_key": flow["flow_key"], "version": item["version"], "status": item["status"]},
    )
    return item


def get_flow_version(*, version_id: str, current_user: dict) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    normalized_version_id = _normalize_uuid(version_id, "版本 ID")
    row = fetch_one(
        """
        SELECT
            v.id,
            v.flow_id,
            f.flow_key,
            f.app_id,
            f.name,
            f.description,
            f.category,
            f.position,
            f.status AS flow_status,
            f.source,
            v.version,
            v.version_number,
            v.status,
            v.change_summary,
            v.trigger_type,
            v.entrypoint,
            v.input_schema,
            v.output_schema,
            v.prompt_template,
            v.prompt_summary,
            v.model_config,
            v.allowed_tools,
            v.allowed_erp_resources,
            v.allowed_rag_scopes,
            v.permission_rules,
            v.approval_policy,
            v.failure_strategy,
            v.steps,
            v.publish_notes,
            v.created_by,
            creator.username AS created_by_username,
            v.approved_by,
            approver.username AS approved_by_username,
            v.published_by,
            publisher.username AS published_by_username,
            v.created_at,
            v.updated_at,
            v.approved_at,
            v.published_at,
            p.id AS active_publication_id,
            p.environment AS active_publication_environment
        FROM automation_flow_versions v
        JOIN automation_flows f ON f.id = v.flow_id
        LEFT JOIN users creator ON creator.id = v.created_by
        LEFT JOIN users approver ON approver.id = v.approved_by
        LEFT JOIN users publisher ON publisher.id = v.published_by
        LEFT JOIN automation_flow_publications p
          ON p.version_id = v.id
         AND p.status = 'active'
        WHERE v.id = %s;
        """,
        (normalized_version_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="自动化流程版本不存在")
    return _version_detail_from_row(row)


def update_flow_version(
    *,
    version_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    if existing["status"] != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有草稿版本允许编辑")
    unknown_fields = sorted(set(payload) - EDITABLE_DRAFT_FIELDS)
    if unknown_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不允许编辑字段：{unknown_fields}")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的版本字段")

    next_allowed_tools = _normalize_allowed_tools_payload(
        payload.get("allowed_tools", existing.get("allowed_tools")),
        existing=existing,
        current_user=current_user,
    )
    next_allowed_erp_resources = _normalize_allowed_erp_resources_payload(
        payload.get("allowed_erp_resources", existing.get("allowed_erp_resources")),
        existing=existing,
        current_user=current_user,
    )
    next_steps = _normalize_steps_payload(
        payload.get("steps", existing.get("steps")),
        existing=existing,
        current_user=current_user,
    )
    raw_tool_parameters = payload.get("tool_parameters", (existing.get("model_config") or {}).get("tool_parameters"))
    if "allowed_tools" in payload:
        raw_tool_parameters = _prune_stale_tool_parameters(
            raw_tool_parameters,
            allowed_tools=next_allowed_tools,
            existing_model_config=existing.get("model_config"),
        )
    next_model_config = _normalize_model_config_payload(
        existing_model_config=existing.get("model_config"),
        raw_tool_parameters=raw_tool_parameters,
        allowed_tools=next_allowed_tools,
    )
    next_values = {
        "change_summary": _normalize_optional_text(payload.get("change_summary", existing.get("change_summary")), 1000),
        "approval_policy": _normalize_required_text(payload.get("approval_policy", existing["approval_policy"]), 2000, "审批策略"),
        "failure_strategy": _normalize_required_text(payload.get("failure_strategy", existing["failure_strategy"]), 2000, "失败策略"),
        "publish_notes": _normalize_optional_text(payload.get("publish_notes", existing.get("publish_notes")), 1000),
        "prompt_summary": _normalize_required_text(payload.get("prompt_summary", existing.get("prompt_summary")), 1000, "Prompt 摘要"),
        "prompt_template": _normalize_required_text(
            payload.get("prompt_template_preview", existing.get("prompt_template_preview")),
            8000,
            "Prompt 模板",
        ),
        "input_schema": _normalize_schema_payload(
            payload.get("input_schema", existing.get("input_schema")),
            label="输入 Schema",
            field_root="input_schema",
        ),
        "output_schema": _normalize_schema_payload(
            payload.get("output_schema", existing.get("output_schema")),
            label="输出 Schema",
            field_root="output_schema",
        ),
        "model_config": next_model_config,
        "allowed_tools": next_allowed_tools,
        "allowed_erp_resources": next_allowed_erp_resources,
        "steps": next_steps,
    }
    _assert_no_secret_payload(next_values)
    prompt_errors = _validate_prompt_contract(
        prompt_summary=next_values["prompt_summary"],
        prompt_template=next_values["prompt_template"],
    )
    if prompt_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=prompt_errors[0]["message"])
    row = fetch_one(
        """
        UPDATE automation_flow_versions
        SET
            change_summary = %s,
            approval_policy = %s,
            failure_strategy = %s,
            publish_notes = %s,
            prompt_summary = %s,
            prompt_template = %s,
            model_config = %s::jsonb,
            input_schema = %s::jsonb,
            output_schema = %s::jsonb,
            allowed_tools = %s::jsonb,
            allowed_erp_resources = %s::jsonb,
            steps = %s::jsonb,
            updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (
            next_values["change_summary"],
            next_values["approval_policy"],
            next_values["failure_strategy"],
            next_values["publish_notes"],
            next_values["prompt_summary"],
            next_values["prompt_template"],
            dumps_json(next_values["model_config"]),
            dumps_json(next_values["input_schema"]),
            dumps_json(next_values["output_schema"]),
            dumps_json(next_values["allowed_tools"]),
            dumps_json(next_values["allowed_erp_resources"]),
            dumps_json(next_values["steps"]),
            existing["id"],
        ),
    )
    item = get_flow_version(version_id=str(row[0]), current_user=current_user)
    _audit(
        current_user,
        "admin.automation_flow_version.update",
        "automation_flow_version",
        item["id"],
        {"flow_id": item["flow_id"], "flow_key": item["flow_key"], "updated_fields": sorted(payload)},
    )
    return item


def submit_flow_version_review(*, version_id: str, current_user: dict) -> dict[str, Any]:
    return _transition_version(
        version_id=version_id,
        current_user=current_user,
        allowed_statuses={"draft", "rejected"},
        next_status="reviewing",
        action="admin.automation_flow_version.submit_review",
    )


def approve_flow_version(*, version_id: str, current_user: dict) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    if existing["status"] != "reviewing":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有 reviewing 版本可以批准")
    row = fetch_one(
        """
        UPDATE automation_flow_versions
        SET
            status = 'approved',
            approved_by = %s,
            approved_at = now(),
            updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (current_user.get("id"), existing["id"]),
    )
    item = get_flow_version(version_id=str(row[0]), current_user=current_user)
    _audit(
        current_user,
        "admin.automation_flow_version.approve",
        "automation_flow_version",
        item["id"],
        {"flow_id": item["flow_id"], "flow_key": item["flow_key"], "version": item["version"]},
    )
    return item


def record_flow_version_verification_evidence(
    *,
    version_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    normalized = _normalize_verification_evidence_payload(existing=existing, payload=payload)
    snapshot_hash = _flow_contract_snapshot_hash(existing)
    verified_at = datetime.now(timezone.utc)
    expires_at = verified_at + timedelta(hours=normalized["ttl_hours"])
    row = fetch_one(
        """
        INSERT INTO automation_flow_version_verification_evidence (
            flow_id,
            version_id,
            flow_key,
            version,
            version_status,
            snapshot_hash,
            script,
            command,
            profile,
            status,
            report_id,
            report_url,
            summary,
            metadata,
            verified_by,
            verified_at,
            expires_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s
        )
        RETURNING
            id,
            flow_id,
            version_id,
            flow_key,
            version,
            version_status,
            snapshot_hash,
            script,
            command,
            profile,
            status,
            report_id,
            report_url,
            summary,
            metadata,
            verified_by,
            NULL::text AS verified_by_username,
            verified_at,
            expires_at,
            created_at;
        """,
        (
            existing["flow_id"],
            existing["id"],
            existing["flow_key"],
            existing["version"],
            existing["status"],
            snapshot_hash,
            normalized["script"],
            normalized["command"],
            normalized["profile"],
            normalized["status"],
            normalized["report_id"],
            normalized["report_url"],
            normalized["summary"],
            dumps_json(normalized["metadata"]),
            current_user.get("id"),
            verified_at,
            expires_at,
        ),
    )
    item = _verification_evidence_from_row(row)
    _audit(
        current_user,
        "admin.automation_flow_version.verification_evidence.record",
        "automation_flow_version_verification_evidence",
        item["id"],
        {
            "flow_id": item["flow_id"],
            "version_id": item["version_id"],
            "flow_key": item["flow_key"],
            "version": item["version"],
            "script": item["script"],
            "profile": item["profile"],
            "status": item["status"],
            "report_id": item["report_id"],
        },
    )
    return item


def list_flow_version_verification_evidence(
    *,
    version_id: str,
    current_user: dict,
    limit: int = 50,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    snapshot_hash = _flow_contract_snapshot_hash(existing)
    normalized_limit = max(1, min(int(limit or 50), 100))
    rows = fetch_all(
        """
        SELECT
            e.id,
            e.flow_id,
            e.version_id,
            e.flow_key,
            e.version,
            e.version_status,
            e.snapshot_hash,
            e.script,
            e.command,
            e.profile,
            e.status,
            e.report_id,
            e.report_url,
            e.summary,
            e.metadata,
            e.verified_by,
            u.username AS verified_by_username,
            e.verified_at,
            e.expires_at,
            e.created_at,
            e.version_id = %s AS is_current_version,
            e.snapshot_hash = %s AS matches_current_snapshot,
            e.status = 'passed'
                AND e.snapshot_hash = %s
                AND e.expires_at > now() AS is_publish_eligible
        FROM automation_flow_version_verification_evidence e
        LEFT JOIN users u ON u.id = e.verified_by
        WHERE e.flow_id = %s
          AND (
              e.version_id = %s
              OR e.snapshot_hash = %s
          )
        ORDER BY
            is_publish_eligible DESC,
            matches_current_snapshot DESC,
            e.verified_at DESC
        LIMIT %s;
        """,
        (
            existing["id"],
            snapshot_hash,
            snapshot_hash,
            existing["flow_id"],
            existing["id"],
            snapshot_hash,
            normalized_limit,
        ),
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        item = _verification_evidence_from_row(row[:20])
        is_current_version = bool(row[20])
        item.update(
            {
                "is_current_version": is_current_version,
                "matches_current_snapshot": bool(row[21]),
                "is_publish_eligible": bool(row[22]),
                "evidence_scope": "current_version" if is_current_version else "same_snapshot",
            }
        )
        items.append(item)

    return {
        "items": items,
        "total": len(items),
        "version_id": existing["id"],
        "flow_id": existing["flow_id"],
        "flow_key": existing["flow_key"],
        "version": existing["version"],
        "snapshot_hash": snapshot_hash,
    }


def run_flow_version_preflight(
    *,
    version_id: str,
    current_user: dict,
    trigger_source: str = "manual",
    audit: bool = True,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    normalized_trigger_source = _normalize_preflight_trigger_source(trigger_source)
    require_regression_evidence = normalized_trigger_source == "publish"
    checks = [
        _preflight_check(
            key="schema_contract",
            label="Schema 结构校验",
            errors=[
                *_validate_schema_items(existing.get("input_schema"), "输入 Schema", "input_schema"),
                *_validate_schema_items(existing.get("output_schema"), "输出 Schema", "output_schema"),
            ],
            passed_message="输入和输出 Schema 字段结构、类型和限制通过。",
        ),
        _preflight_check(
            key="secret_scan",
            label="密钥与敏感字段扫描",
            errors=_scan_flow_version_secrets(existing),
            passed_message="版本快照未发现密钥、token、Authorization 或数据库连接信息。",
        ),
        _preflight_check(
            key="prompt_contract",
            label="Prompt 合同校验",
            errors=_validate_prompt_contract(
                prompt_summary=existing.get("prompt_summary"),
                prompt_template=existing.get("prompt_template_preview"),
            ),
            passed_message="Prompt 摘要和模板非空、长度合规，且未发现敏感配置。",
        ),
        _preflight_check(
            key="execution_contract",
            label="执行合同快检",
            errors=_validate_execution_contract(existing, current_user),
            passed_message="入口、工具、权限规则和执行步骤满足发布合同。",
        ),
        _preflight_check(
            key="code_projection_regression",
            label="代码投影回归快检",
            errors=_validate_code_projection_contract(existing, current_user),
            passed_message="当前代码投影仍存在，且版本快照未越过代码投影允许的工具和资源。",
        ),
        _preflight_check(
            key="business_regression_binding",
            label="真实业务回归绑定",
            errors=_validate_business_regression_binding(existing, require_evidence=require_regression_evidence),
            passed_message=(
                "该流程已绑定真实业务回归或评测脚本，"
                + ("且已有最近一次通过证据。" if require_regression_evidence else "发布时将校验最近一次通过证据。")
            ),
            artifacts=_business_regression_artifacts(existing),
        ),
    ]
    failed_checks = [item for item in checks if item["status"] == "failed"]
    result = {
        "preflight_run_id": None,
        "ok": not failed_checks,
        "version_id": existing["id"],
        "flow_id": existing["flow_id"],
        "flow_key": existing["flow_key"],
        "version": existing["version"],
        "status": existing["status"],
        "trigger_source": normalized_trigger_source,
        "blocking_failures": len(failed_checks),
        "checks": checks,
        "created_by": str(current_user.get("id")) if current_user.get("id") else None,
        "created_by_username": current_user.get("username"),
        "created_at": None,
    }
    preflight_run = _persist_preflight_run(result=result, current_user=current_user)
    result.update(preflight_run)

    if audit:
        _audit(
            current_user,
            "admin.automation_flow_version.preflight",
            "automation_flow_version",
            existing["id"],
            {
                "flow_id": existing["flow_id"],
                "flow_key": existing["flow_key"],
                "version": existing["version"],
                "preflight_run_id": result["preflight_run_id"],
                "ok": result["ok"],
                "trigger_source": normalized_trigger_source,
                "failed_checks": [item["key"] for item in failed_checks],
            },
        )

    return result


def publish_flow_version(
    *,
    version_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    if existing["status"] not in {"approved", "published"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有 approved 版本可以发布")
    environment = _normalize_environment(payload.get("environment") or "production")
    reason = _normalize_optional_text(payload.get("reason"), 1000) or "发布自动化流程版本"
    _assert_no_secret_payload({"reason": reason})
    preflight = run_flow_version_preflight(
        version_id=existing["id"],
        current_user=current_user,
        trigger_source="publish",
        audit=False,
    )
    if not preflight["ok"]:
        _audit(
            current_user,
            "admin.automation_flow_version.publish_blocked",
            "automation_flow_version",
            existing["id"],
            {
                "flow_id": existing["flow_id"],
                "flow_key": existing["flow_key"],
                "version": existing["version"],
                "environment": environment,
                "failed_checks": [
                    item["key"]
                    for item in preflight["checks"]
                    if item["status"] == "failed"
                ],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "发布前预检未通过",
                "preflight": preflight,
            },
        )

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE automation_flow_publications
                SET status = 'rolled_back'
                WHERE flow_id = %s
                  AND environment = %s
                  AND status = 'active';
                """,
                (existing["flow_id"], environment),
            )
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET status = 'deprecated', updated_at = now()
                WHERE flow_id = %s
                  AND status = 'published'
                  AND id <> %s;
                """,
                (existing["flow_id"], existing["id"]),
            )
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET
                    status = 'published',
                    published_by = %s,
                    published_at = now(),
                    publish_notes = COALESCE(%s, publish_notes),
                    updated_at = now()
                WHERE id = %s;
                """,
                (current_user.get("id"), reason, existing["id"]),
            )
            cur.execute(
                """
                INSERT INTO automation_flow_publications (
                    flow_id,
                    version_id,
                    environment,
                    status,
                    rollout_percent,
                    published_by,
                    reason
                )
                VALUES (%s, %s, %s, 'active', 100, %s, %s)
                RETURNING id;
                """,
                (existing["flow_id"], existing["id"], environment, current_user.get("id"), reason),
            )
            publication_id = str(cur.fetchone()[0])

    item = get_publication(publication_id=publication_id)
    _audit(
        current_user,
        "admin.automation_flow_version.publish",
        "automation_flow_publication",
        item["id"],
        {
            "flow_id": item["flow_id"],
            "version_id": item["version_id"],
            "environment": item["environment"],
            "reason": item["reason"],
        },
    )
    return item


def rollback_publication(
    *,
    publication_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    active = get_publication(publication_id=publication_id)
    if active["status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有 active publication 可以回滚")
    reason = _normalize_optional_text(payload.get("reason"), 1000) or "回滚自动化流程版本"

    previous = fetch_one(
        """
        SELECT id
        FROM automation_flow_versions
        WHERE flow_id = %s
          AND id <> %s
          AND status IN ('published', 'deprecated', 'rolled_back')
        ORDER BY version_number DESC
        LIMIT 1;
        """,
        (active["flow_id"], active["version_id"]),
    )
    if previous is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可回滚的上一版本")

    previous_version_id = str(previous[0])
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE automation_flow_publications
                SET status = 'rolled_back'
                WHERE id = %s;
                """,
                (active["id"],),
            )
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET status = 'rolled_back', updated_at = now()
                WHERE id = %s;
                """,
                (active["version_id"],),
            )
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET
                    status = 'published',
                    published_by = %s,
                    published_at = now(),
                    updated_at = now()
                WHERE id = %s;
                """,
                (current_user.get("id"), previous_version_id),
            )
            cur.execute(
                """
                INSERT INTO automation_flow_publications (
                    flow_id,
                    version_id,
                    environment,
                    status,
                    rollout_percent,
                    published_by,
                    rollback_from_version_id,
                    reason
                )
                VALUES (%s, %s, %s, 'active', 100, %s, %s, %s)
                RETURNING id;
                """,
                (
                    active["flow_id"],
                    previous_version_id,
                    active["environment"],
                    current_user.get("id"),
                    active["version_id"],
                    reason,
                ),
            )
            next_publication_id = str(cur.fetchone()[0])

    item = get_publication(publication_id=next_publication_id)
    _audit(
        current_user,
        "admin.automation_flow_publication.rollback",
        "automation_flow_publication",
        item["id"],
        {
            "flow_id": item["flow_id"],
            "version_id": item["version_id"],
            "rollback_from_version_id": item["rollback_from_version_id"],
            "environment": item["environment"],
            "reason": item["reason"],
        },
    )
    return item


def get_publication(*, publication_id: str) -> dict[str, Any]:
    normalized_publication_id = _normalize_uuid(publication_id, "发布 ID")
    row = fetch_one(
        """
        SELECT
            p.id,
            p.flow_id,
            f.flow_key,
            p.version_id,
            v.version,
            v.version_number,
            p.environment,
            p.status,
            p.rollout_percent,
            p.published_by,
            u.username AS published_by_username,
            p.published_at,
            p.rollback_from_version_id,
            p.reason,
            p.created_at
        FROM automation_flow_publications p
        JOIN automation_flows f ON f.id = p.flow_id
        JOIN automation_flow_versions v ON v.id = p.version_id
        LEFT JOIN users u ON u.id = p.published_by
        WHERE p.id = %s;
        """,
        (normalized_publication_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="自动化流程发布记录不存在")
    return _publication_from_row(row)


def resolve_flow_execution_reference(
    *,
    flow_key: str | None,
    current_user: dict,
    execution_source: str,
    environment: str = "production",
) -> dict[str, Any] | None:
    if not flow_key:
        return None

    ensure_automation_flow_version_schema()
    flow = ensure_flow_projection(flow_id=flow_key, current_user=current_user)
    publication_row = fetch_one(
        """
        SELECT
            p.id,
            p.version_id,
            v.version
        FROM automation_flow_publications p
        JOIN automation_flow_versions v ON v.id = p.version_id
        WHERE p.flow_id = %s
          AND p.environment = %s
          AND p.status = 'active'
        ORDER BY p.published_at DESC, p.created_at DESC
        LIMIT 1;
        """,
        (flow["id"], _normalize_environment(environment)),
    )

    version_id = None
    version = None
    publication_id = None
    if publication_row:
        publication_id = str(publication_row[0])
        version_id = str(publication_row[1])
        version = publication_row[2]
    else:
        projection = get_flow_config(flow["flow_key"], current_user)
        version = str(projection.get("version") or FLOW_VERSION)

    return {
        "flow_id": flow["id"],
        "flow_key": flow["flow_key"],
        "flow_version_id": version_id,
        "flow_version": version,
        "publication_id": publication_id,
        "execution_source": _normalize_optional_text(execution_source, 200) or "unknown",
    }


def ensure_flow_projection(*, flow_id: str, current_user: dict) -> dict[str, Any]:
    projection = get_flow_config(flow_id, current_user)
    flow_key = str(projection["id"])
    ensure_automation_flow_version_schema()
    row = fetch_one(
        """
        INSERT INTO automation_flows (
            flow_key,
            app_id,
            name,
            description,
            category,
            position,
            status,
            source,
            created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'enabled', %s, %s)
        ON CONFLICT (flow_key) DO UPDATE
        SET
            app_id = EXCLUDED.app_id,
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            position = EXCLUDED.position,
            source = EXCLUDED.source,
            updated_at = now()
        RETURNING
            id,
            flow_key,
            app_id,
            name,
            description,
            category,
            position,
            owner_user_id,
            status,
            source,
            created_by,
            created_at,
            updated_at;
        """,
        (
            flow_key,
            projection["app_id"],
            projection["name"],
            projection["description"],
            projection["category"],
            projection["position"],
            projection.get("source") or "code_defined",
            current_user.get("id"),
        ),
    )
    return _flow_from_row(row)


def _transition_version(
    *,
    version_id: str,
    current_user: dict,
    allowed_statuses: set[str],
    next_status: str,
    action: str,
) -> dict[str, Any]:
    ensure_automation_flow_version_schema()
    existing = get_flow_version(version_id=version_id, current_user=current_user)
    if existing["status"] not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态 {existing['status']} 不能流转为 {next_status}",
        )
    row = fetch_one(
        """
        UPDATE automation_flow_versions
        SET status = %s, updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (next_status, existing["id"]),
    )
    item = get_flow_version(version_id=str(row[0]), current_user=current_user)
    _audit(
        current_user,
        action,
        "automation_flow_version",
        item["id"],
        {
            "flow_id": item["flow_id"],
            "flow_key": item["flow_key"],
            "version": item["version"],
            "from_status": existing["status"],
            "to_status": item["status"],
        },
    )
    return item


def _build_version_label(version_number: int) -> str:
    now = datetime.now(timezone.utc)
    return f"{now:%Y.%m.%d}.{version_number}"


def _normalize_uuid(value: Any, label: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 格式不正确") from error


def _normalize_environment(value: Any) -> str:
    environment = str(value or "production").strip()
    if environment not in PUBLICATION_ENVIRONMENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="发布环境不合法")
    return environment


def _normalize_preflight_trigger_source(value: Any) -> str:
    trigger_source = str(value or "manual").strip()
    if trigger_source not in {"manual", "publish"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="预检触发来源不合法")
    return trigger_source


def _normalize_optional_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_length]


def _normalize_required_text(value: Any, max_length: int, label: str) -> str:
    text = _normalize_optional_text(value, max_length)
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label}不能为空")
    return text


def _normalize_verification_evidence_payload(*, existing: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    script = _normalize_optional_text(payload.get("script"), 500)
    if not script:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证脚本不能为空")
    binding = _regression_binding_for_script(str(existing["flow_key"]), script)
    if binding is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证脚本未绑定到该自动化流程")
    if not _is_allowed_verification_script(script):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证脚本必须位于 scripts/verify_*")

    script_path = _repo_root() / script
    if not script_path.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证脚本不存在")
    script_text = script_path.read_text(encoding="utf-8", errors="ignore").lower()
    if "no mock/stub/fake" not in script_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证脚本缺少真实验证声明")
    for marker in FORBIDDEN_VERIFICATION_MARKERS:
        if marker in script_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证脚本包含禁止的 mock/monkeypatch 标记")

    profile = str(payload.get("profile") or binding.get("profile") or "api").strip()
    if profile not in {"api", "release"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证 profile 必须是 api 或 release")
    status_value = str(payload.get("status") or "passed").strip()
    if status_value not in VERIFICATION_EVIDENCE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证状态不合法")
    report_id = _normalize_optional_text(payload.get("report_id"), 200)
    if not report_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证报告 ID 不能为空")

    try:
        ttl_hours = int(payload.get("ttl_hours") or DEFAULT_VERIFICATION_EVIDENCE_TTL_HOURS)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证证据有效小时数必须是数字") from error
    if ttl_hours < 1 or ttl_hours > 720:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证证据有效期必须在 1 到 720 小时之间")

    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证证据 metadata 必须是对象")

    normalized = {
        "script": script,
        "command": _normalize_optional_text(payload.get("command"), 1000) or str(binding.get("command") or f".venv/bin/python {script}"),
        "profile": profile,
        "status": status_value,
        "report_id": report_id,
        "report_url": _normalize_optional_text(payload.get("report_url"), 1000),
        "summary": _normalize_optional_text(payload.get("summary"), 1000),
        "ttl_hours": ttl_hours,
        "metadata": metadata,
    }
    _assert_no_secret_payload(normalized)
    return normalized


def _assert_no_secret_payload(value: Any) -> None:
    text = dumps_json(value).lower()
    if any(marker in text for marker in FORBIDDEN_SECRET_MARKERS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="流程版本治理字段不能包含密钥、token 或数据库连接信息")


def _preflight_check(
    *,
    key: str,
    label: str,
    errors: list[Any],
    passed_message: str,
    artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    issues = [_normalize_preflight_issue(error) for error in errors]
    return {
        "key": key,
        "label": label,
        "status": "failed" if issues else "passed",
        "message": issues[0]["message"] if issues else passed_message,
        "details": [issue["message"] for issue in issues[:8]],
        "repair_hints": issues[:8],
        "artifacts": (artifacts or [])[:8],
    }


def _preflight_issue(
    *,
    code: str,
    field_path: str,
    message: str,
    suggestion: str,
    severity: str = "blocking",
) -> dict[str, str]:
    return {
        "code": code,
        "field_path": field_path,
        "severity": severity,
        "message": message,
        "suggestion": suggestion,
    }


def _normalize_preflight_issue(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        message = str(value.get("message") or "预检失败")
        field_path = str(value.get("field_path") or "version")
        return {
            "code": str(value.get("code") or "preflight.failed"),
            "field_path": field_path,
            "severity": str(value.get("severity") or "blocking"),
            "message": message,
            "suggestion": str(value.get("suggestion") or "请根据失败信息修正该字段后重新预检。"),
        }
    message = str(value)
    return _preflight_issue(
        code="preflight.failed",
        field_path="version",
        message=message,
        suggestion="请根据失败信息修正该字段后重新预检。",
    )


def _persist_preflight_run(*, result: dict[str, Any], current_user: dict) -> dict[str, Any]:
    failed_check_keys = [
        item["key"]
        for item in result["checks"]
        if item["status"] == "failed"
    ]
    row = fetch_one(
        """
        INSERT INTO automation_flow_version_preflight_runs (
            flow_id,
            version_id,
            flow_key,
            version,
            version_status,
            trigger_source,
            ok,
            blocking_failures,
            checks,
            failed_check_keys,
            created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
        RETURNING id, created_at;
        """,
        (
            result["flow_id"],
            result["version_id"],
            result["flow_key"],
            result["version"],
            result["status"],
            result["trigger_source"],
            result["ok"],
            result["blocking_failures"],
            dumps_json(result["checks"]),
            dumps_json(failed_check_keys),
            current_user.get("id"),
        ),
    )
    return {
        "preflight_run_id": str(row[0]),
        "created_at": row[1].isoformat() if row[1] else None,
    }


def _validate_schema_items(items: Any, label: str, field_root: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if not isinstance(items, list) or not items:
        return [
            _preflight_issue(
                code="schema.array_required",
                field_path=field_root,
                message=f"{label} 必须是非空数组",
                suggestion="把该 Schema 保存为至少包含 1 个字段定义的数组。",
            )
        ]

    seen_names: set[str] = set()
    for index, item in enumerate(items, start=1):
        path = f"{label}[{index}]"
        field_path = f"{field_root}[{index}]"
        if not isinstance(item, dict):
            errors.append(
                _preflight_issue(
                    code="schema.item_object_required",
                    field_path=field_path,
                    message=f"{path} 必须是对象",
                    suggestion="把该项改成对象，并包含 name、label、type 等字段定义。",
                )
            )
            continue

        name = str(item.get("name") or "").strip()
        field_type = str(item.get("type") or "").strip()
        field_label = str(item.get("label") or "").strip()

        if not name:
            errors.append(
                _preflight_issue(
                    code="schema.name_required",
                    field_path=f"{field_path}.name",
                    message=f"{path}.name 不能为空",
                    suggestion="填写稳定的字段名，只使用字母、数字和下划线，且不能以数字开头。",
                )
            )
        elif not name.replace("_", "").isalnum() or name[0].isdigit():
            errors.append(
                _preflight_issue(
                    code="schema.name_invalid",
                    field_path=f"{field_path}.name",
                    message=f"{path}.name 只能使用字母、数字和下划线，且不能以数字开头",
                    suggestion="改成类似 customer_id、order_no、monthly_sales 这样的稳定字段名。",
                )
            )
        elif name in seen_names:
            errors.append(
                _preflight_issue(
                    code="schema.name_duplicate",
                    field_path=f"{field_path}.name",
                    message=f"{path}.name 重复：{name}",
                    suggestion="给重复字段改一个唯一名称，避免运行期覆盖输入或输出。",
                )
            )
        else:
            seen_names.add(name)

        if not field_label:
            errors.append(
                _preflight_issue(
                    code="schema.label_required",
                    field_path=f"{field_path}.label",
                    message=f"{path}.label 不能为空",
                    suggestion="补充给业务人员看的中文字段名称。",
                )
            )

        if not field_type:
            errors.append(
                _preflight_issue(
                    code="schema.type_required",
                    field_path=f"{field_path}.type",
                    message=f"{path}.type 不能为空",
                    suggestion="从受支持类型中选择一个，例如 text、textarea、select、xlsx、json。",
                )
            )
        elif field_type not in SUPPORTED_SCHEMA_TYPES:
            errors.append(
                _preflight_issue(
                    code="schema.type_unsupported",
                    field_path=f"{field_path}.type",
                    message=f"{path}.type 不支持：{field_type}",
                    suggestion=f"改成受支持的类型：{', '.join(sorted(SUPPORTED_SCHEMA_TYPES))}。",
                )
            )

        errors.extend(_validate_positive_number(item, path, field_path, "max_length"))
        errors.extend(_validate_positive_number(item, path, field_path, "max_bytes"))
        errors.extend(_validate_positive_number(item, path, field_path, "max_bytes_each"))
        errors.extend(_validate_positive_number(item, path, field_path, "max_bytes_total"))
        errors.extend(_validate_positive_number(item, path, field_path, "max_files"))
        errors.extend(_validate_positive_number(item, path, field_path, "max_items"))

        if "min" in item and "max" in item:
            try:
                if float(item["min"]) > float(item["max"]):
                    errors.append(
                        _preflight_issue(
                            code="schema.min_gt_max",
                            field_path=f"{field_path}.min",
                            message=f"{path}.min 不能大于 max",
                            suggestion="调小 min 或调大 max，保证最小值不超过最大值。",
                        )
                    )
            except (TypeError, ValueError):
                errors.append(
                    _preflight_issue(
                        code="schema.min_max_number_required",
                        field_path=f"{field_path}.min",
                        message=f"{path}.min/max 必须是数字",
                        suggestion="把 min 和 max 都改成数字，或删除不需要的限制。",
                    )
                )

        if "accept" in item and not isinstance(item["accept"], list):
            errors.append(
                _preflight_issue(
                    code="schema.accept_array_required",
                    field_path=f"{field_path}.accept",
                    message=f"{path}.accept 必须是数组",
                    suggestion="把 accept 改成文件类型数组，例如 [\".xlsx\", \".csv\"]。",
                )
            )
        if "options" in item and not isinstance(item["options"], list):
            errors.append(
                _preflight_issue(
                    code="schema.options_array_required",
                    field_path=f"{field_path}.options",
                    message=f"{path}.options 必须是数组",
                    suggestion="把 options 改成可选项数组，供 select 或 multi_select 使用。",
                )
            )

    return errors


def _validate_positive_number(item: dict[str, Any], path: str, field_path: str, key: str) -> list[dict[str, str]]:
    if key not in item:
        return []
    try:
        if float(item[key]) <= 0:
            return [
                _preflight_issue(
                    code="schema.positive_number_required",
                    field_path=f"{field_path}.{key}",
                    message=f"{path}.{key} 必须大于 0",
                    suggestion="把该限制改成大于 0 的数字，或删除不需要的限制。",
                )
            ]
    except (TypeError, ValueError):
        return [
            _preflight_issue(
                code="schema.number_required",
                field_path=f"{field_path}.{key}",
                message=f"{path}.{key} 必须是数字",
                suggestion="把该限制改成数字，或删除不需要的限制。",
            )
        ]
    return []


def _validate_prompt_contract(*, prompt_summary: Any, prompt_template: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    summary = str(prompt_summary or "").strip()
    template = str(prompt_template or "").strip()

    if not summary:
        errors.append(
            _preflight_issue(
                code="prompt.summary_required",
                field_path="prompt_summary",
                message="Prompt 摘要不能为空",
                suggestion="补充面向管理员的 Prompt 摘要，说明该流程让 AI 做什么、业务边界是什么。",
            )
        )
    elif len(summary) > 1000:
        errors.append(
            _preflight_issue(
                code="prompt.summary_too_long",
                field_path="prompt_summary",
                message="Prompt 摘要不能超过 1000 个字符",
                suggestion="把摘要压缩为业务目标、输入输出和权限边界，不要粘贴完整模板。",
            )
        )

    if not template:
        errors.append(
            _preflight_issue(
                code="prompt.template_required",
                field_path="prompt_template_preview",
                message="Prompt 模板不能为空",
                suggestion="补充实际执行会使用的 Prompt 模板，或保留从代码投影生成的模板内容。",
            )
        )
    elif len(template) > 8000:
        errors.append(
            _preflight_issue(
                code="prompt.template_too_long",
                field_path="prompt_template_preview",
                message="Prompt 模板不能超过 8000 个字符",
                suggestion="拆分过长说明，保留该流程真正需要的任务目标、输入约束、输出格式和安全边界。",
            )
        )

    return errors


def _normalize_schema_payload(value: Any, *, label: str, field_root: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 必须是数组")

    normalized: list[dict[str, Any]] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 数组项必须是对象")
        normalized.append(json.loads(dumps_json(raw_item)))

    errors = _validate_schema_items(normalized, label, field_root)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors[0]["message"])

    return normalized


def _normalize_model_config_payload(
    *,
    existing_model_config: Any,
    raw_tool_parameters: Any,
    allowed_tools: list[str],
) -> dict[str, Any]:
    model_config = json.loads(dumps_json(existing_model_config if isinstance(existing_model_config, dict) else {}))
    normalized_tool_parameters, errors = _normalize_tool_parameters_value(raw_tool_parameters, allowed_tools)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=errors[0]["message"])
    model_config["tool_parameters"] = normalized_tool_parameters
    return model_config


def _prune_stale_tool_parameters(
    value: Any,
    *,
    allowed_tools: list[str],
    existing_model_config: Any,
) -> Any:
    if not isinstance(value, dict):
        return value

    existing_tool_parameters = {}
    if isinstance(existing_model_config, dict) and isinstance(existing_model_config.get("tool_parameters"), dict):
        existing_tool_parameters = existing_model_config["tool_parameters"]
    existing_parameter_tools = {
        str(tool).strip()
        for tool in existing_tool_parameters
        if str(tool).strip()
    }
    allowed_tool_set = set(allowed_tools)

    pruned: dict[Any, Any] = {}
    for raw_tool, raw_tool_parameters in value.items():
        tool = str(raw_tool or "").strip()
        if tool not in allowed_tool_set and tool in existing_parameter_tools and tool in TOOL_PARAMETER_SPECS:
            continue
        pruned[raw_tool] = raw_tool_parameters
    return pruned


def _normalize_tool_parameters_value(value: Any, allowed_tools: list[str]) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    raw_parameters = value or {}
    if not isinstance(raw_parameters, dict):
        return (
            {},
            [
                _preflight_issue(
                    code="tool_parameters.object_required",
                    field_path="tool_parameters",
                    message="工具参数必须是对象",
                    suggestion="把工具参数改成以工具名为 key、参数对象为 value 的 JSON 对象。",
                )
            ],
        )

    allowed_tool_list: list[str] = []
    for item in allowed_tools:
        if isinstance(item, str) and item.strip() and item not in allowed_tool_list:
            allowed_tool_list.append(item)
    allowed_tool_set = set(allowed_tool_list)
    default_parameters = default_tool_parameters_for_tools(allowed_tool_list)
    allowed_parameter_tools = set(default_parameters)
    normalized = json.loads(dumps_json(default_parameters))

    for raw_tool, raw_tool_parameters in raw_parameters.items():
        tool = str(raw_tool or "").strip()
        field_path = f"tool_parameters.{tool or '<empty>'}"
        if not tool:
            errors.append(
                _preflight_issue(
                    code="tool_parameters.tool_required",
                    field_path=field_path,
                    message="工具参数不能包含空工具名",
                    suggestion="删除空工具名，或改成当前流程 allowed_tools 内支持参数的工具名。",
                )
            )
            continue
        if tool not in allowed_tool_set:
            errors.append(
                _preflight_issue(
                    code="tool_parameters.tool_not_allowed",
                    field_path=field_path,
                    message=f"工具参数包含当前流程未允许的工具：{tool}",
                    suggestion="删除该工具参数，或先在 allowed_tools 中保留该代码投影内工具。",
                )
            )
            continue
        if tool not in allowed_parameter_tools:
            errors.append(
                _preflight_issue(
                    code="tool_parameters.tool_schema_missing",
                    field_path=field_path,
                    message=f"工具尚未开放参数编辑：{tool}",
                    suggestion="删除该工具参数；如确需编辑，请先在代码投影中补充工具参数白名单和真实回归。",
                )
            )
            continue
        if not isinstance(raw_tool_parameters, dict):
            errors.append(
                _preflight_issue(
                    code="tool_parameters.params_object_required",
                    field_path=field_path,
                    message=f"{tool} 的工具参数必须是对象",
                    suggestion="把该工具参数改成参数名到参数值的 JSON 对象。",
                )
            )
            continue

        spec = TOOL_PARAMETER_SPECS[tool]
        unknown_parameters = sorted(set(str(key) for key in raw_tool_parameters) - set(spec))
        if unknown_parameters:
            errors.append(
                _preflight_issue(
                    code="tool_parameters.param_not_allowed",
                    field_path=field_path,
                    message=f"{tool} 包含未开放参数：{unknown_parameters[:5]}",
                    suggestion="删除未开放参数，或先在代码投影中补充该参数白名单、范围和真实回归。",
                )
            )
            continue

        for name, raw_value in raw_tool_parameters.items():
            parameter_name = str(name)
            parameter_field_path = f"{field_path}.{parameter_name}"
            parameter_value, issue = _normalize_tool_parameter_value(
                raw_value,
                spec[parameter_name],
                tool=tool,
                parameter_name=parameter_name,
                field_path=parameter_field_path,
            )
            if issue:
                errors.append(issue)
                continue
            normalized.setdefault(tool, {})[parameter_name] = parameter_value

    return normalized, errors


def _normalize_tool_parameter_value(
    raw_value: Any,
    spec: dict[str, Any],
    *,
    tool: str,
    parameter_name: str,
    field_path: str,
) -> tuple[Any, dict[str, str] | None]:
    parameter_type = str(spec.get("type") or "").strip()
    label = f"{tool}.{parameter_name}"

    if parameter_type == "integer":
        if isinstance(raw_value, bool):
            return None, _tool_parameter_type_issue(field_path, label, "整数")
        if isinstance(raw_value, int):
            value = raw_value
        elif isinstance(raw_value, float) and raw_value.is_integer():
            value = int(raw_value)
        else:
            return None, _tool_parameter_type_issue(field_path, label, "整数")
        return _validate_tool_parameter_range(value, spec, field_path, label)

    if parameter_type == "number":
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            return None, _tool_parameter_type_issue(field_path, label, "数字")
        return _validate_tool_parameter_range(float(raw_value), spec, field_path, label)

    if parameter_type == "boolean":
        if not isinstance(raw_value, bool):
            return None, _tool_parameter_type_issue(field_path, label, "布尔值")
        return raw_value, None

    if parameter_type == "string":
        if not isinstance(raw_value, str):
            return None, _tool_parameter_type_issue(field_path, label, "字符串")
        max_length = int(spec.get("max_length") or 200)
        if len(raw_value) > max_length:
            return (
                None,
                _preflight_issue(
                    code="tool_parameters.string_too_long",
                    field_path=field_path,
                    message=f"{label} 不能超过 {max_length} 个字符",
                    suggestion="缩短该参数，或改用代码投影中已评审的固定值。",
                ),
            )
        return raw_value, None

    if parameter_type == "select":
        options = [str(item) for item in spec.get("options") or []]
        value = str(raw_value or "").strip()
        if value not in options:
            return (
                None,
                _preflight_issue(
                    code="tool_parameters.option_invalid",
                    field_path=field_path,
                    message=f"{label} 必须是允许选项之一：{options}",
                    suggestion="从代码投影允许的参数选项中选择，不要填写任意值。",
                ),
            )
        return value, None

    return (
        None,
        _preflight_issue(
            code="tool_parameters.type_unsupported",
            field_path=field_path,
            message=f"{label} 参数类型未支持：{parameter_type}",
            suggestion="先在代码投影中补充该参数类型的校验规则和真实回归。",
        ),
    )


def _validate_tool_parameter_range(
    value: int | float,
    spec: dict[str, Any],
    field_path: str,
    label: str,
) -> tuple[int | float, dict[str, str] | None]:
    min_value = spec.get("min")
    max_value = spec.get("max")
    if min_value is not None and value < min_value:
        return (
            value,
            _preflight_issue(
                code="tool_parameters.value_too_small",
                field_path=field_path,
                message=f"{label} 不能小于 {min_value}",
                suggestion="把该参数调回代码投影允许范围内。",
            ),
        )
    if max_value is not None and value > max_value:
        return (
            value,
            _preflight_issue(
                code="tool_parameters.value_too_large",
                field_path=field_path,
                message=f"{label} 不能大于 {max_value}",
                suggestion="把该参数调回代码投影允许范围内。",
            ),
        )
    return value, None


def _tool_parameter_type_issue(field_path: str, label: str, expected_type: str) -> dict[str, str]:
    return _preflight_issue(
        code="tool_parameters.type_invalid",
        field_path=field_path,
        message=f"{label} 必须是{expected_type}",
        suggestion="按代码投影中的工具参数类型填写，不要保存任意 JSON 值。",
    )


def _normalize_allowed_tools_payload(value: Any, *, existing: dict[str, Any], current_user: dict) -> list[str]:
    if not isinstance(value, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许工具必须是字符串数组")

    tools: list[str] = []
    for raw_item in value:
        if not isinstance(raw_item, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许工具必须是字符串数组")
        item = raw_item.strip()
        if not item:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许工具不能包含空值")
        if len(item) > 160:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许工具名称不能超过 160 个字符")
        if item not in tools:
            tools.append(item)

    if not tools:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许工具至少保留一项")

    projection = get_flow_config(existing["flow_key"], current_user)
    projection_tools = {
        str(item).strip()
        for item in projection.get("allowed_tools") or []
        if isinstance(item, str) and str(item).strip()
    }
    unknown_tools = sorted(set(tools) - projection_tools)
    if unknown_tools:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不允许添加代码投影外工具：{unknown_tools[:5]}",
        )

    return tools


def _normalize_allowed_erp_resources_payload(value: Any, *, existing: dict[str, Any], current_user: dict) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许 ERP 资源必须是数组")

    projection = get_flow_config(existing["flow_key"], current_user)
    projection_resources: dict[str, dict[str, Any]] = {
        str(item.get("resource")): item
        for item in projection.get("allowed_erp_resources") or []
        if isinstance(item, dict) and item.get("resource")
    }

    resource_keys: list[str] = []
    for raw_item in value:
        if isinstance(raw_item, str):
            resource_key = raw_item.strip()
        elif isinstance(raw_item, dict):
            resource_key = str(raw_item.get("resource") or "").strip()
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许 ERP 资源必须是资源 key 或资源对象数组")

        if not resource_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许 ERP 资源不能包含空资源")
        if len(resource_key) > 160:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="允许 ERP 资源名称不能超过 160 个字符")
        if resource_key not in resource_keys:
            resource_keys.append(resource_key)

    unknown_resources = sorted(set(resource_keys) - set(projection_resources))
    if unknown_resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不允许添加代码投影外 ERP 资源：{unknown_resources[:5]}",
        )

    return [projection_resources[key] for key in resource_keys]


def _json_equivalent(left: Any, right: Any) -> bool:
    return json.loads(dumps_json(left)) == json.loads(dumps_json(right))


def _is_step_id_selector(raw_item: dict[str, Any]) -> bool:
    return set(raw_item) <= {"id"}


def _normalize_steps_payload(value: Any, *, existing: dict[str, Any], current_user: dict) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行步骤必须是数组")

    projection = get_flow_config(existing["flow_key"], current_user)
    projection_steps: dict[str, dict[str, Any]] = {
        str(item.get("id")): item
        for item in projection.get("steps") or []
        if isinstance(item, dict) and item.get("id")
    }

    step_ids: list[str] = []
    submitted_step_objects: list[tuple[str, dict[str, Any]]] = []
    for raw_item in value:
        if isinstance(raw_item, str):
            step_id = raw_item.strip()
        elif isinstance(raw_item, dict):
            step_id = str(raw_item.get("id") or "").strip()
            submitted_step_objects.append((step_id, raw_item))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行步骤必须是步骤 ID 或步骤对象数组")

        if not step_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行步骤不能包含空步骤 ID")
        if len(step_id) > 160:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行步骤 ID 不能超过 160 个字符")
        if step_id not in step_ids:
            step_ids.append(step_id)

    if not step_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行步骤至少保留一项")

    unknown_steps = sorted(set(step_ids) - set(projection_steps))
    if unknown_steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不允许添加代码投影外执行步骤：{unknown_steps[:5]}",
        )

    for step_id, raw_step in submitted_step_objects:
        if _is_step_id_selector(raw_step):
            continue
        projection_step = projection_steps[step_id]
        if not _json_equivalent(raw_step, projection_step):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"执行步骤对象内容不允许编辑：{step_id}",
            )

    normalized_steps = [json.loads(dumps_json(projection_steps[step_id])) for step_id in step_ids]
    order_errors = _validate_step_order(normalized_steps)
    if order_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=order_errors[0]["message"])

    return normalized_steps


def _scan_flow_version_secrets(existing: dict[str, Any]) -> list[dict[str, str]]:
    scan_payload = {
        "change_summary": existing.get("change_summary"),
        "input_schema": existing.get("input_schema"),
        "output_schema": existing.get("output_schema"),
        "prompt_template_preview": existing.get("prompt_template_preview"),
        "prompt_summary": existing.get("prompt_summary"),
        "model_config": existing.get("model_config"),
        "allowed_tools": existing.get("allowed_tools"),
        "allowed_erp_resources": existing.get("allowed_erp_resources"),
        "allowed_rag_scopes": existing.get("allowed_rag_scopes"),
        "permission_rules": existing.get("permission_rules"),
        "approval_policy": existing.get("approval_policy"),
        "failure_strategy": existing.get("failure_strategy"),
        "steps": existing.get("steps"),
        "publish_notes": existing.get("publish_notes"),
    }
    return _dedupe_preflight_issues(_scan_secret_value(scan_payload, ""))


def _scan_secret_value(value: Any, path: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = _join_preflight_path(path, str(key))
            key_text = str(key).lower()
            for marker in FORBIDDEN_SECRET_MARKERS:
                if marker in key_text:
                    errors.append(
                        _preflight_issue(
                            code="secret.marker_in_key",
                            field_path=child_path,
                            message=f"发现禁止保存的敏感字段名：{marker}",
                            suggestion="删除该字段，或改为运行时从密钥管理服务读取，不要把密钥字段保存在流程版本里。",
                        )
                    )
            errors.extend(_scan_secret_value(child, child_path))
        return errors

    if isinstance(value, list):
        for index, child in enumerate(value, start=1):
            errors.extend(_scan_secret_value(child, f"{path}[{index}]"))
        return errors

    if value is None:
        return []

    text = str(value).lower()
    for marker in FORBIDDEN_SECRET_MARKERS:
        if marker in text:
            errors.append(
                _preflight_issue(
                    code="secret.marker_in_value",
                    field_path=path,
                    message=f"发现禁止保存的敏感标记：{marker}",
                    suggestion="删除该字段中的真实密钥、Token、Authorization 或数据库连接串，只保留占位说明。",
                )
            )
    return errors


def _dedupe_preflight_issues(issues: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for issue in issues:
        key = (issue["code"], issue["field_path"], issue["message"])
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _join_preflight_path(parent: str, key: str) -> str:
    if key and key.replace("_", "").isalnum() and not key[0].isdigit():
        return f"{parent}.{key}" if parent else key
    return f'{parent}["{key}"]' if parent else f'["{key}"]'


def _validate_execution_contract(existing: dict[str, Any], current_user: dict) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if existing.get("flow_status") != "enabled":
        errors.append(
            _preflight_issue(
                code="execution.flow_disabled",
                field_path="flow_status",
                message="流程当前未启用，不能发布新版本",
                suggestion="先在流程配置中启用该流程，再重新发起发布前预检。",
            )
        )
    if not str(existing.get("trigger_type") or "").strip():
        errors.append(
            _preflight_issue(
                code="execution.trigger_type_required",
                field_path="trigger_type",
                message="trigger_type 不能为空",
                suggestion="选择一个明确的触发方式，保持与当前代码投影一致。",
            )
        )
    entrypoint = str(existing.get("entrypoint") or "").strip()
    if not entrypoint:
        errors.append(
            _preflight_issue(
                code="execution.entrypoint_required",
                field_path="entrypoint",
                message="entrypoint 不能为空",
                suggestion="补充以 / 开头的流程入口路径。",
            )
        )
    elif not entrypoint.startswith("/"):
        errors.append(
            _preflight_issue(
                code="execution.entrypoint_invalid",
                field_path="entrypoint",
                message="entrypoint 必须以 / 开头",
                suggestion="把入口改成类似 /finance/excel-generate 这样的路径。",
            )
        )

    allowed_tools = existing.get("allowed_tools")
    if not isinstance(allowed_tools, list) or not allowed_tools or not all(isinstance(item, str) and item.strip() for item in allowed_tools):
        errors.append(
            _preflight_issue(
                code="execution.allowed_tools_invalid",
                field_path="allowed_tools",
                message="allowed_tools 必须是非空字符串数组",
                suggestion="补充该流程实际允许调用的工具名数组，并删除空值或非字符串项。",
            )
        )
        normalized_allowed_tools: list[str] = []
    else:
        normalized_allowed_tools = [str(item).strip() for item in allowed_tools]

    model_config = existing.get("model_config")
    if not isinstance(model_config, dict):
        errors.append(
            _preflight_issue(
                code="execution.model_config_object_required",
                field_path="model_config",
                message="model_config 必须是对象",
                suggestion="恢复代码投影里的模型配置对象，不要保存数组、字符串或其他类型。",
            )
        )
    else:
        _, tool_parameter_errors = _normalize_tool_parameters_value(
            model_config.get("tool_parameters"),
            normalized_allowed_tools,
        )
        errors.extend(tool_parameter_errors)

    permission_rules = existing.get("permission_rules")
    if not isinstance(permission_rules, list) or not permission_rules or not all(isinstance(item, str) and item.strip() for item in permission_rules):
        errors.append(
            _preflight_issue(
                code="execution.permission_rules_invalid",
                field_path="permission_rules",
                message="permission_rules 必须是非空字符串数组",
                suggestion="补充岗位、角色或权限边界说明，确保发布后可审计。",
            )
        )

    approval_policy = str(existing.get("approval_policy") or "").strip()
    failure_strategy = str(existing.get("failure_strategy") or "").strip()
    change_summary = str(existing.get("change_summary") or "").strip()
    if not change_summary:
        errors.append(
            _preflight_issue(
                code="execution.change_summary_required",
                field_path="change_summary",
                message="change_summary 不能为空",
                suggestion="填写本版本相对上一版的业务变更摘要。",
            )
        )
    if not approval_policy:
        errors.append(
            _preflight_issue(
                code="execution.approval_policy_required",
                field_path="approval_policy",
                message="approval_policy 不能为空",
                suggestion="说明该流程是否需要人工审批，以及审批条件。",
            )
        )
    if not failure_strategy:
        errors.append(
            _preflight_issue(
                code="execution.failure_strategy_required",
                field_path="failure_strategy",
                message="failure_strategy 不能为空",
                suggestion="说明失败时如何记录、重试、回滚或交给人工处理。",
            )
        )

    steps = existing.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(
            _preflight_issue(
                code="execution.steps_required",
                field_path="steps",
                message="steps 必须是非空数组",
                suggestion="补充至少一个执行步骤，描述流程运行时的关键动作。",
            )
        )
    else:
        step_ids: set[str] = set()
        for index, step in enumerate(steps, start=1):
            path = f"steps[{index}]"
            if not isinstance(step, dict):
                errors.append(
                    _preflight_issue(
                        code="execution.step_object_required",
                        field_path=path,
                        message=f"{path} 必须是对象",
                        suggestion="把该步骤改成对象，并包含 id、name、inputs、retryable。",
                    )
                )
                continue
            step_id = str(step.get("id") or "").strip()
            if not step_id:
                errors.append(
                    _preflight_issue(
                        code="execution.step_id_required",
                        field_path=f"{path}.id",
                        message=f"{path}.id 不能为空",
                        suggestion="给该步骤补一个稳定唯一的 id。",
                    )
                )
            elif step_id in step_ids:
                errors.append(
                    _preflight_issue(
                        code="execution.step_id_duplicate",
                        field_path=f"{path}.id",
                        message=f"{path}.id 重复：{step_id}",
                        suggestion="把重复步骤 id 改成唯一值，避免运行记录追踪混淆。",
                    )
                )
            else:
                step_ids.add(step_id)
            if not str(step.get("name") or "").strip():
                errors.append(
                    _preflight_issue(
                        code="execution.step_name_required",
                        field_path=f"{path}.name",
                        message=f"{path}.name 不能为空",
                        suggestion="补充业务人员能看懂的步骤名称。",
                    )
                )
            if not isinstance(step.get("inputs"), list):
                errors.append(
                    _preflight_issue(
                        code="execution.step_inputs_array_required",
                        field_path=f"{path}.inputs",
                        message=f"{path}.inputs 必须是数组",
                        suggestion="把 inputs 改成该步骤依赖的字段名数组；没有依赖时使用空数组。",
                    )
                )
            if not isinstance(step.get("retryable"), bool):
                errors.append(
                    _preflight_issue(
                        code="execution.step_retryable_boolean_required",
                        field_path=f"{path}.retryable",
                        message=f"{path}.retryable 必须是布尔值",
                        suggestion="把 retryable 改成 true 或 false。",
                    )
                )
        errors.extend(_validate_step_order(steps))

    return errors


def _validate_step_order(steps: list[Any]) -> list[dict[str, str]]:
    step_positions: dict[str, int] = {}
    for index, step in enumerate(steps):
        if isinstance(step, dict):
            step_id = str(step.get("id") or "").strip()
            if step_id and step_id not in step_positions:
                step_positions[step_id] = index

    errors: list[dict[str, str]] = []
    for before_step, after_step in STEP_ORDER_DEPENDENCIES:
        before_index = step_positions.get(before_step)
        after_index = step_positions.get(after_step)
        if before_index is None or after_index is None:
            continue
        if before_index > after_index:
            errors.append(
                _preflight_issue(
                    code="execution.step_order_invalid",
                    field_path="steps",
                    message=f"执行步骤顺序不合法：{before_step} 必须早于 {after_step}",
                    suggestion="只在代码投影已有步骤内调整顺序，并保留前置校验、查询、生成、记录之间的依赖顺序。",
                )
            )
    return errors


def _validate_code_projection_contract(existing: dict[str, Any], current_user: dict) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    try:
        projection = get_flow_config(existing["flow_key"], current_user)
    except HTTPException:
        return [
            _preflight_issue(
                code="projection.flow_missing",
                field_path="flow_key",
                message="当前代码投影中找不到该流程，不能发布",
                suggestion="确认流程没有从代码投影中删除；如需删除，请先停用或回滚已治理版本。",
            )
        ]

    if existing.get("entrypoint") != projection.get("entrypoint"):
        errors.append(
            _preflight_issue(
                code="projection.entrypoint_mismatch",
                field_path="entrypoint",
                message="版本入口与当前代码投影不一致",
                suggestion="把版本入口恢复为当前代码投影入口，或先完成代码投影变更评审。",
            )
        )
    if existing.get("trigger_type") != projection.get("trigger_type"):
        errors.append(
            _preflight_issue(
                code="projection.trigger_type_mismatch",
                field_path="trigger_type",
                message="触发方式与当前代码投影不一致",
                suggestion="把触发方式恢复为当前代码投影值，避免发布后入口合同漂移。",
            )
        )

    projection_tools = set(projection.get("allowed_tools") or [])
    version_tools = set(existing.get("allowed_tools") or [])
    unknown_tools = sorted(version_tools - projection_tools)
    if unknown_tools:
        errors.append(
            _preflight_issue(
                code="projection.allowed_tools_overreach",
                field_path="allowed_tools",
                message=f"版本包含代码投影未允许的工具：{unknown_tools[:5]}",
                suggestion="从版本 allowed_tools 中移除这些工具，或先在代码投影中显式开放并通过评审。",
            )
        )

    projection_resources = {
        str(item.get("resource"))
        for item in projection.get("allowed_erp_resources") or []
        if isinstance(item, dict) and item.get("resource")
    }
    version_resources = {
        str(item.get("resource"))
        for item in existing.get("allowed_erp_resources") or []
        if isinstance(item, dict) and item.get("resource")
    }
    unknown_resources = sorted(version_resources - projection_resources)
    if unknown_resources:
        errors.append(
            _preflight_issue(
                code="projection.allowed_erp_resources_overreach",
                field_path="allowed_erp_resources",
                message=f"版本包含代码投影未允许的 ERP 资源：{unknown_resources[:5]}",
                suggestion="从版本 allowed_erp_resources 中移除这些资源，或先在代码投影中显式开放并通过评审。",
            )
        )

    projection_steps = {
        str(item.get("id")): item
        for item in projection.get("steps") or []
        if isinstance(item, dict) and item.get("id")
    }
    version_steps = {
        str(item.get("id")): item
        for item in existing.get("steps") or []
        if isinstance(item, dict) and item.get("id")
    }
    unknown_steps = sorted(set(version_steps) - set(projection_steps))
    if unknown_steps:
        errors.append(
            _preflight_issue(
                code="projection.steps_overreach",
                field_path="steps",
                message=f"版本包含代码投影未允许的执行步骤：{unknown_steps[:5]}",
                suggestion="从版本 steps 中移除这些步骤，或先在代码投影中显式开放并通过评审。",
            )
        )
    for step_id in sorted(set(version_steps) & set(projection_steps)):
        if _json_equivalent(version_steps[step_id], projection_steps[step_id]):
            continue
        errors.append(
            _preflight_issue(
                code="projection.step_object_mismatch",
                field_path="steps",
                message=f"执行步骤对象与代码投影不一致：{step_id}",
                suggestion="恢复代码投影里的规范步骤对象；当前阶段只允许选择投影内步骤和调整安全顺序，不允许编辑步骤内容。",
            )
        )

    return errors


def _flow_contract_snapshot_hash(existing: dict[str, Any]) -> str:
    snapshot = {
        "trigger_type": existing.get("trigger_type"),
        "entrypoint": existing.get("entrypoint"),
        "input_schema": existing.get("input_schema") or [],
        "output_schema": existing.get("output_schema") or [],
        "prompt_template": existing.get("prompt_template_preview") or "",
        "prompt_summary": existing.get("prompt_summary") or "",
        "model_config": existing.get("model_config") or {},
        "allowed_tools": existing.get("allowed_tools") or [],
        "allowed_erp_resources": existing.get("allowed_erp_resources") or [],
        "allowed_rag_scopes": existing.get("allowed_rag_scopes") or {},
        "permission_rules": existing.get("permission_rules") or [],
        "steps": existing.get("steps") or [],
    }
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _latest_business_regression_evidence(existing: dict[str, Any], script: str) -> dict[str, Any] | None:
    snapshot_hash = _flow_contract_snapshot_hash(existing)
    row = fetch_one(
        """
        SELECT
            e.id,
            e.flow_id,
            e.version_id,
            e.flow_key,
            e.version,
            e.version_status,
            e.snapshot_hash,
            e.script,
            e.command,
            e.profile,
            e.status,
            e.report_id,
            e.report_url,
            e.summary,
            e.metadata,
            e.verified_by,
            u.username AS verified_by_username,
            e.verified_at,
            e.expires_at,
            e.created_at
        FROM automation_flow_version_verification_evidence e
        LEFT JOIN users u ON u.id = e.verified_by
        WHERE e.flow_id = %s
          AND e.script = %s
          AND e.profile IN ('api', 'release')
          AND e.status = 'passed'
          AND e.expires_at > now()
          AND e.snapshot_hash = %s
        ORDER BY
            CASE WHEN e.version_id = %s THEN 0 ELSE 1 END,
            e.verified_at DESC
        LIMIT 1;
        """,
        (
            existing["flow_id"],
            script,
            snapshot_hash,
            existing["id"],
        ),
    )
    return _verification_evidence_from_row(row) if row else None


def _business_regression_artifacts(existing: dict[str, Any]) -> list[dict[str, Any]]:
    flow_key = str(existing.get("flow_key") or "")
    return [
        {
            "label": str(item["label"]),
            "command": str(item["command"]),
            "script": str(item["script"]),
            "profile": str(item["profile"]),
            "publish_evidence_required": bool(item.get("critical")),
            "latest_evidence": _latest_business_regression_evidence(existing, str(item["script"])),
        }
        for item in _regression_bindings_for_flow(flow_key)
    ]


def _validate_business_regression_binding(existing: dict[str, Any], *, require_evidence: bool = False) -> list[dict[str, str]]:
    flow_key = str(existing.get("flow_key") or "").strip()
    bindings = _regression_bindings_for_flow(flow_key)
    if not bindings:
        return [
            _preflight_issue(
                code="regression.binding_missing",
                field_path="flow_key",
                message=f"流程 {flow_key or '-'} 尚未绑定真实业务回归或评测脚本",
                suggestion="先为该 flow_key 在发布验证绑定表中登记真实 API/DB/浏览器回归脚本，再开放发布。",
            )
        ]

    errors: list[dict[str, str]] = []
    has_recent_evidence = False
    has_critical_bindings = any(bool(item.get("critical")) for item in bindings)
    for index, binding in enumerate(bindings, start=1):
        path = f"regression_bindings[{index}]"
        script = str(binding.get("script") or "").strip()
        profile = str(binding.get("profile") or "").strip()
        binding_has_structural_error = False
        if profile not in {"api", "release"}:
            binding_has_structural_error = True
            errors.append(
                _preflight_issue(
                    code="regression.profile_invalid",
                    field_path=f"{path}.profile",
                    message=f"{script or '-'} 绑定的 profile 不是 api/release：{profile or '-'}",
                    suggestion="把该绑定接入真实 API 或 release 发布闸门，不要只放在 quick 快检里。",
                )
            )
        script_path = _repo_root() / script
        if not script or not script_path.is_file():
            binding_has_structural_error = True
            errors.append(
                _preflight_issue(
                    code="regression.script_missing",
                    field_path=f"{path}.script",
                    message=f"绑定脚本不存在：{script or '-'}",
                    suggestion="补齐真实验证脚本，或把绑定修正为已存在的 scripts/verify_*.py 或 scripts/verify_*.mjs。",
                )
            )
            continue
        if not _is_allowed_verification_script(script):
            binding_has_structural_error = True
            errors.append(
                _preflight_issue(
                    code="regression.script_name_invalid",
                    field_path=f"{path}.script",
                    message=f"绑定脚本必须位于 scripts/verify_*：{script}",
                    suggestion="使用公开可复现的 scripts/verify_*.py 或 scripts/verify_*.mjs 作为发布证据。",
                )
            )
        if not _verify_all_contains_script(script):
            binding_has_structural_error = True
            errors.append(
                _preflight_issue(
                    code="regression.script_not_in_gate",
                    field_path=f"{path}.script",
                    message=f"绑定脚本尚未接入统一发布闸门：{script}",
                    suggestion="把该脚本加入 scripts/verify_all.py 的 api/release profile 后重新预检。",
                )
            )
        text = script_path.read_text(encoding="utf-8", errors="ignore")
        lower_text = text.lower()
        for marker in FORBIDDEN_VERIFICATION_MARKERS:
            if marker in lower_text:
                binding_has_structural_error = True
                errors.append(
                    _preflight_issue(
                        code="regression.mock_marker_forbidden",
                        field_path=f"{path}.script",
                        message=f"绑定脚本包含禁止的 mock/monkeypatch 标记：{marker}",
                        suggestion="发布绑定只能使用真实 API、真实数据库或真实浏览器路径；移除 mock/monkeypatch 后重新预检。",
                    )
            )
        if "no mock/stub/fake" not in lower_text:
            binding_has_structural_error = True
            errors.append(
                _preflight_issue(
                    code="regression.real_policy_missing",
                    field_path=f"{path}.script",
                    message=f"绑定脚本缺少真实验证声明：{script}",
                    suggestion="在脚本输出或说明中明确 no mock/stub/fake，并保持真实 API/DB/浏览器路径。",
                )
            )
        if require_evidence and not binding_has_structural_error:
            if _latest_business_regression_evidence(existing, script):
                has_recent_evidence = True
            elif binding.get("critical"):
                errors.append(
                    _preflight_issue(
                        code="regression.critical_evidence_missing",
                        field_path=f"{path}.report_id",
                        message=f"高风险流程关键脚本缺少最近通过证据：{script}",
                        suggestion="先运行该关键绑定脚本，并写入当前合同快照下的 passed 报告 ID 和有效期后再发布。",
                    )
                )
    if require_evidence and bindings and not has_critical_bindings and not has_recent_evidence:
        errors.append(
            _preflight_issue(
                code="regression.evidence_missing",
                field_path="regression_bindings.report_id",
                message="发布缺少最近一次通过的真实验证证据",
                suggestion="先运行该流程绑定的真实业务回归或评测脚本，并写入通过状态、报告 ID 和有效期后再发布。",
            )
        )
    return errors


def _regression_bindings_for_flow(flow_key: str) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    bindings.extend(REGRESSION_BINDINGS_BY_FLOW_KEY.get(flow_key, []))
    for suffix, suffix_bindings in REGRESSION_BINDINGS_BY_SUFFIX.items():
        if flow_key.endswith(suffix):
            bindings.extend(suffix_bindings)
    for prefix, prefix_bindings in REGRESSION_BINDINGS_BY_PREFIX.items():
        if flow_key.startswith(prefix):
            bindings.extend(prefix_bindings)
    return _dedupe_regression_bindings(bindings)


def _regression_binding_for_script(flow_key: str, script: str) -> dict[str, Any] | None:
    for binding in _regression_bindings_for_flow(flow_key):
        if str(binding.get("script") or "") == script:
            return binding
    return None


def _dedupe_regression_bindings(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        key = str(binding.get("script") or binding.get("command") or binding.get("label"))
        if key in seen:
            if binding.get("critical"):
                by_key[key]["critical"] = True
            continue
        seen.add(key)
        by_key[key] = binding
        result.append(binding)
    return result


def _is_allowed_verification_script(value: str) -> bool:
    path = Path(value)
    return (
        len(path.parts) == 2
        and path.parts[0] == "scripts"
        and path.name.startswith("verify_")
        and path.suffix in {".py", ".mjs"}
    )


def _verify_all_contains_script(value: str) -> bool:
    verify_all_path = _repo_root() / "scripts" / "verify_all.py"
    if not verify_all_path.is_file():
        return False
    return value in verify_all_path.read_text(encoding="utf-8", errors="ignore")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _flow_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "flow_key": row[1],
        "app_id": row[2],
        "name": row[3],
        "description": row[4],
        "category": row[5],
        "position": row[6],
        "owner_user_id": str(row[7]) if row[7] else None,
        "status": row[8],
        "source": row[9],
        "created_by": str(row[10]) if row[10] else None,
        "created_at": row[11],
        "updated_at": row[12],
    }


def _version_summary_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "flow_id": str(row[1]),
        "flow_key": row[2],
        "version": row[3],
        "version_number": row[4],
        "status": row[5],
        "change_summary": row[6],
        "trigger_type": row[7],
        "entrypoint": row[8],
        "approval_policy": row[9],
        "failure_strategy": row[10],
        "publish_notes": row[11],
        "created_by": str(row[12]) if row[12] else None,
        "created_by_username": row[13],
        "approved_by": str(row[14]) if row[14] else None,
        "approved_by_username": row[15],
        "published_by": str(row[16]) if row[16] else None,
        "published_by_username": row[17],
        "created_at": row[18],
        "updated_at": row[19],
        "approved_at": row[20],
        "published_at": row[21],
        "active_publication_id": str(row[22]) if row[22] else None,
        "active_publication_environment": row[23],
    }


def _version_detail_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "flow_id": str(row[1]),
        "flow_key": row[2],
        "app_id": row[3],
        "name": row[4],
        "description": row[5],
        "category": row[6],
        "position": row[7],
        "flow_status": row[8],
        "source": row[9],
        "version": row[10],
        "version_number": row[11],
        "status": row[12],
        "change_summary": row[13],
        "trigger_type": row[14],
        "entrypoint": row[15],
        "input_schema": _json_value(row[16], []),
        "output_schema": _json_value(row[17], []),
        "prompt_template_preview": row[18],
        "prompt_summary": row[19],
        "model_config": _json_value(row[20], {}),
        "allowed_tools": _json_value(row[21], []),
        "allowed_erp_resources": _json_value(row[22], []),
        "allowed_rag_scopes": _json_value(row[23], {}),
        "permission_rules": _json_value(row[24], []),
        "approval_policy": row[25],
        "failure_strategy": row[26],
        "steps": _json_value(row[27], []),
        "publish_notes": row[28],
        "created_by": str(row[29]) if row[29] else None,
        "created_by_username": row[30],
        "approved_by": str(row[31]) if row[31] else None,
        "approved_by_username": row[32],
        "published_by": str(row[33]) if row[33] else None,
        "published_by_username": row[34],
        "created_at": row[35],
        "updated_at": row[36],
        "approved_at": row[37],
        "published_at": row[38],
        "active_publication_id": str(row[39]) if row[39] else None,
        "active_publication_environment": row[40],
    }


def _publication_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "flow_id": str(row[1]),
        "flow_key": row[2],
        "version_id": str(row[3]),
        "version": row[4],
        "version_number": row[5],
        "environment": row[6],
        "status": row[7],
        "rollout_percent": row[8],
        "published_by": str(row[9]) if row[9] else None,
        "published_by_username": row[10],
        "published_at": row[11],
        "rollback_from_version_id": str(row[12]) if row[12] else None,
        "reason": row[13],
        "created_at": row[14],
    }


def _verification_evidence_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "flow_id": str(row[1]),
        "version_id": str(row[2]) if row[2] else None,
        "flow_key": row[3],
        "version": row[4],
        "version_status": row[5],
        "snapshot_hash": row[6],
        "script": row[7],
        "command": row[8],
        "profile": row[9],
        "status": row[10],
        "report_id": row[11],
        "report_url": row[12],
        "summary": row[13],
        "metadata": _json_value(row[14], {}),
        "verified_by": str(row[15]) if row[15] else None,
        "verified_by_username": row[16],
        "verified_at": _iso_datetime(row[17]),
        "expires_at": _iso_datetime(row[18]),
        "created_at": _iso_datetime(row[19]),
    }


def _iso_datetime(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def _audit(
    current_user: dict,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any],
) -> None:
    write_audit_log(
        user_id=current_user.get("id"),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata={
            "actor_username": current_user.get("username"),
            "actor_role": current_user.get("role"),
            "actor_position": current_user.get("position"),
            **metadata,
        },
    )
