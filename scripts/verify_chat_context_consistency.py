"""Local PostgreSQL checks for chat locking, context CAS, and order reference rules."""
from __future__ import annotations

import asyncio
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app.main as main
from app.db import close_pool, execute, fetch_one, open_pool
from app.graph.workflow import _build_contextual_query, extract_order_no
from app.observability import request_id_var
from app.services import context_service
from app.services.chat_thread_lock_service import ChatThreadLock
from app.services.logging_service import create_chat_thread, save_chat_message
from app.services.run_record_service import now_ms, start_run


def take_lock(thread_id: str, timeout: float = 0.2) -> str:
    with ChatThreadLock(thread_id, timeout_seconds=timeout):
        return "acquired"


async def drain(response: StreamingResponse) -> None:
    async for _ in response.body_iterator:
        pass


async def cancel_after_first_chunk(response: StreamingResponse) -> None:
    await response.body_iterator.__anext__()
    await response.body_iterator.aclose()


def main_check() -> None:
    open_pool()
    thread_id = None
    run_ids = []
    try:
        user = fetch_one("SELECT id, username, role, position FROM users WHERE role = 'admin' LIMIT 1")
        assert user, "local verification requires an admin fixture"
        current_user = {"id": str(user[0]), "username": user[1], "role": user[2], "position": user[3]}
        thread_id = create_chat_thread(user_id=current_user["id"], title="chat context verification")["id"]

        first = context_service.upsert_thread_state(
            thread_id=thread_id, user_id=current_user["id"],
            order_no="AMZ-US-250-123456", expected_context_version=0,
            slots={"pending_external_action": {"status": "waiting_confirmation"}},
        )
        assert first == 1
        try:
            context_service.upsert_thread_state(
                thread_id=thread_id, user_id=current_user["id"],
                order_no="AMZ-US-250-OLD", expected_context_version=0,
            )
            raise AssertionError("stale context write was accepted")
        except HTTPException as error:
            assert error.status_code == 409

        with patch.object(context_service, "maybe_update_thread_summary"), patch.object(
            context_service, "maybe_extract_user_memories"
        ):
            context_service.update_context_after_turn(
                thread_id=thread_id, user_id=current_user["id"],
                user_message="查询其他问题", graph_result={"answer": "请说明订单号", "intent": "order"},
                expected_context_version=1,
            )
        state = context_service.get_thread_state(thread_id)
        assert state["context_version"] == 2 and state["order_no"] is None, state
        assert state["slots"]["pending_external_action"]["active"] is False, state

        prior = {"state": {"order_no": "AMZ-US-250-123456"}}
        with patch("app.graph.workflow.extract_order_no_from_text", return_value=None):
            generic = extract_order_no({"user_input": "查一下订单状态", "context": prior})
            referred = extract_order_no({"user_input": "这个订单到哪里了", "context": prior})
            explicit = extract_order_no({"user_input": "查询 AMZ-US-250-789012", "context": prior})
            erp_generic = _build_contextual_query({
                "user_input": "查销售发票", "intent": "erp", "context": prior,
            })
        assert generic == {"order_no": None, "order_no_source": "missing"}, generic
        assert referred == {"order_no": "AMZ-US-250-123456", "order_no_source": "inherited"}, referred
        assert explicit == {"order_no": "AMZ-US-250-789012", "order_no_source": "explicit"}, explicit
        assert erp_generic == "查销售发票", erp_generic

        context_service.upsert_thread_state(
            thread_id=thread_id, user_id=current_user["id"],
            order_no="AMZ-US-250-123456", expected_context_version=2,
        )
        with patch.object(context_service, "maybe_update_thread_summary"), patch.object(
            context_service, "maybe_extract_user_memories"
        ):
            context_service.update_context_after_turn(
                thread_id=thread_id, user_id=current_user["id"],
                user_message="这个订单到哪里了", expected_context_version=3,
                graph_result={"answer": "已查询", "intent": "order",
                              "order_no": "AMZ-US-250-123456", "order_no_source": "inherited"},
            )
        inherited_audit = fetch_one(
            "SELECT count(*) FROM audit_logs WHERE resource_type = 'thread' "
            "AND resource_id = %s AND action = 'chat.order_inherited'", (thread_id,),
        )[0]
        assert inherited_audit == 1

        marker = request_id_var.set("chat-context-verification")
        try:
            save_chat_message(thread_id, current_user["id"], "user", "request id verification")
        finally:
            request_id_var.reset(marker)
        saved = fetch_one(
            "SELECT metadata FROM chat_messages WHERE thread_id = %s ORDER BY created_at DESC LIMIT 1",
            (thread_id,),
        )[0]
        assert saved["request_id"] == "chat-context-verification", saved

        with ChatThreadLock(thread_id, timeout_seconds=0.2):
            with ThreadPoolExecutor(max_workers=2) as workers:
                same = workers.submit(take_lock, thread_id)
                other = workers.submit(take_lock, thread_id + "-other")
                assert other.result() == "acquired"
                try:
                    same.result()
                    raise AssertionError("same thread acquired the lock twice")
                except HTTPException as error:
                    assert error.status_code == 423
        assert take_lock(thread_id) == "acquired"

        with patch.object(main, "_chat_stream_unlocked", return_value=StreamingResponse(
            iter(["data: one\n\n", "data: two\n\n"]), media_type="text/event-stream",
        )):
            response = main.chat_stream(main.ChatRequest(message="你好", thread_id=thread_id), current_user)
        with ThreadPoolExecutor(max_workers=1) as workers:
            blocked = workers.submit(take_lock, thread_id)
            try:
                blocked.result()
                raise AssertionError("stream released lock before its body was consumed")
            except HTTPException as error:
                assert error.status_code == 423
        asyncio.run(drain(response))
        assert take_lock(thread_id) == "acquired"

        cancelled_run_id = start_run(
            run_type="chat_stream", app_id="chat-context-verification",
            app_name="chat context verification", entrypoint="/chat/stream",
            current_user=current_user, thread_id=thread_id,
        )
        run_ids.append(cancelled_run_id)
        fake_stream = StreamingResponse(
            iter(["data: one\n\n", "data: two\n\n"]), media_type="text/event-stream",
        )
        fake_stream.chat_run_id = cancelled_run_id
        fake_stream.chat_started_ms = now_ms()
        with patch.object(main, "_chat_stream_unlocked", return_value=fake_stream):
            cancelled = main.chat_stream(main.ChatRequest(message="你好", thread_id=thread_id), current_user)
        asyncio.run(cancel_after_first_chunk(cancelled))
        assert take_lock(thread_id) == "acquired"
        run_status = fetch_one("SELECT status, metadata FROM automation_runs WHERE id = %s", (cancelled_run_id,))
        assert run_status[0] == "failed" and run_status[1]["cancelled"] is True, run_status

        active = 0
        max_active = 0
        counter_lock = threading.Lock()

        def fake_chat(request, _user):
            nonlocal active, max_active
            with counter_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.15)
            with counter_lock:
                active -= 1
            return {"thread_id": request.thread_id, "answer": request.message}

        with patch.object(main, "_chat_unlocked", side_effect=fake_chat):
            with ThreadPoolExecutor(max_workers=2) as workers:
                responses = [workers.submit(main.chat, main.ChatRequest(
                    message=f"message-{i}", thread_id=thread_id,
                ), current_user) for i in range(2)]
                assert all(item.result()["thread_id"] == thread_id for item in responses)
        assert max_active == 1, max_active

        print(json.dumps({"ok": True, "context_version": state["context_version"],
                          "stale_update": 409, "same_thread_timeout": 423,
                          "different_thread_parallel": True, "stream_release": True,
                          "stream_cancel_release": True,
                          "same_thread_serial": max_active == 1,
                          "order_inheritance": referred["order_no_source"]}))
    finally:
        for run_id in run_ids:
            execute("DELETE FROM automation_runs WHERE id = %s", (run_id,))
        if thread_id:
            execute("DELETE FROM audit_logs WHERE resource_type = 'thread' AND resource_id = %s", (thread_id,))
            execute("DELETE FROM chat_threads WHERE id = %s", (thread_id,))
        close_pool()


if __name__ == "__main__":
    main_check()
