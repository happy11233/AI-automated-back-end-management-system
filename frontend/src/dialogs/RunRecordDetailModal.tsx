import { Button, Card, Col, Collapse, Empty, Modal, Row, Space, Table, Tabs, Tag } from "antd";
import type { RunRecordDetailResponse, RunRecordItem } from "../api";
import type {
  RunRecordMcpToolCall,
  RunRecordBusinessTimelineItem,
  RunRecordEvidenceItem,
} from "../workspace/types";
import {
  recordFromUnknown,
  compactDisplayText,
  formatTime,
  formatDuration,
  formatBytes,
  textFromUnknown,
  firstRecord,
  labelForBadge,
  shortTaskId,
  Paragraph,
  Text,
  Title,
  StatusTag,
  runStatusLabel,
  isPosition,
  positionLabel,
  RiskTag,
  sanitizeTechnicalValue,
} from "../workspace/shared";
import { RunRecordDetailItem } from "../components/RunRecordDetailItem";

export function mcpToolCallsFromRunRecord(detail: RunRecordDetailResponse): RunRecordMcpToolCall[] {
  const calls: RunRecordMcpToolCall[] = [];
  const seen = new Set<string>();

  detail.steps
    .filter((step) => step.resource_type === "mcp_tool")
    .forEach((step) => {
      const trace = recordFromUnknown(step.metadata);
      const call = normalizeMcpToolCall(trace, step);
      if (!seen.has(call.key)) {
        calls.push(call);
        seen.add(call.key);
      }
    });

  const runMetadata = recordFromUnknown(detail.run.metadata);
  const wechatSend = recordFromUnknown(runMetadata.wechat_send);
  const fallbackCalls = Array.isArray(wechatSend.mcp_tool_calls) ? wechatSend.mcp_tool_calls : [];
  fallbackCalls.forEach((item, index) => {
    const call = normalizeMcpToolCall(recordFromUnknown(item), null, index);
    if (!seen.has(call.key)) {
      calls.push(call);
      seen.add(call.key);
    }
  });

  return calls;
}

export function runRecordBusinessTimeline(detail: RunRecordDetailResponse): RunRecordBusinessTimelineItem[] {
  const steps = [...detail.steps].sort((left, right) => left.step_order - right.step_order);
  if (!steps.length) {
    return [
      {
        key: detail.run.id,
        title: runRecordBusinessActionLabel(detail.run),
        description: compactDisplayText(detail.run.error_message || detail.run.output_preview || detail.run.input_preview || "本次运行没有记录拆分步骤。", 140),
        status: detail.run.status,
        time: formatTime(detail.run.finished_at || detail.run.started_at),
        duration: formatDuration(detail.run.duration_ms),
        provider: detail.run.execution_source || "-",
        resource: runRecordResourceText(detail.run.resource_type, detail.run.resource_id),
      },
    ];
  }

  return steps.map((step) => ({
    key: step.id,
    title: runRecordStepBusinessLabel(step.step_name, step.resource_type),
    description: compactDisplayText(
      step.error_message || step.output_preview || step.input_preview || runRecordStepFallbackDescription(step),
      150,
    ),
    status: step.status,
    time: formatTime(step.finished_at || step.started_at),
    duration: formatDuration(step.duration_ms),
    provider: step.provider || "-",
    resource: runRecordResourceText(step.resource_type, step.resource_id),
  }));
}

export function runRecordBusinessActionLabel(run: RunRecordItem) {
  const byAppId: Record<string, string> = {
    finance_compound_report_generation: "生成财务经营报表",
    finance_salary_export: "导出工资表",
    finance_salary_wechat_send: "发送工资表文件",
    operations_listing_launch: "生成运营 Listing",
    customer_service_reply_draft: "生成客服回复草稿",
    finance_excel_settlement: "处理财务结算表",
    finance_reconciliation: "执行财务对账",
  };

  return byAppId[run.app_id] || run.app_name || "执行业务动作";
}

export function runRecordStepBusinessLabel(stepName: string, resourceType: string | null) {
  const normalized = stepName.toLowerCase();
  const labels: Record<string, string> = {
    finance_compound_intent_recognition: "识别财务资料需求",
    finance_compound_permission_check: "校验财务数据权限",
    finance_compound_merge_workbook: "汇总经营数据并生成报表",
    finance_compound_save_files: "保存生成文件",
    finance_compound_email_delivery: "处理邮件发送",
    finance_salary_export: "生成工资表",
    finance_salary_query: "查询工资单数据",
    finance_salary_save_file: "保存工资表文件",
    finance_salary_wechat_confirmation: "等待企业微信发送确认",
    operations_listing_launch: "生成运营 Listing 内容",
    customer_service_reply_draft: "生成客服回复草稿",
    permission_check: "校验岗位和资源权限",
    approval_check: "检查审批要求",
    audit_log: "写入审计记录",
  };

  if (labels[normalized]) {
    return labels[normalized];
  }
  if (normalized.includes("permission")) {
    return "校验岗位和资源权限";
  }
  if (normalized.includes("approval") || normalized.includes("confirm")) {
    return "等待审批或人工确认";
  }
  if (normalized.includes("erp") || resourceType === "erp") {
    return "查询 ERP 业务数据";
  }
  if (normalized.includes("mcp") || resourceType === "mcp_tool") {
    return "调用自动化工具";
  }
  if (normalized.includes("file") || normalized.includes("artifact")) {
    return "生成或保存文件";
  }

  return stepName.replace(/_/g, " ");
}

export function runRecordStepFallbackDescription(step: RunRecordDetailResponse["steps"][number]) {
  if (step.status === "failed" && step.error_message) {
    return step.error_message;
  }
  if (step.status === "blocked") {
    return "系统已根据岗位、资源或审批规则阻断本步骤。";
  }
  if (step.resource_type || step.resource_id) {
    return `处理对象：${runRecordResourceText(step.resource_type, step.resource_id)}`;
  }
  return "本步骤已记录到运行日志。";
}

export function runRecordResourceText(resourceType: string | null, resourceId: string | null) {
  const type = resourceType || "业务资源";
  const id = resourceId || "-";
  return `${type} / ${id}`;
}

export function runRecordArtifactEvidence(detail: RunRecordDetailResponse): RunRecordEvidenceItem[] {
  return detail.artifacts.map((artifact) => ({
    key: artifact.id,
    title: artifact.name || artifact.artifact_type || "生成产物",
    description: [
      artifact.mime_type ? `格式：${artifact.mime_type}` : "",
      artifact.size_bytes ? `大小：${formatBytes(artifact.size_bytes)}` : "",
      artifact.created_at ? `生成时间：${formatTime(artifact.created_at)}` : "",
    ].filter(Boolean).join(" / ") || "本次运行生成的业务文件或结果引用。",
    tag: artifactTypeBusinessLabel(artifact.artifact_type),
    mono: artifact.external_ref || undefined,
  }));
}

export function artifactTypeBusinessLabel(value: string) {
  const labels: Record<string, string> = {
    excel: "Excel 文件",
    xlsx: "Excel 文件",
    file: "生成文件",
    generated_file: "生成文件",
    platform_draft: "业务草稿",
    erp_reference: "ERP 引用",
  };
  return labels[value] || value || "产物";
}

export function runRecordErpReferenceEvidence(detail: RunRecordDetailResponse): RunRecordEvidenceItem[] {
  const metadata = recordFromUnknown(detail.run.metadata);
  const sources = [
    metadata.erp_references,
    metadata.erpReferences,
    metadata.erp_resources,
    metadata.erpResources,
    metadata.resource_references,
  ];
  const seen = new Set<string>();
  const references: RunRecordEvidenceItem[] = [];

  sources.flatMap(recordsFromUnknown).forEach((record, index) => {
    const resource = textFromUnknown(record.resource_label || record.resource || record.doctype || record.resource_type || "ERP 资源");
    const recordId = textFromUnknown(record.record_id || record.name || record.id || record.resource_id || "");
    const title = textFromUnknown(record.title || record.name || recordId || resource);
    const key = `${resource}:${recordId || index}`;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    references.push({
      key,
      title,
      description: recordId ? `${resource} / ${recordId}` : resource,
      tag: "ERP 数据",
      mono: recordId || undefined,
    });
  });

  detail.steps
    .filter((step) => step.resource_type && step.resource_type.toLowerCase().includes("erp"))
    .forEach((step) => {
      const key = `${step.resource_type}:${step.resource_id || step.id}`;
      if (seen.has(key)) {
        return;
      }
      seen.add(key);
      references.push({
        key,
        title: runRecordStepBusinessLabel(step.step_name, step.resource_type),
        description: runRecordResourceText(step.resource_type, step.resource_id),
        tag: "ERP 查询",
        mono: step.resource_id || undefined,
      });
    });

  return references.slice(0, 8);
}

export function runRecordApprovalEvidence(detail: RunRecordDetailResponse): RunRecordEvidenceItem[] {
  const metadata = recordFromUnknown(detail.run.metadata);
  const approval = firstRecord(
    metadata.approval_result,
    metadata.approval,
    metadata.approval_request,
    metadata.confirmation_card,
  );
  const approvalId = textFromUnknown(
    metadata.approval_id
      || approval?.approval_id
      || approval?.id
      || approval?.request_id
      || "",
  );
  const approvalStatus = textFromUnknown(
    metadata.approval_status
      || approval?.status
      || approval?.status_label
      || "",
  );
  const approvalSummary = textFromUnknown(
    metadata.approval_summary
      || approval?.summary_cn
      || approval?.message
      || approval?.description
      || "",
  );

  if (approvalId || approvalStatus || approvalSummary) {
    return [
      {
        key: approvalId || "approval",
        title: approvalStatus ? labelForBadge(approvalStatus) : "等待审批",
        description: approvalSummary || "该业务动作已进入审批或确认流程。",
        tag: "审批",
        mono: approvalId ? shortTaskId(approvalId) : undefined,
      },
    ];
  }

  if (detail.run.status === "blocked") {
    return [
      {
        key: "blocked",
        title: "权限或审批规则已拦截",
        description: detail.run.error_message || detail.run.output_preview || "系统已根据后台规则阻断本次执行。",
        tag: "拦截",
      },
    ];
  }

  return [
    {
      key: "no-approval",
      title: "无需人工审批",
      description: detail.run.status === "failed"
        ? (detail.run.error_message || "本次运行失败，但未记录人工审批要求。")
        : "本次运行未记录额外人工审批要求。",
      tag: "审批",
    },
  ];
}

export function recordsFromUnknown(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null && !Array.isArray(item));
}

export function normalizeMcpToolCall(
  trace: Record<string, unknown>,
  step: RunRecordDetailResponse["steps"][number] | null,
  fallbackIndex = 0,
): RunRecordMcpToolCall {
  const toolId = textFromUnknown(trace.tool_id || step?.resource_id || "mcp_tool");
  const status = textFromUnknown(trace.status || step?.status || "unknown");
  return {
    key: step?.id || `${toolId}-${fallbackIndex}`,
    toolId,
    label: textFromUnknown(trace.label || toolId),
    serverName: textFromUnknown(trace.server_name || "-"),
    toolName: textFromUnknown(trace.tool_name || "-"),
    riskLevel: textFromUnknown(trace.risk_level || "medium"),
    status,
    stepStatus: step?.status || mcpTraceStepStatus(status),
    message: textFromUnknown(trace.message || step?.output_preview || step?.error_message || "-"),
    durationMs: typeof trace.duration_ms === "number" ? trace.duration_ms : step?.duration_ms ?? null,
    backendPermissionChecked: trace.backend_permission_checked === true,
    permissionGate: textFromUnknown(trace.permission_gate || "Skill Executor / backend policy"),
    requiresApproval: trace.requires_approval === true,
    source: textFromUnknown(trace.source || "-"),
  };
}

export function mcpTraceStepStatus(value: string) {
  const status = value.toLowerCase();
  if (["failed", "error", "unhealthy", "invalid_config"].includes(status)) return "failed";
  if (["waiting_executor", "waiting_callback", "not_configured", "stub_ready"].includes(status)) return "blocked";
  return "succeeded";
}

export function RunRecordDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: RunRecordDetailResponse | null;
  onClose: () => void;
}) {
  const mcpToolCalls = detail ? mcpToolCallsFromRunRecord(detail) : [];
  const timeline = detail ? runRecordBusinessTimeline(detail) : [];
  const artifactEvidence = detail ? runRecordArtifactEvidence(detail) : [];
  const erpEvidence = detail ? runRecordErpReferenceEvidence(detail) : [];
  const approvalEvidence = detail ? runRecordApprovalEvidence(detail) : [];

  return (
    <Modal
      open={open}
      title={detail ? `运行记录 / ${detail.run.app_name}` : "运行记录"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={920}
    >
      {loading ? (
        <Empty description="正在加载运行记录详情" />
      ) : detail ? (
        <Tabs
          className="runRecordDetailTabs"
          items={[
            {
              key: "business",
              label: "业务视图",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="runRecordBusinessSummaryGrid">
                    <div className="runRecordBusinessSummaryItem">
                      <Text type="secondary">执行结果</Text>
                      <Space size={6} wrap>
                        <StatusTag value={detail.run.status} />
                        <Text strong>{runStatusLabel(detail.run.status)}</Text>
                      </Space>
                    </div>
                    <div className="runRecordBusinessSummaryItem">
                      <Text type="secondary">业务动作</Text>
                      <Text strong>{runRecordBusinessActionLabel(detail.run)}</Text>
                      <Text type="secondary">{detail.run.app_name}</Text>
                    </div>
                    <div className="runRecordBusinessSummaryItem">
                      <Text type="secondary">操作人/岗位</Text>
                      <Text strong>{detail.run.username || "-"}</Text>
                      <Text type="secondary">
                        {isPosition(detail.run.position) ? positionLabel(detail.run.position) : "管理员"}
                      </Text>
                    </div>
                    <div className="runRecordBusinessSummaryItem">
                      <Text type="secondary">耗时</Text>
                      <Title level={4}>{formatDuration(detail.run.duration_ms)}</Title>
                      <Text type="secondary">{formatTime(detail.run.started_at)}</Text>
                    </div>
                  </div>

                  <Card size="small" title="执行时间线" className="runRecordBusinessSectionCard">
                    <div className="runRecordBusinessTimeline">
                      {timeline.map((item) => (
                        <div className="runRecordBusinessTimelineItem" key={item.key}>
                          <span className={`runRecordBusinessTimelineDot ${item.status}`} />
                          <div className="runRecordBusinessTimelineBody">
                            <div className="runRecordBusinessTimelineHeader">
                              <Space size={8} wrap>
                                <Text strong>{item.title}</Text>
                                <StatusTag value={item.status} />
                              </Space>
                              <Text type="secondary">{item.time}</Text>
                            </div>
                            <Paragraph className="runRecordBusinessTimelineDescription">{item.description}</Paragraph>
                            <Space size={[6, 6]} wrap>
                              <Tag>{item.duration}</Tag>
                              <Tag>{item.provider}</Tag>
                              <Tag>{item.resource}</Tag>
                            </Space>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Row gutter={[12, 12]}>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="产物证据" className="runRecordBusinessSectionCard">
                        <RunRecordEvidenceList items={artifactEvidence} emptyText="本次运行没有生成文件或业务产物" />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="ERP / 业务引用" className="runRecordBusinessSectionCard">
                        <RunRecordEvidenceList items={erpEvidence} emptyText="本次运行没有记录 ERP 引用" />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="审批和安全" className="runRecordBusinessSectionCard">
                        <RunRecordEvidenceList items={approvalEvidence} emptyText="本次运行没有审批记录" />
                      </Card>
                    </Col>
                  </Row>
                </Space>
              ),
            },
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="runRecordDetailGrid">
                    <RunRecordDetailItem label="状态" value={<StatusTag value={detail.run.status} />} />
                    <RunRecordDetailItem label="类型" value={detail.run.run_type} mono />
                    <RunRecordDetailItem label="应用 ID" value={detail.run.app_id} mono />
                    <RunRecordDetailItem label="入口" value={detail.run.entrypoint} mono />
                    <RunRecordDetailItem label="流程 Key" value={detail.run.flow_key || "-"} mono />
                    <RunRecordDetailItem label="流程版本" value={detail.run.flow_version || "-"} mono />
                    <RunRecordDetailItem label="版本 ID" value={detail.run.flow_version_id || "-"} mono />
                    <RunRecordDetailItem label="发布指针" value={detail.run.publication_id || "-"} mono />
                    <RunRecordDetailItem label="执行来源" value={detail.run.execution_source || "-"} mono />
                    <RunRecordDetailItem label="用户" value={detail.run.username || "-"} />
                    <RunRecordDetailItem
                      label="岗位"
                      value={isPosition(detail.run.position) ? positionLabel(detail.run.position) : "管理员"}
                    />
                    <RunRecordDetailItem
                      label="资源"
                      value={`${detail.run.resource_type || "-"} / ${detail.run.resource_id || "-"}`}
                      mono
                    />
                    <RunRecordDetailItem label="耗时" value={formatDuration(detail.run.duration_ms)} />
                    <RunRecordDetailItem label="开始时间" value={formatTime(detail.run.started_at)} />
                    <RunRecordDetailItem label="结束时间" value={formatTime(detail.run.finished_at)} />
                  </div>
                </Space>
              ),
            },
            {
              key: "io",
              label: "输入输出",
              children: (
                <Row gutter={[12, 12]} className="runRecordDetailIoGrid">
                  <Col xs={24} md={12}>
                    <Card size="small" title="输入摘要" className="runRecordDetailSectionCard">
                      <Paragraph className="runRecordDetailPreview">{detail.run.input_preview || "-"}</Paragraph>
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card size="small" title="输出/错误摘要" className="runRecordDetailSectionCard">
                      <Paragraph className="runRecordDetailPreview">
                        {detail.run.error_message || detail.run.output_preview || "-"}
                      </Paragraph>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "mcp",
              label: `MCP 调用 ${mcpToolCalls.length}`,
              children: mcpToolCalls.length ? (
                <Table<RunRecordMcpToolCall>
                  rowKey="key"
                  dataSource={mcpToolCalls}
                  pagination={false}
                  scroll={{ x: 980 }}
                  columns={[
                    {
                      title: "工具",
                      dataIndex: "label",
                      width: 250,
                      render: (_, record) => (
                        <Space direction="vertical" size={2} className="runRecordCellStack">
                          <Text strong className="runRecordText">{record.label}</Text>
                          <Text type="secondary" className="runRecordMono">{record.toolId}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "Server / Tool",
                      width: 190,
                      render: (_, record) => (
                        <Space direction="vertical" size={2}>
                          <Text className="runRecordMono">{record.serverName}</Text>
                          <Text className="runRecordMono">{record.toolName}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "风险",
                      dataIndex: "riskLevel",
                      width: 110,
                      render: (value) => <RiskTag value={String(value)} />,
                    },
                    {
                      title: "状态",
                      dataIndex: "stepStatus",
                      width: 130,
                      render: (_, record) => (
                        <Space direction="vertical" size={2}>
                          <StatusTag value={record.stepStatus} />
                          <Text type="secondary">{record.status}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "权限闸门",
                      width: 190,
                      render: (_, record) => (
                        <Space direction="vertical" size={2}>
                          <Tag color={record.backendPermissionChecked ? "green" : "gold"}>
                            {record.backendPermissionChecked ? "后端已校验" : "需确认"}
                          </Tag>
                          {record.requiresApproval ? <Tag color="gold">审批/确认</Tag> : <Tag>无需审批</Tag>}
                        </Space>
                      ),
                    },
                    {
                      title: "说明",
                      dataIndex: "message",
                      render: (value, record) => (
                        <Space direction="vertical" size={2}>
                          <Text className="runRecordPreview">{String(value || "-")}</Text>
                          <Text type="secondary">来源：{record.source}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "耗时",
                      dataIndex: "durationMs",
                      width: 90,
                      render: (value) => formatDuration(value),
                    },
                  ]}
                />
              ) : (
                <Empty description="本次运行暂无 MCP 工具调用" />
              ),
            },
            {
              key: "steps",
              label: `执行步骤 ${detail.steps.length}`,
              children: (
                <Table
                  rowKey="id"
                  dataSource={detail.steps}
                  pagination={false}
                  scroll={{ x: 760 }}
                  locale={{ emptyText: <Empty description="暂无步骤" /> }}
                  columns={[
                    { title: "序号", dataIndex: "step_order", width: 70 },
                    {
                      title: "步骤",
                      dataIndex: "step_name",
                      width: 180,
                      render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
                    },
                    {
                      title: "状态",
                      dataIndex: "status",
                      width: 92,
                      render: (value) => <StatusTag value={String(value)} />,
                    },
                    { title: "Provider", dataIndex: "provider", width: 120 },
                    {
                      title: "资源",
                      dataIndex: "resource_id",
                      width: 160,
                      render: (value) => <Text className="runRecordMono">{value || "-"}</Text>,
                    },
                    {
                      title: "摘要",
                      dataIndex: "output_preview",
                      render: (value, record) => (
                        <Text className="runRecordPreview">
                          {record.error_message || value || record.input_preview || "-"}
                        </Text>
                      ),
                    },
                    {
                      title: "耗时",
                      dataIndex: "duration_ms",
                      width: 90,
                      render: (value) => formatDuration(value),
                    },
                  ]}
                />
              ),
            },
            {
              key: "artifacts",
              label: `产物引用 ${detail.artifacts.length}`,
              children: (
                <Table
                  rowKey="id"
                  dataSource={detail.artifacts}
                  pagination={false}
                  scroll={{ x: 680 }}
                  locale={{ emptyText: <Empty description="暂无产物引用" /> }}
                  columns={[
                    { title: "类型", dataIndex: "artifact_type", width: 130 },
                    {
                      title: "名称",
                      dataIndex: "name",
                      render: (value) => <Text className="runRecordText">{String(value)}</Text>,
                    },
                    {
                      title: "引用",
                      dataIndex: "external_ref",
                      width: 180,
                      render: (value) => <Text className="runRecordMono">{value || "-"}</Text>,
                    },
                    { title: "大小", dataIndex: "size_bytes", width: 100, render: (value) => formatBytes(value) },
                  ]}
                />
              ),
            },
            {
              key: "tech",
              label: "技术详情",
              children: (
                <Collapse
                  className="runRecordTechCollapse"
                  items={[
                    {
                      key: "run",
                      label: "运行 metadata",
                      children: (
                        <pre className="statePre">{JSON.stringify(sanitizeTechnicalValue(detail.run.metadata), null, 2)}</pre>
                      ),
                    },
                    {
                      key: "steps",
                      label: "步骤 metadata",
                      children: (
                        <pre className="statePre">
                          {JSON.stringify(sanitizeTechnicalValue(detail.steps.map((step) => ({
                            id: step.id,
                            step_name: step.step_name,
                            status: step.status,
                            metadata: step.metadata,
                          }))), null, 2)}
                        </pre>
                      ),
                    },
                    {
                      key: "artifacts",
                      label: "产物 metadata",
                      children: (
                        <pre className="statePre">
                          {JSON.stringify(sanitizeTechnicalValue(detail.artifacts.map((artifact) => ({
                            id: artifact.id,
                            artifact_type: artifact.artifact_type,
                            name: artifact.name,
                            metadata: artifact.metadata,
                          }))), null, 2)}
                        </pre>
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一条运行记录" />
      )}
    </Modal>
  );
}

export function RunRecordEvidenceList({
  items,
  emptyText,
}: {
  items: RunRecordEvidenceItem[];
  emptyText: string;
}) {
  if (!items.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />;
  }

  return (
    <div className="runRecordEvidenceList">
      {items.map((item) => (
        <div className="runRecordEvidenceItem" key={item.key}>
          <div className="runRecordEvidenceHeader">
            <Text strong className="runRecordText">{item.title}</Text>
            {item.tag ? <Tag>{item.tag}</Tag> : null}
          </div>
          <Text type="secondary" className="runRecordPreview">{item.description}</Text>
          {item.mono ? <Text className="runRecordMono">{item.mono}</Text> : null}
        </div>
      ))}
    </div>
  );
}
