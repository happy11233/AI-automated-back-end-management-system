import { useEffect, useState } from "react";
import {
  CopyOutlined,
  DownloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  TableOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Checkbox, Empty, Input, Select, Space, Tag, Tooltip, message } from "antd";
import { downloadGeneratedFile, type ChatAttachment, type EnterpriseWechatFileSendConfirmPayload, type EmailFileSendConfirmPayload } from "../api";
import type {
  ChatMessage,
  EnterpriseWechatConfirmationCardData,
  EnterpriseWechatManualRecipientType,
  EnterpriseWechatRecipientCandidate,
} from "../workspace/types";
import {
  chatAttachmentArtifactId,
  Paragraph,
  Text,
  Title,
  formatBytes,
  enterpriseWechatConfirmKey,
  recordFromUnknown,
  firstRecord,
  textFromUnknown,
  downloadBlob,
} from "../workspace/shared";
import { PlatformDraftSummary } from "./PlatformDraftSummary";

export function MessageList({
  messages,
  confirmingEnterpriseWechatKey = "",
  downloadingArtifactId = "",
  onConfirmEnterpriseWechatSend,
  onConfirmEmailSend,
  onDownloadGeneratedArtifact,
  token,
}: {
  messages: ChatMessage[];
  confirmingEnterpriseWechatKey?: string;
  downloadingArtifactId?: string;
  onConfirmEnterpriseWechatSend?: (payload: EnterpriseWechatFileSendConfirmPayload) => Promise<void>;
  onConfirmEmailSend?: (payload: EmailFileSendConfirmPayload) => Promise<void>;
  onDownloadGeneratedArtifact?: (artifactId: string, filename?: string | null) => Promise<boolean>;
  token?: string;
}) {
  if (messages.length === 0) {
    return (
      <div className="chatEmptyState">
        <Empty description="暂无消息，开始一次 AI 对话" />
      </div>
    );
  }

  async function copyMessageContent(content: string) {
    if (!content.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(content);
      message.success("已复制回答");
    } catch {
      message.error("复制失败，请检查浏览器权限");
    }
  }

  return (
    <div className="messageList">
      {messages.map((item) => {
        const confirmationCard = enterpriseWechatConfirmationCardFromMessage(item);
        const emailCard = emailConfirmationCardFromMessage(item);
        const downloadableAttachment = item.attachments?.find((attachment) => (
          Boolean(chatAttachmentArtifactId(attachment) || attachment.content_base64)
        ));
        const downloadableArtifactId = downloadableAttachment
          ? chatAttachmentArtifactId(downloadableAttachment)
          : "";

        return (
          <div key={item.id} className={`messageRow ${item.role}`}>
            {item.role !== "user" ? (
              <div className="messageAvatar assistant" aria-hidden="true">
                <RobotOutlined />
              </div>
            ) : null}
            <div className={`messageBubble ${item.role}`}>
                <div className="messageHeader">
                  <div className="messageIdentity">
                  <span className="messageRoleLabel">{roleLabelForMessage(item.role)}</span>
                  </div>
                <div className="messageMetaRight">
                  {item.role !== "user" && item.content ? (
                    <Tooltip title="复制回答">
                      <Button
                        type="text"
                        size="small"
                        aria-label="复制回答"
                        icon={<CopyOutlined />}
                        onClick={() => void copyMessageContent(item.content)}
                      />
                    </Tooltip>
                  ) : null}
                  {item.role !== "user" && downloadableAttachment ? (
                    <Tooltip title="下载文件">
                      <Button
                        type="text"
                        size="small"
                        aria-label="下载文件"
                        icon={<DownloadOutlined />}
                        loading={Boolean(downloadableArtifactId && downloadingArtifactId === downloadableArtifactId)}
                        onClick={() => {
                          if (downloadableArtifactId && onDownloadGeneratedArtifact) {
                            void onDownloadGeneratedArtifact(downloadableArtifactId, downloadableAttachment.filename);
                            return;
                          }
                          downloadBase64Attachment(downloadableAttachment);
                        }}
                      />
                    </Tooltip>
                  ) : null}
                  <Text type="secondary">{item.createdAt}</Text>
                </div>
              </div>
              {item.businessProgress ? (
                <div className="messageBusinessProgress">
                  <span className="messageBusinessProgressDot" />
                  <span>{item.businessProgress.label}</span>
                  {item.businessProgress.detail ? <Text type="secondary">{item.businessProgress.detail}</Text> : null}
                </div>
              ) : null}
              {item.content || !item.businessProgress ? (
                <Paragraph className="messageContent">{item.content || "正在生成..."}</Paragraph>
              ) : null}
              {item.erpReferences?.length ? (
                <Space size={[6, 6]} wrap className="erpReferenceList">
                  {item.erpReferences.map((reference) => (
                    <Tag color="geekblue" key={`${reference.resource}-${reference.record_id}`}>
                      引用：{reference.resource_label} / {reference.record_id}
                    </Tag>
                  ))}
                </Space>
              ) : null}
              {item.attachments?.length ? (
                <Space direction="vertical" size={8} className="messageAttachmentList">
                  {item.attachments.map((attachment) => {
                    const artifactId = chatAttachmentArtifactId(attachment);
                    const isGeneratedImage = item.role !== "user" && Boolean(artifactId) && attachment.mime_type?.startsWith("image/");
                    const canDownloadArtifact = Boolean(artifactId && onDownloadGeneratedArtifact);
                    const canDownloadBase64 = Boolean(attachment.content_base64);

                    return (
                      <div className="messageAttachmentItem" key={`${attachment.filename}-${attachment.size_bytes || artifactId || 0}`}>
                        <Space size={8}>
                          <TableOutlined />
                          <Text strong>{attachment.filename}</Text>
                          {attachment.size_bytes ? <Text type="secondary">{formatBytes(attachment.size_bytes)}</Text> : null}
                        </Space>
                        {isGeneratedImage && token ? <GeneratedChatImage token={token} artifactId={artifactId} alt={attachment.filename} /> : null}
                        <Button
                          size="small"
                          type="text"
                          icon={<DownloadOutlined />}
                          loading={Boolean(artifactId && downloadingArtifactId === artifactId)}
                          disabled={!canDownloadArtifact && !canDownloadBase64}
                          onClick={() => {
                            if (artifactId && onDownloadGeneratedArtifact) {
                              void onDownloadGeneratedArtifact(artifactId, attachment.filename);
                              return;
                            }
                            downloadBase64Attachment(attachment);
                          }}
                          aria-label={`下载文件 ${attachment.filename}`}
                        />
                      </div>
                    );
                  })}
                </Space>
              ) : null}
              {confirmationCard && onConfirmEnterpriseWechatSend ? (
                <EnterpriseWechatSendConfirmationCard
                  card={confirmationCard}
                  chatMessage={item}
                  confirmingKey={confirmingEnterpriseWechatKey}
                  downloadingArtifactId={downloadingArtifactId}
                  onConfirm={onConfirmEnterpriseWechatSend}
                  onDownloadArtifact={onDownloadGeneratedArtifact}
                />
              ) : null}
              {emailCard && onConfirmEmailSend ? (
                <EmailSendConfirmationCard
                  card={emailCard}
                  onConfirm={onConfirmEmailSend}
                  onDownloadArtifact={onDownloadGeneratedArtifact}
                />
              ) : null}
              {item.platformDraft ? (
                <div className="messagePlatformDraft">
                  <PlatformDraftSummary draft={item.platformDraft} />
                </div>
              ) : null}
            </div>
            {item.role === "user" ? (
              <div className="messageAvatar user" aria-hidden="true">
                我
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

type EmailConfirmationCard = {
  confirmationId: string;
  recipient: string;
  subject: string;
  sensitiveType: string;
  expiresAt: string;
  artifacts: { artifactId: string; filename: string }[];
};

function emailConfirmationCardFromMessage(item: ChatMessage): EmailConfirmationCard | null {
  const automation = recordFromUnknown(item.automation);
  const approval = recordFromUnknown(item.approvalResult);
  const card = firstRecord(automation.confirmation_card, automation.email_send, approval);
  if (!card || card.status !== "waiting_email_confirmation") return null;
  const confirmationId = textFromUnknown(card.confirmation_id);
  const recipient = textFromUnknown(card.recipient);
  const artifacts = (Array.isArray(card.artifacts) ? card.artifacts : []).map((value) => {
    const artifact = recordFromUnknown(value);
    return { artifactId: textFromUnknown(artifact.artifact_id), filename: textFromUnknown(artifact.filename) };
  }).filter((artifact) => artifact.artifactId);
  if (!confirmationId || !recipient || !artifacts.length) return null;
  return {
    confirmationId, recipient, artifacts,
    subject: textFromUnknown(card.subject),
    sensitiveType: textFromUnknown(card.sensitive_type) || "敏感文件",
    expiresAt: textFromUnknown(card.expires_at),
  };
}

function EmailSendConfirmationCard({ card, onConfirm, onDownloadArtifact }: {
  card: EmailConfirmationCard;
  onConfirm: (payload: EmailFileSendConfirmPayload) => Promise<void>;
  onDownloadArtifact?: (artifactId: string, filename?: string | null) => Promise<boolean>;
}) {
  const [recipientConfirmed, setRecipientConfirmed] = useState(false);
  const [sensitiveConfirmed, setSensitiveConfirmed] = useState(false);
  const [sending, setSending] = useState(false);
  const expired = Boolean(card.expiresAt && Date.parse(card.expiresAt) <= Date.now());
  return (
    <div className="enterpriseWechatConfirmCard">
      <div className="enterpriseWechatConfirmHeader"><Text strong>邮箱发送确认</Text><Tag color="orange">等待确认</Tag></div>
      <div><Text>收件人：{card.recipient}</Text></div>
      <div><Text>主题：{card.subject}</Text></div>
      <div><Text>敏感数据：{card.sensitiveType}，共 {card.artifacts.length} 个文件</Text></div>
      {card.artifacts.map((artifact) => (
        <div key={artifact.artifactId} className="enterpriseWechatConfirmFile">
          <Text>{artifact.filename}</Text>
          <Button size="small" icon={<DownloadOutlined />} onClick={() => void onDownloadArtifact?.(artifact.artifactId, artifact.filename)}>预览/下载</Button>
        </div>
      ))}
      <Space direction="vertical" size={6} className="enterpriseWechatConfirmChecks">
        <Checkbox checked={recipientConfirmed} onChange={(event) => setRecipientConfirmed(event.target.checked)}>我已核对收件人和附件</Checkbox>
        <Checkbox checked={sensitiveConfirmed} onChange={(event) => setSensitiveConfirmed(event.target.checked)}>我确认允许发送上述敏感数据</Checkbox>
      </Space>
      <div className="enterpriseWechatConfirmFooter">
        <Text type="secondary">{expired ? "确认已过期，请重新生成文件" : `有效期至 ${card.expiresAt}`}</Text>
        <Button type="primary" icon={<SendOutlined />} loading={sending}
          disabled={expired || !recipientConfirmed || !sensitiveConfirmed}
          onClick={() => {
            setSending(true);
            void onConfirm({ confirmation_id: card.confirmationId, recipient: card.recipient,
              artifact_ids: card.artifacts.map((artifact) => artifact.artifactId),
              recipient_confirmed: true, sensitive_data_confirmed: true,
            }).finally(() => setSending(false));
          }}>确认发送邮件</Button>
      </div>
    </div>
  );
}

function GeneratedChatImage({ token, artifactId, alt }: { token: string; artifactId: string; alt: string }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let active = true;
    let objectUrl = "";
    void downloadGeneratedFile(token, artifactId).then(file => {
      objectUrl = URL.createObjectURL(file.blob);
      if (active) setUrl(objectUrl);
      else URL.revokeObjectURL(objectUrl);
    }).catch(() => { if (active) setUrl(""); });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [token, artifactId]);
  return url ? <img src={url} alt={alt} style={{ display: "block", maxWidth: "100%", maxHeight: 330, borderRadius: 12, marginTop: 9 }} /> : null;
}

export function EnterpriseWechatSendConfirmationCard({
  card,
  chatMessage,
  confirmingKey,
  downloadingArtifactId,
  onConfirm,
  onDownloadArtifact,
}: {
  card: EnterpriseWechatConfirmationCardData;
  chatMessage: ChatMessage;
  confirmingKey: string;
  downloadingArtifactId: string;
  onConfirm: (payload: EnterpriseWechatFileSendConfirmPayload) => Promise<void>;
  onDownloadArtifact?: (artifactId: string, filename?: string | null) => Promise<boolean>;
}) {
  const initialRecipientId = card.selectedRecipientId || (card.candidates.length === 1 ? card.candidates[0].id : "");
  const [selectedRecipientId, setSelectedRecipientId] = useState(initialRecipientId);
  const [previewConfirmed, setPreviewConfirmed] = useState(false);
  const [sensitiveConfirmed, setSensitiveConfirmed] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const shouldOpenManualByDefault = !initialRecipientId && card.allowManualRecipient && card.candidates.length === 0;
  const [manualMode, setManualMode] = useState(shouldOpenManualByDefault);
  const [manualType, setManualType] = useState<EnterpriseWechatManualRecipientType>("user");
  const [manualValue, setManualValue] = useState("");
  const [manualName, setManualName] = useState("");

  useEffect(() => {
    setSelectedRecipientId(initialRecipientId);
    setPreviewConfirmed(false);
    setSensitiveConfirmed(false);
    setManualMode(shouldOpenManualByDefault);
    setManualType("user");
    setManualValue("");
    setManualName("");
  }, [card.artifact.artifactId, initialRecipientId, shouldOpenManualByDefault]);

  const selectedCandidate = card.candidates.find((candidate) => candidate.id === selectedRecipientId) || null;
  const normalizedManualValue = manualValue.trim();
  const normalizedManualName = manualName.trim();
  const manualRecipient: EnterpriseWechatRecipientCandidate | null = manualMode && normalizedManualValue
    ? {
        id: `manual:${manualType}:${normalizedManualValue}`,
        name: normalizedManualName || normalizedManualValue,
        objectType: manualType,
        objectTypeLabel: enterpriseWechatObjectTypeLabel(manualType),
        department: "",
        phoneLast4: "",
        avatarUrl: "",
        avatarText: (normalizedManualName || normalizedManualValue).slice(0, 1) || "企",
        raw: {
          id: `manual:${manualType}:${normalizedManualValue}`,
          object_type: manualType,
          object_type_label: enterpriseWechatObjectTypeLabel(manualType),
          name: normalizedManualName || normalizedManualValue,
          wechat_userid: manualType === "user" ? normalizedManualValue : null,
          chat_id: manualType === "group" ? normalizedManualValue : null,
          department_id: manualType === "department" ? normalizedManualValue : null,
          source: "manual_chat_input",
        },
      }
    : null;
  const selectedRecipient = manualMode ? manualRecipient : selectedCandidate;
  const confirmKey = enterpriseWechatConfirmKey(
    card.artifact.artifactId,
    selectedRecipient?.id || selectedRecipientId || card.recipientName,
  );
  const isConfirming = confirmingKey === confirmKey;
  const canConfirm = Boolean(
    card.artifact.artifactId
      && selectedRecipient
      && previewConfirmed
      && (!card.requiresSensitiveConfirmation || sensitiveConfirmed),
  );

  async function previewFile() {
    if (!card.artifact.artifactId || !onDownloadArtifact) {
      message.warning("没有找到可预览的文件");
      return;
    }

    setIsPreviewing(true);
    try {
      const ok = await onDownloadArtifact(card.artifact.artifactId, card.artifact.filename);
      if (ok) {
        setPreviewConfirmed(true);
      }
    } finally {
      setIsPreviewing(false);
    }
  }

  function confirmSend() {
    if (!selectedRecipient || !canConfirm) {
      return;
    }

    void onConfirm({
      artifact_id: card.artifact.artifactId,
      filename: card.artifact.filename || null,
      recipient_name: selectedRecipient.name || card.recipientName || normalizedManualValue,
      recipient_candidate_id: selectedRecipient.id,
      recipient: selectedRecipient.raw,
      source_message: card.sourceMessage || null,
      source_message_id: chatMessage.id,
      source_workflow_id: card.workflowId || null,
      thread_id: chatMessage.threadId || null,
      recipient_confirmed: true,
      sensitive_data_confirmed: previewConfirmed && (!card.requiresSensitiveConfirmation || sensitiveConfirmed),
    });
  }

  return (
    <div className="enterpriseWechatConfirmCard">
      <div className="enterpriseWechatConfirmHeader">
        <Space size={8} wrap>
          <SafetyCertificateOutlined />
          <Text strong>{card.title || "企业微信文件发送确认"}</Text>
          {card.statusLabel ? <Tag color="gold">{card.statusLabel}</Tag> : null}
        </Space>
        <Tag color="blue">无正文，仅发送文件</Tag>
      </div>

      <div className="enterpriseWechatConfirmFile">
        <Space size={8} className="enterpriseWechatConfirmFileName">
          <TableOutlined />
          <span>{card.artifact.filename || "已生成文件"}</span>
        </Space>
        <Button
          size="small"
          icon={<DownloadOutlined />}
          loading={isPreviewing || downloadingArtifactId === card.artifact.artifactId}
          disabled={!card.artifact.artifactId || !onDownloadArtifact}
          onClick={() => void previewFile()}
        >
          下载预览
        </Button>
      </div>

      <div className="enterpriseWechatRecipientBlock">
        <div className="enterpriseWechatSectionTitle">
          <TeamOutlined />
          <span>选择企业微信接收对象</span>
        </div>
        {card.recipientSearchMessage ? (
          <Text type="secondary" className="enterpriseWechatHint">{card.recipientSearchMessage}</Text>
        ) : null}
        {card.candidates.length ? (
          <div className="enterpriseWechatCandidateList">
            {card.candidates.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                className={`enterpriseWechatCandidate ${selectedRecipientId === candidate.id ? "selected" : ""}`}
                onClick={() => {
                  setSelectedRecipientId(candidate.id);
                  setManualMode(false);
                }}
              >
                <Avatar size={30} src={candidate.avatarUrl || undefined}>
                  {candidate.avatarText}
                </Avatar>
                <span className="enterpriseWechatCandidateMain">
                  <span className="enterpriseWechatCandidateNameRow">
                    <Text strong>{candidate.name}</Text>
                    <Tag>{candidate.objectTypeLabel}</Tag>
                  </span>
                  <span className="enterpriseWechatCandidateMeta">
                    {enterpriseWechatCandidateMeta(candidate)}
                  </span>
                </span>
              </button>
            ))}
          </div>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未找到匹配的企业微信接收对象" />
        )}
        {card.allowManualRecipient ? (
          <div className="enterpriseWechatManualRecipient">
            <Button
              size="small"
              type={manualMode ? "primary" : "default"}
              onClick={() => {
                setManualMode((current) => !current);
                setSelectedRecipientId("");
              }}
            >
              手动输入 userid / chat_id
            </Button>
            {manualMode ? (
              <div className="enterpriseWechatManualRecipientForm">
                <Select<EnterpriseWechatManualRecipientType>
                  size="small"
                  value={manualType}
                  onChange={setManualType}
                  options={[
                    { label: "成员 userid", value: "user" },
                    { label: "群聊 chat_id", value: "group" },
                    { label: "部门 department_id", value: "department" },
                  ]}
                />
                <Input
                  size="small"
                  value={manualValue}
                  placeholder={manualType === "user" ? "输入 userid" : manualType === "group" ? "输入 chat_id" : "输入 department_id"}
                  onChange={(event) => setManualValue(event.target.value)}
                />
                <Input
                  size="small"
                  value={manualName}
                  placeholder="显示名称，可不填"
                  onChange={(event) => setManualName(event.target.value)}
                />
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <Space direction="vertical" size={6} className="enterpriseWechatConfirmChecks">
        <Checkbox checked={previewConfirmed} onChange={(event) => setPreviewConfirmed(event.target.checked)}>
          我已预览文件内容，确认这个文件可以发送
        </Checkbox>
        {card.requiresSensitiveConfirmation ? (
          <Checkbox checked={sensitiveConfirmed} onChange={(event) => setSensitiveConfirmed(event.target.checked)}>
            我确认接收对象正确，并允许发送工资、财务或客户隐私文件
          </Checkbox>
        ) : null}
      </Space>

      <div className="enterpriseWechatConfirmFooter">
        <Text type="secondary">确认后由后端发送，并写入运行记录和审计。</Text>
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={isConfirming}
          disabled={!canConfirm}
          onClick={confirmSend}
        >
          确认发送到企业微信
        </Button>
      </div>
    </div>
  );
}

export function enterpriseWechatConfirmationCardFromMessage(messageItem: ChatMessage): EnterpriseWechatConfirmationCardData | null {
  const automation = recordFromUnknown(messageItem.automation);
  const approvalResult = recordFromUnknown(messageItem.approvalResult);
  const automationWechatSend = recordFromUnknown(automation.wechat_send);
  const approvalWechatSend = recordFromUnknown(approvalResult.wechat_send);
  const rawCard = firstRecord(
    automation.confirmation_card,
    automationWechatSend.confirmation_card,
    approvalResult.confirmation_card,
    approvalWechatSend.confirmation_card,
  );
  if (!rawCard) {
    return null;
  }

  const status = textFromUnknown(
    rawCard.status || automationWechatSend.status || automation.status || approvalResult.status,
  );
  if (status && !enterpriseWechatNeedsConfirmation(status)) {
    return null;
  }

  const artifact = recordFromUnknown(rawCard.artifact);
  const artifactId = textFromUnknown(
    artifact.artifact_id || automation.artifact_id || automationWechatSend.artifact_id,
  );
  if (!artifactId) {
    return null;
  }

  const recipientSearch = recordFromUnknown(rawCard.recipient_search || automationWechatSend.recipient_search);
  const selectedRecipient = enterpriseWechatRecipientCandidateFromUnknown(
    rawCard.selected_recipient || automationWechatSend.recipient || automation.recipient,
  );
  const candidateItems = Array.isArray(recipientSearch.items) ? recipientSearch.items : [];
  const candidates = candidateItems
    .map(enterpriseWechatRecipientCandidateFromUnknown)
    .filter((item): item is EnterpriseWechatRecipientCandidate => Boolean(item));
  if (selectedRecipient && !candidates.some((item) => item.id === selectedRecipient.id)) {
    candidates.unshift(selectedRecipient);
  }

  return {
    title: textFromUnknown(rawCard.title) || "企业微信文件发送确认",
    status,
    statusLabel: textFromUnknown(rawCard.status_label || automationWechatSend.status_label || automation.status_label),
    description: textFromUnknown(rawCard.description),
    recipientName: textFromUnknown(
      automation.recipient_name || automationWechatSend.recipient_name || recipientSearch.query || selectedRecipient?.name,
    ),
    recipientSearchMessage: textFromUnknown(recipientSearch.message || automationWechatSend.message || rawCard.description),
    allowManualRecipient: rawCard.allow_manual_recipient !== false,
    requiresRecipientSelection: Boolean(rawCard.requires_recipient_selection || recipientSearch.needs_selection),
    requiresSensitiveConfirmation: rawCard.requires_sensitive_confirmation !== false,
    workflowId: textFromUnknown(automation.workflow_id || "finance_salary_wechat_send"),
    sourceMessage: textFromUnknown(
      automation.source_message || recordFromUnknown(automationWechatSend.payload).source_message,
    ),
    artifact: {
      artifactId,
      filename: textFromUnknown(artifact.filename || automation.filename || automationWechatSend.artifact_filename) || "生成文件",
      downloadPath: textFromUnknown(artifact.download_path || automation.download_path || automationWechatSend.download_path),
      mimeType: textFromUnknown(artifact.mime_type),
    },
    candidates,
    selectedRecipientId: selectedRecipient?.id || "",
  };
}

export function enterpriseWechatRecipientCandidateFromUnknown(value: unknown): EnterpriseWechatRecipientCandidate | null {
  const record = recordFromUnknown(value);
  const name = textFromUnknown(record.name);
  if (!name) {
    return null;
  }

  const objectType = textFromUnknown(record.object_type || "user") || "user";
  const id = textFromUnknown(record.id || record.wechat_userid || record.chat_id || record.department_id || `${objectType}:${name}`);
  return {
    id,
    name,
    objectType,
    objectTypeLabel: textFromUnknown(record.object_type_label) || enterpriseWechatObjectTypeLabel(objectType),
    department: textFromUnknown(record.department),
    phoneLast4: textFromUnknown(record.phone_last4),
    avatarUrl: textFromUnknown(record.avatar_url),
    avatarText: textFromUnknown(record.avatar_text || name.slice(0, 1) || "企"),
    raw: record,
  };
}

export function enterpriseWechatCandidateMeta(candidate: EnterpriseWechatRecipientCandidate) {
  const parts = [
    candidate.department,
    candidate.phoneLast4 ? `手机尾号 ${candidate.phoneLast4}` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" / ") : "企业微信通讯录";
}

export function enterpriseWechatObjectTypeLabel(value: string) {
  const normalized = value.trim();
  if (normalized === "group") {
    return "群聊";
  }
  if (normalized === "department") {
    return "部门";
  }
  return "成员";
}

export function enterpriseWechatNeedsConfirmation(status: string) {
  return [
    "waiting_confirmation",
    "waiting_recipient_selection",
    "waiting_wechat_confirmation",
    "generated",
  ].includes(status);
}

export function downloadBase64Attachment(attachment: ChatAttachment) {
  if (!attachment.content_base64) {
    return;
  }

  const binary = atob(attachment.content_base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const blob = new Blob([bytes], {
    type: attachment.mime_type || "application/octet-stream",
  });
  downloadBlob(blob, attachment.filename || "attachment.xlsx");
}

export function roleLabelForMessage(role: ChatMessage["role"]) {
  const labels: Record<ChatMessage["role"], string> = {
    user: "用户",
    assistant: "助手",
    system: "系统",
    tool: "工具",
  };

  return labels[role];
}
