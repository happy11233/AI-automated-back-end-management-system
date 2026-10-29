"""Check that slow synchronous automation work does not block the API event loop."""
from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from starlette.datastructures import UploadFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.api import automation, operations_images
from app.skills.executor import SkillExecutionResult


USER = {"id": "fixture", "username": "fixture", "role": "admin", "position": "finance"}


async def assert_responsive(call, worker):
    loop_thread = threading.get_ident()
    worker_threads = []

    def slow_worker(*args, **kwargs):
        worker_threads.append(threading.get_ident())
        time.sleep(0.18)
        return worker(*args, **kwargs)

    ticks = 0
    with patch.object(automation, "start_run", return_value="fixture-run"), \
         patch.object(automation, "record_step"), \
         patch.object(automation, "finish_run"), \
         patch.object(automation, "save_generated_file"), \
         patch.object(automation, "write_audit_log"), \
         patch.object(automation, "resolve_flow_execution_reference", return_value={}), \
         patch.object(automation, "_infer_finance_excel_erp_resources_from_instruction", return_value=[]), \
         patch.object(automation, "_query_finance_excel_erp_context", return_value=[]), \
         patch.object(automation, "analyze_finance_report_files", side_effect=slow_worker), \
         patch.object(automation, "execute_skill", side_effect=slow_worker), \
         patch.object(operations_images, "ensure_operations_image_access"), \
         patch.object(operations_images, "generate_product_scene", side_effect=slow_worker):
        task = asyncio.create_task(call())
        while not task.done():
            await asyncio.sleep(0.01)
            ticks += 1
        await task
    assert worker_threads and all(ident != loop_thread for ident in worker_threads), worker_threads
    assert ticks >= 5, f"event loop stopped while worker ran: {ticks} ticks"


async def main():
    report = SimpleNamespace(content=b"report", filename="report.docx", mime_type="application/docx",
                             output_format="word", answer="done", metadata={})
    skill = SkillExecutionResult(skill_id="fixture", status="succeeded", answer="done",
                                attachments=[{"content": b"excel", "filename": "result.xlsx"}])

    await assert_responsive(
        lambda: automation.analyze_finance_report(files=None, instruction="sample figures",
                                                output_format="word", current_user=USER),
        lambda *args, **kwargs: report,
    )
    await assert_responsive(
        lambda: automation.transform_finance_excel_file(
            file=UploadFile(file=BytesIO(b"source"), filename="source.xlsx"),
            instruction="format worksheet", erp_resources="[]", current_user=USER),
        lambda *args, **kwargs: skill,
    )
    await assert_responsive(
        lambda: automation.reconcile_finance_files(
            files=[UploadFile(file=BytesIO(b"source"), filename="source.xlsx")],
            instruction="compare", base_currency="CNY", current_user=USER),
        lambda *args, **kwargs: skill,
    )
    await assert_responsive(
        lambda: operations_images.generate_image(
            file=UploadFile(file=BytesIO(b"image"), filename="image.png",
                            headers={"content-type": "image/png"}),
            prompt="scene", current_user=USER),
        lambda *args, **kwargs: {"artifact_id": "fixture"},
    )
    print("nonblocking automation checks passed: report, Excel, reconciliation, image")


if __name__ == "__main__":
    asyncio.run(main())
