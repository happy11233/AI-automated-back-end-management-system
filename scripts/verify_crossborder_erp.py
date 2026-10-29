"""Verify the synthetic batch through real login, ERP API and role permissions."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
BATCH = "CB-DEMO-20261021"
COMPANY = "Crossborder Demo 2026"
SKU = "CB-OWN-DE-CABLE-002"


def request(path, *, token=None, payload=None, form=None, expected=200):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = Request(BASE + path, data=data, headers=headers)
    try:
        with urlopen(req, timeout=90) as response:
            status, result = response.status, json.load(response)
    except HTTPError as error:
        status, result = error.code, json.load(error)
    assert status == expected, (path, status, result)
    return result


def query(token, resource, *, filters=None, query=None, expected=200):
    result = request("/erp/query", token=token, payload={
        "resource": resource, "filters": filters, "query": query, "limit": 100,
    }, expected=expected)
    if expected == 200:
        assert result["ok"] and result["provider"] == "erpnext", result
    return result


def main():
    deadline = time.monotonic() + int(os.getenv("VERIFY_STARTUP_WAIT_SECONDS", "180"))
    while True:
        try:
            with urlopen(BASE + "/ready", timeout=5) as response:
                if response.status == 200:
                    break
        except (URLError, TimeoutError, ConnectionError):
            if time.monotonic() >= deadline:
                raise RuntimeError(f"API did not become ready: {BASE}") from None
        time.sleep(3)
    request("/health")
    request("/ready")
    tokens = {}
    for role, username, password in [
        ("operations", "operations_demo", "Operations123456"),
        ("finance", "finance_demo", "Finance123456"),
        ("customer_service", "employee_demo", "Employee123456"),
    ]:
        auth = request("/auth/login", form={
            "username": username,
            "password": os.getenv(f"VERIFY_{role.upper()}_PASSWORD", password),
        })
        assert auth["position"] == role, role
        tokens[role] = auth["access_token"]
        health = request("/erp/status", token=tokens[role])
        assert health["ok"] and health["provider"] == "erpnext", health

    counts = {}
    cases = [
        ("operations", "Crossborder Product", 60, {"demo_batch": BATCH}),
        ("operations", "Competitor Product", 40, {"demo_batch": BATCH}),
        ("operations", "Ad Campaign Daily", 60, {"demo_batch": BATCH}),
        ("finance", "Marketplace Settlement", 60, {"demo_batch": BATCH}),
        ("finance", "Sales Invoice", 60, {"company": COMPANY, "docstatus": 1}),
        ("finance", "Purchase Invoice", 12, {"company": COMPANY, "docstatus": 1}),
        ("finance", "Payment Entry", 53, {"company": COMPANY, "docstatus": 1}),
        ("customer_service", "Shipment Tracking", 40, {"demo_batch": BATCH}),
        ("customer_service", "Sales Order", 60, {"company": COMPANY, "docstatus": 1}),
        ("customer_service", "Delivery Note", 40, {"company": COMPANY, "docstatus": 1}),
        ("customer_service", "Issue", 30, [["name", "like", "CB-ISSUE-%"]]),
    ]
    for role, resource, count, filters in cases:
        scopes = request("/erp/scopes", token=tokens[role])
        assert resource in {item["resource"] for item in scopes["resources"]}, resource
        items = query(tokens[role], resource, filters=filters)["items"]
        assert len(items) == count, (resource, len(items), count)
        counts[resource] = count
        sample = items[len(items)//2]
        detail = request(f"/erp/records/{quote(resource, safe='')}/{quote(sample['name'], safe='')}", token=tokens[role])
        assert detail["ok"] and detail["item"]["name"] == sample["name"], detail
        print(f"PASS {role}: {resource} = {count}", flush=True)

    for filters in (None, {"item_code": SKU}, [["item_code", "=", SKU]]):
        prices = query(tokens["operations"], "Item Price", filters=filters, query=SKU)["items"]
        assert len(prices) == 1 and prices[0]["name"] == "CB-PRICE-002", prices
        assert prices[0]["currency"] == "EUR" and abs(prices[0]["price_list_rate"]-12.08) < .001, prices
    for filters in ({"item_code": SKU, "buying": 1}, [["item_code", "=", SKU], ["selling", "=", 0]]):
        assert not query(tokens["operations"], "Item Price", filters=filters)["items"]
    print("PASS selling price: EUR 12.08; purchase prices excluded", flush=True)

    for role, resource in [("operations", "Marketplace Settlement"), ("customer_service", "GL Entry"), ("finance", "Competitor Product")]:
        query(tokens[role], resource, expected=403)
    dashboards = {}
    for role, token in tokens.items():
        dashboard = request("/erp/dashboard-overview", token=token)
        assert dashboard["sections"] and all(item["ok"] for item in dashboard["sections"]), dashboard
        for section in dashboard["sections"]:
            currencies = {item.get("currency") for item in section["items"] if item.get("currency")}
            if len(currencies) > 1 and section["amount_total"] is not None:
                assert "公司本位币" in section["amount_label"], section
        dashboards[role] = {s["resource"]: s["total_count"] for s in dashboard["sections"]}
    result = {"ok": True, "batch": BATCH, "api": BASE, "counts": counts,
              "selling_price": {"sku": SKU, "currency": "EUR", "price": 12.08},
              "permission_isolation": True, "dashboards": dashboards,
              "note": "Synthetic business data verified through live ERPNext; no mocked API."}
    output = Path(__file__).resolve().parents[1] / "data/crossborder-demo/integration-verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
