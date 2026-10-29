"""Celery runtime. Task status remains in PostgreSQL, payloads stay out of results."""
from pathlib import Path

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from kombu import Exchange, Queue

from app.config import settings

celery_app = Celery('company_rag', broker=settings.celery_broker_url, include=['app.tasks'])
celery_app.conf.update(
    task_serializer='json', accept_content=['json'], result_serializer='json',
    task_ignore_result=True, task_acks_late=True, task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1, worker_concurrency=settings.celery_worker_concurrency,
    worker_max_tasks_per_child=100, broker_connection_retry_on_startup=True,
    worker_enable_remote_control=False, worker_send_task_events=False,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_soft_time_limit=settings.celery_task_soft_time_limit_seconds,
    task_time_limit=settings.celery_task_time_limit_seconds,
    task_default_queue='default', task_default_delivery_mode='persistent',
    task_default_exchange='company_rag_tasks', task_default_exchange_type='topic', task_default_routing_key='default',
    task_queues=(Queue('default', exchange=Exchange('company_rag_tasks', type='topic'), routing_key='default',
                      queue_arguments={'x-queue-type': 'quorum'}),
                 Queue('maintenance', exchange=Exchange('company_rag_tasks', type='topic'), routing_key='maintenance',
                       queue_arguments={'x-queue-type': 'quorum'})),
    broker_transport_options={'confirm_publish': True},
    task_routes={'maintenance.*': {'queue': 'maintenance', 'routing_key': 'maintenance'},
                 'jobs.*': {'queue': 'default', 'routing_key': 'default'}},
    timezone=settings.celery_timezone, enable_utc=True,
    beat_schedule={'scheduler-heartbeat': {
        'task': 'maintenance.scheduler_heartbeat', 'schedule': 15.0,
        'options': {'expires': 30},
    }, 'daily-context-cleanup': {
        'task': 'maintenance.cleanup_context', 'schedule': 86400.0,
        'options': {'expires': 3600},
    }, 'publish-outbox': {
        'task': 'maintenance.publish_outbox', 'schedule': 5.0,
        'options': {'expires': 30},
    }, 'publish-approval-tickets': {
        'task': 'maintenance.publish_approval_tickets', 'schedule': 5.0,
        'options': {'expires': 30},
    }, 'competitor-monitor-inspections': {
        # Recover the latest due Shanghai slot; persistent slot keys deduplicate.
        'task': 'maintenance.competitor_monitor', 'schedule': 60.0,
        'options': {'expires': 120},
    }},
)
# Beat's persistent scheduler requires an existing parent directory.
Path('data/celery').mkdir(parents=True, exist_ok=True)


@worker_process_init.connect
def initialize_worker(**kwargs):
    from app.db import open_pool
    open_pool()


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    from app.db import close_pool
    from app.observability import flush_traces
    flush_traces()
    close_pool()
