import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Input, Select, Space, Table, Tag, Typography, Upload, message } from 'antd';
import { DownloadOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { downloadGeneratedFile, isAuthExpiredError, listBackgroundJobs, submitFinanceReconciliationJob, type BackgroundJob } from '../api';

const labels = { queued: '排队中', running: '处理中', succeeded: '已完成', failed: '失败' };
const colors = { queued: 'default', running: 'processing', succeeded: 'success', failed: 'error' };
const failures: Record<string, string> = { permission_changed: '执行前岗位或应用权限已变化，请联系管理员', attempts_exhausted: '恢复次数已达上限，请核对后重新提交' };

function jobStatusDetail(job: BackgroundJob) {
  if (job.status === 'failed') {
    if (job.error_code?.startsWith('attempts_exhausted')) return '临时故障重试次数已达上限，请核对后重新提交';
    return failures[job.error_code || ''] || '处理失败，请检查文件内容后重新提交';
  }
  if (job.status === 'queued' && job.error_code?.startsWith('temporary_') && job.next_attempt_at) {
    return `临时故障，已完成 ${job.attempt_count}/${job.max_attempts} 次尝试；预计 ${new Date(job.next_attempt_at).toLocaleString('zh-CN', { hour12: false })} 重试`;
  }
  return job.status === 'queued' ? '等待后台处理，可离开页面' : '正在处理，可离开页面';
}

export function FinanceReconciliationJobs({ token }: { token: string }) {
  const [files, setFiles] = useState<File[]>([]);
  const [instruction, setInstruction] = useState('按订单号和 SKU 匹配结算、采购、物流、广告与汇率数据，生成利润表并标记异常。');
  const [currency, setCurrency] = useState('CNY');
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [downloading, setDownloading] = useState('');
  const [revision, setRevision] = useState(0);
  const submission = useRef<{ fingerprint: string; key: string } | null>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    setLoading(true);
    async function refresh() {
      try {
        const response = await listBackgroundJobs(token, controller.signal);
        if (controller.signal.aborted) return;
        setJobs(response.items);
        setError('');
        failures = 0;
      } catch (cause) {
        if (controller.signal.aborted || isAuthExpiredError(cause)) return;
        failures += 1;
        setError(cause instanceof Error ? cause.message : '任务状态暂不可用');
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          timer = setTimeout(refresh, Math.min(30000, 3000 * 2 ** failures));
        }
      }
    }
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [token, revision]);

  async function submit() {
    if (submittingRef.current) return;
    if (!files.length) { message.warning('请选择对账 Excel 文件'); return; }
    if (files.length > 8 || files.some((file) => !/\.xlsx?$/i.test(file.name) || file.size === 0 || file.size > 8 * 1024 * 1024) ||
        files.reduce((total, file) => total + file.size, 0) > 32 * 1024 * 1024) {
      message.warning('限 1–8 个 xlsx/xls，单文件不超过 8 MiB，总计不超过 32 MiB，文件不能为空'); return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    setError('');
    try {
      // Reuse the key after uncertain network outcomes, but bind it to actual bytes.
      const hashes = await Promise.all(files.map(async (file) => {
        const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
        return { name: file.name, hash: Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('') };
      }));
      const fingerprint = JSON.stringify([hashes, instruction.trim(), currency]);
      if (submission.current?.fingerprint !== fingerprint) submission.current = { fingerprint, key: crypto.randomUUID() };
      await submitFinanceReconciliationJob(token, files, instruction, currency, submission.current.key);
      submission.current = null;
      setFiles([]);
      setRevision((value) => value + 1);
      message.success('任务已保存，可离开页面后继续查看');
    } catch (cause) {
      if (!isAuthExpiredError(cause)) setError(cause instanceof Error ? cause.message : '提交失败，请重试');
    } finally { submittingRef.current = false; setSubmitting(false); }
  }

  async function download(job: BackgroundJob) {
    if (!job.result.artifact_id) return;
    setDownloading(job.id);
    try {
      const result = await downloadGeneratedFile(token, job.result.artifact_id);
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = url; link.download = result.filename; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) {
      if (!isAuthExpiredError(cause)) setError(cause instanceof Error ? cause.message : '下载失败');
    } finally { setDownloading(''); }
  }

  return <Space direction="vertical" className="pageStack" data-testid="finance-background-jobs">
    <Card title="提交财务对账">
      <Space direction="vertical" className="pageStack">
        <Typography.Text type="secondary">上传后交由后台处理；离开、刷新或重新登录后，可在此查看本人任务。最近 50 条任务按待处理优先展示，结果下载需在文件有效期内完成。</Typography.Text>
        <Upload accept=".xlsx,.xls" multiple disabled={submitting} beforeUpload={() => false}
          fileList={files.map((file, index) => ({ uid: String(index), name: file.name, originFileObj: file as never }))}
          onChange={({ fileList }) => setFiles(fileList.flatMap((file) => file.originFileObj ? [file.originFileObj] : []))}>
          <Button icon={<UploadOutlined />} disabled={submitting}>选择对账文件</Button>
        </Upload>
        <Input.TextArea aria-label="对账要求" value={instruction} maxLength={4000} rows={3} disabled={submitting} onChange={(event) => setInstruction(event.target.value)} />
        <Space wrap><Select aria-label="本位币" value={currency} disabled={submitting} onChange={setCurrency} options={['CNY', 'USD', 'EUR', 'GBP', 'JPY'].map((value) => ({ value, label: value }))} />
          <Button type="primary" loading={submitting} onClick={() => void submit()}>提交后台对账</Button></Space>
      </Space>
    </Card>
    {error && <Alert type="error" showIcon message="任务服务暂不可用" description={error} action={<Button onClick={() => setRevision((value) => value + 1)}>重试加载</Button>} />}
    <Card title="我的对账任务" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => setRevision((value) => value + 1)}>刷新任务</Button>}>
      <Table<BackgroundJob> rowKey="id" dataSource={jobs} loading={loading} scroll={{ x: 760 }} pagination={{ pageSize: 8, hideOnSinglePage: true }} locale={{ emptyText: '暂无对账任务' }} columns={[
        { title: '任务', key: 'id', render: (_, job) => <Typography.Text copyable={{ text: job.id }}>{job.id.slice(0, 8)}</Typography.Text> },
        { title: '提交时间', dataIndex: 'created_at', render: (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false }) },
        { title: '状态', key: 'status', render: (_, job) => <Tag color={colors[job.status]}>{labels[job.status]}</Tag> },
        { title: '处理结果', key: 'result', render: (_, job) => job.status === 'succeeded' ?
          <Button icon={<DownloadOutlined />} loading={downloading === job.id} disabled={!job.result.artifact_id} onClick={() => void download(job)}>下载对账结果</Button> :
          job.status === 'failed' ? <Typography.Text type="danger">{jobStatusDetail(job)}</Typography.Text> :
          <Typography.Text type="secondary">{jobStatusDetail(job)}</Typography.Text> },
      ]} />
    </Card>
  </Space>;
}
