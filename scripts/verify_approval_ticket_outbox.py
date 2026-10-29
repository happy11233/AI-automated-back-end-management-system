"""Local transaction and fault-injection checks for approval ticket outbox."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import close_pool, execute, fetch_one, open_pool
from app.services import approval_ticket_outbox_service as outbox
from app.mcp_servers import ticket_system
from app.tools.approval_tool import create_approval_request


def outbox_state(approval_id: str):
    return fetch_one('''SELECT status,attempt_count,external_ticket_id,next_attempt_at
        FROM approval_ticket_outbox WHERE approval_id=%s''', (approval_id,))


def main():
    open_pool()
    approval_ids = []
    thread_ids = []
    try:
        user = fetch_one("SELECT id FROM users WHERE role='employee' AND position='customer_service' LIMIT 1")
        assert user, 'local verification requires a customer-service user'
        user_id = str(user[0])
        with patch('app.tools.approval_tool.summarize_approval', return_value={
            'summary': '验证审批', 'source': 'test',
        }):
            thread_id = f'thread-outbox-{uuid4().hex}'
            thread_ids.append(thread_id)
            payload = {'order_no': f'TEST-{uuid4().hex[:8]}', 'reason': 'verify'}
            first = create_approval_request(thread_id, user_id, 'customer_service_refund', payload)
            second = create_approval_request(thread_id, user_id, 'customer_service_refund', payload)
            approval_id = first['approval_id']
            approval_ids.append(approval_id)
            assert second['approval_id'] == approval_id
            assert first['external_ticket']['status'] == 'pending'
            assert fetch_one('SELECT count(*) FROM approval_ticket_outbox WHERE approval_id=%s',
                             (approval_id,))[0] == 1

            key = f"approval:{thread_id}:customer_service_refund:"
            stored_key = fetch_one('SELECT idempotency_key FROM approval_ticket_outbox WHERE approval_id=%s',
                                   (approval_id,))[0]
            assert stored_key.startswith(key)
            ticket_id = outbox._ticket_id(stored_key)

            with patch('app.services.approval_ticket_outbox_service.create_external_ticket', side_effect=TimeoutError('once')) as create, \
                 patch('app.services.approval_ticket_outbox_service.get_external_ticket', return_value={'found': False}), \
                 patch('app.mcp_servers.ticket_system._is_feishu_ticket_configured', return_value=False):
                dispatched = outbox.dispatch_approval_tickets(approval_id=approval_id)
                assert dispatched == {'processed': 1, 'succeeded': 0, 'unresolved': 1}
                assert create.call_count == 1
            assert outbox_state(approval_id)[0:2] == ('failed', 1)
            execute('UPDATE approval_ticket_outbox SET next_attempt_at=now() WHERE approval_id=%s',
                    (approval_id,))
            with patch('app.services.approval_ticket_outbox_service.create_external_ticket',
                       return_value={'ticket_id': ticket_id, 'created': True}) as create, \
                 patch('app.mcp_servers.ticket_system._is_feishu_ticket_configured', return_value=False):
                dispatched = outbox.dispatch_approval_tickets(approval_id=approval_id)
                assert dispatched == {'processed': 1, 'succeeded': 1, 'unresolved': 0}
                assert create.call_count == 1
            assert outbox_state(approval_id)[0:3] == ('succeeded', 2, ticket_id)
            stored = fetch_one('SELECT payload FROM approval_requests WHERE id=%s', (approval_id,))[0]
            assert stored['external_ticket']['ticket_id'] == ticket_id
            assert outbox.dispatch_approval_tickets(approval_id=approval_id)['processed'] == 0

            crash_thread = f'thread-outbox-{uuid4().hex}'
            thread_ids.append(crash_thread)
            crash = create_approval_request(crash_thread, user_id, 'customer_service_refund', payload)
            crash_id = crash['approval_id']
            approval_ids.append(crash_id)
            crash_key = fetch_one('SELECT idempotency_key FROM approval_ticket_outbox WHERE approval_id=%s',
                                  (crash_id,))[0]
            crash_ticket_id = outbox._ticket_id(crash_key)
            execute("""UPDATE approval_ticket_outbox SET status='dispatching',attempt_count=1,
                updated_at=now()-interval '6 minutes',next_attempt_at=now() WHERE approval_id=%s""", (crash_id,))
            with patch('app.services.approval_ticket_outbox_service.get_external_ticket',
                       return_value={'found': True, 'ticket_id': crash_ticket_id}) as lookup, \
                 patch('app.services.approval_ticket_outbox_service.create_external_ticket') as create, \
                 patch('app.mcp_servers.ticket_system._is_feishu_ticket_configured', return_value=True):
                assert outbox.dispatch_approval_tickets(approval_id=crash_id)['succeeded'] == 1
                assert lookup.call_count == 1 and create.call_count == 0
            assert outbox_state(crash_id)[0] == 'succeeded'

            uncertain_thread = f'thread-outbox-{uuid4().hex}'
            thread_ids.append(uncertain_thread)
            uncertain = create_approval_request(uncertain_thread, user_id, 'customer_service_refund', payload)
            uncertain_id = uncertain['approval_id']
            approval_ids.append(uncertain_id)
            with patch('app.services.approval_ticket_outbox_service.create_external_ticket', side_effect=TimeoutError('unknown')) as create, \
                 patch('app.services.approval_ticket_outbox_service.get_external_ticket', return_value={'found': False}), \
                 patch('app.mcp_servers.ticket_system._is_feishu_ticket_configured', return_value=True):
                assert outbox.dispatch_approval_tickets(approval_id=uncertain_id)['unresolved'] == 1
                execute('UPDATE approval_ticket_outbox SET next_attempt_at=now() WHERE approval_id=%s',
                        (uncertain_id,))
                assert outbox.dispatch_approval_tickets(approval_id=uncertain_id)['unresolved'] == 1
                assert create.call_count == 1, 'unknown Feishu result was replayed'
            assert outbox_state(uncertain_id)[0] == 'uncertain'

            stable_thread = f'thread-outbox-{uuid4().hex}'
            thread_ids.append(stable_thread)
            stable_payload = {'customer_message_id': str(uuid4()), 'order_no': 'STABLE-ORDER',
                              'intent': 'refund', 'risk_level': 'high', 'buyer_message': 'refund',
                              'erp_summary': 'first draft'}
            stable_first = create_approval_request(stable_thread, user_id, 'customer_service_refund', stable_payload)
            approval_ids.append(stable_first['approval_id'])
            stable_second = create_approval_request(stable_thread, user_id, 'customer_service_refund',
                                                    {**stable_payload, 'erp_summary': 'new draft'})
            assert stable_second['approval_id'] == stable_first['approval_id']

        with TemporaryDirectory() as directory, \
             patch.object(ticket_system, 'DATA_DIR', Path(directory)), \
             patch.object(ticket_system, 'TICKETS_FILE', Path(directory) / 'tickets.jsonl'), \
             patch.object(ticket_system, '_is_feishu_ticket_configured', return_value=False):
            first_ticket = ticket_system.create_ticket('Test', 'Test', idempotency_key='ticket-fixture')
            second_ticket = ticket_system.create_ticket('Test', 'Test', idempotency_key='ticket-fixture')
            assert first_ticket['ticket_id'] == second_ticket['ticket_id']
            assert len((Path(directory) / 'tickets.jsonl').read_text().splitlines()) == 1
        print('approval outbox checks passed: atomic insert, retry, crash reconciliation, unknown outcome')
    finally:
        for approval_id in approval_ids:
            execute("DELETE FROM audit_logs WHERE resource_type='approval' AND resource_id=%s", (approval_id,))
            execute('DELETE FROM approval_requests WHERE id=%s', (approval_id,))
        for thread_id in thread_ids:
            execute('DELETE FROM chat_threads WHERE id=%s', (thread_id,))
        close_pool()


if __name__ == '__main__':
    main()
