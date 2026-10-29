import React from "react";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Collapse, Empty, Row, Segmented, Select, Space, Table } from "antd";
import { ProCard } from "@ant-design/pro-components";
import {
  WorkspaceTabs,
  TrendChart,
  RankingChart,
  DistributionChart,
  chartColors,
} from "../components/WorkspaceCharts";
import type { EffectAnalyticsResponse } from "../api";
import { type Role, type EffectAnalyticsFilterState } from "../workspace/types";
import { Paragraph, Text, Title, formatPercent, formatTime, StatusTag } from "../workspace/shared";

export function EffectAnalyticsPanel({
  role,
  analytics,
  filters,
  setFilters,
  loading,
  refreshAnalytics,
}: {
  role: Role;
  analytics: EffectAnalyticsResponse | null;
  filters: EffectAnalyticsFilterState;
  setFilters: React.Dispatch<React.SetStateAction<EffectAnalyticsFilterState>>;
  loading: boolean;
  refreshAnalytics: () => void;
}) {
  const summary = analytics?.summary;

  return (
    <Space direction="vertical" className="pageStack">
      <ProCard
        title="分析范围"
        subTitle={
          role === "admin" ? "基于真实运行记录和审计事件的全平台只读指标" : "当前账号仅查看自己的执行效果"
        }
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshAnalytics} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className={role === "admin" ? "effectAnalyticsToolbar admin" : "effectAnalyticsToolbar"}>
          <Segmented
            size="small"
            value={filters.dateRange}
            onChange={(value) =>
              setFilters((current) => ({
                ...current,
                dateRange: value as EffectAnalyticsFilterState["dateRange"],
              }))
            }
            options={[
              { label: "近7天", value: "7d" },
              { label: "近30天", value: "30d" },
              { label: "近90天", value: "90d" },
              { label: "全部", value: "all" },
            ]}
          />
          {role === "admin" && (
            <Select
              size="small"
              value={filters.position}
              onChange={(value) => setFilters((current) => ({ ...current, position: value }))}
              options={[
                { label: "全部岗位", value: "all" },
                { label: "运营", value: "operations" },
                { label: "客服", value: "customer_service" },
                { label: "财务", value: "finance" },
              ]}
            />
          )}
          <Button
            size="small"
            type="primary"
            icon={<SearchOutlined />}
            onClick={refreshAnalytics}
            loading={loading}
          >
            查询
          </Button>
        </div>
      </ProCard>
      <Row gutter={[12, 12]} className="effectMetricRow">
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard metric-blue">
            <Text type="secondary">自动化次数</Text>
            <Title level={3}>{summary?.total_runs ?? 0}</Title>
            <Text type="secondary">{analytics?.scope.date_range_label || "近 30 天"}</Text>
          </Card>
        </Col>
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard metric-green">
            <Text type="secondary">成功率</Text>
            <Title level={3}>{formatPercent(summary?.success_rate)}</Title>
            <Text type="secondary">{summary?.succeeded_runs ?? 0} 次成功</Text>
          </Card>
        </Col>
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard metric-amber">
            <Text type="secondary">越权拦截</Text>
            <Title level={3}>{summary?.blocked_runs ?? 0}</Title>
            <Text type="secondary">{formatPercent(summary?.blocked_rate)} 拦截率</Text>
          </Card>
        </Col>
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard metric-purple">
            <Text type="secondary">估算节省</Text>
            <Title level={3}>{summary?.estimated_saved_hours ?? 0}h</Title>
            <Text type="secondary">按成功执行保守估算</Text>
          </Card>
        </Col>
      </Row>
      <WorkspaceTabs
        storageKey="effect_tab"
        items={[
          {
            key: "overview",
            label: "效果总览",
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} xl={14} className="effectPanelCol">
                  <ProCard title="执行趋势" bordered className="effectPanelCard">
                    <TrendChart
                      label="执行趋势"
                      data={(analytics?.trend || []).map((item) => ({
                        label: item.date,
                        shortLabel: item.date.slice(5),
                        values: {
                          succeeded: item.succeeded_runs,
                          failed: item.failed_runs,
                          blocked: item.blocked_runs,
                        },
                      }))}
                      series={[
                        { key: "succeeded", label: "成功", color: chartColors.green },
                        { key: "failed", label: "失败", color: chartColors.red },
                        { key: "blocked", label: "权限拦截", color: chartColors.amber },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={10} className="effectPanelCol">
                  <ProCard title="状态分布" bordered className="effectPanelCard">
                    <DistributionChart
                      label="状态分布"
                      items={(analytics?.status_distribution || []).map((item) => ({
                        key: item.status,
                        label:
                          (
                            {
                              succeeded: "成功",
                              failed: "失败",
                              blocked: "权限拦截",
                              running: "运行中",
                            } as Record<string, string>
                          )[item.status] || item.status,
                        value: item.count,
                        color:
                          (
                            {
                              succeeded: chartColors.green,
                              failed: chartColors.red,
                              blocked: chartColors.amber,
                              running: chartColors.blue,
                            } as Record<string, string>
                          )[item.status] || chartColors.gray,
                      }))}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "ranking",
            label: "岗位与应用",
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} xl={12} className="effectPanelCol">
                  <ProCard title="岗位效果排行" bordered className="effectPanelCard">
                    <RankingChart
                      label="岗位执行次数排行"
                      items={[...(analytics?.position_ranking || [])]
                        .sort((a, b) => b.total_runs - a.total_runs)
                        .map((item) => ({
                          key: item.position,
                          label: item.position_label,
                          value: item.total_runs,
                          color:
                            item.position === "finance"
                              ? chartColors.purple
                              : item.position === "customer_service"
                                ? chartColors.green
                                : chartColors.blue,
                          detail: (
                            <>
                              成功率 {formatPercent(item.success_rate)} · 节省 {item.estimated_saved_minutes}{" "}
                              分钟
                            </>
                          ),
                        }))}
                    />
                    <Collapse
                      ghost
                      items={[
                        {
                          key: "details",
                          label: "查看岗位明细",
                          children: (
                            <>
                              <Table
                                rowKey="position"
                                size="small"
                                dataSource={analytics?.position_ranking || []}
                                pagination={false}
                                scroll={{ x: 560 }}
                                locale={{ emptyText: <Empty description="暂无岗位数据" /> }}
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
                                    title: "节省",
                                    dataIndex: "estimated_saved_minutes",
                                    render: (value) => `${value} 分钟`,
                                  },
                                ]}
                              />
                            </>
                          ),
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="effectPanelCol">
                  <ProCard title="应用使用排行" bordered className="effectPanelCard">
                    <RankingChart
                      label="应用执行次数排行"
                      items={[...(analytics?.app_ranking || [])]
                        .sort((a, b) => b.total_runs - a.total_runs)
                        .slice(0, 8)
                        .map((item) => ({
                          key: item.app_id,
                          label: item.app_name,
                          value: item.total_runs,
                          color: chartColors.purple,
                          detail: <>成功率 {formatPercent(item.success_rate)}</>,
                        }))}
                    />
                    <Collapse
                      ghost
                      items={[
                        {
                          key: "details",
                          label: "查看应用明细",
                          children: (
                            <>
                              <Table
                                rowKey="app_id"
                                size="small"
                                dataSource={analytics?.app_ranking || []}
                                pagination={false}
                                scroll={{ x: 680 }}
                                locale={{ emptyText: <Empty description="暂无应用数据" /> }}
                                columns={[
                                  {
                                    title: "应用",
                                    dataIndex: "app_name",
                                    width: 210,
                                    render: (value, record) => (
                                      <Space direction="vertical" size={2} className="effectCellStack">
                                        <Text strong className="effectText">
                                          {String(value)}
                                        </Text>
                                        <Text className="effectMono">{record.app_id}</Text>
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
                                    title: "最近运行",
                                    dataIndex: "last_run_at",
                                    render: (value) => formatTime(value),
                                  },
                                ]}
                              />
                            </>
                          ),
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "security",
            label: "安全分析",
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} xl={12} className="effectPanelCol">
                  <ProCard title="失败与拦截原因" bordered className="effectPanelCard">
                    <Table
                      rowKey={(record) => `${record.status}-${record.reason}`}
                      size="small"
                      dataSource={analytics?.failure_reasons || []}
                      pagination={false}
                      scroll={{ x: 640 }}
                      locale={{ emptyText: <Empty description="暂无失败或拦截" /> }}
                      columns={[
                        {
                          title: "状态",
                          dataIndex: "status",
                          width: 92,
                          render: (value) => <StatusTag value={String(value)} />,
                        },
                        {
                          title: "原因",
                          dataIndex: "reason",
                          render: (value) => <Text className="effectText">{String(value)}</Text>,
                        },
                        { title: "次数", dataIndex: "count", width: 76 },
                        {
                          title: "最近",
                          dataIndex: "last_seen_at",
                          width: 130,
                          render: (value) => formatTime(value),
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="effectPanelCol">
                  <ProCard title="审计安全摘要" bordered className="effectPanelCard">
                    <div className="effectAuditSummary">
                      <div>
                        <Text type="secondary">审计事件</Text>
                        <Title level={4}>{analytics?.audit_summary.total_events ?? 0}</Title>
                      </div>
                      <div>
                        <Text type="secondary">权限拦截</Text>
                        <Title level={4}>{analytics?.audit_summary.blocked_events ?? 0}</Title>
                      </div>
                      <div>
                        <Text type="secondary">审批事件</Text>
                        <Title level={4}>{analytics?.audit_summary.approval_events ?? 0}</Title>
                      </div>
                    </div>
                    <Table
                      rowKey={(record) => `${record.action}-${record.resource_type}`}
                      size="small"
                      dataSource={analytics?.audit_summary.top_actions || []}
                      pagination={false}
                      scroll={{ x: 560 }}
                      locale={{ emptyText: <Empty description="暂无审计事件" /> }}
                      columns={[
                        {
                          title: "动作",
                          dataIndex: "action",
                          render: (value) => <Text className="effectMono">{String(value)}</Text>,
                        },
                        {
                          title: "资源",
                          dataIndex: "resource_type",
                          width: 110,
                          render: (value) => value || "-",
                        },
                        { title: "次数", dataIndex: "count", width: 76 },
                        {
                          title: "最近",
                          dataIndex: "last_seen_at",
                          width: 130,
                          render: (value) => formatTime(value),
                        },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "methodology",
            label: "估算口径",
            children: (
              <ProCard title="估算口径" bordered>
                <div className="effectEstimateGrid">
                  {(analytics?.estimate_model || []).map((item) => (
                    <div className="effectEstimateItem" key={item.run_type}>
                      <Text className="effectMono">{item.run_type}</Text>
                      <Text strong>{item.saved_minutes_per_run} 分钟/次</Text>
                      <Text type="secondary" className="effectText">
                        {item.description}
                      </Text>
                    </div>
                  ))}
                </div>
              </ProCard>
            ),
          },
        ]}
      />
    </Space>
  );
}
