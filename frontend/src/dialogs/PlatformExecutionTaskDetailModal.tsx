import { Button, Card, Col, Collapse, Empty, Modal, Row, Space, Tabs } from "antd";
import type { Position, PlatformExecutionTaskItem } from "../api";
import { type Role } from "../workspace/types";
import {
  shortTaskId,
  canRetryPlatformTask,
  PlatformExecutionTaskStatusTag,
  platformActionTypeLabel,
  platformTaskDraftTitle,
  isPosition,
  platformTaskPosition,
  positionLabel,
  formatTime,
  Paragraph,
  Text,
  Title,
  recordFromUnknown,
  textFromUnknown,
  RiskTag,
} from "../workspace/shared";
import { RunRecordDetailItem } from "../components/RunRecordDetailItem";

export function PlatformExecutionTaskDetailModal({
  open,
  loading,
  task,
  role,
  retryingTaskId,
  retryTask,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  task: PlatformExecutionTaskItem | null;
  role: Role;
  retryingTaskId: string;
  retryTask: (taskId: string) => void;
  onClose: () => void;
}) {
  const canViewTechnicalDetails = role === "admin";

  return (
    <Modal
      open={open}
      title={task ? `执行任务 / ${shortTaskId(task.id)}` : "执行任务详情"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="retry"
          disabled={!task || !canRetryPlatformTask(task)}
          loading={task ? retryingTaskId === task.id : false}
          onClick={() => task && retryTask(task.id)}
        >
          重试任务
        </Button>,
      ]}
      width="min(960px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载执行任务详情" />
      ) : task ? (
        <Tabs
          className="platformTaskDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="platformTaskDetailGrid">
                    <RunRecordDetailItem label="状态" value={<PlatformExecutionTaskStatusTag value={task.status} />} />
                    <RunRecordDetailItem label="动作类型" value={platformActionTypeLabel(task.action_type)} />
                    <RunRecordDetailItem label="草稿标题" value={platformTaskDraftTitle(task)} />
                    <RunRecordDetailItem
                      label="岗位"
                      value={isPosition(platformTaskPosition(task)) ? positionLabel(platformTaskPosition(task) as Position) : "-"}
                    />
                    <RunRecordDetailItem label="目标" value={task.target || "-"} mono />
                    <RunRecordDetailItem label="外部引用" value={task.external_reference || "-"} mono />
                    <RunRecordDetailItem label="尝试次数" value={`${task.attempt_count}/${task.max_attempts}`} />
                    <RunRecordDetailItem label="更新时间" value={formatTime(task.updated_at)} />
                    <RunRecordDetailItem label="完成时间" value={formatTime(task.completed_at)} />
                    <RunRecordDetailItem label="下次重试" value={formatTime(task.next_attempt_at)} />
                  </div>
                  {task.last_error ? (
                    <Paragraph className="platformTaskError">{task.last_error}</Paragraph>
                  ) : null}
                </Space>
              ),
            },
            {
              key: "business",
              label: "业务进度",
              children: (
                <PlatformExecutionTaskBusinessView
                  task={task}
                  canViewTechnicalDetails={canViewTechnicalDetails}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一条执行任务" />
      )}
    </Modal>
  );
}

export function PlatformExecutionTaskBusinessView({
  task,
  canViewTechnicalDetails,
}: {
  task: PlatformExecutionTaskItem;
  canViewTechnicalDetails: boolean;
}) {
  const requestPayload = task.request_payload || {};
  const responsePayload = task.response_payload || {};
  const metadata = task.metadata || {};
  const content = task.draft?.content || recordFromUnknown(requestPayload.content);
  const draftType = task.draft?.draft_type || task.draft_type || textFromUnknown(requestPayload.draft_type || metadata.draft_type);
  const actionPhase = textFromUnknown(requestPayload.action_phase || "");
  const finalPublish = Boolean(metadata.final_publish) || actionPhase === "publish_or_send";
  const executorName = textFromUnknown(metadata.executor_name || metadata.executor_type || "");
  const businessTarget = platformTaskBusinessTarget(task, content);
  const successMessage = platformTaskBusinessResult(task, responsePayload);
  const nextAction = platformTaskNextAction(task, finalPublish);
  const failureReason = platformTaskFailureReason(task, responsePayload);

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <div className="businessTaskSummaryGrid">
        <RunRecordDetailItem label="当前状态" value={<PlatformExecutionTaskStatusTag value={String(task.status)} />} />
        <RunRecordDetailItem label="业务动作" value={platformActionTypeLabel(task.action_type)} />
        <RunRecordDetailItem label="草稿" value={platformTaskDraftTitle(task)} />
        <RunRecordDetailItem label="目标对象" value={businessTarget} mono />
        <RunRecordDetailItem label="外部系统" value={platformExternalTargetLabel(task.target || textFromUnknown(requestPayload.external_target || ""))} />
        <RunRecordDetailItem label="执行器" value={executorName || "等待配置"} />
        <RunRecordDetailItem label="外部引用" value={task.external_reference || textFromUnknown(responsePayload.external_reference || responsePayload.id || "-")} mono />
        <RunRecordDetailItem label="尝试次数" value={`${task.attempt_count}/${task.max_attempts}`} />
      </div>

      <Card size="small" title="业务时间线" className="businessDraftSectionCard">
        <div className="businessTaskTimeline">
          {platformTaskTimelineItems(task, finalPublish).map((item) => (
            <div key={item.key} className={`businessTaskTimelineItem ${item.tone}`}>
              <span className="businessTaskTimelineDot" />
              <div className="businessTaskTimelineBody">
                <Text strong>{item.title}</Text>
                <Text type="secondary" className="businessTaskTimelineText">{item.description}</Text>
                {item.time ? <Text type="secondary" className="runRecordMono">{item.time}</Text> : null}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {failureReason ? (
        <Card size="small" title="失败原因" className="businessDraftSectionCard">
          <Paragraph className="businessTaskFailureText">{failureReason}</Paragraph>
        </Card>
      ) : (
        <Card size="small" title={task.status === "succeeded" ? "执行结果" : "下一步"} className="businessDraftSectionCard">
          <Paragraph className="businessDraftText">
            {task.status === "succeeded" ? successMessage : nextAction}
          </Paragraph>
        </Card>
      )}

      {draftType === "listing" ? (
        <ListingTaskBusinessSummary content={content} />
      ) : draftType === "customer_reply" ? (
        <CustomerReplyTaskBusinessSummary content={content} />
      ) : null}

      {canViewTechnicalDetails ? (
        <Collapse
          size="small"
          className="technicalDetailsCollapse"
          items={[
            {
              key: "raw",
              label: "管理员技术详情",
              children: <PlatformExecutionTaskTechnicalView task={task} />,
            },
          ]}
        />
      ) : null}
    </Space>
  );
}

export function ListingTaskBusinessSummary({ content }: { content: Record<string, unknown> }) {
  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} md={12}>
        <Card size="small" title="Listing 标题" className="businessDraftSectionCard">
          <Paragraph className="businessDraftText">{textFromUnknown(content.listing_title || "待确认")}</Paragraph>
        </Card>
      </Col>
      <Col xs={24} md={12}>
        <Card size="small" title="SKU / 站点" className="businessDraftSectionCard">
          <Space direction="vertical" size={6} className="pageStack">
            <RunRecordDetailItem label="SKU" value={textFromUnknown(content.sku || "待确认")} mono />
            <RunRecordDetailItem label="站点" value={textFromUnknown(content.marketplace || "待确认")} />
          </Space>
        </Card>
      </Col>
    </Row>
  );
}

export function CustomerReplyTaskBusinessSummary({ content }: { content: Record<string, unknown> }) {
  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} md={12}>
        <Card size="small" title="客服回复摘要" className="businessDraftSectionCard">
          <Paragraph className="businessDraftText">{textFromUnknown(content.reply_draft || "待确认")}</Paragraph>
        </Card>
      </Col>
      <Col xs={24} md={12}>
        <Card size="small" title="订单与风险" className="businessDraftSectionCard">
          <Space direction="vertical" size={6} className="pageStack">
            <RunRecordDetailItem label="订单号" value={textFromUnknown(content.order_no || "待确认")} mono />
            <RunRecordDetailItem label="风险等级" value={<RiskTag value={textFromUnknown(content.risk_level || "unprocessed")} />} />
          </Space>
        </Card>
      </Col>
    </Row>
  );
}

export function PlatformExecutionTaskTechnicalView({ task }: { task: PlatformExecutionTaskItem }) {
  return (
    <Space direction="vertical" size={12} className="pageStack">
      <Card size="small" title="请求内容" className="businessDraftSectionCard">
        <pre className="platformDraftPre">{JSON.stringify(task.request_payload || {}, null, 2)}</pre>
      </Card>
      <Card size="small" title="响应内容" className="businessDraftSectionCard">
        <pre className="platformDraftPre">{JSON.stringify(task.response_payload || {}, null, 2)}</pre>
      </Card>
      <Card size="small" title="元数据" className="businessDraftSectionCard">
        <pre className="platformDraftPre">{JSON.stringify(task.metadata || {}, null, 2)}</pre>
      </Card>
    </Space>
  );
}

export function platformTaskBusinessTarget(task: PlatformExecutionTaskItem, content: Record<string, unknown>) {
  if (task.action_type === "write_listing_draft" || task.action_type === "publish_listing") {
    return textFromUnknown(content.sku || task.draft?.external_target || task.target || "待确认 SKU");
  }

  if (task.action_type === "write_customer_reply" || task.action_type === "send_customer_reply") {
    return textFromUnknown(content.order_no || content.customer_message_id || task.draft?.external_target || task.target || "待确认客户消息");
  }

  return textFromUnknown(task.draft?.external_target || task.target || "-");
}

export function platformTaskBusinessResult(
  task: PlatformExecutionTaskItem,
  responsePayload: Record<string, unknown>,
) {
  const message = textFromUnknown(responsePayload.message || responsePayload.detail || responsePayload.status_message || "");
  if (message) {
    return message;
  }

  if (task.action_type === "publish_listing") {
    return task.external_reference
      ? `Listing 已提交到外部平台，外部引用：${task.external_reference}`
      : "Listing 已提交到外部平台。";
  }

  if (task.action_type === "send_customer_reply") {
    return task.external_reference
      ? `客服回复已发送，外部引用：${task.external_reference}`
      : "客服回复已发送。";
  }

  return task.external_reference
    ? `外部执行器已处理完成，外部引用：${task.external_reference}`
    : "外部执行器已处理完成。";
}

export function platformTaskNextAction(task: PlatformExecutionTaskItem, finalPublish: boolean) {
  if (task.status === "queued") {
    if (task.last_error) {
      return "当前任务等待外部执行器接入或重试。请先确认执行器配置，配置完成后可点击重试。";
    }
    return "任务已进入队列，系统会派发给外部执行器。";
  }

  if (task.status === "dispatching") {
    return "系统正在把任务发送给外部执行器，请等待执行结果。";
  }

  if (task.status === "waiting_callback") {
    return "外部执行器已接收任务，当前正在等待平台回调确认完成结果。";
  }

  if (task.status === "cancelled") {
    return "任务已取消。如仍需处理，请回到草稿重新发起。";
  }

  if (finalPublish) {
    return "请关注外部平台是否完成发布或发送。";
  }

  return "请回到草稿审核中心继续审核或发布。";
}

export function platformTaskFailureReason(
  task: PlatformExecutionTaskItem,
  responsePayload: Record<string, unknown>,
) {
  if (task.status !== "failed" && !task.last_error) {
    return "";
  }

  const raw = textFromUnknown(
    task.last_error
      || responsePayload.message
      || responsePayload.error
      || responsePayload.detail
      || "外部执行任务失败，请稍后重试或联系管理员。",
  );
  const lower = raw.toLowerCase();

  if (lower.includes("timeout") || lower.includes("timed out")) {
    return "外部系统响应超时，任务没有确认完成。请稍后重试，或让管理员检查外部执行器连接。";
  }

  if (lower.includes("http") || lower.includes("url") || lower.includes("connection")) {
    return "外部执行器连接异常，任务没有成功提交。请让管理员检查执行器地址、网络和鉴权配置。";
  }

  if (lower.includes("executor") || lower.includes("webhook") || lower.includes("not configured")) {
    return "外部执行器还没有配置完成，草稿已保存，但暂时不能自动写回外部平台。";
  }

  return raw;
}

export function platformTaskTimelineItems(task: PlatformExecutionTaskItem, finalPublish: boolean) {
  const createdTime = formatTime(task.created_at || "");
  const updatedTime = formatTime(task.updated_at || "");
  const completedTime = formatTime(task.completed_at || "");
  const items: Array<{ key: string; title: string; description: string; time: string; tone: string }> = [
    {
      key: "created",
      title: "任务已创建",
      description: finalPublish ? "草稿已审核通过，系统准备发布或发送。" : "系统已保存草稿，并准备写回外部平台。",
      time: createdTime,
      tone: "done",
    },
  ];

  if (["dispatching", "waiting_callback", "succeeded", "failed"].includes(String(task.status))) {
    items.push({
      key: "dispatching",
      title: "已派发执行器",
      description: "系统已把业务动作发送给外部执行器处理。",
      time: updatedTime,
      tone: task.status === "failed" ? "warning" : "done",
    });
  } else {
    items.push({
      key: "dispatching",
      title: "等待派发",
      description: "任务正在队列中等待外部执行器处理。",
      time: "",
      tone: "pending",
    });
  }

  if (["waiting_callback", "succeeded", "failed"].includes(String(task.status))) {
    items.push({
      key: "callback",
      title: task.status === "waiting_callback" ? "等待外部回调" : "已收到外部结果",
      description: task.status === "waiting_callback"
        ? "外部平台仍在处理，系统会等待回调更新最终状态。"
        : "外部执行器已返回处理结果。",
      time: task.status === "waiting_callback" ? updatedTime : completedTime || updatedTime,
      tone: task.status === "waiting_callback" ? "active" : task.status === "failed" ? "warning" : "done",
    });
  } else {
    items.push({
      key: "callback",
      title: "等待外部结果",
      description: "任务完成后会在这里显示结果和外部引用。",
      time: "",
      tone: "pending",
    });
  }

  items.push({
    key: "finished",
    title: task.status === "succeeded" ? "业务动作完成" : task.status === "failed" ? "业务动作失败" : "等待完成",
    description: task.status === "succeeded"
      ? "员工可以继续后续业务处理。"
      : task.status === "failed"
        ? "请根据失败原因修改配置、草稿或重试任务。"
        : "系统还没有收到最终完成结果。",
    time: task.status === "succeeded" || task.status === "failed" ? completedTime || updatedTime : "",
    tone: task.status === "succeeded" ? "done" : task.status === "failed" ? "danger" : "pending",
  });

  return items;
}

export function platformExternalTargetLabel(value: string) {
  const normalized = value.trim();
  const labels: Record<string, string> = {
    amazon_seller_central: "Amazon Seller Central",
    amazon: "Amazon",
    customer_service_system: "客服系统",
    erp: "ERP 系统",
  };

  if (!normalized) {
    return "外部平台";
  }

  if (/^https?:\/\//i.test(normalized)) {
    return "外部执行器 Webhook";
  }

  return labels[normalized] ?? normalized;
}
