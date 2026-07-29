from __future__ import annotations

import base64
import re
from io import BytesIO
from typing import Any

from fastapi import HTTPException, status
from langchain_core.messages import HumanMessage
from openpyxl import Workbook

from app.erp.base import ERPProviderError
from app.erp.providers import get_active_provider
from app.erp.resources import provider_fields_for, provider_resource_for
from app.json_utils import dumps_json
from app.llm import chat, chat_model
from app.permissions import ensure_erp_resource_allowed
from app.services.generated_file_service import get_generated_file_storage_reference, save_generated_file
from app.services.logging_service import write_audit_log
from app.services.mcp_tool_registry_service import execute_managed_mcp_tool
from app.services.platform_draft_service import (
    create_platform_action_execution,
    create_platform_draft,
    finish_platform_action_execution,
    get_platform_draft,
    listing_content_from_answer,
    update_platform_draft_status,
    update_platform_draft_writeback,
)
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    now_ms,
    record_step,
    sanitize_metadata,
    start_run,
)
from app.services.user_ai_app_permission_service import is_ai_app_allowed
from app.skills.executor import SkillExecutionResult
from app.skills.registry import SkillDefinition


AMAZON_UPLOAD_MODES = {"auto", "web_form", "batch_excel"}
AMAZON_LISTING_FINAL_MESSAGE = "已填写完成，请你检查 Amazon 页面后手动发布"


def generate_operations_listing_draft(
    *,
    payload: dict[str, Any],
    current_user: dict,
    source: str,
    skill: SkillDefinition,
    execution_context: dict[str, Any],
) -> SkillExecutionResult:
    message = str(payload.get("message") or payload.get("input_text") or "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请说明要生成哪个商品的 Listing。")

    attachments = _normalize_attachments(payload.get("attachments") or payload.get("files") or [])
    sku = extract_listing_sku(message)
    marketplace = extract_listing_marketplace(message)
    user_price = extract_listing_price(message)
    user_inventory = extract_listing_inventory(message)
    upload_mode = normalize_upload_mode(payload.get("upload_mode") or extract_upload_mode(message))

    started_ms = now_ms()
    run_id = start_run(
        run_type="operations_listing_amazon_draft",
        app_id=skill.app_id,
        app_name=skill.name,
        entrypoint="/chat" if source.startswith("chat") else "/ai-workflows/operations_listing_launch/run",
        current_user=current_user,
        resource_type="skill",
        resource_id=skill.skill_id,
        input_text=message,
        metadata={
            "skill_id": skill.skill_id,
            "flow_key": execution_context["flow_key"],
            "source": source,
            "sku": sku,
            "marketplace": marketplace,
            "upload_mode": upload_mode,
            "attachment_count": len(attachments),
        },
    )
    erp_context = query_listing_erp_context(
        sku=sku,
        current_user=current_user,
        message=message,
    )
    record_step(
        run_id=run_id,
        step_name="erpnext_listing_context",
        step_order=1,
        status_value="succeeded" if erp_context["ok"] else "blocked",
        provider="erpnext",
        resource_type="erp",
        resource_id=sku,
        input_text={"sku": sku, "message": message},
        output_text=erp_context,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "sku": sku,
            "item_found": bool(erp_context.get("item")),
            "price_source": "user" if user_price is not None else erp_context.get("price_source"),
            "inventory_source": "user" if user_inventory is not None else erp_context.get("inventory_source"),
        },
    )

    image_started_ms = now_ms()
    image_analysis = analyze_listing_images(attachments)
    image_artifact_ids, image_assets = save_listing_image_assets(
        run_id=run_id,
        attachments=attachments,
        current_user=current_user,
        sku=sku,
    )
    record_step(
        run_id=run_id,
        step_name="product_image_analysis",
        step_order=2,
        status_value="succeeded" if image_analysis["image_count"] else "blocked",
        provider="llm_vision",
        resource_type="listing_assets",
        resource_id=sku,
        input_text={"attachment_count": len(attachments)},
        output_text=image_analysis,
        duration_ms=elapsed_ms(image_started_ms),
        metadata={
            "image_count": image_analysis["image_count"],
            "used_multimodal_model": image_analysis.get("used_multimodal_model"),
        },
    )

    listing_started_ms = now_ms()
    resolved_price = user_price if user_price is not None else erp_context.get("price")
    resolved_inventory = user_inventory if user_inventory is not None else erp_context.get("inventory")
    prompt = _build_listing_generation_prompt(
        message=message,
        sku=sku,
        marketplace=marketplace,
        erp_context=erp_context,
        image_analysis=image_analysis,
        price=resolved_price,
        inventory=resolved_inventory,
        upload_mode=upload_mode,
    )
    answer = chat(prompt)
    draft_content = listing_content_from_answer(answer=answer, input_text=message)
    draft_content.update({
        "sku": sku or draft_content.get("sku"),
        "marketplace": marketplace or draft_content.get("marketplace"),
        "price": resolved_price,
        "inventory": resolved_inventory,
        "price_source": "user" if user_price is not None else erp_context.get("price_source"),
        "inventory_source": "user" if user_inventory is not None else erp_context.get("inventory_source"),
        "upload_mode": upload_mode,
        "image_artifact_ids": image_artifact_ids,
        "image_assets": image_assets,
        "erp_context": _public_erp_context(erp_context),
        "image_analysis": image_analysis,
        "amazon_upload_status": "waiting_confirmation",
        "amazon_upload_required": True,
        "review_required": True,
        "publish_policy": "运营确认后只自动填写 Amazon 后台，最终发布必须人工点击。",
    })
    record_step(
        run_id=run_id,
        step_name="generate_listing_draft",
        step_order=3,
        status_value="succeeded",
        provider="dashscope",
        resource_type="listing",
        resource_id=sku,
        input_text=prompt,
        output_text=answer,
        duration_ms=elapsed_ms(listing_started_ms),
        metadata={
            "sku": sku,
            "marketplace": marketplace,
            "price_source": draft_content.get("price_source"),
            "inventory_source": draft_content.get("inventory_source"),
            "upload_mode": upload_mode,
        },
    )

    save_started_ms = now_ms()
    platform_draft = create_platform_draft(
        draft_type="listing",
        platform="amazon",
        external_target="amazon_seller_central",
        title=str(draft_content.get("listing_title") or "Amazon Listing 草稿"),
        position="operations",
        owner_user_id=current_user.get("id"),
        source_run_id=run_id,
        source_resource_type="skill",
        source_resource_id=skill.skill_id,
        content=draft_content,
        writeback_status="draft_saved",
        writeback_message="Listing 草稿已生成，等待运营确认后再打开 Amazon Seller Central 填表。",
        metadata={
            "automation": "operations_listing_amazon",
            "source": source,
            "saved_by_ai": True,
            "sku": sku,
            "marketplace": marketplace,
            "upload_mode": upload_mode,
            "amazon_upload_status": "waiting_confirmation",
        },
    )
    record_step(
        run_id=run_id,
        step_name="save_listing_platform_draft",
        step_order=4,
        status_value="succeeded",
        provider="platform_drafts",
        resource_type="platform_draft",
        resource_id=platform_draft["id"],
        input_text=draft_content,
        output_text=platform_draft,
        duration_ms=elapsed_ms(save_started_ms),
        metadata={
            "draft_id": platform_draft["id"],
            "amazon_upload_status": "waiting_confirmation",
        },
    )

    final_answer = (
        "已生成 Amazon Listing 草稿，并保存到平台草稿区。\n"
        f"SKU：{sku or '未识别，请运营确认'}\n"
        f"目标站点：{marketplace or 'US'}\n"
        f"上传方式：{upload_mode_label(upload_mode)}\n"
        f"草稿 ID：{platform_draft['id']}\n"
        "下一步：运营确认标题、五点、描述、关键词、价格、库存和图片后，再点击确认上传 Amazon。"
        "\n\n"
        f"{answer}"
    )
    finish_run(
        run_id,
        status_value="succeeded",
        output_text=final_answer,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "platform_draft_id": platform_draft["id"],
            "amazon_upload_status": "waiting_confirmation",
            "sku": sku,
            "marketplace": marketplace,
            "upload_mode": upload_mode,
        },
    )
    write_audit_log(
        user_id=current_user.get("id"),
        action="operations_listing.amazon_draft_created",
        resource_type="platform_draft",
        resource_id=platform_draft["id"],
        metadata={
            "username": current_user.get("username"),
            "position": current_user.get("position"),
            "sku": sku,
            "marketplace": marketplace,
            "upload_mode": upload_mode,
        },
    )
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status="waiting_amazon_upload_confirmation",
        run_id=run_id,
        answer=final_answer,
        platform_draft=platform_draft,
        erp_references=erp_context.get("references") or [],
        metadata={
            "source": source,
            "skill_id": skill.skill_id,
            "skill_name": skill.name,
            "flow_key": execution_context["flow_key"],
            "risk_level": skill.risk_level,
            "step_count": 4,
            "sku": sku,
            "marketplace": marketplace,
            "upload_mode": upload_mode,
            "amazon_upload_status": "waiting_confirmation",
        },
    )


def confirm_and_prepare_amazon_listing_upload(
    *,
    draft_id: str,
    current_user: dict,
    confirmed: bool,
    upload_mode: str = "auto",
    target_marketplace: str | None = None,
    price: float | None = None,
    inventory: int | None = None,
) -> dict[str, Any]:
    draft = get_platform_draft(draft_id=draft_id, current_user=current_user)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing 草稿不存在或无权操作")
    if draft["draft_type"] != "listing":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有 Listing 草稿可以上传 Amazon")
    if draft["position"] != "operations":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有运营草稿可以上传 Amazon")
    if current_user.get("role") != "admin" and current_user.get("position") != "operations":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前岗位无权上传 Amazon Listing")
    if current_user.get("role") != "admin" and not is_ai_app_allowed(current_user, "automation-listing"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="运营 Listing 应用已被管理员禁用")
    if not confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先确认 Listing 内容、价格、库存、图片和目标站点")

    content = dict(draft.get("content") or {})
    upload_mode = normalize_upload_mode(upload_mode or content.get("upload_mode"))
    marketplace = target_marketplace or content.get("marketplace") or "US"
    if price is not None:
        content["price"] = price
        content["price_source"] = "user_confirmation"
    if inventory is not None:
        content["inventory"] = inventory
        content["inventory_source"] = "user_confirmation"

    listing_payload = listing_payload_from_draft_content(content)
    missing = missing_required_listing_fields(listing_payload)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Listing 草稿还缺少字段：{'、'.join(missing)}。请先补全后再上传 Amazon。",
        )

    started_ms = now_ms()
    run_id = start_run(
        run_type="operations_listing_amazon_upload",
        app_id="automation-listing",
        app_name="运营 Listing Amazon 上传准备",
        entrypoint="/platform-drafts/{draft_id}/amazon-upload",
        current_user=current_user,
        resource_type="platform_draft",
        resource_id=draft_id,
        input_text={
            "draft_id": draft_id,
            "upload_mode": upload_mode,
            "marketplace": marketplace,
        },
        metadata={
            "draft_id": draft_id,
            "sku": content.get("sku"),
            "marketplace": marketplace,
            "upload_mode": upload_mode,
            "manual_final_publish_required": True,
        },
    )
    if draft["status"] != "approved":
        draft = update_platform_draft_status(
            draft_id=draft_id,
            status_value="approved",
            metadata={
                "review_decision": "approved",
                "review_comment": "运营确认上传 Amazon Seller Central",
                "reviewed_by": current_user.get("id"),
                "reviewed_by_username": current_user.get("username"),
                "reviewed_at": _now_iso(),
                "amazon_upload_confirmed": True,
            },
        )

    assets = _assets_from_content(content, current_user=current_user)
    batch_artifact_id = None
    if upload_mode == "batch_excel":
        batch_file = build_amazon_batch_template_bytes(content=content, listing=listing_payload)
        batch_artifact_id = save_generated_file(
            run_id=run_id,
            content=batch_file,
            filename=f"amazon_listing_template_{content.get('sku') or 'sku'}.xlsx",
            artifact_type="excel_file",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            current_user=current_user,
            metadata={
                "draft_id": draft_id,
                "sku": content.get("sku"),
                "marketplace": marketplace,
                "business": "amazon_listing_batch_template",
            },
        )
        if batch_artifact_id:
            storage = get_generated_file_storage_reference(batch_artifact_id, current_user=current_user)
            assets.append({
                "type": "amazon_batch_template",
                "artifact_id": batch_artifact_id,
                "filename": storage["filename"],
                "local_file_path": storage["storage_path"],
            })

    execution = create_platform_action_execution(
        draft_id=draft_id,
        action_type="write_listing_draft",
        executor_type="playwright_mcp",
        target="amazon_seller_central",
        status_value="running",
        request_payload={
            "listing": listing_payload,
            "target_marketplace": marketplace,
            "sku": content.get("sku"),
            "upload_mode": upload_mode,
            "asset_count": len(assets),
            "stop_before_publish": True,
        },
        response_payload={},
        run_id=run_id,
        triggered_by=current_user.get("id"),
    )

    mcp_tool_calls: list[dict[str, Any]] = []
    try:
        mcp_result = execute_managed_mcp_tool(
            tool_id="playwright_amazon.prepare_seller_central_listing",
            arguments={
                "listing": listing_payload,
                "target_marketplace": marketplace,
                "sku": content.get("sku"),
                "assets": assets,
                "stop_before_publish": True,
                "upload_mode": upload_mode,
                "selector_profile": active_amazon_field_mapping_profile(),
            },
            current_user=current_user,
            source="operations_listing_amazon_upload",
            trace_collector=mcp_tool_calls,
        )
    except Exception as error:
        message = f"Amazon Playwright MCP 调用失败：{error}"
        execution = finish_platform_action_execution(
            execution_id=execution["id"],
            status_value="failed",
            response_payload={},
            error_message=message,
        )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft_id,
            writeback_status="failed",
            writeback_message=message,
            metadata={
                "amazon_upload_status": "failed",
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": "write_listing_draft",
                "mcp_tool_calls": mcp_tool_calls,
            },
        )
        record_step(
            run_id=run_id,
            step_name="playwright_amazon_prepare",
            step_order=1,
            status_value="failed",
            provider="mcp.playwright_amazon",
            resource_type="platform_draft",
            resource_id=draft_id,
            input_text={"draft_id": draft_id, "upload_mode": upload_mode},
            error_message=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "mcp_tool_calls": mcp_tool_calls},
        )
        finish_run(run_id, status_value="failed", error_message=message, duration_ms=elapsed_ms(started_ms))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)

    normalized_result = mcp_result if isinstance(mcp_result, dict) else {"ok": True, "status": "ready", "result": mcp_result}
    business_status, writeback_status, run_status = _status_from_mcp_result(normalized_result)
    execution = finish_platform_action_execution(
        execution_id=execution["id"],
        status_value="succeeded" if run_status == "succeeded" else "waiting_executor" if run_status == "blocked" else "failed",
        response_payload=normalized_result,
        error_message=None if run_status != "failed" else str(normalized_result.get("message") or "Amazon 上传准备失败"),
    )
    message = _amazon_upload_message(normalized_result, business_status)
    updated_draft = update_platform_draft_writeback(
        draft_id=draft_id,
        writeback_status=writeback_status,
        writeback_message=message,
        metadata={
            "amazon_upload_status": business_status,
            "amazon_upload_confirmed": True,
            "amazon_upload_confirmed_by": current_user.get("id"),
            "amazon_upload_confirmed_by_username": current_user.get("username"),
            "amazon_upload_confirmed_at": _now_iso(),
            "amazon_upload_mode": upload_mode,
            "amazon_upload_marketplace": marketplace,
            "amazon_batch_template_artifact_id": batch_artifact_id,
            "latest_execution_id": execution["id"],
            "latest_execution_status": execution["status"],
            "latest_action_type": "write_listing_draft",
            "manual_final_publish_required": True,
            "mcp_tool_calls": mcp_tool_calls,
        },
    )
    record_step(
        run_id=run_id,
        step_name="playwright_amazon_prepare",
        step_order=1,
        status_value=run_status,
        provider="mcp.playwright_amazon",
        resource_type="platform_draft",
        resource_id=draft_id,
        input_text={"draft_id": draft_id, "upload_mode": upload_mode, "marketplace": marketplace},
        output_text=normalized_result,
        duration_ms=elapsed_ms(started_ms),
        metadata={"execution_id": execution["id"], "mcp_tool_calls": mcp_tool_calls},
    )
    finish_run(
        run_id,
        status_value=run_status,
        output_text=message,
        error_message=None if run_status != "failed" else message,
        duration_ms=elapsed_ms(started_ms),
        metadata={
            "draft_id": draft_id,
            "amazon_upload_status": business_status,
            "writeback_status": writeback_status,
            "execution_id": execution["id"],
            "batch_artifact_id": batch_artifact_id,
        },
    )
    write_audit_log(
        user_id=current_user.get("id"),
        action="operations_listing.amazon_upload_prepare",
        resource_type="platform_draft",
        resource_id=draft_id,
        metadata={
            "username": current_user.get("username"),
            "position": current_user.get("position"),
            "draft_id": draft_id,
            "sku": content.get("sku"),
            "marketplace": marketplace,
            "upload_mode": upload_mode,
            "status": business_status,
            "manual_final_publish_required": True,
        },
    )
    return {
        "draft": updated_draft,
        "execution": _public_execution(execution, current_user=current_user),
        "task": None,
        "run_id": run_id,
        "message": message,
        "amazon_upload": {
            "status": business_status,
            "status_label": _amazon_status_label(business_status),
            "upload_mode": upload_mode,
            "target_marketplace": marketplace,
            "manual_final_publish_required": True,
            "auto_publish_allowed": False,
            "batch_template_artifact_id": batch_artifact_id,
            "mcp_result": sanitize_metadata(normalized_result),
        },
    }


def query_listing_erp_context(*, sku: str | None, current_user: dict, message: str) -> dict[str, Any]:
    if not sku:
        return {
            "ok": False,
            "status": "missing_sku",
            "message": "未识别到 SKU，Listing 草稿会基于用户描述生成。",
            "item": None,
            "price": None,
            "inventory": None,
            "references": [],
        }
    for resource in ["Item", "Item Price", "Bin"]:
        ensure_erp_resource_allowed(current_user, resource)
    provider = get_active_provider()
    item = _query_first_erp_item(provider=provider, resource="Item", sku=sku, fields=provider_fields_for("Item", provider.provider_id))
    price_item = _query_first_erp_item(
        provider=provider,
        resource="Item Price",
        sku=sku,
        fields=provider_fields_for("Item Price", provider.provider_id),
    )
    inventory_item = _query_first_erp_item(
        provider=provider,
        resource="Bin",
        sku=sku,
        fields=provider_fields_for("Bin", provider.provider_id),
    )
    references = []
    for resource, item_value in [("Item", item), ("Item Price", price_item), ("Bin", inventory_item)]:
        if item_value:
            references.append({
                "resource": resource,
                "resource_label": _resource_label(resource),
                "record_id": str(item_value.get("name") or item_value.get("item_code") or sku),
                "title": str(item_value.get("item_name") or item_value.get("price_list") or item_value.get("warehouse") or sku),
                "provider": provider.provider_id,
                "provider_resource": provider_resource_for(resource, provider.provider_id),
            })
    return {
        "ok": bool(item or price_item or inventory_item),
        "status": "ok" if item or price_item or inventory_item else "not_found",
        "message": f"已按 SKU {sku} 查询 ERPNext 商品资料。" if item or price_item or inventory_item else f"ERPNext 未查到 SKU {sku} 的商品资料。",
        "item": item,
        "price_item": price_item,
        "inventory_item": inventory_item,
        "price": _first_number(price_item, ["price_list_rate", "rate", "price"]) if price_item else None,
        "price_source": "erpnext_item_price" if price_item else None,
        "inventory": _first_int(inventory_item, ["actual_qty", "projected_qty", "quantity", "stock"]) if inventory_item else None,
        "inventory_source": "erpnext_bin" if inventory_item else None,
        "references": references,
    }


def _query_first_erp_item(*, provider: Any, resource: str, sku: str, fields: list[str]) -> dict[str, Any] | None:
    provider_resource = provider_resource_for(resource, provider.provider_id)
    if provider_resource is None:
        return None
    filters: list[Any] | None = [["item_code", "=", sku]]
    if resource == "Item":
        filters = None
    try:
        result = provider.query_resource(
            resource=resource,
            provider_resource=provider_resource,
            query=sku,
            filters=filters,
            fields=fields,
            limit=5,
        )
    except ERPProviderError:
        return None
    items = result.get("items") if isinstance(result.get("items"), list) else []
    return items[0] if items and isinstance(items[0], dict) else None


def analyze_listing_images(attachments: list[dict[str, Any]]) -> dict[str, Any]:
    image_items = [
        item
        for item in attachments
        if str(item.get("mime_type") or item.get("content_type") or "").lower().startswith("image/")
    ]
    if not image_items:
        return {
            "image_count": 0,
            "summary": "本次没有上传产品图片。可以先生成文字草稿，上传 Amazon 前需要运营确认图片。",
            "used_multimodal_model": False,
            "items": [],
        }

    analyzed_items: list[dict[str, Any]] = []
    used_model = False
    for item in image_items[:6]:
        filename = str(item.get("filename") or item.get("name") or "product_image")
        mime_type = str(item.get("mime_type") or item.get("content_type") or "image/png")
        content_base64 = item.get("content_base64")
        summary = "已记录用户上传的产品图片，生成 Listing 时只使用图片中能确定的信息。"
        if isinstance(content_base64, str) and content_base64.strip():
            model_summary = _try_multimodal_image_summary(content_base64=content_base64, mime_type=mime_type)
            if model_summary:
                summary = model_summary
                used_model = True
        analyzed_items.append({
            "filename": filename,
            "mime_type": mime_type,
            "summary": summary,
        })
    return {
        "image_count": len(image_items),
        "summary": "\n".join(f"{index}. {item['filename']}：{item['summary']}" for index, item in enumerate(analyzed_items, start=1)),
        "used_multimodal_model": used_model,
        "items": analyzed_items,
    }


def save_listing_image_assets(
    *,
    run_id: str,
    attachments: list[dict[str, Any]],
    current_user: dict,
    sku: str | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    artifact_ids: list[str] = []
    assets: list[dict[str, Any]] = []
    for index, item in enumerate(attachments[:8], start=1):
        mime_type = str(item.get("mime_type") or item.get("content_type") or "").strip()
        if not mime_type.lower().startswith("image/"):
            continue
        filename = str(item.get("filename") or item.get("name") or f"product_image_{index}.png").strip()[:180]
        content_base64 = item.get("content_base64")
        asset = {
            "type": "product_image",
            "filename": filename,
            "mime_type": mime_type,
            "source": "chat_upload",
        }
        if isinstance(content_base64, str) and content_base64.strip():
            try:
                content = base64.b64decode(content_base64, validate=True)
            except Exception:
                content = b""
            if content:
                artifact_id = save_generated_file(
                    run_id=run_id,
                    content=content,
                    filename=filename,
                    artifact_type="image_file",
                    mime_type=mime_type,
                    current_user=current_user,
                    metadata={
                        "business": "amazon_listing_product_image",
                        "sku": sku,
                    },
                )
                if artifact_id:
                    artifact_ids.append(artifact_id)
                    asset["artifact_id"] = artifact_id
        assets.append(asset)
    return artifact_ids, assets


def listing_payload_from_draft_content(content: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": content.get("listing_title") or content.get("title"),
        "bullet_points": content.get("five_bullets") or content.get("bullet_points") or [],
        "description": content.get("product_description") or content.get("description") or content.get("full_listing_package"),
        "keywords": content.get("backend_search_terms") or content.get("keywords"),
        "price": content.get("price"),
        "inventory": content.get("inventory"),
        "brand": content.get("brand"),
        "product_type": content.get("product_type"),
    }


def missing_required_listing_fields(listing: dict[str, Any]) -> list[str]:
    mapping = {
        "title": "标题",
        "bullet_points": "五点描述",
        "description": "产品描述",
        "keywords": "关键词",
        "price": "价格",
        "inventory": "库存",
    }
    return [label for key, label in mapping.items() if not listing.get(key)]


def build_amazon_batch_template_bytes(*, content: dict[str, Any], listing: dict[str, Any]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Amazon Listing"
    headers = [
        "sku",
        "marketplace",
        "title",
        "bullet_point_1",
        "bullet_point_2",
        "bullet_point_3",
        "bullet_point_4",
        "bullet_point_5",
        "description",
        "generic_keywords",
        "price",
        "quantity",
        "image_paths",
        "final_publish_policy",
    ]
    sheet.append(headers)
    bullets = listing.get("bullet_points") if isinstance(listing.get("bullet_points"), list) else []
    sheet.append([
        content.get("sku"),
        content.get("marketplace") or "US",
        listing.get("title"),
        *[(bullets[index] if index < len(bullets) else "") for index in range(5)],
        listing.get("description"),
        listing.get("keywords"),
        listing.get("price"),
        listing.get("inventory"),
        ", ".join(_asset_names(content)),
        "系统只上传草稿，最终发布必须运营人工点击。",
    ])
    for column in sheet.columns:
        letter = column[0].column_letter
        sheet.column_dimensions[letter].width = min(max(len(str(column[0].value or "")) + 4, 14), 42)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def active_amazon_field_mapping_profile() -> dict[str, Any] | None:
    # 第一版字段映射可先从环境变量进入 MCP；后续管理员页面可把可视化表单保存为同样的结构。
    return None


def normalize_upload_mode(value: Any) -> str:
    mode = str(value or "auto").strip().lower()
    if mode in AMAZON_UPLOAD_MODES:
        return mode
    if mode in {"网页", "表单", "web"}:
        return "web_form"
    if mode in {"excel", "批量", "模板", "batch"}:
        return "batch_excel"
    return "auto"


def upload_mode_label(value: str) -> str:
    return {
        "auto": "系统自动选择",
        "web_form": "网页逐字段填写",
        "batch_excel": "批量 Excel 模板上传",
    }.get(value, value)


def extract_listing_sku(text: str) -> str | None:
    patterns = [
        r"\bSKU\s*[:：#]?\s*([A-Za-z0-9][A-Za-z0-9_.-]{2,80})",
        r"\b([A-Z0-9]{2,}[A-Z0-9_.-]*-[A-Z0-9_.-]{2,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip().upper()[:80]
    return None


def extract_listing_marketplace(text: str) -> str:
    lowered = text.lower()
    if any(item in lowered for item in ["英国站", "uk", "united kingdom"]):
        return "UK"
    if any(item in lowered for item in ["德国站", "de", "germany"]):
        return "DE"
    if any(item in lowered for item in ["日本站", "jp", "japan"]):
        return "JP"
    if any(item in lowered for item in ["美国站", "us", "usa", "united states"]):
        return "US"
    return "US"


def extract_listing_price(text: str) -> float | None:
    match = re.search(r"(?:价格|售价|price)\s*[:：]?\s*(?:USD|\$|￥|CNY)?\s*(\d+(?:\.\d{1,2})?)", text, re.I)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def extract_listing_inventory(text: str) -> int | None:
    match = re.search(r"(?:库存|数量|inventory|stock)\s*[:：]?\s*(\d{1,7})", text, re.I)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def extract_upload_mode(text: str) -> str:
    lowered = text.lower()
    if any(item in lowered for item in ["批量", "模板", "excel", "xlsx"]):
        return "batch_excel"
    if any(item in lowered for item in ["网页", "逐个", "字段", "表单"]):
        return "web_form"
    return "auto"


def _build_listing_generation_prompt(
    *,
    message: str,
    sku: str | None,
    marketplace: str,
    erp_context: dict[str, Any],
    image_analysis: dict[str, Any],
    price: Any,
    inventory: Any,
    upload_mode: str,
) -> str:
    return f"""你是跨境电商运营 Listing 专员，正在为 Amazon Seller Central 生成上架草稿。

要求：
1. 输出英文 Listing，附中文审核备注。
2. 必须包含 Title (English)、5 条 Bullet Points、Product Description、Backend Search Terms、Promo Copy、Review Notes。
3. 价格和库存只能使用用户输入或 ERPNext 查询结果，不能编造。
4. 图片只能用于识别可见信息，不确定的材质、认证、容量、功效不能编造。
5. 不要说已经发布或已经上传，系统会先保存草稿，等运营确认后再打开 Amazon 填表。

SKU：{sku or "未识别"}
目标站点：{marketplace}
上传方式：{upload_mode_label(upload_mode)}
价格：{price if price is not None else "待运营补充"}
库存：{inventory if inventory is not None else "待运营补充"}

ERPNext 摘要：
{dumps_json(_public_erp_context(erp_context))}

图片分析：
{image_analysis.get("summary")}

用户原始需求：
{message}
"""


def _try_multimodal_image_summary(*, content_base64: str, mime_type: str) -> str | None:
    try:
        base64.b64decode(content_base64, validate=True)
    except Exception:
        return None
    try:
        response = chat_model.invoke([
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": (
                        "请用中文简短分析这张产品图，只描述图片能确定的产品类型、颜色、形状、包装、使用场景。"
                        "不要编造材质、容量、认证、功效。"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{content_base64}"},
                },
            ])
        ])
    except Exception:
        return None
    text = str(getattr(response, "content", "") or "").strip()
    return text[:1000] if text else None


def _normalize_attachments(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _assets_from_content(content: dict[str, Any], *, current_user: dict) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for item in content.get("image_assets") or []:
        if not isinstance(item, dict):
            continue
        assets.append(item)
    for artifact_id in content.get("image_artifact_ids") or []:
        try:
            storage = get_generated_file_storage_reference(str(artifact_id), current_user=current_user)
        except Exception:
            continue
        assets.append({
            "type": "product_image",
            "artifact_id": str(artifact_id),
            "filename": storage["filename"],
            "mime_type": storage["mime_type"],
            "local_file_path": storage["storage_path"],
        })
    return assets


def _asset_names(content: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in content.get("image_analysis", {}).get("items") or []:
        if isinstance(item, dict) and item.get("filename"):
            names.append(str(item["filename"]))
    return names


def _public_erp_context(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": value.get("status"),
        "message": value.get("message"),
        "item": _compact_erp_item(value.get("item")),
        "price": value.get("price"),
        "price_source": value.get("price_source"),
        "inventory": value.get("inventory"),
        "inventory_source": value.get("inventory_source"),
        "reference_count": len(value.get("references") or []),
    }


def _compact_erp_item(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        key: value.get(key)
        for key in ["name", "item_code", "item_name", "item_group", "stock_uom", "disabled"]
        if value.get(key) not in (None, "")
    }


def _first_number(item: dict[str, Any] | None, keys: list[str]) -> float | None:
    if not isinstance(item, dict):
        return None
    for key in keys:
        value = item.get(key)
        try:
            if value not in (None, ""):
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(item: dict[str, Any] | None, keys: list[str]) -> int | None:
    number = _first_number(item, keys)
    return int(number) if number is not None else None


def _resource_label(resource: str) -> str:
    return {
        "Item": "商品资料",
        "Item Price": "商品价格",
        "Bin": "库存",
    }.get(resource, resource)


def _status_from_mcp_result(result: dict[str, Any]) -> tuple[str, str, str]:
    raw = str(result.get("status") or "").strip().lower()
    if raw in {"waiting_manual_publish", "completed", "succeeded"}:
        return "waiting_manual_publish", "external_synced", "succeeded"
    if raw in {"waiting_executor", "stub_ready", "ready_to_execute"}:
        return "waiting_executor", "rpa_ready", "blocked"
    if raw in {"invalid_argument", "blocked", "failed", "error"} or result.get("ok") is False:
        return "failed", "failed", "failed"
    return "waiting_executor", "rpa_ready", "blocked"


def _amazon_upload_message(result: dict[str, Any], business_status: str) -> str:
    if business_status == "waiting_manual_publish":
        return AMAZON_LISTING_FINAL_MESSAGE
    return str(result.get("message") or "Amazon 上传准备已停止，等待运营或管理员处理。")


def _amazon_status_label(value: str) -> str:
    return {
        "waiting_manual_publish": "等待人工发布",
        "waiting_executor": "等待执行器配置",
        "failed": "执行失败",
    }.get(value, value)


def _public_execution(execution: dict[str, Any], *, current_user: dict) -> dict[str, Any]:
    if current_user.get("role") == "admin":
        return sanitize_metadata(execution)
    cleaned = sanitize_metadata(execution)
    cleaned["target"] = "amazon_seller_central"
    cleaned["request_payload"] = {
        "message": "Amazon 上传执行参数仅管理员可见",
        "manual_final_publish_required": True,
    }
    response = cleaned.get("response_payload") if isinstance(cleaned.get("response_payload"), dict) else {}
    cleaned["response_payload"] = {
        "status": response.get("status"),
        "message": response.get("message"),
        "filled_fields": response.get("filled_fields") or [],
        "failed_fields": response.get("failed_fields") or [],
        "manual_final_publish_required": True,
        "auto_publish_allowed": False,
    }
    return cleaned


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
