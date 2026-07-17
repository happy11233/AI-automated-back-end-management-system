from typing import Literal

from fastapi import HTTPException, status

from app.services.logging_service import write_audit_log


Position = Literal["operations", "customer_service", "finance"]

POSITION_LABELS: dict[str, str] = {
    "operations": "运营",
    "customer_service": "客服",
    "finance": "财务",
}

POSITION_DEFAULT_DEPARTMENTS: dict[str, str] = {
    "operations": "运营部",
    "customer_service": "客服部",
    "finance": "财务部",
}

POSITION_CAPABILITIES: dict[str, list[str]] = {
    "operations": [
        "生成 Listing",
        "生成标题",
        "生成五点描述",
        "生成关键词",
        "生成促销文案",
        "竞品分析",
    ],
    "customer_service": [
        "智能客服",
        "自动回复",
        "退款售后话术",
        "多语言客服翻译",
    ],
    "finance": [
        "分析财务报表",
        "统计工资",
        "上传 Excel 后按财务要求生成新 Excel 表",
        "财务对账自动化",
    ],
}

POSITION_ERP_SCOPES: dict[str, list[str]] = {
    "operations": [
        "Item",
        "Item Price",
        "Sales Order",
        "Sales Invoice summary",
    ],
    "customer_service": [
        "Customer",
        "Sales Order",
        "Delivery Note",
        "Issue",
        "Return request",
    ],
    "finance": [
        "GL Entry",
        "Payment Entry",
        "Salary Slip",
        "Sales Invoice",
        "Purchase Invoice",
    ],
}

POSITION_BLOCKED_KEYWORDS: dict[str, list[str]] = {
    "operations": [
        "财务报表",
        "工资",
        "薪资",
        "利润",
        "毛利",
        "净利",
        "成本明细",
        "付款流水",
        "银行流水",
    ],
    "customer_service": [
        "财务报表",
        "工资",
        "薪资",
        "利润",
        "毛利",
        "净利",
        "成本明细",
        "付款流水",
        "银行流水",
        "员工薪酬",
    ],
    "finance": [
        "客服私有会话",
        "客服聊天记录",
        "售后私聊",
        "运营私有数据",
        "运营私有会话",
    ],
}


def is_valid_position(position: str | None) -> bool:
    return position in POSITION_LABELS


def default_department_for_position(position: str | None) -> str | None:
    if position is None:
        return None

    return POSITION_DEFAULT_DEPARTMENTS.get(position)


def capabilities_for_position(position: str | None) -> list[str]:
    if position is None:
        return []

    return POSITION_CAPABILITIES.get(position, [])


def erp_scopes_for_position(position: str | None) -> list[str]:
    if position is None:
        return []

    return POSITION_ERP_SCOPES.get(position, [])


def all_erp_scopes() -> list[str]:
    scopes: list[str] = []
    for items in POSITION_ERP_SCOPES.values():
        for item in items:
            if item not in scopes:
                scopes.append(item)

    return scopes


def validate_user_position(role: str, position: str | None) -> None:
    if role == "admin":
        if position is not None and not is_valid_position(position):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="岗位只能是 operations、customer_service 或 finance",
            )
        return

    if role != "employee":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色只能是 admin 或 employee",
        )

    if not is_valid_position(position):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="员工必须选择岗位：operations、customer_service 或 finance",
        )


def ensure_chat_allowed_for_position(current_user: dict, message: str) -> None:
    if current_user.get("role") == "admin":
        return

    position = current_user.get("position")

    if not is_valid_position(position):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未绑定岗位，请联系管理员分配岗位后再使用 AI 对话。",
        )

    blocked_keywords = POSITION_BLOCKED_KEYWORDS.get(position, [])
    normalized_message = message.lower()
    matched_keyword = next(
        (
            keyword
            for keyword in blocked_keywords
            if keyword.lower() in normalized_message
        ),
        None,
    )

    if matched_keyword:
        label = POSITION_LABELS.get(position, position)
        write_audit_log(
            user_id=current_user.get("id"),
            action="chat.blocked_by_position",
            resource_type="position",
            resource_id=str(position),
            metadata={
                "username": current_user.get("username"),
                "position": position,
                "keyword": matched_keyword,
                "message": message[:500],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{label}岗位无权查询“{matched_keyword}”相关内容。",
        )


def ensure_erp_resource_allowed(current_user: dict, resource: str) -> None:
    if current_user.get("role") == "admin":
        return

    position = current_user.get("position")

    if not is_valid_position(position):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未绑定岗位，无法访问 ERP。",
        )

    allowed_resources = erp_scopes_for_position(position)
    if resource in allowed_resources:
        return

    label = POSITION_LABELS.get(position, position)
    write_audit_log(
        user_id=current_user.get("id"),
        action="erp.query.blocked_by_position",
        resource_type="erp",
        resource_id=resource,
        metadata={
            "username": current_user.get("username"),
            "position": position,
            "resource": resource,
            "allowed_resources": allowed_resources,
        },
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"{label}岗位无权查询 ERP 资源：{resource}",
    )
