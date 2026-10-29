import { useEffect, useRef, useState } from "react";
import { Alert, Button, Card, Empty, Input, List, Select, Space, Spin, Tag, Typography } from "antd";
import { ArrowRightOutlined, CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined, ReloadOutlined, RobotOutlined } from "@ant-design/icons";
import { listAgentActivity, type AgentActivity, type AiWorkflowItem, type AgentReadiness } from "../api";
import { WorkspaceTabs, TrendChart, DistributionChart, chartColors } from "./WorkspaceCharts";
import { BusinessTasks } from "./BusinessTasks";
import "./agent-workspace.css";
import { FinanceReconciliationJobs } from './FinanceReconciliationJobs';

const { Title, Paragraph, Text } = Typography;
const statusLabels: Record<string, string> = { running: "执行中", succeeded: "处理完成", failed: "执行异常", blocked: "执行受阻" };
const statusColors: Record<string, string> = { running: "processing", succeeded: "success", failed: "error", blocked: "warning" };
const formatTime = (value: string | null) => value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "暂无记录";
const businessDescriptions: Record<string, string> = {
  operations_listing_launch: "根据商品资料准备 Listing、标题、卖点和搜索词，形成待审核的上架草稿。",
  operations_competitor_analysis: "一键比较自家商品与模拟热点竞品价格，每天 08:00、11:00、14:00、16:00 自动巡检。",
  customer_service_refund_reply: "结合订单和售后政策准备处理建议，高风险动作进入审批。",
  customer_service_logistics_reply: "结合订单、物流和知识库准备客户回复，跟踪需要升级的异常。",
  customer_service_message_loop: "接收客户消息，识别意图与风险、获取业务上下文，生成回复草稿并按规则转人工。",
  finance_report_analysis: "根据报表期间和业务指标生成分析摘要、异常提示与复核建议。",
  finance_salary_summary: "汇总授权范围内的工资数据，生成可核对的业务文件。",
  finance_salary_wechat_send: "准备工资文件与发送资料，最终发送保留人工确认。",
  finance_monthly_package_wechat_send: "整理月度报表和工资资料，合并业务文件并准备发送。",
  finance_excel_settlement: "处理财务表格并形成汇总文件，数据来源接入后再启用自动任务。",
  finance_reconciliation: "核对结算、采购、物流、广告与汇率数据，输出利润和异常账单。",
};

export function AgentWorkspace({ token, role, workflows, selectedWorkflowId, loading, refreshWorkflows, openTechnicalDetail, onOpenWorkflow, onNavigate }: {
  token: string; role: "admin" | "employee"; workflows: AiWorkflowItem[]; selectedWorkflowId: string | null;
  loading: boolean; refreshWorkflows: () => void; openTechnicalDetail: (id: string) => void;
  onOpenWorkflow: (id: string) => void; onNavigate: (view: string) => void;
}) {
  const [activity, setActivity] = useState<AgentActivity | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState("all");
  const [visibleCount, setVisibleCount] = useState(6);
  const requestId = useRef(0);
  useEffect(() => {
    const id = ++requestId.current;
    setBusy(true);
    setError("");
    if (!token) { setBusy(false); return; }
    listAgentActivity(token, selectedWorkflowId || undefined, status || undefined)
      .then((data) => { if (id === requestId.current) setActivity(data); })
      .catch((cause: unknown) => { if (id === requestId.current) setError(cause instanceof Error ? cause.message : "执行数据加载失败"); })
      .finally(() => { if (id === requestId.current) setBusy(false); });
    return () => { requestId.current += 1; };
  }, [token, selectedWorkflowId, status, revision]);
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible" && token) setRevision((value) => value + 1);
    }, 15000);
    return () => window.clearInterval(interval);
  }, [token]);
  useEffect(() => setVisibleCount(6), [search, position]);
  const selected = workflows.find((item) => item.id === selectedWorkflowId);
  const readiness = activity?.agents.find((item) => item.id === selectedWorkflowId)?.readiness;
  const filtered = workflows.filter((item) => (position === "all" || item.position === position) &&
    (item.name + item.scenario + item.category).toLowerCase().includes(search.trim().toLowerCase()));
  const refresh = () => { refreshWorkflows(); setRevision((value) => value + 1); };
  const selectStatus = (value: string) => {
    setStatus(status === value ? "" : value);
    const url = new URL(window.location.href);
    url.searchParams.set(selectedWorkflowId ? "agent_tab" : "agent_center_tab", selectedWorkflowId ? "records" : "activity");
    window.history.replaceState(window.history.state, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  const resultsView = selected?.position === "customer_service" ? "customer_service_inbox" :
    selected?.position === "operations" ? "platform_draft_review" : "file_downloads";
  const readinessTag = (value?: AgentReadiness) => <Tag color={value && value.state !== "requires_source" ? "blue" : "gold"}>{value?.label || "接入状态待确认"}</Tag>;
  const metric = (key: keyof AgentActivity["summary"]) => activity ? activity.summary[key] : "—";
  const recent = activity?.recent || [];
  const resultItems = recent.filter((item) => Boolean(item.output));
  const timeline = activity ? Array.from({ length: 7 }, (_, index) => {
    const now = new Date(new Date(activity.as_of).getTime() + 8 * 3600000);
    now.setUTCDate(now.getUTCDate() - 6 + index);
    const date = now.toISOString().slice(0, 10);
    const bucket = activity.trend.find((item) => item.date === date);
    return { label: date, shortLabel: date.slice(5), timestamp: Date.parse(date + "T00:00:00Z"), values: { total: bucket?.total || 0, failed: bucket?.failed || 0 } };
  }) : [];
  const runs = (
    <Card title="最近执行记录" extra={<Text type="secondary">最多展示最近 20 条</Text>}>
      <Space wrap className="agentRecordFilters">
        <Select aria-label="执行状态" value={status} onChange={setStatus} options={[
          { value: "", label: "全部状态" }, ...Object.entries(statusLabels).map(([value, label]) => ({ value, label })),
        ]} />
        {role === "admin" && <Button onClick={() => onNavigate("run_records")}>完整运行记录</Button>}
      </Space>
      <List loading={busy} pagination={{ pageSize: 5, hideOnSinglePage: true, size: "small" }} dataSource={recent} locale={{ emptyText: <Empty description={error ? "执行记录暂不可用，请重试" : "暂无符合条件的执行记录"} /> }} renderItem={(item) => (
        <List.Item className="agentRunItem">
          <div className="agentRunContent"><Space wrap><Text strong>{item.name}</Text><Tag color={statusColors[item.status]}>{statusLabels[item.status] || item.status}</Tag></Space>
            <Paragraph className="agentRunPreview">{item.error || item.output || "任务尚未产生业务结果"}</Paragraph>
            <Text type="secondary">开始于 {formatTime(item.started_at)}</Text>
          </div>
        </List.Item>
      )} />
    </Card>
  );
  const results = (
    <Card title="业务成果" extra={<Button onClick={() => onNavigate(resultsView)}>查看业务结果 <ArrowRightOutlined /></Button>}>
      <Paragraph type="secondary">执行成功表示该处理步骤完成；草稿待审核、审批通过和外部发布完成是不同状态，请以业务结果页为准。</Paragraph>
      <List loading={busy} pagination={{ pageSize: 5, hideOnSinglePage: true, size: "small" }} dataSource={resultItems} locale={{ emptyText: <Empty description={error ? "成果数据暂不可用" : "最近执行中暂无成果摘要"} /> }} renderItem={(item) => (
        <List.Item><div className="agentResultContent"><Space wrap><Text strong>{item.name}</Text><Tag color={statusColors[item.status]}>{statusLabels[item.status] || item.status}</Tag></Space><Paragraph className="agentResultText">{item.output}</Paragraph><Text type="secondary">{formatTime(item.finished_at || item.started_at)}</Text></div></List.Item>
      )} />
    </Card>
  );

  return <Space direction="vertical" size={20} className="pageStack agentWorkspace">
    <div className="agentHero">
      <div className="agentHeroCopy">
        <Space wrap><span className="agentEyebrow"><RobotOutlined /> AGENT WORKSPACE</span>{selected && readinessTag(readiness)}</Space>
        <Title level={2}>{selected?.name || (selectedWorkflowId ? "Agent 详情" : "让任务自动推进，让结果清晰可见")}</Title>
        <Paragraph>{selected ? businessDescriptions[selected.id] || selected.business_value : "集中查看业务 Agent、真实执行记录与待处理事项。数据源和事件接入完成后，由业务事件触发任务。"}</Paragraph>
      </div>
      <Space wrap className="agentHeroActions"><Button icon={<ReloadOutlined />} loading={busy || loading} onClick={refresh}>刷新状态</Button>{selectedWorkflowId && <Button onClick={() => onNavigate("ai_workflows")}>全部 Agent</Button>}</Space>
    </div>
    {error && <Alert type="error" showIcon message="执行数据暂不可用" description={error} action={<Button onClick={refresh}>重试</Button>} />}
    <div className="agentMetricGrid" aria-label="授权范围内的任务统计">
      {[
        { key: "running" as const, label: "执行中", icon: <ClockCircleOutlined />, color: "blue" },
        { key: "succeeded" as const, label: "处理完成", icon: <CheckCircleOutlined />, color: "green" },
        { key: "failed" as const, label: "执行异常", icon: <ExclamationCircleOutlined />, color: "red" },
        { key: "blocked" as const, label: "执行受阻", icon: <ExclamationCircleOutlined />, color: "amber" },
      ].map((item) => <button type="button" key={item.key} className={"agentMetric agentMetric-" + item.color} aria-pressed={status === item.key} onClick={() => selectStatus(item.key)}><span>{item.icon} {item.label}</span><strong>{metric(item.key)}</strong><small>点击筛选执行记录</small></button>)}
    </div>
    {activity && <Text type="secondary">{activity.scope} · 统计覆盖全部历史 · 更新于 {formatTime(activity.as_of)}</Text>}
    {selectedWorkflowId ? selected ? <WorkspaceTabs storageKey="agent_tab" items={[
      { key: "overview", label: "任务概况", children: <div className="agentMainGrid"><Space direction="vertical" className="pageStack">
        <Card title="任务如何推进"><div className="agentFlowSteps">{["业务事件", "获取授权数据", "Agent 处理", "审核与回写"].map((label, index) => <div key={label}><span>{index + 1}</span><Text strong>{label}</Text></div>)}</div><Alert type={readiness && readiness.state !== "requires_source" ? "info" : "warning"} showIcon message={readiness?.label || "接入状态待确认"} description={readiness?.description || "正在核对数据源与触发能力，暂不表示 Agent 已启用。"} /></Card>
        <Card title="任务交付"><Paragraph className="agentBusinessText">{selected.output_contract}</Paragraph><div className="agentPolicy"><Text strong>审核边界</Text><Paragraph>{selected.approval_policy}</Paragraph></div></Card>
        {runs}
      </Space><Space direction="vertical" className="pageStack">
        <Card title="触发与接入"><div className="agentInfoPair"><Text type="secondary">业务范围</Text><Text strong>{selected.position_label} · {selected.category}</Text></div><div className="agentInfoPair"><Text type="secondary">触发来源</Text><Text strong>{readiness?.trigger_label || "待确认"}</Text></div><div className="agentInfoPair"><Text type="secondary">运行计划</Text><Text>尚无已验证的定时规则</Text></div><Text type="secondary">事件入口可用并不代表外部渠道已持续投递，接入前不会自动启动任务。</Text></Card>
        <Card title="需要你关注"><Paragraph>{selected.requires_approval ? "涉及高风险操作时，Agent 将等待审批。审批数量请以实际业务待办为准。" : "出现资料缺失或执行异常时再介入；已有草稿仍须按业务规则审核。"}</Paragraph><Button block onClick={() => onNavigate(resultsView)}>查看结果与待办 <ArrowRightOutlined /></Button></Card>
      </Space></div> },
      ...(selected.id === 'finance_reconciliation' ? [{ key: 'jobs', label: '对账任务', children: <FinanceReconciliationJobs key={token} token={token} /> }] : []),
      { key: "records", label: "执行记录", children: runs },
      { key: "tasks", label: "业务任务", children: <BusinessTasks key={token + selected.id} token={token} workflows={workflows} workflowId={selected.id} /> },
      { key: "results", label: "业务成果", children: results },
      { key: "rules", label: "自动化规则", children: <Card title="触发规则与执行边界"><Alert showIcon type="info" message="当前为接入信息与规则说明" description="尚未实现的自动监听或定时规则不会显示为已启用。管理员需要完成数据源、字段映射和事件验证后才能启用对应能力。" /><div className="agentRuleGrid"><div><Title level={5}>接入条件</Title>{busy ? <Spin /> : error ? <Text type="danger">接入条件加载失败，请重试</Text> : <List dataSource={readiness?.requirements || []} renderItem={(item) => <List.Item>{item}</List.Item>} />}</div><div><Title level={5}>执行约束</Title><Paragraph>{selected.approval_policy}</Paragraph><Text type="secondary">岗位与应用授权继续限制数据访问和业务动作。</Text></div></div>{role === "admin" && <Space wrap><Button onClick={() => onNavigate("connectors")}>检查连接配置</Button><Button onClick={() => onNavigate("automation_flows")}>流程治理</Button><Button onClick={() => openTechnicalDetail(selected.id)}>技术详情</Button></Space>}</Card> },
    ]} defaultKey={selected.id === 'finance_reconciliation' ? 'jobs' : undefined} /> : <Card><Empty description={loading ? "正在加载 Agent" : "Agent 不存在或当前账号无权访问"} /></Card> : <WorkspaceTabs storageKey="agent_center_tab" items={[
      { key: "agents", label: "业务 Agent", children: <Space direction="vertical" className="pageStack">
        <div className="agentCatalogFilters"><Input.Search aria-label="搜索 Agent" allowClear placeholder="搜索任务名称或业务场景" value={search} onChange={(event) => setSearch(event.target.value)} />{role === "admin" && <Select aria-label="业务范围" value={position} onChange={setPosition} options={[{ value: "all", label: "全部业务" }, { value: "operations", label: "运营" }, { value: "customer_service", label: "客服" }, { value: "finance", label: "财务" }]} />}</div>
        <div className="agentCatalogGrid">{filtered.slice(0, visibleCount).map((workflow) => { const state = activity?.agents.find((item) => item.id === workflow.id)?.readiness; return <Card key={workflow.id} className="agentCatalogCard"><div className="agentCatalogIcon"><RobotOutlined /></div><Space wrap><Tag>{workflow.position_label}</Tag>{readinessTag(state)}</Space><Title level={4}>{workflow.name}</Title><Paragraph className="agentCatalogDescription">{businessDescriptions[workflow.id] || workflow.business_value}</Paragraph><div className="agentCatalogFooter"><Text type="secondary">{workflow.requires_approval ? "含人工审核环节" : "按业务规则审核"}</Text><Button type="link" onClick={() => onOpenWorkflow(workflow.id)}>查看任务 <ArrowRightOutlined /></Button></div></Card>; })}</div>
        {!filtered.length && <Empty description={loading ? "正在加载 Agent" : "没有匹配的 Agent"} />}
        {filtered.length > visibleCount && <Button onClick={() => setVisibleCount((value) => value + 6)}>查看更多 Agent</Button>}
      </Space> },
      { key: "tasks", label: "我的任务", children: <BusinessTasks key={token} token={token} workflows={workflows} /> },
      { key: "activity", label: "执行概览", children: <Space direction="vertical" className="pageStack"><div className="agentChartGrid"><Card title="近 7 天执行趋势" extra={<Text type="secondary">北京时间</Text>}>{activity?.trend.length ? <TrendChart data={timeline} label="Agent 执行趋势" series={[{ key: "total", label: "执行总数", color: chartColors.blue }, { key: "failed", label: "异常", color: chartColors.red }]} /> : <Empty description={busy ? "正在加载" : "近 7 天暂无执行数据"} />}</Card><Card title="历史状态分布">{activity ? <DistributionChart label="Agent 执行状态分布" items={Object.entries(statusLabels).map(([key, label]) => ({ key, label, value: activity.summary[key as keyof AgentActivity["summary"]], color: ({ running: chartColors.blue, succeeded: chartColors.green, failed: chartColors.red, blocked: chartColors.amber })[key] || chartColors.gray }))} /> : <Empty description={error ? "统计暂不可用" : "正在加载"} />}</Card></div>{runs}</Space> },
    ]} />}
  </Space>;
}
