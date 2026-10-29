"""Fault-injection checks for canonical complex-plan step recovery."""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import chat_plan_execute_service as service


USER = {"id": "resume-user", "role": "admin", "position": "finance"}
MESSAGE = "整理本月对账文件并生成复核摘要"
PLAN = {
    "kind": "general_complex_task",
    "steps": [
        {"key": "prepare", "label": "准备摘要", "executor_type": "ai_workflow",
         "ref": "finance-reconciliation", "arguments": {}},
        {"key": "inspect", "label": "检查结果", "executor_type": "mcp",
         "ref": "finance.read_summary", "arguments": {"mode": "read"}},
    ],
}


def make_context(*, first_status="succeeded", message=MESSAGE):
    plan = {**PLAN, "plan_version": service._plan_version(PLAN)}
    binding = service._plan_execution_binding(
        message=message, attachments=[], current_user=USER, plan=plan,
    )
    step = plan["steps"][0]
    prior = {
        "step_name": service._plan_step_id(plan, "prepare"),
        "status": first_status,
        "output_preview": "摘要已准备",
        "metadata": {
            "execution_binding": binding,
            "step_input_hash": service._stable_hash({"binding": binding, "step": step}),
            "output_summary": "摘要已准备",
            "output_manifest": [],
        },
    }
    return plan, {
        "run": {"id": "old-run", "run_type": "chat_plan_execute", "thread_id": "thread-1",
                "user_id": USER["id"], "metadata": {"execution_binding": binding}},
        "summary": {"run_id": "old-run"},
        "raw_detail": {"steps": [prior]},
        "platform_draft": None,
    }


def run_checks():
    plan, resume_context = make_context()
    binding = service._plan_execution_binding(message=MESSAGE, attachments=[], current_user=USER, plan=plan)
    service._validate_general_resume(resume_context=resume_context, thread_id='thread-1',
                                     current_user=USER, binding=binding)
    assert service._looks_like_resume_request('继续上一次计划')
    assert not service._looks_like_resume_request('继续生成另一份对账表')
    try:
        service._validate_general_resume(resume_context=resume_context, thread_id='another-thread',
                                         current_user=USER, binding=binding)
        raise AssertionError('cross-thread resume was accepted')
    except HTTPException as error:
        assert error.status_code == 409
    record_step = Mock(return_value="new-step-id")
    finish_step = Mock(return_value=True)
    workflow = Mock(return_value={"answer": "摘要已准备"})
    mcp = Mock(return_value={"status": "succeeded", "message": "已检查"})
    definition = SimpleNamespace(position_scopes=["finance"])
    with patch.object(service, "record_step", record_step), \
         patch.object(service, "finish_step", finish_step), \
         patch.object(service, "get_ai_workflow", return_value={}), \
         patch.object(service, "run_ai_workflow", workflow), \
         patch.object(service, "get_mcp_tool_definition", return_value=definition), \
         patch.object(service, "list_mcp_tools", return_value={"items": [{"tool_id": "finance.read_summary", "enabled": True}]}), \
         patch.object(service, "execute_managed_mcp_tool", mcp):
        result = service._run_general_complex_plan(
            message=MESSAGE, current_user=USER, thread_id="thread-1", plan=plan,
            run_id="new-run", resume_context=resume_context,
        )
    assert workflow.call_count == 0, "succeeded workflow step was re-executed"
    assert mcp.call_count == 1, "unstarted step was not executed exactly once"
    assert any(item["status_value"] == "running" and item["step_name"] == service._plan_step_id(plan, "inspect")
               for item in [call.kwargs for call in record_step.call_args_list]), record_step.call_args_list
    assert "已检查" in result["answer"]

    changed_plan, changed_context = make_context()
    with patch.object(service, "execute_managed_mcp_tool", Mock()) as execute:
        try:
            service._run_general_complex_plan(
                message=MESSAGE + "，另外导出 CSV", current_user=USER, thread_id="thread-1",
                plan=changed_plan, run_id="new-run", resume_context=changed_context,
            )
            raise AssertionError("changed input was accepted for resume")
        except HTTPException as error:
            assert error.status_code == 409
        assert execute.call_count == 0

    running_plan, running_context = make_context(first_status="running")
    with patch.object(service, "execute_managed_mcp_tool", Mock()) as execute:
        try:
            service._run_general_complex_plan(
                message=MESSAGE, current_user=USER, thread_id="thread-1", plan=running_plan,
                run_id="new-run", resume_context=running_context,
            )
            raise AssertionError("unknown prior outcome was accepted for resume")
        except HTTPException as error:
            assert error.status_code == 409
        assert execute.call_count == 0

    legacy_plan, legacy_context = make_context()
    legacy_context["raw_detail"]["steps"][0]["step_name"] = "plan.prepare"
    with patch.object(service, "execute_managed_mcp_tool", Mock()) as execute:
        try:
            service._run_general_complex_plan(
                message=MESSAGE, current_user=USER, thread_id="thread-1", plan=legacy_plan,
                run_id="new-run", resume_context=legacy_context,
            )
            raise AssertionError("legacy step without binding was accepted")
        except HTTPException as error:
            assert error.status_code == 409
        assert execute.call_count == 0

    assert service._plan_step_id(PLAN, "prepare").startswith("plan:v1-")

    mcp_plan = {"kind": "general_complex_task", "steps": [PLAN["steps"][1]]}
    mcp_plan["plan_version"] = service._plan_version(mcp_plan)
    mcp_binding = service._plan_execution_binding(message=MESSAGE, attachments=[],
                                                  current_user=USER, plan=mcp_plan)
    mcp_prior = {
        "step_name": service._plan_step_id(mcp_plan, "inspect"), "status": "succeeded",
        "output_preview": "已检查", "metadata": {
            "execution_binding": mcp_binding,
            "step_input_hash": service._stable_hash({"binding": mcp_binding, "step": mcp_plan["steps"][0]}),
            "output_summary": "已检查", "output_manifest": [],
        },
    }
    mcp_context = {"summary": {"run_id": "old-run"}, "raw_detail": {"steps": [mcp_prior]},
                   "platform_draft": None}
    with patch.object(service, "get_mcp_tool_definition", return_value=definition), \
         patch.object(service, "list_mcp_tools", return_value={"items": [{"tool_id": "finance.read_summary", "enabled": True}]}), \
         patch.object(service, "execute_managed_mcp_tool", Mock()) as execute:
        service._run_general_complex_plan(message=MESSAGE, current_user=USER, thread_id="thread-1",
                                          plan=mcp_plan, run_id="new-run", resume_context=mcp_context)
        assert execute.call_count == 0, "completed MCP action was replayed"
    print("chat plan resume checks passed")


if __name__ == "__main__":
    run_checks()
