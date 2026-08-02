from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.config import settings
from app.services.enterprise_wechat_service import (
    EnterpriseWechatApiError,
    attachment_from_storage_reference,
    get_enterprise_wechat_effective_settings,
    get_enterprise_wechat_contact,
    recipient_from_candidate,
    search_enterprise_wechat_recipients,
    send_enterprise_wechat_file,
)
from app.services.generated_file_service import get_generated_file_storage_reference
from app.services.finance_salary_service import (
    FinanceSalaryExportResult,
    SalaryExportIntent,
    recognize_salary_export_intent,
)
from app.services.mcp_tool_registry_service import execute_managed_mcp_tool


FINANCE_WECHAT_BUSINESS_STATUSES = {
    "waiting_confirmation",
    "waiting_recipient_selection",
    "waiting_generation",
    "waiting_wechat_confirmation",
    "generated",
    "waiting_manual_send",
    "waiting_executor",
    "waiting_callback",
    "completed",
    "failed",
}

FINANCE_WECHAT_STATUS_LABELS = {
    "waiting_confirmation": "等待确认",
    "waiting_recipient_selection": "等待选择接收对象",
    "waiting_generation": "等待生成文件",
    "waiting_wechat_confirmation": "等待企业微信确认",
    "generated": "工资表已生成",
    "waiting_manual_send": "等待人工发送",
    "waiting_executor": "等待外部执行器",
    "waiting_callback": "等待执行器回调",
    "completed": "执行完成",
    "failed": "执行失败",
}

FINANCE_WECHAT_RUN_STATUS_BY_BUSINESS_STATUS = {
    "waiting_confirmation": "blocked",
    "waiting_recipient_selection": "blocked",
    "waiting_generation": "blocked",
    "waiting_wechat_confirmation": "blocked",
    "generated": "succeeded",
    "waiting_manual_send": "blocked",
    "waiting_executor": "blocked",
    "waiting_callback": "blocked",
    "completed": "succeeded",
    "failed": "failed",
}


@dataclass
class FinanceSalaryWechatSendIntent:
    intent: str
    salary_intent: SalaryExportIntent
    recipient_name: str | None
    confidence: float
    matched_keywords: list[str]
    missing_fields: list[str]


def recognize_salary_wechat_send_intent(
    message: str,
    today: date | None = None,
) -> FinanceSalaryWechatSendIntent:
    salary_intent = recognize_salary_export_intent(message, today=today)
    text = " ".join((message or "").strip().split())
    lowered = text.lower()
    matched_keywords = list(salary_intent.matched_keywords)

    has_wechat = any(keyword in lowered for keyword in ["微信", "个人微信", "wechat", "weixin"])
    has_send = any(keyword in lowered for keyword in ["发送", "发给", "传给", "转发", "send"])
    if has_wechat:
        matched_keywords.append("微信")
    if has_send:
        matched_keywords.append("发送")

    recipient_name = extract_wechat_recipient(text)
    missing_fields: list[str] = []
    if salary_intent.intent != "finance_salary_export":
        missing_fields.append("工资表")
    if not has_wechat:
        missing_fields.append("微信")
    if not recipient_name:
        missing_fields.append("微信联系人")

    confidence = 0.35
    if salary_intent.intent == "finance_salary_export":
        confidence += 0.35
    if has_wechat:
        confidence += 0.15
    if has_send:
        confidence += 0.08
    if recipient_name:
        confidence += 0.07

    return FinanceSalaryWechatSendIntent(
        intent="finance_salary_wechat_send" if not missing_fields else "unknown",
        salary_intent=salary_intent,
        recipient_name=recipient_name,
        confidence=round(min(confidence, 0.98), 2),
        matched_keywords=_dedupe(matched_keywords),
        missing_fields=missing_fields,
    )


def extract_wechat_recipient(message: str) -> str | None:
    text = " ".join((message or "").strip().split())
    if not text:
        return None

    patterns = [
        r"(?:发送给|发给|传给|转发给|微信发给|微信发送给)\s*([A-Za-z0-9_\-\u4e00-\u9fff]{2,32})",
        r"(?:给)\s*([A-Za-z0-9_\-\u4e00-\u9fff]{2,32})(?:\s*的?微信)?",
        r"(?:联系人|微信联系人|接收人)\s*[:：]\s*([A-Za-z0-9_\-\u4e00-\u9fff]{2,32})",
        r"(?:微信)\s*[:：]\s*([A-Za-z0-9_\-\u4e00-\u9fff]{2,32})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        candidate = _clean_recipient(match.group(1))
        if candidate:
            return candidate
    return None


def build_salary_wechat_plan(intent: FinanceSalaryWechatSendIntent) -> dict[str, Any]:
    period = intent.salary_intent.period_label
    recipient = intent.recipient_name or "待确认联系人"
    return {
        "title": "工资表企业微信发送",
        "summary": f"准备生成 {period} 员工工资表，并通过企业微信发送给 {recipient}。",
        "period_label": period,
        "recipient_name": intent.recipient_name,
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": True,
        "manual_final_send_required": False,
        "steps": [
            {
                "key": "intent",
                "label": "识别需求",
                "description": f"识别工资期间为 {period}，发送目标为企业微信。",
            },
            {
                "key": "permission",
                "label": "检查权限",
                "description": "后端检查财务岗位、AI 应用启用状态和 ERP Salary Slip 访问权限。",
            },
            {
                "key": "erp",
                "label": "读取 ERP",
                "description": "按期间查询 ERPNext Salary Slip。",
            },
            {
                "key": "excel",
                "label": "生成 Excel",
                "description": "生成工资明细、自动化摘要和意图识别 Sheet。",
            },
            {
                "key": "confirm",
                "label": "发送前确认",
                "description": "文件生成后，在聊天窗口确认企业微信接收对象和工资敏感数据。",
            },
            {
                "key": "enterprise_wechat_send",
                "label": "企业微信发送",
                "description": "确认后由后端企业微信应用发送文件，不附带正文说明，并写入运行记录和审计。",
            },
        ],
        "warnings": [
            "工资表属于敏感数据，发送前必须确认联系人。",
            "Skill 选择可以由大模型辅助，真实发送必须走后端权限、确认和审计。",
        ],
        "status_flow": [
            {"status": "waiting_generation", "label": FINANCE_WECHAT_STATUS_LABELS["waiting_generation"]},
            {"status": "waiting_recipient_selection", "label": FINANCE_WECHAT_STATUS_LABELS["waiting_recipient_selection"]},
            {"status": "waiting_wechat_confirmation", "label": FINANCE_WECHAT_STATUS_LABELS["waiting_wechat_confirmation"]},
            {"status": "generated", "label": FINANCE_WECHAT_STATUS_LABELS["generated"]},
            {"status": "completed", "label": FINANCE_WECHAT_STATUS_LABELS["completed"]},
        ],
    }


def ensure_salary_wechat_intent_ready(intent: FinanceSalaryWechatSendIntent) -> None:
    if intent.salary_intent.intent != "finance_salary_export":
        raise ValueError("请说明要生成哪个月份的员工工资表。")
    if "微信" in intent.missing_fields:
        raise ValueError("请说明是否要通过企业微信发送工资表。")
    if "微信联系人" in intent.missing_fields:
        raise ValueError("请说明要发送给哪个微信联系人，例如：发给张三。")


def prepare_salary_wechat_dispatch(
    *,
    intent: FinanceSalaryWechatSendIntent,
    salary_result: FinanceSalaryExportResult,
    current_user: dict,
    source: str,
) -> dict[str, Any]:
    plan = build_salary_wechat_plan(intent)
    executor_mode = (settings.finance_wechat_executor_mode or "manual_final_click").strip() or "manual_final_click"
    wechat_settings = get_enterprise_wechat_effective_settings()
    configured = bool(wechat_settings["configured"])
    executor_type = "enterprise_wechat_api"
    recipient_search = search_enterprise_wechat_recipients(
        intent.recipient_name or "",
        object_types=_recipient_object_types_for_name(intent.recipient_name or ""),
        current_user=current_user,
    )
    selected_recipient = recipient_search.get("selected_item") if isinstance(recipient_search.get("selected_item"), dict) else None
    requires_recipient_selection = bool(recipient_search.get("needs_selection"))
    status = "waiting_recipient_selection" if requires_recipient_selection else "waiting_wechat_confirmation"
    message = (
        recipient_search.get("message")
        if requires_recipient_selection
        else "已生成工资表，请在聊天窗口确认企业微信接收对象和敏感数据后发送。"
    )

    payload = {
        "action": "send_enterprise_wechat_file_after_confirmation",
        "platform": "enterprise_wechat",
        "target_app": "enterprise_wechat",
        "channel": "enterprise_wechat",
        "recipient_name": intent.recipient_name,
        "recipient": selected_recipient,
        "recipient_search": recipient_search,
        "filename": salary_result.filename,
        "period_label": intent.salary_intent.period_label,
        "employee_count": len(salary_result.items),
        "manual_final_send_required": False,
        "message_body": "",
        "source": source,
        "requested_by": current_user.get("id"),
    }
    logs = [
        {
            "level": "info",
            "message": "工资表已生成，发送前需要确认企业微信接收对象和敏感数据。",
        },
        {
            "level": "warning",
            "message": "企业微信文件发送不会附带正文说明。",
        },
    ]
    if configured and wechat_settings["real_send_enabled"]:
        logs.append({
            "level": "info",
            "message": "企业微信应用已配置且真实发送开关已启用，确认后可由后端发送。",
        })
    elif configured:
        logs.append({
            "level": "info",
            "message": "企业微信应用已配置，但真实发送开关未启用；确认后会停留在待发送状态。",
        })
    else:
        logs.append({
            "level": "info",
            "message": "未配置企业微信应用参数，确认后会提示管理员配置。",
        })

    return {
        "status": status,
        "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
        "message": message,
        "executor_type": executor_type,
        "executor_mode": executor_mode,
        "configured": configured,
        "platform": "enterprise_wechat",
        "target_app": "enterprise_wechat",
        "channel": "enterprise_wechat",
        "recipient_name": intent.recipient_name,
        "recipient": selected_recipient,
        "recipient_search": recipient_search,
        "requires_recipient_selection": requires_recipient_selection,
        "manual_final_send_required": False,
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": True,
        "message_body": "",
        "payload": payload,
        "plan": plan,
        "logs": logs,
        "screenshots": [],
    }


def normalize_salary_wechat_business_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status in FINANCE_WECHAT_BUSINESS_STATUSES:
        return status
    return "waiting_manual_send"


def run_record_status_for_salary_wechat(business_status: Any) -> str:
    status = normalize_salary_wechat_business_status(business_status)
    return FINANCE_WECHAT_RUN_STATUS_BY_BUSINESS_STATUS.get(status, "blocked")


def dispatch_salary_wechat_send_task(
    *,
    dispatch: dict[str, Any],
    artifact_id: str | None,
    artifact_filename: str,
    current_user: dict,
) -> dict[str, Any]:
    mode = _normalize_executor_mode(settings.finance_wechat_executor_mode)
    mcp_tool_calls: list[dict[str, Any]] = []
    payload = _build_executor_payload(
        dispatch={
            **dispatch,
            "recipient_confirmed": True,
            "sensitive_data_confirmed": True,
        },
        artifact_id=artifact_id,
        artifact_filename=artifact_filename,
        current_user=current_user,
        mcp_tool_calls=mcp_tool_calls,
        recipient_confirmed=True,
        sensitive_data_confirmed=True,
    )
    base = {
        **dispatch,
        "payload": payload,
        "artifact_id": artifact_id,
        "artifact_filename": artifact_filename,
        "download_path": payload["salary_file"].get("download_path"),
        "mcp_tool_calls": mcp_tool_calls,
        "manual_final_send_required": True,
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": True,
        "status": "generated",
        "status_label": FINANCE_WECHAT_STATUS_LABELS["generated"],
        "executor_mode": mode,
        "logs": list(dispatch.get("logs") or []),
    }

    if mode == "n8n":
        return _dispatch_to_n8n(base, current_user=current_user)
    if mode == "tagui_mac":
        return _waiting_for_tagui_mac(base, current_user=current_user)
    return _waiting_for_manual_send(base)


def build_wechat_prepare_confirmation_task(
    *,
    dispatch: dict[str, Any],
    artifact_id: str | None,
    artifact_filename: str,
    current_user: dict,
) -> dict[str, Any]:
    mcp_tool_calls: list[dict[str, Any]] = []
    status = (
        "waiting_recipient_selection"
        if dispatch.get("requires_recipient_selection")
        else "waiting_wechat_confirmation"
    )
    payload = _build_executor_payload(
        dispatch=dispatch,
        artifact_id=artifact_id,
        artifact_filename=artifact_filename,
        current_user=current_user,
        mcp_tool_calls=mcp_tool_calls,
        recipient_confirmed=False,
        sensitive_data_confirmed=False,
    )
    logs = list(dispatch.get("logs") or [])
    logs.append({
        "level": "warning",
        "message": "文件已生成；企业微信发送前，需要确认接收对象和敏感数据。",
    })
    return {
        **dispatch,
        "payload": payload,
        "artifact_id": artifact_id,
        "artifact_filename": artifact_filename,
        "download_path": payload["salary_file"].get("download_path"),
        "mcp_tool_calls": mcp_tool_calls,
        "manual_final_send_required": False,
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": True,
        "status": status,
        "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
        "executor_type": "confirmation_required",
        "executor_mode": "confirm_before_enterprise_wechat_send",
        "configured": True,
        "message_body": "",
        "message": (
            "请先选择正确的企业微信接收对象。"
            if status == "waiting_recipient_selection"
            else "文件已生成。请确认企业微信接收对象和敏感数据后发送；消息不会附带正文说明。"
        ),
        "confirmation_card": build_enterprise_wechat_confirmation_card(
            execution={
                **dispatch,
                "status": status,
                "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
                "artifact_id": artifact_id,
                "artifact_filename": artifact_filename,
                "download_path": payload["salary_file"].get("download_path"),
                "payload": payload,
            },
        ),
        "logs": logs,
    }


def build_enterprise_wechat_file_confirmation_task(
    *,
    artifact_id: str,
    artifact_filename: str,
    recipient_name: str,
    current_user: dict,
    source_message: str | None = None,
    source_workflow_id: str | None = None,
    mime_type: str | None = None,
    requires_sensitive_confirmation: bool = False,
    artifacts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_recipient = recipient_name.strip()
    generated_artifacts = _normalize_confirmation_artifacts(
        artifact_id=artifact_id,
        artifact_filename=artifact_filename,
        mime_type=mime_type,
        artifacts=artifacts,
    )
    primary_artifact = generated_artifacts[0]
    recipient_search = search_enterprise_wechat_recipients(
        normalized_recipient,
        object_types=_recipient_object_types_for_name(normalized_recipient),
        current_user=current_user,
    )
    selected_recipient = recipient_search.get("selected_item") if isinstance(recipient_search.get("selected_item"), dict) else None
    requires_recipient_selection = bool(recipient_search.get("needs_selection"))
    status = "waiting_recipient_selection" if requires_recipient_selection else "waiting_wechat_confirmation"
    payload = {
        "task_type": "enterprise_wechat_generated_file_send",
        "task_version": "2026-07-29",
        "action": "send_enterprise_wechat_file_after_confirmation",
        "platform": "enterprise_wechat",
        "target_app": "enterprise_wechat",
        "channel": "enterprise_wechat",
        "recipient_name": normalized_recipient,
        "recipient": selected_recipient,
        "recipient_search": recipient_search,
        "salary_file": {
            "artifact_id": primary_artifact["artifact_id"],
            "filename": primary_artifact["filename"],
            "download_path": primary_artifact["download_path"],
            "mime_type": primary_artifact["mime_type"],
        },
        "generated_file": {
            "artifact_id": primary_artifact["artifact_id"],
            "filename": primary_artifact["filename"],
            "download_path": primary_artifact["download_path"],
            "mime_type": primary_artifact["mime_type"],
        },
        "generated_artifacts": generated_artifacts,
        "attachments": generated_artifacts,
        "source_message": source_message,
        "source_workflow_id": source_workflow_id,
        "manual_final_send_required": False,
        "requires_sensitive_confirmation": requires_sensitive_confirmation,
        "message_body": "",
        "requested_by": current_user.get("id"),
    }
    execution = {
        "status": status,
        "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
        "message": (
            "没有找到唯一的企业微信接收对象，请选择候选对象，或手动输入 userid / chat_id / department_id。"
            if requires_recipient_selection
            else "文件已生成。请确认企业微信接收对象后发送；消息不会附带正文说明。"
        ),
        "executor_type": "confirmation_required",
        "executor_mode": "confirm_before_enterprise_wechat_send",
        "configured": True,
        "platform": "enterprise_wechat",
        "target_app": "enterprise_wechat",
        "channel": "enterprise_wechat",
        "recipient_name": normalized_recipient,
        "recipient": selected_recipient,
        "recipient_search": recipient_search,
        "requires_recipient_selection": requires_recipient_selection,
        "manual_final_send_required": False,
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": requires_sensitive_confirmation,
        "message_body": "",
        "artifact_id": primary_artifact["artifact_id"],
        "artifact_filename": primary_artifact["filename"],
        "download_path": primary_artifact["download_path"],
        "generated_artifacts": generated_artifacts,
        "payload": payload,
        "logs": [
            {"level": "info", "message": "已准备企业微信文件发送确认卡。"},
            {"level": "warning", "message": "企业微信文件发送不会附带正文说明。"},
        ],
        "screenshots": [],
    }
    execution["confirmation_card"] = build_enterprise_wechat_confirmation_card(execution=execution)
    return execution


def build_enterprise_wechat_confirmation_card(*, execution: dict[str, Any]) -> dict[str, Any]:
    payload = execution.get("payload") if isinstance(execution.get("payload"), dict) else {}
    salary_file = payload.get("salary_file") if isinstance(payload.get("salary_file"), dict) else {}
    generated_file = payload.get("generated_file") if isinstance(payload.get("generated_file"), dict) else {}
    file_payload = generated_file or salary_file
    generated_artifacts = execution.get("generated_artifacts")
    if not isinstance(generated_artifacts, list):
        generated_artifacts = payload.get("generated_artifacts") if isinstance(payload.get("generated_artifacts"), list) else []
    recipient = execution.get("recipient") if isinstance(execution.get("recipient"), dict) else None
    recipient_search = execution.get("recipient_search") if isinstance(execution.get("recipient_search"), dict) else {}
    requires_sensitive_confirmation = bool(execution.get("requires_sensitive_confirmation"))
    return {
        "type": "enterprise_wechat_file_send_confirmation",
        "title": "企业微信文件发送确认",
        "channel": "enterprise_wechat",
        "status": execution.get("status"),
        "status_label": execution.get("status_label"),
        "description": "确认后由后端发送文件，不附带正文说明。",
        "message_body": "",
        "body_required": False,
        "allow_manual_recipient": True,
        "manual_recipient_types": ["user", "group", "department"],
        "requires_recipient_selection": bool(execution.get("requires_recipient_selection") or recipient_search.get("needs_selection")),
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": requires_sensitive_confirmation,
        "selected_recipient": recipient,
        "recipient_search": recipient_search,
        "artifact": {
            "artifact_id": execution.get("artifact_id") or file_payload.get("artifact_id"),
            "filename": execution.get("artifact_filename") or file_payload.get("filename"),
            "download_path": execution.get("download_path") or file_payload.get("download_path"),
            "mime_type": file_payload.get("mime_type"),
        },
        "artifacts": generated_artifacts or [
            {
                "artifact_id": execution.get("artifact_id") or file_payload.get("artifact_id"),
                "filename": execution.get("artifact_filename") or file_payload.get("filename"),
                "download_path": execution.get("download_path") or file_payload.get("download_path"),
                "mime_type": file_payload.get("mime_type"),
            }
        ],
        "actions": {
            "confirm_endpoint": "/automation/files/enterprise-wechat-send/confirm",
            "confirm_method": "POST",
        },
    }


def dispatch_enterprise_wechat_file_send_task(
    *,
    artifact_id: str,
    artifact_ids: list[str] | None = None,
    recipient_candidate_id: str | None,
    recipient: dict[str, Any] | None,
    recipient_name: str,
    current_user: dict,
    sensitive_data_confirmed: bool = True,
    requires_sensitive_confirmation: bool = True,
) -> dict[str, Any]:
    selected_recipient, recipient_search = _resolve_enterprise_wechat_recipient_for_send(
        recipient_candidate_id=recipient_candidate_id,
        recipient=recipient,
        recipient_name=recipient_name,
        current_user=current_user,
    )
    if selected_recipient is None:
        status = "waiting_recipient_selection"
        return {
            "status": status,
            "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
            "message": (recipient_search or {}).get("message") or "请先选择正确的企业微信接收对象。",
            "executor_type": "enterprise_wechat_api",
            "channel": "enterprise_wechat",
            "recipient_name": recipient_name,
            "recipient": None,
            "recipient_search": recipient_search or {},
            "requires_recipient_selection": True,
            "requires_recipient_confirmation": True,
            "requires_sensitive_confirmation": requires_sensitive_confirmation,
            "manual_final_send_required": False,
            "message_body": "",
            "logs": [
                {"level": "warning", "message": "企业微信接收对象不唯一或不存在，不能发送。"},
            ],
        }

    normalized_artifact_ids = _normalize_artifact_ids(artifact_id, artifact_ids)
    storage_references = [
        get_generated_file_storage_reference(item, current_user=current_user)
        for item in normalized_artifact_ids
    ]
    attachments = [attachment_from_storage_reference(item) for item in storage_references]
    generated_artifacts = [
        _generated_artifact_from_storage_reference(item, fallback_artifact_id=item_id)
        for item, item_id in zip(storage_references, normalized_artifact_ids)
    ]
    primary_artifact = generated_artifacts[0]
    filenames = "、".join(item["filename"] for item in generated_artifacts)
    try:
        send_result = send_enterprise_wechat_file(
            recipient=recipient_from_candidate(selected_recipient),
            attachments=attachments,
            confirmed=True,
            sensitive_confirmed=sensitive_data_confirmed,
        )
    except EnterpriseWechatApiError as error:
        status = "failed"
        error_diagnostics = _collect_enterprise_wechat_error_diagnostics(error)
        return {
            "status": status,
            "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
            "message": "企业微信发送失败，请联系管理员查看企业微信接口诊断。",
            "executor_type": "enterprise_wechat_api",
            "channel": "enterprise_wechat",
            "recipient_name": recipient_name,
            "recipient": selected_recipient,
            "recipient_search": recipient_search or {},
            "artifact_id": primary_artifact["artifact_id"],
            "artifact_filename": primary_artifact["filename"],
            "download_path": primary_artifact["download_path"],
            "generated_artifacts": generated_artifacts,
            "requires_recipient_confirmation": True,
            "requires_sensitive_confirmation": requires_sensitive_confirmation,
            "manual_final_send_required": False,
            "message_body": "",
            "admin_error_detail": str(error),
            "wechat_error_code": error.errcode,
            "wechat_error_message": error.errmsg,
            "api_diagnostics": error_diagnostics,
            "request_response_trace": error_diagnostics,
            "logs": [
                {"level": "error", "message": f"企业微信 API 返回失败：{error}"},
            ],
        }
    except Exception as error:
        status = "failed"
        return {
            "status": status,
            "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
            "message": "企业微信发送失败，请联系管理员查看企业微信接口诊断。",
            "executor_type": "enterprise_wechat_api",
            "channel": "enterprise_wechat",
            "recipient_name": recipient_name,
            "recipient": selected_recipient,
            "recipient_search": recipient_search or {},
            "artifact_id": primary_artifact["artifact_id"],
            "artifact_filename": primary_artifact["filename"],
            "download_path": primary_artifact["download_path"],
            "generated_artifacts": generated_artifacts,
            "requires_recipient_confirmation": True,
            "requires_sensitive_confirmation": requires_sensitive_confirmation,
            "manual_final_send_required": False,
            "message_body": "",
            "admin_error_detail": str(error),
            "logs": [
                {"level": "error", "message": f"企业微信 API 返回失败：{error}"},
            ],
        }

    business_status = _business_status_from_enterprise_wechat_result(send_result)
    execution = {
        "status": business_status,
        "status_label": FINANCE_WECHAT_STATUS_LABELS[business_status],
        "message": str(send_result.get("message") or "企业微信文件发送流程已处理。"),
        "executor_type": "enterprise_wechat_api",
        "configured": bool(send_result.get("status") != "not_configured"),
        "channel": "enterprise_wechat",
        "recipient_name": recipient_name,
        "recipient": selected_recipient,
        "recipient_search": recipient_search or {},
        "artifact_id": primary_artifact["artifact_id"],
        "artifact_filename": primary_artifact["filename"],
        "download_path": primary_artifact["download_path"],
        "generated_artifacts": generated_artifacts,
        "requires_recipient_confirmation": True,
        "requires_sensitive_confirmation": requires_sensitive_confirmation,
        "manual_final_send_required": False,
        "message_body": "",
        "send_result": send_result,
        "logs": [
            {"level": "info", "message": "已完成接收对象和敏感数据确认。"},
            {"level": "info", "message": f"已处理企业微信文件发送：{filenames}。"},
        ],
        "screenshots": [],
    }
    execution["confirmation_card"] = build_enterprise_wechat_confirmation_card(execution=execution)
    return execution


def _collect_enterprise_wechat_error_diagnostics(error: EnterpriseWechatApiError) -> list[dict[str, Any]]:
    diagnostic = error.diagnostic if isinstance(error.diagnostic, dict) else {}
    if not diagnostic:
        return []
    return [diagnostic]


def _recipient_object_types_for_name(value: str) -> list[str]:
    text = str(value or "")
    if "群" in text or "群聊" in text:
        return ["group"]
    if "部门" in text or text.endswith("部"):
        return ["department", "user"]
    return ["user", "group", "department"]


def _normalize_confirmation_artifacts(
    *,
    artifact_id: str,
    artifact_filename: str,
    mime_type: str | None,
    artifacts: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in artifacts or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("artifact_id") or item.get("id") or "").strip()
        if not item_id:
            continue
        normalized.append(
            {
                "artifact_id": item_id,
                "filename": str(item.get("filename") or item.get("name") or item_id),
                "download_path": str(item.get("download_path") or f"/files/{item_id}/download"),
                "mime_type": str(item.get("mime_type") or mime_type or "application/octet-stream"),
            }
        )
    if not normalized:
        normalized.append(
            {
                "artifact_id": artifact_id,
                "filename": artifact_filename,
                "download_path": f"/files/{artifact_id}/download",
                "mime_type": mime_type or "application/octet-stream",
            }
        )
    return _dedupe_artifacts(normalized)


def _normalize_artifact_ids(artifact_id: str, artifact_ids: list[str] | None) -> list[str]:
    values = [str(item or "").strip() for item in (artifact_ids or [])]
    values.append(str(artifact_id or "").strip())
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _generated_artifact_from_storage_reference(
    item: dict[str, Any],
    *,
    fallback_artifact_id: str | None = None,
) -> dict[str, Any]:
    artifact_id = str(item.get("id") or item.get("artifact_id") or fallback_artifact_id or "")
    return {
        "artifact_id": artifact_id,
        "filename": str(item.get("filename") or artifact_id),
        "download_path": f"/files/{artifact_id}/download",
        "mime_type": str(item.get("mime_type") or "application/octet-stream"),
    }


def _dedupe_artifacts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item.get("artifact_id") or "").strip()
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        result.append(item)
    return result


def _resolve_enterprise_wechat_recipient_for_send(
    *,
    recipient_candidate_id: str | None,
    recipient: dict[str, Any] | None,
    recipient_name: str,
    current_user: dict,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    candidate_id = str(recipient_candidate_id or "").strip()
    if candidate_id and not candidate_id.startswith("user-fallback:") and _looks_like_uuid(candidate_id):
        contact = get_enterprise_wechat_contact(candidate_id)
        if contact:
            return contact, {
                "query": recipient_name,
                "items": [contact],
                "matched_count": 1,
                "needs_selection": False,
                "selected_item": contact,
                "source": "enterprise_wechat_contacts",
            }

    if isinstance(recipient, dict) and recipient.get("name"):
        return recipient, {
            "query": recipient_name or str(recipient.get("name") or ""),
            "items": [recipient],
            "matched_count": 1,
            "needs_selection": False,
            "selected_item": recipient,
            "source": recipient.get("source") or "request_payload",
        }

    search_result = search_enterprise_wechat_recipients(
        recipient_name,
        object_types=_recipient_object_types_for_name(recipient_name),
        current_user=current_user,
    )
    if search_result.get("needs_selection"):
        return None, search_result
    selected = search_result.get("selected_item")
    return selected if isinstance(selected, dict) else None, search_result


def _looks_like_uuid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", value))


def _business_status_from_enterprise_wechat_result(result: dict[str, Any]) -> str:
    raw_status = str(result.get("status") or "").strip().lower()
    if raw_status in {"completed", "sent", "success", "succeeded"}:
        return "completed"
    if raw_status in {"waiting_executor", "not_configured", "disabled"}:
        return "waiting_executor"
    if raw_status in {"waiting_confirmation"}:
        return "waiting_wechat_confirmation"
    if raw_status in {"invalid_argument", "failed", "error"}:
        return "failed"
    return "waiting_executor"


def _clean_recipient(value: str) -> str | None:
    text = value.strip(" ，。,.；;：:「」『』()（）[]【】")
    if not text:
        return None
    stop_words = ["并", "然后", "后", "，", "。", ",", ".", "；", ";"]
    for stop_word in stop_words:
        if stop_word in text:
            text = text.split(stop_word, 1)[0].strip()
    if text in {"微信", "个人微信", "这个月", "本月", "上个月", "工资表", "员工工资表"}:
        return None
    return text[:32]


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def _normalize_executor_mode(value: str | None) -> str:
    mode = (value or "manual_final_click").strip().lower()
    if mode in {"n8n", "tagui_mac", "manual_final_click"}:
        return mode
    return "manual_final_click"


def _build_executor_payload(
    *,
    dispatch: dict[str, Any],
    artifact_id: str | None,
    artifact_filename: str,
    current_user: dict,
    mcp_tool_calls: list[dict[str, Any]],
    recipient_confirmed: bool,
    sensitive_data_confirmed: bool,
) -> dict[str, Any]:
    original_payload = dispatch.get("payload") if isinstance(dispatch.get("payload"), dict) else {}
    artifact_download_path = f"/files/{artifact_id}/download" if artifact_id else None

    selected_recipient = dispatch.get("recipient") if isinstance(dispatch.get("recipient"), dict) else None
    if selected_recipient is None and isinstance(original_payload.get("recipient"), dict):
        selected_recipient = original_payload["recipient"]

    return {
        "task_type": "finance_salary_wechat_send",
        "task_version": "2026-07-28",
        "business_status": "generated",
        "platform": dispatch.get("platform") or "enterprise_wechat",
        "target_app": dispatch.get("target_app") or "enterprise_wechat",
        "channel": dispatch.get("channel") or "enterprise_wechat",
        "action": dispatch.get("action") or "send_enterprise_wechat_file_after_confirmation",
        "recipient": {
            "name": original_payload.get("recipient_name") or dispatch.get("recipient_name"),
            "confirmed": recipient_confirmed,
            "selected": selected_recipient,
        },
        "recipient_search": dispatch.get("recipient_search") or original_payload.get("recipient_search") or {},
        "salary_file": {
            "artifact_id": artifact_id,
            "filename": artifact_filename,
            "download_path": artifact_download_path,
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        "period": {
            "label": original_payload.get("period_label"),
        },
        "safety": {
            "manual_final_send_required": bool(dispatch.get("manual_final_send_required")),
            "sensitive_data_confirmed": sensitive_data_confirmed,
            "auto_click_send_allowed": False,
            "llm_direct_execution_allowed": False,
            "message_body_allowed": False,
        },
        "message_body": "",
        "requested_by": {
            "id": current_user.get("id"),
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
        },
        "source": original_payload.get("source") or dispatch.get("source"),
    }


def _waiting_for_manual_send(base: dict[str, Any]) -> dict[str, Any]:
    logs = list(base.get("logs") or [])
    logs.append({
        "level": "info",
        "message": "当前为人工最终发送模式，系统已生成工资表并停止在微信发送前。",
    })
    return {
        **base,
        "status": "waiting_manual_send",
        "status_label": FINANCE_WECHAT_STATUS_LABELS["waiting_manual_send"],
        "executor_type": "manual_final_click",
        "configured": True,
        "message": "工资表已生成，等待财务人工确认并在个人微信中最终发送。",
        "logs": logs,
    }


def _waiting_for_tagui_mac(base: dict[str, Any], *, current_user: dict) -> dict[str, Any]:
    logs = list(base.get("logs") or [])
    payload = base.get("payload") if isinstance(base.get("payload"), dict) else {}
    salary_file = payload.get("salary_file") if isinstance(payload.get("salary_file"), dict) else {}
    recipient = payload.get("recipient") if isinstance(payload.get("recipient"), dict) else {}
    local_file_path = None
    artifact_id = salary_file.get("artifact_id") or base.get("artifact_id")
    if artifact_id:
        try:
            storage_reference = get_generated_file_storage_reference(
                str(artifact_id),
                current_user=current_user,
            )
            local_file_path = storage_reference["storage_path"]
        except Exception as error:
            return _failed_dispatch(base, logs, f"读取微信附件本机路径失败：{error}", executor_type="tagui_mac")

    try:
        rpa_result = execute_managed_mcp_tool(
            tool_id="desktop_rpa.prepare_wechat_attachment",
            arguments={
                "recipient_name": recipient.get("name") or base.get("recipient_name"),
                "artifact_id": salary_file.get("artifact_id"),
                "filename": salary_file.get("filename"),
                "download_path": salary_file.get("download_path"),
                "local_file_path": local_file_path,
                "platform_name": "mac",
            },
            current_user=current_user,
            source="finance_salary_wechat_send",
            trace_collector=base.get("mcp_tool_calls") if isinstance(base.get("mcp_tool_calls"), list) else None,
        )
    except Exception as error:
        return _failed_dispatch(base, logs, f"Mac RPA MCP 调用失败：{error}", executor_type="tagui_mac")

    if not isinstance(rpa_result, dict):
        rpa_result = {"ok": True, "status": "waiting_executor", "result": rpa_result}

    logs.append({
        "level": "info",
        "message": str(rpa_result.get("message") or "Mac RPA MCP 已返回准备状态。"),
    })
    status = normalize_salary_wechat_business_status(rpa_result.get("status") or "waiting_executor")
    return {
        **base,
        "status": status,
        "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
        "executor_type": "tagui_mac",
        "configured": bool(settings.finance_wechat_mac_rpa_enabled),
        "message": str(rpa_result.get("message") or "工资表已生成，Mac 个人微信执行器已准备。"),
        "logs": logs,
        "script_hint": rpa_result.get("script_hint") or [],
        "mcp_tool_id": "desktop_rpa.prepare_wechat_attachment",
        "mcp_result": rpa_result,
    }


def _dispatch_to_n8n(base: dict[str, Any], *, current_user: dict) -> dict[str, Any]:
    logs = list(base.get("logs") or [])
    payload = base.get("payload") if isinstance(base.get("payload"), dict) else {}
    try:
        dispatch_result = execute_managed_mcp_tool(
            tool_id="n8n.dispatch_workflow",
            arguments={
                "workflow_type": "finance_salary_wechat_send",
                "payload": payload,
            },
            current_user=current_user,
            source="finance_salary_wechat_send",
            trace_collector=base.get("mcp_tool_calls") if isinstance(base.get("mcp_tool_calls"), list) else None,
        )
    except Exception as error:
        return _failed_dispatch(base, logs, f"n8n MCP 调用失败：{error}", executor_type="n8n")

    if not isinstance(dispatch_result, dict):
        dispatch_result = {"ok": True, "status": "accepted", "result": dispatch_result}

    status = _status_from_executor_response(dispatch_result)
    logs.append({
        "level": "info",
        "message": f"n8n 已接收任务，当前状态：{FINANCE_WECHAT_STATUS_LABELS[status]}。",
    })
    return {
        **base,
        "status": status,
        "status_label": FINANCE_WECHAT_STATUS_LABELS[status],
        "executor_type": "n8n",
        "configured": bool(dispatch_result.get("configured", True)),
        "message": str(dispatch_result.get("message") or _message_for_dispatched_status(status)),
        "response_payload": dispatch_result.get("response_payload") or dispatch_result,
        "external_reference": dispatch_result.get("external_reference") or _external_reference(dispatch_result),
        "mcp_tool_id": "n8n.dispatch_workflow",
        "mcp_result": dispatch_result,
        "logs": logs,
    }


def _failed_dispatch(
    base: dict[str, Any],
    logs: list[dict[str, Any]],
    message: str,
    *,
    executor_type: str,
) -> dict[str, Any]:
    logs.append({"level": "error", "message": message})
    return {
        **base,
        "status": "failed",
        "status_label": FINANCE_WECHAT_STATUS_LABELS["failed"],
        "executor_type": executor_type,
        "configured": True,
        "message": message,
        "logs": logs,
    }


def _status_from_executor_response(response_payload: dict[str, Any]) -> str:
    raw_status = str(response_payload.get("status") or "").strip().lower()
    if raw_status in {"completed", "done", "success", "succeeded"}:
        return "completed"
    if raw_status in {"failed", "error"}:
        return "failed"
    if raw_status in {"waiting_executor", "not_configured"}:
        return "waiting_executor"
    if raw_status in {"waiting_manual_send", "manual_send_required"}:
        return "waiting_manual_send"
    if raw_status in {"waiting_callback", "queued", "accepted", "running", "processing"}:
        return "waiting_callback"
    if response_payload.get("callback_expected") is True:
        return "waiting_callback"
    if response_payload.get("accepted") is True:
        return "waiting_callback"
    return "waiting_manual_send"


def _message_for_dispatched_status(status: str) -> str:
    if status == "completed":
        return "外部执行器已完成准备动作，请财务复核微信窗口并人工最终发送。"
    if status == "failed":
        return "外部执行器返回失败，请检查 n8n/RPA 日志。"
    if status == "waiting_callback":
        return "工资表已生成并派发给 n8n/RPA，等待外部执行器处理结果。"
    return "工资表已生成，等待财务人工确认并在个人微信中最终发送。"


def _external_reference(response_payload: dict[str, Any]) -> str | None:
    for key in ("external_reference", "execution_id", "task_id", "id"):
        value = response_payload.get(key)
        if value:
            return str(value)
    return None
