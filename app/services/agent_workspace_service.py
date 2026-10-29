"""Read-only Agent activity, scoped to existing workflow and record permissions."""
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.db import fetch_all, fetch_one
from app.services.ai_workflow_service import list_ai_workflows


def automation_readiness(workflow: dict[str, Any]) -> dict[str, Any]:
    if workflow['id'] == 'operations_competitor_analysis':
        return {
            'state': 'mock_monitor', 'label': '模拟价格监控',
            'trigger_label': '手动分析 / 每天四次巡检',
            'description': '专用看板提供模拟商品价格对比；北京时间 08:00、11:00、14:00、16:00 巡检，实际运行状态以看板为准。',
            'requirements': ['应用迁移 025', '启动 Celery worker 和 beat', '官方开放 API 尚待授权与适配'],
        }
    if workflow["id"] == "customer_service_message_loop":
        return {
            "state": "webhook_available",
            "label": "事件入口可用 · 接入待验证",
            "trigger_label": "客户消息事件",
            "description": "已支持认证 webhook 接收消息并自动处理；尚不能确认外部渠道持续投递。低风险结果仍需以渠道回执确认发送。",
            "requirements": ["外部渠道连接并投递消息", "使用客服账号令牌或已配置的 webhook 密钥认证", "确认业务数据权限与执行渠道"],
            "webhook_secret_configured": bool(settings.customer_service_webhook_secret),
        }
    from app.services.agent_business_event_service import EVENT_ADAPTERS

    if workflow["id"] in EVENT_ADAPTERS:
        event_type = EVENT_ADAPTERS[workflow["id"]][0]
        return {
            "state": "event_available", "label": "业务事件入口可用 · 待连接来源",
            "trigger_label": "业务系统事件",
            "description": "已支持结构化业务事件自动执行与重复事件去重；尚未确认外部系统持续投递，不表示已开启定时任务。",
            "requirements": ["连接业务系统并投递 " + event_type + " 事件", "完成字段映射与账号授权", "验证回写结果和通知"],
            "event_type": event_type,
        }
    return {
        "state": "requires_source",
        "label": "待接入数据源",
        "trigger_label": "业务事件待接入",
        "description": "已有业务处理能力，当前仍依赖人工提供资料；自动事件、数据映射和调度尚未接通。",
        "requirements": ["连接业务数据源", "映射任务所需字段", "配置并验证事件或定时触发规则"],
    }


def _app_ids(workflow: dict[str, Any]) -> list[str]:
    source = workflow.get("source_task_id")
    special = {
        "finance_excel_transform": "finance-excel-transform",
        "finance_reconciliation": "finance-reconciliation",
        "customer_service_message_loop": "customer-service-message-loop",
    }
    return list(dict.fromkeys([workflow["id"], special.get(source, "automation-" + str(source))]))


def agent_activity(current_user: dict, workflow_id: str | None = None, status: str | None = None) -> dict[str, Any]:
    workflows = list_ai_workflows(current_user)
    if workflow_id:
        workflows = [item for item in workflows if item["id"] == workflow_id]
        if not workflows:
            raise HTTPException(status_code=404, detail="Agent 不存在或无权访问")
    result: dict[str, Any] = {
        "summary": {"total": 0, "running": 0, "succeeded": 0, "failed": 0, "blocked": 0},
        "agents": [{"id": item["id"], "readiness": automation_readiness(item)} for item in workflows],
        "recent": [], "trend": [], "as_of": datetime.now(timezone.utc).isoformat(),
        "scope": "全部获授权 Agent 的执行记录" if current_user.get("role") == "admin" else "本人在当前岗位下的执行记录",
    }
    app_ids = list(dict.fromkeys(app_id for workflow in workflows for app_id in _app_ids(workflow)))
    if not app_ids:
        return result
    conditions = ["app_id = ANY(%s)"]
    params: list[Any] = [app_ids]
    if current_user.get("role") != "admin":
        conditions.extend(["user_id = %s", "position = %s"])
        params.extend([current_user["id"], current_user.get("position")])
    where = " AND ".join(conditions)
    counts = fetch_one(
        "SELECT count(*), count(*) FILTER (WHERE status='running'), count(*) FILTER (WHERE status='succeeded'), "
        "count(*) FILTER (WHERE status='failed'), count(*) FILTER (WHERE status='blocked') "
        "FROM automation_runs WHERE " + where, tuple(params),
    )
    result["summary"] = dict(zip(result["summary"], counts))
    rows = fetch_all(
        "SELECT to_char(started_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD'), count(*), "
        "count(*) FILTER (WHERE status='failed') FROM automation_runs WHERE " + where +
        " AND started_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Shanghai') AT TIME ZONE 'Asia/Shanghai' - interval '6 days' "
        "GROUP BY 1 ORDER BY 1", tuple(params),
    )
    result["trend"] = [{"date": row[0], "total": row[1], "failed": row[2]} for row in rows]
    recent_params = list(params)
    if status:
        where += " AND status = %s"
        recent_params.append(status)
    rows = fetch_all(
        "SELECT id, app_id, app_name, status, output_preview, error_message, started_at, finished_at "
        "FROM automation_runs WHERE " + where + " ORDER BY started_at DESC, id DESC LIMIT 20", tuple(recent_params),
    )
    result["recent"] = [{
        "id": str(row[0]), "app_id": row[1], "name": row[2], "status": row[3],
        "output": row[4], "error": row[5],
        "started_at": row[6].isoformat() if row[6] else None,
        "finished_at": row[7].isoformat() if row[7] else None,
    } for row in rows]
    return result
