import React, { lazy, useState } from "react";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Segmented, Space, Table, Tabs, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import { TrendChart, chartColors } from "../components/WorkspaceCharts";
import type { MonitoringCenterResponse } from "../api";
import { type MonitoringCenterFilterState } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  formatTime,
  formatPercent,
  formatDuration,
  StatusTag,
} from "../workspace/shared";
import { ConnectorStatusTag } from "../components/ConnectorStatusTag";

const MonitoringAiopsPanel = lazy(() => import("../components/MonitoringAiopsPanel").then((module) => ({ default: module.MonitoringAiopsPanel })));

export function MonitoringCenterPanel({
  token,
  data,
  filters,
  setFilters,
  loading,
  refreshMonitoringCenter,
}: {
  token: string;
  data: MonitoringCenterResponse | null;
  filters: MonitoringCenterFilterState;
  setFilters: React.Dispatch<React.SetStateAction<MonitoringCenterFilterState>>;
  loading: boolean;
  refreshMonitoringCenter: () => void;
}) {
  const summary = data?.run_summary;
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="监控范围"
        subTitle="管理员专属，聚合真实 API、数据库、ERP、连接器、运行记录、审计和 AI 评测状态"
        bordered
        extra={
          <Space size={8} wrap>
            <Tag color={monitoringStatusColor(data?.overall_status || "unknown")}>
              {monitoringStatusLabel(data?.overall_status || "unknown")}
            </Tag>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={refreshMonitoringCenter}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <div className="monitoringToolbar">
          <Segmented
            size="small"
            value={filters.dateRange}
            onChange={(value) => setFilters({ dateRange: value as MonitoringCenterFilterState["dateRange"] })}
            options={[
              { label: "近7天", value: "7d" },
              { label: "近30天", value: "30d" },
              { label: "近90天", value: "90d" },
              { label: "全部", value: "all" },
            ]}
          />
          <Button
            size="small"
            type="primary"
            icon={<SearchOutlined />}
            onClick={refreshMonitoringCenter}
            loading={loading}
          >
            查询
          </Button>
          <Text type="secondary" className="monitoringGeneratedAt">
            生成时间：{formatTime(data?.scope.generated_at || null)}
          </Text>
        </div>
      </ProCard>

      <Row gutter={[12, 12]} className="monitoringMetricRow">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard metric-blue">
            <Text type="secondary">运行总数</Text>
            <Title level={3}>{summary?.total_runs ?? 0}</Title>
            <Text type="secondary">{data?.scope.date_range_label || "近 30 天"}</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard metric-green">
            <Text type="secondary">成功率</Text>
            <Title level={3}>{formatPercent(summary?.success_rate)}</Title>
            <Text type="secondary">{summary?.succeeded_runs ?? 0} 次成功</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard metric-amber">
            <Text type="secondary">问题事件</Text>
            <Title level={3}>{(summary?.failed_runs ?? 0) + (summary?.blocked_runs ?? 0)}</Title>
            <Text type="secondary">失败 + 权限拦截</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard metric-purple">
            <Text type="secondary">P95 耗时</Text>
            <Title level={3}>{formatDuration(summary?.p95_duration_ms)}</Title>
            <Text type="secondary">
              P50 {formatDuration(summary?.p50_duration_ms)} · P99 {formatDuration(summary?.p99_duration_ms)}{" "}
              · {summary?.duration_samples ?? 0} 个样本
            </Text>
          </Card>
        </Col>
      </Row>

      <Tabs
        className="monitoringCenterTabs"
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "overview",
            label: "总览",
            children: (
              <Space direction="vertical" size={12} className="pageStack">
                <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                  <Col xs={24} xl={15} className="monitoringPanelCol">
                    <ProCard title="服务健康" bordered className="monitoringPanelCard">
                      <div className="monitoringHealthGrid">
                        {(data?.service_health || []).map((item) => (
                          <div className="monitoringHealthItem" key={item.id}>
                            <div className="monitoringHealthHeader">
                              <Text strong className="monitoringText">
                                {item.name}
                              </Text>
                              <Tag color={monitoringStatusColor(item.status)}>
                                {monitoringStatusLabel(item.status)}
                              </Tag>
                            </div>
                            <Text className="monitoringMetricText">{item.metric}</Text>
                            <Text type="secondary" className="monitoringText">
                              {item.message}
                            </Text>
                          </div>
                        ))}
                        {!data?.service_health.length && <Empty description="暂无服务健康数据" />}
                      </div>
                    </ProCard>
                  </Col>
                  <Col xs={24} xl={9} className="monitoringPanelCol">
                    <ProCard title="基础资产" bordered className="monitoringPanelCard">
                      <div className="monitoringAssetGrid">
                        <MonitoringAsset
                          label="用户"
                          value={data?.users.total_users ?? 0}
                          hint={`${data?.users.items.length ?? 0} 个角色/岗位桶`}
                        />
                        <MonitoringAsset
                          label="文档"
                          value={data?.knowledge.active_documents ?? 0}
                          hint={`${data?.knowledge.child_chunks ?? 0} 个向量切片`}
                        />
                        <MonitoringAsset
                          label="连接器"
                          value={data?.connectors.summary.total ?? 0}
                          hint={`${data?.connectors.summary.healthy ?? 0} 个健康`}
                        />
                        <MonitoringAsset
                          label="评测样本"
                          value={data?.evaluation.summary.total_cases ?? 0}
                          hint={`${data?.evaluation.summary.report_count ?? 0} 份报告`}
                        />
                      </div>
                    </ProCard>
                  </Col>
                </Row>

                <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                  <Col xs={24} xl={14} className="monitoringPanelCol">
                    <ProCard title="运行趋势" bordered className="monitoringPanelCard">
                      {data?.run_trend.length ? (
                        <TrendChart
                          label="运行趋势"
                          data={(data?.run_trend || []).map((item) => ({
                            label: item.date,
                            shortLabel: item.date.slice(5),
                            values: {
                              succeeded: item.succeeded_runs,
                              failed: item.failed_runs,
                              blocked: item.blocked_runs,
                              running: item.running_runs,
                            },
                          }))}
                          series={[
                            ...[
                              { key: "succeeded", label: "成功", color: chartColors.green },
                              { key: "failed", label: "失败", color: chartColors.red },
                              { key: "blocked", label: "权限拦截", color: chartColors.amber },
                            ],
                            { key: "running", label: "运行中", color: chartColors.blue },
                          ]}
                        />
                      ) : (
                        <Empty description="暂无运行趋势" />
                      )}
                    </ProCard>
                  </Col>
                  <Col xs={24} xl={10} className="monitoringPanelCol">
                    <ProCard title="ERP 与 AI 评测" bordered className="monitoringPanelCard">
                      <div className="monitoringSignalList">
                        <div className="monitoringSignalItem">
                          <div className="monitoringHealthHeader">
                            <Text strong className="monitoringText">
                              ERP 连接
                            </Text>
                            <Tag
                              color={monitoringStatusColor(
                                data?.erp_health.ok ? "ok" : data?.erp_health.status || "unknown",
                              )}
                            >
                              {data?.erp_health.provider_label || "ERP"}
                            </Tag>
                          </div>
                          <Text type="secondary" className="monitoringText">
                            {data?.erp_health.message || "-"}
                          </Text>
                        </div>
                        <div className="monitoringSignalItem">
                          <div className="monitoringHealthHeader">
                            <Text strong className="monitoringText">
                              AI 评测通过率
                            </Text>
                            <Tag color={monitoringStatusColor(data?.evaluation.status || "unknown")}>
                              {monitoringStatusLabel(data?.evaluation.status || "unknown")}
                            </Tag>
                          </div>
                          <Text className="monitoringMetricText">
                            {formatPercent(data?.evaluation.summary.average_pass_rate)}
                          </Text>
                          <Text type="secondary" className="monitoringText">
                            最近报告：{formatTime(data?.evaluation.latest_report_at || null)}
                          </Text>
                        </div>
                      </div>
                    </ProCard>
                  </Col>
                </Row>
              </Space>
            ),
          },
          {
            key: "aiops",
            label: "AIOps 运维",
            children: (
              <MonitoringAiopsPanel
                token={token}
                active={activeTab === "aiops"}
                data={data?.aiops}
                loading={loading}
                refreshMonitoringCenter={refreshMonitoringCenter}
              />
            ),
          },
          {
            key: "issues",
            label: "运行问题",
            children: (
              <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="最近问题" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="id"
                      size="small"
                      loading={loading}
                      dataSource={data?.recent_issues || []}
                      pagination={false}
                      scroll={{ x: 560 }}
                      locale={{ emptyText: <Empty description="暂无失败或拦截事件" /> }}
                      columns={[
                        {
                          title: "状态",
                          dataIndex: "status",
                          width: 82,
                          render: (value) => <StatusTag value={String(value)} />,
                        },
                        {
                          title: "应用",
                          dataIndex: "app_name",
                          width: 190,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">
                                {String(value)}
                              </Text>
                              <Text type="secondary" className="monitoringText">
                                {record.summary || record.run_type_label}
                              </Text>
                            </Space>
                          ),
                        },
                        { title: "岗位", dataIndex: "position_label", width: 76 },
                        { title: "时间", dataIndex: "occurred_at", render: (value) => formatTime(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="慢任务 Top" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="id"
                      size="small"
                      loading={loading}
                      dataSource={data?.slow_runs || []}
                      pagination={false}
                      scroll={{ x: 560 }}
                      locale={{ emptyText: <Empty description="暂无耗时记录" /> }}
                      columns={[
                        {
                          title: "应用",
                          dataIndex: "app_name",
                          width: 190,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">
                                {String(value)}
                              </Text>
                              <Text className="monitoringMono">{record.run_type}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "状态",
                          dataIndex: "status",
                          width: 82,
                          render: (value) => <StatusTag value={String(value)} />,
                        },
                        { title: "岗位", dataIndex: "position_label", width: 76 },
                        { title: "耗时", dataIndex: "duration_ms", render: (value) => formatDuration(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "distribution",
            label: "分布分析",
            children: (
              <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="岗位运行分布" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="position"
                      size="small"
                      dataSource={data?.position_summary || []}
                      pagination={false}
                      scroll={{ x: 620 }}
                      locale={{ emptyText: <Empty description="暂无岗位运行数据" /> }}
                      columns={[
                        {
                          title: "岗位",
                          dataIndex: "position_label",
                          width: 110,
                          render: (value) => <Text strong>{String(value)}</Text>,
                        },
                        { title: "次数", dataIndex: "total_runs", width: 78 },
                        {
                          title: "成功率",
                          dataIndex: "success_rate",
                          width: 92,
                          render: (value) => formatPercent(value),
                        },
                        { title: "失败", dataIndex: "failed_runs", width: 72 },
                        { title: "拦截", dataIndex: "blocked_runs", width: 72 },
                        {
                          title: "均耗时",
                          dataIndex: "avg_duration_ms",
                          render: (value) => formatDuration(value),
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="自动化类型分布" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="run_type"
                      size="small"
                      dataSource={data?.run_type_summary || []}
                      pagination={false}
                      scroll={{ x: 900 }}
                      locale={{ emptyText: <Empty description="暂无类型运行数据" /> }}
                      columns={[
                        {
                          title: "类型",
                          dataIndex: "label",
                          width: 190,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">
                                {String(value)}
                              </Text>
                              <Text className="monitoringMono">{record.run_type}</Text>
                            </Space>
                          ),
                        },
                        { title: "次数", dataIndex: "total_runs", width: 78 },
                        {
                          title: "成功率",
                          dataIndex: "success_rate",
                          width: 92,
                          render: (value) => formatPercent(value),
                        },
                        {
                          title: "均耗时",
                          dataIndex: "avg_duration_ms",
                          width: 92,
                          render: (value) => formatDuration(value),
                        },
                        {
                          title: "P50",
                          dataIndex: "p50_duration_ms",
                          width: 92,
                          render: (value) => formatDuration(value),
                        },
                        {
                          title: "P95",
                          dataIndex: "p95_duration_ms",
                          width: 92,
                          render: (value) => formatDuration(value),
                        },
                        {
                          title: "P99",
                          dataIndex: "p99_duration_ms",
                          width: 92,
                          render: (value) => formatDuration(value),
                        },
                        { title: "最近", dataIndex: "latest_run_at", render: (value) => formatTime(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} className="monitoringPanelCol">
                  <ProCard title="步骤耗时分解" bordered className="monitoringPanelCard">
                    <Table
                      rowKey={(record) => `${record.step_name}:${record.provider}`}
                      size="small"
                      dataSource={data?.step_summary || []}
                      pagination={false}
                      scroll={{ x: 980 }}
                      locale={{ emptyText: <Empty description="暂无步骤耗时数据" /> }}
                      columns={[
                        {
                          title: "步骤",
                          dataIndex: "step_name",
                          width: 240,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">
                                {String(value)}
                              </Text>
                              <Text className="monitoringMono">
                                {record.stage_type} · {record.provider}
                              </Text>
                            </Space>
                          ),
                        },
                        { title: "样本", dataIndex: "total_steps", width: 78 },
                        { title: "失败", dataIndex: "failed_steps", width: 72 },
                        { title: "拦截", dataIndex: "blocked_steps", width: 72 },
                        {
                          title: "均耗时",
                          dataIndex: "avg_duration_ms",
                          width: 100,
                          render: (value) => formatDuration(value),
                        },
                        {
                          title: "P50",
                          dataIndex: "p50_duration_ms",
                          width: 100,
                          render: (value) => formatDuration(value),
                        },
                        {
                          title: "P95",
                          dataIndex: "p95_duration_ms",
                          width: 100,
                          render: (value) => formatDuration(value),
                        },
                        {
                          title: "P99",
                          dataIndex: "p99_duration_ms",
                          width: 100,
                          render: (value) => formatDuration(value),
                        },
                        { title: "最近", dataIndex: "latest_step_at", render: (value) => formatTime(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "connectors",
            label: "连接审计",
            children: (
              <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="连接器状态" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={data?.connectors.items || []}
                      pagination={false}
                      scroll={{ x: 620 }}
                      locale={{ emptyText: <Empty description="暂无连接器状态" /> }}
                      columns={[
                        {
                          title: "连接器",
                          dataIndex: "label",
                          width: 180,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">
                                {String(value)}
                              </Text>
                              <Text type="secondary" className="monitoringText">
                                {record.category}
                              </Text>
                            </Space>
                          ),
                        },
                        {
                          title: "状态",
                          dataIndex: "status",
                          width: 96,
                          render: (value) => <ConnectorStatusTag status={String(value)} />,
                        },
                        {
                          title: "检查",
                          dataIndex: "supports_real_health_check",
                          width: 72,
                          render: (value) => (value ? "已接入" : "未接入"),
                        },
                        {
                          title: "说明",
                          dataIndex: "health_message",
                          render: (value) => <Text className="monitoringText">{String(value)}</Text>,
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="审计动作 Top" bordered className="monitoringPanelCard">
                    <div className="monitoringAuditSummary">
                      <MonitoringAsset
                        label="审计事件"
                        value={data?.audit_summary.total_events ?? 0}
                        hint="当前筛选范围"
                      />
                      <MonitoringAsset
                        label="权限事件"
                        value={data?.audit_summary.security_events ?? 0}
                        hint="拦截/拒绝/权限"
                      />
                      <MonitoringAsset
                        label="审批事件"
                        value={data?.audit_summary.approval_events ?? 0}
                        hint="审批相关"
                      />
                    </div>
                    <Table
                      rowKey={(record) => `${record.action}-${record.resource_type}`}
                      size="small"
                      dataSource={data?.audit_actions || []}
                      pagination={false}
                      scroll={{ x: 620 }}
                      locale={{ emptyText: <Empty description="暂无审计动作" /> }}
                      columns={[
                        {
                          title: "动作",
                          dataIndex: "action",
                          render: (value) => <Text className="monitoringMono">{String(value)}</Text>,
                        },
                        {
                          title: "资源",
                          dataIndex: "resource_type",
                          width: 110,
                          render: (value) => value || "-",
                        },
                        { title: "次数", dataIndex: "count", width: 78 },
                        {
                          title: "最近",
                          dataIndex: "last_seen_at",
                          width: 132,
                          render: (value) => formatTime(value),
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </Space>
  );
}

export function MonitoringAsset({ label, value, hint }: { label: string; value: React.ReactNode; hint: string }) {
  return (
    <div className="monitoringAssetItem">
      <Text type="secondary">{label}</Text>
      <Title level={4}>{value}</Title>
      <Text type="secondary" className="monitoringText">{hint}</Text>
    </div>
  );
}

export function monitoringStatusLabel(value: string) {
  const labels: Record<string, string> = {
    ok: "正常",
    healthy: "健康",
    success: "正常",
    warning: "需关注",
    failed: "异常",
    degraded: "异常",
    not_configured: "未配置",
    not_implemented: "待接入",
    configured_pending: "待联调",
    http_error: "接口异常",
    connection_error: "连接异常",
    timeout: "超时",
    unknown: "未知",
  };

  return labels[value] ?? value;
}

export function monitoringStatusColor(value: string) {
  const colors: Record<string, string> = {
    ok: "green",
    healthy: "green",
    success: "green",
    warning: "gold",
    failed: "red",
    degraded: "gold",
    not_configured: "default",
    not_implemented: "gold",
    configured_pending: "blue",
    http_error: "red",
    connection_error: "red",
    timeout: "red",
  };

  return colors[value] || "default";
}
