from __future__ import annotations

from fastapi import HTTPException, status

from app.auth.security import hash_password, verify_password
from app.db import execute, fetch_one, transaction
from app.services.logging_service import write_audit_log


def ensure_user_settings_schema() -> None:
    execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS display_name TEXT;
        """
    )
    execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS email TEXT;
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_users_email
        ON users(email);
        """
    )


def get_user_settings(current_user: dict) -> dict:
    row = fetch_one(
        """
        SELECT id, username, role, department, position, display_name, email, created_at
        FROM users
        WHERE id = %s;
        """,
        (current_user["id"],),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _row_to_settings(row)


def update_user_profile(
    *,
    current_user: dict,
    display_name: str | None,
    email: str | None,
) -> dict:
    normalized_name = _clean_text(display_name, 80)
    normalized_email = _clean_email(email)
    row = fetch_one(
        """
        UPDATE users
        SET display_name = %s,
            email = %s
        WHERE id = %s
        RETURNING id, username, role, department, position, display_name, email, created_at;
        """,
        (normalized_name, normalized_email, current_user["id"]),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    item = _row_to_settings(row)
    write_audit_log(
        user_id=current_user["id"],
        action="user.settings.profile_update",
        resource_type="user",
        resource_id=current_user["id"],
        metadata={
            "username": current_user["username"],
            "display_name_set": bool(item["display_name"]),
            "email_set": bool(item["email"]),
        },
    )
    return item


def update_user_password(
    *,
    current_user: dict,
    old_password: str,
    new_password: str,
) -> None:
    if not old_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入当前密码")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能少于 6 位")
    if old_password == new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能和当前密码相同")

    row = fetch_one(
        """
        SELECT password_hash
        FROM users
        WHERE id = %s;
        """,
        (current_user["id"],),
    )
    if row is None or not row[0]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if not verify_password(old_password, row[0]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE id = %s;
                """,
                (hash_password(new_password), current_user["id"]),
            )

    write_audit_log(
        user_id=current_user["id"],
        action="user.settings.password_update",
        resource_type="user",
        resource_id=current_user["id"],
        metadata={
            "username": current_user["username"],
        },
    )


def _row_to_settings(row) -> dict:
    created_at = row[7]
    return {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "department": row[3],
        "position": row[4],
        "display_name": row[5],
        "email": row[6],
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
    }


def _clean_text(value: str | None, max_length: int) -> str | None:
    text = (value or "").strip()
    return text[:max_length] if text else None


def _clean_email(value: str | None) -> str | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    if len(text) > 180 or "@" not in text or text.startswith("@") or text.endswith("@"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")
    return text
