from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from psycopg.errors import UniqueViolation

from app.auth.security import hash_password, require_admin
from app.db import fetch_all, fetch_one
from app.permissions import (
    capabilities_for_position,
    default_department_for_position,
    erp_scopes_for_position,
    validate_user_position,
)
from app.services.logging_service import write_audit_log


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
    role: str
    department: str | None = None
    position: str | None = None
    capabilities: list[str] = []
    erp_scopes: list[str] = []
    created_at: str


class UserListResponse(BaseModel):
    items: list[UserItem]


class UserCreateResponse(BaseModel):
    item: UserItem


@router.get("", response_model=UserListResponse)
def list_users(current_user: dict = Depends(require_admin)):
    rows = fetch_all(
        """
        SELECT id, username, role, department, position, created_at
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
            RETURNING id, username, role, department, position, created_at;
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


def _row_to_user_item(row) -> dict:
    position = row[4]

    return {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "department": row[3],
        "position": position,
        "capabilities": capabilities_for_position(position),
        "erp_scopes": erp_scopes_for_position(position),
        "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
    }
