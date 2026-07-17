from contextlib import asynccontextmanager
import json
import time
from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.agents.low_risk_agent import run_low_risk_agent
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.api.audit_logs import router as audit_logs_router
from app.api.auth import router as auth_router
from app.api.ai_workflows import router as ai_workflows_router
from app.api.automation_flows import router as automation_flows_router
from app.api.connectors import router as connectors_router
from app.api.effect_analytics import router as effect_analytics_router
from app.api.evaluation_center import router as evaluation_center_router
from app.api.monitoring_center import router as monitoring_center_router
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
from app.permissions import ensure_chat_allowed_for_position
from app.rag.ingest import ingest_documents
from app.rag.loaders import (
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
    load_documents_from_bytes,
)
from app.services.context_service import (
    build_context_bundle,
    update_context_after_turn,
)
from app.services.erp_service import query_erp_for_current_user, summarize_erp_items
from app.services.logging_service import (ensure_chat_thread,save_chat_message,write_audit_log,)
from app.services.mcp_service import (
    create_external_ticket,
    get_external_ticket,
    sync_document_system_to_rag,
)
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    now_ms,
    record_artifact,
    record_step,
    start_run,
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    yield
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
app.include_router(connectors_router)
app.include_router(effect_analytics_router)
app.include_router(evaluation_center_router)
app.include_router(monitoring_center_router)
app.include_router(audit_logs_router)
app.include_router(erp_router)
app.include_router(refunds_router)
app.include_router(run_records_router)
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


class McpTicketCreateRequest(BaseModel):
    title: str
    description: str
    priority: str = "normal"


def format_sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


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
    )

    write_audit_log(
        user_id=current_user["id"],
        action="mcp.documents.sync",
        resource_type="mcp",
        resource_id="document_system",
        metadata={
            "visibility": request.visibility,
            "department": request.department,
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


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest,current_user: dict = Depends(get_current_user),):
    ensure_chat_allowed_for_position(current_user, request.message)
    thread_id = request.thread_id or f"thread-{uuid4()}"
    ensure_chat_thread(thread_id, current_user["id"], title=request.message[:50])
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
    run_id = start_run(
        run_type="chat",
        app_id=f"{position or 'admin'}-chat-agent",
        app_name=f"{position_label_for_run(position)} AI 对话",
        entrypoint="/chat",
        current_user=current_user,
        thread_id=thread_id,
        resource_type="thread",
        resource_id=thread_id,
        input_text=request.message,
        metadata={
            "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
            "recent_message_count": len(context_bundle.get("recent_messages", [])),
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
        "approval_result": result.get("approval_result"),
    }


@app.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    ensure_chat_allowed_for_position(current_user, request.message)
    thread_id = request.thread_id or f"thread-{uuid4()}"
    ensure_chat_thread(thread_id, current_user["id"], title=request.message[:50])
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
    run_id = start_run(
        run_type="chat_stream",
        app_id=f"{position or 'admin'}-chat-agent",
        app_name=f"{position_label_for_run(position)} AI 对话",
        entrypoint="/chat/stream",
        current_user=current_user,
        thread_id=thread_id,
        resource_type="thread",
        resource_id=thread_id,
        input_text=request.message,
        metadata={
            "context_summary_used": bool(context_bundle.get("summary", {}).get("summary")),
            "recent_message_count": len(context_bundle.get("recent_messages", [])),
        },
    )

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
    ensure_chat_allowed_for_position(current_user, request.message)
    thread_id = request.thread_id or f"agent-thread-{uuid4()}"

    ensure_chat_thread(
        thread_id=thread_id,
        user_id=current_user["id"],
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
    current_user: dict = Depends(require_admin),
):
    if visibility not in ["employee", "admin"]:
        raise HTTPException(
            status_code=400,
            detail="visibility 只能是 employee 或 admin",
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
        raw_documents=documents,
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
        **result,
    }
