from app.db import open_pool, close_pool, fetch_one
from app.rag.ingest import ingest_text_document


def upsert_user(username: str, role: str, department: str, position: str | None = None) -> str:
    row = fetch_one(
        """
        INSERT INTO users (username, role, department, position)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (username)
        DO UPDATE SET
            role = EXCLUDED.role,
            department = EXCLUDED.department,
            position = EXCLUDED.position
        RETURNING id;
        """,
        (username, role, department, position),
    )

    return str(row[0])


def upsert_order(
    order_no: str,
    user_id: str,
    status: str,
    amount_cents: int,
    refundable: bool,
) -> str:
    row = fetch_one(
        """
        INSERT INTO orders (order_no, user_id, status, amount_cents, refundable)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (order_no)
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            status = EXCLUDED.status,
            amount_cents = EXCLUDED.amount_cents,
            refundable = EXCLUDED.refundable
        RETURNING id;
        """,
        (order_no, user_id, status, amount_cents, refundable),
    )

    return str(row[0])


def main():
    open_pool()

    admin_id = upsert_user("admin_demo", "admin", "管理部")
    employee_id = upsert_user("employee_demo", "employee", "客服部", "customer_service")
    upsert_user("operations_demo", "employee", "运营部", "operations")
    upsert_user("finance_demo", "employee", "财务部", "finance")

    upsert_order("10086", employee_id, "shipping", 29900, True)
    upsert_order("10087", employee_id, "delivered", 59900, True)
    upsert_order("10088", employee_id, "refunded", 19900, False)

    ingest_text_document(
        title="退款规则",
        source="internal-policy/refund.md",
        visibility="employee",
        department=None,
        text=(
            "退款申请通过后，一般会在3到5个工作日内原路返回至支付账户。\n"
            "订单已发货但未签收时，用户可以申请退款，但需要先确认物流状态。"
        ),
    )

    ingest_text_document(
        title="特殊退款审批规则",
        source="internal-policy/admin-refund.md",
        visibility="admin",
        department="管理部",
        text="超过500元的特殊退款需要客服岗位审批，普通员工不能直接执行退款。",
    )

    close_pool()

    print("种子数据写入完成")


if __name__ == "__main__":
    main()
