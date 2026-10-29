from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.auth.security import get_current_user
from app.services.operations_image_service import MAX_IMAGE_BYTES, ensure_operations_image_access, generate_product_scene

router = APIRouter(prefix="/operations/images", tags=["operations-images"])


class ProductSceneResponse(BaseModel):
    artifact_id: str
    filename: str
    mime_type: str
    model: str
    run_id: str


@router.post("/generate", response_model=ProductSceneResponse)
async def generate_image(file: UploadFile = File(...), prompt: str = Form(...), current_user: dict = Depends(get_current_user)):
    ensure_operations_image_access(current_user)
    content = await file.read(MAX_IMAGE_BYTES + 1)
    return await run_in_threadpool(
        generate_product_scene,
        content=content,
        mime_type=file.content_type,
        prompt=prompt,
        current_user=current_user,
        entrypoint="/operations/images/generate",
    )
