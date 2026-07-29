from contextlib import asynccontextmanager, suppress
import asyncio
import base64
import json
import logging
from queue import Empty, Queue
from threading import Thread
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from app.agents.low_risk_agent import run_low_risk_agent
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.api.audit_logs import router as audit_logs_router
from app.api.auth import router as auth_router
from app.api.ai_workflows import router as ai_workflows_router
from app.api.automation_flows import governance_router as automation_flow_governance_router
from app.api.automation_flows import router as automation_flows_router
from app.api.business_action_loop import router as business_action_loop_router
from app.api.connectors import router as connectors_router
from app.api.customer_service import router as customer_service_router
from app.api.effect_analytics import router as effect_analytics_router
from app.api.evaluation_center import router as evaluation_center_router
from app.api.feedback import router as feedback_router
from app.api.files import router as files_router
from app.api.monitoring_center import router as monitoring_center_router
from app.api.mcp_tools import router as mcp_tools_router
from app.api.notifications import router as notifications_router
from app.api.platform_action_executors import router as platform_action_executors_router
from app.api.platform_drafts import router as platform_drafts_router
from app.api.platform_execution_tasks import router as platform_execution_tasks_router
from app.api.rag_authorization import router as rag_authorization_router
from app.api.settings import router as settings_router
from app.auth.security import get_current_user, require_admin
from app.db import close_pool, open_pool
from app.graph.workflow import graph
from app.llm import chat as run_llm_chat, chat_model
from app.api.approvals import router as approvals_router
from app.api.automation import router as automation_router
from app.api.erp import router as erp_router
from app.api.refunds import router as refunds_router
from app.api.run_records import router as run_records_router
from app.api.threads import router as threads_router
from app.api.users import router as users_router
from app.permissions import POSITION_LABELS, ensure_chat_allowed_for_position, is_valid_position
from app.rag.ingest import (
    ALLOWED_FIELD_SCOPES,
    ALLOWED_MARKET_SCOPES,
    ALLOWED_SENSITIVITY_LEVELS,
    ALLOWED_STORE_SCOPES,
    ingest_documents,
    normalize_field_scope,
    normalize_market_scope,
    normalize_sensitivity_level,
    normalize_store_scope,
)
from app.rag.loaders import (
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
    load_documents_from_bytes,
)
from app.services.context_service import (
    build_context_bundle,
    cleanup_expired_context,
    update_context_after_turn,
)
from app.services.agent_execution_service import (
    PLAN_EXECUTE_WORKFLOW_ID,
    build_finance_monthly_package_plan,
    classify_agent_task,
    execute_finance_monthly_package_wechat,
)
from app.services.chat_automation_dispatcher import run_chat_automation
from app.services.automation_flow_version_service import resolve_flow_execution_reference
from app.services.chat_react_decision_service import (
    decide_chat_action,
    forced_graph_intent_for_action,
    permission_denial_for_decision,
)
from app.services.customer_service_automation_service import ensure_customer_service_automation_schema
from app.services.erp_service import query_erp_for_current_user, summarize_erp_items
from app.services.email_service import (
    EmailAttachment,
    email_result_metadata,
    is_email_send_requested,
    send_email_with_attachments,
)
from app.services.enterprise_wechat_service import ensure_enterprise_wechat_schema
from app.services.feedback_service import ensure_feedback_schema
from app.services.generated_file_service import (
    ensure_generated_file_schema,
    get_latest_generated_file_for_thread,
    save_generated_file,
)
from app.services.rag_authorization_service import (
    create_document_grant,
    normalize_document_access_inputs,
    normalize_document_grant_inputs,
)
from app.services.platform_draft_service import ensure_platform_draft_schema
from app.services.finance_salary_service import (
    export_salary_workbook_from_erp,
    recognize_salary_export_intent,
)
from app.services.finance_compound_intent_service import (
    FINANCE_COMPOUND_INTENT,
    finance_compound_requested_resources,
    recognize_finance_compound_intent,
    should_handle_finance_compound_generation,
)
from app.services.finance_salary_wechat_service import (
    build_enterprise_wechat_file_confirmation_task,
    build_salary_wechat_plan,
    build_wechat_prepare_confirmation_task,
    extract_wechat_recipient,
    prepare_salary_wechat_dispatch,
    recognize_salary_wechat_send_intent,
    run_record_status_for_salary_wechat,
)
from app.services.logging_service import (
    create_chat_thread,
    ensure_chat_thread,
    ensure_chat_thread_schema,
    get_thread,
    save_chat_message,
    write_audit_log,
)
from app.services.mcp_service import (
    create_external_ticket,
    get_external_ticket,
    sync_document_system_to_rag,
)
from app.services.mcp_tool_registry_service import ensure_mcp_tool_registry_schema
from app.services.notification_service import ensure_notification_schema
from app.services.platform_action_executor_config_service import ensure_platform_action_executor_config_schema
from app.services.run_record_service import (
    elapsed_ms,
    ensure_run_record_flow_reference_schema,
    finish_run,
    now_ms,
    record_artifact,
    record_step,
    start_run,
)
from app.services.user_ai_app_permission_service import (
    ensure_user_ai_app_permission_schema,
    is_ai_app_allowed,
)
from app.skills.executor import execute_skill
from app.skills.registry import skill_for_react_action
from app.services.user_settings_service import ensure_user_settings_schema

logger = logging.getLogger(__name__)


async def cleanup_expired_context_loop() -> None:
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            await asyncio.to_thread(cleanup_expired_context)
        except Exception:
            logger.exception("Failed to cleanup expired context records")


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    ensure_user_settings_schema()
    ensure_user_ai_app_permission_schema()
    ensure_customer_service_automation_schema()
    ensure_generated_file_schema()
    ensure_platform_draft_schema()
    ensure_platform_action_executor_config_schema()
    ensure_mcp_tool_registry_schema()
    ensure_notification_schema()
    ensure_feedback_schema()
    ensure_chat_thread_schema()
    ensure_run_record_flow_reference_schema()
    ensure_enterprise_wechat_schema()
    cleanup_expired_context()
    cleanup_task = asyncio.create_task(cleanup_expired_context_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        close_pool()


app = FastAPI(
    title="AI automated back-end management system",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5188",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5188",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(ai_workflows_router)
app.include_router(approvals_router)
app.include_router(automation_router)
app.include_router(automation_flows_router)
app.include_router(automation_flow_governance_router)
app.include_router(business_action_loop_router)
app.include_router(connectors_router)
app.include_router(customer_service_router)
app.include_router(effect_analytics_router)
app.include_router(evaluation_center_router)
app.include_router(feedback_router)
app.include_router(files_router)
app.include_router(monitoring_center_router)
app.include_router(mcp_tools_router)
app.include_router(notifications_router)
app.include_router(platform_action_executors_router)
app.include_router(platform_drafts_router)
app.include_router(platform_execution_tasks_router)
app.include_router(rag_authorization_router)
app.include_router(audit_logs_router)
app.include_router(erp_router)
app.include_router(refunds_router)
app.include_router(run_records_router)
app.include_router(settings_router)
app.include_router(threads_router)
app.include_router(users_router)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    intent: str | None = None
    risk_level: str | None = None
    erp_references: list[dict] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)
    platform_draft: dict | None = None
    approval_result: dict | None = None
    automation: dict | None = None


class ChatStreamEvent(BaseModel):
    event: str
    data: dict


class AgentChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class AgentChatResponse(BaseModel):
    thread_id: str
    answer: str


class ChatIntentResponse(BaseModel):
    thread_id: str
    answer: str
    intent: str | None = None
    risk_level: str | None = None
    approval_result: dict | None = None


class PublicLLMMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class PublicLLMChatRequest(BaseModel):
    message: str
    history: list[PublicLLMMessage] = Field(default_factory=list)


class PublicLLMChatResponse(BaseModel):
    answer: str


class McpDocumentSyncRequest(BaseModel):
    visibility: Literal["employee", "admin"] = "employee"
    department: str | None = None
    position_scope: Literal["operations", "customer_service", "finance"] | None = None
    market_scope: Literal["us", "de", "jp"] | None = None
    store_scope: Literal["us_store", "de_store", "jp_store"] | None = None
    field_scope: Literal[
        "operations_listing",
        "operations_inventory",
        "operations_sales",
        "customer_profile",
        "customer_logistics",
        "customer_after_sales",
        "finance_invoice",
        "finance_payment",
        "finance_profit",
        "finance_salary",
    ] | None = None
    sensitivity_level: Literal["internal", "confidential", "restricted"] | None = None


class McpTicketCreateRequest(BaseModel):
    title: str
    description: str
    priority: str = "normal"


def format_sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def format_business_progress_sse(
    *,
    thread_id: str,
    step_key: str,
    label: str,
    workflow_id: str = "chat",
    status_value: str = "running",
    detail: str | None = None,
    data: dict[str, Any] | None = None,
) -> str:
    payload = {
        "thread_id": thread_id,
        "workflow_id": workflow_id,
        "step_key": step_key,
        "label": label,
        "status": status_value,
        "detail": detail,
        "data": data or {},
    }
    return format_sse("business_progress", payload)


def business_error_message_for_user(error: Exception, current_user: dict) -> str:
    detail = getattr(error, "detail", None)
    raw_message = str(detail or error or "执行失败")
    lowered = raw_message.lower()

    if "erpnext" in lowered or "erp" in lowered or "502" in lowered or "salary slip" in lowered:
        message = "ERPNext 暂时不可用，请稍后重试或联系管理员。"
    elif "权限" in raw_message or "403" in raw_message or "forbidden" in lowered:
        message = "当前账号没有执行这个操作的权限，请联系管理员开通。"
    elif "联系人" in raw_message:
        message = raw_message
    elif "没有查到" in raw_message:
        message = raw_message
    else:
        message = "这次自动化没有执行成功，请稍后重试或联系管理员。"

    if current_user.get("role") == "admin":
        message = f"{message} 技术线索：{raw_message[:180]}"

    return message


def resolve_chat_thread_id(
    requested_thread_id: str | None,
    current_user: dict,
    title: str | None = None,
) -> str:
    normalized_thread_id = requested_thread_id.strip() if requested_thread_id else ""

    if not normalized_thread_id:
        return create_chat_thread(
            user_id=current_user["id"],
            title=title or "新会话",
            position=current_user.get("position"),
        )["id"]

    thread = get_thread(normalized_thread_id)
    if thread is None:
        raise HTTPException(
            status_code=404,
            detail="会话不存在，请先创建新会话。",
        )

    if thread["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="没有权限使用该会话。",
        )

    if (
        current_user.get("role") != "admin"
        and thread.get("position")
        and thread.get("position") != current_user.get("position")
    ):
        raise HTTPException(
            status_code=403,
            detail="没有权限使用其他岗位的会话。",
        )

    ensure_chat_thread(
        thread_id=normalized_thread_id,
        user_id=current_user["id"],
        title=title or thread.get("title"),
        position=current_user.get("position"),
    )
    return normalized_thread_id


def chunk_text(text: str, size: int = 12):
    if not text:
        return

    for index in range(0, len(text), size):
        yield text[index:index + size]


def erp_references_from_result(result: dict) -> list[dict]:
    erp_result = result.get("erp_result")
    if not isinstance(erp_result, dict):
        return []

    references = erp_result.get("references")
    return references if isinstance(references, list) else []


def attachments_from_result(result: dict) -> list[dict]:
    attachments = result.get("attachments")
    return attachments if isinstance(attachments, list) else []


def platform_draft_from_result(result: dict) -> dict | None:
    draft = result.get("platform_draft")
    return draft if isinstance(draft, dict) else None


def _platform_draft_without_content(draft: dict | None) -> dict | None:
    if not isinstance(draft, dict):
        return None

    return {
        **draft,
        "content": {},
    }


def _save_assistant_automation_message(
    *,
    result: dict,
    current_user: dict,
    entrypoint: str | None = None,
) -> None:
    erp_references = result.get("erp_references") if isinstance(result.get("erp_references"), list) else []
    metadata = {
        "intent": result.get("intent"),
        "risk_level": result.get("risk_level"),
        "position": current_user.get("position"),
        "erp_references": erp_references,
        "approval_result": result.get("approval_result"),
        "attachments": [
            _attachment_without_content(item)
            for item in attachments_from_result(result)
        ],
        "platform_draft": _platform_draft_without_content(platform_draft_from_result(result)),
        "automation": result.get("automation"),
    }
    if entrypoint:
        metadata["entrypoint"] = entrypoint

    save_chat_message(
        thread_id=result.get("thread_id"),
        user_id=current_user["id"],
        role="assistant",
        content=result.get("answer", ""),
        metadata=metadata,
    )


def _finish_chat_automation_run(
    *,
    run_id: str,
    result: dict,
    request: ChatRequest,
    started_ms: int,
    step_started_ms: int,
    current_user: dict,
    context_bundle: dict,
    action: str,
) -> None:
    erp_references = result.get("erp_references") if isinstance(result.get("erp_references"), list) else []
    draft = platform_draft_from_result(result)
    automation = result.get("automation") if isinstance(result.get("automation"), dict) else {}
    record_step(
        run_id=run_id,
        step_name="chat_automation.dispatch",
        step_order=1,
        status_value="succeeded",
        provider="chat_automation_dispatcher",
        resource_type="automation",
        resource_id=str(automation.get("workflow_id") or automation.get("type") or result.get("intent")),
        input_text=request.message,
        output_text=result.get("answer", ""),
        duration_ms=elapsed_ms(step_started_ms),
        metadata={
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "automation": automation,
            "platform_draft_id": draft.get("id") if draft else None,
            "erp_reference_count": len(erp_references),
        },
    )
    if draft:
        record_artifact(
            run_id=run_id,
            artifact_type="platform_draft",
            name=str(draft.get("title") or draft.get("id")),
            external_ref=str(draft.get("id")),
            metadata={
                "draft_type": draft.get("draft_type"),
                "position": draft.get("position"),
                "status": draft.get("status"),
                "writeback_status": draft.get("writeback_status"),
                "external_target": draft.get("external_target"),
            },
        )

    finish_run(
        run_id,
        status_value="succeeded",
        output_text=result.get("answer", ""),
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "final_thread_id": result.get("thread_id"),
            "automation": automation,
            "platform_draft_id": draft.get("id") if draft else None,
            "erp_reference_count": len(erp_references),
        },
    )
    write_audit_log(
        user_id=current_user["id"],
        action=action,
        resource_type="thread",
        resource_id=result.get("thread_id"),
        metadata={
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "position": current_user.get("position"),
            "automation": automation,
            "platform_draft_id": draft.get("id") if draft else None,
            "erp_reference_count": len(erp_references),
            "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
            "recent_message_count": len(context_bundle.get("recent_messages", [])),
        },
    )


def _run_finance_salary_export_chat(
    *,
    request: ChatRequest,
    current_user: dict,
    thread_id: str,
    run_id: str,
    started_ms: int,
    intent,
    stream: bool,
) -> dict:
    record_step(
        run_id=run_id,
        step_name="finance_salary_intent_recognition",
        step_order=1,
        status_value="succeeded",
        provider="rules",
        resource_type="automation",
        resource_id="salary_summary",
        input_text=request.message,
        output_text=f"{intent.intent} / {intent.period_label} / {intent.output_format}",
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": intent.intent,
            "confidence": intent.confidence,
            "matched_keywords": intent.matched_keywords,
            "entrypoint": "chat_stream" if stream else "chat",
        },
    )
    step_started_ms = now_ms()
    try:
        salary_result = export_salary_workbook_from_erp(
            message=request.message,
            current_user=current_user,
            intent=intent,
        )
    except ValueError as error:
        record_step(
            run_id=run_id,
            step_name="finance_salary_export",
            step_order=2,
            status_value="failed",
            provider="erp_provider",
            resource_type="erp",
            resource_id="Salary Slip",
            input_text=request.message,
            error_message=error,
            duration_ms=elapsed_ms(step_started_ms),
            metadata={
                "intent": intent.intent,
                "period_label": intent.period_label,
                "start_date": intent.start_date.isoformat(),
                "end_date": intent.end_date.isoformat(),
            },
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    attachment = _salary_export_attachment(salary_result)
    record_step(
        run_id=run_id,
        step_name="finance_salary_export",
        step_order=2,
        status_value="succeeded",
        provider=salary_result.provider,
        resource_type="erp",
        resource_id="Salary Slip",
        input_text=request.message,
        output_text=salary_result.filename,
        duration_ms=elapsed_ms(step_started_ms),
        metadata=salary_result.metadata,
    )
    artifact_id = save_generated_file(
        run_id=run_id,
        content=salary_result.content,
        artifact_type="excel_file",
        mime_type=attachment["mime_type"],
        filename=salary_result.filename,
        current_user=current_user,
        metadata=salary_result.metadata,
    )
    if artifact_id:
        attachment["metadata"] = {
            **attachment["metadata"],
            "artifact_id": artifact_id,
            "download_path": f"/files/{artifact_id}/download",
        }
    email_requested = is_email_send_requested(request.message)
    email_result = None
    email_metadata = {
        "email_requested": False,
        "email_sent": False,
    }
    if email_requested:
        email_started_ms = now_ms()
        email_result = send_email_with_attachments(
            to_email=current_user.get("email"),
            subject=f"{salary_result.intent.period_label}员工工资表",
            body=(
                f"你好，{current_user.get('display_name') or current_user.get('username')}：\n\n"
                f"系统已根据你的 AI 对话请求自动生成 {salary_result.intent.period_label} 员工工资表，"
                f"共 {len(salary_result.items)} 名员工，应发合计 "
                f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
                f"{salary_result.metadata['net_pay_total']:.2f}。\n\n"
                "附件为本次生成的 Excel 文件。"
            ),
            attachments=[
                EmailAttachment(
                    filename=salary_result.filename,
                    content=salary_result.content,
                    mime_type=attachment["mime_type"],
                )
            ],
        )
        email_metadata = email_result_metadata(email_result)
        record_step(
            run_id=run_id,
            step_name="email_delivery",
            step_order=3,
            status_value="succeeded" if email_result.sent else "failed",
            provider=email_result.provider,
            resource_type="email",
            resource_id=email_result.recipient,
            input_text=request.message,
            output_text="已发送工资表邮件" if email_result.sent else email_result.error,
            duration_ms=elapsed_ms(email_started_ms),
            error_message=email_result.error if not email_result.sent else None,
            metadata=email_metadata,
        )

    answer = (
        f"已识别为财务工资表导出请求，自动查询 {salary_result.provider_label} 的 "
        f"Salary Slip，并生成 {salary_result.intent.period_label} 员工工资表 Excel。\n"
        f"本次共 {len(salary_result.items)} 名员工，应发合计 "
        f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
        f"{salary_result.metadata['net_pay_total']:.2f}。\n"
        f"附件：{salary_result.filename}"
    )
    if email_requested and email_result:
        if email_result.sent:
            answer += f"\n已按你的要求发送到邮箱：{email_result.recipient}"
        else:
            answer += f"\n你要求发送到邮箱，但邮件未发送成功：{email_result.error}"
    else:
        answer += "\n你没有要求发送邮箱，本次只在对话中输出并生成可下载附件。"
    finish_run(
        run_id,
        status_value="succeeded",
        output_text=answer,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            **salary_result.metadata,
            **email_metadata,
            "final_thread_id": thread_id,
            "attachment_count": 1,
            "artifact_id": artifact_id,
        },
    )
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": "finance_salary_export",
        "risk_level": "medium",
        "erp_resource": "Salary Slip",
        "attachments": [attachment],
        "salary_metadata": {
            **salary_result.metadata,
            **email_metadata,
        },
    }


def _run_finance_compound_generation_chat(
    *,
    request: ChatRequest,
    current_user: dict,
    thread_id: str,
    run_id: str,
    started_ms: int,
    intent,
    react_decision,
    stream: bool,
) -> dict:
    try:
        skill_result = execute_skill(
            skill_id=FINANCE_COMPOUND_INTENT,
            payload={
                "message": request.message,
                "intent": intent,
                "requested_erp_resources": finance_compound_requested_resources(intent),
                "metadata": {
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "entrypoint": "chat_stream" if stream else "chat",
                },
            },
            current_user=current_user,
            source="chat_stream" if stream else "chat",
            react_decision=chat_react_decision_dict(react_decision),
        )
    except HTTPException as error:
        finish_run(
            run_id,
            status_value="failed",
            error_message=str(error.detail),
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": FINANCE_COMPOUND_INTENT,
                "react_decision": chat_react_decision_dict(react_decision),
            },
        )
        raise
    except ValueError as error:
        answer = str(error)
        if answer.startswith("缺少【") and answer.endswith("是否继续生成？"):
            finish_run(
                run_id,
                status_value="blocked",
                output_text=answer,
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "intent": "ask_clarification",
                    "source_intent": FINANCE_COMPOUND_INTENT,
                    "react_decision": chat_react_decision_dict(react_decision),
                },
            )
            return {
                "thread_id": thread_id,
                "answer": answer,
                "intent": "ask_clarification",
                "risk_level": "medium",
                "erp_references": [],
                "attachments": [],
                "approval_result": None,
                "react_decision": chat_react_decision_dict(react_decision),
            }
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": FINANCE_COMPOUND_INTENT,
                "react_decision": chat_react_decision_dict(react_decision),
            },
        )
        raise
    except Exception as error:
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": FINANCE_COMPOUND_INTENT,
                "react_decision": chat_react_decision_dict(react_decision),
            },
        )
        raise

    attachments = [_skill_attachment_to_chat_attachment(item) for item in skill_result.attachments]
    approval_result: dict[str, Any] | None = None
    automation = {
        "type": "skill",
        "skill_id": skill_result.skill_id,
        "status": skill_result.status,
        "generated_files": skill_result.metadata.get("generated_files"),
    }
    answer = skill_result.answer or ""
    if intent.wechat_requested and attachments:
        primary_attachment = attachments[0]
        attachment_meta = primary_attachment.get("metadata") if isinstance(primary_attachment.get("metadata"), dict) else {}
        artifact_id = str(attachment_meta.get("artifact_id") or "")
        if artifact_id:
            recipient_name = extract_wechat_recipient(request.message) or "待确认联系人"
            wechat_execution = build_enterprise_wechat_file_confirmation_task(
                artifact_id=artifact_id,
                artifact_filename=str(primary_attachment.get("filename") or artifact_id),
                recipient_name=recipient_name,
                current_user=current_user,
                source_message=request.message,
                source_workflow_id="finance_monthly_package_wechat_send",
                mime_type=str(primary_attachment.get("mime_type") or "application/octet-stream"),
                requires_sensitive_confirmation=True,
            )
            approval_result = {
                "status": wechat_execution.get("status"),
                "status_label": wechat_execution.get("status_label"),
                "requires_recipient_confirmation": True,
                "requires_sensitive_data_confirmation": True,
                "confirmation_card": wechat_execution.get("confirmation_card"),
            }
            automation = {
                **automation,
                "wechat_send": wechat_execution,
                "confirmation_card": wechat_execution.get("confirmation_card"),
                "artifact_id": artifact_id,
                "filename": primary_attachment.get("filename"),
                "download_path": attachment_meta.get("download_path"),
            }
            answer = (
                f"{answer}\n\n"
                "你要求通过企业微信发送，本次已准备发送确认卡。"
                "请先下载预览并确认敏感数据，确认后由后端发送，不附带正文说明。"
            ).strip()
    finish_run(
        run_id,
        status_value="succeeded",
        output_text=answer,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            **skill_result.metadata,
            "final_thread_id": thread_id,
            "attachment_count": len(attachments),
            "react_decision": chat_react_decision_dict(react_decision),
            "approval_result": approval_result,
        },
    )
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": skill_result.metadata.get("intent") or FINANCE_COMPOUND_INTENT,
        "risk_level": "high",
        "erp_references": [],
        "attachments": attachments,
        "approval_result": approval_result,
        "automation": automation,
        "react_decision": chat_react_decision_dict(react_decision),
    }


def _skill_attachment_to_chat_attachment(item: dict) -> dict:
    content = item.get("content")
    content_base64 = item.get("content_base64")
    if isinstance(content, bytes):
        size_bytes = len(content)
        content_base64 = base64.b64encode(content).decode("ascii")
    else:
        size_bytes = int(item.get("size_bytes") or 0)
    return {
        "type": item.get("type") or "excel_file",
        "filename": item.get("filename"),
        "mime_type": item.get("mime_type"),
        "size_bytes": size_bytes,
        "content_base64": content_base64,
        "metadata": item.get("metadata") or {},
    }


def _salary_export_attachment(result) -> dict:
    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {
        "type": "excel_file",
        "filename": result.filename,
        "mime_type": mime_type,
        "size_bytes": len(result.content),
        "content_base64": base64.b64encode(result.content).decode("ascii"),
        "metadata": result.metadata,
    }


def _attachment_without_content(item: dict) -> dict:
    return {
        key: value
        for key, value in item.items()
        if key != "content_base64"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


def build_public_llm_prompt(request: PublicLLMChatRequest) -> str:
    message = request.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    if len(message) > 2000:
        raise HTTPException(status_code=400, detail="消息不能超过 2000 个字符")

    history_lines = []
    for item in request.history[-12:]:
        content = item.content.strip()
        if not content:
            continue

        role_name = "用户" if item.role == "user" else "AI"
        history_lines.append(f"{role_name}：{content[:1000]}")

    history_text = "\n".join(history_lines) or "暂无历史对话"
    return f"""你是个人首页右下角的通用 AI 聊天助手。
你只进行普通大模型聊天，不检索知识库，不调用 RAG，不调用订单工具，不执行后台管理动作。
回答要自然、简洁、友好。

当前临时对话历史：
{history_text}

用户最新消息：
{message}
"""


@app.post("/public/llm/chat/stream")
def public_llm_chat_stream(request: PublicLLMChatRequest):
    prompt = build_public_llm_prompt(request)

    def event_generator():
        try:
            for chunk in chat_model.stream(prompt):
                text = chunk.content or ""
                if text:
                    yield format_sse("content", {"content": text})

            yield format_sse("done", {"message": "完成"})
        except Exception as error:
            yield format_sse("error", {"message": str(error)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/public/llm/chat", response_model=PublicLLMChatResponse)
def public_llm_chat(request: PublicLLMChatRequest):
    prompt = build_public_llm_prompt(request)
    answer = run_llm_chat(prompt)
    return {"answer": answer}


@app.post("/admin/mcp/documents/sync")
def sync_mcp_documents(
    request: McpDocumentSyncRequest,
    current_user: dict = Depends(require_admin),
):
    result = sync_document_system_to_rag(
        visibility=request.visibility,
        department=request.department,
        position_scope=request.position_scope,
        market_scope=request.market_scope,
        store_scope=request.store_scope,
        field_scope=request.field_scope,
        sensitivity_level=request.sensitivity_level,
    )

    write_audit_log(
        user_id=current_user["id"],
        action="mcp.documents.sync",
        resource_type="mcp",
        resource_id="document_system",
        metadata={
            "visibility": request.visibility,
            "department": request.department,
            "position_scope": request.position_scope,
            "market_scope": request.market_scope,
            "store_scope": request.store_scope,
            "field_scope": request.field_scope,
            "sensitivity_level": request.sensitivity_level,
            "synced_count": result["synced_count"],
            "username": current_user["username"],
        },
    )

    return result


@app.post("/admin/mcp/tickets")
def create_mcp_ticket(
    request: McpTicketCreateRequest,
    current_user: dict = Depends(require_admin),
):
    result = create_external_ticket(
        title=request.title,
        description=request.description,
        priority=request.priority,
        requester=current_user["id"],
        source="admin-api",
    )

    write_audit_log(
        user_id=current_user["id"],
        action="mcp.ticket.create",
        resource_type="ticket",
        resource_id=result.get("ticket_id"),
        metadata={
            "title": request.title,
            "priority": request.priority,
            "username": current_user["username"],
        },
    )

    return result


@app.get("/admin/mcp/tickets/{ticket_id}")
def get_mcp_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_admin),
):
    result = get_external_ticket(ticket_id)

    write_audit_log(
        user_id=current_user["id"],
        action="mcp.ticket.get",
        resource_type="ticket",
        resource_id=ticket_id,
        metadata={
            "found": result.get("found"),
            "username": current_user["username"],
        },
    )

    return result


def ensure_chat_app_enabled(current_user: dict) -> None:
    if current_user.get("role") == "admin":
        return

    position = current_user.get("position")
    app_id = f"{position}-chat-agent"
    if is_ai_app_allowed(current_user, app_id):
        return

    raise HTTPException(
        status_code=403,
        detail="AI 对话应用已被管理员禁用。",
    )


def can_export_salary_from_chat(current_user: dict) -> bool:
    return current_user.get("role") == "admin" or current_user.get("position") == "finance"


def chat_react_decision_dict(decision) -> dict:
    return decision.model_dump() if hasattr(decision, "model_dump") else dict(decision)


def direct_chat_result(
    *,
    thread_id: str,
    answer: str,
    intent: str,
    risk_level: str = "low",
    decision=None,
) -> dict:
    result = {
        "thread_id": thread_id,
        "answer": answer,
        "intent": intent,
        "risk_level": risk_level,
        "erp_references": [],
        "attachments": [],
        "approval_result": None,
    }
    if decision is not None:
        result["react_decision"] = chat_react_decision_dict(decision)
    return result


def _looks_like_generated_file_wechat_send_request(message: str) -> bool:
    text = " ".join((message or "").strip().split())
    lowered = text.lower()
    if not text:
        return False

    has_channel = any(keyword in lowered for keyword in ["企业微信", "企微", "微信", "wechat", "weixin"])
    has_send = any(keyword in lowered for keyword in ["发送", "发给", "传给", "转发", "send"])
    has_file_reference = any(
        keyword in lowered
        for keyword in [
            "刚刚",
            "刚才",
            "上面",
            "这个文件",
            "当前文件",
            "附件",
            "已生成",
            "生成好的",
            "生成的文件",
            "excel",
            "xlsx",
            "word",
            "docx",
            "文档",
            "表格",
        ]
    )
    return has_channel and has_send and has_file_reference


def _references_existing_generated_file(message: str) -> bool:
    lowered = (message or "").lower()
    return any(
        keyword in lowered
        for keyword in ["刚刚", "刚才", "上面", "这个文件", "当前文件", "附件", "已生成", "生成好的", "生成的文件"]
    )


def _should_handle_generated_file_wechat_send(message: str, *, salary_wechat_requested: bool) -> bool:
    if not _looks_like_generated_file_wechat_send_request(message):
        return False
    if salary_wechat_requested and not _references_existing_generated_file(message):
        return False
    return True


def _generated_file_requires_sensitive_confirmation(storage_reference: dict[str, Any]) -> bool:
    metadata = storage_reference.get("metadata") if isinstance(storage_reference.get("metadata"), dict) else {}
    text = " ".join(
        str(item or "")
        for item in [
            storage_reference.get("filename"),
            storage_reference.get("artifact_type"),
            storage_reference.get("app_id"),
            storage_reference.get("app_name"),
            storage_reference.get("run_type"),
            metadata.get("erp_resource"),
            metadata.get("provider_resource"),
            metadata.get("field_scope"),
            metadata.get("sensitivity_level"),
            metadata.get("source"),
        ]
    ).lower()
    sensitive_keywords = [
        "salary",
        "salary slip",
        "工资",
        "薪资",
        "应发",
        "实发",
        "财务",
        "finance",
        "reconciliation",
        "settlement",
        "invoice",
        "payment",
        "客户",
        "customer",
        "buyer",
        "phone",
        "mobile",
        "privacy",
        "confidential",
        "restricted",
    ]
    if any(keyword in text for keyword in sensitive_keywords):
        return True
    return any(
        key in metadata
        for key in [
            "gross_pay_total",
            "net_pay_total",
            "employee_count",
            "customer_id",
            "buyer_email",
            "phone",
            "mobile",
        ]
    )


def _generated_file_is_finance_sensitive(storage_reference: dict[str, Any]) -> bool:
    metadata = storage_reference.get("metadata") if isinstance(storage_reference.get("metadata"), dict) else {}
    text = " ".join(
        str(item or "")
        for item in [
            storage_reference.get("filename"),
            storage_reference.get("app_id"),
            storage_reference.get("app_name"),
            metadata.get("erp_resource"),
            metadata.get("provider_resource"),
        ]
    ).lower()
    return any(
        keyword in text
        for keyword in ["salary", "salary slip", "工资", "薪资", "财务", "finance", "settlement", "reconciliation"]
    )


def _artifact_type_from_filename(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith((".doc", ".docx")):
        return "word_file"
    return "excel_file"


def _attachment_from_generated_file_reference(storage_reference: dict[str, Any]) -> dict[str, Any]:
    filename = str(storage_reference.get("filename") or "生成文件")
    return {
        "type": str(storage_reference.get("artifact_type") or _artifact_type_from_filename(filename)),
        "filename": filename,
        "mime_type": str(storage_reference.get("mime_type") or "application/octet-stream"),
        "size_bytes": storage_reference.get("size_bytes") or 0,
        "metadata": {
            "artifact_id": storage_reference.get("id"),
            "download_path": f"/files/{storage_reference.get('id')}/download",
            "run_id": storage_reference.get("run_id"),
            "app_id": storage_reference.get("app_id"),
        },
    }


def _run_enterprise_wechat_generated_file_send_chat(
    *,
    request: ChatRequest,
    current_user: dict,
    thread_id: str,
    run_id: str,
    started_ms: int,
    stream: bool,
) -> dict:
    recipient_name = extract_wechat_recipient(request.message) or ""
    record_step(
        run_id=run_id,
        step_name="enterprise_wechat_generated_file_intent",
        step_order=1,
        status_value="succeeded",
        provider="rules",
        resource_type="thread",
        resource_id=thread_id,
        input_text=request.message,
        output_text=recipient_name or "待填写接收对象",
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": "enterprise_wechat_file_send",
            "recipient_name": recipient_name,
            "entrypoint": "chat_stream" if stream else "chat",
        },
    )

    step_started_ms = now_ms()
    storage_reference = get_latest_generated_file_for_thread(
        thread_id=thread_id,
        current_user=current_user,
        allowed_types={"excel_file", "word_file", "docx_file", "report_file"},
    )
    if storage_reference is None:
        answer = "当前会话没有找到可发送的 Excel/Word 文件，请先生成文件或上传文件。"
        record_step(
            run_id=run_id,
            step_name="enterprise_wechat_generated_file_lookup",
            step_order=2,
            status_value="blocked",
            provider="generated_file_service",
            resource_type="thread",
            resource_id=thread_id,
            input_text=request.message,
            output_text=answer,
            duration_ms=elapsed_ms(step_started_ms),
        )
        finish_run(
            run_id,
            status_value="blocked",
            output_text=answer,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": "enterprise_wechat_file_send",
                "reason": "no_generated_file",
            },
        )
        return {
            "thread_id": thread_id,
            "answer": answer,
            "intent": "enterprise_wechat_file_send",
            "risk_level": "medium",
            "attachments": [],
            "approval_result": None,
            "automation": None,
        }

    sensitive_required = _generated_file_requires_sensitive_confirmation(storage_reference)
    if (
        sensitive_required
        and _generated_file_is_finance_sensitive(storage_reference)
        and current_user.get("role") != "admin"
    ):
        if current_user.get("position") != "finance":
            finish_run(
                run_id,
                status_value="blocked",
                output_text="只有财务岗位或管理员可以发送工资、财务文件到企业微信。",
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "intent": "enterprise_wechat_file_send",
                    "reason": "finance_sensitive_permission_denied",
                    "artifact_id": storage_reference["id"],
                },
            )
            raise HTTPException(
                status_code=403,
                detail="只有财务岗位或管理员可以发送工资、财务文件到企业微信。",
            )
        if not is_ai_app_allowed(current_user, "automation-salary_wechat_send"):
            finish_run(
                run_id,
                status_value="blocked",
                output_text="工资表微信发送应用已被管理员禁用。",
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "intent": "enterprise_wechat_file_send",
                    "reason": "salary_wechat_app_disabled",
                    "artifact_id": storage_reference["id"],
                },
            )
            raise HTTPException(
                status_code=403,
                detail="工资表微信发送应用已被管理员禁用。",
            )

    attachment = _attachment_from_generated_file_reference(storage_reference)
    finance_sensitive = sensitive_required and _generated_file_is_finance_sensitive(storage_reference)
    workflow_id = "finance_salary_wechat_send" if finance_sensitive else "enterprise_wechat_file_send"
    wechat_execution = build_enterprise_wechat_file_confirmation_task(
        artifact_id=str(storage_reference["id"]),
        artifact_filename=str(storage_reference.get("filename") or attachment["filename"]),
        recipient_name=recipient_name,
        current_user=current_user,
        source_message=request.message,
        source_workflow_id=workflow_id,
        mime_type=str(storage_reference.get("mime_type") or attachment["mime_type"]),
        requires_sensitive_confirmation=sensitive_required,
    )
    status_value = str(wechat_execution.get("status") or "waiting_wechat_confirmation")
    status_label = str(wechat_execution.get("status_label") or "等待确认")
    record_step(
        run_id=run_id,
        step_name="enterprise_wechat_generated_file_confirmation_required",
        step_order=2,
        status_value=run_record_status_for_salary_wechat(status_value),
        provider=str(wechat_execution.get("executor_type") or "confirmation_required"),
        resource_type="enterprise_wechat",
        resource_id=recipient_name or "manual_recipient",
        input_text={
            "artifact_id": storage_reference["id"],
            "filename": storage_reference.get("filename"),
            "recipient_name": recipient_name,
        },
        output_text=wechat_execution.get("message"),
        duration_ms=elapsed_ms(step_started_ms),
        metadata=wechat_execution,
    )

    filename = str(storage_reference.get("filename") or attachment["filename"])
    if recipient_name:
        answer = (
            f"已找到当前会话最近生成的文件：{filename}。\n"
            f"准备通过企业微信发送给“{recipient_name}”。\n"
            "请在下方确认接收对象和文件预览；确认后由后端发送，不附带正文说明。"
        )
    else:
        answer = (
            f"已找到当前会话最近生成的文件：{filename}。\n"
            "还没有识别到企业微信接收对象，请在下方选择候选对象，"
            "或手动输入 userid / chat_id / department_id 后确认发送。"
        )

    finish_run(
        run_id,
        status_value=run_record_status_for_salary_wechat(status_value),
        output_text=answer,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": "enterprise_wechat_file_send",
            "risk_level": "high" if sensitive_required else "medium",
            "business_status": status_value,
            "business_status_label": status_label,
            "artifact_id": storage_reference["id"],
            "filename": filename,
            "recipient_name": recipient_name,
            "requires_sensitive_confirmation": sensitive_required,
            "wechat_send": wechat_execution,
        },
    )
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": "enterprise_wechat_file_send",
        "risk_level": "high" if sensitive_required else "medium",
        "attachments": [attachment],
        "approval_result": {
            "status": status_value,
            "status_label": status_label,
            "requires_recipient_confirmation": True,
            "requires_sensitive_data_confirmation": sensitive_required,
            "confirmation_card": wechat_execution.get("confirmation_card"),
        },
        "automation": {
            "type": "enterprise_wechat_file_send",
            "status": status_value,
            "status_label": status_label,
            "workflow_id": workflow_id,
            "recipient_name": recipient_name,
            "source_message": request.message,
            "artifact_id": storage_reference["id"],
            "filename": filename,
            "download_path": f"/files/{storage_reference['id']}/download",
            "wechat_send": wechat_execution,
            "confirmation_card": wechat_execution.get("confirmation_card"),
        },
    }


def _run_finance_salary_wechat_send_chat(
    *,
    request: ChatRequest,
    current_user: dict,
    thread_id: str,
    run_id: str,
    started_ms: int,
    stream: bool,
) -> dict:
    intent = recognize_salary_wechat_send_intent(request.message)
    plan = build_salary_wechat_plan(intent)
    record_step(
        run_id=run_id,
        step_name="finance_salary_wechat_plan",
        step_order=1,
        status_value="succeeded" if not intent.missing_fields else "blocked",
        provider="rules",
        resource_type="automation",
        resource_id="finance_salary_wechat_send",
        input_text=request.message,
        output_text=plan,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": intent.intent,
            "confidence": intent.confidence,
            "recipient_name": intent.recipient_name,
            "missing_fields": intent.missing_fields,
            "entrypoint": "chat_stream" if stream else "chat",
        },
    )

    missing_text = "、".join(intent.missing_fields)
    if missing_text:
        answer = (
            "我先整理好了工资表微信发送计划，但还不能执行。\n"
            f"还需要补充：{missing_text}。\n"
            f"计划目标：{plan['summary']}\n"
            "请补充企业微信接收对象。文件生成完成后，我会在聊天窗口让你确认一次。"
        )
        business_status = "waiting_confirmation"
        business_status_label = "等待确认"
        finish_run(
            run_id,
            status_value="blocked",
            output_text=answer,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": "finance_salary_wechat_send",
                "risk_level": "high",
                "requires_confirmation": True,
                "missing_fields": intent.missing_fields,
                "recipient_name": intent.recipient_name,
                "business_status": business_status,
                "business_status_label": business_status_label,
                "execution_plan": plan,
            },
        )
        return {
            "thread_id": thread_id,
            "answer": answer,
            "intent": "finance_salary_wechat_send",
            "risk_level": "high",
            "attachments": [],
            "approval_result": {
                "status": business_status,
                "status_label": business_status_label,
                "requires_recipient_confirmation": True,
                "requires_sensitive_data_confirmation": True,
            },
            "automation": {
                "type": "finance_salary_wechat_send",
                "status": business_status,
                "status_label": business_status_label,
                "workflow_id": "finance_salary_wechat_send",
                "execution_plan": plan,
                "recipient_name": intent.recipient_name,
                "missing_fields": intent.missing_fields,
                "source_message": request.message,
            },
        }

    step_started_ms = now_ms()
    try:
        salary_result = export_salary_workbook_from_erp(
            message=request.message,
            current_user=current_user,
            intent=intent.salary_intent,
        )
    except ValueError as error:
        record_step(
            run_id=run_id,
            step_name="finance_salary_wechat_excel_export",
            step_order=2,
            status_value="failed",
            provider="erp_provider",
            resource_type="erp",
            resource_id="Salary Slip",
            input_text=request.message,
            error_message=error,
            duration_ms=elapsed_ms(step_started_ms),
            metadata={
                "period_label": intent.salary_intent.period_label,
                "recipient_name": intent.recipient_name,
            },
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    attachment = {
        "type": "excel_file",
        "filename": salary_result.filename,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "size_bytes": len(salary_result.content),
        "metadata": salary_result.metadata,
    }
    artifact_id = save_generated_file(
        run_id=run_id,
        content=salary_result.content,
        artifact_type="excel_file",
        mime_type=attachment["mime_type"],
        filename=salary_result.filename,
        current_user=current_user,
        metadata=salary_result.metadata,
    )
    if artifact_id:
        attachment["metadata"] = {
            **attachment["metadata"],
            "artifact_id": artifact_id,
            "download_path": f"/files/{artifact_id}/download",
        }
    record_step(
        run_id=run_id,
        step_name="finance_salary_wechat_excel_export",
        step_order=2,
        status_value="succeeded",
        provider=salary_result.provider,
        resource_type="erp",
        resource_id="Salary Slip",
        input_text=request.message,
        output_text=salary_result.filename,
        duration_ms=elapsed_ms(step_started_ms),
        metadata={
            **salary_result.metadata,
            "artifact_id": artifact_id,
        },
    )

    dispatch = prepare_salary_wechat_dispatch(
        intent=intent,
        salary_result=salary_result,
        current_user=current_user,
        source="chat_stream" if stream else "chat",
    )
    wechat_execution = build_wechat_prepare_confirmation_task(
        dispatch=dispatch,
        artifact_id=artifact_id,
        artifact_filename=salary_result.filename,
        current_user=current_user,
    )
    business_status = str(wechat_execution.get("status") or "waiting_wechat_confirmation")
    business_status_label = str(wechat_execution.get("status_label") or "等待确认")
    record_step(
        run_id=run_id,
        step_name="enterprise_wechat_confirmation_required",
        step_order=3,
        status_value=run_record_status_for_salary_wechat(business_status),
        provider=str(wechat_execution.get("executor_type") or "confirmation_required"),
        resource_type="enterprise_wechat",
        resource_id=str(intent.recipient_name or ""),
        input_text={
            "recipient_name": intent.recipient_name,
            "artifact_id": artifact_id,
        },
        output_text=wechat_execution.get("message"),
        duration_ms=0,
        metadata=wechat_execution,
    )

    if business_status == "waiting_recipient_selection":
        answer = (
            f"已生成 {salary_result.intent.period_label} 员工工资表 Excel，但企业微信接收对象还需要你选择。\n"
            f"文件：{salary_result.filename}\n"
            f"本次共 {len(salary_result.items)} 名员工，应发合计 "
            f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
            f"{salary_result.metadata['net_pay_total']:.2f}。\n"
            "请在下方候选列表里点选正确的人、群聊或部门，再确认发送。"
        )
    else:
        answer = (
            f"已生成 {salary_result.intent.period_label} 员工工资表 Excel，并准备通过企业微信发送给“{intent.recipient_name}”。\n"
            f"本次共 {len(salary_result.items)} 名员工，应发合计 "
            f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
            f"{salary_result.metadata['net_pay_total']:.2f}。\n"
            f"文件：{salary_result.filename}\n"
            "请在下方确认企业微信接收对象和敏感数据。确认后由后端发送文件，不附带正文说明。"
        )
    finish_run(
        run_id,
        status_value=run_record_status_for_salary_wechat(business_status),
        output_text=answer,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": "finance_salary_wechat_send",
            "risk_level": "high",
            "requires_confirmation": True,
            "missing_fields": intent.missing_fields,
            "recipient_name": intent.recipient_name,
            "business_status": business_status,
            "business_status_label": business_status_label,
            "artifact_id": artifact_id,
            "execution_plan": plan,
            "wechat_send": wechat_execution,
        },
    )
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": "finance_salary_wechat_send",
        "risk_level": "high",
        "attachments": [attachment],
        "approval_result": {
            "status": business_status,
            "status_label": business_status_label,
            "requires_recipient_confirmation": True,
            "requires_sensitive_data_confirmation": True,
            "confirmation_card": wechat_execution.get("confirmation_card"),
        },
        "automation": {
            "type": "finance_salary_wechat_send",
            "status": business_status,
            "status_label": business_status_label,
            "workflow_id": "finance_salary_wechat_send",
            "execution_plan": plan,
            "recipient_name": intent.recipient_name,
            "missing_fields": intent.missing_fields,
            "source_message": request.message,
            "artifact_id": artifact_id,
            "filename": salary_result.filename,
            "download_path": f"/files/{artifact_id}/download" if artifact_id else None,
            "wechat_send": wechat_execution,
            "confirmation_card": wechat_execution.get("confirmation_card"),
        },
    }


def react_direct_result_for_decision(decision, current_user: dict, thread_id: str) -> dict | None:
    denial = permission_denial_for_decision(decision, current_user)
    if denial:
        return direct_chat_result(
            thread_id=thread_id,
            answer=denial,
            intent="permission_denied",
            risk_level="blocked",
            decision=decision,
        )

    if decision.action == "ask_clarification":
        return direct_chat_result(
            thread_id=thread_id,
            answer=decision.clarification_question or "请再说明具体要处理什么业务。",
            intent="ask_clarification",
            risk_level="low",
            decision=decision,
        )

    return None


def automation_route_from_react_decision(decision) -> dict | None:
    skill = skill_for_react_action(decision.action)
    if skill and skill.skill_id in {"operations_listing", "customer_reply"}:
        route = {
            "intent": decision.action,
            "position": skill.position,
            "skill_id": skill.skill_id,
            "flow_key": skill.flow_key,
            "label": skill.name,
        }
        if skill.skill_id == "operations_listing":
            route["workflow_id"] = "operations_listing_launch"
        return route
    return None


def record_react_decision_step(run_id: str, decision, message: str, thread_id: str, started_ms: int) -> None:
    record_step(
        run_id=run_id,
        step_name="react.intent_planning",
        step_order=1,
        status_value="succeeded",
        provider="llm_react_planner",
        resource_type="thread",
        resource_id=thread_id,
        input_text=message,
        output_text=decision.action,
        duration_ms=elapsed_ms(started_ms),
        metadata=chat_react_decision_dict(decision),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest,current_user: dict = Depends(get_current_user),):
    ensure_chat_app_enabled(current_user)
    ensure_chat_allowed_for_position(current_user, request.message)
    salary_export_intent = recognize_salary_export_intent(request.message)
    finance_compound_intent = recognize_finance_compound_intent(request.message)
    salary_wechat_intent = recognize_salary_wechat_send_intent(request.message)
    salary_wechat_requested = (
        salary_wechat_intent.salary_intent.intent == "finance_salary_export"
        and "微信" in salary_wechat_intent.matched_keywords
    )
    if (
        current_user.get("role") != "admin"
        and current_user.get("position") == "finance"
        and salary_wechat_requested
        and not is_ai_app_allowed(current_user, "automation-salary_wechat_send")
    ):
        raise HTTPException(
            status_code=403,
            detail="工资表微信发送应用已被管理员禁用。",
        )
    if (
        current_user.get("role") != "admin"
        and current_user.get("position") == "finance"
        and salary_export_intent.intent == "finance_salary_export"
        and not salary_wechat_requested
        and not is_ai_app_allowed(current_user, "automation-salary_summary")
    ):
        raise HTTPException(
            status_code=403,
            detail="统计工资应用已被管理员禁用。",
        )
    thread_id = resolve_chat_thread_id(
        request.thread_id,
        current_user,
        title=request.message[:50],
    )
    context_bundle = build_context_bundle(
        thread_id=thread_id,
        user_id=current_user["id"],
    )

    save_chat_message(
        thread_id=thread_id,
        user_id=current_user["id"],
        role="user",
        content=request.message,
    )
    started_ms = now_ms()
    position = current_user.get("position")
    flow_reference = (
        resolve_flow_execution_reference(
            flow_key=f"automation:{position}:chat-agent",
            current_user=current_user,
            execution_source="chat",
        )
        if is_valid_position(position)
        else None
    )
    run_id = start_run(
        run_type="chat",
        app_id=f"{position or 'admin'}-chat-agent",
        app_name=f"{position_label_for_run(position)} AI 对话",
        entrypoint="/chat",
        current_user=current_user,
        thread_id=thread_id,
        resource_type="thread",
        resource_id=thread_id,
        flow_reference=flow_reference,
        input_text=request.message,
        metadata={
            "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
            "recent_message_count": len(context_bundle.get("recent_messages", [])),
        },
    )

    agent_route = classify_agent_task(request.message, current_user)
    if agent_route.requires_plan_execute and agent_route.workflow_id == PLAN_EXECUTE_WORKFLOW_ID:
        record_step(
            run_id=run_id,
            step_name="agent.task_classifier",
            step_order=1,
            status_value="succeeded",
            provider="rules",
            resource_type="automation",
            resource_id=agent_route.workflow_id,
            input_text=request.message,
            output_text=agent_route.intent,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "mode": agent_route.mode,
                "reason": agent_route.reason,
                "confidence": agent_route.confidence,
                "estimated_step_count": agent_route.estimated_step_count,
            },
        )
        try:
            result = execute_finance_monthly_package_wechat(
                message=request.message,
                current_user=current_user,
                thread_id=thread_id,
                parent_run_id=run_id,
                source="chat",
            )
        except ValueError as error:
            finish_run(
                run_id,
                status_value="failed",
                error_message=error,
                duration_ms=elapsed_ms(started_ms),
                metadata={"intent": agent_route.intent, "mode": agent_route.mode},
            )
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            finish_run(
                run_id,
                status_value="failed",
                error_message=error,
                duration_ms=elapsed_ms(started_ms),
                metadata={"intent": agent_route.intent, "mode": agent_route.mode},
            )
            raise

        save_chat_message(
            thread_id=thread_id,
            user_id=current_user["id"],
            role="assistant",
            content=result.get("answer", ""),
            metadata={
                "intent": result.get("intent"),
                "risk_level": result.get("risk_level"),
                "position": current_user.get("position"),
                "attachments": [
                    _attachment_without_content(item)
                    for item in attachments_from_result(result)
                ],
                "approval_result": result.get("approval_result"),
                "automation": result.get("automation"),
            },
        )
        update_context_after_turn(
            thread_id=thread_id,
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=result,
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=result.get("answer", ""),
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": result.get("intent"),
                "risk_level": result.get("risk_level"),
                "mode": agent_route.mode,
                "child_run_id": (result.get("automation") or {}).get("run_id") if isinstance(result.get("automation"), dict) else None,
            },
        )
        write_audit_log(
            user_id=current_user["id"],
            action="chat.agent_plan_execute",
            resource_type="thread",
            resource_id=thread_id,
            metadata={
                "intent": result.get("intent"),
                "position": current_user.get("position"),
                "workflow_id": agent_route.workflow_id,
                "child_run_id": (result.get("automation") or {}).get("run_id") if isinstance(result.get("automation"), dict) else None,
            },
        )
        return {
            "thread_id": thread_id,
            "answer": result.get("answer", ""),
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "erp_references": [],
            "attachments": attachments_from_result(result),
            "approval_result": result.get("approval_result"),
            "automation": result.get("automation"),
        }

    if _should_handle_generated_file_wechat_send(request.message, salary_wechat_requested=salary_wechat_requested):
        result = _run_enterprise_wechat_generated_file_send_chat(
            request=request,
            current_user=current_user,
            thread_id=thread_id,
            run_id=run_id,
            started_ms=started_ms,
            stream=False,
        )
        _save_assistant_automation_message(
            result=result,
            current_user=current_user,
        )
        update_context_after_turn(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=result,
        )
        write_audit_log(
            user_id=current_user["id"],
            action="chat.enterprise_wechat_file_send_prepare",
            resource_type="thread",
            resource_id=result.get("thread_id", thread_id),
            metadata={
                "intent": result.get("intent"),
                "position": current_user.get("position"),
                "artifact_id": (result.get("automation") or {}).get("artifact_id")
                if isinstance(result.get("automation"), dict)
                else None,
                "recipient_name": (result.get("automation") or {}).get("recipient_name")
                if isinstance(result.get("automation"), dict)
                else None,
            },
        )
        return {
            "thread_id": result.get("thread_id", thread_id),
            "answer": result.get("answer", ""),
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "erp_references": [],
            "attachments": attachments_from_result(result),
            "approval_result": result.get("approval_result"),
            "automation": result.get("automation"),
        }

    react_decision = decide_chat_action(request.message, current_user)
    record_react_decision_step(run_id, react_decision, request.message, thread_id, started_ms)
    direct_result = react_direct_result_for_decision(react_decision, current_user, thread_id)
    if direct_result:
        save_chat_message(
            thread_id=thread_id,
            user_id=current_user["id"],
            role="assistant",
            content=direct_result["answer"],
            metadata={
                "intent": direct_result["intent"],
                "risk_level": direct_result["risk_level"],
                "position": current_user.get("position"),
                "react_decision": direct_result.get("react_decision"),
            },
        )
        update_context_after_turn(
            thread_id=thread_id,
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=direct_result,
        )
        finish_run(
            run_id,
            status_value="blocked" if direct_result["risk_level"] == "blocked" else "succeeded",
            output_text=direct_result["answer"],
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": direct_result["intent"],
                "risk_level": direct_result["risk_level"],
                "react_decision": direct_result.get("react_decision"),
            },
        )
        write_audit_log(
            user_id=current_user["id"],
            action="chat.react_direct",
            resource_type="thread",
            resource_id=thread_id,
            metadata={
                "intent": direct_result["intent"],
                "position": current_user.get("position"),
                "react_decision": direct_result.get("react_decision"),
            },
        )
        return direct_result

    if (
        react_decision.action == FINANCE_COMPOUND_INTENT
        and should_handle_finance_compound_generation(finance_compound_intent)
    ):
        try:
            result = _run_finance_compound_generation_chat(
                request=request,
                current_user=current_user,
                thread_id=thread_id,
                run_id=run_id,
                started_ms=started_ms,
                intent=finance_compound_intent,
                react_decision=react_decision,
                stream=False,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        assistant_metadata = {
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "position": current_user.get("position"),
            "attachments": [
                _attachment_without_content(item)
                for item in attachments_from_result(result)
            ],
            "approval_result": result.get("approval_result"),
            "automation": result.get("automation"),
            "react_decision": result.get("react_decision"),
        }
        save_chat_message(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            role="assistant",
            content=result.get("answer", ""),
            metadata=assistant_metadata,
        )
        update_context_after_turn(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=result,
        )
        write_audit_log(
            user_id=current_user["id"],
            action="chat.finance_compound_report_generation",
            resource_type="thread",
            resource_id=result.get("thread_id", thread_id),
            metadata={
                "intent": result.get("intent"),
                "position": current_user.get("position"),
                "attachment_count": len(attachments_from_result(result)),
                "period_label": finance_compound_intent.period_label,
                "outputs": list(finance_compound_intent.outputs),
            },
        )
        return {
            "thread_id": result.get("thread_id", thread_id),
            "answer": result.get("answer", ""),
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "erp_references": [],
            "attachments": attachments_from_result(result),
            "approval_result": result.get("approval_result"),
            "automation": result.get("automation"),
        }

    if (
        react_decision.action == "finance_salary_export"
        and current_user.get("role") != "admin"
        and current_user.get("position") == "finance"
        and not is_ai_app_allowed(current_user, "automation-salary_summary")
    ):
        raise HTTPException(
            status_code=403,
            detail="统计工资应用已被管理员禁用。",
        )

    if (
        can_export_salary_from_chat(current_user)
        and react_decision.action == "finance_salary_export"
    ):
        try:
            result = _run_finance_salary_export_chat(
                request=request,
                current_user=current_user,
                thread_id=thread_id,
                run_id=run_id,
                started_ms=started_ms,
                intent=salary_export_intent,
                stream=False,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error
        assistant_metadata = {
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "position": current_user.get("position"),
            "erp_resource": result.get("erp_resource"),
            "attachments": [
                _attachment_without_content(item)
                for item in attachments_from_result(result)
            ],
        }
        save_chat_message(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            role="assistant",
            content=result.get("answer", ""),
            metadata=assistant_metadata,
        )
        update_context_after_turn(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=result,
        )
        write_audit_log(
            user_id=current_user["id"],
            action="chat.finance_salary_export",
            resource_type="thread",
            resource_id=result.get("thread_id", thread_id),
            metadata={
                "intent": result.get("intent"),
                "position": current_user.get("position"),
                "attachment_count": len(attachments_from_result(result)),
                "period_label": salary_export_intent.period_label,
            },
        )
        return {
            "thread_id": result.get("thread_id", thread_id),
            "answer": result.get("answer", ""),
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "erp_references": [],
            "attachments": attachments_from_result(result),
            "approval_result": None,
        }

    if react_decision.action == "finance_salary_wechat_send":
        if (
            current_user.get("role") != "admin"
            and not is_ai_app_allowed(current_user, "automation-salary_wechat_send")
        ):
            raise HTTPException(
                status_code=403,
                detail="工资表微信发送应用已被管理员禁用。",
            )
        try:
            result = _run_finance_salary_wechat_send_chat(
                request=request,
                current_user=current_user,
                thread_id=thread_id,
                run_id=run_id,
                started_ms=started_ms,
                stream=False,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        assistant_metadata = {
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "position": current_user.get("position"),
            "attachments": [
                _attachment_without_content(item)
                for item in attachments_from_result(result)
            ],
            "approval_result": result.get("approval_result"),
            "automation": result.get("automation"),
        }
        save_chat_message(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            role="assistant",
            content=result.get("answer", ""),
            metadata=assistant_metadata,
        )
        update_context_after_turn(
            thread_id=result.get("thread_id", thread_id),
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=result,
        )
        return {
            "thread_id": result.get("thread_id", thread_id),
            "answer": result.get("answer", ""),
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "erp_references": [],
            "attachments": attachments_from_result(result),
            "approval_result": result.get("approval_result"),
            "automation": result.get("automation"),
        }

    try:
        step_started_ms = now_ms()
        automation_result = run_chat_automation(
            message=request.message,
            current_user=current_user,
            thread_id=thread_id,
            forced_route=automation_route_from_react_decision(react_decision),
            react_decision=chat_react_decision_dict(react_decision),
            attachments=request.attachments,
            source="chat",
        )
    except Exception as error:
        record_step(
            run_id=run_id,
            step_name="chat_automation.dispatch",
            step_order=1,
            status_value="failed",
            provider="chat_automation_dispatcher",
            resource_type="thread",
            resource_id=thread_id,
            input_text=request.message,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    if automation_result:
        _finish_chat_automation_run(
            run_id=run_id,
            result=automation_result,
            request=request,
            started_ms=started_ms,
            step_started_ms=step_started_ms,
            current_user=current_user,
            context_bundle=context_bundle,
            action="chat.automation_dispatch",
        )
        _save_assistant_automation_message(
            result=automation_result,
            current_user=current_user,
        )
        update_context_after_turn(
            thread_id=automation_result.get("thread_id", thread_id),
            user_id=current_user["id"],
            user_message=request.message,
            graph_result=automation_result,
        )
        return {
            "thread_id": automation_result.get("thread_id", thread_id),
            "answer": automation_result.get("answer", ""),
            "intent": automation_result.get("intent"),
            "risk_level": automation_result.get("risk_level"),
            "erp_references": automation_result.get("erp_references") or [],
            "attachments": attachments_from_result(automation_result),
            "platform_draft": platform_draft_from_result(automation_result),
            "approval_result": automation_result.get("approval_result"),
        }

    graph_input = {
        "thread_id": thread_id,
        "user_input": request.message,
        "user_id": current_user["id"],
        "role": current_user["role"],
        "department": current_user.get("department"),
        "position": current_user.get("position"),
        "username": current_user.get("username"),
        "context": context_bundle,
        "forced_intent": forced_graph_intent_for_action(react_decision.action),
        "react_decision": chat_react_decision_dict(react_decision),
    }
    try:
        step_started_ms = now_ms()
        result = graph.invoke(graph_input)
        erp_references = erp_references_from_result(result)
        record_step(
            run_id=run_id,
            step_name="graph.invoke",
            step_order=1,
            status_value="succeeded",
            provider="langgraph",
            resource_type="thread",
            resource_id=result.get("thread_id", thread_id),
            input_text=request.message,
            output_text=result.get("answer", ""),
            duration_ms=elapsed_ms(step_started_ms),
            metadata={
                "intent": result.get("intent"),
                "risk_level": result.get("risk_level"),
                "erp_resource": result.get("erp_resource"),
                "erp_reference_count": len(erp_references),
            },
        )
        for index, reference in enumerate(erp_references[:10], start=1):
            record_artifact(
                run_id=run_id,
                artifact_type="erp_reference",
                name=str(reference.get("title") or reference.get("record_id") or "ERP 引用"),
                external_ref=str(reference.get("record_id") or ""),
                metadata={
                    "resource": reference.get("resource"),
                    "resource_label": reference.get("resource_label"),
                    "provider": reference.get("provider"),
                    "provider_resource": reference.get("provider_resource"),
                    "reference_order": index,
                },
            )
        record_artifact(
            run_id=run_id,
            artifact_type="chat_thread",
            name=result.get("thread_id", thread_id),
            external_ref=result.get("thread_id", thread_id),
            metadata={
                "intent": result.get("intent"),
                "risk_level": result.get("risk_level"),
            },
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=result.get("answer", ""),
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": result.get("intent"),
                "risk_level": result.get("risk_level"),
                "erp_resource": result.get("erp_resource"),
                "erp_reference_count": len(erp_references),
            },
        )
    except Exception as error:
        record_step(
            run_id=run_id,
            step_name="graph.invoke",
            step_order=1,
            status_value="failed",
            provider="langgraph",
            resource_type="thread",
            resource_id=thread_id,
            input_text=request.message,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    erp_references = erp_references_from_result(result)
    save_chat_message(
        thread_id=result.get("thread_id", thread_id),
        user_id=current_user["id"],
        role="assistant",
        content=result.get("answer", ""),
        metadata={
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "order_no": result.get("order_no"),
            "position": current_user.get("position"),
            "erp_resource": result.get("erp_resource"),
            "erp_status": (result.get("erp_result") or {}).get("status")
            if isinstance(result.get("erp_result"), dict)
            else None,
            "erp_references": erp_references,
            "approval_result": result.get("approval_result"),
        },
    )
    update_context_after_turn(
        thread_id=result.get("thread_id", thread_id),
        user_id=current_user["id"],
        user_message=request.message,
        graph_result=result,
    )

    write_audit_log(
        user_id=current_user["id"],
        action="chat.invoke",
        resource_type="thread",
        resource_id=result.get("thread_id", thread_id),
        metadata={
            "intent": result.get("intent"),
            "risk_level": result.get("risk_level"),
            "order_no": result.get("order_no"),
            "position": current_user.get("position"),
            "erp_resource": result.get("erp_resource"),
            "erp_reference_count": len(erp_references),
            "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
            "recent_message_count": len(context_bundle.get("recent_messages", [])),
        },
    )

    return {
        "thread_id": result.get("thread_id", thread_id),
        "answer": result.get("answer", ""),
        "intent": result.get("intent"),
        "risk_level": result.get("risk_level"),
        "erp_references": erp_references,
        "attachments": attachments_from_result(result),
        "approval_result": result.get("approval_result"),
    }


@app.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    ensure_chat_app_enabled(current_user)
    ensure_chat_allowed_for_position(current_user, request.message)
    salary_export_intent = recognize_salary_export_intent(request.message)
    finance_compound_intent = recognize_finance_compound_intent(request.message)
    salary_wechat_intent = recognize_salary_wechat_send_intent(request.message)
    salary_wechat_requested = (
        salary_wechat_intent.salary_intent.intent == "finance_salary_export"
        and "微信" in salary_wechat_intent.matched_keywords
    )
    if (
        current_user.get("role") != "admin"
        and current_user.get("position") == "finance"
        and salary_export_intent.intent == "finance_salary_export"
        and not salary_wechat_requested
        and not is_ai_app_allowed(current_user, "automation-salary_summary")
    ):
        raise HTTPException(
            status_code=403,
            detail="统计工资应用已被管理员禁用。",
        )
    thread_id = resolve_chat_thread_id(
        request.thread_id,
        current_user,
        title=request.message[:50],
    )
    context_bundle = build_context_bundle(
        thread_id=thread_id,
        user_id=current_user["id"],
    )

    save_chat_message(
        thread_id=thread_id,
        user_id=current_user["id"],
        role="user",
        content=request.message,
        metadata={
            "entrypoint": "chat_stream",
        },
    )

    graph_input = {
        "thread_id": thread_id,
        "user_input": request.message,
        "user_id": current_user["id"],
        "role": current_user["role"],
        "department": current_user.get("department"),
        "position": current_user.get("position"),
        "username": current_user.get("username"),
        "context": context_bundle,
    }
    started_ms = now_ms()
    position = current_user.get("position")
    flow_reference = (
        resolve_flow_execution_reference(
            flow_key=f"automation:{position}:chat-agent",
            current_user=current_user,
            execution_source="chat_stream",
        )
        if is_valid_position(position)
        else None
    )
    run_id = start_run(
        run_type="chat_stream",
        app_id=f"{position or 'admin'}-chat-agent",
        app_name=f"{position_label_for_run(position)} AI 对话",
        entrypoint="/chat/stream",
        current_user=current_user,
        thread_id=thread_id,
        resource_type="thread",
        resource_id=thread_id,
        flow_reference=flow_reference,
        input_text=request.message,
        metadata={
            "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
            "recent_message_count": len(context_bundle.get("recent_messages", [])),
        },
    )
    agent_route = classify_agent_task(request.message, current_user)
    react_decision = None if agent_route.requires_plan_execute else decide_chat_action(request.message, current_user)
    if react_decision is not None:
        graph_input.update({
            "forced_intent": forced_graph_intent_for_action(react_decision.action),
            "react_decision": chat_react_decision_dict(react_decision),
        })

    def event_generator():
        result_state = dict(graph_input)
        step_order = 1

        try:
            yield format_sse(
                "start",
                {
                    "thread_id": thread_id,
                    "message": "开始处理用户消息",
                },
            )
            yield format_business_progress_sse(
                thread_id=thread_id,
                workflow_id="chat_react",
                step_key="understanding",
                label="正在理解你的需求",
            )

            if agent_route.requires_plan_execute and agent_route.workflow_id == PLAN_EXECUTE_WORKFLOW_ID:
                plan = build_finance_monthly_package_plan(request.message)
                record_step(
                    run_id=run_id,
                    step_name="agent.task_classifier",
                    step_order=step_order,
                    status_value="succeeded",
                    provider="rules",
                    resource_type="automation",
                    resource_id=agent_route.workflow_id,
                    input_text=request.message,
                    output_text=agent_route.intent,
                    duration_ms=elapsed_ms(started_ms),
                    metadata={
                        "mode": agent_route.mode,
                        "reason": agent_route.reason,
                        "confidence": agent_route.confidence,
                        "estimated_step_count": agent_route.estimated_step_count,
                        "plan": plan,
                    },
                )
                progress_queue: Queue[dict[str, Any]] = Queue()

                def enqueue_progress(progress: dict[str, Any]) -> None:
                    progress_queue.put({"kind": "progress", "payload": progress})

                def run_plan_executor() -> None:
                    try:
                        result = execute_finance_monthly_package_wechat(
                            message=request.message,
                            current_user=current_user,
                            thread_id=thread_id,
                            parent_run_id=run_id,
                            source="chat_stream",
                            progress_callback=enqueue_progress,
                        )
                    except Exception as error:
                        progress_queue.put({"kind": "error", "error": error})
                    else:
                        progress_queue.put({"kind": "result", "result": result})

                worker = Thread(target=run_plan_executor, daemon=True)
                worker.start()
                result_state = None
                while result_state is None:
                    try:
                        progress_event = progress_queue.get(timeout=0.2)
                    except Empty:
                        if not worker.is_alive():
                            raise RuntimeError("复杂任务执行线程已结束，但没有返回执行结果。")
                        continue

                    if progress_event.get("kind") == "progress":
                        payload = progress_event.get("payload") or {}
                        yield format_business_progress_sse(
                            thread_id=thread_id,
                            workflow_id=str(payload.get("workflow_id") or PLAN_EXECUTE_WORKFLOW_ID),
                            step_key=str(payload.get("step_key") or "running"),
                            label=str(payload.get("label") or "正在执行复杂任务"),
                            status_value=str(payload.get("status") or "running"),
                            detail=payload.get("detail") if isinstance(payload.get("detail"), str) else None,
                            data=payload.get("data") if isinstance(payload.get("data"), dict) else {},
                        )
                        continue

                    if progress_event.get("kind") == "error":
                        raise progress_event["error"]

                    if progress_event.get("kind") == "result":
                        result_state = progress_event.get("result") or {}

                final_thread_id = result_state.get("thread_id", thread_id)
                answer = result_state.get("answer", "")
                attachments = attachments_from_result(result_state)
                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": final_thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                save_chat_message(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    role="assistant",
                    content=answer,
                    metadata={
                        "entrypoint": "chat_stream",
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "position": current_user.get("position"),
                        "attachments": [
                            _attachment_without_content(item)
                            for item in attachments
                        ],
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                    },
                )
                update_context_after_turn(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=result_state,
                )
                finish_run(
                    run_id,
                    status_value="succeeded",
                    output_text=answer,
                    duration_ms=elapsed_ms(started_ms),
                    metadata={
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "mode": agent_route.mode,
                        "child_run_id": (result_state.get("automation") or {}).get("run_id") if isinstance(result_state.get("automation"), dict) else None,
                    },
                )
                write_audit_log(
                    user_id=current_user["id"],
                    action="chat.stream.agent_plan_execute",
                    resource_type="thread",
                    resource_id=final_thread_id,
                    metadata={
                        "intent": result_state.get("intent"),
                        "position": current_user.get("position"),
                        "workflow_id": agent_route.workflow_id,
                        "child_run_id": (result_state.get("automation") or {}).get("run_id") if isinstance(result_state.get("automation"), dict) else None,
                    },
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": final_thread_id,
                        "answer": answer,
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "erp_references": [],
                        "attachments": attachments,
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                    },
                )
                return

            if _should_handle_generated_file_wechat_send(request.message, salary_wechat_requested=salary_wechat_requested):
                yield format_business_progress_sse(
                    thread_id=thread_id,
                    workflow_id="enterprise_wechat_file_send",
                    step_key="file_lookup",
                    label="正在查找最近生成的文件",
                )
                result_state = _run_enterprise_wechat_generated_file_send_chat(
                    request=request,
                    current_user=current_user,
                    thread_id=thread_id,
                    run_id=run_id,
                    started_ms=started_ms,
                    stream=True,
                )
                final_thread_id = result_state.get("thread_id", thread_id)
                answer = result_state.get("answer", "")
                attachments = attachments_from_result(result_state)
                yield format_business_progress_sse(
                    thread_id=final_thread_id,
                    workflow_id="enterprise_wechat_file_send",
                    step_key="confirmation",
                    label="正在准备企业微信发送确认",
                    status_value=str((result_state.get("approval_result") or {}).get("status") or "blocked")
                    if isinstance(result_state.get("approval_result"), dict)
                    else "blocked",
                    data={
                        "artifact_id": (result_state.get("automation") or {}).get("artifact_id")
                        if isinstance(result_state.get("automation"), dict)
                        else None,
                    },
                )
                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": final_thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                _save_assistant_automation_message(
                    result=result_state,
                    current_user=current_user,
                    entrypoint="chat_stream",
                )
                update_context_after_turn(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=result_state,
                )
                write_audit_log(
                    user_id=current_user["id"],
                    action="chat.stream.enterprise_wechat_file_send_prepare",
                    resource_type="thread",
                    resource_id=final_thread_id,
                    metadata={
                        "intent": result_state.get("intent"),
                        "position": current_user.get("position"),
                        "artifact_id": (result_state.get("automation") or {}).get("artifact_id")
                        if isinstance(result_state.get("automation"), dict)
                        else None,
                    },
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": final_thread_id,
                        "answer": answer,
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "erp_references": [],
                        "attachments": attachments,
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                    },
                )
                return

            assert react_decision is not None
            record_react_decision_step(run_id, react_decision, request.message, thread_id, started_ms)
            direct_result = react_direct_result_for_decision(react_decision, current_user, thread_id)
            if direct_result:
                answer = direct_result["answer"]
                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                save_chat_message(
                    thread_id=thread_id,
                    user_id=current_user["id"],
                    role="assistant",
                    content=answer,
                    metadata={
                        "entrypoint": "chat_stream",
                        "intent": direct_result["intent"],
                        "risk_level": direct_result["risk_level"],
                        "position": current_user.get("position"),
                        "react_decision": direct_result.get("react_decision"),
                    },
                )
                update_context_after_turn(
                    thread_id=thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=direct_result,
                )
                finish_run(
                    run_id,
                    status_value="blocked" if direct_result["risk_level"] == "blocked" else "succeeded",
                    output_text=answer,
                    duration_ms=elapsed_ms(started_ms),
                    metadata={
                        "intent": direct_result["intent"],
                        "risk_level": direct_result["risk_level"],
                        "react_decision": direct_result.get("react_decision"),
                    },
                )
                write_audit_log(
                    user_id=current_user["id"],
                    action="chat.stream.react_direct",
                    resource_type="thread",
                    resource_id=thread_id,
                    metadata={
                        "intent": direct_result["intent"],
                        "position": current_user.get("position"),
                        "react_decision": direct_result.get("react_decision"),
                    },
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": thread_id,
                        "answer": answer,
                        "intent": direct_result["intent"],
                        "risk_level": direct_result["risk_level"],
                        "erp_references": [],
                        "attachments": [],
                        "approval_result": None,
                    },
                )
                return

            if (
                react_decision.action == FINANCE_COMPOUND_INTENT
                and should_handle_finance_compound_generation(finance_compound_intent)
            ):
                yield format_business_progress_sse(
                    thread_id=thread_id,
                    workflow_id=FINANCE_COMPOUND_INTENT,
                    step_key="permission",
                    label="正在检查财务权限",
                )
                yield format_business_progress_sse(
                    thread_id=thread_id,
                    workflow_id=FINANCE_COMPOUND_INTENT,
                    step_key="generate_files",
                    label="正在生成财务资料",
                    data={
                        "period_label": finance_compound_intent.period_label,
                        "outputs": list(finance_compound_intent.outputs),
                    },
                )
                result_state = _run_finance_compound_generation_chat(
                    request=request,
                    current_user=current_user,
                    thread_id=thread_id,
                    run_id=run_id,
                    started_ms=started_ms,
                    intent=finance_compound_intent,
                    react_decision=react_decision,
                    stream=True,
                )
                final_thread_id = result_state.get("thread_id", thread_id)
                answer = result_state.get("answer", "")
                attachments = attachments_from_result(result_state)

                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": final_thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                save_chat_message(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    role="assistant",
                    content=answer,
                    metadata={
                        "entrypoint": "chat_stream",
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "position": current_user.get("position"),
                        "attachments": [
                            _attachment_without_content(item)
                            for item in attachments
                        ],
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                        "react_decision": result_state.get("react_decision"),
                    },
                )
                update_context_after_turn(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=result_state,
                )
                write_audit_log(
                    user_id=current_user["id"],
                    action="chat.stream.finance_compound_report_generation",
                    resource_type="thread",
                    resource_id=final_thread_id,
                    metadata={
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "position": current_user.get("position"),
                        "attachment_count": len(attachments),
                        "period_label": finance_compound_intent.period_label,
                        "outputs": list(finance_compound_intent.outputs),
                    },
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": final_thread_id,
                        "answer": answer,
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "erp_references": [],
                        "attachments": attachments,
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                    },
                )
                return

            if react_decision.action == "finance_salary_wechat_send":
                yield format_business_progress_sse(
                    thread_id=thread_id,
                    workflow_id="finance_salary_wechat_send",
                    step_key="permission",
                    label="正在检查财务权限",
                )
                if (
                    current_user.get("role") != "admin"
                    and not is_ai_app_allowed(current_user, "automation-salary_wechat_send")
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="工资表微信发送应用已被管理员禁用。",
                    )
                yield format_business_progress_sse(
                    thread_id=thread_id,
                    workflow_id="finance_salary_wechat_send",
                    step_key="confirmation_plan",
                    label="正在整理发送确认信息",
                    detail=f"联系人：{salary_wechat_intent.recipient_name or '待确认'}",
                    data={
                        "period_label": salary_wechat_intent.salary_intent.period_label,
                        "recipient_name": salary_wechat_intent.recipient_name,
                    },
                )
                result_state = _run_finance_salary_wechat_send_chat(
                    request=request,
                    current_user=current_user,
                    thread_id=thread_id,
                    run_id=run_id,
                    started_ms=started_ms,
                    stream=True,
                )
                final_thread_id = result_state.get("thread_id", thread_id)
                answer = result_state.get("answer", "")
                attachments = attachments_from_result(result_state)
                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": final_thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                save_chat_message(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    role="assistant",
                    content=answer,
                    metadata={
                        "entrypoint": "chat_stream",
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "position": current_user.get("position"),
                        "attachments": [
                            _attachment_without_content(item)
                            for item in attachments
                        ],
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                    },
                )
                update_context_after_turn(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=result_state,
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": final_thread_id,
                        "answer": answer,
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "erp_references": [],
                        "attachments": attachments,
                        "approval_result": result_state.get("approval_result"),
                        "automation": result_state.get("automation"),
                    },
                )
                return

            if (
                react_decision.action == "finance_salary_export"
                and current_user.get("role") != "admin"
                and current_user.get("position") == "finance"
                and not is_ai_app_allowed(current_user, "automation-salary_summary")
            ):
                raise HTTPException(
                    status_code=403,
                    detail="统计工资应用已被管理员禁用。",
                )

            if (
                can_export_salary_from_chat(current_user)
                and react_decision.action == "finance_salary_export"
            ):
                result_state = _run_finance_salary_export_chat(
                    request=request,
                    current_user=current_user,
                    thread_id=thread_id,
                    run_id=run_id,
                    started_ms=started_ms,
                    intent=salary_export_intent,
                    stream=True,
                )
                final_thread_id = result_state.get("thread_id", thread_id)
                answer = result_state.get("answer", "")
                attachments = attachments_from_result(result_state)

                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": final_thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                save_chat_message(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    role="assistant",
                    content=answer,
                    metadata={
                        "entrypoint": "chat_stream",
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "position": current_user.get("position"),
                        "erp_resource": result_state.get("erp_resource"),
                        "attachments": [
                            _attachment_without_content(item)
                            for item in attachments
                        ],
                    },
                )
                update_context_after_turn(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=result_state,
                )
                write_audit_log(
                    user_id=current_user["id"],
                    action="chat.stream.finance_salary_export",
                    resource_type="thread",
                    resource_id=final_thread_id,
                    metadata={
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "position": current_user.get("position"),
                        "erp_resource": result_state.get("erp_resource"),
                        "attachment_count": len(attachments),
                        "period_label": salary_export_intent.period_label,
                        "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
                        "recent_message_count": len(context_bundle.get("recent_messages", [])),
                    },
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": final_thread_id,
                        "answer": answer,
                        "intent": result_state.get("intent"),
                        "risk_level": result_state.get("risk_level"),
                        "erp_resource": result_state.get("erp_resource"),
                        "erp_references": [],
                        "attachments": attachments,
                        "approval_result": None,
                    },
                )
                return

            automation_started_ms = now_ms()
            if react_decision.action == "operations_listing_draft":
                for step_key, label in [
                    ("permission", "正在检查运营权限"),
                    ("erp", "正在查询 SKU 商品资料"),
                    ("image", "正在分析产品图片"),
                    ("listing", "正在生成 Listing 草稿"),
                ]:
                    yield format_business_progress_sse(
                        thread_id=thread_id,
                        workflow_id="operations_listing_amazon",
                        step_key=step_key,
                        label=label,
                    )
            automation_result = run_chat_automation(
                message=request.message,
                current_user=current_user,
                thread_id=thread_id,
                forced_route=automation_route_from_react_decision(react_decision),
                react_decision=chat_react_decision_dict(react_decision),
                attachments=request.attachments,
                source="chat_stream",
            )
            if automation_result:
                result_state.update(automation_result)
                final_thread_id = automation_result.get("thread_id", thread_id)
                answer = automation_result.get("answer", "")
                erp_references = automation_result.get("erp_references") or []
                draft = platform_draft_from_result(automation_result)
                if react_decision.action == "operations_listing_draft":
                    yield format_business_progress_sse(
                        thread_id=final_thread_id,
                        workflow_id="operations_listing_amazon",
                        step_key="waiting_confirmation",
                        label="等待你确认上传 Amazon",
                        status_value="blocked",
                        data={
                            "platform_draft_id": draft.get("id") if draft else None,
                        },
                    )

                _finish_chat_automation_run(
                    run_id=run_id,
                    result=automation_result,
                    request=request,
                    started_ms=started_ms,
                    step_started_ms=automation_started_ms,
                    current_user=current_user,
                    context_bundle=context_bundle,
                    action="chat.stream.automation_dispatch",
                )
                yield format_sse(
                    "node",
                    {
                        "thread_id": final_thread_id,
                        "node": "chat_automation_dispatch",
                        "data": {
                            "intent": automation_result.get("intent"),
                            "risk_level": automation_result.get("risk_level"),
                            "automation": automation_result.get("automation"),
                            "platform_draft_id": draft.get("id") if draft else None,
                        },
                    },
                )

                for chunk in chunk_text(answer):
                    yield format_sse(
                        "content",
                        {
                            "thread_id": final_thread_id,
                            "content": chunk,
                        },
                    )
                    time.sleep(0.04)

                _save_assistant_automation_message(
                    result=automation_result,
                    current_user=current_user,
                    entrypoint="chat_stream",
                )
                update_context_after_turn(
                    thread_id=final_thread_id,
                    user_id=current_user["id"],
                    user_message=request.message,
                    graph_result=automation_result,
                )
                yield format_sse(
                    "done",
                    {
                        "thread_id": final_thread_id,
                        "answer": answer,
                        "intent": automation_result.get("intent"),
                        "risk_level": automation_result.get("risk_level"),
                        "erp_references": erp_references,
                        "attachments": attachments_from_result(automation_result),
                        "platform_draft": draft,
                        "approval_result": automation_result.get("approval_result"),
                    },
                )
                return

            for event in graph.stream(graph_input, stream_mode="updates"):
                for node_name, node_output in event.items():
                    node_started_ms = now_ms()
                    if isinstance(node_output, dict):
                        result_state.update(node_output)
                    record_step(
                        run_id=run_id,
                        step_name=f"graph.node.{node_name}",
                        step_order=step_order,
                        status_value="succeeded",
                        provider="langgraph",
                        resource_type="thread",
                        resource_id=result_state.get("thread_id", thread_id),
                        input_text=request.message if step_order == 1 else None,
                        output_text=_stream_node_output_preview(node_output),
                        duration_ms=elapsed_ms(node_started_ms),
                        metadata={
                            "node": node_name,
                            "intent": result_state.get("intent"),
                            "risk_level": result_state.get("risk_level"),
                            "erp_resource": result_state.get("erp_resource"),
                        },
                    )
                    step_order += 1

                    yield format_sse(
                        "node",
                        {
                            "thread_id": result_state.get("thread_id", thread_id),
                            "node": node_name,
                            "data": node_output,
                        },
                    )

            final_thread_id = result_state.get("thread_id", thread_id)
            answer = result_state.get("answer", "")
            erp_references = erp_references_from_result(result_state)
            for index, reference in enumerate(erp_references[:10], start=1):
                record_artifact(
                    run_id=run_id,
                    artifact_type="erp_reference",
                    name=str(reference.get("title") or reference.get("record_id") or "ERP 引用"),
                    external_ref=str(reference.get("record_id") or ""),
                    metadata={
                        "resource": reference.get("resource"),
                        "resource_label": reference.get("resource_label"),
                        "provider": reference.get("provider"),
                        "provider_resource": reference.get("provider_resource"),
                        "reference_order": index,
                    },
                )
            record_artifact(
                run_id=run_id,
                artifact_type="chat_thread",
                name=final_thread_id,
                external_ref=final_thread_id,
                metadata={
                    "intent": result_state.get("intent"),
                    "risk_level": result_state.get("risk_level"),
                },
            )

            for chunk in chunk_text(answer):
                yield format_sse(
                    "content",
                    {
                        "thread_id": final_thread_id,
                        "content": chunk,
                    },
                )
                time.sleep(0.04)

            save_chat_message(
                thread_id=final_thread_id,
                user_id=current_user["id"],
                role="assistant",
                content=answer,
                metadata={
                    "entrypoint": "chat_stream",
                    "intent": result_state.get("intent"),
                    "risk_level": result_state.get("risk_level"),
                    "order_no": result_state.get("order_no"),
                    "position": current_user.get("position"),
                    "erp_resource": result_state.get("erp_resource"),
                    "erp_status": (result_state.get("erp_result") or {}).get("status")
                    if isinstance(result_state.get("erp_result"), dict)
                    else None,
                    "erp_references": erp_references,
                    "approval_result": result_state.get("approval_result"),
                },
            )
            update_context_after_turn(
                thread_id=final_thread_id,
                user_id=current_user["id"],
                user_message=request.message,
                graph_result=result_state,
            )
            write_audit_log(
                user_id=current_user["id"],
                action="chat.stream.invoke",
                resource_type="thread",
                resource_id=final_thread_id,
                metadata={
                    "intent": result_state.get("intent"),
                    "risk_level": result_state.get("risk_level"),
                    "order_no": result_state.get("order_no"),
                    "position": current_user.get("position"),
                    "erp_resource": result_state.get("erp_resource"),
                    "erp_status": (result_state.get("erp_result") or {}).get("status")
                    if isinstance(result_state.get("erp_result"), dict)
                    else None,
                    "erp_reference_count": len(erp_references),
                    "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
                    "recent_message_count": len(context_bundle.get("recent_messages", [])),
                },
            )
            finish_run(
                run_id,
                status_value="succeeded",
                output_text=answer,
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "intent": result_state.get("intent"),
                    "risk_level": result_state.get("risk_level"),
                    "erp_resource": result_state.get("erp_resource"),
                    "erp_reference_count": len(erp_references),
                    "final_thread_id": final_thread_id,
                },
            )

            yield format_sse(
                "done",
                {
                    "thread_id": final_thread_id,
                    "answer": answer,
                    "intent": result_state.get("intent"),
                    "risk_level": result_state.get("risk_level"),
                    "erp_resource": result_state.get("erp_resource"),
                    "erp_references": erp_references,
                    "attachments": attachments_from_result(result_state),
                    "approval_result": result_state.get("approval_result"),
                },
            )
        except Exception as error:
            record_step(
                run_id=run_id,
                step_name="graph.stream",
                step_order=step_order,
                status_value="failed",
                provider="langgraph",
                resource_type="thread",
                resource_id=thread_id,
                input_text=request.message,
                error_message=error,
                duration_ms=elapsed_ms(started_ms),
            )
            finish_run(
                run_id,
                status_value="failed",
                error_message=error,
                duration_ms=elapsed_ms(started_ms),
            )
            yield format_sse(
                "error",
                {
                    "thread_id": thread_id,
                    "message": business_error_message_for_user(error, current_user),
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def position_label_for_run(position: str | None) -> str:
    labels = {
        "operations": "运营",
        "customer_service": "客服",
        "finance": "财务",
    }
    return labels.get(str(position), "平台")


def _stream_node_output_preview(node_output) -> str:
    if not isinstance(node_output, dict):
        return str(node_output)

    preview = {
        "intent": node_output.get("intent"),
        "risk_level": node_output.get("risk_level"),
        "erp_resource": node_output.get("erp_resource"),
        "answer": node_output.get("answer"),
    }
    return {key: value for key, value in preview.items() if value is not None}

@app.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(
    request: AgentChatRequest,
    current_user: dict = Depends(get_current_user),
):
    ensure_chat_app_enabled(current_user)
    ensure_chat_allowed_for_position(current_user, request.message)
    thread_id = resolve_chat_thread_id(
        request.thread_id,
        current_user,
        title=request.message[:50],
    )
    context_bundle = build_context_bundle(
        thread_id=thread_id,
        user_id=current_user["id"],
    )

    save_chat_message(
        thread_id=thread_id,
        user_id=current_user["id"],
        role="user",
        content=request.message,
        metadata={
            "entrypoint": "agent",
        },
    )

    result = run_low_risk_agent(
        message=request.message,
        thread_id=thread_id,
        current_user=current_user,
        context=context_bundle,
    )

    save_chat_message(
        thread_id=thread_id,
        user_id=current_user["id"],
        role="assistant",
        content=result["answer"],
        metadata={
            "entrypoint": "agent",
        },
    )

    write_audit_log(
        user_id=current_user["id"],
        action="agent.chat.invoke",
        resource_type="thread",
        resource_id=thread_id,
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
        },
    )
    update_context_after_turn(
        thread_id=thread_id,
        user_id=current_user["id"],
        user_message=request.message,
        graph_result={
            "answer": result["answer"],
            "intent": "agent",
            "risk_level": "low",
        },
    )

    return {
        "thread_id": thread_id,
        "answer": result["answer"],
    }


@app.post("/admin/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    visibility: str = Form("employee"),
    department: str | None = Form(None),
    position_scope: str | None = Form(None),
    market_scope: str | None = Form(None),
    store_scope: str | None = Form(None),
    field_scope: str | None = Form(None),
    sensitivity_level: str | None = Form(None),
    access_mode: str | None = Form(None),
    owner_user_id: str | None = Form(None),
    owner_team_id: str | None = Form(None),
    grant_subject_type: str | None = Form(None),
    grant_subject_id: str | None = Form(None),
    grant_access_level: str | None = Form(None),
    grant_reason: str | None = Form(None),
    grant_expires_at: datetime | None = Form(None),
    current_user: dict = Depends(require_admin),
):
    if visibility not in ["employee", "admin"]:
        raise HTTPException(
            status_code=400,
            detail="visibility 只能是 employee 或 admin",
        )

    normalized_position_scope = position_scope.strip() if position_scope else None
    if normalized_position_scope == "":
        normalized_position_scope = None

    if normalized_position_scope and normalized_position_scope not in POSITION_LABELS:
        raise HTTPException(
            status_code=400,
            detail="position_scope 只能是 operations、customer_service 或 finance",
        )

    try:
        normalized_market_scope = normalize_market_scope(market_scope)
        normalized_store_scope = normalize_store_scope(store_scope)
        normalized_field_scope = normalize_field_scope(field_scope)
        normalized_sensitivity_level = normalize_sensitivity_level(sensitivity_level)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if normalized_market_scope and normalized_market_scope not in ALLOWED_MARKET_SCOPES:
        raise HTTPException(
            status_code=400,
            detail="market_scope 只能是 us、de 或 jp",
        )

    if normalized_store_scope and normalized_store_scope not in ALLOWED_STORE_SCOPES:
        raise HTTPException(
            status_code=400,
            detail="store_scope 只能是 us_store、de_store 或 jp_store",
        )

    if normalized_field_scope and normalized_field_scope not in ALLOWED_FIELD_SCOPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "field_scope 只能是 operations_listing、operations_inventory、operations_sales、"
                "customer_profile、customer_logistics、customer_after_sales、finance_invoice、"
                "finance_payment、finance_profit 或 finance_salary"
            ),
        )

    if normalized_sensitivity_level and normalized_sensitivity_level not in ALLOWED_SENSITIVITY_LEVELS:
        raise HTTPException(
            status_code=400,
            detail="sensitivity_level 只能是 internal、confidential 或 restricted",
        )

    upload_access = normalize_document_access_inputs(
        access_mode=access_mode,
        owner_user_id=owner_user_id,
        owner_team_id=owner_team_id,
    )
    document_for_grant_validation = {
        "id": "",
        "position_scope": normalized_position_scope,
        "market_scope": normalized_market_scope,
        "store_scope": normalized_store_scope,
        "field_scope": normalized_field_scope,
        "sensitivity_level": normalized_sensitivity_level,
        "access_mode": upload_access["access_mode"],
        "owner_user_id": upload_access["owner_user_id"],
        "owner_team_id": upload_access["owner_team_id"],
    }
    upload_grant = normalize_document_grant_inputs(
        subject_type=grant_subject_type,
        subject_id=grant_subject_id,
        access_level=grant_access_level,
        reason=grant_reason,
        expires_at=grant_expires_at,
        document=document_for_grant_validation,
    )

    filename = Path(file.filename or "untitled.txt").name
    raw = await file.read()

    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="文件不能超过 20MB",
        )

    try:
        documents = load_documents_from_bytes(filename, raw)
    except UnsupportedDocumentTypeError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except EmptyDocumentError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"文件解析失败：{error}",
        ) from error

    result = ingest_documents(
        title=filename,
        source=f"upload/{filename}",
        visibility=visibility,
        department=department,
        position_scope=normalized_position_scope,
        market_scope=normalized_market_scope,
        store_scope=normalized_store_scope,
        field_scope=normalized_field_scope,
        sensitivity_level=normalized_sensitivity_level,
        owner_user_id=upload_access["owner_user_id"],
        owner_team_id=upload_access["owner_team_id"],
        access_mode=upload_access["access_mode"],
        raw_documents=documents,
    )
    initial_grant = None
    if upload_grant:
        initial_grant = create_document_grant(
            document_id=result["document_id"],
            payload=upload_grant,
            current_user=current_user,
        )

    write_audit_log(
        user_id=current_user["id"],
        action="document.upload",
        resource_type="document",
        resource_id=result["document_id"],
        metadata={
            "filename": filename,
            "content_type": file.content_type,
            "visibility": visibility,
            "department": department,
            "position_scope": normalized_position_scope,
            "market_scope": normalized_market_scope,
            "store_scope": normalized_store_scope,
            "field_scope": normalized_field_scope,
            "sensitivity_level": normalized_sensitivity_level,
            "access_mode": upload_access["access_mode"],
            "owner_user_id": upload_access["owner_user_id"],
            "owner_team_id": upload_access["owner_team_id"],
            "initial_grant_id": initial_grant["id"] if initial_grant else None,
            "initial_grant_subject_type": initial_grant["subject_type"] if initial_grant else None,
            "initial_grant_subject_id": initial_grant["subject_id"] if initial_grant else None,
            "initial_grant_access_level": initial_grant["access_level"] if initial_grant else None,
            "content_hash": result.get("content_hash"),
            "version": result.get("version"),
            "status": result.get("status"),
            "update_action": result.get("update_action"),
            "parent_chunk_count": result.get("parent_chunk_count"),
            "chunk_count": result["chunk_count"],
            "username": current_user["username"],
            "role": current_user["role"],
        },
    )

    return {
        "message": "文档上传并入库成功",
        "filename": filename,
        "content_type": file.content_type,
        "visibility": visibility,
        "department": department,
        "position_scope": normalized_position_scope,
        "market_scope": normalized_market_scope,
        "store_scope": normalized_store_scope,
        "field_scope": normalized_field_scope,
        "sensitivity_level": normalized_sensitivity_level,
        "access_mode": upload_access["access_mode"],
        "owner_user_id": upload_access["owner_user_id"],
        "owner_team_id": upload_access["owner_team_id"],
        "initial_grant": initial_grant,
        **result,
    }
