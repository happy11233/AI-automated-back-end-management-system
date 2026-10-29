import { ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Segmented, Space, Table, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { Position, PlatformExecutionTaskItem } from "../api";
import { type Role, type PlatformExecutionTaskFilterState } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  positionLabel,
  platformTaskDraftTitle,
  shortTaskId,
  platformActionTypeLabel,
  platformTaskPosition,
  isPosition,
  PlatformExecutionTaskStatusTag,
  formatTime,
  canRetryPlatformTask,
} from "../workspace/shared";

export function PlatformExecutionTasksPanel({
  role,
  position,
  tasks,
  filters,
  onStatusChange,
  loading,
  retryingTaskId,
  refreshTasks,
  openDetail,
  retryTask,
}: {
  role: Role;
  position: Position | null;
  tasks: PlatformExecutionTaskItem[];
  filters: PlatformExecutionTaskFilterState;
  onStatusChange: (status: PlatformExecutionTaskFilterState["status"]) => void;
  loading: boolean;
  retryingTaskId: string;
  refreshTasks: () => void;
  openDetail: (taskId: string) => void;
  retryTask: (taskId: string) => void;
}) {
  const queuedCount = tasks.filter((item) => item.status === "queued" || item.status === "dispatching").length;
  const waitingCount = tasks.filter((item) => item.status === "waiting_callback").length;
  const succeededCount = tasks.filter((item) => item.status === "succeeded").length;
  const failedCount = tasks.filter((item) => item.status === "failed").length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="platformTaskMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-blue">
            <Text type="secondary">队列中</Text>
            <Title level={3}>{queuedCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-amber">
            <Text type="secondary">等待回调</Text>
            <Title level={3}>{waitingCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-green">
            <Text type="secondary">成功</Text>
            <Title level={3}>{succeededCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-red">
            <Text type="secondary">失败</Text>
            <Title level={3}>{failedCount}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="执行任务中心"
        subTitle={role === "admin" ? "查看外部执行器任务队列、回调和重试状态" : position ? `${positionLabel(position)}岗位外部执行任务` : "当前账号未绑定岗位"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshTasks} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="platformTaskToolbar">
          <Segmented
            size="small"
            value={filters.status}
            onChange={(value) => onStatusChange(value as PlatformExecutionTaskFilterState["status"])}
            options={[
              { label: "全部", value: "all" },
              { label: "队列中", value: "queued" },
              { label: "派发中", value: "dispatching" },
              { label: "等回调", value: "waiting_callback" },
              { label: "成功", value: "succeeded" },
              { label: "失败", value: "failed" },
            ]}
          />
        </div>

        <Table<PlatformExecutionTaskItem>
          rowKey="id"
          loading={loading}
          dataSource={tasks}
          className="platformTaskTable"
          scroll={{ x: 1180 }}
          locale={{ emptyText: <Empty description="暂无执行任务" /> }}
          columns={[
            {
              title: "任务",
              dataIndex: "id",
              width: 248,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{platformTaskDraftTitle(record)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortTaskId(record.id)}</Text>
                </Space>
              ),
            },
            {
              title: "动作类型",
              dataIndex: "action_type",
              width: 158,
              render: (value) => <Tag color="blue">{platformActionTypeLabel(String(value))}</Tag>,
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 92,
              render: (_, record) => {
                const value = platformTaskPosition(record);
                return isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-";
              },
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 118,
              render: (value) => <PlatformExecutionTaskStatusTag value={String(value)} />,
            },
            {
              title: "外部引用",
              dataIndex: "external_reference",
              width: 170,
              render: (value) => <Text className="runRecordMono">{value ? String(value) : "-"}</Text>,
            },
            {
              title: "尝试",
              dataIndex: "attempt_count",
              width: 96,
              render: (_, record) => `${record.attempt_count}/${record.max_attempts}`,
            },
            {
              title: "错误",
              dataIndex: "last_error",
              width: 230,
              render: (value) => value ? (
                <Tooltip title={String(value)}>
                  <Text className="runRecordPreview" type="danger">{String(value)}</Text>
                </Tooltip>
              ) : "-",
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 150,
              render: (_, record) => (
                <Space size={6} wrap className="platformTaskActionCell">
                  <Button size="small" type="link" onClick={() => openDetail(record.id)}>
                    详情
                  </Button>
                  <Button
                    size="small"
                    disabled={!canRetryPlatformTask(record)}
                    loading={retryingTaskId === record.id}
                    onClick={() => retryTask(record.id)}
                  >
                    重试
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
