import { useEffect, useState } from "react";
import { CloudUploadOutlined } from "@ant-design/icons";
import { Button, Card, Space, Tag, message } from "antd";
import { executePlatformDraft, type PlatformDraftItem, type PlatformActionExecutionItem } from "../api";
import {
  textFromUnknown,
  platformDraftTypeLabel,
  platformDraftStatusLabel,
  platformDraftWritebackLabel,
  platformExecutionStatusColor,
  platformExecutionStatusLabel,
  platformExecutorTypeLabel,
  Paragraph,
  Text,
  Title,
} from "../workspace/shared";
import { DetailText } from "./DetailText";

export function PlatformDraftSummary({ draft }: { draft: PlatformDraftItem }) {
  const [currentDraft, setCurrentDraft] = useState(draft);
  const [latestExecution, setLatestExecution] = useState<PlatformActionExecutionItem | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  useEffect(() => {
    setCurrentDraft(draft);
    setLatestExecution(null);
  }, [draft]);

  const runExternalWriteback = async () => {
    const storedToken = localStorage.getItem("access_token") || "";
    if (!storedToken) {
      message.warning("请先登录");
      return;
    }

    setIsExecuting(true);
    try {
      const result = await executePlatformDraft(storedToken, currentDraft.id);
      setCurrentDraft(result.draft);
      setLatestExecution(result.execution);
      if (result.execution.status === "succeeded") {
        message.success("外部写回执行成功");
      } else if (result.execution.status === "waiting_executor") {
        message.info("已进入等待外部执行器状态");
      } else {
        message.error(result.message || "外部写回执行失败");
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "外部写回执行失败");
    } finally {
      setIsExecuting(false);
    }
  };

  const metadataExecutionStatus = textFromUnknown(currentDraft.metadata.latest_execution_status || "");
  const metadataExecutionId = textFromUnknown(currentDraft.metadata.latest_execution_id || "");
  const latestStatus = latestExecution?.status || metadataExecutionStatus;
  const latestExecutionId = latestExecution?.id || metadataExecutionId;

  return (
    <Card
      size="small"
      title="平台草稿写回"
      className="contextCard"
      extra={
        <Button
          size="small"
          icon={<CloudUploadOutlined />}
          loading={isExecuting}
          onClick={runExternalWriteback}
        >
          执行外部写回
        </Button>
      }
    >
      <div className="platformDraftSummaryGrid">
        <DetailText label="草稿 ID" value={currentDraft.id} mono />
        <DetailText label="类型" value={platformDraftTypeLabel(currentDraft.draft_type)} />
        <DetailText label="状态" value={platformDraftStatusLabel(currentDraft.status)} />
        <DetailText label="写回目标" value={currentDraft.external_target} mono />
        <DetailText label="写回状态" value={platformDraftWritebackLabel(currentDraft.writeback_status)} />
        <DetailText label="平台" value={currentDraft.platform} />
      </div>
      {latestStatus ? (
        <Space size={[6, 6]} wrap className="platformExecutionStatus">
          <Tag color={platformExecutionStatusColor(latestStatus)}>
            执行：{platformExecutionStatusLabel(latestStatus)}
          </Tag>
          {latestExecutionId ? <Tag>执行 ID：{latestExecutionId}</Tag> : null}
          {latestExecution?.executor_type ? <Tag>{platformExecutorTypeLabel(latestExecution.executor_type)}</Tag> : null}
        </Space>
      ) : null}
      {currentDraft.writeback_message ? (
        <Paragraph className="automationTaskResultText">{currentDraft.writeback_message}</Paragraph>
      ) : null}
    </Card>
  );
}
