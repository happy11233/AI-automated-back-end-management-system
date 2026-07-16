from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.run_record_service import get_run_detail, list_runs


router = APIRouter(
    prefix="/run-records",
    tags=["run-records"],
)


class RunRecordItem(BaseModel):
    id: str
    run_type: str
    app_id: str
    app_name: str
    entrypoint: str
    status: str
    user_id: str | None
    username: str | None
    role: str | None
    position: str | None
    thread_id: str | None
    resource_type: str | None
    resource_id: str | None
    input_preview: str | None
    output_preview: str | None
    error_message: str | None
    duration_ms: int | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None
    finished_at: str | None
    created_at: str | None
    step_count: int
    artifact_count: int


class RunRecordStepItem(BaseModel):
    id: str
    run_id: str
    step_order: int
    step_name: str
    status: str
    provider: str | None
    resource_type: str | None
    resource_id: str | None
    input_preview: str | None
    output_preview: str | None
    error_message: str | None
    duration_ms: int | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None
    finished_at: str | None


class RunRecordArtifactItem(BaseModel):
    id: str
    run_id: str
    artifact_type: str
    name: str
    mime_type: str | None
    size_bytes: int | None
    external_ref: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None


class RunRecordsResponse(BaseModel):
    items: list[RunRecordItem]


class RunRecordDetailResponse(BaseModel):
    run: RunRecordItem
    steps: list[RunRecordStepItem]
    artifacts: list[RunRecordArtifactItem]


@router.get("", response_model=RunRecordsResponse)
def get_run_records(
    status_filter: str | None = Query(default=None, alias="status"),
    run_type: str | None = Query(default=None),
    app_id: str | None = Query(default=None),
    position: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_runs(
            current_user=current_user,
            status_filter=status_filter,
            run_type=run_type,
            app_id=app_id,
            position=position,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
        )
    }


@router.get("/{run_id}", response_model=RunRecordDetailResponse)
def get_run_record_detail(
    run_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_run_detail(run_id, current_user=current_user)
