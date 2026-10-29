from typing import Any


ERP_RESOURCE_CATALOG: dict[str, dict[str, Any]] = {
    "Crossborder Product": {
        "label": "跨境商品档案",
        "description": "我方 SKU 的站点、店铺、销售币种、卖点和模拟来源。",
        "keywords": ["跨境商品", "商品档案", "我方商品", "我方产品"],
        "provider_refs": {"erpnext": "Crossborder Product"},
        "erpnext_fields": ["name", "item_code", "product_name", "market", "store", "brand", "currency", "selling_price", "rating", "review_count", "language", "features", "demo_batch", "is_simulated"],
    },
    "Competitor Product": {
        "label": "竞品资料",
        "description": "与我方 SKU 关联的竞品观察；模拟资料不计入我方库存和账务。",
        "keywords": ["竞品", "竞争对手", "竞对", "competitor"],
        "provider_refs": {"erpnext": "Competitor Product"},
        "erpnext_fields": ["name", "own_item_code", "product_name", "brand", "market", "currency", "price", "rating", "review_count", "estimated_monthly_sales", "fulfillment", "observed_date", "strengths", "weaknesses", "data_source", "demo_batch", "is_simulated"],
    },
    "Ad Campaign Daily": {
        "label": "广告日报",
        "description": "SKU 广告曝光、点击、订单、花费、ACOS 和 ROAS。",
        "keywords": ["广告", "广告日报", "投放", "acos", "roas"],
        "provider_refs": {"erpnext": "Ad Campaign Daily"},
        "erpnext_fields": ["name", "campaign_name", "item_code", "market", "report_date", "currency", "impressions", "clicks", "ad_orders", "spend", "ad_sales", "acos", "roas", "demo_batch", "is_simulated"],
    },
    "Marketplace Settlement": {
        "label": "平台结算",
        "description": "订单销售、退款、平台与履约费用、净回款及待核差额。",
        "keywords": ["平台结算", "结算单", "净回款", "结算差异", "settlement"],
        "provider_refs": {"erpnext": "Marketplace Settlement"},
        "erpnext_fields": ["name", "order_no", "sales_invoice", "payment_entry", "item_code", "market", "settlement_date", "currency", "gross_amount", "refund_amount", "platform_fee", "fulfillment_fee", "expected_payout", "actual_payout", "difference", "exchange_rate", "status", "note", "demo_batch", "is_simulated"],
    },
    "Shipment Tracking": {
        "label": "物流轨迹",
        "description": "订单运单、承运商、预计送达和物流异常。",
        "keywords": ["物流轨迹", "物流状态", "物流异常", "包裹轨迹", "shipment"],
        "provider_refs": {"erpnext": "Shipment Tracking"},
        "erpnext_fields": ["name", "order_no", "sales_order", "delivery_note", "tracking_no", "carrier", "market", "shipped_date", "estimated_delivery", "status", "last_event", "demo_batch", "is_simulated"],
    },
    "Item": {
        "label": "商品资料",
        "description": "商品、SKU、基础属性和可售状态。",
        "keywords": ["商品", "SKU", "物料", "产品", "item"],
        "provider_refs": {
            "erpnext": "Item",
            "kingdee": "BD_MATERIAL",
            "yonyou": "product",
        },
        "erpnext_fields": ["name", "item_name", "item_group", "disabled", "modified"],
    },
    "Item Price": {
        "label": "商品价格",
        "description": "SKU 销售价格表、币种和生效售价；不包含采购进价。",
        "keywords": ["价格", "售价", "报价", "单价", "item price"],
        "provider_refs": {
            "erpnext": "Item Price",
            "kingdee": "SAL_PRICE",
            "yonyou": "price-list",
        },
        "erpnext_fields": ["name", "item_code", "price_list", "price_list_rate", "currency", "modified"],
    },
    "Bin": {
        "label": "库存",
        "description": "SKU 在 ERPNext 仓库中的可用库存。",
        "keywords": ["库存", "数量", "stock", "inventory", "bin"],
        "provider_refs": {
            "erpnext": "Bin",
            "kingdee": "STK_INVENTORY",
            "yonyou": "inventory",
        },
        "erpnext_fields": ["name", "item_code", "warehouse", "actual_qty", "projected_qty", "modified"],
    },
    "Sales Order": {
        "label": "销售订单",
        "description": "订单、客户、状态、金额和交付进度。",
        "keywords": ["订单", "销售单", "order", "发货单号", "出单"],
        "provider_refs": {
            "erpnext": "Sales Order",
            "kingdee": "SAL_SaleOrder",
            "yonyou": "sales-order",
        },
        "erpnext_fields": ["name", "customer", "company", "transaction_date", "po_no", "status", "currency", "grand_total", "base_grand_total", "modified"],
    },
    "Sales Invoice summary": {
        "label": "销售发票摘要",
        "description": "仅面向运营的销售发票摘要字段，不开放完整财务明细。",
        "keywords": ["发票摘要", "发票汇总", "销售发票摘要"],
        "provider_refs": {
            "erpnext": "Sales Invoice",
            "kingdee": "AR_RECEIVABLE_SUMMARY",
            "yonyou": "sales-invoice-summary",
        },
        "erpnext_fields": ["name", "customer", "company", "posting_date", "po_no", "status", "currency", "grand_total", "base_grand_total"],
    },
    "Customer": {
        "label": "客户资料",
        "description": "客户名称、分组和联系方式线索。",
        "keywords": ["客户", "买家", "customer", "买家名"],
        "provider_refs": {
            "erpnext": "Customer",
            "kingdee": "BD_Customer",
            "yonyou": "customer",
        },
        "erpnext_fields": ["name", "customer_name", "customer_group", "territory", "modified"],
    },
    "Delivery Note": {
        "label": "物流/出库单",
        "description": "发货、物流、签收和交付状态。",
        "keywords": ["物流", "发货", "出库", "签收", "delivery", "运单"],
        "provider_refs": {
            "erpnext": "Delivery Note",
            "kingdee": "SAL_OUTSTOCK",
            "yonyou": "delivery-note",
        },
        "erpnext_fields": ["name", "customer", "company", "posting_date", "lr_no", "title", "status", "currency", "grand_total", "base_grand_total", "modified"],
    },
    "Issue": {
        "label": "售后工单",
        "description": "客服售后问题、处理状态和优先级。",
        "keywords": ["售后", "工单", "问题单", "issue", "投诉"],
        "provider_refs": {
            "erpnext": "Issue",
            "kingdee": "CRM_SERVICE_REQUEST",
            "yonyou": "service-ticket",
        },
        "erpnext_fields": ["name", "subject", "customer", "status", "priority", "description", "modified"],
    },
    "Return request": {
        "label": "退货请求",
        "description": "退货、退款和售后逆向流程。",
        "keywords": ["退货", "退款", "return", "售后退款", "逆向"],
        "provider_refs": {
            "erpnext": "Issue",
            "kingdee": "SAL_RETURNSTOCK",
            "yonyou": "return-request",
        },
        "erpnext_fields": ["name", "subject", "customer", "status", "priority", "description", "modified"],
    },
    "GL Entry": {
        "label": "总账分录",
        "description": "财务总账凭证和科目分录。",
        "keywords": ["总账", "分录", "凭证", "报表", "利润", "成本", "gl"],
        "provider_refs": {
            "erpnext": "GL Entry",
            "kingdee": "GL_VOUCHER",
            "yonyou": "gl-entry",
        },
        "erpnext_fields": ["name", "company", "posting_date", "account", "debit", "credit", "voucher_type", "voucher_no"],
    },
    "Payment Entry": {
        "label": "收付款单",
        "description": "收款、付款、往来和支付状态。",
        "keywords": ["付款", "收款", "支付", "回款", "payment", "银行流水"],
        "provider_refs": {
            "erpnext": "Payment Entry",
            "kingdee": "CN_PAYAPPLY",
            "yonyou": "payment-entry",
        },
        "erpnext_fields": ["name", "company", "posting_date", "payment_type", "party", "paid_amount", "base_paid_amount", "paid_from_account_currency", "status", "reference_no"],
    },
    "Salary Slip": {
        "label": "工资单",
        "description": "员工薪资、工资月份和发放状态。",
        "keywords": ["工资", "薪资", "salary", "工资单", "薪酬"],
        "provider_refs": {
            "erpnext": "Salary Slip",
            "kingdee": "HR_SALARY",
            "yonyou": "salary-slip",
        },
        "erpnext_fields": ["name", "employee", "employee_name", "start_date", "end_date", "gross_pay", "net_pay", "status"],
    },
    "Sales Invoice": {
        "label": "销售发票",
        "description": "财务可见的完整销售发票记录。",
        "keywords": ["销售发票", "开票", "invoice", "发票", "应收"],
        "provider_refs": {
            "erpnext": "Sales Invoice",
            "kingdee": "AR_RECEIVABLE",
            "yonyou": "sales-invoice",
        },
        "erpnext_fields": ["name", "customer", "company", "posting_date", "due_date", "po_no", "status", "currency", "grand_total", "base_grand_total", "outstanding_amount"],
    },
    "Purchase Invoice": {
        "label": "采购发票",
        "description": "供应商采购发票、应付金额和付款状态。",
        "keywords": ["采购发票", "应付", "采购单", "purchase invoice"],
        "provider_refs": {
            "erpnext": "Purchase Invoice",
            "kingdee": "AP_PAYABLE",
            "yonyou": "purchase-invoice",
        },
        "erpnext_fields": ["name", "supplier", "company", "posting_date", "due_date", "bill_no", "status", "currency", "grand_total", "base_grand_total", "outstanding_amount"],
    },
}


def resolve_resource_name(value: str) -> str | None:
    text = value.strip()
    if text in ERP_RESOURCE_CATALOG:
        return text

    lowered = text.lower()
    for resource, definition in ERP_RESOURCE_CATALOG.items():
        label = str(definition["label"]).lower()
        refs = definition.get("provider_refs", {})
        ref_values = [str(item).lower() for item in refs.values() if item]

        if resource.lower() == lowered or label == lowered or lowered in ref_values:
            return resource

    return None


def match_resource_by_keywords(
    text: str,
    scopes: list[str],
) -> str | None:
    ranked = rank_resource_matches(text, scopes)
    return ranked[0][0] if ranked else None


def rank_resource_matches(text: str, scopes: list[str]) -> list[tuple[str, int]]:
    normalized_text = text.lower()
    matches: list[tuple[str, int]] = []

    for resource in scopes:
        definition = ERP_RESOURCE_CATALOG.get(resource)
        if definition is None:
            continue

        candidates = [
            resource,
            str(definition["label"]),
            *[str(item) for item in definition.get("keywords", [])],
            *[str(item) for item in definition.get("provider_refs", {}).values()],
        ]

        score = 0
        for candidate in candidates:
            candidate_text = candidate.lower()
            if candidate_text and candidate_text in normalized_text:
                score += max(len(candidate_text), 1)

        if score > 0:
            matches.append((resource, score))

    return sorted(matches, key=lambda item: -item[1])


def list_resource_definitions(scopes: list[str]) -> list[dict[str, Any]]:
    items = []
    for resource in scopes:
        definition = ERP_RESOURCE_CATALOG.get(resource)
        if definition is None:
            continue

        items.append(resource_to_public(resource, definition))

    return items


def resource_to_public(resource: str, definition: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource": resource,
        "label": definition["label"],
        "description": definition["description"],
        "provider_refs": definition.get("provider_refs", {}),
    }


def provider_resource_for(resource: str, provider_id: str) -> str | None:
    definition = ERP_RESOURCE_CATALOG.get(resource)
    if definition is None:
        return None

    refs = definition.get("provider_refs", {})
    value = refs.get(provider_id)
    return str(value) if value else None


def provider_fields_for(resource: str, provider_id: str) -> list[str]:
    definition = ERP_RESOURCE_CATALOG.get(resource) or {}
    fields = definition.get(f"{provider_id}_fields")

    if isinstance(fields, list) and fields:
        return [str(item) for item in fields]

    return ["name", "modified"]
