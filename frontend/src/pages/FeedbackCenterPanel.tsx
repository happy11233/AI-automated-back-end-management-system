import { ReloadOutlined } from "@ant-design/icons";
import { Button, Empty, Segmented, Space, Table, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { FeedbackItem, FeedbackSummary } from "../api";
import { type FeedbackFilterState } from "../workspace/types";
import { FeedbackMetricRow } from "../components/FeedbackMetricRow";
import {
  FeedbackStatusTag,
  Paragraph,
  Text,
  Title,
  isPosition,
  positionLabel,
  FeedbackPriorityTag,
  formatTime,
} from "../workspace/shared";

export function FeedbackCenterPanel({
  items,
  summary,
  filters,
  onStatusChange,
  loading,
  completingFeedbackId,
  refreshFeedback,
  completeFeedback,
}: {
  items: FeedbackItem[];
  summary: FeedbackSummary;
  filters: FeedbackFilterState;
  onStatusChange: (status: FeedbackFilterState["status"]) => void;
  loading: boolean;
  completingFeedbackId: string;
  refreshFeedback: () => void;
  completeFeedback: (feedback: FeedbackItem) => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <FeedbackMetricRow summary={summary} />

      <ProCard
        title="反馈中心"
        subTitle="集中处理员工提交的平台问题、体验建议和自动化改进需求"
        bordered
        extra={
          <Space size={8} wrap>
            <Segmented
              size="small"
              value={filters.status}
              onChange={(value) => onStatusChange(value as FeedbackFilterState["status"])}
              options={[
                { label: "全部", value: "all" },
                { label: "待处理", value: "open" },
                { label: "已完成", value: "completed" },
              ]}
            />
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshFeedback} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table<FeedbackItem>
          rowKey="id"
          loading={loading}
          dataSource={items}
          className="feedbackTable"
          scroll={{ x: 1220 }}
          locale={{ emptyText: <Empty description="暂无员工反馈" /> }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              fixed: "left",
              render: (value) => <FeedbackStatusTag value={String(value)} />,
            },
            {
              title: "反馈内容",
              dataIndex: "title",
              width: 340,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Tooltip title={record.description}>
                    <Text strong className="runRecordText">{String(value || "-")}</Text>
                  </Tooltip>
                  <Text type="secondary" className="runRecordPreview">{record.description}</Text>
                </Space>
              ),
            },
            {
              title: "提交人",
              dataIndex: "username",
              width: 170,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordText">{record.display_name || record.username}</Text>
                  <Text type="secondary" className="runRecordMono">{record.username}</Text>
                </Space>
              ),
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 100,
              render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
            },
            {
              title: "分类",
              dataIndex: "category",
              width: 120,
              render: (value) => <Tag>{String(value || "-")}</Tag>,
            },
            {
              title: "优先级",
              dataIndex: "priority",
              width: 110,
              render: (value) => <FeedbackPriorityTag value={String(value)} />,
            },
            {
              title: "处理说明",
              dataIndex: "admin_note",
              render: (value) => (
                <Tooltip title={String(value || "")}>
                  <Text className="runRecordPreview">{String(value || "-")}</Text>
                </Tooltip>
              ),
            },
            {
              title: "提交时间",
              dataIndex: "created_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 130,
              render: (_, record) => (
                <Button
                  size="small"
                  type={record.status === "open" ? "primary" : "default"}
                  disabled={record.status !== "open"}
                  loading={completingFeedbackId === record.id}
                  onClick={() => completeFeedback(record)}
                >
                  {record.status === "open" ? "完成" : "已完成"}
                </Button>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}
