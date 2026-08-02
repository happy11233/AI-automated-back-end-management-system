from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.config import settings


router = APIRouter(
    prefix="/desktop-downloads",
    tags=["desktop-downloads"],
)

DesktopPlatform = Literal["mac"]


class DesktopDownloadItem(BaseModel):
    platform: DesktopPlatform
    label: str
    available: bool
    filename: str | None = None
    download_path: str
    size_bytes: int | None = None
    updated_at: str | None = None


class DesktopDownloadsResponse(BaseModel):
    items: list[DesktopDownloadItem]


@router.get("", response_model=DesktopDownloadsResponse)
def list_desktop_downloads(current_user: dict = Depends(get_current_user)):
    del current_user
    platform = "mac"
    release_file = _find_latest_release_file(platform)
    return {"items": [_build_release_item(platform, release_file)]}


@router.get("/{platform}/download")
def download_desktop_release(
    platform: DesktopPlatform,
    current_user: dict = Depends(get_current_user),
):
    del current_user
    release_file = _find_latest_release_file(platform)
    if release_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"暂未找到 {platform} 版桌面端安装包",
        )

    media_type = "application/zip" if release_file.suffix.lower() == ".zip" else "application/octet-stream"
    return FileResponse(
        path=str(release_file),
        media_type=media_type,
        filename=release_file.name,
    )


def _build_release_item(platform: DesktopPlatform, release_file: Path | None) -> DesktopDownloadItem:
    if release_file is None:
        return DesktopDownloadItem(
            platform=platform,
            label=_platform_label(platform),
            available=False,
            filename=None,
            download_path=f"/desktop-downloads/{platform}/download",
        )

    stat = release_file.stat()
    updated_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return DesktopDownloadItem(
        platform=platform,
        label=_platform_label(platform),
        available=True,
        filename=release_file.name,
        download_path=f"/desktop-downloads/{platform}/download",
        size_bytes=stat.st_size,
        updated_at=updated_at,
    )


def _find_latest_release_file(platform: DesktopPlatform) -> Path | None:
    release_dir = Path(settings.desktop_release_dir)
    if not release_dir.exists():
        return None

    candidates = []
    for path in release_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".zip", ".dmg", ".exe", ".msi"}:
            continue
        if _matches_platform(platform, path.name.lower()):
            candidates.append(path)

    if not candidates:
        return None

    return max(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size))


def _matches_platform(platform: DesktopPlatform, filename: str) -> bool:
    return any(token in filename for token in ("mac", "darwin", "apple"))


def _platform_label(platform: DesktopPlatform) -> str:
    return "macOS 版"
