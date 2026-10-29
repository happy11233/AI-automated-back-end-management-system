import React, { useEffect, useRef, useState } from "react";
import {
  AppstoreOutlined,
  CloudUploadOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  SendOutlined,
  StopOutlined,
  TableOutlined,
} from "@ant-design/icons";
import { Button, Input, Tag, Tooltip, message } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type {
  ChatAttachment,
  EnterpriseWechatFileSendConfirmPayload,
  EmailFileSendConfirmPayload,
  Position,
  ThreadListItem,
} from "../api";
import { type ChatMessage } from "../workspace/types";
import {
  threadDisplayTitle,
  shortThreadId,
  TextArea,
  positionLabel,
  threadTitleSource,
} from "../workspace/shared";
import { MessageList } from "../components/MessageList";

export function fileToChatAttachment(file: File): Promise<ChatAttachment> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const contentBase64 = result.includes(",") ? result.slice(result.indexOf(",") + 1) : result;
      resolve({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        size_bytes: file.size,
        content_base64: contentBase64,
      });
    };
    reader.onerror = () => reject(new Error(`无法读取文件：${file.name}`));
    reader.readAsDataURL(file);
  });
}

export function ChatPanel(props: {
  messageInput: string;
  setMessageInput: (value: string) => void;
  attachments: ChatAttachment[];
  setAttachments: (value: ChatAttachment[]) => void;
  openSupportedApps: () => void;
  activeThread: ThreadListItem | null;
  activeThreadId: string;
  createThread: () => void;
  renameThread: (title: string) => Promise<boolean>;
  sendMessage: () => void;
  stopMessage: () => void;
  messages: ChatMessage[];
  isLoading: boolean;
  statusMessage: string;
  isCreatingThread: boolean;
  isRenamingThread: boolean;
  position: Position | null;
  token: string;
  confirmingEnterpriseWechatKey: string;
  downloadingArtifactId: string;
  confirmEnterpriseWechatSend: (payload: EnterpriseWechatFileSendConfirmPayload) => Promise<void>;
  confirmEmailSend: (payload: EmailFileSendConfirmPayload) => Promise<void>;
  downloadGeneratedArtifact: (artifactId: string, filename?: string | null) => Promise<boolean>;
}) {
  const title = props.activeThread
    ? threadDisplayTitle(props.activeThread, "employee")
    : props.activeThreadId ? shortThreadId(props.activeThreadId) : "新会话";
  const titleDraftSource = props.activeThread ? threadEditableTitle(props.activeThread) : title;
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(titleDraftSource);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const isComposingRef = useRef(false);
  const chatMessagesPaneRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);

  useEffect(() => {
    if (!isEditingTitle) {
      setTitleDraft(titleDraftSource);
    }
  }, [isEditingTitle, titleDraftSource]);

  useEffect(() => {
    shouldStickToBottomRef.current = true;
  }, [props.activeThreadId]);

  useEffect(() => {
    const pane = chatMessagesPaneRef.current;
    if (!pane || !props.messages.length || !shouldStickToBottomRef.current) {
      return;
    }

    pane.scrollTop = pane.scrollHeight;
  }, [props.messages, props.activeThreadId]);

  async function saveTitle() {
    const ok = await props.renameThread(titleDraft);
    if (ok) {
      setIsEditingTitle(false);
    }
  }

  async function handleFilesSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) {
      return;
    }

    const oversized = files.find((file) => file.size > 12 * 1024 * 1024);
    if (oversized) {
      message.warning(`文件过大：${oversized.name}，单个文件不能超过 12MB`);
      return;
    }

    try {
      const nextAttachments = await Promise.all(files.map(fileToChatAttachment));
      props.setAttachments([...props.attachments, ...nextAttachments]);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "附件读取失败");
    }
  }

  return (
    <ProCard bordered className="chatWorkspace" bodyStyle={{ padding: 0, height: "100%" }}>
      <div
        className="chatMessagesPane"
        ref={chatMessagesPaneRef}
        onScroll={() => {
          const pane = chatMessagesPaneRef.current;
          if (!pane) {
            return;
          }
          const distanceToBottom = pane.scrollHeight - pane.scrollTop - pane.clientHeight;
          shouldStickToBottomRef.current = distanceToBottom < 72;
        }}
      >
        <MessageList
          messages={props.messages}
          token={props.token}
          confirmingEnterpriseWechatKey={props.confirmingEnterpriseWechatKey}
          downloadingArtifactId={props.downloadingArtifactId}
          onConfirmEnterpriseWechatSend={props.confirmEnterpriseWechatSend}
          onConfirmEmailSend={props.confirmEmailSend}
          onDownloadGeneratedArtifact={props.downloadGeneratedArtifact}
        />
      </div>

      <div className="chatComposerWrap">
        <div className="chatComposer">
          <TextArea
            variant="borderless"
            className="chatComposerInput"
            placeholder="输入你要处理的问题或自动化指令"
            value={props.messageInput}
            onChange={(event) => props.setMessageInput(event.target.value)}
            onCompositionStart={() => {
              isComposingRef.current = true;
            }}
            onCompositionEnd={() => {
              isComposingRef.current = false;
            }}
            autoSize={{ minRows: 2, maxRows: 6 }}
            onPressEnter={(event) => {
              const nativeEvent = event.nativeEvent as KeyboardEvent & { isComposing?: boolean };
              if (!event.shiftKey && !nativeEvent.isComposing && !isComposingRef.current) {
                event.preventDefault();
                props.sendMessage();
              }
            }}
          />
          {props.attachments.length ? (
            <div className="chatAttachmentStrip">
              {props.attachments.map((attachment, index) => (
                <div className="chatAttachmentChip" key={`${attachment.filename}-${index}`}>
                  <TableOutlined />
                  <span>{attachment.filename}</span>
                  <Button
                    type="text"
                    size="small"
                    aria-label={`移除附件 ${attachment.filename}`}
                    icon={<DeleteOutlined />}
                    onClick={() => props.setAttachments(props.attachments.filter((_, itemIndex) => itemIndex !== index))}
                  />
                </div>
              ))}
            </div>
          ) : null}
          <div className="chatComposerFooter">
            <div className="chatComposerTools">
              <Tooltip title="上传附件">
                <Button
                  type="text"
                  aria-label="上传附件"
                  icon={<CloudUploadOutlined />}
                  onClick={() => fileInputRef.current?.click()}
                />
              </Tooltip>
              <input
                ref={fileInputRef}
                className="chatFileInput"
                type="file"
                multiple
                onChange={(event) => void handleFilesSelected(event)}
              />
              <Tooltip title="当前支持应用">
                <Button
                  type="text"
                  aria-label="当前支持应用"
                  icon={<AppstoreOutlined />}
                  onClick={props.openSupportedApps}
                />
              </Tooltip>
            </div>
            <div className="chatConversationDock">
              {isEditingTitle ? (
                <>
                  <Input
                    size="small"
                    className="chatThreadTitleInput"
                    value={titleDraft}
                    maxLength={120}
                    autoFocus
                    onChange={(event) => setTitleDraft(event.target.value)}
                    onPressEnter={() => void saveTitle()}
                  />
                  <Button
                    size="small"
                    type="primary"
                    aria-label="保存会话标题"
                    loading={props.isRenamingThread}
                    disabled={!titleDraft.trim()}
                    onClick={() => void saveTitle()}
                  >
                    保存
                  </Button>
                  <Button
                    size="small"
                    aria-label="取消修改会话标题"
                    disabled={props.isRenamingThread}
                    onClick={() => {
                      setTitleDraft(titleDraftSource);
                      setIsEditingTitle(false);
                    }}
                  >
                    取消
                  </Button>
                </>
              ) : (
                <>
                  <Tooltip title={props.activeThreadId ? `会话 ID：${props.activeThreadId}` : "待创建会话"}>
                    <button
                      type="button"
                      className="chatConversationTitle"
                      onClick={() => {
                        if (props.activeThreadId) {
                          setTitleDraft(titleDraftSource);
                          setIsEditingTitle(true);
                        }
                      }}
                    >
                      {title}
                    </button>
                  </Tooltip>
                  {props.activeThreadId ? (
                    <Tooltip title="重命名会话">
                      <Button
                        type="text"
                        size="small"
                        aria-label="重命名会话"
                        icon={<EditOutlined />}
                        onClick={() => {
                          setTitleDraft(titleDraftSource);
                          setIsEditingTitle(true);
                        }}
                      />
                    </Tooltip>
                  ) : null}
                  <Tooltip title="新建会话">
                    <Button
                      type="text"
                      size="small"
                      aria-label="新建会话"
                      loading={props.isCreatingThread}
                      icon={<PlusOutlined />}
                      onClick={props.createThread}
                    />
                  </Tooltip>
                </>
              )}
            </div>
            <div className="chatComposerActions">
              {props.position ? <Tag className="chatPositionTag">{positionLabel(props.position)}</Tag> : null}
              <Tooltip title={props.isLoading ? "终止" : "发送"}>
                <Button
                  type="primary"
                  shape="circle"
                  aria-label={props.isLoading ? "终止" : "发送"}
                  icon={props.isLoading ? <StopOutlined /> : <SendOutlined />}
                  onClick={props.isLoading ? props.stopMessage : props.sendMessage}
                />
              </Tooltip>
            </div>
          </div>
        </div>
        <div className="chatStatusLine" title={props.statusMessage}>
          {props.statusMessage}
        </div>
      </div>
    </ProCard>
  );
}

export function threadEditableTitle(thread: ThreadListItem) {
  return threadTitleSource(thread).trim();
}
