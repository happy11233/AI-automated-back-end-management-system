from __future__ import annotations

from app.db import execute, fetch_all
from app.permissions import POSITION_LABELS, is_valid_position
from app.services.automation_service import AUTOMATION_TASKS


SPECIAL_POSITION_APPS: dict[str, list[str]] = {
    "finance": [
        "finance-excel-transform",
        "finance-reconciliation",
    ],
    "customer_service": [
        "customer-service-refund-approvals",
        "customer-service-message-loop",
    ],
}

ADMIN_PLATFORM_APPS = [
    "admin-knowledge",
    "admin-audit",
]

SPECIAL_APP_LABELS: dict[str, tuple[str, str]] = {
    "finance-excel-transform": ("财务 Excel 生成", "文件自动化"),
    "finance-reconciliation": ("财务对账自动化", "财务对账"),
    "customer-service-refund-approvals": ("退款审批", "客服售后"),
    "customer-service-message-loop": ("客服消息自动化闭环", "客服售后"),
    "admin-knowledge": ("知识库维护", "知识治理"),
    "admin-audit": ("审计与权限追踪", "安全治理"),
}


def ensure_user_ai_app_permission_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS user_ai_app_permissions (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            app_id TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, app_id)
        );
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_ai_app_permissions_app
        ON user_ai_app_permissions(app_id, enabled);
        """
    )


def available_ai_app_ids_for_user(user: dict) -> list[str]:
    return [item["id"] for item in available_ai_apps_for_user(user)]


def available_ai_apps_for_user(user: dict) -> list[dict]:
    role = user.get("role")
    position = user.get("position")
    positions: list[str]

    if role == "admin":
        positions = ["operations", "customer_service", "finance"]
    elif is_valid_position(position):
        positions = [str(position)]
    else:
        positions = []

    apps: list[dict] = []
    for item in positions:
        apps.extend(_position_ai_apps(item))

    if role == "admin":
        for app_id in ADMIN_PLATFORM_APPS:
            name, category = SPECIAL_APP_LABELS[app_id]
            apps.append({
                "id": app_id,
                "name": name,
                "position": "platform",
                "position_label": "平台",
                "category": category,
            })

    return _unique_apps(apps)


def allowed_ai_app_ids_for_user(user: dict) -> list[str]:
    available_apps = available_ai_apps_for_user(user)
    if not available_apps:
        return []

    rows = fetch_all(
        """
        SELECT app_id, enabled
        FROM user_ai_app_permissions
        WHERE user_id = %s;
        """,
        (user["id"],),
    )
    overrides = {str(row[0]): bool(row[1]) for row in rows}

    return [
        app["id"]
        for app in available_apps
        for app_id in [app["id"]]
        if overrides.get(app_id, True)
    ]


def ai_app_permission_items_for_user(user: dict) -> list[dict]:
    allowed_ids = set(allowed_ai_app_ids_for_user(user))
    return [
        {
            **item,
            "enabled": item["id"] in allowed_ids,
        }
        for item in available_ai_apps_for_user(user)
    ]


def is_ai_app_allowed(user: dict, app_id: str) -> bool:
    if user.get("role") == "admin":
        return True

    return app_id in allowed_ai_app_ids_for_user(user)


def set_user_ai_app_permission(
    *,
    user_id: str,
    app_id: str,
    enabled: bool,
    actor_id: str,
) -> None:
    execute(
        """
        INSERT INTO user_ai_app_permissions (user_id, app_id, enabled, updated_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, app_id)
        DO UPDATE SET
            enabled = EXCLUDED.enabled,
            updated_by = EXCLUDED.updated_by,
            updated_at = now();
        """,
        (user_id, app_id, enabled, actor_id),
    )


def _position_ai_apps(position: str) -> list[dict]:
    position_label = POSITION_LABELS.get(position, position)
    apps = [
        {
            "id": f"automation-{task_id}",
            "name": spec["label"],
            "position": position,
            "position_label": position_label,
            "category": "岗位自动化",
        }
        for task_id, spec in AUTOMATION_TASKS.get(position, {}).items()
        if not (position == "finance" and task_id == "excel_transform")
    ]

    for app_id in SPECIAL_POSITION_APPS.get(position, []):
        name, category = SPECIAL_APP_LABELS[app_id]
        apps.append({
            "id": app_id,
            "name": name,
            "position": position,
            "position_label": position_label,
            "category": category,
        })

    apps.extend([
        {
            "id": f"{position}-erp-query",
            "name": f"{position_label}数据问答助手",
            "position": position,
            "position_label": position_label,
            "category": "数据查询",
        },
        {
            "id": f"{position}-chat-agent",
            "name": f"{position_label} AI 对话",
            "position": position,
            "position_label": position_label,
            "category": "AI Agent",
        },
    ])

    return apps


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result


def _unique_apps(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []

    for item in items:
        app_id = str(item["id"])
        if app_id in seen:
            continue

        seen.add(app_id)
        result.append(item)

    return result
