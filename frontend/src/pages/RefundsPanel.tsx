import { Empty, Table } from "antd";
import { ProCard } from "@ant-design/pro-components";
import { type Refund } from "../workspace/types";
import { StatusTag, EllipsisText } from "../workspace/shared";

export function RefundsPanel({ refunds }: { refunds: Refund[] }) {
  return (
    <ProCard title="退款流水" bordered>
      <Table<Refund>
        rowKey="id"
        dataSource={refunds}
        locale={{ emptyText: <Empty description="暂无退款流水" /> }}
        scroll={{ x: 760 }}
        columns={[
          { title: "订单", dataIndex: "orderNo", width: 160 },
          { title: "金额", dataIndex: "amount", width: 120 },
          { title: "状态", dataIndex: "status", width: 120, render: (value) => <StatusTag value={String(value)} /> },
          { title: "时间", dataIndex: "createdAt", width: 160 },
          { title: "审批 ID", dataIndex: "approvalId", width: 220, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
        ]}
      />
    </ProCard>
  );
}
