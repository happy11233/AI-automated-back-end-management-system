"""ERPNext-only, idempotent synthetic crossborder fixture.

Run seed with bench execute after copying this module into the bench directory.
60 own SKUs live in Item; 40 competitor observations never affect stock/GL.
All identities, prices, FX rates and observations are explicitly synthetic.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

BATCH = "CB-DEMO-20261021"
COMPANY = "Crossborder Demo 2026"
ABBR = "CBD26"
AS_OF = date(2026, 10, 21)
MARKETS = [("US", "USD", "English", "7.10", "1"), ("DE", "EUR", "German", "7.80", "0.93"), ("JP", "JPY", "Japanese", "0.048", "151")]
CATEGORIES = [
    ("CABLE", "编织 USB-C 数据线", "Braided USB-C Cable", "12.99", "3.40"),
    ("LAMP", "LED 护眼台灯", "LED Desk Lamp", "34.99", "11.20"),
    ("BOTTLE", "不锈钢保温杯", "Insulated Bottle", "24.99", "6.80"),
    ("STAND", "折叠电脑支架", "Laptop Stand", "29.99", "8.60"),
    ("BAG", "旅行收纳包", "Travel Organizer", "18.99", "4.90"),
    ("FEEDER", "宠物自动喂食器", "Pet Feeder", "59.99", "22.50"),
    ("MAT", "防滑瑜伽垫", "Yoga Mat", "32.99", "9.80"),
    ("GRINDER", "便携咖啡研磨机", "Coffee Grinder", "39.99", "13.20"),
    ("PUMP", "便携充气泵", "Air Pump", "44.99", "15.80"),
    ("HUB", "USB-C 扩展坞", "USB-C Hub", "49.99", "17.40"),
]


def money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def products():
    rows = []
    for i in range(60):
        market, currency, language, fx, factor = MARKETS[i % 3]
        cat = CATEGORIES[(i // 3) % 10]
        model = i // 30 + 1
        rows.append(dict(index=i, sku=f"CB-OWN-{market}-{cat[0]}-{i+1:03d}",
            product_name=f"[模拟·我方] {cat[1]} {market} V{model}",
            english_name=f"AsterDemo {cat[2]} V{model}", market=market, currency=currency,
            language=language, fx=float(fx), price=money((Decimal(cat[3])+4*(model-1))*Decimal(factor)),
            cost=money(Decimal(cat[4])*Decimal("7.10")),
            stock=0 if i in (0,20) else (5 if i % 13 == 0 else 80+i*3),
            warehouse=f"CB Demo {market} Warehouse - {ABBR}", price_list=f"CB Demo {currency}",
            asin=f"D{i+1:09d}", rating=money(4.1+(i % 8)/10), review_count=40+i*17,
            features=f"模拟商品；{cat[2]}；V{model}；{language}说明书；30天模拟退货政策；不可真实销售"))
    return rows


def ensure(doctype, name, values):
    import frappe
    if frappe.db.exists(doctype, name):
        return frappe.get_doc(doctype, name)
    doc = frappe.get_doc(dict(doctype=doctype, **values))
    doc.insert(ignore_permissions=True, set_name=name)
    return doc


def f(name, label, kind="Data", **kwargs):
    return dict(fieldname=name, label=label, fieldtype=kind, **kwargs)


def create_doctypes():
    import frappe
    definitions = {
        "Crossborder Product": [f("item_code","我方SKU","Link",options="Item",reqd=1,in_list_view=1), f("product_name","商品名称",in_list_view=1), f("market","站点",in_list_view=1), f("brand","品牌"), f("store","店铺"), f("asin","模拟ASIN"), f("currency","币种","Link",options="Currency"), f("selling_price","售价","Currency",options="currency",in_list_view=1), f("rating","评分","Float"), f("review_count","评价数","Int"), f("language","语言"), f("features","卖点与政策","Small Text")],
        "Competitor Product": [f("own_item_code","关联我方SKU","Link",options="Item",reqd=1,in_list_view=1), f("product_name","竞品名称",in_list_view=1), f("brand","模拟品牌"), f("market","站点",in_list_view=1), f("asin","模拟ASIN"), f("currency","币种","Link",options="Currency"), f("price","观察售价","Currency",options="currency",in_list_view=1), f("rating","评分","Float"), f("review_count","评价数","Int"), f("estimated_monthly_sales","模拟月销量","Int"), f("fulfillment","配送方式"), f("observed_date","观察日期","Date"), f("product_url","模拟链接"), f("strengths","模拟优势","Small Text"), f("weaknesses","模拟短板","Small Text"), f("data_source","数据来源")],
        "Marketplace Settlement": [f("order_no","平台订单号",reqd=1,in_list_view=1), f("sales_invoice","销售发票","Link",options="Sales Invoice"), f("payment_entry","收款单","Link",options="Payment Entry"), f("item_code","SKU","Link",options="Item"), f("market","站点"), f("settlement_date","结算日期","Date"), f("currency","币种","Link",options="Currency"), *[f(k,label,"Currency",options="currency") for k,label in [("gross_amount","销售总额"),("refund_amount","退款"),("platform_fee","平台佣金"),("fulfillment_fee","履约费"),("expected_payout","预计净回款"),("actual_payout","模拟实际回款"),("difference","待核差额")]], f("exchange_rate","模拟折人民币汇率","Float",precision="6"), f("status","核对状态","Select",options="Matched\nMismatch\nPending",in_list_view=1), f("note","说明","Small Text")],
        "Ad Campaign Daily": [f("campaign_name","广告活动",in_list_view=1), f("item_code","SKU","Link",options="Item",in_list_view=1), f("market","站点"), f("report_date","日期","Date",in_list_view=1), f("currency","币种","Link",options="Currency"), *[f(k,label,"Int") for k,label in [("impressions","曝光"),("clicks","点击"),("ad_orders","广告订单")]], f("spend","花费","Currency",options="currency"), f("ad_sales","归因销售额","Currency",options="currency"), f("acos","ACOS百分比","Percent"), f("roas","ROAS","Float")],
        "Shipment Tracking": [f("order_no","平台订单号",reqd=1,in_list_view=1), f("sales_order","销售订单","Link",options="Sales Order"), f("delivery_note","发货单","Link",options="Delivery Note"), f("tracking_no","模拟运单号",in_list_view=1), f("carrier","承运商"), f("market","站点"), f("shipped_date","发货日期","Date"), f("estimated_delivery","预计送达","Date"), f("status","物流状态","Select",options="In Transit\nDelivered\nDelayed\nException",in_list_view=1), f("last_event","最新轨迹","Small Text")],
    }
    for dt, fields in definitions.items():
        if frappe.db.exists("DocType", dt):
            continue
        roles = ["System Manager","Accounts User","Auditor"] if dt == "Marketplace Settlement" else ["System Manager","Sales User","Stock User","Support Team"]
        frappe.get_doc(dict(doctype="DocType",name=dt,module="Custom",custom=1,autoname="prompt",
            fields=fields+[f("demo_batch","模拟批次",reqd=1),f("is_simulated","模拟数据","Check",default="1")],
            permissions=[dict(role=role,read=1,write=int(role=="System Manager"),create=int(role=="System Manager"),report=1,export=1) for role in roles])).insert(ignore_permissions=True)
    frappe.clear_cache()


def seed_catalog():
    import frappe
    frappe.set_user("Administrator")
    create_doctypes()
    if not frappe.db.exists("Company",COMPANY):
        frappe.get_doc(dict(doctype="Company",company_name=COMPANY,abbr=ABBR,default_currency="CNY",country="China",chart_of_accounts="Standard",create_chart_of_accounts_based_on="Standard Template")).insert(ignore_permissions=True)
    for market,currency,*_ in MARKETS:
        frappe.db.set_value("Currency",currency,"enabled",1)
        ensure("Price List",f"CB Demo {currency}",dict(price_list_name=f"CB Demo {currency}",currency=currency,selling=1,buying=0,enabled=1))
        ensure("Warehouse",f"CB Demo {market} Warehouse - {ABBR}",dict(warehouse_name=f"CB Demo {market} Warehouse",company=COMPANY,is_group=0))
    group = "Products" if frappe.db.exists("Item Group","Products") else "All Item Groups"
    for p in products():
        ensure("Item",p["sku"],dict(item_code=p["sku"],item_name=p["product_name"],item_group=group,stock_uom="Nos",is_stock_item=1,valuation_rate=p["cost"],description=f"{p['features']} | Amazon {p['market']} Demo Store | {p['currency']} {p['price']} | {BATCH}"))
        ensure("Item Price",f"CB-PRICE-{p['index']+1:03d}",dict(item_code=p["sku"],price_list=p["price_list"],currency=p["currency"],price_list_rate=p["price"],valid_from="2026-10-01"))
        ensure("Crossborder Product",f"CB-PRODUCT-{p['index']+1:03d}",dict(item_code=p["sku"],product_name=p["product_name"],brand="AsterDemo",market=p["market"],store=f"Amazon {p['market']} Demo Store",asin=p["asin"],currency=p["currency"],selling_price=p["price"],rating=p["rating"],review_count=p["review_count"],language=p["language"],features=p["features"],demo_batch=BATCH,is_simulated=1))
    for i,p in enumerate(products()[:40]):
        ensure("Competitor Product",f"CB-COMP-{i+1:03d}",dict(own_item_code=p["sku"],product_name=f"[模拟·竞品] RivalDemo {p['english_name']}",brand=f"RivalDemo-{i%5+1}",market=p["market"],asin=f"R{i+1:09d}",currency=p["currency"],price=money(p["price"]*(.82+(i%7)*.055)),rating=money(3.8+(i%11)/10),review_count=80+i*31,estimated_monthly_sales=100+i*23,fulfillment="FBA" if i%3 else "FBM",observed_date=str(AS_OF),product_url=f"https://example.invalid/competitor/{i+1}",strengths="模拟：评价较多、价格优惠",weaknesses="模拟：包装和配件投诉",data_source="synthetic fixture; no scraping",demo_batch=BATCH,is_simulated=1))
    frappe.db.commit()
    print(json.dumps(dict(own_products=frappe.db.count("Item",{"item_code":["like","CB-OWN-%"]}),competitor_products=frappe.db.count("Competitor Product",{"demo_batch":BATCH})),ensure_ascii=False))


def account(**filters):
    import frappe
    name = frappe.db.get_value("Account",dict(company=COMPANY,is_group=0,**filters),"name")
    if not name:
        raise RuntimeError(f"Required account missing: {filters}")
    return name


def seed_business():
    """Use native ERPNext validation/submit; never manufacture GL or Bin rows."""
    import frappe
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    frappe.set_user("Administrator")
    if not frappe.db.exists("Company",COMPANY):
        raise RuntimeError("Run seed_catalog first")
    ar = account(account_type="Receivable")
    ap = account(account_type="Payable")
    cash = account(account_type="Cash")
    income = account(root_type="Income")
    expense = account(root_type="Expense")
    # Opening Stock requires a balance-sheet opening balance account.
    opening = account(account_type="Temporary",root_type="Asset")
    cc = frappe.db.get_value("Cost Center",{"company":COMPANY,"is_group":0},"name")
    ar_parent = frappe.db.get_value("Account",ar,"parent_account")
    receivable_by_currency = {"CNY": ar}
    for market,currency,*_ in MARKETS:
        if frappe.db.exists("Account",{"company":COMPANY,"account_currency":currency,"account_type":"Receivable","is_group":0}):
            receivable_by_currency[currency] = frappe.db.get_value("Account",{"company":COMPANY,"account_currency":currency,"account_type":"Receivable","is_group":0},"name")
            continue
        account_name = f"CB Receivable {currency}"
        existing = frappe.db.get_value("Account",{"company":COMPANY,"account_name":account_name},"name")
        if existing:
            receivable_by_currency[currency] = existing
        else:
            currency_account = frappe.get_doc(dict(doctype="Account",account_name=account_name,company=COMPANY,parent_account=ar_parent,root_type="Asset",account_type="Receivable",account_currency=currency,is_group=0)).insert(ignore_permissions=True)
            receivable_by_currency[currency] = currency_account.name
    frappe.db.commit()
    if not frappe.db.exists("Fiscal Year",{"year_start_date":["<=",str(AS_OF)],"year_end_date":[">=",str(AS_OF)]}):
        ensure("Fiscal Year","CB Demo FY 2026",dict(year="CB Demo FY 2026",year_start_date="2026-01-01",year_end_date="2026-12-31"))
    for market,*_ in MARKETS:
        name = f"CB-OPENING-{market}-20261001"
        if not frappe.db.exists("Stock Reconciliation",name):
            doc = ensure("Stock Reconciliation",name,dict(company=COMPANY,purpose="Opening Stock",posting_date="2026-10-01",posting_time="09:00:00",set_posting_time=1,expense_account=opening,cost_center=cc,items=[dict(item_code=p["sku"],warehouse=p["warehouse"],qty=p["stock"],valuation_rate=p["cost"]) for p in products() if p["market"]==market and p["stock"]>0]))
            doc.submit()
            frappe.db.commit()
    customer_group = frappe.db.get_value("Customer Group",{"is_group":0},"name") or "All Customer Groups"
    territory = frappe.db.get_value("Territory",{"is_group":0},"name") or "All Territories"
    supplier_group = frappe.db.get_value("Supplier Group",{"is_group":0},"name") or "All Supplier Groups"
    ensure("Issue Type","CB Demo After-sales",dict(issue_type="CB Demo After-sales"))
    for i in range(6):
        ensure("Supplier",f"CB Demo Supplier {i+1:02d}",dict(supplier_name=f"CB Demo Supplier {i+1:02d}",supplier_type="Company",supplier_group=supplier_group))
    for i,p in enumerate(products()):
        day = AS_OF-timedelta(days=i%20)
        due = day+timedelta(days=5)
        qty = i%3+1
        buyer = f"CB Demo {p['market']} Buyer {i%30+1:03d}"
        customer_doc = ensure("Customer",buyer,dict(customer_name=buyer,customer_group=customer_group,territory=territory,customer_type="Individual"))
        customer_doc.default_currency = p["currency"]
        customer_accounts = [row for row in customer_doc.accounts if row.company == COMPANY]
        if customer_accounts:
            customer_accounts[0].account = receivable_by_currency[p["currency"]]
        else:
            customer_doc.append("accounts", {"company": COMPANY, "account": receivable_by_currency[p["currency"]]})
        customer_doc.save(ignore_permissions=True)
        order_no = f"AMZ-{p['market']}-900-{i+1:07d}-2026101"
        common = dict(company=COMPANY,customer=buyer,currency=p["currency"],conversion_rate=p["fx"],selling_price_list=p["price_list"],price_list_currency=p["currency"],plc_conversion_rate=p["fx"],ignore_pricing_rule=1,po_no=order_no)
        so = ensure("Sales Order",f"CB-SO-{i+1:04d}",dict(**common,transaction_date=str(day),delivery_date=str(due),items=[dict(item_code=p["sku"],qty=qty,rate=p["price"],delivery_date=str(due),warehouse=p["warehouse"]) ]))
        if so.docstatus==0:
            so.submit()
        si = ensure("Sales Invoice",f"CB-SI-{i+1:04d}",dict(**common,posting_date=str(day),posting_time="10:00:00",set_posting_time=1,due_date=str(due),debit_to=receivable_by_currency[p["currency"]],items=[dict(item_code=p["sku"],qty=qty,rate=p["price"],sales_order=so.name,so_detail=so.items[0].name,income_account=income,cost_center=cc)]))
        if si.docstatus==0:
            si.submit()
        gross = money(si.grand_total)
        fee = money(gross*.15)
        fulfillment = money(gross*.06)
        refund = money(gross*.2) if i%17==0 else 0
        expected = money(Decimal(str(gross))-Decimal(str(fee))-Decimal(str(fulfillment))-Decimal(str(refund)))
        pending = i%9==0
        diff = money(expected*.03) if i%11==0 and not pending else 0
        actual = 0 if pending else money(expected-diff)
        payment_name = None
        if actual:
            payment_name = f"CB-PAY-{i+1:04d}"
            if not frappe.db.exists("Payment Entry",payment_name):
                pe = get_payment_entry("Sales Invoice",si.name,party_amount=actual,bank_account=cash,bank_amount=money(actual*p["fx"]))
                pe.posting_date = str(day)
                pe.reference_no = f"CB-SET-{i+1:04d}"
                pe.reference_date = str(day)
                pe.remarks = f"[SIMULATED] {BATCH} {order_no}; deductions remain pending review"
                pe.insert(ignore_permissions=True,set_name=payment_name)
                pe.submit()
        ensure("Marketplace Settlement",f"CB-SET-{i+1:04d}",dict(order_no=order_no,sales_invoice=si.name,payment_entry=payment_name,item_code=p["sku"],market=p["market"],settlement_date=str(day),currency=p["currency"],gross_amount=gross,refund_amount=refund,platform_fee=fee,fulfillment_fee=fulfillment,expected_payout=expected,actual_payout=actual,difference=money(expected-actual),exchange_rate=p["fx"],status="Pending" if pending else ("Mismatch" if diff else "Matched"),note="模拟结算和固定模拟汇率；费用及退款为待核记录，未自动冲销应收，待财务审核。",demo_batch=BATCH,is_simulated=1))
        if i<45 and p["stock"]>5:
            dn = ensure("Delivery Note",f"CB-DN-{i+1:04d}",dict(**common,posting_date=str(day),posting_time="11:00:00",set_posting_time=1,lr_no=f"CBTRACK-{p['market']}-{i+1:07d}",title=f"[模拟] {order_no} / Amazon {p['market']} Demo Store",items=[dict(item_code=p["sku"],qty=qty,rate=p["price"],against_sales_order=so.name,so_detail=so.items[0].name,warehouse=p["warehouse"],cost_center=cc)]))
            if dn.docstatus==0:
                dn.submit()
            shipping = "Exception" if i%19==0 else ("Delayed" if i%7==0 else ("Delivered" if (AS_OF-day).days>=5 else "In Transit"))
            ensure("Shipment Tracking",f"CB-SHIP-{i+1:04d}",dict(order_no=order_no,sales_order=so.name,delivery_note=dn.name,tracking_no=dn.lr_no,carrier={"US":"UPS Demo","DE":"DHL Demo","JP":"Yamato Demo"}[p["market"]],market=p["market"],shipped_date=str(day),estimated_delivery=str(due),status=shipping,last_event=f"模拟轨迹：{shipping}；非真实物流",demo_batch=BATCH,is_simulated=1))
        if i<30:
            problem = ["物流延误咨询","商品破损退款申请","配件缺失补发申请","产品使用咨询","退货申请"][i%5]
            ensure("Issue",f"CB-ISSUE-{i+1:04d}",dict(subject=f"[模拟] {order_no} {problem}",customer=buyer,status="Open",priority="High" if i%5 in (1,4) else "Medium",issue_type="CB Demo After-sales",description=f"模拟客服记录；{BATCH}；订单{order_no}；SKU {p['sku']}；语言{p['language']}；{problem}。退款需人工审批，不表示已退款。"))
        ad_orders = 1+i%9
        clicks = 35+i*3
        spend = money(clicks*(.22+(i%6)*.11)*float(MARKETS[i%3][4]))
        sales = money(ad_orders*p["price"])
        ensure("Ad Campaign Daily",f"CB-AD-{i+1:04d}",dict(campaign_name=f"CB Demo {p['market']} Sponsored Products",item_code=p["sku"],market=p["market"],report_date=str(AS_OF-timedelta(days=i//20)),currency=p["currency"],impressions=clicks*35,clicks=clicks,ad_orders=ad_orders,spend=spend,ad_sales=sales,acos=money(spend/sales*100),roas=money(sales/spend),demo_batch=BATCH,is_simulated=1))
        frappe.db.commit()
        print(f"CB seed order {i+1}/60",flush=True)
    for i,p in enumerate(products()[:12]):
        pi = ensure("Purchase Invoice",f"CB-PI-{i+1:04d}",dict(company=COMPANY,supplier=f"CB Demo Supplier {i%6+1:02d}",posting_date="2026-10-02",posting_time="10:00:00",set_posting_time=1,due_date="2026-10-31",bill_no=f"CB-BILL-{i+1:04d}",bill_date="2026-10-02",currency="CNY",conversion_rate=1,credit_to=ap,update_stock=0,remarks=f"[SIMULATED] {BATCH}; no extra stock receipt",items=[dict(item_code=p["sku"],qty=20+i,rate=p["cost"],expense_account=expense,cost_center=cc)]))
        if pi.docstatus==0:
            pi.submit()
        frappe.db.commit()
    return verify()


def verify():
    import frappe
    own = frappe.db.count("Item",{"item_code":["like","CB-OWN-%"]})
    comp = frappe.db.count("Competitor Product",{"demo_batch":BATCH})
    counts = {dt:frappe.db.count(dt,{"demo_batch":BATCH}) for dt in ("Crossborder Product","Competitor Product","Marketplace Settlement","Ad Campaign Daily","Shipment Tracking")}
    counts.update({dt:frappe.db.count(dt,{"company":COMPANY,"docstatus":1}) for dt in ("Sales Order","Sales Invoice","Delivery Note","Purchase Invoice","Payment Entry","Stock Reconciliation")})
    counts["Issue"] = frappe.db.count("Issue",{"name":["like","CB-ISSUE-%"]})
    gl = frappe.db.sql("select sum(debit), sum(credit), count(*) from `tabGL Entry` where company=%s and is_cancelled=0",COMPANY)[0]
    rows = frappe.get_all("Marketplace Settlement",filters={"demo_batch":BATCH},fields=["name","gross_amount","refund_amount","platform_fee","fulfillment_fee","expected_payout","actual_payout","difference"])
    invalid = [r.name for r in rows if abs(money(r.gross_amount-r.refund_amount-r.platform_fee-r.fulfillment_fee)-money(r.expected_payout))>.011 or abs(money(r.expected_payout-r.actual_payout)-money(r.difference))>.011]
    result = dict(batch=BATCH,as_of=str(AS_OF),is_simulated=True,company=COMPANY,own_products=own,competitor_products=comp,total_products=own+comp,counts=counts,gl=dict(debit=money(gl[0] or 0),credit=money(gl[1] or 0),rows=gl[2],balanced=money(gl[0] or 0)==money(gl[1] or 0)),stock_ledger_rows=frappe.db.count("Stock Ledger Entry",{"company":COMPANY,"is_cancelled":0}),invalid_settlements=invalid,sample_sku=products()[1]["sku"],sample_order="AMZ-DE-900-0000002-2026101",note="All data/FX synthetic. Marketplace deductions await financial review. Existing records preserved.")
    result["ok"] = own==60 and comp==40 and counts["Sales Order"]==60 and counts["Sales Invoice"]==60 and counts["Marketplace Settlement"]==60 and counts["Ad Campaign Daily"]==60 and counts["Issue"]==30 and counts["Purchase Invoice"]==12 and result["gl"]["balanced"] and result["stock_ledger_rows"]>0 and not invalid
    Path(frappe.get_site_path("private","files","crossborder-demo-manifest.json")).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result["ok"]:
        raise RuntimeError("Crossborder fixture verification failed")
    return result
