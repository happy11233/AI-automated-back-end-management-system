from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable

from fastapi import HTTPException, status

from app.permissions import POSITION_LABELS, erp_scopes_for_position, is_valid_position
from app.services.user_ai_app_permission_service import is_ai_app_allowed
from app.skills.registry import SkillDefinition, get_skill


MIN_REACT_EXECUTION_CONFIDENCE = 0.8


@dataclass
class SkillExecutionResult:
    skill_id: str
    status: str
    run_id: str | None = None
    answer: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    platform_draft: dict[str, Any] | None = None
    approval_result: dict[str, Any] | None = None
    erp_references: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_skill_access(
    *,
    skill: SkillDefinition,
    current_user: dict,
    react_decision: dict[str, Any] | None = None,
    requested_erp_resources: list[str] | None = None,
) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        position = current_user.get("position")
        if not is_valid_position(position):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前账号未绑定岗位，无法执行自动化 Skill。",
            )
        if position != skill.position:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{POSITION_LABELS.get(str(position), '当前')}岗位无权执行{skill.name}。",
            )
        if not _is_skill_app_allowed(current_user, skill.app_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{skill.name}应用已被管理员禁用。",
            )

    if react_decision:
        confidence = react_decision.get("confidence")
        if isinstance(confidence, (int, float)) and confidence < MIN_REACT_EXECUTION_CONFIDENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="自动化意图置信度不足，请先追问用户确认后再执行 Skill。",
            )

        requested_position = react_decision.get("requested_position")
        if requested_position not in {None, "unknown", skill.position}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"ReAct 判断的业务岗位与 Skill 不一致，已阻断执行：{requested_position}。",
            )

    _validate_erp_resources(skill=skill, current_user=current_user, requested_erp_resources=requested_erp_resources)

    execution_user = _execution_user_for_skill(current_user=current_user, skill=skill)
    return {
        "skill_id": skill.skill_id,
        "app_id": skill.app_id,
        "flow_key": skill.flow_key,
        "position": skill.position,
        "execution_user": execution_user,
        "requested_erp_resources": requested_erp_resources or [],
    }


def execute_skill(
    *,
    skill_id: str,
    payload: dict[str, Any],
    current_user: dict,
    source: str,
    react_decision: dict[str, Any] | None = None,
) -> SkillExecutionResult:
    skill = get_skill(skill_id)
    requested_erp_resources = _payload_requested_erp_resources(payload)
    context = validate_skill_access(
        skill=skill,
        current_user=current_user,
        react_decision=react_decision,
        requested_erp_resources=requested_erp_resources,
    )
    executor = _load_executor(skill.executor)
    return executor(
        payload=payload,
        current_user=context["execution_user"],
        source=source,
        skill=skill,
        execution_context=context,
    )


def _execution_user_for_skill(*, current_user: dict, skill: SkillDefinition) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        return current_user
    return {**current_user, "position": skill.position}


def _is_skill_app_allowed(current_user: dict, app_id: str) -> bool:
    allowed_ids = current_user.get("allowed_ai_app_ids")
    if isinstance(allowed_ids, list):
        return app_id in {str(item) for item in allowed_ids}
    return is_ai_app_allowed(current_user, app_id)


def _validate_erp_resources(
    *,
    skill: SkillDefinition,
    current_user: dict,
    requested_erp_resources: list[str] | None,
) -> None:
    requested = requested_erp_resources or []
    allowed_by_skill = set(skill.allowed_erp_resources)
    allowed_by_position = set(erp_scopes_for_position(skill.position))

    for resource in requested:
        if resource not in allowed_by_skill:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{skill.name}不允许访问 ERP 资源：{resource}",
            )
        if resource not in allowed_by_position:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{POSITION_LABELS[skill.position]}岗位无权访问 ERP 资源：{resource}",
            )
        if current_user.get("role") != "admin" and resource not in erp_scopes_for_position(current_user.get("position")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"当前岗位无权访问 ERP 资源：{resource}",
            )


def _payload_requested_erp_resources(payload: dict[str, Any]) -> list[str]:
    raw_value = payload.get("erp_resources") or payload.get("requested_erp_resources") or []
    if isinstance(raw_value, str):
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    return []


def _load_executor(dotted_path: str) -> Callable[..., SkillExecutionResult]:
    module_name, function_name = dotted_path.split(":", 1)
    module = import_module(module_name)
    executor = getattr(module, function_name)
    if not callable(executor):
        raise TypeError(f"Skill executor 不可调用：{dotted_path}")
    return executor
