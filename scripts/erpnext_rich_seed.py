import json
from datetime import date


ITEMS = [
    ("AMZ-AIR-PUMP-001", "Portable Tire Air Pump", 29.99),
    ("AMZ-LED-DESK-002", "Foldable LED Desk Lamp", 42.50),
    ("AMZ-CABLE-USB-C-003", "Braided USB-C Cable Pack", 13.99),
    ("AMZ-BOTTLE-THERMO-004", "Stainless Steel Thermal Bottle", 24.90),
    ("AMZ-BAG-ORGANIZER-005", "Travel Cable Organizer Bag", 18.80),
    ("AMZ-KITCHEN-SCALE-006", "Digital Kitchen Scale", 21.60),
    ("AMZ-YOGA-MAT-007", "Non Slip Yoga Mat", 35.90),
    ("AMZ-PET-FEEDER-008", "Automatic Pet Feeder", 68.00),
    ("AMZ-HUMIDIFIER-009", "Mini Desk Humidifier", 31.20),
    ("AMZ-LAPTOP-STAND-010", "Aluminum Laptop Stand", 39.90),
    ("AMZ-COFFEE-GRINDER-011", "Electric Coffee Grinder", 56.00),
    ("AMZ-SECURITY-CAM-012", "Indoor Security Camera", 49.50),
]


ORDERS = [
    {
        "market": "US",
        "customer": "美国买家 Olivia Carter",
        "po_no": "AMZ-US-112-4589012-7783401",
        "item": "AMZ-AIR-PUMP-001",
        "qty": 2,
        "date": "2026-07-02",
        "due": "2026-07-17",
        "tracking": "1ZAMZUS202607020001",
        "issue": "退款咨询：买家反馈便携充气泵外包装破损，希望退 8 美元差价。",
    },
    {
        "market": "DE",
        "customer": "德国买家 Lukas Weber",
        "po_no": "AMZ-DE-305-7712468-1290045",
        "item": "AMZ-LED-DESK-002",
        "qty": 1,
        "date": "2026-07-03",
        "due": "2026-07-18",
        "tracking": "DHL-DE-AMZ-2026070302",
        "issue": "物流查询：德国买家询问台灯预计签收时间，包裹已到法兰克福分拨中心。",
    },
    {
        "market": "JP",
        "customer": "日本买家 Haruka Sato",
        "po_no": "AMZ-JP-250-6630188-4402197",
        "item": "AMZ-CABLE-USB-C-003",
        "qty": 3,
        "date": "2026-07-04",
        "due": "2026-07-19",
        "tracking": "YAMATO-JP-2026070403",
        "issue": "售后咨询：买家反馈 USB-C 线材数量不符，需要补发一件。",
    },
    {
        "market": "US",
        "customer": "美国买家 Ethan Brooks",
        "po_no": "AMZ-US-742-9912033-6501188",
        "item": "AMZ-BOTTLE-THERMO-004",
        "qty": 4,
        "date": "2026-07-05",
        "due": "2026-07-20",
        "tracking": "1ZAMZUS202607050004",
        "issue": "差评预警：买家反馈保温杯杯盖漏水，要求换新。",
    },
    {
        "market": "UK",
        "customer": "英国买家 Emily Johnson",
        "po_no": "AMZ-UK-026-1187309-5520041",
        "item": "AMZ-BAG-ORGANIZER-005",
        "qty": 2,
        "date": "2026-07-06",
        "due": "2026-07-21",
        "tracking": "ROYAL-UK-AMZ-2026070605",
        "issue": "物流查询：英国买家反馈追踪号暂无更新，请确认是否已出库。",
    },
    {
        "market": "CA",
        "customer": "加拿大买家 Noah Martin",
        "po_no": "AMZ-CA-811-2048097-7721905",
        "item": "AMZ-KITCHEN-SCALE-006",
        "qty": 1,
        "date": "2026-07-07",
        "due": "2026-07-22",
        "tracking": "CP-CA-AMZ-2026070706",
        "issue": "售后咨询：厨房秤显示误差较大，买家申请退货标签。",
    },
    {
        "market": "DE",
        "customer": "德国买家 Anna Fischer",
        "po_no": "AMZ-DE-583-3345901-8012209",
        "item": "AMZ-YOGA-MAT-007",
        "qty": 2,
        "date": "2026-07-08",
        "due": "2026-07-23",
        "tracking": "DHL-DE-AMZ-2026070807",
        "issue": "退货请求：买家认为瑜伽垫颜色与页面图片不一致，申请退货。",
    },
    {
        "market": "FR",
        "customer": "法国买家 Camille Dubois",
        "po_no": "AMZ-FR-407-8261044-0193307",
        "item": "AMZ-PET-FEEDER-008",
        "qty": 1,
        "date": "2026-07-09",
        "due": "2026-07-24",
        "tracking": "LA-POSTE-FR-2026070908",
        "issue": "退款咨询：自动喂食器定时功能异常，买家要求全额退款。",
    },
    {
        "market": "JP",
        "customer": "日本买家 Yuki Tanaka",
        "po_no": "AMZ-JP-112-9083442-5570183",
        "item": "AMZ-HUMIDIFIER-009",
        "qty": 2,
        "date": "2026-07-10",
        "due": "2026-07-25",
        "tracking": "YAMATO-JP-2026071009",
        "issue": "售后咨询：加湿器运行噪音偏大，买家希望获取使用说明。",
    },
    {
        "market": "AU",
        "customer": "澳洲买家 Liam Wilson",
        "po_no": "AMZ-AU-739-1102488-6649022",
        "item": "AMZ-LAPTOP-STAND-010",
        "qty": 1,
        "date": "2026-07-11",
        "due": "2026-07-26",
        "tracking": "AUSPOST-AMZ-2026071110",
        "issue": "物流查询：澳洲买家询问笔记本支架是否会在周末前送达。",
    },
    {
        "market": "US",
        "customer": "美国买家 Sophia Clark",
        "po_no": "AMZ-US-624-6639201-3459180",
        "item": "AMZ-COFFEE-GRINDER-011",
        "qty": 1,
        "date": "2026-07-12",
        "due": "2026-07-27",
        "tracking": "1ZAMZUS2026071211",
        "issue": "售后咨询：咖啡研磨机缺少清洁刷，需要补发配件。",
    },
    {
        "market": "DE",
        "customer": "德国买家 Felix Schneider",
        "po_no": "AMZ-DE-951-4408127-2041186",
        "item": "AMZ-SECURITY-CAM-012",
        "qty": 2,
        "date": "2026-07-13",
        "due": "2026-07-28",
        "tracking": "DHL-DE-AMZ-2026071312",
        "issue": "技术支持：室内摄像头连接 Wi-Fi 失败，买家要求德语说明。",
    },
    {
        "market": "ES",
        "customer": "西班牙买家 Lucia Garcia",
        "po_no": "AMZ-ES-302-7801993-6147205",
        "item": "AMZ-BOTTLE-THERMO-004",
        "qty": 3,
        "date": "2026-07-14",
        "due": "2026-07-29",
        "tracking": "CORREOS-ES-2026071413",
        "issue": "退货请求：其中一个保温杯有划痕，买家要求部分退款或补发。",
    },
    {
        "market": "IT",
        "customer": "意大利买家 Matteo Rossi",
        "po_no": "AMZ-IT-109-3370102-7721184",
        "item": "AMZ-LAPTOP-STAND-010",
        "qty": 2,
        "date": "2026-07-15",
        "due": "2026-07-30",
        "tracking": "POSTE-IT-2026071514",
        "issue": "物流查询：包裹显示已签收但买家未收到，需要核查签收证明。",
    },
    {
        "market": "US",
        "customer": "美国买家 Ava Miller",
        "po_no": "AMZ-US-887-2219044-1095521",
        "item": "AMZ-PET-FEEDER-008",
        "qty": 1,
        "date": "2026-07-16",
        "due": "2026-07-31",
        "tracking": "1ZAMZUS2026071615",
        "issue": "售后咨询：自动喂食器 App 无法绑定设备，要求远程指导。",
    },
]


SUPPLIERS = [
    ("深圳市星河电子有限公司", "Raw Material"),
    ("宁波海风家居用品有限公司", "Hardware"),
    ("广州云仓物流服务有限公司", "Services"),
    ("苏州晨光包装材料有限公司", "Raw Material"),
]


PURCHASES = [
    ("PI-AMZ-COST-202607-001", "深圳市星河电子有限公司", "AMZ-SECURITY-CAM-012", 20, 27.80, "2026-07-05"),
    ("PI-AMZ-COST-202607-002", "宁波海风家居用品有限公司", "AMZ-BOTTLE-THERMO-004", 60, 9.30, "2026-07-06"),
    ("PI-AMZ-COST-202607-003", "广州云仓物流服务有限公司", "AMZ-BAG-ORGANIZER-005", 1, 680.00, "2026-07-08"),
    ("PI-AMZ-COST-202607-004", "苏州晨光包装材料有限公司", "AMZ-CABLE-USB-C-003", 100, 4.20, "2026-07-10"),
    ("PI-AMZ-COST-202607-005", "深圳市星河电子有限公司", "AMZ-PET-FEEDER-008", 18, 36.50, "2026-07-12"),
]


EMPLOYEES = [
    ("EMP-CN-OPS-001", "张晨", "Operations"),
    ("EMP-CN-CS-002", "李晓雨", "Customer Service"),
    ("EMP-CN-FIN-003", "王静", "Finance"),
    ("EMP-CN-WH-004", "陈浩", "Warehouse"),
    ("EMP-CN-MKT-005", "赵一鸣", "Marketing"),
]


SALARY_SLIPS = [
    ("SAL-AMZ-202607-001", "EMP-CN-OPS-001", "张晨", 12800, 10450, "2026-07-01", "2026-07-31"),
    ("SAL-AMZ-202607-002", "EMP-CN-CS-002", "李晓雨", 9800, 8120, "2026-07-01", "2026-07-31"),
    ("SAL-AMZ-202607-003", "EMP-CN-FIN-003", "王静", 14200, 11680, "2026-07-01", "2026-07-31"),
    ("SAL-AMZ-202607-004", "EMP-CN-WH-004", "陈浩", 8700, 7250, "2026-07-01", "2026-07-31"),
    ("SAL-AMZ-202607-005", "EMP-CN-MKT-005", "赵一鸣", 11900, 9650, "2026-07-01", "2026-07-31"),
]


EXTRA_ITEM_NAMES = [
    "Wireless Charging Pad",
    "Smart Plug Mini",
    "Noise Cancelling Earbuds",
    "Waterproof Phone Pouch",
    "Magnetic Car Phone Mount",
    "Reusable Food Storage Bags",
    "Electric Milk Frother",
    "Compact Travel Umbrella",
    "Memory Foam Seat Cushion",
    "Solar Garden Lights",
    "Adjustable Dumbbell Set",
    "Kids Drawing Tablet",
    "Bluetooth Barcode Scanner",
    "USB-C Docking Station",
    "Portable Garment Steamer",
    "Mini Projector",
    "Robot Vacuum Filter Pack",
    "Digital Meat Thermometer",
    "Laptop Privacy Screen",
    "Smart Door Sensor",
    "Camping Lantern",
    "Silicone Baking Mat",
    "Pet Grooming Brush",
    "Reusable Water Filter",
]


EXTRA_CUSTOMER_NAMES = {
    "US": ["美国买家 Mia Davis", "美国买家 Lucas Brown", "美国买家 Harper White", "美国买家 Jack Taylor"],
    "DE": ["德国买家 Mia Hoffmann", "德国买家 Paul Wagner", "德国买家 Lara Becker", "德国买家 Tim Richter"],
    "JP": ["日本买家 Aoi Nakamura", "日本买家 Ren Suzuki", "日本买家 Mei Ito", "日本买家 Sora Kobayashi"],
    "UK": ["英国买家 Grace Smith", "英国买家 Oliver Davies", "英国买家 Isla Brown", "英国买家 Harry Wilson"],
    "CA": ["加拿大买家 Emma Lee", "加拿大买家 William Chen", "加拿大买家 Chloe Singh", "加拿大买家 Logan Moore"],
    "FR": ["法国买家 Manon Martin", "法国买家 Hugo Bernard", "法国买家 Lea Moreau", "法国买家 Nathan Laurent"],
    "AU": ["澳洲买家 Charlotte Harris", "澳洲买家 Mason Thompson", "澳洲买家 Amelia Walker", "澳洲买家 Henry Scott"],
    "ES": ["西班牙买家 Sofia Lopez", "西班牙买家 Daniel Martinez", "西班牙买家 Paula Fernandez", "西班牙买家 Hugo Sanchez"],
    "IT": ["意大利买家 Giulia Bianchi", "意大利买家 Leonardo Romano", "意大利买家 Aurora Conti", "意大利买家 Marco Ferri"],
}


EXTRA_ISSUES = [
    "物流查询：客户反馈追踪停留超过 48 小时，需要确认最新节点。",
    "售后咨询：商品可以正常使用，但配件少了一件，希望补发。",
    "退款咨询：客户收到商品后发现轻微划痕，申请部分退款。",
    "退货请求：客户误购型号，希望获取退货地址和标签。",
    "差评预警：客户表示页面描述不够清晰，需要客服主动解释。",
    "技术支持：客户无法完成首次配网，需要发送操作步骤。",
    "物流查询：客户要求确认是否会在承诺日期前送达。",
    "售后咨询：客户询问保修期和更换流程。",
]


EXTRA_SUPPLIERS = [
    ("杭州越海跨境供应链有限公司", "Services"),
    ("东莞蓝鲸电子科技有限公司", "Electrical"),
    ("青岛北辰家居制品有限公司", "Hardware"),
    ("厦门云帆包装有限公司", "Raw Material"),
    ("上海星途广告服务有限公司", "Services"),
    ("深圳前海海外仓服务有限公司", "Services"),
]


EXTRA_EMPLOYEE_NAMES = [
    ("EMP-CN-OPS-006", "刘海宁", "Operations"),
    ("EMP-CN-OPS-007", "周文博", "Operations"),
    ("EMP-CN-CS-008", "孙佳琪", "Customer Service"),
    ("EMP-CN-CS-009", "何雨桐", "Customer Service"),
    ("EMP-CN-FIN-010", "郭雪", "Finance"),
    ("EMP-CN-FIN-011", "唐明", "Finance"),
    ("EMP-CN-WH-012", "马俊杰", "Warehouse"),
    ("EMP-CN-MKT-013", "林可欣", "Marketing"),
    ("EMP-CN-OPS-014", "吴子涵", "Operations"),
    ("EMP-CN-CS-015", "郑雅雯", "Customer Service"),
]


def _expanded_items() -> list[tuple[str, str, float]]:
    items = list(ITEMS)
    for index, name in enumerate(EXTRA_ITEM_NAMES, start=13):
        items.append((f"AMZ-BULK-SKU-{index:03d}", name, round(15.5 + index * 2.35, 2)))
    return items


def _expanded_orders() -> list[dict]:
    orders = list(ORDERS)
    markets = list(EXTRA_CUSTOMER_NAMES)
    items = _expanded_items()
    for index in range(1, 121):
        market = markets[(index - 1) % len(markets)]
        customer = EXTRA_CUSTOMER_NAMES[market][(index - 1) % 4]
        item_code = items[(index + 5) % len(items)][0]
        day = ((index - 1) % 28) + 1
        due_day = min(day + 12, 28)
        qty = (index % 4) + 1
        station_no = 100 + index
        tail = 7000000 + index * 137
        order_no = f"AMZ-{market}-{station_no:03d}-{tail:07d}-{1200000 + index:07d}"
        tracking_prefix = {
            "US": "1ZBULKUS",
            "DE": "DHL-DE-BULK",
            "JP": "YAMATO-JP-BULK",
            "UK": "ROYAL-UK-BULK",
            "CA": "CP-CA-BULK",
            "FR": "LA-POSTE-FR-BULK",
            "AU": "AUSPOST-BULK",
            "ES": "CORREOS-ES-BULK",
            "IT": "POSTE-IT-BULK",
        }[market]
        orders.append(
            {
                "market": market,
                "customer": customer,
                "po_no": order_no,
                "item": item_code,
                "qty": qty,
                "date": f"2026-06-{day:02d}",
                "due": f"2026-08-{due_day:02d}",
                "tracking": f"{tracking_prefix}-202606{day:02d}-{index:04d}",
                "issue": EXTRA_ISSUES[(index - 1) % len(EXTRA_ISSUES)],
            }
        )
    return orders


def _expanded_suppliers() -> list[tuple[str, str]]:
    return [*SUPPLIERS, *EXTRA_SUPPLIERS]


def _expanded_purchases() -> list[tuple]:
    purchases = list(PURCHASES)
    suppliers = _expanded_suppliers()
    items = _expanded_items()
    for index in range(1, 41):
        supplier = suppliers[(index - 1) % len(suppliers)][0]
        item_code = items[(index + 8) % len(items)][0]
        qty = 8 + (index % 12) * 3
        rate = round(_item_rate(item_code) * 0.46, 2)
        day = ((index - 1) % 28) + 1
        purchases.append((f"PI-AMZ-BULK-202606-{index:03d}", supplier, item_code, qty, rate, f"2026-06-{day:02d}"))
    return purchases


def _expanded_employees() -> list[tuple[str, str, str]]:
    return [*EMPLOYEES, *EXTRA_EMPLOYEE_NAMES]


def _expanded_salary_slips() -> list[tuple]:
    slips = list(SALARY_SLIPS)
    for month in (5, 6):
        for index, (employee_id, employee_name, _department) in enumerate(_expanded_employees(), start=1):
            gross_pay = 7600 + index * 530 + month * 80
            net_pay = round(gross_pay * 0.82, 2)
            slips.append(
                (
                    f"SAL-AMZ-2026{month:02d}-{index:03d}",
                    employee_id,
                    employee_name,
                    gross_pay,
                    net_pay,
                    f"2026-{month:02d}-01",
                    f"2026-{month:02d}-28",
                )
            )
    return slips


def seed_company_rag_rich_demo_data() -> None:
    import frappe

    company = _first_value("Company", "name") or "xiang"
    customer_group = _first_value("Customer Group", "name") or "Commercial"
    territory = _first_value("Territory", "name") or "Rest Of The World"
    item_group = "Products" if frappe.db.exists("Item Group", "Products") else "All Item Groups"
    warehouse = _first_value("Warehouse", "name", {"company": company, "is_group": 0})
    receivable = _account(company, "Receivable", "Asset") or _first_account(company, "Asset")
    payable = _account(company, "Payable", "Liability") or _first_account(company, "Liability")
    bank = _account(company, "Bank", "Asset") or _account(company, "Cash", "Asset") or _first_account(company, "Asset")
    expense = _first_account(company, "Expense")
    income = _first_account(company, "Income")
    cost_center = _first_value("Cost Center", "name", {"is_group": 0})

    created = {
        "items": [],
        "item_prices": [],
        "customers": [],
        "sales_orders": [],
        "delivery_notes": [],
        "sales_invoices": [],
        "issues": [],
        "suppliers": [],
        "purchase_invoices": [],
        "payment_entries": [],
        "employees": [],
        "salary_slips": [],
        "gl_entries": [],
        "errors": [],
    }

    _ensure_issue_type()
    _ensure_salary_slip_doctype()

    all_items = _expanded_items()
    all_orders = _expanded_orders()
    all_suppliers = _expanded_suppliers()
    all_purchases = _expanded_purchases()
    all_employees = _expanded_employees()
    all_salary_slips = _expanded_salary_slips()

    for item_code, item_name, rate in all_items:
        _safe(created, "items", item_code, lambda: _ensure_item(item_code, item_name, item_group))
        _safe(created, "item_prices", item_code, lambda: _ensure_item_price(item_code, rate))

    for order in all_orders:
        customer = _safe(
            created,
            "customers",
            order["customer"],
            lambda order=order: _ensure_customer(order["customer"], customer_group, territory),
        )
        if not customer:
            continue

        _safe(
            created,
            "sales_orders",
            order["po_no"],
            lambda order=order, customer=customer: _ensure_sales_order(company, customer, order, warehouse),
        )
        _safe(
            created,
            "delivery_notes",
            order["tracking"],
            lambda order=order, customer=customer: _ensure_delivery_note(company, customer, order, warehouse),
        )
        _safe(
            created,
            "sales_invoices",
            order["po_no"],
            lambda order=order, customer=customer: _ensure_sales_invoice(company, customer, order, receivable, income, cost_center),
        )
        _safe(
            created,
            "issues",
            order["po_no"],
            lambda order=order, customer=customer: _ensure_issue(customer, order),
        )
        _safe(
            created,
            "payment_entries",
            f"PAY-{order['po_no']}",
            lambda order=order, customer=customer: _ensure_customer_payment(company, customer, order, receivable, bank),
        )

    for supplier_name, supplier_group in all_suppliers:
        _safe(created, "suppliers", supplier_name, lambda supplier_name=supplier_name, supplier_group=supplier_group: _ensure_supplier(supplier_name, supplier_group))

    for purchase in all_purchases:
        _safe(
            created,
            "purchase_invoices",
            purchase[0],
            lambda purchase=purchase: _ensure_purchase_invoice(company, purchase, payable, expense, cost_center),
        )
        _safe(
            created,
            "payment_entries",
            f"PAY-{purchase[0]}",
            lambda purchase=purchase: _ensure_supplier_payment(company, purchase, payable, bank),
        )

    for employee in all_employees:
        _safe(created, "employees", employee[0], lambda employee=employee: _ensure_employee(company, employee))

    for salary in all_salary_slips:
        _safe(created, "salary_slips", salary[0], lambda salary=salary: _ensure_salary_slip(company, salary))

    for order in all_orders:
        _safe(
            created,
            "gl_entries",
            f"GL-{order['po_no']}",
            lambda order=order: _ensure_sales_gl_entries(company, order, receivable, income, cost_center),
        )

    for purchase in all_purchases:
        _safe(
            created,
            "gl_entries",
            f"GL-{purchase[0]}",
            lambda purchase=purchase: _ensure_purchase_gl_entries(company, purchase, payable, expense, cost_center),
        )

    frappe.db.commit()
    print(json.dumps(created, ensure_ascii=False, indent=2))


def _safe(created: dict, key: str, label: str, func):
    try:
        value = func()
        created[key].append(value or label)
        return value or label
    except Exception as exc:  # noqa: BLE001 - seed should keep going and report all failures.
        created["errors"].append({"section": key, "label": label, "error": str(exc)})
        return None


def _ensure_item(item_code: str, item_name: str, item_group: str) -> str:
    import frappe

    payload = {
        "item_name": item_name,
        "item_group": item_group,
        "stock_uom": "Nos",
        "is_stock_item": 0,
    }
    if frappe.db.exists("Item", item_code):
        doc = frappe.get_doc("Item", item_code)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc({"doctype": "Item", "item_code": item_code, **payload})
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_item_price(item_code: str, rate: float) -> str:
    import frappe

    existing = frappe.db.exists("Item Price", {"item_code": item_code, "price_list": "Standard Selling"})
    payload = {"price_list_rate": rate, "currency": "CNY"}
    if existing:
        doc = frappe.get_doc("Item Price", existing)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Item Price",
            "item_code": item_code,
            "price_list": "Standard Selling",
            **payload,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


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


def _ensure_sales_order(company: str, customer: str, order: dict, warehouse: str | None) -> str:
    import frappe

    existing = frappe.db.exists("Sales Order", {"po_no": order["po_no"]})
    if existing:
        return existing

    item_row = {
        "item_code": order["item"],
        "qty": order["qty"],
        "rate": _item_rate(order["item"]),
        "delivery_date": order["due"],
    }
    if warehouse:
        item_row["warehouse"] = warehouse

    doc = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "company": company,
            "customer": customer,
            "transaction_date": order["date"],
            "delivery_date": order["due"],
            "currency": "CNY",
            "selling_price_list": "Standard Selling",
            "po_no": order["po_no"],
            "items": [item_row],
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_delivery_note(company: str, customer: str, order: dict, warehouse: str | None) -> str:
    import frappe

    existing = frappe.db.exists("Delivery Note", {"lr_no": order["tracking"]})
    if existing:
        return existing

    item_row = {"item_code": order["item"], "qty": order["qty"], "rate": _item_rate(order["item"])}
    if warehouse:
        item_row["warehouse"] = warehouse

    doc = frappe.get_doc(
        {
            "doctype": "Delivery Note",
            "company": company,
            "customer": customer,
            "posting_date": order["date"],
            "posting_time": "10:30:00",
            "currency": "CNY",
            "lr_no": order["tracking"],
            "title": f"亚马逊订单 {order['po_no']} / {order['market']} 站",
            "items": [item_row],
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_sales_invoice(
    company: str,
    customer: str,
    order: dict,
    receivable: str | None,
    income: str | None,
    cost_center: str | None,
) -> str:
    import frappe

    existing = frappe.db.exists("Sales Invoice", {"po_no": order["po_no"]})
    if existing:
        return existing

    item = {"item_code": order["item"], "qty": order["qty"], "rate": _item_rate(order["item"])}
    if income:
        item["income_account"] = income
    if cost_center:
        item["cost_center"] = cost_center

    payload = {
        "doctype": "Sales Invoice",
        "company": company,
        "customer": customer,
        "posting_date": order["date"],
        "due_date": order["due"],
        "currency": "CNY",
        "selling_price_list": "Standard Selling",
        "po_no": order["po_no"],
        "items": [item],
    }
    if receivable:
        payload["debit_to"] = receivable

    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_issue(customer: str, order: dict) -> str:
    import frappe

    subject = f"{order['po_no']} {order['issue'][:28]}"
    existing = frappe.db.exists("Issue", {"subject": subject})
    if existing:
        doc = frappe.get_doc("Issue", existing)
        doc.description = _issue_description(order)
        doc.save(ignore_permissions=True)
        return doc.name

    priority = "High" if any(word in order["issue"] for word in ["退款", "退货", "差评"]) else "Medium"
    doc = frappe.get_doc(
        {
            "doctype": "Issue",
            "subject": subject,
            "customer": customer,
            "status": "Open",
            "priority": priority,
            "issue_type": "Amazon After-sales",
            "description": _issue_description(order),
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _issue_description(order: dict) -> str:
    return (
        f"亚马逊订单号：{order['po_no']}\n"
        f"站点：{order['market']}\n"
        f"物流单号：{order['tracking']}\n"
        f"客户问题：{order['issue']}\n"
        "客服建议：先安抚客户，确认照片/视频证据，再按金额和风险判断补发、部分退款或转人工。"
    )


def _ensure_supplier(supplier_name: str, supplier_group: str) -> str:
    import frappe

    group = supplier_group if frappe.db.exists("Supplier Group", supplier_group) else "All Supplier Groups"
    if frappe.db.exists("Supplier", supplier_name):
        doc = frappe.get_doc("Supplier", supplier_name)
        doc.supplier_group = group
        doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": group,
            "supplier_type": "Company",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_purchase_invoice(
    company: str,
    purchase: tuple,
    payable: str | None,
    expense: str | None,
    cost_center: str | None,
) -> str:
    import frappe

    bill_no, supplier, item_code, qty, rate, posting_date = purchase
    existing = frappe.db.exists("Purchase Invoice", {"bill_no": bill_no})
    if existing:
        return existing

    item = {"item_code": item_code, "qty": qty, "rate": rate}
    if expense:
        item["expense_account"] = expense
    if cost_center:
        item["cost_center"] = cost_center

    payload = {
        "doctype": "Purchase Invoice",
        "company": company,
        "supplier": supplier,
        "posting_date": posting_date,
        "due_date": "2026-08-05",
        "currency": "CNY",
        "bill_no": bill_no,
        "bill_date": posting_date,
        "items": [item],
    }
    if payable:
        payload["credit_to"] = payable

    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_customer_payment(company: str, customer: str, order: dict, receivable: str | None, bank: str | None) -> str | None:
    import frappe

    if not receivable or not bank:
        return None
    reference_no = f"PAY-{order['po_no']}"
    existing = frappe.db.exists("Payment Entry", {"reference_no": reference_no})
    if existing:
        return existing

    amount = round(_item_rate(order["item"]) * order["qty"], 2)
    doc = frappe.get_doc(
        {
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "company": company,
            "posting_date": order["date"],
            "party_type": "Customer",
            "party": customer,
            "paid_from": receivable,
            "paid_to": bank,
            "paid_amount": amount,
            "received_amount": amount,
            "paid_from_account_currency": "CNY",
            "paid_to_account_currency": "CNY",
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "reference_no": reference_no,
            "reference_date": order["date"],
            "remarks": f"亚马逊订单收款：{order['po_no']} / {order['market']} 站",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_supplier_payment(company: str, purchase: tuple, payable: str | None, bank: str | None) -> str | None:
    import frappe

    if not payable or not bank:
        return None
    bill_no, supplier, _item_code, qty, rate, posting_date = purchase
    reference_no = f"PAY-{bill_no}"
    existing = frappe.db.exists("Payment Entry", {"reference_no": reference_no})
    if existing:
        return existing

    amount = round(qty * rate, 2)
    doc = frappe.get_doc(
        {
            "doctype": "Payment Entry",
            "payment_type": "Pay",
            "company": company,
            "posting_date": posting_date,
            "party_type": "Supplier",
            "party": supplier,
            "paid_from": bank,
            "paid_to": payable,
            "paid_amount": amount,
            "received_amount": amount,
            "paid_from_account_currency": "CNY",
            "paid_to_account_currency": "CNY",
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "reference_no": reference_no,
            "reference_date": posting_date,
            "remarks": f"供应商付款：{supplier} / {bill_no}",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_employee(company: str, employee: tuple) -> str:
    import frappe

    employee_id, employee_name, department = employee
    if frappe.db.exists("Employee", employee_id):
        doc = frappe.get_doc("Employee", employee_id)
        doc.employee_name = employee_name
        doc.status = "Active"
        doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Employee",
            "name": employee_id,
            "employee": employee_id,
            "employee_name": employee_name,
            "first_name": employee_name,
            "company": company,
            "status": "Active",
            "gender": "Other",
            "date_of_birth": "1993-01-01",
            "date_of_joining": "2024-01-01",
            "department": department if frappe.db.exists("Department", department) else None,
        }
    )
    doc.insert(ignore_permissions=True, ignore_mandatory=True)
    return doc.name


def _ensure_salary_slip(company: str, salary: tuple) -> str:
    import frappe

    slip_name, employee_id, employee_name, gross_pay, net_pay, start_date, end_date = salary
    existing = frappe.db.exists("Salary Slip", slip_name) or frappe.db.exists("Salary Slip", {"employee": employee_id, "start_date": start_date, "end_date": end_date})
    if existing:
        doc = frappe.get_doc("Salary Slip", existing)
        doc.employee_name = employee_name
        doc.gross_pay = gross_pay
        doc.net_pay = net_pay
        doc.flags.ignore_mandatory = True
        doc.save(ignore_permissions=True)
        return doc.name

    doc = frappe.get_doc(
        {
            "doctype": "Salary Slip",
            "name": slip_name,
            "employee": employee_id,
            "employee_name": employee_name,
            "company": company,
            "posting_date": "2026-07-31",
            "start_date": start_date,
            "end_date": end_date,
            "gross_pay": gross_pay,
            "net_pay": net_pay,
            "status": "Draft",
        }
    )
    doc.insert(ignore_permissions=True, ignore_mandatory=True)
    return doc.name


def _ensure_sales_gl_entries(company: str, order: dict, receivable: str | None, income: str | None, cost_center: str | None) -> list[str]:
    amount = round(_item_rate(order["item"]) * order["qty"], 2)
    voucher_no = _first_value("Sales Invoice", "name", {"po_no": order["po_no"]})
    if not voucher_no:
        return []
    names = []
    if receivable:
        names.append(_ensure_gl_entry(
            company,
            order["date"],
            receivable,
            amount,
            0,
            "Sales Invoice",
            voucher_no,
            cost_center,
            f"应收账款 / {order['customer']}",
            party_type="Customer",
            party=order["customer"],
        ))
    if income:
        names.append(_ensure_gl_entry(company, order["date"], income, 0, amount, "Sales Invoice", voucher_no, cost_center, f"销售收入 / {order['market']} 站"))
    return names


def _ensure_purchase_gl_entries(company: str, purchase: tuple, payable: str | None, expense: str | None, cost_center: str | None) -> list[str]:
    bill_no, supplier, _item_code, qty, rate, posting_date = purchase
    amount = round(qty * rate, 2)
    voucher_no = _first_value("Purchase Invoice", "name", {"bill_no": bill_no})
    if not voucher_no:
        return []
    names = []
    if expense:
        names.append(_ensure_gl_entry(company, posting_date, expense, amount, 0, "Purchase Invoice", voucher_no, cost_center, f"采购成本 / {supplier}"))
    if payable:
        names.append(_ensure_gl_entry(
            company,
            posting_date,
            payable,
            0,
            amount,
            "Purchase Invoice",
            voucher_no,
            cost_center,
            f"应付账款 / {supplier}",
            party_type="Supplier",
            party=supplier,
        ))
    return names


def _ensure_gl_entry(
    company: str,
    posting_date: str,
    account: str,
    debit: float,
    credit: float,
    voucher_type: str,
    voucher_no: str,
    cost_center: str | None,
    against: str,
    party_type: str | None = None,
    party: str | None = None,
) -> str:
    import frappe

    existing = frappe.db.exists(
        "GL Entry",
        {
            "company": company,
            "posting_date": posting_date,
            "account": account,
            "voucher_type": voucher_type,
            "voucher_no": voucher_no,
            "debit": debit,
            "credit": credit,
        },
    )
    if existing:
        return existing

    payload = {
        "doctype": "GL Entry",
        "company": company,
        "posting_date": posting_date,
        "account": account,
        "debit": debit,
        "credit": credit,
        "debit_in_account_currency": debit,
        "credit_in_account_currency": credit,
        "voucher_type": voucher_type,
        "voucher_no": voucher_no,
        "against": against,
        "is_opening": "No",
        "fiscal_year": _fiscal_year(posting_date),
    }
    if cost_center:
        payload["cost_center"] = cost_center
    if party_type and party:
        payload["party_type"] = party_type
        payload["party"] = party

    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True, ignore_mandatory=True)
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


def _ensure_salary_slip_doctype() -> None:
    import frappe

    if frappe.db.exists("DocType", "Salary Slip"):
        return

    doc = frappe.get_doc(
        {
            "doctype": "DocType",
            "name": "Salary Slip",
            "module": "Custom",
            "custom": 1,
            "istable": 0,
            "editable_grid": 0,
            "track_changes": 1,
            "fields": [
                {"fieldname": "employee", "label": "员工编号", "fieldtype": "Data", "in_list_view": 1},
                {"fieldname": "employee_name", "label": "员工姓名", "fieldtype": "Data", "in_list_view": 1},
                {"fieldname": "company", "label": "公司", "fieldtype": "Link", "options": "Company"},
                {"fieldname": "posting_date", "label": "过账日期", "fieldtype": "Date"},
                {"fieldname": "start_date", "label": "开始日期", "fieldtype": "Date", "in_list_view": 1},
                {"fieldname": "end_date", "label": "结束日期", "fieldtype": "Date"},
                {"fieldname": "gross_pay", "label": "应发工资", "fieldtype": "Currency", "in_list_view": 1},
                {"fieldname": "net_pay", "label": "实发工资", "fieldtype": "Currency", "in_list_view": 1},
                {"fieldname": "status", "label": "状态", "fieldtype": "Select", "options": "Draft\nSubmitted\nPaid", "default": "Draft", "in_list_view": 1},
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
                {"role": "HR Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
                {"role": "Accounts Manager", "read": 1, "write": 1, "create": 1},
            ],
        }
    )
    doc.insert(ignore_permissions=True)


def _item_rate(item_code: str) -> float:
    for code, _name, rate in _expanded_items():
        if code == item_code:
            return float(rate)
    return 1.0


def _account(company: str, account_type: str, root_type: str) -> str | None:
    import frappe

    values = frappe.db.get_all(
        "Account",
        filters={"company": company, "account_type": account_type, "root_type": root_type, "is_group": 0},
        pluck="name",
        limit=1,
    )
    return values[0] if values else None


def _first_account(company: str, root_type: str) -> str | None:
    import frappe

    values = frappe.db.get_all(
        "Account",
        filters={"company": company, "root_type": root_type, "is_group": 0},
        pluck="name",
        limit=1,
    )
    return values[0] if values else None


def _first_value(doctype: str, fieldname: str, filters: dict | None = None) -> str | None:
    import frappe

    values = frappe.db.get_all(doctype, filters=filters, pluck=fieldname, limit=1)
    return values[0] if values else None


def _fiscal_year(posting_date: str) -> str:
    parsed = date.fromisoformat(posting_date)
    return str(parsed.year)
