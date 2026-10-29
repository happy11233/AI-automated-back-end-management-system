import { useState } from "react";
import { ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Segmented, Space, Table, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { BusinessActionLoopItem, BusinessActionLoopResponse, Position } from "../api";
import { type Role, type View } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  positionLabel,
  shortDraftId,
  platformDraftTypeLabel,
  isPosition,
  formatTime,
  isWaitingPlatformTaskStatus,
  platformDraftWritebackLabel,
  platformDraftStatusLabel,
  platformExecutionTaskStatusLabel,
} from "../workspace/shared";

export function BusinessActionLoopPanel({
  role,
  position,
  data,
  loading,
  refreshLoop,
  openDraft,
  openTask,
  navigateToView,
}: {
  role: Role;
  position: Position | null;
  data: BusinessActionLoopResponse | null;
  loading: boolean;
  refreshLoop: () => void;
  openDraft: (draftId: string) => void;
  openTask: (taskId: string) => void;
  navigateToView: (view: View) => void;
}) {
  const summary = data?.summary || {
    total: 0,
    pending_review: 0,
    waiting_external: 0,
    succeeded: 0,
    failed: 0,
    unread_notifications: 0,
  };
  const [stageFilter, setStageFilter] = useState("all");
  const items = data?.items || [];
  const visibleItems = items.filter(
    (item) =>
      stageFilter === "all" ||
      (stageFilter === "attention"
        ? ["failed", "rejected"].includes(item.stage)
        : item.stage === stageFilter),
  );

  return (
    <Space direction="vertical" className="pageStack">
      <Row gutter={[16, 16]} className="businessActionMetricRow">
        {[
          {
            title: "闭环总数",
            value: summary.total,
            tone: "blue",
            hint: <>未读通知 {summary.unread_notifications}</>,
          },
          { title: "待审核", value: summary.pending_review, tone: "amber", hint: <>待确认后继续执行</> },
          {
            title: "已完成",
            value: summary.succeeded,
            tone: "green",
            hint: <>外部执行中 {summary.waiting_external}</>,
          },
          { title: "失败", value: summary.failed, tone: "red", hint: <>关注异常并处理</> },
        ].map((item) => (
          <Col xs={12} xl={6} key={item.title}>
            <Card size="small" className={"runRecordMetricCard metric-" + item.tone}>
              <Text type="secondary">{item.title}</Text>
              <Title level={3}>{item.value}</Title>
              <Text type="secondary">{item.hint}</Text>
            </Card>
          </Col>
        ))}
      </Row>
      <div className="workspaceFilterBar workspaceStatusFilters">
        <Segmented
          aria-label="业务闭环状态"
          value={stageFilter}
          onChange={(value) => setStageFilter(String(value))}
          options={[
            { label: "全部", value: "all" },
            { label: "待审核", value: "needs_review" },
            { label: "待发布", value: "ready_to_publish" },
            { label: "执行中", value: "external_running" },
            { label: "已完成", value: "done" },
            { label: "异常", value: "attention" },
          ]}
        />
      </div>
      <ProCard
        title="业务动作闭环"
        subTitle={
          role === "admin"
            ? "查看运营和客服 AI 触发后的草稿、审核、外部写回、发布或发送状态"
            : position
              ? `${positionLabel(position)}岗位业务动作状态`
              : "当前账号未绑定岗位"
        }
        bordered
        extra={
          <Space size={8} wrap>
            <Button size="small" onClick={() => navigateToView("platform_draft_review")}>
              草稿审核
            </Button>
            <Button size="small" onClick={() => navigateToView("platform_execution_tasks")}>
              执行任务
            </Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshLoop} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table<BusinessActionLoopItem>
          rowKey="draft_id"
          loading={loading}
          dataSource={visibleItems}
          className="businessActionLoopTable"
          scroll={{ x: 1120 }}
          locale={{ emptyText: <Empty description="暂无业务动作闭环" /> }}
          columns={[
            {
              title: "业务动作",
              dataIndex: "title",
              width: 280,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">
                    {String(value)}
                  </Text>
                  <Text type="secondary" className="runRecordMono">
                    {shortDraftId(record.draft_id)}
                  </Text>
                </Space>
              ),
            },
            {
              title: "类型",
              dataIndex: "draft_type",
              width: 130,
              render: (value) => (
                <Tag color={value === "listing" ? "blue" : "cyan"}>
                  {platformDraftTypeLabel(String(value))}
                </Tag>
              ),
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 96,
              render: (value) => (isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-"),
            },
            {
              title: "闭环进度",
              dataIndex: "stage",
              width: 420,
              render: (_, record) => <BusinessActionLoopTimeline item={record} />,
            },
            {
              title: "外部引用",
              dataIndex: "external_reference",
              width: 170,
              render: (value) => <Text className="runRecordMono">{value ? String(value) : "-"}</Text>,
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "draft_id",
              fixed: "right",
              width: 170,
              render: (_, record) => (
                <Space size={6} wrap className="businessActionLoopActions">
                  <Button size="small" type="link" onClick={() => openDraft(record.draft_id)}>
                    草稿
                  </Button>
                  <Button
                    size="small"
                    disabled={!record.latest_task_id}
                    onClick={() => record.latest_task_id && openTask(record.latest_task_id)}
                  >
                    任务
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

export function BusinessActionLoopTimeline({ item }: { item: BusinessActionLoopItem }) {
  const timelineItems = businessActionLoopTimelineItems(item);
  const nextText = item.stage === "failed"
    ? item.last_error || item.writeback_message || item.next_action
    : item.next_action;

  return (
    <Space direction="vertical" size={8} className="businessLoopTimelineWrap">
      <Space size={6} wrap>
        <Tag color={businessActionStageColor(item.stage)}>{item.stage_label}</Tag>
        {item.latest_action_label ? <Tag color="blue">{item.latest_action_label}</Tag> : null}
      </Space>
      <div className="businessLoopTimeline">
        {timelineItems.map((step) => (
          <Tooltip key={step.key} title={step.description}>
            <span className={`businessLoopTimelineStep ${step.tone}`}>
              <span className="businessLoopTimelineDot" />
              <span className="businessLoopTimelineLabel">{step.label}</span>
            </span>
          </Tooltip>
        ))}
      </div>
      <Text className={item.stage === "failed" ? "runRecordPreview dangerText" : "runRecordPreview"}>
        {nextText}
      </Text>
    </Space>
  );
}

export function businessActionStageColor(value: string) {
  const colors: Record<string, string> = {
    draft_saved: "default",
    needs_review: "gold",
    ready_to_publish: "blue",
    external_running: "processing",
    done: "green",
    failed: "red",
    rejected: "default",
  };

  return colors[value] ?? "default";
}

export function businessActionLoopTimelineItems(item: BusinessActionLoopItem) {
  const draftDone = ["pending_review", "approved", "published", "rejected"].includes(item.draft_status);
  const reviewDone = ["approved", "published"].includes(item.draft_status);
  const executionActive = isWaitingPlatformTaskStatus(item.latest_task_status || "");
  const executionDone = item.latest_task_status === "succeeded" || item.draft_status === "published";
  const failed = item.stage === "failed";
  const rejected = item.stage === "rejected";

  return [
    {
      key: "draft",
      label: "草稿",
      description: item.writeback_status_label || platformDraftWritebackLabel(item.writeback_status),
      tone: failed && item.writeback_status === "failed" ? "danger" : draftDone ? "done" : "pending",
    },
    {
      key: "review",
      label: "审核",
      description: item.draft_status_label || platformDraftStatusLabel(item.draft_status),
      tone: rejected ? "danger" : reviewDone ? "done" : item.draft_status === "pending_review" ? "active" : "pending",
    },
    {
      key: "execute",
      label: "执行",
      description: item.latest_task_status_label || (item.latest_task_status ? platformExecutionTaskStatusLabel(item.latest_task_status) : "等待发起外部执行"),
      tone: failed && item.latest_task_status === "failed" ? "danger" : executionDone ? "done" : executionActive ? "active" : "pending",
    },
    {
      key: "finish",
      label: "完成",
      description: item.external_reference ? `外部引用：${item.external_reference}` : "等待外部平台返回最终结果",
      tone: item.stage === "done" ? "done" : failed ? "danger" : "pending",
    },
  ];
}
