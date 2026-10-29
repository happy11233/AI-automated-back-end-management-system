import { MessageOutlined, ReloadOutlined } from "@ant-design/icons";
import { Button, Card, Col, Collapse, Empty, Input, Row, Space, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { ThreadListItem } from "../api";
import { type ChatMessage, type Role, type ChatRoute } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  threadDisplayTitle,
  shortThreadId,
  formatTime,
  textFromUnknown,
  recordFromUnknown,
  RiskTag,
  shortTaskId,
  sanitizeTechnicalValue,
  labelForBadge,
} from "../workspace/shared";
import { MessageList } from "../components/MessageList";

export function ThreadsPanel({
  threads,
  activeThreadId,
  threadSearch,
  setThreadSearch,
  refreshThreads,
  openThread,
  messages,
  summary,
  state,
  loading,
  role,
  retentionDays,
}: {
  threads: ThreadListItem[];
  activeThreadId: string;
  threadSearch: string;
  setThreadSearch: (value: string) => void;
  refreshThreads: () => void;
  openThread: (threadId: string, options?: { navigate?: boolean; replacePath?: boolean; silent?: boolean }) => void;
  messages: ChatMessage[];
  summary: string;
  state: Record<string, unknown> | null;
  loading: boolean;
  role: Role;
  retentionDays: number;
}) {
  const activeThread = threads.find((item) => item.id === activeThreadId) || null;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9} className="splitCardCol">
        <ProCard
          title="会话记录"
          bordered
          className="splitCard"
          extra={
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshThreads} loading={loading}>
              刷新
            </Button>
          }
        >
          <Space direction="vertical" size={12} className="pageStack">
            <Input.Search
              value={threadSearch}
              onChange={(event) => setThreadSearch(event.target.value)}
              onSearch={refreshThreads}
              placeholder={role === "admin" ? "搜索标题、账号、岗位或会话 ID" : "搜索我的会话"}
              allowClear
            />
            <Text type="secondary">仅显示近 {retentionDays} 天会话，过期记录会自动清理。</Text>
            <div className="threadHistoryList">
              {threads.length ? (
                threads.map((thread) => (
                  <button
                    key={thread.id}
                    type="button"
                    className={`threadHistoryItem ${thread.id === activeThreadId ? "active" : ""}`}
                    onClick={() => openThread(thread.id, { navigate: false })}
                  >
                    <div className="threadHistoryTitleRow">
                      <Text strong className="threadHistoryTitle">
                        {threadDisplayTitle(thread, role)}
                      </Text>
                      <Tag color={thread.status === "closed" ? "default" : "green"}>{thread.status}</Tag>
                    </div>
                    <Text type="secondary" className="threadHistoryPreview">
                      {thread.last_message_preview || shortThreadId(thread.id)}
                    </Text>
                    <div className="threadHistoryMeta">
                      <Text type="secondary">{formatTime(thread.updated_at)}</Text>
                      <Text type="secondary">{thread.message_count} 条</Text>
                    </div>
                  </button>
                ))
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无会话记录" />
              )}
            </div>
          </Space>

        </ProCard>
      </Col>
      <Col xs={24} xl={15} className="splitCardCol">
        <ProCard
          title={activeThread ? threadDisplayTitle(activeThread, role) : "消息记录"}
          bordered
          className="splitCard"
          extra={activeThreadId ? (
            <Space size={8} align="center">
              <Button
                size="small"
                type="primary"
                icon={<MessageOutlined />}
                onClick={() => openThread(activeThreadId)}
              >
                跳转到对话
              </Button>
              <Tag color="blue">{shortThreadId(activeThreadId)}</Tag>
            </Space>
          ) : null}
        >
          <Space direction="vertical" size={14} className="pageStack">
            <MessageList messages={messages} />
            {summary ? (
              <Card size="small" title="会话摘要" className="contextCard">
                <Paragraph>{summary}</Paragraph>
              </Card>
            ) : null}

            {state ? (
              <ThreadBusinessStateCard
                state={state}
                messages={messages}
                role={role}
              />
            ) : null}
          </Space>
        </ProCard>
      </Col>
    </Row>
  );
}

export function ThreadBusinessStateCard({
  state,
  messages,
  role,
}: {
  state: Record<string, unknown>;
  messages: ChatMessage[];
  role: Role;
}) {
  const latestAssistant = [...messages].reverse().find((item) => item.role === "assistant") || null;
  const currentIntent = textFromUnknown(state.current_intent || "");
  const rawRiskLevel = textFromUnknown(state.risk_level || "");
  const riskLevel = ["unprocessed", "low", "medium", "high"].includes(rawRiskLevel) ? rawRiskLevel : "";
  const approvalId = textFromUnknown(state.approval_id || "");
  const approvalResult = recordFromUnknown(latestAssistant?.approvalResult);
  const approvalStatus = textFromUnknown(approvalResult.status || approvalResult.status_label || "");
  const attachments = latestAssistant?.attachments || [];
  const platformDraft = latestAssistant?.platformDraft || null;
  const automation = recordFromUnknown(latestAssistant?.automation);
  const nextAction = threadNextAction({
    approvalId,
    approvalStatus,
    attachmentCount: attachments.length,
    hasDraft: Boolean(platformDraft),
    automation,
  });
  const hasBusinessState = Boolean(currentIntent || riskLevel || approvalId || approvalStatus || attachments.length || platformDraft || Object.keys(automation).length);

  if (!hasBusinessState && role !== "admin") {
    return null;
  }

  return (
    <Card size="small" title="业务状态" className="contextCard">
      <div className="threadBusinessStateGrid">
        <div className="threadBusinessStateItem">
          <Text type="secondary">识别意图</Text>
          <Text strong>{intentBusinessLabel(currentIntent, latestAssistant?.route)}</Text>
          {riskLevel ? <RiskTag value={riskLevel} /> : <Tag>普通</Tag>}
        </div>
        <div className="threadBusinessStateItem">
          <Text type="secondary">审批状态</Text>
          <Text strong>{approvalBusinessLabel({ approvalId, approvalStatus, automation })}</Text>
          {approvalId ? <Text type="secondary">审批编号：{shortTaskId(approvalId)}</Text> : null}
        </div>
        <div className="threadBusinessStateItem">
          <Text type="secondary">下一步操作</Text>
          <Text strong>{nextAction.title}</Text>
          <Text type="secondary">{nextAction.description}</Text>
        </div>
      </div>
      {attachments.length ? (
        <div className="threadBusinessAttachmentList">
          {attachments.slice(0, 4).map((attachment) => (
            <Tag color="blue" key={`${attachment.filename}-${attachment.size_bytes || ""}`}>
              附件：{attachment.filename}
            </Tag>
          ))}
        </div>
      ) : null}
      {role === "admin" ? (
        <Collapse
          className="threadBusinessTechCollapse"
          size="small"
          ghost
          items={[
            {
              key: "admin-tech",
              label: "管理员技术详情",
              children: (
                <pre className="statePre">
                  {JSON.stringify(sanitizeTechnicalValue({
                    state,
                    latestAssistant: latestAssistant ? {
                      route: latestAssistant.route,
                      attachments: latestAssistant.attachments,
                      platformDraft: latestAssistant.platformDraft,
                      approvalResult: latestAssistant.approvalResult,
                      automation: latestAssistant.automation,
                    } : null,
                  }), null, 2)}
                </pre>
              ),
            },
          ]}
        />
      ) : null}
    </Card>
  );
}

export function threadNextAction({
  approvalId,
  approvalStatus,
  attachmentCount,
  hasDraft,
  automation,
}: {
  approvalId: string;
  approvalStatus: string;
  attachmentCount: number;
  hasDraft: boolean;
  automation: Record<string, unknown>;
}) {
  const normalizedApproval = approvalStatus.toLowerCase();
  if (attachmentCount > 0) {
    return {
      title: "下载或查看生成附件",
      description: `本会话已生成 ${attachmentCount} 个附件，可在消息下方下载。`,
    };
  }
  if (hasDraft) {
    return {
      title: "去草稿审核中心确认",
      description: "AI 已生成业务草稿，下一步由对应岗位审核内容。",
    };
  }
  if (approvalId || ["pending", "blocked", "waiting", "reviewing"].includes(normalizedApproval)) {
    return {
      title: "等待审批或人工确认",
      description: "该动作需要管理员或负责人确认后继续。",
    };
  }
  if (Object.keys(automation).length > 0) {
    return {
      title: "查看自动化执行结果",
      description: "系统已生成自动化结果，可继续补充要求或查看相关业务中心。",
    };
  }
  return {
    title: "继续对话补充要求",
    description: "可以继续告诉 AI 需要查询、生成或调整的业务内容。",
  };
}

export function approvalBusinessLabel({
  approvalId,
  approvalStatus,
  automation,
}: {
  approvalId: string;
  approvalStatus: string;
  automation: Record<string, unknown>;
}) {
  const businessStatus = textFromUnknown(automation.business_status_label || automation.status_label || "");
  if (approvalStatus) {
    return labelForBadge(approvalStatus);
  }
  if (businessStatus) {
    return businessStatus;
  }
  if (approvalId) {
    return "等待审批";
  }
  return "无需审批";
}

export function intentBusinessLabel(intent: string, route?: ChatRoute) {
  const labels: Record<string, string> = {
    finance_compound_report_generation: "财务资料生成",
    finance_salary_export: "工资表导出",
    finance_salary_wechat_send: "工资表发送确认",
    enterprise_wechat_file_send: "企业微信文件发送",
    operations_listing_draft: "运营 Listing 草稿",
    customer_service_reply_draft: "客服回复草稿",
    permission_denied: "权限拦截",
    ask_clarification: "需要补充信息",
    erp: "ERP 数据查询",
    order: "订单查询",
    policy: "知识库问答",
    chitchat: "普通对话",
  };
  if (intent && labels[intent]) {
    return labels[intent];
  }
  if (route) {
    return labelForRoute(route);
  }
  return intent || "暂未识别业务动作";
}

export function labelForRoute(route: ChatRoute) {
  const labels: Record<ChatRoute, string> = {
    refund_workflow: "高风险退款审批",
    order_agent: "订单工具查询",
    knowledge_rag: "知识库问答",
    finance_compound_report_generation: "财务资料自动生成",
    finance_salary_export: "工资表自动导出",
    enterprise_wechat_file_send: "企业微信文件发送",
  };

  return labels[route];
}
