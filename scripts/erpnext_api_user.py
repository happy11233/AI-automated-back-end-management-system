import json


INTEGRATION_ROLES = [
    "Accounts User",
    "Auditor",
    "Delivery User",
    "HR User",
    "Sales User",
    "Stock User",
    "Support Team",
]


def ensure_company_rag_api_user() -> None:
    import frappe
    from frappe.core.doctype.user.user import generate_keys

    email = "company_rag_api@example.com"
    full_name = "Company RAG API"

    if not frappe.db.exists("User", email):
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": "Company",
                "last_name": "RAG API",
                "full_name": full_name,
                "enabled": 1,
                "send_welcome_email": 0,
                "user_type": "System User",
            }
        )
        user.insert(ignore_permissions=True)
    else:
        user = frappe.get_doc("User", email)
        if not user.enabled:
            user.enabled = 1
        user.user_type = "System User"
        user.save(ignore_permissions=True)

    for role in INTEGRATION_ROLES:
        if not frappe.db.exists(
            "Has Role",
            {
                "parent": email,
                "parenttype": "User",
                "role": role,
            },
        ):
            user.add_roles(role)

    frappe.set_user("Administrator")
    user.reload()
    keys = {"api_key": user.api_key, "api_secret": None}
    if not user.api_key:
        keys = generate_keys(email)
    frappe.db.commit()

    print(
        json.dumps(
            {
                "user": email,
                "api_key": keys["api_key"],
                "api_secret": keys["api_secret"] or "<unchanged>",
            },
            ensure_ascii=False,
        )
    )
