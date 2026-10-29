import { Tag } from "antd";

export function ConnectorStatusTag({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    healthy: "green",
    degraded: "gold",
    unhealthy: "red",
    disabled: "default",
    unknown: "default",
    not_configured: "default",
    invalid_config: "red",
    not_implemented: "gold",
    configured_pending: "blue",
    configured: "green",
    stub_ready: "blue",
  };

  return <Tag color={colorMap[status] || "default"}>{labelForConnectorStatus(status)}</Tag>;
}

export function labelForConnectorStatus(value: string) {
  const labels: Record<string, string> = {
    healthy: "健康",
    degraded: "异常",
    unhealthy: "异常",
    disabled: "已暂停",
    unknown: "未检查",
    not_configured: "未配置",
    invalid_config: "配置异常",
    not_implemented: "待接入",
    configured_pending: "已配置待联调",
    configured: "已配置",
    stub_ready: "预留可用",
  };

  return labels[value] ?? value;
}
