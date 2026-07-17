from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.erp.resources import list_resource_definitions
from app.permissions import POSITION_LABELS, erp_scopes_for_position, is_valid_position
from app.services.automation_service import AUTOMATION_TASKS


FLOW_VERSION = "2026.07.17"


def list_flow_configs(current_user: dict) -> list[dict[str, Any]]:
    positions = _visible_positions(current_user)
    flows: list[dict[str, Any]] = []

    for position in positions:
        flows.extend(_automation_task_flows(position))
        if position == "customer_service":
            flows.append(_customer_service_message_loop_flow())
        flows.append(_erp_query_flow(position))
        flows.append(_chat_flow(position))
        if position == "finance":
            flows.append(_finance_excel_flow())

    if current_user.get("role") == "admin":
        flows.extend(_admin_platform_flows())

    return flows


def get_flow_config(flow_id: str, current_user: dict) -> dict[str, Any]:
    for flow in list_flow_configs(current_user):
        if flow["id"] == flow_id or flow["app_id"] == flow_id:
            return flow

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="自动化流程配置不存在或无权查看",
    )


def _visible_positions(current_user: dict) -> list[str]:
    if current_user.get("role") == "admin":
        return list(POSITION_LABELS.keys())

    position = current_user.get("position")
    return [position] if is_valid_position(position) else []


def _automation_task_flows(position: str) -> list[dict[str, Any]]:
    flows = []
    for task_id, spec in AUTOMATION_TASKS.get(position, {}).items():
        flows.append(
            _base_flow(
                flow_id=f"automation:{position}:{task_id}",
                app_id=f"automation-{task_id}",
                name=str(spec["label"]),
                description=str(spec["instruction"]),
                category="岗位文本自动化",
                position=position,
                trigger_type="manual_form",
                entrypoint="/automation/generate",
                input_schema=[
                    {
                        "name": "input_text",
                        "label": "任务内容",
                        "type": "textarea",
                        "required": True,
                        "max_length": 10000,
                        "placeholder": spec["placeholder"],
                    }
                ],
                output_schema=[
                    {
                        "name": "answer",
                        "label": "生成结果",
                        "type": "markdown_text",
                        "description": spec["output_format"],
                    }
                ],
                prompt_summary="后端按岗位、任务说明、用户输入和输出格式拼装 Prompt，并在执行前做岗位任务权限校验。",
                prompt_template_preview=(
                    "你是企业内部的 {position_label} 岗位 AI 自动化助手。\n"
                    f"任务说明：{spec['instruction']}\n"
                    "用户输入：{input_text}\n"
                    f"输出格式：{spec['output_format']}"
                ),
                allowed_tools=["llm.chat"],
                allowed_erp_resources=[],
                permission_rules=[
                    "管理员可查看和执行全部岗位任务",
                    "员工只能查看和执行自己岗位的任务",
                    "任务执行前校验 task_id 是否属于当前岗位",
                ],
                approval_policy="当前流程不需要审批；高风险退款类操作由聊天审批流程处理。",
                failure_strategy="LLM 调用失败时写入失败运行记录并把真实错误返回给前端。",
                steps=[
                    _step("validate_position_task", "校验岗位和 task_id 权限", ["current_user.position", "task_id"]),
                    _step("build_prompt", "按岗位任务模板构建 Prompt", ["input_text"]),
                    _step("llm_chat", "调用真实大模型生成结果", ["prompt"]),
                    _step("record_run", "写入运行记录和审计日志", ["run_id"]),
                ],
            )
        )

    return flows


def _finance_excel_flow() -> dict[str, Any]:
    return _base_flow(
        flow_id="automation:finance:excel-file-transform",
        app_id="finance-excel-transform",
        name="财务 Excel 生成",
        description="上传真实 Excel 文件，生成处理摘要、数值汇总、AI 建议和整理后的新工作簿。",
        category="文件自动化",
        position="finance",
        trigger_type="manual_file_upload",
        entrypoint="/automation/finance/excel-transform",
        input_schema=[
            {
                "name": "file",
                "label": "Excel 文件",
                "type": "file",
                "required": True,
                "accept": [".xlsx", ".xls"],
                "max_bytes": 8 * 1024 * 1024,
            },
            {
                "name": "instruction",
                "label": "财务处理要求",
                "type": "textarea",
                "required": False,
                "max_length": 2000,
            },
        ],
        output_schema=[
            {"name": "workbook", "label": "新 Excel 文件", "type": "xlsx"},
            {"name": "metadata", "label": "文件摘要", "type": "json"},
        ],
        prompt_summary="仅读取 Excel 摘要、sheet 概览和少量样例行给大模型生成财务复核建议，不保存完整 Excel 内容到运行记录。",
        prompt_template_preview="财务 AI 助手根据源文件名、处理要求、sheet 概览和样例数据输出复核建议。",
        allowed_tools=["pandas.read_excel", "openpyxl.write_workbook", "llm.chat"],
        allowed_erp_resources=[],
        permission_rules=[
            "仅财务岗位或管理员可以上传财务 Excel",
            "文件大小限制 8MB",
            "运行记录只保存文件名、sheet 数、行列数和输出字节数",
        ],
        approval_policy="当前流程不需要审批；生成结果需由财务人员人工复核后使用。",
        failure_strategy="读取失败、格式不支持或生成失败时返回真实错误，并写入失败运行记录。",
        steps=[
            _step("validate_file", "校验文件类型、大小和岗位权限", ["file"]),
            _step("read_excel", "读取真实 Excel workbook", ["file"]),
            _step("build_finance_summary", "生成 sheet 和数值摘要", ["sheets"]),
            _step("llm_finance_suggestion", "调用大模型生成财务建议", ["summary"]),
            _step("write_workbook", "生成新的 Excel 文件", ["workbook"]),
            _step("record_artifact", "写入文件产物摘要", ["filename", "metadata"]),
        ],
    )


def _customer_service_message_loop_flow() -> dict[str, Any]:
    resources = list_resource_definitions(erp_scopes_for_position("customer_service"))
    return _base_flow(
        flow_id="automation:customer_service:message-loop",
        app_id="customer-service-message-loop",
        name="客服消息自动化闭环",
        description="把客户消息变成可追踪工单：AI 识别意图、查订单/物流/知识库、生成回复草稿，并按风险转自动回复待发送或人工介入。",
        category="客服售后",
        position="customer_service",
        trigger_type="manual_case_or_webhook",
        entrypoint="/customer-service/messages",
        input_schema=[
            {"name": "channel", "label": "消息渠道", "type": "select", "required": True},
            {"name": "message", "label": "客户原话", "type": "textarea", "required": True, "max_length": 10000},
            {"name": "order_no", "label": "订单号", "type": "text", "required": False},
            {"name": "tracking_no", "label": "物流单号", "type": "text", "required": False},
            {"name": "buyer_language", "label": "客户语言", "type": "select", "required": False},
        ],
        output_schema=[
            {"name": "intent", "label": "意图", "type": "text"},
            {"name": "risk_level", "label": "风险等级", "type": "text"},
            {"name": "reply_draft", "label": "回复草稿", "type": "markdown_text"},
            {"name": "automation_decision", "label": "自动化决策", "type": "text"},
            {"name": "erp_references", "label": "ERP 引用", "type": "json_array"},
        ],
        prompt_summary="收件箱消息处理时先按客服岗位权限查 ERP/RAG，再调用 LLM 生成回复，并用规则控制低风险/高风险流转。",
        prompt_template_preview=(
            "你是跨境电商企业内部的客服自动化助手。\n"
            "基于客户原话、ERP 查询摘要和知识库摘要，生成回复草稿和人工处理建议。"
        ),
        allowed_tools=["customer_service.messages", "erp.provider.query", "rag.retrieve", "llm.chat", "approval.request"],
        allowed_erp_resources=resources,
        permission_rules=[
            "只有客服岗位和管理员可使用客服消息闭环",
            "ERP 查询只能访问客服岗位资源",
            "低风险问题只进入待发送状态，不伪装已经外部发送",
            "退款、投诉、差评、拒付等高风险必须转人工/审批",
        ],
        approval_policy="高风险售后消息创建审批/人工介入记录，外部退款、赔付、删除评价等动作禁止自动执行。",
        failure_strategy="任一步失败会保留客户消息并标记 failed，同时写入运行记录和事件时间线。",
        steps=[
            _step("create_message", "客户消息进入客服自动化收件箱", ["message", "channel"]),
            _step("classify_intent_and_risk", "识别物流、退货、尺码、换货、优惠码、退款、投诉等意图和风险", ["message"]),
            _step("erp_permission_query", "按客服岗位权限查询订单、物流、工单或退货请求", ["order_no", "tracking_no"]),
            _step("rag_policy_lookup", "检索客服知识库和公司政策", ["message"]),
            _step("generate_reply_draft", "生成对应语种回复草稿和内部建议", ["erp_summary", "rag_summary"]),
            _step("route_decision", "低风险进入待发送，高风险转人工/审批", ["risk_level"]),
            _step("record_timeline", "写入事件、运行记录和审计日志", ["message_id", "run_id"]),
        ],
    )


def _erp_query_flow(position: str) -> dict[str, Any]:
    resources = list_resource_definitions(erp_scopes_for_position(position))
    return _base_flow(
        flow_id=f"automation:{position}:erp-query",
        app_id=f"{position}-erp-query",
        name=f"{POSITION_LABELS[position]} ERP 查询",
        description=f"按{POSITION_LABELS[position]}岗位权限查询 ERP 资源，结果可用于工作台和 AI 对话。",
        category="数据查询",
        position=position,
        trigger_type="manual_query",
        entrypoint="/erp/query",
        input_schema=[
            {"name": "resource", "label": "ERP 资源", "type": "select", "required": True},
            {"name": "query", "label": "查询关键词", "type": "text", "required": False, "max_length": 200},
            {"name": "filters", "label": "过滤条件", "type": "json", "required": False},
            {"name": "limit", "label": "返回数量", "type": "number", "required": False, "min": 1, "max": 100},
        ],
        output_schema=[
            {"name": "items", "label": "ERP 记录列表", "type": "json_array"},
            {"name": "message", "label": "查询状态", "type": "text"},
        ],
        prompt_summary="该流程不直接构建 Prompt；AI 对话需要 ERP 时会先做岗位资源校验，再调用 ERP provider。",
        prompt_template_preview="无独立 Prompt。自然语言对话由 LangGraph 识别资源后复用本查询能力。",
        allowed_tools=["erp.provider.query"],
        allowed_erp_resources=resources,
        permission_rules=[
            "员工只能选择当前岗位 ERP scope 内的资源",
            "管理员可查看全部岗位资源映射",
            "越权资源会返回 403 并写入 blocked 运行记录",
        ],
        approval_policy="只读查询不需要审批；写入、退款、付款等动作必须另走审批流程。",
        failure_strategy="ERP provider 未配置、DocType 不存在或 HTTP 错误会写入失败运行记录。",
        steps=[
            _step("resolve_resource", "解析 ERP 资源名称", ["resource"]),
            _step("permission_check", "按岗位校验 ERP scope", ["current_user.position", "resource"]),
            _step("provider_query", "调用真实 ERP provider", ["query", "filters", "limit"]),
            _step("record_run", "写入运行记录和审计日志", ["run_id"]),
        ],
    )


def _chat_flow(position: str) -> dict[str, Any]:
    resources = list_resource_definitions(erp_scopes_for_position(position))
    return _base_flow(
        flow_id=f"automation:{position}:chat-agent",
        app_id=f"{position}-chat-agent",
        name=f"{POSITION_LABELS[position]} AI 对话",
        description=f"在{POSITION_LABELS[position]}岗位权限内进行 RAG、ERP 和业务流程问答，越权问题会被拦截。",
        category="AI Agent",
        position=position,
        trigger_type="manual_chat",
        entrypoint="/chat 或 /chat/stream",
        input_schema=[
            {"name": "message", "label": "用户消息", "type": "textarea", "required": True},
            {"name": "thread_id", "label": "会话 ID", "type": "text", "required": False},
        ],
        output_schema=[
            {"name": "answer", "label": "AI 回复", "type": "markdown_text"},
            {"name": "erp_references", "label": "ERP 引用", "type": "json_array"},
            {"name": "approval_result", "label": "审批结果", "type": "json"},
        ],
        prompt_summary="LangGraph 先做岗位越权关键词检查和意图识别，再按意图调用 RAG、订单、ERP 或审批节点。",
        prompt_template_preview="聊天 Prompt 分布在 LangGraph 节点内，运行时只传入当前用户岗位、上下文摘要和允许工具结果。",
        allowed_tools=["langgraph.workflow", "rag.retrieve", "erp.provider.query", "approval.request"],
        allowed_erp_resources=resources,
        permission_rules=[
            "对话入口先执行岗位越权关键词拦截",
            "ERP 查询节点只能访问岗位允许资源",
            "运行记录只保存输入/输出预览和引用数量，不复制完整上下文",
        ],
        approval_policy="高风险退款等动作会创建审批请求，管理员审核后才执行。",
        failure_strategy="图节点异常会返回真实错误事件，并将 run 标记为 failed。",
        steps=[
            _step("position_guard", "岗位越权关键词拦截", ["message"]),
            _step("load_context", "加载会话摘要和最近消息", ["thread_id"]),
            _step("intent_detection", "识别业务意图", ["message"]),
            _step("tool_or_rag", "调用 RAG、ERP、订单或审批工具", ["intent"]),
            _step("answer_generation", "生成最终回复和引用", ["tool_results"]),
            _step("record_run", "写入运行记录、引用和会话消息", ["run_id"]),
        ],
    )


def _admin_platform_flows() -> list[dict[str, Any]]:
    return [
        {
            **_base_flow(
                flow_id="automation:platform:knowledge-upload",
                app_id="admin-knowledge",
                name="知识库维护",
                description="上传企业规则、客服话术、财务制度和运营资料，进入真实 RAG 入库流程。",
                category="知识治理",
                position=None,
                trigger_type="manual_file_upload",
                entrypoint="/admin/documents/upload",
                input_schema=[
                    {"name": "file", "label": "文档文件", "type": "file", "required": True},
                    {"name": "visibility", "label": "可见范围", "type": "select", "required": True},
                    {"name": "department", "label": "部门", "type": "text", "required": False},
                ],
                output_schema=[
                    {"name": "document_id", "label": "文档 ID", "type": "uuid"},
                    {"name": "chunk_count", "label": "切片数量", "type": "number"},
                ],
                prompt_summary="该流程不直接调用聊天 Prompt；上传后进入真实文档解析、切片和向量入库。",
                prompt_template_preview="无独立 Prompt。",
                allowed_tools=["document.loader", "rag.ingest", "pgvector.upsert"],
                allowed_erp_resources=[],
                permission_rules=["仅管理员可上传和维护知识库"],
                approval_policy="当前流程不需要审批；生产环境可增加发布审核。",
                failure_strategy="解析或入库失败时返回真实错误，不写入模拟文档。",
                steps=[
                    _step("validate_upload", "校验文件和可见范围", ["file", "visibility"]),
                    _step("load_document", "解析真实文档内容", ["file"]),
                    _step("ingest_chunks", "切片并写入向量库", ["documents"]),
                ],
            ),
            "position_label": "平台",
        }
    ]


def _base_flow(
    *,
    flow_id: str,
    app_id: str,
    name: str,
    description: str,
    category: str,
    position: str | None,
    trigger_type: str,
    entrypoint: str,
    input_schema: list[dict[str, Any]],
    output_schema: list[dict[str, Any]],
    prompt_summary: str,
    prompt_template_preview: str,
    allowed_tools: list[str],
    allowed_erp_resources: list[dict[str, Any]],
    permission_rules: list[str],
    approval_policy: str,
    failure_strategy: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": flow_id,
        "app_id": app_id,
        "name": name,
        "description": description,
        "category": category,
        "position": position,
        "position_label": POSITION_LABELS.get(position, "平台"),
        "status": "enabled",
        "version": FLOW_VERSION,
        "publish_status": "published",
        "owner": f"{POSITION_LABELS.get(position, '平台')}负责人" if position else "管理员",
        "trigger_type": trigger_type,
        "entrypoint": entrypoint,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "prompt_summary": prompt_summary,
        "prompt_template_preview": prompt_template_preview,
        "model_config": {
            "provider": "DashScope Bailian",
            "chat_model": "qwen-plus",
            "streaming": entrypoint.endswith("/stream") or "stream" in entrypoint,
            "secrets_visible": False,
        },
        "allowed_tools": allowed_tools,
        "allowed_erp_resources": allowed_erp_resources,
        "permission_rules": permission_rules,
        "approval_policy": approval_policy,
        "failure_strategy": failure_strategy,
        "steps": steps,
        "source": "code_defined",
    }


def _step(step_id: str, name: str, inputs: list[str]) -> dict[str, Any]:
    return {
        "id": step_id,
        "name": name,
        "inputs": inputs,
        "retryable": step_id not in {"permission_check", "position_guard"},
    }
