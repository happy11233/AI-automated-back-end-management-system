from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.rag_authorization_service import (
    add_rag_team_member,
    create_document_grant,
    create_rag_team,
    get_document_access,
    list_document_grants,
    list_rag_documents,
    list_rag_team_members,
    list_rag_teams,
    remove_rag_team_member,
    revoke_document_grant,
    update_document_access,
    update_rag_team,
)


router = APIRouter(tags=["rag-authorization"])


class RagTeamCreateRequest(BaseModel):
    team_key: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    position_scope: Literal["operations", "customer_service", "finance"] | None = None
    market_scope: Literal["us", "de", "jp"] | None = None
    store_scope: Literal["us_store", "de_store", "jp_store"] | None = None
    status: Literal["active", "paused", "archived"] = "active"


class RagTeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    position_scope: Literal["operations", "customer_service", "finance"] | None = None
    market_scope: Literal["us", "de", "jp"] | None = None
    store_scope: Literal["us_store", "de_store", "jp_store"] | None = None
    status: Literal["active", "paused", "archived"] | None = None


class RagTeamItem(BaseModel):
    id: str
    team_key: str
    name: str
    description: str | None = None
    position_scope: str | None = None
    market_scope: str | None = None
    store_scope: str | None = None
    status: str
    created_by: str | None = None
    created_by_username: str | None = None
    member_count: int
    created_at: datetime
    updated_at: datetime


class RagTeamListResponse(BaseModel):
    items: list[RagTeamItem]
    total: int


class RagTeamResponse(BaseModel):
    item: RagTeamItem


class RagTeamMemberRequest(BaseModel):
    user_id: str
    member_role: Literal["member", "supervisor", "auditor"] = "member"
    expires_at: datetime | None = None


class RagTeamMemberItem(BaseModel):
    id: str
    team_id: str
    user_id: str
    username: str
    display_name: str | None = None
    role: str
    position: str | None = None
    department: str | None = None
    member_role: str
    status: str
    expires_at: datetime | None = None
    added_by: str | None = None
    added_by_username: str | None = None
    created_at: datetime
    updated_at: datetime


class RagTeamMemberListResponse(BaseModel):
    items: list[RagTeamMemberItem]
    total: int


class RagTeamMemberResponse(BaseModel):
    item: RagTeamMemberItem


class RagTeamMemberDeleteResponse(BaseModel):
    ok: bool
    team_id: str
    user_id: str


class DocumentAccessUpdateRequest(BaseModel):
    access_mode: Literal["open", "owner_only", "team_only", "explicit_grants", "owner_and_grants"] | None = None
    owner_user_id: str | None = None
    owner_team_id: str | None = None


class DocumentAccessItem(BaseModel):
    id: str
    title: str
    source: str | None = None
    visibility: str
    department: str | None = None
    position_scope: str | None = None
    market_scope: str | None = None
    store_scope: str | None = None
    field_scope: str | None = None
    sensitivity_level: str | None = None
    owner_user_id: str | None = None
    owner_team_id: str | None = None
    access_mode: str
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentAccessResponse(BaseModel):
    item: DocumentAccessItem


class DocumentListResponse(BaseModel):
    items: list[DocumentAccessItem]
    total: int


class DocumentGrantCreateRequest(BaseModel):
    subject_type: Literal["user", "team"]
    subject_id: str
    access_level: Literal["read", "manage"] = "read"
    reason: str | None = Field(default=None, max_length=500)
    expires_at: datetime | None = None


class DocumentGrantItem(BaseModel):
    id: str
    document_id: str
    subject_type: str
    subject_id: str
    subject_name: str | None = None
    access_level: str
    status: str
    granted_by: str | None = None
    granted_by_username: str | None = None
    reason: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DocumentGrantListResponse(BaseModel):
    items: list[DocumentGrantItem]
    total: int


class DocumentGrantResponse(BaseModel):
    item: DocumentGrantItem


class DocumentGrantRevokeResponse(BaseModel):
    ok: bool
    item: DocumentGrantItem


@router.get("/rag-teams", response_model=RagTeamListResponse)
def get_rag_teams(current_user: dict = Depends(require_admin)):
    return list_rag_teams()


@router.post("/rag-teams", response_model=RagTeamResponse)
def create_rag_team_endpoint(
    request: RagTeamCreateRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": create_rag_team(
            payload=request.model_dump(),
            current_user=current_user,
        )
    }


@router.patch("/rag-teams/{team_id}", response_model=RagTeamResponse)
def update_rag_team_endpoint(
    team_id: str,
    request: RagTeamUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": update_rag_team(
            team_id=team_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.get("/rag-teams/{team_id}/members", response_model=RagTeamMemberListResponse)
def get_rag_team_members(
    team_id: str,
    current_user: dict = Depends(require_admin),
):
    return list_rag_team_members(team_id=team_id)


@router.post("/rag-teams/{team_id}/members", response_model=RagTeamMemberResponse)
def add_rag_team_member_endpoint(
    team_id: str,
    request: RagTeamMemberRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": add_rag_team_member(
            team_id=team_id,
            payload=request.model_dump(),
            current_user=current_user,
        )
    }


@router.delete("/rag-teams/{team_id}/members/{user_id}", response_model=RagTeamMemberDeleteResponse)
def remove_rag_team_member_endpoint(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(require_admin),
):
    return remove_rag_team_member(
        team_id=team_id,
        user_id=user_id,
        current_user=current_user,
    )


@router.get("/documents", response_model=DocumentListResponse)
def get_documents(
    search: str | None = None,
    status: Literal["active", "deleted", "all"] = "active",
    limit: int = 50,
    current_user: dict = Depends(require_admin),
):
    return list_rag_documents(search=search, status=status, limit=limit)


@router.get("/documents/{document_id}/access", response_model=DocumentAccessResponse)
def get_document_access_endpoint(
    document_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": get_document_access(document_id=document_id)}


@router.patch("/documents/{document_id}/access", response_model=DocumentAccessResponse)
def update_document_access_endpoint(
    document_id: str,
    request: DocumentAccessUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": update_document_access(
            document_id=document_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.get("/documents/{document_id}/grants", response_model=DocumentGrantListResponse)
def get_document_grants(
    document_id: str,
    current_user: dict = Depends(require_admin),
):
    return list_document_grants(document_id=document_id)


@router.post("/documents/{document_id}/grants", response_model=DocumentGrantResponse)
def create_document_grant_endpoint(
    document_id: str,
    request: DocumentGrantCreateRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": create_document_grant(
            document_id=document_id,
            payload=request.model_dump(),
            current_user=current_user,
        )
    }


@router.delete("/documents/{document_id}/grants/{grant_id}", response_model=DocumentGrantRevokeResponse)
def revoke_document_grant_endpoint(
    document_id: str,
    grant_id: str,
    current_user: dict = Depends(require_admin),
):
    return revoke_document_grant(
        document_id=document_id,
        grant_id=grant_id,
        current_user=current_user,
    )
