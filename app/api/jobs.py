from hashlib import sha256
import asyncio
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile

from app.artifact_storage import delete_artifact, put_artifact
from app.auth.security import get_current_user
from app.services.background_job_service import create_job, get_job, list_jobs, require_jobs_enabled
from app.services.user_ai_app_permission_service import is_ai_app_allowed

router = APIRouter(prefix='/jobs', tags=['background-jobs'])


@router.get('')
def job_list(limit: int = Query(50, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    return list_jobs(current_user, limit)


@router.post('/finance-reconciliation', status_code=202)
async def submit_reconciliation(
    files: list[UploadFile] = File(...), instruction: str = Form('', max_length=4000),
    base_currency: str = Form('CNY', min_length=3, max_length=3),
    idempotency_key: str = Header(..., alias='Idempotency-Key', min_length=8, max_length=128),
    current_user: dict = Depends(get_current_user),
):
    require_jobs_enabled()
    if current_user['role'] != 'admin' and (current_user.get('position') != 'finance' or
            not is_ai_app_allowed(current_user, 'finance-reconciliation')):
        raise HTTPException(403, '无权执行财务对账')
    if not 1 <= len(files) <= 8:
        raise HTTPException(400, '请上传 1 至 8 个 Excel 文件')
    inputs, total = [], 0
    keep_files = False
    try:
        for file in files:
            filename = Path(file.filename or '').name
            if Path(filename).suffix.lower() not in {'.xlsx', '.xls'}:
                raise HTTPException(400, '只支持 xlsx 或 xls')
            content = await file.read(8 * 1024 * 1024 + 1)
            total += len(content)
            if not content or len(content) > 8 * 1024 * 1024 or total > 32 * 1024 * 1024:
                raise HTTPException(400, '单文件限制 8MB，总文件限制 32MB，且不能是空文件')
            ref = await asyncio.to_thread(put_artifact, 'job-input-'+uuid4().hex+Path(filename).suffix, content, 'application/octet-stream')
            inputs.append({'filename': filename, 'storage_reference': ref, 'sha256': sha256(content).hexdigest()})
        result = await asyncio.to_thread(create_job, kind='finance_reconciliation', payload={
            'files': inputs, 'instruction': instruction, 'base_currency': base_currency.upper(),
        }, idempotency_key=idempotency_key, current_user=current_user)
        keep_files = not result['reused']
        return {**result, 'status_url': '/jobs/'+result['id']}
    finally:
        if not keep_files:
            for item in inputs:
                try:
                    await asyncio.to_thread(delete_artifact, item['storage_reference'])
                except Exception:
                    pass


@router.get('/{job_id}')
def job_status(job_id: UUID, current_user: dict = Depends(get_current_user)):
    return get_job(str(job_id), current_user)
