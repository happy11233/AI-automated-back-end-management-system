from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.llm import chat
from app.permissions import POSITION_LABELS, is_valid_position
from app.services.automation_service import build_automation_prompt
from app.services.erp_service import query_erp_for_current_user, summarize_erp_items
from app.services.logging_service import write_audit_log
from app.services.platform_draft_service import (
    create_platform_draft,
    listing_content_from_answer,
)
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    now_ms,
    record_step,
    sanitize_text,
    start_run,
)
from app.services.user_ai_app_permission_service import is_ai_app_allowed


WORKFLOW_VERSION = "2026.07.17"
SUPPORTED_EXECUTION_MODES = {"llm_generate", "erp_then_llm", "listing_draft_writeback"}


WORKFLOW_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "operations_listing_launch",
        "name": "运营 Listing 上架准备",
        "position": "operations",
        "category": "运营增长",
        "scenario": "新品 SKU 上架前，自动生成 Listing、标题、五点描述、关键词和促销文案草稿。",
        "business_value": "减少运营反复整理卖点、关键词和促销文案的时间，并自动写入跨境平台草稿等待审核。",
        "trigger_type": "manual_form",
        "automation_level": "tool_auto",
        "execution_mode": "listing_draft_writeback",
        "entry_view": "automation_operations",
        "entry_label": "打开运营 AI 自动化",
        "source_task_id": "listing",
        "input_placeholder": "输入 SKU、品名、材质、尺寸、站点、目标人群、竞品差异和合规限制。",
        "output_contract": "Listing 草稿、标题、五点描述、后台搜索词、促销文案、中文优化备注，以及已保存的跨境平台草稿 ID。",
        "requires_approval": False,
        "approval_policy": "AI 只保存平台草稿，不直接发布到 Amazon；运营审核通过后发布。",
        "tools": ["erp.provider.query", "llm.chat", "platform_drafts.write", "openpyxl.write_workbook", "mcp.playwright_amazon.prepare_seller_central_listing", "rpa.queue_ready", "run_records"],
        "erp_resources": ["Item", "Item Price", "Bin", "Sales Order"],
        "writeback_target": "写入 platform_drafts，状态 pending_review；可由 Playwright MCP、Amazon SP-API、ERP、影刀 RPA 或 n8n 读取后写入外部平台草稿。",
        "notification_target": "运营负责人在草稿区查看并审核发布。",
        "saved_minutes": 45,
    },
    {
        "id": "operations_competitor_analysis",
        "name": "运营竞品分析",
        "position": "operations",
        "category": "运营增长",
        "scenario": "把竞品卖点、价格、差评点和链接摘录转成差异化分析。",
        "business_value": "减少运营复制竞品信息、整理痛点和写分析报告的时间。",
        "trigger_type": "manual_form",
        "automation_level": "draft_auto",
        "execution_mode": "llm_generate",
        "entry_view": "automation_operations",
        "entry_label": "打开运营 AI 自动化",
        "source_task_id": "competitor_analysis",
        "input_placeholder": "输入竞品标题、价格、卖点、差评摘要、链接摘录和目标站点。",
        "output_contract": "竞品定位、价格区间、核心卖点、差评痛点、可复制点、差异化建议。",
        "requires_approval": False,
        "approval_policy": "分析结论仅作为运营决策参考，不自动改价或发布。",
        "tools": ["llm.chat", "run_records"],
        "erp_resources": ["Item", "Item Price", "Sales Order"],
        "writeback_target": "运行记录；后续可接运营看板。",
        "notification_target": "运营负责人在工作台查看结果。",
        "saved_minutes": 30,
    },
    {
        "id": "customer_service_refund_reply",
        "name": "客服退款售后处理",
        "position": "customer_service",
        "category": "客服售后",
        "scenario": "买家提出退款、退货、换货或投诉时，自动查权限内 ERP 信息并生成回复话术。",
        "business_value": "减少客服查订单、查物流、翻规则、写话术和升级判断的重复操作。",
        "trigger_type": "manual_form",
        "automation_level": "assist_auto",
        "execution_mode": "erp_then_llm",
        "entry_view": "automation_customer_service",
        "entry_label": "打开客服 AI 自动化",
        "source_task_id": "refund_script",
        "input_placeholder": "输入买家原话、订单号、物流单号、退款原因、站点和希望处理方式。",
        "output_contract": "首轮回复、二次跟进、升级人工话术、审批/升级建议和 ERP 引用摘要。",
        "requires_approval": True,
        "approval_policy": "大额退款、补偿或写入动作必须走审批；当前工作流只生成话术和建议。",
        "tools": ["erp.provider.query", "llm.chat", "approval.request", "run_records"],
        "erp_resources": ["Customer", "Sales Order", "Delivery Note", "Issue", "Return request"],
        "writeback_target": "运行记录；后续可接客服工单系统。",
        "notification_target": "客服主管或当前客服在工作台查看。",
        "saved_minutes": 12,
    },
    {
        "id": "customer_service_logistics_reply",
        "name": "客服物流查询回复",
        "position": "customer_service",
        "category": "客服售后",
        "scenario": "买家询问物流、签收、丢件或延迟时，自动查询物流/订单并生成多语言回复。",
        "business_value": "减少客服重复查物流和写英文回复的时间。",
        "trigger_type": "manual_form",
        "automation_level": "assist_auto",
        "execution_mode": "erp_then_llm",
        "entry_view": "automation_customer_service",
        "entry_label": "打开客服 AI 自动化",
        "source_task_id": "smart_reply",
        "input_placeholder": "输入买家物流问题、订单号、物流单号、目标语言和站点。",
        "output_contract": "推荐回复、物流摘要、下一步处理建议、升级条件。",
        "requires_approval": False,
        "approval_policy": "只读查询和话术生成不需要审批；赔付/退款仍需审批。",
        "tools": ["erp.provider.query", "llm.chat", "run_records"],
        "erp_resources": ["Sales Order", "Delivery Note", "Issue"],
        "writeback_target": "运行记录；后续可接客服工单回复草稿。",
        "notification_target": "当前客服在工作台查看。",
        "saved_minutes": 8,
    },
    {
        "id": "customer_service_message_loop",
        "name": "客服消息自动化闭环",
        "position": "customer_service",
        "category": "客服售后",
        "scenario": "客户消息进入收件箱后，自动识别意图、查 ERP/RAG、生成回复草稿，并按风险决定低风险待发送或高风险转人工。",
        "business_value": "减少客服复制订单号、查物流、翻规则、写英文回复和判断升级的重复操作。",
        "trigger_type": "manual_form",
        "automation_level": "case_loop_auto",
        "execution_mode": "external_existing_endpoint",
        "entry_view": "customer_service_inbox",
        "entry_label": "打开客服自动化收件箱",
        "source_task_id": "customer_service_message_loop",
        "input_placeholder": "请到客服自动化收件箱录入真实客户消息，或后续由 Amazon/邮箱/n8n webhook 写入。",
        "output_contract": "意图、风险等级、ERP/RAG 摘要、回复草稿、自动回复/转人工决策、审批记录和运行记录。",
        "requires_approval": True,
        "approval_policy": "低风险只生成待发送回复；退款、投诉、差评、拒付等高风险必须转人工或审批，不自动执行赔付/退款。",
        "tools": ["customer_service.messages", "erp.provider.query", "rag.retrieve", "llm.chat", "approval.request", "run_records"],
        "erp_resources": ["Customer", "Sales Order", "Delivery Note", "Issue", "Return request"],
        "writeback_target": "写入 customer_service_messages、message_events、automation_runs；外部发送由正式渠道连接器执行。",
        "notification_target": "客服在收件箱查看待发送、草稿和转人工消息。",
        "saved_minutes": 15,
    },
    {
        "id": "finance_report_analysis",
        "name": "财务报表分析",
        "position": "finance",
        "category": "财务分析",
        "scenario": "财务粘贴报表摘要、费用、利润、现金流或异常项，AI 自动生成分析和复核建议。",
        "business_value": "减少财务反复整理报表说明、异常描述和复核结论的时间。",
        "trigger_type": "manual_form",
        "automation_level": "draft_auto",
        "execution_mode": "llm_generate",
        "entry_view": "automation_finance",
        "entry_label": "打开财务 AI 自动化",
        "source_task_id": "report_analysis",
        "input_placeholder": "输入报表期间、销售额、费用、利润、现金流、异常项目和复核要求。",
        "output_contract": "摘要、关键指标、异常项、风险提示、下一步建议。",
        "requires_approval": False,
        "approval_policy": "分析结果需财务复核，不自动入账。",
        "tools": ["llm.chat", "run_records"],
        "erp_resources": ["GL Entry", "Payment Entry", "Sales Invoice", "Purchase Invoice"],
        "writeback_target": "运行记录；后续可接财务报表附件或 BI 看板。",
        "notification_target": "财务负责人在工作台查看。",
        "saved_minutes": 20,
    },
    {
        "id": "finance_salary_summary",
        "name": "财务工资统计",
        "position": "finance",
        "category": "财务分析",
        "scenario": "财务用模糊问题要求工资表时，AI 自动识别期间，查询 ERP 工资单并生成 Excel。",
        "business_value": "减少财务登录 ERP、筛选工资期间、复制员工工资明细和整理 Excel 的重复操作。",
        "trigger_type": "manual_form",
        "automation_level": "tool_auto",
        "execution_mode": "external_existing_endpoint",
        "entry_view": "automation_finance",
        "entry_label": "打开统计工资",
        "source_task_id": "salary_summary",
        "input_placeholder": "例如：把这个月所有员工的工资表发我。",
        "output_contract": "工资明细 Excel、自动化摘要、意图识别结果、总额、人数和复核建议。",
        "requires_approval": True,
        "approval_policy": "工资数据只能由财务岗位处理，发放或调整需人工审批。",
        "tools": ["intent.recognizer", "erp.provider.query", "openpyxl.write_workbook", "run_records"],
        "erp_resources": ["Salary Slip"],
        "writeback_target": "下载工资 Excel；运行记录保存意图、期间、员工数、金额合计和文件产物。",
        "notification_target": "财务负责人在工作台查看。",
        "saved_minutes": 25,
    },
    {
        "id": "finance_salary_wechat_send",
        "name": "财务工资表微信发送准备",
        "position": "finance",
        "category": "财务自动化",
        "scenario": "生成指定期间员工工资表，并准备通过个人微信发送给已确认联系人。",
        "business_value": "减少财务查询工资单、整理 Excel 和重复准备微信附件的操作，同时保留人工最终发送确认。",
        "trigger_type": "manual_form",
        "automation_level": "assist_auto",
        "execution_mode": "external_existing_endpoint",
        "entry_view": "automation_finance",
        "entry_label": "打开财务微信发送准备",
        "source_task_id": "salary_wechat_send",
        "input_placeholder": "例如：生成这个月员工工资表，准备通过个人微信发给张三。",
        "output_contract": "执行计划、工资 Excel、微信联系人、待人工发送状态、执行器日志和审计记录。",
        "requires_approval": True,
        "approval_policy": "工资属于敏感数据，联系人和最终发送必须人工确认；第一版不自动点击微信发送。",
        "tools": [
            "intent.recognizer",
            "erp.provider.query",
            "openpyxl.write_workbook",
            "mcp.n8n.dispatch_workflow",
            "mcp.desktop_rpa.prepare_wechat_attachment",
            "mcp.file_center.get_generated_file_download_path",
            "run_records",
        ],
        "erp_resources": ["Salary Slip"],
        "writeback_target": "保存工资 Excel 到文档下载，并创建 waiting_manual_send 外部发送准备记录。",
        "notification_target": "财务在聊天结果和文档下载中查看，并人工完成微信最终发送。",
        "saved_minutes": 18,
    },
    {
        "id": "finance_monthly_package_wechat_send",
        "name": "财务月度资料微信发送",
        "position": "finance",
        "category": "Agent 复杂任务",
        "scenario": "财务用一句话要求整理本月财务报表和工资表，合并成汇总 Excel，并准备通过个人微信发送给指定联系人。",
        "business_value": "把跨 ERP 查询、工资表生成、财务报表整理、文件合并和外部发送准备整合为一个可审计的 Plan-and-Execute 自动化任务。",
        "trigger_type": "chat_plan_execute",
        "automation_level": "plan_execute_auto",
        "execution_mode": "agent_execution_hub",
        "entry_view": "chat",
        "entry_label": "在 AI 对话中发起复杂财务任务",
        "source_task_id": "finance_monthly_package_wechat_send",
        "input_placeholder": "例如：整理这个月财务报表和工资表，合并后通过微信发给张三。",
        "output_contract": "工资表 Excel、财务报表 Excel、合并汇总 Excel、微信待人工发送状态、MCP 调用记录和审计记录。",
        "requires_approval": True,
        "approval_policy": "工资和财务数据属于敏感内容；复杂任务不需要确认计划，但微信最终发送必须人工确认。",
        "tools": [
            "react.intent_classifier",
            "plan_execute.planner",
            "skill.finance_salary_export",
            "python.erp_report",
            "python.openpyxl",
            "mcp.file_center.get_generated_file_download_path",
            "mcp.n8n.dispatch_workflow",
            "mcp.desktop_rpa.prepare_wechat_attachment",
            "run_records",
        ],
        "erp_resources": ["Salary Slip", "GL Entry", "Payment Entry", "Sales Invoice", "Purchase Invoice"],
        "writeback_target": "保存多个 Excel 到文档下载，创建个人微信待人工发送任务，管理员可在运行记录查看完整步骤。",
        "notification_target": "财务在聊天最终结果和文档下载中查看，管理员在运行记录中审计。",
        "saved_minutes": 35,
    },
    {
        "id": "finance_excel_settlement",
        "name": "财务 Excel 生成",
        "position": "finance",
        "category": "文件自动化",
        "scenario": "上传 Amazon 结算表、工资表或费用表，并选择财务权限内 ERP 表，系统生成新 Excel、摘要和异常提示。",
        "business_value": "减少财务复制粘贴、跨表查 ERP、分类、对账和做汇总表的重复操作。",
        "trigger_type": "manual_file_upload",
        "automation_level": "tool_auto",
        "execution_mode": "external_existing_endpoint",
        "entry_view": "automation_finance_excel_transform",
        "entry_label": "打开财务 Excel 生成",
        "source_task_id": "finance_excel_transform",
        "input_placeholder": "请到财务 Excel 生成页面选择或上传真实 Excel 文件，并按需选择销售发票、收付款单、总账分录等 ERP 表。",
        "output_contract": "新 Excel 文件、处理摘要、ERP 数据摘要、数值汇总、异常提示。",
        "requires_approval": False,
        "approval_policy": "生成结果需财务复核后使用，不自动入账。",
        "tools": ["erp.provider.query", "pandas.read_excel", "openpyxl.write_workbook", "llm.chat", "run_records"],
        "erp_resources": ["Sales Invoice", "Payment Entry", "GL Entry", "Salary Slip", "Purchase Invoice"],
        "writeback_target": "下载新 Excel；运行记录保存文件摘要和产物信息。",
        "notification_target": "财务在页面下载结果。",
        "saved_minutes": 35,
    },
    {
        "id": "finance_reconciliation",
        "name": "财务对账自动化",
        "position": "finance",
        "category": "财务对账",
        "scenario": "上传 Amazon 结算表、物流账单、采购成本表、广告费表和汇率表，系统自动按订单号/SKU 匹配，生成订单利润表和异常账单。",
        "business_value": "减少财务跨表复制粘贴、手动 VLOOKUP、费用归集、利润核算和异常账单排查的重复操作。",
        "trigger_type": "manual_file_upload",
        "automation_level": "tool_auto",
        "execution_mode": "external_existing_endpoint",
        "entry_view": "automation_finance",
        "entry_label": "打开财务对账中心",
        "source_task_id": "finance_reconciliation",
        "input_placeholder": "请到财务 AI 自动化页面上传 Amazon 结算表、物流账单、采购成本表、广告费表和汇率表。",
        "output_contract": "对账摘要、订单利润表、异常账单、字段识别和源文件概览。",
        "requires_approval": False,
        "approval_policy": "生成结果需财务复核后使用，不自动入账、不自动付款。",
        "tools": ["pandas.read_excel", "field_mapping", "order_sku_matching", "profit_calculation", "openpyxl.write_workbook", "run_records"],
        "erp_resources": ["Sales Invoice", "Payment Entry", "GL Entry", "Purchase Invoice"],
        "writeback_target": "下载财务对账 Excel；运行记录保存文件摘要、利润合计和异常数量。",
        "notification_target": "财务在页面下载结果；后续可接飞书、钉钉或邮箱。",
        "saved_minutes": 60,
    },
]


def list_ai_workflows(current_user: dict) -> list[dict[str, Any]]:
    return [_workflow_item(item) for item in WORKFLOW_DEFINITIONS if _can_view_workflow(current_user, item)]


def get_ai_workflow(workflow_id: str, current_user: dict) -> dict[str, Any]:
    workflow = _find_workflow(workflow_id)
    if not _can_view_workflow(current_user, workflow):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 工作流不存在或无权查看")

    return _workflow_item(workflow)


def run_ai_workflow(
    *,
    workflow_id: str,
    input_text: str,
    current_user: dict,
) -> dict[str, Any]:
    workflow = _find_workflow(workflow_id)
    if not _can_view_workflow(current_user, workflow):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权执行该 AI 工作流")

    if workflow["execution_mode"] not in SUPPORTED_EXECUTION_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该工作流需要在专用页面执行，请使用返回的入口进入现有真实功能。",
        )

    normalized_input = input_text.strip()
    if not normalized_input:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入工作流任务内容")

    safe_input = sanitize_text(normalized_input)
    started_ms = now_ms()
    execution_user = _execution_user_for_workflow(current_user, workflow)
    run_id = start_run(
        run_type="ai_workflow",
        app_id=str(workflow["id"]),
        app_name=str(workflow["name"]),
        entrypoint=f"/ai-workflows/{workflow['id']}/run",
        current_user=execution_user,
        resource_type="ai_workflow",
        resource_id=str(workflow["id"]),
        input_text=normalized_input,
        metadata=_run_metadata(workflow),
    )
    steps: list[dict[str, Any]] = []
    erp_references: list[dict[str, Any]] = []
    platform_draft: dict[str, Any] | None = None
    erp_summary = ""

    try:
        steps.append(_record_workflow_step(
            run_id=run_id,
            order=1,
            name="trigger_validate",
            status_value="succeeded",
            workflow=workflow,
            input_text=normalized_input,
            output_text="人工触发参数校验通过",
            duration_ms=0,
        ))

        if workflow["execution_mode"] == "erp_then_llm":
            erp_started_ms = now_ms()
            erp_result = query_erp_for_current_user(
                user_input=safe_input,
                current_user=execution_user,
                query=safe_input,
                limit=5,
                source="ai_workflow",
                allowed_resources=list(workflow["erp_resources"]),
            )
            erp_items = erp_result.get("items") if isinstance(erp_result.get("items"), list) else []
            erp_resource = erp_result.get("resource")
            erp_summary = summarize_erp_items(str(erp_resource), erp_items) if erp_resource else str(erp_result.get("message") or "")
            erp_references = erp_result.get("references") if isinstance(erp_result.get("references"), list) else []
            steps.append(_record_workflow_step(
                run_id=run_id,
                order=2,
                name="erp_permission_query",
                status_value="succeeded" if erp_result.get("ok") else "blocked" if erp_result.get("status") == "no_scope" else "failed",
                workflow=workflow,
                input_text=normalized_input,
                output_text={
                    "status": erp_result.get("status"),
                    "resource": erp_resource,
                    "reference_count": len(erp_references),
                    "message": erp_result.get("message"),
                },
                duration_ms=elapsed_ms(erp_started_ms),
            ))

        prompt_started_ms = now_ms()
        prompt = _build_workflow_prompt(
            workflow=workflow,
            input_text=safe_input,
            erp_summary=erp_summary,
        )
        answer = chat(prompt)
        steps.append(_record_workflow_step(
            run_id=run_id,
            order=len(steps) + 1,
            name="ai_generate_decision",
            status_value="succeeded",
            workflow=workflow,
            input_text=normalized_input,
            output_text=answer,
            duration_ms=elapsed_ms(prompt_started_ms),
        ))

        if workflow["execution_mode"] == "listing_draft_writeback":
            writeback_started_ms = now_ms()
            draft_content = listing_content_from_answer(answer=answer, input_text=normalized_input)
            platform_draft = create_platform_draft(
                draft_type="listing",
                platform="amazon",
                external_target="amazon_seller_central",
                title=str(draft_content.get("listing_title") or workflow["name"]),
                position="operations",
                owner_user_id=execution_user.get("id"),
                source_run_id=run_id,
                source_resource_type="ai_workflow",
                source_resource_id=str(workflow["id"]),
                content=draft_content,
                writeback_status="draft_saved",
                writeback_message=(
                    "已保存到跨境平台草稿区，等待运营确认后再打开 Amazon Seller Central 填表。"
                ),
                metadata={
                    "automation": "operations_listing_launch",
                    "source": "ai_workflow",
                    "saved_by_ai": True,
                    "amazon_upload_status": "waiting_confirmation",
                },
            )
            steps.append(_record_workflow_step(
                run_id=run_id,
                order=len(steps) + 1,
                name="save_platform_draft",
                status_value="succeeded",
                workflow=workflow,
                input_text=str(workflow["id"]),
                output_text={
                    "draft_id": platform_draft["id"],
                    "status": platform_draft["status"],
                    "writeback_status": platform_draft["writeback_status"],
                    "external_target": platform_draft["external_target"],
                },
                duration_ms=elapsed_ms(writeback_started_ms),
            ))
            answer = (
                "AI 已完成 Listing 草稿生成，并等待运营确认上传 Amazon。\n"
                f"草稿 ID：{platform_draft['id']}\n"
                f"写回目标：{platform_draft['external_target']}\n"
                f"写回状态：{platform_draft['writeback_status']}\n\n"
                "下一步：运营确认后调用 Amazon Playwright 上传准备，系统会停在最终发布前。\n\n"
                f"{answer}"
            )

        steps.append(_record_workflow_step(
            run_id=run_id,
            order=len(steps) + 1,
            name="write_run_record",
            status_value="succeeded",
            workflow=workflow,
            input_text=str(workflow["id"]),
            output_text="已写入运行记录和审计事件",
            duration_ms=0,
        ))
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=answer,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                **_run_metadata(workflow),
                "erp_reference_count": len(erp_references),
                "step_count": len(steps),
                "platform_draft_id": platform_draft.get("id") if platform_draft else None,
            },
        )
    except Exception as error:
        record_step(
            run_id=run_id,
            step_name="ai_workflow_error",
            step_order=len(steps) + 1,
            status_value="failed",
            provider="ai_workflow",
            resource_type="ai_workflow",
            resource_id=str(workflow["id"]),
            input_text=normalized_input,
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata=_run_metadata(workflow),
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
            metadata=_run_metadata(workflow),
        )
        raise

    write_audit_log(
        user_id=current_user.get("id"),
        action="ai_workflow.run",
        resource_type="ai_workflow",
        resource_id=str(workflow["id"]),
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": workflow["position"],
            "workflow_name": workflow["name"],
            "execution_mode": workflow["execution_mode"],
            "requires_approval": workflow["requires_approval"],
            "run_id": run_id,
            "platform_draft_id": platform_draft.get("id") if platform_draft else None,
        },
    )

    return {
        "run_id": run_id,
        "workflow": _workflow_item(workflow),
        "status": "succeeded",
        "answer": answer,
        "erp_references": erp_references,
        "platform_draft": platform_draft,
        "steps": steps,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _workflow_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        **item,
        "version": WORKFLOW_VERSION,
        "position_label": POSITION_LABELS.get(item["position"], item["position"]),
        "executable": item["execution_mode"] in SUPPORTED_EXECUTION_MODES,
        "stages": _workflow_stages(item),
    }


def _workflow_stages(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"key": "trigger", "label": "触发", "description": _trigger_label(item["trigger_type"]), "automated": item["trigger_type"] != "manual_file_upload"},
        {"key": "data_read", "label": "读数据", "description": _data_read_description(item), "automated": bool(item["erp_resources"])},
        {"key": "ai_decision", "label": "AI 判断", "description": item["output_contract"], "automated": True},
        {"key": "tool_execution", "label": "工具执行", "description": "、".join(item["tools"]), "automated": True},
        {"key": "approval", "label": "审批", "description": item["approval_policy"], "automated": not item["requires_approval"]},
        {"key": "writeback", "label": "写回", "description": item["writeback_target"], "automated": item["execution_mode"] != "external_existing_endpoint"},
        {"key": "notification", "label": "通知", "description": item["notification_target"], "automated": False},
        {"key": "record", "label": "记录", "description": "写入 automation_runs、steps、audit_logs。", "automated": True},
    ]


def _can_view_workflow(current_user: dict, workflow: dict[str, Any]) -> bool:
    if current_user.get("role") == "admin":
        return True

    position = current_user.get("position")
    return (
        is_valid_position(position)
        and workflow.get("position") == position
        and is_ai_app_allowed(current_user, _app_id_for_workflow(workflow))
    )


def _find_workflow(workflow_id: str) -> dict[str, Any]:
    for workflow in WORKFLOW_DEFINITIONS:
        if workflow["id"] == workflow_id:
            return workflow

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 工作流不存在")


def _app_id_for_workflow(workflow: dict[str, Any]) -> str:
    source_task_id = str(workflow.get("source_task_id") or "")
    if source_task_id == "finance_excel_transform":
        return "finance-excel-transform"
    if source_task_id == "finance_reconciliation":
        return "finance-reconciliation"
    if source_task_id == "customer_service_message_loop":
        return "customer-service-message-loop"
    if source_task_id:
        return f"automation-{source_task_id}"

    return str(workflow["id"])


def _execution_user_for_workflow(current_user: dict, workflow: dict[str, Any]) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        return current_user

    return {
        **current_user,
        "position": workflow["position"],
    }


def _build_workflow_prompt(*, workflow: dict[str, Any], input_text: str, erp_summary: str) -> str:
    source_task_id = workflow.get("source_task_id")
    if workflow["execution_mode"] in {"llm_generate", "listing_draft_writeback"} and source_task_id:
        prompt = build_automation_prompt(
            position=str(workflow["position"]),
            task_id=str(source_task_id),
            input_text=input_text,
        )
        if workflow["execution_mode"] == "listing_draft_writeback":
            prompt += (
                "\n系统执行说明：你需要一次性完成标题、五点描述、产品描述、后台搜索词、促销文案和审核备注，"
                "后续系统会自动保存为平台草稿，不要要求员工再分步骤复制粘贴。\n"
            )
        return prompt

    erp_block = erp_summary or "本次未检索到 ERP 记录，请基于用户提供的信息生成建议，并明确标注需要人工确认的信息。"
    return f"""你是跨境电商企业内部的 {workflow['position_label'] if 'position_label' in workflow else POSITION_LABELS[workflow['position']]} AI 工作流助手。
你只能处理当前工作流允许的业务，不要越权，不要编造已经写回系统的结果。

工作流名称：{workflow['name']}
业务场景：{workflow['scenario']}
审批规则：{workflow['approval_policy']}
输出要求：{workflow['output_contract']}

ERP 查询摘要：
{erp_block}

用户输入：
{input_text}

请输出：
1. 处理结论
2. 可直接使用的业务内容
3. 需要人工确认/审批的事项
4. 下一步动作
"""


def _record_workflow_step(
    *,
    run_id: str,
    order: int,
    name: str,
    status_value: str,
    workflow: dict[str, Any],
    input_text: Any,
    output_text: Any,
    duration_ms: int,
) -> dict[str, Any]:
    record_step(
        run_id=run_id,
        step_name=name,
        step_order=order,
        status_value=status_value,
        provider="ai_workflow",
        resource_type="ai_workflow",
        resource_id=str(workflow["id"]),
        input_text=input_text,
        output_text=output_text,
        duration_ms=duration_ms,
        metadata=_run_metadata(workflow),
    )
    return {
        "step_order": order,
        "step_name": name,
        "status": status_value,
        "duration_ms": duration_ms,
    }


def _run_metadata(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_id": workflow["id"],
        "workflow_name": workflow["name"],
        "position": workflow["position"],
        "category": workflow["category"],
        "execution_mode": workflow["execution_mode"],
        "requires_approval": workflow["requires_approval"],
        "saved_minutes": workflow["saved_minutes"],
    }


def _trigger_label(value: str) -> str:
    labels = {
        "manual_form": "员工在工作流中心输入任务内容后触发。",
        "manual_file_upload": "员工在专用页面上传真实文件后触发。",
        "external_message": "外部客户消息或内部收件箱触发。",
    }
    return labels.get(value, value)


def _data_read_description(item: dict[str, Any]) -> str:
    if item["execution_mode"] == "erp_then_llm":
        return "按当前岗位权限查询 ERP 资源：" + "、".join(item["erp_resources"])

    if item["execution_mode"] == "external_existing_endpoint":
        return "读取上传文件和现有工具输出，不在工作流中心复制文件内容。"

    return "读取员工输入和当前岗位配置，不访问跨岗位数据。"
