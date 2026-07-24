from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from app.permissions import erp_scopes_for_position


SkillRiskLevel = Literal["low", "medium", "high"]
SkillPosition = Literal["operations", "customer_service", "finance"]


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str
    name: str
    description: str
    position: SkillPosition
    app_id: str
    flow_key: str
    legacy_ids: tuple[str, ...]
    react_actions: tuple[str, ...]
    entrypoints: tuple[str, ...]
    risk_level: SkillRiskLevel
    requires_approval: bool
    allowed_erp_resources: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    executor: str
    skill_doc_path: str
    verification_scripts: tuple[str, ...]
    input_schema: tuple[dict[str, Any], ...]
    output_schema: tuple[dict[str, Any], ...]
    safety_rules: tuple[str, ...]


SKILL_DEFINITIONS: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        skill_id="operations_listing",
        name="运营 Listing 上架草稿",
        description="根据 SKU、产品卖点、目标站点和合规限制生成 Listing 上架草稿，并写入平台草稿区等待运营审核。",
        position="operations",
        app_id="automation-listing",
        flow_key="automation:operations:listing",
        legacy_ids=("operations_listing_launch", "operations_listing_draft", "listing"),
        react_actions=("operations_listing_draft",),
        entrypoints=("/chat", "/chat/stream", "/ai-workflows/operations_listing_launch/run"),
        risk_level="medium",
        requires_approval=False,
        allowed_erp_resources=("Item", "Item Price", "Sales Order"),
        allowed_tools=("llm.chat", "platform_drafts.write", "rpa.queue_ready", "run_records"),
        executor="app.skills.operations_listing.executor:execute",
        skill_doc_path="app/skills/operations_listing/SKILL.md",
        verification_scripts=(
            "scripts/verify_chat_automation_dispatch.py",
            "scripts/verify_ai_workflows.py",
            "scripts/verify_platform_draft_automation.py",
        ),
        input_schema=(
            {
                "name": "message",
                "type": "textarea",
                "required": True,
                "max_length": 10000,
                "description": "SKU、产品名、卖点、站点、受众、竞品差异和合规限制。",
            },
        ),
        output_schema=(
            {"name": "answer", "type": "markdown_text", "description": "Listing 内容和优化说明。"},
            {"name": "platform_draft", "type": "json", "description": "平台草稿 ID、状态和写回状态。"},
            {"name": "run_id", "type": "text", "description": "运行记录 ID。"},
        ),
        safety_rules=(
            "仅运营岗位或管理员可执行。",
            "非管理员必须启用 automation-listing。",
            "管理员执行时必须按运营岗位收窄执行上下文。",
            "只保存平台草稿，不直接发布到外部平台。",
        ),
    ),
    SkillDefinition(
        skill_id="customer_reply",
        name="客服回复草稿",
        description="根据客户消息、订单号、物流单号和售后问题生成客服回复草稿，低风险待发送，高风险转人工或审批。",
        position="customer_service",
        app_id="customer-service-message-loop",
        flow_key="automation:customer_service:message-loop",
        legacy_ids=("customer_service_reply_draft", "customer_service_message_loop"),
        react_actions=("customer_service_reply_draft",),
        entrypoints=("/chat", "/chat/stream", "/customer-service/messages"),
        risk_level="high",
        requires_approval=True,
        allowed_erp_resources=("Customer", "Sales Order", "Delivery Note", "Issue", "Return request"),
        allowed_tools=("customer_service.messages", "erp.provider.query", "rag.retrieve", "llm.chat", "approval.request", "run_records"),
        executor="app.skills.customer_reply.executor:execute",
        skill_doc_path="app/skills/customer_reply/SKILL.md",
        verification_scripts=(
            "scripts/verify_chat_automation_dispatch.py",
            "scripts/verify_customer_service_automation.py",
            "scripts/verify_customer_service_refund_approvals.py",
        ),
        input_schema=(
            {"name": "message", "type": "textarea", "required": True, "max_length": 10000},
            {"name": "order_no", "type": "text", "required": False},
            {"name": "tracking_no", "type": "text", "required": False},
        ),
        output_schema=(
            {"name": "reply_draft", "type": "markdown_text"},
            {"name": "platform_draft", "type": "json"},
            {"name": "approval_result", "type": "json"},
            {"name": "erp_references", "type": "json_array"},
        ),
        safety_rules=(
            "仅客服岗位或管理员可执行。",
            "非管理员必须启用 customer-service-message-loop。",
            "RAG 查询必须继续传 current_user.id，不能绕过 owner/team/grant。",
            "退款、投诉、差评、拒付等高风险必须转人工或审批。",
        ),
    ),
    SkillDefinition(
        skill_id="finance_salary_export",
        name="财务工资表导出",
        description="识别工资表导出请求，按期间查询 ERP Salary Slip，并生成可下载工资 Excel。",
        position="finance",
        app_id="automation-salary_summary",
        flow_key="automation:finance:salary-export",
        legacy_ids=("finance_salary_export", "finance_salary_summary", "salary_summary"),
        react_actions=("finance_salary_export",),
        entrypoints=("/chat", "/chat/stream", "/automation/finance/salary-export"),
        risk_level="high",
        requires_approval=True,
        allowed_erp_resources=("Salary Slip",),
        allowed_tools=("intent.recognizer", "erp.provider.query", "openpyxl.write_workbook", "run_records"),
        executor="app.skills.finance_salary_export.executor:execute",
        skill_doc_path="app/skills/finance_salary_export/SKILL.md",
        verification_scripts=(
            "scripts/verify_finance_salary_export.py",
            "scripts/verify_chat_react_guardrails.py",
        ),
        input_schema=(
            {"name": "message", "type": "textarea", "required": True, "max_length": 1000},
        ),
        output_schema=(
            {"name": "workbook", "type": "xlsx"},
            {"name": "summary", "type": "json"},
            {"name": "run_id", "type": "text"},
        ),
        safety_rules=(
            "仅财务岗位或管理员可执行。",
            "非管理员必须启用 automation-salary_summary。",
            "ERP 资源只能是 Salary Slip。",
            "模糊 Excel 请求必须追问，不能直接执行工资导出。",
        ),
    ),
    SkillDefinition(
        skill_id="finance_excel_settlement",
        name="财务 Excel 生成",
        description="上传真实财务 Excel，并可选择财务岗位权限内 ERP 表，生成新工作簿、数值汇总和 AI 建议。",
        position="finance",
        app_id="finance-excel-transform",
        flow_key="automation:finance:excel-file-transform",
        legacy_ids=("finance_excel_settlement", "finance_excel_transform"),
        react_actions=(),
        entrypoints=("/automation/finance/excel-transform", "/ai-workflows/finance_excel_settlement"),
        risk_level="medium",
        requires_approval=False,
        allowed_erp_resources=tuple(erp_scopes_for_position("finance")),
        allowed_tools=("erp.provider.query", "pandas.read_excel", "openpyxl.write_workbook", "llm.chat", "run_records"),
        executor="app.skills.finance_excel_settlement.executor:execute",
        skill_doc_path="app/skills/finance_excel_settlement/SKILL.md",
        verification_scripts=("scripts/verify_finance_excel_transform.py",),
        input_schema=(
            {"name": "file", "type": "file", "required": True, "accept": [".xlsx", ".xls"], "max_bytes": 8 * 1024 * 1024},
            {"name": "instruction", "type": "textarea", "required": False, "max_length": 2000},
            {"name": "erp_resources", "type": "multi_select", "required": False, "max_items": 5},
        ),
        output_schema=(
            {"name": "workbook", "type": "xlsx"},
            {"name": "metadata", "type": "json"},
            {"name": "run_id", "type": "text"},
        ),
        safety_rules=(
            "仅财务岗位或管理员可执行。",
            "非管理员必须启用 finance-excel-transform。",
            "ERP 表只能选择财务岗位和 Skill 声明资源的交集。",
            "文件大小、格式和空文件检查不能丢。",
        ),
    ),
    SkillDefinition(
        skill_id="finance_reconciliation",
        name="财务对账自动化",
        description="上传结算、物流、采购、广告和汇率表，按订单号/SKU 匹配并生成利润表和异常账单。",
        position="finance",
        app_id="finance-reconciliation",
        flow_key="automation:finance:reconciliation",
        legacy_ids=("finance_reconciliation",),
        react_actions=(),
        entrypoints=("/automation/finance/reconciliation", "/ai-workflows/finance_reconciliation"),
        risk_level="medium",
        requires_approval=False,
        allowed_erp_resources=(),
        allowed_tools=("pandas.read_excel", "field_mapping", "order_sku_matching", "profit_calculation", "openpyxl.write_workbook", "run_records"),
        executor="app.skills.finance_reconciliation.executor:execute",
        skill_doc_path="app/skills/finance_reconciliation/SKILL.md",
        verification_scripts=("scripts/verify_finance_reconciliation.py",),
        input_schema=(
            {"name": "files", "type": "file_list", "required": True, "accept": [".xlsx", ".xls"], "max_files": 8},
            {"name": "instruction", "type": "textarea", "required": False, "max_length": 2000},
            {"name": "base_currency", "type": "select", "required": False, "default": "CNY"},
        ),
        output_schema=(
            {"name": "workbook", "type": "xlsx"},
            {"name": "summary", "type": "json"},
            {"name": "run_id", "type": "text"},
        ),
        safety_rules=(
            "仅财务岗位或管理员可执行。",
            "非管理员必须启用 finance-reconciliation。",
            "保留多文件数量、单文件大小和总大小校验。",
            "结果需财务复核，不自动入账、不自动付款。",
        ),
    ),
)

_SKILLS_BY_ID = {skill.skill_id: skill for skill in SKILL_DEFINITIONS}
_SKILLS_BY_REACT_ACTION = {
    action: skill
    for skill in SKILL_DEFINITIONS
    for action in skill.react_actions
}


def list_skills(*, position: str | None = None) -> list[SkillDefinition]:
    items = list(SKILL_DEFINITIONS)
    if position:
        items = [skill for skill in items if skill.position == position]
    return items


def get_skill(skill_id: str) -> SkillDefinition:
    try:
        return _SKILLS_BY_ID[skill_id]
    except KeyError as error:
        raise KeyError(f"Skill 不存在：{skill_id}") from error


def skill_for_react_action(action: str) -> SkillDefinition | None:
    return _SKILLS_BY_REACT_ACTION.get(action)


def skill_doc_absolute_path(skill: SkillDefinition) -> Path:
    return Path(__file__).resolve().parents[2] / skill.skill_doc_path
