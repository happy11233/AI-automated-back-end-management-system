"""Shared, side-effect-free intent signals before capability selection."""
from __future__ import annotations

import re
from dataclasses import dataclass

_QUESTIONS = re.compile(r"谁|到哪|什么|怎么|怎样|如何|为什么|哪里|哪儿|哪个|哪位|多少|多久|是否|要不要|需不需要|应不应该|该不该|(?:吗|呢|么|[？?])\s*$|\b(?:how|what|who|where|why|when)\b", re.I)
_POLICY_TERMS = ("请假", "休假", "年假", "病假", "事假", "调休", "报销", "审批人", "负责人", "制度", "规定", "政策", "规则", "流程", "规范", "手续", "假期", "权限", "申请条件", "操作方法", "教程", "加班")
_ACTIONS = r"发送|发给|发到|转发|传给|导出|生成|上传|保存|提交|创建|填写|录入|申请|回复|处理|制作|做一份|整理|下载|写入|合并|打开|接管|导入|发我"
_COMMAND = re.compile(
    r"(?:请(?:AI\s*|自动)?(?=(?:" + _ACTIONS + r"))|帮我|替我|请你|麻烦(?:你)?|请问|能否|能不能|可不可以|可以)"
    r".{0,30}?(?:" + _ACTIONS + r")|(?:^|[，,。；;]|然后|接着|最后|再|并)(?:请|先)?"
    r"(?:把|将).{0,60}?(?:" + _ACTIONS + r")|^(?:请问)?能(?=(?:把|将|" + _ACTIONS + r")).{0,60}?(?:" + _ACTIONS + r")|^(?:请|先|只|仅)?(?:自动)?(?:" + _ACTIONS + r")", re.I,
)

_NEGATED = re.compile(r"(?:不要|别|不用|无需|不必|禁止|不能|暂不|不需要|不允许|停止|取消).{0,8}?(?:" + _ACTIONS + r")|\b(?:do not|don't|never|cancel)\s+(?:send|submit|upload|create|export)", re.I)
_DATA = re.compile(r"工资|薪资|发票|总账|收付款|销售订单|订单|库存|sku|物流|客户|商品|利润|收入|销售额|工单|erp", re.I)
_READ = re.compile(r"^(?:请|帮我|帮忙|只)?(?:查询|查一下|查|查看|看看|看|列出|搜索)|\b(?:show|query|list|lookup)\b", re.I)
_SOCIAL = {"你好", "您好", "hi", "hello", "在吗", "早上好", "下午好", "晚上好", "谢谢", "感谢", "好的谢谢", "再见", "拜拜", "你是谁"}


def instruction_text(message: str) -> str:
    text = " ".join((message or "").strip().split())
    # Customer quotes are task input, not top-level authorization.
    return re.sub(r'“[^”]*”|「[^」]*」|『[^』]*』|"[^"\n]*"', ' [引用内容] ', text)


def is_action_negated(message: str) -> bool:
    return bool(_NEGATED.search(instruction_text(message)))


def has_execution_request(message: str) -> bool:
    text = instruction_text(message)
    # Interrogative arguments name missing knowledge, not a concrete target.
    if re.search(r"(?:发给|发送给|发送到|发到|交给|提交给|找|由).{0,3}(?:谁|哪)|(?:应该|应当|要不要|是否|怎么|如何).{0,12}(?:发给|发送|提交|生成|导出)", text):
        return False
    # Evaluate clauses separately: "不要发送，只生成" still permits generation.
    for clause in re.split(r"[，,。；;]|然后|接着|最后|再", text):
        if _NEGATED.search(clause):
            continue
        command = _COMMAND.search(clause.strip())
        if not command:
            continue
        question = _QUESTIONS.search(clause[command.start():])
        if question:
            # Questions in an earlier customer quote cannot override a later command.
            question_offset = question.start() + command.start()
        else:
            question_offset = len(clause)
        if question and question_offset < command.end() and not re.match(r"^(?:请问)?(?:能否|能不能|可不可以|可以|能)", clause.strip()):
            continue
        if question and not (re.search(r"帮我|替我|请你|麻烦|(?:把|将).*(?:" + _ACTIONS + r")", clause) or re.match(r"^(?:请问)?(?:能否|能不能|可不可以|可以|能)", clause.strip())):
            return False
        return True
    return bool(re.search(r"^(?:please\s+)?(?:send|export|generate|create|upload|save|reply)\b", text, re.I) and not _NEGATED.search(text))


def knowledge_action_parts(message: str) -> tuple[str, str] | None:
    text = instruction_text(message)
    match = re.search(r"(?:[，,；;]\s*)?(?:然后|接着|再|并(?:且)?|最后)\s*(.+)$", text)
    if not match:
        return None
    query, action = text[:match.start()].strip(" ，,；;"), match.group(1).strip()
    if any(term in query for term in _POLICY_TERMS) and has_execution_request(action):
        return re.sub(r"^(?:先|请先|帮我先)?(?:查询|查一下|查询一下|查)?", "", query).strip(), action
    return None


def is_information_request(message: str) -> bool:
    text = instruction_text(message).lower()
    if not text or knowledge_action_parts(text):
        return False
    if has_execution_request(text):
        return False
    return bool(_QUESTIONS.search(text) or any(term in text for term in _POLICY_TERMS)
                or (_READ.search(text) and _DATA.search(text)))


def is_policy_information_request(message: str) -> bool:
    text = instruction_text(message).lower()
    if not is_information_request(text):
        return False
    return any(term in text for term in _POLICY_TERMS) or bool(re.search(r"(?:邮箱|电话|联系人).*(?:谁|什么|哪)|(?:谁|什么|哪).*(?:邮箱|电话|联系人)", text)) or bool(re.search(
        r"(?:发|发送|转发|传|交|提交|申请|审批|处理|导出|生成|上传|保存).{0,16}(?:给谁|找谁|到哪|怎么|如何|是否|要不要|吗|[？?])|(?:怎么|如何).{0,25}(?:生成|导出|发送|上传|回复)|(?:退款|退货).{0,8}(?:流程|规定|多久|多久到账)", text))


def is_data_query(message: str) -> bool:
    text = instruction_text(message)
    return not has_execution_request(text) and not is_policy_information_request(text) and bool(_DATA.search(text)) and bool(_READ.search(text) or _QUESTIONS.search(text))


def refund_case_kind(message: str) -> str | None:
    """Distinguish order refund eligibility from an instruction to start a refund."""
    text = instruction_text(message).lower()
    if re.search(r"退款规则|退款政策|退款流程|退款多久到账|refund policy|refund timeline", text):
        return None
    if re.search(r"能不能退款|是否可以退款|可不可以退款|可以退(?:款)?吗|能退(?:款)?吗|是否可退|退款资格|符合退款条件|"
                 r"\b(?:can i|may i) (?:get a |request a )?refund\b|\b(?:is|am) .*\b(?:refundable|eligible for (?:a )?refund)\b", text):
        return "eligibility"
    if re.search(r"申请退款|我要退款|给我退款|帮我退款|取消订单退款|退钱|\b(?:please |i want to |i'd like to )?(?:request a |get a )?refund (?:my |this )?order\b", text):
        return "application"
    return None


def is_social_request(message: str) -> bool:
    return re.sub(r"[\s，,。！!？?]+", "", (message or "").lower()) in _SOCIAL


def is_unsupported_leave_action(message: str) -> bool:
    text = instruction_text(message)
    # Generating an application draft is not the same capability as submitting it.
    submitting = bool(re.search(r"(?:提交|审批|自动处理).{0,20}(?:请假|休假|年假|病假|事假|调休|报销)|(?:帮我|替我|请).{0,8}申请(?:请假|休假|年假|病假|事假|调休|报销)", text))
    return submitting and has_execution_request(text)


@dataclass(frozen=True)
class IntentContract:
    route: str
    evidence_required: bool
    capability_id: str | None
    missing_fields: tuple[str, ...] = ()


def contract_for_action(action: str) -> IntentContract:
    if action in {"rag_query", "policy"}:
        return IntentContract("rag", True, "knowledge.search")
    if action in {"erp_query", "order_query"}:
        return IntentContract("query", True, action)
    if action in {"chitchat", "ask_clarification", "deny"}:
        return IntentContract(action, False, None)
    return IntentContract("automation", True, action)
