from fastapi import APIRouter, Depends, HTTPException

from app.auth.security import get_current_user
from app.services.context_service import (
    get_thread_state,
    get_thread_summary,
    list_user_memories,
)
from app.services.logging_service import get_thread, list_thread_messages


router = APIRouter(
    prefix="/threads",
    tags=["threads"],
)


@router.get("/{thread_id}/messages")
def get_messages(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
):
    thread = get_thread(thread_id)

    if thread is None:
        raise HTTPException(
            status_code=404,
            detail="会话不存在",
        )

    if current_user["role"] != "admin" and thread["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="没有权限查看该会话",
        )

    return {
        "thread": thread,
        "summary": get_thread_summary(thread_id),
        "state": get_thread_state(thread_id),
        "memories": list_user_memories(current_user["id"], limit=20),
        "messages": list_thread_messages(thread_id),
    }
