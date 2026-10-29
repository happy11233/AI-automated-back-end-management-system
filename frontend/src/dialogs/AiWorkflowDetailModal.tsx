import React from "react";
import { Button, Card, Col, Empty, Modal, Row, Space, Table, Tabs, Tag } from "antd";
import type { AiWorkflowDetailResponse } from "../api";
import { Paragraph, Text, Title } from "../workspace/shared";

export function AiWorkflowDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: AiWorkflowDetailResponse | null;
  onClose: () => void;
}) {
  const workflow = detail?.item || null;

  return (
    <Modal
      open={open}
      title={workflow ? `AI 工作流 / ${workflow.name}` : "AI 工作流"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width="min(980px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载 AI 工作流详情" />
      ) : workflow ? (
        <Tabs
          className="aiWorkflowDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <div className="aiWorkflowDetailGrid">
                  <AiWorkflowDetailItem label="工作流 ID" value={workflow.id} mono />
                  <AiWorkflowDetailItem label="版本" value={workflow.version} mono />
                  <AiWorkflowDetailItem label="岗位" value={workflow.position_label} />
                  <AiWorkflowDetailItem label="类别" value={workflow.category} />
                  <AiWorkflowDetailItem label="触发方式" value={workflowTriggerLabel(workflow.trigger_type)} />
                  <AiWorkflowDetailItem label="执行模式" value={executionModeLabel(workflow.execution_mode)} />
                  <AiWorkflowDetailItem label="审批" value={workflow.requires_approval ? "需要审批" : "无需审批"} />
                  <AiWorkflowDetailItem label="预计节省" value={`${workflow.saved_minutes} 分钟`} />
                </div>
              ),
            },
            {
              key: "scenario",
              label: "场景",
              children: (
                <Row gutter={[12, 12]} className="aiWorkflowDetailTabGrid">
                  <Col xs={24} md={12}>
                    <Card title="业务场景" size="small" className="aiWorkflowDetailSectionCard">
                      <Paragraph className="aiWorkflowDetailPreview">{workflow.scenario}</Paragraph>
                      <Paragraph className="aiWorkflowDetailPreview compact">{workflow.business_value}</Paragraph>
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="输出与审批" size="small" className="aiWorkflowDetailSectionCard">
                      <Paragraph className="aiWorkflowDetailPreview">{workflow.output_contract}</Paragraph>
                      <Paragraph className="aiWorkflowDetailPreview compact">{workflow.approval_policy}</Paragraph>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "stages",
              label: `步骤 ${workflow.stages.length}`,
              children: (
                <Table
                  rowKey="key"
                  size="small"
                  dataSource={workflow.stages}
                  pagination={false}
                  scroll={{ x: 760 }}
                  columns={[
                    { title: "阶段", dataIndex: "label", width: 110, render: (value) => <Text strong>{String(value)}</Text> },
                    {
                      title: "自动化",
                      dataIndex: "automated",
                      width: 96,
                      render: (value) => <Tag color={value ? "green" : "default"}>{value ? "自动" : "人工"}</Tag>,
                    },
                    {
                      title: "说明",
                      dataIndex: "description",
                      render: (value) => <Text className="aiWorkflowText">{String(value)}</Text>,
                    },
                  ]}
                />
              ),
            },
            {
              key: "resources",
              label: "资源写回",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <Row gutter={[12, 12]} className="aiWorkflowDetailTabGrid">
                    <Col xs={24} md={8}>
                      <Card title="允许工具" size="small" className="aiWorkflowDetailSectionCard">
                        <Space size={[6, 6]} wrap className="aiWorkflowTagBlock">
                          {workflow.tools.map((item) => (
                            <Tag color="blue" key={item}>{item}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="ERP 资源" size="small" className="aiWorkflowDetailSectionCard">
                        <Space size={[6, 6]} wrap className="aiWorkflowTagBlock">
                          {workflow.erp_resources.map((item) => (
                            <Tag color="geekblue" key={item}>{item}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="入口" size="small" className="aiWorkflowDetailSectionCard">
                        <Paragraph className="aiWorkflowDetailPreview compact">
                          {workflow.entry_label} / {workflow.entry_view}
                        </Paragraph>
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={[12, 12]} className="aiWorkflowDetailTabGrid">
                    <Col xs={24} md={12}>
                      <Card title="写回目标" size="small" className="aiWorkflowDetailSectionCard">
                        <Paragraph className="aiWorkflowDetailPreview compact">{workflow.writeback_target}</Paragraph>
                      </Card>
                    </Col>
                    <Col xs={24} md={12}>
                      <Card title="通知目标" size="small" className="aiWorkflowDetailSectionCard">
                        <Paragraph className="aiWorkflowDetailPreview compact">{workflow.notification_target}</Paragraph>
                      </Card>
                    </Col>
                  </Row>
                </Space>
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一个 AI 工作流" />
      )}
    </Modal>
  );
}

export function AiWorkflowDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="aiWorkflowDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "aiWorkflowMono" : "aiWorkflowText"}>{value}</Text>
    </div>
  );
}

export function executionModeLabel(value: string) {
  const labels: Record<string, string> = {
    llm_generate: "LLM 生成",
    erp_then_llm: "ERP + LLM",
    external_existing_endpoint: "专用真实入口",
  };

  return labels[value] ?? value;
}

export function workflowTriggerLabel(value: string) {
  const labels: Record<string, string> = {
    manual_form: "人工表单触发",
    manual_file_upload: "人工文件上传",
    external_message: "外部消息触发",
  };

  return labels[value] ?? value;
}
