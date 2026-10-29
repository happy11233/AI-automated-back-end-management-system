"""Opt-in LangSmith tracing. Business payloads stay private by default."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from functools import lru_cache, wraps
import logging
import os
import re
from time import monotonic
from typing import Any
from uuid import uuid4

from langsmith import Client, traceable, tracing_context
from langsmith.run_helpers import get_current_run_tree
from prometheus_client import Counter, Histogram

from app.config import settings

# SDK environment defaults cannot bypass the private client. Explicit scopes
# enable approved tracing using settings captured above.
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'

logger = logging.getLogger(__name__)
OBSERVED_RUNS = Counter('company_rag_observed_runs_total', 'Observed application/agent runs', ['component', 'status'])
OBSERVED_DURATION = Histogram('company_rag_observed_duration_seconds', 'Observed application/agent execution time', ['component'])
request_id_var: ContextVar[str | None] = ContextVar('request_id', default=None)
_SAFE_METADATA = {
    'request_id', 'business_run_id', 'workflow_id', 'skill_id', 'environment',
    'ls_provider', 'ls_model_name', 'ls_model_type', 'ls_temperature',
    'ls_max_tokens', 'input_tokens', 'output_tokens', 'total_tokens',
    'input_token_details', 'output_token_details', 'cache_read', 'cache_creation',
    'reasoning', 'audio', 'task_id', 'component',
}


def _safe_metadata(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items()
            if key in _SAFE_METADATA and isinstance(item, (str, int, float, bool))
            and (not isinstance(item, str) or re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', item))}


def _usage_only(value: dict) -> dict:
    if not isinstance(value, dict):
        return {}
    llm_output = value.get('llm_output')
    usage = value.get('usage_metadata') or (llm_output.get('token_usage') if isinstance(llm_output, dict) else None)
    if not isinstance(usage, dict):
        return {}
    aliases = {'prompt_tokens': 'input_tokens', 'completion_tokens': 'output_tokens'}
    return {'usage_metadata': {aliases.get(k, k): v for k, v in usage.items()
                              if k in {'input_tokens', 'output_tokens', 'total_tokens',
                                       'prompt_tokens', 'completion_tokens'}
                              and isinstance(v, int) and v >= 0}}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): ('[REDACTED]' if any(word in str(k).lower() for word in
                ('password', 'secret', 'token', 'authorization', 'cookie', 'api_key',
                 'salary', 'payroll', 'content_base64', 'attachment', 'email', 'phone'))
                else _redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value[:100]]
    if isinstance(value, str):
        value = re.sub(r'(?i)Bearer\s+\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b1[3-9]\d{9}\b', '[REDACTED]', value)
        value = re.sub(r'(?i)(?:postgres(?:ql)?|amqps?|redis|https?)://[^\s]*', '[REDACTED_URL]', value)
        return value[:2000]
    return value if isinstance(value, (int, float, bool, type(None))) else '[OBJECT]'


class PrivateTracingClient(Client):
    """Scrub errors, metadata, events and attachments as well as inputs/outputs."""

    @staticmethod
    def _private_fields(fields: dict) -> dict:
        fields = dict(fields)
        for key in ('attachments', 'events', 'serialized'):
            fields.pop(key, None)
        if fields.get('error'):
            fields['error'] = 'Execution failed; details retained in application logs.'
        if 'extra' in fields:
            extra = fields.get('extra') or {}
            fields['extra'] = {'metadata': _safe_metadata(extra.get('metadata', {}))}
        if 'tags' in fields:
            fields['tags'] = [tag for tag in fields['tags'] or []
                              if tag in {'company-rag-agent', 'api', 'worker', 'verification'}]
        fields['dangerously_allow_filesystem'] = False
        return fields

    def create_run(self, name, inputs, run_type, **kwargs):
        try:
            return super().create_run(name, inputs, run_type, **self._private_fields(kwargs))
        except Exception:
            logger.warning('LangSmith trace creation failed')

    def update_run(self, run_id, **kwargs):
        try:
            return super().update_run(run_id, **self._private_fields(kwargs))
        except Exception:
            logger.warning('LangSmith trace update failed')


@lru_cache(maxsize=1)
def tracing_client() -> Client | None:
    if not settings.langsmith_tracing:
        return None
    if not settings.langsmith_api_key:
        logger.warning('LangSmith is enabled without an API key; tracing is disabled')
        return None
    try:
        return PrivateTracingClient(
            api_url=settings.langsmith_endpoint, api_key=settings.langsmith_api_key,
            workspace_id=settings.langsmith_workspace_id or None, timeout_ms=2000,
            hide_inputs=(lambda _: {}) if settings.langsmith_hide_inputs else _redact,
            hide_outputs=_usage_only if settings.langsmith_hide_outputs else _redact,
            tracing_sampling_rate=settings.langsmith_tracing_sampling_rate,
            omit_traced_runtime_info=True,
        )
    except Exception:
        logger.warning('LangSmith client initialization failed; tracing is disabled')
        return None


def flush_traces() -> None:
    if not settings.langsmith_tracing:
        return
    client = tracing_client()
    if client:
        try:
            client.flush(timeout=2)
        except Exception:
            logger.warning('LangSmith flush did not complete')


@contextmanager
def trace_scope(name: str):
    client = tracing_client()
    # Explicitly disabled contexts also suppress accidental SDK environment tracing.
    with tracing_context(
        enabled=client is not None, client=client,
        parent=get_current_run_tree() or False,
        project_name=settings.langsmith_project, tags=['company-rag-agent'],
        metadata=_safe_metadata({'request_id': request_id_var.get(), 'component': name}),
    ):
        yield


def observed(name: str, run_type: str = 'chain'):
    """Preserve signatures and propagate context through sync/async entry points."""
    def decorate(func):
        traced = traceable(name=name, run_type=run_type)(func)
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                started = monotonic()
                try:
                    if tracing_client() is None:
                        with tracing_context(enabled=False, parent=False):
                            result = await func(*args, **kwargs)
                    else:
                        with trace_scope(name):
                            result = await traced(*args, **kwargs)
                except BaseException:
                    OBSERVED_RUNS.labels(name, 'error').inc()
                    raise
                else:
                    OBSERVED_RUNS.labels(name, 'success').inc()
                    return result
                finally:
                    OBSERVED_DURATION.labels(name).observe(monotonic()-started)
            return async_wrapper
        @wraps(func)
        def wrapper(*args, **kwargs):
            started = monotonic()
            try:
                if tracing_client() is None:
                    with tracing_context(enabled=False, parent=False):
                        result = func(*args, **kwargs)
                else:
                    with trace_scope(name):
                        result = traced(*args, **kwargs)
            except BaseException:
                OBSERVED_RUNS.labels(name, 'error').inc()
                raise
            else:
                OBSERVED_RUNS.labels(name, 'success').inc()
                return result
            finally:
                OBSERVED_DURATION.labels(name).observe(monotonic()-started)
        return wrapper
    return decorate


def submit_with_context(executor, func, *args, **kwargs):
    return executor.submit(copy_context().run, func, *args, **kwargs)


def trace_metadata() -> dict:
    run = get_current_run_tree()
    metadata = {'request_id': request_id_var.get()}
    if run is not None and settings.langsmith_tracing:
        metadata['langsmith_run_id'] = str(run.id)
        metadata['langsmith_trace_id'] = str(run.trace_id)
    return {k: v for k, v in metadata.items() if v}


def annotate_trace(**metadata) -> None:
    run = get_current_run_tree()
    if run is not None:
        run.add_metadata(_safe_metadata(metadata))


class RequestContextMiddleware:
    """Pure ASGI middleware retains tracing for the entire SSE response."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        token = request_id_var.set(str(uuid4()))
        async def send_with_id(message):
            if message['type'] == 'http.response.start':
                message = {**message, 'headers': [*message.get('headers', []),
                           (b'x-request-id', request_id_var.get().encode())]}
            await send(message)
        try:
            @observed('api.request')
            async def serve_request():
                await self.app(scope, receive, send_with_id)
            await serve_request()
        finally:
            request_id_var.reset(token)
