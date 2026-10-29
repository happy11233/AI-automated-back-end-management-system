import React from "react";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Collapse, Empty, Input, Row, Select, Space, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { RunRecordItem } from "../api";
import { type Role, type RunRecordFilterState } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  StatusTag,
  isPosition,
  positionLabel,
  formatDuration,
  formatTime,
} from "../workspace/shared";

export function RunRecordsPanel({
  role,
  records,
  filters,
  setFilters,
  loading,
  refreshRecords,
  openDetail,
}: {
  role: Role;
  records: RunRecordItem[];
  filters: RunRecordFilterState;
  setFilters: React.Dispatch<React.SetStateAction<RunRecordFilterState>>;
  loading: boolean;
  refreshRecords: () => void;
  openDetail: (runId: string) => void;
}) {
  const statusCounts = {
    succeeded: records.filter((item) => item.status === "succeeded").length,
    failed: records.filter((item) => item.status === "failed").length,
    blocked: records.filter((item) => item.status === "blocked").length,
    running: records.filter((item) => item.status === "running").length,
  };

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="runRecordMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-blue">
            <Text type="secondary">记录总数</Text>
            <Title level={3}>{records.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-green">
            <Text type="secondary">成功</Text>
            <Title level={3}>{statusCounts.succeeded}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-red">
            <Text type="secondary">失败</Text>
            <Title level={3}>{statusCounts.failed}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-amber">
            <Text type="secondary">越权拦截</Text>
            <Title level={3}>{statusCounts.blocked}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="运行记录"
        subTitle={role === "admin" ? "管理员查看全平台脱敏摘要" : "当前账号只能查看自己的运行记录"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshRecords} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="workspaceFilterBar runRecordPrimaryFilters">
          <Select
            size="small"
            value={filters.status}
            onChange={(value) => setFilters((current) => ({ ...current, status: value }))}
            options={[
              { label: "全部状态", value: "all" },
              { label: "成功", value: "succeeded" },
              { label: "失败", value: "failed" },
              { label: "拦截", value: "blocked" },
              { label: "运行中", value: "running" },
            ]}
          />
          <Input
            size="small"
            value={filters.runType}
            placeholder="类型"
            onChange={(event) => setFilters((current) => ({ ...current, runType: event.target.value }))}
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
            onClick={refreshRecords}
            loading={loading}
          >
            查询
          </Button>
        </div>
        <Collapse
          className="workspaceAdvancedFilters"
          ghost
          defaultActiveKey={
            [filters.appId, filters.resourceType, filters.resourceId, filters.flowKey].filter(Boolean).length
              ? ["advanced"]
              : []
          }
          items={[
            {
              key: "advanced",
              label: (
                <>
                  高级筛选
                  {[filters.appId, filters.resourceType, filters.resourceId, filters.flowKey].filter(Boolean)
                    .length ? (
                    <Tag color="blue">
                      {
                        [filters.appId, filters.resourceType, filters.resourceId, filters.flowKey].filter(
                          Boolean,
                        ).length
                      }{" "}
                      项已设置
                    </Tag>
                  ) : null}
                </>
              ),
              children: (
                <div className="workspaceAdvancedGrid">
                  <Input
                    size="small"
                    value={filters.appId}
                    placeholder="应用 ID"
                    onChange={(event) => setFilters((current) => ({ ...current, appId: event.target.value }))}
                  />
                  <Input
                    size="small"
                    value={filters.resourceType}
                    placeholder="资源类型"
                    onChange={(event) =>
                      setFilters((current) => ({ ...current, resourceType: event.target.value }))
                    }
                  />
                  <Input
                    size="small"
                    value={filters.resourceId}
                    placeholder="资源 ID"
                    onChange={(event) =>
                      setFilters((current) => ({ ...current, resourceId: event.target.value }))
                    }
                  />
                  <Input
                    size="small"
                    value={filters.flowKey}
                    placeholder="流程 Key"
                    onChange={(event) =>
                      setFilters((current) => ({ ...current, flowKey: event.target.value }))
                    }
                  />
                  <Button
                    onClick={() =>
                      setFilters((current) => ({
                        ...current,
                        appId: "",
                        resourceType: "",
                        resourceId: "",
                        flowKey: "",
                      }))
                    }
                  >
                    清除高级条件
                  </Button>
                </div>
              ),
            },
          ]}
        />

        <Table<RunRecordItem>
          rowKey="id"
          loading={loading}
          dataSource={records}
          className="runRecordTable"
          scroll={{ x: 1260 }}
          locale={{ emptyText: <Empty description="暂无运行记录" /> }}
          columns={[
            {
              title: "应用",
              dataIndex: "app_name",
              width: 210,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">
                    {value}
                  </Text>
                  <Text type="secondary" className="runRecordMono">
                    {record.app_id}
                  </Text>
                </Space>
              ),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 92,
              render: (value) => <StatusTag value={String(value)} />,
            },
            {
              title: "类型",
              dataIndex: "run_type",
              width: 150,
              render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
            },
            {
              title: "流程版本",
              dataIndex: "flow_key",
              width: 210,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordMono">{value || "-"}</Text>
                  <Text type="secondary" className="runRecordMono">
                    {record.flow_version || "-"}
                  </Text>
                </Space>
              ),
            },
            {
              title: "用户/岗位",
              dataIndex: "username",
              width: 140,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text>{value || "-"}</Text>
                  {isPosition(record.position) ? (
                    <Tag color="purple">{positionLabel(record.position)}</Tag>
                  ) : (
                    <Tag>管理员</Tag>
                  )}
                </Space>
              ),
            },
            {
              title: "资源",
              dataIndex: "resource_id",
              width: 180,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text type="secondary">{record.resource_type || "-"}</Text>
                  <Text className="runRecordMono">{value || "-"}</Text>
                </Space>
              ),
            },
            {
              title: "摘要",
              dataIndex: "output_preview",
              width: 260,
              render: (value, record) => (
                <Text className="runRecordPreview">
                  {record.error_message || value || record.input_preview || "-"}
                </Text>
              ),
            },
            {
              title: "耗时",
              dataIndex: "duration_ms",
              width: 90,
              render: (value) => formatDuration(value),
            },
            {
              title: "步骤/产物",
              dataIndex: "step_count",
              width: 100,
              render: (value, record) => `${value}/${record.artifact_count}`,
            },
            {
              title: "时间",
              dataIndex: "started_at",
              width: 170,
              render: (value) => formatTime(value),
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
