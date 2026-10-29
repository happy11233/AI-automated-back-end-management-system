"""Authorized business tasks; no endpoint here executes an external action."""
from hashlib import sha256
import json
from uuid import uuid4

from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.agent_task_contracts import StoreCreate, StoreGrant, TaskCreate
from app.db import transaction
from app.services.ai_workflow_service import get_ai_workflow, list_ai_workflows, _app_id_for_workflow
from app.services.run_record_service import sanitize_metadata


def _audit(cur, user: dict, action: str, resource_id: str, metadata: dict | None = None):
    cur.execute(
        'INSERT INTO audit_logs(user_id,action,resource_type,resource_id,metadata) '
        'VALUES (%s,%s,%s,%s,%s)',
        (user['id'], action, 'agent_task', resource_id, Jsonb(sanitize_metadata(metadata or {}))),
    )


def _store(cur, store_id: str, user: dict, position: str | None = None):
    params = [store_id]
    scope = ''
    if user['role'] != 'admin':
        scope = (' AND s.active AND EXISTS (SELECT 1 FROM ecommerce_store_grants g '
                 'WHERE g.store_id=s.id AND g.user_id=%s AND g.position=%s AND g.enabled)')
        params.extend([user['id'], position or user.get('position')])
    cur.execute('SELECT s.* FROM ecommerce_stores s WHERE s.id=%s' + scope, params)
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, '店铺不存在或无权访问')
    return row


def list_stores(user: dict) -> dict:
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        where, params = '', []
        if user['role'] != 'admin':
            where = ('WHERE s.active AND EXISTS (SELECT 1 FROM ecommerce_store_grants g '
                     'WHERE g.store_id=s.id AND g.user_id=%s AND g.position=%s AND g.enabled)')
            params = [user['id'], user.get('position')]
        cur.execute('SELECT s.id,s.platform,s.external_store_id,s.marketplace,s.name,s.active '
                    'FROM ecommerce_stores s ' + where + ' ORDER BY s.created_at,s.id', params)
        return {'items': cur.fetchall()}


def create_store(data: StoreCreate, user: dict) -> dict:
    if user['role'] != 'admin':
        raise HTTPException(403, '仅管理员可登记店铺')
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            'INSERT INTO ecommerce_stores(platform,external_store_id,marketplace,name,created_by) '
            'VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING *',
            (data.platform, data.external_store_id, data.marketplace, data.name, user['id']),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(409, '该平台店铺和站点已登记')
        _audit(cur, user, 'agent.store.create', str(row['id']))
        return {'item': row, 'connection_status': 'registered_only'}


def grant_store(store_id: str, data: StoreGrant, user: dict) -> dict:
    if user['role'] != 'admin':
        raise HTTPException(403, '仅管理员可配置店铺授权')
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        _store(cur, store_id, user)
        cur.execute('SELECT id,position FROM users WHERE id=%s', (data.user_id,))
        target = cur.fetchone()
        if not target or (data.enabled and target['position'] != data.position):
            raise HTTPException(422, '授权岗位必须与目标员工当前岗位一致')
        cur.execute(
            'INSERT INTO ecommerce_store_grants(store_id,user_id,position,enabled,updated_by) '
            'VALUES (%s,%s,%s,%s,%s) ON CONFLICT(store_id,user_id,position) DO UPDATE SET '
            'enabled=EXCLUDED.enabled,updated_by=EXCLUDED.updated_by,updated_at=now()',
            (store_id, data.user_id, data.position, data.enabled, user['id']),
        )
        _audit(cur, user, 'agent.store.grant', store_id, {'user_id': str(data.user_id), 'enabled': data.enabled})
        return {'store_id': store_id, **data.model_dump()}


def _scope(user: dict, workflows: list[dict]) -> tuple[str, list]:
    if user['role'] == 'admin':
        return 'TRUE', []
    return (
        't.owner_user_id=%s AND t.position=%s AND t.workflow_id=ANY(%s) AND t.app_id=ANY(%s) '
        'AND (t.store_id IS NULL OR EXISTS (SELECT 1 FROM ecommerce_stores s '
        'JOIN ecommerce_store_grants g ON g.store_id=s.id WHERE s.id=t.store_id AND s.active '
        'AND g.user_id=%s AND g.position=t.position AND g.enabled))',
        [user['id'], user.get('position'), [w['id'] for w in workflows],
         [_app_id_for_workflow(w) for w in workflows], user['id']],
    )


def _get_task(cur, task_id: str, user: dict, workflows: list[dict], *, lock=False):
    scope, params = _scope(user, workflows)
    cur.execute('SELECT t.* FROM agent_tasks t WHERE t.id=%s AND ' + scope +
                (' FOR UPDATE OF t' if lock else ''), [task_id, *params])
    task = cur.fetchone()
    if not task:
        raise HTTPException(404, '任务不存在或无权访问')
    return task


def create_task(data: TaskCreate, idempotency_key: str, user: dict) -> dict:
    key = idempotency_key.strip()
    if not 8 <= len(key) <= 128:
        raise HTTPException(422, 'Idempotency-Key 必须为 8–128 个非空字符')
    workflow = get_ai_workflow(data.workflow_id, user)
    normalized = data.model_dump(mode='json')
    digest = sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    workflows = [workflow] if user['role'] != 'admin' else []
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        if data.store_id:
            store = _store(cur, str(data.store_id), user, workflow['position'])
            if not store['active']:
                raise HTTPException(409, '店铺已停用')
        if data.thread_id:
            cur.execute('SELECT user_id,position,status FROM chat_threads WHERE id=%s', (data.thread_id,))
            thread = cur.fetchone()
            if not thread or str(thread['user_id']) != user['id'] or thread['status'] != 'active' or (
                thread['position'] is not None and thread['position'] != workflow['position']
            ):
                raise HTTPException(404, '会话不存在或不属于当前岗位')
        task_id = str(uuid4())
        policy = {'requires_approval': workflow['requires_approval'],
                  'approval_policy': workflow['approval_policy'], 'external_execution_enabled': False}
        cur.execute(
            'INSERT INTO agent_tasks(id,owner_user_id,position,workflow_id,app_id,title,goal,source,'
            'thread_id,store_id,expected_outputs,completion_criteria,policy_snapshot,workflow_version,'
            'idempotency_key,input_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
            'ON CONFLICT(owner_user_id,idempotency_key) DO NOTHING RETURNING *',
            (task_id, user['id'], workflow['position'], workflow['id'], _app_id_for_workflow(workflow),
             workflow['name'], data.goal, 'chat' if data.thread_id else 'manual', data.thread_id, data.store_id,
             Jsonb(data.expected_outputs or [workflow['output_contract']]), Jsonb(data.completion_criteria),
             Jsonb(policy), workflow['version'], key, digest),
        )
        task = cur.fetchone()
        if not task:
            cur.execute('SELECT id,input_hash FROM agent_tasks WHERE owner_user_id=%s AND idempotency_key=%s',
                        (user['id'], key))
            previous = cur.fetchone()
            if previous['input_hash'] != digest:
                raise HTTPException(409, '该幂等键已用于不同任务输入')
            task = _get_task(cur, str(previous['id']), user, workflows)
            reused = True
        else:
            for ref in data.objects:
                cur.execute(
                    'INSERT INTO ecommerce_business_objects(store_id,object_type,external_id,line_id) '
                    'VALUES (%s,%s,%s,%s) ON CONFLICT(store_id,object_type,external_id,line_id) '
                    'DO UPDATE SET external_id=EXCLUDED.external_id RETURNING id',
                    (data.store_id, ref.object_type, ref.external_id, ref.line_id),
                )
                object_id = cur.fetchone()['id']
                cur.execute('INSERT INTO agent_task_objects(task_id,object_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',
                            (task_id, object_id))
            _audit(cur, user, 'agent.task.create', task_id, {'workflow_id': workflow['id']})
            reused = False
        return {'item': _public_task(task), 'reused': reused,
                'message': '任务已登记，尚未执行；后续执行须通过任务授权与结果核验。'}


def _public_task(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in {'input_hash', 'idempotency_key'}}


def list_tasks(user: dict, *, status: str | None = None, workflow_id: str | None = None,
               limit: int = 30, offset: int = 0) -> dict:
    workflows = list_ai_workflows(user)
    if workflow_id and not any(w['id'] == workflow_id for w in workflows):
        raise HTTPException(404, 'Agent 不存在或无权访问')
    scope, params = _scope(user, workflows)
    if status:
        scope += ' AND t.status=%s'
        params.append(status)
    if workflow_id:
        scope += ' AND t.workflow_id=%s'
        params.append(workflow_id)
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT count(*) AS total FROM agent_tasks t WHERE ' + scope, params)
        total = cur.fetchone()['total']
        cur.execute('SELECT t.* FROM agent_tasks t WHERE ' + scope +
                    ' ORDER BY t.updated_at DESC,t.id DESC LIMIT %s OFFSET %s', [*params, limit, offset])
        return {'items': [_public_task(row) for row in cur.fetchall()], 'total': total,
                'limit': limit, 'offset': offset}


def task_detail(task_id: str, user: dict) -> dict:
    workflows = list_ai_workflows(user)
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        task = _get_task(cur, task_id, user, workflows)
        cur.execute('SELECT o.id,o.store_id,o.object_type,o.external_id,o.line_id '
                    'FROM agent_task_objects x JOIN ecommerce_business_objects o ON o.id=x.object_id '
                    'WHERE x.task_id=%s ORDER BY o.object_type,o.external_id,o.line_id', (task_id,))
        objects = cur.fetchall()
        if task['store_id']:
            store = _store(cur, str(task['store_id']), user, task['position'])
            store = {k: store[k] for k in ('id', 'platform', 'external_store_id', 'marketplace', 'name')}
        else:
            store = None
        # A task link never broadens the original run/file owner and position scope.
        run_scope, run_params = '', [task_id]
        if user['role'] != 'admin':
            run_scope = ' AND r.user_id=%s AND r.position=%s AND r.app_id IN (t.app_id,t.workflow_id)'
            run_params.extend([user['id'], user.get('position')])
        cur.execute(
            'SELECT r.id,r.status,r.app_id,r.app_name,r.output_preview,r.error_message,r.started_at,'
            'r.finished_at,x.attempt_number FROM agent_task_runs x '
            'JOIN agent_tasks t ON t.id=x.task_id JOIN automation_runs r ON r.id=x.run_id '
            'WHERE x.task_id=%s' + run_scope + ' ORDER BY x.attempt_number', run_params,
        )
        runs = cur.fetchall()
        run_ids = [row['id'] for row in runs]
        steps, artifacts = [], []
        if run_ids:
            cur.execute('SELECT id,run_id,step_order,step_name,status,duration_ms,output_preview,error_message '
                        'FROM automation_run_steps WHERE run_id=ANY(%s) ORDER BY run_id,step_order,started_at',
                        (run_ids,))
            steps = cur.fetchall()
            cur.execute('SELECT id,run_id,name,mime_type,size_bytes,downloadable,expires_at '
                        'FROM automation_run_artifacts WHERE run_id=ANY(%s) ORDER BY created_at', (run_ids,))
            artifacts = cur.fetchall()
        return {'item': _public_task(task), 'store': store, 'objects': objects, 'runs': runs,
                'steps': steps, 'artifacts': artifacts}


def link_run(task_id: str, run_id: str, user: dict) -> dict:
    workflows = list_ai_workflows(user)
    with transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
        task = _get_task(cur, task_id, user, workflows, lock=True)
        cur.execute('SELECT id,user_id,position,app_id,thread_id,metadata FROM automation_runs WHERE id=%s FOR UPDATE', (run_id,))
        run = cur.fetchone()
        if not run or str(run['user_id']) != str(task['owner_user_id']) or (
            run['position'] != task['position'] or run['app_id'] not in {task['app_id'], task['workflow_id']}
        ):
            raise HTTPException(404, '运行记录不存在或不属于该任务的用户、岗位和应用')
        if task['thread_id'] and run['thread_id'] != task['thread_id']:
            raise HTTPException(409, '运行记录不属于任务会话')
        if task['store_id'] and str((run['metadata'] or {}).get('store_id') or '') != str(task['store_id']):
            raise HTTPException(409, '运行记录缺少匹配的店铺证据，不能关联到该店铺任务')
        cur.execute('SELECT task_id,attempt_number FROM agent_task_runs WHERE run_id=%s', (run_id,))
        previous = cur.fetchone()
        if previous:
            if str(previous['task_id']) != task_id:
                raise HTTPException(409, '运行记录已关联其他任务')
            return {'task_id': task_id, 'run_id': run_id, 'attempt_number': previous['attempt_number'], 'reused': True}
        cur.execute('SELECT COALESCE(max(attempt_number),0)+1 AS next FROM agent_task_runs WHERE task_id=%s', (task_id,))
        attempt = cur.fetchone()['next']
        cur.execute('INSERT INTO agent_task_runs(task_id,run_id,attempt_number) VALUES (%s,%s,%s)',
                    (task_id, run_id, attempt))
        cur.execute('UPDATE agent_tasks SET updated_at=now(),revision=revision+1 WHERE id=%s', (task_id,))
        _audit(cur, user, 'agent.task.link_run', task_id, {'run_id': run_id})
        # An execution success is evidence, not business-completion verification.
        return {'task_id': task_id, 'run_id': run_id, 'attempt_number': attempt, 'reused': False}
