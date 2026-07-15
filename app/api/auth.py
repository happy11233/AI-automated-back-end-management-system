from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth.security import authenticate_user, create_access_token, get_current_user
from app.permissions import capabilities_for_position, erp_scopes_for_position


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    department: str | None = None
    position: str | None = None
    capabilities: list[str] = []
    erp_scopes: list[str] = []


class CurrentUserResponse(BaseModel):
    id: str
    username: str
    role: str
    department: str | None = None
    position: str | None = None
    capabilities: list[str] = []
    erp_scopes: list[str] = []


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(
        username=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "department": user.get("department"),
        "position": user.get("position"),
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
        "department": user.get("department"),
        "position": user.get("position"),
        "capabilities": capabilities_for_position(user.get("position")),
        "erp_scopes": erp_scopes_for_position(user.get("position")),
    }


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "department": current_user.get("department"),
        "position": current_user.get("position"),
        "capabilities": capabilities_for_position(current_user.get("position")),
        "erp_scopes": erp_scopes_for_position(current_user.get("position")),
    }
