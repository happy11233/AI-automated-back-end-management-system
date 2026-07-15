import json


ITEMS = [
    {
        "item_code": "AMZ-AIR-PUMP-001",
        "item_name": "Amazon Portable Air Pump",
        "rate": 29.99,
    },
    {
        "item_code": "AMZ-LED-DESK-002",
        "item_name": "Amazon LED Desk Lamp",
        "rate": 42.5,
    },
    {
        "item_code": "AMZ-CABLE-USB-C-003",
        "item_name": "Amazon Braided USB-C Cable Pack",
        "rate": 13.99,
    },
]

CUSTOMERS = [
    {
        "customer_name": "Amazon US Buyer - Olivia Carter",
        "territory": "Rest Of The World",
        "po_no": "AMZ-US-112-4589012-7783401",
        "item_code": "AMZ-AIR-PUMP-001",
        "qty": 2,
        "tracking": "1ZAMZUS202607150001",
        "issue": "退款咨询：买家反馈便携充气泵包装破损，要求部分退款。",
    },
    {
        "customer_name": "Amazon DE Buyer - Lukas Weber",
        "territory": "Rest Of The World",
        "po_no": "AMZ-DE-305-7712468-1290045",
        "item_code": "AMZ-LED-DESK-002",
        "qty": 1,
        "tracking": "DHL-DE-AMZ-2026071502",
        "issue": "物流查询：德国买家询问台灯预计签收时间。",
    },
    {
        "customer_name": "Amazon JP Buyer - Haruka Sato",
        "territory": "Rest Of The World",
        "po_no": "AMZ-JP-250-6630188-4402197",
        "item_code": "AMZ-CABLE-USB-C-003",
        "qty": 3,
        "tracking": "YAMATO-JP-2026071503",
        "issue": "售后咨询：买家反馈 USB-C 线材数量不符，需要补发。",
    },
]


def seed_amazon_demo_data() -> None:
    import frappe

    company = _first_value("Company", "name") or "xiang"
    customer_group = _first_value("Customer Group", "name") or "Commercial"
    territory = _first_value("Territory", "name") or "Rest Of The World"
    item_group = "Products" if frappe.db.exists("Item Group", "Products") else "All Item Groups"
    warehouse = _warehouse_for_company(company)

    created = {
        "items": [],
        "item_prices": [],
        "customers": [],
        "sales_orders": [],
        "delivery_notes": [],
        "sales_invoices": [],
        "issues": [],
    }

    _ensure_issue_type()

    for item in ITEMS:
        _ensure_item(item, item_group)
        created["items"].append(item["item_code"])

        if _ensure_item_price(item):
            created["item_prices"].append(item["item_code"])

    for order in CUSTOMERS:
        customer = _ensure_customer(
            customer_name=order["customer_name"],
            customer_group=customer_group,
            territory=order.get("territory") or territory,
        )
        created["customers"].append(customer)

        sales_order = _ensure_sales_order(
            company=company,
            customer=customer,
            po_no=order["po_no"],
            item_code=order["item_code"],
            qty=order["qty"],
            warehouse=warehouse,
        )
        created["sales_orders"].append(sales_order)

        delivery_note = _ensure_delivery_note(
            company=company,
            customer=customer,
            po_no=order["po_no"],
            item_code=order["item_code"],
            qty=order["qty"],
            warehouse=warehouse,
            tracking=order["tracking"],
        )
        created["delivery_notes"].append(delivery_note)

        sales_invoice = _ensure_sales_invoice(
            company=company,
            customer=customer,
            po_no=order["po_no"],
            item_code=order["item_code"],
            qty=order["qty"],
        )
        created["sales_invoices"].append(sales_invoice)

        issue = _ensure_issue(
            customer=customer,
            po_no=order["po_no"],
            subject=f"{order['po_no']} {order['issue'][:30]}",
            description=order["issue"],
        )
        created["issues"].append(issue)

    frappe.db.commit()
    print(json.dumps(created, ensure_ascii=False))


def _ensure_item(item: dict, item_group: str) -> None:
    import frappe

    if frappe.db.exists("Item", item["item_code"]):
        doc = frappe.get_doc("Item", item["item_code"])
        doc.item_name = item["item_name"]
        doc.item_group = item_group
        doc.stock_uom = "Nos"
        doc.save(ignore_permissions=True)
        return

    frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": item["item_code"],
            "item_name": item["item_name"],
            "item_group": item_group,
            "stock_uom": "Nos",
            "is_stock_item": 0,
        }
    ).insert(ignore_permissions=True)


def _ensure_item_price(item: dict) -> bool:
    import frappe

    existing = frappe.db.exists(
        "Item Price",
        {
            "item_code": item["item_code"],
            "price_list": "Standard Selling",
        },
    )
    if existing:
        doc = frappe.get_doc("Item Price", existing)
        doc.price_list_rate = item["rate"]
        doc.currency = "CNY"
        doc.save(ignore_permissions=True)
        return False

    frappe.get_doc(
        {
            "doctype": "Item Price",
            "item_code": item["item_code"],
            "price_list": "Standard Selling",
            "price_list_rate": item["rate"],
            "currency": "CNY",
        }
    ).insert(ignore_permissions=True)
    return True


def _ensure_customer(customer_name: str, customer_group: str, territory: str) -> str:
    import frappe

    if frappe.db.exists("Customer", customer_name):
        doc = frappe.get_doc("Customer", customer_name)
        doc.customer_group = customer_group
        doc.territory = territory
        doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Individual",
            "customer_group": customer_group,
            "territory": territory,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_sales_order(
    company: str,
    customer: str,
    po_no: str,
    item_code: str,
    qty: int,
    warehouse: str | None,
) -> str:
    import frappe

    existing = frappe.db.exists("Sales Order", {"po_no": po_no})
    if existing:
        return existing

    rate = _item_rate(item_code)
    item_row = {
        "item_code": item_code,
        "qty": qty,
        "rate": rate,
        "delivery_date": "2026-07-20",
    }
    if warehouse:
        item_row["warehouse"] = warehouse

    doc = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "company": company,
            "customer": customer,
            "transaction_date": "2026-07-15",
            "delivery_date": "2026-07-20",
            "currency": "CNY",
            "selling_price_list": "Standard Selling",
            "po_no": po_no,
            "items": [item_row],
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_delivery_note(
    company: str,
    customer: str,
    po_no: str,
    item_code: str,
    qty: int,
    warehouse: str | None,
    tracking: str,
) -> str:
    import frappe

    existing = frappe.db.exists("Delivery Note", {"lr_no": tracking})
    if existing:
        return existing

    item_row = {
        "item_code": item_code,
        "qty": qty,
        "rate": _item_rate(item_code),
    }
    if warehouse:
        item_row["warehouse"] = warehouse

    doc = frappe.get_doc(
        {
            "doctype": "Delivery Note",
            "company": company,
            "customer": customer,
            "posting_date": "2026-07-15",
            "posting_time": "10:30:00",
            "currency": "CNY",
            "lr_no": tracking,
            "title": f"Amazon order {po_no}",
            "items": [item_row],
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_sales_invoice(
    company: str,
    customer: str,
    po_no: str,
    item_code: str,
    qty: int,
) -> str:
    import frappe

    existing = frappe.db.exists("Sales Invoice", {"po_no": po_no})
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "company": company,
            "customer": customer,
            "posting_date": "2026-07-15",
            "due_date": "2026-07-30",
            "currency": "CNY",
            "selling_price_list": "Standard Selling",
            "po_no": po_no,
            "items": [
                {
                    "item_code": item_code,
                    "qty": qty,
                    "rate": _item_rate(item_code),
                }
            ],
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_issue(customer: str, po_no: str, subject: str, description: str) -> str:
    import frappe

    existing = frappe.db.exists("Issue", {"subject": subject})
    if existing:
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "Issue",
            "subject": subject,
            "customer": customer,
            "status": "Open",
            "priority": "High" if "退款" in description else "Medium",
            "issue_type": "Amazon After-sales",
            "description": f"Amazon订单号：{po_no}\n{description}",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_issue_type() -> None:
    import frappe

    if frappe.db.exists("Issue Type", "Amazon After-sales"):
        return

    frappe.get_doc(
        {
            "doctype": "Issue Type",
            "name": "Amazon After-sales",
            "issue_type": "Amazon After-sales",
        }
    ).insert(ignore_permissions=True)


def _item_rate(item_code: str) -> float:
    for item in ITEMS:
        if item["item_code"] == item_code:
            return float(item["rate"])
    return 1.0


def _first_value(doctype: str, fieldname: str) -> str | None:
    import frappe

    values = frappe.db.get_all(doctype, pluck=fieldname, limit=1)
    return values[0] if values else None


def _warehouse_for_company(company: str) -> str | None:
    import frappe

    values = frappe.db.get_all(
        "Warehouse",
        filters={"company": company, "is_group": 0},
        pluck="name",
        limit=1,
    )
    return values[0] if values else None
