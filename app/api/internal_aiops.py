import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.erp.providers import get_active_provider


router = APIRouter(
    prefix="/internal/aiops",
    tags=["internal-aiops"],
)


class AIOpsDrillIncidentRequest(BaseModel):
    failure_type: str = Field(default="http_5xx", description="http_5xx 或 slow_response")
    message: str | None = Field(default=None, max_length=500)
    delay_ms: int = Field(default=0, ge=0, le=10000)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _drill_state_path() -> Path:
    return Path("data/aiops_drill_state.json")


def _default_drill_state() -> dict[str, Any]:
    return {
        "active": False,
        "failure_type": None,
        "message": "",
        "delay_ms": 0,
        "updated_at": None,
    }


def _load_drill_state() -> dict[str, Any]:
    state = _default_drill_state()
    path = _drill_state_path()
    if not path.exists():
        return state
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return state
    if isinstance(payload, dict):
        state.update(payload)
    return state


def _save_drill_state(state: dict[str, Any]) -> dict[str, Any]:
    path = _drill_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def _require_probe_secret(secret: str | None) -> None:
    expected = settings.aiops_probe_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AIOps internal probes are not enabled",
        )
    if secret != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid AIOps probe secret",
        )


@router.get("/erp-health")
def get_erp_health_for_aiops(
    x_aiops_probe_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_probe_secret(x_aiops_probe_secret)
    provider = get_active_provider()
    result = provider.health_check()
    payload = {
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "ok": bool(result.get("ok")),
        "configured": bool(result.get("configured")),
        "status": str(result.get("status") or "unknown"),
        "message": str(result.get("message") or ""),
        "detail": result.get("detail"),
    }
    if not payload["ok"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=payload,
        )
    return payload


@router.get("/drill/state")
def get_aiops_drill_state(
    x_aiops_probe_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_probe_secret(x_aiops_probe_secret)
    return _load_drill_state()


@router.post("/drill/inject")
def inject_aiops_drill_incident(
    request: AIOpsDrillIncidentRequest,
    x_aiops_probe_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_probe_secret(x_aiops_probe_secret)
    failure_type = request.failure_type.strip()
    if failure_type not in {"http_5xx", "slow_response"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="failure_type 仅支持 http_5xx 或 slow_response",
        )

    delay_ms = request.delay_ms
    if failure_type == "slow_response" and delay_ms <= 0:
        delay_ms = 1500

    state = _save_drill_state(
        {
            "active": True,
            "failure_type": failure_type,
            "message": request.message or "AIOps controlled drill incident",
            "delay_ms": delay_ms,
            "injected_at": _now_iso(),
            "recovered_at": None,
        }
    )
    return {"ok": True, "state": state}


@router.post("/drill/recover")
def recover_aiops_drill_incident(
    x_aiops_probe_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_probe_secret(x_aiops_probe_secret)
    previous = _load_drill_state()
    state = _save_drill_state(
        {
            **previous,
            "active": False,
            "delay_ms": 0,
            "message": "AIOps drill recovered",
            "recovered_at": _now_iso(),
        }
    )
    return {"ok": True, "previous": previous, "state": state}


@router.get("/drill-health")
def get_aiops_drill_health(
    x_aiops_probe_secret: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_probe_secret(x_aiops_probe_secret)
    state = _load_drill_state()
    delay_ms = int(state.get("delay_ms") or 0)
    if delay_ms > 0:
        time.sleep(min(delay_ms, 10000) / 1000)

    if state.get("active"):
        failure_type = state.get("failure_type") or "http_5xx"
        payload = {
            "ok": False,
            "status": failure_type,
            "message": state.get("message") or "AIOps controlled drill incident",
            "drill": state,
        }
        if failure_type == "http_5xx":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=payload,
            )
        return payload

    return {
        "ok": True,
        "status": "healthy",
        "message": "AIOps drill probe is healthy",
        "drill": state,
    }
