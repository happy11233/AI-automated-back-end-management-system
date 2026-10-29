import { useMemo } from "react";
import { ApiOutlined, ReloadOutlined, TableOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Collapse,
  Empty,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Table,
  Tag,
  type TableColumnsType,
} from "antd";
import { ProCard, StatisticCard } from "@ant-design/pro-components";
import type {
  ErpDiagnosticsResponse,
  ErpQueryResponse,
  ErpResourceItem,
  ErpStatusResponse,
  Position,
} from "../api";
import { type Role, type View } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  TextArea,
  textFromUnknown,
  sanitizeTechnicalValue,
  formatAmount,
} from "../workspace/shared";

export function ErpPanel({
  role,
  position,
  activeView,
  status,
  diagnostics,
  resources,
  selectedResource,
  setSelectedResource,
  queryText,
  setQueryText,
  filtersText,
  setFiltersText,
  limit,
  setLimit,
  result,
  isLoading,
  onRefresh,
  onQuery,
}: {
  role: Role;
  position: Position | null;
  activeView: View;
  status: ErpStatusResponse | null;
  diagnostics: ErpDiagnosticsResponse | null;
  resources: ErpResourceItem[];
  selectedResource: string;
  setSelectedResource: (value: string) => void;
  queryText: string;
  setQueryText: (value: string) => void;
  filtersText: string;
  setFiltersText: (value: string) => void;
  limit: number;
  setLimit: (value: number) => void;
  result: ErpQueryResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  onQuery: () => void;
}) {
  const statusColor = status?.ok ? "green" : status?.configured ? "gold" : "default";
  const selected = resources.find((item) => item.resource === selectedResource);
  const diagnosticHealth = diagnostics?.active_health;
  const currentErpView = activeView === "erp" ? "erp_query" : activeView;
  const resultColumns = useMemo(
    () => buildErpResultColumns(result),
    [result],
  );

  const queryPanel = (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="ERP 连接查询"
        subTitle="管理员用于验证 ERP 连接、资源映射和岗位数据；员工查询由 AI 对话自动触发"
        bordered
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <Card size="small" title="连接状态" className="erpAlignedCard">
              <Space direction="vertical" size={12} className="pageStack">
                <Space size={[8, 8]} wrap>
                  <Tag color="blue">{status?.provider_label || "ERP"}</Tag>
                  <Tag color={statusColor}>{status?.status || "unknown"}</Tag>
                  {status?.configured ? <Tag color="green">已配置</Tag> : <Tag>未配置</Tag>}
                </Space>
                <Paragraph type="secondary" className="erpDescription">
                  {status?.message || "点击刷新获取 ERP 连接状态和当前岗位资源。"}
                </Paragraph>
                {selected ? (
                  <div>
                    <Text strong>{selected.label}</Text>
                    <Paragraph type="secondary" className="erpDescription">
                      {selected.description}
                    </Paragraph>
                  </div>
                ) : null}
              </Space>
            </Card>
          </Col>
          <Col xs={24} lg={16}>
            <Card size="small" title="查询条件" className="erpAlignedCard">
              <Form layout="vertical" className="erpQueryForm">
                <Row gutter={12}>
                  <Col xs={24} md={12}>
                    <Form.Item label="资源">
                      <Select
                        value={selectedResource || undefined}
                        placeholder="选择当前岗位允许的 ERP 资源"
                        onChange={setSelectedResource}
                        options={resources.map((item) => ({
                          label: `${item.label} / ${item.resource}`,
                          value: item.resource,
                        }))}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item label="关键字">
                      <Input
                        value={queryText}
                        placeholder="可选，例如订单号、客户名、SKU"
                        onChange={(event) => setQueryText(event.target.value)}
                      />
                    </Form.Item>
                  </Col>
                  {role === "admin" ? (
                    <Col xs={24}>
                      <Form.Item label="高级过滤（JSON，可选）">
                        <TextArea
                          value={filtersText}
                          rows={4}
                          placeholder='例如 {"status": "Open"}，一般只需要填写上面的关键字'
                          onChange={(event) => setFiltersText(event.target.value)}
                        />
                      </Form.Item>
                    </Col>
                  ) : null}
                  <Col xs={24} md={8}>
                    <Form.Item label="返回数量">
                      <InputNumber
                        min={1}
                        max={100}
                        value={limit}
                        onChange={(value) => setLimit(typeof value === "number" ? value : 10)}
                      />
                    </Form.Item>
                  </Col>
                </Row>
                <Space>
                  <Button icon={<ReloadOutlined />} onClick={onRefresh}>
                    刷新
                  </Button>
                  <Button type="primary" icon={<ApiOutlined />} loading={isLoading} onClick={onQuery}>
                    查询 ERP
                  </Button>
                </Space>
              </Form>
            </Card>
          </Col>
        </Row>
      </ProCard>
      <ProCard title="连接结果" bordered>
        {result ? (
          <ErpQueryResultView result={result} columns={resultColumns} role={role} />
        ) : (
          <Empty description="还没有连接查询结果" />
        )}
      </ProCard>
    </Space>
  );

  const diagnosticsPanel = (
    <ProCard title="管理员 ERP 诊断" bordered>
      {diagnostics ? (
        <Space direction="vertical" size={14} className="pageStack">
          <StatisticCard.Group direction="row">
            <StatisticCard
              statistic={{
                title: "连接状态",
                value: diagnosticHealth?.status || "unknown",
                status: diagnosticHealth?.ok ? "success" : "warning",
                description: String(diagnosticHealth?.detail || diagnosticHealth?.message || ""),
              }}
            />
            <StatisticCard
              statistic={{
                title: "当前 Provider",
                value: diagnostics.active_provider_label,
                status: diagnostics.active_configured ? "success" : "warning",
                description: diagnostics.active_provider,
              }}
            />
            <StatisticCard
              statistic={{
                title: "岗位映射",
                value: diagnostics.position_resource_mappings.reduce(
                  (count, item) => count + item.resources.filter((resource) => resource.supported).length,
                  0,
                ),
                suffix: "项",
                status: "processing",
                description: "当前 provider 支持的岗位资源",
              }}
            />
          </StatisticCard.Group>

          <Table
            rowKey="provider"
            size="small"
            pagination={false}
            dataSource={diagnostics.providers}
            columns={[
              {
                title: "Provider",
                dataIndex: "label",
                width: 140,
                render: (value, item) => (
                  <Space size={6}>
                    <Text>{String(value)}</Text>
                    {item.active ? <Tag color="blue">当前</Tag> : null}
                  </Space>
                ),
              },
              { title: "说明", dataIndex: "description" },
              {
                title: "配置",
                width: 110,
                render: (_, item) => (
                  <Tag color={item.configured ? "green" : "default"}>
                    {item.configured ? "已配置" : "未配置"}
                  </Tag>
                ),
              },
              {
                title: "配置项",
                render: (_, item) => (
                  <Space size={[4, 4]} wrap>
                    {item.config_fields.map((field) => (
                      <Tag color={field.configured ? "green" : "default"} key={`${item.provider}-${field.name}`}>
                        {field.name}
                        {field.value_preview ? `=${field.value_preview}` : ""}
                      </Tag>
                    ))}
                  </Space>
                ),
              },
            ]}
          />

          <Table
            rowKey="position"
            size="small"
            pagination={false}
            dataSource={diagnostics.position_resource_mappings}
            columns={[
              { title: "岗位", dataIndex: "position_label", width: 110 },
              {
                title: "资源映射",
                render: (_, item) => (
                  <Space size={[4, 4]} wrap>
                    {item.resources.map((resource) => (
                      <Tag color={resource.supported ? "green" : "gold"} key={`${item.position}-${resource.resource}`}>
                        {resource.label}:{resource.provider_resource || "未映射"}
                      </Tag>
                    ))}
                  </Space>
                ),
              },
            ]}
          />

          {diagnostics.next_steps.length ? (
            <Card size="small" title="下一步">
              <Space direction="vertical" size={4}>
                {diagnostics.next_steps.map((item) => (
                  <Text key={item}>{item}</Text>
                ))}
              </Space>
            </Card>
          ) : null}
        </Space>
      ) : (
        <Empty description="暂无诊断数据，点击刷新重新加载" />
      )}
    </ProCard>
  );

  const resourcesPanel = (
    <ProCard title="当前岗位可查询资源" bordered>
      <Table<ErpResourceItem>
        rowKey="resource"
        size="middle"
        pagination={false}
        dataSource={resources}
        locale={{ emptyText: <Empty description="暂无 ERP 资源，请刷新或联系管理员分配岗位" /> }}
        columns={[
          ...(role === "admin" ? [{ title: "资源", dataIndex: "resource", width: 170 }] : []),
          { title: "名称", dataIndex: "label", width: 140 },
          { title: "说明", dataIndex: "description" },
          ...(role === "admin" ? [{
            title: "当前 Provider 对象",
            width: 180,
            render: (_: unknown, item: ErpResourceItem) => {
              const provider = status?.provider || "erpnext";
              return item.provider_refs[provider] || "-";
            },
          }] : []),
        ]}
      />
    </ProCard>
  );

  if (currentErpView === "erp_resources") {
    return resourcesPanel;
  }

  if (currentErpView === "erp_diagnostics") {
    return role === "admin" ? diagnosticsPanel : <Empty description="当前账号无权查看 ERP 管理诊断" />;
  }

  return queryPanel;
}

export function ErpQueryResultView({
  result,
  columns,
  role,
}: {
  result: ErpQueryResponse;
  columns: ReturnType<typeof buildErpResultColumns>;
  role: Role;
}) {
  const statusTone = result.ok ? "green" : result.configured ? "gold" : "red";
  const businessMessage = result.ok
    ? result.items.length
      ? `已从 ${result.provider_label} 查询到 ${result.items.length} 条${result.resource_label}记录。`
      : `${result.provider_label} 连接正常，但当前条件下没有查到${result.resource_label}记录。`
    : result.message || "ERP 查询没有返回可用数据。";

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <Row gutter={[12, 12]}>
        <Col xs={24} md={8}>
          <Card size="small" className="erpResultSummaryCard">
            <Space direction="vertical" size={6}>
              <Text type="secondary">连接状态</Text>
              <Space size={6} wrap>
                <Tag color={statusTone}>{resultStatusLabel(result)}</Tag>
                <Tag>{result.provider_label}</Tag>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" className="erpResultSummaryCard">
            <Space direction="vertical" size={6}>
              <Text type="secondary">查询资源</Text>
              <Text strong>{result.resource_label}</Text>
              <Text type="secondary" className="erpResultSmallText">
                {result.provider_resource}
              </Text>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small" className="erpResultSummaryCard">
            <Space direction="vertical" size={6}>
              <Text type="secondary">返回记录</Text>
              <Text strong>{result.items.length} 条</Text>
              <Text type="secondary" className="erpResultSmallText">
                {result.configured ? "ERP 已配置" : "ERP 未配置"}
              </Text>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card size="small" className="erpResultMessageCard">
        <Space size={8} align="start">
          <TableOutlined className="erpResultMessageIcon" />
          <Paragraph className="erpResultMessage">{businessMessage}</Paragraph>
        </Space>
      </Card>

      {result.items.length ? (
        <Table<Record<string, unknown>>
          rowKey={(item, index) => `${textFromUnknown(item.name || item.id || item.po_no || item.lr_no)}-${index ?? 0}`}
          size="small"
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          scroll={{ x: true }}
          dataSource={result.items}
          columns={columns}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={result.ok ? "没有匹配记录，可以换一个订单号、客户名、SKU 或放宽过滤条件" : "查询失败，请先检查连接状态和资源权限"}
        />
      )}

      {role === "admin" ? (
        <Collapse
          ghost
          items={[
            {
              key: "debug",
              label: "管理员技术详情",
              children: <pre className="statePre">{JSON.stringify(sanitizeTechnicalValue(result), null, 2)}</pre>,
            },
          ]}
        />
      ) : null}
    </Space>
  );
}

export const erpFieldLabels: Record<string, string> = {
  name: "编号",
  id: "编号",
  customer: "客户",
  customer_name: "客户名称",
  supplier: "供应商",
  account: "科目",
  party: "往来方",
  item_code: "SKU",
  own_item_code: "关联我方 SKU",
  product_name: "商品名称",
  market: "站点",
  store: "店铺",
  brand: "品牌",
  company: "公司",
  price: "竞品售价",
  selling_price: "我方售价",
  rating: "评分",
  review_count: "评价数",
  order_no: "平台订单号",
  expected_payout: "预计净回款",
  actual_payout: "模拟实际回款",
  difference: "待核差额",
  spend: "广告花费",
  ad_sales: "广告销售额",
  acos: "ACOS（%）",
  tracking_no: "模拟运单号",
  carrier: "承运商",
  estimated_delivery: "预计送达",
  report_date: "广告日期",
  demo_batch: "模拟批次",
  is_simulated: "模拟数据",
  base_grand_total: "本位币金额",
  base_paid_amount: "本位币支付金额",
  paid_from_account_currency: "支付币种",
  item_name: "商品名称",
  item_group: "商品分组",
  status: "状态",
  priority: "优先级",
  subject: "主题",
  description: "说明",
  po_no: "订单号",
  lr_no: "物流单号",
  title: "标题",
  posting_date: "过账日期",
  transaction_date: "交易日期",
  due_date: "到期日",
  modified: "更新时间",
  grand_total: "金额",
  outstanding_amount: "未结金额",
  paid_amount: "支付金额",
  debit: "借方",
  credit: "贷方",
  voucher_type: "凭证类型",
  voucher_no: "凭证号",
  payment_type: "支付类型",
  price_list: "价格表",
  price_list_rate: "价格",
  currency: "币种",
  employee: "员工编号",
  employee_name: "员工",
  gross_pay: "应发工资",
  net_pay: "实发工资",
  start_date: "开始日期",
  end_date: "结束日期",
};

export const preferredErpFields = [
  "name",
  "customer",
  "customer_name",
  "supplier",
  "item_code",
  "item_name",
  "po_no",
  "lr_no",
  "subject",
  "account",
  "party",
  "status",
  "currency",
  "grand_total",
  "outstanding_amount",
  "paid_amount",
  "debit",
  "credit",
  "posting_date",
  "transaction_date",
  "due_date",
  "modified",
];

export function buildErpResultColumns(result: ErpQueryResponse | null): TableColumnsType<Record<string, unknown>> {
  if (!result?.items.length) {
    return [];
  }

  const availableFields = new Set<string>();
  result.items.forEach((item) => {
    Object.keys(item).forEach((key) => availableFields.add(key));
  });

  const crossborderFields: Record<string, string[]> = {
    "Crossborder Product": ["name", "item_code", "product_name", "market", "store", "currency", "selling_price", "is_simulated"],
    "Competitor Product": ["name", "own_item_code", "product_name", "market", "currency", "price", "rating", "is_simulated"],
    "Ad Campaign Daily": ["name", "item_code", "report_date", "market", "currency", "spend", "ad_sales", "acos"],
    "Marketplace Settlement": ["name", "order_no", "currency", "expected_payout", "actual_payout", "difference", "status", "is_simulated"],
    "Shipment Tracking": ["name", "order_no", "tracking_no", "carrier", "market", "estimated_delivery", "status", "is_simulated"],
    "Item Price": ["name", "item_code", "price_list", "price_list_rate", "currency", "modified"],
  };
  const preferred = crossborderFields[result.resource] || preferredErpFields;
  const orderedFields = [
    ...preferred.filter((field) => availableFields.has(field)),
    ...Array.from(availableFields)
      .filter((field) => !preferred.includes(field))
      .sort(),
  ].slice(0, 8);

  return orderedFields.map((field) => ({
    title: erpFieldLabels[field] || field,
    dataIndex: field,
    key: field,
    ellipsis: true,
    render: (value: unknown) => renderErpCell(value, field),
  }));
}

export function renderErpCell(value: unknown, field: string) {
  if (value === null || value === undefined || value === "") {
    return <Text type="secondary">-</Text>;
  }

  if (field === "status" || field === "priority" || field === "payment_type") {
    return <Tag>{textFromUnknown(value)}</Tag>;
  }

  if (typeof value === "number" && isAmountField(field)) {
    return formatAmount(value);
  }

  if (Array.isArray(value)) {
    return <Text className="erpResultSmallText">包含 {value.length} 条明细</Text>;
  }

  if (typeof value === "object") {
    return <Text className="erpResultSmallText">包含明细信息</Text>;
  }

  return textFromUnknown(value);
}

export function isAmountField(field: string) {
  return [
    "price",
    "selling_price",
    "expected_payout",
    "actual_payout",
    "difference",
    "spend",
    "ad_sales",
    "grand_total",
    "outstanding_amount",
    "paid_amount",
    "debit",
    "credit",
    "price_list_rate",
    "gross_pay",
    "net_pay",
  ].includes(field);
}

export function resultStatusLabel(result: ErpQueryResponse) {
  if (result.ok) {
    return result.items.length ? "查询成功" : "连接正常";
  }

  if (!result.configured) {
    return "未配置";
  }

  return result.status || "查询异常";
}
