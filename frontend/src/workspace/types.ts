import React from "react";
import type {
  ChatAttachment,
  BusinessProgressPayload,
  AutomationTaskItem,
  FeedbackCategory,
  FeedbackPriority,
  ErpReference,
  ErpResourceItem,
  Position,
  PublicLLMMessage,
  RagDocumentAccessMode,
  RagGrantAccessLevel,
  RagGrantSubjectType,
  RagTeamMemberRole,
  RagTeamStatus,
  PlatformDraftItem,
  PlatformDraftStatus,
  PlatformExecutionTaskStatus,
  NotificationStatus,
  UserAiAppPermissionItem,
} from "../api";

export type Role = "admin" | "employee";

export type ProjectTarget = "automation" | "gateway";

export type ChatRoute =
  | "refund_workflow"
  | "order_agent"
  | "knowledge_rag"
  | "finance_compound_report_generation"
  | "finance_salary_export"
  | "enterprise_wechat_file_send";

export type FinanceAutomationTool = "report_analysis" | "salary_export" | "excel_upload" | "reconciliation";

export type View =
  | "dashboard"
  | "ai_apps"
  | "business_action_loop"
  | "platform_draft_review"
  | "platform_execution_tasks"
  | "notifications"
  | "feedback_improvement"
  | "feedback_center"
  | "desktop_downloads"
  | "file_downloads"
  | "run_records"
  | "effect_analytics"
  | "evaluation_center"
  | "monitoring_center"
  | "ai_workflow_finance_salary_wechat_send"
  | "ai_workflow_finance_monthly_package_wechat_send"
  | "ai_workflows"
  | "ai_workflow_operations_listing_launch"
  | "ai_workflow_operations_competitor_analysis"
  | "operations_product_scene"
  | "ai_workflow_customer_service_refund_reply"
  | "ai_workflow_customer_service_logistics_reply"
  | "ai_workflow_customer_service_message_loop"
  | "ai_workflow_finance_report_analysis"
  | "ai_workflow_finance_salary_summary"
  | "ai_workflow_finance_excel_settlement"
  | "ai_workflow_finance_reconciliation"
  | "automation_flows"
  | "connectors"
  | "mcp_tools"
  | "platform_action_executors"
  | "automation"
  | "automation_operations"
  | "automation_operations_listing"
  | "automation_operations_title"
  | "automation_operations_bullets"
  | "automation_operations_keywords"
  | "automation_operations_promo_copy"
  | "automation_operations_competitor_analysis"
  | "automation_customer_service"
  | "automation_customer_service_smart_reply"
  | "automation_customer_service_auto_reply"
  | "automation_customer_service_refund_script"
  | "automation_customer_service_multilingual_translation"
  | "customer_service_inbox"
  | "automation_finance"
  | "automation_finance_report_analysis"
  | "automation_finance_salary_summary"
  | "automation_finance_excel_transform"
  | "automation_finance_excel_upload"
  | "automation_finance_reconciliation"
  | "erp"
  | "erp_query"
  | "erp_resources"
  | "erp_diagnostics"
  | "chat"
  | "user_settings"
  | "documents"
  | "users"
  | "approvals"
  | "refunds"
  | "audit"
  | "threads";

export type NavGroupId = `nav_group_${string}`;

export type NavItemBase = {
  path: string;
  name: string;
  icon: React.ReactNode;
  roles: Role[];
  positions?: Position[];
  children?: NavItem[];
};

export type NavRouteItem = NavItemBase & {
  id: View;
  type?: undefined;
  threadId?: string;
  chatAction?: "new";
};

export type NavGroupItem = NavItemBase & {
  id: NavGroupId;
  children: NavItem[];
  type: "group";
};

export type NavItem = NavRouteItem | NavGroupItem;

export type NavigableNavItem = NavItem & {
  id: View;
  type?: undefined;
  threadId?: string;
  chatAction?: "new";
};

export type ChatMessage = {
  id: string;
  threadId: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: string;
  route?: ChatRoute;
  erpReferences?: ErpReference[];
  attachments?: ChatAttachment[];
  platformDraft?: PlatformDraftItem | null;
  approvalResult?: Record<string, unknown> | null;
  automation?: Record<string, unknown> | null;
  businessProgress?: BusinessProgressPayload | null;
};

export type EnterpriseWechatRecipientCandidate = {
  id: string;
  name: string;
  objectType: string;
  objectTypeLabel: string;
  department: string;
  phoneLast4: string;
  avatarUrl: string;
  avatarText: string;
  raw: Record<string, unknown>;
};

export type EnterpriseWechatManualRecipientType = "user" | "group" | "department";

export type EnterpriseWechatConfirmationCardData = {
  title: string;
  status: string;
  statusLabel: string;
  description: string;
  recipientName: string;
  recipientSearchMessage: string;
  allowManualRecipient: boolean;
  requiresRecipientSelection: boolean;
  requiresSensitiveConfirmation: boolean;
  workflowId: string;
  sourceMessage: string;
  artifact: {
    artifactId: string;
    filename: string;
    downloadPath: string;
    mimeType: string;
  };
  candidates: EnterpriseWechatRecipientCandidate[];
  selectedRecipientId: string;
};

export type PublicLLMChatMessage = PublicLLMMessage & {
  id: string;
};

export type Approval = {
  id: string;
  threadId: string;
  actionType: string;
  actionLabel: string;
  status: string;
  refundStatus: 'pending' | 'succeeded' | 'failed' | null;
  ticketStatus: 'pending' | 'dispatching' | 'succeeded' | 'failed' | 'uncertain' | null;
  externalTicketId: string | null;
  orderNo: string;
  amount: string;
  reason: string;
  summary: string;
  createdAt: string;
};

export type Refund = {
  id: string;
  approvalId: string;
  orderNo: string;
  amount: string;
  status: string;
  createdAt: string;
};

export type AuditLog = {
  id: string;
  action: string;
  actionLabel: string;
  resourceType: string;
  resourceTypeLabel: string;
  resourceId: string;
  actor: string;
  position: string;
  createdAt: string;
};

export type UserRecord = {
  id: string;
  username: string;
  displayName: string;
  email: string;
  role: Role;
  department: string;
  position: Position | null;
  capabilities: string[];
  erpScopes: string[];
  allowedAiAppIds: string[];
  aiAppPermissions: UserAiAppPermissionItem[];
  createdAt: string;
};

export type AutomationTaskRecord = AutomationTaskItem & {
  inputText: string;
  output: string;
  platformDraft: PlatformDraftItem | null;
};

export type NewUserForm = {
  username: string;
  password: string;
  role: Role;
  position: Position | null;
  department: string;
};

export type AiAppRecord = {
  id: string;
  name: string;
  description: string;
  category: string;
  position: Position | "platform";
  positionLabel: string;
  status: "enabled" | "planned";
  dataSources: string[];
  owner: string;
  entryView: View;
  entryLabel: string;
};

export type RunRecordFilterState = {
  status: "all" | "running" | "succeeded" | "failed" | "blocked";
  runType: string;
  appId: string;
  position: Position | "all";
  resourceType: string;
  resourceId: string;
  flowKey: string;
};

export type GeneratedFileFilterState = {
  search: string;
  dateRange: "today" | "7d" | "30d" | "all";
  fileType: "all" | "excel" | "word";
};

export type PlatformDraftFilterState = {
  draftType: "all" | "listing" | "customer_reply";
  status: "all" | PlatformDraftStatus;
};

export type PlatformExecutionTaskFilterState = {
  status: "all" | PlatformExecutionTaskStatus;
};

export type NotificationFilterState = {
  status: "all" | NotificationStatus;
  page: number;
  pageSize: number;
};

export type FeedbackFilterState = {
  status: "all" | "open" | "completed";
};

export type FeedbackFormState = {
  category: FeedbackCategory;
  priority: FeedbackPriority;
  title: string;
  description: string;
};

export type PlatformActionExecutorFormState = {
  id: string | null;
  name: string;
  executorType: string;
  actionTypes: string[];
  webhookUrl: string;
  apiKey: string;
  timeoutSeconds: number;
  enabled: boolean;
};

export type EffectAnalyticsFilterState = {
  dateRange: "7d" | "30d" | "90d" | "all";
  position: Position | "all";
};

export type AutomationFlowFilterState = {
  position: Position | "all";
  category: string;
};

export type AutomationFlowVersionFormState = {
  version: string;
  changeSummary: string;
  approvalPolicy: string;
  failureStrategy: string;
  publishNotes: string;
  promptSummary: string;
  promptTemplatePreview: string;
  inputSchemaJson: string;
  outputSchemaJson: string;
  toolParametersJson: string;
  allowedTools: string[];
  allowedErpResources: ErpResourceItem[];
  selectedStepIds: string[];
  publishEnvironment: "dev" | "staging" | "production";
};

export type AiWorkflowFilterState = {
  position: Position | "all";
  category: string;
};

export type CustomerServiceInboxForm = {
  channel: "manual" | "amazon" | "email" | "ticket" | "api";
  buyerName: string;
  buyerEmail: string;
  buyerLanguage: string;
  marketplace: string;
  orderNo: string;
  trackingNo: string;
  sku: string;
  subject: string;
  message: string;
};

export type CustomerServiceInboxFilters = {
  status: string;
  riskLevel: string;
};

export type UserProfileFormState = {
  displayName: string;
  email: string;
};

export type UserPasswordFormState = {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
};

export type MonitoringCenterFilterState = {
  dateRange: "7d" | "30d" | "90d" | "all";
};

export type DashboardMarket = string;

export type DashboardDateRange = "all" | "today" | "7d" | "30d";

export type DashboardStore = "all" | "us_store" | "de_store" | "jp_store";

export type DocumentPositionScope = Position | "all";

export type DocumentMarketScope = "all" | "us" | "de" | "jp";

export type DocumentStoreScope = DashboardStore;

export type DocumentFieldScope =
  | "all"
  | "operations_listing"
  | "operations_inventory"
  | "operations_sales"
  | "customer_profile"
  | "customer_logistics"
  | "customer_after_sales"
  | "finance_invoice"
  | "finance_payment"
  | "finance_profit"
  | "finance_salary";

export type DocumentSensitivityLevel = "internal" | "confidential" | "restricted";

export type RagTeamFormState = {
  teamKey: string;
  name: string;
  description: string;
  positionScope: DocumentPositionScope;
  marketScope: DocumentMarketScope;
  storeScope: DocumentStoreScope;
  status: RagTeamStatus;
};

export type RagTeamMemberFormState = {
  userId: string;
  memberRole: RagTeamMemberRole;
  expiresAt: string;
};

export type DocumentAccessFormState = {
  accessMode: RagDocumentAccessMode;
  ownerUserId: string;
  ownerTeamId: string;
};

export type DocumentGrantFormState = {
  subjectType: RagGrantSubjectType;
  subjectId: string;
  accessLevel: RagGrantAccessLevel;
  reason: string;
  expiresAt: string;
};

export type RunRecordMcpToolCall = {
  key: string;
  toolId: string;
  label: string;
  serverName: string;
  toolName: string;
  riskLevel: string;
  status: string;
  stepStatus: string;
  message: string;
  durationMs: number | null;
  backendPermissionChecked: boolean;
  permissionGate: string;
  requiresApproval: boolean;
  source: string;
};

export type RunRecordBusinessTimelineItem = {
  key: string;
  title: string;
  description: string;
  status: string;
  time: string;
  duration: string;
  provider: string;
  resource: string;
};

export type RunRecordEvidenceItem = {
  key: string;
  title: string;
  description: string;
  tag?: string;
  mono?: string;
};

export type EnterpriseWechatFormState = {
  corpId: string;
  agentId: string;
  secret: string;
  clearSecret: boolean;
  realSendEnabled: boolean;
  timeoutSeconds: number;
};

export type ErpBusinessField = {
  key: string;
  label: string;
  group: string;
  mono?: boolean;
  money?: boolean;
  important?: boolean;
};

export type ErpBusinessRow = {
  field: string;
  label: string;
  group: string;
  value: string;
  mono?: boolean;
};

export type ErpAmountSummaryCard = {
  label: string;
  value: string;
  description?: string;
};
