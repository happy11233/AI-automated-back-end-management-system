import { Button, Card, Col, Collapse, Empty, Modal, Row, Space, Table, Tabs, Tag } from "antd";
import type { PlatformDraftItem, PlatformActionExecutionItem, PlatformDraftDetailResponse } from "../api";
import { type Role } from "../workspace/types";
import {
  canRejectPlatformDraft,
  canReviewPlatformDraft,
  platformDraftPublishButtonLabel,
  platformDraftTypeLabel,
  isPosition,
  positionLabel,
  PlatformDraftStatusTag,
  platformDraftWritebackLabel,
  formatTime,
  Paragraph,
  Text,
  Title,
  TextArea,
  platformActionTypeLabel,
  platformExecutionStatusColor,
  platformExecutionStatusLabel,
  platformExecutorTypeLabel,
  stringListFromUnknown,
  textFromUnknown,
  customerIntentLabel,
  RiskTag,
} from "../workspace/shared";
import { RunRecordDetailItem } from "../components/RunRecordDetailItem";

export function PlatformDraftDetailModal({
  open,
  loading,
  detail,
  role,
  actionKey,
  reviewComment,
  setReviewComment,
  reviewDraft,
  publishDraft,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: PlatformDraftDetailResponse | null;
  role: Role;
  actionKey: string;
  reviewComment: string;
  setReviewComment: (value: string) => void;
  reviewDraft: (draftId: string, decision: "approved" | "rejected") => void;
  publishDraft: (draftId: string) => void;
  onClose: () => void;
}) {
  const draft = detail?.item || null;
  const canViewTechnicalDetails = role === "admin";

  return (
    <Modal
      open={open}
      title={draft ? `草稿审核 / ${draft.title}` : "草稿审核"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="reject"
          danger
          disabled={!draft || !canRejectPlatformDraft(draft)}
          loading={draft ? actionKey === `${draft.id}:rejected` : false}
          onClick={() => draft && reviewDraft(draft.id, "rejected")}
        >
          驳回
        </Button>,
        <Button
          key="approve"
          disabled={!draft || !canReviewPlatformDraft(draft)}
          loading={draft ? actionKey === `${draft.id}:approved` : false}
          onClick={() => draft && reviewDraft(draft.id, "approved")}
        >
          审核通过
        </Button>,
        <Button
          key="publish"
          type="primary"
          disabled={!draft || draft.status !== "approved"}
          loading={draft ? actionKey === `${draft.id}:publish` : false}
          onClick={() => draft && publishDraft(draft.id)}
        >
          {draft ? platformDraftPublishButtonLabel(draft) : "发布/发送"}
        </Button>,
      ]}
      width={940}
    >
      {loading ? (
        <Empty description="正在加载草稿详情" />
      ) : draft ? (
        <Tabs
          className="platformDraftDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="platformDraftDetailGrid">
                    <RunRecordDetailItem label="类型" value={platformDraftTypeLabel(draft.draft_type)} />
                    <RunRecordDetailItem
                      label="岗位"
                      value={isPosition(draft.position) ? positionLabel(draft.position) : draft.position}
                    />
                    <RunRecordDetailItem label="审核状态" value={<PlatformDraftStatusTag value={draft.status} />} />
                    <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
                    <RunRecordDetailItem label="平台" value={draft.platform} />
                    <RunRecordDetailItem label="外部目标" value={draft.external_target} mono />
                    <RunRecordDetailItem label="创建时间" value={formatTime(draft.created_at)} />
                    <RunRecordDetailItem label="更新时间" value={formatTime(draft.updated_at)} />
                  </div>
                  {draft.writeback_message ? (
                    <Paragraph className="platformDraftMessage">{draft.writeback_message}</Paragraph>
                  ) : null}
                  <TextArea
                    value={reviewComment}
                    onChange={(event) => setReviewComment(event.target.value)}
                    placeholder="审核意见，可选"
                    autoSize={{ minRows: 2, maxRows: 4 }}
                  />
                </Space>
              ),
            },
            {
              key: "content",
              label: "业务内容",
              children: <PlatformDraftBusinessView draft={draft} canViewTechnicalDetails={canViewTechnicalDetails} />,
            },
            {
              key: "executions",
              label: `执行记录 ${detail?.executions.length || 0}`,
              children: (
                <Table<PlatformActionExecutionItem>
                  rowKey="id"
                  dataSource={detail?.executions || []}
                  pagination={false}
                  scroll={{ x: 780 }}
                  locale={{ emptyText: <Empty description="暂无执行记录" /> }}
                  columns={[
                    {
                      title: "动作",
                      dataIndex: "action_type",
                      width: 160,
                      render: (value) => <Text className="runRecordMono">{platformActionTypeLabel(String(value))}</Text>,
                    },
                    {
                      title: "状态",
                      dataIndex: "status",
                      width: 120,
                      render: (value) => <Tag color={platformExecutionStatusColor(String(value))}>{platformExecutionStatusLabel(String(value))}</Tag>,
                    },
                    { title: "执行器", dataIndex: "executor_type", width: 120, render: (value) => platformExecutorTypeLabel(String(value)) },
                    {
                      title: "目标",
                      dataIndex: "target",
                      render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
                    },
                    { title: "时间", dataIndex: "created_at", width: 150, render: (value) => formatTime(String(value || "")) },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一条草稿" />
      )}
    </Modal>
  );
}

export function PlatformDraftBusinessView({
  draft,
  canViewTechnicalDetails,
}: {
  draft: PlatformDraftItem;
  canViewTechnicalDetails: boolean;
}) {
  return (
    <Space direction="vertical" size={14} className="pageStack">
      {draft.draft_type === "listing" ? (
        <ListingDraftBusinessView draft={draft} />
      ) : draft.draft_type === "customer_reply" ? (
        <CustomerReplyDraftBusinessView draft={draft} />
      ) : (
        <GenericDraftBusinessView draft={draft} />
      )}
      {canViewTechnicalDetails ? (
        <Collapse
          size="small"
          className="technicalDetailsCollapse"
          items={[
            {
              key: "raw",
              label: "管理员技术详情",
              children: (
                <pre className="platformDraftPre">
                  {JSON.stringify(draft.content, null, 2)}
                </pre>
              ),
            },
          ]}
        />
      ) : null}
    </Space>
  );
}

export function ListingDraftBusinessView({ draft }: { draft: PlatformDraftItem }) {
  const content = draft.content || {};
  const bullets = stringListFromUnknown(content.five_bullets);
  const fullPackage = textFromUnknown(content.full_listing_package || "");

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <div className="businessDraftSummaryGrid">
        <RunRecordDetailItem label="SKU" value={textFromUnknown(content.sku || "待确认")} mono />
        <RunRecordDetailItem label="站点" value={textFromUnknown(content.marketplace || "待确认")} />
        <RunRecordDetailItem label="审核要求" value={content.review_required ? "需要运营人工审核" : "无需人工审核"} />
        <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
      </div>

      <Card size="small" title="Listing 标题" className="businessDraftSectionCard">
        <Paragraph className="businessDraftText">{textFromUnknown(content.listing_title || draft.title)}</Paragraph>
      </Card>

      <Card size="small" title="五点描述" className="businessDraftSectionCard">
        {bullets.length ? (
          <ol className="businessDraftList">
            {bullets.map((item, index) => (
              <li key={`${index}-${item}`}>{item}</li>
            ))}
          </ol>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无五点描述" />
        )}
      </Card>

      <Row gutter={[12, 12]}>
        <Col xs={24} md={12}>
          <Card size="small" title="后台关键词" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">{textFromUnknown(content.backend_search_terms || "待补充")}</Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="促销文案" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">{textFromUnknown(content.promo_copy || "待补充")}</Paragraph>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="发布策略" className="businessDraftSectionCard">
        <Paragraph className="businessDraftText">
          {textFromUnknown(content.publish_policy || "AI 已保存草稿，必须由运营人工审核后发布。")}
        </Paragraph>
      </Card>

      {fullPackage ? (
        <Card size="small" title="完整 Listing 草稿" className="businessDraftSectionCard">
          <Paragraph className="businessDraftLongText">{fullPackage}</Paragraph>
        </Card>
      ) : null}
    </Space>
  );
}

export function CustomerReplyDraftBusinessView({ draft }: { draft: PlatformDraftItem }) {
  const content = draft.content || {};
  const riskLevel = textFromUnknown(content.risk_level || "unprocessed");
  const intent = textFromUnknown(content.intent || "general_question");

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <div className="businessDraftSummaryGrid">
        <RunRecordDetailItem label="客户消息 ID" value={textFromUnknown(content.customer_message_id || "-")} mono />
        <RunRecordDetailItem label="订单号" value={textFromUnknown(content.order_no || "待确认")} mono />
        <RunRecordDetailItem label="物流单号" value={textFromUnknown(content.tracking_no || "待确认")} mono />
        <RunRecordDetailItem label="渠道" value={textFromUnknown(content.channel || draft.platform || "-")} />
        <RunRecordDetailItem label="语言" value={textFromUnknown(content.buyer_language || "待确认")} />
        <RunRecordDetailItem label="问题类型" value={customerIntentLabel(intent)} />
        <RunRecordDetailItem label="风险等级" value={<RiskTag value={riskLevel} />} />
        <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
      </div>

      <Card size="small" title="客服回复草稿" className="businessDraftSectionCard">
        <Paragraph className="businessDraftLongText">
          {textFromUnknown(content.reply_draft || "尚未生成回复草稿")}
        </Paragraph>
      </Card>

      <Row gutter={[12, 12]}>
        <Col xs={24} md={12}>
          <Card size="small" title="自动化判断" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">
              {textFromUnknown(content.automation_decision || "待客服人工复核")}
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="转人工原因" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">
              {textFromUnknown(content.handoff_reason || (riskLevel === "high" ? "高风险问题，需要人工审核。" : "暂无转人工原因。"))}
            </Paragraph>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="发送策略" className="businessDraftSectionCard">
        <Paragraph className="businessDraftText">
          {textFromUnknown(content.send_policy || "AI 已保存客服回复草稿，发送前必须由客服确认。")}
        </Paragraph>
      </Card>
    </Space>
  );
}

export function GenericDraftBusinessView({ draft }: { draft: PlatformDraftItem }) {
  return (
    <Card size="small" title="业务摘要" className="businessDraftSectionCard">
      <Space direction="vertical" size={10} className="pageStack">
        <div className="businessDraftSummaryGrid">
          <RunRecordDetailItem label="草稿类型" value={platformDraftTypeLabel(draft.draft_type)} />
          <RunRecordDetailItem label="平台" value={draft.platform} />
          <RunRecordDetailItem label="外部目标" value={draft.external_target} mono />
          <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
        </div>
        <Paragraph className="businessDraftText">
          当前草稿类型还没有专用业务视图。请由管理员在技术详情中确认字段，再补充岗位化展示模板。
        </Paragraph>
      </Space>
    </Card>
  );
}
