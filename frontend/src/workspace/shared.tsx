import {
  ApiOutlined,
  AuditOutlined,
  BellOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  CommentOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  HistoryOutlined,
  PictureOutlined,
  MessageOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { Input, Tag, Tooltip, Typography } from "antd";
import type {
  ChatAttachment,
  Position,
  PlatformDraftItem,
  PlatformExecutionTaskItem,
  ThreadListItem,
} from "../api";
import type {
  NavItem,
  NavGroupItem,
  NavGroupId,
  View,
  Role,
  NavigableNavItem,
} from "./types";

export const { Paragraph, Text, Title } = Typography;

export const { TextArea } = Input;

export const positionConfigs: Record<Position, { label: string; department: string; capabilities: string[]; erpScopes: string[] }> = {
  operations: {
    label: "运营",
    department: "运营部",
    capabilities: ["生成 Listing", "生成标题", "生成五点描述", "生成关键词", "生成促销文案", "竞品分析"],
    erpScopes: ["Item", "Item Price", "Sales Order", "Sales Invoice summary"],
  },
  customer_service: {
    label: "客服",
    department: "客服部",
    capabilities: ["智能客服", "自动回复", "退款售后话术", "多语言客服翻译"],
    erpScopes: ["Customer", "Sales Order", "Delivery Note", "Issue", "Return request"],
  },
  finance: {
    label: "财务",
    department: "财务部",
    capabilities: ["分析财务报表", "统计工资", "上传 Excel 后按财务要求生成新 Excel 表"],
    erpScopes: ["GL Entry", "Payment Entry", "Salary Slip", "Sales Invoice", "Purchase Invoice"],
  },
};

export const aiWorkflowNavItems: NavItem[] = [
  {
    path: "/agents/operations-product-scene",
    id: "operations_product_scene",
    name: "运营商品场景图",
    icon: <PictureOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/agents/operations-listing-launch",
    id: "ai_workflow_operations_listing_launch",
    name: "运营 Listing 上架准备",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/agents/operations-competitor-analysis",
    id: "ai_workflow_operations_competitor_analysis",
    name: "运营竞品分析",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/agents/customer-service-refund-reply",
    id: "ai_workflow_customer_service_refund_reply",
    name: "客服退款售后处理",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/agents/customer-service-logistics-reply",
    id: "ai_workflow_customer_service_logistics_reply",
    name: "客服物流查询回复",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/agents/customer-service-message-loop",
    id: "ai_workflow_customer_service_message_loop",
    name: "客服消息自动化闭环",
    icon: <CommentOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/agents/finance-report-analysis",
    id: "ai_workflow_finance_report_analysis",
    name: "财务报表分析",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/agents/finance-salary-summary",
    id: "ai_workflow_finance_salary_summary",
    name: "财务工资统计",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/agents/finance-salary-wechat-send",
    id: "ai_workflow_finance_salary_wechat_send",
    name: "财务工资表发送准备",
    icon: <FileTextOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/agents/finance-monthly-package-wechat-send",
    id: "ai_workflow_finance_monthly_package_wechat_send",
    name: "财务月度资料整理",
    icon: <FileTextOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/agents/finance-excel-settlement",
    id: "ai_workflow_finance_excel_settlement",
    name: "财务 Excel 生成",
    icon: <CloudUploadOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/agents/finance-reconciliation",
    id: "ai_workflow_finance_reconciliation",
    name: "财务对账自动化",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
];

export function navGroup(id: string, name: string, children: NavItem[]): NavGroupItem {
  return {
    path: `/__nav/${id}`,
    id: `nav_group_${id}` as NavGroupId,
    name,
    icon: null,
    roles: ["admin", "employee"],
    type: "group",
    children,
  };
}

export const navItems: NavItem[] = [
  navGroup("home", "首页", [
    { path: "/dashboard", id: "dashboard", name: "概览", icon: <DatabaseOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("account", "账户", [
    { path: "/settings", id: "user_settings", name: "用户设置", icon: <EditOutlined />, roles: ["admin", "employee"] },
    { path: "/users", id: "users", name: "用户管理", icon: <SafetyCertificateOutlined />, roles: ["admin"] },
    { path: "/notifications", id: "notifications", name: "通知中心", icon: <BellOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("ai-workbench", "自动化工作台", [
    {
      path: "/agents",
      id: "ai_workflows",
      name: "Agent 中心",
      icon: <RobotOutlined />,
      roles: ["admin", "employee"],
      children: aiWorkflowNavItems,
    },
    { path: "/chat", id: "chat", name: "AI 对话", icon: <MessageOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("business-loop", "业务闭环", [
    { path: "/business-action-loop", id: "business_action_loop", name: "业务动作闭环", icon: <CheckCircleOutlined />, roles: ["admin", "employee"], positions: ["operations", "customer_service"] },
    { path: "/platform-drafts/review", id: "platform_draft_review", name: "草稿审核中心", icon: <CheckCircleOutlined />, roles: ["admin", "employee"], positions: ["operations", "customer_service"] },
    { path: "/platform-execution-tasks", id: "platform_execution_tasks", name: "执行任务中心", icon: <HistoryOutlined />, roles: ["admin", "employee"], positions: ["operations", "customer_service"] },
    {
      path: "/automation/customer-service-inbox",
      id: "customer_service_inbox",
      name: "客服自动化收件箱",
      icon: <CommentOutlined />,
      roles: ["admin", "employee"],
      positions: ["customer_service"],
    },
    { path: "/approvals", id: "approvals", name: "退款审批", icon: <CheckCircleOutlined />, roles: ["employee"], positions: ["customer_service"] },
    { path: "/files", id: "file_downloads", name: "文件下载", icon: <FileTextOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("knowledge-data", "知识与数据", [
    {
      path: "/erp",
      id: "erp",
      name: "ERP 查询",
      icon: <ApiOutlined />,
      roles: ["admin"],
      children: [
        {
          path: "/erp/query",
          id: "erp_query",
          name: "ERP 连接查询",
          icon: <SearchOutlined />,
          roles: ["admin"],
        },
        {
          path: "/erp/resources",
          id: "erp_resources",
          name: "ERP 资源列表",
          icon: <DatabaseOutlined />,
          roles: ["admin"],
        },
        {
          path: "/erp/diagnostics",
          id: "erp_diagnostics",
          name: "ERP 管理诊断",
          icon: <AuditOutlined />,
          roles: ["admin"],
        },
      ],
    },
    { path: "/documents", id: "documents", name: "知识库", icon: <FileTextOutlined />, roles: ["admin"] },
    { path: "/threads", id: "threads", name: "会话详情", icon: <RobotOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("governance", "治理监控", [
    { path: "/run-records", id: "run_records", name: "运行记录", icon: <HistoryOutlined />, roles: ["admin"] },
    { path: "/effect-analytics", id: "effect_analytics", name: "效果分析", icon: <AuditOutlined />, roles: ["admin"] },
    { path: "/evaluation-center", id: "evaluation_center", name: "AI 评测中心", icon: <CheckCircleOutlined />, roles: ["admin"] },
    { path: "/monitoring-center", id: "monitoring_center", name: "监控中心", icon: <SafetyCertificateOutlined />, roles: ["admin"] },
    { path: "/automation-flows", id: "automation_flows", name: "流程配置", icon: <AuditOutlined />, roles: ["admin"] },
    { path: "/connectors", id: "connectors", name: "连接器中心", icon: <ApiOutlined />, roles: ["admin"] },
    { path: "/mcp-tools", id: "mcp_tools", name: "MCP 工具管理", icon: <ApiOutlined />, roles: ["admin"] },
    { path: "/platform-action-executors", id: "platform_action_executors", name: "外部执行器配置", icon: <ApiOutlined />, roles: ["admin"] },
    { path: "/audit", id: "audit", name: "审计日志", icon: <AuditOutlined />, roles: ["admin"] },
  ]),
  navGroup("other", "其他", [
    { path: "/desktop-downloads", id: "desktop_downloads", name: "桌面端下载", icon: <DownloadOutlined />, roles: ["admin", "employee"] },
    { path: "/feedback", id: "feedback_improvement", name: "反馈改进", icon: <CommentOutlined />, roles: ["employee"] },
    { path: "/feedback-center", id: "feedback_center", name: "反馈中心", icon: <CommentOutlined />, roles: ["admin"] },
  ]),
];

export const aiWorkflowViewMap: Partial<Record<View, string>> = {
  ai_workflow_finance_salary_wechat_send: "finance_salary_wechat_send",
  ai_workflow_finance_monthly_package_wechat_send: "finance_monthly_package_wechat_send",
  ai_workflow_operations_listing_launch: "operations_listing_launch",
  ai_workflow_operations_competitor_analysis: "operations_competitor_analysis",
  ai_workflow_customer_service_refund_reply: "customer_service_refund_reply",
  ai_workflow_customer_service_logistics_reply: "customer_service_logistics_reply",
  ai_workflow_customer_service_message_loop: "customer_service_message_loop",
  ai_workflow_finance_report_analysis: "finance_report_analysis",
  ai_workflow_finance_salary_summary: "finance_salary_summary",
  ai_workflow_finance_excel_settlement: "finance_excel_settlement",
  ai_workflow_finance_reconciliation: "finance_reconciliation",
};

export const workflowIdViewMap: Record<string, View> = Object.fromEntries(
  Object.entries(aiWorkflowViewMap).map(([view, workflowId]) => [workflowId, view as View]),
) as Record<string, View>;

export const workflowSourceTaskIdMap: Record<string, string> = {
  finance_salary_wechat_send: "salary_wechat_send",
  finance_monthly_package_wechat_send: "finance_monthly_package_wechat_send",
  operations_listing_launch: "listing",
  operations_competitor_analysis: "competitor_analysis",
  customer_service_refund_reply: "refund_script",
  customer_service_logistics_reply: "smart_reply",
  customer_service_message_loop: "customer_service_message_loop",
  finance_report_analysis: "report_analysis",
  finance_salary_summary: "salary_summary",
  finance_excel_settlement: "finance_excel_transform",
  finance_reconciliation: "finance_reconciliation",
};

export const automationTaskViewMap: Partial<Record<View, string>> = {
  automation_operations_listing: "listing",
  automation_operations_title: "title",
  automation_operations_bullets: "bullets",
  automation_operations_keywords: "keywords",
  automation_operations_promo_copy: "promo_copy",
  automation_operations_competitor_analysis: "competitor_analysis",
  automation_customer_service_smart_reply: "smart_reply",
  automation_customer_service_auto_reply: "auto_reply",
  automation_customer_service_refund_script: "refund_script",
  automation_customer_service_multilingual_translation: "multilingual_translation",
  automation_finance_report_analysis: "report_analysis",
};

export const SENSITIVE_TECHNICAL_KEYS = [
  "authorization",
  "token",
  "cookie",
  "password",
  "secret",
  "api_key",
  "access_key",
  "refresh_token",
  "database_url",
];

export function sanitizeTechnicalValue(value: unknown, key = ""): unknown {
  const loweredKey = key.toLowerCase();
  if (SENSITIVE_TECHNICAL_KEYS.some((item) => loweredKey.includes(item))) {
    return "***";
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeTechnicalValue(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([childKey, childValue]) => [
        childKey,
        sanitizeTechnicalValue(childValue, childKey),
      ]),
    );
  }
  return value;
}

export function enterpriseWechatConfirmKey(artifactId: string, recipientId: string | null | undefined) {
  return `${artifactId || "artifact"}:${recipientId || "recipient"}`;
}

export function firstRecord(...values: unknown[]) {
  for (const value of values) {
    const record = recordFromUnknown(value);
    if (Object.keys(record).length > 0) {
      return record;
    }
  }
  return null;
}

export function chatAttachmentArtifactId(attachment: ChatAttachment) {
  return textFromUnknown(attachment.metadata?.artifact_id);
}

export function StatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    enabled: "green",
    draft: "default",
    reviewing: "gold",
    published: "green",
    deprecated: "default",
    rolled_back: "volcano",
    pending: "gold",
    approved: "green",
    rejected: "red",
    succeeded: "green",
    failed: "red",
    blocked: "volcano",
    running: "blue",
    active: "green",
    paused: "gold",
    archived: "default",
    removed: "default",
    revoked: "default",
    expired: "orange",
  };

  return <Tag color={colorMap[value] || "default"}>{labelForBadge(value)}</Tag>;
}

export function PlatformDraftStatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    pending_review: "gold",
    approved: "green",
    published: "blue",
    rejected: "red",
  };

  return <Tag color={colorMap[value] || "default"}>{platformDraftStatusLabel(value)}</Tag>;
}

export function RiskTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    unprocessed: "default",
    low: "green",
    medium: "gold",
    high: "red",
  };

  return <Tag color={colorMap[value] || "default"}>{riskLabel(value)}</Tag>;
}

export function EllipsisText({ value }: { value: unknown }) {
  const text = String(value ?? "-");

  return (
    <Tooltip title={text}>
      <Text className="tableEllipsisText">{text}</Text>
    </Tooltip>
  );
}

export function metricStatus(value: string): "success" | "processing" | "error" | "default" | "warning" {
  if (value === "success" || value === "processing" || value === "error" || value === "warning") {
    return value;
  }

  return "default";
}

export function textFromUnknown(value: unknown) {
  return String(value ?? "").slice(0, 120);
}

export function recordFromUnknown(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return {};
}

export function stringListFromUnknown(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => textFromUnknown(item)).filter(Boolean);
  }

  if (typeof value === "string") {
    return value
      .split(/\n|\r|；|;|•/)
      .map((item) => item.replace(/^\s*[-*\d.、)）]+\s*/, "").trim())
      .filter(Boolean);
  }

  return [];
}

export function formatAmount(value: number) {
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function readStoredPosition(): Position | null {
  const value = localStorage.getItem("position");
  return isPosition(value) ? value : null;
}

export function readStoredAllowedAiAppIds(): string[] | null {
  const value = localStorage.getItem("allowed_ai_app_ids");
  if (!value) {
    return null;
  }

  try {
    const parsed = JSON.parse(value) as unknown;
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : null;
  } catch {
    return null;
  }
}

export function canAccessNavItem(
  item: NavItem,
  role: Role,
  position: Position | null,
  allowedAiAppIds: string[] | null = readStoredAllowedAiAppIds(),
) {
  return item.roles.includes(role)
    && (role === "admin" || !item.positions?.length || item.positions.includes(position as Position))
    && (item.type === "group" || isViewAllowedByAiApp(item.id, role, allowedAiAppIds));
}

export function isViewAllowedByAiApp(view: View, role: Role, allowedAiAppIds: string[] | null) {
  if (role === "admin" || allowedAiAppIds === null) {
    return true;
  }

  const appId = aiAppIdForView(view);
  return !appId || allowedAiAppIds.includes(appId);
}

export function aiAppIdForView(view: View): string | null {
  if (view === "operations_product_scene") return "operations-product-scene";
  const taskId = automationTaskViewMap[view];
  if (taskId) {
    return `automation-${taskId}`;
  }

  const workflowId = aiWorkflowViewMap[view];
  if (workflowId) {
    return aiAppIdForWorkflowId(workflowId);
  }

  if (view === "automation_finance_excel_transform" || view === "automation_finance_excel_upload") {
    return "finance-excel-transform";
  }

  if (view === "file_downloads") {
    return null;
  }

  if (view === "automation_finance_reconciliation") {
    return "finance-reconciliation";
  }

  if (view === "customer_service_inbox") {
    return "customer-service-message-loop";
  }

  if (view === "approvals") {
    return "customer-service-refund-approvals";
  }

  if (view === "chat") {
    const storedPosition = readStoredPosition();
    return storedPosition ? `${storedPosition}-chat-agent` : null;
  }

  if (view === "erp_query") {
    const storedPosition = readStoredPosition();
    return storedPosition ? `${storedPosition}-erp-query` : null;
  }

  return null;
}

export function aiAppIdForWorkflowId(workflowId: string): string {
  if (workflowId === "finance_excel_settlement") {
    return "finance-excel-transform";
  }

  if (workflowId === "finance_reconciliation") {
    return "finance-reconciliation";
  }

  if (workflowId === "customer_service_message_loop") {
    return "customer-service-message-loop";
  }

  const sourceTaskId = workflowSourceTaskIdMap[workflowId] || workflowId;
  return `automation-${sourceTaskId}`;
}

export function flattenNavItems(items: NavItem[]): NavItem[] {
  return items.flatMap((item) => [item, ...flattenNavItems(item.children || [])]);
}

export function isNavigableNavItem(item: NavItem): item is NavigableNavItem {
  return item.type !== "group";
}

export function flattenNavigableNavItems(items: NavItem[]): NavigableNavItem[] {
  return flattenNavItems(items).filter(isNavigableNavItem);
}

export function allNavItems(): NavigableNavItem[] {
  return flattenNavigableNavItems(navItems);
}

export function canRoleAccessView(
  role: Role,
  view: View,
  position: Position | null = readStoredPosition(),
  allowedAiAppIds: string[] | null = readStoredAllowedAiAppIds(),
) {
  const item = allNavItems().find((nav) => nav.id === view);
  return item ? canAccessNavItem(item, role, position, allowedAiAppIds) : false;
}

export function canUseCustomerServiceInbox(role: Role, position: Position | null) {
  return role === "admin" || position === "customer_service";
}

export function canUseApprovalCenter(role: Role, position: Position | null) {
  return role === "employee" && position === "customer_service";
}

export function compactDisplayText(value: string, limit: number) {
  const text = value.replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit)}...` : text;
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(value: string | null) {
  if (!value) {
    return "-";
  }

  return formatDate(value);
}

export function shortThreadId(threadId: string) {
  if (!threadId) {
    return "";
  }

  return threadId.length > 18 ? `${threadId.slice(0, 14)}...` : threadId;
}

export function threadTitleSource(thread: ThreadListItem) {
  const explicitTitle = thread.title?.trim();
  if (explicitTitle && explicitTitle !== "新会话") {
    return explicitTitle;
  }

  const firstUserMessage = thread.first_user_message_preview?.trim();
  if (firstUserMessage) {
    return firstUserMessage;
  }

  if (explicitTitle) {
    return explicitTitle;
  }

  return shortThreadId(thread.id) || "未命名会话";
}

export function threadDisplayTitle(thread: ThreadListItem, role: Role) {
  const baseTitle = threadTitleSource(thread).trim();
  const cleanTitle = baseTitle.length > 28 ? `${baseTitle.slice(0, 28)}...` : baseTitle;

  if (role !== "admin") {
    return cleanTitle;
  }

  const owner = thread.display_name || thread.username || "未知用户";
  const positionText = thread.position ? positionLabel(thread.position) : roleLabel((thread.role || "employee") as Role);
  return `${cleanTitle} / ${positionText} / ${owner}`;
}

export function formatDuration(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  if (value < 1000) {
    return `${value}ms`;
  }

  return `${(value / 1000).toFixed(1)}s`;
}

export function formatPercent(value: unknown) {
  if (typeof value !== "number") {
    return "0%";
  }

  return `${Math.round(value * 1000) / 10}%`;
}

export function formatBytes(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  if (value < 1024) {
    return `${value}B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)}KB`;
  }

  return `${(value / 1024 / 1024).toFixed(1)}MB`;
}

export function runStatusLabel(value: string) {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "执行中",
    succeeded: "已完成",
    failed: "失败",
    blocked: "已阻断",
    cancelled: "已取消",
  };

  return labels[value] ?? value;
}

export function roleLabel(role: Role) {
  return role === "admin" ? "管理员" : "员工";
}

export function positionLabel(position: Position) {
  return positionConfigs[position].label;
}

export function isPosition(value: unknown): value is Position {
  return value === "operations" || value === "customer_service" || value === "finance";
}

export function labelForBadge(value: string) {
  const labels: Record<string, string> = {
    enabled: "已启用",
    draft: "草稿",
    reviewing: "审核中",
    published: "已发布",
    deprecated: "已废弃",
    rolled_back: "已回滚",
    ready: "待运行",
    warning: "需关注",
    passed: "通过",
    pending: "待审批",
    approved: "已通过",
    rejected: "已拒绝",
    succeeded: "成功",
    failed: "失败",
    blocked: "已拦截",
    running: "运行中",
    active: "启用",
    paused: "暂停",
    archived: "归档",
    removed: "已移除",
    revoked: "已撤销",
    expired: "已过期",
  };

  return labels[value] ?? value;
}

export function riskLabel(value: string) {
  const labels: Record<string, string> = {
    unprocessed: "未处理",
    low: "低风险",
    medium: "中风险",
    high: "高风险",
  };

  return labels[value] ?? value;
}

export function customerIntentLabel(value: string) {
  const labels: Record<string, string> = {
    logistics: "物流查询",
    return_policy: "退货规则",
    size_advice: "尺码建议",
    exchange: "换货",
    shipping_time: "发货时效",
    promo_code: "优惠码",
    refund: "退款",
    complaint: "投诉",
    bad_review: "差评",
    chargeback: "拒付",
    general_question: "普通问题",
    未识别: "未识别",
  };

  return labels[value] ?? value;
}

export function platformDraftTypeLabel(value: string) {
  const labels: Record<string, string> = {
    listing: "Listing 草稿",
    customer_reply: "客服回复草稿",
  };

  return labels[value] ?? value;
}

export function platformDraftStatusLabel(value: string) {
  const labels: Record<string, string> = {
    pending_review: "待人工审核",
    approved: "已审核",
    published: "已发布",
    rejected: "已驳回",
  };

  return labels[value] ?? value;
}

export function PlatformExecutionTaskStatusTag({ value }: { value: string }) {
  return (
    <Tag color={platformExecutionTaskStatusColor(value)}>
      {platformExecutionTaskStatusLabel(value)}
    </Tag>
  );
}

export function platformExecutionTaskStatusLabel(value: string) {
  const labels: Record<string, string> = {
    queued: "队列中",
    dispatching: "派发中",
    waiting_callback: "等待回调",
    succeeded: "执行成功",
    failed: "执行失败",
    cancelled: "已取消",
  };

  return labels[value] ?? value;
}

export function platformExecutionTaskStatusColor(value: string) {
  const colors: Record<string, string> = {
    queued: "gold",
    dispatching: "processing",
    waiting_callback: "blue",
    succeeded: "green",
    failed: "red",
    cancelled: "default",
  };

  return colors[value] ?? "default";
}

export function FeedbackStatusTag({ value }: { value: string }) {
  return <Tag color={value === "completed" ? "green" : "gold"}>{value === "completed" ? "已完成" : "待处理"}</Tag>;
}

export function FeedbackPriorityTag({ value }: { value: string }) {
  const colors: Record<string, string> = {
    low: "default",
    normal: "blue",
    high: "orange",
    urgent: "red",
  };

  return <Tag color={colors[value] || "default"}>{feedbackPriorityLabel(value)}</Tag>;
}

export function feedbackPriorityLabel(value: string) {
  const labels: Record<string, string> = {
    low: "较低",
    normal: "普通",
    high: "较高",
    urgent: "紧急",
  };

  return labels[value] ?? value;
}

export function platformDraftWritebackLabel(value: string) {
  const labels: Record<string, string> = {
    draft_saved: "已保存草稿",
    rpa_ready: "RPA/连接器就绪",
    external_synced: "已同步外部平台",
    failed: "写回失败",
  };

  return labels[value] ?? value;
}

export function platformActionTypeLabel(value: string) {
  const labels: Record<string, string> = {
    write_listing_draft: "写入 Listing 草稿",
    write_customer_reply: "写入客服回复草稿",
    publish_listing: "发布 Listing",
    send_customer_reply: "发送客服回复",
  };

  return labels[value] ?? value;
}

export function shortDraftId(draftId: string) {
  return draftId.length > 18 ? `${draftId.slice(0, 8)}...${draftId.slice(-6)}` : draftId;
}

export function shortTaskId(taskId: string | null) {
  if (!taskId) {
    return "-";
  }

  return taskId.length > 18 ? `${taskId.slice(0, 8)}...${taskId.slice(-6)}` : taskId;
}

export function platformTaskDraftTitle(task: PlatformExecutionTaskItem) {
  return task.draft?.title || task.draft_title || textFromUnknown(task.metadata?.draft_title || "") || shortDraftId(task.draft_id);
}

export function platformTaskPosition(task: PlatformExecutionTaskItem) {
  return task.draft?.position || task.draft_position || task.position || task.metadata?.position || null;
}

export function canRetryPlatformTask(task: PlatformExecutionTaskItem) {
  return task.status === "failed" || task.status === "queued";
}

export function isWaitingPlatformTaskStatus(status: string) {
  return status === "queued" || status === "dispatching" || status === "waiting_callback";
}

export function canReviewPlatformDraft(draft: PlatformDraftItem) {
  return draft.status === "pending_review" || draft.status === "rejected";
}

export function canRejectPlatformDraft(draft: PlatformDraftItem) {
  return draft.status === "pending_review" || draft.status === "approved";
}

export function platformDraftPublishButtonLabel(draft: PlatformDraftItem) {
  return draft.draft_type === "customer_reply" ? "发送" : "发布";
}

export function platformExecutionStatusLabel(value: string) {
  const labels: Record<string, string> = {
    waiting_executor: "等待外部执行器",
    running: "执行中",
    succeeded: "执行成功",
    failed: "执行失败",
  };

  return labels[value] ?? value;
}

export function platformExecutionStatusColor(value: string) {
  const colors: Record<string, string> = {
    waiting_executor: "gold",
    running: "processing",
    succeeded: "green",
    failed: "red",
  };

  return colors[value] ?? "default";
}

export function platformExecutorTypeLabel(value: string) {
  const labels: Record<string, string> = {
    webhook: "Webhook 执行器",
    manual_waiting: "等待配置",
  };

  return labels[value] ?? value;
}
