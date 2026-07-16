from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.llm import chat
from app.permissions import POSITION_LABELS, is_valid_position
from app.services.automation_service import (
    build_automation_prompt,
    find_automation_task,
    list_all_automation_tasks,
    list_automation_tasks,
)
from app.services.finance_excel_service import (
    MAX_EXCEL_BYTES,
    transform_finance_excel,
)
from app.services.logging_service import write_audit_log
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    now_ms,
    record_artifact,
    record_step,
    start_run,
)


router = APIRouter(
    prefix="/automation",
    tags=["automation"],
)


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
    return {
        "position": effective_position,
        "position_label": POSITION_LABELS[effective_position],
        "items": list_automation_tasks(effective_position),
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
        input_text=request.input_text,
        metadata={
            "task_id": request.task_id,
            "task_label": task["label"],
            "position": task["position"],
            "position_label": task["position_label"],
        },
    )

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
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=answer,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "task_id": request.task_id,
                "task_label": task["label"],
                "position": task["position"],
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
        },
    )

    return {
        "position": task["position"],
        "position_label": task["position_label"],
        "task_id": request.task_id,
        "task_label": task["label"],
        "answer": answer,
    }


@router.post("/finance/excel-transform")
async def transform_finance_excel_file(
    file: UploadFile = File(...),
    instruction: str = Form(default=""),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin" and current_user.get("position") != "finance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有财务岗位或管理员可以使用财务 Excel 生成功能。",
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

    run_id = start_run(
        run_type="finance_excel_transform",
        app_id="finance-excel-transform",
        app_name="财务 Excel 生成",
        entrypoint="/automation/finance/excel-transform",
        current_user=current_user,
        resource_type="automation",
        resource_id="finance_excel_transform",
        input_text=instruction,
        metadata={
            "source_filename": file.filename or "finance.xlsx",
            "source_bytes": len(content),
        },
    )
    started_ms = now_ms()

    try:
        step_started_ms = now_ms()
        result = transform_finance_excel(
            source_filename=file.filename or "finance.xlsx",
            content=content,
            instruction=instruction,
        )
        record_step(
            run_id=run_id,
            step_name="finance_excel_transform",
            step_order=1,
            status_value="succeeded",
            provider="pandas_openpyxl_dashscope",
            resource_type="automation",
            resource_id="finance_excel_transform",
            input_text=instruction,
            output_text=result.filename,
            duration_ms=elapsed_ms(step_started_ms),
            metadata=result.metadata,
        )
        record_artifact(
            run_id=run_id,
            artifact_type="excel_file",
            name=result.filename,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=len(result.content),
            external_ref=result.filename,
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
            **result.metadata,
        },
    )

    encoded_filename = quote(result.filename)
    return Response(
        content=result.content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename={result.filename}; filename*=UTF-8''{encoded_filename}"
            ),
        },
    )
