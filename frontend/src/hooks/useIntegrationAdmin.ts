import { readRoleFromToken, upsertPlatformActionExecutor } from "../workspace/appHelpers";
import { useState } from "react";
import { Modal, message } from "antd";
import {
  checkPlatformActionExecutorHealth,
  checkMcpToolHealth,
  createPlatformActionExecutor,
  deletePlatformActionExecutor,
  getConnectorDetail,
  isAuthExpiredError,
  listPlatformActionExecutors,
  listConnectors,
  listMcpTools,
  updatePlatformActionExecutor,
  updateMcpTool,
  type ConnectorDetailResponse,
  type ConnectorItem,
  type ConnectorsResponse,
  type McpToolItem,
  type McpToolsResponse,
  type PlatformActionExecutorItem,
  type PlatformActionExecutorOption,
  type PlatformActionExecutorPayload,
  type PlatformActionExecutorsResponse,
} from "../api";
import type { PlatformActionExecutorFormState } from "../workspace/types";

export function useIntegrationAdmin({ token, setStatusMessage, refreshAuditLogs }: { token: string; setStatusMessage: (value: string) => void; refreshAuditLogs: () => Promise<void> }) {
  const [connectors, setConnectors] = useState<ConnectorItem[]>([]);

  const [connectorSummary, setConnectorSummary] = useState<ConnectorsResponse["summary"] | null>(null);

  const [connectorDetail, setConnectorDetail] = useState<ConnectorDetailResponse | null>(null);

  const [isConnectorDetailOpen, setIsConnectorDetailOpen] = useState(false);

  const [isConnectorDetailLoading, setIsConnectorDetailLoading] = useState(false);

  const [isConnectorsLoading, setIsConnectorsLoading] = useState(false);

  const [mcpTools, setMcpTools] = useState<McpToolItem[]>([]);

  const [mcpToolSummary, setMcpToolSummary] = useState<McpToolsResponse["summary"] | null>(null);

  const [isMcpToolsLoading, setIsMcpToolsLoading] = useState(false);

  const [checkingMcpToolId, setCheckingMcpToolId] = useState("");

  const [updatingMcpToolId, setUpdatingMcpToolId] = useState("");

  const [platformActionExecutors, setPlatformActionExecutors] = useState<PlatformActionExecutorItem[]>([]);

  const [platformActionExecutorSummary, setPlatformActionExecutorSummary] = useState<PlatformActionExecutorsResponse["summary"] | null>(null);

  const [platformActionExecutorActionOptions, setPlatformActionExecutorActionOptions] = useState<PlatformActionExecutorOption[]>([]);

  const [platformActionExecutorTypeOptions, setPlatformActionExecutorTypeOptions] = useState<PlatformActionExecutorOption[]>([]);

  const [platformActionExecutorForm, setPlatformActionExecutorForm] = useState<PlatformActionExecutorFormState>({
    id: null,
    name: "",
    executorType: "webhook",
    actionTypes: [],
    webhookUrl: "",
    apiKey: "",
    timeoutSeconds: 12,
    enabled: true,
  });

  const [isPlatformActionExecutorsLoading, setIsPlatformActionExecutorsLoading] = useState(false);

  const [isSavingPlatformActionExecutor, setIsSavingPlatformActionExecutor] = useState(false);

  const [checkingPlatformActionExecutorId, setCheckingPlatformActionExecutorId] = useState("");

  const [deletingPlatformActionExecutorId, setDeletingPlatformActionExecutorId] = useState("");

  async function refreshConnectors(activeToken = token) {
    if (!activeToken) {
      return;
    }

    setIsConnectorsLoading(true);

    try {
      const result = await listConnectors(activeToken);
      setConnectors(result.items);
      setConnectorSummary(result.summary);
      setStatusMessage("连接器中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "连接器中心加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsConnectorsLoading(false);
    }
  }

  async function openConnectorDetail(connectorId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsConnectorDetailOpen(true);
    setIsConnectorDetailLoading(true);
    setConnectorDetail(null);

    try {
      setConnectorDetail(await getConnectorDetail(token, connectorId));
      setStatusMessage("连接器详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "连接器详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsConnectorDetailLoading(false);
    }
  }

  async function refreshMcpTools(activeToken = token) {
    if (!activeToken || readRoleFromToken(activeToken) !== "admin") {
      return;
    }

    setIsMcpToolsLoading(true);
    try {
      const result = await listMcpTools(activeToken);
      setMcpTools(result.items);
      setMcpToolSummary(result.summary);
      setStatusMessage("MCP 工具目录已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "MCP 工具目录加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsMcpToolsLoading(false);
    }
  }

  async function toggleMcpTool(item: McpToolItem, enabled: boolean) {
    if (!token) {
      return;
    }
    setUpdatingMcpToolId(item.id);
    try {
      const result = await updateMcpTool(token, item.id, {
        enabled,
        admin_note: item.admin_note || "",
      });
      setMcpTools((current) => current.map((tool) => tool.id === item.id ? result.item : tool));
      setStatusMessage(enabled ? "MCP 工具已启用" : "MCP 工具已暂停");
      message.success(enabled ? "MCP 工具已启用" : "MCP 工具已暂停");
      void refreshAuditLogs();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "MCP 工具状态更新失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setUpdatingMcpToolId("");
    }
  }

  async function checkMcpTool(item: McpToolItem) {
    if (!token) {
      return;
    }
    setCheckingMcpToolId(item.id);
    try {
      const result = await checkMcpToolHealth(token, item.id);
      setMcpTools((current) => current.map((tool) => tool.id === item.id ? result.item : tool));
      setStatusMessage("MCP 工具健康检查完成");
      message.success("MCP 工具健康检查完成");
      void refreshAuditLogs();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "MCP 工具健康检查失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setCheckingMcpToolId("");
    }
  }

  async function refreshPlatformActionExecutors(activeToken = token) {
    if (!activeToken || readRoleFromToken(activeToken) !== "admin") {
      return;
    }

    setIsPlatformActionExecutorsLoading(true);

    try {
      const result = await listPlatformActionExecutors(activeToken);
      setPlatformActionExecutors(result.items);
      setPlatformActionExecutorSummary(result.summary);
      setPlatformActionExecutorActionOptions(result.action_types);
      setPlatformActionExecutorTypeOptions(result.executor_types);
      setStatusMessage("外部执行器配置已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "外部执行器配置加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsPlatformActionExecutorsLoading(false);
    }
  }

  function resetPlatformActionExecutorForm() {
    setPlatformActionExecutorForm({
      id: null,
      name: "",
      executorType: "webhook",
      actionTypes: [],
      webhookUrl: "",
      apiKey: "",
      timeoutSeconds: 12,
      enabled: true,
    });
  }

  function editPlatformActionExecutor(item: PlatformActionExecutorItem) {
    if (item.is_environment_fallback) {
      message.info("环境变量兜底执行器为只读配置");
      return;
    }
    setPlatformActionExecutorForm({
      id: item.id,
      name: item.name,
      executorType: item.executor_type,
      actionTypes: item.action_types,
      webhookUrl: "",
      apiKey: "",
      timeoutSeconds: item.timeout_seconds || 12,
      enabled: item.enabled,
    });
    setStatusMessage(`正在编辑执行器：${item.name}`);
  }

  function buildPlatformActionExecutorPayload(): PlatformActionExecutorPayload | null {
    const name = platformActionExecutorForm.name.trim();
    const webhookUrl = platformActionExecutorForm.webhookUrl.trim();
    if (!name) {
      message.warning("请填写执行器名称");
      return null;
    }
    if (!platformActionExecutorForm.actionTypes.length) {
      message.warning("请选择至少一个平台动作");
      return null;
    }
    if (!webhookUrl && !platformActionExecutorForm.id) {
      message.warning("请填写 Webhook URL");
      return null;
    }

    const payload: PlatformActionExecutorPayload = {
      name,
      executor_type: platformActionExecutorForm.executorType,
      action_types: platformActionExecutorForm.actionTypes,
      webhook_url: webhookUrl || "__UNCHANGED__",
      timeout_seconds: platformActionExecutorForm.timeoutSeconds,
      enabled: platformActionExecutorForm.enabled,
    };
    const apiKey = platformActionExecutorForm.apiKey.trim();
    if (apiKey) {
      payload.api_key = apiKey;
    } else if (!platformActionExecutorForm.id) {
      payload.api_key = null;
    }
    return payload;
  }

  async function savePlatformActionExecutor() {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    const payload = buildPlatformActionExecutorPayload();
    if (!payload) {
      return;
    }

    setIsSavingPlatformActionExecutor(true);
    try {
      if (platformActionExecutorForm.id) {
        await updatePlatformActionExecutor(token, platformActionExecutorForm.id, payload);
        message.success("外部执行器已更新");
      } else {
        await createPlatformActionExecutor(token, payload);
        message.success("外部执行器已创建");
      }
      resetPlatformActionExecutorForm();
      await refreshPlatformActionExecutors(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "外部执行器保存失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSavingPlatformActionExecutor(false);
    }
  }

  async function checkPlatformActionExecutor(item: PlatformActionExecutorItem) {
    if (!token) {
      return;
    }
    setCheckingPlatformActionExecutorId(item.id);
    try {
      const result = await checkPlatformActionExecutorHealth(token, item.id);
      setPlatformActionExecutors((current) => upsertPlatformActionExecutor(current, result.item));
      message.success("健康检查已完成");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "健康检查失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setCheckingPlatformActionExecutorId("");
    }
  }

  function removePlatformActionExecutor(item: PlatformActionExecutorItem) {
    if (!token || item.is_environment_fallback) {
      return;
    }

    Modal.confirm({
      title: "删除外部执行器",
      content: `确认删除“${item.name}”？已有历史任务记录不会被删除。`,
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        setDeletingPlatformActionExecutorId(item.id);
        try {
          await deletePlatformActionExecutor(token, item.id);
          setPlatformActionExecutors((current) => current.filter((executor) => executor.id !== item.id));
          if (platformActionExecutorForm.id === item.id) {
            resetPlatformActionExecutorForm();
          }
          message.success("外部执行器已删除");
          void refreshPlatformActionExecutors(token);
        } catch (error) {
          if (isAuthExpiredError(error)) {
            return;
          }
          const text = error instanceof Error ? error.message : "外部执行器删除失败";
          setStatusMessage(text);
          message.error(text);
        } finally {
          setDeletingPlatformActionExecutorId("");
        }
      },
    });
  }
  function resetIntegrationAdmin() {
    setConnectors([]);
    setConnectorSummary(null);
    setConnectorDetail(null);
    setIsConnectorDetailOpen(false);
    setIsConnectorDetailLoading(false);
    setIsConnectorsLoading(false);
    setMcpTools([]);
    setMcpToolSummary(null);
    setIsMcpToolsLoading(false);
    setCheckingMcpToolId("");
    setUpdatingMcpToolId("");
    setPlatformActionExecutors([]);
    setPlatformActionExecutorSummary(null);
    setPlatformActionExecutorActionOptions([]);
    setPlatformActionExecutorTypeOptions([]);
    setPlatformActionExecutorForm({
      id: null,
      name: "",
      executorType: "webhook",
      actionTypes: [],
      webhookUrl: "",
      apiKey: "",
      timeoutSeconds: 12,
      enabled: true,
    });
    setIsPlatformActionExecutorsLoading(false);
    setIsSavingPlatformActionExecutor(false);
    setCheckingPlatformActionExecutorId("");
    setDeletingPlatformActionExecutorId("");
  }

  return {
    connectors,
    connectorSummary,
    connectorDetail,
    isConnectorDetailOpen,
    setIsConnectorDetailOpen,
    isConnectorDetailLoading,
    isConnectorsLoading,
    mcpTools,
    mcpToolSummary,
    isMcpToolsLoading,
    checkingMcpToolId,
    updatingMcpToolId,
    platformActionExecutors,
    platformActionExecutorSummary,
    platformActionExecutorActionOptions,
    platformActionExecutorTypeOptions,
    platformActionExecutorForm,
    setPlatformActionExecutorForm,
    isPlatformActionExecutorsLoading,
    isSavingPlatformActionExecutor,
    checkingPlatformActionExecutorId,
    deletingPlatformActionExecutorId,
    refreshConnectors,
    openConnectorDetail,
    refreshMcpTools,
    toggleMcpTool,
    checkMcpTool,
    refreshPlatformActionExecutors,
    resetPlatformActionExecutorForm,
    editPlatformActionExecutor,
    savePlatformActionExecutor,
    checkPlatformActionExecutor,
    removePlatformActionExecutor,
    resetIntegrationAdmin,
  };
}
