"""Authenticated structured events. No external publication or scheduled polling."""
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.db import execute, pool
from app.services.ai_workflow_service import get_ai_workflow, run_ai_workflow


class ProductEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sku: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=300)
    marketplace: str = Field(min_length=1, max_length=120)
    attributes: dict[str, str] = Field(min_length=1, max_length=30)
    compliance_requirements: str = Field(min_length=1, max_length=2000)


class CompetitorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    marketplace: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=300)
    competitors: list[dict[str, str]] = Field(min_length=1, max_length=10)


class ReportEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    period: str = Field(min_length=1, max_length=100)
    currency: str = Field(min_length=3, max_length=8)
    metrics: dict[str, float] = Field(min_length=1, max_length=40)
    review_requirements: str = Field(default="", max_length=1000)


EVENT_ADAPTERS = {
    "operations_listing_launch": ("product.updated", ProductEvent),
    "operations_competitor_analysis": ("competitor.snapshot", CompetitorEvent),
    "finance_report_analysis": ("finance.report.ready", ReportEvent),
}
_schema_ready = False


def ensure_agent_event_schema() -> None:
    global _schema_ready
    if not _schema_ready:
        execute((Path(__file__).resolve().parents[2] / "sql/023_agent_business_events.sql").read_text())
        _schema_ready = True


def receive_business_event(*, current_user: dict, workflow_id: str, event_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    workflow = get_ai_workflow(workflow_id, current_user)
    adapter = EVENT_ADAPTERS.get(workflow_id)
    if adapter is None or event_type != adapter[0]:
        raise HTTPException(422, "该 Agent 尚未接入此事件类型")
    try:
        structured = adapter[1].model_validate(data).model_dump()
        encoded = json.dumps(structured, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (ValidationError, ValueError, TypeError):
        raise HTTPException(422, "业务事件缺少必填字段或字段格式不正确") from None
    if len(encoded.encode()) > 16000:
        raise HTTPException(422, "业务事件数据超过 16KB")
    event_id = event_id.strip()
    if not event_id:
        raise HTTPException(422, "事件标识不能为空")
    digest = sha256((event_type + encoded).encode()).hexdigest()
    ensure_agent_event_schema()
    # Claim is committed before any LLM work. Redelivery never re-runs a claimed
    # event, even after an uncertain response or a worker/process interruption.
    with pool.connection() as conn:
        with conn.transaction():
            claim = conn.execute(
                "INSERT INTO agent_business_events (user_id,workflow_id,event_id,payload_hash,status) "
                "VALUES (%s,%s,%s,%s,'processing') ON CONFLICT DO NOTHING RETURNING id",
                (current_user["id"], workflow_id, event_id, digest),
            ).fetchone()
            if not claim:
                previous = conn.execute(
                    "SELECT id,payload_hash,status,run_id,error_code,notification_id FROM agent_business_events "
                    "WHERE user_id=%s AND workflow_id=%s AND event_id=%s",
                    (current_user["id"], workflow_id, event_id),
                ).fetchone()
                if previous[1] != digest:
                    raise HTTPException(409, "同一事件标识已用于不同业务数据")
                if previous[2] == "processing":
                    raise HTTPException(409, "事件已接收，正在处理或等待确认，不会重复执行")
                return {"event_id": event_id, "status": previous[2], "run_id": str(previous[3]) if previous[3] else None, "reused": True, "error_code": previous[4]}
    record_id = str(claim[0])
    try:
        # The event has actual business fields; no prompt is requested from users.
        result = run_ai_workflow(
            workflow_id=workflow_id,
            input_text="业务事件：" + event_type + "\n授权业务数据：\n" + encoded,
            current_user=current_user,
            business_event_id=record_id,
        )
    except Exception as error:
        execute("UPDATE agent_business_events SET status='failed',error_code=%s,finished_at=now() WHERE id=%s", (type(error).__name__, record_id))
        # Persist only an error class, not prompts, credentials or upstream bodies.
        raise HTTPException(502, "Agent 事件执行失败，事件已记录，请检查运行记录；相同事件不会重复执行") from None
    # Result status and notification commit together; a duplicate response cannot
    # create a second notification or business execution.
    with pool.connection() as conn:
        with conn.transaction():
            notification = conn.execute(
                "INSERT INTO notifications (user_id,type,title,body,resource_type,resource_id,metadata) "
                "VALUES (%s,'agent_event',%s,%s,'agent',%s,%s::jsonb) RETURNING id",
                (current_user["id"], workflow["name"] + "处理完成", "业务事件已处理，请查看任务成果；外部发布状态以业务结果为准。", workflow_id, json.dumps({"event_id": record_id, "run_id": result["run_id"]})),
            ).fetchone()
            conn.execute("UPDATE agent_business_events SET status='succeeded',run_id=%s,notification_id=%s,finished_at=now() WHERE id=%s", (result["run_id"], notification[0], record_id))
    return {"event_id": event_id, "status": "succeeded", "run_id": result["run_id"], "reused": False}


def business_event_status(*, current_user: dict, workflow_id: str, event_id: str) -> dict[str, Any]:
    get_ai_workflow(workflow_id, current_user)
    ensure_agent_event_schema()
    from app.db import fetch_one

    row = fetch_one(
        "SELECT e.status,e.run_id,e.error_code,e.created_at,e.finished_at,r.status, "
        "e.status='processing' AND e.created_at < now()-interval '15 minutes' "
        "FROM agent_business_events e LEFT JOIN automation_runs r ON r.id=e.run_id "
        "WHERE e.user_id=%s AND e.workflow_id=%s AND e.event_id=%s",
        (current_user["id"], workflow_id, event_id),
    )
    if not row:
        raise HTTPException(404, "事件不存在或无权访问")
    return {"event_id": event_id, "status": row[0], "run_id": str(row[1]) if row[1] else None,
        "error_code": row[2], "created_at": row[3].isoformat(),
        "finished_at": row[4].isoformat() if row[4] else None,
        "run_status": row[5], "requires_confirmation": bool(row[6]),
        "automatic_retry": False}
