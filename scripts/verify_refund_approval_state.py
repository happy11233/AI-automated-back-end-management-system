"""Isolated local PostgreSQL checks for refund approvals and retries."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import close_pool, execute, fetch_one, open_pool
from app.services.approval_service import authorize_refund_retry, review_approval
from app.services.refund_service import execute_refund_for_approval


def create_case(applicant_id: str, order_no: str, *, refundable: bool, thread_id: str) -> str:
    execute("INSERT INTO chat_threads(id,user_id,title,position) VALUES (%s,%s,'refund verification','customer_service')",
            (thread_id, applicant_id))
    execute("INSERT INTO orders(order_no,status,amount_cents,refundable) VALUES (%s,'shipping',29900,%s)",
            (order_no, refundable))
    row = fetch_one("""INSERT INTO approval_requests(thread_id,requested_by,action_type,payload)
        VALUES (%s,%s,'refund',%s) RETURNING id""",
        (thread_id, applicant_id, Jsonb({'order_no': order_no, 'risk_level': 'high'})))
    return str(row[0])


def main():
    open_pool()
    approval_ids = []
    thread_ids = []
    order_nos = []
    reviewer_id = str(uuid4())
    team_id = str(uuid4())
    try:
        applicant = fetch_one("SELECT id,username FROM users WHERE role='employee' AND position='customer_service' LIMIT 1")
        assert applicant, 'local verification requires a customer-service user'
        applicant_user = {'id': str(applicant[0]), 'role': 'employee', 'position': 'customer_service'}
        reviewer_user = {'id': reviewer_id, 'role': 'employee', 'position': 'customer_service'}
        execute("INSERT INTO users(id,username,role,position) VALUES (%s,%s,'employee','customer_service')",
                (reviewer_id, f'refund-review-{reviewer_id}'))
        execute("INSERT INTO rag_teams(id,team_key,name,position_scope,created_by) VALUES (%s,%s,'Refund verification','customer_service',%s)",
                (team_id, f'refund-review-{team_id}', applicant_user['id']))
        execute("INSERT INTO rag_team_memberships(team_id,user_id,member_role) VALUES (%s,%s,'supervisor')",
                (team_id, reviewer_id))

        for refundable in (True, False):
            order_no = f'REFUND-VERIFY-{uuid4().hex[:12]}'
            thread_id = f'thread-refund-{uuid4().hex}'
            approval_id = create_case(applicant_user['id'], order_no, refundable=refundable,
                                      thread_id=thread_id)
            approval_ids.append(approval_id)
            thread_ids.append(thread_id)
            order_nos.append(order_no)

            self_review = review_approval(approval_id, applicant_user, approved=True)
            assert self_review.get('forbidden') and fetch_one('SELECT status FROM approval_requests WHERE id=%s',
                                                              (approval_id,))[0] == 'pending'
            reviewed = review_approval(approval_id, reviewer_user, approved=True)
            assert reviewed['status'] == 'approved' and reviewed['refund_status'] == 'pending'
            first = execute_refund_for_approval(approval_id)
            expected = 'succeeded' if refundable else 'failed'
            assert first['refund_status'] == expected and first['success'] is refundable, first
            assert fetch_one('SELECT refund_status FROM approval_requests WHERE id=%s', (approval_id,))[0] == expected
            assert fetch_one('SELECT count(*) FROM refund_transactions WHERE approval_id=%s', (approval_id,))[0] == 1

            if not refundable:
                try:
                    authorize_refund_retry(approval_id, applicant_user)
                    raise AssertionError('applicant could retry own refund')
                except HTTPException as error:
                    assert error.status_code == 403
                authorize_refund_retry(approval_id, reviewer_user)
                execute('UPDATE orders SET refundable=true WHERE order_no=%s', (order_no,))
                retried = execute_refund_for_approval(approval_id)
                assert retried['success'] and retried['refund_status'] == 'succeeded'
                assert retried['refund_transaction_id'] == first['refund_transaction_id']

            with ThreadPoolExecutor(max_workers=3) as executor:
                repeats = list(executor.map(lambda _: execute_refund_for_approval(approval_id), range(3)))
            assert all(item['success'] and item['refund_transaction_id'] ==
                       (first['refund_transaction_id'] if refundable else retried['refund_transaction_id'])
                       for item in repeats)
            assert fetch_one('SELECT count(*) FROM refund_transactions WHERE approval_id=%s', (approval_id,))[0] == 1
            assert fetch_one('SELECT status,refundable FROM orders WHERE order_no=%s', (order_no,)) == ('refunded', False)
        print('refund approval checks passed: self-review, supervisor, failure retry and concurrent idempotency')
    finally:
        for approval_id in approval_ids:
            execute("DELETE FROM audit_logs WHERE resource_type='approval' AND resource_id=%s", (approval_id,))
            execute('DELETE FROM refund_transactions WHERE approval_id=%s', (approval_id,))
            execute('DELETE FROM approval_requests WHERE id=%s', (approval_id,))
        for thread_id in thread_ids:
            execute('DELETE FROM chat_threads WHERE id=%s', (thread_id,))
        for order_no in order_nos:
            execute('DELETE FROM orders WHERE order_no=%s', (order_no,))
        execute('DELETE FROM rag_team_memberships WHERE team_id=%s', (team_id,))
        execute('DELETE FROM rag_teams WHERE id=%s', (team_id,))
        execute('DELETE FROM users WHERE id=%s', (reviewer_id,))
        close_pool()


if __name__ == '__main__':
    main()
