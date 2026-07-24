from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from psycopg.errors import UniqueViolation

from app.auth.security import hash_password, require_admin
from app.db import fetch_all, fetch_one, transaction
from app.permissions import (
    default_department_for_position,
    erp_scopes_for_position,
    validate_user_position,
)
from app.services.logging_service import write_audit_log
from app.services.user_ai_app_permission_service import (
    ai_app_permission_items_for_user,
    allowed_ai_app_ids_for_user,
    available_ai_app_ids_for_user,
    set_user_ai_app_permission,
)


router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["admin", "employee"] = "employee"
    position: Literal["operations", "customer_service", "finance"] | None = None
    department: str | None = None


class UserItem(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    email: str | None = None
    role: str
    department: str | None = None
    position: str | None = None
    capabilities: list[str] = []
    erp_scopes: list[str] = []
    allowed_ai_app_ids: list[str] = []
    ai_app_permissions: list[dict] = []
    created_at: str


class UserListResponse(BaseModel):
    items: list[UserItem]


class UserCreateResponse(BaseModel):
    item: UserItem


class UserUpdateResponse(BaseModel):
    item: UserItem


class UserDeleteResponse(BaseModel):
    ok: bool
    deleted_user_id: str


class UserAiAppPermissionRequest(BaseModel):
    enabled: bool


@router.get("", response_model=UserListResponse)
def list_users(current_user: dict = Depends(require_admin)):
    rows = fetch_all(
        """
        SELECT id, username, role, department, position, display_name, email, created_at
        FROM users
        ORDER BY created_at DESC;
        """
    )

    return {
        "items": [
            _row_to_user_item(row)
            for row in rows
        ]
    }


@router.post("", response_model=UserCreateResponse)
def create_user(
    request: UserCreateRequest,
    current_user: dict = Depends(require_admin),
):
    username = request.username.strip()
    department = request.department.strip() if request.department else None
    position = request.position

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名不能为空",
        )

    validate_user_position(request.role, position)

    if request.role == "employee" and not department:
        department = default_department_for_position(position)

    password_hash = hash_password(request.password)

    try:
        row = fetch_one(
            """
            INSERT INTO users (username, role, department, position, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, username, role, department, position, display_name, email, created_at;
            """,
            (
                username,
                request.role,
                department,
                position,
                password_hash,
            ),
        )
    except UniqueViolation as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        ) from error

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建用户失败",
        )

    item = _row_to_user_item(row)

    write_audit_log(
        user_id=current_user["id"],
        action="admin.user.create",
        resource_type="user",
        resource_id=item["id"],
        metadata={
            "username": current_user["username"],
            "created_username": item["username"],
            "created_role": item["role"],
            "created_position": item["position"],
            "created_department": item["department"],
        },
    )
    write_audit_log(
        user_id=current_user["id"],
        action="admin.user.permission_assignment",
        resource_type="user",
        resource_id=item["id"],
        metadata={
            "username": current_user["username"],
            "created_username": item["username"],
            "created_role": item["role"],
            "position": item["position"],
            "capabilities": item["capabilities"],
            "erp_scopes": item["erp_scopes"],
        },
    )

    return {"item": item}


@router.put("/{user_id}/ai-apps/{app_id}", response_model=UserUpdateResponse)
def update_user_ai_app_permission(
    user_id: str,
    app_id: str,
    request: UserAiAppPermissionRequest,
    current_user: dict = Depends(require_admin),
):
    row = _get_user_row(user_id)
    item = _row_to_user_item(row)
    available_ids = available_ai_app_ids_for_user(item)

    if app_id not in available_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户岗位下不存在这个 AI 应用",
        )

    set_user_ai_app_permission(
        user_id=item["id"],
        app_id=app_id,
        enabled=request.enabled,
        actor_id=current_user["id"],
    )

    updated_row = _get_user_row(user_id)
    updated_item = _row_to_user_item(updated_row)
    write_audit_log(
        user_id=current_user["id"],
        action="admin.user.ai_app_permission_update",
        resource_type="user",
        resource_id=updated_item["id"],
        metadata={
            "username": current_user["username"],
            "target_username": updated_item["username"],
            "app_id": app_id,
            "enabled": request.enabled,
        },
    )

    return {"item": updated_item}


@router.delete("/{user_id}", response_model=UserDeleteResponse)
def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
):
    row = _get_user_row(user_id)
    item = _row_to_user_item(row)

    if item["id"] == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录的管理员账号",
        )

    if item["role"] == "admin":
        admin_count = fetch_one("SELECT count(*) FROM users WHERE role = 'admin';")
        if admin_count and int(admin_count[0] or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除系统最后一个管理员账号",
            )

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s;", (item["id"],))

    write_audit_log(
        user_id=current_user["id"],
        action="admin.user.delete",
        resource_type="user",
        resource_id=item["id"],
        metadata={
            "username": current_user["username"],
            "deleted_username": item["username"],
            "deleted_role": item["role"],
            "deleted_position": item["position"],
        },
    )

    return {
        "ok": True,
        "deleted_user_id": item["id"],
    }


def _get_user_row(user_id: str):
    row = fetch_one(
        """
        SELECT id, username, role, department, position, display_name, email, created_at
        FROM users
        WHERE id = %s;
        """,
        (user_id,),
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return row


def _row_to_user_item(row) -> dict:
    position = row[4]
    user = {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "department": row[3],
        "position": position,
        "display_name": row[5],
        "email": row[6],
    }
    ai_app_permissions = ai_app_permission_items_for_user(user)
    allowed_ai_app_ids = allowed_ai_app_ids_for_user(user)

    return {
        **user,
        "position": position,
        "capabilities": [
            item["name"]
            for item in ai_app_permissions
            if item["enabled"]
        ],
        "erp_scopes": erp_scopes_for_position(position),
        "allowed_ai_app_ids": allowed_ai_app_ids,
        "ai_app_permissions": ai_app_permissions,
        "created_at": row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
    }
