import json
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.erp.base import ERPProviderError
from app.erp.providers import get_active_provider
from app.erp.resources import (
    ERP_RESOURCE_CATALOG,
    provider_fields_for,
    provider_resource_for,
    resolve_resource_name,
)
from app.llm import chat
from app.permissions import (
    POSITION_LABELS,
    ensure_erp_resource_allowed,
    erp_scopes_for_position,
    is_valid_position,
)
from app.services.automation_service import (
    build_automation_prompt,
    find_automation_task,
    list_all_automation_tasks,
    list_automation_tasks,
)
from app.services.finance_excel_service import (
    MAX_EXCEL_BYTES,
)
from app.services.finance_reconciliation_service import (
    MAX_RECONCILIATION_FILE_BYTES,
    MAX_RECONCILIATION_FILES,
    MAX_RECONCILIATION_TOTAL_BYTES,
)
from app.services.finance_report_service import (
    MAX_REPORT_FILE_BYTES,
    MAX_REPORT_FILES,
    FinanceReportInputFile,
    analyze_finance_report_files,
)
from app.services.finance_salary_service import recognize_salary_export_intent
from app.services.finance_salary_wechat_service import (
    build_salary_wechat_plan,
    build_wechat_prepare_confirmation_task,
    dispatch_enterprise_wechat_file_send_task,
    dispatch_salary_wechat_send_task,
    ensure_salary_wechat_intent_ready,
    recognize_salary_wechat_send_intent,
    run_record_status_for_salary_wechat,
)
from app.services.generated_file_service import save_generated_file
from app.services.generated_file_service import get_generated_file_storage_reference
from app.services.logging_service import (
    get_thread_for_user,
    save_chat_message,
    update_chat_message,
    update_latest_chat_message_by_artifact,
    write_audit_log,
)
from app.services.automation_flow_version_service import resolve_flow_execution_reference
from app.services.platform_draft_service import (
    create_platform_draft,
    listing_content_from_answer,
)
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    get_run_detail,
    now_ms,
    record_artifact,
    record_step,
    start_run,
)
from app.services.user_ai_app_permission_service import is_ai_app_allowed
from app.skills.executor import SkillExecutionResult, execute_skill


router = APIRouter(
    prefix="/automation",
    tags=["automation"],
)


FINANCE_EXCEL_ERP_LIMIT = 50
MAX_FINANCE_EXCEL_ERP_RESOURCES = 5


def _format_sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _finance_wechat_progress_sse(
    *,
    step_key: str,
    label: str,
    status_value: str = "running",
    detail: str | None = None,
    data: dict[str, Any] | None = None,
) -> str:
    return _format_sse(
        "business_progress",
        {
            "workflow_id": "finance_salary_wechat_send",
            "step_key": step_key,
            "label": label,
            "status": status_value,
            "detail": detail,
            "data": data or {},
        },
    )


def _automation_business_error_message(error: Exception, current_user: dict) -> str:
    detail = getattr(error, "detail", None)
    raw_message = str(detail or error or "执行失败")
    lowered = raw_message.lower()

    if "没有查到" in raw_message:
        message = raw_message
    elif "没有识别到" in raw_message or "请说明" in raw_message:
        message = raw_message
    elif "erpnext" in lowered or "erp" in lowered or "502" in lowered or "salary slip" in lowered:
        message = "ERPNext 暂时不可用，请稍后重试或联系管理员。"
    elif "权限" in raw_message or "403" in raw_message or "forbidden" in lowered:
        message = "当前账号没有执行这个操作的权限，请联系管理员开通。"
    elif "联系人" in raw_message:
        message = raw_message
    else:
        message = "这次自动化没有执行成功，请稍后重试或联系管理员。"

    if current_user.get("role") == "admin":
        message = f"{message} 技术线索：{raw_message[:180]}"

    return message


class AutomationTaskItem(BaseModel):
    task_id: str
    label: str
    placeholder: str
    instruction: str
    output_format: str
    position: str
    position_label: str


class AutomationTasksResponse(BaseModel):
    position: str
    position_label: str
    items: list[AutomationTaskItem]


class AutomationGenerateRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64)
    input_text: str = Field(min_length=1, max_length=10000)


class AutomationGenerateResponse(BaseModel):
    position: str
    position_label: str
    task_id: str
    task_label: str
    answer: str
    platform_draft: dict[str, Any] | None = None


class FinanceSalaryExportRequest(BaseModel):
    message: str = Field(
        default="把这个月所有员工的工资表发我",
        min_length=1,
        max_length=1000,
    )


class FinanceSalaryWechatPlanRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class FinanceSalaryWechatPlanResponse(BaseModel):
    intent: str
    confidence: float
    period_label: str
    recipient_name: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    plan: dict[str, Any]


class FinanceSalaryWechatSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    recipient_name: str | None = Field(default=None, max_length=64)
    recipient_confirmed: bool = False
    sensitive_data_confirmed: bool = False


class FinanceWechatAttachmentPrepareRequest(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=80)
    recipient_name: str = Field(min_length=1, max_length=64)
    filename: str | None = Field(default=None, max_length=240)
    source_message: str | None = Field(default=None, max_length=1000)
    source_workflow_id: str | None = Field(default=None, max_length=120)
    recipient_confirmed: bool = False
    sensitive_data_confirmed: bool = False


class FinanceEnterpriseWechatFileSendConfirmRequest(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=80)
    artifact_ids: list[str] = Field(default_factory=list)
    recipient_name: str = Field(min_length=1, max_length=64)
    recipient_candidate_id: str | None = Field(default=None, max_length=120)
    recipient: dict[str, Any] | None = None
    filename: str | None = Field(default=None, max_length=240)
    source_message: str | None = Field(default=None, max_length=1000)
    source_message_id: str | None = Field(default=None, max_length=80)
    source_workflow_id: str | None = Field(default=None, max_length=120)
    thread_id: str | None = Field(default=None, max_length=160)
    recipient_confirmed: bool = False
    sensitive_data_confirmed: bool = False


class FinanceSalaryWechatSendResponse(BaseModel):
    run_id: str
    status: str
    status_label: str
    answer: str
    filename: str
    artifact_id: str | None = None
    download_path: str | None = None
    recipient_name: str
    plan: dict[str, Any]
    execution: dict[str, Any]


class FinanceWechatAttachmentPrepareResponse(BaseModel):
    run_id: str
    status: str
    status_label: str
    answer: str
    filename: str
    artifact_id: str
    download_path: str | None = None
    recipient_name: str
    execution: dict[str, Any]


class FinanceEnterpriseWechatFileSendConfirmResponse(BaseModel):
    run_id: str
    status: str
    status_label: str
    answer: str
    filename: str
    artifact_id: str
    download_path: str | None = None
    recipient_name: str
    execution: dict[str, Any]


class FinanceSalaryWechatStatusResponse(BaseModel):
    run_id: str
    run_status: str
    status: str
    status_label: str
    answer: str | None = None
    filename: str | None = None
    artifact_id: str | None = None
    download_path: str | None = None
    recipient_name: str | None = None
    executor_type: str | None = None
    manual_final_send_required: bool = True
    steps: list[dict[str, Any]] = Field(default_factory=list)
    logs: list[dict[str, Any]] = Field(default_factory=list)


def ensure_finance_user(current_user: dict, detail: str) -> None:
    if current_user.get("role") == "admin" or current_user.get("position") == "finance":
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _skill_result_attachment(result: SkillExecutionResult) -> dict[str, Any]:
    if not result.attachments:
        raise ValueError("Skill 未返回文件产物。")
    attachment = result.attachments[0]
    if not isinstance(attachment.get("content"), bytes):
        raise ValueError("Skill 文件产物格式错误。")
    if not attachment.get("filename"):
        raise ValueError("Skill 文件产物缺少文件名。")
    return attachment


def _skill_result_metadata(result: SkillExecutionResult) -> dict[str, Any]:
    return {
        "skill_id": result.skill_id,
        **result.metadata,
    }


def _flow_key_for_automation_task(position: str, task_id: str) -> str:
    if position == "finance" and task_id == "salary_summary":
        return "automation:finance:salary-export"
    if position == "finance" and task_id == "excel_transform":
        return "automation:finance:excel-file-transform"
    return f"automation:{position}:{task_id}"


def _resolve_optional_flow_reference(
    *,
    flow_key: str,
    current_user: dict,
    execution_source: str,
) -> dict[str, Any] | None:
    try:
        return resolve_flow_execution_reference(
            flow_key=flow_key,
            current_user=current_user,
            execution_source=execution_source,
        )
    except HTTPException as error:
        if error.status_code == status.HTTP_404_NOT_FOUND:
            return None
        raise


def _run_record_status_for_mcp_trace(trace: dict[str, Any]) -> str:
    status_text = str(trace.get("status") or "").strip().lower()
    if status_text in {"failed", "error", "unhealthy", "invalid_config"}:
        return "failed"
    if status_text in {"waiting_executor", "waiting_callback", "not_configured", "stub_ready"}:
        return "blocked"
    return "succeeded"


def _record_mcp_tool_steps(
    *,
    run_id: str,
    traces: list[dict[str, Any]],
    start_order: int,
) -> None:
    for index, trace in enumerate(traces, start=start_order):
        tool_id = str(trace.get("tool_id") or trace.get("resource_id") or "mcp_tool")
        record_step(
            run_id=run_id,
            step_name=f"mcp_tool.{tool_id}",
            step_order=index,
            status_value=_run_record_status_for_mcp_trace(trace),
            provider="mcp",
            resource_type="mcp_tool",
            resource_id=tool_id,
            input_text={
                "tool_id": tool_id,
                "argument_keys": trace.get("argument_keys") or [],
                "source": trace.get("source"),
            },
            output_text=trace.get("message") or trace.get("status"),
            duration_ms=trace.get("duration_ms") if isinstance(trace.get("duration_ms"), int) else None,
            metadata=trace,
        )


@router.get("/tasks", response_model=AutomationTasksResponse)
def get_my_tasks(current_user: dict = Depends(get_current_user)):
    position = current_user.get("position")

    if current_user.get("role") != "admin" and not is_valid_position(position):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未绑定岗位，无法查看岗位任务。",
        )

    if current_user.get("role") == "admin":
        return {
            "position": "operations",
            "position_label": POSITION_LABELS["operations"],
            "items": list_all_automation_tasks(),
        }

    effective_position = position
    items = [
        item
        for item in list_automation_tasks(effective_position)
        if is_ai_app_allowed(current_user, f"automation-{item['task_id']}")
    ]

    return {
        "position": effective_position,
        "position_label": POSITION_LABELS[effective_position],
        "items": items,
    }


@router.post("/generate", response_model=AutomationGenerateResponse)
def generate_automation(
    request: AutomationGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    position = current_user.get("position")

    if current_user.get("role") != "admin" and not is_valid_position(position):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未绑定岗位，无法使用岗位自动化。",
        )

    task = find_automation_task(request.task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前岗位无权使用该自动化任务",
        )

    if current_user.get("role") != "admin" and task["position"] != position:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前岗位无权使用该自动化任务",
        )

    if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, f"automation-{request.task_id}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该 AI 应用已被管理员禁用。",
        )

    prompt = build_automation_prompt(
        position=task["position"],
        task_id=request.task_id,
        input_text=request.input_text,
    )
    started_ms = now_ms()
    run_id = start_run(
        run_type="automation_generate",
        app_id=f"automation-{request.task_id}",
        app_name=task["label"],
        entrypoint="/automation/generate",
        current_user=current_user,
        resource_type="automation",
        resource_id=request.task_id,
        flow_reference=resolve_flow_execution_reference(
            flow_key=_flow_key_for_automation_task(task["position"], request.task_id),
            current_user=current_user,
            execution_source="manual_form",
        ),
        input_text=request.input_text,
        metadata={
            "task_id": request.task_id,
            "task_label": task["label"],
            "position": task["position"],
            "position_label": task["position_label"],
        },
    )
    platform_draft = None

    try:
        step_started_ms = now_ms()
        answer = chat(prompt)
        record_step(
            run_id=run_id,
            step_name="llm_chat",
            step_order=1,
            status_value="succeeded",
            provider="dashscope",
            resource_type="automation",
            resource_id=request.task_id,
            input_text=request.input_text,
            output_text=answer,
            duration_ms=elapsed_ms(step_started_ms),
            metadata={
                "task_id": request.task_id,
                "task_label": task["label"],
                "prompt_built": True,
            },
        )
        if task["position"] == "operations" and request.task_id == "listing":
            draft_started_ms = now_ms()
            draft_content = listing_content_from_answer(
                answer=answer,
                input_text=request.input_text,
            )
            platform_draft = create_platform_draft(
                draft_type="listing",
                platform="amazon",
                external_target="amazon_seller_central",
                title=str(draft_content.get("listing_title") or task["label"]),
                position="operations",
                owner_user_id=current_user.get("id"),
                source_run_id=run_id,
                source_resource_type="automation",
                source_resource_id=request.task_id,
                content=draft_content,
                writeback_status="draft_saved",
                writeback_message=(
                    "已保存为 Amazon Listing 平台草稿，等待运营确认后再打开 Seller Central 填表。"
                ),
                metadata={
                    "automation": "operations_listing",
                    "source": "automation_generate",
                    "saved_by_ai": True,
                    "amazon_upload_status": "waiting_confirmation",
                },
            )
            record_step(
                run_id=run_id,
                step_name="save_platform_draft",
                step_order=2,
                status_value="succeeded",
                provider="platform_drafts",
                resource_type="platform_draft",
                resource_id=platform_draft["id"],
                input_text=request.input_text,
                output_text=platform_draft,
                duration_ms=elapsed_ms(draft_started_ms),
                metadata={
                    "draft_id": platform_draft["id"],
                    "external_target": platform_draft["external_target"],
                    "writeback_status": platform_draft["writeback_status"],
                },
            )
            answer = (
                "AI 已完成 Listing 草稿生成，并等待运营确认上传 Amazon。\n"
                f"草稿 ID：{platform_draft['id']}\n"
                f"写回目标：{platform_draft['external_target']}\n"
                f"写回状态：{platform_draft['writeback_status']}\n\n"
                "下一步：运营确认后调用 Amazon Playwright 上传准备，系统会停在最终发布前。\n\n"
                f"{answer}"
            )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=answer,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "task_id": request.task_id,
                "task_label": task["label"],
                "position": task["position"],
                "platform_draft_id": platform_draft.get("id") if platform_draft else None,
            },
        )
    except Exception as error:
        record_step(
            run_id=run_id,
            step_name="llm_chat",
            step_order=1,
            status_value="failed",
            provider="dashscope",
            resource_type="automation",
            resource_id=request.task_id,
            input_text=request.input_text,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "task_id": request.task_id,
                "task_label": task["label"],
            },
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    write_audit_log(
        user_id=current_user["id"],
        action="automation.generate",
        resource_type="automation",
        resource_id=request.task_id,
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": task["position"],
            "position_label": task["position_label"],
            "task_id": request.task_id,
            "task_label": task["label"],
            "input_preview": request.input_text[:500],
            "platform_draft_id": platform_draft.get("id") if platform_draft else None,
        },
    )

    return {
        "position": task["position"],
        "position_label": task["position_label"],
        "task_id": request.task_id,
        "task_label": task["label"],
        "answer": answer,
        "platform_draft": platform_draft,
    }


@router.post("/finance/report-analysis")
async def analyze_finance_report(
    files: list[UploadFile] | None = File(default=None),
    instruction: str = Form(default=""),
    output_format: str = Form(default="word"),
    current_user: dict = Depends(get_current_user),
):
    ensure_finance_user(current_user, "只有财务岗位或管理员可以分析财务报表。")

    if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, "automation-report_analysis"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="分析财务报表应用已被管理员禁用。",
        )

    uploaded_files = files or []
    has_manual_text = bool(instruction.strip())
    if not uploaded_files and not has_manual_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传财务报表文件，或手动输入财务报表内容。",
        )
    if len(uploaded_files) > MAX_REPORT_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"一次最多上传 {MAX_REPORT_FILES} 个财务报表文件。",
        )

    input_files: list[FinanceReportInputFile] = []
    total_bytes = 0
    for file in uploaded_files:
        filename = file.filename or "finance_report"
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{filename} 是空文件。",
            )
        if len(content) > MAX_REPORT_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{filename} 超过 10MB。",
            )
        total_bytes += len(content)
        input_files.append(FinanceReportInputFile(filename=filename, content=content))

    if not input_files and has_manual_text:
        manual_content = instruction.strip().encode("utf-8")
        total_bytes += len(manual_content)
        input_files.append(FinanceReportInputFile(filename="manual_finance_report.txt", content=manual_content))

    run_id = start_run(
        run_type="finance_report_analysis",
        app_id="automation-report_analysis",
        app_name="分析财务报表",
        entrypoint="/automation/finance/report-analysis",
        current_user=current_user,
        resource_type="automation",
        resource_id="finance_report_analysis",
        input_text=instruction,
        metadata={
            "source_file_count": len(input_files),
            "source_filenames": [item.filename for item in input_files],
            "source_bytes": total_bytes,
            "output_format": output_format,
        },
    )
    started_ms = now_ms()

    try:
        step_started_ms = now_ms()
        result = analyze_finance_report_files(
            files=input_files,
            instruction=instruction,
            output_format=output_format,
        )
        record_step(
            run_id=run_id,
            step_name="parse_files_and_analyze_report",
            step_order=1,
            status_value="succeeded",
            provider="document_loader_dashscope",
            resource_type="automation",
            resource_id="finance_report_analysis",
            input_text=instruction,
            output_text=result.answer,
            duration_ms=elapsed_ms(step_started_ms),
            metadata=result.metadata,
        )
        artifact_type = "word_file" if result.output_format == "word" else "excel_file"
        save_generated_file(
            run_id=run_id,
            content=result.content,
            artifact_type=artifact_type,
            mime_type=result.mime_type,
            filename=result.filename,
            current_user=current_user,
            metadata=result.metadata,
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=f"已生成 {result.filename}",
            duration_ms=elapsed_ms(started_ms),
            metadata=result.metadata,
        )
    except ValueError as error:
        record_step(
            run_id=run_id,
            step_name="parse_files_and_analyze_report",
            step_order=1,
            status_value="failed",
            provider="document_loader_dashscope",
            resource_type="automation",
            resource_id="finance_report_analysis",
            input_text=instruction,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "source_file_count": len(input_files),
                "source_filenames": [item.filename for item in input_files],
                "source_bytes": total_bytes,
                "output_format": output_format,
            },
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    write_audit_log(
        user_id=current_user["id"],
        action="automation.finance_report_analysis",
        resource_type="automation",
        resource_id="finance_report_analysis",
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            **result.metadata,
        },
    )

    encoded_filename = quote(result.filename)
    return Response(
        content=result.content,
        media_type=result.mime_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename={result.filename}; filename*=UTF-8''{encoded_filename}"
            ),
            "X-Automation-Output-Format": result.output_format,
        },
    )


@router.post("/finance/salary-export")
def export_finance_salary_file(
    request: FinanceSalaryExportRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin" and current_user.get("position") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有财务岗位或管理员可以导出员工工资表。",
        )

    if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, "automation-salary_summary"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="统计工资应用已被管理员禁用。",
        )

    intent = recognize_salary_export_intent(request.message)
    run_id = start_run(
        run_type="finance_salary_export",
        app_id="automation-salary_summary",
        app_name="统计工资",
        entrypoint="/automation/finance/salary-export",
        current_user=current_user,
        resource_type="erp",
        resource_id="Salary Slip",
        flow_reference=resolve_flow_execution_reference(
            flow_key="automation:finance:salary-export",
            current_user=current_user,
            execution_source="manual_form",
        ),
        input_text=request.message,
        metadata={
            "intent": intent.intent,
            "intent_confidence": intent.confidence,
            "period_label": intent.period_label,
            "start_date": intent.start_date.isoformat(),
            "end_date": intent.end_date.isoformat(),
            "output_format": intent.output_format,
            "matched_keywords": intent.matched_keywords,
        },
    )
    started_ms = now_ms()

    try:
        record_step(
            run_id=run_id,
            step_name="intent_recognition",
            step_order=1,
            status_value="succeeded" if intent.intent == "finance_salary_export" else "failed",
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
            },
        )
        step_started_ms = now_ms()
        skill_result = execute_skill(
            skill_id="finance_salary_export",
            payload={
                "message": request.message,
                "intent": intent,
                "metadata": {
                    "run_id": run_id,
                    "entrypoint": "/automation/finance/salary-export",
                },
            },
            current_user=current_user,
            source="automation_api",
        )
        attachment = _skill_result_attachment(skill_result)
        result_metadata = _skill_result_metadata(skill_result)
        record_step(
            run_id=run_id,
            step_name="erp_salary_query_and_excel_export",
            step_order=2,
            status_value="succeeded",
            provider=str(result_metadata.get("provider") or "skill_executor"),
            resource_type="erp",
            resource_id="Salary Slip",
            input_text=request.message,
            output_text=attachment["filename"],
            duration_ms=elapsed_ms(step_started_ms),
            metadata=result_metadata,
        )
        save_generated_file(
            run_id=run_id,
            content=attachment["content"],
            artifact_type="excel_file",
            mime_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment["filename"],
            current_user=current_user,
            metadata=result_metadata,
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=skill_result.answer or f"已生成 {attachment['filename']}",
            duration_ms=elapsed_ms(started_ms),
            metadata=result_metadata,
        )
    except ValueError as error:
        record_step(
            run_id=run_id,
            step_name="erp_salary_query_and_excel_export",
            step_order=2,
            status_value="failed",
            provider="erp_provider",
            resource_type="erp",
            resource_id="Salary Slip",
            input_text=request.message,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    write_audit_log(
        user_id=current_user["id"],
        action="automation.finance_salary_export",
        resource_type="erp",
        resource_id="Salary Slip",
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            **result_metadata,
        },
    )

    encoded_filename = quote(str(attachment["filename"]))
    return Response(
        content=attachment["content"],
        media_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename={attachment['filename']}; filename*=UTF-8''{encoded_filename}"
            ),
            "X-Automation-Intent": str(result_metadata.get("intent") or intent.intent),
            "X-Automation-Period": f"{intent.start_date.isoformat()}..{intent.end_date.isoformat()}",
            "X-Automation-Employee-Count": str(result_metadata.get("employee_count") or 0),
        },
    )


@router.post("/finance/salary-wechat-send/plan", response_model=FinanceSalaryWechatPlanResponse)
def plan_finance_salary_wechat_send(
    request: FinanceSalaryWechatPlanRequest,
    current_user: dict = Depends(get_current_user),
):
    ensure_finance_user(current_user, "只有财务岗位或管理员可以准备工资表微信发送任务。")
    if current_user.get("role") != "admin" and not is_ai_app_allowed(
        current_user,
        "automation-salary_wechat_send",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="工资表微信发送应用已被管理员禁用。",
        )

    intent = recognize_salary_wechat_send_intent(request.message)
    return {
        "intent": intent.intent,
        "confidence": intent.confidence,
        "period_label": intent.salary_intent.period_label,
        "recipient_name": intent.recipient_name,
        "missing_fields": intent.missing_fields,
        "plan": build_salary_wechat_plan(intent),
    }


@router.post("/finance/salary-wechat-send", response_model=FinanceSalaryWechatSendResponse)
def send_finance_salary_wechat(
    request: FinanceSalaryWechatSendRequest,
    current_user: dict = Depends(get_current_user),
):
    ensure_finance_user(current_user, "只有财务岗位或管理员可以准备工资表微信发送任务。")
    if current_user.get("role") != "admin" and not is_ai_app_allowed(
        current_user,
        "automation-salary_wechat_send",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="工资表微信发送应用已被管理员禁用。",
        )

    intent = recognize_salary_wechat_send_intent(request.message)
    if request.recipient_name:
        intent.recipient_name = request.recipient_name.strip()
        intent.missing_fields = [item for item in intent.missing_fields if item != "微信联系人"]
        if "微信" not in intent.missing_fields and intent.salary_intent.intent == "finance_salary_export":
            intent.intent = "finance_salary_wechat_send"
    try:
        ensure_salary_wechat_intent_ready(intent)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    run_id = start_run(
        run_type="finance_salary_wechat_send",
        app_id="automation-salary_wechat_send",
        app_name="工资表微信发送准备",
        entrypoint="/automation/finance/salary-wechat-send",
        current_user=current_user,
        resource_type="automation",
        resource_id="finance_salary_wechat_send",
        flow_reference=_resolve_optional_flow_reference(
            flow_key="automation:finance:salary-wechat-send",
            current_user=current_user,
            execution_source="manual_form",
        ),
        input_text=request.message,
        metadata={
            "recipient_name": intent.recipient_name,
            "recipient_confirmed": request.recipient_confirmed,
            "sensitive_data_confirmed": request.sensitive_data_confirmed,
            "intent_confidence": intent.confidence,
        },
    )
    started_ms = now_ms()
    artifact_id: str | None = None

    try:
        record_step(
            run_id=run_id,
            step_name="wechat_send_plan",
            step_order=1,
            status_value="succeeded",
            provider="rules",
            resource_type="automation",
            resource_id="finance_salary_wechat_send",
            input_text=request.message,
            output_text=build_salary_wechat_plan(intent),
            duration_ms=0,
            metadata={
                "recipient_name": intent.recipient_name,
                "recipient_confirmed": request.recipient_confirmed,
                "sensitive_data_confirmed": request.sensitive_data_confirmed,
            },
        )
        step_started_ms = now_ms()
        skill_result = execute_skill(
            skill_id="finance_salary_wechat_send",
            payload={
                "message": request.message,
                "intent": intent,
                "metadata": {
                    "run_id": run_id,
                    "entrypoint": "/automation/finance/salary-wechat-send",
                    "recipient_confirmed": request.recipient_confirmed,
                    "sensitive_data_confirmed": request.sensitive_data_confirmed,
                },
            },
            current_user=current_user,
            source="automation_api",
        )
        attachment = _skill_result_attachment(skill_result)
        result_metadata = _skill_result_metadata(skill_result)
        record_step(
            run_id=run_id,
            step_name="erp_salary_query_and_excel_export",
            step_order=2,
            status_value="succeeded",
            provider=str((result_metadata.get("salary") or {}).get("provider") or "skill_executor"),
            resource_type="erp",
            resource_id="Salary Slip",
            input_text=request.message,
            output_text=attachment["filename"],
            duration_ms=elapsed_ms(step_started_ms),
            metadata=result_metadata,
        )
        artifact_id = save_generated_file(
            run_id=run_id,
            content=attachment["content"],
            artifact_type="excel_file",
            mime_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment["filename"],
            current_user=current_user,
            metadata=result_metadata,
        )
        if request.recipient_confirmed and request.sensitive_data_confirmed:
            wechat_execution = dispatch_salary_wechat_send_task(
                dispatch=result_metadata.get("wechat_send") or {},
                artifact_id=artifact_id,
                artifact_filename=attachment["filename"],
                current_user=current_user,
            )
        else:
            wechat_execution = build_wechat_prepare_confirmation_task(
                dispatch=result_metadata.get("wechat_send") or {},
                artifact_id=artifact_id,
                artifact_filename=attachment["filename"],
                current_user=current_user,
            )
        result_metadata = {
            **result_metadata,
            "wechat_send": wechat_execution,
            "business_status": wechat_execution["status"],
            "business_status_label": wechat_execution.get("status_label"),
            "artifact_id": artifact_id,
        }
        record_artifact(
            run_id=run_id,
            artifact_type="wechat_send_task",
            name=f"微信待发送：{intent.recipient_name}",
            external_ref="personal_wechat",
            metadata=wechat_execution,
        )
        record_step(
            run_id=run_id,
            step_name=(
                "wechat_rpa_prepare"
                if request.recipient_confirmed and request.sensitive_data_confirmed
                else "wechat_confirmation_required"
            ),
            step_order=3,
            status_value=run_record_status_for_salary_wechat(wechat_execution["status"]),
            provider=str(wechat_execution.get("executor_type") or "confirmation_required"),
            resource_type="external_automation",
            resource_id="personal_wechat",
            input_text={"recipient_name": intent.recipient_name},
            output_text=wechat_execution.get("message"),
            duration_ms=0,
            metadata=wechat_execution,
        )
        mcp_tool_calls = wechat_execution.get("mcp_tool_calls") if isinstance(wechat_execution.get("mcp_tool_calls"), list) else []
        _record_mcp_tool_steps(
            run_id=run_id,
            traces=mcp_tool_calls,
            start_order=4,
        )
        finish_run(
            run_id,
            status_value=run_record_status_for_salary_wechat(wechat_execution["status"]),
            output_text=wechat_execution.get("message") or skill_result.answer,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                **result_metadata,
                "recipient_confirmed": request.recipient_confirmed,
                "sensitive_data_confirmed": request.sensitive_data_confirmed,
                "manual_final_send_required": True,
            },
        )
    except ValueError as error:
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    write_audit_log(
        user_id=current_user["id"],
        action="automation.finance_salary_wechat_send",
        resource_type="automation",
        resource_id="finance_salary_wechat_send",
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            "run_id": run_id,
            "recipient_name": intent.recipient_name,
            "recipient_confirmed": request.recipient_confirmed,
            "sensitive_data_confirmed": request.sensitive_data_confirmed,
            "manual_final_send_required": True,
            "artifact_id": artifact_id,
            **result_metadata,
        },
    )

    attachment = _skill_result_attachment(skill_result)
    wechat_send = result_metadata.get("wechat_send") or {}
    return {
        "run_id": run_id,
        "status": wechat_send.get("status") or "waiting_manual_send",
        "status_label": wechat_send.get("status_label") or "等待人工发送",
        "answer": (
            f"{skill_result.answer or '工资表已生成。'}\n"
            f"{wechat_send.get('message') or '文件已生成，等待准备微信确认。'}"
        ),
        "filename": attachment["filename"],
        "artifact_id": artifact_id,
        "download_path": wechat_send.get("download_path"),
        "recipient_name": str(intent.recipient_name),
        "plan": wechat_send.get("plan") or build_salary_wechat_plan(intent),
        "execution": wechat_send,
    }


@router.post("/files/enterprise-wechat-send/confirm", response_model=FinanceEnterpriseWechatFileSendConfirmResponse)
def confirm_enterprise_wechat_file_send(
    request: FinanceEnterpriseWechatFileSendConfirmRequest,
    current_user: dict = Depends(get_current_user),
):
    return _confirm_enterprise_wechat_file_send(request, current_user, legacy_finance_endpoint=False)


@router.post("/finance/enterprise-wechat-file-send/confirm", response_model=FinanceEnterpriseWechatFileSendConfirmResponse)
def confirm_finance_enterprise_wechat_file_send(
    request: FinanceEnterpriseWechatFileSendConfirmRequest,
    current_user: dict = Depends(get_current_user),
):
    return _confirm_enterprise_wechat_file_send(request, current_user, legacy_finance_endpoint=True)


def _confirm_enterprise_wechat_file_send(
    request: FinanceEnterpriseWechatFileSendConfirmRequest,
    current_user: dict,
    *,
    legacy_finance_endpoint: bool,
) -> dict[str, Any]:
    if not request.recipient_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先确认企业微信接收对象。",
        )

    artifact_ids = _enterprise_wechat_confirm_artifact_ids(request)
    storage_references = [
        get_generated_file_storage_reference(item, current_user=current_user)
        for item in artifact_ids
    ]
    storage_reference = storage_references[0]
    generated_artifacts = [
        _enterprise_wechat_generated_artifact_from_storage_reference(item)
        for item in storage_references
    ]
    filename = request.filename or _enterprise_wechat_filename_summary(generated_artifacts)
    recipient_name = request.recipient_name.strip()
    sensitive_required = any(
        _enterprise_wechat_file_requires_sensitive_confirmation(
            filename=str(item.get("filename") or filename),
            storage_reference=item,
            source_workflow_id=request.source_workflow_id,
        )
        for item in storage_references
    )
    if legacy_finance_endpoint or sensitive_required:
        _ensure_sensitive_enterprise_wechat_file_allowed(
            current_user=current_user,
            source_workflow_id=request.source_workflow_id,
            filename=str(filename),
        )
    if sensitive_required and not request.sensitive_data_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="工资、财务或客户隐私文件属于敏感数据，请先确认允许发送。",
        )

    app_id = _enterprise_wechat_file_send_app_id(request.source_workflow_id, sensitive_required)
    flow_key = _enterprise_wechat_file_send_flow_key(request.source_workflow_id, sensitive_required)
    entrypoint = (
        "/automation/finance/enterprise-wechat-file-send/confirm"
        if legacy_finance_endpoint
        else "/automation/files/enterprise-wechat-send/confirm"
    )
    run_id = start_run(
        run_type="enterprise_wechat_file_send",
        app_id=app_id,
        app_name="企业微信文件发送",
        entrypoint=entrypoint,
        current_user=current_user,
        thread_id=request.thread_id,
        resource_type="generated_file",
        resource_id=request.artifact_id,
        flow_reference=_resolve_optional_flow_reference(
            flow_key=flow_key,
            current_user=current_user,
            execution_source="chat_confirmation",
        ),
        input_text=request.source_message or f"发送 {filename} 到企业微信 {recipient_name}",
        metadata={
            "artifact_id": request.artifact_id,
            "artifact_ids": artifact_ids,
            "filename": filename,
            "filenames": [item["filename"] for item in generated_artifacts],
            "recipient_name": recipient_name,
            "recipient_candidate_id": request.recipient_candidate_id,
            "source_workflow_id": request.source_workflow_id,
            "source_message_id": request.source_message_id,
            "thread_id": request.thread_id,
            "recipient_confirmed": True,
            "sensitive_data_confirmed": bool(request.sensitive_data_confirmed),
            "sensitive_required": sensitive_required,
            "message_body": "",
        },
    )
    started_ms = now_ms()

    try:
        record_step(
            run_id=run_id,
            step_name="enterprise_wechat_sensitive_confirmation",
            step_order=1,
            status_value="succeeded",
            provider="backend_policy",
            resource_type="generated_file",
            resource_id=request.artifact_id,
            input_text={
                "recipient_name": recipient_name,
                "recipient_candidate_id": request.recipient_candidate_id,
                "artifact_id": request.artifact_id,
                "artifact_ids": artifact_ids,
            },
            output_text="接收对象和敏感数据确认通过。",
            duration_ms=0,
            metadata={
                "recipient_confirmed": True,
                "sensitive_data_confirmed": bool(request.sensitive_data_confirmed),
                "sensitive_required": sensitive_required,
                "message_body": "",
            },
        )
        execution = dispatch_enterprise_wechat_file_send_task(
            artifact_id=request.artifact_id,
            artifact_ids=artifact_ids,
            recipient_candidate_id=request.recipient_candidate_id,
            recipient=request.recipient,
            recipient_name=recipient_name,
            current_user=current_user,
            sensitive_data_confirmed=True,
            requires_sensitive_confirmation=sensitive_required,
        )
        record_step(
            run_id=run_id,
            step_name="enterprise_wechat_file_send",
            step_order=2,
            status_value=run_record_status_for_salary_wechat(execution["status"]),
            provider=str(execution.get("executor_type") or "enterprise_wechat_api"),
            resource_type="enterprise_wechat",
            resource_id=recipient_name,
            input_text={
                "artifact_id": request.artifact_id,
                "artifact_ids": artifact_ids,
                "filename": filename,
                "recipient_name": recipient_name,
                "recipient_candidate_id": request.recipient_candidate_id,
            },
            output_text=execution.get("message"),
            duration_ms=elapsed_ms(started_ms),
            metadata=execution,
        )
        finish_run(
            run_id,
            status_value=run_record_status_for_salary_wechat(execution["status"]),
            output_text=execution.get("message"),
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "wechat_send": execution,
                "business_status": execution["status"],
                "business_status_label": execution.get("status_label"),
                "artifact_id": request.artifact_id,
                "artifact_ids": artifact_ids,
                "filename": filename,
                "generated_artifacts": generated_artifacts,
                "recipient_name": recipient_name,
                "source_workflow_id": request.source_workflow_id,
                "source_message_id": request.source_message_id,
                "thread_id": request.thread_id,
                "sensitive_required": sensitive_required,
                "wechat_error_code": execution.get("wechat_error_code"),
                "wechat_error_message": execution.get("wechat_error_message"),
                "api_diagnostics": execution.get("api_diagnostics"),
                "request_response_trace": execution.get("request_response_trace"),
                "admin_error_detail": execution.get("admin_error_detail"),
                "message_body": "",
            },
        )
    except Exception as error:
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    answer = _enterprise_wechat_send_answer(
        execution=execution,
        filename=str(filename),
        recipient_name=recipient_name,
    )
    if request.thread_id and request.source_message_id:
        _update_enterprise_wechat_send_message(
            thread_id=request.thread_id,
            message_id=request.source_message_id,
            current_user=current_user,
            answer=answer,
            execution=execution,
            artifact_id=request.artifact_id,
            filename=str(filename),
            generated_artifacts=generated_artifacts,
            source_workflow_id=request.source_workflow_id,
            sensitive_required=sensitive_required,
        )

    write_audit_log(
        user_id=current_user["id"],
        action="automation.enterprise_wechat_file_send",
        resource_type="generated_file",
        resource_id=request.artifact_id,
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            "run_id": run_id,
            "recipient_name": recipient_name,
            "recipient_candidate_id": request.recipient_candidate_id,
            "artifact_id": request.artifact_id,
            "artifact_ids": artifact_ids,
            "status": execution["status"],
            "source_workflow_id": request.source_workflow_id,
            "source_message_id": request.source_message_id,
            "sensitive_required": sensitive_required,
            "wechat_error_code": execution.get("wechat_error_code"),
            "wechat_error_message": execution.get("wechat_error_message"),
            "api_diagnostics": execution.get("api_diagnostics"),
            "request_response_trace": execution.get("request_response_trace"),
            "admin_error_detail": execution.get("admin_error_detail"),
            "send_result": execution.get("send_result"),
            "logs": execution.get("logs"),
            "message_body": "",
        },
    )

    return {
        "run_id": run_id,
        "status": execution["status"],
        "status_label": execution.get("status_label") or execution["status"],
        "answer": answer,
        "filename": str(filename),
        "artifact_id": request.artifact_id,
        "download_path": execution.get("download_path") or f"/files/{request.artifact_id}/download",
        "recipient_name": recipient_name,
        "execution": execution,
    }


@router.post("/finance/wechat-attachment/prepare", response_model=FinanceWechatAttachmentPrepareResponse)
def prepare_finance_wechat_attachment(
    request: FinanceWechatAttachmentPrepareRequest,
    current_user: dict = Depends(get_current_user),
):
    ensure_finance_user(current_user, "只有财务岗位或管理员可以准备个人微信附件。")
    if current_user.get("role") != "admin" and not is_ai_app_allowed(
        current_user,
        "automation-salary_wechat_send",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="工资表微信发送应用已被管理员禁用。",
        )
    if not request.recipient_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先确认微信联系人，再准备个人微信附件。",
        )
    if not request.sensitive_data_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="工资或财务文件属于敏感数据，请先确认允许准备发送。",
        )

    recipient_name = request.recipient_name.strip()
    storage_reference = get_generated_file_storage_reference(
        request.artifact_id,
        current_user=current_user,
    )
    filename = request.filename or storage_reference["filename"]
    run_id = start_run(
        run_type="finance_wechat_attachment_prepare",
        app_id="automation-salary_wechat_send",
        app_name="个人微信附件准备",
        entrypoint="/automation/finance/wechat-attachment/prepare",
        current_user=current_user,
        resource_type="generated_file",
        resource_id=request.artifact_id,
        flow_reference=_resolve_optional_flow_reference(
            flow_key="automation:finance:wechat-attachment-prepare",
            current_user=current_user,
            execution_source="manual_confirm",
        ),
        input_text=request.source_message or f"准备通过个人微信发送 {filename} 给 {recipient_name}",
        metadata={
            "artifact_id": request.artifact_id,
            "filename": filename,
            "recipient_name": recipient_name,
            "source_workflow_id": request.source_workflow_id,
            "recipient_confirmed": request.recipient_confirmed,
            "sensitive_data_confirmed": request.sensitive_data_confirmed,
            "manual_final_send_required": True,
        },
    )
    started_ms = now_ms()

    try:
        record_step(
            run_id=run_id,
            step_name="wechat_sensitive_confirmation",
            step_order=1,
            status_value="succeeded",
            provider="backend_policy",
            resource_type="generated_file",
            resource_id=request.artifact_id,
            input_text={
                "recipient_name": recipient_name,
                "artifact_id": request.artifact_id,
            },
            output_text="联系人和敏感数据确认通过，准备调用外部微信执行器。",
            duration_ms=0,
            metadata={
                "recipient_confirmed": True,
                "sensitive_data_confirmed": True,
                "manual_final_send_required": True,
            },
        )
        dispatch = {
            "status": "generated",
            "status_label": "文件已生成",
            "message": "文件已生成，正在准备个人微信附件。",
            "executor_type": "tagui_or_manual",
            "executor_mode": "manual_final_click",
            "configured": True,
            "platform": "mac",
            "target_app": "personal_wechat",
            "recipient_name": recipient_name,
            "manual_final_send_required": True,
            "requires_recipient_confirmation": True,
            "requires_sensitive_confirmation": True,
            "payload": {
                "action": "prepare_personal_wechat_file_send",
                "platform": "mac",
                "target_app": "personal_wechat",
                "recipient_name": recipient_name,
                "filename": filename,
                "manual_final_send_required": True,
                "source": "manual_confirm",
                "requested_by": current_user.get("id"),
                "source_message": request.source_message,
            },
            "plan": {
                "title": "个人微信附件准备",
                "summary": f"打开个人微信，搜索 {recipient_name}，并把 {filename} 作为附件放入聊天窗口。",
                "recipient_name": recipient_name,
                "manual_final_send_required": True,
                "steps": [
                    {"key": "confirm", "label": "确认联系人和敏感数据"},
                    {"key": "file", "label": "读取生成文件本机路径"},
                    {"key": "rpa", "label": "打开微信并粘贴附件"},
                    {"key": "manual_send", "label": "等待人工点击发送"},
                ],
            },
            "logs": [
                {"level": "warning", "message": "个人微信最终发送必须由人工点击完成。"},
            ],
        }
        execution = dispatch_salary_wechat_send_task(
            dispatch=dispatch,
            artifact_id=request.artifact_id,
            artifact_filename=str(filename),
            current_user=current_user,
        )
        record_step(
            run_id=run_id,
            step_name="wechat_rpa_prepare",
            step_order=2,
            status_value=run_record_status_for_salary_wechat(execution["status"]),
            provider=str(execution.get("executor_type") or "tagui_or_manual"),
            resource_type="external_automation",
            resource_id="personal_wechat",
            input_text={"recipient_name": recipient_name, "artifact_id": request.artifact_id},
            output_text=execution.get("message"),
            duration_ms=elapsed_ms(started_ms),
            metadata=execution,
        )
        mcp_tool_calls = execution.get("mcp_tool_calls") if isinstance(execution.get("mcp_tool_calls"), list) else []
        _record_mcp_tool_steps(
            run_id=run_id,
            traces=mcp_tool_calls,
            start_order=3,
        )
        finish_run(
            run_id,
            status_value=run_record_status_for_salary_wechat(execution["status"]),
            output_text=execution.get("message"),
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "wechat_send": execution,
                "business_status": execution["status"],
                "business_status_label": execution.get("status_label"),
                "artifact_id": request.artifact_id,
                "filename": filename,
                "recipient_name": recipient_name,
                "source_workflow_id": request.source_workflow_id,
                "manual_final_send_required": True,
            },
        )
    except Exception as error:
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    write_audit_log(
        user_id=current_user["id"],
        action="automation.finance_wechat_attachment_prepare",
        resource_type="generated_file",
        resource_id=request.artifact_id,
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            "run_id": run_id,
            "recipient_name": recipient_name,
            "artifact_id": request.artifact_id,
            "status": execution["status"],
            "manual_final_send_required": True,
        },
    )

    return {
        "run_id": run_id,
        "status": execution["status"],
        "status_label": execution.get("status_label") or execution["status"],
        "answer": execution.get("message") or "个人微信附件已准备，请人工确认后发送。",
        "filename": str(filename),
        "artifact_id": request.artifact_id,
        "download_path": execution.get("download_path"),
        "recipient_name": recipient_name,
        "execution": execution,
    }


def _enterprise_wechat_send_answer(
    *,
    execution: dict[str, Any],
    filename: str,
    recipient_name: str,
) -> str:
    status_value = str(execution.get("status") or "")
    if status_value == "completed":
        return f"企业微信文件已发送给“{recipient_name}”。\n文件：{filename}\n本次消息没有附带正文说明。"
    if status_value == "waiting_executor":
        return (
            f"文件已经确认，但企业微信真实发送还没有完成。\n"
            f"接收对象：{recipient_name}\n"
            f"文件：{filename}\n"
            f"原因：{execution.get('message') or '企业微信发送通道未启用或未配置。'}"
        )
    if status_value == "waiting_recipient_selection":
        return f"还需要先选择正确的企业微信接收对象，暂未发送文件：{filename}"
    return f"企业微信文件发送失败：{execution.get('message') or '请联系管理员查看运行记录。'}\n文件：{filename}"


def _enterprise_wechat_confirm_artifact_ids(request: FinanceEnterpriseWechatFileSendConfirmRequest) -> list[str]:
    values = [str(item or "").strip() for item in request.artifact_ids]
    values.append(str(request.artifact_id or "").strip())
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _enterprise_wechat_generated_artifact_from_storage_reference(item: dict[str, Any]) -> dict[str, Any]:
    artifact_id = str(item["id"])
    return {
        "artifact_id": artifact_id,
        "filename": str(item.get("filename") or artifact_id),
        "download_path": f"/files/{artifact_id}/download",
        "mime_type": str(item.get("mime_type") or "application/octet-stream"),
    }


def _enterprise_wechat_filename_summary(generated_artifacts: list[dict[str, Any]]) -> str:
    return "、".join(str(item.get("filename") or item.get("artifact_id") or "文件") for item in generated_artifacts)


def _enterprise_wechat_file_requires_sensitive_confirmation(
    *,
    filename: str,
    storage_reference: dict[str, Any],
    source_workflow_id: str | None,
) -> bool:
    metadata = storage_reference.get("metadata") if isinstance(storage_reference.get("metadata"), dict) else {}
    text = " ".join(
        str(item or "")
        for item in [
            filename,
            storage_reference.get("artifact_type"),
            storage_reference.get("app_id"),
            storage_reference.get("app_name"),
            storage_reference.get("run_type"),
            source_workflow_id,
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


def _ensure_sensitive_enterprise_wechat_file_allowed(
    *,
    current_user: dict,
    source_workflow_id: str | None,
    filename: str,
) -> None:
    if current_user.get("role") == "admin":
        return

    text = f"{source_workflow_id or ''} {filename}".lower()
    is_finance_sensitive = any(keyword in text for keyword in ["salary", "工资", "finance", "财务", "settlement", "reconciliation"])
    if is_finance_sensitive and current_user.get("position") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有财务岗位或管理员可以发送工资、财务文件到企业微信。",
        )
    if is_finance_sensitive and not is_ai_app_allowed(current_user, "automation-salary_wechat_send"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="工资表微信发送应用已被管理员禁用。",
        )


def _enterprise_wechat_file_send_app_id(source_workflow_id: str | None, sensitive_required: bool) -> str:
    workflow_id = str(source_workflow_id or "").strip()
    if workflow_id in {"finance_salary_wechat_send", "finance_monthly_package_wechat_send"}:
        return "automation-salary_wechat_send"
    return "automation-enterprise_wechat_file_send"


def _enterprise_wechat_file_send_flow_key(source_workflow_id: str | None, sensitive_required: bool) -> str:
    workflow_id = str(source_workflow_id or "").strip()
    if workflow_id in {"finance_salary_wechat_send", "finance_monthly_package_wechat_send"}:
        return "automation:finance:salary-wechat-send"
    return "automation:platform:enterprise-wechat-file-send"


def _update_enterprise_wechat_send_message(
    *,
    thread_id: str,
    message_id: str,
    current_user: dict,
    answer: str,
    execution: dict[str, Any],
    artifact_id: str,
    filename: str,
    generated_artifacts: list[dict[str, Any]] | None,
    source_workflow_id: str | None,
    sensitive_required: bool,
) -> None:
    thread = get_thread_for_user(thread_id, current_user)
    if thread is None:
        return
    artifacts = generated_artifacts or [
        {
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": f"/files/{artifact_id}/download",
        }
    ]
    message_metadata = {
        "intent": "enterprise_wechat_file_send",
        "risk_level": "high" if sensitive_required else "medium",
        "attachments": [
            {
                "type": _artifact_type_for_filename(str(item.get("filename") or "")),
                "filename": str(item.get("filename") or "文件"),
                "metadata": {
                    "artifact_id": item.get("artifact_id"),
                    "download_path": item.get("download_path") or f"/files/{item.get('artifact_id')}/download",
                },
            }
            for item in artifacts
        ],
        "approval_result": {
            "status": execution.get("status"),
            "status_label": execution.get("status_label"),
            "requires_recipient_confirmation": True,
            "requires_sensitive_data_confirmation": sensitive_required,
        },
        "automation": {
            "type": "enterprise_wechat_file_send",
            "workflow_id": source_workflow_id or "enterprise_wechat_file_send",
            "status": execution.get("status"),
            "status_label": execution.get("status_label"),
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": f"/files/{artifact_id}/download",
            "generated_artifacts": artifacts,
            "wechat_send": execution,
        },
    }
    updated = update_chat_message(
        message_id=message_id,
        thread_id=thread_id,
        content=answer,
        metadata=message_metadata,
    )
    if updated is None:
        update_latest_chat_message_by_artifact(
            thread_id=thread_id,
            artifact_id=artifact_id,
            content=answer,
            metadata=message_metadata,
        )


def _artifact_type_for_filename(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith((".docx", ".doc")):
        return "word_file"
    return "excel_file"


def _save_enterprise_wechat_send_message(
    *,
    thread_id: str,
    current_user: dict,
    answer: str,
    execution: dict[str, Any],
    artifact_id: str,
    filename: str,
) -> None:
    thread = get_thread_for_user(thread_id, current_user)
    if thread is None:
        return
    save_chat_message(
        thread_id=thread_id,
        user_id=current_user["id"],
        role="assistant",
        content=answer,
        metadata={
            "entrypoint": "chat_confirmation",
            "intent": "finance_salary_wechat_send",
            "risk_level": "high",
            "attachments": [
                {
                    "type": "excel_file",
                    "filename": filename,
                    "metadata": {
                        "artifact_id": artifact_id,
                        "download_path": f"/files/{artifact_id}/download",
                    },
                }
            ],
            "approval_result": {
                "status": execution.get("status"),
                "status_label": execution.get("status_label"),
            },
            "automation": {
                "type": "finance_salary_wechat_send",
                "workflow_id": "finance_salary_wechat_send",
                "status": execution.get("status"),
                "status_label": execution.get("status_label"),
                "artifact_id": artifact_id,
                "filename": filename,
                "download_path": f"/files/{artifact_id}/download",
                "wechat_send": execution,
            },
        },
    )


@router.post("/finance/salary-wechat-send/stream")
def send_finance_salary_wechat_stream(
    request: FinanceSalaryWechatSendRequest,
    current_user: dict = Depends(get_current_user),
):
    intent = recognize_salary_wechat_send_intent(request.message)
    period_label = intent.salary_intent.period_label
    recipient_name = request.recipient_name or intent.recipient_name

    def event_generator():
        try:
            yield _finance_wechat_progress_sse(
                step_key="understanding",
                label="正在理解你的需求",
                data={
                    "period_label": period_label,
                    "recipient_name": recipient_name,
                },
            )
            yield _finance_wechat_progress_sse(
                step_key="permission",
                label="正在检查财务权限",
                detail="正在确认岗位、应用启用状态和 ERP 资源权限",
            )
            yield _finance_wechat_progress_sse(
                step_key="erp_salary_query",
                label=f"正在查询 ERPNext 工资单（{period_label}）",
                data={
                    "period_label": period_label,
                },
            )
            response = send_finance_salary_wechat(request, current_user)
            yield _finance_wechat_progress_sse(
                step_key="excel_export",
                label="正在生成工资表 Excel",
                detail=response.get("filename"),
                data={
                    "filename": response.get("filename"),
                    "artifact_id": response.get("artifact_id"),
                },
            )
            if response.get("status") == "waiting_wechat_confirmation":
                yield _finance_wechat_progress_sse(
                    step_key="wechat_confirm",
                    label="等待你确认是否准备微信附件",
                    status_value="blocked",
                    detail="工资表已生成；确认后系统会打开微信、搜索联系人并附上文件，仍不会自动点击发送",
                    data={
                        "recipient_name": response.get("recipient_name") or recipient_name,
                        "artifact_id": response.get("artifact_id"),
                    },
                )
            else:
                yield _finance_wechat_progress_sse(
                    step_key="wechat_prepare",
                    label=f"正在准备微信发送任务（{response.get('recipient_name') or recipient_name or '待确认联系人'}）",
                    data={
                        "recipient_name": response.get("recipient_name") or recipient_name,
                    },
                )
                yield _finance_wechat_progress_sse(
                    step_key="manual_confirm",
                    label="等待你确认并人工发送",
                    status_value="blocked",
                    detail="系统不会自动点击微信发送按钮",
                )
            yield _format_sse("done", response)
        except Exception as error:
            yield _finance_wechat_progress_sse(
                step_key="failed",
                label="执行没有完成",
                status_value="failed",
            )
            yield _format_sse(
                "error",
                {
                    "message": _automation_business_error_message(error, current_user),
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


@router.get("/finance/salary-wechat-send/{run_id}/status", response_model=FinanceSalaryWechatStatusResponse)
def get_finance_salary_wechat_status(
    run_id: str,
    current_user: dict = Depends(get_current_user),
):
    detail = get_run_detail(run_id, current_user=current_user)
    run = detail["run"]
    if run.get("run_type") != "finance_salary_wechat_send":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工资表微信发送任务不存在")

    metadata = run.get("metadata") or {}
    execution = metadata.get("wechat_send") if isinstance(metadata.get("wechat_send"), dict) else {}
    artifact_id = metadata.get("artifact_id")
    filename = execution.get("artifact_filename")
    download_path = execution.get("download_path")

    for artifact in detail.get("artifacts") or []:
        if artifact.get("artifact_type") == "excel_file":
            artifact_id = artifact_id or artifact.get("id")
            filename = filename or artifact.get("name")
            if artifact_id and not download_path:
                download_path = f"/files/{artifact_id}/download"
            break

    business_status = execution.get("status") or metadata.get("business_status")
    if not business_status:
        business_status = "failed" if run.get("status") == "failed" else "waiting_manual_send"

    return {
        "run_id": run_id,
        "run_status": run["status"],
        "status": str(business_status),
        "status_label": str(execution.get("status_label") or metadata.get("business_status_label") or business_status),
        "answer": run.get("output_preview"),
        "filename": filename,
        "artifact_id": artifact_id,
        "download_path": download_path,
        "recipient_name": execution.get("recipient_name") or metadata.get("recipient_name"),
        "executor_type": execution.get("executor_type"),
        "manual_final_send_required": bool(execution.get("manual_final_send_required", True)),
        "steps": detail.get("steps") or [],
        "logs": execution.get("logs") if isinstance(execution.get("logs"), list) else [],
    }


@router.post("/finance/excel-transform")
async def transform_finance_excel_file(
    file: UploadFile | None = File(default=None),
    instruction: str = Form(default=""),
    erp_resources: str = Form(default="[]"),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin" and current_user.get("position") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有财务岗位或管理员可以使用财务 Excel 生成功能。",
        )

    if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, "finance-excel-transform"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="财务 Excel 生成已被管理员禁用。",
        )

    source_filename = file.filename if file and file.filename else "finance_erp_generated.xlsx"
    content: bytes | None = None
    source_mode = "erp_context"
    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请上传非空 Excel 文件，或不上传文件直接选择/说明要使用的财务 ERP 表。",
            )

        if len(content) > MAX_EXCEL_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Excel 文件不能超过 8MB。",
            )
        source_mode = "uploaded_excel"

    explicit_erp_resources = _parse_finance_excel_erp_resources(
        raw_value=erp_resources,
        current_user=current_user,
    )
    inferred_erp_resources = (
        []
        if explicit_erp_resources
        else _infer_finance_excel_erp_resources_from_instruction(
            instruction=instruction,
            current_user=current_user,
        )
    )
    selected_erp_resources = explicit_erp_resources or inferred_erp_resources
    if content is None and not selected_erp_resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传 Excel 文件，或选择财务 ERP 表，或在要求中说明要使用工资、销售发票、收付款、总账、采购发票等哪类财务数据。",
        )

    run_id = start_run(
        run_type="finance_excel_transform",
        app_id="finance-excel-transform",
        app_name="财务 Excel 生成",
        entrypoint="/automation/finance/excel-transform",
        current_user=current_user,
        resource_type="automation",
        resource_id="finance_excel_transform",
        flow_reference=resolve_flow_execution_reference(
            flow_key="automation:finance:excel-file-transform",
            current_user=current_user,
            execution_source="manual_file_upload" if content is not None else "natural_language_erp_generate",
        ),
        input_text=instruction,
        metadata={
            "source_filename": source_filename,
            "source_mode": source_mode,
            "source_bytes": len(content or b""),
            "explicit_erp_resources": explicit_erp_resources,
            "inferred_erp_resources": inferred_erp_resources,
            "selected_erp_resources": selected_erp_resources,
        },
    )
    started_ms = now_ms()

    try:
        erp_context = _query_finance_excel_erp_context(selected_erp_resources)
        if selected_erp_resources:
            record_step(
                run_id=run_id,
                step_name="finance_erp_context_query",
                step_order=1,
                status_value="succeeded",
                provider=erp_context[0]["provider"] if erp_context else "erp",
                resource_type="erp",
                resource_id=",".join(selected_erp_resources),
                input_text=",".join(selected_erp_resources),
                output_text=f"已读取 {len(erp_context)} 个财务 ERP 表上下文",
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "selected_erp_resources": selected_erp_resources,
                    "erp_resources": [
                        {
                            "resource": item["resource"],
                            "label": item["label"],
                            "status": item["status"],
                            "ok": item["ok"],
                            "result_count": len(item.get("items") or []),
                        }
                        for item in erp_context
                    ],
                },
            )
        step_started_ms = now_ms()
        skill_result = execute_skill(
            skill_id="finance_excel_settlement",
            payload={
                "source_filename": source_filename,
                "content": content,
                "instruction": instruction,
                "erp_context": erp_context,
                "erp_resources": selected_erp_resources,
                "metadata": {
                    "run_id": run_id,
                    "entrypoint": "/automation/finance/excel-transform",
                },
            },
            current_user=current_user,
            source="automation_api",
        )
        attachment = _skill_result_attachment(skill_result)
        result_metadata = _skill_result_metadata(skill_result)
        record_step(
            run_id=run_id,
            step_name="finance_excel_transform",
            step_order=2 if selected_erp_resources else 1,
            status_value="succeeded",
            provider="skill_executor",
            resource_type="automation",
            resource_id="finance_excel_transform",
            input_text=instruction,
            output_text=attachment["filename"],
            duration_ms=elapsed_ms(step_started_ms),
            metadata=result_metadata,
        )
        save_generated_file(
            run_id=run_id,
            content=attachment["content"],
            artifact_type="excel_file",
            mime_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment["filename"],
            current_user=current_user,
            metadata=result_metadata,
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=skill_result.answer or f"已生成 {attachment['filename']}",
            duration_ms=elapsed_ms(started_ms),
            metadata=result_metadata,
        )
    except ValueError as error:
        record_step(
            run_id=run_id,
            step_name="finance_excel_transform",
            step_order=1,
            status_value="failed",
            provider="pandas_openpyxl_dashscope",
            resource_type="automation",
            resource_id="finance_excel_transform",
            input_text=instruction,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "source_filename": source_filename,
                "source_mode": source_mode,
                "source_bytes": len(content or b""),
                "explicit_erp_resources": explicit_erp_resources,
                "inferred_erp_resources": inferred_erp_resources,
                "selected_erp_resources": selected_erp_resources,
            },
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    write_audit_log(
        user_id=current_user["id"],
        action="automation.finance_excel_transform",
        resource_type="automation",
        resource_id="finance_excel_transform",
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            **result_metadata,
        },
    )

    encoded_filename = quote(str(attachment["filename"]))
    return Response(
        content=attachment["content"],
        media_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename={attachment['filename']}; filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


def _parse_finance_excel_erp_resources(
    *,
    raw_value: str,
    current_user: dict,
) -> list[str]:
    value = (raw_value or "").strip()
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in value.split(",")]

    if isinstance(parsed, str):
        candidates = [parsed]
    elif isinstance(parsed, list):
        candidates = [str(item).strip() for item in parsed]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ERP 表选择格式错误，请重新选择财务 ERP 表。",
        )

    finance_scopes = set(erp_scopes_for_position("finance"))
    selected: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue

        resource = resolve_resource_name(candidate)
        if resource is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"未知 ERP 资源：{candidate}",
            )

        if resource not in finance_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"财务 Excel 生成只能选择财务岗位 ERP 表：{resource}",
            )

        ensure_erp_resource_allowed(current_user, resource)

        if resource not in selected:
            selected.append(resource)

    if len(selected) > MAX_FINANCE_EXCEL_ERP_RESOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"一次最多选择 {MAX_FINANCE_EXCEL_ERP_RESOURCES} 张财务 ERP 表。",
        )

    return selected


def _infer_finance_excel_erp_resources_from_instruction(
    *,
    instruction: str,
    current_user: dict,
) -> list[str]:
    text = " ".join((instruction or "").strip().split())
    if not text:
        return []

    normalized = text.lower()
    finance_scopes = list(erp_scopes_for_position("finance"))
    matched: list[str] = []

    for resource in finance_scopes:
        definition = ERP_RESOURCE_CATALOG.get(resource)
        if not definition:
            continue

        candidates = [
            resource,
            str(definition.get("label") or ""),
            str(definition.get("description") or ""),
            *[str(item) for item in definition.get("keywords", [])],
            *[str(item) for item in definition.get("provider_refs", {}).values() if item],
        ]
        if any(candidate and candidate.lower() in normalized for candidate in candidates):
            matched.append(resource)

    if any(keyword in normalized for keyword in ["利润", "利润表", "成本", "费用", "盈亏", "profit", "margin"]):
        _append_resource_if_allowed(matched, "GL Entry")
        _append_resource_if_allowed(matched, "Sales Invoice")
        _append_resource_if_allowed(matched, "Purchase Invoice")

    if any(keyword in normalized for keyword in ["对账", "核对", "结算", "回款", "到账", "未收", "应收", "payment", "settlement"]):
        _append_resource_if_allowed(matched, "Sales Invoice")
        _append_resource_if_allowed(matched, "Payment Entry")

    if any(keyword in normalized for keyword in ["工资", "薪资", "薪酬", "员工工资", "payroll", "salary"]):
        _append_resource_if_allowed(matched, "Salary Slip")

    if any(keyword in normalized for keyword in ["总账", "分录", "凭证", "gl"]):
        _append_resource_if_allowed(matched, "GL Entry")

    if any(keyword in normalized for keyword in ["采购", "供应商", "应付", "purchase"]):
        _append_resource_if_allowed(matched, "Purchase Invoice")

    if any(keyword in normalized for keyword in ["发票", "开票", "invoice", "应收"]):
        _append_resource_if_allowed(matched, "Sales Invoice")

    allowed: list[str] = []
    finance_scope_set = set(finance_scopes)
    for resource in matched:
        if resource not in finance_scope_set or resource in allowed:
            continue
        ensure_erp_resource_allowed(current_user, resource)
        allowed.append(resource)
        if len(allowed) >= MAX_FINANCE_EXCEL_ERP_RESOURCES:
            break

    return allowed


def _append_resource_if_allowed(items: list[str], resource: str) -> None:
    if resource in ERP_RESOURCE_CATALOG and resource not in items:
        items.append(resource)


def _query_finance_excel_erp_context(resources: list[str]) -> list[dict[str, Any]]:
    if not resources:
        return []

    provider = get_active_provider()
    context: list[dict[str, Any]] = []

    for resource in resources:
        definition = ERP_RESOURCE_CATALOG[resource]
        provider_resource = provider_resource_for(resource, provider.provider_id)
        base_item: dict[str, Any] = {
            "resource": resource,
            "label": str(definition["label"]),
            "provider": provider.provider_id,
            "provider_label": provider.provider_label,
            "provider_resource": provider_resource or "",
        }

        if provider_resource is None:
            context.append({
                **base_item,
                "ok": False,
                "configured": provider.is_configured(),
                "status": "unsupported_resource",
                "message": f"{provider.provider_label} 暂未映射资源 {resource}",
                "items": [],
            })
            continue

        try:
            result = provider.query_resource(
                resource=resource,
                provider_resource=provider_resource,
                query=None,
                filters=None,
                fields=provider_fields_for(resource, provider.provider_id),
                limit=FINANCE_EXCEL_ERP_LIMIT,
            )
        except ERPProviderError as error:
            context.append({
                **base_item,
                "ok": False,
                "configured": provider.is_configured(),
                "status": error.status,
                "message": error.message,
                "items": [],
            })
            continue

        context.append({
            **base_item,
            "ok": bool(result.get("ok")),
            "configured": bool(result.get("configured")),
            "status": str(result.get("status") or "unknown"),
            "message": str(result.get("message") or ""),
            "items": result.get("items") if isinstance(result.get("items"), list) else [],
        })

    return context


@router.post("/finance/reconciliation")
async def reconcile_finance_files(
    files: list[UploadFile] = File(...),
    instruction: str = Form(default=""),
    base_currency: str = Form(default="CNY"),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin" and current_user.get("position") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有财务岗位或管理员可以使用财务对账自动化。",
        )

    if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, "finance-reconciliation"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="财务对账自动化已被管理员禁用。",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少上传 1 个对账 Excel 文件。",
        )

    if len(files) > MAX_RECONCILIATION_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"一次最多上传 {MAX_RECONCILIATION_FILES} 个 Excel 文件。",
        )

    input_files: list[dict[str, Any]] = []
    total_bytes = 0
    for file in files:
        content = await file.read()
        filename = file.filename or "finance_reconciliation.xlsx"
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{filename} 是空文件。",
            )
        if len(content) > MAX_RECONCILIATION_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{filename} 超过 8MB。",
            )
        total_bytes += len(content)
        input_files.append({"filename": filename, "content": content})

    if total_bytes > MAX_RECONCILIATION_TOTAL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="对账文件总大小不能超过 32MB。",
        )

    run_id = start_run(
        run_type="finance_reconciliation",
        app_id="finance-reconciliation",
        app_name="财务对账自动化",
        entrypoint="/automation/finance/reconciliation",
        current_user=current_user,
        resource_type="automation",
        resource_id="finance_reconciliation",
        flow_reference=resolve_flow_execution_reference(
            flow_key="automation:finance:reconciliation",
            current_user=current_user,
            execution_source="manual_file_upload",
        ),
        input_text=instruction,
        metadata={
            "source_file_count": len(input_files),
            "source_filenames": [str(item["filename"]) for item in input_files],
            "source_bytes": total_bytes,
            "base_currency": base_currency,
        },
    )
    started_ms = now_ms()

    try:
        step_started_ms = now_ms()
        skill_result = execute_skill(
            skill_id="finance_reconciliation",
            payload={
                "files": [
                    {
                        "filename": item["filename"],
                        "content": item["content"],
                    }
                    for item in input_files
                ],
                "instruction": instruction,
                "base_currency": base_currency,
                "metadata": {
                    "run_id": run_id,
                    "entrypoint": "/automation/finance/reconciliation",
                },
            },
            current_user=current_user,
            source="automation_api",
        )
        attachment = _skill_result_attachment(skill_result)
        result_metadata = _skill_result_metadata(skill_result)
        record_step(
            run_id=run_id,
            step_name="finance_reconciliation",
            step_order=1,
            status_value="succeeded",
            provider="skill_executor",
            resource_type="automation",
            resource_id="finance_reconciliation",
            input_text=instruction,
            output_text=attachment["filename"],
            duration_ms=elapsed_ms(step_started_ms),
            metadata=result_metadata,
        )
        save_generated_file(
            run_id=run_id,
            content=attachment["content"],
            artifact_type="excel_file",
            mime_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment["filename"],
            current_user=current_user,
            metadata=result_metadata,
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=skill_result.answer or f"已生成 {attachment['filename']}",
            duration_ms=elapsed_ms(started_ms),
            metadata=result_metadata,
        )
    except ValueError as error:
        record_step(
            run_id=run_id,
            step_name="finance_reconciliation",
            step_order=1,
            status_value="failed",
            provider="pandas_openpyxl",
            resource_type="automation",
            resource_id="finance_reconciliation",
            input_text=instruction,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "source_file_count": len(input_files),
                "source_filenames": [str(item["filename"]) for item in input_files],
                "source_bytes": total_bytes,
                "base_currency": base_currency,
            },
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    write_audit_log(
        user_id=current_user["id"],
        action="automation.finance_reconciliation",
        resource_type="automation",
        resource_id="finance_reconciliation",
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            **result_metadata,
        },
    )

    encoded_filename = quote(str(attachment["filename"]))
    return Response(
        content=attachment["content"],
        media_type=attachment.get("mime_type") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename={attachment['filename']}; filename*=UTF-8''{encoded_filename}"
            ),
        },
    )
