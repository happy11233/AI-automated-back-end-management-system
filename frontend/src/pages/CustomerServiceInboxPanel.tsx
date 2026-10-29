import { MessageOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Col, Empty, Input, Row, Select, Space, Table, Tabs, Tag } from "antd";
import { ProCard, StatisticCard } from "@ant-design/pro-components";
import type {
  CustomerServiceMessageDetailResponse,
  CustomerServiceMessageItem,
  CustomerServiceProcessResponse,
  Position,
} from "../api";
import type {
  Role,
  CustomerServiceInboxFilters,
  CustomerServiceInboxForm,
} from "../workspace/types";
import {
  canUseCustomerServiceInbox,
  metricStatus,
  Paragraph,
  Text,
  Title,
  customerIntentLabel,
  RiskTag,
  formatTime,
  textFromUnknown,
  platformDraftWritebackLabel,
  StatusTag,
  formatDuration,
} from "../workspace/shared";
import { DetailText } from "../components/DetailText";

export function CustomerServiceInboxPanel({
  role,
  position,
  messages,
  detail,
  processResult,
  filters,
  setFilters,
  form,
  setForm,
  loading,
  creating,
  processingMessageId,
  refreshMessages,
  createMessage,
  processMessage,
  openDetail,
}: {
  role: Role;
  position: Position | null;
  messages: CustomerServiceMessageItem[];
  detail: CustomerServiceMessageDetailResponse | null;
  processResult: CustomerServiceProcessResponse | null;
  filters: CustomerServiceInboxFilters;
  setFilters: (value: CustomerServiceInboxFilters) => void;
  form: CustomerServiceInboxForm;
  setForm: (value: CustomerServiceInboxForm | ((current: CustomerServiceInboxForm) => CustomerServiceInboxForm)) => void;
  loading: boolean;
  creating: boolean;
  processingMessageId: string;
  refreshMessages: (nextFilters?: CustomerServiceInboxFilters) => void;
  createMessage: () => void;
  processMessage: (messageId: string) => void;
  openDetail: (messageId: string) => void;
}) {
  if (!canUseCustomerServiceInbox(role, position)) {
    return (
      <ProCard title="客服自动化收件箱" bordered>
        <Empty description="当前账号无权使用客服自动化收件箱" />
      </ProCard>
    );
  }

  const stats = [
    { title: "消息总数", value: messages.length, status: "processing" },
    { title: "低风险待发送", value: messages.filter((item) => item.status === "auto_reply_ready").length, status: "success" },
    { title: "转人工", value: messages.filter((item) => item.status === "human_handoff").length, status: "warning" },
    { title: "处理失败", value: messages.filter((item) => item.status === "failed").length, status: "error" },
  ];

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]}>
        {stats.map((item) => (
          <Col xs={12} md={6} key={item.title}>
            <StatisticCard
              statistic={{
                title: item.title,
                value: item.value,
                suffix: "条",
                status: metricStatus(item.status),
              }}
            />
          </Col>
        ))}
      </Row>

      <ProCard title="客服自动化工作台" bordered className="customerInboxWorkspace">
        <Tabs
          items={[
            {
              key: "queue",
              label: "消息处理",
              children: (
                <CustomerInboxQueueAndResult
                  messages={messages}
                  detail={detail}
                  processResult={processResult}
                  filters={filters}
                  setFilters={setFilters}
                  loading={loading}
                  processingMessageId={processingMessageId}
                  refreshMessages={refreshMessages}
                  processMessage={processMessage}
                  openDetail={openDetail}
                />
              ),
            },
            {
              key: "manual",
              label: "手动补录",
              children: (
                <CustomerInboxManualEntry
                  form={form}
                  setForm={setForm}
                  creating={creating}
                  loading={loading}
                  createMessage={createMessage}
                  refreshMessages={refreshMessages}
                />
              ),
            },
            {
              key: "webhook",
              label: "Webhook 接入",
              children: <CustomerInboxWebhookInfo />,
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

export function CustomerInboxQueueAndResult({
  messages,
  detail,
  processResult,
  filters,
  setFilters,
  loading,
  processingMessageId,
  refreshMessages,
  processMessage,
  openDetail,
}: {
  messages: CustomerServiceMessageItem[];
  detail: CustomerServiceMessageDetailResponse | null;
  processResult: CustomerServiceProcessResponse | null;
  filters: CustomerServiceInboxFilters;
  setFilters: (value: CustomerServiceInboxFilters) => void;
  loading: boolean;
  processingMessageId: string;
  refreshMessages: (nextFilters?: CustomerServiceInboxFilters) => void;
  processMessage: (messageId: string) => void;
  openDetail: (messageId: string) => void;
}) {
  const selected = detail?.item || null;

  return (
    <Space direction="vertical" size={12} className="customerInboxTabPane">
      <ProCard title="消息队列" bordered>
        <Space direction="vertical" size={12} className="pageStack">
          <Space wrap className="customerInboxToolbar">
            <Select
              value={filters.status}
              style={{ width: 132 }}
              options={[
                { label: "全部状态", value: "all" },
                { label: "新消息", value: "new" },
                { label: "处理中", value: "processing" },
                { label: "草稿", value: "drafted" },
                { label: "待发送", value: "auto_reply_ready" },
                { label: "转人工", value: "human_handoff" },
                { label: "失败", value: "failed" },
              ]}
              onChange={(value) => {
                const next = { ...filters, status: value };
                setFilters(next);
                refreshMessages(next);
              }}
            />
            <Select
              value={filters.riskLevel}
              style={{ width: 120 }}
              options={[
                { label: "全部风险", value: "all" },
                { label: "未处理", value: "unprocessed" },
                { label: "低风险", value: "low" },
                { label: "中风险", value: "medium" },
                { label: "高风险", value: "high" },
              ]}
              onChange={(value) => {
                const next = { ...filters, riskLevel: value };
                setFilters(next);
                refreshMessages(next);
              }}
            />
          </Space>
          <Table<CustomerServiceMessageItem>
            rowKey="id"
            size="small"
            dataSource={messages}
            loading={loading}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            columns={[
              {
                title: "客户消息",
                dataIndex: "message",
                width: 310,
                render: (_, record) => (
                  <Space direction="vertical" size={2} className="customerInboxMessageCell">
                    <Text strong ellipsis>
                      {record.subject || record.buyer_name || record.channel}
                    </Text>
                    <Text type="secondary" className="customerInboxPreview">
                      {record.message}
                    </Text>
                    <Space size={[4, 4]} wrap>
                      {record.order_no ? <Tag>{record.order_no}</Tag> : null}
                      {record.tracking_no ? <Tag color="geekblue">{record.tracking_no}</Tag> : null}
                    </Space>
                  </Space>
                ),
              },
              {
                title: "意图",
                dataIndex: "intent",
                width: 130,
                render: (value) => <Tag>{customerIntentLabel(String(value || "未识别"))}</Tag>,
              },
              {
                title: "风险",
                dataIndex: "risk_level",
                width: 100,
                render: (value) => <RiskTag value={String(value)} />,
              },
              {
                title: "状态",
                dataIndex: "status",
                width: 110,
                render: (value) => <CustomerStatusTag value={String(value)} />,
              },
              {
                title: "渠道",
                dataIndex: "channel",
                width: 90,
                render: (value) => <Tag color="blue">{String(value)}</Tag>,
              },
              {
                title: "创建时间",
                dataIndex: "created_at",
                width: 130,
                render: (value) => formatTime(String(value || "")),
              },
              {
                title: "操作",
                key: "actions",
                fixed: "right",
                width: 170,
                render: (_, record) => (
                  <Space size={6} wrap>
                    <Button size="small" onClick={() => openDetail(record.id)}>
                      详情
                    </Button>
                    <Button
                      size="small"
                      type="primary"
                      loading={processingMessageId === record.id}
                      disabled={processingMessageId === record.id}
                      onClick={() => processMessage(record.id)}
                    >
                      AI 处理
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Space>
      </ProCard>

      <ProCard title="处理结果" bordered>
        {selected ? (
          <Space direction="vertical" size={12} className="pageStack">
            <Space size={[6, 6]} wrap>
              <CustomerStatusTag value={selected.status} />
              <RiskTag value={selected.risk_level} />
              {selected.intent ? <Tag>{customerIntentLabel(selected.intent)}</Tag> : null}
              {selected.automation_decision ? (
                <Tag color="purple">{customerDecisionLabel(selected.automation_decision)}</Tag>
              ) : null}
            </Space>

            <div className="customerInboxDetailGrid">
              <DetailText label="订单号" value={selected.order_no || "-"} />
              <DetailText label="物流单号" value={selected.tracking_no || "-"} />
              <DetailText label="站点" value={selected.marketplace || "-"} />
              <DetailText label="语言" value={selected.buyer_language || "-"} />
              <DetailText label="运行记录" value={selected.run_id || "-"} mono />
              <DetailText label="审批 ID" value={selected.approval_id || "-"} mono />
              <DetailText label="草稿 ID" value={textFromUnknown(selected.metadata.platform_draft_id || "-")} mono />
              <DetailText label="写回状态" value={platformDraftWritebackLabel(textFromUnknown(selected.metadata.writeback_status || "-"))} />
            </div>

            <ResultBlock title="客户原话" content={selected.message} />
            <ResultBlock
              title={selected.reply_parse_status === "validated" ? "客户回复正文（草稿）" : "历史回复或待复核内容"}
              content={selected.reply_draft || (selected.reply_parse_status === "invalid" ? "回复结构校验失败，未提取可发送正文。" : "尚未处理")}
            />
            {selected.internal_note ? <ResultBlock title="客服内部处理建议" content={selected.internal_note} /> : null}
            {selected.needs_human_review ? <Tag color="gold">需要人工复核</Tag> : null}
            {selected.reply_parse_status === "invalid" && selected.metadata.reply_unparsed_output ? (
              <ResultBlock title="待人工检查的原始输出（仅内部可见）" content={textFromUnknown(selected.metadata.reply_unparsed_output)} />
            ) : null}
            {selected.metadata.writeback_message ? (
              <ResultBlock title="自动化写回" content={textFromUnknown(selected.metadata.writeback_message)} />
            ) : null}
            <ResultBlock title="ERP 摘要" content={selected.erp_summary || "暂无 ERP 摘要"} />
            <ResultBlock title="知识库摘要" content={selected.rag_summary || "暂无知识库摘要"} />
            {selected.handoff_reason ? (
              <ResultBlock title="转人工原因" content={selected.handoff_reason} />
            ) : null}

            {selected.erp_references.length ? (
              <Space size={[6, 6]} wrap>
                {selected.erp_references.map((reference) => (
                  <Tag color="geekblue" key={`${reference.resource}-${reference.record_id}`}>
                    {reference.resource_label} / {reference.record_id}
                  </Tag>
                ))}
              </Space>
            ) : null}

            {detail?.events.length ? (
              <ProCard title="事件时间线" bordered size="small">
                <Space direction="vertical" size={8} className="pageStack">
                  {detail.events.map((event) => (
                    <div className="customerInboxEvent" key={event.id}>
                      <Text strong>{customerEventLabel(event.event_type)}</Text>
                      <Text type="secondary">{formatTime(event.created_at)}</Text>
                      <Text className="customerInboxPreview">{event.content}</Text>
                    </div>
                  ))}
                </Space>
              </ProCard>
            ) : null}

            {processResult?.item.id === selected.id ? (
              <Table
                rowKey={(record) => `${record.step_order}-${record.step_name}`}
                size="small"
                dataSource={processResult.steps}
                pagination={false}
                columns={[
                  {
                    title: "步骤",
                    dataIndex: "step_name",
                    render: (value) => <Text className="aiWorkflowMono">{String(value)}</Text>,
                  },
                  {
                    title: "状态",
                    dataIndex: "status",
                    width: 92,
                    render: (value) => <StatusTag value={String(value)} />,
                  },
                  {
                    title: "耗时",
                    dataIndex: "duration_ms",
                    width: 92,
                    render: (value) => formatDuration(value),
                  },
                ]}
              />
            ) : null}
          </Space>
        ) : (
          <Empty description="请选择或创建一条客户消息" />
        )}
      </ProCard>
    </Space>
  );
}

export function CustomerInboxManualEntry({
  form,
  setForm,
  creating,
  loading,
  createMessage,
  refreshMessages,
}: {
  form: CustomerServiceInboxForm;
  setForm: (value: CustomerServiceInboxForm | ((current: CustomerServiceInboxForm) => CustomerServiceInboxForm)) => void;
  creating: boolean;
  loading: boolean;
  createMessage: () => void;
  refreshMessages: (nextFilters?: CustomerServiceInboxFilters) => void;
}) {
  return (
    <div className="customerInboxTabPane">
      <Row gutter={[12, 12]} align="top">
        <Col xs={24} md={6}>
          <Select
            className="fullWidthControl"
            value={form.channel}
            options={[
              { label: "手动录入", value: "manual" },
              { label: "Amazon", value: "amazon" },
              { label: "邮箱", value: "email" },
              { label: "工单", value: "ticket" },
              { label: "API", value: "api" },
            ]}
            onChange={(value) => setForm((current) => ({ ...current, channel: value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.buyerName}
            placeholder="客户姓名"
            onChange={(event) => setForm((current) => ({ ...current, buyerName: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.buyerEmail}
            placeholder="客户邮箱"
            onChange={(event) => setForm((current) => ({ ...current, buyerEmail: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Select
            className="fullWidthControl"
            value={form.buyerLanguage}
            options={[
              { label: "自动识别", value: "auto" },
              { label: "English", value: "English" },
              { label: "中文", value: "Chinese" },
              { label: "Deutsch", value: "German" },
              { label: "日本語", value: "Japanese" },
            ]}
            onChange={(value) => setForm((current) => ({ ...current, buyerLanguage: value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.marketplace}
            placeholder="站点，例如 Amazon US"
            onChange={(event) => setForm((current) => ({ ...current, marketplace: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.orderNo}
            placeholder="订单号"
            onChange={(event) => setForm((current) => ({ ...current, orderNo: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.trackingNo}
            placeholder="物流单号"
            onChange={(event) => setForm((current) => ({ ...current, trackingNo: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.sku}
            placeholder="SKU"
            onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={8}>
          <Input
            value={form.subject}
            placeholder="主题"
            onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={16}>
          <Input.TextArea
            value={form.message}
            placeholder="客户原话，例如：Where is my order?"
            autoSize={false}
            rows={3}
            onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
          />
        </Col>
        <Col xs={24}>
          <Space wrap>
            <Button type="primary" icon={<MessageOutlined />} loading={creating} onClick={createMessage}>
              加入收件箱
            </Button>
            <Button icon={<ReloadOutlined />} loading={loading} onClick={() => refreshMessages()}>
              刷新列表
            </Button>
          </Space>
        </Col>
      </Row>
    </div>
  );
}

export function CustomerInboxWebhookInfo() {
  return (
    <div className="customerInboxTabPane">
      <div className="customerWebhookInfo">
        <div>
          <Text strong>Webhook</Text>
          <Text className="customerWebhookUrl">POST /api/customer-service/webhooks/messages</Text>
        </div>
        <div>
          <Text type="secondary">鉴权</Text>
          <Text>客服岗位 Bearer token 或 X-Customer-Service-Webhook-Secret</Text>
        </div>
        <div>
          <Text type="secondary">动作</Text>
          <Text>收到外部客户消息后自动入库、识别意图、查 ERP/RAG、生成回复并按风险流转</Text>
        </div>
      </div>
    </div>
  );
}

export function ResultBlock({ title, content }: { title: string; content: string }) {
  return (
    <div className="customerInboxResultBlock">
      <Text strong>{title}</Text>
      <Paragraph className="customerInboxResultText">{content}</Paragraph>
    </div>
  );
}

export function CustomerStatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    new: "blue",
    processing: "processing",
    drafted: "gold",
    auto_reply_ready: "green",
    human_handoff: "red",
    closed: "default",
    failed: "volcano",
  };

  return <Tag color={colorMap[value] || "default"}>{customerStatusLabel(value)}</Tag>;
}

export function customerStatusLabel(value: string) {
  const labels: Record<string, string> = {
    new: "新消息",
    processing: "处理中",
    drafted: "草稿待确认",
    auto_reply_ready: "待发送",
    human_handoff: "转人工",
    closed: "已关闭",
    failed: "失败",
  };

  return labels[value] ?? value;
}

export function customerDecisionLabel(value: string) {
  const labels: Record<string, string> = {
    handoff_required: "必须转人工",
    draft_only: "仅生成草稿",
    low_risk_auto_reply_ready: "低风险待发送",
  };

  return labels[value] ?? value;
}

export function customerEventLabel(value: string) {
  const labels: Record<string, string> = {
    created: "创建",
    processing_started: "开始处理",
    processed: "处理完成",
    failed: "失败",
  };

  return labels[value] ?? value;
}
