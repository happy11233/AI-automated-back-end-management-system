"""Generate and persist product scene images for the operations team."""
from __future__ import annotations

import base64
import binascii
import logging
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.config import settings
from app.observability import annotate_trace, observed
from app.services.chat_intent_guard_service import is_information_request, is_action_negated
from app.services.generated_file_service import save_generated_file
from app.services.run_record_service import elapsed_ms, finish_run, now_ms, record_step, start_run
from app.services.user_ai_app_permission_service import is_ai_app_allowed

logger = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_RESULT_BYTES = 20 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
IMAGE_INTENT_MARKERS = ("生成场景图", "生成背景图", "生成图片", "制作场景图", "产品场景图", "商品场景图", "换背景", "作图", "生图")


def ensure_operations_image_access(current_user: dict) -> None:
    if current_user.get("role") != "admin" and current_user.get("position") != "operations":
        raise HTTPException(status_code=403, detail="仅运营岗位可使用商品场景图生成")
    if not is_ai_app_allowed(current_user, "operations-product-scene"):
        raise HTTPException(status_code=403, detail="商品场景图应用已被管理员禁用")


def image_type_from_bytes(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_source_image(content: bytes, claimed_type: str | None) -> str:
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="请上传不超过 10 MB 的商品图片")
    actual_type = image_type_from_bytes(content)
    if actual_type not in ALLOWED_IMAGE_TYPES or claimed_type not in ALLOWED_IMAGE_TYPES or actual_type != claimed_type:
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPEG 或 WebP 图片，文件格式须与内容一致")
    return actual_type


def image_generation_requested(message: str, attachments: list[dict] | None = None) -> bool:
    text = message.strip().lower()
    if is_information_request(text) or is_action_negated(text):
        return False
    return any(marker in text for marker in IMAGE_INTENT_MARKERS) and (
        any(str(item.get("mime_type") or "").startswith("image/") for item in (attachments or []))
        or text.startswith(("生成场景图", "生成背景图", "生成图片", "制作场景图", "换背景", "作图", "生图"))
    )


def image_from_chat_attachments(attachments: list[dict]) -> tuple[bytes, str] | None:
    for item in attachments:
        if not str(item.get("mime_type") or "").startswith("image/"):
            continue
        encoded = item.get("content_base64")
        if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES * 4 // 3) + 100:
            raise HTTPException(status_code=400, detail="会话图片无效或超过 10 MB")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise HTTPException(status_code=400, detail="会话图片编码无效") from error
        return content, validate_source_image(content, item.get("mime_type"))
    return None


def _provider_url() -> str:
    base = settings.bailian_image_api_base_url.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.hostname or not (
        parsed.hostname in {"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com"}
        or parsed.hostname.endswith(".maas.aliyuncs.com")
    ):
        raise HTTPException(status_code=503, detail="图像服务地址配置无效")
    return f"{base}/services/aigc/multimodal-generation/generation"


def _download_generated_image(client: httpx.Client, image_url: str) -> tuple[bytes, str]:
    parsed = urlparse(image_url)
    if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.hostname or not (
        parsed.hostname.endswith(".aliyuncs.com") or parsed.hostname.endswith(".aliyuncs.com.cn")
    ):
        raise HTTPException(status_code=502, detail="图像服务返回了不受信任的图片地址")
    try:
        with client.stream("GET", image_url, follow_redirects=False) as response:
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_RESULT_BYTES:
                    raise HTTPException(status_code=502, detail="生成图片超过 20 MB 限制")
                chunks.append(chunk)
        content = b"".join(chunks)
    except httpx.HTTPError as error:
        logger.warning("Unable to download generated product image: %s", type(error).__name__)
        raise HTTPException(status_code=502, detail="生成图片下载失败，请重试") from error
    mime_type = image_type_from_bytes(content)
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=502, detail="图像服务返回的文件不是有效图片")
    return content, mime_type


@observed("operations.product_scene_image")
def generate_product_scene(*, content: bytes, mime_type: str | None, prompt: str, current_user: dict, entrypoint: str, thread_id: str | None = None) -> dict:
    ensure_operations_image_access(current_user)
    instruction = prompt.strip()
    if not instruction or len(instruction) > 1200:
        raise HTTPException(status_code=400, detail="请输入 1 到 1200 字的场景描述")
    mime_type = validate_source_image(content, mime_type)
    if not settings.dashscope_api_key or settings.dashscope_api_key.startswith("your_"):
        raise HTTPException(status_code=503, detail="图像服务尚未配置百炼 API Key")
    model = settings.bailian_image_edit_model
    image_data = f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"
    scene_instruction = (
        "以输入图片中的商品为唯一主体，保持商品真实外观、形状、颜色、品牌标识和文字不变；只替换白色背景，"
        "生成一张适合电商展示的高质量写实产品场景图。不要增加第二个商品、虚构配件或修改标签。场景要求：" + instruction
    )
    payload = {
        "model": model,
        "input": {"messages": [{"role": "user", "content": [{"image": image_data}, {"text": scene_instruction}]}]},
        "parameters": {"n": 1, "watermark": False},
    }
    started = now_ms()
    run_id = start_run(
        run_type="image_generation", app_id="operations-product-scene", app_name="运营商品场景图",
        entrypoint=entrypoint, current_user=current_user, thread_id=thread_id,
        resource_type="image_generation", input_text="商品场景图生成",
        metadata={"model": model, "source_image": True},
    )
    annotate_trace(workflow_id="operations_product_scene", business_run_id=run_id, ls_provider="dashscope", ls_model_name=model)
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.bailian_image_timeout_seconds, connect=10)) as client:
            response = client.post(_provider_url(), headers={"Authorization": f"Bearer {settings.dashscope_api_key}", "Content-Type": "application/json"}, json=payload)
            if response.status_code >= 400:
                logger.warning("Product image provider failed: status=%s", response.status_code)
                raise HTTPException(status_code=502, detail="图像服务暂时不可用，请检查模型权限或稍后重试")
            result = response.json()
            if result.get("code"):
                raise HTTPException(status_code=502, detail="图像生成失败，请检查模型权限或调整提示词")
            choices = result.get("output", {}).get("choices", [])
            output = choices[0].get("message", {}).get("content", []) if choices else []
            image_url = next((part.get("image") for part in output if isinstance(part, dict) and part.get("image")), None)
            if not image_url:
                raise HTTPException(status_code=502, detail="图像服务未返回生成图片")
            generated, generated_mime = _download_generated_image(client, image_url)
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[generated_mime]
        filename = f"product-scene.{extension}"
        artifact_id = save_generated_file(
            run_id=run_id, content=generated, filename=filename, artifact_type="image_file",
            mime_type=generated_mime, current_user=current_user,
            metadata={"workflow_id": "operations_product_scene", "model": model, "source_image": True},
        )
        if not artifact_id:
            raise HTTPException(status_code=500, detail="生成图片保存失败")
        record_step(run_id=run_id, step_name="image_generation", status_value="succeeded", provider="dashscope", resource_type="image_file", resource_id=artifact_id, duration_ms=elapsed_ms(started), metadata={"model": model, "bytes": len(generated)})
        finish_run(run_id, status_value="succeeded", output_text="商品场景图已生成", duration_ms=elapsed_ms(started), metadata={"artifact_id": artifact_id})
        return {"artifact_id": artifact_id, "filename": filename, "mime_type": generated_mime, "model": model, "run_id": run_id}
    except Exception as error:
        finish_run(run_id, status_value="failed", error_message=type(error).__name__, duration_ms=elapsed_ms(started))
        if isinstance(error, HTTPException):
            raise
        logger.exception("Product scene image generation failed")
        raise HTTPException(status_code=502, detail="图像生成失败，请稍后重试") from error
