from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.generated_file_service import get_generated_file, list_generated_files


router = APIRouter(
    prefix="/files",
    tags=["files"],
)


class GeneratedFileItem(BaseModel):
    id: str
    run_id: str
    artifact_type: str
    name: str
    mime_type: str | None
    size_bytes: int | None
    external_ref: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None
    expires_at: str | None
    downloadable: bool
    app_id: str
    app_name: str
    run_type: str
    status: str
    username: str | None
    position: str | None


class GeneratedFilesResponse(BaseModel):
    items: list[GeneratedFileItem]


@router.get("", response_model=GeneratedFilesResponse)
def get_files(
    search: str | None = Query(default=None),
    date_range: str = Query(default="30d"),
    file_type: str = Query(default="all"),
    limit: int = Query(default=80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_generated_files(
            current_user=current_user,
            search=search,
            date_range=date_range,
            file_type=file_type,
            limit=limit,
        )
    }


@router.get("/{artifact_id}/download")
def download_file(
    artifact_id: str,
    current_user: dict = Depends(get_current_user),
):
    item = get_generated_file(artifact_id, current_user=current_user)
    filename = item["filename"]
    encoded_filename = quote(filename)
    return Response(
        content=item["content"],
        media_type=item["mime_type"],
        headers={
            "Content-Disposition": (
                f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"
            ),
        },
    )
