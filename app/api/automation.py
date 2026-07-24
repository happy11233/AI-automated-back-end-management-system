import json
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
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
from app.services.generated_file_service import save_generated_file
from app.services.logging_service import write_audit_log
from app.services.automation_flow_version_service import resolve_flow_execution_reference
from app.services.platform_action_executor_service import execute_platform_draft_action
from app.services.platform_draft_service import (
    create_platform_draft,
    listing_content_from_answer,
)
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
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
                writeback_status="rpa_ready",
                writeback_message=(
                    "已保存为 Amazon Listing 平台草稿，等待运营审核；可由 SP-API、ERP 连接器或影刀 RPA 同步到外部平台。"
                ),
                metadata={
                    "automation": "operations_listing",
                    "source": "automation_generate",
                    "saved_by_ai": True,
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
            action_started_ms = now_ms()
            action_result = execute_platform_draft_action(
                draft_id=platform_draft["id"],
                current_user=current_user,
                trigger_source="automation_generate",
            )
            platform_draft = action_result["draft"]
            record_step(
                run_id=run_id,
                step_name="submit_external_writeback",
                step_order=3,
                status_value=(
                    "succeeded"
                    if action_result["execution"]["status"] == "succeeded"
                    else "blocked"
                    if action_result["execution"]["status"] == "waiting_executor"
                    else "failed"
                ),
                provider="platform_action_executor",
                resource_type="platform_draft",
                resource_id=platform_draft["id"],
                input_text={"draft_id": platform_draft["id"]},
                output_text=action_result,
                duration_ms=elapsed_ms(action_started_ms),
                metadata={
                    "execution_id": action_result["execution"]["id"],
                    "execution_status": action_result["execution"]["status"],
                    "executor_type": action_result["execution"]["executor_type"],
                },
            )
            answer = (
                "AI 已完成 Listing 全流程自动化，并提交外部写回执行闭环。\n"
                f"草稿 ID：{platform_draft['id']}\n"
                f"写回目标：{platform_draft['external_target']}\n"
                f"写回状态：{platform_draft['writeback_status']}\n\n"
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


@router.post("/finance/excel-transform")
async def transform_finance_excel_file(
    file: UploadFile = File(...),
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

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请上传非空 Excel 文件。",
        )

    if len(content) > MAX_EXCEL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Excel 文件不能超过 8MB。",
        )

    selected_erp_resources = _parse_finance_excel_erp_resources(
        raw_value=erp_resources,
        current_user=current_user,
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
            execution_source="manual_file_upload",
        ),
        input_text=instruction,
        metadata={
            "source_filename": file.filename or "finance.xlsx",
            "source_bytes": len(content),
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
                "source_filename": file.filename or "finance.xlsx",
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
                "source_filename": file.filename or "finance.xlsx",
                "source_bytes": len(content),
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
