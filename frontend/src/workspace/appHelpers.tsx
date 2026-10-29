import { MessageOutlined } from "@ant-design/icons";
import {
  type ChatAttachment,
  type ApprovalItem,
  type AuditLogItem,
  type BusinessProgressPayload,
  type AutomationTaskItem,
  type ErpReference,
  type Position,
  type PlatformDraftItem,
  type PlatformExecutionTaskItem,
  type PlatformActionExecutorItem,
  type NotificationSummary,
  type RefundItem,
  type ThreadMessageItem,
  type ThreadListItem,
  type UserItem,
} from "../api";
import type {
  View,
  Role,
  ChatMessage,
  Approval,
  Refund,
  AuditLog,
  EffectAnalyticsFilterState,
  AiWorkflowFilterState,
  AutomationFlowFilterState,
  UserRecord,
  AutomationTaskRecord,
  NavItem,
  ChatRoute,
} from "./types";
import {
  aiWorkflowViewMap,
  recordFromUnknown,
  positionLabel,
  chatAttachmentArtifactId,
  textFromUnknown,
  firstRecord,
  navItems,
  threadDisplayTitle,
  canAccessNavItem,
  allNavItems,
  isPosition,
  compactDisplayText,
  formatDate,
} from "./shared";

export const EMPTY_NOTIFICATION_SUMMARY: NotificationSummary = {
  unread_count: 0,
  read_count: 0,
  total_count: 0,
  resource_count: 0,
};

export const auditActionLabels: Record<string, string> = {
  "admin.automation_flow_publication.rollback": "管理员回滚自动化流程发布",
  "admin.automation_flow_version.approve": "管理员批准自动化流程版本",
  "admin.automation_flow_version.create": "管理员创建自动化流程版本",
  "admin.automation_flow_version.preflight": "管理员执行自动化流程发布前检查",
  "admin.automation_flow_version.publish": "管理员发布自动化流程版本",
  "admin.automation_flow_version.publish_blocked": "自动化流程发布被预检拦截",
  "admin.automation_flow_version.reject": "管理员拒绝自动化流程版本",
  "admin.automation_flow_version.submit_review": "管理员提交自动化流程版本审核",
  "admin.automation_flow_version.update": "管理员更新自动化流程版本",
  "admin.automation_flow_version.verification_evidence.record": "管理员记录自动化流程验证证据",
  "admin.mcp_tool.health_check": "管理员检查 MCP 工具健康状态",
  "admin.mcp_tool.update": "管理员更新 MCP 工具状态",
  "admin.rag_document.access_update": "管理员更新知识文档访问权限",
  "admin.rag_document.grant_create": "管理员新增知识文档授权",
  "admin.rag_document.grant_revoke": "管理员撤销知识文档授权",
  "admin.rag_team.create": "管理员创建知识库团队",
  "admin.rag_team.member_add": "管理员添加知识库团队成员",
  "admin.rag_team.member_remove": "管理员移除知识库团队成员",
  "admin.rag_team.update": "管理员更新知识库团队",
  "admin.user.ai_app_permission_update": "管理员调整用户 AI 应用权限",
  "admin.user.create": "管理员创建用户",
  "admin.user.delete": "管理员删除用户",
  "admin.user.permission_assignment": "管理员分配用户岗位权限",
  "agent.chat.invoke": "Agent 对话调用",
  "ai_workflow.run": "AI 工作流运行",
  "approval.review": "审批处理",
  "automation.finance_excel_transform": "财务 Excel 新表生成",
  "automation.finance_reconciliation": "财务对账自动化",
  "automation.finance_report_analysis": "财务报表分析",
  "automation.finance_salary_export": "财务工资表导出",
  "automation.generate": "岗位自动化内容生成",
  "chat.automation_dispatch": "AI 对话触发业务自动化",
  "chat.blocked_by_position": "AI 对话被岗位权限拦截",
  "chat.finance_salary_export": "AI 对话导出财务工资表",
  "chat.invoke": "AI 对话调用",
  "chat.react_direct": "AI 对话 ReAct 直接处理",
  "chat.stream.automation_dispatch": "流式 AI 对话触发业务自动化",
  "chat.stream.finance_salary_export": "流式 AI 对话导出财务工资表",
  "chat.stream.invoke": "流式 AI 对话调用",
  "chat.stream.react_direct": "流式 AI 对话 ReAct 直接处理",
  "customer_service.message.create": "客服消息接入",
  "customer_service.message.process": "客服消息自动处理",
  "document.upload": "知识文档上传",
  "erp.dashboard_overview": "ERP 工作台概览查询",
  "erp.query": "ERP 数据查询",
  "erp.query.blocked_by_position": "ERP 查询被岗位权限拦截",
  "erp.record_detail": "ERP 单据详情查询",
  "feedback.complete": "管理员完成员工反馈",
  "feedback.create": "员工提交反馈",
  "mcp.documents.sync": "MCP 文档同步",
  "mcp.ticket.create": "MCP 工单创建",
  "mcp.ticket.get": "MCP 工单查询",
  "mcp_tool.invoke": "MCP 工具调用",
  "platform_action_executor.create": "管理员创建外部执行器",
  "platform_action_executor.delete": "管理员删除外部执行器",
  "platform_action_executor.health_check": "管理员检查外部执行器连接",
  "platform_action_executor.update": "管理员更新外部执行器",
  "platform_draft.execute": "平台草稿发送外部执行器",
  "platform_draft.review": "平台草稿审核",
  "platform_execution.callback": "外部执行器回调执行结果",
  "rag.authorization.deny": "知识库权限拒绝",
  "rag.authorization.hit": "知识库权限命中",
  "user.settings.password_update": "用户修改密码",
  "user.settings.profile_update": "用户更新个人设置",
};

export const auditResourceTypeLabels: Record<string, string> = {
  ai_workflow: "AI 工作流",
  approval: "审批",
  audit_log: "审计日志",
  automation: "岗位自动化",
  automation_flow: "自动化流程",
  automation_flow_publication: "自动化流程发布",
  automation_flow_version: "自动化流程版本",
  automation_flow_version_verification_evidence: "流程验证证据",
  chat: "AI 对话",
  customer_service_message: "客服消息",
  document: "知识文档",
  erp: "ERP 数据",
  feedback: "员工反馈",
  mcp: "MCP 工具",
  mcp_tool: "MCP 工具",
  platform_action_executor: "外部执行器",
  platform_draft: "平台草稿",
  platform_execution: "平台执行任务",
  rag_authorization: "知识库权限",
  rag_document: "知识文档",
  rag_document_grant: "知识文档授权",
  rag_team: "知识库团队",
  rag_team_member: "知识库团队成员",
  refund: "退款",
  user: "用户",
  user_settings: "用户设置",
};

export function chatAttachmentTypeFromFilename(filename: string): string {
  const lowered = filename.toLowerCase();
  if (lowered.endsWith(".doc") || lowered.endsWith(".docx")) {
    return "word_file";
  }
  return "excel_file";
}

export function chatMessageContainsArtifact(messageItem: ChatMessage, artifactId: string) {
  if (!artifactId) {
    return false;
  }
  if ((messageItem.attachments || []).some((attachment) => chatAttachmentArtifactId(attachment) === artifactId)) {
    return true;
  }

  const automation = recordFromUnknown(messageItem.automation);
  if (textFromUnknown(automation.artifact_id) === artifactId) {
    return true;
  }
  const approvalResult = recordFromUnknown(messageItem.approvalResult);
  const confirmationCard = firstRecord(
    approvalResult.confirmation_card,
    automation.confirmation_card,
    recordFromUnknown(automation.wechat_send).confirmation_card,
  );
  const artifact = recordFromUnknown(confirmationCard?.artifact);
  return textFromUnknown(artifact.artifact_id) === artifactId;
}

export function auditActionLabel(action: string) {
  const normalized = action.trim();

  if (!normalized) {
    return "-";
  }

  return auditActionLabels[normalized] || fallbackAuditActionLabel(normalized);
}

export function auditResourceTypeLabel(resourceType: string) {
  const normalized = resourceType.trim();

  if (!normalized || normalized === "-") {
    return "-";
  }

  return auditResourceTypeLabels[normalized] || fallbackAuditActionLabel(normalized);
}

export function auditBackendActionFilter(value: string) {
  const normalized = value.trim();

  if (!normalized) {
    return "";
  }

  const lowerValue = normalized.toLowerCase();
  const matchedAction = Object.entries(auditActionLabels).find(([action, label]) => {
    return action.toLowerCase().includes(lowerValue) || label.toLowerCase().includes(lowerValue);
  })?.[0];

  return matchedAction || (/^[a-z0-9_.-]+$/i.test(normalized) ? normalized : "");
}

export function fallbackAuditActionLabel(value: string) {
  return value
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => auditActionWordLabels[part.toLowerCase()] || part)
    .join(" / ");
}

export function defaultAutomationFlowFilters(role: Role, position: Position | null): AutomationFlowFilterState {
  return {
    position: role === "admin" ? "all" : position || "all",
    category: "",
  };
}

export function defaultAiWorkflowFilters(role: Role, position: Position | null): AiWorkflowFilterState {
  return {
    position: role === "admin" ? "all" : position || "all",
    category: "",
  };
}

export function defaultEffectAnalyticsFilters(role: Role, position: Position | null): EffectAnalyticsFilterState {
  return {
    dateRange: "30d",
    position: role === "admin" ? "all" : position || "all",
  };
}

export function overviewRecordId(item: Record<string, unknown>) {
  const value = item.name || item.po_no || item.lr_no || item.subject || item.item_code;
  return value ? textFromUnknown(value) : "";
}

export function readStoredRole(): Role {
  if (!localStorage.getItem("access_token")) {
    return "employee";
  }

  return localStorage.getItem("role") === "admin" ? "admin" : "employee";
}

export function visibleNavigationForUser(
  role: Role,
  position: Position | null,
  allowedAiAppIds: string[] | null,
): NavItem[] {
  return filterNavItemsForUser(navItems, role, position, allowedAiAppIds);
}

export function withChatThreadNavigation(
  items: NavItem[],
  threads: ThreadListItem[],
  role: Role,
): NavItem[] {
  return items.map((item) => {
    const children = item.children
      ? withChatThreadNavigation(item.children, threads, role)
      : undefined;

    if (item.id !== "chat") {
      return {
        ...item,
        ...(children ? { children } : {}),
      };
    }

    const threadChildren: NavItem[] = threads.slice(0, 5).map((thread) => ({
      path: `/chat/${encodeURIComponent(thread.id)}`,
      id: "chat" as View,
      name: threadDisplayTitle(thread, role),
      icon: <MessageOutlined />,
      roles: item.roles,
      positions: item.positions,
      threadId: thread.id,
    }));

    return {
      ...item,
      children: threadChildren,
    };
  });
}

export function filterNavItemsForUser(
  items: NavItem[],
  role: Role,
  position: Position | null,
  allowedAiAppIds: string[] | null,
): NavItem[] {
  return items
    .filter((item) => canAccessNavItem(item, role, position, allowedAiAppIds))
    .map((item) => {
      const children = item.children?.length
        ? filterNavItemsForUser(item.children, role, position, allowedAiAppIds)
        : undefined;

      return {
        ...item,
        ...(children ? { children } : {}),
      };
    })
    .filter((item) => !item.children || item.children.length > 0);
}

export const legacyAgentRoutes: Record<string, View> = {
  "/ai-apps": "ai_workflows",
  "/automation": "ai_workflows",
  "/automation/operations": "ai_workflows",
  "/automation/customer-service": "ai_workflows",
  "/automation/finance": "ai_workflows",
  "/automation/operations/listing": "ai_workflow_operations_listing_launch",
  "/automation/operations/title": "ai_workflow_operations_listing_launch",
  "/automation/operations/bullets": "ai_workflow_operations_listing_launch",
  "/automation/operations/keywords": "ai_workflow_operations_listing_launch",
  "/automation/operations/promo-copy": "ai_workflow_operations_listing_launch",
  "/automation/operations/competitor-analysis": "ai_workflow_operations_competitor_analysis",
  "/automation/customer-service/smart-reply": "ai_workflow_customer_service_message_loop",
  "/automation/customer-service/auto-reply": "ai_workflow_customer_service_message_loop",
  "/automation/customer-service/multilingual-translation": "ai_workflow_customer_service_message_loop",
  "/automation/customer-service/refund-script": "ai_workflow_customer_service_refund_reply",
  "/automation/finance/report-analysis": "ai_workflow_finance_report_analysis",
  "/automation/finance/salary-summary": "ai_workflow_finance_salary_summary",
  "/automation/finance/excel-transform": "ai_workflow_finance_excel_settlement",
  "/automation/finance/excel-upload": "ai_workflow_finance_excel_settlement",
  "/automation/finance/reconciliation": "ai_workflow_finance_reconciliation"
};

export function viewFromPath(pathname: string): View {
  if (pathname === "/chat/new" || pathname.startsWith("/chat/")) {
    return "chat";
  }

  const legacy = legacyAgentRoutes[pathname];
  if (legacy) return legacy;
  pathname = pathname.replace(/^\/ai-workflows(?=\/|$)/, "/agents");

  const matched = allNavItems().find((item) => item.path === pathname);
  return matched?.id || "dashboard";
}

export function pathForView(view: View): string {
  if (view === "ai_apps" || isAutomationView(view)) {
    const key = Object.keys(legacyAgentRoutes).find((path) =>
      path.replace(/^\//, "").replace(/[/-]/g, "_") === view
    );
    return pathForView(key ? legacyAgentRoutes[key] : "ai_workflows");
  }

  if (view === "erp") {
    return "/erp/query";
  }

  if (view === "automation_finance_excel_upload") {
    return "/automation/finance/excel-transform";
  }

  return allNavItems().find((item) => item.id === view)?.path || "/dashboard";
}

export function threadIdFromPathname(pathname: string) {
  if (!pathname.startsWith("/chat/") || pathname === "/chat/new") {
    return "";
  }

  const rawThreadId = pathname.replace(/^\/chat\//, "");
  try {
    return decodeURIComponent(rawThreadId);
  } catch {
    return rawThreadId;
  }
}

export function navigateToView(view: View, options: { replace?: boolean } = {}) {
  const path = pathForView(view);

  if (window.location.pathname !== path) {
    if (options.replace) {
      window.history.replaceState(null, "", path);
    } else {
      window.history.pushState(null, "", path);
    }
  }

  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function resolveNavTargetView(item: NavItem, role: Role, position: Position | null): View {
  if (item.id === "ai_workflows") return "ai_workflows";
  if (item.children?.length) {
    return resolveNavTargetView(item.children[0], role, position);
  }

  if (item.type === "group") {
    return "dashboard";
  }

  if (item.id === "erp") {
    return "erp_query";
  }

  if (item.id !== "automation") {
    return item.id;
  }

  if (role === "admin") {
    return "automation_operations";
  }

  if (position === "customer_service") {
    return "customer_service_inbox";
  }

  if (position === "finance") {
    return "automation_finance";
  }

  return "automation_operations";
}

export function readRoleFromToken(token: string): Role {
  const [, payload] = token.split(".");

  if (!payload) {
    return "employee";
  }

  try {
    const decoded = JSON.parse(window.atob(toBase64(payload))) as { role?: unknown };
    return decoded.role === "admin" ? "admin" : "employee";
  } catch {
    return "employee";
  }
}

export function readPositionFromToken(token: string): Position | null {
  const [, payload] = token.split(".");

  if (!payload) {
    return null;
  }

  try {
    const decoded = JSON.parse(window.atob(toBase64(payload))) as { position?: unknown };
    return isPosition(decoded.position) ? decoded.position : null;
  } catch {
    return null;
  }
}

export function toBase64(value: string) {
  return value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
}

export function titleForView(view: View) {
  const found = allNavItems().find((item) => item.id === view);
  return found?.name ?? "概览";
}

export function hasAdminAccess(role: Role, token?: string) {
  return token ? readRoleFromToken(token) === "admin" : role === "admin";
}

export function isAutomationView(view: View) {
  return view === "automation" || view.startsWith("automation_");
}

export function isAiWorkflowView(view: View) {
  return view === "ai_workflows" || view.startsWith("ai_workflow_");
}

export function workflowIdFromView(view: View) {
  return aiWorkflowViewMap[view] || null;
}

export function canUseBusinessActionLoop(role: Role, position: Position | null) {
  return role === "admin" || position === "operations" || position === "customer_service";
}

export function canUsePlatformExecutionTasks(role: Role, position: Position | null) {
  return role === "admin" || position === "operations" || position === "customer_service";
}

export function isErpView(view: View) {
  return view === "erp"
    || view === "erp_query"
    || view === "erp_resources"
    || view === "erp_diagnostics";
}

export function workspacePageDescription(view: View, role: Role, position: Position | null) {
  const descriptions: Partial<Record<View, string>> = {
    dashboard: "查看工作概况和业务数据，从常用入口开始处理任务",
    ai_apps: "查看业务 Agent 的接入状态、执行进度与成果",
    ai_workflows: "查看 Agent 接入状态、执行进度、业务成果与待处理事项",
    operations_product_scene: "上传商品白底图，描述目标场景并生成展示图片",
    effect_analytics: "了解自动化效果，比较岗位与应用表现",
    evaluation_center: "查看评测质量、报告及发布前检查",
    monitoring_center: "关注服务健康、运行趋势和待处理问题",
    run_records: "按状态查找执行记录，查看业务结果与完整过程",
    documents: "管理知识文档、团队与文档访问权限",
    user_settings: "维护个人资料和账号安全",
    users: "管理用户、岗位与 AI 应用权限",
    business_action_loop: "追踪从草稿、审核到外部执行的业务进度",
    platform_draft_review: "审核 AI 生成的草稿，确认后继续业务操作",
    platform_execution_tasks: "跟踪外部任务进度，处理失败与待回调任务",
    customer_service_inbox: "处理客户消息，查看风险和智能回复建议",
    connectors: "查看系统连接状态，按需配置外部服务",
    mcp_tools: "管理工具启用状态、岗位范围与健康检查",
    platform_action_executors: "配置业务动作执行器，检查连接与运行条件",
    automation_flows: "管理流程版本、审批规则与发布检查",
    notifications: "查看业务进展和需要关注的通知",
    file_downloads: "查找并下载自动化生成的业务文件",
    audit: "按动作和资源追溯系统操作",
    approvals: "审核退款及高风险客服事项",
    feedback_center: "处理反馈，跟踪问题改进进度",
    feedback_improvement: "提交建议并查看处理进度",
    erp: "查询权限范围内的业务数据与资源",
    erp_query: "选择资源并查询 ERP 业务记录",
    erp_resources: "查看已接入的 ERP 资源及可用范围",
    erp_diagnostics: "检查 ERP 连接、资源与访问权限",
  };
  if (descriptions[view]) return descriptions[view];
  if (isAiWorkflowView(view)) return "追踪 Agent 的触发来源、执行过程与业务成果";
  if (isAutomationView(view)) return "填写任务资料，生成并确认业务结果";
  return position
    ? `${positionLabel(position)}岗位工作台`
    : role === "admin"
      ? "企业业务管理工作台"
      : "员工工作台";
}

export function approvalActionLabel(actionType: string) {
  const labels: Record<string, string> = {
    refund: "退款审批",
    customer_service_refund: "客服退款审批",
    customer_service_complaint: "客服投诉审批",
    customer_service_bad_review: "差评风险审批",
    customer_service_chargeback: "拒付风险审批",
  };

  return labels[actionType] || `${actionType.replace(/_/g, " ")} 审批`;
}

export function buildApprovalSummaryFallback(actionType: string, payload: Record<string, unknown>) {
  const label = approvalActionLabel(actionType);
  const orderNo = String(payload.order_no || payload.orderNo || "未提供订单号");
  const reason = normalizeApprovalReviewerText(
    actionType,
    String(payload.user_input || payload.buyer_message || payload.handoff_reason || ""),
  );
  const reviewer = approvalReviewerLabel(actionType);
  const reasonText = reason ? `原因：${compactDisplayText(reason, 70)}` : `请${reviewer}确认是否允许继续处理。`;

  return `${label}，订单：${orderNo}。${reasonText}`;
}

export function approvalReviewerLabel(actionType: string) {
  return actionType === "refund" || actionType.startsWith("customer_service_") ? "客服" : "管理员";
}

export function normalizeApprovalReviewerText(actionType: string, value: string) {
  if (approvalReviewerLabel(actionType) !== "客服") {
    return value;
  }

  return value
    .replace(/需要管理员确认/g, "需要客服确认")
    .replace(/需要管理员审批/g, "需要客服审批")
    .replace(/管理员决定/g, "客服决定");
}

export function mapApproval(item: ApprovalItem): Approval {
  const payload = item.payload || {};
  const orderNo = String(payload.order_no || "待确认");
  const amount = moneyFromOrderResult(payload.order_result);
  const fallbackReason = String(payload.user_input || payload.buyer_message || item.action_type);

  return {
    id: item.id,
    threadId: item.thread_id,
    actionType: item.action_type,
    actionLabel: approvalActionLabel(item.action_type),
    status: item.status,
    refundStatus: item.refund_status || null,
    ticketStatus: item.ticket_status || null,
    externalTicketId: item.external_ticket_id || null,
    orderNo,
    amount,
    reason: fallbackReason,
    summary: String(item.summary_cn || payload.summary_cn || buildApprovalSummaryFallback(item.action_type, payload)),
    createdAt: formatDate(item.created_at),
  };
}

export function mapRefund(item: RefundItem): Refund {
  return {
    id: item.id,
    approvalId: item.approval_id,
    orderNo: item.order_no,
    amount: formatCents(item.amount_cents),
    status: item.status,
    createdAt: formatDate(item.created_at),
  };
}

export function mapAuditLog(item: AuditLogItem): AuditLog {
  const username = typeof item.metadata.username === "string" ? item.metadata.username : item.user_id || "-";
  const position = typeof item.metadata.position === "string" ? item.metadata.position : "-";

  return {
    id: item.id,
    action: item.action,
    actionLabel: auditActionLabel(item.action),
    resourceType: item.resource_type || "-",
    resourceTypeLabel: auditResourceTypeLabel(item.resource_type || "-"),
    resourceId: item.resource_id || "-",
    actor: username,
    position,
    createdAt: formatDate(item.created_at),
  };
}

export function mapUser(item: UserItem): UserRecord {
  return {
    id: item.id,
    username: item.username,
    displayName: item.display_name || "",
    email: item.email || "",
    role: item.role,
    department: item.department || "-",
    position: item.position,
    capabilities: item.capabilities || [],
    erpScopes: item.erp_scopes || [],
    allowedAiAppIds: item.allowed_ai_app_ids || [],
    aiAppPermissions: item.ai_app_permissions || [],
    createdAt: formatDate(item.created_at),
  };
}

export function mergeAutomationTasks(
  items: AutomationTaskItem[],
  current: AutomationTaskRecord[],
): AutomationTaskRecord[] {
  return items.map((item) => {
    const found = current.find((record) => record.task_id === item.task_id);

    return {
      ...item,
      inputText: found?.inputText ?? "",
      output: found?.output ?? "",
      platformDraft: found?.platformDraft ?? null,
    };
  });
}

export function mapThreadMessage(item: ThreadMessageItem): ChatMessage {
  const route = routeFromIntent(
    typeof item.metadata.intent === "string" ? item.metadata.intent : null,
    typeof item.metadata.risk_level === "string" ? item.metadata.risk_level : null,
  );

  return {
    id: item.id,
    threadId: item.thread_id,
    role: item.role,
    content: item.content,
    createdAt: formatDate(item.created_at),
    route,
    erpReferences: parseErpReferences(item.metadata.erp_references),
    attachments: parseChatAttachments(item.metadata.attachments),
    platformDraft: parsePlatformDraft(item.metadata.platform_draft),
    approvalResult: recordFromUnknown(item.metadata.approval_result),
    automation: recordFromUnknown(item.metadata.automation),
  };
}

export function normalizeBusinessProgress(value: unknown): BusinessProgressPayload | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const item = value as Record<string, unknown>;
  const label = typeof item.label === "string" ? item.label.trim() : "";
  if (!label) {
    return null;
  }
  return {
    thread_id: typeof item.thread_id === "string" ? item.thread_id : undefined,
    workflow_id: typeof item.workflow_id === "string" ? item.workflow_id : undefined,
    step_key: typeof item.step_key === "string" ? item.step_key : undefined,
    label,
    status: typeof item.status === "string" ? item.status : "running",
    detail: typeof item.detail === "string" ? item.detail : null,
    data: item.data && typeof item.data === "object" ? (item.data as Record<string, unknown>) : {},
  };
}

export function parseErpReferences(value: unknown): ErpReference[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      resource: textFromUnknown(item.resource),
      resource_label: textFromUnknown(item.resource_label || item.resource),
      record_id: textFromUnknown(item.record_id || item.name),
      title: textFromUnknown(item.title || item.record_id || item.name),
      provider: item.provider ? textFromUnknown(item.provider) : null,
      provider_resource: item.provider_resource ? textFromUnknown(item.provider_resource) : null,
    }))
    .filter((item) => item.resource && item.record_id);
}

export function parseChatAttachments(value: unknown): ChatAttachment[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item) => ({
      type: textFromUnknown(item.type),
      filename: textFromUnknown(item.filename || item.name),
      mime_type: textFromUnknown(item.mime_type),
      size_bytes: typeof item.size_bytes === "number" ? item.size_bytes : undefined,
      content_base64: typeof item.content_base64 === "string" ? item.content_base64 : undefined,
      metadata: typeof item.metadata === "object" && item.metadata !== null ? item.metadata as Record<string, unknown> : undefined,
    }))
    .filter((item) => item.filename);
}

export function parsePlatformDraft(value: unknown): PlatformDraftItem | null {
  if (typeof value !== "object" || value === null) {
    return null;
  }

  const item = value as Record<string, unknown>;
  const id = textFromUnknown(item.id);
  if (!id) {
    return null;
  }

  return {
    id,
    draft_type: textFromUnknown(item.draft_type),
    platform: textFromUnknown(item.platform),
    external_target: textFromUnknown(item.external_target),
    title: textFromUnknown(item.title),
    status: textFromUnknown(item.status),
    position: textFromUnknown(item.position),
    owner_user_id: item.owner_user_id ? textFromUnknown(item.owner_user_id) : null,
    source_run_id: item.source_run_id ? textFromUnknown(item.source_run_id) : null,
    source_resource_type: item.source_resource_type ? textFromUnknown(item.source_resource_type) : null,
    source_resource_id: item.source_resource_id ? textFromUnknown(item.source_resource_id) : null,
    content: typeof item.content === "object" && item.content !== null ? item.content as Record<string, unknown> : {},
    writeback_status: textFromUnknown(item.writeback_status),
    writeback_message: item.writeback_message ? textFromUnknown(item.writeback_message) : null,
    metadata: typeof item.metadata === "object" && item.metadata !== null ? item.metadata as Record<string, unknown> : {},
    created_at: textFromUnknown(item.created_at),
    updated_at: textFromUnknown(item.updated_at),
  };
}

export function moneyFromOrderResult(value: unknown) {
  if (typeof value === "object" && value !== null && "amount" in value) {
    return String((value as { amount?: unknown }).amount || "-");
  }

  return "-";
}

export function formatCents(value: number) {
  return `${(value / 100).toFixed(2)}元`;
}

export function routeFromIntent(intent: string | null, riskLevel: string | null): ChatRoute | undefined {
  if (intent === "order") {
    return "order_agent";
  }

  if (intent === "policy" || intent === "agent") {
    return "knowledge_rag";
  }

  if (intent === "finance_salary_export") {
    return "finance_salary_export";
  }

  if (intent === "finance_compound_report_generation") {
    return "finance_compound_report_generation";
  }

  if (intent === "finance_salary_wechat_send" || intent === "enterprise_wechat_file_send") {
    return "enterprise_wechat_file_send";
  }

  if (intent === "refund" || riskLevel === "high") {
    return "refund_workflow";
  }

  return undefined;
}

export function upsertPlatformExecutionTask(
  items: PlatformExecutionTaskItem[],
  nextTask: PlatformExecutionTaskItem,
) {
  const exists = items.some((item) => item.id === nextTask.id);
  const merged = exists
    ? items.map((item) => item.id === nextTask.id ? nextTask : item)
    : [nextTask, ...items];

  return merged.sort((a, b) => String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")));
}

export function upsertPlatformActionExecutor(
  items: PlatformActionExecutorItem[],
  nextItem: PlatformActionExecutorItem,
) {
  const exists = items.some((item) => item.id === nextItem.id);
  const merged = exists
    ? items.map((item) => item.id === nextItem.id ? nextItem : item)
    : [nextItem, ...items];

  return merged.sort((a, b) => Number(b.enabled) - Number(a.enabled) || String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")));
}

export function platformDraftPublishSuccessLabel(draft: PlatformDraftItem) {
  return draft.draft_type === "customer_reply" ? "客服回复已发送" : "Listing 已发布";
}

export const auditActionWordLabels: Record<string, string> = {
  access: "访问",
  add: "添加",
  admin: "管理员",
  agent: "Agent",
  ai: "AI",
  app: "应用",
  approve: "批准",
  approval: "审批",
  assignment: "分配",
  authorization: "权限",
  automation: "自动化",
  blocked: "拦截",
  by: "按",
  callback: "回调",
  chat: "对话",
  complete: "完成",
  create: "创建",
  customer: "客户",
  dashboard: "工作台",
  delete: "删除",
  deny: "拒绝",
  detail: "详情",
  direct: "直接处理",
  dispatch: "派发",
  document: "文档",
  documents: "文档",
  erp: "ERP",
  evidence: "证据",
  execute: "执行",
  executor: "执行器",
  feedback: "反馈",
  finance: "财务",
  flow: "流程",
  get: "查询",
  grant: "授权",
  health: "健康",
  hit: "命中",
  invoke: "调用",
  mcp: "MCP",
  member: "成员",
  message: "消息",
  overview: "概览",
  password: "密码",
  permission: "权限",
  platform: "平台",
  preflight: "预检",
  process: "处理",
  profile: "个人资料",
  publication: "发布记录",
  publish: "发布",
  query: "查询",
  rag: "知识库",
  react: "ReAct",
  reconciliation: "对账",
  record: "记录",
  reject: "拒绝",
  remove: "移除",
  report: "报表",
  review: "审核",
  revoke: "撤销",
  rollback: "回滚",
  run: "运行",
  salary: "工资",
  service: "客服",
  settings: "设置",
  stream: "流式",
  submit: "提交",
  sync: "同步",
  team: "团队",
  ticket: "工单",
  transform: "转换",
  update: "更新",
  upload: "上传",
  user: "用户",
  version: "版本",
  workflow: "工作流",
};
