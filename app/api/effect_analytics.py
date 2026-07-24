from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.effect_analytics_service import build_effect_analytics


router = APIRouter(
    prefix="/effect-analytics",
    tags=["effect-analytics"],
)


class EffectAnalyticsScope(BaseModel):
    role: str | None
    position: str | None
    position_label: str
    date_range: str
    date_range_label: str
    since: str | None
    generated_at: str


class EffectAnalyticsSummary(BaseModel):
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    running_runs: int
    success_rate: float
    failure_rate: float
    blocked_rate: float
    avg_duration_ms: int
    total_duration_ms: int
    estimated_saved_minutes: int
    estimated_saved_hours: float


class EffectStatusBucket(BaseModel):
    status: str
    count: int


class EffectTrendPoint(BaseModel):
    date: str
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int


class EffectPositionStat(BaseModel):
    position: str
    position_label: str
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    success_rate: float
    estimated_saved_minutes: int


class EffectAppStat(BaseModel):
    app_id: str
    app_name: str
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    success_rate: float
    last_run_at: str | None


class EffectRunTypeStat(BaseModel):
    run_type: str
    label: str
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    blocked_runs: int
    success_rate: float
    avg_duration_ms: int


class EffectFailureReason(BaseModel):
    status: str
    reason: str
    count: int
    last_seen_at: str | None


class EffectAuditAction(BaseModel):
    action: str
    resource_type: str | None
    count: int
    last_seen_at: str | None


class EffectAuditSummary(BaseModel):
    total_events: int
    blocked_events: int
    approval_events: int
    top_actions: list[EffectAuditAction]


class EffectEstimateModelItem(BaseModel):
    run_type: str
    saved_minutes_per_run: int
    description: str


class EffectAnalyticsResponse(BaseModel):
    scope: EffectAnalyticsScope
    summary: EffectAnalyticsSummary
    status_distribution: list[EffectStatusBucket]
    trend: list[EffectTrendPoint]
    position_ranking: list[EffectPositionStat]
    app_ranking: list[EffectAppStat]
    run_type_ranking: list[EffectRunTypeStat]
    failure_reasons: list[EffectFailureReason]
    audit_summary: EffectAuditSummary
    estimate_model: list[EffectEstimateModelItem]


@router.get("", response_model=EffectAnalyticsResponse)
def get_effect_analytics(
    date_range: str = Query(default="30d", pattern="^(7d|30d|90d|all)$"),
    position: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(require_admin),
):
    return build_effect_analytics(
        current_user=current_user,
        date_range=date_range,
        position=position,
    )
