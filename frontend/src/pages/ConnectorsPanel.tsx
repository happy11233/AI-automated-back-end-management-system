import { useState } from "react";
import { ApiOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Input, Row, Select, Space, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { ConnectorItem, ConnectorsResponse } from "../api";
import { Paragraph, Text, Title } from "../workspace/shared";
import { ConnectorStatusTag } from "../components/ConnectorStatusTag";

export function ConnectorsPanel({
  connectors,
  summary,
  loading,
  refreshConnectors,
  openDetail,
}: {
  connectors: ConnectorItem[];
  summary: ConnectorsResponse["summary"] | null;
  loading: boolean;
  refreshConnectors: () => void;
  openDetail: (connectorId: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const filteredConnectors = connectors.filter(
    (item) =>
      `${item.label} ${item.category} ${item.description}`
        .toLowerCase()
        .includes(search.trim().toLowerCase()) &&
      (statusFilter === "all" ||
        (statusFilter === "healthy" && item.status === "healthy") ||
        (statusFilter === "attention" && !["healthy", "disabled"].includes(item.status)) ||
        (statusFilter === "disabled" && !item.active)),
  );
  const categories = Array.from(new Set(filteredConnectors.map((item) => item.category))).filter(Boolean);

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="connectorMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-blue">
            <Text type="secondary">连接器</Text>
            <Title level={3}>{summary?.total ?? connectors.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-purple">
            <Text type="secondary">已配置</Text>
            <Title level={3}>
              {summary?.configured ?? connectors.filter((item) => item.configured).length}
            </Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-green">
            <Text type="secondary">健康</Text>
            <Title level={3}>
              {summary?.healthy ?? connectors.filter((item) => item.status === "healthy").length}
            </Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-amber">
            <Text type="secondary">待配置</Text>
            <Title level={3}>
              {summary?.needs_config ?? connectors.filter((item) => item.status === "not_configured").length}
            </Title>
          </Card>
        </Col>
      </Row>

      <div className="workspaceFilterBar">
        <Input
          aria-label="搜索连接器"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="搜索连接器名称或类别"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <Select
          aria-label="连接器状态"
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { label: "全部状态", value: "all" },
            { label: "健康", value: "healthy" },
            { label: "需关注", value: "attention" },
            { label: "已暂停", value: "disabled" },
          ]}
        />
        <Text type="secondary">{filteredConnectors.length} 个连接器</Text>
      </div>
      <ProCard
        title="系统连接器"
        subTitle="集中查看外部系统连接、真实健康状态、配置掩码、资源映射和岗位权限范围"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshConnectors} loading={loading}>
            刷新
          </Button>
        }
      >
        <Space direction="vertical" size={16} className="pageStack">
          {!categories.length && <Empty description="没有匹配的连接器" />}
          {categories.map((category) => (
            <div key={category} className="connectorCategoryBlock">
              <Space size={8} className="connectorCategoryTitle">
                <Tag color="blue">{category}</Tag>
                <Text type="secondary">
                  {filteredConnectors.filter((item) => item.category === category).length} 个连接器
                </Text>
              </Space>
              <Row gutter={[12, 12]}>
                {filteredConnectors
                  .filter((item) => item.category === category)
                  .map((connector) => (
                    <Col xs={24} lg={12} xl={8} key={connector.id} className="connectorCardCol">
                      <Card size="small" className="contextCard connectorCard">
                        <div className="connectorCardBody">
                          <div className="connectorHeader">
                            <Space size={8} className="connectorTitleWrap">
                              <ApiOutlined />
                              <Tooltip title={connector.description} placement="topLeft">
                                <Text strong className="connectorTitle tooltipTitle">
                                  {connector.label}
                                </Text>
                              </Tooltip>
                            </Space>
                            <ConnectorStatusTag status={connector.status} />
                          </div>
                          <div className="connectorMetaGrid">
                            <div>
                              <Text type="secondary">鉴权</Text>
                              <Text strong>{connector.auth_type}</Text>
                            </div>
                            <div>
                              <Text type="secondary">管理范围</Text>
                              <Text strong>{connector.managed_by}</Text>
                            </div>
                            <div>
                              <Text type="secondary">资源</Text>
                              <Text strong>{connector.resources.length} 项</Text>
                            </div>
                            <div>
                              <Text type="secondary">真实健康检查</Text>
                              <Text strong>{connector.supports_real_health_check ? "已接入" : "未接入"}</Text>
                            </div>
                          </div>
                          <Space size={[6, 6]} wrap className="connectorTagList">
                            {connector.position_scope_labels.map((item) => (
                              <Tag key={`${connector.id}-${item}`} color="purple">
                                {item}
                              </Tag>
                            ))}
                          </Space>
                          <Paragraph className="connectorHealthMessage">{connector.health_message}</Paragraph>
                          <div className="connectorFooter">
                            <Button size="small" type="primary" onClick={() => openDetail(connector.id)}>
                              详情
                            </Button>
                          </div>
                        </div>
                      </Card>
                    </Col>
                  ))}
              </Row>
            </div>
          ))}
        </Space>
      </ProCard>
    </Space>
  );
}
