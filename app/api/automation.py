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
    answer = chat(prompt)

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

    try:
        result = transform_finance_excel(
            source_filename=file.filename or "finance.xlsx",
            content=content,
            instruction=instruction,
        )
    except ValueError as error:
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
