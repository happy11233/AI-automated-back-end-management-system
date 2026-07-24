from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import psycopg
import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
ADMIN_USERNAME = os.getenv("VERIFY_ADMIN_USERNAME", "admin_demo")
ADMIN_PASSWORD = os.getenv("VERIFY_ADMIN_PASSWORD", "Admin123456")
EMPLOYEE_USERNAME = os.getenv("VERIFY_OPERATIONS_USERNAME", "operations_demo")
EMPLOYEE_PASSWORD = os.getenv("VERIFY_OPERATIONS_PASSWORD", "Operations123456")
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
BOUND_REGRESSION_TIMEOUT_SECONDS = int(os.getenv("VERIFY_BOUND_REGRESSION_TIMEOUT_SECONDS", "720"))
SECRET_MARKERS = ["Bearer ", "Authorization", "api_key", "api_secret", "callback_token", "database_url", "password"]


def main() -> None:
    marker = f"verify-flow-version-{int(time.time())}-{uuid4().hex[:8]}"
    created_version_ids: list[str] = []
    created_publication_ids: list[str] = []
    created_evidence_ids: list[str] = []
    preserved_publications: list[dict[str, Any]] = []
    preserved_version_statuses: list[dict[str, Any]] = []

    ensure_schema()
    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    employee_token = login(EMPLOYEE_USERNAME, EMPLOYEE_PASSWORD)

    flows = get_json(admin_token, "/automation-flows")["items"]
    flow = pick_flow(flows, "财务 Excel 生成")
    flow_path = quote(flow["id"], safe="")
    flow_db_id = ensure_flow_projection_for_cleanup(admin_token, flow["id"])
    preserved_publications = load_active_publications(flow_db_id)
    preserved_version_statuses = load_version_statuses(flow_db_id)
    salary_flow = pick_flow(flows, "统计工资")
    salary_flow_db_id = ensure_flow_projection_for_cleanup(admin_token, salary_flow["id"])
    preserved_publications.extend(load_active_publications(salary_flow_db_id, "staging"))
    preserved_version_statuses.extend(load_version_statuses(salary_flow_db_id))
    customer_service_flow = pick_flow(flows, "客服消息自动化闭环")
    customer_service_flow_db_id = ensure_flow_projection_for_cleanup(admin_token, customer_service_flow["id"])
    preserved_publications.extend(load_active_publications(customer_service_flow_db_id, "staging"))
    preserved_version_statuses.extend(load_version_statuses(customer_service_flow_db_id))

    try:
        assert_forbidden(employee_token, f"/automation-flows/{flow_path}/versions")
        assert_forbidden(employee_token, "/automation-flow-versions/00000000-0000-0000-0000-000000000000")

        first_version = post_json(
            admin_token,
            f"/automation-flows/{flow_path}/versions",
            {
                "change_summary": f"{marker} 第一版草稿",
                "publish_notes": f"{marker} 第一版发布说明",
            },
        )["item"]
        created_version_ids.append(first_version["id"])
        assert first_version["status"] == "draft", first_version
        assert first_version["version_number"] >= 1, first_version
        assert first_version["input_schema"], first_version
        assert first_version["output_schema"], first_version
        assert first_version["allowed_tools"], first_version

        listed_versions = get_json(admin_token, f"/automation-flows/{flow_path}/versions")["items"]
        assert any(item["id"] == first_version["id"] for item in listed_versions), listed_versions

        secret_create_response = post_raw(
            admin_token,
            f"/automation-flows/{flow_path}/versions",
            {
                "change_summary": f"{marker} 不允许保存密钥",
                "publish_notes": "callback_token=should_not_be_saved",
            },
        )
        assert secret_create_response.status_code == 400, secret_create_response.text

        updated_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {
                "change_summary": f"{marker} 第一版已补治理说明",
                "approval_policy": "第一阶段版本治理验证：发布前由管理员确认。",
                "failure_strategy": "第一阶段版本治理验证：失败时保留运行记录并允许回滚。",
                "publish_notes": f"{marker} 第一版治理字段更新",
                "prompt_summary": f"{first_version['prompt_summary']}。{marker} 低代码 Prompt 摘要编辑。",
                "prompt_template_preview": f"{first_version['prompt_template_preview']}\n\n# {marker} 低代码 Prompt 模板编辑",
            },
        )["item"]
        assert updated_version["status"] == "draft", updated_version
        assert updated_version["approval_policy"].startswith("第一阶段版本治理验证"), updated_version
        assert marker in updated_version["prompt_summary"], updated_version
        assert marker in updated_version["prompt_template_preview"], updated_version

        original_allowed_tools = list(updated_version["allowed_tools"])
        if len(original_allowed_tools) > 1:
            allowed_tools_subset = original_allowed_tools[:-1]
            tools_subset_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": allowed_tools_subset,
                },
            )["item"]
            assert tools_subset_version["allowed_tools"] == allowed_tools_subset, tools_subset_version
            removed_tool = original_allowed_tools[-1]
            assert removed_tool not in (
                tools_subset_version["model_config"].get("tool_parameters") or {}
            ), tools_subset_version

            empty_tools_response = patch_raw(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": [],
                },
            )
            assert empty_tools_response.status_code == 400, empty_tools_response.text

            overreach_tools_response = patch_raw(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": [*allowed_tools_subset, "unsafe.shell"],
                },
            )
            assert overreach_tools_response.status_code == 400, overreach_tools_response.text
            assert "代码投影外工具" in overreach_tools_response.text, overreach_tools_response.text

            updated_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": original_allowed_tools,
                },
            )["item"]
            assert updated_version["allowed_tools"] == original_allowed_tools, updated_version

        original_allowed_resources = list(updated_version["allowed_erp_resources"])
        if len(original_allowed_resources) > 1:
            allowed_resources_subset = original_allowed_resources[:-1]
            resources_subset_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": updated_version["allowed_tools"],
                    "allowed_erp_resources": allowed_resources_subset,
                },
            )["item"]
            assert [item["resource"] for item in resources_subset_version["allowed_erp_resources"]] == [
                item["resource"] for item in allowed_resources_subset
            ], resources_subset_version

            empty_resources_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": updated_version["allowed_tools"],
                    "allowed_erp_resources": [],
                },
            )["item"]
            assert empty_resources_version["allowed_erp_resources"] == [], empty_resources_version

            overreach_resources_response = patch_raw(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": updated_version["allowed_tools"],
                    "allowed_erp_resources": [
                        *allowed_resources_subset,
                        {
                            "resource": "Unsafe Secret Ledger",
                            "label": "越权资源",
                            "description": "不应允许保存的投影外 ERP 资源。",
                            "provider_refs": {"erpnext": "Unsafe Secret Ledger"},
                        },
                    ],
                },
            )
            assert overreach_resources_response.status_code == 400, overreach_resources_response.text
            assert "代码投影外 ERP 资源" in overreach_resources_response.text, overreach_resources_response.text

            updated_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {
                    "change_summary": updated_version["change_summary"],
                    "approval_policy": updated_version["approval_policy"],
                    "failure_strategy": updated_version["failure_strategy"],
                    "publish_notes": updated_version["publish_notes"],
                    "prompt_summary": updated_version["prompt_summary"],
                    "prompt_template_preview": updated_version["prompt_template_preview"],
                    "allowed_tools": updated_version["allowed_tools"],
                    "allowed_erp_resources": original_allowed_resources,
                },
            )["item"]
            assert [item["resource"] for item in updated_version["allowed_erp_resources"]] == [
                item["resource"] for item in original_allowed_resources
            ], updated_version

        original_input_schema = json.loads(json.dumps(updated_version["input_schema"], ensure_ascii=False))
        edited_input_schema = json.loads(json.dumps(original_input_schema, ensure_ascii=False))
        edited_input_schema[0]["label"] = f"{marker} 输入字段治理编辑"
        input_schema_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"input_schema": edited_input_schema},
        )["item"]
        assert input_schema_version["input_schema"] == edited_input_schema, input_schema_version

        empty_input_schema_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"input_schema": []},
        )
        assert empty_input_schema_response.status_code == 400, empty_input_schema_response.text

        bad_input_schema_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {
                "input_schema": [
                    {
                        "name": "",
                        "label": "坏字段",
                        "type": "api_key",
                    }
                ]
            },
        )
        assert bad_input_schema_response.status_code == 400, bad_input_schema_response.text

        updated_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"input_schema": original_input_schema},
        )["item"]
        assert updated_version["input_schema"] == original_input_schema, updated_version

        original_output_schema = json.loads(json.dumps(updated_version["output_schema"], ensure_ascii=False))
        edited_output_schema = json.loads(json.dumps(original_output_schema, ensure_ascii=False))
        edited_output_schema[0]["label"] = f"{marker} 输出字段治理编辑"
        output_schema_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"output_schema": edited_output_schema},
        )["item"]
        assert output_schema_version["output_schema"] == edited_output_schema, output_schema_version

        empty_output_schema_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"output_schema": []},
        )
        assert empty_output_schema_response.status_code == 400, empty_output_schema_response.text

        bad_output_schema_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {
                "output_schema": [
                    {
                        "name": "",
                        "label": "坏字段",
                        "type": "api_key",
                    }
                ]
            },
        )
        assert bad_output_schema_response.status_code == 400, bad_output_schema_response.text

        updated_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"output_schema": original_output_schema},
        )["item"]
        assert updated_version["output_schema"] == original_output_schema, updated_version

        original_steps = json.loads(json.dumps(updated_version["steps"], ensure_ascii=False))
        assert original_steps, updated_version
        if len(original_steps) > 1:
            steps_subset = original_steps[:-1]
            steps_subset_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {"steps": steps_subset},
            )["item"]
            assert steps_subset_version["steps"] == steps_subset, steps_subset_version

            reordered_steps = [original_steps[1], original_steps[0], *original_steps[2:]]
            reordered_steps_version = patch_json(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {"steps": reordered_steps},
            )["item"]
            assert reordered_steps_version["steps"] == reordered_steps, reordered_steps_version

            invalid_order_steps = [original_steps[-1], *original_steps[:-1]]
            invalid_order_steps_response = patch_raw(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {"steps": invalid_order_steps},
            )
            assert invalid_order_steps_response.status_code == 400, invalid_order_steps_response.text
            assert "执行步骤顺序不合法" in invalid_order_steps_response.text, invalid_order_steps_response.text

            tampered_step = json.loads(json.dumps(original_steps[0], ensure_ascii=False))
            tampered_step["name"] = f"{tampered_step.get('name', '')} {marker} 篡改步骤名"
            tampered_steps_response = patch_raw(
                admin_token,
                f"/automation-flow-versions/{first_version['id']}",
                {"steps": [tampered_step, *original_steps[1:]]},
            )
            assert tampered_steps_response.status_code == 400, tampered_steps_response.text
            assert "执行步骤对象内容不允许编辑" in tampered_steps_response.text, tampered_steps_response.text

        empty_steps_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"steps": []},
        )
        assert empty_steps_response.status_code == 400, empty_steps_response.text

        overreach_steps_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {
                "steps": [
                    {
                        "id": "unsafe-secret-step",
                        "name": "越权步骤",
                        "inputs": [],
                        "retryable": False,
                    }
                ]
            },
        )
        assert overreach_steps_response.status_code == 400, overreach_steps_response.text
        assert "代码投影外执行步骤" in overreach_steps_response.text, overreach_steps_response.text

        updated_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"steps": original_steps},
        )["item"]
        assert updated_version["steps"] == original_steps, updated_version

        drifted_steps = json.loads(json.dumps(original_steps, ensure_ascii=False))
        drifted_steps[0]["name"] = f"{drifted_steps[0].get('name', '')} {marker} 数据库绕过篡改"
        set_version_steps(first_version["id"], drifted_steps)
        drift_preflight = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/preflight", {})
        assert drift_preflight["ok"] is False, drift_preflight
        drift_hints = repair_hints_for(drift_preflight, "code_projection_regression")
        assert any(hint["code"] == "projection.step_object_mismatch" for hint in drift_hints), drift_preflight
        set_version_steps(first_version["id"], original_steps)

        original_tool_parameters = json.loads(
            json.dumps(updated_version["model_config"].get("tool_parameters") or {}, ensure_ascii=False)
        )
        assert original_tool_parameters.get("erp.provider.query"), updated_version
        edited_tool_parameters = json.loads(json.dumps(original_tool_parameters, ensure_ascii=False))
        edited_tool_parameters["erp.provider.query"]["limit"] = 30
        tool_parameters_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"tool_parameters": edited_tool_parameters},
        )["item"]
        assert tool_parameters_version["model_config"]["tool_parameters"] == edited_tool_parameters, tool_parameters_version

        overreach_tool_parameters_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"tool_parameters": {"unsafe.secret.tool": {"limit": 1}}},
        )
        assert overreach_tool_parameters_response.status_code == 400, overreach_tool_parameters_response.text
        assert "未允许的工具" in overreach_tool_parameters_response.text, overreach_tool_parameters_response.text

        bad_tool_parameters_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"tool_parameters": {"erp.provider.query": {"limit": 1000}}},
        )
        assert bad_tool_parameters_response.status_code == 400, bad_tool_parameters_response.text
        assert "不能大于" in bad_tool_parameters_response.text, bad_tool_parameters_response.text

        updated_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"tool_parameters": original_tool_parameters},
        )["item"]
        assert updated_version["model_config"]["tool_parameters"] == original_tool_parameters, updated_version

        secret_prompt_response = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {
                "change_summary": updated_version["change_summary"],
                "approval_policy": updated_version["approval_policy"],
                "failure_strategy": updated_version["failure_strategy"],
                "publish_notes": updated_version["publish_notes"],
                "prompt_summary": "Authorization: Bearer should_not_be_saved",
                "prompt_template_preview": updated_version["prompt_template_preview"],
            },
        )
        assert secret_prompt_response.status_code == 400, secret_prompt_response.text

        preflight = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/preflight", {})
        assert preflight["ok"] is True, preflight
        assert preflight["preflight_run_id"], preflight
        assert preflight["trigger_source"] == "manual", preflight
        assert_preflight_run(preflight["preflight_run_id"], version_id=first_version["id"], ok=True, trigger_source="manual")
        assert {item["key"] for item in preflight["checks"]} == {
            "schema_contract",
            "secret_scan",
            "prompt_contract",
            "execution_contract",
            "code_projection_regression",
            "business_regression_binding",
        }, preflight
        assert all(isinstance(item.get("repair_hints"), list) for item in preflight["checks"]), preflight
        regression_artifacts = artifacts_for(preflight, "business_regression_binding")
        assert any(item["script"] == "scripts/verify_finance_excel_transform.py" for item in regression_artifacts), preflight
        assert_preflight_run_contains_artifact(preflight["preflight_run_id"], "business_regression_binding", "scripts/verify_finance_excel_transform.py")

        set_version_publish_notes(first_version["id"], "callback_token=should_be_blocked_by_preflight")
        secret_preflight = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/preflight", {})
        assert secret_preflight["ok"] is False, secret_preflight
        assert secret_preflight["preflight_run_id"], secret_preflight
        assert_preflight_run(secret_preflight["preflight_run_id"], version_id=first_version["id"], ok=False, trigger_source="manual")
        assert "secret_scan" in failed_preflight_keys(secret_preflight), secret_preflight
        secret_hints = repair_hints_for(secret_preflight, "secret_scan")
        assert any(hint["field_path"] == "publish_notes" for hint in secret_hints), secret_preflight
        assert any("Token" in hint["suggestion"] or "密钥" in hint["suggestion"] for hint in secret_hints), secret_preflight
        set_version_publish_notes(first_version["id"], updated_version["publish_notes"])

        evidence_prompt_summary = f"{updated_version['prompt_summary']}。{marker} 发布证据快照。"
        evidence_prompt_template = f"{updated_version['prompt_template_preview']}\n\n# {marker} 发布证据快照"
        evidence_prompt_version = patch_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {
                "change_summary": updated_version["change_summary"],
                "approval_policy": updated_version["approval_policy"],
                "failure_strategy": updated_version["failure_strategy"],
                "publish_notes": updated_version["publish_notes"],
                "prompt_summary": evidence_prompt_summary,
                "prompt_template_preview": evidence_prompt_template,
            },
        )["item"]
        assert evidence_prompt_version["prompt_summary"] == evidence_prompt_summary, evidence_prompt_version

        reviewing = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/submit-review", {})["item"]
        assert reviewing["status"] == "reviewing", reviewing
        approved = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/approve", {})["item"]
        assert approved["status"] == "approved", approved
        missing_evidence_publish = post_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}/publish",
            {"environment": "production", "reason": f"{marker} 缺少发布证据必须阻断"},
        )
        assert missing_evidence_publish.status_code == 400, missing_evidence_publish.text
        missing_evidence_detail = missing_evidence_publish.json()["detail"]
        assert missing_evidence_detail["message"] == "发布前预检未通过", missing_evidence_detail
        assert missing_evidence_detail["preflight"]["trigger_source"] == "publish", missing_evidence_detail
        assert "business_regression_binding" in failed_preflight_keys(missing_evidence_detail["preflight"]), missing_evidence_detail
        evidence_hints = repair_hints_for(missing_evidence_detail["preflight"], "business_regression_binding")
        assert any(hint["code"] == "regression.evidence_missing" for hint in evidence_hints), missing_evidence_detail
        assert_preflight_run(
            missing_evidence_detail["preflight"]["preflight_run_id"],
            version_id=first_version["id"],
            ok=False,
            trigger_source="publish",
        )
        evidence_report_id = f"{marker}-finance-excel-transform"
        finance_regression_stdout = run_bound_regression_script("scripts/verify_finance_excel_transform.py")
        verification_evidence = post_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}/verification-evidence",
            {
                "script": "scripts/verify_finance_excel_transform.py",
                "command": ".venv/bin/python scripts/verify_finance_excel_transform.py",
                "profile": "api",
                "status": "passed",
                "report_id": evidence_report_id,
                "summary": "自动化流程版本治理回归已真实执行绑定脚本后写入发布证据。",
                "ttl_hours": 168,
                "metadata": {
                    "marker": marker,
                    "bound_regression_stdout_tail": finance_regression_stdout[-1000:],
                    "verification": "real API, real PostgreSQL, real auth; no mock/stub/fake/monkeypatch",
                },
            },
        )["item"]
        assert verification_evidence["status"] == "passed", verification_evidence
        assert verification_evidence["report_id"] == evidence_report_id, verification_evidence
        assert verification_evidence["script"] == "scripts/verify_finance_excel_transform.py", verification_evidence
        assert verification_evidence["snapshot_hash"] and len(verification_evidence["snapshot_hash"]) == 64, verification_evidence
        created_evidence_ids.append(verification_evidence["id"])
        direct_evidence_list = get_json(admin_token, f"/automation-flow-versions/{first_version['id']}/verification-evidence")
        assert direct_evidence_list["total"] >= 1, direct_evidence_list
        assert direct_evidence_list["snapshot_hash"] == verification_evidence["snapshot_hash"], direct_evidence_list
        assert any(
            item["report_id"] == evidence_report_id
            and item["is_current_version"] is True
            and item["matches_current_snapshot"] is True
            and item["is_publish_eligible"] is True
            for item in direct_evidence_list["items"]
        ), direct_evidence_list

        evidence_preflight = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/preflight", {})
        assert evidence_preflight["ok"] is True, evidence_preflight
        latest_evidence_artifacts = artifacts_for(evidence_preflight, "business_regression_binding")
        assert any(
            (item.get("latest_evidence") or {}).get("report_id") == evidence_report_id
            for item in latest_evidence_artifacts
        ), evidence_preflight
        assert_preflight_run_contains_evidence(
            evidence_preflight["preflight_run_id"],
            "business_regression_binding",
            evidence_report_id,
        )
        set_version_input_schema(
            first_version["id"],
            [
                {
                    "name": "",
                    "label": "坏字段",
                    "type": "api_key",
                }
            ],
        )
        invalid_preflight = post_json(admin_token, f"/automation-flow-versions/{first_version['id']}/preflight", {})
        assert invalid_preflight["ok"] is False, invalid_preflight
        assert invalid_preflight["preflight_run_id"], invalid_preflight
        assert_preflight_run(invalid_preflight["preflight_run_id"], version_id=first_version["id"], ok=False, trigger_source="manual")
        invalid_preflight_keys = failed_preflight_keys(invalid_preflight)
        assert "schema_contract" in invalid_preflight_keys, invalid_preflight
        assert "secret_scan" in invalid_preflight_keys, invalid_preflight
        schema_hints = repair_hints_for(invalid_preflight, "schema_contract")
        assert any(hint["code"] == "schema.name_required" and hint["field_path"] == "input_schema[1].name" for hint in schema_hints), invalid_preflight
        assert any(hint["code"] == "schema.type_unsupported" and hint["field_path"] == "input_schema[1].type" for hint in schema_hints), invalid_preflight
        invalid_secret_hints = repair_hints_for(invalid_preflight, "secret_scan")
        assert any(hint["field_path"] == "input_schema[1].type" for hint in invalid_secret_hints), invalid_preflight
        blocked_publish = post_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}/publish",
            {"environment": "production", "reason": f"{marker} 坏 Schema 发布必须阻断"},
        )
        assert blocked_publish.status_code == 400, blocked_publish.text
        blocked_detail = blocked_publish.json()["detail"]
        assert blocked_detail["message"] == "发布前预检未通过", blocked_detail
        assert blocked_detail["preflight"]["ok"] is False, blocked_detail
        assert blocked_detail["preflight"]["trigger_source"] == "publish", blocked_detail
        assert repair_hints_for(blocked_detail["preflight"], "schema_contract"), blocked_detail
        assert artifacts_for(blocked_detail["preflight"], "business_regression_binding"), blocked_detail
        assert_preflight_run(blocked_detail["preflight"]["preflight_run_id"], version_id=first_version["id"], ok=False, trigger_source="publish")
        set_version_input_schema(first_version["id"], first_version["input_schema"])
        first_publication = post_json(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}/publish",
            {"environment": "production", "reason": f"{marker} 发布第一版"},
        )["item"]
        created_publication_ids.append(first_publication["id"])
        assert first_publication["status"] == "active", first_publication
        assert first_publication["version_id"] == first_version["id"], first_publication
        assert count_preflight_runs(first_version["id"], "publish", True) >= 1

        published_patch = patch_raw(
            admin_token,
            f"/automation-flow-versions/{first_version['id']}",
            {"change_summary": f"{marker} 不允许修改已发布版本"},
        )
        assert published_patch.status_code == 400, published_patch.text

        second_version = post_json(
            admin_token,
            f"/automation-flows/{flow_path}/versions",
            {
                "change_summary": f"{marker} 第二版草稿",
                "publish_notes": f"{marker} 第二版发布说明",
            },
        )["item"]
        created_version_ids.append(second_version["id"])
        assert second_version["version_number"] > first_version["version_number"], second_version
        patch_json(
            admin_token,
            f"/automation-flow-versions/{second_version['id']}",
            {
                "change_summary": second_version["change_summary"],
                "approval_policy": second_version["approval_policy"],
                "failure_strategy": second_version["failure_strategy"],
                "publish_notes": second_version["publish_notes"],
                "prompt_summary": evidence_prompt_summary,
                "prompt_template_preview": evidence_prompt_template,
            },
        )
        reused_evidence_list = get_json(admin_token, f"/automation-flow-versions/{second_version['id']}/verification-evidence")
        assert any(
            item["report_id"] == evidence_report_id
            and item["is_current_version"] is False
            and item["matches_current_snapshot"] is True
            and item["is_publish_eligible"] is True
            and item["evidence_scope"] == "same_snapshot"
            for item in reused_evidence_list["items"]
        ), reused_evidence_list
        post_json(admin_token, f"/automation-flow-versions/{second_version['id']}/submit-review", {})
        post_json(admin_token, f"/automation-flow-versions/{second_version['id']}/approve", {})
        second_publication = post_json(
            admin_token,
            f"/automation-flow-versions/{second_version['id']}/publish",
            {"environment": "production", "reason": f"{marker} 发布第二版"},
        )["item"]
        created_publication_ids.append(second_publication["id"])
        assert second_publication["status"] == "active", second_publication
        assert second_publication["version_id"] == second_version["id"], second_publication
        assert count_preflight_runs(second_version["id"], "publish", True) >= 1

        active_count = count_active_publications(flow_db_id, "production")
        assert active_count == 1, active_count

        rollback_publication = post_json(
            admin_token,
            f"/automation-flow-publications/{second_publication['id']}/rollback",
            {"reason": f"{marker} 回滚到第一版"},
        )["item"]
        created_publication_ids.append(rollback_publication["id"])
        assert rollback_publication["status"] == "active", rollback_publication
        assert rollback_publication["version_id"] == first_version["id"], rollback_publication
        assert rollback_publication["rollback_from_version_id"] == second_version["id"], rollback_publication
        assert count_active_publications(flow_db_id, "production") == 1

        first_detail = get_json(admin_token, f"/automation-flow-versions/{first_version['id']}")["item"]
        second_detail = get_json(admin_token, f"/automation-flow-versions/{second_version['id']}")["item"]
        assert first_detail["status"] == "published", first_detail
        assert second_detail["status"] == "rolled_back", second_detail

        payload = json.dumps(
            {
                "first": first_detail,
                "second": second_detail,
                "rollback": rollback_publication,
            },
            ensure_ascii=False,
        )
        for secret_text in SECRET_MARKERS:
            assert secret_text not in payload, f"flow version response leaked {secret_text}"

        audit_actions = load_audit_actions(created_version_ids, created_publication_ids, created_evidence_ids)
        for action in {
            "admin.automation_flow_version.create",
            "admin.automation_flow_version.update",
            "admin.automation_flow_version.submit_review",
            "admin.automation_flow_version.approve",
            "admin.automation_flow_version.preflight",
            "admin.automation_flow_version.verification_evidence.record",
            "admin.automation_flow_version.publish_blocked",
            "admin.automation_flow_version.publish",
            "admin.automation_flow_publication.rollback",
        }:
            assert action in audit_actions, audit_actions

        critical_evidence_policy = verify_critical_evidence_policy(
            admin_token=admin_token,
            flow=salary_flow,
            marker=marker,
            label="财务工资导出",
            expected_critical_scripts=[
                "scripts/verify_finance_salary_export.py",
                "scripts/verify_chat_react_guardrails.py",
            ],
            evidence_summaries=[
                "高风险财务工资导出流程关键证据：ERP Salary Slip 和 Excel 检查回归已真实执行。",
                "高风险财务工资导出流程关键证据：聊天入口工资导出和岗位越权守卫回归已真实执行。",
            ],
            created_version_ids=created_version_ids,
            created_publication_ids=created_publication_ids,
            created_evidence_ids=created_evidence_ids,
        )
        customer_service_critical_evidence_policy = verify_critical_evidence_policy(
            admin_token=admin_token,
            flow=customer_service_flow,
            marker=marker,
            label="客服售后",
            expected_critical_scripts=[
                "scripts/verify_customer_service_automation.py",
                "scripts/verify_customer_service_refund_approvals.py",
            ],
            evidence_summaries=[
                "高风险客服售后流程关键证据：客服消息自动化闭环真实回归已执行。",
                "高风险客服售后流程关键证据：客服退款审批权限和真实退款流水回归已执行。",
            ],
            created_version_ids=created_version_ids,
            created_publication_ids=created_publication_ids,
            created_evidence_ids=created_evidence_ids,
        )

        print(json.dumps({
            "ok": True,
            "flow_id": flow["id"],
            "created_version_ids": created_version_ids,
            "created_publication_ids": created_publication_ids,
            "active_publication_count": count_active_publications(flow_db_id, "production"),
            "persisted_preflight_runs": count_preflight_runs(first_version["id"]) + count_preflight_runs(second_version["id"]),
            "verification_evidence_report_id": evidence_report_id,
            "evidence_list_total": direct_evidence_list["total"],
            "critical_evidence_policy": critical_evidence_policy,
            "customer_service_critical_evidence_policy": customer_service_critical_evidence_policy,
            "employee_forbidden": True,
            "note": "real API, real PostgreSQL, real auth; no mock/stub/fake/monkeypatch",
        }, ensure_ascii=False, indent=2))
    finally:
        cleanup(created_version_ids, created_publication_ids, preserved_publications, preserved_version_statuses)


def verify_critical_evidence_policy(
    *,
    admin_token: str,
    flow: dict[str, Any],
    marker: str,
    label: str,
    expected_critical_scripts: list[str],
    evidence_summaries: list[str],
    created_version_ids: list[str],
    created_publication_ids: list[str],
    created_evidence_ids: list[str],
) -> dict[str, Any]:
    assert len(expected_critical_scripts) >= 2, expected_critical_scripts
    assert len(evidence_summaries) == len(expected_critical_scripts), evidence_summaries
    flow_path = quote(flow["id"], safe="")
    version = post_json(
        admin_token,
        f"/automation-flows/{flow_path}/versions",
        {
            "change_summary": f"{marker} {label}高风险关键证据策略",
            "approval_policy": "高风险流程发布前必须补齐关键绑定脚本的真实通过证据。",
            "failure_strategy": "关键证据缺失时阻断发布，只保留预检记录和修复建议。",
            "publish_notes": f"{marker} {label}高风险证据策略 staging 发布",
        },
    )["item"]
    created_version_ids.append(version["id"])
    assert version["status"] == "draft", version

    manual_preflight = post_json(admin_token, f"/automation-flow-versions/{version['id']}/preflight", {})
    artifacts = artifacts_for(manual_preflight, "business_regression_binding")
    critical_artifacts = [item for item in artifacts if item.get("publish_evidence_required") is True]
    critical_scripts = sorted(item["script"] for item in critical_artifacts)
    assert critical_scripts == sorted(expected_critical_scripts), manual_preflight

    post_json(admin_token, f"/automation-flow-versions/{version['id']}/submit-review", {})
    post_json(admin_token, f"/automation-flow-versions/{version['id']}/approve", {})

    missing_all_publish = post_raw(
        admin_token,
        f"/automation-flow-versions/{version['id']}/publish",
        {"environment": "staging", "reason": f"{marker} {label}缺少全部关键证据必须阻断"},
    )
    assert missing_all_publish.status_code == 400, missing_all_publish.text
    missing_all_preflight = missing_all_publish.json()["detail"]["preflight"]
    assert "business_regression_binding" in failed_preflight_keys(missing_all_preflight), missing_all_preflight
    missing_all_hints = repair_hints_for(missing_all_preflight, "business_regression_binding")
    assert (
        sum(1 for hint in missing_all_hints if hint["code"] == "regression.critical_evidence_missing")
        == len(expected_critical_scripts)
    ), missing_all_preflight

    evidence_report_ids: list[str] = []
    first_report_id = record_critical_evidence(
        admin_token=admin_token,
        version_id=version["id"],
        script=expected_critical_scripts[0],
        report_id=f"{marker}-{critical_report_suffix(expected_critical_scripts[0])}",
        summary=evidence_summaries[0],
        marker=marker,
        created_evidence_ids=created_evidence_ids,
    )
    evidence_report_ids.append(first_report_id)

    missing_second_publish = post_raw(
        admin_token,
        f"/automation-flow-versions/{version['id']}/publish",
        {"environment": "staging", "reason": f"{marker} {label}缺少剩余关键证据必须阻断"},
    )
    assert missing_second_publish.status_code == 400, missing_second_publish.text
    missing_second_preflight = missing_second_publish.json()["detail"]["preflight"]
    missing_second_hints = repair_hints_for(missing_second_preflight, "business_regression_binding")
    assert (
        sum(1 for hint in missing_second_hints if hint["code"] == "regression.critical_evidence_missing")
        == len(expected_critical_scripts) - 1
    ), missing_second_preflight
    assert_preflight_run_contains_evidence(
        missing_second_preflight["preflight_run_id"],
        "business_regression_binding",
        first_report_id,
    )

    for script, summary in zip(expected_critical_scripts[1:], evidence_summaries[1:], strict=True):
        evidence_report_ids.append(
            record_critical_evidence(
                admin_token=admin_token,
                version_id=version["id"],
                script=script,
                report_id=f"{marker}-{critical_report_suffix(script)}",
                summary=summary,
                marker=marker,
                created_evidence_ids=created_evidence_ids,
            )
        )

    high_risk_publication = post_json(
        admin_token,
        f"/automation-flow-versions/{version['id']}/publish",
        {"environment": "staging", "reason": f"{marker} {label}高风险关键证据已补齐"},
    )["item"]
    created_publication_ids.append(high_risk_publication["id"])
    assert high_risk_publication["status"] == "active", high_risk_publication
    assert high_risk_publication["environment"] == "staging", high_risk_publication
    assert high_risk_publication["version_id"] == version["id"], high_risk_publication

    return {
        "flow_id": flow["id"],
        "version_id": version["id"],
        "critical_scripts": critical_scripts,
        "missing_all_blocking_failures": missing_all_preflight["blocking_failures"],
        "missing_second_blocking_failures": missing_second_preflight["blocking_failures"],
        "reports": evidence_report_ids,
        "publication_id": high_risk_publication["id"],
    }


def record_critical_evidence(
    *,
    admin_token: str,
    version_id: str,
    script: str,
    report_id: str,
    summary: str,
    marker: str,
    created_evidence_ids: list[str],
) -> str:
    stdout = run_bound_regression_script(script)
    evidence = post_json(
        admin_token,
        f"/automation-flow-versions/{version_id}/verification-evidence",
        {
            "script": script,
            "command": f".venv/bin/python {script}",
            "profile": "api",
            "status": "passed",
            "report_id": report_id,
            "summary": summary,
            "ttl_hours": 168,
            "metadata": {
                "marker": marker,
                "bound_regression_stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
                "verification": "real API, real PostgreSQL, real auth; no mock/stub/fake/monkeypatch",
            },
        },
    )["item"]
    created_evidence_ids.append(evidence["id"])
    return report_id


def critical_report_suffix(script: str) -> str:
    return Path(script).stem.removeprefix("verify_").replace("_", "-")


def ensure_schema() -> None:
    migration_sql = (ROOT / "sql" / "016_automation_flow_versions.sql").read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)
        conn.commit()


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def get_json(token: str, path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=60)
    assert response.status_code == 200, response.text
    return response.json()


def post_json(token: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = post_raw(token, path, payload)
    assert response.status_code == 200, response.text
    return response.json()


def post_raw(token: str, path: str, payload: dict[str, Any]) -> requests.Response:
    return requests.post(f"{API_BASE_URL}{path}", headers=json_headers(token), json=payload, timeout=60)


def patch_json(token: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = patch_raw(token, path, payload)
    assert response.status_code == 200, response.text
    return response.json()


def patch_raw(token: str, path: str, payload: dict[str, Any]) -> requests.Response:
    return requests.patch(f"{API_BASE_URL}{path}", headers=json_headers(token), json=payload, timeout=60)


def assert_forbidden(token: str, path: str) -> None:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=60)
    assert response.status_code == 403, response.text


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def json_headers(token: str) -> dict[str, str]:
    return {**auth_headers(token), "Content-Type": "application/json"}


def run_bound_regression_script(script: str) -> str:
    env = os.environ.copy()
    env["VERIFY_API_BASE_URL"] = API_BASE_URL
    env["VERIFY_DATABASE_URL"] = DATABASE_URL
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=BOUND_REGRESSION_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            f"{script} timed out after {BOUND_REGRESSION_TIMEOUT_SECONDS}s\n"
            f"stdout:\n{_subprocess_text(exc.stdout)}\n"
            f"stderr:\n{_subprocess_text(exc.stderr)}"
        ) from exc
    if result.returncode != 0:
        raise AssertionError(
            f"{script} exited with {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout


def _subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def pick_flow(items: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for item in items:
        if item["name"] == name:
            return item
    raise AssertionError(f"missing automation flow: {name}")


def failed_preflight_keys(preflight: dict[str, Any]) -> set[str]:
    return {
        item["key"]
        for item in preflight["checks"]
        if item["status"] == "failed"
    }


def repair_hints_for(preflight: dict[str, Any], check_key: str) -> list[dict[str, Any]]:
    for item in preflight["checks"]:
        if item["key"] == check_key:
            hints = item.get("repair_hints")
            assert isinstance(hints, list), item
            return hints
    raise AssertionError(f"missing preflight check: {check_key}")


def artifacts_for(preflight: dict[str, Any], check_key: str) -> list[dict[str, Any]]:
    for item in preflight["checks"]:
        if item["key"] == check_key:
            artifacts = item.get("artifacts")
            assert isinstance(artifacts, list), item
            return artifacts
    raise AssertionError(f"missing preflight check: {check_key}")


def assert_preflight_run(preflight_run_id: str, *, version_id: str, ok: bool, trigger_source: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT version_id, trigger_source, ok, blocking_failures, checks
                FROM automation_flow_version_preflight_runs
                WHERE id = %s;
                """,
                (preflight_run_id,),
            )
            row = cur.fetchone()
    assert row is not None, preflight_run_id
    assert str(row[0]) == version_id, row
    assert row[1] == trigger_source, row
    assert row[2] is ok, row
    assert int(row[3]) >= 0, row
    assert isinstance(row[4], list) and row[4], row
    failed_checks = [item for item in row[4] if item.get("status") == "failed"]
    if not ok:
        assert failed_checks, row
        assert all(isinstance(item.get("repair_hints"), list) and item["repair_hints"] for item in failed_checks), row


def assert_preflight_run_contains_artifact(preflight_run_id: str, check_key: str, script: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT checks
                FROM automation_flow_version_preflight_runs
                WHERE id = %s;
                """,
                (preflight_run_id,),
            )
            row = cur.fetchone()
    assert row is not None, preflight_run_id
    checks = row[0]
    assert isinstance(checks, list), row
    for item in checks:
        if item.get("key") != check_key:
            continue
        artifacts = item.get("artifacts")
        assert isinstance(artifacts, list), item
        assert any(artifact.get("script") == script for artifact in artifacts), item
        return
    raise AssertionError(f"missing persisted check {check_key} in {preflight_run_id}")


def assert_preflight_run_contains_evidence(preflight_run_id: str, check_key: str, report_id: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT checks
                FROM automation_flow_version_preflight_runs
                WHERE id = %s;
                """,
                (preflight_run_id,),
            )
            row = cur.fetchone()
    assert row is not None, preflight_run_id
    checks = row[0]
    assert isinstance(checks, list), row
    for item in checks:
        if item.get("key") != check_key:
            continue
        artifacts = item.get("artifacts")
        assert isinstance(artifacts, list), item
        assert any(
            (artifact.get("latest_evidence") or {}).get("report_id") == report_id
            for artifact in artifacts
        ), item
        return
    raise AssertionError(f"missing persisted evidence {report_id} in {preflight_run_id}")


def count_preflight_runs(version_id: str, trigger_source: str | None = None, ok: bool | None = None) -> int:
    conditions = ["version_id = %s"]
    params: list[Any] = [version_id]
    if trigger_source is not None:
        conditions.append("trigger_source = %s")
        params.append(trigger_source)
    if ok is not None:
        conditions.append("ok = %s")
        params.append(ok)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT count(*)
                FROM automation_flow_version_preflight_runs
                WHERE {' AND '.join(conditions)};
                """,
                params,
            )
            return int(cur.fetchone()[0])


def ensure_flow_projection_for_cleanup(token: str, flow_id: str) -> str:
    created = post_json(
        token,
        f"/automation-flows/{quote(flow_id, safe='')}/versions",
        {"change_summary": "verify-flow-version-bootstrap"},
    )["item"]
    version_id = created["id"]
    flow_db_id = created["flow_id"]
    cleanup([version_id], [], [], [])
    return flow_db_id


def set_version_publish_notes(version_id: str, publish_notes: str | None) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET publish_notes = %s, updated_at = now()
                WHERE id = %s;
                """,
                (publish_notes, version_id),
            )
        conn.commit()


def set_version_input_schema(version_id: str, input_schema: list[dict[str, Any]]) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET input_schema = %s::jsonb, updated_at = now()
                WHERE id = %s;
                """,
                (json.dumps(input_schema, ensure_ascii=False), version_id),
            )
        conn.commit()


def set_version_steps(version_id: str, steps: list[dict[str, Any]]) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET steps = %s::jsonb, updated_at = now()
                WHERE id = %s;
                """,
                (json.dumps(steps, ensure_ascii=False), version_id),
            )
        conn.commit()


def set_version_prompt_summary(version_id: str, prompt_summary: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE automation_flow_versions
                SET prompt_summary = %s, updated_at = now()
                WHERE id = %s;
                """,
                (prompt_summary, version_id),
            )
        conn.commit()


def load_active_publications(flow_id: str, environment: str = "production") -> list[dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, version_id, status
                FROM automation_flow_publications
                WHERE flow_id = %s
                  AND environment = %s
                  AND status = 'active';
                """,
                (flow_id, environment),
            )
            return [
                {"id": str(row[0]), "version_id": str(row[1]), "status": row[2]}
                for row in cur.fetchall()
            ]


def load_version_statuses(flow_id: str) -> list[dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status FROM automation_flow_versions WHERE flow_id = %s;",
                (flow_id,),
            )
            return [{"id": str(row[0]), "status": row[1]} for row in cur.fetchall()]


def count_active_publications(flow_id: str, environment: str) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM automation_flow_publications
                WHERE flow_id = %s
                  AND environment = %s
                  AND status = 'active';
                """,
                (flow_id, environment),
            )
            return int(cur.fetchone()[0])


def load_audit_actions(
    version_ids: list[str],
    publication_ids: list[str],
    evidence_ids: list[str],
) -> set[str]:
    resource_ids = [*version_ids, *publication_ids, *evidence_ids]
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT action
                FROM audit_logs
                WHERE resource_id = ANY(%s);
                """,
                (resource_ids,),
            )
            return {str(row[0]) for row in cur.fetchall()}


def cleanup(
    version_ids: list[str],
    publication_ids: list[str],
    preserved_publications: list[dict[str, Any]],
    preserved_version_statuses: list[dict[str, Any]],
) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            if publication_ids:
                cur.execute(
                    "DELETE FROM automation_flow_publications WHERE id = ANY(%s);",
                    (publication_ids,),
                )
            if version_ids:
                cur.execute(
                    "DELETE FROM automation_flow_versions WHERE id = ANY(%s);",
                    (version_ids,),
                )
            for item in preserved_version_statuses:
                cur.execute(
                    "UPDATE automation_flow_versions SET status = %s WHERE id = %s;",
                    (item["status"], item["id"]),
                )
            for item in preserved_publications:
                cur.execute(
                    "UPDATE automation_flow_publications SET status = %s WHERE id = %s;",
                    (item["status"], item["id"]),
                )
        conn.commit()


if __name__ == "__main__":
    main()
