"""Task registration and evidence queries; external actions remain separately gated."""
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.agent_task_contracts import StoreCreate, StoreGrant, TaskCreate, TaskRunLink, TaskStatus
from app.auth.security import get_current_user, require_admin
from app.services import agent_task_service as service

router = APIRouter(prefix='/agent-tasks', tags=['agent-tasks'])


@router.get('/stores')
def stores(user: dict = Depends(get_current_user)):
    return service.list_stores(user)


@router.post('/stores', status_code=201)
def register_store(data: StoreCreate, user: dict = Depends(require_admin)):
    return service.create_store(data, user)


@router.put('/stores/{store_id}/grants')
def store_grant(store_id: UUID, data: StoreGrant, user: dict = Depends(require_admin)):
    return service.grant_store(str(store_id), data, user)


@router.post('', status_code=201)
def register_task(data: TaskCreate, idempotency_key: str = Header(alias='Idempotency-Key', min_length=8, max_length=128),
                  user: dict = Depends(get_current_user)):
    return service.create_task(data, idempotency_key, user)


@router.get('')
def tasks(status: TaskStatus | None = None, workflow_id: str | None = Query(default=None, max_length=100),
          limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0),
          user: dict = Depends(get_current_user)):
    return service.list_tasks(user, status=status, workflow_id=workflow_id, limit=limit, offset=offset)


@router.get('/{task_id}')
def detail(task_id: UUID, user: dict = Depends(get_current_user)):
    return service.task_detail(str(task_id), user)


@router.post('/{task_id}/runs')
def attach_run(task_id: UUID, data: TaskRunLink, user: dict = Depends(get_current_user)):
    return service.link_run(str(task_id), str(data.run_id), user)
