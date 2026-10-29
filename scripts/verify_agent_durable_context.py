"""Verify the low-risk agent reconstructs each turn from persisted chat context."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.low_risk_agent import run_low_risk_agent
from app.db import close_pool, execute, fetch_one, open_pool
from app.services.context_service import build_context_bundle
from app.services.logging_service import save_chat_message


def main():
    open_pool()
    thread_id = f"verify-agent-context-{uuid4().hex}"
    try:
        row = fetch_one("SELECT id,username,role,position FROM users WHERE role='admin' LIMIT 1")
        assert row, "local verification requires an admin fixture"
        user = {"id": str(row[0]), "username": row[1], "role": row[2], "position": row[3]}
        execute("INSERT INTO chat_threads(id,user_id,title,position) VALUES (%s,%s,'agent context test',%s)",
                (thread_id, user["id"], user["position"]))
        save_chat_message(thread_id=thread_id, user_id=user["id"], role="user",
                          content="先问报销规则", metadata={"entrypoint": "agent"})
        save_chat_message(thread_id=thread_id, user_id=user["id"], role="assistant",
                          content="报销规则见知识库", metadata={"entrypoint": "agent"})

        invoke = Mock(return_value={"messages": [SimpleNamespace(content="后续回答") ]})
        with patch("app.agents.low_risk_agent.create_agent", return_value=SimpleNamespace(invoke=invoke)) as create:
            result = run_low_risk_agent(message="那审批呢？", thread_id=thread_id, current_user=user,
                                        context=build_context_bundle(thread_id, user["id"]))
        assert result["answer"] == "后续回答"
        assert "checkpointer" not in create.call_args.kwargs, "agent retained process-local memory"
        messages = invoke.call_args.args[0]["messages"]
        assert "先问报销规则" in messages[0]["content"]
        assert "报销规则见知识库" in messages[0]["content"]
        assert messages[1]["content"] == "那审批呢？"
        assert invoke.call_args.kwargs["config"]["configurable"]["thread_id"] == f"{user['id']}:{thread_id}"
        child_code = (
            "import json,sys; from app.db import open_pool,close_pool; "
            "from app.services.context_service import build_context_bundle; "
            "open_pool(); print(json.dumps([m['content'] for m in "
            "build_context_bundle(sys.argv[1],sys.argv[2])['recent_messages']],ensure_ascii=False)); close_pool()"
        )
        child_output = subprocess.check_output([sys.executable, "-c", child_code, thread_id, user["id"]],
                                               cwd=ROOT, text=True)
        assert json.loads(child_output) == ["先问报销规则", "报销规则见知识库"]
        print("agent durable-context checks passed: fresh process reads persisted history")
    finally:
        execute("DELETE FROM chat_threads WHERE id=%s", (thread_id,))
        close_pool()


if __name__ == "__main__":
    main()
