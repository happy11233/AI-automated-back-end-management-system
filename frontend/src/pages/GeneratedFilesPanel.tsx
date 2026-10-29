import React from "react";
import { DownloadOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, Input, Row, Segmented, Select, Space, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { GeneratedFileItem } from "../api";
import { type Role, type GeneratedFileFilterState } from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  formatBytes,
  isPosition,
  positionLabel,
  formatTime,
  runStatusLabel,
  stringListFromUnknown,
  textFromUnknown,
} from "../workspace/shared";

export function GeneratedFilesPanel({
  role,
  files,
  filters,
  setFilters,
  loading,
  downloadingFileId,
  refreshFiles,
  downloadFile,
}: {
  role: Role;
  files: GeneratedFileItem[];
  filters: GeneratedFileFilterState;
  setFilters: React.Dispatch<React.SetStateAction<GeneratedFileFilterState>>;
  loading: boolean;
  downloadingFileId: string;
  refreshFiles: () => void;
  downloadFile: (file: GeneratedFileItem) => void;
}) {
  const excelCount = files.filter((item) => isExcelFile(item)).length;
  const wordCount = files.filter((item) => isWordFile(item)).length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="fileDownloadMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-blue">
            <Text type="secondary">可下载文件</Text>
            <Title level={3}>{files.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-green">
            <Text type="secondary">Excel</Text>
            <Title level={3}>{excelCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-purple">
            <Text type="secondary">Word</Text>
            <Title level={3}>{wordCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard metric-amber">
            <Text type="secondary">保存期</Text>
            <Title level={3}>30天</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="文件下载"
        subTitle={role === "admin" ? "管理员可查看全平台生成文件" : "当前账号生成过的文件会保留 1 个月"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshFiles} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="fileDownloadToolbar">
          <Input
            className="fileDownloadSearchControl"
            size="small"
            allowClear
            value={filters.search}
            placeholder="搜索文件、应用"
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            onPressEnter={refreshFiles}
          />
          <Segmented
            className="fileDownloadDateControl"
            size="small"
            value={filters.dateRange}
            onChange={(value) => setFilters((current) => ({ ...current, dateRange: value as GeneratedFileFilterState["dateRange"] }))}
            options={[
              { label: "今天", value: "today" },
              { label: "近7天", value: "7d" },
              { label: "近30天", value: "30d" },
              { label: "全部", value: "all" },
            ]}
          />
          <Select
            className="fileDownloadTypeControl"
            size="small"
            value={filters.fileType}
            onChange={(value) => setFilters((current) => ({ ...current, fileType: value }))}
            options={[
              { label: "全部类型", value: "all" },
              { label: "Excel", value: "excel" },
              { label: "Word", value: "word" },
            ]}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshFiles} loading={loading}>
            查询
          </Button>
        </div>

        <Table<GeneratedFileItem>
          rowKey="id"
          loading={loading}
          dataSource={files}
          className="fileDownloadTable"
          scroll={{ x: 1180 }}
          locale={{ emptyText: <Empty description="暂无可下载文件" /> }}
          columns={[
            {
              title: "文件",
              dataIndex: "name",
              width: 260,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{record.artifact_type}</Text>
                </Space>
              ),
            },
            {
              title: "应用",
              dataIndex: "app_name",
              width: 180,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text>{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{record.app_id}</Text>
                </Space>
              ),
            },
            {
              title: "业务摘要",
              dataIndex: "metadata",
              width: 360,
              render: (_, record) => <GeneratedFileBusinessSummary file={record} />,
            },
            {
              title: "类型",
              dataIndex: "mime_type",
              width: 100,
              render: (_, record) => <Tag color={isWordFile(record) ? "purple" : "blue"}>{fileTypeLabel(record)}</Tag>,
            },
            { title: "大小", dataIndex: "size_bytes", width: 100, render: (value) => formatBytes(value) },
            {
              title: "生成账号",
              dataIndex: "username",
              width: 140,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text>{value || "-"}</Text>
                  {isPosition(record.position) ? <Tag color="purple">{positionLabel(record.position)}</Tag> : null}
                </Space>
              ),
            },
            { title: "生成时间", dataIndex: "created_at", width: 160, render: (value) => formatTime(value) },
            { title: "过期时间", dataIndex: "expires_at", width: 160, render: (value) => formatTime(value) },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 100,
              render: (_, record) => (
                <Button
                  size="small"
                  type="link"
                  icon={<DownloadOutlined />}
                  loading={downloadingFileId === record.id}
                  disabled={!record.downloadable}
                  onClick={() => downloadFile(record)}
                >
                  下载
                </Button>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

export function GeneratedFileBusinessSummary({ file }: { file: GeneratedFileItem }) {
  const summary = generatedFileBusinessSummary(file);

  return (
    <Space direction="vertical" size={6} className="generatedFileBusinessSummary">
      <Space size={6} wrap>
        <Tag color={summary.color}>{summary.typeLabel}</Tag>
        <Tag color={file.status === "succeeded" ? "green" : "gold"}>{runStatusLabel(file.status)}</Tag>
      </Space>
      <Text strong className="generatedFileSummaryTitle">{summary.title}</Text>
      <div className="generatedFileMetricGrid">
        {summary.metrics.map((item) => (
          <span className="generatedFileMetric" key={`${item.label}-${item.value}`}>
            <Text type="secondary">{item.label}</Text>
            <Text>{item.value}</Text>
          </span>
        ))}
      </div>
      {summary.note ? <Text type="secondary" className="generatedFileSummaryNote">{summary.note}</Text> : null}
    </Space>
  );
}

export function isExcelFile(file: GeneratedFileItem) {
  const mime = (file.mime_type || "").toLowerCase();
  const name = file.name.toLowerCase();
  return mime.includes("spreadsheet") || name.endsWith(".xlsx") || name.endsWith(".xls");
}

export function isWordFile(file: GeneratedFileItem) {
  const mime = (file.mime_type || "").toLowerCase();
  const name = file.name.toLowerCase();
  return mime.includes("wordprocessingml") || name.endsWith(".docx");
}

export function fileTypeLabel(file: GeneratedFileItem) {
  if (isExcelFile(file)) {
    return "Excel";
  }

  if (isWordFile(file)) {
    return "Word";
  }

  return file.artifact_type || "文件";
}

export function generatedFileBusinessSummary(file: GeneratedFileItem): {
  typeLabel: string;
  color: string;
  title: string;
  metrics: Array<{ label: string; value: string }>;
  note: string;
} {
  const metadata = file.metadata || {};
  const runType = file.run_type || file.app_id || "";
  const sourceFiles = stringListFromUnknown(metadata.source_filenames);
  const sourceFilename = textFromUnknown(metadata.source_filename || sourceFiles[0] || "");

  if (runType === "finance_salary_export" || file.app_id === "automation-salary_summary") {
    return {
      typeLabel: "工资表",
      color: "purple",
      title: "工资导出结果",
      metrics: [
        { label: "期间", value: textFromUnknown(metadata.period_label || `${metadata.start_date || "-"} 至 ${metadata.end_date || "-"}`) },
        { label: "员工数", value: countLabel(metadata.employee_count, "人") },
        { label: "应发合计", value: moneyLabel(metadata.gross_pay_total) },
        { label: "实发合计", value: moneyLabel(metadata.net_pay_total) },
      ],
      note: `数据来源：${textFromUnknown(metadata.provider_label || metadata.resource || "ERP 工资单")}，下载和查看会进入审计。`,
    };
  }

  if (runType === "finance_excel_transform" || file.app_id === "finance-excel-transform") {
    return {
      typeLabel: "Excel 生成",
      color: "blue",
      title: sourceFilename ? `来源文件：${sourceFilename}` : "财务 Excel 处理结果",
      metrics: [
        { label: "工作表", value: countLabel(metadata.sheet_count, "个") },
        { label: "数据行", value: countLabel(metadata.total_rows, "行") },
        { label: "字段数", value: countLabel(metadata.total_columns, "列") },
        { label: "ERP 表", value: countLabel(metadata.erp_resource_count, "个") },
      ],
      note: textFromUnknown(metadata.instruction_preview || "已生成处理摘要、数值汇总和 AI 建议。"),
    };
  }

  if (runType === "finance_reconciliation" || file.app_id === "finance-reconciliation") {
    return {
      typeLabel: "财务对账",
      color: "gold",
      title: `币种：${textFromUnknown(metadata.base_currency || "CNY")}`,
      metrics: [
        { label: "源文件", value: countLabel(metadata.source_file_count, "个") },
        { label: "订单行", value: countLabel(metadata.order_line_count, "行") },
        { label: "异常", value: countLabel(metadata.anomaly_count, "条") },
        { label: "利润", value: moneyLabel(metadata.total_profit) },
      ],
      note: `销售额 ${moneyLabel(metadata.total_sales)}，亏损订单 ${countLabel(metadata.negative_profit_count, "个")}。`,
    };
  }

  if (runType === "finance_report_analysis" || file.app_id === "automation-report_analysis") {
    return {
      typeLabel: "财务报告",
      color: isWordFile(file) ? "purple" : "blue",
      title: sourceFiles.length ? `来源：${sourceFiles.slice(0, 2).join("、")}` : "财务报表分析结果",
      metrics: [
        { label: "源文件", value: countLabel(metadata.source_file_count, "个") },
        { label: "解析文档", value: countLabel(metadata.parsed_document_count, "份") },
        { label: "解析字数", value: countLabel(metadata.parsed_text_chars, "字") },
        { label: "格式", value: textFromUnknown(metadata.output_format || fileTypeLabel(file)) },
      ],
      note: "报告包含摘要、关键指标、异常项、风险和复核建议。",
    };
  }

  return {
    typeLabel: fileTypeLabel(file),
    color: isWordFile(file) ? "purple" : "default",
    title: textFromUnknown(file.app_name || "生成文件"),
    metrics: [
      { label: "大小", value: formatBytes(file.size_bytes) },
      { label: "保存期", value: "30天" },
      { label: "生成时间", value: formatTime(file.created_at) },
      { label: "状态", value: runStatusLabel(file.status) },
    ],
    note: "可下载文件已保存，过期后会自动清理。",
  };
}

export function countLabel(value: unknown, unit: string) {
  if (typeof value !== "number") {
    return "-";
  }

  return `${value.toLocaleString("zh-CN")}${unit}`;
}

export function moneyLabel(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
