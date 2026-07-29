from __future__ import annotations

from typing import Literal, TypedDict

from app.permissions import POSITION_LABELS, is_valid_position


AutomationPosition = Literal["operations", "customer_service", "finance"]


class AutomationTaskSpec(TypedDict):
    label: str
    placeholder: str
    instruction: str
    output_format: str


AUTOMATION_TASKS: dict[str, dict[str, AutomationTaskSpec]] = {
    "operations": {
        "listing": {
            "label": "Listing 全流程上架草稿",
            "placeholder": "一句话输入 SKU、产品名称、卖点、尺寸、材质、目标站点、受众、竞品差异和合规限制，AI 自动完成完整 Listing 并保存草稿。",
            "instruction": (
                "一次性完成 Amazon 跨境电商 Listing 上架草稿自动化，默认英文输出。"
                "系统会把标题、五点描述、产品描述、后台搜索词和促销文案写入平台草稿区，等待运营审核发布。"
            ),
            "output_format": (
                "请按以下结构输出：\n"
                "1. Title (English)\n"
                "2. Five Bullet Points (English)\n"
                "3. Product Description (English)\n"
                "4. Backend Search Terms (English, comma separated)\n"
                "5. Promotion Copy (English)\n"
                "6. Chinese Optimization Notes\n"
                "系统动作：生成后自动保存到跨境平台草稿，不需要员工逐条复制粘贴。"
            ),
        },
        "title": {
            "label": "生成标题",
            "placeholder": "输入产品名称、核心卖点、材质、尺寸、适用场景和站点要求。",
            "instruction": (
                "生成多个 Amazon 标题备选方案。标题要突出核心关键词，符合跨境电商常见搜索习惯。"
            ),
            "output_format": (
                "请输出 5 个标题备选，每个标题后附一行简短说明，解释关键词排序和差异点。"
            ),
        },
        "bullets": {
            "label": "生成五点描述",
            "placeholder": "输入产品卖点、功能、规格、使用场景、材质和用户痛点。",
            "instruction": (
                "根据输入生成 5 条高转化五点描述，强调利益点、使用场景和差异化。"
            ),
            "output_format": (
                "请输出 5 条 Bullet Points，每条控制在 1 到 2 句，并附一行中文总结。"
            ),
        },
        "keywords": {
            "label": "生成关键词",
            "placeholder": "输入产品信息、核心词、同义词、目标市场和竞品词。",
            "instruction": (
                "生成 Amazon 后台搜索词与前台关键词组合，避免重复和无效堆砌。"
            ),
            "output_format": (
                "请输出 3 组关键词：核心词、长尾词、后台搜索词。后台搜索词用英文逗号分隔。"
            ),
        },
        "promo_copy": {
            "label": "生成促销文案",
            "placeholder": "输入活动类型、折扣、节日、受众、转化目标和促销约束。",
            "instruction": (
                "生成适合站内促销、广告、落地页和社媒复用的营销文案。"
            ),
            "output_format": (
                "请输出 3 个版本：短促销文案、长促销文案、广告标题。每个版本附中文说明。"
            ),
        },
        "competitor_analysis": {
            "label": "竞品分析",
            "placeholder": "输入竞品名称、链接摘录、价格、差评点、优势、用户画像。",
            "instruction": (
                "根据输入做竞品分析，帮助运营快速判断差异化机会、价格策略和内容优化方向。"
            ),
            "output_format": (
                "请输出：竞品定位、价格区间、核心卖点、差评痛点、可复制点、差异化建议。"
            ),
        },
    },
    "customer_service": {
        "smart_reply": {
            "label": "智能客服",
            "placeholder": "输入客户原话、订单状态、问题背景、希望达到的处理结果。",
            "instruction": (
                "生成客服智能回复，优先安抚情绪、澄清问题、给出下一步动作。"
            ),
            "output_format": (
                "请输出：推荐回复、处理建议、升级条件。推荐回复保持自然礼貌。"
            ),
        },
        "auto_reply": {
            "label": "自动回复",
            "placeholder": "输入客户消息和可公开的处理规则，生成自动回复模板。",
            "instruction": (
                "生成可直接复用的自动回复模板，适合售前、售后和订单咨询场景。"
            ),
            "output_format": (
                "请输出：自动回复正文、可替换变量、禁用表达。"
            ),
        },
        "refund_script": {
            "label": "退款售后话术",
            "placeholder": "输入退款原因、订单状态、用户诉求和售后规则。",
            "instruction": (
                "生成退款/退货/换货场景的话术，兼顾安抚、边界说明和合规表达。"
            ),
            "output_format": (
                "请输出：首轮回复话术、二次跟进话术、升级人工的话术。"
            ),
        },
        "multilingual_translation": {
            "label": "多语言客服翻译",
            "placeholder": "输入需要翻译的客服消息，标注目标语言或国家站点。",
            "instruction": (
                "为跨境客服生成多语言翻译，保留原意、礼貌语气和业务术语。"
            ),
            "output_format": (
                "请输出：原文、英文版、中文版、简要用语建议。"
            ),
        },
    },
    "finance": {
        "report_analysis": {
            "label": "分析财务报表",
            "placeholder": "输入财务报表摘要、利润、成本、现金流、异常说明或报表截图文字。",
            "instruction": (
                "分析财务报表，给出趋势、异常点、风险提示和下一步建议。"
            ),
            "output_format": (
                "请输出：摘要、关键指标、异常项、风险、建议。"
            ),
        },
        "salary_summary": {
            "label": "统计工资",
            "placeholder": "例如：把这个月所有员工的工资表发我。",
            "instruction": (
                "识别财务自然语言请求，按期间查询 ERP 工资单，并生成可下载的员工工资 Excel。"
            ),
            "output_format": (
                "输出：工资明细 Excel、自动化摘要、意图识别结果、总额、人数和复核建议。"
            ),
        },
        "salary_wechat_send": {
            "label": "工资表微信发送准备",
            "placeholder": "例如：生成这个月员工工资表，准备通过个人微信发给张三。",
            "instruction": (
                "识别工资表微信发送需求，按期间查询 ERP 工资单，生成 Excel，并创建个人微信待人工发送任务。"
                "第一版不会自动点击微信发送按钮，必须由财务确认联系人和敏感文件后手动发送。"
            ),
            "output_format": (
                "输出：执行计划、工资 Excel、接收人、待人工发送状态、确认项、执行器状态和审计记录。"
            ),
        },
        "excel_transform": {
            "label": "Excel 生成",
            "placeholder": "请到财务 Excel 生成页面选择或上传 Excel，并可选择销售发票、收付款单等财务 ERP 表辅助生成。",
            "instruction": (
                "上传真实财务 Excel 文件，并可选择财务岗位权限内 ERP 表，生成处理摘要、数值汇总、AI 建议和新工作簿。"
            ),
            "output_format": (
                "输出：新 Excel 文件、处理摘要、ERP 数据摘要、数值汇总、AI 建议和整理后的数据 Sheet。"
            ),
        },
    },
}


def get_automation_task(position: str, task_id: str) -> AutomationTaskSpec:
    if not is_valid_position(position):
        raise ValueError("无效岗位")

    task = AUTOMATION_TASKS.get(position, {}).get(task_id)
    if task is None:
        raise ValueError("当前岗位不支持该任务")

    return task


def list_automation_tasks(position: str) -> list[dict]:
    if not is_valid_position(position):
        return []

    return [
        {
            "task_id": task_id,
            "label": spec["label"],
            "placeholder": spec["placeholder"],
            "instruction": spec["instruction"],
            "output_format": spec["output_format"],
            "position": position,
            "position_label": POSITION_LABELS[position],
        }
        for task_id, spec in AUTOMATION_TASKS[position].items()
    ]


def list_all_automation_tasks() -> list[dict]:
    items: list[dict] = []

    for position in AUTOMATION_TASKS:
        items.extend(list_automation_tasks(position))

    return items


def find_automation_task(task_id: str) -> dict | None:
    for position, tasks in AUTOMATION_TASKS.items():
        spec = tasks.get(task_id)
        if spec is None:
            continue

        return {
            "task_id": task_id,
            "position": position,
            "position_label": POSITION_LABELS[position],
            **spec,
        }

    return None


def build_automation_prompt(position: str, task_id: str, input_text: str) -> str:
    task = get_automation_task(position, task_id)
    position_label = POSITION_LABELS[position]

    return f"""你是企业内部的 {position_label} 岗位 AI 自动化助手。
你只负责这个岗位允许的任务，不要越权，不要解释规则本身。

任务名称：{task['label']}
任务说明：{task['instruction']}

用户输入：
{input_text}

输出格式：
{task['output_format']}

附加要求：
- 输出要直接可用，尽量具体，不要空话。
- 如果信息不足，可以基于常识合理补全，但要明确标注“假设”。
- 不要输出与任务无关的内容。
"""
