from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.security import require_admin
from app.services.automation_flow_service import get_flow_config, list_flow_configs
from app.services.automation_flow_version_service import (
    approve_flow_version,
    create_flow_version,
    get_flow_version,
    list_flow_version_verification_evidence,
    list_flow_versions,
    publish_flow_version,
    record_flow_version_verification_evidence,
    rollback_publication,
    run_flow_version_preflight,
    submit_flow_version_review,
    update_flow_version,
)


router = APIRouter(
    prefix="/automation-flows",
    tags=["automation-flows"],
)

governance_router = APIRouter(tags=["automation-flow-governance"])


class FlowResourceItem(BaseModel):
    resource: str
    label: str
    description: str
    provider_refs: dict[str, str]


class FlowStepItem(BaseModel):
    id: str
    name: str
    inputs: list[str]
    retryable: bool


class AutomationFlowItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    app_id: str
    name: str
    description: str
    category: str
    position: str | None
    position_label: str
    status: str
    version: str
    publish_status: str
    owner: str
    trigger_type: str
    entrypoint: str
    input_schema: list[dict[str, Any]]
    output_schema: list[dict[str, Any]]
    prompt_summary: str
    prompt_template_preview: str
    model_settings: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    allowed_tools: list[str]
    allowed_erp_resources: list[FlowResourceItem]
    permission_rules: list[str]
    approval_policy: str
    failure_strategy: str
    steps: list[FlowStepItem]
    source: str


class AutomationFlowsResponse(BaseModel):
    items: list[AutomationFlowItem]


class AutomationFlowDetailResponse(BaseModel):
    item: AutomationFlowItem


class AutomationFlowVersionCreateRequest(BaseModel):
    version: str | None = Field(default=None, max_length=80)
    change_summary: str | None = Field(default=None, max_length=1000)
    approval_policy: str | None = Field(default=None, max_length=2000)
    failure_strategy: str | None = Field(default=None, max_length=2000)
    publish_notes: str | None = Field(default=None, max_length=1000)


class AutomationFlowVersionUpdateRequest(BaseModel):
    change_summary: str | None = Field(default=None, max_length=1000)
    approval_policy: str | None = Field(default=None, max_length=2000)
    failure_strategy: str | None = Field(default=None, max_length=2000)
    publish_notes: str | None = Field(default=None, max_length=1000)
    prompt_summary: str | None = Field(default=None, max_length=1000)
    prompt_template_preview: str | None = Field(default=None, max_length=8000)
    input_schema: list[dict[str, Any]] | None = None
    output_schema: list[dict[str, Any]] | None = None
    tool_parameters: dict[str, dict[str, Any]] | None = None
    allowed_tools: list[str] | None = None
    allowed_erp_resources: list[dict[str, Any]] | None = None
    steps: list[dict[str, Any]] | None = None


class AutomationFlowVersionPublishRequest(BaseModel):
    environment: str = Field(default="production", max_length=40)
    reason: str | None = Field(default=None, max_length=1000)


class AutomationFlowPublicationRollbackRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AutomationFlowVerificationEvidenceRequest(BaseModel):
    script: str = Field(max_length=500)
    command: str | None = Field(default=None, max_length=1000)
    profile: str = Field(default="api", max_length=40)
    status: str = Field(default="passed", max_length=40)
    report_id: str = Field(max_length=200)
    report_url: str | None = Field(default=None, max_length=1000)
    summary: str | None = Field(default=None, max_length=1000)
    ttl_hours: int = Field(default=168, ge=1, le=720)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutomationFlowVersionSummary(BaseModel):
    id: str
    flow_id: str
    flow_key: str
    version: str
    version_number: int
    status: str
    change_summary: str | None = None
    trigger_type: str
    entrypoint: str
    approval_policy: str
    failure_strategy: str
    publish_notes: str | None = None
    created_by: str | None = None
    created_by_username: str | None = None
    approved_by: str | None = None
    approved_by_username: str | None = None
    published_by: str | None = None
    published_by_username: str | None = None
    created_at: Any
    updated_at: Any
    approved_at: Any | None = None
    published_at: Any | None = None
    active_publication_id: str | None = None
    active_publication_environment: str | None = None


class AutomationFlowVersionItem(AutomationFlowVersionSummary):
    app_id: str
    name: str
    description: str | None = None
    category: str
    position: str | None = None
    flow_status: str
    source: str
    input_schema: list[dict[str, Any]]
    output_schema: list[dict[str, Any]]
    prompt_template_preview: str | None = None
    prompt_summary: str | None = None
    model_settings: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    allowed_tools: list[str]
    allowed_erp_resources: list[dict[str, Any]]
    allowed_rag_scopes: dict[str, Any]
    permission_rules: list[str]
    steps: list[dict[str, Any]]


class AutomationFlowVersionListResponse(BaseModel):
    items: list[AutomationFlowVersionSummary]
    total: int


class AutomationFlowVersionResponse(BaseModel):
    item: AutomationFlowVersionItem


class AutomationFlowPublicationItem(BaseModel):
    id: str
    flow_id: str
    flow_key: str
    version_id: str
    version: str
    version_number: int
    environment: str
    status: str
    rollout_percent: int
    published_by: str | None = None
    published_by_username: str | None = None
    published_at: Any
    rollback_from_version_id: str | None = None
    reason: str | None = None
    created_at: Any


class AutomationFlowPublicationResponse(BaseModel):
    item: AutomationFlowPublicationItem


class AutomationFlowVerificationEvidenceItem(BaseModel):
    id: str
    flow_id: str
    version_id: str | None = None
    flow_key: str
    version: str
    version_status: str
    snapshot_hash: str
    script: str
    command: str
    profile: str
    status: str
    report_id: str
    report_url: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    verified_by: str | None = None
    verified_by_username: str | None = None
    verified_at: Any
    expires_at: Any
    created_at: Any
    is_current_version: bool | None = None
    matches_current_snapshot: bool | None = None
    is_publish_eligible: bool | None = None
    evidence_scope: str | None = None


class AutomationFlowVerificationEvidenceResponse(BaseModel):
    item: AutomationFlowVerificationEvidenceItem


class AutomationFlowVerificationEvidenceListResponse(BaseModel):
    items: list[AutomationFlowVerificationEvidenceItem]
    total: int
    version_id: str
    flow_id: str
    flow_key: str
    version: str
    snapshot_hash: str


class AutomationFlowVersionPreflightRepairHint(BaseModel):
    code: str
    field_path: str
    severity: str
    message: str
    suggestion: str


class AutomationFlowVersionPreflightArtifact(BaseModel):
    label: str
    command: str
    script: str
    profile: str
    publish_evidence_required: bool = False
    latest_evidence: AutomationFlowVerificationEvidenceItem | None = None


class AutomationFlowVersionPreflightCheck(BaseModel):
    key: str
    label: str
    status: str
    message: str
    details: list[str]
    repair_hints: list[AutomationFlowVersionPreflightRepairHint] = Field(default_factory=list)
    artifacts: list[AutomationFlowVersionPreflightArtifact] = Field(default_factory=list)


class AutomationFlowVersionPreflightResponse(BaseModel):
    preflight_run_id: str | None = None
    ok: bool
    version_id: str
    flow_id: str
    flow_key: str
    version: str
    status: str
    trigger_source: str
    blocking_failures: int
    checks: list[AutomationFlowVersionPreflightCheck]
    created_by: str | None = None
    created_by_username: str | None = None
    created_at: Any | None = None


@router.get("", response_model=AutomationFlowsResponse)
def get_automation_flows(
    position: str | None = Query(default=None),
    category: str | None = Query(default=None),
    current_user: dict = Depends(require_admin),
):
    flows = list_flow_configs(current_user)

    if position:
        flows = [item for item in flows if item["position"] == position]

    if category:
        flows = [item for item in flows if category.lower() in item["category"].lower()]

    return {"items": flows}


@router.get("/{flow_id}", response_model=AutomationFlowDetailResponse)
def get_automation_flow_detail(
    flow_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": get_flow_config(flow_id, current_user)}


@router.get("/{flow_id}/versions", response_model=AutomationFlowVersionListResponse)
def get_automation_flow_versions(
    flow_id: str,
    current_user: dict = Depends(require_admin),
):
    return list_flow_versions(flow_id=flow_id, current_user=current_user)


@router.post("/{flow_id}/versions", response_model=AutomationFlowVersionResponse)
def create_automation_flow_version_endpoint(
    flow_id: str,
    request: AutomationFlowVersionCreateRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": create_flow_version(
            flow_id=flow_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.get("/versions/{version_id}", response_model=AutomationFlowVersionResponse)
def get_automation_flow_version_detail(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": get_flow_version(version_id=version_id, current_user=current_user)}


@router.patch("/versions/{version_id}", response_model=AutomationFlowVersionResponse)
def update_automation_flow_version_endpoint(
    version_id: str,
    request: AutomationFlowVersionUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": update_flow_version(
            version_id=version_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.post("/versions/{version_id}/submit-review", response_model=AutomationFlowVersionResponse)
def submit_automation_flow_version_review(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": submit_flow_version_review(version_id=version_id, current_user=current_user)}


@router.post("/versions/{version_id}/approve", response_model=AutomationFlowVersionResponse)
def approve_automation_flow_version_endpoint(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": approve_flow_version(version_id=version_id, current_user=current_user)}


@router.post("/versions/{version_id}/preflight", response_model=AutomationFlowVersionPreflightResponse)
def run_automation_flow_version_preflight_endpoint(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return run_flow_version_preflight(version_id=version_id, current_user=current_user)


@router.post("/versions/{version_id}/verification-evidence", response_model=AutomationFlowVerificationEvidenceResponse)
def record_automation_flow_version_verification_evidence_endpoint(
    version_id: str,
    request: AutomationFlowVerificationEvidenceRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": record_flow_version_verification_evidence(
            version_id=version_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.get("/versions/{version_id}/verification-evidence", response_model=AutomationFlowVerificationEvidenceListResponse)
def list_automation_flow_version_verification_evidence_endpoint(
    version_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    return list_flow_version_verification_evidence(
        version_id=version_id,
        current_user=current_user,
        limit=limit,
    )


@router.post("/versions/{version_id}/publish", response_model=AutomationFlowPublicationResponse)
def publish_automation_flow_version_endpoint(
    version_id: str,
    request: AutomationFlowVersionPublishRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": publish_flow_version(
            version_id=version_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.post("/publications/{publication_id}/rollback", response_model=AutomationFlowPublicationResponse)
def rollback_automation_flow_publication_endpoint(
    publication_id: str,
    request: AutomationFlowPublicationRollbackRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": rollback_publication(
            publication_id=publication_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@governance_router.get("/automation-flow-versions/{version_id}", response_model=AutomationFlowVersionResponse)
def get_automation_flow_version_detail_alias(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return get_automation_flow_version_detail(version_id=version_id, current_user=current_user)


@governance_router.patch("/automation-flow-versions/{version_id}", response_model=AutomationFlowVersionResponse)
def update_automation_flow_version_alias(
    version_id: str,
    request: AutomationFlowVersionUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    return update_automation_flow_version_endpoint(
        version_id=version_id,
        request=request,
        current_user=current_user,
    )


@governance_router.post("/automation-flow-versions/{version_id}/submit-review", response_model=AutomationFlowVersionResponse)
def submit_automation_flow_version_review_alias(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return submit_automation_flow_version_review(version_id=version_id, current_user=current_user)


@governance_router.post("/automation-flow-versions/{version_id}/approve", response_model=AutomationFlowVersionResponse)
def approve_automation_flow_version_alias(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return approve_automation_flow_version_endpoint(version_id=version_id, current_user=current_user)


@governance_router.post("/automation-flow-versions/{version_id}/preflight", response_model=AutomationFlowVersionPreflightResponse)
def run_automation_flow_version_preflight_alias(
    version_id: str,
    current_user: dict = Depends(require_admin),
):
    return run_automation_flow_version_preflight_endpoint(version_id=version_id, current_user=current_user)


@governance_router.post("/automation-flow-versions/{version_id}/verification-evidence", response_model=AutomationFlowVerificationEvidenceResponse)
def record_automation_flow_version_verification_evidence_alias(
    version_id: str,
    request: AutomationFlowVerificationEvidenceRequest,
    current_user: dict = Depends(require_admin),
):
    return record_automation_flow_version_verification_evidence_endpoint(
        version_id=version_id,
        request=request,
        current_user=current_user,
    )


@governance_router.get("/automation-flow-versions/{version_id}/verification-evidence", response_model=AutomationFlowVerificationEvidenceListResponse)
def list_automation_flow_version_verification_evidence_alias(
    version_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    return list_automation_flow_version_verification_evidence_endpoint(
        version_id=version_id,
        limit=limit,
        current_user=current_user,
    )


@governance_router.post("/automation-flow-versions/{version_id}/publish", response_model=AutomationFlowPublicationResponse)
def publish_automation_flow_version_alias(
    version_id: str,
    request: AutomationFlowVersionPublishRequest,
    current_user: dict = Depends(require_admin),
):
    return publish_automation_flow_version_endpoint(
        version_id=version_id,
        request=request,
        current_user=current_user,
    )


@governance_router.post("/automation-flow-publications/{publication_id}/rollback", response_model=AutomationFlowPublicationResponse)
def rollback_automation_flow_publication_alias(
    publication_id: str,
    request: AutomationFlowPublicationRollbackRequest,
    current_user: dict = Depends(require_admin),
):
    return rollback_automation_flow_publication_endpoint(
        publication_id=publication_id,
        request=request,
        current_user=current_user,
    )
