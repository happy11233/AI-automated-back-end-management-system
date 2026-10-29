import React, { useEffect, useState } from "react";
import {
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  SendOutlined,
  SearchOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import {
  Avatar,
  Button,
  Card,
  Checkbox,
  Col,
  Collapse,
  Empty,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  message,
  type TableColumnsType,
} from "antd";
import { WorkspaceTabs } from "../components/WorkspaceCharts";
import {
  getEnterpriseWechatManagement,
  listEnterpriseWechatContacts,
  syncEnterpriseWechatContacts,
  testEnterpriseWechatSend,
  updateEnterpriseWechatSettings,
  upsertEnterpriseWechatGroup,
  type ConnectorConfigField,
  type ConnectorDetailResponse,
  type EnterpriseWechatContactItem,
  type EnterpriseWechatManagementResponse,
} from "../api";
import { ConnectorStatusTag } from "../components/ConnectorStatusTag";
import { formatTime, Paragraph, Text, Title, StatusTag } from "../workspace/shared";
import { type EnterpriseWechatFormState } from "../workspace/types";

export function ConnectorDetailModal({
  open,
  loading,
  detail,
  token,
  refreshConnectors,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: ConnectorDetailResponse | null;
  token: string;
  refreshConnectors: () => void;
  onClose: () => void;
}) {
  const connector = detail?.item || null;
  const isWechatConnector = connector?.id === "wechat_work";
  const [wechatManagement, setWechatManagement] = useState<EnterpriseWechatManagementResponse | null>(null);
  const [wechatForm, setWechatForm] = useState({
    corpId: "",
    agentId: "",
    secret: "",
    clearSecret: false,
    realSendEnabled: false,
    timeoutSeconds: 12,
  });
  const [wechatContactQuery, setWechatContactQuery] = useState("");
  const [wechatContactType, setWechatContactType] = useState("all");
  const [wechatGroupName, setWechatGroupName] = useState("");
  const [wechatGroupChatId, setWechatGroupChatId] = useState("");
  const [wechatSelectedContactId, setWechatSelectedContactId] = useState("");
  const [isWechatManagementLoading, setIsWechatManagementLoading] = useState(false);
  const [isWechatSaving, setIsWechatSaving] = useState(false);
  const [isWechatSyncing, setIsWechatSyncing] = useState(false);
  const [isWechatGroupSaving, setIsWechatGroupSaving] = useState(false);
  const [isWechatTesting, setIsWechatTesting] = useState(false);

  useEffect(() => {
    if (!open || !isWechatConnector || !token) {
      return;
    }
    void loadWechatManagement();
  }, [open, isWechatConnector, token]);

  async function loadWechatManagement() {
    if (!token) {
      return;
    }
    setIsWechatManagementLoading(true);
    try {
      const result = await getEnterpriseWechatManagement(token);
      setWechatManagement(result);
      setWechatForm((current) => ({
        ...current,
        secret: "",
        clearSecret: false,
        realSendEnabled: result.settings.real_send_enabled,
        timeoutSeconds: result.settings.timeout_seconds || 12,
      }));
      setWechatSelectedContactId((current) => current || result.contacts.items[0]?.id || "");
    } catch (error) {
      const text = error instanceof Error ? error.message : "企业微信管理信息加载失败";
      message.error(text);
    } finally {
      setIsWechatManagementLoading(false);
    }
  }

  async function saveWechatSettings() {
    if (!token) {
      return;
    }
    setIsWechatSaving(true);
    try {
      const result = await updateEnterpriseWechatSettings(token, {
        corp_id: wechatForm.corpId.trim() || null,
        agent_id: wechatForm.agentId.trim() || null,
        secret: wechatForm.secret.trim() || null,
        clear_secret: wechatForm.clearSecret,
        real_send_enabled: wechatForm.realSendEnabled,
        timeout_seconds: wechatForm.timeoutSeconds,
      });
      setWechatManagement((current) => current ? { ...current, settings: result.settings } : current);
      setWechatForm((current) => ({ ...current, corpId: "", agentId: "", secret: "", clearSecret: false }));
      refreshConnectors();
      message.success("企业微信配置已保存");
      void loadWechatManagement();
    } catch (error) {
      const text = error instanceof Error ? error.message : "企业微信配置保存失败";
      message.error(text);
    } finally {
      setIsWechatSaving(false);
    }
  }

  async function syncWechatContacts() {
    if (!token) {
      return;
    }
    setIsWechatSyncing(true);
    try {
      const result = await syncEnterpriseWechatContacts(token);
      message.success(String(result.message || "企业微信通讯录同步完成"));
      await loadWechatManagement();
      refreshConnectors();
    } catch (error) {
      const text = error instanceof Error ? error.message : "企业微信通讯录同步失败";
      message.error(text);
    } finally {
      setIsWechatSyncing(false);
    }
  }

  async function searchWechatContacts(nextQuery = wechatContactQuery, nextType = wechatContactType) {
    if (!token) {
      return;
    }
    setIsWechatManagementLoading(true);
    try {
      const result = await listEnterpriseWechatContacts(token, {
        query: nextQuery.trim(),
        object_type: nextType,
      });
      setWechatManagement((current) => current ? {
        ...current,
        contacts: result,
      } : current);
      setWechatSelectedContactId((current) => {
        if (current && result.items.some((item) => item.id === current)) {
          return current;
        }
        return result.items[0]?.id || "";
      });
    } catch (error) {
      const text = error instanceof Error ? error.message : "企业微信通讯录搜索失败";
      message.error(text);
    } finally {
      setIsWechatManagementLoading(false);
    }
  }

  async function saveWechatGroup() {
    if (!token) {
      return;
    }
    if (!wechatGroupName.trim() || !wechatGroupChatId.trim()) {
      message.warning("请填写群聊名称和 chat_id");
      return;
    }
    setIsWechatGroupSaving(true);
    try {
      await upsertEnterpriseWechatGroup(token, {
        name: wechatGroupName.trim(),
        chat_id: wechatGroupChatId.trim(),
      });
      setWechatGroupName("");
      setWechatGroupChatId("");
      message.success("群聊已保存");
      await searchWechatContacts("", "all");
      refreshConnectors();
    } catch (error) {
      const text = error instanceof Error ? error.message : "群聊保存失败";
      message.error(text);
    } finally {
      setIsWechatGroupSaving(false);
    }
  }

  async function runWechatTestSend() {
    if (!token || !wechatSelectedContactId) {
      message.warning("请先选择一个接收对象");
      return;
    }
    setIsWechatTesting(true);
    try {
      const result = await testEnterpriseWechatSend(token, { recipient_id: wechatSelectedContactId });
      message.success(String(result.message || "企业微信测试发送流程已完成"));
      await loadWechatManagement();
      refreshConnectors();
    } catch (error) {
      const text = error instanceof Error ? error.message : "企业微信测试发送失败";
      message.error(text);
    } finally {
      setIsWechatTesting(false);
    }
  }

  return (
    <Modal
      open={open}
      title={connector ? `连接器 / ${connector.label}` : "连接器"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width="min(980px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载连接器详情" />
      ) : connector ? (
        <Tabs
          className="connectorDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <div className="connectorDetailGrid">
                  <ConnectorDetailItem label="连接器 ID" value={connector.id} mono />
                  <ConnectorDetailItem label="类别" value={connector.category} />
                  <ConnectorDetailItem label="状态" value={<ConnectorStatusTag status={connector.status} />} />
                  <ConnectorDetailItem label="健康状态" value={connector.health_status} mono />
                  <ConnectorDetailItem label="鉴权方式" value={connector.auth_type} />
                  <ConnectorDetailItem label="管理范围" value={connector.managed_by} />
                  <ConnectorDetailItem label="真实健康检查" value={connector.supports_real_health_check ? "已接入" : "未接入"} />
                  <ConnectorDetailItem label="最后检查" value={formatTime(connector.last_checked_at)} mono />
                </div>
              ),
            },
            {
              key: "health",
              label: "健康",
              children: (
                <Card title="健康信息" size="small" className="connectorDetailSectionCard">
                  <Paragraph className="connectorDetailPreview">{connector.health_message}</Paragraph>
                  <Space size={[6, 6]} wrap className="connectorTagBlock">
                    {connector.capabilities.map((item) => (
                      <Tag color="blue" key={item}>{item}</Tag>
                    ))}
                    {connector.position_scope_labels.map((item) => (
                      <Tag color="purple" key={item}>{item}</Tag>
                    ))}
                  </Space>
                </Card>
              ),
            },
            {
              key: "config",
              label: "配置",
              children: (
                <Row gutter={[12, 12]} className="connectorDetailTabGrid">
                  <Col xs={24} md={12}>
                    <Card title="配置项" size="small" className="connectorDetailSectionCard">
                      <ConnectorConfigTable fields={connector.config_fields} />
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="下一步" size="small" className="connectorDetailSectionCard">
                      <div className="connectorRuleList">
                        {connector.next_steps.map((item) => (
                          <div className="connectorRuleItem" key={item}>{item}</div>
                        ))}
                      </div>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "resources",
              label: "资源映射",
              children: (
                <Table
                  rowKey={(record) => `${record.resource}-${record.provider_resource}`}
                  dataSource={connector.resources}
                  pagination={false}
                  scroll={{ x: 820 }}
                  locale={{ emptyText: <Empty description="暂无资源映射" /> }}
                  columns={[
                    {
                      title: "资源",
                      dataIndex: "label",
                      width: 170,
                      render: (value, record) => (
                        <Space direction="vertical" size={2} className="connectorCellStack">
                          <Text strong className="connectorText">{String(value)}</Text>
                          <Text className="connectorMono">{record.resource}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "外部对象",
                      dataIndex: "provider_resource",
                      width: 190,
                      render: (value) => <Text className="connectorMono">{value || "-"}</Text>,
                    },
                    {
                      title: "岗位范围",
                      dataIndex: "position_scope_labels",
                      width: 190,
                      render: (value: string[]) => (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => <Tag color="purple" key={item}>{item}</Tag>)}
                        </Space>
                      ),
                    },
                    {
                      title: "字段",
                      dataIndex: "fields",
                      render: (value: string[]) => value.length ? (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => <Tag key={item}>{item}</Tag>)}
                        </Space>
                      ) : (
                        <Text type="secondary">-</Text>
                      ),
                    },
                  ]}
                />
              ),
            },
            ...(isWechatConnector ? [{
              key: "wechat_work_management",
              label: "企业微信管理",
              children: (
                <EnterpriseWechatManagementPanel
                  management={wechatManagement}
                  loading={isWechatManagementLoading}
                  form={wechatForm}
                  setForm={setWechatForm}
                  contactQuery={wechatContactQuery}
                  setContactQuery={setWechatContactQuery}
                  contactType={wechatContactType}
                  setContactType={setWechatContactType}
                  selectedContactId={wechatSelectedContactId}
                  setSelectedContactId={setWechatSelectedContactId}
                  groupName={wechatGroupName}
                  setGroupName={setWechatGroupName}
                  groupChatId={wechatGroupChatId}
                  setGroupChatId={setWechatGroupChatId}
                  saving={isWechatSaving}
                  syncing={isWechatSyncing}
                  groupSaving={isWechatGroupSaving}
                  testing={isWechatTesting}
                  refresh={loadWechatManagement}
                  saveSettings={saveWechatSettings}
                  syncContacts={syncWechatContacts}
                  searchContacts={searchWechatContacts}
                  saveGroup={saveWechatGroup}
                  testSend={runWechatTestSend}
                />
              ),
            }] : []),
          ]}
        />
      ) : (
        <Empty description="请选择一个连接器" />
      )}
    </Modal>
  );
}

export function EnterpriseWechatManagementPanel({
  management,
  loading,
  form,
  setForm,
  contactQuery,
  setContactQuery,
  contactType,
  setContactType,
  selectedContactId,
  setSelectedContactId,
  groupName,
  setGroupName,
  groupChatId,
  setGroupChatId,
  saving,
  syncing,
  groupSaving,
  testing,
  refresh,
  saveSettings,
  syncContacts,
  searchContacts,
  saveGroup,
  testSend,
}: {
  management: EnterpriseWechatManagementResponse | null;
  loading: boolean;
  form: EnterpriseWechatFormState;
  setForm: React.Dispatch<React.SetStateAction<EnterpriseWechatFormState>>;
  contactQuery: string;
  setContactQuery: (value: string) => void;
  contactType: string;
  setContactType: (value: string) => void;
  selectedContactId: string;
  setSelectedContactId: (value: string) => void;
  groupName: string;
  setGroupName: (value: string) => void;
  groupChatId: string;
  setGroupChatId: (value: string) => void;
  saving: boolean;
  syncing: boolean;
  groupSaving: boolean;
  testing: boolean;
  refresh: () => Promise<void>;
  saveSettings: () => Promise<void>;
  syncContacts: () => Promise<void>;
  searchContacts: (query?: string, objectType?: string) => Promise<void>;
  saveGroup: () => Promise<void>;
  testSend: () => Promise<void>;
}) {
  const settings = management?.settings || null;
  const contacts = management?.contacts || null;
  const diagnostics = management?.diagnostics || null;
  const fieldPreview = (name: string) =>
    settings?.config_fields.find((item) => item.name === name)?.value_preview || "未配置";
  const missingFields = settings?.missing_fields || [];
  const contactColumns: TableColumnsType<EnterpriseWechatContactItem> = [
    {
      title: "接收对象",
      dataIndex: "name",
      width: 220,
      render: (_, record) => (
        <Space size={8}>
          <Avatar size={28} src={record.avatar_url || undefined}>
            {record.avatar_text || record.name.slice(0, 1)}
          </Avatar>
          <Space direction="vertical" size={0} className="connectorCellStack">
            <Text strong className="connectorText">
              {record.name}
            </Text>
            <Text type="secondary" className="connectorMono">
              {record.wechat_userid || record.chat_id || record.department_id || "-"}
            </Text>
          </Space>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "object_type_label",
      width: 96,
      render: (value) => <Tag>{String(value || "成员")}</Tag>,
    },
    {
      title: "部门",
      dataIndex: "department",
      width: 160,
      render: (value) => <Text>{value || "-"}</Text>,
    },
    {
      title: "手机号后四位",
      dataIndex: "phone_last4",
      width: 120,
      render: (value) => <Text className="connectorMono">{value || "-"}</Text>,
    },
    {
      title: "来源",
      dataIndex: "source",
      render: (value) => <Text type="secondary">{String(value || "-")}</Text>,
    },
  ];

  return (
    <Space direction="vertical" className="pageStack enterpriseWechatManager">
      <Row gutter={[12, 12]}>
        <Col xs={12} lg={6}>
          <div className="enterpriseWechatMetric">
            <Text type="secondary">配置状态</Text>
            <Text strong>{settings?.configured ? "已配置" : "未配置"}</Text>
          </div>
        </Col>
        <Col xs={12} lg={6}>
          <div className="enterpriseWechatMetric">
            <Text type="secondary">真实发送</Text>
            <Text strong>{settings?.real_send_enabled ? "已启用" : "未启用"}</Text>
          </div>
        </Col>
        <Col xs={12} lg={6}>
          <div className="enterpriseWechatMetric">
            <Text type="secondary">缓存对象</Text>
            <Text strong>{contacts?.summary.total ?? 0}</Text>
          </div>
        </Col>
        <Col xs={12} lg={6}>
          <div className="enterpriseWechatMetric">
            <Text type="secondary">最近同步</Text>
            <Text strong>{formatTime(settings?.last_sync_at || "")}</Text>
          </div>
        </Col>
      </Row>
      <WorkspaceTabs
        storageKey="wechat_tab"
        items={[
          {
            key: "config",
            label: "配置与引导",
            children: (
              <Space direction="vertical" className="pageStack">
                <div className="enterpriseWechatSection">
                  <div className="enterpriseWechatSectionHeader">
                    <Space direction="vertical" size={2}>
                      <Text strong>后台配置</Text>
                      <Text type="secondary">Secret 保存后只展示脱敏内容；空输入会保留原配置。</Text>
                    </Space>
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={loading}
                      onClick={() => void refresh()}
                    >
                      刷新
                    </Button>
                  </div>
                  <div className="enterpriseWechatConfigGrid">
                    <div className="enterpriseWechatField">
                      <Text type="secondary">Corp ID</Text>
                      <Input
                        value={form.corpId}
                        placeholder={`当前：${fieldPreview("corp_id")}`}
                        onChange={(event) =>
                          setForm((current) => ({ ...current, corpId: event.target.value }))
                        }
                      />
                    </div>
                    <div className="enterpriseWechatField">
                      <Text type="secondary">Agent ID</Text>
                      <Input
                        value={form.agentId}
                        placeholder={`当前：${fieldPreview("agent_id")}`}
                        onChange={(event) =>
                          setForm((current) => ({ ...current, agentId: event.target.value }))
                        }
                      />
                    </div>
                    <div className="enterpriseWechatField">
                      <Text type="secondary">Secret</Text>
                      <Input.Password
                        value={form.secret}
                        placeholder={`当前：${fieldPreview("secret")}`}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            secret: event.target.value,
                            clearSecret: false,
                          }))
                        }
                      />
                    </div>
                    <div className="enterpriseWechatField">
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
                    <div className="enterpriseWechatSwitchRow">
                      <Switch
                        checked={form.realSendEnabled}
                        onChange={(checked) =>
                          setForm((current) => ({ ...current, realSendEnabled: checked }))
                        }
                      />
                      <Text>{form.realSendEnabled ? "允许真实发送" : "仅生成文件，等待管理员配置"}</Text>
                    </div>
                    <div className="enterpriseWechatSwitchRow">
                      <Checkbox
                        checked={form.clearSecret}
                        onChange={(event) =>
                          setForm((current) => ({
                            ...current,
                            clearSecret: event.target.checked,
                            secret: "",
                          }))
                        }
                      >
                        清空 Secret
                      </Checkbox>
                    </div>
                    <div className="enterpriseWechatActionRow">
                      <Button
                        type="primary"
                        icon={<SaveOutlined />}
                        loading={saving}
                        onClick={() => void saveSettings()}
                      >
                        保存配置
                      </Button>
                    </div>
                  </div>
                  <Paragraph className="connectorDetailPreview">
                    {settings?.message || "正在读取企业微信配置状态。"}
                  </Paragraph>
                </div>
                <Collapse
                  ghost
                  items={[
                    {
                      key: "guide",
                      label: "配置引导与演示清单",
                      children: (
                        <div className="enterpriseWechatSection">
                          <div className="enterpriseWechatSectionHeader">
                            <Space direction="vertical" size={2}>
                              <Text strong>配置引导</Text>
                              <Text type="secondary">
                                先把企业微信参数和可见范围配好，再在聊天里做真实发送演示。
                              </Text>
                            </Space>
                            <Space size={6} wrap>
                              {missingFields.length ? (
                                missingFields.map((field) => (
                                  <Tag key={field} color="gold">
                                    {enterpriseWechatMissingFieldLabel(field)}
                                  </Tag>
                                ))
                              ) : (
                                <Tag color="green">配置完整</Tag>
                              )}
                            </Space>
                          </div>
                          <Row gutter={[12, 12]}>
                            <Col xs={24} lg={12}>
                              <div className="enterpriseWechatGuidePanel">
                                <Text strong>配置步骤</Text>
                                <div className="enterpriseWechatStepList">
                                  {(settings?.setup_steps || []).map((step) => (
                                    <div key={`${step.key}-${step.status}`} className="enterpriseWechatStep">
                                      <Space size={6}>
                                        <StatusTag value={step.status} />
                                        <Text strong>{step.label}</Text>
                                      </Space>
                                      <Text type="secondary">{step.description}</Text>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </Col>
                            <Col xs={24} lg={12}>
                              <div className="enterpriseWechatGuidePanel">
                                <Text strong>演示清单</Text>
                                <div className="enterpriseWechatStepList">
                                  {(settings?.demo_checklist || []).map((step) => (
                                    <div key={`${step.key}-${step.status}`} className="enterpriseWechatStep">
                                      <Space size={6}>
                                        <StatusTag value={step.status} />
                                        <Text strong>{step.label}</Text>
                                      </Space>
                                      <Text type="secondary">{step.description}</Text>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </Col>
                          </Row>
                        </div>
                      ),
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: "contacts",
            label: "通讯录与测试",
            children: (
              <Space direction="vertical" className="pageStack">
                <Row gutter={[12, 12]}>
                  <Col xs={24} lg={12}>
                    <div className="enterpriseWechatSection">
                      <div className="enterpriseWechatSectionHeader">
                        <Space direction="vertical" size={2}>
                          <Text strong>通讯录同步</Text>
                          <Text type="secondary">
                            成员 {contacts?.summary.users ?? 0}、部门 {contacts?.summary.departments ?? 0}
                            、群聊 {contacts?.summary.groups ?? 0}
                          </Text>
                        </Space>
                        <Button icon={<TeamOutlined />} loading={syncing} onClick={() => void syncContacts()}>
                          一键同步
                        </Button>
                      </div>
                      <div className="enterpriseWechatStepList">
                        {(diagnostics?.steps || []).map((step) => (
                          <div key={`${step.label}-${step.status}`} className="enterpriseWechatStep">
                            <Space size={6}>
                              <StatusTag value={step.status} />
                              <Text strong>{step.label}</Text>
                            </Space>
                            <Text type="secondary">{step.message}</Text>
                          </div>
                        ))}
                      </div>
                    </div>
                  </Col>
                  <Col xs={24} lg={12}>
                    <div className="enterpriseWechatSection">
                      <div className="enterpriseWechatSectionHeader">
                        <Space direction="vertical" size={2}>
                          <Text strong>手动录入群聊</Text>
                          <Text type="secondary">企业微信群聊第一版使用名称和 chat_id 手动维护。</Text>
                        </Space>
                      </div>
                      <div className="enterpriseWechatGroupGrid">
                        <Input
                          value={groupName}
                          placeholder="群聊名称"
                          onChange={(event) => setGroupName(event.target.value)}
                        />
                        <Input
                          value={groupChatId}
                          placeholder="chat_id"
                          onChange={(event) => setGroupChatId(event.target.value)}
                        />
                        <Button
                          icon={<PlusOutlined />}
                          loading={groupSaving}
                          onClick={() => void saveGroup()}
                        >
                          保存群聊
                        </Button>
                      </div>
                    </div>
                  </Col>
                </Row>
                <div className="enterpriseWechatSection">
                  <div className="enterpriseWechatSectionHeader">
                    <Space direction="vertical" size={2}>
                      <Text strong>通讯录候选</Text>
                      <Text type="secondary">搜索姓名、部门或群聊，重名时由管理员选择正确对象。</Text>
                    </Space>
                    <Button
                      icon={<SendOutlined />}
                      loading={testing}
                      disabled={!selectedContactId}
                      onClick={() => void testSend()}
                    >
                      发送安全测试文件
                    </Button>
                  </div>
                  <div className="enterpriseWechatSearchRow">
                    <Input
                      value={contactQuery}
                      prefix={<SearchOutlined />}
                      placeholder="搜索姓名、部门、群聊"
                      onPressEnter={() => void searchContacts()}
                      onChange={(event) => setContactQuery(event.target.value)}
                    />
                    <Select
                      value={contactType}
                      options={[
                        { value: "all", label: "全部类型" },
                        { value: "user", label: "成员" },
                        { value: "department", label: "部门" },
                        { value: "group", label: "群聊" },
                      ]}
                      onChange={(value) => {
                        setContactType(value);
                        void searchContacts(contactQuery, value);
                      }}
                    />
                    <Button icon={<SearchOutlined />} loading={loading} onClick={() => void searchContacts()}>
                      搜索
                    </Button>
                  </div>
                  <Table<EnterpriseWechatContactItem>
                    rowKey="id"
                    size="small"
                    loading={loading}
                    dataSource={contacts?.items || []}
                    columns={contactColumns}
                    scroll={{ x: 760 }}
                    pagination={{ pageSize: 6, hideOnSinglePage: true }}
                    locale={{ emptyText: <Empty description="暂无企业微信候选，请先同步或手动录入群聊" /> }}
                    rowSelection={{
                      type: "radio",
                      selectedRowKeys: selectedContactId ? [selectedContactId] : [],
                      onChange: (keys) => setSelectedContactId(String(keys[0] || "")),
                    }}
                  />
                </div>
              </Space>
            ),
          },
        ]}
      />
    </Space>
  );
}

export function enterpriseWechatMissingFieldLabel(value: string) {
  const labels: Record<string, string> = {
    corp_id: "Corp ID",
    agent_id: "Agent ID",
    secret: "Secret",
    real_send_enabled: "真实发送",
  };
  return labels[value] || value;
}

export function ConnectorConfigTable({ fields }: { fields: ConnectorConfigField[] }) {
  return (
    <Table
      rowKey="name"
      size="small"
      dataSource={fields}
      pagination={false}
      scroll={{ x: 540 }}
      locale={{ emptyText: <Empty description="无需环境变量配置" /> }}
      columns={[
        { title: "配置项", dataIndex: "name", width: 190, render: (value) => <Text className="connectorMono">{String(value)}</Text> },
        {
          title: "状态",
          dataIndex: "configured",
          width: 92,
          render: (value) => <Tag color={value ? "green" : "default"}>{value ? "已配置" : "未配置"}</Tag>,
        },
        {
          title: "值",
          dataIndex: "value_preview",
          width: 130,
          render: (value, record) => (
            <Text className="connectorMono">{value || (record.secret ? "****" : "-")}</Text>
          ),
        },
        { title: "说明", dataIndex: "description", render: (value) => <Text className="connectorText">{String(value)}</Text> },
      ]}
    />
  );
}

export function ConnectorDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="connectorDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "connectorMono" : "connectorText"}>{value}</Text>
    </div>
  );
}
