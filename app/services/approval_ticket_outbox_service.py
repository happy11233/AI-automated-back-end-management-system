"""Dispatch approval tickets after the local approval transaction commits."""
from __future__ import annotations

from hashlib import sha256

from psycopg.types.json import Jsonb

from app.db import pool
from app.json_utils import dumps_json
from app.services.mcp_service import create_external_ticket, get_external_ticket


def _ticket_id(idempotency_key: str) -> str:
    return f"TICKET-{sha256(idempotency_key.encode()).hexdigest()[:16].upper()}"


def _claim_one(approval_id: str | None = None):
    with pool.connection() as conn:
        with conn.transaction():
            row = conn.execute(
                """SELECT o.id,o.approval_id,o.idempotency_key,o.status,o.attempt_count,o.max_attempts,
                          a.thread_id,a.requested_by,a.action_type,a.payload
                   FROM approval_ticket_outbox o JOIN approval_requests a ON a.id=o.approval_id
                   WHERE (%s::uuid IS NULL OR o.approval_id=%s::uuid)
                     AND ((o.status IN ('pending','failed') AND o.attempt_count<o.max_attempts)
                          OR o.status='uncertain'
                          OR (o.status='dispatching' AND o.updated_at<now()-interval '5 minutes'))
                     AND o.next_attempt_at<=now()
                   ORDER BY o.next_attempt_at,o.created_at LIMIT 1 FOR UPDATE OF o SKIP LOCKED""",
                (approval_id, approval_id),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """UPDATE approval_ticket_outbox
                   SET status='dispatching',updated_at=now(),
                       attempt_count=attempt_count+CASE WHEN %s IN ('pending','failed') THEN 1 ELSE 0 END
                   WHERE id=%s""", (row[3], row[0]),
            )
            return row


def _finish_success(row, ticket: dict) -> None:
    with pool.connection() as conn:
        with conn.transaction():
            changed = conn.execute(
                """UPDATE approval_ticket_outbox SET status='succeeded',external_ticket_id=%s,
                   last_error=NULL,updated_at=now() WHERE id=%s AND status='dispatching'
                   RETURNING approval_id""", (ticket['ticket_id'], row[0]),
            ).fetchone()
            if changed is None:
                return
            conn.execute(
                """UPDATE approval_requests SET payload=jsonb_set(payload,'{external_ticket}',%s::jsonb,true)
                   WHERE id=%s""", (Jsonb(ticket), row[1]),
            )
            conn.execute(
                """INSERT INTO audit_logs(user_id,action,resource_type,resource_id,metadata)
                   VALUES (%s,'approval.ticket_created','approval',%s,%s::jsonb)""",
                (row[7], str(row[1]), dumps_json({'ticket_id': ticket['ticket_id']})),
            )


def _finish_unresolved(row, error: Exception | None, *, can_retry: bool) -> None:
    attempts = row[4] + (1 if row[3] in {'pending', 'failed'} else 0)
    status = 'failed' if can_retry else 'uncertain'
    delay = min(300, 5 * 2 ** max(0, attempts - 1)) if can_retry else 60
    with pool.connection() as conn:
        conn.execute(
            """UPDATE approval_ticket_outbox
               SET status=%s,last_error=%s,next_attempt_at=now()+(%s*interval '1 second'),
                   updated_at=now() WHERE id=%s AND status='dispatching'""",
            (status, type(error).__name__ if error else 'ticket_not_found', delay, row[0]),
        )
        conn.commit()


def dispatch_approval_tickets(limit: int = 10, *, approval_id: str | None = None) -> dict:
    from app.mcp_servers.ticket_system import _is_feishu_ticket_configured

    processed = succeeded = unresolved = 0
    for _ in range(max(1, min(limit, 50))):
        row = _claim_one(approval_id)
        if row is None:
            break
        processed += 1
        ticket_id = _ticket_id(row[2])
        ticket = None
        error = None
        if row[3] in {'uncertain', 'dispatching'}:
            try:
                found = get_external_ticket(ticket_id)
                if found.get('found'):
                    ticket = found
            except Exception as cause:
                error = cause
        if ticket is None and row[3] in {'pending', 'failed'} and error is None:
            try:
                ticket = create_external_ticket(
                    title=f"人工审批：{row[8]}",
                    description=dumps_json({'thread_id': row[6], 'requested_by': str(row[7]),
                                            'action_type': row[8], 'payload': row[9]}),
                    priority='high', requester=str(row[7]), source='company-rag-agent',
                    idempotency_key=row[2],
                )
            except Exception as cause:
                error = cause
                try:
                    found = get_external_ticket(ticket_id)
                    if found.get('found'):
                        ticket = found
                except Exception:
                    pass
        if ticket and ticket.get('ticket_id') == ticket_id:
            _finish_success(row, ticket)
            succeeded += 1
        else:
            _finish_unresolved(row, error, can_retry=not _is_feishu_ticket_configured())
            unresolved += 1
    return {'processed': processed, 'succeeded': succeeded, 'unresolved': unresolved}
