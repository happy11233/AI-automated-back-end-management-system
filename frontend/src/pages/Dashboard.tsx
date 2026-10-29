import React from "react";
import {
  CheckCircleOutlined,
  CommentOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  HistoryOutlined,
  ReloadOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Segmented, Select, Space, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import { WorkspaceTabs } from "../components/WorkspaceCharts";
import type { ErpDashboardOverviewResponse, Position } from "../api";
import type {
  DashboardMarket,
  DashboardDateRange,
  DashboardStore,
  Role,
  View,
} from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  positionLabel,
  positionConfigs,
  metricStatus,
  formatAmount,
  textFromUnknown,
  canRoleAccessView,
} from "../workspace/shared";

export const fallbackDashboardMarketOptions: Array<{ label: string; value: DashboardMarket }> = [
  { label: "全部站点", value: "all" },
  { label: "美国站", value: "us" },
  { label: "德国站", value: "de" },
  { label: "日本站", value: "jp" },
];

export const dashboardDateRangeOptions: Array<{ label: string; value: DashboardDateRange }> = [
  { label: "全部时间", value: "all" },
  { label: "今天", value: "today" },
  { label: "近7天", value: "7d" },
  { label: "近30天", value: "30d" },
];

export const dashboardStoreOptions: Array<{ label: string; value: DashboardStore }> = [
  { label: "全部店铺", value: "all" },
  { label: "US Store", value: "us_store" },
  { label: "DE Store", value: "de_store" },
  { label: "JP Store", value: "jp_store" },
];

export function Dashboard({
  stats,
  role,
  position,
  erpOverview,
  erpDashboardMarket,
  setErpDashboardMarket,
  erpDashboardDateRange,
  setErpDashboardDateRange,
  erpDashboardStore,
  setErpDashboardStore,
  refreshErpOverview,
  onOpenRecordDetail,
  onNavigate,
}: {
  stats: Array<{ title: string; value: number; suffix: string }>;
  role: Role;
  position: Position | null;
  erpOverview: ErpDashboardOverviewResponse | null;
  erpDashboardMarket: DashboardMarket;
  setErpDashboardMarket: (value: DashboardMarket) => void;
  erpDashboardDateRange: DashboardDateRange;
  setErpDashboardDateRange: (value: DashboardDateRange) => void;
  erpDashboardStore: DashboardStore;
  setErpDashboardStore: (value: DashboardStore) => void;
  refreshErpOverview: () => void;
  onOpenRecordDetail: (resource: string, item: Record<string, unknown>) => void;
  onNavigate: (view: View) => void;
}) {
  const visibleStats = role === "admin" ? stats : stats.filter((item) => item.title === "会话消息");
  const shortcuts = dashboardShortcuts(role, position);

  return (
    <WorkspaceTabs
      storageKey="dashboard_tab"
      items={[
        {
          key: "work",
          label: "工作概览",
          children: (
            <Space direction="vertical" className="pageStack">
              {role === "admin" ? (
                <Row gutter={[12, 12]} className="dashboardStatsRow">
                  {visibleStats.map((item, index) => (
                    <Col xs={24} sm={8} key={item.title} className="dashboardStatCol">
                      <Card
                        size="small"
                        className={`contextCard dashboardStatCard dashboardSummaryCard metric-${["blue", "green", "purple"][index % 3]}`}
                      >
                        <div className="dashboardCenteredMetric">
                          <Text type="secondary" className="dashboardMetricTitle">
                            {item.title}
                          </Text>
                          <Title level={3} className="dashboardMetricValue">
                            {item.value}
                            <span className="dashboardMetricSuffix">{item.suffix}</span>
                          </Title>
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              ) : (
                <div className="workspaceWelcome">
                  <div>
                    <Text type="secondary">{position ? positionLabel(position) : "员工"}工作台</Text>
                    <Title level={3}>从常用应用开始今天的工作</Title>
                  </div>
                  <Tag color="blue">按岗位权限展示</Tag>
                </div>
              )}
              <ProCard
                title={role === "admin" ? "管理员快捷入口" : "岗位快捷入口"}
                subTitle={
                  role === "admin"
                    ? "常用后台维护和诊断"
                    : position
                      ? `${positionLabel(position)}常用功能`
                      : "未绑定岗位"
                }
                bordered
              >
                <Row
                  gutter={[role === "admin" ? 12 : 8, role === "admin" ? 12 : 8]}
                  className={"dashboardShortcutCompactGrid"}
                >
                  {shortcuts.map((item) => (
                    <Col xs={24} md={12} xl={6} key={item.view} className="dashboardShortcutCol">
                      <Card
                        size="small"
                        className={
                          role === "admin"
                            ? "contextCard dashboardShortcutCard"
                            : "contextCard dashboardShortcutCard compact"
                        }
                      >
                        <div className="dashboardShortcutBody">
                          <Space className="dashboardShortcutTitle">
                            {item.icon}
                            <Tooltip title={item.description} placement="right">
                              <Text strong className="dashboardShortcutTitleText">
                                {item.title}
                              </Text>
                            </Tooltip>
                          </Space>
                          <Button
                            className="dashboardShortcutButton"
                            aria-label={`打开 ${item.title}`}
                            type="primary"
                            onClick={() => onNavigate(item.view)}
                          >
                            打开
                          </Button>
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </ProCard>
              {role !== "admin" ? (
                <ProCard title="岗位工作台" bordered>
                  {position ? (
                    <Space direction="vertical" size={12} style={{ width: "100%" }}>
                      <Text type="secondary">当前岗位：{positionLabel(position)}</Text>
                      <Row gutter={[12, 12]}>
                        {positionConfigs[position].capabilities.map((item) => (
                          <Col xs={24} md={12} key={item} className="capabilityCardCol">
                            <Card size="small" className="contextCard capabilityCard">
                              <Text strong>{item}</Text>
                            </Card>
                          </Col>
                        ))}
                      </Row>
                    </Space>
                  ) : (
                    <Empty description="当前账号尚未绑定岗位" />
                  )}
                </ProCard>
              ) : null}
            </Space>
          ),
        },
        {
          key: "business",
          label: "业务数据",
          children: (
            <DashboardOverviewSection
              role={role}
              erpOverview={erpOverview}
              erpDashboardMarket={erpDashboardMarket}
              setErpDashboardMarket={setErpDashboardMarket}
              erpDashboardDateRange={erpDashboardDateRange}
              setErpDashboardDateRange={setErpDashboardDateRange}
              erpDashboardStore={erpDashboardStore}
              setErpDashboardStore={setErpDashboardStore}
              refreshErpOverview={refreshErpOverview}
              onOpenRecordDetail={onOpenRecordDetail}
            />
          ),
        },
      ]}
    />
  );
}

export function DashboardOverviewSection({
  role,
  erpOverview,
  erpDashboardMarket,
  setErpDashboardMarket,
  erpDashboardDateRange,
  setErpDashboardDateRange,
  erpDashboardStore,
  setErpDashboardStore,
  refreshErpOverview,
  onOpenRecordDetail,
}: {
  role: Role;
  erpOverview: ErpDashboardOverviewResponse | null;
  erpDashboardMarket: DashboardMarket;
  setErpDashboardMarket: (value: DashboardMarket) => void;
  erpDashboardDateRange: DashboardDateRange;
  setErpDashboardDateRange: (value: DashboardDateRange) => void;
  erpDashboardStore: DashboardStore;
  setErpDashboardStore: (value: DashboardStore) => void;
  refreshErpOverview: () => void;
  onOpenRecordDetail: (resource: string, item: Record<string, unknown>) => void;
}) {
  const isEmployee = role !== "admin";
  const marketSelectOptions = dashboardMarketSelectOptions(erpOverview);

  return (
    <ProCard
      title={role === "admin" ? "平台数据概览" : "岗位数据概览"}
      subTitle={role === "admin" ? erpOverview?.message || "从 ERP 权限范围内加载关键数据" : undefined}
      bordered
      className={isEmployee ? "dashboardOverviewSection compact" : "dashboardOverviewSection"}
    >
      {erpOverview ? (
        <Space direction="vertical" size={isEmployee ? 12 : 16} className="pageStack">
          <div className={isEmployee ? "dashboardOverviewToolbar compact" : "dashboardOverviewToolbar"}>
            {role === "admin" ? (
              <Space size={8} wrap>
                <Text strong>{erpOverview.title}</Text>
                <Tag color="blue">{erpOverview.market_label}</Tag>
                <Tag color="geekblue">{erpOverview.store_label}</Tag>
                <Tag color="cyan">{erpOverview.date_range_label}</Tag>
              </Space>
            ) : null}
            <Space size={8} wrap>
              <Select<DashboardMarket>
                size="small"
                value={erpDashboardMarket}
                className="dashboardMarketSelect"
                options={marketSelectOptions}
                onChange={setErpDashboardMarket}
              />
              <Segmented<DashboardDateRange>
                size="small"
                value={erpDashboardDateRange}
                options={dashboardDateRangeOptions}
                onChange={setErpDashboardDateRange}
              />
              <Segmented<DashboardStore>
                size="small"
                value={erpDashboardStore}
                options={dashboardStoreOptions}
                onChange={setErpDashboardStore}
              />
              <Button size="small" icon={<ReloadOutlined />} onClick={refreshErpOverview}>
                刷新
              </Button>
            </Space>
          </div>

          <div className={isEmployee ? "dashboardMetricCardGrid compact" : "dashboardMetricCardGrid"}>
            {erpOverview.metrics.map((item) => (
              <Card
                key={item.title}
                size="small"
                className={`contextCard dashboardMetricCard status-${metricStatus(item.status)}`}
              >
                <div className="dashboardCenteredMetric">
                  <Text type="secondary" className="dashboardMetricTitle">{item.title}</Text>
                  <Title level={3} className="dashboardMetricValue">
                    {item.value}
                    {item.suffix ? <span className="dashboardMetricSuffix">{item.suffix}</span> : null}
                  </Title>
                  {role === "admin" && item.description ? (
                    <Text type="secondary" className="dashboardMetricDescription">{item.description}</Text>
                  ) : null}
                </div>
              </Card>
            ))}
          </div>

          {erpOverview.sections.length ? (
            <Row gutter={[12, 12]}>
              {erpOverview.sections.map((section) => (
                <Col xs={24} xl={8} key={section.resource} className="dashboardOverviewCol">
                  <Card
                    size="small"
                    className={isEmployee ? "contextCard dashboardOverviewCard compact" : "contextCard dashboardOverviewCard"}
                    title={
                      <Space size={6}>
                        <Text>{section.title}</Text>
                        {role === "admin" ? <Tag color={section.ok ? "green" : "gold"}>{section.status}</Tag> : null}
                      </Space>
                    }
                  >
                    <div className={isEmployee ? "dashboardOverviewBody compact" : "dashboardOverviewBody"}>
                      {role === "admin" ? (
                        <>
                          <Paragraph type="secondary" className="dashboardOverviewDescription">
                            {section.message}
                          </Paragraph>
                          <Space size={[6, 6]} wrap>
                            <Tag color="blue">匹配 {section.total_count} 条</Tag>
                            {section.amount_total !== null && section.amount_total !== undefined ? (
                              <Tag color="green">
                                {section.amount_label || "金额合计"} {formatAmount(section.amount_total)}
                              </Tag>
                            ) : null}
                          </Space>
                        </>
                      ) : section.amount_total !== null && section.amount_total !== undefined ? (
                        <Text className="dashboardOverviewAmount">
                          {section.amount_label || "金额合计"} {formatAmount(section.amount_total)}
                        </Text>
                      ) : null}
                      <div className={isEmployee ? "dashboardRecordList compact" : "dashboardRecordList"}>
                        {section.items.length ? (
                          section.items.slice(0, isEmployee ? 2 : 3).map((item, index) => (
                            <div className="compactRecord" key={`${section.resource}-${index}`}>
                              <div className="compactRecordHeader">
                                <Text strong className="compactRecordPrimary">{overviewPrimaryText(item)}</Text>
                                <Button
                                  size="small"
                                  type="link"
                                  aria-label={`查看 ${section.title} ERP 详情`}
                                  onClick={() => onOpenRecordDetail(section.resource, item)}
                                >
                                  详情
                                </Button>
                              </div>
                              {role === "admin" ? (
                                <Text type="secondary" className="compactRecordSecondary">
                                  {overviewSecondaryText(item)}
                                </Text>
                              ) : null}
                            </div>
                          ))
                        ) : (
                          <div className="dashboardOverviewEmpty">
                            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无记录" />
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          ) : null}
        </Space>
      ) : (
        <Empty description="暂无岗位数据概览，点击刷新重新加载" />
      )}
    </ProCard>
  );
}

export function dashboardMarketSelectOptions(
  erpOverview: ErpDashboardOverviewResponse | null,
): Array<{ label: string; value: DashboardMarket }> {
  const options = erpOverview?.market_options?.length
    ? erpOverview.market_options
    : fallbackDashboardMarketOptions.map((item) => ({ ...item, count: 0 }));

  return options.map((item) => ({
    value: item.value,
    label: item.count > 0 ? `${item.label}（${item.count}）` : item.label,
  }));
}

export function overviewPrimaryText(item: Record<string, unknown>) {
  return textFromUnknown(
    item.name
      || item.po_no
      || item.lr_no
      || item.subject
      || item.item_code
      || item.customer
      || item.account
      || item.party
      || "-",
  );
}

export function overviewSecondaryText(item: Record<string, unknown>) {
  const parts = [
    item.customer || item.customer_name || item.supplier || item.account || item.item_name,
    item.status,
    item.grand_total ? `金额 ${item.grand_total} ${item.currency || ""}` : null,
    item.outstanding_amount ? `未收 ${item.outstanding_amount} ${item.currency || ""}` : null,
    item.price_list_rate ? `价格 ${item.price_list_rate} ${item.currency || ""}` : null,
    item.posting_date || item.transaction_date || item.modified,
  ]
    .filter(Boolean)
    .map(textFromUnknown);

  return parts.length ? parts.join(" / ") : "暂无更多字段";
}

export function dashboardShortcuts(role: Role, position: Position | null): Array<{
  title: string; description: string; view: View; icon: React.ReactNode;
}> {
  const items: Array<{ title: string; description: string; view: View; icon: React.ReactNode }> = [
    { title: "Agent 中心", description: "查看业务 Agent 的接入状态、执行进度与成果。", view: "ai_workflows", icon: <RobotOutlined /> },
    { title: "业务文件", description: "查看自动化任务生成的报告与文件。", view: "file_downloads", icon: <FileTextOutlined /> },
  ];
  if (role === "admin") items.push(
    { title: "运行记录", description: "追踪真实执行过程与失败原因。", view: "run_records", icon: <HistoryOutlined /> },
    { title: "连接配置", description: "检查业务数据源与执行渠道是否接入。", view: "connectors", icon: <DatabaseOutlined /> },
  );
  else if (position === "customer_service") items.push(
    { title: "客服收件箱", description: "查看消息处理结果、待发送回复与异常。", view: "customer_service_inbox", icon: <CommentOutlined /> },
    { title: "退款审批", description: "处理需要人工决策的售后事项。", view: "approvals", icon: <CheckCircleOutlined /> },
  );
  else if (position === "operations") items.push(
    { title: "草稿审核", description: "审核 Agent 准备的业务草稿。", view: "platform_draft_review", icon: <CheckCircleOutlined /> },
  );
  return items.filter((item) => canRoleAccessView(role, item.view, position));
}
