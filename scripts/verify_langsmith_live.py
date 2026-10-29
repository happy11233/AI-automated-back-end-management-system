"""Real LangSmith upload/readback with privacy assertions; no simulated service."""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import logging
from pathlib import Path
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', action='store_true', help='Make one real, short model call (billable)')
    args = parser.parse_args()
    from app.config import settings
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        raise SystemExit('Configure LANGSMITH_TRACING and LANGSMITH_API_KEY in private .env first')
    if not settings.langsmith_hide_inputs or not settings.langsmith_hide_outputs:
        raise SystemExit('Live verification requires both LangSmith privacy settings enabled')
    # Force only this verification process to be sampled, leaving configured 10% unchanged.
    settings.langsmith_tracing_sampling_rate = 1.0
    from app.observability import (
        observed, tracing_client, request_id_var, submit_with_context, trace_metadata,
    )
    client = tracing_client()
    if client is None:
        raise SystemExit('LangSmith private client initialization failed')
    request_id = 'verification-'+uuid4().hex
    sentinel = 'privacy-canary-'+uuid4().hex
    expected_ids = {}

    @observed('verification.langsmith.transform', 'tool')
    def transform(value: str):
        expected_ids['transform'] = trace_metadata()['langsmith_run_id']
        assert request_id_var.get() == request_id
        return {'digest': hashlib.sha256(value.encode()).hexdigest(), 'private_value': value}

    @observed('verification.langsmith.async', 'tool')
    async def transform_async(value: str):
        expected_ids['async'] = trace_metadata()['langsmith_run_id']
        return {'private_value': value}

    @observed('verification.langsmith.error', 'tool')
    def privacy_error(value: str):
        expected_ids['error'] = trace_metadata()['langsmith_run_id']
        raise ValueError(value)

    @observed('verification.langsmith.acceptance')
    def acceptance(value: str):
        expected_ids['root'] = trace_metadata()['langsmith_run_id']
        with ThreadPoolExecutor(1) as executor:
            assert submit_with_context(executor, transform, value).result()['digest']
        asyncio.run(transform_async(value))
        try:
            privacy_error(value)
        except ValueError:
            pass
        if args.model:
            from app.llm import chat_model
            response = chat_model.bind(max_tokens=128, extra_body={'enable_thinking': False}).invoke(
                'This is a monitoring connectivity check. Reply only: OK.'
            )
            assert response.content, 'Real model did not return content'
        return {'private_value': value}

    token = request_id_var.set(request_id)
    try:
        acceptance(sentinel)
    finally:
        request_id_var.reset(token)
    client.flush(timeout=15)
    deadline = time.monotonic()+50
    runs = {}
    while time.monotonic() < deadline:
        try:
            runs = {key: client.read_run(run_id, load_child_runs=key == 'root')
                    for key, run_id in expected_ids.items()}
            if all(run.end_time for run in runs.values()):
                break
        except Exception as error:
            if type(error).__name__ not in {'LangSmithNotFoundError', 'LangSmithRateLimitError'}:
                raise
        time.sleep(0.5)
    assert len(runs) == len(expected_ids) and all(run.end_time for run in runs.values()), 'Cloud readback deadline exceeded'
    root = runs['root']
    children = list(root.child_runs or [])
    checked = list(runs.values())+children
    for run in checked:
        assert run.inputs in ({}, None), 'Inputs were not hidden'
        assert set(run.outputs or {}) <= {'usage_metadata'}, 'Output content was not hidden'
        assert sentinel not in run.model_dump_json(), 'Privacy canary escaped into cloud trace'
    for key in ('transform', 'async', 'error'):
        assert str(runs[key].parent_run_id) == str(root.id), 'Parent trace mismatch'
        assert runs[key].extra.get('metadata', {}).get('request_id') == request_id
    assert runs['error'].error == 'Execution failed; details retained in application logs.'
    assert not root.error and (root.end_time-root.start_time).total_seconds() >= 0
    llm_runs = [run for run in children if run.run_type == 'llm']
    if args.model:
        assert llm_runs, 'Real model child trace was not exported'
    print(json.dumps({
        'ok': True, 'project': settings.langsmith_project,
        'root_run_id': str(root.id), 'request_id': request_id,
        'verified_runs': len({str(run.id) for run in checked}),
        'privacy': 'hidden inputs/outputs, scrubbed error; cloud readback passed',
        'real_model_call': bool(args.model),
        'model_token_usage': [run.total_tokens for run in llm_runs],
    }, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never echo SDK exception text, HTTP headers or secret-bearing config.
        logging.getLogger(__name__).error('LangSmith live verification failed: %s', type(error).__name__)
        raise SystemExit(1) from None
