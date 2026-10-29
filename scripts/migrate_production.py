"""Explicit, idempotent production additions; never run from API startup."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import open_pool, close_pool, transaction


def main():
    open_pool()
    try:
        with transaction() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(714206232)')
            for name in ('022_background_jobs.sql', '023_agent_business_events.sql', '024_agent_tasks.sql',
                         '025_competitor_monitor.sql', '026_email_send_confirmations.sql',
                         '027_mcp_execution_approvals.sql', '028_platform_callback_events.sql',
                         '029_chat_context_version.sql', '030_background_job_retries.sql',
                         '031_refund_status.sql', '032_approval_ticket_outbox.sql'):
                conn.execute((Path(__file__).resolve().parents[1]/'sql'/name).read_text())
        print('Applied migrations 022 through 032')
    finally:
        close_pool()


if __name__ == '__main__':
    main()
