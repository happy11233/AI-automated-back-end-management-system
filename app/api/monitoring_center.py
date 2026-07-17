from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.monitoring_center_service import build_monitoring_center


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
    p95_duration_ms: int
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
    latest_run_at: str | None


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


class MonitoringCenterResponse(BaseModel):
    scope: MonitoringScope
    overall_status: str
    database: MonitoringDatabase
    run_summary: MonitoringRunSummary
    run_trend: list[MonitoringTrendPoint]
    position_summary: list[MonitoringPositionSummary]
    run_type_summary: list[MonitoringRunTypeSummary]
    recent_issues: list[MonitoringRunEvent]
    slow_runs: list[MonitoringRunEvent]
    audit_summary: MonitoringAuditSummary
    audit_actions: list[MonitoringAuditAction]
    connectors: MonitoringConnectors
    erp_health: MonitoringErpHealth
    evaluation: MonitoringEvaluation
    knowledge: MonitoringKnowledge
    users: MonitoringUsers
    service_health: list[MonitoringServiceHealthItem]


@router.get("", response_model=MonitoringCenterResponse)
def get_monitoring_center(
    date_range: str = Query(default="30d", pattern="^(7d|30d|90d|all)$"),
    current_user: dict = Depends(require_admin),
):
    return build_monitoring_center(date_range=date_range)
