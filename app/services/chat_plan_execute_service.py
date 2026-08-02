from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal

from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.json_utils import dumps_json
from app.llm import chat_model
from app.permissions import POSITION_LABELS, ensure_erp_resource_allowed, is_valid_position
from app.services.agent_execution_service import (
    CHAT_PLAN_EXECUTE_APP_ID,
    CHAT_PLAN_EXECUTE_WORKFLOW_ID,
    AgentPlanStep,
)
from app.services.ai_workflow_service import run_ai_workflow
from app.services.email_service import EmailAttachment, email_result_metadata, send_email_with_attachments
from app.services.enterprise_wechat_service import search_enterprise_wechat_recipients
from app.services.external_action_gateway_service import (
    ExternalActionIntent,
    resolve_external_action_followup_intent,
    recognize_external_action_intent,
    resolve_external_action_message,
)
from app.services.finance_compound_generation_service import execute_finance_compound_generation
from app.services.finance_compound_intent_service import recognize_finance_compound_intent
from app.services.finance_report_service import FinanceReportInputFile, analyze_finance_report_files
from app.services.finance_salary_service import export_salary_workbook_from_erp, recognize_salary_export_intent
from app.services.finance_salary_wechat_service import (
    build_enterprise_wechat_file_confirmation_task,
    build_salary_wechat_plan,
    build_wechat_prepare_confirmation_task,
    dispatch_enterprise_wechat_file_send_task,
    extract_wechat_recipient,
    prepare_salary_wechat_dispatch,
    recognize_salary_wechat_send_intent,
    run_record_status_for_salary_wechat,
)
from app.services.generated_file_service import (
    get_generated_file_storage_reference,
    get_latest_generated_file_for_thread,
    save_generated_file,
)
from app.services.logging_service import write_audit_log
from app.services.mcp_tool_registry_service import (
    execute_managed_mcp_tool,
    get_mcp_tool_definition,
    list_mcp_tools,
)
from app.services.operations_listing_amazon_service import generate_operations_listing_draft
from app.services.platform_draft_service import (
    get_latest_platform_draft_for_source_run,
    get_platform_draft,
)
from app.services.run_record_service import elapsed_ms, finish_run, get_run_detail, list_runs, now_ms, record_step, start_run
from app.services.user_ai_app_permission_service import is_ai_app_allowed
from app.skills.executor import execute_skill
from app.skills.registry import get_skill, list_skills, skill_for_react_action


ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class ChatPlanStepSpec:
    key: str
    label: str
    executor_type: str
    ref: str
    description: str
    sensitive: bool = False
    requires_confirmation: bool = False


class ChatPlanStepChoice(BaseModel):
    key: str = Field(description="步骤键名。")
    label: str = Field(description="步骤标题。")
    executor_type: Literal["skill", "mcp", "ai_workflow"] = Field(description="执行器类型。")
    ref: str = Field(description="Skill ID 或 MCP 工具 ID，或工作流 ID。")
    description: str = Field(description="这一步要做什么。")
    sensitive: bool = Field(default=False, description="是否涉及敏感动作。")
    requires_confirmation: bool = Field(default=False, description="是否必须人工确认后再继续。")
    arguments: dict[str, Any] = Field(default_factory=dict, description="执行这一步时要传给 Skill 或 MCP 的参数。")


class GenericChatPlanChoice(BaseModel):
    kind: Literal["external_action", "finance", "amazon_listing", "message_send", "file_processing", "general_complex_task", "clarify", "deny"] = Field(description="任务大类。")
    main_object: str = Field(default="", description="主对象，例如财务资料、Listing 草稿、文件发送。")
    summary: str = Field(default="", description="中文概述。")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度。")
    requires_clarification: bool = Field(default=False, description="是否需要追问。")
    clarification_question: str | None = Field(default=None, description="追问内容。")
    required_fields: list[str] = Field(default_factory=list, description="还缺哪些关键字段。")
    expected_outputs: list[str] = Field(default_factory=list, description="最终应输出什么。")
    steps: list[ChatPlanStepChoice] = Field(default_factory=list, description="执行步骤。")
    selected_skill_id: str | None = Field(default=None, description="优先执行的 Skill。")
    selected_mcp_tool_id: str | None = Field(default=None, description="优先执行的 MCP 工具。")


def _build_external_action_plan(intent: ExternalActionIntent) -> dict[str, Any]:
    steps = [
        ChatPlanStepSpec(
            key="external_action_route",
            label="识别外部动作",
            executor_type="policy",
            ref="external_action_gateway",
            description="识别发送、填写、上传或写入外部平台的统一入口。",
            sensitive=True,
        ).__dict__,
        ChatPlanStepSpec(
            key="permission",
            label="检查权限",
            executor_type="policy",
            ref="backend.permission",
            description="检查岗位、AI 应用、ERP 资源和外部连接器权限。",
            sensitive=True,
        ).__dict__,
    ]

    if intent.business_object == "salary_table":
        steps.append(
            ChatPlanStepSpec(
                key="generate_salary",
                label="生成工资表",
                executor_type="skill",
                ref="finance_salary_export",
                description="按期间查询 ERP 工资单并生成工资表 Excel。",
                sensitive=True,
            ).__dict__
        )
    elif intent.business_object in {"finance_report", "finance_package"}:
        steps.append(
            ChatPlanStepSpec(
                key="generate_finance_report",
                label="生成财务资料",
                executor_type="skill",
                ref="finance_compound_report_generation",
                description="按用户要求查询 ERP 财务资源并生成财务资料。",
                sensitive=True,
            ).__dict__
        )
    elif intent.business_object == "listing_draft":
        steps.append(
            ChatPlanStepSpec(
                key="generate_listing_draft",
                label="生成 Listing 草稿",
                executor_type="skill",
                ref="operations_listing",
                description="根据用户信息、图片和 ERP 商品资料生成 Listing 草稿。",
                sensitive=True,
            ).__dict__
        )
    elif intent.business_object in {"inventory_table", "employee_table", "customer_reply_draft"}:
        steps.append(
            ChatPlanStepSpec(
                key="generate_business_file",
                label="生成业务文件",
                executor_type="skill",
                ref=f"{intent.business_object}.generator",
                description="通过 ERP 抽象资源或对应 Skill 生成业务文件；缺少生成器时返回可理解提示。",
                sensitive=True,
            ).__dict__
        )
    else:
        steps.append(
            ChatPlanStepSpec(
                key="identify_files",
                label="识别文件",
                executor_type="python",
                ref="file.lookup",
                description="优先使用当前会话最近生成文件；没有时再根据业务对象生成。",
                sensitive=True,
            ).__dict__
        )

    if intent.target_channel == "enterprise_wechat":
        steps.append(
            ChatPlanStepSpec(
                key="enterprise_wechat_confirmation",
                label="企业微信发送确认",
                executor_type="mcp",
                ref="message_sender.search_enterprise_wechat_recipient",
                description="搜索企业微信接收对象并生成发送确认卡。",
                sensitive=True,
                requires_confirmation=True,
            ).__dict__
        )
    elif intent.target_channel == "email":
        steps.append(
            ChatPlanStepSpec(
                key="email_confirmation",
                label="邮箱发送确认",
                executor_type="mcp",
                ref="message_sender.prepare_message_draft",
                description="生成邮箱发送确认卡，不直接发送。",
                sensitive=True,
                requires_confirmation=True,
            ).__dict__
        )
    elif intent.target_channel == "amazon_seller_central":
        steps.append(
            ChatPlanStepSpec(
                key="amazon_fill_confirmation",
                label="Amazon 填写确认",
                executor_type="mcp",
                ref="playwright_amazon.prepare_seller_central_listing",
                description="打开 Seller Central 并填写草稿，停在最终发布前。",
                sensitive=True,
                requires_confirmation=True,
            ).__dict__
        )
    else:
        steps.append(
            ChatPlanStepSpec(
                key="external_confirmation",
                label="外部动作确认",
                executor_type="mcp",
                ref="message_sender.prepare_message_draft",
                description="外部动作目标不够明确时，先生成确认或追问。",
                sensitive=True,
                requires_confirmation=True,
            ).__dict__
        )

    target_label = {
        "enterprise_wechat": "企业微信",
        "email": "邮箱",
        "amazon_seller_central": "Amazon Seller Central",
        "customer_service_system": "客服系统",
        "erp_or_external_platform": "外部平台",
        "unknown_message_channel": "待确认发送通道",
    }.get(intent.target_channel, intent.target_channel)
    object_label = _business_object_label(intent.business_object)
    action_label = _external_action_label(intent.external_action_type)
    return {
        "kind": "external_action",
        "requires_clarification": False,
        "main_object": object_label,
        "summary": f"识别到需要{action_label}：{object_label} -> {target_label}。",
        "confidence": intent.confidence,
        "external_action_type": intent.external_action_type,
        "target_channel": intent.target_channel,
        "business_object": intent.business_object,
        "data_source": intent.data_source,
        "recipient_name": intent.recipient_name,
        "requires_confirmation": True,
        "external_action_intent": intent.to_dict(),
        "steps": steps,
        "expected_outputs": ["chat_summary", "download_link", "approval_card"],
        "required_fields": [],
    }


def build_chat_plan_execute_plan(
    *,
    message: str,
    current_user: dict,
    attachments: list[dict[str, Any]] | None = None,
    thread_id: str | None = None,
    resume_run_id: str | None = None,
) -> dict[str, Any]:
    raw_text = " ".join((message or "").strip().split())
    text = raw_text
    attachment_list = attachments or []
    if not text:
        return {
            "kind": "clarify",
            "requires_clarification": True,
            "question": _default_complex_task_question(current_user),
            "reason": "用户消息为空。",
            "confidence": 1.0,
        }
    text, pending_external_action = resolve_external_action_message(text, thread_id)
    external_action_followup_intent = resolve_external_action_followup_intent(raw_text, thread_id, attachment_list)
    if external_action_followup_intent is not None:
        if pending_external_action and pending_external_action.get("active") and not external_action_followup_intent.recipient_name:
            external_action_followup_intent = ExternalActionIntent(
                **{
                    **external_action_followup_intent.to_dict(),
                    "recipient_name": str(pending_external_action.get("recipient_name") or "") or None,
                }
            )
        plan = _build_external_action_plan(external_action_followup_intent)
        plan["source_message"] = str((pending_external_action or {}).get("source_message") or raw_text)
        plan["effective_message"] = text
        return plan

    if _looks_like_resume_request(text):
        resume_context = _load_resume_context(resume_run_id=resume_run_id, current_user=current_user)
        if resume_context and isinstance(resume_context.get("plan"), dict):
            resumed_plan = dict(resume_context["plan"])
            resumed_plan["resume_run_id"] = resume_run_id
            resumed_plan["resume_mode"] = True
            resumed_plan["resume_summary"] = resume_context.get("summary")
            return resumed_plan
        return {
            "kind": "clarify",
            "requires_clarification": True,
            "question": "我需要先找到上一轮还没完成的复杂任务。请再发一次上一句任务，或告诉我想继续哪一单。",
            "reason": "检测到续跑请求，但没找到可继续的计划。",
            "confidence": 0.8,
        }

    external_action_intent = recognize_external_action_intent(text, attachment_list)
    if external_action_intent is not None:
        if pending_external_action and pending_external_action.get("active"):
            external_action_intent = ExternalActionIntent(
                **{
                    **external_action_intent.to_dict(),
                    "recipient_name": external_action_intent.recipient_name or pending_external_action.get("recipient_name"),
                }
            )
        plan = _build_external_action_plan(external_action_intent)
        plan["source_message"] = str((pending_external_action or {}).get("source_message") or raw_text)
        plan["effective_message"] = text
        return plan

    if _is_salary_finance_task(text):
        intent = recognize_salary_export_intent(text)
        if not is_valid_position(current_user.get("position")) and current_user.get("role") != "admin":
            return _deny_plan("当前账号未绑定岗位，不能执行这个任务。")
        if current_user.get("role") != "admin" and current_user.get("position") != "finance":
            return _deny_plan("这个任务属于财务岗位，当前账号没有权限。")
        if "工资" in text and not is_ai_app_allowed(current_user, "automation-salary_summary"):
            return _deny_plan("统计工资应用已被管理员禁用。")
        if _contains(text, ["企业微信", "微信"]) and not is_ai_app_allowed(current_user, "automation-salary_wechat_send"):
            return _deny_plan("工资表微信发送应用已被管理员禁用。")
        steps = [
            ChatPlanStepSpec(
                key="permission",
                label="检查权限",
                executor_type="policy",
                ref="backend.permission",
                description="检查财务岗位、AI 应用、ERP 资源和敏感数据权限。",
                sensitive=True,
            ),
            ChatPlanStepSpec(
                key="generate_salary",
                label="生成工资表",
                executor_type="skill",
                ref="finance_salary_export",
                description="按期间查询 ERP Salary Slip 并生成工资表 Excel。",
                sensitive=True,
            ),
        ]
        if _contains(text, ["财务报表", "报表", "月报", "经营"]):
            steps.append(
                ChatPlanStepSpec(
                    key="generate_report",
                    label="生成财务报表",
                    executor_type="skill",
                    ref="finance_compound_report_generation",
                    description="生成本期财务报表。",
                    sensitive=True,
                )
            )
        if _contains(text, ["合并", "汇总", "整理后", "一个表", "一个文件"]):
            steps.append(
                ChatPlanStepSpec(
                    key="merge",
                    label="整理文件",
                    executor_type="python",
                    ref="finance.merge",
                    description="合并或整理财务文件。",
                    sensitive=True,
                )
            )
        if _contains(text, ["企业微信", "微信"]):
            steps.append(
                ChatPlanStepSpec(
                    key="wechat_prepare",
                    label="准备企业微信发送",
                    executor_type="mcp",
                    ref="message_sender.prepare_message_draft",
                    description="生成企业微信发送确认卡。",
                    sensitive=True,
                    requires_confirmation=True,
                )
            )
        return {
            "kind": "finance",
            "requires_clarification": False,
            "main_object": "财务资料",
            "confidence": max(intent.confidence, 0.92),
            "steps": [step.__dict__ for step in steps],
            "expected_outputs": ["chat_summary", "workbook", "download_link", "approval_card"],
            "required_fields": [],
        }

    if _is_amazon_listing_task(text):
        if current_user.get("role") != "admin" and current_user.get("position") != "operations":
            return _deny_plan("这个任务属于运营岗位，当前账号没有权限。")
        if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, "automation-listing"):
            return _deny_plan("运营 Listing 应用已被管理员禁用。")
        steps = [
            ChatPlanStepSpec(
                key="permission",
                label="检查权限",
                executor_type="policy",
                ref="backend.permission",
                description="检查运营岗位、AI 应用和 Amazon 草稿权限。",
                sensitive=True,
            ),
            ChatPlanStepSpec(
                key="draft",
                label="生成 Listing 草稿",
                executor_type="skill",
                ref="operations_listing",
                description="根据 SKU、图片和 ERP 商品资料生成 Listing 草稿。",
                sensitive=True,
            ),
            ChatPlanStepSpec(
                key="amazon_prepare",
                label="准备 Amazon 填表",
                executor_type="mcp",
                ref="playwright_amazon.prepare_seller_central_listing",
                description="打开 Seller Central，填写字段，停在发布前。",
                sensitive=True,
                requires_confirmation=True,
            ),
        ]
        return {
            "kind": "amazon_listing",
            "requires_clarification": False,
            "main_object": "Amazon Listing",
            "confidence": 0.96,
            "steps": [step.__dict__ for step in steps],
            "expected_outputs": ["platform_draft", "download_link", "approval_card"],
            "required_fields": ["sku?"],
        }

    if _contains(text, ["企业微信", "微信", "邮箱", "email", "mail"]) and _contains(text, ["发送", "发给", "转发"]):
        steps = [
            ChatPlanStepSpec(
                key="identify_files",
                label="识别文件",
                executor_type="python",
                ref="file.lookup",
                description="识别当前会话或上传文件中的可发送附件。",
                sensitive=True,
            ),
            ChatPlanStepSpec(
                key="recipient_search",
                label="搜索接收对象",
                executor_type="mcp",
                ref="message_sender.search_enterprise_wechat_recipient",
                description="搜索企业微信候选对象并处理重名情况。",
                sensitive=True,
            ),
            ChatPlanStepSpec(
                key="draft",
                label="生成发送确认卡",
                executor_type="mcp",
                ref="message_sender.prepare_message_draft",
                description="生成消息或文件发送草稿，等待人工确认。",
                sensitive=True,
                requires_confirmation=True,
            ),
        ]
        if _contains(text, ["邮箱", "email", "mail"]):
            steps[-1] = ChatPlanStepSpec(
                key="draft",
                label="生成发送确认卡",
                executor_type="mcp",
                ref="message_sender.send_confirmed_email",
                description="生成邮件发送或直接发送确认流程。",
                sensitive=True,
                requires_confirmation=True,
            )
        return {
            "kind": "message_send",
            "requires_clarification": False,
            "main_object": "文件发送",
            "confidence": 0.91,
            "steps": [step.__dict__ for step in steps],
            "expected_outputs": ["approval_card", "download_link"],
            "required_fields": ["recipient"],
        }

    if _contains(text, ["报表", "excel", "xlsx", "word", "docx", "pdf", "图片", "上传"]) and len(attachment_list) > 0:
        return {
            "kind": "file_processing",
            "requires_clarification": False,
            "main_object": "文档处理",
            "confidence": 0.84,
            "steps": [
                {
                    "key": "analyze_files",
                    "label": "分析文件",
                    "executor_type": "python",
                    "ref": "finance_report.analyze_files",
                    "description": "读取用户上传文件并整理为业务结果。",
                    "sensitive": False,
                    "requires_confirmation": False,
                }
            ],
            "expected_outputs": ["chat_summary", "workbook", "download_link"],
            "required_fields": [],
        }

    if should_use_chat_plan_execute(text, attachment_list):
        llm_plan = _build_llm_generic_chat_plan(
            message=text,
            current_user=current_user,
            attachments=attachment_list,
        )
        if llm_plan.get("requires_clarification"):
            return llm_plan
        if llm_plan.get("kind") != "clarify":
            return llm_plan

    return {
        "kind": "clarify",
        "requires_clarification": True,
        "question": _default_complex_task_question(current_user),
        "reason": "当前信息还不足以确定具体复杂任务。",
        "confidence": 0.66,
    }


def _build_llm_generic_chat_plan(
    *,
    message: str,
    current_user: dict,
    attachments: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_skills = _candidate_skills_for_plan(message=message, current_user=current_user)
    candidate_tools = _candidate_mcp_tools_for_plan(message=message, current_user=current_user)
    if not candidate_skills and not candidate_tools:
        return _deny_plan("当前账号没有可用的 Skill 或 MCP 工具，无法执行这个复杂任务。")

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
你是企业内部复杂任务规划器。
你的任务是从候选 Skill 和 MCP 工具里选出最合适的一条执行路径，尽量少步骤、低延迟、可审计。

规则：
- 简单任务不要强行升级为复杂任务。
- 复杂任务可以先规划再执行，不需要用户先确认计划。
- 选择 Skill 优先于外部 MCP。
- 只有在必须调用外部平台、浏览器、企业微信、邮箱或审计查询时，才选 MCP。
- 提交、发布、改价、入库、付款、发票这类动作必须标记 requires_confirmation=true。
- 如果关键信息不足，直接返回 requires_clarification=true 并提出一个口语化追问。
- 不要返回 raw JSON 字符串解释，只返回结构化结果。
""".strip(),
        ),
        (
            "human",
            """
用户岗位：{position_label}
用户消息：{message}
附件概览：{attachments}

候选 Skills：
{candidate_skills}

候选 MCP 工具：
{candidate_tools}

请根据候选项给出最合理的复杂任务规划。
""".strip(),
        ),
    ])
    planner = prompt | chat_model.with_structured_output(GenericChatPlanChoice)
    decision = planner.invoke(
        {
            "position_label": POSITION_LABELS.get(str(current_user.get("position")), "管理员/未绑定岗位"),
            "message": message,
            "attachments": dumps_json(_attachment_summaries(attachments)),
            "candidate_skills": dumps_json(candidate_skills),
            "candidate_tools": dumps_json(candidate_tools),
        }
    )
    decision.clarification_question = _sanitize_clarification_question(decision.clarification_question, current_user)
    plan = _generic_plan_from_decision(decision)
    if plan.get("requires_clarification"):
        return plan
    return plan


def _generic_plan_from_decision(decision: GenericChatPlanChoice) -> dict[str, Any]:
    steps = [step.model_dump() for step in decision.steps]
    if not steps:
        if decision.selected_skill_id:
            steps = [
                {
                    "key": "selected_skill",
                    "label": "执行 Skill",
                    "executor_type": "skill",
                    "ref": decision.selected_skill_id,
                    "description": decision.summary or "由 AI 选择的 Skill 执行。",
                    "sensitive": False,
                    "requires_confirmation": False,
                    "arguments": {},
                }
            ]
        elif decision.selected_mcp_tool_id:
            steps = [
                {
                    "key": "selected_tool",
                    "label": "执行 MCP 工具",
                    "executor_type": "mcp",
                    "ref": decision.selected_mcp_tool_id,
                    "description": decision.summary or "由 AI 选择的 MCP 工具执行。",
                    "sensitive": False,
                    "requires_confirmation": False,
                    "arguments": {},
                }
            ]
    if not steps and decision.kind not in {"clarify", "deny"}:
        return _deny_plan("AI 未能生成可执行的复杂任务步骤，请换一种更具体的说法。")
    return {
        "kind": decision.kind,
        "main_object": decision.main_object,
        "summary": decision.summary,
        "confidence": decision.confidence,
        "requires_clarification": decision.requires_clarification,
        "clarification_question": decision.clarification_question,
        "required_fields": decision.required_fields,
        "expected_outputs": decision.expected_outputs or ["chat_summary"],
        "steps": steps,
        "selected_skill_id": decision.selected_skill_id,
        "selected_mcp_tool_id": decision.selected_mcp_tool_id,
    }


def _default_complex_task_question(current_user: dict) -> str:
    position = str(current_user.get("position") or "")
    if position == "finance":
        return "你要我先做哪类财务动作？比如整理工资表、财务报表、查 ERP、生成文件或发文件。"
    if position == "operations":
        return "你要我先做哪类运营动作？比如生成 Listing 草稿、查 SKU、处理商品图、填表或发文件。"
    if position == "customer_service":
        return "你要我先做哪类客服动作？比如整理回复草稿、查订单、查物流、保存草稿或发文件。"
    return "你要我先做哪件复杂任务？比如整理表格、生成草稿、发文件、查 ERP 或填外部平台。"


def _sanitize_clarification_question(question: str | None, current_user: dict) -> str | None:
    text = " ".join((question or "").strip().split())
    if not text:
        return question

    position = str(current_user.get("position") or "")
    lowered = text.lower()
    blocked_terms_by_position = {
        "finance": ["amazon", "seller central", "listing", "运营", "商品图"],
        "operations": ["工资", "薪资", "薪酬", "财务报表", "总账", "收付款", "发票"],
        "customer_service": ["工资", "薪资", "薪酬", "财务报表", "总账", "收付款", "发票", "listing", "amazon"],
    }
    blocked_terms = blocked_terms_by_position.get(position, [])
    if any(term.lower() in lowered for term in blocked_terms):
        return _default_complex_task_question(current_user)
    return text


def _find_resume_run_id(*, thread_id: str, current_user: dict) -> str | None:
    runs = list_runs(
        current_user=current_user,
        resource_type="thread",
        resource_id=thread_id,
        limit=20,
    )
    for run in runs:
        if str(run.get("status") or "") not in {"failed", "blocked", "running"}:
            continue
        metadata = run.get("metadata") if isinstance(run.get("metadata"), dict) else {}
        if metadata.get("workflow_id") or metadata.get("complex_kind") or metadata.get("mode") == "plan_execute":
            return str(run.get("id"))
        if run.get("run_type") in {"chat_plan_execute", "agent_plan_execute"}:
            return str(run.get("id"))
    return None


def _load_resume_context(*, resume_run_id: str | None, current_user: dict) -> dict[str, Any] | None:
    if not resume_run_id:
        return None
    try:
        detail = get_run_detail(resume_run_id, current_user=current_user)
    except HTTPException:
        return None

    run = detail.get("run") if isinstance(detail.get("run"), dict) else {}
    metadata = run.get("metadata") if isinstance(run.get("metadata"), dict) else {}
    plan = metadata.get("plan") if isinstance(metadata.get("plan"), dict) else None
    platform_draft = get_latest_platform_draft_for_source_run(
        source_run_id=resume_run_id,
        current_user=current_user,
    )
    generated_files: list[dict[str, Any]] = []
    for item in detail.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        artifact_type = str(item.get("artifact_type") or "")
        if artifact_type not in {"excel_file", "word_file", "docx_file", "report_file"}:
            continue
        try:
            generated_files.append(get_generated_file_storage_reference(str(item.get("id")), current_user=current_user))
        except HTTPException:
            continue

    completed_steps = [
        str(step.get("step_name") or "")
        for step in detail.get("steps") or []
        if isinstance(step, dict) and str(step.get("status") or "") == "succeeded"
    ]
    return {
        "run": run,
        "plan": plan,
        "summary": {
            "run_id": resume_run_id,
            "status": run.get("status"),
            "workflow_id": metadata.get("workflow_id"),
            "complex_kind": metadata.get("complex_kind") or metadata.get("intent"),
            "step_count": len(detail.get("steps") or []),
            "artifact_count": len(detail.get("artifacts") or []),
            "completed_steps": completed_steps,
            "has_platform_draft": bool(platform_draft),
            "has_generated_files": bool(generated_files),
        },
        "platform_draft": platform_draft,
        "generated_files": generated_files,
        "raw_detail": detail,
    }


def _candidate_skills_for_plan(*, message: str, current_user: dict) -> list[dict[str, Any]]:
    text = message.lower()
    items = list_skills(position=current_user.get("position") if current_user.get("position") in {"operations", "customer_service", "finance"} else None)
    scored = sorted(items, key=lambda skill: _skill_match_score(skill, text), reverse=True)
    result: list[dict[str, Any]] = []
    for skill in scored[:8]:
        score = _skill_match_score(skill, text)
        if score <= 0 and result:
            continue
        result.append(
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "position": skill.position,
                "description": skill.description,
                "allowed_tools": list(skill.allowed_tools[:8]),
                "allowed_erp_resources": list(skill.allowed_erp_resources[:8]),
                "risk_level": skill.risk_level,
                "requires_approval": skill.requires_approval,
            }
        )
    return result


def _candidate_mcp_tools_for_plan(*, message: str, current_user: dict) -> list[dict[str, Any]]:
    text = message.lower()
    mcp_items = list_mcp_tools().get("items") or []
    if not isinstance(mcp_items, list):
        return []
    allowed_position = current_user.get("position")
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in mcp_items:
        if not isinstance(item, dict):
            continue
        if current_user.get("role") != "admin" and allowed_position not in set(item.get("position_scopes") or []):
            continue
        score = _mcp_tool_match_score(item, text)
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    result: list[dict[str, Any]] = []
    for score, item in scored[:10]:
        if score <= 0 and result:
            continue
        result.append(
            {
                "tool_id": item.get("tool_id"),
                "label": item.get("label"),
                "category": item.get("category"),
                "description": item.get("description"),
                "risk_level": item.get("risk_level"),
                "execution_mode": item.get("execution_mode"),
                "requires_approval": item.get("requires_approval"),
            }
        )
    return result


def _skill_match_score(skill, text: str) -> int:
    haystack = " ".join(
        str(item or "")
        for item in [
            skill.skill_id,
            skill.name,
            skill.description,
            skill.app_id,
            skill.flow_key,
            " ".join(skill.legacy_ids),
            " ".join(skill.react_actions),
            " ".join(skill.allowed_tools),
            " ".join(skill.allowed_erp_resources),
        ]
    ).lower()
    return sum(1 for keyword in _generic_keywords(text) if keyword in haystack)


def _mcp_tool_match_score(item: dict[str, Any], text: str) -> int:
    haystack = " ".join(
        str(item.get(key) or "")
        for key in ["tool_id", "label", "category", "description", "execution_mode"]
    ).lower()
    return sum(1 for keyword in _generic_keywords(text) if keyword in haystack)


def _generic_keywords(text: str) -> list[str]:
    words = [word for word in re.split(r"[\s,，。；;:：/]+", text) if len(word) >= 2]
    base = {
        "生成",
        "整理",
        "发送",
        "发给",
        "上传",
        "下载",
        "审核",
        "确认",
        "报表",
        "工资",
        "财务",
        "listing",
        "amazon",
        "seller",
        "微信",
        "企业微信",
        "邮箱",
        "word",
        "excel",
        "pdf",
        "图片",
        "对账",
        "客服",
        "运营",
    }
    return list(base.union(words[:12]))


def _attachment_summaries(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in attachments:
        if not isinstance(item, dict):
            continue
        summaries.append(
            {
                "type": item.get("type"),
                "filename": item.get("filename"),
                "mime_type": item.get("mime_type"),
                "size_bytes": item.get("size_bytes"),
                "metadata_keys": sorted((item.get("metadata") or {}).keys()) if isinstance(item.get("metadata"), dict) else [],
            }
        )
    return summaries


def should_use_chat_plan_execute(message: str, attachments: list[dict[str, Any]] | None = None) -> bool:
    text = " ".join((message or "").strip().split())
    if not text:
        return False

    lowered = text.lower()
    if _looks_like_resume_request(text):
        return True

    attachment_list = attachments or []
    action_score = sum(
        1
        for keyword in [
            "然后",
            "再",
            "并且",
            "同时",
            "最后",
            "先",
            "接着",
            "合并",
            "整理后",
            "整理成",
            "写入",
            "填入",
            "打开",
            "搜索",
            "生成",
            "发送",
            "发给",
            "上传",
            "下载",
            "确认",
        ]
        if keyword in lowered
    )
    send_score = sum(1 for keyword in ["微信", "企业微信", "邮箱", "email", "mail", "amazon", "seller central", "亚马逊"] if keyword in lowered)
    file_score = sum(1 for keyword in ["excel", "xlsx", "word", "docx", "pdf", "图片", "附件", "文档", "表格", "listing", "上架", "草稿"] if keyword in lowered)
    attachment_score = sum(1 for item in attachment_list if isinstance(item, dict))

    if any(keyword in lowered for keyword in ["amazon", "seller central", "listing", "上架"]):
        return True
    if send_score > 0 and (file_score > 0 or attachment_score > 0 or action_score >= 1):
        return True
    if file_score + attachment_score >= 2:
        return True
    if action_score >= 3:
        return True
    if "http://" in lowered or "https://" in lowered:
        return action_score >= 2 or attachment_score > 0
    return False


def _skill_result_attachments(result: Any) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    for item in getattr(result, "attachments", []) or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        content_base64 = item.get("content_base64")
        if isinstance(content, bytes):
            content_base64 = base64.b64encode(content).decode("ascii")
        attachments.append(
            {
                "type": item.get("type") or "file",
                "filename": item.get("filename"),
                "mime_type": item.get("mime_type"),
                "size_bytes": len(content) if isinstance(content, bytes) else item.get("size_bytes") or 0,
                "content_base64": content_base64,
                "metadata": item.get("metadata") or {},
            }
        )
    return attachments


def _generic_tool_summary(result: Any) -> str:
    if isinstance(result, dict):
        parts: list[str] = []
        for key in ["message", "status", "status_label", "download_path", "id", "tool_id"]:
            value = result.get(key)
            if value not in (None, "", []):
                parts.append(f"{key}={value}")
        return "，".join(parts) if parts else dumps_json(result)[:200]
    return str(result)


def _run_general_complex_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    attachments: list[dict[str, Any]] | None = None,
    progress_callback: ProgressCallback | None = None,
    resume_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    steps = [step for step in plan.get("steps") or [] if isinstance(step, dict)]
    if not steps:
        return {
            "answer": plan.get("summary") or "已完成复杂任务规划，但没有可执行步骤。",
            "attachments": [],
            "approval_result": None,
            "automation": {
                "type": "chat_plan_execute",
                "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
                "run_id": run_id,
                "plan": plan,
                "resume_context": (resume_context or {}).get("summary"),
            },
            "platform_draft": (resume_context or {}).get("platform_draft"),
        }

    outputs: list[dict[str, Any]] = []
    step_summaries: list[str] = []
    approval_result: dict[str, Any] | None = None
    platform_draft: dict[str, Any] | None = (resume_context or {}).get("platform_draft")
    step_records: list[dict[str, Any]] = []
    mcp_traces: list[dict[str, Any]] = []
    completed_step_names = set((resume_context or {}).get("summary", {}).get("completed_steps") or [])

    for index, step in enumerate(steps, start=1):
        key = str(step.get("key") or f"step_{index}")
        label = str(step.get("label") or key)
        executor_type = str(step.get("executor_type") or "skill")
        ref = str(step.get("ref") or "")
        arguments = step.get("arguments") if isinstance(step.get("arguments"), dict) else {}
        if key in completed_step_names and platform_draft is not None and executor_type in {"skill", "ai_workflow"}:
            step_summaries.append(f"{label}：复用上次成功结果")
            step_records.append({
                "key": key,
                "label": label,
                "executor_type": executor_type,
                "ref": ref,
                "status": "reused",
            })
            continue

        _emit(progress_callback, thread_id, f"generic.{key}", label, "running")
        started_ms = now_ms()
        if executor_type == "skill":
            result = execute_skill(
                skill_id=ref,
                payload={
                    "message": message,
                    "attachments": attachments or [],
                    "metadata": {
                        "run_id": run_id,
                        "thread_id": thread_id,
                        "step_key": key,
                        "plan_kind": plan.get("kind"),
                        "resume_run_id": (resume_context or {}).get("summary", {}).get("run_id"),
                        "arguments": arguments,
                    },
                    **arguments,
                },
                current_user=current_user,
                source="chat_plan_execute",
            )
            skill_attachments = _skill_result_attachments(result)
            outputs.extend(skill_attachments)
            if getattr(result, "platform_draft", None) is not None:
                platform_draft = result.platform_draft
            if getattr(result, "approval_result", None) is not None:
                approval_result = result.approval_result
            answer_piece = str(getattr(result, "answer", "") or "").strip()
            if answer_piece:
                step_summaries.append(answer_piece)
            step_output = {
                "status": getattr(result, "status", "succeeded"),
                "answer": answer_piece,
                "attachment_count": len(skill_attachments),
                "platform_draft_id": platform_draft.get("id") if isinstance(platform_draft, dict) else None,
            }
            record_step(
                run_id=run_id,
                step_name=f"plan.{key}",
                step_order=index,
                status_value="succeeded",
                provider="skill",
                resource_type="automation",
                resource_id=ref,
                input_text=message,
                output_text=answer_piece or ref,
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "executor_type": executor_type,
                    "step": step,
                    "platform_draft_id": platform_draft.get("id") if isinstance(platform_draft, dict) else None,
                },
            )
        elif executor_type == "mcp":
            result = execute_managed_mcp_tool(
                tool_id=ref,
                arguments=arguments,
                current_user=current_user,
                source="chat_plan_execute",
                trace_collector=mcp_traces,
            )
            summary = _generic_tool_summary(result)
            if summary:
                step_summaries.append(f"{label}：{summary}")
            if isinstance(result, dict):
                if result.get("platform_draft") and isinstance(result.get("platform_draft"), dict):
                    platform_draft = result.get("platform_draft")
                if result.get("approval_result") and isinstance(result.get("approval_result"), dict):
                    approval_result = result.get("approval_result")
                if result.get("download_path"):
                    outputs.append(
                        {
                            "type": "json",
                            "filename": f"{key}.json",
                            "mime_type": "application/json",
                            "size_bytes": len(summary.encode("utf-8")),
                            "content_base64": base64.b64encode(summary.encode("utf-8")).decode("ascii"),
                            "metadata": {
                                "tool_id": ref,
                                "download_path": result.get("download_path"),
                            },
                        }
                    )
            record_step(
                run_id=run_id,
                step_name=f"plan.{key}",
                step_order=index,
                status_value="succeeded",
                provider="mcp",
                resource_type="mcp_tool",
                resource_id=ref,
                input_text=arguments,
                output_text=summary,
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "executor_type": executor_type,
                    "step": step,
                    "mcp_traces": mcp_traces[-1:] if mcp_traces else [],
                },
            )
        elif executor_type == "ai_workflow":
            result = run_ai_workflow(
                workflow_id=ref,
                input_text=message,
                current_user=current_user,
            )
            if isinstance(result, dict):
                answer_piece = str(result.get("answer") or "").strip()
                if answer_piece:
                    step_summaries.append(answer_piece)
                if result.get("platform_draft") and isinstance(result.get("platform_draft"), dict):
                    platform_draft = result.get("platform_draft")
                if result.get("approval_result") and isinstance(result.get("approval_result"), dict):
                    approval_result = result.get("approval_result")
                if result.get("attachments") and isinstance(result.get("attachments"), list):
                    outputs.extend([item for item in result.get("attachments") if isinstance(item, dict)])
            record_step(
                run_id=run_id,
                step_name=f"plan.{key}",
                step_order=index,
                status_value="succeeded",
                provider="ai_workflow",
                resource_type="ai_workflow",
                resource_id=ref,
                input_text=message,
                output_text=answer_piece if isinstance(result, dict) else ref,
                duration_ms=elapsed_ms(started_ms),
                metadata={"executor_type": executor_type, "step": step},
            )
        else:
            raise ValueError(f"不支持的执行器类型：{executor_type}")

        _emit(progress_callback, thread_id, f"generic.{key}", label, "succeeded")

    if platform_draft and isinstance(platform_draft, dict):
        step_summaries.append(f"草稿 ID：{platform_draft.get('id')}")
    if approval_result and isinstance(approval_result, dict):
        step_summaries.append(f"确认状态：{approval_result.get('status_label') or approval_result.get('status')}")

    answer_lines = [plan.get("summary") or "已完成复杂任务。"]
    if step_summaries:
        answer_lines.append("执行结果：")
        answer_lines.extend([f"- {item}" for item in step_summaries[:12]])
    if resume_context and resume_context.get("summary"):
        answer_lines.append(f"已接续上一次运行：{resume_context['summary'].get('run_id')}")

    automation = {
        "type": "chat_plan_execute",
        "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
        "run_id": run_id,
        "plan": plan,
        "resume_context": (resume_context or {}).get("summary"),
        "step_records": step_records,
        "mcp_traces": mcp_traces,
    }
    return {
        "answer": "\n".join(answer_lines),
        "attachments": outputs,
        "approval_result": approval_result,
        "platform_draft": platform_draft,
        "automation": automation,
    }


def execute_chat_plan_execute(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    attachments: list[dict[str, Any]] | None = None,
    parent_run_id: str | None = None,
    source: str = "chat",
    progress_callback: ProgressCallback | None = None,
    resume_run_id: str | None = None,
    plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_message = " ".join((message or "").strip().split())
    if resume_run_id is None and _looks_like_resume_request(normalized_message):
        resume_run_id = _find_resume_run_id(thread_id=thread_id, current_user=current_user)
    if plan is None:
        plan = build_chat_plan_execute_plan(
            message=message,
            current_user=current_user,
            attachments=attachments or [],
            thread_id=thread_id,
            resume_run_id=resume_run_id,
        )
    if plan.get("requires_clarification"):
        answer = str(plan.get("question") or "请补充关键字段。")
        return {
            "thread_id": thread_id,
            "answer": answer,
            "intent": "ask_clarification",
            "risk_level": "low",
            "erp_references": [],
            "attachments": [],
            "approval_result": None,
            "automation": {
                "type": "chat_plan_execute",
                "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
                "kind": "clarify",
                "plan": plan,
            },
        }

    if plan.get("kind") == "deny":
        answer = str(plan.get("deny_message") or plan.get("reason") or "当前任务无法执行。")
        return {
            "thread_id": thread_id,
            "answer": answer,
            "intent": "deny",
            "risk_level": "blocked",
            "erp_references": [],
            "attachments": [],
            "approval_result": None,
            "automation": {
                "type": "chat_plan_execute",
                "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
                "kind": "deny",
                "plan": plan,
            },
        }

    steps = [step for step in plan.get("steps") or [] if isinstance(step, dict)]
    _emit(progress_callback, thread_id, "understanding", "正在理解你的需求")
    resume_context = _load_resume_context(resume_run_id=resume_run_id, current_user=current_user)
    run_id = start_run(
        run_type="chat_plan_execute",
        app_id=CHAT_PLAN_EXECUTE_APP_ID,
        app_name="通用复杂任务执行",
        entrypoint="/chat" if source == "chat" else "/chat/stream",
        current_user=current_user,
        thread_id=thread_id,
        resource_type="thread",
        resource_id=thread_id,
        input_text=message,
        metadata={
            "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
            "complex_kind": plan.get("kind"),
            "plan": plan,
            "parent_run_id": parent_run_id,
            "resume_run_id": resume_run_id,
            "resume_context": resume_context.get("summary") if resume_context else None,
        },
    )
    try:
        _record_plan_step(run_id, 1, "plan.build", "succeeded", "planner", thread_id, message, plan)
        permissions = _check_permissions(current_user=current_user, plan=plan, message=message)
        _record_plan_step(
            run_id,
            2,
            "permission.check",
            "succeeded" if permissions["ok"] else "blocked",
            "backend_policy",
            thread_id,
            {"position": current_user.get("position"), "role": current_user.get("role")},
            permissions,
        )
        if not permissions["ok"]:
            answer = permissions["message"]
            finish_run(run_id, status_value="blocked", output_text=answer, duration_ms=0, metadata={"plan": plan})
            return _result(thread_id=thread_id, answer=answer, plan=plan, run_id=run_id, risk_level="blocked")

        outputs: list[dict[str, Any]] = []
        approval_result: dict[str, Any] | None = None
        automation: dict[str, Any] | None = None
        step_order = 3

        if plan["kind"] == "external_action":
            external_result = _run_external_action_plan(
                message=message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                attachments=attachments or [],
                progress_callback=progress_callback,
                resume_context=resume_context,
            )
            outputs.extend(external_result.get("attachments") or [])
            approval_result = external_result.get("approval_result")
            automation = external_result.get("automation")
            answer = external_result.get("answer")
        elif plan["kind"] == "finance":
            finance_result = _run_finance_plan(
                message=message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                progress_callback=progress_callback,
                resume_context=resume_context,
            )
            outputs.extend(finance_result.get("attachments") or [])
            approval_result = finance_result.get("approval_result")
            automation = finance_result.get("automation")
            answer = finance_result.get("answer")
        elif plan["kind"] == "amazon_listing":
            listing_result = _run_amazon_plan(
                message=message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                attachments=attachments or [],
                resume_context=resume_context,
            )
            outputs.extend(listing_result.get("attachments") or [])
            approval_result = listing_result.get("approval_result")
            automation = listing_result.get("automation")
            answer = listing_result.get("answer")
        elif plan["kind"] == "message_send":
            send_result = _run_message_send_plan(
                message=message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                resume_context=resume_context,
            )
            outputs.extend(send_result.get("attachments") or [])
            approval_result = send_result.get("approval_result")
            automation = send_result.get("automation")
            answer = send_result.get("answer")
        elif plan["kind"] == "general_complex_task":
            general_result = _run_general_complex_plan(
                message=message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                attachments=attachments or [],
                progress_callback=progress_callback,
                resume_context=resume_context,
            )
            outputs.extend(general_result.get("attachments") or [])
            approval_result = general_result.get("approval_result")
            automation = general_result.get("automation")
            answer = general_result.get("answer")
        else:
            file_result = _run_file_processing_plan(
                message=message,
                current_user=current_user,
                thread_id=thread_id,
                attachments=attachments or [],
                plan=plan,
                run_id=run_id,
                resume_context=resume_context,
            )
            outputs.extend(file_result.get("attachments") or [])
            answer = file_result.get("answer")

        finish_run(
            run_id,
            status_value="succeeded",
            output_text=answer,
            duration_ms=0,
            metadata={
                "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
                "complex_kind": plan.get("kind"),
                "plan": plan,
                "attachment_count": len(outputs),
                "approval_result": approval_result,
                "automation": automation,
            },
        )
        write_audit_log(
            user_id=current_user.get("id"),
            action="chat.plan_execute",
            resource_type="thread",
            resource_id=thread_id,
            metadata={
                "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
                "complex_kind": plan.get("kind"),
                "run_id": run_id,
            },
        )
        return {
            "thread_id": thread_id,
            "answer": answer,
            "intent": "chat_plan_execute",
            "risk_level": "high" if plan.get("kind") in {"external_action", "finance", "amazon_listing", "message_send"} else "medium",
            "erp_references": [],
            "attachments": outputs,
            "approval_result": approval_result,
            "automation": automation or {
                "type": "chat_plan_execute",
                "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
                "run_id": run_id,
                "plan": plan,
            },
        }
    except HTTPException as error:
        finish_run(run_id, status_value="failed", error_message=str(error.detail), duration_ms=0, metadata={"plan": plan})
        raise
    except Exception as error:
        finish_run(run_id, status_value="failed", error_message=error, duration_ms=0, metadata={"plan": plan})
        raise


def _run_external_action_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    attachments: list[dict[str, Any]] | None = None,
    progress_callback: ProgressCallback | None = None,
    resume_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    effective_message = str(
        plan.get("effective_message")
        or plan.get("source_message")
        or message
        or ""
    ).strip() or message
    target_channel = str(plan.get("target_channel") or "")
    business_object = str(plan.get("business_object") or "latest_file")
    action_type = str(plan.get("external_action_type") or "")

    record_step(
        run_id=run_id,
        step_name="external_action.route",
        step_order=3,
        status_value="succeeded",
        provider="rules",
        resource_type="external_action",
        resource_id=target_channel or "unknown",
        input_text=message,
        output_text=plan.get("summary"),
        duration_ms=0,
        metadata={
            "external_action_type": action_type,
            "target_channel": target_channel,
            "business_object": business_object,
            "data_source": plan.get("data_source"),
            "recipient_name": plan.get("recipient_name"),
            "external_action_intent": plan.get("external_action_intent"),
        },
    )

    if target_channel == "unknown_message_channel":
        return {
            "answer": "我识别到你想发送文件，但还不确定通过企业微信还是邮箱发送。请补充发送通道。",
            "attachments": [],
            "approval_result": {
                "status": "waiting_clarification",
                "status_label": "等待补充发送通道",
                "requires_confirmation": True,
            },
            "automation": _external_action_automation(run_id=run_id, plan=plan, status="waiting_clarification"),
        }

    if target_channel == "amazon_seller_central" or business_object == "listing_draft":
        _emit(progress_callback, thread_id, "external_action.amazon", "正在准备 Amazon 草稿填写")
        return _with_external_action_metadata(
            _run_amazon_plan(
                message=effective_message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                attachments=attachments or [],
                resume_context=resume_context,
            ),
            plan=plan,
        )

    if business_object == "salary_table" and target_channel == "enterprise_wechat":
        _emit(progress_callback, thread_id, "external_action.salary_wechat", "正在准备工资表企业微信发送")
        salary_intent = recognize_salary_wechat_send_intent(effective_message)
        return _with_external_action_metadata(
            _run_salary_wechat_plan(
                message=effective_message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                progress_callback=progress_callback,
                salary_wechat_intent=salary_intent,
            ),
            plan=plan,
        )

    if business_object == "salary_table" and target_channel == "email":
        _emit(progress_callback, thread_id, "external_action.salary_email", "正在生成工资表并准备邮箱确认")
        return _with_external_action_metadata(
            _run_salary_email_plan(
                message=effective_message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                progress_callback=progress_callback,
            ),
            plan=plan,
        )

    if business_object in {"finance_report", "finance_package"} and target_channel == "enterprise_wechat":
        _emit(progress_callback, thread_id, "external_action.finance_wechat", "正在整理财务资料并准备企业微信确认")
        return _with_external_action_metadata(
            _run_finance_plan(
                message=effective_message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                progress_callback=progress_callback,
                resume_context=resume_context,
            ),
            plan=plan,
        )

    if target_channel in {"enterprise_wechat", "email"}:
        _emit(progress_callback, thread_id, "external_action.file_send", "正在查找最近生成文件并准备发送确认")
        return _with_external_action_metadata(
            _run_message_send_plan(
                message=effective_message,
                current_user=current_user,
                thread_id=thread_id,
                plan=plan,
                run_id=run_id,
                resume_context=resume_context,
            ),
            plan=plan,
        )

    return {
        "answer": "我已经识别到这是外部软件动作，但这个目标平台还没有接入真实执行器。当前不会直接操作外部系统。",
        "attachments": [],
        "approval_result": {
            "status": "waiting_executor",
            "status_label": "等待接入外部执行器",
            "requires_confirmation": True,
        },
        "automation": _external_action_automation(run_id=run_id, plan=plan, status="waiting_executor"),
    }


def _run_finance_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    progress_callback: ProgressCallback | None = None,
    resume_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _emit(progress_callback, thread_id, "finance.permission", "正在检查财务权限")
    intent = recognize_finance_compound_intent(message)
    salary_wechat_intent = recognize_salary_wechat_send_intent(message)
    if intent.intent != "finance_compound_report_generation" and salary_wechat_intent.intent == "finance_salary_wechat_send":
        return _run_salary_wechat_plan(
            message=message,
            current_user=current_user,
            thread_id=thread_id,
            plan=plan,
            run_id=run_id,
            progress_callback=progress_callback,
            salary_wechat_intent=salary_wechat_intent,
        )

    result = execute_finance_compound_generation(
        message=message,
        current_user=current_user,
        intent=intent,
        run_id=run_id,
        source="chat",
    )
    attachments = [_attachment_to_chat_attachment(item) for item in result.attachments]
    approval_result: dict[str, Any] | None = None
    automation: dict[str, Any] = {
        "type": "finance_compound_generation",
        "run_id": run_id,
        "plan": plan,
        "generated_count": len(attachments),
    }
    if intent.wechat_requested and attachments:
        primary_attachment = attachments[0]
        primary_metadata = primary_attachment.get("metadata") if isinstance(primary_attachment.get("metadata"), dict) else {}
        artifact_id = str(primary_metadata.get("artifact_id") or "").strip()
        if artifact_id:
            generated_artifacts = []
            for item in attachments:
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                item_artifact_id = str(metadata.get("artifact_id") or "").strip()
                if not item_artifact_id:
                    continue
                generated_artifacts.append(
                    {
                        "artifact_id": item_artifact_id,
                        "filename": str(item.get("filename") or item_artifact_id),
                        "download_path": str(
                            metadata.get("download_path") or f"/files/{item_artifact_id}/download"
                        ),
                        "mime_type": str(item.get("mime_type") or "application/octet-stream"),
                    }
                )
            recipient_name = extract_wechat_recipient(message) or "待确认联系人"
            wechat_execution = build_enterprise_wechat_file_confirmation_task(
                artifact_id=artifact_id,
                artifact_filename=str(primary_attachment.get("filename") or artifact_id),
                recipient_name=recipient_name,
                current_user=current_user,
                source_message=message,
                source_workflow_id="finance_monthly_package_wechat_send",
                mime_type=str(primary_attachment.get("mime_type") or "application/octet-stream"),
                requires_sensitive_confirmation=True,
                artifacts=generated_artifacts,
            )
            approval_result = {
                "status": wechat_execution.get("status"),
                "status_label": wechat_execution.get("status_label"),
                "requires_recipient_confirmation": True,
                "requires_sensitive_data_confirmation": True,
                "confirmation_card": wechat_execution.get("confirmation_card"),
            }
            automation = {
                **automation,
                "type": "enterprise_wechat_file_send",
                "status": wechat_execution.get("status"),
                "status_label": wechat_execution.get("status_label"),
                "workflow_id": "finance_monthly_package_wechat_send",
                "recipient_name": recipient_name,
                "source_message": message,
                "wechat_send": wechat_execution,
                "confirmation_card": wechat_execution.get("confirmation_card"),
                "artifact_id": artifact_id,
                "filename": primary_attachment.get("filename"),
                "download_path": primary_metadata.get("download_path"),
                "generated_artifacts": generated_artifacts,
            }
    _emit(progress_callback, thread_id, "finance.done", "正在整理最终结果")
    return {
        "answer": result.answer,
        "attachments": attachments,
        "approval_result": approval_result,
        "automation": automation,
    }


def _run_salary_wechat_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    progress_callback: ProgressCallback | None = None,
    salary_wechat_intent: Any | None = None,
) -> dict[str, Any]:
    intent = salary_wechat_intent or recognize_salary_wechat_send_intent(message)
    salary_plan = build_salary_wechat_plan(intent)
    started_ms = now_ms()
    record_step(
        run_id=run_id,
        step_name="finance_salary_wechat_plan",
        step_order=3,
        status_value="succeeded" if not intent.missing_fields else "blocked",
        provider="rules",
        resource_type="automation",
        resource_id="finance_salary_wechat_send",
        input_text=message,
        output_text=salary_plan,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "intent": intent.intent,
            "confidence": intent.confidence,
            "recipient_name": intent.recipient_name,
            "missing_fields": intent.missing_fields,
            "entrypoint": "chat_plan_execute",
        },
    )
    if intent.missing_fields:
        missing_text = "、".join(intent.missing_fields)
        answer = (
            "我先整理好了工资表企业微信发送计划，但还不能执行。\n"
            f"还需要补充：{missing_text}。\n"
            f"计划目标：{salary_plan['summary']}\n"
            "补充后我会生成工资表，并在聊天窗口让你确认接收对象和敏感数据。"
        )
        return {
            "answer": answer,
            "attachments": [],
            "approval_result": {
                "status": "waiting_confirmation",
                "status_label": "等待确认",
                "requires_recipient_confirmation": True,
                "requires_sensitive_data_confirmation": True,
            },
            "automation": {
                "type": "finance_salary_wechat_send",
                "status": "waiting_confirmation",
                "status_label": "等待确认",
                "workflow_id": "finance_salary_wechat_send",
                "execution_plan": salary_plan,
                "recipient_name": intent.recipient_name,
                "missing_fields": intent.missing_fields,
                "source_message": message,
            },
        }

    _emit(progress_callback, thread_id, "finance.salary_export", "正在生成工资表")
    step_started_ms = now_ms()
    salary_result = export_salary_workbook_from_erp(
        message=message,
        current_user=current_user,
        intent=intent.salary_intent,
        fallback_to_previous_month=True,
    )
    attachment: dict[str, Any] = {
        "type": "excel_file",
        "filename": salary_result.filename,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "size_bytes": len(salary_result.content),
        "metadata": salary_result.metadata,
    }
    artifact_id = save_generated_file(
        run_id=run_id,
        content=salary_result.content,
        artifact_type="excel_file",
        mime_type=attachment["mime_type"],
        filename=salary_result.filename,
        current_user=current_user,
        metadata=salary_result.metadata,
    )
    if artifact_id:
        attachment["metadata"] = {
            **attachment["metadata"],
            "artifact_id": artifact_id,
            "download_path": f"/files/{artifact_id}/download",
        }
    record_step(
        run_id=run_id,
        step_name="finance_salary_wechat_excel_export",
        step_order=4,
        status_value="succeeded",
        provider=salary_result.provider,
        resource_type="erp",
        resource_id="Salary Slip",
        input_text=message,
        output_text=salary_result.filename,
        duration_ms=elapsed_ms(step_started_ms),
        metadata={
            **salary_result.metadata,
            "artifact_id": artifact_id,
        },
    )

    _emit(progress_callback, thread_id, "finance.wechat_confirmation", "正在整理企业微信发送确认")
    dispatch = prepare_salary_wechat_dispatch(
        intent=intent,
        salary_result=salary_result,
        current_user=current_user,
        source="chat_plan_execute",
    )
    wechat_execution = build_wechat_prepare_confirmation_task(
        dispatch=dispatch,
        artifact_id=artifact_id,
        artifact_filename=salary_result.filename,
        current_user=current_user,
    )
    business_status = str(wechat_execution.get("status") or "waiting_wechat_confirmation")
    business_status_label = str(wechat_execution.get("status_label") or "等待确认")
    record_step(
        run_id=run_id,
        step_name="enterprise_wechat_confirmation_required",
        step_order=5,
        status_value=run_record_status_for_salary_wechat(business_status),
        provider=str(wechat_execution.get("executor_type") or "confirmation_required"),
        resource_type="enterprise_wechat",
        resource_id=str(intent.recipient_name or ""),
        input_text={
            "recipient_name": intent.recipient_name,
            "artifact_id": artifact_id,
        },
        output_text=wechat_execution.get("message"),
        duration_ms=0,
        metadata=wechat_execution,
    )
    fallback_note = _salary_period_fallback_note(salary_result.metadata)
    if business_status == "waiting_recipient_selection":
        answer = (
            f"{fallback_note}已生成 {salary_result.intent.period_label} 员工工资表 Excel，但企业微信接收对象还需要你选择。\n"
            f"文件：{salary_result.filename}\n"
            f"本次共 {len(salary_result.items)} 名员工，应发合计 "
            f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
            f"{salary_result.metadata['net_pay_total']:.2f}。\n"
            "请在下方候选列表里点选正确的人、群聊或部门，再确认发送。"
        )
    else:
        answer = (
            f"{fallback_note}已生成 {salary_result.intent.period_label} 员工工资表 Excel，并准备通过企业微信发送给“{intent.recipient_name}”。\n"
            f"本次共 {len(salary_result.items)} 名员工，应发合计 "
            f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
            f"{salary_result.metadata['net_pay_total']:.2f}。\n"
            f"文件：{salary_result.filename}\n"
            "请在下方确认企业微信接收对象和敏感数据。确认后由后端发送文件，不附带正文说明。"
        )
    return {
        "answer": answer,
        "attachments": [attachment],
        "approval_result": {
            "status": business_status,
            "status_label": business_status_label,
            "requires_recipient_confirmation": True,
            "requires_sensitive_data_confirmation": True,
            "confirmation_card": wechat_execution.get("confirmation_card"),
        },
        "automation": {
            "type": "finance_salary_wechat_send",
            "status": business_status,
            "status_label": business_status_label,
            "workflow_id": "finance_salary_wechat_send",
            "execution_plan": salary_plan,
            "recipient_name": intent.recipient_name,
            "missing_fields": intent.missing_fields,
            "source_message": message,
            "artifact_id": artifact_id,
            "filename": salary_result.filename,
            "download_path": f"/files/{artifact_id}/download" if artifact_id else None,
            "wechat_send": wechat_execution,
            "confirmation_card": wechat_execution.get("confirmation_card"),
        },
    }


def _run_salary_email_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    recipient = _extract_email_recipient(message)
    if not recipient:
        return {
            "answer": "我识别到你想通过邮箱发送工资表，但还没有看到收件邮箱。请补充邮箱地址。",
            "attachments": [],
            "approval_result": {
                "status": "waiting_clarification",
                "status_label": "等待补充邮箱",
                "requires_confirmation": True,
            },
            "automation": _external_action_automation(run_id=run_id, plan=plan, status="waiting_clarification"),
        }

    _emit(progress_callback, thread_id, "finance.salary_export", "正在生成工资表")
    step_started_ms = now_ms()
    salary_result = export_salary_workbook_from_erp(
        message=message,
        current_user=current_user,
        intent=recognize_salary_export_intent(message),
    )
    attachment: dict[str, Any] = {
        "type": "excel_file",
        "filename": salary_result.filename,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "size_bytes": len(salary_result.content),
        "metadata": salary_result.metadata,
    }
    artifact_id = save_generated_file(
        run_id=run_id,
        content=salary_result.content,
        artifact_type="excel_file",
        mime_type=attachment["mime_type"],
        filename=salary_result.filename,
        current_user=current_user,
        metadata=salary_result.metadata,
    )
    if artifact_id:
        attachment["metadata"] = {
            **attachment["metadata"],
            "artifact_id": artifact_id,
            "download_path": f"/files/{artifact_id}/download",
        }
    record_step(
        run_id=run_id,
        step_name="finance_salary_email_excel_export",
        step_order=4,
        status_value="succeeded",
        provider=salary_result.provider,
        resource_type="erp",
        resource_id="Salary Slip",
        input_text=message,
        output_text=salary_result.filename,
        duration_ms=elapsed_ms(step_started_ms),
        metadata={
            **salary_result.metadata,
            "artifact_id": artifact_id,
            "target_channel": "email",
        },
    )

    storage_reference = get_generated_file_storage_reference(str(artifact_id), current_user=current_user) if artifact_id else None
    email_confirmation = _send_email_plan(
        latest=storage_reference or {
            "id": artifact_id,
            "filename": salary_result.filename,
            "mime_type": attachment["mime_type"],
        },
        recipient=recipient,
        message=message,
        current_user=current_user,
    )
    answer = (
        f"已生成 {salary_result.intent.period_label} 员工工资表 Excel，并准备发送到邮箱 {recipient}。\n"
        f"文件：{salary_result.filename}\n"
        f"本次共 {len(salary_result.items)} 名员工，应发合计 "
        f"{salary_result.metadata['gross_pay_total']:.2f}，实发合计 "
        f"{salary_result.metadata['net_pay_total']:.2f}。\n"
        "请在邮箱发送确认卡里确认收件人和附件后再发送。"
    )
    return {
        "answer": answer,
        "attachments": [attachment],
        "approval_result": email_confirmation,
        "automation": {
            "type": "email_file_send",
            "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
            "run_id": run_id,
            "status": email_confirmation.get("status"),
            "status_label": email_confirmation.get("status_label"),
            "plan": plan,
            "recipient": recipient,
            "artifact_id": artifact_id,
            "filename": salary_result.filename,
            "download_path": f"/files/{artifact_id}/download" if artifact_id else None,
            "email_send": email_confirmation,
        },
    }


def _run_amazon_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    attachments: list[dict[str, Any]] | None = None,
    resume_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    skill_result = execute_skill(
        skill_id="operations_listing",
        payload={
            "message": message,
            "attachments": attachments or [],
            "metadata": {"run_id": run_id, "thread_id": thread_id},
        },
        current_user=current_user,
        source="chat",
    )
    draft = skill_result.platform_draft
    if draft is None:
        raise ValueError("Listing 草稿未生成。")
    answer = str(skill_result.answer or "已生成 Listing 草稿，等待运营确认后再继续 Amazon 填表。")
    attachments = []
    if draft:
        attachments.append(_attachment_from_platform_draft(draft))
    return {
        "answer": answer,
        "attachments": attachments,
        "approval_result": None,
        "automation": {
            "type": "amazon_listing_draft",
            "run_id": run_id,
            "plan": plan,
            "platform_draft": draft,
            "amazon_upload": {
                "status": "waiting_confirmation",
                "manual_final_publish_required": True,
            },
        },
    }


def _run_message_send_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    plan: dict[str, Any],
    run_id: str,
    resume_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_channel = str(plan.get("target_channel") or "")
    recipient = _extract_email_recipient(message) if target_channel == "email" or _contains(message, ["邮箱", "email", "mail"]) else extract_wechat_recipient(message)
    if not recipient:
        return {
            "answer": "请先补充接收对象。",
            "attachments": [],
            "approval_result": None,
            "automation": {"type": "message_send", "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID, "plan": plan},
        }
    latest = get_latest_generated_file_for_thread(thread_id=thread_id, current_user=current_user, allowed_types={"excel_file", "word_file", "docx_file", "report_file"})
    if latest is None:
        return {
            "answer": "当前会话还没有可发送的文件，请先生成或上传文件。",
            "attachments": [],
            "approval_result": None,
            "automation": {"type": "message_send", "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID, "plan": plan},
        }
    if _contains(message, ["企业微信", "微信"]):
        execution = build_enterprise_wechat_file_confirmation_task(
            artifact_id=str(latest["id"]),
            artifact_filename=str(latest.get("filename") or "文件"),
            recipient_name=recipient,
            current_user=current_user,
            source_message=message,
            source_workflow_id="chat_plan_execute",
            mime_type=str(latest.get("mime_type") or "application/octet-stream"),
            requires_sensitive_confirmation=True,
        )
    else:
        execution = _send_email_plan(
            latest=latest,
            recipient=recipient,
            message=message,
            current_user=current_user,
        )
    attachment = _attachment_from_storage_reference(latest)
    return {
        "answer": str(execution.get("message") or "已生成发送确认卡，请确认后再发送。"),
        "attachments": [attachment],
        "approval_result": execution,
        "automation": {
            "type": "message_send",
            "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
            "run_id": run_id,
            "plan": plan,
            "execution": execution,
        },
    }


def _run_file_processing_plan(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    attachments: list[dict[str, Any]],
    plan: dict[str, Any],
    run_id: str,
    resume_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = _normalize_input_files(attachments)
    if not parsed:
        return {
            "answer": "请先上传 Excel、Word、PDF 或图片文件，再让我处理。",
            "attachments": [],
            "approval_result": None,
            "automation": {"type": "file_processing", "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID, "plan": plan},
        }
    result = analyze_finance_report_files(files=parsed, instruction=message, output_format="word")
    saved_id = save_generated_file(
        run_id=run_id,
        content=result.content,
        filename=result.filename,
        artifact_type="word_file",
        mime_type=result.mime_type,
        current_user=current_user,
        metadata=result.metadata,
    )
    attachment = {
        "type": "word_file",
        "filename": result.filename,
        "mime_type": result.mime_type,
        "size_bytes": len(result.content),
        "content_base64": base64.b64encode(result.content).decode("ascii"),
        "metadata": {
            **result.metadata,
            "artifact_id": saved_id,
            "download_path": f"/files/{saved_id}/download" if saved_id else None,
        },
    }
    return {
        "answer": result.answer or "文件已处理完成。",
        "attachments": [attachment],
        "approval_result": None,
        "automation": {
            "type": "file_processing",
            "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
            "run_id": run_id,
            "plan": plan,
        },
    }


def _send_email_plan(
    *,
    latest: dict[str, Any],
    recipient: str,
    message: str,
    current_user: dict,
) -> dict[str, Any]:
    artifact_id = str(latest.get("id") or "").strip()
    filename = str(latest.get("filename") or "generated_file")
    download_path = f"/files/{artifact_id}/download" if artifact_id else None
    return {
        "type": "email_file_send_confirmation",
        "status": "waiting_email_confirmation",
        "status_label": "等待邮箱发送确认",
        "message": "已生成邮箱发送确认卡，请确认收件人和附件后再发送。",
        "channel": "email",
        "recipient": recipient,
        "subject": message[:120] or "业务文件",
        "body": "",
        "requires_confirmation": True,
        "requires_sensitive_confirmation": True,
        "llm_direct_execution_allowed": False,
        "artifact": {
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": download_path,
            "mime_type": str(latest.get("mime_type") or "application/octet-stream"),
        },
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "filename": filename,
                "download_path": download_path,
                "mime_type": str(latest.get("mime_type") or "application/octet-stream"),
            }
        ],
    }


def _check_permissions(*, current_user: dict, plan: dict[str, Any], message: str) -> dict[str, Any]:
    if current_user.get("role") != "admin" and not is_valid_position(current_user.get("position")):
        return {"ok": False, "message": "当前账号未绑定岗位，无法执行复杂自动化。"}
    kind = plan.get("kind")
    if kind == "external_action":
        business_object = str(plan.get("business_object") or "")
        target_channel = str(plan.get("target_channel") or "")
        if business_object in {"salary_table", "finance_report", "finance_package", "employee_table"}:
            if current_user.get("role") != "admin" and current_user.get("position") != "finance":
                return {"ok": False, "message": "这个外部动作涉及财务或员工敏感数据，当前账号没有权限。"}
        if business_object in {"listing_draft", "inventory_table"} or target_channel == "amazon_seller_central":
            if current_user.get("role") != "admin" and current_user.get("position") != "operations":
                return {"ok": False, "message": "这个外部动作属于运营岗位，当前账号没有权限。"}
        if business_object == "customer_reply_draft":
            if current_user.get("role") != "admin" and current_user.get("position") != "customer_service":
                return {"ok": False, "message": "这个外部动作属于客服岗位，当前账号没有权限。"}
        return {"ok": True, "message": "外部动作权限检查通过。"}
    if kind == "finance" and current_user.get("role") != "admin" and current_user.get("position") != "finance":
        return {"ok": False, "message": "这个任务属于财务岗位，当前账号没有权限。"}
    if kind == "amazon_listing" and current_user.get("role") != "admin" and current_user.get("position") != "operations":
        return {"ok": False, "message": "这个任务属于运营岗位，当前账号没有权限。"}
    return {"ok": True, "message": "权限检查通过。"}


def _run_amazon_listing_to_chat_attachment(draft: dict[str, Any]) -> dict[str, Any]:
    return _attachment_from_platform_draft(draft)


def _attachment_from_platform_draft(draft: dict[str, Any]) -> dict[str, Any]:
    content = draft.get("content") if isinstance(draft.get("content"), dict) else {}
    filename = str(content.get("filename") or draft.get("title") or "listing_draft.xlsx")
    content_bytes = str(content.get("raw_text") or "").encode("utf-8")
    return {
        "type": "json",
        "filename": filename,
        "mime_type": "application/json",
        "size_bytes": len(content_bytes),
        "content_base64": base64.b64encode(content_bytes).decode("ascii") if content_bytes else None,
        "metadata": {
            "platform_draft_id": draft.get("id"),
            "download_path": None,
        },
    }


def _attachment_from_storage_reference(storage_reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": storage_reference.get("artifact_type") or "file",
        "filename": storage_reference.get("filename"),
        "mime_type": storage_reference.get("mime_type"),
        "size_bytes": storage_reference.get("size_bytes") or 0,
        "metadata": {
            "artifact_id": storage_reference.get("id"),
            "download_path": f"/files/{storage_reference.get('id')}/download",
        },
    }


def _attachment_to_chat_attachment(item: Any) -> dict[str, Any]:
    content = getattr(item, "content", None)
    if isinstance(content, bytes):
        content_base64 = base64.b64encode(content).decode("ascii")
        size_bytes = len(content)
    else:
        content_base64 = None
        size_bytes = 0
    return {
        "type": "excel_file",
        "filename": getattr(item, "filename", None),
        "mime_type": getattr(item, "mime_type", None),
        "size_bytes": size_bytes,
        "content_base64": content_base64,
        "metadata": getattr(item, "metadata", {}) or {},
    }


def _normalize_input_files(items: list[dict[str, Any]]) -> list[FinanceReportInputFile]:
    files: list[FinanceReportInputFile] = []
    for item in items:
        filename = str(item.get("filename") or "file")
        content = item.get("content")
        content_base64 = item.get("content_base64")
        if isinstance(content, bytes):
            raw = content
        elif isinstance(content_base64, str):
            try:
                raw = base64.b64decode(content_base64)
            except Exception:
                continue
        else:
            continue
        files.append(FinanceReportInputFile(filename=filename, content=raw))
    return files


def _needs_sensitive_confirmation(storage_reference: dict[str, Any]) -> bool:
    name = str(storage_reference.get("filename") or "").lower()
    return any(keyword in name for keyword in ["工资", "salary", "财务", "invoice", "payment"])


def _read_storage_path(storage_reference: dict[str, Any]) -> bytes:
    path = storage_reference.get("storage_path")
    if not path:
        return b""
    from pathlib import Path
    return Path(str(path)).read_bytes()


def _contains(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _looks_like_resume_request(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["继续上一次计划", "继续上次计划", "继续", "恢复上一次计划", "重试上一次计划"])


def _is_salary_finance_task(text: str) -> bool:
    return _contains(text, ["工资", "薪资", "报表", "财务"])


def _is_amazon_listing_task(text: str) -> bool:
    return _contains(text, ["amazon", "seller central", "listing", "亚马逊", "上架"])


def _business_object_label(value: str) -> str:
    labels = {
        "salary_table": "工资表",
        "finance_report": "财务报表",
        "finance_package": "财务资料包",
        "inventory_table": "库存表",
        "employee_table": "员工表",
        "listing_draft": "Listing 草稿",
        "customer_reply_draft": "客服回复草稿",
        "latest_file": "最近生成文件",
    }
    return labels.get(value, value or "业务文件")


def _external_action_label(value: str) -> str:
    labels = {
        "send_file": "发送文件",
        "send_message": "发送消息",
        "fill_web_form": "填写外部表单",
        "upload_file": "上传文件",
        "write_draft": "写入外部草稿",
    }
    return labels.get(value, value or "执行外部动作")


def _extract_email_recipient(message: str) -> str | None:
    match = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", message or "")
    return match.group(0) if match else None


def _salary_period_fallback_note(metadata: dict[str, Any]) -> str:
    if not isinstance(metadata, dict) or not metadata.get("period_fallback_applied"):
        return ""
    from_label = str(metadata.get("period_fallback_from") or "本月")
    to_label = str(metadata.get("period_fallback_to") or "上个月")
    return f"{from_label} 暂未查到工资单，我已自动改用 {to_label}。\n"


def _external_action_automation(*, run_id: str, plan: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "type": "external_action",
        "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
        "run_id": run_id,
        "status": status,
        "plan": plan,
        "external_action_type": plan.get("external_action_type"),
        "target_channel": plan.get("target_channel"),
        "business_object": plan.get("business_object"),
        "requires_confirmation": True,
    }


def _with_external_action_metadata(result: dict[str, Any], *, plan: dict[str, Any]) -> dict[str, Any]:
    automation = result.get("automation") if isinstance(result.get("automation"), dict) else {}
    result["automation"] = {
        **automation,
        "external_action_gateway": {
            "external_action_type": plan.get("external_action_type"),
            "target_channel": plan.get("target_channel"),
            "business_object": plan.get("business_object"),
            "data_source": plan.get("data_source"),
            "requires_confirmation": True,
        },
        "plan": automation.get("plan") or plan,
    }
    return result


def _deny_plan(message: str) -> dict[str, Any]:
    return {
        "kind": "deny",
        "requires_clarification": False,
        "confidence": 1.0,
        "reason": message,
        "steps": [],
        "expected_outputs": [],
        "required_fields": [],
        "deny_message": message,
    }


def _result(*, thread_id: str, answer: str, plan: dict[str, Any], run_id: str, risk_level: str) -> dict[str, Any]:
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": "chat_plan_execute",
        "risk_level": risk_level,
        "erp_references": [],
        "attachments": [],
        "approval_result": None,
        "automation": {
            "type": "chat_plan_execute",
            "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
            "run_id": run_id,
            "plan": plan,
        },
    }


def _record_plan_step(
    run_id: str,
    order: int,
    name: str,
    status_value: str,
    provider: str,
    resource_id: str,
    input_text: Any,
    output_text: Any,
) -> None:
    record_step(
        run_id=run_id,
        step_name=name,
        step_order=order,
        status_value=status_value,
        provider=provider,
        resource_type="automation",
        resource_id=resource_id,
        input_text=input_text,
        output_text=output_text,
        duration_ms=0,
        metadata={"workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID},
    )


def _emit(progress_callback: ProgressCallback | None, thread_id: str, step_key: str, label: str, status: str = "running", detail: str | None = None) -> None:
    if progress_callback is None:
        return
    progress_callback(
        {
            "thread_id": thread_id,
            "workflow_id": CHAT_PLAN_EXECUTE_WORKFLOW_ID,
            "step_key": step_key,
            "label": label,
            "status": status,
            "detail": detail,
        }
    )
