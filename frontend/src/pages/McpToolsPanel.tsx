import { ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Space, Switch, Table, Tabs, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { McpToolItem, McpToolsResponse } from "../api";
import { Paragraph, Text, Title, RiskTag, formatTime, StatusTag } from "../workspace/shared";
import { ConnectorStatusTag } from "../components/ConnectorStatusTag";
import { SchemaTable } from "../components/SchemaTable";

export function McpToolsPanel({
  tools,
  summary,
  loading,
  checkingId,
  updatingId,
  refresh,
  toggle,
  checkHealth,
}: {
  tools: McpToolItem[];
  summary: McpToolsResponse["summary"] | null;
  loading: boolean;
  checkingId: string;
  updatingId: string;
  refresh: () => void;
  toggle: (item: McpToolItem, enabled: boolean) => void;
  checkHealth: (item: McpToolItem) => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="connectorMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-blue">
            <Text type="secondary">MCP 工具</Text>
            <Title level={3}>{summary?.total ?? tools.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-green">
            <Text type="secondary">已启用</Text>
            <Title level={3}>{summary?.enabled ?? tools.filter((item) => item.enabled).length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-amber">
            <Text type="secondary">高风险</Text>
            <Title level={3}>{summary?.high_risk ?? tools.filter((item) => item.risk_level === "high").length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-purple">
            <Text type="secondary">MCP Server</Text>
            <Title level={3}>{summary?.servers ?? new Set(tools.map((item) => item.server_name)).size}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="MCP 工具管理"
        subTitle="MCP 只作为工具层；高风险工具必须经过 Skill Executor、权限、审批和审计后才能执行"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
            刷新
          </Button>
        }
      >
        <Table<McpToolItem>
          rowKey="id"
          loading={loading}
          dataSource={tools}
          scroll={{ x: 1280 }}
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          locale={{ emptyText: <Empty description="暂无 MCP 工具" /> }}
          columns={[
            {
              title: "工具",
              dataIndex: "label",
              width: 260,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{record.label}</Text>
                  <Text type="secondary" className="runRecordMono">{record.tool_id}</Text>
                </Space>
              ),
            },
            {
              title: "Server / Tool",
              width: 230,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordMono">{record.server_name}</Text>
                  <Text className="runRecordMono">{record.tool_name}</Text>
                </Space>
              ),
            },
            {
              title: "类别",
              dataIndex: "category",
              width: 120,
              render: (value) => <Tag color="blue">{String(value)}</Tag>,
            },
            {
              title: "风险",
              dataIndex: "risk_level",
              width: 105,
              render: (value) => <RiskTag value={String(value)} />,
            },
            {
              title: "允许岗位",
              dataIndex: "position_scope_labels",
              width: 210,
              render: (value: string[]) => (
                <Space size={[4, 4]} wrap>
                  {(value || []).map((item) => <Tag color="purple" key={item}>{item}</Tag>)}
                </Space>
              ),
            },
            {
              title: "模式",
              dataIndex: "execution_mode",
              width: 160,
              render: (value, record) => (
                <Space direction="vertical" size={2}>
                  <Text className="runRecordMono">{String(value)}</Text>
                  {record.requires_approval ? <Tag color="gold">需要审批/确认</Tag> : <Tag>无需审批</Tag>}
                </Space>
              ),
            },
            {
              title: "启用",
              dataIndex: "enabled",
              width: 110,
              render: (_, record) => (
                <Switch
                  size="small"
                  checked={record.enabled}
                  loading={updatingId === record.id}
                  onChange={(checked) => toggle(record, checked)}
                />
              ),
            },
            {
              title: "健康",
              dataIndex: "health_status",
              width: 150,
              render: (_, record) => (
                <Space direction="vertical" size={2}>
                  <ConnectorStatusTag status={record.health_status} />
                  <Text type="secondary">{formatTime(record.last_checked_at)}</Text>
                </Space>
              ),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 120,
              render: (_, record) => (
                <Button size="small" onClick={() => checkHealth(record)} loading={checkingId === record.id}>
                  检查
                </Button>
              ),
            },
          ]}
          expandable={{
            expandedRowRender: (record) => (
              <Space direction="vertical" size={12} className="pageStack">
                <Paragraph>{record.description}</Paragraph>
                <Space size={[6, 6]} wrap>
                  <StatusTag value={record.status} />
                  <RiskTag value={record.risk_level} />
                  <Tag color="blue">{record.execution_mode}</Tag>
                  {record.supports_real_health_check ? <Tag color="green">支持健康检查</Tag> : <Tag>无健康检查</Tag>}
                </Space>
                <Row gutter={[12, 12]}>
                  <Col xs={24} lg={12}>
                    <div className="connectorRuleList">
                      <Text strong>安全规则</Text>
                      {record.safety_rules.map((item) => (
                        <div className="connectorRuleItem" key={item}>{item}</div>
                      ))}
                    </div>
                  </Col>
                  <Col xs={24} lg={12}>
                    <div className="connectorRuleList">
                      <Text strong>业务示例</Text>
                      <div className="connectorRuleItem">{record.example}</div>
                      <Text type="secondary">{record.health_message}</Text>
                    </div>
                  </Col>
                </Row>
                <Tabs
                  size="small"
                  items={[
                    {
                      key: "input",
                      label: `输入 ${record.input_schema.length}`,
                      children: <SchemaTable items={record.input_schema} />,
                    },
                    {
                      key: "output",
                      label: `输出 ${record.output_schema.length}`,
                      children: <SchemaTable items={record.output_schema} />,
                    },
                  ]}
                />
              </Space>
            ),
          }}
        />
      </ProCard>
    </Space>
  );
}
