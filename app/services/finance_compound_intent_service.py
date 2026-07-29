from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Literal


FinanceCompoundOutput = Literal["finance_monthly_report", "finance_salary_export"]

FINANCE_REPORT_OUTPUT = "finance_monthly_report"
FINANCE_SALARY_OUTPUT = "finance_salary_export"
FINANCE_COMPOUND_INTENT = "finance_compound_report_generation"

FINANCE_REPORT_RESOURCES = ("GL Entry", "Payment Entry", "Sales Invoice", "Purchase Invoice")
FINANCE_SALARY_RESOURCES = ("Salary Slip",)

OUTPUT_LABELS = {
    FINANCE_REPORT_OUTPUT: "财务报表",
    FINANCE_SALARY_OUTPUT: "员工工资表",
}


@dataclass(frozen=True)
class FinanceCompoundIntent:
    intent: str
    outputs: tuple[FinanceCompoundOutput, ...]
    period_label: str
    start_date: date
    end_date: date
    merge_requested: bool
    email_requested: bool
    wechat_requested: bool
    confidence: float
    matched_keywords: tuple[str, ...]

    @property
    def requested_erp_resources(self) -> tuple[str, ...]:
        resources: list[str] = []
        if FINANCE_REPORT_OUTPUT in self.outputs:
            resources.extend(FINANCE_REPORT_RESOURCES)
        if FINANCE_SALARY_OUTPUT in self.outputs:
            resources.extend(FINANCE_SALARY_RESOURCES)
        return tuple(dict.fromkeys(resources))

    @property
    def output_labels(self) -> tuple[str, ...]:
        return tuple(OUTPUT_LABELS[output] for output in self.outputs)


def recognize_finance_compound_intent(
    message: str,
    *,
    today: date | None = None,
) -> FinanceCompoundIntent:
    normalized = " ".join((message or "").strip().split())
    lowered = normalized.lower()
    current_day = today or date.today()
    start_date, end_date, period_label = _resolve_period(normalized, current_day)
    matched_keywords: list[str] = []

    has_salary = _contains_any(lowered, _salary_keywords(), matched_keywords)
    has_report = _looks_like_finance_report_request(lowered, matched_keywords)
    wants_generation = _contains_any(lowered, _generation_keywords(), matched_keywords)
    merge_requested = _contains_any(lowered, _merge_keywords(), matched_keywords)
    email_requested = _contains_any(lowered, _email_keywords(), matched_keywords)
    wechat_requested = _contains_any(lowered, _wechat_keywords(), matched_keywords)

    outputs: list[FinanceCompoundOutput] = []
    if has_report:
        outputs.append(FINANCE_REPORT_OUTPUT)
    if has_salary:
        outputs.append(FINANCE_SALARY_OUTPUT)
    outputs = _sort_outputs_by_message_order(outputs, lowered)

    confidence = 0.42
    if has_report:
        confidence += 0.3
    if has_salary:
        confidence += 0.18
    if wants_generation:
        confidence += 0.08
    if len(outputs) > 1:
        confidence += 0.08

    # 单纯工资表仍走原工资表 Skill；只要出现财务报表，才进入本复合/报表生成链路。
    if FINANCE_REPORT_OUTPUT not in outputs:
        return FinanceCompoundIntent(
            intent="unknown",
            outputs=tuple(outputs),
            period_label=period_label,
            start_date=start_date,
            end_date=end_date,
            merge_requested=merge_requested,
            email_requested=email_requested,
            wechat_requested=wechat_requested,
            confidence=round(min(confidence, 0.89), 2),
            matched_keywords=tuple(dict.fromkeys(matched_keywords)),
        )

    return FinanceCompoundIntent(
        intent=FINANCE_COMPOUND_INTENT,
        outputs=tuple(outputs),
        period_label=period_label,
        start_date=start_date,
        end_date=end_date,
        merge_requested=merge_requested,
        email_requested=email_requested,
        wechat_requested=wechat_requested,
        confidence=round(min(confidence, 0.98), 2),
        matched_keywords=tuple(dict.fromkeys(matched_keywords)),
    )


def finance_compound_requested_resources(intent: FinanceCompoundIntent) -> list[str]:
    return list(intent.requested_erp_resources)


def should_handle_finance_compound_generation(intent: FinanceCompoundIntent) -> bool:
    return intent.intent == FINANCE_COMPOUND_INTENT and FINANCE_REPORT_OUTPUT in intent.outputs


def _looks_like_finance_report_request(lowered: str, matched_keywords: list[str]) -> bool:
    specific_keywords = [
        "财务报表",
        "财务报告",
        "财务月报",
        "月度财务",
        "财报",
        "经营汇总",
        "经营报表",
        "经营分析",
        "经营月报",
        "经营情况",
        "公司情况",
    ]
    if _contains_any(lowered, specific_keywords, matched_keywords):
        return True

    generic_report = _contains_any(lowered, ["报表", "月报", "汇总表"], matched_keywords)
    finance_context = _contains_any(
        lowered,
        ["财务", "经营", "利润", "收入", "支出", "总账", "收付款", "销售发票", "采购发票"],
        matched_keywords,
    )
    return generic_report and finance_context


def _salary_keywords() -> list[str]:
    return [
        "工资",
        "工资表",
        "工资单",
        "薪资",
        "薪资表",
        "薪水",
        "薪水表",
        "薪酬",
        "薪酬表",
        "payroll",
        "salary",
        "salary report",
    ]


def _generation_keywords() -> list[str]:
    return ["生成", "导出", "下载", "整理", "做一份", "做一个", "出一份", "excel", "xlsx", "附件", "表"]


def _merge_keywords() -> list[str]:
    return [
        "合并成一张",
        "合成一张",
        "汇成一张",
        "汇总成一张",
        "放到一张",
        "放在一张",
        "合并到一个",
        "放到一个excel",
        "一个excel",
        "一个文件",
        "合并文件",
    ]


def _email_keywords() -> list[str]:
    return ["邮箱", "邮件", "email", "e-mail", "发到我邮箱", "发送到邮箱"]


def _wechat_keywords() -> list[str]:
    return ["微信", "企业微信", "企微", "wechat", "weixin"]


def _contains_any(text: str, keywords: list[str], matched_keywords: list[str]) -> bool:
    found = False
    for keyword in keywords:
        if keyword and keyword in text:
            matched_keywords.append(keyword)
            found = True
    return found


def _sort_outputs_by_message_order(
    outputs: list[FinanceCompoundOutput],
    lowered: str,
) -> list[FinanceCompoundOutput]:
    if len(outputs) <= 1:
        return outputs

    indexes = {
        FINANCE_REPORT_OUTPUT: _first_index(lowered, ["财务报表", "财务报告", "财报", "经营汇总", "经营报表", "报表", "月报"]),
        FINANCE_SALARY_OUTPUT: _first_index(lowered, _salary_keywords()),
    }
    return sorted(outputs, key=lambda output: indexes.get(output, 999999))


def _first_index(text: str, keywords: list[str]) -> int:
    indexes = [text.find(keyword) for keyword in keywords if keyword in text]
    return min(indexes) if indexes else 999999


def _resolve_period(text: str, today: date) -> tuple[date, date, str]:
    range_to_today = re.search(
        r"从\s*([0-9]{4}[-年/.][0-9]{1,2}[-月/.][0-9]{1,2}日?|[0-9]{1,2}月[0-9]{1,2}日?)\s*(?:到|至|-|~)?\s*(?:现在|今天|当前|至今)",
        text,
    )
    if range_to_today:
        start = _parse_date_fragment(range_to_today.group(1), today)
        if start is not None:
            return start, today, _range_label(start, today)

    explicit_range = re.search(
        r"([0-9]{4}[-年/.][0-9]{1,2}[-月/.][0-9]{1,2}日?|[0-9]{1,2}月[0-9]{1,2}日?)\s*(?:到|至|-|~)\s*([0-9]{4}[-年/.][0-9]{1,2}[-月/.][0-9]{1,2}日?|[0-9]{1,2}月[0-9]{1,2}日?)",
        text,
    )
    if explicit_range:
        start = _parse_date_fragment(explicit_range.group(1), today)
        end = _parse_date_fragment(explicit_range.group(2), today)
        if start is not None and end is not None:
            if end < start:
                start, end = end, start
            return start, end, _range_label(start, end)

    month_match = re.search(r"(20\d{2})[-年/.](0?[1-9]|1[0-2])", text)
    if month_match:
        return _month_range(int(month_match.group(1)), int(month_match.group(2)))

    chinese_month_match = re.search(r"(?<![0-9])(?<!\d)(0?[1-9]|1[0-2])月(?![0-9一二三四五六七八九十])", text)
    if chinese_month_match and "下个月" not in text and "上个月" not in text:
        return _month_range(today.year, int(chinese_month_match.group(1)))

    if any(keyword in text for keyword in ["上个月", "上月", "last month"]):
        year = today.year
        month = today.month - 1
        if month == 0:
            year -= 1
            month = 12
        return _month_range(year, month)

    if any(keyword in text for keyword in ["下个月", "下月", "next month"]):
        year = today.year
        month = today.month + 1
        if month == 13:
            year += 1
            month = 1
        return _month_range(year, month)

    return _month_range(today.year, today.month)


def _parse_date_fragment(raw_value: str, today: date) -> date | None:
    text = raw_value.strip().rstrip("日")
    full_match = re.fullmatch(r"(20\d{2})[-年/.](0?[1-9]|1[0-2])[-月/.](0?[1-9]|[12][0-9]|3[01])", text)
    if full_match:
        year = int(full_match.group(1))
        month = int(full_match.group(2))
        day = int(full_match.group(3))
        return _safe_date(year, month, day)

    short_match = re.fullmatch(r"(0?[1-9]|1[0-2])月(0?[1-9]|[12][0-9]|3[01])", text)
    if short_match:
        month = int(short_match.group(1))
        day = int(short_match.group(2))
        return _safe_date(today.year, month, day)

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _month_range(year: int, month: int) -> tuple[date, date, str]:
    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    return start_date, end_date, f"{year}年{month:02d}月"


def _range_label(start_date: date, end_date: date) -> str:
    if start_date.year == end_date.year and start_date.month == end_date.month:
        return f"{start_date.year}年{start_date.month:02d}月{start_date.day:02d}日-{end_date.day:02d}日"
    return f"{start_date.isoformat()} 至 {end_date.isoformat()}"
