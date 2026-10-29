"""Exercise signed platform callbacks against the local API and PostgreSQL.

Creates only local draft/task rows. No external executor is called.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import close_pool, execute, fetch_one, open_pool
from app.services.platform_action_executor_service import (
    _mark_dispatch_effects_completed,
    _record_async_dispatch,
)
from app.services.platform_draft_service import (
    create_platform_action_execution,
    create_platform_draft,
    create_platform_execution_task,
    finish_platform_execution_task,
    get_platform_draft,
    get_platform_execution_task_by_token,
    mark_platform_execution_task_dispatching,
    mark_platform_execution_task_waiting_callback,
    finish_platform_action_execution,
    update_platform_draft_writeback,
)

BASE = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8002").rstrip("/")
SECRET = os.getenv("PLATFORM_ACTION_EXECUTION_CALLBACK_SECRET", "local-platform-callback-secret")


def make_task(*, waiting: bool = True) -> tuple[dict, dict, dict]:
    draft = create_platform_draft(
        draft_type="listing", platform="test", external_target="local_fixture",
        title=f"callback verification {uuid.uuid4().hex}", position="operations",
        owner_user_id=None, source_run_id=None, source_resource_type=None,
        source_resource_id=None, content={"sku": "CALLBACK-TEST"},
    )
    task = create_platform_execution_task(
        draft_id=draft["id"], action_type="write_listing_draft",
        target="local_fixture", request_payload={}, requested_by=None,
    )
    execution = create_platform_action_execution(
        draft_id=draft["id"], action_type="write_listing_draft",
        executor_type="webhook", target="local_fixture", status_value="running",
        request_payload={},
    )
    task = mark_platform_execution_task_dispatching(
        task_id=task["id"], latest_execution_id=execution["id"], target="local_fixture",
    )
    if waiting:
        task = mark_platform_execution_task_waiting_callback(
            task_id=task["id"], latest_execution_id=execution["id"],
            attempt_count=task["attempt_count"], response_payload={"accepted": True},
        )
        assert task and task["status"] == "waiting_callback"
    return draft, task, execution


def callback(task: dict, execution: dict, *, result: str, event_id: str,
             token: str | None = None, attempt: int | None = None,
             nonce: str | None = None) -> requests.Response:
    payload = {
        "callback_token": token or task["callback_token"],
        "attempt_count": attempt or task["attempt_count"],
        "execution_id": execution["id"],
        "external_event_id": event_id,
        "status": result,
        "response_payload": {"external_reference": f"local-{event_id}"},
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    nonce = nonce or uuid.uuid4().hex
    digest = hashlib.sha256(body).hexdigest()
    signature = "sha256=" + hmac.new(
        SECRET.encode(), f"v1:{timestamp}:{nonce}:{task['id']}:{digest}".encode(), hashlib.sha256,
    ).hexdigest()
    return requests.post(
        f"{BASE}/platform-execution-tasks/{task['id']}/callback", data=body,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Callback-Signature": signature,
            "X-Platform-Callback-Timestamp": timestamp,
            "X-Platform-Callback-Nonce": nonce,
        }, timeout=15,
    )


def counts(task_id: str) -> tuple[int, int]:
    audit_count = fetch_one(
        "SELECT count(*) FROM audit_logs WHERE resource_type = 'platform_execution_task' "
        "AND resource_id = %s AND action = 'platform_execution.callback'", (task_id,),
    )[0]
    notice_count = fetch_one(
        "SELECT count(*) FROM notifications WHERE resource_type = 'platform_execution_task' "
        "AND resource_id = %s AND type IN ('platform_execution.succeeded', 'platform_execution.failed')",
        (task_id,),
    )[0]
    return audit_count, notice_count


def main() -> None:
    assert requests.get(f"{BASE}/health", timeout=3).status_code == 200
    open_pool()
    fixtures = []
    try:
        draft, task, execution = make_task()
        fixtures.append((draft, task))
        with ThreadPoolExecutor(max_workers=2) as workers:
            calls = [workers.submit(callback, task, execution, result=result,
                                    event_id=f"race-{result}") for result in ("succeeded", "failed")]
            responses = [call.result() for call in calls]
        assert all(response.status_code == 200 for response in responses), [
            (response.status_code, response.text[:300]) for response in responses
        ]
        statuses = {response.json()["task"]["status"] for response in responses}
        assert len(statuses) == 1, statuses
        before = counts(task["id"])
        assert before[0] == 1 and before[1] >= 1, before
        replay = callback(task, execution, result="succeeded", event_id="race-succeeded",
                          nonce="replay-same-event")
        assert replay.status_code == 200 and replay.json()["task"]["status"] in statuses, replay.text
        same_nonce_replay = callback(task, execution, result="succeeded", event_id="race-succeeded",
                                     nonce="replay-same-event")
        assert same_nonce_replay.status_code == 200, same_nonce_replay.text
        assert counts(task["id"]) == before
        changed_event = callback(task, execution, result="failed", event_id="race-succeeded")
        assert changed_event.status_code == 409, changed_event.text

        failure_draft, failure_task, failure_execution = make_task()
        fixtures.append((failure_draft, failure_task))
        failure = callback(failure_task, failure_execution, result="failed", event_id="expected-failure")
        assert failure.status_code == 200, failure.text
        assert failure.json()["task"]["status"] == "failed"
        assert failure.json()["draft"]["writeback_status"] == "failed"
        failure_before = counts(failure_task["id"])
        failure_replay = callback(failure_task, failure_execution, result="failed", event_id="expected-failure")
        assert failure_replay.status_code == 200 and counts(failure_task["id"]) == failure_before

        retry_draft, retry_task, first_execution = make_task()
        fixtures.append((retry_draft, retry_task))
        old_token = retry_task["callback_token"]
        finish_platform_execution_task(task_id=retry_task["id"], status_value="failed")
        second_execution = create_platform_action_execution(
            draft_id=retry_draft["id"], action_type="write_listing_draft",
            executor_type="webhook", target="local_fixture", status_value="running",
            request_payload={},
        )
        retry_task = mark_platform_execution_task_dispatching(
            task_id=retry_task["id"], latest_execution_id=second_execution["id"],
            target="local_fixture", rotate_callback_token=True,
        )
        assert retry_task["callback_token"] != old_token and retry_task["attempt_count"] == 2
        stale = callback(retry_task, first_execution, result="succeeded", event_id="old-attempt",
                         token=old_token, attempt=1)
        assert stale.status_code == 404, stale.text
        mismatched = callback(retry_task, first_execution, result="succeeded", event_id="wrong-execution")
        assert mismatched.status_code == 409, mismatched.text
        current = callback(retry_task, second_execution, result="succeeded", event_id="current-attempt")
        assert current.status_code == 200 and current.json()["task"]["status"] == "succeeded", current.text

        early_draft, early_task, early_execution = make_task(waiting=False)
        fixtures.append((early_draft, early_task))
        early = callback(early_task, early_execution, result="succeeded", event_id="early-callback")
        assert early.status_code == 200, early.text
        late_dispatch = _record_async_dispatch(
            task=early_task, draft=early_draft, execution=early_execution,
            response_payload={"accepted": True}, action_type="write_listing_draft",
            final_publish=False, executor_config={},
        )
        assert late_dispatch == (None, None, None), late_dispatch
        after_early = get_platform_draft(draft_id=early_draft["id"], current_user={"role": "admin"})
        assert after_early["writeback_status"] == "external_synced", after_early

        for _ in range(3):
            race_draft, race_task, race_execution = make_task(waiting=False)
            fixtures.append((race_draft, race_task))
            with ThreadPoolExecutor(max_workers=2) as workers:
                dispatch_future = workers.submit(
                    _record_async_dispatch, task=race_task, draft=race_draft,
                    execution=race_execution, response_payload={"accepted": True},
                    action_type="write_listing_draft", final_publish=False,
                    executor_config={},
                )
                callback_future = workers.submit(
                    callback, race_task, race_execution, result="succeeded",
                    event_id=f"dispatch-race-{uuid.uuid4().hex}",
                )
                dispatch_future.result()
                race_response = callback_future.result()
            assert race_response.status_code == 200, race_response.text
            final_task = get_platform_execution_task_by_token(
                task_id=race_task["id"], callback_token=race_task["callback_token"],
            )
            final_draft = get_platform_draft(draft_id=race_draft["id"], current_user={"role": "admin"})
            assert final_task["status"] == "succeeded" and final_draft["writeback_status"] == "external_synced"

        sync_draft, sync_task, sync_execution = make_task(waiting=False)
        fixtures.append((sync_draft, sync_task))
        sync_task = finish_platform_execution_task(
            task_id=sync_task["id"], status_value="succeeded",
            expected_status="dispatching", expected_execution_id=sync_execution["id"],
            metadata={"dispatch_processing_at": "in-progress"},
        )
        assert sync_task
        with ThreadPoolExecutor(max_workers=1) as workers:
            late_callback = workers.submit(
                callback, sync_task, sync_execution, result="failed", event_id="sync-winner",
            )
            time.sleep(0.1)
            assert not late_callback.done(), "callback returned before synchronous writeback completed"
            finish_platform_action_execution(
                execution_id=sync_execution["id"], status_value="succeeded",
            )
            update_platform_draft_writeback(
                draft_id=sync_draft["id"], writeback_status="external_synced",
                writeback_message="sync completed",
            )
            _mark_dispatch_effects_completed(sync_task)
            sync_replay = late_callback.result()
        assert sync_replay.status_code == 200, sync_replay.text
        assert sync_replay.json()["task"]["status"] == "succeeded"
        assert sync_replay.json()["draft"]["writeback_status"] == "external_synced"
        assert counts(sync_task["id"]) == (0, 0)
        print(json.dumps({"ok": True, "race_result": next(iter(statuses)),
                          "race_audits": before[0], "race_notifications": before[1],
                          "replay": replay.status_code, "stale_token": stale.status_code,
                          "wrong_execution": mismatched.status_code,
                          "current_attempt": current.status_code,
                          "failed_callback": failure.status_code,
                          "early_callback": early.status_code, "dispatch_races": 3,
                          "sync_callback": sync_replay.status_code}))
    finally:
        for draft, task in fixtures:
            execute("DELETE FROM notifications WHERE resource_type = 'platform_execution_task' AND resource_id = %s", (task["id"],))
            execute("DELETE FROM audit_logs WHERE resource_type = 'platform_execution_task' AND resource_id = %s", (task["id"],))
            execute("DELETE FROM platform_drafts WHERE id = %s", (draft["id"],))
        close_pool()


if __name__ == "__main__":
    main()
