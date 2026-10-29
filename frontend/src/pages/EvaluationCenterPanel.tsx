import { ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Collapse, Empty, Row, Space, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import { WorkspaceTabs, RankingChart, chartColors } from "../components/WorkspaceCharts";
import type { EvaluationCenterResponse } from "../api";
import { Paragraph, Text, Title, formatPercent, formatTime, labelForBadge } from "../workspace/shared";

export function EvaluationCenterPanel({
  data,
  loading,
  runningEvaluationId,
  refreshEvaluationCenter,
  runEvaluation,
}: {
  data: EvaluationCenterResponse | null;
  loading: boolean;
  runningEvaluationId: string;
  refreshEvaluationCenter: () => void;
  runEvaluation: (datasetId: string) => void;
}) {
  const summary = data?.summary;

  return (
    <Space direction="vertical" className="pageStack">
      <ProCard
        title="质量指标"
        subTitle="管理员专属，只展示真实评测摘要和发布闸门，不返回原始 chunk 内容"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshEvaluationCenter} loading={loading}>
            刷新
          </Button>
        }
      >
        <Row gutter={[12, 12]} className="evaluationMetricRow">
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard metric-blue">
              <Text type="secondary">评测集</Text>
              <Title level={3}>{summary?.dataset_count ?? 0}</Title>
              <Text type="secondary">真实 JSONL 资产</Text>
            </Card>
          </Col>
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard metric-purple">
              <Text type="secondary">样本数</Text>
              <Title level={3}>{summary?.total_cases ?? 0}</Title>
              <Text type="secondary">RAG + 回归套件</Text>
            </Card>
          </Col>
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard metric-green">
              <Text type="secondary">平均通过率</Text>
              <Title level={3}>{formatPercent(summary?.average_pass_rate)}</Title>
              <Text type="secondary">基于已有报告</Text>
            </Card>
          </Col>
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard metric-amber">
              <Text type="secondary">回归套件</Text>
              <Title level={3}>{summary?.regression_suite_count ?? 0}</Title>
              <Text type="secondary">真实脚本覆盖</Text>
            </Card>
          </Col>
        </Row>
      </ProCard>
      <WorkspaceTabs
        storageKey="evaluation_tab"
        items={[
          {
            key: "overview",
            label: "质量总览",
            children: (
              <Row gutter={[24, 24]}>
                <Col xs={24} xl={14}>
                  <ProCard title="评测通过率对比" subTitle="每个评测集的已有报告；暂无报告时不估算" bordered>
                    <RankingChart
                      label="评测通过率"
                      percent
                      unit="%"
                      items={(data?.reports || [])
                        .filter((item) => typeof item.pass_rate === "number")
                        .map((item) => ({
                          key: item.dataset_id,
                          label: item.dataset_name,
                          value: (item.pass_rate || 0) * 100,
                          color: (item.pass_rate || 0) >= 0.9 ? chartColors.green : chartColors.amber,
                          detail: <>更新于 {formatTime(item.updated_at)}</>,
                        }))}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={10}>
                  <ProCard title="发布闸门" bordered className="evaluationPanelCard">
                    <div className="evaluationGateList">
                      {(data?.release_gates || []).map((item) => (
                        <div className="evaluationGateItem" key={item.id}>
                          <div className="evaluationGateHeader">
                            <Text strong className="evaluationText">
                              {item.name}
                            </Text>
                            <Tag color={evaluationGateColor(item.status)}>{labelForBadge(item.status)}</Tag>
                          </div>
                          <Text type="secondary" className="evaluationText">
                            阈值：{item.threshold}
                          </Text>
                          <Text className="evaluationMono">{item.actual}</Text>
                        </div>
                      ))}
                      {!data?.release_gates.length && <Empty description="暂无发布闸门" />}
                    </div>
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "datasets",
            label: "评测集",
            children: (
              <ProCard title="评测集资产" bordered className="evaluationPanelCard">
                <Table
                  rowKey="id"
                  loading={loading}
                  dataSource={data?.datasets || []}
                  pagination={false}
                  scroll={{ x: 820 }}
                  locale={{ emptyText: <Empty description="暂无评测集" /> }}
                  columns={[
                    {
                      title: "评测集",
                      dataIndex: "name",
                      width: 230,
                      render: (value, record) => (
                        <Space direction="vertical" size={2} className="evaluationCellStack">
                          <Text strong className="evaluationText">
                            {String(value)}
                          </Text>
                          <Text className="evaluationMono">{record.path}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "类型",
                      dataIndex: "category",
                      width: 92,
                      render: (value) => <Tag color="blue">{String(value)}</Tag>,
                    },
                    { title: "样本", dataIndex: "case_count", width: 82 },
                    {
                      title: "正/拒答",
                      dataIndex: "positive_cases",
                      width: 108,
                      render: (value, record) => `${value}/${record.refusal_cases}`,
                    },
                    {
                      title: "报告",
                      dataIndex: "has_report",
                      width: 82,
                      render: (value) => (
                        <Tag color={value ? "green" : "default"}>{value ? "已有" : "暂无"}</Tag>
                      ),
                    },
                    {
                      title: "更新",
                      dataIndex: "report_updated_at",
                      width: 132,
                      render: (value) => formatTime(value),
                    },
                    {
                      title: "操作",
                      dataIndex: "id",
                      fixed: "right",
                      width: 112,
                      render: (value, record) => (
                        <Button
                          size="small"
                          type="primary"
                          disabled={!record.can_run || record.id !== "rag_smoke"}
                          loading={runningEvaluationId === record.id}
                          onClick={() => runEvaluation(String(value))}
                        >
                          运行
                        </Button>
                      ),
                    },
                  ]}
                />
              </ProCard>
            ),
          },
          {
            key: "reports",
            label: "评测报告",
            children: (
              <Space direction="vertical" className="pageStack">
                <ProCard title="最近评测报告" bordered className="evaluationPanelCard">
                  <Table
                    rowKey="dataset_id"
                    dataSource={data?.reports || []}
                    pagination={false}
                    scroll={{ x: 760 }}
                    locale={{ emptyText: <Empty description="暂无评测报告" /> }}
                    columns={[
                      {
                        title: "报告",
                        dataIndex: "dataset_name",
                        width: 220,
                        render: (value, record) => (
                          <Space direction="vertical" size={2} className="evaluationCellStack">
                            <Text strong className="evaluationText">
                              {String(value)}
                            </Text>
                            <Text className="evaluationMono">{record.dataset_id}</Text>
                          </Space>
                        ),
                      },
                      {
                        title: "通过率",
                        dataIndex: "pass_rate",
                        width: 92,
                        render: (value) => formatPercent(value),
                      },
                      {
                        title: "Hit@5",
                        dataIndex: "metrics",
                        width: 88,
                        render: (value) => formatPercent(metricValue(value, "hit@5")),
                      },
                      {
                        title: "MRR",
                        dataIndex: "metrics",
                        width: 88,
                        render: (value) => formatNumber(metricValue(value, "MRR")),
                      },
                      {
                        title: "拒答",
                        dataIndex: "metrics",
                        width: 88,
                        render: (value) => formatPercent(metricValue(value, "refusal_accuracy")),
                      },
                      {
                        title: "样本",
                        dataIndex: "counts",
                        width: 78,
                        render: (value) => String(metricValue(value, "total_cases") ?? 0),
                      },
                      { title: "更新", dataIndex: "updated_at", render: (value) => formatTime(value) },
                    ]}
                  />
                </ProCard>
                <Collapse
                  ghost
                  items={[
                    {
                      key: "failures",
                      label: "查看失败样例摘要",
                      children: (
                        <ProCard title="失败样例摘要" bordered className="evaluationPanelCard">
                          <div className="evaluationFailureList">
                            {(data?.reports || [])
                              .flatMap((report) =>
                                report.failed_cases.map(
                                  (item) =>
                                    ({
                                      ...(item as Record<string, unknown>),
                                      dataset: report.dataset_name,
                                    }) as Record<string, unknown>,
                                ),
                              )
                              .slice(0, 8)
                              .map((item) => (
                                <div
                                  className="evaluationFailureItem"
                                  key={`${item.dataset}-${String(item.id)}`}
                                >
                                  <div className="evaluationGateHeader">
                                    <Text strong className="evaluationText">
                                      {String(item.id || "-")}
                                    </Text>
                                    <Tag color="red">{String(item.type || "failed")}</Tag>
                                  </div>
                                  <Text type="secondary" className="evaluationText">
                                    {String(item.dataset)}
                                  </Text>
                                  <Text className="evaluationText">{String(item.reason || "-")}</Text>
                                </div>
                              ))}
                            {!data?.reports.some((report) => report.failed_cases.length) && (
                              <Empty description="暂无失败样例" />
                            )}
                          </div>
                        </ProCard>
                      ),
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: "regression",
            label: "回归套件",
            children: (
              <ProCard title="真实回归套件" bordered>
                <Table
                  rowKey="id"
                  dataSource={data?.regression_suites || []}
                  pagination={false}
                  scroll={{ x: 860 }}
                  locale={{ emptyText: <Empty description="暂无回归套件" /> }}
                  columns={[
                    {
                      title: "套件",
                      dataIndex: "name",
                      width: 220,
                      render: (value, record) => (
                        <Space direction="vertical" size={2} className="evaluationCellStack">
                          <Text strong className="evaluationText">
                            {String(value)}
                          </Text>
                          <Text type="secondary" className="evaluationText">
                            {record.description}
                          </Text>
                        </Space>
                      ),
                    },
                    {
                      title: "类型",
                      dataIndex: "category",
                      width: 110,
                      render: (value) => <Tag color="purple">{String(value)}</Tag>,
                    },
                    { title: "用例", dataIndex: "case_count", width: 72 },
                    {
                      title: "真实服务",
                      dataIndex: "real_services",
                      width: 220,
                      render: (value: string[]) => (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => (
                            <Tag key={item}>{item}</Tag>
                          ))}
                        </Space>
                      ),
                    },
                    {
                      title: "命令",
                      dataIndex: "command",
                      render: (value) => <Text className="evaluationMono">{String(value)}</Text>,
                    },
                  ]}
                />
              </ProCard>
            ),
          },
        ]}
      />
    </Space>
  );
}

export function formatNumber(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  return value.toFixed(3);
}

export function metricValue(metrics: unknown, key: string) {
  if (!metrics || typeof metrics !== "object") {
    return null;
  }

  const value = (metrics as Record<string, unknown>)[key];
  return typeof value === "number" ? value : null;
}

export function evaluationGateColor(value: string) {
  const colors: Record<string, string> = {
    passed: "green",
    ready: "blue",
    warning: "gold",
    failed: "red",
  };

  return colors[value] || "default";
}
