import React from "react";
import { ReloadOutlined, SendOutlined } from "@ant-design/icons";
import { Button, Col, Empty, Input, Row, Segmented, Select, Space, Table, Tag, Tooltip } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { FeedbackCategory, FeedbackItem, FeedbackPriority, FeedbackSummary } from "../api";
import { type FeedbackFilterState, type FeedbackFormState } from "../workspace/types";
import { FeedbackMetricRow } from "../components/FeedbackMetricRow";
import {
  Paragraph,
  Text,
  Title,
  TextArea,
  FeedbackStatusTag,
  FeedbackPriorityTag,
  formatTime,
} from "../workspace/shared";

export const feedbackCategoryOptions: Array<{ label: FeedbackCategory; value: FeedbackCategory }> = [
  { label: "功能建议", value: "功能建议" },
  { label: "体验问题", value: "体验问题" },
  { label: "数据问题", value: "数据问题" },
  { label: "自动化需求", value: "自动化需求" },
  { label: "权限流程", value: "权限流程" },
  { label: "其他", value: "其他" },
];

export const feedbackPriorityOptions: Array<{ label: string; value: FeedbackPriority }> = [
  { label: "普通", value: "normal" },
  { label: "较低", value: "low" },
  { label: "较高", value: "high" },
  { label: "紧急", value: "urgent" },
];

export function FeedbackImprovementPanel({
  items,
  summary,
  filters,
  onStatusChange,
  form,
  setForm,
  loading,
  submitting,
  refreshFeedback,
  submitFeedback,
}: {
  items: FeedbackItem[];
  summary: FeedbackSummary;
  filters: FeedbackFilterState;
  onStatusChange: (status: FeedbackFilterState["status"]) => void;
  form: FeedbackFormState;
  setForm: React.Dispatch<React.SetStateAction<FeedbackFormState>>;
  loading: boolean;
  submitting: boolean;
  refreshFeedback: () => void;
  submitFeedback: () => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <FeedbackMetricRow summary={summary} />

      <ProCard
        title="提交反馈改进"
        subTitle="把平台不好用、重复操作仍然多、想新增的自动化流程提交给管理员处理"
        bordered
      >
        <Row gutter={[12, 12]} className="feedbackFormGrid">
          <Col xs={24} md={8} lg={6}>
            <Text type="secondary">反馈分类</Text>
            <Select<FeedbackCategory>
              className="fullWidthControl"
              value={form.category}
              options={feedbackCategoryOptions}
              onChange={(value) => setForm((current) => ({ ...current, category: value }))}
            />
          </Col>
          <Col xs={24} md={8} lg={6}>
            <Text type="secondary">优先级</Text>
            <Select<FeedbackPriority>
              className="fullWidthControl"
              value={form.priority}
              options={feedbackPriorityOptions}
              onChange={(value) => setForm((current) => ({ ...current, priority: value }))}
            />
          </Col>
          <Col xs={24} md={8} lg={12}>
            <Text type="secondary">标题</Text>
            <Input
              value={form.title}
              maxLength={120}
              placeholder="例如：财务工资表导出希望增加部门筛选"
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            />
          </Col>
          <Col xs={24}>
            <Text type="secondary">具体内容</Text>
            <TextArea
              rows={4}
              maxLength={3000}
              showCount
              value={form.description}
              placeholder="请写清楚出现在哪个页面、现在要手工做什么、希望 AI 或自动化帮你做到什么程度。"
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </Col>
          <Col xs={24}>
            <Space className="feedbackFormActions">
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={submitting}
                onClick={submitFeedback}
              >
                提交反馈
              </Button>
              <Button icon={<ReloadOutlined />} onClick={refreshFeedback} loading={loading}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </ProCard>

      <ProCard
        title="我的反馈"
        subTitle="管理员完成后，这里会显示处理状态和完成说明"
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
          </Space>
        }
      >
        <Table<FeedbackItem>
          rowKey="id"
          loading={loading}
          dataSource={items}
          className="feedbackTable"
          scroll={{ x: 980 }}
          locale={{ emptyText: <Empty description="暂无反馈记录" /> }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              render: (value) => <FeedbackStatusTag value={String(value)} />,
            },
            {
              title: "反馈",
              dataIndex: "title",
              width: 320,
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
                <Tooltip title={String(value || "管理员处理完成后会显示说明")}>
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
              title: "完成时间",
              dataIndex: "completed_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}
