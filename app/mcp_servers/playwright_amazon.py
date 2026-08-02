from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.config import settings


mcp = FastMCP(
    "company-playwright-amazon",
    instructions="Amazon Seller Central 浏览器自动化工具。只填写草稿，禁止自动点击最终发布。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """返回 Amazon Playwright 执行器配置状态，不打开浏览器。"""
    enabled = bool(settings.amazon_playwright_enabled)
    seller_url = _seller_central_url()
    user_data_dir = _browser_user_data_dir()
    selectors_ready = _selectors_ready()
    playwright_available = _playwright_available()
    status = "configured" if enabled and user_data_dir and selectors_ready and playwright_available else "stub_ready"

    if not enabled:
        message = "Amazon Playwright 执行器未启用；当前只返回待配置状态。"
    elif not playwright_available:
        message = "未安装 playwright Python 包，无法真实操作 Seller Central。"
    elif not user_data_dir:
        message = "未配置浏览器用户目录，无法复用本机已登录 Seller Central 状态。"
    elif not selectors_ready:
        message = "未配置 Seller Central 字段选择器，暂不能真实填表。"
    else:
        message = "Amazon Playwright 执行器已配置；会填入草稿并停在发布前。"

    return {
        "ok": True,
        "status": status,
        "message": message,
        "seller_central_url": seller_url,
        "enabled": enabled,
        "playwright_available": playwright_available,
        "uses_existing_browser_state": bool(user_data_dir),
        "selector_profile_configured": selectors_ready,
        "auto_publish_allowed": False,
    }


@mcp.tool()
def prepare_seller_central_listing(
    listing: dict[str, Any],
    target_marketplace: str = "US",
    sku: str | None = None,
    category_path: str | None = None,
    assets: list[dict[str, Any]] | None = None,
    stop_before_publish: bool = True,
    upload_mode: str = "auto",
    selector_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """准备 Amazon Seller Central Listing 填表任务；第一版禁止自动发布。"""
    normalized_listing = _normalize_listing(listing)
    normalized_assets = assets or []
    normalized_upload_mode = _normalize_upload_mode(upload_mode, normalized_assets)
    if category_path and not normalized_listing.get("category_path"):
        normalized_listing["category_path"] = str(category_path).strip()
    selectors_ready = bool(_selector_profile(selector_profile))
    missing_fields = [
        key
        for key in ("title", "bullet_points", "description", "keywords", "category_path")
        if not normalized_listing.get(key)
    ]
    if missing_fields:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": f"Listing 草稿缺少必要字段：{', '.join(missing_fields)}。",
            "missing_fields": missing_fields,
            "auto_publish_allowed": False,
        }

    if not stop_before_publish:
        return {
            "ok": False,
            "status": "blocked",
            "message": "安全策略要求停在最终发布前，不能自动发布 Amazon Listing。",
            "auto_publish_allowed": False,
        }

    selectors = _selector_profile(selector_profile)
    if not settings.amazon_playwright_enabled:
        return _waiting_executor(
            normalized_listing=normalized_listing,
            target_marketplace=target_marketplace,
            sku=sku,
            assets=normalized_assets,
            upload_mode=normalized_upload_mode,
            message="Amazon Playwright 执行器未启用；已生成受控填表任务，等待管理员配置后执行。",
        )

    user_data_dir = _browser_user_data_dir()
    if not user_data_dir:
        return {
            "ok": False,
            "status": "failed",
            "message": "未检测到可用的 Seller Central 登录态，无法继续执行，请先登录后再重试。",
            "target": "amazon_seller_central",
            "target_marketplace": str(target_marketplace or "US").upper(),
            "sku": str(sku or "").strip() or None,
            "category_path": str(normalized_listing.get("category_path") or "").strip() or None,
            "upload_mode": normalized_upload_mode,
            "filled_fields": _field_labels(normalized_listing),
            "failed_fields": [
                {
                    "field": "login_state",
                    "label": "Seller Central 登录态",
                    "reason": "未检测到可用的浏览器登录态，无法继续执行。",
                }
            ],
            "current_url": _seller_central_url(),
            "retry_attempted": False,
            "manual_final_publish_required": True,
            "auto_publish_allowed": False,
            "uses_existing_browser_state": False,
            "selector_profile_configured": selectors_ready,
        }

    if not selectors:
        return _waiting_executor(
            normalized_listing=normalized_listing,
            target_marketplace=target_marketplace,
            sku=sku,
            assets=normalized_assets,
            upload_mode=normalized_upload_mode,
            message="未配置 Seller Central 字段选择器。当前不执行真实填表，避免误操作页面。",
        )

    return _run_playwright_prepare(
        normalized_listing=normalized_listing,
        target_marketplace=target_marketplace,
        sku=sku,
        assets=normalized_assets,
        upload_mode=normalized_upload_mode,
        selectors=selectors,
        user_data_dir=user_data_dir,
    )


def _run_playwright_prepare(
    *,
    normalized_listing: dict[str, Any],
    target_marketplace: str,
    sku: str | None,
    assets: list[dict[str, Any]],
    upload_mode: str,
    selectors: dict[str, Any],
    user_data_dir: str,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as error:
        return _waiting_executor(
            normalized_listing=normalized_listing,
            target_marketplace=target_marketplace,
            sku=sku,
            assets=assets,
            upload_mode=upload_mode,
            message=f"未安装 playwright Python 包，无法真实操作 Seller Central：{error}",
        )

    timeout_ms = max(3, int(settings.amazon_playwright_timeout_seconds or 20)) * 1000
    url = str(
        selectors.get("bulk_upload_url" if upload_mode == "batch_excel" else "listing_url")
        or selectors.get("url")
        or _seller_central_url()
    ).strip()
    failures: list[dict[str, Any]] = []
    filled_fields: list[str] = []
    retry_state: dict[str, Any] = {"attempted": False}
    current_url = url
    try:
        playwright = sync_playwright().start()
        try:
            context = _launch_context(playwright, user_data_dir=user_data_dir)
        except Exception as error:
            playwright.stop()
            return _waiting_executor(
                normalized_listing=normalized_listing,
                target_marketplace=target_marketplace,
                sku=sku,
                assets=assets,
                upload_mode=upload_mode,
                message=f"无法打开浏览器用户目录，请确认已安装 Chrome/Chromium 且目录未被其他进程锁定：{error}",
            )

        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if upload_mode == "batch_excel":
            _upload_batch_template(page, selectors=selectors, assets=assets, failures=failures, retry_state=retry_state)
            if not failures:
                filled_fields.append("批量 Excel 模板")
        else:
            _fill_listing_form(
                page,
                selectors=selectors,
                listing=normalized_listing,
                assets=assets,
                failures=failures,
                filled_fields=filled_fields,
                retry_state=retry_state,
            )
        publish_selector = _selector(selectors, "publish_button", "publish_button_selector", "submit_button")
        publish_button_detected = False
        if publish_selector:
            try:
                page.locator(publish_selector).first.wait_for(state="attached", timeout=min(3000, timeout_ms))
                publish_button_detected = True
            except (PlaywrightTimeoutError, PlaywrightError):
                publish_button_detected = False
        screenshot_path = _save_screenshot(page, prefix="amazon-listing-failed" if failures else "amazon-listing-ready")
        current_url = page.url
    except Exception as error:
        return {
            "ok": False,
            "status": "failed",
            "message": f"Amazon Seller Central 自动填表失败，已停止并等待运营人工处理：{error}",
            "target": "amazon_seller_central",
            "target_marketplace": str(target_marketplace or "US").upper(),
            "sku": str(sku or "").strip() or None,
            "category_path": str(normalized_listing.get("category_path") or "").strip() or None,
            "upload_mode": upload_mode,
            "current_url": url,
            "retry_attempted": bool(retry_state.get("attempted")),
            "manual_final_publish_required": True,
            "auto_publish_allowed": False,
        }

    if failures:
        return {
            "ok": False,
            "status": "failed",
            "message": "Amazon 页面有字段没有找到或无法填写，已停在当前页面，请运营人工接着填。",
            "target": "amazon_seller_central",
            "target_marketplace": str(target_marketplace or "US").upper(),
            "sku": str(sku or "").strip() or None,
            "category_path": str(normalized_listing.get("category_path") or "").strip() or None,
            "upload_mode": upload_mode,
            "filled_fields": filled_fields,
            "failed_fields": failures,
            "screenshot_path": screenshot_path,
            "current_url": current_url,
            "retry_attempted": bool(retry_state.get("attempted")),
            "manual_final_publish_required": True,
            "auto_publish_allowed": False,
        }

    return {
        "ok": True,
        "status": "waiting_manual_publish",
        "message": "已填写完成，请你检查 Amazon 页面后手动发布。",
        "target": "amazon_seller_central",
        "target_marketplace": str(target_marketplace or "US").upper(),
        "seller_central_url": url,
        "current_url": current_url,
        "sku": str(sku or "").strip() or None,
        "category_path": str(normalized_listing.get("category_path") or "").strip() or None,
        "upload_mode": upload_mode,
        "filled_fields": filled_fields,
        "asset_count": len(assets),
        "publish_button_detected": publish_button_detected,
        "screenshot_path": screenshot_path,
        "retry_attempted": bool(retry_state.get("attempted")),
        "manual_final_publish_required": True,
        "auto_publish_allowed": False,
        "uses_existing_browser_state": True,
        "selector_profile_configured": True,
    }


def _fill_listing_form(
    page: Any,
    *,
    selectors: dict[str, Any],
    listing: dict[str, Any],
    assets: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    filled_fields: list[str],
    retry_state: dict[str, Any],
) -> None:
    fields = [
        ("title", "标题", listing.get("title")),
        ("description", "产品描述", listing.get("description")),
        ("keywords", "搜索关键词", listing.get("keywords")),
    ]
    for key, label, value in fields:
        if _fill_text(page, selector=_selector(selectors, key, f"{key}_selector"), value=value, retry_state=retry_state):
            filled_fields.append(label)
        else:
            failures.append({"field": key, "label": label, "reason": "未找到字段或无法填写", "retry_attempted": bool(retry_state.get("attempted"))})

    for key, label, value in [
        ("price", "价格", listing.get("price")),
        ("inventory", "库存", listing.get("inventory")),
    ]:
        if value in (None, ""):
            continue
        if _fill_text(page, selector=_selector(selectors, key, f"{key}_selector"), value=value, retry_state=retry_state):
            filled_fields.append(label)
        else:
            failures.append({"field": key, "label": label, "reason": "未找到字段或无法填写", "retry_attempted": bool(retry_state.get("attempted"))})

    bullet_selectors = _bullet_selectors(selectors)
    bullets = listing.get("bullet_points") if isinstance(listing.get("bullet_points"), list) else []
    if bullet_selectors and bullets:
        for index, value in enumerate(bullets[: min(len(bullet_selectors), 5)]):
            if _fill_text(page, selector=bullet_selectors[index], value=value, retry_state=retry_state):
                filled_fields.append(f"五点描述 {index + 1}")
            else:
                failures.append({"field": f"bullet_{index + 1}", "label": f"五点描述 {index + 1}", "reason": "未找到字段或无法填写", "retry_attempted": bool(retry_state.get("attempted"))})
    else:
        failures.append({"field": "bullet_points", "label": "五点描述", "reason": "未配置五点字段选择器", "retry_attempted": bool(retry_state.get("attempted"))})

    category_selector = _selector(selectors, "category_path", "category_path_selector", "browse_node", "browse_node_selector")
    category_value = str(listing.get("category_path") or "").strip()
    if category_value:
        if category_selector:
            if _fill_text(page, selector=category_selector, value=category_value, retry_state=retry_state):
                filled_fields.append("类目")
            else:
                failures.append({"field": "category_path", "label": "类目", "reason": "未找到字段或无法填写", "retry_attempted": bool(retry_state.get("attempted"))})
        else:
            filled_fields.append("类目")

    image_selector = _selector(selectors, "image_upload", "image_upload_selector")
    image_files = _local_files(assets, allowed_types={"product_image"})
    if image_selector and image_files:
        try:
            page.set_input_files(image_selector, image_files)
            filled_fields.append("产品图片")
        except Exception as error:
            retry_state["attempted"] = True
            try:
                page.set_input_files(image_selector, image_files)
                filled_fields.append("产品图片")
            except Exception as retry_error:
                failures.append({"field": "image_upload", "label": "产品图片", "reason": str(retry_error)[:200], "retry_attempted": True})


def _upload_batch_template(page: Any, *, selectors: dict[str, Any], assets: list[dict[str, Any]], failures: list[dict[str, Any]], retry_state: dict[str, Any]) -> None:
    selector = _selector(selectors, "bulk_template_upload", "bulk_template_upload_selector")
    files = _local_files(assets, allowed_types={"amazon_batch_template"})
    if not selector:
        failures.append({"field": "bulk_template_upload", "label": "批量模板上传", "reason": "未配置批量模板上传控件选择器", "retry_attempted": bool(retry_state.get("attempted"))})
        return
    if not files:
        failures.append({"field": "bulk_template", "label": "批量 Excel 模板", "reason": "未找到可上传的批量模板文件", "retry_attempted": bool(retry_state.get("attempted"))})
        return
    try:
        page.set_input_files(selector, files[0])
    except Exception as error:
        retry_state["attempted"] = True
        try:
            page.set_input_files(selector, files[0])
        except Exception as retry_error:
            failures.append({"field": "bulk_template_upload", "label": "批量模板上传", "reason": str(retry_error)[:200], "retry_attempted": True})


def _fill_text(page: Any, *, selector: str | None, value: Any, retry_state: dict[str, Any]) -> bool:
    if not selector or value in (None, ""):
        return False
    for attempt in range(2):
        try:
            locator = page.locator(selector).first
            locator.scroll_into_view_if_needed(timeout=1500)
            locator.fill(str(value))
            if attempt > 0:
                retry_state["attempted"] = True
            return True
        except Exception:
            retry_state["attempted"] = True
            continue
    return False


def _launch_context(playwright: Any, *, user_data_dir: str):
    kwargs: dict[str, Any] = {
        "user_data_dir": user_data_dir,
        "headless": bool(settings.amazon_playwright_headless),
    }
    channel = str(settings.amazon_playwright_browser_channel or "").strip()
    if channel:
        kwargs["channel"] = channel
    try:
        return playwright.chromium.launch_persistent_context(**kwargs)
    except Exception:
        if "channel" in kwargs:
            kwargs.pop("channel")
            return playwright.chromium.launch_persistent_context(**kwargs)
        raise


def _save_screenshot(page: Any, *, prefix: str) -> str | None:
    try:
        target_dir = Path("data/playwright_screenshots")
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{prefix}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)
    except Exception:
        return None


def _normalize_listing(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    bullet_points = value.get("bullet_points") or value.get("bullets") or value.get("five_points")
    if isinstance(bullet_points, str):
        bullet_points = [item.strip() for item in bullet_points.split("\n") if item.strip()]
    keywords = value.get("keywords") or value.get("search_terms")
    if isinstance(keywords, list):
        keywords = " ".join(str(item).strip() for item in keywords if str(item).strip())
    normalized = {
        "title": str(value.get("title") or "").strip(),
        "bullet_points": bullet_points if isinstance(bullet_points, list) else [],
        "description": str(value.get("description") or "").strip(),
        "keywords": str(keywords or "").strip(),
        "price": value.get("price"),
        "inventory": value.get("inventory") or value.get("stock"),
    }
    category_path = str(value.get("category_path") or value.get("category") or value.get("browse_node") or "").strip()
    if category_path:
        normalized["category_path"] = category_path[:500]
    if value.get("brand"):
        normalized["brand"] = str(value["brand"]).strip()
    if value.get("product_type"):
        normalized["product_type"] = str(value["product_type"]).strip()
    return normalized


def _waiting_executor(
    *,
    normalized_listing: dict[str, Any],
    target_marketplace: str,
    sku: str | None,
    assets: list[dict[str, Any]],
    upload_mode: str,
    message: str,
    status: str = "waiting_executor",
) -> dict[str, Any]:
    selectors_ready = _selectors_ready()
    return {
        "ok": True,
        "status": status,
        "message": message,
        "target": "amazon_seller_central",
        "target_marketplace": str(target_marketplace or "US").upper(),
        "seller_central_url": _seller_central_url(),
        "sku": str(sku or "").strip() or None,
        "upload_mode": upload_mode,
        "filled_fields": _field_labels(normalized_listing),
        "asset_count": len(assets),
        "manual_final_publish_required": True,
        "auto_publish_allowed": False,
        "uses_existing_browser_state": bool(_browser_user_data_dir()),
        "selector_profile_configured": selectors_ready,
    }


def _field_labels(listing: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    mapping = {
        "title": "标题",
        "bullet_points": "五点描述",
        "description": "产品描述",
        "keywords": "搜索关键词",
        "price": "价格",
        "inventory": "库存",
    }
    for key, label in mapping.items():
        if listing.get(key):
            labels.append(label)
    return labels


def _selector(profile: dict[str, Any], *keys: str) -> str | None:
    selectors = profile.get("selectors") if isinstance(profile.get("selectors"), dict) else profile
    for key in keys:
        value = selectors.get(key) if isinstance(selectors, dict) else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _bullet_selectors(profile: dict[str, Any]) -> list[str]:
    selectors = profile.get("selectors") if isinstance(profile.get("selectors"), dict) else profile
    raw = selectors.get("bullet_points") if isinstance(selectors, dict) else None
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    result: list[str] = []
    for index in range(1, 6):
        value = selectors.get(f"bullet_point_{index}") if isinstance(selectors, dict) else None
        if isinstance(value, str) and value.strip():
            result.append(value.strip())
    return result


def _local_files(assets: list[dict[str, Any]], *, allowed_types: set[str]) -> list[str]:
    files: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if str(asset.get("type") or "") not in allowed_types:
            continue
        raw_path = str(asset.get("local_file_path") or "").strip()
        if not raw_path:
            continue
        path = Path(raw_path).expanduser()
        if path.exists() and path.is_file():
            files.append(str(path))
    return files


def _seller_central_url() -> str:
    return (settings.amazon_seller_central_url or "https://sellercentral.amazon.com/").strip()


def _browser_user_data_dir() -> str | None:
    value = str(settings.amazon_playwright_user_data_dir or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    return str(path) if path.exists() and path.is_dir() else None


def _selectors_ready(selector_profile: dict[str, Any] | None = None) -> bool:
    return bool(_selector_profile(selector_profile))


def _selector_profile(value: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(value, dict) and value:
        return value
    raw = str(settings.amazon_playwright_selector_profile or "").strip()
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        path = Path(raw).expanduser()
        if not path.exists() or not path.is_file():
            return {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return loaded if isinstance(loaded, dict) else {}


def _normalize_upload_mode(value: str, assets: list[dict[str, Any]]) -> str:
    mode = str(value or "auto").strip().lower()
    if mode == "auto":
        if any(isinstance(item, dict) and item.get("type") == "amazon_batch_template" for item in assets):
            return "batch_excel"
        return "web_form"
    if mode in {"batch_excel", "web_form"}:
        return mode
    return "web_form"


def _playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except Exception:
        return False
    return True


if __name__ == "__main__":
    mcp.run(transport="stdio")
