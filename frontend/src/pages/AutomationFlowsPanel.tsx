import React from "react";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Select, Space, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { AutomationFlowItem, ErpResourceItem } from "../api";
import { type Role, type AutomationFlowFilterState } from "../workspace/types";
import { Paragraph, Text, Title, StatusTag } from "../workspace/shared";

export function AutomationFlowsPanel({
  role,
  flows,
  filters,
  setFilters,
  loading,
  refreshFlows,
  openDetail,
}: {
  role: Role;
  flows: AutomationFlowItem[];
  filters: AutomationFlowFilterState;
  setFilters: React.Dispatch<React.SetStateAction<AutomationFlowFilterState>>;
  loading: boolean;
  refreshFlows: () => void;
  openDetail: (flowId: string) => void;
}) {
  const enabledCount = flows.filter((item) => item.status === "enabled").length;
  const categories = Array.from(new Set(flows.map((item) => item.category))).filter(Boolean);
  const erpResourceCount = new Set(
    flows.flatMap((item) => item.allowed_erp_resources.map((resource) => resource.resource)),
  ).size;
  const approvalCount = flows.filter((item) => item.approval_policy.includes("审批")).length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="flowConfigMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">流程总数</Text>
            <Title level={3}>{flows.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">已发布</Text>
            <Title level={3}>{enabledCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">ERP 资源</Text>
            <Title level={3}>{erpResourceCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">审批策略</Text>
            <Title level={3}>{approvalCount}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="自动化流程配置"
        subTitle={role === "admin" ? "管理员查看全平台只读流程定义" : "当前账号只能查看自己岗位的流程定义"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshFlows} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className={role === "admin" ? "flowConfigFilterGrid admin" : "flowConfigFilterGrid"}>
          {role === "admin" ? (
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
          ) : null}
          <Select
            size="small"
            allowClear
            value={filters.category || undefined}
            placeholder="流程类别"
            onChange={(value) => setFilters((current) => ({ ...current, category: value || "" }))}
            options={categories.map((item) => ({ label: item, value: item }))}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshFlows} loading={loading}>
            查询
          </Button>
        </div>

        <Table<AutomationFlowItem>
          rowKey="id"
          loading={loading}
          dataSource={flows}
          className="flowConfigTable"
          scroll={{ x: 1160 }}
          locale={{ emptyText: <Empty description="暂无流程配置" /> }}
          columns={[
            {
              title: "流程",
              dataIndex: "name",
              width: 230,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="flowConfigCellStack">
                  <Text strong className="flowConfigText">{value}</Text>
                  <Text type="secondary" className="flowConfigMono">{record.app_id}</Text>
                </Space>
              ),
            },
            {
              title: "岗位",
              dataIndex: "position_label",
              width: 96,
              render: (value, record) => (
                <Tag color={record.position ? "purple" : "blue"}>{String(value)}</Tag>
              ),
            },
            {
              title: "类别",
              dataIndex: "category",
              width: 130,
              render: (value) => <Text className="flowConfigText">{String(value)}</Text>,
            },
            {
              title: "入口",
              dataIndex: "entrypoint",
              width: 210,
              render: (value) => <Text className="flowConfigMono">{String(value)}</Text>,
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 92,
              render: (value) => <StatusTag value={String(value)} />,
            },
            {
              title: "版本",
              dataIndex: "version",
              width: 110,
              render: (value) => <Text className="flowConfigMono">{String(value)}</Text>,
            },
            {
              title: "允许资源",
              dataIndex: "allowed_erp_resources",
              width: 170,
              render: (value: ErpResourceItem[]) => (
                <Space size={[4, 4]} wrap>
                  {value.length ? (
                    <>
                      <Tag color="geekblue">{value.length} 项</Tag>
                      {value.slice(0, 2).map((item) => (
                        <Tag key={item.resource}>{item.label}</Tag>
                      ))}
                    </>
                  ) : (
                    <Text type="secondary">无 ERP 资源</Text>
                  )}
                </Space>
              ),
            },
            {
              title: "说明",
              dataIndex: "description",
              width: 260,
              render: (value) => <Text className="flowConfigPreview">{String(value)}</Text>,
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 96,
              render: (value) => (
                <Button size="small" type="link" onClick={() => openDetail(String(value))}>
                  详情
                </Button>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}
