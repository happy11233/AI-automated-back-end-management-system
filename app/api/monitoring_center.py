from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.aiops_bridge_service import (
    AIOpsBridgeError,
    get_aiops_incident_detail,
    repair_aiops_incident,
)
from app.services.monitoring_center_service import build_monitoring_center
from app.services.live_metrics_service import build_live_metrics


router = APIRouter(
    prefix="/monitoring-center",
    tags=["monitoring-center"],
)


class MonitoringScope(BaseModel):
    date_range: str
    date_range_label: str
    since: str | None
    generated_at: str


class MonitoringDatabase(BaseModel):
    status: str
    message: str
    checked_at: str | None
    database_name: str


class MonitoringRunSummary(BaseModel):
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    running_runs: int
    success_rate: float
    failure_rate: float
    blocked_rate: float
    avg_duration_ms: int
    p50_duration_ms: int
    p95_duration_ms: int
    p99_duration_ms: int
    duration_samples: int
    latest_run_at: str | None
    active_users: int


class MonitoringTrendPoint(BaseModel):
    date: str
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    running_runs: int


class MonitoringPositionSummary(BaseModel):
    position: str
    position_label: str
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    success_rate: float
    avg_duration_ms: int


class MonitoringRunTypeSummary(BaseModel):
    run_type: str
    label: str
    app_name: str | None
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    success_rate: float
    avg_duration_ms: int
    p50_duration_ms: int
    p95_duration_ms: int
    p99_duration_ms: int
    duration_samples: int
    latest_run_at: str | None


class MonitoringStepSummary(BaseModel):
    step_name: str
    provider: str
    stage_type: str
    total_steps: int
    succeeded_steps: int
    failed_steps: int
    blocked_steps: int
    avg_duration_ms: int
    p50_duration_ms: int
    p95_duration_ms: int
    p99_duration_ms: int
    duration_samples: int
    latest_step_at: str | None


class MonitoringRunEvent(BaseModel):
    id: str
    status: str
    run_type: str
    run_type_label: str
    app_id: str
    app_name: str
    position: str | None
    position_label: str
    duration_ms: int | None
    occurred_at: str | None = None
    started_at: str | None = None
    summary: str | None = None


class MonitoringAuditSummary(BaseModel):
    total_events: int
    security_events: int
    approval_events: int
    user_admin_events: int
    latest_event_at: str | None


class MonitoringAuditAction(BaseModel):
    action: str
    resource_type: str | None
    count: int
    last_seen_at: str | None


class MonitoringConnectorSummary(BaseModel):
    total: int
    configured: int
    healthy: int
    needs_config: int
    pending: int


class MonitoringConnectorItem(BaseModel):
    id: str
    label: str
    category: str
    active: bool
    configured: bool
    status: str
    health_status: str
    health_message: str
    supports_real_health_check: bool
    position_scope_labels: list[str]
    last_checked_at: str


class MonitoringConnectors(BaseModel):
    summary: MonitoringConnectorSummary
    items: list[MonitoringConnectorItem]


class MonitoringErpHealth(BaseModel):
    provider: str
    provider_label: str
    configured: bool
    ok: bool
    status: str
    message: str
    checked_at: str


class MonitoringEvaluation(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)
    release_gates: list[dict[str, Any]] = Field(default_factory=list)
    latest_report_at: str | None
    status: str


class MonitoringKnowledge(BaseModel):
    total_documents: int
    active_documents: int
    latest_document_at: str | None
    child_chunks: int
    indexed_documents: int
    latest_chunk_at: str | None
    parent_chunks: int


class MonitoringUserBucket(BaseModel):
    role: str
    position: str
    position_label: str
    count: int


class MonitoringUsers(BaseModel):
    total_users: int
    items: list[MonitoringUserBucket]


class MonitoringServiceHealthItem(BaseModel):
    id: str
    name: str
    status: str
    message: str
    metric: str


class MonitoringAiopsHealth(BaseModel):
    status: str
    message: str
    checked_at: str | None
    base_url: str | None


class MonitoringAiopsSummary(BaseModel):
    service_target_count: int
    enabled_service_target_count: int
    incident_count: int
    open_incident_count: int
    critical_open_incident_count: int
    action_required_count: int
    remediating_count: int
    resolved_count: int
    failed_count: int
    last_incident_at: str | None
    scheduler_enabled: bool
    default_inspection_interval_seconds: int
    storage_backend: str
    poll_interval_seconds: int
    repairable_count: int


class MonitoringAiopsIncidentItem(BaseModel):
    incident_id: str
    title: str
    service: str
    environment: str
    namespace: str
    severity: str
    severity_label: str
    status: str
    status_label: str
    alert_type: str
    alert_type_label: str
    summary: str
    current_stage: str
    current_stage_label: str
    root_cause: str | None
    impact: str | None
    recommendation: str | None
    service_target_id: str | None
    runtime_type: str | None
    evidence_count: int
    action_count: int
    repair_available: bool
    repair_reason: str | None
    latest_verification_status: str | None
    latest_verification_summary: str | None
    created_at: str | None
    updated_at: str | None
    detail_api: str
    repair_api: str


class MonitoringAiopsIntegration(BaseModel):
    configured: bool
    reachable: bool
    status: str
    message: str
    base_url: str | None
    health: MonitoringAiopsHealth
    summary: MonitoringAiopsSummary
    incidents: list[MonitoringAiopsIncidentItem]


class MonitoringAiopsRepairRequest(BaseModel):
    reason: str | None = None


class MonitoringAiopsRepairResponse(BaseModel):
    run: dict[str, Any]
    detail: dict[str, Any]


class MonitoringCenterResponse(BaseModel):
    scope: MonitoringScope
    overall_status: str
    database: MonitoringDatabase
    run_summary: MonitoringRunSummary
    run_trend: list[MonitoringTrendPoint]
    position_summary: list[MonitoringPositionSummary]
    run_type_summary: list[MonitoringRunTypeSummary]
    step_summary: list[MonitoringStepSummary]
    recent_issues: list[MonitoringRunEvent]
    slow_runs: list[MonitoringRunEvent]
    audit_summary: MonitoringAuditSummary
    audit_actions: list[MonitoringAuditAction]
    connectors: MonitoringConnectors
    erp_health: MonitoringErpHealth
    evaluation: MonitoringEvaluation
    knowledge: MonitoringKnowledge
    users: MonitoringUsers
    aiops: MonitoringAiopsIntegration
    service_health: list[MonitoringServiceHealthItem]


@router.get("", response_model=MonitoringCenterResponse)
def get_monitoring_center(
    date_range: str = Query(default="30d", pattern="^(7d|30d|90d|all)$"),
    current_user: dict = Depends(require_admin),
):
    return build_monitoring_center(date_range=date_range)


@router.get("/live-metrics")
def get_monitoring_live_metrics(current_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return build_live_metrics()


@router.get("/aiops/incidents/{incident_id}", response_model=dict[str, Any])
def get_monitoring_center_aiops_incident(
    incident_id: str,
    current_user: dict = Depends(require_admin),
):
    try:
        return get_aiops_incident_detail(incident_id)
    except AIOpsBridgeError as error:
        raise _bridge_http_exception(error) from error


@router.post("/aiops/incidents/{incident_id}/repair", response_model=MonitoringAiopsRepairResponse)
def repair_monitoring_center_aiops_incident(
    incident_id: str,
    request: MonitoringAiopsRepairRequest | None = None,
    current_user: dict = Depends(require_admin),
):
    approved_by = (
        current_user.get("username")
        or current_user.get("display_name")
        or current_user.get("id")
        or "admin"
    )
    reason = (
        request.reason.strip()
        if request and request.reason and request.reason.strip()
        else "管理员在监控中心二次确认 AI 修复"
    )
    try:
        return repair_aiops_incident(
            incident_id,
            approved_by=approved_by,
            reason=reason,
        )
    except AIOpsBridgeError as error:
        raise _bridge_http_exception(error) from error


def _bridge_http_exception(error: AIOpsBridgeError) -> HTTPException:
    message = str(error)
    status_code = 404 if message.startswith("404") else 502
    return HTTPException(status_code=status_code, detail=message)
