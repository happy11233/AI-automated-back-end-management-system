from app.db import fetch_all, transaction
from app.json_utils import dumps_json


def execute_refund_for_approval(approval_id: str) -> dict:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, action_type, status, payload
                FROM approval_requests
                WHERE id = %s
                FOR UPDATE;
                """,
                (approval_id,),
            )
            approval = cur.fetchone()

            if approval is None:
                return {
                    "success": False,
                    "message": "审批记录不存在。",
                }

            if approval[1] != "refund":
                return {
                    "success": False,
                    "message": "该审批不是退款审批。",
                }

            if approval[2] != "approved":
                return {
                    "success": False,
                    "message": "审批尚未通过，不能执行退款。",
                }

            payload = approval[3]
            order_no = payload.get("order_no")

            if not order_no:
                return {
                    "success": False,
                    "message": "审批记录中缺少订单号。",
                }

            cur.execute(
                """
                SELECT order_no, amount_cents, refundable
                FROM orders
                WHERE order_no = %s
                FOR UPDATE;
                """,
                (order_no,),
            )
            order = cur.fetchone()

            if order is None:
                return {
                    "success": False,
                    "message": f"订单 {order_no} 不存在。",
                }

            cur.execute(
                """
                SELECT id
                FROM refund_transactions
                WHERE approval_id = %s;
                """,
                (approval_id,),
            )
            existing = cur.fetchone()

            if existing is not None:
                return {
                    "success": True,
                    "message": "该审批已经执行过退款，未重复执行。",
                    "refund_transaction_id": str(existing[0]),
                }

            if order[2] is False:
                failed_refund = create_refund_transaction(
                    cur=cur,
                    approval_id=approval_id,
                    order_no=order[0],
                    amount_cents=order[1],
                    status="failed",
                    payload={
                        **payload,
                        "failure_reason": "order_not_refundable",
                    },
                )

                return {
                    "success": False,
                    "message": f"订单 {order_no} 当前不可退款。",
                    "refund_transaction_id": str(failed_refund[0]),
                }

            refund = create_refund_transaction(
                cur=cur,
                approval_id=approval_id,
                order_no=order[0],
                amount_cents=order[1],
                status="succeeded",
                payload=payload,
            )

            cur.execute(
                """
                UPDATE orders
                SET status = 'refunded',
                    refundable = false,
                    updated_at = now()
                WHERE order_no = %s
                RETURNING id;
                """,
                (order_no,),
            )

            return {
                "success": True,
                "message": f"订单 {order_no} 已退款成功。",
                "refund_transaction_id": str(refund[0]),
            }


def create_refund_transaction(
    cur,
    approval_id: str,
    order_no: str,
    amount_cents: int,
    status: str,
    payload: dict,
):
    cur.execute(
        """
        INSERT INTO refund_transactions (
            approval_id,
            order_no,
            amount_cents,
            status,
            payload
        )
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            approval_id,
            order_no,
            amount_cents,
            status,
            dumps_json(payload),
        ),
    )

    return cur.fetchone()


def list_refund_transactions(limit: int = 50) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, approval_id, order_no, amount_cents, status, payload, created_at
        FROM refund_transactions
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (limit,),
    )

    return [
        {
            "id": str(row[0]),
            "approval_id": str(row[1]),
            "order_no": row[2],
            "amount_cents": row[3],
            "status": row[4],
            "payload": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]
