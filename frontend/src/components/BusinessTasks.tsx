import { useEffect, useRef, useState } from "react";
import { Alert, Button, Card, Descriptions, Drawer, Empty, Form, Input, List, Modal, Pagination, Select, Space, Spin, Tag, Typography, message } from "antd";
import { PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { createBusinessTask, getBusinessTask, listBusinessTasks, listTaskStores, type AiWorkflowItem, type BusinessTask, type BusinessTaskDetail, type BusinessTaskInput, type BusinessTaskStatus, type TaskStore } from "../api";

const { Paragraph, Text, Title } = Typography;
const states: Record<BusinessTaskStatus, { label: string; color: string }> = {
  draft: { label: "已登记 · 未执行", color: "default" },
  awaiting_input: { label: "待补资料", color: "warning" }, queued: { label: "排队中", color: "processing" },
  running: { label: "执行中", color: "processing" }, awaiting_approval: { label: "待审批", color: "warning" },
  awaiting_external: { label: "待外部核验", color: "warning" }, partially_completed: { label: "部分完成", color: "warning" },
  succeeded: { label: "业务已完成", color: "success" }, failed: { label: "执行失败", color: "error" },
  cancelled: { label: "已取消", color: "default" },
};
const time = (value: string) => new Date(value).toLocaleString("zh-CN", { hour12: false });
const errorText = (error: unknown) => error instanceof Error ? error.message : "请求失败，请重试";
const taskTag = (status: BusinessTaskStatus) => <Tag color={states[status]?.color}>{states[status]?.label || status}</Tag>;
const runLabels: Record<string, string> = { running: "执行中", succeeded: "步骤成功", failed: "执行失败", blocked: "执行受阻" };
type TaskForm = { workflow_id: string; store_id?: string; goal: string; expected_outputs?: string; completion_criteria?: string };

export function BusinessTasks({ token, workflows, workflowId }: { token: string; workflows: AiWorkflowItem[]; workflowId?: string }) {
  const [items, setItems] = useState<BusinessTask[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<BusinessTaskStatus | undefined>();
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [stores, setStores] = useState<TaskStore[]>([]);
  const [storesBusy, setStoresBusy] = useState(false);
  const [storeError, setStoreError] = useState("");
  const [storeRevision, setStoreRevision] = useState(0);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<BusinessTaskDetail | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailRevision, setDetailRevision] = useState(0);
  const requestId = useRef(0);
  const savingRef = useRef(false);
  const submission = useRef<{ body: string; key: string } | null>(null);
  const mounted = useRef(true);
  const [form] = Form.useForm<TaskForm>();
  const [notice, messageContext] = message.useMessage();
  const choices = workflows.filter((workflow) => !workflowId || workflow.id === workflowId);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const id = ++requestId.current;
    setBusy(true); setError(""); setItems([]); setTotal(0);
    listBusinessTasks(token, { workflowId, status, page })
      .then((data) => { if (id === requestId.current) { setItems(data.items); setTotal(data.total); } })
      .catch((cause: unknown) => { if (id === requestId.current) setError(errorText(cause)); })
      .finally(() => { if (id === requestId.current) setBusy(false); });
    return () => { requestId.current += 1; };
  }, [token, workflowId, status, page, revision]);
  useEffect(() => {
    if (!creating) return;
    let active = true;
    setStoresBusy(true); setStoreError(""); setStores([]);
    listTaskStores(token).then((data) => { if (active) setStores(data.items.filter((store) => store.active !== false)); })
      .catch((cause: unknown) => { if (active) setStoreError(errorText(cause)); })
      .finally(() => { if (active) setStoresBusy(false); });
    return () => { active = false; };
  }, [creating, token, storeRevision]);
  useEffect(() => {
    let active = true;
    setDetail(null); setDetailError("");
    if (!detailId) { setDetailBusy(false); return; }
    setDetailBusy(true);
    getBusinessTask(token, detailId).then((data) => { if (active) setDetail(data); })
      .catch((cause: unknown) => { if (active) setDetailError(errorText(cause)); })
      .finally(() => { if (active) setDetailBusy(false); });
    return () => { active = false; };
  }, [token, detailId, detailRevision]);
  const openCreate = () => {
    submission.current = null; setSaveError(""); form.resetFields();
    form.setFieldsValue({ workflow_id: workflowId || choices[0]?.id }); setCreating(true);
  };
  const create = async (values: TaskForm) => {
    if (savingRef.current) return;
    const lines = (value?: string) => (value || "").split("\n").map((line) => line.trim()).filter(Boolean);
    const input: BusinessTaskInput = {
      workflow_id: values.workflow_id, goal: values.goal.trim(),
      ...(values.store_id ? { store_id: values.store_id } : {}),
      expected_outputs: lines(values.expected_outputs), completion_criteria: lines(values.completion_criteria),
    };
    if ([input.expected_outputs!, input.completion_criteria!].some((entries) => entries.length > 20 || entries.some((entry) => entry.length > 500))) {
      setSaveError("交付物和完成条件各最多 20 条，每条不超过 500 字。"); return;
    }
    const body = JSON.stringify(input);
    if (submission.current?.body !== body) submission.current = { body, key: crypto.randomUUID() };
    const key = submission.current!.key;
    savingRef.current = true; setSaving(true); setSaveError("");
    try {
      const response = await createBusinessTask(token, input, key);
      if (!mounted.current) return;
      setCreating(false); setStatus(undefined); setPage(1); setRevision((value) => value + 1);
      setDetailId(response.item.id); void notice.success(response.message);
    } catch (cause) { if (mounted.current) setSaveError(errorText(cause)); }
    finally { savingRef.current = false; if (mounted.current) setSaving(false); }
  };
  return <>
    {messageContext}
    <Card className="businessTasks" title={workflowId ? "业务任务" : "我的业务任务"} extra={<Space wrap><Button icon={<ReloadOutlined />} loading={busy} onClick={() => setRevision((value) => value + 1)}>刷新任务</Button><Button type="primary" icon={<PlusOutlined />} disabled={!choices.length} onClick={openCreate}>登记任务</Button></Space>}>
      <Paragraph type="secondary">任务统一保存目标、店铺、交付物和执行证据。当前支持登记和查询；运行成功与业务完成分别记录。</Paragraph>
      <Space wrap className="businessTaskFilters"><Select aria-label="业务任务状态" placeholder="全部任务状态" allowClear value={status} onChange={(value) => { setStatus(value); setPage(1); }} options={Object.entries(states).map(([value, state]) => ({ value, label: state.label }))} /></Space>
      {error && <Alert type="error" showIcon message="业务任务加载失败" description={error} action={<Button onClick={() => setRevision((value) => value + 1)}>重试</Button>} />}
      <List loading={busy} dataSource={items} rowKey="id" locale={{ emptyText: <Empty description={error ? "任务数据暂不可用，请重试" : "暂无符合条件的业务任务"} /> }} renderItem={(item) => <List.Item className="businessTaskRow">
        <div className="businessTaskCopy"><Space wrap><Text strong>{item.title}</Text>{taskTag(item.status)}</Space><Paragraph className="agentRunPreview">{item.goal}</Paragraph><Text type="secondary">更新于 {time(item.updated_at)} · {item.store_id ? "已限定店铺" : "未限定店铺"}</Text></div>
        <Button onClick={() => setDetailId(item.id)}>任务详情</Button>
      </List.Item>} />
      {total > 10 && <Pagination className="businessTaskPagination" current={page} pageSize={10} total={total} onChange={setPage} showSizeChanger={false} size="small" />}
    </Card>
    <Modal title="登记业务任务" open={creating} onCancel={() => { if (!savingRef.current) setCreating(false); }} onOk={() => form.submit()} okText="保存任务" cancelText="取消" confirmLoading={saving} cancelButtonProps={{ disabled: saving }} closable={!saving} maskClosable={!saving} okButtonProps={{ disabled: storesBusy || Boolean(storeError) }}>
      <Alert type="info" showIcon message="保存后为已登记状态，不会自动执行或操作店铺。" />
      {saveError && <Alert type="error" showIcon message={saveError} />}
      {storeError && <Alert type="error" showIcon message="店铺授权加载失败，请重试" description={storeError} action={<Button onClick={() => setStoreRevision((value) => value + 1)}>重试店铺</Button>} />}
      <Form form={form} layout="vertical" onFinish={create} disabled={saving} className="businessTaskForm">
        <Form.Item name="workflow_id" label="负责 Agent" rules={[{ required: true, message: "请选择负责 Agent" }]}><Select disabled={Boolean(workflowId) || saving} options={choices.map((workflow) => ({ value: workflow.id, label: workflow.name }))} /></Form.Item>
        <Form.Item name="store_id" label="任务店铺" extra="仅展示已授权且启用的店铺；登记店铺不代表平台已连接。"><Select allowClear loading={storesBusy} placeholder="未限定店铺（仅登记）" options={stores.map((store) => ({ value: store.id, label: store.name + " · " + store.platform + " / " + store.marketplace }))} /></Form.Item>
        <Form.Item name="goal" label="任务目标" rules={[{ required: true, whitespace: true, message: "请填写任务目标" }]}><Input.TextArea rows={4} maxLength={4000} showCount placeholder="说明要处理的业务范围、问题和目标" /></Form.Item>
        <Form.Item name="expected_outputs" label="预期交付物" extra="每行一条；留空则采用 Agent 的默认交付说明。"><Input.TextArea rows={2} placeholder="例如：待审核的商品上架草稿" /></Form.Item>
        <Form.Item name="completion_criteria" label="完成条件" extra="每行一条，业务完成需要后续证据核验。"><Input.TextArea rows={2} placeholder="例如：人工复核通过，并取得平台结果回执" /></Form.Item>
      </Form>
    </Modal>
    <Drawer title="业务任务详情" open={Boolean(detailId)} onClose={() => setDetailId(null)} width="min(680px, 100vw)" extra={<Button onClick={() => setDetailRevision((value) => value + 1)} loading={detailBusy}>刷新详情</Button>}>
      {detailBusy && <Spin />}
      {detailError && <Alert type="error" showIcon message="任务详情加载失败" description={detailError} />}
      {detail && <div className="businessTaskDetail">
        <Space wrap><Title level={4}>{detail.item.title}</Title>{taskTag(detail.item.status)}</Space>
        <Paragraph className="agentBusinessText">{detail.item.goal}</Paragraph>
        <Descriptions column={1} size="small" items={[
          { key: "id", label: "任务编号", children: detail.item.id },
          { key: "store", label: "店铺范围", children: detail.store ? detail.store.name + " · " + detail.store.platform + " / " + detail.store.marketplace : "未限定店铺" },
          { key: "source", label: "任务来源", children: ({ manual: "手工登记", chat: "员工对话", event: "业务事件", schedule: "定时规则" } as Record<string, string>)[detail.item.source] || detail.item.source },
          { key: "updated", label: "最后更新", children: time(detail.item.updated_at) },
        ]} />
        <Title level={5}>预期交付物</Title><List size="small" dataSource={detail.item.expected_outputs} renderItem={(item) => <List.Item>{item}</List.Item>} />
        <Title level={5}>完成条件</Title>{detail.item.completion_criteria.length ? <List size="small" dataSource={detail.item.completion_criteria} renderItem={(item) => <List.Item>{item}</List.Item>} /> : <Text type="secondary">尚未填写完成条件，不能据此认定业务已完成。</Text>}
        <Alert type="info" showIcon message="执行与审核边界" description={detail.item.policy_snapshot.approval_policy + (detail.item.policy_snapshot.external_execution_enabled ? "" : " 当前任务尚未启用外部执行。")} />
        {detail.objects.length > 0 && <><Title level={5}>关联业务对象</Title><List size="small" dataSource={detail.objects} renderItem={(item) => <List.Item>{item.object_type} · {item.external_id}{item.line_id ? " / " + item.line_id : ""}</List.Item>} /></>}
        <Title level={5}>运行证据</Title>
        <Paragraph type="secondary">单次运行成功仅代表处理步骤完成；外部回执与业务验收另行核对。</Paragraph>
        <List dataSource={detail.runs} locale={{ emptyText: "暂无关联运行证据，任务尚未执行" }} renderItem={(run) => <List.Item><div className="businessTaskCopy"><Space wrap><Text strong>第 {run.attempt_number} 次 · {run.app_name}</Text><Tag>{runLabels[run.status] || run.status}</Tag></Space><Paragraph>{run.error_message || run.output_preview || "暂无结果摘要"}</Paragraph><Text type="secondary">{time(run.started_at)}</Text>{detail.steps.filter((step) => step.run_id === run.id).map((step) => <Paragraph key={step.id}>{step.step_order}. {step.step_name} · {runLabels[step.status] || step.status}{step.error_message ? " · " + step.error_message : ""}</Paragraph>)}</div></List.Item>} />
        <Title level={5}>产物记录</Title><List dataSource={detail.artifacts} locale={{ emptyText: "暂无产物" }} renderItem={(artifact) => <List.Item><div className="businessTaskCopy"><Text>{artifact.name}</Text><br /><Text type="secondary">{artifact.mime_type} · {artifact.size_bytes} 字节{artifact.expires_at ? " · 到期 " + time(artifact.expires_at) : ""}</Text></div></List.Item>} />
      </div>}
    </Drawer>
  </>;
}
