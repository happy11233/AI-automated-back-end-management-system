from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json
from app.mcp_client import call_mcp_tool
from app.permissions import POSITION_LABELS
from app.services.logging_service import write_audit_log
from app.services.run_record_service import elapsed_ms, now_ms, sanitize_metadata


McpToolRiskLevel = Literal["low", "medium", "high"]
McpToolPosition = Literal["operations", "customer_service", "finance", "platform"]

_SCHEMA_READY = False


@dataclass(frozen=True)
class ManagedMcpToolDefinition:
    tool_id: str
    server_name: str
    tool_name: str
    label: str
    category: str
    description: str
    risk_level: McpToolRiskLevel
    position_scopes: tuple[McpToolPosition, ...]
    execution_mode: str
    enabled_by_default: bool
    requires_approval: bool
    supports_real_health_check: bool
    input_schema: tuple[dict[str, Any], ...]
    output_schema: tuple[dict[str, Any], ...]
    safety_rules: tuple[str, ...]
    example: str


MCP_TOOL_DEFINITIONS: tuple[ManagedMcpToolDefinition, ...] = (
    ManagedMcpToolDefinition(
        tool_id="document_system.list_documents",
        server_name="document_system",
        tool_name="list_documents",
        label="列出文档系统文件",
        category="知识库",
        description="列出可同步到 RAG 的公司文档或飞书文档引用。",
        risk_level="low",
        position_scopes=("platform",),
        execution_mode="read_only",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=(),
        output_schema=({"name": "documents", "type": "json_array", "description": "文档文件名、标题、来源和 provider。"},),
        safety_rules=("仅管理员通过文档同步入口调用。", "不会直接修改知识库，入库仍由后端 RAG ingest 控制。"),
        example="管理员同步 MCP 文档到知识库。",
    ),
    ManagedMcpToolDefinition(
        tool_id="document_system.read_document",
        server_name="document_system",
        tool_name="read_document",
        label="读取文档内容",
        category="知识库",
        description="读取 list_documents 返回的指定文档内容，用于 RAG 入库。",
        risk_level="medium",
        position_scopes=("platform",),
        execution_mode="read_only",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=({"name": "filename", "type": "text", "required": True},),
        output_schema=({"name": "document", "type": "json", "description": "标题、来源、正文和 provider。"},),
        safety_rules=("只允许读取 docs 下的 md/txt 或已配置飞书文档。", "实际 RAG 可见性由后端入库参数决定。"),
        example="读取公司制度文档后写入知识库。",
    ),
    ManagedMcpToolDefinition(
        tool_id="ticket_system.create_ticket",
        server_name="ticket_system",
        tool_name="create_ticket",
        label="创建外部工单",
        category="业务协同",
        description="创建外部工单，适合客服转人工、售后跟进或管理员派单。",
        risk_level="medium",
        position_scopes=("customer_service", "platform"),
        execution_mode="write_controlled",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=(
            {"name": "title", "type": "text", "required": True},
            {"name": "description", "type": "textarea", "required": True},
            {"name": "priority", "type": "select", "required": False},
        ),
        output_schema=({"name": "ticket", "type": "json", "description": "工单号、状态和创建结果。"},),
        safety_rules=("由后端审批或客服流程调用。", "不会直接退款或修改订单。"),
        example="高风险客服问题转人工处理。",
    ),
    ManagedMcpToolDefinition(
        tool_id="ticket_system.get_ticket",
        server_name="ticket_system",
        tool_name="get_ticket",
        label="查询外部工单",
        category="业务协同",
        description="按工单号查询外部工单状态。",
        risk_level="low",
        position_scopes=("customer_service", "platform"),
        execution_mode="read_only",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=({"name": "ticket_id", "type": "text", "required": True},),
        output_schema=({"name": "ticket", "type": "json", "description": "工单详情或未找到信息。"},),
        safety_rules=("只读查询。", "普通员工入口仍需客服岗位权限。"),
        example="客服查看售后工单处理状态。",
    ),
    ManagedMcpToolDefinition(
        tool_id="erpnext.query_salary_slips",
        server_name="erpnext_tools",
        tool_name="query_salary_slips",
        label="查询 ERPNext 工资单",
        category="ERPNext",
        description="按工资期间只读查询 ERPNext Salary Slip。",
        risk_level="high",
        position_scopes=("finance", "platform"),
        execution_mode="read_only_sensitive",
        enabled_by_default=True,
        requires_approval=True,
        supports_real_health_check=True,
        input_schema=(
            {"name": "start_date", "type": "date", "required": True},
            {"name": "end_date", "type": "date", "required": True},
            {"name": "limit", "type": "integer", "required": False, "default": 80},
        ),
        output_schema=({"name": "salary_slips", "type": "json_array", "description": "工资单只读结果。"},),
        safety_rules=("只能由财务 Skill Executor 调用。", "调用前必须检查 Salary Slip ERP 权限。", "工资属于敏感数据。"),
        example="财务工资表导出 Skill 查询本月 Salary Slip。",
    ),
    ManagedMcpToolDefinition(
        tool_id="file_center.get_generated_file_download_path",
        server_name="file_center",
        tool_name="get_generated_file_download_path",
        label="生成文件下载路径",
        category="文件系统",
        description="根据生成文件产物 ID 返回后端下载路径，不直接返回文件内容。",
        risk_level="medium",
        position_scopes=("operations", "customer_service", "finance", "platform"),
        execution_mode="read_path_only",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=({"name": "artifact_id", "type": "text", "required": True},),
        output_schema=({"name": "download_path", "type": "text", "description": "后端下载路径。"},),
        safety_rules=("MCP 不读取文件字节。", "下载仍必须走 /files 权限校验。"),
        example="AI 生成工资表后返回可下载文件路径。",
    ),
    ManagedMcpToolDefinition(
        tool_id="n8n.dispatch_workflow",
        server_name="n8n_dispatcher",
        tool_name="dispatch_workflow",
        label="派发 n8n 工作流",
        category="外部自动化",
        description="把后端已授权的自动化任务投递到 n8n Webhook。",
        risk_level="high",
        position_scopes=("finance", "platform"),
        execution_mode="external_dispatch",
        enabled_by_default=True,
        requires_approval=True,
        supports_real_health_check=True,
        input_schema=(
            {"name": "workflow_type", "type": "text", "required": True},
            {"name": "payload", "type": "json", "required": True},
        ),
        output_schema=({"name": "dispatch", "type": "json", "description": "n8n 接收状态、外部引用和消息。"},),
        safety_rules=("payload 必须由后端 executor 构造。", "Webhook URL 必须通过 allowlist 安全校验。", "不允许大模型直接调用。"),
        example="工资表生成后投递 n8n，准备个人微信附件任务。",
    ),
    ManagedMcpToolDefinition(
        tool_id="desktop_rpa.prepare_wechat_attachment",
        server_name="desktop_rpa",
        tool_name="prepare_wechat_attachment",
        label="准备个人微信附件任务",
        category="桌面 RPA",
        description="为 Mac 个人微信半自动准备附件发送：打开微信、搜索联系人、粘贴附件，停在最终发送前；Windows 分支预留。",
        risk_level="high",
        position_scopes=("finance", "platform"),
        execution_mode="rpa_prepare_only",
        enabled_by_default=True,
        requires_approval=True,
        supports_real_health_check=True,
        input_schema=(
            {"name": "recipient_name", "type": "text", "required": True},
            {"name": "artifact_id", "type": "text", "required": False},
            {"name": "filename", "type": "text", "required": False},
            {"name": "download_path", "type": "text", "required": False},
            {"name": "local_file_path", "type": "text", "required": False},
            {"name": "platform_name", "type": "text", "required": False, "default": "mac"},
        ),
        output_schema=({"name": "rpa_task", "type": "json", "description": "RPA 预留任务、脚本提示和安全标志。"},),
        safety_rules=("不点击微信发送。", "联系人和工资敏感数据必须在文件生成后人工确认。", "本机文件路径只允许后端 executor 传给 MCP，不展示给普通用户。"),
        example="财务确认联系人后，Mac 自动打开个人微信并把工资表放入聊天窗口。",
    ),
    ManagedMcpToolDefinition(
        tool_id="playwright_amazon.prepare_seller_central_listing",
        server_name="playwright_amazon",
        tool_name="prepare_seller_central_listing",
        label="准备 Amazon Listing 填表",
        category="浏览器自动化",
        description="使用本机已登录浏览器状态打开 Seller Central，填写 Listing 草稿并停在发布前。",
        risk_level="high",
        position_scopes=("operations", "platform"),
        execution_mode="browser_prepare_only",
        enabled_by_default=True,
        requires_approval=True,
        supports_real_health_check=True,
        input_schema=(
            {"name": "listing", "type": "json", "required": True, "description": "标题、五点、描述、关键词、价格和库存。"},
            {"name": "target_marketplace", "type": "text", "required": False, "default": "US"},
            {"name": "sku", "type": "text", "required": False},
            {"name": "assets", "type": "json_array", "required": False, "description": "图片或表格产物引用，不直接包含账号凭证。"},
            {"name": "stop_before_publish", "type": "boolean", "required": False, "default": True},
            {"name": "upload_mode", "type": "select", "required": False, "options": ["auto", "web_form", "batch_excel"], "default": "auto"},
            {"name": "selector_profile", "type": "json", "required": False, "description": "管理员可视化字段映射保存后的选择器结构。"},
        ),
        output_schema=({"name": "browser_task", "type": "json", "description": "填表字段、配置状态和停在发布前的安全标志。"},),
        safety_rules=(
            "只能由运营 Skill Executor 或管理员受控入口调用。",
            "不保存 Amazon 账号密码。",
            "第一版永远不自动点击发布按钮。",
            "未配置浏览器登录态或字段选择器时只返回待配置状态。",
        ),
        example="运营审核 Listing 草稿后，自动打开 Seller Central 并填写字段，发布前由人工复核。",
    ),
    ManagedMcpToolDefinition(
        tool_id="message_sender.prepare_message_draft",
        server_name="message_sender",
        tool_name="prepare_message_draft",
        label="生成消息发送草稿",
        category="消息发送",
        description="为邮箱或企业微信生成待确认消息草稿，不真实发送。",
        risk_level="medium",
        position_scopes=("operations", "customer_service", "finance", "platform"),
        execution_mode="draft_only",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=(
            {"name": "channel", "type": "select", "required": True, "options": ["email", "enterprise_wechat"]},
            {"name": "recipient", "type": "text", "required": True},
            {"name": "subject", "type": "text", "required": False},
            {"name": "body", "type": "textarea", "required": True},
            {"name": "attachments", "type": "json_array", "required": False},
            {"name": "sensitive", "type": "boolean", "required": False, "default": False},
        ),
        output_schema=({"name": "message_draft", "type": "business_card", "description": "待确认的业务消息摘要和附件数量。"},),
        safety_rules=("只生成草稿。", "接收人、正文和附件必须在后端确认后才能发送。", "普通用户看不到底层 payload。"),
        example="财务生成月报附件后，先生成邮箱草稿等待确认。",
    ),
    ManagedMcpToolDefinition(
        tool_id="message_sender.send_confirmed_email",
        server_name="message_sender",
        tool_name="send_confirmed_email",
        label="发送已确认邮件",
        category="消息发送",
        description="用户确认接收人和敏感数据后，通过 SMTP 发送业务邮件和附件。",
        risk_level="high",
        position_scopes=("finance", "platform"),
        execution_mode="external_send_confirmed",
        enabled_by_default=True,
        requires_approval=True,
        supports_real_health_check=True,
        input_schema=(
            {"name": "recipient", "type": "email", "required": True},
            {"name": "subject", "type": "text", "required": True},
            {"name": "body", "type": "textarea", "required": True},
            {"name": "attachments", "type": "json_array", "required": False},
            {"name": "confirmed", "type": "boolean", "required": True},
            {"name": "sensitive_confirmed", "type": "boolean", "required": True},
        ),
        output_schema=({"name": "send_result", "type": "json", "description": "发送状态、通道和脱敏后的接收人。"},),
        safety_rules=(
            "不能由大模型直接调用。",
            "必须确认接收人、正文和敏感数据。",
            "默认真实发送开关关闭。",
            "附件本机路径只允许读取生成文件目录。",
        ),
        example="财务确认月报和工资附件后，后端通过 SMTP 发送给指定邮箱。",
    ),
    ManagedMcpToolDefinition(
        tool_id="message_sender.search_enterprise_wechat_recipient",
        server_name="message_sender",
        tool_name="search_enterprise_wechat_recipient",
        label="搜索企业微信接收对象",
        category="消息发送",
        description="按姓名、群聊或部门名称搜索企业微信候选对象，重名时必须让用户点选。",
        risk_level="medium",
        position_scopes=("finance", "platform"),
        execution_mode="recipient_lookup",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=(
            {"name": "query", "type": "text", "required": True},
            {"name": "object_types", "type": "multi_select", "required": False, "options": ["user", "group", "department"]},
            {"name": "limit", "type": "integer", "required": False, "default": 8},
        ),
        output_schema=({"name": "candidates", "type": "business_card_list", "description": "头像、姓名、对象类型、部门和手机号后四位。"},),
        safety_rules=(
            "只返回候选摘要，不发送消息。",
            "同名或多候选必须由用户点选。",
            "普通用户看不到完整手机号。",
        ),
        example="财务说发给张三时，先搜索企业微信候选人。",
    ),
    ManagedMcpToolDefinition(
        tool_id="message_sender.send_confirmed_enterprise_wechat_file",
        server_name="message_sender",
        tool_name="send_confirmed_enterprise_wechat_file",
        label="发送已确认企业微信文件",
        category="消息发送",
        description="用户确认接收对象和敏感数据后，通过企业微信应用发送 Excel / Word 文件，不附带正文说明。",
        risk_level="high",
        position_scopes=("finance", "platform"),
        execution_mode="external_send_confirmed",
        enabled_by_default=True,
        requires_approval=True,
        supports_real_health_check=True,
        input_schema=(
            {"name": "recipient", "type": "json", "required": False},
            {"name": "recipient_candidate_id", "type": "text", "required": False},
            {"name": "attachments", "type": "json_array", "required": True},
            {"name": "confirmed", "type": "boolean", "required": True},
            {"name": "sensitive_confirmed", "type": "boolean", "required": True},
        ),
        output_schema=({"name": "send_result", "type": "business_card", "description": "企业微信发送状态、接收对象和附件数量。"},),
        safety_rules=(
            "不能由大模型直接调用。",
            "必须确认接收对象和敏感数据。",
            "不发送正文说明，只发送文件。",
            "默认真实发送开关关闭。",
            "附件本机路径只允许读取生成文件目录。",
        ),
        example="财务确认工资表和接收对象后，后端通过企业微信应用发送文件。",
    ),
    ManagedMcpToolDefinition(
        tool_id="postgres_readonly.summarize_automation_runs",
        server_name="postgres_readonly",
        tool_name="summarize_automation_runs",
        label="汇总自动化运行状态",
        category="管理员诊断",
        description="按状态、应用和类型汇总最近自动化运行记录，返回中文表格化摘要。",
        risk_level="high",
        position_scopes=("platform",),
        execution_mode="readonly_diagnostics",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=({"name": "limit", "type": "integer", "required": False, "default": 50},),
        output_schema=({"name": "summary_table", "type": "table", "description": "状态、类型、应用和次数。"},),
        safety_rules=("管理员专用。", "固定只读查询。", "不允许自由 SQL。", "不返回连接串或原始 payload。"),
        example="管理员询问最近自动化失败最多的是哪类。",
    ),
    ManagedMcpToolDefinition(
        tool_id="postgres_readonly.list_recent_failures",
        server_name="postgres_readonly",
        tool_name="list_recent_failures",
        label="查看最近失败记录",
        category="管理员诊断",
        description="列出最近失败或阻断的自动化运行记录，便于管理员排查。",
        risk_level="high",
        position_scopes=("platform",),
        execution_mode="readonly_diagnostics",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=({"name": "limit", "type": "integer", "required": False, "default": 10},),
        output_schema=({"name": "items", "type": "table", "description": "运行 ID、应用、岗位、状态和错误摘要。"},),
        safety_rules=("管理员专用。", "只读查询。", "只返回摘要字段。", "普通员工不能使用数据库 MCP。"),
        example="管理员查看最近有哪些自动化被阻断。",
    ),
    ManagedMcpToolDefinition(
        tool_id="postgres_readonly.get_run_diagnostics",
        server_name="postgres_readonly",
        tool_name="get_run_diagnostics",
        label="查看运行诊断摘要",
        category="管理员诊断",
        description="按运行 ID 查看执行步骤和错误摘要，不返回 raw SQL 或大段 JSON。",
        risk_level="high",
        position_scopes=("platform",),
        execution_mode="readonly_diagnostics",
        enabled_by_default=True,
        requires_approval=False,
        supports_real_health_check=True,
        input_schema=({"name": "run_id", "type": "text", "required": True},),
        output_schema=(
            {"name": "run", "type": "business_card", "description": "运行摘要。"},
            {"name": "steps", "type": "table", "description": "步骤摘要。"},
        ),
        safety_rules=("管理员专用。", "固定只读查询。", "不展示 SQL、连接串或完整 payload。"),
        example="管理员问某次微信发送为什么没有进入 RPA。",
    ),
)

_MCP_TOOLS_BY_ID = {tool.tool_id: tool for tool in MCP_TOOL_DEFINITIONS}


def ensure_mcp_tool_registry_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    execute(
        """
        CREATE TABLE IF NOT EXISTS mcp_tool_settings (
            tool_id TEXT PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            health_status TEXT NOT NULL DEFAULT 'unknown',
            health_message TEXT,
            last_checked_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    _SCHEMA_READY = True


def list_static_mcp_tools() -> list[dict[str, Any]]:
    return [_definition_to_public(definition, None) for definition in MCP_TOOL_DEFINITIONS]


def list_mcp_tools() -> dict[str, Any]:
    ensure_mcp_tool_registry_schema()
    settings_by_id = _tool_settings_by_id()
    items = [
        _definition_to_public(definition, settings_by_id.get(definition.tool_id))
        for definition in MCP_TOOL_DEFINITIONS
    ]
    return {
        "summary": _summary(items),
        "items": items,
    }


def get_mcp_tool(tool_id: str) -> dict[str, Any]:
    ensure_mcp_tool_registry_schema()
    definition = get_mcp_tool_definition(tool_id)
    return {
        "item": _definition_to_public(definition, _get_tool_setting(tool_id)),
    }


def get_mcp_tool_definition(tool_id: str) -> ManagedMcpToolDefinition:
    try:
        return _MCP_TOOLS_BY_ID[tool_id]
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MCP 工具不存在") from error


def update_mcp_tool(
    *,
    tool_id: str,
    enabled: bool,
    admin_note: str | None,
    current_user: dict,
) -> dict[str, Any]:
    ensure_mcp_tool_registry_schema()
    definition = get_mcp_tool_definition(tool_id)
    existing = _get_tool_setting(tool_id)
    metadata = {
        **((existing or {}).get("metadata") or {}),
        "admin_note": (admin_note or "").strip()[:1000],
    }
    setting = _upsert_tool_setting(
        tool_id=tool_id,
        enabled=enabled,
        health_status=(existing or {}).get("health_status") or "unknown",
        health_message=(existing or {}).get("health_message"),
        metadata=metadata,
        current_user=current_user,
    )
    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.mcp_tool.update",
        resource_type="mcp_tool",
        resource_id=tool_id,
        metadata={
            "tool_id": tool_id,
            "label": definition.label,
            "enabled": enabled,
            "username": current_user.get("username"),
        },
    )
    return {"item": _definition_to_public(definition, setting)}


def check_mcp_tool_health(*, tool_id: str, current_user: dict) -> dict[str, Any]:
    ensure_mcp_tool_registry_schema()
    definition = get_mcp_tool_definition(tool_id)
    try:
        result = call_mcp_tool(definition.server_name, "health_check", {})
    except Exception as error:
        result = {
            "ok": False,
            "status": "unhealthy",
            "message": str(error),
        }

    health_status = _health_status_from_result(result)
    health_message = str(result.get("message") or result.get("status") or health_status)
    existing = _get_tool_setting(tool_id)
    setting = _upsert_tool_setting(
        tool_id=tool_id,
        enabled=_enabled_for(definition, existing),
        health_status=health_status,
        health_message=health_message,
        metadata={
            **((existing or {}).get("metadata") or {}),
            "last_health_payload": sanitize_metadata(result),
        },
        current_user=current_user,
        touch_health=True,
    )
    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.mcp_tool.health_check",
        resource_type="mcp_tool",
        resource_id=tool_id,
        metadata={
            "tool_id": tool_id,
            "label": definition.label,
            "health_status": health_status,
            "username": current_user.get("username"),
        },
    )
    return {
        "item": _definition_to_public(definition, setting),
        "health": sanitize_metadata(result),
    }


def execute_managed_mcp_tool(
    *,
    tool_id: str,
    arguments: dict[str, Any] | None,
    current_user: dict,
    source: str,
    trace_collector: list[dict[str, Any]] | None = None,
) -> Any:
    started_ms = now_ms()
    ensure_mcp_tool_registry_schema()
    definition = get_mcp_tool_definition(tool_id)
    try:
        setting = _get_tool_setting(tool_id)
        if not _enabled_for(definition, setting):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"MCP 工具已暂停：{definition.label}")

        _ensure_position_allowed(definition=definition, current_user=current_user)
        if definition.risk_level == "high" and source in {"llm", "llm_direct", "chat_direct", "react_only"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="高风险 MCP 工具不能由大模型直接调用，必须通过后端 Skill Executor。",
            )

        result = call_mcp_tool(definition.server_name, definition.tool_name, arguments or {})
        duration_ms = elapsed_ms(started_ms)
        trace = _mcp_tool_trace(
            definition=definition,
            current_user=current_user,
            source=source,
            arguments=arguments or {},
            result=result,
            duration_ms=duration_ms,
        )
        if trace_collector is not None:
            trace_collector.append(trace)
        write_audit_log(
            user_id=current_user.get("id"),
            action="mcp_tool.invoke",
            resource_type="mcp_tool",
            resource_id=tool_id,
            metadata={
                **trace,
                "arguments": sanitize_metadata(arguments or {}),
            },
        )
        return result
    except Exception as error:
        if trace_collector is not None:
            trace_collector.append(_mcp_tool_trace(
                definition=definition,
                current_user=current_user,
                source=source,
                arguments=arguments or {},
                result=None,
                duration_ms=elapsed_ms(started_ms),
                error_message=str(error),
            ))
        raise


def _tool_settings_by_id() -> dict[str, dict[str, Any]]:
    rows = fetch_all(
        """
        SELECT tool_id, enabled, health_status, health_message, last_checked_at, metadata, updated_by, updated_at
        FROM mcp_tool_settings;
        """
    )
    return {_row_to_setting(row)["tool_id"]: _row_to_setting(row) for row in rows}


def _get_tool_setting(tool_id: str) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT tool_id, enabled, health_status, health_message, last_checked_at, metadata, updated_by, updated_at
        FROM mcp_tool_settings
        WHERE tool_id = %s
        LIMIT 1;
        """,
        (tool_id,),
    )
    return _row_to_setting(row) if row else None


def _upsert_tool_setting(
    *,
    tool_id: str,
    enabled: bool,
    health_status: str,
    health_message: str | None,
    metadata: dict[str, Any],
    current_user: dict,
    touch_health: bool = False,
) -> dict[str, Any]:
    row = fetch_one(
        """
        INSERT INTO mcp_tool_settings (
            tool_id, enabled, health_status, health_message, last_checked_at, metadata, updated_by, updated_at
        )
        VALUES (%s, %s, %s, %s, CASE WHEN %s THEN now() ELSE NULL END, %s::jsonb, %s, now())
        ON CONFLICT (tool_id) DO UPDATE
        SET enabled = EXCLUDED.enabled,
            health_status = EXCLUDED.health_status,
            health_message = EXCLUDED.health_message,
            last_checked_at = CASE WHEN %s THEN now() ELSE mcp_tool_settings.last_checked_at END,
            metadata = EXCLUDED.metadata,
            updated_by = EXCLUDED.updated_by,
            updated_at = now()
        RETURNING tool_id, enabled, health_status, health_message, last_checked_at, metadata, updated_by, updated_at;
        """,
        (
            tool_id,
            enabled,
            health_status,
            health_message,
            touch_health,
            dumps_json(sanitize_metadata(metadata)),
            current_user.get("id"),
            touch_health,
        ),
    )
    return _row_to_setting(row)


def _row_to_setting(row) -> dict[str, Any]:
    return {
        "tool_id": str(row[0]),
        "enabled": bool(row[1]),
        "health_status": row[2],
        "health_message": row[3],
        "last_checked_at": row[4].isoformat() if row[4] else None,
        "metadata": row[5] or {},
        "updated_by": str(row[6]) if row[6] else None,
        "updated_at": row[7].isoformat() if row[7] else None,
    }


def _definition_to_public(
    definition: ManagedMcpToolDefinition,
    setting: dict[str, Any] | None,
) -> dict[str, Any]:
    enabled = _enabled_for(definition, setting)
    health_status = (setting or {}).get("health_status") or "unknown"
    return {
        "id": definition.tool_id,
        "tool_id": definition.tool_id,
        "server_name": definition.server_name,
        "tool_name": definition.tool_name,
        "label": definition.label,
        "category": definition.category,
        "description": definition.description,
        "risk_level": definition.risk_level,
        "risk_label": _risk_label(definition.risk_level),
        "position_scopes": list(definition.position_scopes),
        "position_scope_labels": [_position_label(item) for item in definition.position_scopes],
        "execution_mode": definition.execution_mode,
        "enabled": enabled,
        "status": "enabled" if enabled else "paused",
        "status_label": "已启用" if enabled else "已暂停",
        "requires_approval": definition.requires_approval,
        "supports_real_health_check": definition.supports_real_health_check,
        "health_status": "disabled" if not enabled else health_status,
        "health_message": (setting or {}).get("health_message") or "尚未执行健康检查。",
        "last_checked_at": (setting or {}).get("last_checked_at"),
        "input_schema": list(definition.input_schema),
        "output_schema": list(definition.output_schema),
        "safety_rules": list(definition.safety_rules),
        "example": definition.example,
        "admin_note": ((setting or {}).get("metadata") or {}).get("admin_note") or "",
    }


def _summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(items),
        "enabled": sum(1 for item in items if item["enabled"]),
        "paused": sum(1 for item in items if not item["enabled"]),
        "high_risk": sum(1 for item in items if item["risk_level"] == "high"),
        "servers": len({item["server_name"] for item in items}),
        "healthy": sum(1 for item in items if item["health_status"] in {"healthy", "configured", "stub_ready"}),
    }


def _enabled_for(definition: ManagedMcpToolDefinition, setting: dict[str, Any] | None) -> bool:
    if setting is None:
        return definition.enabled_by_default
    return bool(setting.get("enabled"))


def _health_status_from_result(result: dict[str, Any]) -> str:
    if result.get("ok") is True:
        raw = str(result.get("status") or "healthy").strip().lower()
        if raw in {"healthy", "configured", "stub_ready"}:
            return raw
        return "healthy"
    raw = str(result.get("status") or "unhealthy").strip().lower()
    if raw in {"not_configured", "invalid_config", "disabled"}:
        return raw
    return "unhealthy"


def _ensure_position_allowed(*, definition: ManagedMcpToolDefinition, current_user: dict) -> None:
    if current_user.get("role") == "admin":
        return
    position = current_user.get("position")
    if position in definition.position_scopes:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"当前岗位无权调用 MCP 工具：{definition.label}",
    )


def _position_label(position: str) -> str:
    if position == "platform":
        return "管理员/平台"
    return POSITION_LABELS.get(position, position)


def _risk_label(risk_level: str) -> str:
    return {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
    }.get(risk_level, risk_level)


def _mcp_tool_trace(
    *,
    definition: ManagedMcpToolDefinition,
    current_user: dict,
    source: str,
    arguments: dict[str, Any],
    result: Any,
    duration_ms: int,
    error_message: str | None = None,
) -> dict[str, Any]:
    result_status = "failed" if error_message else "succeeded"
    message = error_message
    if isinstance(result, dict):
        result_status = str(result.get("status") or ("succeeded" if result.get("ok", True) else "failed"))
        message = str(result.get("message") or result_status)
    return {
        "tool_id": definition.tool_id,
        "label": definition.label,
        "server_name": definition.server_name,
        "tool_name": definition.tool_name,
        "category": definition.category,
        "risk_level": definition.risk_level,
        "risk_label": _risk_label(definition.risk_level),
        "requires_approval": definition.requires_approval,
        "position_scopes": list(definition.position_scopes),
        "position_scope_labels": [_position_label(item) for item in definition.position_scopes],
        "execution_mode": definition.execution_mode,
        "source": source,
        "status": result_status,
        "message": message or result_status,
        "duration_ms": duration_ms,
        "argument_keys": sorted(arguments.keys()),
        "backend_permission_checked": True,
        "permission_gate": "Skill Executor / backend policy",
        "llm_direct_execution_allowed": False,
        "manual_final_send_required": bool(
            isinstance(result, dict) and result.get("manual_final_send_required") is True
        ),
        "error_message": error_message,
    }
