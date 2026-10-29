import React from "react";
import { Button, Card, Empty, Modal, Space, Table, Tabs, Tag } from "antd";
import type { ErpRecordDetailResponse } from "../api";
import type {
  Role,
  ErpBusinessField,
  ErpBusinessRow,
  ErpAmountSummaryCard,
} from "../workspace/types";
import { Paragraph, Text, Title, sanitizeTechnicalValue, textFromUnknown } from "../workspace/shared";

export function ErpRecordDetailModal({
  open,
  loading,
  detail,
  role,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: ErpRecordDetailResponse | null;
  role: Role;
  onClose: () => void;
}) {
  const item = detail?.item || null;
  const rows = detail && item ? erpBusinessRows(detail.resource, item) : [];
  const moneyCards = item && detail ? erpMoneySummaryCards(detail.resource, item) : [];
  const rawDetail = detail ? {
    ...detail,
    item: item || null,
  } : null;
  const tabItems = detail ? [
    {
      key: "summary",
      label: "业务概览",
      children: (
        <Space direction="vertical" size={12} className="pageStack">
          {moneyCards.length ? (
            <div className="erpAmountCardGrid">
              {moneyCards.map((card) => (
                <div className="erpAmountCard" key={card.label}>
                  <Text type="secondary">{card.label}</Text>
                  <Title level={4}>{card.value}</Title>
                  {card.description ? <Text type="secondary">{card.description}</Text> : null}
                </div>
              ))}
            </div>
          ) : null}
          <div className="erpRecordDetailGrid">
            <ErpRecordDetailItem
              label="查询状态"
              value={<Tag color={detail.ok ? "green" : "gold"}>{detail.ok ? "已找到" : "未找到"}</Tag>}
            />
            <ErpRecordDetailItem label="数据来源" value={detail.provider_label} />
            <ErpRecordDetailItem label="业务对象" value={detail.resource_label} />
            <ErpRecordDetailItem label="记录编号" value={detail.record_id} mono />
          </div>
          <Card title="查询说明" size="small" className="erpRecordDetailSectionCard">
            <Paragraph className="erpRecordDetailMessage">{detail.message}</Paragraph>
          </Card>
        </Space>
      ),
    },
    {
      key: "fields",
      label: `业务字段 ${rows.length}`,
      children: rows.length ? (
        <Table
          rowKey="field"
          size="small"
          pagination={{ pageSize: 12, hideOnSinglePage: true }}
          dataSource={rows}
          columns={[
            {
              title: "分组",
              dataIndex: "group",
              width: 110,
              render: (value) => <Tag>{String(value || "业务信息")}</Tag>,
            },
            {
              title: "字段",
              dataIndex: "label",
              width: 180,
              render: (value) => <Text className="erpRecordText">{String(value)}</Text>,
            },
            {
              title: "内容",
              dataIndex: "value",
              render: (value, record) => (
                <Text className={record.mono ? "erpRecordMono" : "erpRecordText"}>
                  {String(value)}
                </Text>
              ),
            },
          ]}
        />
      ) : (
        <Empty description="暂无业务字段" />
      ),
    },
    ...(role === "admin" && rawDetail ? [
      {
        key: "tech",
        label: "技术详情",
        children: (
          <Card title="管理员技术详情" size="small" className="erpRecordDetailSectionCard">
            <pre className="erpRecordRawPre">{JSON.stringify(sanitizeTechnicalValue(rawDetail), null, 2)}</pre>
          </Card>
        ),
      },
    ] : []),
  ] : [];

  return (
    <Modal
      open={open}
      title={detail ? `ERP 记录详情 / ${detail.resource_label}` : "ERP 记录详情"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width="min(900px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载 ERP 记录详情" />
      ) : detail ? (
        <Tabs
          className="erpRecordDetailTabs"
          items={tabItems}
        />
      ) : (
        <Empty description="暂无 ERP 记录详情" />
      )}
    </Modal>
  );
}

export function ErpRecordDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="erpRecordDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "erpRecordMono" : "erpRecordText"}>{value}</Text>
    </div>
  );
}

export const ERP_BUSINESS_FIELDS: Record<string, ErpBusinessField[]> = {
  "Crossborder Product": [
    { key: "name", label: "商品档案", group: "基础信息", mono: true },
    { key: "item_code", label: "我方 SKU", group: "基础信息", mono: true },
    { key: "product_name", label: "商品名称", group: "基础信息" },
    { key: "market", label: "站点", group: "渠道信息" },
    { key: "store", label: "店铺", group: "渠道信息" },
    { key: "currency", label: "币种", group: "价格信息" },
    { key: "selling_price", label: "售价", group: "价格信息", money: true, important: true },
    { key: "rating", label: "模拟评分", group: "商品表现" },
    { key: "review_count", label: "模拟评价数", group: "商品表现" },
    { key: "features", label: "卖点与政策", group: "业务说明" },
    { key: "is_simulated", label: "模拟数据", group: "数据来源" },
  ],
  "Competitor Product": [
    { key: "name", label: "竞品档案", group: "基础信息", mono: true },
    { key: "own_item_code", label: "关联我方 SKU", group: "基础信息", mono: true },
    { key: "product_name", label: "竞品名称", group: "基础信息" },
    { key: "brand", label: "模拟品牌", group: "竞品信息" },
    { key: "market", label: "站点", group: "渠道信息" },
    { key: "price", label: "模拟售价", group: "价格信息", money: true, important: true },
    { key: "rating", label: "模拟评分", group: "竞品表现" },
    { key: "review_count", label: "模拟评价数", group: "竞品表现" },
    { key: "estimated_monthly_sales", label: "模拟月销量", group: "竞品表现" },
    { key: "fulfillment", label: "配送方式", group: "竞品信息" },
    { key: "strengths", label: "模拟优势", group: "分析记录" },
    { key: "weaknesses", label: "模拟短板", group: "分析记录" },
    { key: "data_source", label: "数据来源", group: "数据来源" },
    { key: "is_simulated", label: "模拟数据", group: "数据来源" },
  ],
  "Ad Campaign Daily": [
    { key: "name", label: "广告日报", group: "基础信息", mono: true },
    { key: "campaign_name", label: "模拟活动", group: "广告信息" },
    { key: "item_code", label: "SKU", group: "广告信息", mono: true },
    { key: "market", label: "站点", group: "广告信息" },
    { key: "report_date", label: "日期", group: "广告信息" },
    { key: "impressions", label: "曝光", group: "广告表现" },
    { key: "clicks", label: "点击", group: "广告表现" },
    { key: "ad_orders", label: "广告订单", group: "广告表现" },
    { key: "spend", label: "模拟花费", group: "广告表现", money: true, important: true },
    { key: "ad_sales", label: "模拟归因销售额", group: "广告表现", money: true },
    { key: "acos", label: "模拟 ACOS", group: "广告表现" },
    { key: "roas", label: "模拟 ROAS", group: "广告表现" },
  ],
  "Marketplace Settlement": [
    { key: "name", label: "结算记录", group: "基础信息", mono: true },
    { key: "order_no", label: "平台订单号", group: "订单信息", mono: true },
    { key: "item_code", label: "SKU", group: "订单信息", mono: true },
    { key: "market", label: "站点", group: "订单信息" },
    { key: "currency", label: "币种", group: "金额信息" },
    { key: "gross_amount", label: "模拟销售总额", group: "金额信息", money: true },
    { key: "refund_amount", label: "模拟退款额", group: "金额信息", money: true },
    { key: "platform_fee", label: "模拟平台佣金", group: "金额信息", money: true },
    { key: "fulfillment_fee", label: "模拟履约费", group: "金额信息", money: true },
    { key: "expected_payout", label: "模拟预计回款", group: "对账信息", money: true },
    { key: "actual_payout", label: "模拟到账", group: "对账信息", money: true },
    { key: "difference", label: "待核差额", group: "对账信息", money: true, important: true },
    { key: "status", label: "对账状态", group: "对账信息" },
    { key: "is_simulated", label: "模拟数据", group: "数据来源" },
  ],
  "Shipment Tracking": [
    { key: "name", label: "物流记录", group: "基础信息", mono: true },
    { key: "order_no", label: "平台订单号", group: "订单信息", mono: true },
    { key: "tracking_no", label: "模拟运单号", group: "物流信息", mono: true },
    { key: "carrier", label: "模拟承运商", group: "物流信息" },
    { key: "market", label: "站点", group: "物流信息" },
    { key: "shipped_date", label: "模拟发货日期", group: "物流信息" },
    { key: "estimated_delivery", label: "模拟预计送达", group: "物流信息" },
    { key: "status", label: "模拟物流状态", group: "物流信息", important: true },
    { key: "last_event", label: "模拟物流轨迹", group: "业务说明" },
    { key: "is_simulated", label: "模拟数据", group: "数据来源" },
  ],
  Item: [
    { key: "name", label: "商品编号", group: "基础信息", mono: true },
    { key: "item_code", label: "SKU", group: "基础信息", mono: true },
    { key: "item_name", label: "商品名称", group: "基础信息" },
    { key: "item_group", label: "商品分组", group: "基础信息" },
    { key: "stock_uom", label: "库存单位", group: "库存信息" },
    { key: "disabled", label: "是否停用", group: "状态信息" },
    { key: "description", label: "商品描述", group: "业务说明" },
  ],
  "Item Price": [
    { key: "name", label: "价格记录", group: "基础信息", mono: true },
    { key: "item_code", label: "SKU", group: "基础信息", mono: true },
    { key: "price_list", label: "价格表", group: "价格信息" },
    { key: "price_list_rate", label: "价格", group: "价格信息", money: true, important: true },
    { key: "currency", label: "币种", group: "价格信息" },
    { key: "valid_from", label: "生效日期", group: "状态信息" },
    { key: "valid_upto", label: "失效日期", group: "状态信息" },
  ],
  Bin: [
    { key: "name", label: "库存记录", group: "基础信息", mono: true },
    { key: "item_code", label: "SKU", group: "基础信息", mono: true },
    { key: "warehouse", label: "仓库", group: "库存信息" },
    { key: "actual_qty", label: "实际库存", group: "库存信息", important: true },
    { key: "projected_qty", label: "预计库存", group: "库存信息" },
    { key: "reserved_qty", label: "已预留", group: "库存信息" },
    { key: "ordered_qty", label: "已订购", group: "库存信息" },
  ],
  "Sales Order": [
    { key: "name", label: "销售订单", group: "基础信息", mono: true },
    { key: "customer", label: "客户", group: "客户信息" },
    { key: "customer_name", label: "客户名称", group: "客户信息" },
    { key: "transaction_date", label: "订单日期", group: "时间信息" },
    { key: "delivery_date", label: "交付日期", group: "时间信息" },
    { key: "grand_total", label: "订单金额", group: "金额信息", money: true, important: true },
    { key: "currency", label: "币种", group: "金额信息" },
    { key: "status", label: "订单状态", group: "状态信息" },
  ],
  "Sales Invoice summary": [
    { key: "name", label: "销售发票", group: "基础信息", mono: true },
    { key: "customer", label: "客户", group: "客户信息" },
    { key: "customer_name", label: "客户名称", group: "客户信息" },
    { key: "posting_date", label: "过账日期", group: "时间信息" },
    { key: "grand_total", label: "发票总额", group: "金额信息", money: true, important: true },
    { key: "currency", label: "币种", group: "金额信息" },
    { key: "outstanding_amount", label: "未结金额", group: "金额信息", money: true, important: true },
    { key: "status", label: "发票状态", group: "状态信息" },
  ],
  Customer: [
    { key: "name", label: "客户编号", group: "基础信息", mono: true },
    { key: "customer_name", label: "客户名称", group: "基础信息" },
    { key: "customer_type", label: "客户类型", group: "基础信息" },
    { key: "customer_group", label: "客户分组", group: "基础信息" },
    { key: "territory", label: "地区", group: "业务信息" },
    { key: "email_id", label: "邮箱", group: "联系信息" },
    { key: "mobile_no", label: "手机号", group: "联系信息" },
  ],
  "Delivery Note": [
    { key: "name", label: "发货单", group: "基础信息", mono: true },
    { key: "customer", label: "客户", group: "客户信息" },
    { key: "customer_name", label: "客户名称", group: "客户信息" },
    { key: "posting_date", label: "发货日期", group: "时间信息" },
    { key: "grand_total", label: "发货金额", group: "金额信息", money: true, important: true },
    { key: "currency", label: "币种", group: "金额信息" },
    { key: "status", label: "发货状态", group: "状态信息" },
    { key: "tracking_no", label: "物流单号", group: "物流信息", mono: true },
  ],
  Issue: [
    { key: "name", label: "工单编号", group: "基础信息", mono: true },
    { key: "subject", label: "问题标题", group: "问题信息" },
    { key: "customer", label: "客户", group: "客户信息" },
    { key: "status", label: "处理状态", group: "状态信息" },
    { key: "priority", label: "优先级", group: "状态信息" },
    { key: "issue_type", label: "问题类型", group: "问题信息" },
    { key: "creation", label: "创建时间", group: "时间信息" },
  ],
  "Return request": [
    { key: "name", label: "退货请求", group: "基础信息", mono: true },
    { key: "customer", label: "客户", group: "客户信息" },
    { key: "sales_order", label: "关联订单", group: "业务信息", mono: true },
    { key: "item_code", label: "SKU", group: "业务信息", mono: true },
    { key: "qty", label: "数量", group: "业务信息" },
    { key: "status", label: "处理状态", group: "状态信息" },
    { key: "reason", label: "原因", group: "问题信息" },
  ],
  "GL Entry": [
    { key: "name", label: "总账记录", group: "基础信息", mono: true },
    { key: "posting_date", label: "过账日期", group: "时间信息" },
    { key: "account", label: "科目", group: "账务信息" },
    { key: "voucher_type", label: "凭证类型", group: "账务信息" },
    { key: "voucher_no", label: "凭证编号", group: "账务信息", mono: true },
    { key: "debit", label: "借方金额", group: "金额信息", money: true, important: true },
    { key: "credit", label: "贷方金额", group: "金额信息", money: true, important: true },
  ],
  "Payment Entry": [
    { key: "name", label: "收付款单", group: "基础信息", mono: true },
    { key: "payment_type", label: "收付款类型", group: "业务信息" },
    { key: "party_type", label: "对象类型", group: "业务信息" },
    { key: "party", label: "往来对象", group: "业务信息" },
    { key: "posting_date", label: "过账日期", group: "时间信息" },
    { key: "paid_amount", label: "支付金额", group: "金额信息", money: true, important: true },
    { key: "paid_from_account_currency", label: "支付币种", group: "金额信息" },
    { key: "status", label: "处理状态", group: "状态信息" },
  ],
  "Salary Slip": [
    { key: "name", label: "工资单", group: "基础信息", mono: true },
    { key: "employee", label: "员工编号", group: "员工信息", mono: true },
    { key: "employee_name", label: "员工姓名", group: "员工信息" },
    { key: "start_date", label: "开始日期", group: "期间信息" },
    { key: "end_date", label: "结束日期", group: "期间信息" },
    { key: "gross_pay", label: "应发工资", group: "金额信息", money: true, important: true },
    { key: "net_pay", label: "实发工资", group: "金额信息", money: true, important: true },
    { key: "status", label: "工资单状态", group: "状态信息" },
  ],
  "Sales Invoice": [
    { key: "name", label: "销售发票", group: "基础信息", mono: true },
    { key: "customer", label: "客户", group: "客户信息" },
    { key: "customer_name", label: "客户名称", group: "客户信息" },
    { key: "posting_date", label: "过账日期", group: "时间信息" },
    { key: "grand_total", label: "发票总额", group: "金额信息", money: true, important: true },
    { key: "currency", label: "币种", group: "金额信息" },
    { key: "outstanding_amount", label: "未结金额", group: "金额信息", money: true, important: true },
    { key: "status", label: "发票状态", group: "状态信息" },
  ],
  "Purchase Invoice": [
    { key: "name", label: "采购发票", group: "基础信息", mono: true },
    { key: "supplier", label: "供应商", group: "供应商信息" },
    { key: "supplier_name", label: "供应商名称", group: "供应商信息" },
    { key: "posting_date", label: "过账日期", group: "时间信息" },
    { key: "grand_total", label: "发票总额", group: "金额信息", money: true, important: true },
    { key: "currency", label: "币种", group: "金额信息" },
    { key: "outstanding_amount", label: "未结金额", group: "金额信息", money: true, important: true },
    { key: "status", label: "发票状态", group: "状态信息" },
  ],
};

export function erpBusinessRows(resource: string, item: Record<string, unknown>): ErpBusinessRow[] {
  const definitions = ERP_BUSINESS_FIELDS[resource] || fallbackErpBusinessFields(item);
  const seen = new Set<string>();
  return definitions
    .map((definition) => {
      seen.add(definition.key);
      return {
        field: definition.key,
        label: definition.label,
        group: definition.group,
        value: definition.money ? formatMoney(item[definition.key]) : businessValue(item[definition.key]),
        mono: definition.mono,
      };
    })
    .concat(
      Object.entries(item)
        .filter(([key, value]) => !seen.has(key) && value !== null && value !== "")
        .slice(0, 12)
        .map(([key, value]) => ({
          field: key,
          label: humanizeFieldName(key),
          group: "其他信息",
          value: businessValue(value),
          mono: false,
        })),
    );
}

export function fallbackErpBusinessFields(item: Record<string, unknown>): ErpBusinessField[] {
  return Object.keys(item).slice(0, 16).map((key) => ({
    key,
    label: humanizeFieldName(key),
    group: "业务信息",
    money: isMoneyField(key),
    important: isMoneyField(key),
    mono: key === "name" || key.endsWith("_id") || key.endsWith("_no"),
  }));
}

export function erpMoneySummaryCards(resource: string, item: Record<string, unknown>): ErpAmountSummaryCard[] {
  const definitions = ERP_BUSINESS_FIELDS[resource] || fallbackErpBusinessFields(item);
  return definitions
    .filter((definition) => definition.money && definition.important)
    .slice(0, 4)
    .map((definition) => ({
      label: definition.label,
      value: formatMoney(item[definition.key]),
      description: moneyCardDescription(definition.key),
    }));
}

export function moneyCardDescription(key: string) {
  const descriptions: Record<string, string> = {
    gross_pay: "工资单应发合计字段",
    net_pay: "工资单实发字段",
    grand_total: "单据总金额",
    outstanding_amount: "当前未结金额",
    paid_amount: "本次收付款金额",
    debit: "总账借方金额",
    credit: "总账贷方金额",
    price_list_rate: "商品当前价格",
  };
  return descriptions[key] || "";
}

export function businessValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  return textFromUnknown(value) || "-";
}

export function formatMoney(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const numeric = typeof value === "number" ? value : Number(String(value).replace(/,/g, ""));
  if (!Number.isFinite(numeric)) {
    return textFromUnknown(value) || "-";
  }
  return numeric.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function isMoneyField(key: string) {
  return [
    "gross_pay",
    "net_pay",
    "grand_total",
    "outstanding_amount",
    "paid_amount",
    "debit",
    "credit",
    "base_grand_total",
    "rounded_total",
    "price_list_rate",
  ].includes(key);
}

export function humanizeFieldName(key: string) {
  const labels: Record<string, string> = {
    name: "编号",
    status: "状态",
    posting_date: "过账日期",
    transaction_date: "业务日期",
    customer: "客户",
    supplier: "供应商",
    item_code: "SKU",
    employee: "员工编号",
    employee_name: "员工姓名",
  };
  return labels[key] || key.replace(/_/g, " ");
}
