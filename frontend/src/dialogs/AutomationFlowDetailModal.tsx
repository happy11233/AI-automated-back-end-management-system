import React, { useEffect, useState } from "react";
import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  DownOutlined,
  FileTextOutlined,
  HistoryOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  UpOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Checkbox,
  Col,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
  message,
} from "antd";
import {
  getAutomationFlowVersion,
  approveAutomationFlowVersion,
  createAutomationFlowVersion,
  isAuthExpiredError,
  listAutomationFlowVersionEvidence,
  listAutomationFlowVersions,
  preflightAutomationFlowVersion,
  publishAutomationFlowVersion,
  rollbackAutomationFlowPublication,
  submitAutomationFlowVersionReview,
  updateAutomationFlowVersion,
  type AutomationFlowDetailResponse,
  type AutomationFlowVersionCreatePayload,
  type AutomationFlowVerificationEvidence,
  type AutomationFlowVerificationEvidenceListResponse,
  type AutomationFlowVersionPreflightResponse,
  type AutomationFlowStepItem,
  type AutomationFlowVersionSummary,
  type AutomationFlowVersionUpdatePayload,
  type ErpResourceItem,
} from "../api";
import { type AutomationFlowVersionFormState } from "../workspace/types";
import { SchemaTable } from "../components/SchemaTable";
import { Paragraph, Text, Title, textFromUnknown, StatusTag, formatTime } from "../workspace/shared";

export function schemaDraftJson(items: Array<Record<string, unknown>> | null | undefined) {
  return JSON.stringify(items || [], null, 2);
}

export function toolParametersDraftJson(modelConfig: Record<string, unknown> | null | undefined) {
  const parameters = modelConfig?.tool_parameters;
  if (!parameters || typeof parameters !== "object" || Array.isArray(parameters)) {
    return "{}";
  }
  return JSON.stringify(parameters, null, 2);
}

export function AutomationFlowDetailModal({
  open,
  loading,
  detail,
  token,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: AutomationFlowDetailResponse | null;
  token: string;
  onClose: () => void;
}) {
  const flow = detail?.item || null;
  const [versions, setVersions] = useState<AutomationFlowVersionSummary[]>([]);
  const [isVersionListLoading, setIsVersionListLoading] = useState(false);
  const [versionActionKey, setVersionActionKey] = useState("");
  const [editingVersionId, setEditingVersionId] = useState("");
  const [versionPreflightResult, setVersionPreflightResult] = useState<AutomationFlowVersionPreflightResponse | null>(null);
  const [versionEvidenceResult, setVersionEvidenceResult] = useState<AutomationFlowVerificationEvidenceListResponse | null>(null);
  const [isVersionEvidenceLoading, setIsVersionEvidenceLoading] = useState(false);
  const [versionEvidenceLoadingId, setVersionEvidenceLoadingId] = useState("");
  const [versionForm, setVersionForm] = useState<AutomationFlowVersionFormState>({
    version: "",
    changeSummary: "",
    approvalPolicy: "",
    failureStrategy: "",
    publishNotes: "",
    promptSummary: "",
    promptTemplatePreview: "",
    inputSchemaJson: "[]",
    outputSchemaJson: "[]",
    toolParametersJson: "{}",
    allowedTools: [],
    allowedErpResources: [],
    selectedStepIds: [],
    publishEnvironment: "production",
  });

  useEffect(() => {
    if (!open) {
      setVersions([]);
      setVersionActionKey("");
      setEditingVersionId("");
      setVersionPreflightResult(null);
      setVersionEvidenceResult(null);
      setIsVersionEvidenceLoading(false);
      setVersionEvidenceLoadingId("");
      return;
    }

    if (!flow || !token) {
      return;
    }

    resetVersionForm(flow);
    setVersionPreflightResult(null);
    setVersionEvidenceResult(null);
    setVersionEvidenceLoadingId("");
    void refreshVersions();
  }, [open, flow?.id, token]);

  function resetVersionForm(nextFlow = flow) {
    setVersionForm({
      version: "",
      changeSummary: "",
      approvalPolicy: nextFlow?.approval_policy || "",
      failureStrategy: nextFlow?.failure_strategy || "",
      publishNotes: "",
      promptSummary: nextFlow?.prompt_summary || "",
      promptTemplatePreview: nextFlow?.prompt_template_preview || "",
      inputSchemaJson: schemaDraftJson(nextFlow?.input_schema),
      outputSchemaJson: schemaDraftJson(nextFlow?.output_schema),
      toolParametersJson: toolParametersDraftJson(nextFlow?.model_config),
      allowedTools: nextFlow?.allowed_tools || [],
      allowedErpResources: nextFlow?.allowed_erp_resources || [],
      selectedStepIds: nextFlow?.steps.map((item) => item.id) || [],
      publishEnvironment: "production",
    });
    setEditingVersionId("");
  }

  async function refreshVersions() {
    if (!flow || !token) {
      setVersions([]);
      return;
    }

    setIsVersionListLoading(true);
    try {
      const result = await listAutomationFlowVersions(token, flow.id);
      setVersions(result.items);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "流程版本列表加载失败";
      message.error(text);
    } finally {
      setIsVersionListLoading(false);
    }
  }

  function buildCreatePayload(): AutomationFlowVersionCreatePayload | null {
    const changeSummary = versionForm.changeSummary.trim();
    const approvalPolicy = versionForm.approvalPolicy.trim();
    const failureStrategy = versionForm.failureStrategy.trim();

    if (!changeSummary) {
      message.warning("请填写变更摘要");
      return null;
    }
    if (!approvalPolicy) {
      message.warning("请填写审批策略");
      return null;
    }
    if (!failureStrategy) {
      message.warning("请填写失败策略");
      return null;
    }

    return {
      version: versionForm.version.trim() || undefined,
      change_summary: changeSummary,
      approval_policy: approvalPolicy,
      failure_strategy: failureStrategy,
      publish_notes: versionForm.publishNotes.trim() || undefined,
    };
  }

  function parseSchemaJson(textValue: string, label: string): Array<Record<string, unknown>> | null {
    const text = textValue.trim();
    if (!text) {
      message.warning(`请填写${label} JSON`);
      return null;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "格式不正确";
      message.warning(`${label} JSON 解析失败：${detail}`);
      return null;
    }

    if (!Array.isArray(parsed)) {
      message.warning(`${label} 必须是数组`);
      return null;
    }
    if (!parsed.length) {
      message.warning(`${label} 至少保留一项`);
      return null;
    }
    if (!parsed.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      message.warning(`${label} 数组项必须是对象`);
      return null;
    }

    return parsed as Array<Record<string, unknown>>;
  }

  function parseToolParametersJson(): Record<string, Record<string, unknown>> | null {
    const text = versionForm.toolParametersJson.trim();
    if (!text) {
      message.warning("请填写工具参数 JSON");
      return null;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "格式不正确";
      message.warning(`工具参数 JSON 解析失败：${detail}`);
      return null;
    }

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      message.warning("工具参数必须是对象");
      return null;
    }
    if (!Object.values(parsed).every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      message.warning("工具参数每个工具的值都必须是对象");
      return null;
    }

    return parsed as Record<string, Record<string, unknown>>;
  }

  function buildUpdatePayload(): AutomationFlowVersionUpdatePayload | null {
    const changeSummary = versionForm.changeSummary.trim();
    const approvalPolicy = versionForm.approvalPolicy.trim();
    const failureStrategy = versionForm.failureStrategy.trim();
    const promptSummary = versionForm.promptSummary.trim();
    const promptTemplatePreview = versionForm.promptTemplatePreview.trim();
    const allowedTools = Array.from(new Set(versionForm.allowedTools.map((item) => item.trim()).filter(Boolean)));
    const projectionResourcesByKey = new Map(flow?.allowed_erp_resources.map((item) => [item.resource, item]) || []);
    const allowedErpResources = Array.from(new Set(versionForm.allowedErpResources.map((item) => item.resource)))
      .map((resource) => projectionResourcesByKey.get(resource))
      .filter((item): item is ErpResourceItem => Boolean(item));
    const projectionStepsById = new Map(flow?.steps.map((item) => [item.id, item]) || []);
    const steps = Array.from(new Set(versionForm.selectedStepIds))
      .map((stepId) => projectionStepsById.get(stepId))
      .filter((item): item is AutomationFlowStepItem => Boolean(item));

    if (!editingVersionId) {
      message.warning("请先载入一个草稿版本");
      return null;
    }
    if (!changeSummary) {
      message.warning("请填写变更摘要");
      return null;
    }
    if (!approvalPolicy) {
      message.warning("请填写审批策略");
      return null;
    }
    if (!failureStrategy) {
      message.warning("请填写失败策略");
      return null;
    }
    if (!promptSummary) {
      message.warning("请填写 Prompt 摘要");
      return null;
    }
    if (!promptTemplatePreview) {
      message.warning("请填写 Prompt 模板预览");
      return null;
    }
    const inputSchema = parseSchemaJson(versionForm.inputSchemaJson, "输入 Schema");
    if (!inputSchema) {
      return null;
    }
    const outputSchema = parseSchemaJson(versionForm.outputSchemaJson, "输出 Schema");
    if (!outputSchema) {
      return null;
    }
    const toolParameters = parseToolParametersJson();
    if (!toolParameters) {
      return null;
    }
    if (!allowedTools.length) {
      message.warning("允许工具至少保留一项");
      return null;
    }
    if (!steps.length) {
      message.warning("执行步骤至少保留一项");
      return null;
    }

    return {
      change_summary: changeSummary,
      approval_policy: approvalPolicy,
      failure_strategy: failureStrategy,
      publish_notes: versionForm.publishNotes.trim() || undefined,
      prompt_summary: promptSummary,
      prompt_template_preview: promptTemplatePreview,
      input_schema: inputSchema,
      output_schema: outputSchema,
      tool_parameters: toolParameters,
      allowed_tools: allowedTools,
      allowed_erp_resources: allowedErpResources,
      steps,
    };
  }

  function moveSelectedStep(stepId: string, direction: -1 | 1) {
    setVersionForm((current) => {
      const nextStepIds = [...current.selectedStepIds];
      const index = nextStepIds.indexOf(stepId);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= nextStepIds.length) {
        return current;
      }
      [nextStepIds[index], nextStepIds[nextIndex]] = [nextStepIds[nextIndex], nextStepIds[index]];
      return {
        ...current,
        selectedStepIds: nextStepIds,
      };
    });
  }

  async function runVersionAction(actionKey: string, successText: string, action: () => Promise<void>) {
    if (!token) {
      message.warning("请先登录管理员账号");
      return;
    }

    setVersionActionKey(actionKey);
    try {
      await action();
      await refreshVersions();
      message.success(successText);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "流程版本操作失败";
      message.error(text);
    } finally {
      setVersionActionKey("");
    }
  }

  async function createDraftVersion() {
    if (!flow) {
      return;
    }
    const payload = buildCreatePayload();
    if (!payload) {
      return;
    }

    await runVersionAction("create", "草稿版本已创建", async () => {
      await createAutomationFlowVersion(token, flow.id, payload);
      resetVersionForm(flow);
    });
  }

  async function saveDraftVersion() {
    const payload = buildUpdatePayload();
    if (!payload) {
      return;
    }

    await runVersionAction(`${editingVersionId}:save`, "草稿治理字段已保存", async () => {
      await updateAutomationFlowVersion(token, editingVersionId, payload);
      resetVersionForm(flow);
    });
  }

  async function loadDraftVersion(record: AutomationFlowVersionSummary) {
    if (record.status !== "draft") {
      message.info("只有草稿版本可以载入编辑");
      return;
    }

    setVersionActionKey(`${record.id}:load`);
    try {
      const detailResult = await getAutomationFlowVersion(token, record.id);
      const version = detailResult.item;
      setEditingVersionId(version.id);
      setVersionForm((current) => ({
        ...current,
        version: version.version,
        changeSummary: version.change_summary || "",
        approvalPolicy: version.approval_policy,
        failureStrategy: version.failure_strategy,
        publishNotes: version.publish_notes || "",
        promptSummary: version.prompt_summary || "",
        promptTemplatePreview: version.prompt_template_preview || "",
        inputSchemaJson: schemaDraftJson(version.input_schema),
        outputSchemaJson: schemaDraftJson(version.output_schema),
        toolParametersJson: toolParametersDraftJson(version.model_config),
        allowedTools: version.allowed_tools || [],
        allowedErpResources: version.allowed_erp_resources || [],
        selectedStepIds: (version.steps || [])
          .map((item) => String(item.id || "").trim())
          .filter(Boolean),
      }));
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "草稿版本详情加载失败";
      message.error(text);
    } finally {
      setVersionActionKey("");
    }
  }

  function submitVersionReview(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:submit`, "版本已提交审核", async () => {
      await submitAutomationFlowVersionReview(token, record.id);
    });
  }

  function approveVersion(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:approve`, "版本已批准", async () => {
      await approveAutomationFlowVersion(token, record.id);
    });
  }

  function preflightVersion(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:preflight`, "发布前预检已完成", async () => {
      const result = await preflightAutomationFlowVersion(token, record.id);
      setVersionPreflightResult(result);
      if (!result.ok) {
        message.warning(`预检未通过：${result.blocking_failures} 项阻断`);
      }
    });
  }

  async function loadVersionEvidence(record: AutomationFlowVersionSummary) {
    if (!token) {
      message.warning("请先登录管理员账号");
      return;
    }

    setIsVersionEvidenceLoading(true);
    setVersionEvidenceLoadingId(record.id);
    try {
      const result = await listAutomationFlowVersionEvidence(token, record.id);
      setVersionEvidenceResult(result);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "发布证据加载失败";
      message.error(text);
    } finally {
      setIsVersionEvidenceLoading(false);
      setVersionEvidenceLoadingId("");
    }
  }

  function publishVersion(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:publish`, "版本已发布", async () => {
      await publishAutomationFlowVersion(token, record.id, {
        environment: versionForm.publishEnvironment,
        reason: versionForm.publishNotes.trim() || `发布流程版本 ${record.version}`,
      });
    });
  }

  function rollbackPublication(record: AutomationFlowVersionSummary) {
    if (!record.active_publication_id) {
      return;
    }

    void runVersionAction(`${record.id}:rollback`, "发布版本已回滚", async () => {
      await rollbackAutomationFlowPublication(token, record.active_publication_id || "", {
        reason: versionForm.publishNotes.trim() || `回滚流程版本 ${record.version}`,
      });
    });
  }

  return (
    <Modal
      open={open}
      title={flow ? `流程配置 / ${flow.name}` : "流程配置"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={980}
    >
      {loading ? (
        <Empty description="正在加载流程配置详情" />
      ) : flow ? (
        <Tabs
          className="flowConfigDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <div className="flowConfigDetailGrid">
                  <FlowConfigDetailItem label="流程 ID" value={flow.id} mono />
                  <FlowConfigDetailItem label="应用 ID" value={flow.app_id} mono />
                  <FlowConfigDetailItem label="岗位" value={flow.position_label} />
                  <FlowConfigDetailItem label="类别" value={flow.category} />
                  <FlowConfigDetailItem label="入口" value={flow.entrypoint} mono />
                  <FlowConfigDetailItem label="触发方式" value={flow.trigger_type} mono />
                  <FlowConfigDetailItem label="版本" value={flow.version} mono />
                  <FlowConfigDetailItem label="负责人" value={flow.owner} />
                </div>
              ),
            },
            {
              key: "schema",
              label: "Schema",
              children: (
                <Row gutter={[12, 12]} className="flowConfigDetailTabGrid">
                  <Col xs={24} md={12}>
                    <Card title="输入 Schema" size="small" className="flowConfigDetailSectionCard">
                      <SchemaTable items={flow.input_schema} />
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="输出 Schema" size="small" className="flowConfigDetailSectionCard">
                      <SchemaTable items={flow.output_schema} />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "prompt",
              label: "Prompt",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <Row gutter={[12, 12]} className="flowConfigDetailTabGrid">
                    <Col xs={24} md={12}>
                      <Card title="Prompt 摘要" size="small" className="flowConfigDetailSectionCard">
                        <Paragraph className="flowConfigDetailPreview">{flow.prompt_summary || "-"}</Paragraph>
                      </Card>
                    </Col>
                    <Col xs={24} md={12}>
                      <Card title="模板预览" size="small" className="flowConfigDetailSectionCard">
                        <pre className="flowConfigPre">{flow.prompt_template_preview || "无独立 Prompt。"}</pre>
                      </Card>
                    </Col>
                  </Row>
                  <Space size={[6, 6]} wrap>
                    {Object.entries(flow.model_config).map(([key, value]) => (
                      <Tag key={key} color={key === "secrets_visible" ? "green" : "blue"}>
                        {key}: {textFromUnknown(value)}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              ),
            },
            {
              key: "permissions",
              label: "权限",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <Row gutter={[12, 12]} className="flowConfigDetailTabGrid">
                    <Col xs={24} md={8}>
                      <Card title="允许工具" size="small" className="flowConfigDetailSectionCard">
                        <Space size={[6, 6]} wrap className="flowConfigTagBlock">
                          {flow.allowed_tools.map((item) => (
                            <Tag color="blue" key={item}>{item}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="审批策略" size="small" className="flowConfigDetailSectionCard">
                        <Paragraph className="flowConfigDetailPreview compact">{flow.approval_policy}</Paragraph>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="失败策略" size="small" className="flowConfigDetailSectionCard">
                        <Paragraph className="flowConfigDetailPreview compact">{flow.failure_strategy}</Paragraph>
                      </Card>
                    </Col>
                  </Row>
                  <Card title="允许资源" size="small" className="flowConfigDetailSectionCard">
                    <div className="flowConfigResourceList">
                      {flow.allowed_erp_resources.length ? (
                        flow.allowed_erp_resources.map((resource) => (
                          <Tag color="geekblue" key={resource.resource}>
                            {resource.label} / {resource.resource}
                          </Tag>
                        ))
                      ) : (
                        <Text type="secondary">该流程不直接访问 ERP 资源</Text>
                      )}
                    </div>
                  </Card>
                  <Card title="权限规则" size="small" className="flowConfigDetailSectionCard">
                    <div className="flowConfigRuleList">
                      {flow.permission_rules.map((item) => (
                        <div className="flowConfigRuleItem" key={item}>{item}</div>
                      ))}
                    </div>
                  </Card>
                </Space>
              ),
            },
            {
              key: "governance",
              label: "版本治理",
              children: (
                <Space direction="vertical" size={12} className="pageStack flowGovernancePanel">
                  <Card
                    title={editingVersionId ? "编辑草稿治理字段" : "创建草稿版本"}
                    size="small"
                    className="flowConfigDetailSectionCard"
                    extra={
                      <Button size="small" onClick={() => resetVersionForm(flow)}>
                        清空
                      </Button>
                    }
                  >
                    <div className="flowGovernanceDraftGrid">
                      <div className="flowGovernanceField">
                        <Text type="secondary">版本号</Text>
                        <Input
                          aria-label="版本号"
                          value={versionForm.version}
                          disabled={Boolean(editingVersionId)}
                          placeholder="留空自动递增"
                          onChange={(event) => setVersionForm((current) => ({ ...current, version: event.target.value }))}
                        />
                      </div>
                      <div className="flowGovernanceField">
                        <Text type="secondary">发布环境</Text>
                        <Select
                          value={versionForm.publishEnvironment}
                          options={[
                            { label: "生产", value: "production" },
                            { label: "预发", value: "staging" },
                            { label: "开发", value: "dev" },
                          ]}
                          onChange={(value) => setVersionForm((current) => ({
                            ...current,
                            publishEnvironment: value as AutomationFlowVersionFormState["publishEnvironment"],
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">变更摘要</Text>
                        <Input.TextArea
                          aria-label="变更摘要"
                          rows={2}
                          value={versionForm.changeSummary}
                          placeholder="说明这次流程配置变更"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            changeSummary: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField">
                        <Text type="secondary">审批策略</Text>
                        <Input.TextArea
                          aria-label="审批策略"
                          rows={3}
                          value={versionForm.approvalPolicy}
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            approvalPolicy: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField">
                        <Text type="secondary">失败策略</Text>
                        <Input.TextArea
                          aria-label="失败策略"
                          rows={3}
                          value={versionForm.failureStrategy}
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            failureStrategy: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">发布说明</Text>
                        <Input.TextArea
                          aria-label="发布说明"
                          rows={2}
                          value={versionForm.publishNotes}
                          placeholder="用于发布或回滚原因"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            publishNotes: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">Prompt 摘要</Text>
                        <Input.TextArea
                          aria-label="Prompt 摘要"
                          rows={3}
                          value={versionForm.promptSummary}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑该流程的 Prompt 摘要"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            promptSummary: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">Prompt 模板预览</Text>
                        <Input.TextArea
                          aria-label="Prompt 模板预览"
                          rows={6}
                          value={versionForm.promptTemplatePreview}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑该流程的 Prompt 模板"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            promptTemplatePreview: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">输入 Schema JSON</Text>
                        <Input.TextArea
                          aria-label="输入 Schema JSON"
                          rows={8}
                          value={versionForm.inputSchemaJson}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑输入 Schema"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            inputSchemaJson: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">输出 Schema JSON</Text>
                        <Input.TextArea
                          aria-label="输出 Schema JSON"
                          rows={8}
                          value={versionForm.outputSchemaJson}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑输出 Schema"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            outputSchemaJson: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">工具参数 JSON</Text>
                        <Input.TextArea
                          aria-label="工具参数 JSON"
                          rows={8}
                          value={versionForm.toolParametersJson}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑白名单工具参数"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            toolParametersJson: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">允许工具</Text>
                        <Checkbox.Group
                          className="flowGovernanceToolGroup"
                          value={versionForm.allowedTools}
                          disabled={!editingVersionId}
                          onChange={(values) => setVersionForm((current) => ({
                            ...current,
                            allowedTools: values.map((item) => String(item)),
                          }))}
                        >
                          <Space size={[8, 6]} wrap>
                            {flow.allowed_tools.map((item) => (
                              <Checkbox key={item} value={item}>{item}</Checkbox>
                            ))}
                          </Space>
                        </Checkbox.Group>
                      </div>
                      {flow.allowed_erp_resources.length ? (
                        <div className="flowGovernanceField flowGovernanceWideField">
                          <Text type="secondary">允许 ERP 资源</Text>
                          <Checkbox.Group
                            className="flowGovernanceToolGroup"
                            value={versionForm.allowedErpResources.map((item) => item.resource)}
                            disabled={!editingVersionId}
                            onChange={(values) => setVersionForm((current) => {
                              const selected = new Set(values.map((item) => String(item)));
                              return {
                                ...current,
                                allowedErpResources: flow.allowed_erp_resources.filter((item) => selected.has(item.resource)),
                              };
                            })}
                          >
                            <Space size={[8, 6]} wrap>
                              {flow.allowed_erp_resources.map((item) => (
                                <Checkbox key={item.resource} value={item.resource}>
                                  {item.label} / {item.resource}
                                </Checkbox>
                              ))}
                            </Space>
                          </Checkbox.Group>
                        </div>
                      ) : null}
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <div className="flowGovernanceFieldHeader">
                          <Text type="secondary">执行步骤编排</Text>
                          <Tooltip title="当前只允许选择代码投影内步骤并调整安全顺序，不能编辑步骤对象内容或新增任意步骤">
                            <Tag color="cyan">投影步骤</Tag>
                          </Tooltip>
                        </div>
                        <Checkbox.Group
                          className="flowGovernanceToolGroup"
                          value={versionForm.selectedStepIds}
                          disabled={!editingVersionId}
                          onChange={(values) => setVersionForm((current) => ({
                            ...current,
                            selectedStepIds: [
                              ...current.selectedStepIds.filter((stepId) => values.includes(stepId)),
                              ...values.map((item) => String(item)).filter((stepId) => !current.selectedStepIds.includes(stepId)),
                            ],
                          }))}
                        >
                          <Space size={[8, 6]} wrap>
                            {flow.steps.map((item) => (
                              <Checkbox key={item.id} value={item.id}>
                                {item.name} / {item.id}
                              </Checkbox>
                            ))}
                          </Space>
                        </Checkbox.Group>
                        <div className="flowGovernanceStepOrderList">
                          {versionForm.selectedStepIds.length ? (
                            versionForm.selectedStepIds.map((stepId, index) => {
                              const step = flow.steps.find((item) => item.id === stepId);
                              return (
                                <div className="flowGovernanceStepOrderItem" key={stepId}>
                                  <div className="flowGovernanceStepOrderText">
                                    <Text strong>{index + 1}. {step?.name || stepId}</Text>
                                    <Text type="secondary" className="flowConfigMono">{stepId}</Text>
                                  </div>
                                  <Space size={4} className="flowGovernanceStepOrderActions">
                                    <Tooltip title="上移步骤">
                                      <Button
                                        aria-label={`上移步骤 ${stepId}`}
                                        icon={<UpOutlined />}
                                        size="small"
                                        disabled={!editingVersionId || index === 0}
                                        onClick={() => moveSelectedStep(stepId, -1)}
                                      />
                                    </Tooltip>
                                    <Tooltip title="下移步骤">
                                      <Button
                                        aria-label={`下移步骤 ${stepId}`}
                                        icon={<DownOutlined />}
                                        size="small"
                                        disabled={!editingVersionId || index === versionForm.selectedStepIds.length - 1}
                                        onClick={() => moveSelectedStep(stepId, 1)}
                                      />
                                    </Tooltip>
                                  </Space>
                                </div>
                              );
                            })
                          ) : (
                            <Text type="secondary">至少保留一个投影内步骤</Text>
                          )}
                        </div>
                      </div>
                      <div className="flowGovernanceActions flowGovernanceWideField">
                        <Space size={8} wrap>
                          <Button
                            icon={<SaveOutlined />}
                            disabled={!editingVersionId}
                            loading={versionActionKey === `${editingVersionId}:save`}
                            onClick={saveDraftVersion}
                          >
                            保存草稿
                          </Button>
                          <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            loading={versionActionKey === "create"}
                            onClick={createDraftVersion}
                          >
                            创建草稿
                          </Button>
                        </Space>
                      </div>
                    </div>
                  </Card>

                  <Card
                    title="版本列表"
                    size="small"
                    className="flowConfigDetailSectionCard"
                    extra={
                      <Button size="small" icon={<ReloadOutlined />} loading={isVersionListLoading} onClick={refreshVersions}>
                        刷新
                      </Button>
                    }
                  >
                    <Table<AutomationFlowVersionSummary>
                      rowKey="id"
                      size="small"
                      dataSource={versions}
                      loading={isVersionListLoading}
                      className="flowGovernanceTable"
                      scroll={{ x: 1080 }}
                      locale={{ emptyText: <Empty description="暂无流程版本" /> }}
                      columns={[
                        {
                          title: "版本",
                          dataIndex: "version",
                          width: 150,
                          render: (_, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Text strong className="flowConfigMono">{record.version}</Text>
                              <Text type="secondary" className="flowConfigMono">No.{record.version_number}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "状态",
                          dataIndex: "status",
                          width: 112,
                          render: (value) => <StatusTag value={String(value)} />,
                        },
                        {
                          title: "编辑",
                          dataIndex: "id",
                          width: 112,
                          render: (_, record) => {
                            const canEdit = record.status === "draft";
                            return (
	                              <Button
	                                size="small"
                                  aria-label="载入"
	                                disabled={!canEdit}
	                                loading={versionActionKey === `${record.id}:load`}
	                                onClick={() => void loadDraftVersion(record)}
	                              >
                                载入
                              </Button>
                            );
                          },
                        },
                        {
                          title: "证据",
                          dataIndex: "id",
                          width: 112,
                          render: (_, record) => (
	                            <Button
	                              size="small"
                                aria-label="证据"
	                              icon={<FileTextOutlined />}
	                              loading={isVersionEvidenceLoading && versionEvidenceLoadingId === record.id}
	                              onClick={() => loadVersionEvidence(record)}
	                            >
                              证据
                            </Button>
                          ),
                        },
                        {
                          title: "变更摘要",
                          dataIndex: "change_summary",
                          width: 260,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Text className="flowConfigPreview">{value || "-"}</Text>
                              {record.publish_notes ? (
                                <Text type="secondary" className="flowConfigPreview">{record.publish_notes}</Text>
                              ) : null}
                            </Space>
                          ),
                        },
                        {
                          title: "审批",
                          dataIndex: "approved_by_username",
                          width: 170,
                          render: (_, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Text className="flowConfigText">{record.approved_by_username || "-"}</Text>
                              <Text type="secondary" className="flowConfigMono">{formatTime(record.approved_at || "")}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "发布",
                          dataIndex: "published_by_username",
                          width: 190,
                          render: (_, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Space size={4} wrap>
                                <Text className="flowConfigText">{record.published_by_username || "-"}</Text>
                                {record.active_publication_environment ? (
                                  <Tag color="green">{record.active_publication_environment}</Tag>
                                ) : null}
                              </Space>
                              <Text type="secondary" className="flowConfigMono">{formatTime(record.published_at || "")}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "操作",
                          dataIndex: "id",
                          fixed: "right",
                          width: 310,
                          render: (_, record) => {
                            const canEdit = record.status === "draft";
                            const canSubmit = record.status === "draft" || record.status === "rejected";
                            const canApprove = record.status === "reviewing";
                            const canPublish = record.status === "approved" || record.status === "published";
                            const canRollback = Boolean(record.active_publication_id);

                            return (
                              <Space size={6} wrap className="flowGovernanceActionCell">
	                                <Button
	                                  size="small"
                                    aria-label="载入"
	                                  disabled={!canEdit}
	                                  loading={versionActionKey === `${record.id}:load`}
	                                  onClick={() => void loadDraftVersion(record)}
	                                >
                                  载入
                                </Button>
	                                <Button
	                                  size="small"
                                    aria-label="提交审核"
	                                  disabled={!canSubmit}
	                                  loading={versionActionKey === `${record.id}:submit`}
	                                  onClick={() => submitVersionReview(record)}
	                                >
                                  提交审核
                                </Button>
		                                <Button
		                                  size="small"
                                      aria-label="批准"
		                                  icon={<CheckCircleOutlined />}
		                                  disabled={!canApprove}
		                                  loading={versionActionKey === `${record.id}:approve`}
	                                  onClick={() => approveVersion(record)}
	                                >
	                                  批准
	                                </Button>
	                                <Button
	                                  size="small"
                                    aria-label="预检"
	                                  icon={<SafetyCertificateOutlined />}
	                                  loading={versionActionKey === `${record.id}:preflight`}
	                                  onClick={() => preflightVersion(record)}
                                >
                                  预检
                                </Button>
	                                <Popconfirm
	                                  title="发布流程版本"
	                                  okText="发布"
                                  cancelText="取消"
                                  disabled={!canPublish}
                                  onConfirm={() => publishVersion(record)}
                                >
	                                  <Button
	                                    size="small"
                                      aria-label="发布"
	                                    type={canPublish ? "primary" : "default"}
	                                    icon={<CloudUploadOutlined />}
	                                    disabled={!canPublish}
                                    loading={versionActionKey === `${record.id}:publish`}
                                  >
                                    发布
                                  </Button>
                                </Popconfirm>
                                <Popconfirm
                                  title="回滚发布版本"
                                  okText="回滚"
                                  cancelText="取消"
                                  disabled={!canRollback}
                                  onConfirm={() => rollbackPublication(record)}
                                >
	                                  <Button
	                                    size="small"
                                      aria-label="回滚"
	                                    danger
	                                    icon={<HistoryOutlined />}
	                                    disabled={!canRollback}
                                    loading={versionActionKey === `${record.id}:rollback`}
                                  >
                                    回滚
                                  </Button>
                                </Popconfirm>
                              </Space>
                            );
                          },
                        },
	                      ]}
	                    />
	                  </Card>
                  {versionEvidenceResult ? (
                    <Card
                      title="发布证据"
                      size="small"
                      className="flowConfigDetailSectionCard flowEvidenceCard"
                      extra={
                        <Space size={6} wrap>
                          <Tag color="blue">{versionEvidenceResult.version}</Tag>
                          <Tag color="purple">{versionEvidenceResult.total} 条</Tag>
                        </Space>
                      }
                    >
                      <div className="flowEvidenceSummary">
                        <Text className="flowConfigMono">
                          {versionEvidenceResult.flow_key}
                        </Text>
                        <Text type="secondary" className="flowConfigMono">
                          快照：{versionEvidenceResult.snapshot_hash.slice(0, 12)}
                        </Text>
                      </div>
                      <Table<AutomationFlowVerificationEvidence>
                        rowKey="id"
                        size="small"
                        dataSource={versionEvidenceResult.items}
                        loading={isVersionEvidenceLoading}
                        pagination={false}
                        className="flowEvidenceTable"
                        scroll={{ x: 980 }}
                        locale={{ emptyText: <Empty description="暂无发布证据" /> }}
                        columns={[
                          {
                            title: "报告",
                            dataIndex: "report_id",
                            width: 220,
                            render: (value, record) => (
                              <Space direction="vertical" size={2} className="flowConfigCellStack">
                                <Text strong className="flowConfigMono">{String(value)}</Text>
                                <Text type="secondary" className="flowConfigPreview">{record.summary || "-"}</Text>
                              </Space>
                            ),
                          },
                          {
                            title: "状态",
                            dataIndex: "status",
                            width: 150,
                            render: (_, record) => (
                              <Space size={4} wrap>
                                <Tag color={record.status === "passed" ? "green" : "red"}>
                                  {record.status === "passed" ? "通过" : "失败"}
                                </Tag>
                                {record.is_publish_eligible ? (
                                  <Tag color="cyan">可发布</Tag>
                                ) : null}
                                {!record.matches_current_snapshot ? (
                                  <Tag color="gold">旧快照</Tag>
                                ) : null}
                              </Space>
                            ),
                          },
                          {
                            title: "脚本",
                            dataIndex: "script",
                            width: 260,
                            render: (_, record) => (
                              <Space direction="vertical" size={2} className="flowConfigCellStack">
                                <Text className="flowConfigMono">{record.script}</Text>
                                <Text type="secondary" className="flowConfigMono">{record.command}</Text>
                              </Space>
                            ),
                          },
                          {
                            title: "范围",
                            dataIndex: "evidence_scope",
                            width: 130,
                            render: (_, record) => (
                              <Space size={4} wrap>
                                <Tag color={record.is_current_version ? "blue" : "geekblue"}>
                                  {record.is_current_version ? "当前版本" : "同快照复用"}
                                </Tag>
                                <Tag color={record.profile === "release" ? "purple" : "cyan"}>{record.profile}</Tag>
                              </Space>
                            ),
                          },
                          {
                            title: "时间",
                            dataIndex: "verified_at",
                            width: 190,
                            render: (_, record) => (
                              <Space direction="vertical" size={2} className="flowConfigCellStack">
                                <Text className="flowConfigMono">{formatTime(record.verified_at)}</Text>
                                <Text type="secondary" className="flowConfigMono">有效至 {formatTime(record.expires_at)}</Text>
                              </Space>
                            ),
                          },
                        ]}
                      />
                    </Card>
                  ) : null}
                  {versionPreflightResult ? (
                    <Card
                      title="发布前预检"
                      size="small"
                      className="flowConfigDetailSectionCard flowPreflightCard"
                      extra={
                        <Tag color={versionPreflightResult.ok ? "green" : "red"}>
                          {versionPreflightResult.ok ? "预检通过" : `${versionPreflightResult.blocking_failures} 项阻断`}
                        </Tag>
                      }
                    >
                      <div className="flowPreflightSummary">
                        <Text className="flowConfigMono">
                          {versionPreflightResult.flow_key} / {versionPreflightResult.version}
                        </Text>
                        <Text type="secondary" className="flowConfigMono">
                          记录：{versionPreflightResult.preflight_run_id || "-"} / {formatTime(versionPreflightResult.created_at || "")}
                        </Text>
                      </div>
                      <div className="flowPreflightCheckGrid">
                        {versionPreflightResult.checks.map((item) => (
                          <div className="flowPreflightCheckItem" key={item.key}>
                            <Space size={6} wrap>
                              <Tag color={item.status === "passed" ? "green" : "red"}>
                                {item.status === "passed" ? "通过" : "失败"}
                              </Tag>
                              <Text strong>{item.label}</Text>
                            </Space>
                            <Paragraph className="flowPreflightMessage">{item.message}</Paragraph>
                            {item.artifacts.length ? (
                              <div className="flowPreflightArtifactList">
                                <Text strong>发布验证</Text>
                                {item.artifacts.map((artifact) => (
                                  <div className="flowPreflightArtifactItem" key={`${artifact.script}:${artifact.command}`}>
                                    <Space size={6} wrap>
	                                      <Tag color={artifact.profile === "release" ? "blue" : "cyan"}>
	                                        {artifact.profile}
	                                      </Tag>
                                        {artifact.publish_evidence_required ? (
                                          <Tag color="volcano">关键证据</Tag>
                                        ) : null}
	                                      <Text className="flowPreflightArtifactLabel">{artifact.label}</Text>
	                                    </Space>
                                    <Text className="flowPreflightArtifactCommand">{artifact.command}</Text>
                                    {artifact.latest_evidence ? (
                                      <Text className="flowPreflightArtifactEvidence">
                                        证据：{artifact.latest_evidence.report_id} / {formatTime(artifact.latest_evidence.verified_at)} / 有效至 {formatTime(artifact.latest_evidence.expires_at)}
                                      </Text>
                                    ) : (
                                      <Text type="secondary" className="flowPreflightArtifactEvidence">
                                        证据：发布前需补最近通过记录
                                      </Text>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : null}
                            {item.repair_hints.length ? (
                              <div className="flowPreflightRepairList">
                                <Text strong>修复建议</Text>
                                {item.repair_hints.map((hint) => (
                                  <div className="flowPreflightRepairItem" key={`${hint.code}:${hint.field_path}:${hint.message}`}>
                                    <Space size={6} wrap>
                                      <Tag color={hint.severity === "blocking" ? "red" : "gold"}>
                                        {hint.severity === "blocking" ? "阻断" : hint.severity}
                                      </Tag>
                                      <Text className="flowPreflightRepairPath">{hint.field_path}</Text>
                                    </Space>
                                    <Paragraph className="flowPreflightRepairSuggestion">
                                      {hint.suggestion}
                                    </Paragraph>
                                  </div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </Card>
                  ) : null}
	                </Space>
	              ),
	            },
            {
              key: "steps",
              label: `步骤 ${flow.steps.length}`,
              children: (
                <Table
                  rowKey="id"
                  dataSource={flow.steps}
                  pagination={false}
                  scroll={{ x: 680 }}
                  locale={{ emptyText: <Empty description="暂无步骤" /> }}
                  columns={[
                    {
                      title: "步骤 ID",
                      dataIndex: "id",
                      width: 190,
                      render: (value) => <Text className="flowConfigMono">{String(value)}</Text>,
                    },
                    {
                      title: "步骤名称",
                      dataIndex: "name",
                      width: 240,
                      render: (value) => <Text className="flowConfigText">{String(value)}</Text>,
                    },
                    {
                      title: "输入",
                      dataIndex: "inputs",
                      render: (value: string[]) => (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => <Tag key={item}>{item}</Tag>)}
                        </Space>
                      ),
                    },
                    {
                      title: "可重试",
                      dataIndex: "retryable",
                      width: 90,
                      render: (value) => <Tag color={value ? "green" : "gold"}>{value ? "是" : "否"}</Tag>,
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一个流程配置" />
      )}
    </Modal>
  );
}

export function FlowConfigDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flowConfigDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "flowConfigMono" : "flowConfigText"}>{value}</Text>
    </div>
  );
}
