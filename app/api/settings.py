from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.user_settings_service import (
    get_user_settings,
    update_user_password,
    update_user_profile,
)


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)


class UserSettingsItem(BaseModel):
    id: str
    username: str
    role: str
    department: str | None = None
    position: str | None = None
    display_name: str | None = None
    email: str | None = None
    created_at: str


class UserSettingsResponse(BaseModel):
    item: UserSettingsItem


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=180)


class UserPasswordUpdateRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserPasswordUpdateResponse(BaseModel):
    ok: bool


@router.get("/me", response_model=UserSettingsResponse)
def read_my_settings(current_user: dict = Depends(get_current_user)):
    return {"item": get_user_settings(current_user)}


@router.put("/me/profile", response_model=UserSettingsResponse)
def update_my_profile(
    request: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    return {
        "item": update_user_profile(
            current_user=current_user,
            display_name=request.display_name,
            email=request.email,
        )
    }


@router.put("/me/password", response_model=UserPasswordUpdateResponse)
def update_my_password(
    request: UserPasswordUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    update_user_password(
        current_user=current_user,
        old_password=request.old_password,
        new_password=request.new_password,
    )
    return {"ok": True}
