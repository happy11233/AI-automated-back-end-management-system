import { Empty, Space, Table, Tag } from "antd";
import { Paragraph, Text, Title, textFromUnknown, formatBytes } from "../workspace/shared";

export function SchemaTable({ items }: { items: Array<Record<string, unknown>> }) {
  return (
    <Table
      rowKey={(record) => String(record.name || record.label)}
      size="small"
      dataSource={items}
      pagination={false}
      scroll={{ x: 520 }}
      locale={{ emptyText: <Empty description="暂无 Schema" /> }}
      columns={[
        {
          title: "字段",
          dataIndex: "name",
          width: 150,
          render: (value, record) => (
            <Space direction="vertical" size={2} className="flowConfigCellStack">
              <Text strong className="flowConfigMono">{textFromUnknown(value)}</Text>
              <Text type="secondary" className="flowConfigText">{textFromUnknown(record.label)}</Text>
            </Space>
          ),
        },
        { title: "类型", dataIndex: "type", width: 110, render: (value) => <Tag>{textFromUnknown(value)}</Tag> },
        {
          title: "要求",
          render: (_, record) => {
            const values = [
              record.required ? "必填" : "可选",
              record.max_length ? `最长 ${record.max_length}` : null,
              record.max_bytes ? `最大 ${formatBytes(Number(record.max_bytes))}` : null,
              record.description ? textFromUnknown(record.description) : null,
            ].filter(Boolean);

            return values.length ? (
              <Space size={[4, 4]} wrap>
                {values.map((item) => <Tag key={String(item)} color="blue">{String(item)}</Tag>)}
              </Space>
            ) : (
              <Text type="secondary">-</Text>
            );
          },
        },
      ]}
    />
  );
}
