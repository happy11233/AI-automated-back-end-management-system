from app.db import fetch_all, transaction
from app.json_utils import dumps_json


REFUND_APPROVAL_ACTIONS = {"refund", "customer_service_refund"}


def execute_refund_for_approval(approval_id: str) -> dict:
    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, action_type, status, refund_status, payload
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

            if approval[1] not in REFUND_APPROVAL_ACTIONS:
                return {
                    "success": False,
                    "message": "该审批不是退款审批。",
                }

            if approval[2] != "approved":
                return {
                    "success": False,
                    "message": "审批尚未通过，不能执行退款。",
                }

            cur.execute(
                """SELECT id, status, amount_cents FROM refund_transactions
                   WHERE approval_id = %s FOR UPDATE""", (approval_id,),
            )
            existing = cur.fetchone()
            if approval[3] == "succeeded" and existing is None:
                return {
                    "success": False, "refund_status": "succeeded",
                    "message": "退款状态与流水不一致，已停止重复执行，请人工对账。",
                }
            if existing is not None and existing[1] == "succeeded":
                cur.execute("UPDATE approval_requests SET refund_status='succeeded' WHERE id=%s", (approval_id,))
                return {
                    "success": True,
                    "refund_status": "succeeded",
                    "message": "该审批已经执行过退款，未重复执行。",
                    "refund_transaction_id": str(existing[0]),
                }

            payload = approval[4] if isinstance(approval[4], dict) else {}
            order_no = payload.get("order_no")

            if not order_no:
                cur.execute("UPDATE approval_requests SET refund_status='failed' WHERE id=%s", (approval_id,))
                return {
                    "success": False,
                    "refund_status": "failed",
                    "message": "审批记录中缺少订单号。",
                }

            cur.execute(
                """
                SELECT order_no, amount_cents, refundable, status
                FROM orders
                WHERE order_no = %s
                FOR UPDATE;
                """,
                (order_no,),
            )
            order = cur.fetchone()

            if order is None:
                cur.execute("UPDATE approval_requests SET refund_status='failed' WHERE id=%s", (approval_id,))
                return {
                    "success": False,
                    "refund_status": "failed",
                    "message": f"订单 {order_no} 不存在。",
                }

            if existing is not None and existing[2] != order[1]:
                cur.execute("UPDATE approval_requests SET refund_status='failed' WHERE id=%s", (approval_id,))
                return {
                    "success": False, "refund_status": "failed",
                    "message": "订单金额已变化，需要重新审批后再退款。",
                }

            if order[3] == "refunded":
                cur.execute("UPDATE approval_requests SET refund_status='failed' WHERE id=%s", (approval_id,))
                return {
                    "success": False, "refund_status": "failed",
                    "message": "订单已标记退款但本审批没有成功流水，请人工对账，禁止重复退款。",
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

                cur.execute("UPDATE approval_requests SET refund_status='failed' WHERE id=%s", (approval_id,))
                return {
                    "success": False,
                    "refund_status": "failed",
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
            cur.execute("UPDATE approval_requests SET refund_status='succeeded' WHERE id=%s", (approval_id,))

            return {
                "success": True,
                "refund_status": "succeeded",
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
        ON CONFLICT (approval_id) DO UPDATE
        SET status = EXCLUDED.status, payload = EXCLUDED.payload
        WHERE refund_transactions.status <> 'succeeded'
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
