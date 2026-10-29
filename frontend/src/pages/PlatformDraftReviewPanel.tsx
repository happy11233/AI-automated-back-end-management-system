import React from "react";
import { CloudUploadOutlined, ReloadOutlined, SendOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Row, Segmented, Select, Space, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { Position, PlatformDraftItem } from "../api";
import { type Role, type PlatformDraftFilterState } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  positionLabel,
  shortDraftId,
  platformDraftTypeLabel,
  isPosition,
  PlatformDraftStatusTag,
  platformDraftWritebackLabel,
  formatTime,
  canReviewPlatformDraft,
  canRejectPlatformDraft,
  platformDraftPublishButtonLabel,
} from "../workspace/shared";

export function PlatformDraftReviewPanel({
  role,
  position,
  drafts,
  filters,
  setFilters,
  loading,
  actionKey,
  refreshDrafts,
  openDetail,
  reviewDraft,
  publishDraft,
}: {
  role: Role;
  position: Position | null;
  drafts: PlatformDraftItem[];
  filters: PlatformDraftFilterState;
  setFilters: React.Dispatch<React.SetStateAction<PlatformDraftFilterState>>;
  loading: boolean;
  actionKey: string;
  refreshDrafts: () => void;
  openDetail: (draftId: string) => void;
  reviewDraft: (draftId: string, decision: "approved" | "rejected") => void;
  publishDraft: (draftId: string) => void;
}) {
  const pendingCount = drafts.filter((item) => item.status === "pending_review").length;
  const approvedCount = drafts.filter((item) => item.status === "approved").length;
  const publishedCount = drafts.filter((item) => item.status === "published").length;
  const rejectedCount = drafts.filter((item) => item.status === "rejected").length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="platformDraftMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-amber">
            <Text type="secondary">待审核</Text>
            <Title level={3}>{pendingCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-green">
            <Text type="secondary">已通过</Text>
            <Title level={3}>{approvedCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-blue">
            <Text type="secondary">已发布/发送</Text>
            <Title level={3}>{publishedCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-red">
            <Text type="secondary">已驳回</Text>
            <Title level={3}>{rejectedCount}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="AI 草稿审核中心"
        subTitle={role === "admin" ? "管理员可审核全部岗位草稿" : position ? `${positionLabel(position)}岗位草稿发布闸门` : "当前账号未绑定岗位"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshDrafts} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="platformDraftToolbar">
          <Segmented
            size="small"
            value={filters.status}
            onChange={(value) => setFilters((current) => ({ ...current, status: value as PlatformDraftFilterState["status"] }))}
            options={[
              { label: "全部", value: "all" },
              { label: "待审核", value: "pending_review" },
              { label: "已通过", value: "approved" },
              { label: "已发布", value: "published" },
              { label: "已驳回", value: "rejected" },
            ]}
          />
          <Select
            size="small"
            className="platformDraftTypeSelect"
            value={filters.draftType}
            onChange={(value) => setFilters((current) => ({ ...current, draftType: value }))}
            options={[
              { label: "全部类型", value: "all" },
              { label: "Listing 草稿", value: "listing" },
              { label: "客服回复草稿", value: "customer_reply" },
            ]}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshDrafts} loading={loading}>
            查询
          </Button>
        </div>

        <Table<PlatformDraftItem>
          rowKey="id"
          loading={loading}
          dataSource={drafts}
          className="platformDraftTable"
          scroll={{ x: 1120 }}
          locale={{ emptyText: <Empty description="暂无平台草稿" /> }}
          columns={[
            {
              title: "草稿",
              dataIndex: "title",
              width: 260,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortDraftId(record.id)}</Text>
                </Space>
              ),
            },
            {
              title: "类型",
              dataIndex: "draft_type",
              width: 130,
              render: (value) => <Tag color={value === "listing" ? "blue" : "cyan"}>{platformDraftTypeLabel(String(value))}</Tag>,
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 96,
              render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
            },
            {
              title: "审核状态",
              dataIndex: "status",
              width: 118,
              render: (value) => <PlatformDraftStatusTag value={String(value)} />,
            },
            {
              title: "写回状态",
              dataIndex: "writeback_status",
              width: 140,
              render: (value) => <Tag color={platformDraftWritebackColor(String(value))}>{platformDraftWritebackLabel(String(value))}</Tag>,
            },
            {
              title: "目标",
              dataIndex: "external_target",
              width: 180,
              render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
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
              width: 220,
              render: (_, record) => (
                <Space size={6} wrap className="platformDraftActionCell">
                  <Button size="small" type="link" onClick={() => openDetail(record.id)}>
                    详情
                  </Button>
                  <Button
                    size="small"
                    disabled={!canReviewPlatformDraft(record)}
                    loading={actionKey === `${record.id}:approved`}
                    onClick={() => reviewDraft(record.id, "approved")}
                  >
                    通过
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={!canRejectPlatformDraft(record)}
                    loading={actionKey === `${record.id}:rejected`}
                    onClick={() => reviewDraft(record.id, "rejected")}
                  >
                    驳回
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    icon={record.draft_type === "customer_reply" ? <SendOutlined /> : <CloudUploadOutlined />}
                    disabled={record.status !== "approved"}
                    loading={actionKey === `${record.id}:publish`}
                    onClick={() => publishDraft(record.id)}
                  >
                    {platformDraftPublishButtonLabel(record)}
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

export function platformDraftWritebackColor(value: string) {
  const colors: Record<string, string> = {
    draft_saved: "default",
    rpa_ready: "gold",
    external_synced: "green",
    failed: "red",
  };

  return colors[value] ?? "default";
}
