from contextlib import asynccontextmanager, suppress
import asyncio
import base64
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

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
from app.services.feedback_service import ensure_feedback_schema
from app.services.generated_file_service import ensure_generated_file_schema, save_generated_file
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
    ensure_notification_schema()
    ensure_feedback_schema()
    ensure_chat_thread_schema()
    ensure_run_record_flow_reference_schema()
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
    title="Company RAG Agent",
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


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    intent: str | None = None
    risk_level: str | None = None
    erp_references: list[dict] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)
    platform_draft: dict | None = None
    approval_result: dict | None = None


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
    save_generated_file(
        run_id=run_id,
        content=salary_result.content,
        artifact_type="excel_file",
        mime_type=attachment["mime_type"],
        filename=salary_result.filename,
        current_user=current_user,
        metadata=salary_result.metadata,
    )
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
    if (
        current_user.get("role") != "admin"
        and current_user.get("position") == "finance"
        and salary_export_intent.intent == "finance_salary_export"
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

    try:
        step_started_ms = now_ms()
        automation_result = run_chat_automation(
            message=request.message,
            current_user=current_user,
            thread_id=thread_id,
            forced_route=automation_route_from_react_decision(react_decision),
            react_decision=chat_react_decision_dict(react_decision),
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
    if (
        current_user.get("role") != "admin"
        and current_user.get("position") == "finance"
        and salary_export_intent.intent == "finance_salary_export"
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
    react_decision = decide_chat_action(request.message, current_user)
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
            automation_result = run_chat_automation(
                message=request.message,
                current_user=current_user,
                thread_id=thread_id,
                forced_route=automation_route_from_react_decision(react_decision),
                react_decision=chat_react_decision_dict(react_decision),
                source="chat_stream",
            )
            if automation_result:
                result_state.update(automation_result)
                final_thread_id = automation_result.get("thread_id", thread_id)
                answer = automation_result.get("answer", "")
                erp_references = automation_result.get("erp_references") or []
                draft = platform_draft_from_result(automation_result)

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
                    "message": str(error),
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
