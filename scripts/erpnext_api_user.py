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


def ensure_item_price_reader(remove_temporary_master_roles: bool = False) -> dict:
    import frappe
    from frappe.permissions import add_permission, update_permission_property

    email = "company_rag_api@example.com"
    role = "Company RAG Reader"
    frappe.set_user("Administrator")
    if not frappe.db.exists("Role", role):
        frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert(
            ignore_permissions=True
        )
    # add_permission copies the original rules before creating Custom DocPerm.
    if not frappe.db.exists("Custom DocPerm", {"parent": "Item Price", "role": role}):
        add_permission("Item Price", role, ptype="read")
    update_permission_property("Item Price", role, 0, "select", 1)
    user = frappe.get_doc("User", email)
    user.add_roles(role)
    if remove_temporary_master_roles:
        # Only revoke the two roles temporarily added during this integration.
        user.set("roles", [row for row in user.roles if row.role not in {
            "Sales Master Manager", "Purchase Master Manager"
        }])
        user.save(ignore_permissions=True)
    frappe.clear_cache(user=email)
    frappe.db.commit()
    return {
        "user": email,
        "role": role,
        "item_price_read": bool(frappe.has_permission("Item Price", "read", user=email)),
        "item_price_write": bool(frappe.has_permission("Item Price", "write", user=email)),
        "temporary_roles_removed": remove_temporary_master_roles,
    }


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
    ensure_item_price_reader()
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
