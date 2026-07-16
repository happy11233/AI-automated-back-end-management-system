from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.evaluation_center_service import build_evaluation_center, run_rag_evaluation


router = APIRouter(
    prefix="/evaluation-center",
    tags=["evaluation-center"],
)


class EvaluationSummary(BaseModel):
    dataset_count: int
    report_count: int
    regression_suite_count: int
    total_cases: int
    average_pass_rate: float


class EvaluationDataset(BaseModel):
    id: str
    name: str
    category: str
    description: str
    path: str
    report_path: str
    runner: str
    case_count: int
    positive_cases: int
    refusal_cases: int
    has_report: bool
    can_run: bool
    updated_at: str | None
    report_updated_at: str | None


class EvaluationReport(BaseModel):
    dataset_id: str
    dataset_name: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, Any] = Field(default_factory=dict)
    pass_rate: float | None
    failed_cases: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None


class EvaluationRegressionSuite(BaseModel):
    id: str
    name: str
    category: str
    description: str
    command: str
    case_count: int
    real_services: list[str]


class EvaluationReleaseGate(BaseModel):
    id: str
    name: str
    status: str
    threshold: str
    actual: str


class EvaluationCenterResponse(BaseModel):
    summary: EvaluationSummary
    datasets: list[EvaluationDataset]
    reports: list[EvaluationReport]
    regression_suites: list[EvaluationRegressionSuite]
    release_gates: list[EvaluationReleaseGate]


class RagEvaluationRunResponse(BaseModel):
    dataset: EvaluationDataset
    report: EvaluationReport


@router.get("", response_model=EvaluationCenterResponse)
def get_evaluation_center(current_user: dict = Depends(require_admin)):
    return build_evaluation_center()


@router.post("/run-rag", response_model=RagEvaluationRunResponse)
def post_run_rag_evaluation(
    dataset_id: str = Query(default="rag_smoke"),
    top_k: int = Query(default=5, ge=1, le=10),
    current_user: dict = Depends(require_admin),
):
    return run_rag_evaluation(dataset_id=dataset_id, top_k=top_k)
