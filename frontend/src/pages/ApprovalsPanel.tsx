import { useState } from "react";
import { CheckCircleOutlined, RedoOutlined, StopOutlined } from "@ant-design/icons";
import { Button, Empty, Segmented, Space, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { Position } from "../api";
import { type Approval, type Role } from "../workspace/types";
import { canUseApprovalCenter, Paragraph, Text, Title, StatusTag, EllipsisText } from "../workspace/shared";

export function ApprovalsPanel({
  approvals,
  reviewApproval,
  retryRefund,
  role,
  position,
}: {
  approvals: Approval[];
  reviewApproval: (id: string, approved: boolean) => void;
  retryRefund: (id: string) => void;
  role: Role;
  position: Position | null;
}) {
  const [statusFilter, setStatusFilter] = useState("pending");
  const visibleApprovals = approvals.filter((item) => statusFilter === "all" || item.status === statusFilter);
  const canReview = canUseApprovalCenter(role, position);

  return (
    <ProCard title="退款审批列表" subTitle="客服岗位处理用户退款、售后升级和高风险客服消息" bordered>
      <div className="workspaceFilterBar workspaceStatusFilters">
        <Segmented
          aria-label="审批状态"
          value={statusFilter}
          onChange={(value) => setStatusFilter(String(value))}
          options={[
            { label: "待处理", value: "pending" },
            { label: "已通过", value: "approved" },
            { label: "已驳回", value: "rejected" },
            { label: "全部", value: "all" },
          ]}
        />
      </div>
      <Table<Approval>
        rowKey="id"
        dataSource={visibleApprovals}
        locale={{ emptyText: <Empty description="暂无待处理退款审批" /> }}
        scroll={{ x: 1120 }}
        columns={[
          {
            title: "审批用途",
            dataIndex: "summary",
            width: 360,
            render: (value) => <Text className="approvalSummaryText">{String(value || "-")}</Text>,
          },
          { title: "类型", dataIndex: "actionLabel", width: 150 },
          { title: "订单", dataIndex: "orderNo", width: 140 },
          { title: "金额", dataIndex: "amount", width: 140 },
          {
            title: "状态",
            dataIndex: "status",
            width: 120,
            render: (value) => <StatusTag value={String(value)} />,
          },
          {
            title: "退款结果",
            dataIndex: "refundStatus",
            width: 130,
            render: (value: Approval["refundStatus"]) => value
              ? <Tag color={value === "succeeded" ? "success" : value === "failed" ? "error" : "processing"}>
                  {value === "succeeded" ? "退款成功" : value === "failed" ? "退款失败" : "待执行/待核对"}
                </Tag>
              : "-",
          },
          {
            title: "外部工单",
            width: 180,
            render: (_, item) => item.ticketStatus
              ? <span>{item.externalTicketId || ({ pending: '待创建', dispatching: '创建中',
                succeeded: '已创建', failed: '创建失败待重试', uncertain: '结果待对账' }[item.ticketStatus])}</span>
              : '-',
          },
          {
            title: "原始原因",
            dataIndex: "reason",
            width: 220,
            ellipsis: true,
            render: (value) => <EllipsisText value={value} />,
          },
          {
            title: "审批 ID",
            dataIndex: "id",
            width: 180,
            ellipsis: true,
            render: (value) => <EllipsisText value={value} />,
          },
          { title: "时间", dataIndex: "createdAt", width: 150 },
          {
            title: "操作",
            width: 150,
            fixed: "right",
            render: (_, item) => (
              <Space>
                <Button
                  size="small"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  disabled={!canReview || item.status !== "pending"}
                  onClick={() => reviewApproval(item.id, true)}
                >
                  通过
                </Button>
                <Button
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  disabled={!canReview || item.status !== "pending"}
                  onClick={() => reviewApproval(item.id, false)}
                >
                  拒绝
                </Button>
                {item.status === "approved" && item.refundStatus !== null && item.refundStatus !== "succeeded" && (
                  <Button size="small" icon={<RedoOutlined />} disabled={!canReview}
                    onClick={() => retryRefund(item.id)}>重试退款</Button>
                )}
              </Space>
            ),
          },
        ]}
      />
    </ProCard>
  );
}
