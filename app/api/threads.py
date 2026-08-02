from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.config import settings
from app.services.context_service import (
    get_thread_state,
    get_thread_summary,
    list_user_memories,
)
from app.services.logging_service import (
    create_chat_thread,
    get_thread_for_user,
    list_chat_threads,
    get_latest_thread_for_user,
    list_thread_messages_for_user,
    update_chat_thread_title,
)


router = APIRouter(
    prefix="/threads",
    tags=["threads"],
)


class ThreadUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@router.get("")
def list_threads(
    limit: int = Query(default=80, ge=1, le=200),
    search: str | None = Query(default=None, max_length=120),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_chat_threads(
            current_user=current_user,
            limit=limit,
            search=search.strip() if search else None,
        ),
        "retention_days": settings.chat_thread_retention_days,
    }


@router.post("")
def create_thread(
    current_user: dict = Depends(get_current_user),
):
    item = create_chat_thread(
        user_id=current_user["id"],
        title="新会话",
        position=current_user.get("position"),
    )
    return {
        "item": {
            **item,
            "username": current_user.get("username"),
            "display_name": current_user.get("display_name"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "message_count": 0,
            "last_message_preview": "",
            "last_message_role": None,
        },
    }


@router.get("/latest")
def get_latest_thread(
    current_user: dict = Depends(get_current_user),
):
    return {
        "item": get_latest_thread_for_user(current_user["id"], current_user.get("position")),
    }


@router.patch("/{thread_id}")
def update_thread(
    thread_id: str,
    request: ThreadUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    thread = get_thread_for_user(thread_id, current_user)

    if thread is None:
        raise HTTPException(
            status_code=404,
            detail="会话不存在或无权访问",
        )

    title = request.title.strip()
    if not title:
        raise HTTPException(
            status_code=400,
            detail="会话标题不能为空",
        )

    update_chat_thread_title(thread_id, title)
    items = list_chat_threads(current_user=current_user, search=thread_id, limit=1)
    return {"item": items[0] if items else {**thread, "title": title}}


@router.get("/{thread_id}/messages")
def get_messages(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
):
    thread = get_thread_for_user(thread_id, current_user)

    if thread is None:
        raise HTTPException(
            status_code=404,
            detail="会话不存在或无权访问",
        )

    messages = list_thread_messages_for_user(thread_id, current_user)

    return {
        "thread": thread,
        "summary": get_thread_summary(thread_id),
        "state": get_thread_state(thread_id),
        "memories": list_user_memories(current_user["id"], limit=20),
        "messages": messages or [],
    }
