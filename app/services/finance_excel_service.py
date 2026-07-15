from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Side, Border
from openpyxl.utils import get_column_letter

from app.llm import chat


ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
MAX_EXCEL_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_ROWS_PER_SHEET = 2000
MAX_PROMPT_ROWS_PER_SHEET = 12


@dataclass
class FinanceExcelTransformResult:
    filename: str
    content: bytes
    metadata: dict[str, Any]


def transform_finance_excel(
    *,
    source_filename: str,
    content: bytes,
    instruction: str,
) -> FinanceExcelTransformResult:
    suffix = Path(source_filename or "").suffix.lower()
    if suffix not in ALLOWED_EXCEL_EXTENSIONS:
        raise ValueError("只支持上传 .xlsx 或 .xls 文件。")

    if len(content) > MAX_EXCEL_BYTES:
        raise ValueError("Excel 文件不能超过 8MB。")

    sheets = _read_excel_sheets(content, suffix)
    if not sheets:
        raise ValueError("Excel 文件里没有可读取的 sheet。")

    normalized_instruction = (
        instruction.strip()
        or "请按财务复核要求整理表格，生成数值汇总，并指出需要人工复核的异常。"
    )
    sheet_summaries = _build_sheet_summaries(sheets)
    ai_suggestion = _build_ai_suggestion(
        instruction=normalized_instruction,
        source_filename=source_filename,
        sheets=sheets,
        sheet_summaries=sheet_summaries,
    )
    workbook = _build_output_workbook(
        source_filename=source_filename,
        instruction=normalized_instruction,
        sheets=sheets,
        sheet_summaries=sheet_summaries,
        ai_suggestion=ai_suggestion,
    )

    output = BytesIO()
    workbook.save(output)
    output_content = output.getvalue()

    safe_stem = _safe_filename(Path(source_filename).stem or "finance_excel")
    output_filename = f"{safe_stem}_ai_finance_result.xlsx"

    return FinanceExcelTransformResult(
        filename=output_filename,
        content=output_content,
        metadata={
            "source_filename": source_filename,
            "output_filename": output_filename,
            "sheet_count": len(sheets),
            "total_rows": sum(summary["row_count"] for summary in sheet_summaries),
            "total_columns": sum(summary["column_count"] for summary in sheet_summaries),
            "instruction_preview": normalized_instruction[:500],
            "output_bytes": len(output_content),
        },
    )


def _read_excel_sheets(content: bytes, suffix: str) -> dict[str, pd.DataFrame]:
    try:
        engine = "xlrd" if suffix == ".xls" else "openpyxl"
        raw_sheets = pd.read_excel(
            BytesIO(content),
            sheet_name=None,
            dtype=object,
            engine=engine,
        )
    except Exception as error:
        raise ValueError(f"Excel 文件读取失败：{error}") from error

    sheets: dict[str, pd.DataFrame] = {}
    for name, frame in raw_sheets.items():
        cleaned = frame.dropna(how="all")
        cleaned = cleaned.dropna(axis=1, how="all")
        cleaned = cleaned.fillna("")
        sheets[str(name)[:31] or "Sheet"] = cleaned

    return sheets


def _build_sheet_summaries(sheets: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for sheet_name, frame in sheets.items():
        numeric_columns = []
        for column in frame.columns:
            numeric_values = pd.to_numeric(frame[column], errors="coerce")
            numeric_count = int(numeric_values.notna().sum())
            if numeric_count == 0:
                continue

            numeric_columns.append(
                {
                    "column": str(column),
                    "count": numeric_count,
                    "sum": float(numeric_values.sum()),
                    "mean": float(numeric_values.mean()),
                    "min": float(numeric_values.min()),
                    "max": float(numeric_values.max()),
                }
            )

        summaries.append(
            {
                "sheet_name": sheet_name,
                "row_count": int(len(frame)),
                "column_count": int(len(frame.columns)),
                "columns": [str(column) for column in frame.columns],
                "numeric_columns": numeric_columns,
            }
        )

    return summaries


def _build_ai_suggestion(
    *,
    instruction: str,
    source_filename: str,
    sheets: dict[str, pd.DataFrame],
    sheet_summaries: list[dict[str, Any]],
) -> str:
    prompt = _build_ai_prompt(
        instruction=instruction,
        source_filename=source_filename,
        sheets=sheets,
        sheet_summaries=sheet_summaries,
    )

    try:
        return str(chat(prompt)).strip()
    except Exception as error:
        return (
            "AI 建议生成失败，已先输出程序整理结果。\n"
            f"失败原因：{error}\n"
            "人工复核建议：检查数值列总额、空值行、重复单号、异常负数、币种和期间是否符合本次处理要求。"
        )


def _build_ai_prompt(
    *,
    instruction: str,
    source_filename: str,
    sheets: dict[str, pd.DataFrame],
    sheet_summaries: list[dict[str, Any]],
) -> str:
    samples: list[str] = []
    for sheet_name, frame in sheets.items():
        sample_rows = frame.head(MAX_PROMPT_ROWS_PER_SHEET).astype(str).to_dict("records")
        samples.append(
            f"Sheet: {sheet_name}\n"
            f"Columns: {', '.join(str(column) for column in frame.columns)}\n"
            f"Sample rows: {sample_rows}"
        )

    return f"""你是跨境电商企业内部财务 AI 助手。
请只围绕财务岗位可见数据做表格整理建议，不要输出越权内容。

源文件：{source_filename}
财务处理要求：{instruction}

表格概览：
{sheet_summaries}

样例数据：
{chr(10).join(samples)}

请输出：
1. 本次新 Excel 应如何使用
2. 关键汇总指标应该重点看哪些列
3. 可能的异常和复核点
4. 如果要继续生成工资/利润/费用分析表，下一步需要补充哪些字段
"""


def _build_output_workbook(
    *,
    source_filename: str,
    instruction: str,
    sheets: dict[str, pd.DataFrame],
    sheet_summaries: list[dict[str, Any]],
    ai_suggestion: str,
) -> Workbook:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "处理摘要"

    _write_summary_sheet(
        summary_sheet,
        source_filename=source_filename,
        instruction=instruction,
        sheet_summaries=sheet_summaries,
    )
    _write_numeric_summary_sheet(workbook, sheet_summaries)
    _write_ai_suggestion_sheet(workbook, ai_suggestion)

    used_titles = set(workbook.sheetnames)
    for sheet_name, frame in sheets.items():
        output_sheet = workbook.create_sheet(
            title=_unique_sheet_title(f"整理_{sheet_name}", used_titles)
        )
        _write_dataframe_sheet(output_sheet, frame)

    return workbook


def _write_summary_sheet(
    sheet,
    *,
    source_filename: str,
    instruction: str,
    sheet_summaries: list[dict[str, Any]],
) -> None:
    total_rows = sum(summary["row_count"] for summary in sheet_summaries)
    total_columns = sum(summary["column_count"] for summary in sheet_summaries)
    rows = [
        ("生成时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("源文件", source_filename),
        ("处理要求", instruction),
        ("源 Sheet 数", len(sheet_summaries)),
        ("总数据行数", total_rows),
        ("总字段数", total_columns),
        ("输出规则", f"每个源 Sheet 最多输出 {MAX_OUTPUT_ROWS_PER_SHEET} 行，超出部分请回到源文件复核。"),
    ]

    sheet.append(["项目", "内容"])
    for row in rows:
        sheet.append(list(row))

    start_row = len(rows) + 4
    sheet.cell(row=start_row, column=1, value="Sheet")
    sheet.cell(row=start_row, column=2, value="行数")
    sheet.cell(row=start_row, column=3, value="列数")
    sheet.cell(row=start_row, column=4, value="字段")

    for index, summary in enumerate(sheet_summaries, start=start_row + 1):
        sheet.cell(row=index, column=1, value=summary["sheet_name"])
        sheet.cell(row=index, column=2, value=summary["row_count"])
        sheet.cell(row=index, column=3, value=summary["column_count"])
        sheet.cell(row=index, column=4, value=", ".join(summary["columns"]))

    _style_sheet(sheet)
    sheet.freeze_panes = "A2"
    _auto_width(sheet, max_width=70)


def _write_numeric_summary_sheet(
    workbook: Workbook,
    sheet_summaries: list[dict[str, Any]],
) -> None:
    sheet = workbook.create_sheet("数值汇总")
    sheet.append(["Sheet", "字段", "有效数值数", "合计", "平均", "最小值", "最大值"])

    wrote_row = False
    for summary in sheet_summaries:
        for item in summary["numeric_columns"]:
            wrote_row = True
            sheet.append(
                [
                    summary["sheet_name"],
                    item["column"],
                    item["count"],
                    item["sum"],
                    item["mean"],
                    item["min"],
                    item["max"],
                ]
            )

    if not wrote_row:
        sheet.append(["-", "未识别到数值列", 0, 0, 0, 0, 0])

    _style_sheet(sheet)
    sheet.freeze_panes = "A2"
    _auto_width(sheet)


def _write_ai_suggestion_sheet(workbook: Workbook, ai_suggestion: str) -> None:
    sheet = workbook.create_sheet("AI建议")
    sheet.append(["AI 财务处理建议"])

    for line in ai_suggestion.splitlines() or ["暂无建议"]:
        sheet.append([line])

    _style_sheet(sheet)
    sheet.freeze_panes = "A2"
    sheet.column_dimensions["A"].width = 120
    for row in sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def _write_dataframe_sheet(sheet, frame: pd.DataFrame) -> None:
    headers = [str(column) if str(column) else f"Column {index}" for index, column in enumerate(frame.columns, start=1)]
    sheet.append(headers)

    for _, row in frame.head(MAX_OUTPUT_ROWS_PER_SHEET).iterrows():
        sheet.append([_clean_excel_value(value) for value in row.tolist()])

    if len(frame) > MAX_OUTPUT_ROWS_PER_SHEET:
        sheet.append([f"已截断：源 Sheet 共 {len(frame)} 行，本结果只输出前 {MAX_OUTPUT_ROWS_PER_SHEET} 行。"])

    _style_sheet(sheet)
    sheet.freeze_panes = "A2"
    _auto_width(sheet)


def _style_sheet(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin_side = Side(style="thin", color="D9E2F3")
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in sheet.iter_rows():
        for cell in row:
            cell.border = border
            if cell.row != 1:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    if sheet.max_row > 1 and sheet.max_column > 1:
        sheet.auto_filter.ref = sheet.dimensions


def _auto_width(sheet, *, max_width: int = 38) -> None:
    for column_cells in sheet.columns:
        column_letter = get_column_letter(column_cells[0].column)
        max_length = 8
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, min(len(value), max_width))
        sheet.column_dimensions[column_letter].width = max(10, min(max_length + 2, max_width))


def _clean_excel_value(value: Any) -> Any:
    if pd.isna(value):
        return ""

    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()

    if isinstance(value, (int, float, str, bool, datetime)):
        return value

    return str(value)


def _safe_filename(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return normalized or "finance_excel"


def _unique_sheet_title(title: str, used_titles: set[str]) -> str:
    clean_title = re.sub(r"[\[\]:*?/\\]", "_", title).strip() or "Sheet"
    clean_title = clean_title[:31]
    candidate = clean_title
    index = 2

    while candidate in used_titles:
        suffix = f"_{index}"
        candidate = f"{clean_title[:31 - len(suffix)]}{suffix}"
        index += 1

    used_titles.add(candidate)
    return candidate
