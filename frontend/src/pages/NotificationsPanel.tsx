import { ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Segmented, Space, Table, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { NotificationItem, NotificationSummary } from "../api";
import { type NotificationFilterState } from "../workspace/types";
import { Paragraph, Text, Title, shortTaskId, formatTime } from "../workspace/shared";

export function NotificationsPanel({
  notifications,
  summary,
  filters,
  onFiltersChange,
  loading,
  markingNotificationId,
  markingAllRead,
  refreshNotifications,
  markRead,
  markAllRead,
  openResource,
}: {
  notifications: NotificationItem[];
  summary: NotificationSummary;
  filters: NotificationFilterState;
  onFiltersChange: (filters: NotificationFilterState) => void;
  loading: boolean;
  markingNotificationId: string;
  markingAllRead: boolean;
  refreshNotifications: () => void;
  markRead: (notificationId: string) => void;
  markAllRead: () => void;
  openResource: (notification: NotificationItem) => void;
}) {
  const filteredTotal = filters.status === "unread" ? summary.unread_count
    : filters.status === "read" ? summary.read_count : summary.total_count;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="notificationMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-blue">
            <Text type="secondary">未读</Text>
            <Title level={3}>{summary.unread_count}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-green">
            <Text type="secondary">已读</Text>
            <Title level={3}>{summary.read_count}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-purple">
            <Text type="secondary">关联资源</Text>
            <Title level={3}>{summary.resource_count}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-amber">
            <Text type="secondary">通知总数</Text>
            <Title level={3}>{summary.total_count}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="通知中心"
        subTitle="接收草稿审核、外部执行器回调、重试结果等业务提醒"
        bordered
        extra={
          <Space size={8} wrap>
            <Button size="small" onClick={markAllRead} loading={markingAllRead} disabled={!summary.unread_count || loading || Boolean(markingNotificationId)}>
              全部已读
            </Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshNotifications} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <div className="notificationToolbar">
          <Segmented
            size="small"
            value={filters.status}
            onChange={(value) => onFiltersChange({ ...filters, status: value as NotificationFilterState["status"], page: 1 })}
            options={[
              { label: "全部", value: "all" },
              { label: "未读", value: "unread" },
              { label: "已读", value: "read" },
            ]}
          />
        </div>

        <Table<NotificationItem>
          rowKey="id"
          loading={loading}
          dataSource={notifications}
          className="notificationTable"
          scroll={{ x: 1040 }}
          pagination={{
            current: filters.page,
            pageSize: filters.pageSize,
            total: filteredTotal,
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50],
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => onFiltersChange({
              ...filters,
              page: pageSize === filters.pageSize ? page : 1,
              pageSize,
            }),
          }}
          locale={{ emptyText: <Empty description={filters.status === "unread" ? "暂无未读通知" : filters.status === "read" ? "暂无已读通知" : "暂无通知"} /> }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 96,
              render: (value) => <NotificationStatusTag value={String(value)} />,
            },
            {
              title: "通知",
              dataIndex: "title",
              width: 280,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong={record.status === "unread"} className="runRecordText">{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{notificationTypeLabel(record.type)}</Text>
                </Space>
              ),
            },
            {
              title: "内容",
              dataIndex: "body",
              render: (value) => (
                <Tooltip title={String(value || "")}>
                  <Text className="runRecordPreview">{String(value || "-")}</Text>
                </Tooltip>
              ),
            },
            {
              title: "关联资源",
              dataIndex: "resource_id",
              width: 180,
              render: (_, record) => record.resource_id ? (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordText">{notificationResourceLabel(record.resource_type)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortTaskId(record.resource_id)}</Text>
                </Space>
              ) : "-",
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 160,
              render: (_, record) => (
                <Space size={6} wrap className="notificationActionCell">
                  <Button
                    size="small"
                    type="link"
                    disabled={!record.resource_id}
                    onClick={() => openResource(record)}
                  >
                    查看
                  </Button>
                  <Button
                    size="small"
                    disabled={record.status === "read" || markingAllRead || Boolean(markingNotificationId)}
                    loading={markingNotificationId === record.id}
                    onClick={() => markRead(record.id)}
                  >
                    已读
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

export function NotificationStatusTag({ value }: { value: string }) {
  return <Tag color={value === "unread" ? "blue" : "default"}>{value === "unread" ? "未读" : "已读"}</Tag>;
}

export function notificationTypeLabel(value: string) {
  const labels: Record<string, string> = {
    "feedback.submitted": "新反馈",
    "feedback.completed": "反馈完成",
    platform_draft_review: "草稿审核",
    platform_execution_task: "执行任务",
    platform_execution_succeeded: "执行成功",
    platform_execution_failed: "执行失败",
    agent_event: "Agent 任务",
    platform_execution_waiting: "等待回调",
    platform_execution_retry: "任务重试",
  };

  return labels[value] ?? (value || "系统通知");
}

export function notificationResourceLabel(value: string | null) {
  const labels: Record<string, string> = {
    feedback: "反馈",
    platform_execution_task: "执行任务",
    platform_draft: "平台草稿",
    run_record: "运行记录",
    agent: "Agent 任务",
  };

  return value ? labels[value] ?? value : "-";
}
