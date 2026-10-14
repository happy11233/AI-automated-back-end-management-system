import React, { useEffect, useState } from "react";
import {
  EyeOutlined,
  ReloadOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import { ProCard } from "@ant-design/pro-components";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Modal,
  Progress,
  Row,
  Space,
  Table,
  Tag,
  Timeline,
  Typography,
  message,
} from "antd";
import {
  getMonitoringCenterAiopsIncident,
  getMonitoringLiveMetrics,
  repairMonitoringCenterAiopsIncident,
  type MonitoringAiopsIncidentDetailResponse,
  type MonitoringAiopsIncidentItem,
  type MonitoringAiopsIntegration,
  type MonitoringLiveMetrics,
} from "../api";

const { Text, Paragraph, Title } = Typography;

type Props = {
  token: string;
  active: boolean;
  data: MonitoringAiopsIntegration | null | undefined;
  loading: boolean;
  refreshMonitoringCenter: () => void;
};

export function MonitoringAiopsPanel({
  token,
  active,
  data,
  loading,
  refreshMonitoringCenter,
}: Props) {
  const [detail, setDetail] = useState<MonitoringAiopsIncidentDetailResponse | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [repairingIncidentId, setRepairingIncidentId] = useState("");
  const [live, setLive] = useState<MonitoringLiveMetrics | null>(null);
  const [liveError, setLiveError] = useState("");
  const summary = data?.summary;
  const incidents = data?.incidents || [];
  const pollMinutes = Math.max(1, Math.round((summary?.poll_interval_seconds || 300) / 60));

  useEffect(() => {
    if (!token || !active) return;
    let mounted = true;
    let pending = false;
    const load = async () => {
      if (pending) return;
      pending = true;
      try {
        const result = await getMonitoringLiveMetrics(token);
        if (mounted) {
          setLive(result);
          setLiveError("");
        }
      } catch (error) {
        if (mounted) setLiveError(error instanceof Error ? error.message : "实时指标读取失败");
      } finally {
        pending = false;
      }
    };
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [token, active]);

  async function openDetail(record: MonitoringAiopsIncidentItem) {
    if (!token) {
      message.warning("请先登录管理员账号");
      return;
    }
    setIsDetailOpen(true);
    setIsDetailLoading(true);
    try {
      setDetail(await getMonitoringCenterAiopsIncident(token, record.incident_id));
    } catch (error) {
      const text = error instanceof Error ? error.message : "AIOps 事故详情加载失败";
      message.error(text);
    } finally {
      setIsDetailLoading(false);
    }
  }

  function confirmRepair(record: MonitoringAiopsIncidentItem) {
    if (!record.repair_available) {
      message.warning(record.repair_reason || "当前问题暂不可修复");
      return;
    }

    Modal.confirm({
      title: `确认修复 ${record.service || record.incident_id}？`,
      content: (
        <Space direction="vertical" size={8}>
          <Text>{record.summary || record.title}</Text>
          <Text type="secondary">AIOps 会执行预检、管理员审批记录、真实修复和恢复验证。</Text>
        </Space>
      ),
      okText: "确认修复",
      cancelText: "取消",
      onOk: () => handleRepair(record),
    });
  }

  async function handleRepair(record: MonitoringAiopsIncidentItem) {
    if (!token) {
      message.warning("请先登录管理员账号");
      return;
    }

    setRepairingIncidentId(record.incident_id);
    try {
      const result = await repairMonitoringCenterAiopsIncident(
        token,
        record.incident_id,
        `管理员在监控中心确认 AI 修复: ${record.service || record.incident_id}`,
      );
      const runStatus = readString(result.run, "status");
      if (runStatus === "passed") {
        message.success("AIOps 修复验证通过");
      } else {
        message.warning(`AIOps 修复结果: ${runStatus || "unknown"}`);
      }
      setDetail(result.detail);
      setIsDetailOpen(true);
      refreshMonitoringCenter();
    } catch (error) {
      const text = error instanceof Error ? error.message : "AIOps 修复失败";
      message.error(text);
    } finally {
      setRepairingIncidentId("");
    }
  }

  return (
    <Space direction="vertical" size={12} className="pageStack">
      <Alert
        type={statusAlertType(data?.status || "disconnected")}
        showIcon
        message={`AIOps 运维状态：${statusLabel(data?.status || "disconnected")}`}
        description={
          data?.reachable
            ? `已接入独立 AIOps 服务，平台每 ${pollMinutes} 分钟轮询一次。管理员可查看问题详细，并在二次确认后执行 AI 修复。`
            : data?.message || "AIOps 服务暂未连接，无法读取巡检与事故状态。"
        }
        action={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshMonitoringCenter} loading={loading}>
            刷新
          </Button>
        }
      />

      <div className="aiopsLiveHeader">
        <Space size={8} wrap>
          <Text strong>实时资源</Text>
          <Tag color={liveError ? "red" : live ? "green" : "default"}>
            {liveError ? "采集失败" : live ? "实时采集" : "连接中"}
          </Tag>
          <Text type="secondary">5 秒刷新 · {live ? formatTime(live.checked_at) : "-"}</Text>
        </Space>
        {liveError && <Text type="danger">{liveError}</Text>}
      </div>

      <Row gutter={[12, 12]} className="aiopsLiveGrid">
        <Col xs={24} lg={12}>
          <Card size="small" title="服务器资源" extra={<Text type="secondary">{live?.host.source || "-"}</Text>}>
            <ResourceMeter label="CPU" percent={live?.host.cpu_percent} />
            <ResourceMeter label="内存" percent={live?.host.memory_percent} detail={formatBytesPair(live?.host.memory_used_bytes, live?.host.memory_total_bytes)} />
            <ResourceMeter label="磁盘" percent={live?.host.disk_percent} detail={formatBytesPair(live?.host.disk_used_bytes, live?.host.disk_total_bytes)} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title="平台 API 容器" extra={<Text type="secondary">{live?.api_container.source || "-"}</Text>}>
            <ResourceMeter label="CPU" percent={live?.api_container.cpu_percent} />
            <ResourceMeter label="内存" percent={live?.api_container.memory_percent} detail={formatBytesPair(live?.api_container.memory_used_bytes, live?.api_container.memory_total_bytes)} />
            <div className="aiopsServiceSignals">
              <span>PostgreSQL <Tag color={!live ? "default" : live.database.status === "ok" ? "green" : "red"}>{!live ? "采集中" : live.database.status === "ok" ? "正常" : "不可用"}</Tag> {live?.database.connections ?? "-"} 连接 · {formatMilliseconds(live?.database.latency_ms)}</span>
              <span>AIOps <Tag color={!live ? "default" : live.aiops.status === "ok" ? "green" : "red"}>{!live ? "采集中" : live.aiops.status === "ok" ? "正常" : "不可用"}</Tag> {formatMilliseconds(live?.aiops.latency_ms)}</span>
            </div>
          </Card>
        </Col>
      </Row>

      <ProCard title="功能调用指标" bordered className="monitoringPanelCard">
        <Table
          rowKey="key"
          size="small"
          pagination={false}
          dataSource={live?.features || []}
          scroll={{ x: 600 }}
          locale={{ emptyText: <Empty description="正在采集功能指标" /> }}
          columns={[
            { title: "功能", dataIndex: "label" },
            { title: "近 1 分钟请求", dataIndex: "requests_1m", width: 130 },
            { title: "服务端错误", dataIndex: "errors_1m", width: 110, render: (value: number) => <Tag color={value ? "red" : "default"}>{value}</Tag> },
            { title: "平均耗时", dataIndex: "avg_latency_ms", width: 120, render: (value: number | null) => formatMilliseconds(value) },
            { title: "P95 耗时", dataIndex: "p95_latency_ms", width: 120, render: (value: number | null) => formatMilliseconds(value) },
          ]}
        />
      </ProCard>

      <Row gutter={[12, 12]} className="monitoringMetricRow">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">开放事故</Text>
            <Title level={3}>{summary?.open_incident_count ?? 0}</Title>
            <Text type="secondary">当前待处理问题</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">严重事故</Text>
            <Title level={3}>{summary?.critical_open_incident_count ?? 0}</Title>
            <Text type="secondary">critical open</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">待修复</Text>
            <Title level={3}>{summary?.action_required_count ?? 0}</Title>
            <Text type="secondary">{summary?.repairable_count ?? 0} 个可直接修复</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">服务目标</Text>
            <Title level={3}>{summary?.enabled_service_target_count ?? 0}</Title>
            <Text type="secondary">{summary?.service_target_count ?? 0} 个已注册</Text>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="AIOps 事故列表"
        bordered
        className="monitoringPanelCard"
        extra={
          <Space size={8} wrap>
            <Tag color={statusColor(data?.status || "disconnected")}>
              {statusLabel(data?.status || "disconnected")}
            </Tag>
            <Text type="secondary">存储：{summary?.storage_backend || "-"}</Text>
            <Text type="secondary">最近事故：{formatTime(summary?.last_incident_at || "")}</Text>
          </Space>
        }
      >
        <Table
          rowKey="incident_id"
          size="small"
          loading={loading}
          dataSource={incidents}
          pagination={{ pageSize: 6, hideOnSinglePage: true }}
          scroll={{ x: 980 }}
          locale={{ emptyText: <Empty description="暂无开放事故" /> }}
          columns={[
            {
              title: "级别",
              dataIndex: "severity",
              width: 90,
              render: (value, record) => (
                <Tag color={severityColor(String(value || ""))}>
                  {record.severity_label || String(value || "-")}
                </Tag>
              ),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              render: (value, record) => (
                <Tag color={statusColor(String(value || ""))}>
                  {record.status_label || statusLabel(String(value || "-"))}
                </Tag>
              ),
            },
            {
              title: "服务",
              dataIndex: "service",
              width: 180,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="monitoringCellStack">
                  <Text strong className="monitoringText">{String(value || "-")}</Text>
                  <Text type="secondary" className="monitoringText">{record.environment || record.namespace || "-"}</Text>
                </Space>
              ),
            },
            {
              title: "问题",
              dataIndex: "summary",
              render: (value, record) => (
                <Space direction="vertical" size={2} className="monitoringCellStack">
                  <Text strong className="monitoringText">{record.title || record.alert_type_label || record.alert_type}</Text>
                  <Text type="secondary" className="monitoringText">{String(value || record.root_cause || "-")}</Text>
                </Space>
              ),
            },
            {
              title: "阶段",
              dataIndex: "current_stage",
              width: 140,
              render: (value, record) => (
                <Tag color="blue">{record.current_stage_label || String(value || "-")}</Tag>
              ),
            },
            {
              title: "证据/动作",
              width: 110,
              render: (_, record) => (
                <Text type="secondary">
                  {record.evidence_count} / {record.action_count}
                </Text>
              ),
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 170,
              render: (value) => <Text type="secondary">{formatTime(String(value || ""))}</Text>,
            },
            {
              title: "操作",
              width: 190,
              fixed: "right",
              render: (_, record) => (
                <Space size={6} wrap>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(record)}>
                    问题详细
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    icon={<ToolOutlined />}
                    disabled={!record.repair_available}
                    loading={repairingIncidentId === record.incident_id}
                    onClick={() => confirmRepair(record)}
                  >
                    AI 修复
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </ProCard>

      <Drawer
        width={820}
        title={detail?.card?.title || "AIOps 事故详情"}
        open={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        extra={
          detail?.card?.repair_available ? (
            <Button
              type="primary"
              icon={<ToolOutlined />}
              loading={repairingIncidentId === detail.card.incident_id}
              onClick={() => confirmRepair(detail.card)}
            >
              AI 修复
            </Button>
          ) : null
        }
      >
        {isDetailLoading ? (
          <Empty description="加载中" />
        ) : detail ? (
          <IncidentDetail detail={detail} />
        ) : (
          <Empty description="请选择事故" />
        )}
      </Drawer>
    </Space>
  );
}

function ResourceMeter({ label, percent, detail }: { label: string; percent?: number | null; detail?: string }) {
  const value = typeof percent === "number" ? Math.max(0, Math.min(100, percent)) : null;
  return (
    <div className="aiopsResourceMeter">
      <div className="aiopsResourceLabel">
        <Text>{label}</Text>
        <Text strong>{value === null ? "-" : `${value.toFixed(1)}%`}</Text>
      </div>
      <Progress percent={value ?? 0} showInfo={false} strokeColor={value !== null && value >= 85 ? "#cf3f3f" : value !== null && value >= 70 ? "#d48a28" : "#27826a"} />
      {detail && <Text type="secondary" className="aiopsResourceDetail">{detail}</Text>}
    </div>
  );
}

function formatBytesPair(used?: number | null, total?: number | null) {
  return `${formatBytes(used)} / ${formatBytes(total)}`;
}

function formatBytes(value?: number | null) {
  if (typeof value !== "number") return "-";
  const unit = value >= 1024 ** 3 ? "GB" : "MB";
  const divisor = unit === "GB" ? 1024 ** 3 : 1024 ** 2;
  return `${(value / divisor).toFixed(1)} ${unit}`;
}

function formatMilliseconds(value?: number | null) {
  return typeof value === "number" ? `${value.toFixed(1)} ms` : "-";
}

function IncidentDetail({ detail }: { detail: MonitoringAiopsIncidentDetailResponse }) {
  const card = detail.card;
  const diagnosis = detail.diagnosis || {};
  return (
    <Space direction="vertical" size={12} className="pageStack">
      <Descriptions size="small" bordered column={1}>
        <Descriptions.Item label="服务">{card.service || "-"}</Descriptions.Item>
        <Descriptions.Item label="环境">{card.environment || "-"}</Descriptions.Item>
        <Descriptions.Item label="命名空间">{card.namespace || "-"}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusColor(card.status)}>{card.status_label || card.status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="影响">{card.impact || "-"}</Descriptions.Item>
        <Descriptions.Item label="建议">{card.recommendation || "-"}</Descriptions.Item>
      </Descriptions>

      <ProCard title="诊断" bordered size="small">
        <Paragraph className="monitoringText">
          {readString(diagnosis, "root_cause") || card.root_cause || "-"}
        </Paragraph>
        <Text type="secondary">
          置信度 {formatPercent(readNumber(diagnosis, "confidence"))}
        </Text>
      </ProCard>

      <ProCard title="修复建议" bordered size="small">
        <Table
          rowKey={(record) => readString(record, "id") || readString(record, "action_id")}
          size="small"
          dataSource={detail.remediation_actions || []}
          pagination={false}
          scroll={{ x: 760 }}
          locale={{ emptyText: <Empty description="暂无修复建议" /> }}
          columns={[
            { title: "动作", dataIndex: "action_type", width: 150, render: (value) => String(value || "-") },
            { title: "风险", dataIndex: "risk", width: 88, render: (value) => <Tag color={riskColor(String(value || ""))}>{String(value || "-")}</Tag> },
            { title: "状态", dataIndex: "status", width: 118, render: (value) => <Tag color={statusColor(String(value || ""))}>{String(value || "-")}</Tag> },
            { title: "命令", dataIndex: "command_preview", render: (value) => <Text className="monitoringMono">{String(value || "-")}</Text> },
          ]}
        />
      </ProCard>

      <ProCard title="证据" bordered size="small">
        <Table
          rowKey={(record) => readString(record, "id")}
          size="small"
          dataSource={detail.evidence || []}
          pagination={false}
          scroll={{ x: 760 }}
          locale={{ emptyText: <Empty description="暂无证据" /> }}
          columns={[
            { title: "来源", dataIndex: "source", width: 120, render: (value) => <Tag>{String(value || "-")}</Tag> },
            { title: "类型", dataIndex: "kind", width: 140, render: (value) => String(value || "-") },
            { title: "摘要", dataIndex: "summary", render: (value) => <Text className="monitoringText">{String(value || "-")}</Text> },
          ]}
        />
      </ProCard>

      <ProCard title="时间线" bordered size="small">
        {detail.timeline?.length ? (
          <Timeline
            items={detail.timeline.slice(-10).map((event) => ({
              color: timelineColor(readString(event, "type")),
              children: (
                <Space direction="vertical" size={2}>
                  <Text strong>{readString(event, "title") || readString(event, "type")}</Text>
                  <Text type="secondary" className="monitoringText">{readString(event, "summary")}</Text>
                  <Text type="secondary">{formatTime(readString(event, "created_at"))}</Text>
                </Space>
              ),
            }))}
          />
        ) : (
          <Empty description="暂无时间线" />
        )}
      </ProCard>
    </Space>
  );
}

function readString(item: Record<string, unknown>, key: string) {
  const value = item[key];
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

function readNumber(item: Record<string, unknown>, key: string) {
  const value = item[key];
  return typeof value === "number" ? value : 0;
}

function formatPercent(value?: number) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return `${Math.round(value * 100)}%`;
}

function formatTime(value: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function statusLabel(status: string) {
  return {
    ok: "正常",
    warning: "告警",
    failed: "失败",
    disconnected: "未连接",
    action_required: "待修复",
    remediating: "修复中",
    resolved: "已恢复",
    passed: "已通过",
    blocked: "已阻断",
  }[status] || status;
}

function statusColor(status: string) {
  if (["ok", "resolved", "passed", "succeeded"].includes(status)) {
    return "green";
  }
  if (["warning", "action_required", "blocked", "dry_run_failed"].includes(status)) {
    return "gold";
  }
  if (["failed", "critical"].includes(status)) {
    return "red";
  }
  if (["remediating", "running", "diagnosing"].includes(status)) {
    return "blue";
  }
  return "default";
}

function statusAlertType(status: string) {
  if (["ok", "resolved", "passed", "succeeded"].includes(status)) {
    return "success";
  }
  if (["warning", "action_required", "blocked", "dry_run_failed"].includes(status)) {
    return "warning";
  }
  if (["failed", "critical", "disconnected"].includes(status)) {
    return "error";
  }
  return "info";
}

function severityColor(severity: string) {
  return severity === "critical" ? "red" : severity === "warning" ? "gold" : "blue";
}

function riskColor(risk: string) {
  return risk === "high" ? "red" : risk === "medium" ? "gold" : "green";
}

function timelineColor(type: string) {
  if (type.includes("failed")) {
    return "red";
  }
  if (type.includes("verification") || type.includes("resolved")) {
    return "green";
  }
  if (type.includes("approval") || type.includes("execution")) {
    return "blue";
  }
  return "gray";
}
