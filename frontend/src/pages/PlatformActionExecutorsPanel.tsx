import React, { useState } from "react";
import { CheckCircleOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
} from "antd";
import { ProCard } from "@ant-design/pro-components";
import type {
  PlatformActionExecutorItem,
  PlatformActionExecutorOption,
  PlatformActionExecutorsResponse,
} from "../api";
import { type PlatformActionExecutorFormState } from "../workspace/types";
import { Paragraph, Text, Title, formatTime } from "../workspace/shared";
import { ConnectorStatusTag } from "../components/ConnectorStatusTag";

export function PlatformActionExecutorsPanel({
  executors,
  summary,
  actionOptions,
  typeOptions,
  form,
  setForm,
  loading,
  saving,
  checkingId,
  deletingId,
  refresh,
  save,
  edit,
  reset,
  checkHealth,
  remove,
}: {
  executors: PlatformActionExecutorItem[];
  summary: PlatformActionExecutorsResponse["summary"] | null;
  actionOptions: PlatformActionExecutorOption[];
  typeOptions: PlatformActionExecutorOption[];
  form: PlatformActionExecutorFormState;
  setForm: React.Dispatch<React.SetStateAction<PlatformActionExecutorFormState>>;
  loading: boolean;
  saving: boolean;
  checkingId: string;
  deletingId: string;
  refresh: () => void;
  save: () => void;
  edit: (item: PlatformActionExecutorItem) => void;
  reset: () => void;
  checkHealth: (item: PlatformActionExecutorItem) => void;
  remove: (item: PlatformActionExecutorItem) => void;
}) {
  const [editorOpen, setEditorOpen] = useState(false);
  return (
    <Space direction="vertical" className="pageStack">
      <Row gutter={[12, 12]} className="platformExecutorMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-blue">
            <Text type="secondary">执行器</Text>
            <Title level={3}>{summary?.total ?? executors.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-purple">
            <Text type="secondary">启用</Text>
            <Title level={3}>{summary?.enabled ?? executors.filter((item) => item.enabled).length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-amber">
            <Text type="secondary">已配置</Text>
            <Title level={3}>
              {summary?.configured ?? executors.filter((item) => item.configured).length}
            </Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard metric-green">
            <Text type="secondary">健康</Text>
            <Title level={3}>
              {summary?.healthy ?? executors.filter((item) => item.health_status === "healthy").length}
            </Title>
          </Card>
        </Col>
      </Row>
      <ProCard
        title="动作执行器路由"
        bordered
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                reset();
                setEditorOpen(true);
              }}
            >
              新增执行器
            </Button>
          </Space>
        }
      >
        <Table<PlatformActionExecutorItem>
          rowKey="id"
          loading={loading}
          dataSource={executors}
          className="platformExecutorTable"
          scroll={{ x: 1180 }}
          locale={{ emptyText: <Empty description="暂无外部执行器配置" /> }}
          columns={[
            {
              title: "执行器",
              dataIndex: "name",
              width: 240,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Space size={6}>
                    <Text strong className="runRecordText">
                      {record.name}
                    </Text>
                    {record.is_environment_fallback ? <Tag>环境变量</Tag> : null}
                  </Space>
                  <Text type="secondary" className="runRecordMono">
                    {record.id}
                  </Text>
                </Space>
              ),
            },
            {
              title: "类型",
              dataIndex: "executor_type_label",
              width: 150,
              render: (_, record) => (
                <Tag color="blue">
                  {record.executor_type_label || platformActionExecutorTypeLabel(record.executor_type)}
                </Tag>
              ),
            },
            {
              title: "动作",
              dataIndex: "action_type_labels",
              width: 260,
              render: (value: string[]) => (
                <Space size={[4, 4]} wrap>
                  {(value || []).map((item) => (
                    <Tag key={item} color="purple">
                      {item}
                    </Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: "Webhook",
              dataIndex: "webhook_url_preview",
              width: 240,
              render: (value) => <Text className="runRecordMono">{value || "-"}</Text>,
            },
            {
              title: "状态",
              dataIndex: "health_status",
              width: 118,
              render: (_, record) => (
                <Space direction="vertical" size={2}>
                  <ConnectorStatusTag status={record.enabled ? record.health_status : "disabled"} />
                  <Text type="secondary">{record.enabled ? "启用" : "已暂停"}</Text>
                </Space>
              ),
            },
            {
              title: "密钥",
              dataIndex: "api_key_configured",
              width: 96,
              render: (value) => <Tag color={value ? "green" : "default"}>{value ? "已配置" : "未配置"}</Tag>,
            },
            {
              title: "最近检查",
              dataIndex: "last_checked_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 220,
              render: (_, record) => (
                <Space size={6} wrap className="platformExecutorActionCell">
                  <Button size="small" onClick={() => checkHealth(record)} loading={checkingId === record.id}>
                    检查
                  </Button>
                  <Button
                    size="small"
                    type="link"
                    disabled={record.is_environment_fallback}
                    onClick={() => {
                      edit(record);
                      setEditorOpen(true);
                    }}
                  >
                    编辑
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={record.is_environment_fallback}
                    loading={deletingId === record.id}
                    onClick={() => remove(record)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
          expandable={{
            expandedRowRender: (record) => (
              <div className="platformExecutorExpanded">
                <Text type="secondary">健康信息</Text>
                <Paragraph>{record.health_message || "尚未执行健康检查。"}</Paragraph>
              </div>
            ),
          }}
        />
      </ProCard>
      <Drawer
        title={form.id ? "编辑外部执行器" : "新增外部执行器"}
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        width="min(800px,100vw)"
      >
        <div className="workspaceLayout workspaceExecutorDrawer">
          <ProCard
            title={form.id ? "编辑外部执行器" : "新增外部执行器"}
            subTitle="按平台动作路由到 Amazon SP-API、影刀、n8n、客服系统或通用 Webhook"
            bordered
            extra={
              <Button size="small" icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
                刷新
              </Button>
            }
          >
            <div className="platformExecutorFormGrid">
              <div className="platformExecutorField">
                <Text type="secondary">名称</Text>
                <Input
                  value={form.name}
                  placeholder="例如：Amazon Listing 发布执行器"
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                />
              </div>
              <div className="platformExecutorField">
                <Text type="secondary">类型</Text>
                <Select
                  value={form.executorType}
                  options={typeOptions.length ? typeOptions : [{ value: "webhook", label: "通用 Webhook" }]}
                  onChange={(value) => setForm((current) => ({ ...current, executorType: value }))}
                />
              </div>
              <div className="platformExecutorField platformExecutorWideField">
                <Text type="secondary">动作路由</Text>
                <Select
                  mode="multiple"
                  value={form.actionTypes}
                  placeholder="选择该执行器负责的动作"
                  options={actionOptions}
                  maxTagCount="responsive"
                  onChange={(value) => setForm((current) => ({ ...current, actionTypes: value }))}
                />
              </div>
              <div className="platformExecutorField platformExecutorWideField">
                <Text type="secondary">Webhook URL</Text>
                <Input
                  value={form.webhookUrl}
                  placeholder={form.id ? "留空表示不修改" : "https://example.com/platform-action/execute"}
                  onChange={(event) => setForm((current) => ({ ...current, webhookUrl: event.target.value }))}
                />
              </div>
              <div className="platformExecutorField">
                <Text type="secondary">API Key</Text>
                <Input.Password
                  value={form.apiKey}
                  placeholder={form.id ? "留空表示不修改" : "可选"}
                  onChange={(event) => setForm((current) => ({ ...current, apiKey: event.target.value }))}
                />
              </div>
              <div className="platformExecutorField">
                <Text type="secondary">超时秒数</Text>
                <InputNumber
                  min={1}
                  max={120}
                  value={form.timeoutSeconds}
                  onChange={(value) =>
                    setForm((current) => ({ ...current, timeoutSeconds: Number(value || 12) }))
                  }
                />
              </div>
              <div className="platformExecutorSwitchRow">
                <Switch
                  checked={form.enabled}
                  onChange={(checked) => setForm((current) => ({ ...current, enabled: checked }))}
                />
                <Text>{form.enabled ? "启用执行器" : "暂停执行器"}</Text>
              </div>
              <div className="platformExecutorButtonRow">
                <Button onClick={reset}>清空</Button>
                <Button type="primary" icon={<CheckCircleOutlined />} onClick={save} loading={saving}>
                  {form.id ? "保存修改" : "创建执行器"}
                </Button>
              </div>
            </div>
          </ProCard>
        </div>
      </Drawer>
    </Space>
  );
}

export function platformActionExecutorTypeLabel(value: string) {
  const labels: Record<string, string> = {
    webhook: "通用 Webhook",
    amazon_sp_api: "Amazon SP-API",
    n8n: "n8n 工作流",
    yingdao: "影刀 RPA",
    customer_service_system: "客服系统",
    erp_writeback: "ERP 写回",
  };

  return labels[value] ?? value;
}
