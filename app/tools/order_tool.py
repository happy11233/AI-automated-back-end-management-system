from langchain_core.tools import tool

from app.db import fetch_one


STATUS_LABELS = {
    "shipping": "运输中",
    "delivered": "已签收",
    "refunded": "已退款",
}


def format_money(amount_cents: int) -> str:
    return f"{amount_cents / 100:.2f}元"


def query_order_status(order_no: str) -> dict:
    row = fetch_one(
        """
        SELECT order_no, status, delivery_eta, amount_cents, refundable
        FROM orders
        WHERE order_no = %s;
        """,
        (order_no,),
    )

    if row is None:
        return {
            "found": False,
            "message": f"没有找到订单 {order_no}。",
        }

    status_label = STATUS_LABELS.get(row[1], row[1])

    return {
        "found": True,
        "order_no": row[0],
        "status": row[1],
        "status_label": status_label,
        "delivery_eta": row[2],
        "amount": format_money(row[3]),
        "refundable": row[4],
        "message": (
            f"订单 {row[0]} 当前状态：{status_label}；"
            f"订单金额：{format_money(row[3])}；"
            f"是否可退款：{'是' if row[4] else '否'}。"
        ),
    }


@tool
def get_order_status(order_no: str) -> dict:
    """查询订单状态。输入订单号，返回订单状态、预计送达时间、订单金额和是否可退款。"""
    return query_order_status(order_no)

def query_order_status_for_user(order_no: str, user_id: str, role: str) -> dict:
    if role == "admin":
        return query_order_status(order_no)

    row = fetch_one(
        """
        SELECT order_no, status, delivery_eta, amount_cents, refundable
        FROM orders
        WHERE order_no = %s AND user_id = %s;
        """,
        (order_no, user_id),
    )

    if row is None:
        return {
            "found": False,
            "message": f"没有找到订单 {order_no}，或你没有权限查看该订单。",
        }

    status_label = STATUS_LABELS.get(row[1], row[1])

    return {
        "found": True,
        "order_no": row[0],
        "status": row[1],
        "status_label": status_label,
        "delivery_eta": row[2],
        "amount": format_money(row[3]),
        "refundable": row[4],
        "message": (
            f"订单 {row[0]} 当前状态：{status_label}；"
            f"订单金额：{format_money(row[3])}；"
            f"是否可退款：{'是' if row[4] else '否'}。"
        ),
    }