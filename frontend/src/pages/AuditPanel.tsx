import { SearchOutlined } from "@ant-design/icons";
import { Button, Empty, Input, Select, Space, Table, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { Position } from "../api";
import { type AuditLog } from "../workspace/types";
import { EllipsisText, isPosition, positionLabel, Paragraph, Text, Title } from "../workspace/shared";

export function AuditPanel({
  logs,
  actionFilter,
  setActionFilter,
  resourceFilter,
  setResourceFilter,
  positionFilter,
  setPositionFilter,
  refreshLogs,
}: {
  logs: AuditLog[];
  actionFilter: string;
  setActionFilter: (value: string) => void;
  resourceFilter: string;
  setResourceFilter: (value: string) => void;
  positionFilter: Position | "all";
  setPositionFilter: (value: Position | "all") => void;
  refreshLogs: () => void;
}) {
  const normalizedActionFilter = actionFilter.trim().toLowerCase();
  const visibleLogs = normalizedActionFilter
    ? logs.filter((item) => {
        const searchable = `${item.action} ${item.actionLabel}`.toLowerCase();
        return searchable.includes(normalizedActionFilter);
      })
    : logs;

  return (
    <ProCard
      title="审计日志"
      bordered
      extra={
        <Space size={8} wrap>
          <Input
            size="small"
            value={actionFilter}
            placeholder="动作筛选"
            onChange={(event) => setActionFilter(event.target.value)}
            style={{ width: 180 }}
          />
          <Input
            size="small"
            value={resourceFilter}
            placeholder="资源类型"
            onChange={(event) => setResourceFilter(event.target.value)}
            style={{ width: 120 }}
          />
          <Select
            size="small"
            value={positionFilter}
            onChange={setPositionFilter}
            style={{ width: 130 }}
            options={[
              { label: "全部岗位", value: "all" },
              { label: "运营", value: "operations" },
              { label: "客服", value: "customer_service" },
              { label: "财务", value: "finance" },
            ]}
          />
          <Button size="small" icon={<SearchOutlined />} onClick={refreshLogs}>
            查询
          </Button>
        </Space>
      }
    >
      <Table<AuditLog>
        rowKey="id"
        dataSource={visibleLogs}
        locale={{ emptyText: <Empty description="暂无审计日志" /> }}
        scroll={{ x: 980 }}
        columns={[
          { title: "动作", dataIndex: "actionLabel", width: 260, ellipsis: true, render: (_, record) => <AuditActionText record={record} /> },
          { title: "资源", dataIndex: "resourceTypeLabel", width: 150, ellipsis: true, render: (_, record) => <AuditResourceTypeText record={record} /> },
          { title: "操作者", dataIndex: "actor", width: 160, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
          {
            title: "岗位",
            dataIndex: "position",
            width: 100,
            render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
          },
          { title: "时间", dataIndex: "createdAt", width: 160 },
          { title: "资源 ID", dataIndex: "resourceId", width: 220, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
        ]}
      />
    </ProCard>
  );
}

export function AuditActionText({ record }: { record: AuditLog }) {
  return (
    <Tooltip title={`原始动作：${record.action}`}>
      <Text className="tableEllipsisText" strong>
        {record.actionLabel}
      </Text>
    </Tooltip>
  );
}

export function AuditResourceTypeText({ record }: { record: AuditLog }) {
  return (
    <Tooltip title={`原始类型：${record.resourceType}`}>
      <Text className="tableEllipsisText">{record.resourceTypeLabel}</Text>
    </Tooltip>
  );
}
