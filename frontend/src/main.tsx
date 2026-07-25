import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiOutlined,
  AppstoreOutlined,
  AuditOutlined,
  BellOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  CommentOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  LoginOutlined,
  DownOutlined,
  FileTextOutlined,
  HistoryOutlined,
  LogoutOutlined,
  MessageOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  SendOutlined,
  SearchOutlined,
  StopOutlined,
  TableOutlined,
  TeamOutlined,
  UpOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import {
  App as AntApp,
  Avatar,
  Button,
  Card,
  Checkbox,
  Col,
  ConfigProvider,
  Collapse,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Dropdown,
  Modal,
  Popconfirm,
  Radio,
  Row,
  Segmented,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
  theme,
  type TableColumnsType,
  type UploadFile,
} from "antd";
import {
  PageContainer,
  ProCard,
  ProConfigProvider,
  ProLayout,
  StatisticCard,
} from "@ant-design/pro-components";
import "./styles.css";
import {
  login,
  checkPlatformActionExecutorHealth,
  completeFeedback,
  createThread,
  createFeedback,
  createPlatformActionExecutor,
  createUser,
  deletePlatformActionExecutor,
  deleteUser,
  executePlatformDraft,
  getBusinessActionLoop,
  getPlatformDraftDetail,
  getPlatformExecutionTask,
  getEffectAnalytics,
  getEvaluationCenter,
  getMonitoringCenter,
  getMySettings,
  getAiWorkflowDetail,
  getConnectorDetail,
  getAutomationFlowDetail,
  getAutomationFlowVersion,
  approveAutomationFlowVersion,
  analyzeFinanceReport,
  downloadGeneratedFile,
  generateAutomation,
  createAutomationFlowVersion,
  createCustomerServiceMessage,
  getCustomerServiceMessageDetail,
  isAuthExpiredError,
  exportFinanceSalary,
  addRagTeamMember,
  createDocumentGrant,
  createRagTeam,
  listCustomerServiceMessages,
  listDocumentGrants,
  reconcileFinanceFiles,
  transformFinanceExcel,
  getDocumentAccess,
  getErpDashboardOverview,
  getErpDiagnostics,
  getErpRecordDetail,
  getErpScopes,
  getErpStatus,
  listAutomationTasks,
  listGeneratedFiles,
  listFeedback,
  listPlatformDrafts,
  listPlatformExecutionTasks,
  listPlatformActionExecutors,
  listRunRecords,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  publishPlatformDraft,
  removeRagTeamMember,
  retryPlatformExecutionTask,
  revokeDocumentGrant,
  sendPublicLLMChatStream,
  sendChatStream,
  uploadDocument,
  listRagDocuments,
  listRagTeamMembers,
  listRagTeams,
  listApprovals,
  listAuditLogs,
  listRefunds,
  listUsers,
  getThreadMessages,
  getRunRecordDetail,
  listConnectors,
  listAutomationFlows,
  listAutomationFlowVersionEvidence,
  listAutomationFlowVersions,
  listAiWorkflows,
  listThreads,
  preflightAutomationFlowVersion,
  publishAutomationFlowVersion,
  queryErp,
  processCustomerServiceMessage,
  rollbackAutomationFlowPublication,
  runRagEvaluation,
  runAiWorkflow,
  submitAutomationFlowVersionReview,
  updateUserAiAppPermission,
  updateAutomationFlowVersion,
  updatePlatformActionExecutor,
  updateDocumentAccess,
  updateMyPassword,
  updateMyProfile,
  updateRagTeam,
  updateThreadTitle,
  reviewApproval as reviewApprovalApi,
  reviewPlatformDraft,
  type ChatAttachment,
  type AiWorkflowDetailResponse,
  type AiWorkflowItem,
  type AiWorkflowRunResponse,
  type AiWorkflowRunStep,
  type ApprovalItem,
  type AuditLogItem,
  type AutomationFlowDetailResponse,
  type AutomationFlowItem,
  type BusinessActionLoopItem,
  type BusinessActionLoopResponse,
  type ConnectorConfigField,
  type ConnectorDetailResponse,
  type ConnectorItem,
  type ConnectorsResponse,
  type CustomerServiceMessageCreatePayload,
  type CustomerServiceMessageDetailResponse,
  type CustomerServiceMessageItem,
  type CustomerServiceProcessResponse,
  type DocumentAccessItem,
  type DocumentGrantItem,
  type DocumentUploadAccessPayload,
  type EffectAnalyticsResponse,
  type EvaluationCenterResponse,
  type MonitoringCenterResponse,
  type AutomationTaskItem,
  type GeneratedFileFilters,
  type GeneratedFileItem,
  type AutomationFlowVersionCreatePayload,
  type AutomationFlowVerificationEvidence,
  type AutomationFlowVerificationEvidenceListResponse,
  type AutomationFlowVersionPreflightResponse,
  type AutomationFlowStepItem,
  type AutomationFlowVersionSummary,
  type AutomationFlowVersionUpdatePayload,
  type FeedbackCategory,
  type FeedbackItem,
  type FeedbackPriority,
  type FeedbackSummary,
  type ErpDashboardOverviewResponse,
  type ErpDiagnosticsResponse,
  type ErpQueryResponse,
  type ErpRecordDetailResponse,
  type ErpReference,
  type ErpResourceItem,
  type ErpStatusResponse,
  type Position,
  type PublicLLMMessage,
  type RagDocumentAccessMode,
  type RagGrantAccessLevel,
  type RagGrantSubjectType,
  type RagMarketScope,
  type RagStoreScope,
  type RagTeamItem,
  type RagTeamMemberItem,
  type RagTeamMemberRole,
  type RagTeamStatus,
  type PlatformDraftItem,
  type PlatformActionExecutionItem,
  type PlatformDraftDetailResponse,
  type PlatformDraftStatus,
  type PlatformExecutionTaskItem,
  type PlatformExecutionTaskStatus,
  type PlatformActionExecutorItem,
  type PlatformActionExecutorOption,
  type PlatformActionExecutorPayload,
  type PlatformActionExecutorsResponse,
  type NotificationItem,
  type NotificationStatus,
  type RefundItem,
  type RunRecordDetailResponse,
  type RunRecordFilters,
  type RunRecordItem,
  type ThreadMessageItem,
  type ThreadListItem,
  type UserCreatePayload,
  type UserAiAppPermissionItem,
  type UserItem,
  type UserSettingsItem,
} from "./api";
import { Contact } from "./portal/components/Contact";
import { Hero } from "./portal/components/Hero";
import { Navbar } from "./portal/components/Navbar";
import { Projects } from "./portal/components/Projects";
import { Skills } from "./portal/components/Skills";
import type { Language } from "./portal/data/content";

const { Paragraph, Text, Title } = Typography;
const { TextArea } = Input;

type Role = "admin" | "employee";
type ChatRoute = "refund_workflow" | "order_agent" | "knowledge_rag" | "finance_salary_export";
type FinanceAutomationTool = "report_analysis" | "salary_export" | "excel_upload" | "reconciliation";
type View =
  | "dashboard"
  | "ai_apps"
  | "business_action_loop"
  | "platform_draft_review"
  | "platform_execution_tasks"
  | "notifications"
  | "feedback_improvement"
  | "feedback_center"
  | "file_downloads"
  | "run_records"
  | "effect_analytics"
  | "evaluation_center"
  | "monitoring_center"
  | "ai_workflows"
  | "ai_workflow_operations_listing_launch"
  | "ai_workflow_operations_competitor_analysis"
  | "ai_workflow_customer_service_refund_reply"
  | "ai_workflow_customer_service_logistics_reply"
  | "ai_workflow_customer_service_message_loop"
  | "ai_workflow_finance_report_analysis"
  | "ai_workflow_finance_salary_summary"
  | "ai_workflow_finance_excel_settlement"
  | "ai_workflow_finance_reconciliation"
  | "automation_flows"
  | "connectors"
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

type NavGroupId = `nav_group_${string}`;

type NavItemBase = {
  path: string;
  name: string;
  icon: React.ReactNode;
  roles: Role[];
  positions?: Position[];
  children?: NavItem[];
};

type NavRouteItem = NavItemBase & {
  id: View;
  type?: undefined;
  threadId?: string;
  chatAction?: "new";
};

type NavGroupItem = NavItemBase & {
  id: NavGroupId;
  children: NavItem[];
  type: "group";
};

type NavItem = NavRouteItem | NavGroupItem;

type NavigableNavItem = NavItem & {
  id: View;
  type?: undefined;
  threadId?: string;
  chatAction?: "new";
};

type ChatMessage = {
  id: string;
  threadId: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: string;
  route?: ChatRoute;
  erpReferences?: ErpReference[];
  attachments?: ChatAttachment[];
  platformDraft?: PlatformDraftItem | null;
};

type PublicLLMChatMessage = PublicLLMMessage & {
  id: string;
};

type Approval = {
  id: string;
  threadId: string;
  actionType: string;
  actionLabel: string;
  status: string;
  orderNo: string;
  amount: string;
  reason: string;
  summary: string;
  createdAt: string;
};

type Refund = {
  id: string;
  approvalId: string;
  orderNo: string;
  amount: string;
  status: string;
  createdAt: string;
};

type AuditLog = {
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

type UserRecord = {
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

type AutomationTaskRecord = AutomationTaskItem & {
  inputText: string;
  output: string;
  platformDraft: PlatformDraftItem | null;
};

type NewUserForm = {
  username: string;
  password: string;
  role: Role;
  position: Position | null;
  department: string;
};

type AiAppRecord = {
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

type RunRecordFilterState = {
  status: "all" | "running" | "succeeded" | "failed" | "blocked";
  runType: string;
  appId: string;
  position: Position | "all";
  resourceType: string;
  resourceId: string;
  flowKey: string;
};

type GeneratedFileFilterState = {
  search: string;
  dateRange: "today" | "7d" | "30d" | "all";
  fileType: "all" | "excel" | "word";
};

type PlatformDraftFilterState = {
  draftType: "all" | "listing" | "customer_reply";
  status: "all" | PlatformDraftStatus;
};

type PlatformExecutionTaskFilterState = {
  status: "all" | PlatformExecutionTaskStatus;
};

type NotificationFilterState = {
  status: "all" | NotificationStatus;
};

type FeedbackFilterState = {
  status: "all" | "open" | "completed";
};

type FeedbackFormState = {
  category: FeedbackCategory;
  priority: FeedbackPriority;
  title: string;
  description: string;
};

type PlatformActionExecutorFormState = {
  id: string | null;
  name: string;
  executorType: string;
  actionTypes: string[];
  webhookUrl: string;
  apiKey: string;
  timeoutSeconds: number;
  enabled: boolean;
};

type EffectAnalyticsFilterState = {
  dateRange: "7d" | "30d" | "90d" | "all";
  position: Position | "all";
};

type AutomationFlowFilterState = {
  position: Position | "all";
  category: string;
};

type AutomationFlowVersionFormState = {
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

type AiWorkflowFilterState = {
  position: Position | "all";
  category: string;
};

type CustomerServiceInboxForm = {
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

type CustomerServiceInboxFilters = {
  status: string;
  riskLevel: string;
};

type UserProfileFormState = {
  displayName: string;
  email: string;
};

type UserPasswordFormState = {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
};

type MonitoringCenterFilterState = {
  dateRange: "7d" | "30d" | "90d" | "all";
};

type DashboardMarket = string;
type DashboardDateRange = "all" | "today" | "7d" | "30d";
type DashboardStore = "all" | "us_store" | "de_store" | "jp_store";
type DocumentPositionScope = Position | "all";
type DocumentMarketScope = "all" | "us" | "de" | "jp";
type DocumentStoreScope = DashboardStore;
type DocumentFieldScope =
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
type DocumentSensitivityLevel = "internal" | "confidential" | "restricted";

type RagTeamFormState = {
  teamKey: string;
  name: string;
  description: string;
  positionScope: DocumentPositionScope;
  marketScope: DocumentMarketScope;
  storeScope: DocumentStoreScope;
  status: RagTeamStatus;
};

type RagTeamMemberFormState = {
  userId: string;
  memberRole: RagTeamMemberRole;
  expiresAt: string;
};

type DocumentAccessFormState = {
  accessMode: RagDocumentAccessMode;
  ownerUserId: string;
  ownerTeamId: string;
};

type DocumentGrantFormState = {
  subjectType: RagGrantSubjectType;
  subjectId: string;
  accessLevel: RagGrantAccessLevel;
  reason: string;
  expiresAt: string;
};

const positionConfigs: Record<Position, { label: string; department: string; capabilities: string[]; erpScopes: string[] }> = {
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

const aiWorkflowNavItems: NavItem[] = [
  {
    path: "/ai-workflows/operations-listing-launch",
    id: "ai_workflow_operations_listing_launch",
    name: "运营 Listing 上架准备",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/ai-workflows/operations-competitor-analysis",
    id: "ai_workflow_operations_competitor_analysis",
    name: "运营竞品分析",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/ai-workflows/customer-service-refund-reply",
    id: "ai_workflow_customer_service_refund_reply",
    name: "客服退款售后处理",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/ai-workflows/customer-service-logistics-reply",
    id: "ai_workflow_customer_service_logistics_reply",
    name: "客服物流查询回复",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/ai-workflows/customer-service-message-loop",
    id: "ai_workflow_customer_service_message_loop",
    name: "客服消息自动化闭环",
    icon: <CommentOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/ai-workflows/finance-report-analysis",
    id: "ai_workflow_finance_report_analysis",
    name: "财务报表分析",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/ai-workflows/finance-salary-summary",
    id: "ai_workflow_finance_salary_summary",
    name: "财务工资统计",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/ai-workflows/finance-excel-settlement",
    id: "ai_workflow_finance_excel_settlement",
    name: "财务 Excel 生成",
    icon: <CloudUploadOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/ai-workflows/finance-reconciliation",
    id: "ai_workflow_finance_reconciliation",
    name: "财务对账自动化",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
];

const automationOperationsNavItems: NavItem[] = [
  {
    path: "/automation/operations/listing",
    id: "automation_operations_listing",
    name: "生成 Listing",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/automation/operations/title",
    id: "automation_operations_title",
    name: "生成标题",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/automation/operations/bullets",
    id: "automation_operations_bullets",
    name: "生成五点描述",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/automation/operations/keywords",
    id: "automation_operations_keywords",
    name: "生成关键词",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/automation/operations/promo-copy",
    id: "automation_operations_promo_copy",
    name: "生成促销文案",
    icon: <RobotOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
  {
    path: "/automation/operations/competitor-analysis",
    id: "automation_operations_competitor_analysis",
    name: "竞品分析",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["operations"],
  },
];

const automationCustomerServiceNavItems: NavItem[] = [
  {
    path: "/automation/customer-service/smart-reply",
    id: "automation_customer_service_smart_reply",
    name: "智能客服",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/automation/customer-service/auto-reply",
    id: "automation_customer_service_auto_reply",
    name: "自动回复",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/automation/customer-service/refund-script",
    id: "automation_customer_service_refund_script",
    name: "退款售后话术",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
  {
    path: "/automation/customer-service/multilingual-translation",
    id: "automation_customer_service_multilingual_translation",
    name: "多语言客服翻译",
    icon: <MessageOutlined />,
    roles: ["admin", "employee"],
    positions: ["customer_service"],
  },
];

const automationFinanceNavItems: NavItem[] = [
  {
    path: "/automation/finance/report-analysis",
    id: "automation_finance_report_analysis",
    name: "分析财务报表",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/automation/finance/salary-summary",
    id: "automation_finance_salary_summary",
    name: "统计工资",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/automation/finance/excel-transform",
    id: "automation_finance_excel_transform",
    name: "Excel 生成",
    icon: <CloudUploadOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
  {
    path: "/automation/finance/reconciliation",
    id: "automation_finance_reconciliation",
    name: "财务对账自动化",
    icon: <AuditOutlined />,
    roles: ["admin", "employee"],
    positions: ["finance"],
  },
];

function navGroup(id: string, name: string, children: NavItem[]): NavGroupItem {
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

const navItems: NavItem[] = [
  navGroup("home", "首页", [
    { path: "/dashboard", id: "dashboard", name: "概览", icon: <DatabaseOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("account", "账户", [
    { path: "/settings", id: "user_settings", name: "用户设置", icon: <EditOutlined />, roles: ["admin", "employee"] },
    { path: "/users", id: "users", name: "用户管理", icon: <SafetyCertificateOutlined />, roles: ["admin"] },
    { path: "/notifications", id: "notifications", name: "通知中心", icon: <BellOutlined />, roles: ["admin", "employee"] },
  ]),
  navGroup("ai-workbench", "AI 工作台", [
    { path: "/ai-apps", id: "ai_apps", name: "AI 应用中心", icon: <AppstoreOutlined />, roles: ["admin", "employee"] },
    {
      path: "/automation",
      id: "automation",
      name: "岗位应用",
      icon: <RobotOutlined />,
      roles: ["admin", "employee"],
      children: [
        {
          path: "/automation/operations",
          id: "automation_operations",
          name: "运营 AI 自动化",
          icon: <RobotOutlined />,
          roles: ["admin", "employee"],
          positions: ["operations"],
          children: automationOperationsNavItems,
        },
        {
          path: "/automation/customer-service",
          id: "automation_customer_service",
          name: "客服 AI 自动化",
          icon: <MessageOutlined />,
          roles: ["admin", "employee"],
          positions: ["customer_service"],
          children: automationCustomerServiceNavItems,
        },
        {
          path: "/automation/finance",
          id: "automation_finance",
          name: "财务 AI 自动化",
          icon: <CloudUploadOutlined />,
          roles: ["admin", "employee"],
          positions: ["finance"],
          children: automationFinanceNavItems,
        },
      ],
    },
    {
      path: "/ai-workflows",
      id: "ai_workflows",
      name: "AI 工作流",
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
    { path: "/platform-action-executors", id: "platform_action_executors", name: "外部执行器配置", icon: <ApiOutlined />, roles: ["admin"] },
    { path: "/audit", id: "audit", name: "审计日志", icon: <AuditOutlined />, roles: ["admin"] },
  ]),
  navGroup("other", "其他", [
    { path: "/feedback", id: "feedback_improvement", name: "反馈改进", icon: <CommentOutlined />, roles: ["employee"] },
    { path: "/feedback-center", id: "feedback_center", name: "反馈中心", icon: <CommentOutlined />, roles: ["admin"] },
  ]),
];

const fallbackDashboardMarketOptions: Array<{ label: string; value: DashboardMarket }> = [
  { label: "全部站点", value: "all" },
  { label: "美国站", value: "us" },
  { label: "德国站", value: "de" },
  { label: "日本站", value: "jp" },
];

const documentMarketScopeOptions: Array<{ label: string; value: DocumentMarketScope }> = [
  { label: "不限站点", value: "all" },
  { label: "美国站", value: "us" },
  { label: "德国站", value: "de" },
  { label: "日本站", value: "jp" },
];

const dashboardDateRangeOptions: Array<{ label: string; value: DashboardDateRange }> = [
  { label: "全部时间", value: "all" },
  { label: "今天", value: "today" },
  { label: "近7天", value: "7d" },
  { label: "近30天", value: "30d" },
];

const dashboardStoreOptions: Array<{ label: string; value: DashboardStore }> = [
  { label: "全部店铺", value: "all" },
  { label: "US Store", value: "us_store" },
  { label: "DE Store", value: "de_store" },
  { label: "JP Store", value: "jp_store" },
];

const documentStoreScopeOptions: Array<{ label: string; value: DocumentStoreScope }> = [
  { label: "不限店铺", value: "all" },
  { label: "US Store", value: "us_store" },
  { label: "DE Store", value: "de_store" },
  { label: "JP Store", value: "jp_store" },
];

const documentFieldScopeOptions: Array<{ label: string; value: DocumentFieldScope }> = [
  { label: "不限字段", value: "all" },
  { label: "运营 Listing", value: "operations_listing" },
  { label: "运营库存", value: "operations_inventory" },
  { label: "运营销售", value: "operations_sales" },
  { label: "客服客户资料", value: "customer_profile" },
  { label: "客服物流", value: "customer_logistics" },
  { label: "客服售后", value: "customer_after_sales" },
  { label: "财务发票", value: "finance_invoice" },
  { label: "财务收付款", value: "finance_payment" },
  { label: "财务利润", value: "finance_profit" },
  { label: "财务工资", value: "finance_salary" },
];

const documentSensitivityLevelOptions: Array<{ label: string; value: DocumentSensitivityLevel }> = [
  { label: "内部", value: "internal" },
  { label: "保密", value: "confidential" },
  { label: "受限", value: "restricted" },
];

const ragTeamStatusLabels: Record<RagTeamStatus, string> = {
  active: "启用",
  paused: "暂停",
  archived: "归档",
};

const ragTeamStatusColors: Record<RagTeamStatus, string> = {
  active: "green",
  paused: "gold",
  archived: "default",
};

const ragTeamStatusOptions: Array<{ label: string; value: RagTeamStatus }> = [
  { label: "启用", value: "active" },
  { label: "暂停", value: "paused" },
  { label: "归档", value: "archived" },
];

const ragTeamMemberRoleLabels: Record<RagTeamMemberRole, string> = {
  member: "成员",
  supervisor: "主管",
  auditor: "审计",
};

const ragTeamMemberRoleOptions: Array<{ label: string; value: RagTeamMemberRole }> = [
  { label: "成员", value: "member" },
  { label: "主管", value: "supervisor" },
  { label: "审计", value: "auditor" },
];

const ragDocumentAccessModeLabels: Record<RagDocumentAccessMode, string> = {
  open: "开放",
  owner_only: "仅归属人",
  team_only: "仅归属团队",
  explicit_grants: "显式授权",
  owner_and_grants: "归属与授权",
};

const ragDocumentAccessModeOptions: Array<{ label: string; value: RagDocumentAccessMode }> = [
  { label: "开放", value: "open" },
  { label: "仅归属人", value: "owner_only" },
  { label: "仅归属团队", value: "team_only" },
  { label: "显式授权", value: "explicit_grants" },
  { label: "归属与授权", value: "owner_and_grants" },
];

const ragGrantSubjectTypeOptions: Array<{ label: string; value: RagGrantSubjectType }> = [
  { label: "用户", value: "user" },
  { label: "团队", value: "team" },
];

const ragGrantAccessLevelLabels: Record<RagGrantAccessLevel, string> = {
  read: "读取",
  manage: "管理",
};

const ragGrantAccessLevelOptions: Array<{ label: string; value: RagGrantAccessLevel }> = [
  { label: "读取", value: "read" },
  { label: "管理", value: "manage" },
];

const feedbackCategoryOptions: Array<{ label: FeedbackCategory; value: FeedbackCategory }> = [
  { label: "功能建议", value: "功能建议" },
  { label: "体验问题", value: "体验问题" },
  { label: "数据问题", value: "数据问题" },
  { label: "自动化需求", value: "自动化需求" },
  { label: "权限流程", value: "权限流程" },
  { label: "其他", value: "其他" },
];

const feedbackPriorityOptions: Array<{ label: string; value: FeedbackPriority }> = [
  { label: "普通", value: "normal" },
  { label: "较低", value: "low" },
  { label: "较高", value: "high" },
  { label: "紧急", value: "urgent" },
];

const auditActionLabels: Record<string, string> = {
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

const auditResourceTypeLabels: Record<string, string> = {
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

const auditActionWordLabels: Record<string, string> = {
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

const aiWorkflowViewMap: Partial<Record<View, string>> = {
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

const workflowSourceTaskIdMap: Record<string, string> = {
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

const workflowIdViewMap: Record<string, View> = Object.fromEntries(
  Object.entries(aiWorkflowViewMap).map(([view, workflowId]) => [workflowId, view as View]),
) as Record<string, View>;

const automationTaskViewMap: Partial<Record<View, string>> = {
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

const automationTaskIdViewMap: Record<string, View> = {
  operations: "automation_operations",
  "operations:listing": "automation_operations_listing",
  "operations:title": "automation_operations_title",
  "operations:bullets": "automation_operations_bullets",
  "operations:keywords": "automation_operations_keywords",
  "operations:promo_copy": "automation_operations_promo_copy",
  "operations:competitor_analysis": "automation_operations_competitor_analysis",
  customer_service: "automation_customer_service",
  "customer_service:smart_reply": "automation_customer_service_smart_reply",
  "customer_service:auto_reply": "automation_customer_service_auto_reply",
  "customer_service:refund_script": "automation_customer_service_refund_script",
  "customer_service:multilingual_translation": "automation_customer_service_multilingual_translation",
  finance: "automation_finance",
  "finance:report_analysis": "automation_finance_report_analysis",
  "finance:salary_summary": "automation_finance_salary_summary",
  "finance:excel_transform": "automation_finance_excel_transform",
};

const automationFinanceToolViewMap: Partial<Record<View, FinanceAutomationTool>> = {
  automation_finance_report_analysis: "report_analysis",
  automation_finance_salary_summary: "salary_export",
  automation_finance_excel_transform: "excel_upload",
  automation_finance_excel_upload: "excel_upload",
  automation_finance_reconciliation: "reconciliation",
};

function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [activeView, setActiveView] = useState<View>(() => viewFromPath(window.location.pathname));
  const [role, setRole] = useState<Role>(readStoredRole);
  const [position, setPosition] = useState<Position | null>(readStoredPosition);
  const [allowedAiAppIds, setAllowedAiAppIds] = useState<string[] | null>(readStoredAllowedAiAppIds);
  const [username, setUsername] = useState(localStorage.getItem("username") ?? "");
  const [displayName, setDisplayName] = useState(localStorage.getItem("display_name") ?? "");
  const [userEmail, setUserEmail] = useState(localStorage.getItem("user_email") ?? "");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("access_token") ?? "");
  const [statusMessage, setStatusMessage] = useState("系统就绪");
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isLoginErrorOpen, setIsLoginErrorOpen] = useState(false);
  const [isSessionExpiredOpen, setIsSessionExpiredOpen] = useState(false);
  const [isPublicLLMOpen, setIsPublicLLMOpen] = useState(false);
  const [lastForbiddenPath, setLastForbiddenPath] = useState("");
  const [publicLLMInput, setPublicLLMInput] = useState("");
  const [publicLLMMessages, setPublicLLMMessages] = useState<PublicLLMChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好，有什么可以帮你的？",
    },
  ]);
  const [isPublicLLMLoading, setIsPublicLLMLoading] = useState(false);

  const [messageInput, setMessageInput] = useState("");
  const [activeThreadId, setActiveThreadId] = useState("");
  const [chatThreads, setChatThreads] = useState<ThreadListItem[]>([]);
  const [threadSearch, setThreadSearch] = useState("");
  const [threadRetentionDays, setThreadRetentionDays] = useState(15);
  const [isThreadListLoading, setIsThreadListLoading] = useState(false);
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [isRenamingThread, setIsRenamingThread] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditActionFilter, setAuditActionFilter] = useState("");
  const [auditResourceFilter, setAuditResourceFilter] = useState("");
  const [auditPositionFilter, setAuditPositionFilter] = useState<Position | "all">("all");
  const [runRecords, setRunRecords] = useState<RunRecordItem[]>([]);
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileItem[]>([]);
  const [generatedFileFilters, setGeneratedFileFilters] = useState<GeneratedFileFilterState>({
    search: "",
    dateRange: "30d",
    fileType: "all",
  });
  const [isGeneratedFilesLoading, setIsGeneratedFilesLoading] = useState(false);
  const [userSettings, setUserSettings] = useState<UserSettingsItem | null>(null);
  const [profileForm, setProfileForm] = useState<UserProfileFormState>({
    displayName: localStorage.getItem("display_name") ?? "",
    email: localStorage.getItem("user_email") ?? "",
  });
  const [passwordForm, setPasswordForm] = useState<UserPasswordFormState>({
    oldPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [isLoadingUserSettings, setIsLoadingUserSettings] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [downloadingFileId, setDownloadingFileId] = useState("");
  const [runRecordFilters, setRunRecordFilters] = useState<RunRecordFilterState>({
    status: "all",
    runType: "",
    appId: "",
    position: "all",
    resourceType: "",
    resourceId: "",
    flowKey: "",
  });
  const [runRecordDetail, setRunRecordDetail] = useState<RunRecordDetailResponse | null>(null);
  const [isRunRecordDetailOpen, setIsRunRecordDetailOpen] = useState(false);
  const [isRunRecordDetailLoading, setIsRunRecordDetailLoading] = useState(false);
  const [isRunRecordsLoading, setIsRunRecordsLoading] = useState(false);
  const [effectAnalytics, setEffectAnalytics] = useState<EffectAnalyticsResponse | null>(null);
  const [effectAnalyticsFilters, setEffectAnalyticsFilters] = useState<EffectAnalyticsFilterState>({
    dateRange: "30d",
    position: "all",
  });
  const [isEffectAnalyticsLoading, setIsEffectAnalyticsLoading] = useState(false);
  const [evaluationCenter, setEvaluationCenter] = useState<EvaluationCenterResponse | null>(null);
  const [isEvaluationCenterLoading, setIsEvaluationCenterLoading] = useState(false);
  const [runningEvaluationId, setRunningEvaluationId] = useState("");
  const [monitoringCenter, setMonitoringCenter] = useState<MonitoringCenterResponse | null>(null);
  const [monitoringCenterFilters, setMonitoringCenterFilters] = useState<MonitoringCenterFilterState>({
    dateRange: "30d",
  });
  const [isMonitoringCenterLoading, setIsMonitoringCenterLoading] = useState(false);
  const [aiWorkflows, setAiWorkflows] = useState<AiWorkflowItem[]>([]);
  const [aiWorkflowFilters, setAiWorkflowFilters] = useState<AiWorkflowFilterState>({
    position: "all",
    category: "",
  });
  const [aiWorkflowInputs, setAiWorkflowInputs] = useState<Record<string, string>>({});
  const [aiWorkflowRunResult, setAiWorkflowRunResult] = useState<AiWorkflowRunResponse | null>(null);
  const [aiWorkflowDetail, setAiWorkflowDetail] = useState<AiWorkflowDetailResponse | null>(null);
  const [isAiWorkflowDetailOpen, setIsAiWorkflowDetailOpen] = useState(false);
  const [isAiWorkflowDetailLoading, setIsAiWorkflowDetailLoading] = useState(false);
  const [isAiWorkflowsLoading, setIsAiWorkflowsLoading] = useState(false);
  const [runningAiWorkflowId, setRunningAiWorkflowId] = useState("");
  const [platformDrafts, setPlatformDrafts] = useState<PlatformDraftItem[]>([]);
  const [platformDraftFilters, setPlatformDraftFilters] = useState<PlatformDraftFilterState>({
    draftType: "all",
    status: "all",
  });
  const [platformDraftDetail, setPlatformDraftDetail] = useState<PlatformDraftDetailResponse | null>(null);
  const [isPlatformDraftsLoading, setIsPlatformDraftsLoading] = useState(false);
  const [isPlatformDraftDetailOpen, setIsPlatformDraftDetailOpen] = useState(false);
  const [isPlatformDraftDetailLoading, setIsPlatformDraftDetailLoading] = useState(false);
  const [platformDraftActionKey, setPlatformDraftActionKey] = useState("");
  const [platformDraftReviewComment, setPlatformDraftReviewComment] = useState("");
  const [businessActionLoop, setBusinessActionLoop] = useState<BusinessActionLoopResponse | null>(null);
  const [isBusinessActionLoopLoading, setIsBusinessActionLoopLoading] = useState(false);
  const [platformExecutionTasks, setPlatformExecutionTasks] = useState<PlatformExecutionTaskItem[]>([]);
  const [platformExecutionTaskFilters, setPlatformExecutionTaskFilters] = useState<PlatformExecutionTaskFilterState>({
    status: "all",
  });
  const [platformExecutionTaskDetail, setPlatformExecutionTaskDetail] = useState<PlatformExecutionTaskItem | null>(null);
  const [isPlatformExecutionTasksLoading, setIsPlatformExecutionTasksLoading] = useState(false);
  const [isPlatformExecutionTaskDetailOpen, setIsPlatformExecutionTaskDetailOpen] = useState(false);
  const [isPlatformExecutionTaskDetailLoading, setIsPlatformExecutionTaskDetailLoading] = useState(false);
  const [retryingPlatformExecutionTaskId, setRetryingPlatformExecutionTaskId] = useState("");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationFilters, setNotificationFilters] = useState<NotificationFilterState>({
    status: "all",
  });
  const [isNotificationsLoading, setIsNotificationsLoading] = useState(false);
  const [markingNotificationId, setMarkingNotificationId] = useState("");
  const [isMarkingAllNotificationsRead, setIsMarkingAllNotificationsRead] = useState(false);
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>([]);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummary>({
    total: 0,
    open: 0,
    completed: 0,
  });
  const [feedbackFilters, setFeedbackFilters] = useState<FeedbackFilterState>({
    status: "all",
  });
  const [feedbackForm, setFeedbackForm] = useState<FeedbackFormState>({
    category: "功能建议",
    priority: "normal",
    title: "",
    description: "",
  });
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [completingFeedbackId, setCompletingFeedbackId] = useState("");
  const [automationFlows, setAutomationFlows] = useState<AutomationFlowItem[]>([]);
  const [automationFlowFilters, setAutomationFlowFilters] = useState<AutomationFlowFilterState>({
    position: "all",
    category: "",
  });
  const [automationFlowDetail, setAutomationFlowDetail] = useState<AutomationFlowDetailResponse | null>(null);
  const [isAutomationFlowDetailOpen, setIsAutomationFlowDetailOpen] = useState(false);
  const [isAutomationFlowDetailLoading, setIsAutomationFlowDetailLoading] = useState(false);
  const [isAutomationFlowsLoading, setIsAutomationFlowsLoading] = useState(false);
  const [customerMessages, setCustomerMessages] = useState<CustomerServiceMessageItem[]>([]);
  const [customerMessageDetail, setCustomerMessageDetail] = useState<CustomerServiceMessageDetailResponse | null>(null);
  const [customerProcessResult, setCustomerProcessResult] = useState<CustomerServiceProcessResponse | null>(null);
  const [customerInboxFilters, setCustomerInboxFilters] = useState<CustomerServiceInboxFilters>({
    status: "all",
    riskLevel: "all",
  });
  const [customerInboxForm, setCustomerInboxForm] = useState<CustomerServiceInboxForm>({
    channel: "manual",
    buyerName: "",
    buyerEmail: "",
    buyerLanguage: "auto",
    marketplace: "Amazon US",
    orderNo: "",
    trackingNo: "",
    sku: "",
    subject: "",
    message: "Where is my order? My order number is AMZ-US-001.",
  });
  const [isCustomerInboxLoading, setIsCustomerInboxLoading] = useState(false);
  const [isCreatingCustomerMessage, setIsCreatingCustomerMessage] = useState(false);
  const [processingCustomerMessageId, setProcessingCustomerMessageId] = useState("");
  const [connectors, setConnectors] = useState<ConnectorItem[]>([]);
  const [connectorSummary, setConnectorSummary] = useState<ConnectorsResponse["summary"] | null>(null);
  const [connectorDetail, setConnectorDetail] = useState<ConnectorDetailResponse | null>(null);
  const [isConnectorDetailOpen, setIsConnectorDetailOpen] = useState(false);
  const [isConnectorDetailLoading, setIsConnectorDetailLoading] = useState(false);
  const [isConnectorsLoading, setIsConnectorsLoading] = useState(false);
  const [platformActionExecutors, setPlatformActionExecutors] = useState<PlatformActionExecutorItem[]>([]);
  const [platformActionExecutorSummary, setPlatformActionExecutorSummary] = useState<PlatformActionExecutorsResponse["summary"] | null>(null);
  const [platformActionExecutorActionOptions, setPlatformActionExecutorActionOptions] = useState<PlatformActionExecutorOption[]>([]);
  const [platformActionExecutorTypeOptions, setPlatformActionExecutorTypeOptions] = useState<PlatformActionExecutorOption[]>([]);
  const [platformActionExecutorForm, setPlatformActionExecutorForm] = useState<PlatformActionExecutorFormState>({
    id: null,
    name: "",
    executorType: "webhook",
    actionTypes: [],
    webhookUrl: "",
    apiKey: "",
    timeoutSeconds: 12,
    enabled: true,
  });
  const [isPlatformActionExecutorsLoading, setIsPlatformActionExecutorsLoading] = useState(false);
  const [isSavingPlatformActionExecutor, setIsSavingPlatformActionExecutor] = useState(false);
  const [checkingPlatformActionExecutorId, setCheckingPlatformActionExecutorId] = useState("");
  const [deletingPlatformActionExecutorId, setDeletingPlatformActionExecutorId] = useState("");
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [automationTasks, setAutomationTasks] = useState<AutomationTaskRecord[]>([]);
  const [erpResources, setErpResources] = useState<ErpResourceItem[]>([]);
  const [erpStatus, setErpStatus] = useState<ErpStatusResponse | null>(null);
  const [erpDiagnostics, setErpDiagnostics] = useState<ErpDiagnosticsResponse | null>(null);
  const [erpDashboardOverview, setErpDashboardOverview] = useState<ErpDashboardOverviewResponse | null>(null);
  const [erpDashboardMarket, setErpDashboardMarket] = useState<DashboardMarket>("all");
  const [erpDashboardDateRange, setErpDashboardDateRange] = useState<DashboardDateRange>("all");
  const [erpDashboardStore, setErpDashboardStore] = useState<DashboardStore>("all");
  const [erpRecordDetail, setErpRecordDetail] = useState<ErpRecordDetailResponse | null>(null);
  const [isErpRecordDetailOpen, setIsErpRecordDetailOpen] = useState(false);
  const [isErpRecordDetailLoading, setIsErpRecordDetailLoading] = useState(false);
  const [selectedErpResource, setSelectedErpResource] = useState("");
  const [erpQueryText, setErpQueryText] = useState("");
  const [erpFiltersText, setErpFiltersText] = useState("{}");
  const [erpLimit, setErpLimit] = useState(10);
  const [erpQueryResult, setErpQueryResult] = useState<ErpQueryResponse | null>(null);
  const [isErpLoading, setIsErpLoading] = useState(false);
  const [newUser, setNewUser] = useState<NewUserForm>({
    username: "",
    password: "",
    role: "employee",
    position: "customer_service",
    department: "",
  });
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [updatingUserAppKey, setUpdatingUserAppKey] = useState("");
  const [deletingUserId, setDeletingUserId] = useState("");
  const [automationLoadingTaskId, setAutomationLoadingTaskId] = useState("");
  const [financeReportFiles, setFinanceReportFiles] = useState<File[]>([]);
  const [financeReportInstruction, setFinanceReportInstruction] = useState(
    "请分析上传的财务报表，输出摘要、关键指标、异常项、风险和下一步复核建议。",
  );
  const [financeReportOutputFormat, setFinanceReportOutputFormat] = useState<"word" | "excel">("word");
  const [isAnalyzingFinanceReport, setIsAnalyzingFinanceReport] = useState(false);
  const [financeReportSummary, setFinanceReportSummary] = useState("");
  const [financeExcelFile, setFinanceExcelFile] = useState<File | null>(null);
  const [financeExcelInstruction, setFinanceExcelInstruction] = useState(
    "根据本月销售发票和收付款单生成收款核对表，按客户/店铺汇总金额并标记未收款、金额不一致等异常。",
  );
  const [financeExcelErpResources, setFinanceExcelErpResources] = useState<string[]>([]);
  const [isTransformingFinanceExcel, setIsTransformingFinanceExcel] = useState(false);
  const [financeSalaryMessage, setFinanceSalaryMessage] = useState("把这个月所有员工的工资表发我");
  const [financeSalaryExportSummary, setFinanceSalaryExportSummary] = useState("");
  const [isExportingFinanceSalary, setIsExportingFinanceSalary] = useState(false);
  const [financeReconciliationFiles, setFinanceReconciliationFiles] = useState<File[]>([]);
  const [financeReconciliationInstruction, setFinanceReconciliationInstruction] = useState(
    "请按订单号和 SKU 匹配 Amazon 结算表、物流账单、采购成本表、广告费表和汇率表，生成订单利润表并标记异常账单。",
  );
  const [financeReconciliationCurrency, setFinanceReconciliationCurrency] = useState("CNY");
  const [isReconcilingFinance, setIsReconcilingFinance] = useState(false);

  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentVisibility, setDocumentVisibility] = useState<Role>("employee");
  const [documentDepartment, setDocumentDepartment] = useState("");
  const [documentPositionScope, setDocumentPositionScope] = useState<DocumentPositionScope>("all");
  const [documentMarketScope, setDocumentMarketScope] = useState<DocumentMarketScope>("all");
  const [documentStoreScope, setDocumentStoreScope] = useState<DocumentStoreScope>("all");
  const [documentFieldScope, setDocumentFieldScope] = useState<DocumentFieldScope>("all");
  const [documentSensitivityLevel, setDocumentSensitivityLevel] = useState<DocumentSensitivityLevel>("internal");
  const [isUploading, setIsUploading] = useState(false);

  const [threadSummary, setThreadSummary] = useState("");
  const [threadStateText, setThreadStateText] = useState("");

  const pendingCount = canUseApprovalCenter(role, position)
    ? approvals.filter((item) => item.status === "pending").length
    : 0;
  const baseVisibleNavItems = useMemo(
    () => visibleNavigationForUser(role, position, allowedAiAppIds),
    [allowedAiAppIds, position, role],
  );
  const visibleNavItems = useMemo(
    () => withChatThreadNavigation(baseVisibleNavItems, chatThreads, role),
    [baseVisibleNavItems, chatThreads, role],
  );
  const flatVisibleNavItems = useMemo(
    () => flattenNavigableNavItems(visibleNavItems),
    [visibleNavItems],
  );
  const route = useMemo(
    () => ({
      path: "/",
      routes: visibleNavItems,
    }),
    [visibleNavItems],
  );
  const safeActiveView = flatVisibleNavItems.some((item) => item.id === activeView) ? activeView : "dashboard";
  const currentPath = safeActiveView === "chat"
    ? window.location.pathname
    : flatVisibleNavItems.find((item) => item.id === safeActiveView)?.path || "/dashboard";

  useEffect(() => {
    function handlePopState() {
      setActiveView(viewFromPath(window.location.pathname));
      const threadIdFromPath = threadIdFromPathname(window.location.pathname);
      if (threadIdFromPath) {
        setActiveThreadId(threadIdFromPath);
        void openChatThread(threadIdFromPath, { silent: true, replacePath: true });
      }
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    function handleAuthExpired(event: Event) {
      const detail = event instanceof CustomEvent ? event.detail : null;
      const text = typeof detail?.message === "string" && detail.message
        ? detail.message
        : "登录失效，需要重新登录";

      clearAuthenticatedState({ publicHome: true });
      setStatusMessage(text);
      setIsSessionExpiredOpen(true);
    }

    window.addEventListener("company-rag-auth-expired", handleAuthExpired);
    return () => window.removeEventListener("company-rag-auth-expired", handleAuthExpired);
  }, []);

  useEffect(() => {
    if (!flatVisibleNavItems.some((item) => item.id === activeView)) {
      const forbiddenPath = window.location.pathname;
      if (forbiddenPath !== lastForbiddenPath) {
        const text = "当前账号没有权限访问该页面，已返回概览。";
        setLastForbiddenPath(forbiddenPath);
        setStatusMessage(text);
        message.warning(text);
      }
      navigateToView("dashboard", { replace: true });
    }
  }, [activeView, flatVisibleNavItems, lastForbiddenPath]);

  useEffect(() => {
    if (!isErpView(safeActiveView) && statusMessage.startsWith("ERP 查询")) {
      setStatusMessage("系统就绪");
    }
  }, [safeActiveView, statusMessage]);

  useEffect(() => {
    if (!token) {
      return;
    }

    if (safeActiveView === "platform_execution_tasks") {
      void refreshPlatformExecutionTasks();
    }

    if (safeActiveView === "business_action_loop") {
      void refreshBusinessActionLoop();
    }

    if (safeActiveView === "notifications") {
      void refreshNotifications();
    }

    if (safeActiveView === "approvals") {
      void refreshApprovals();
    }

    if (safeActiveView === "feedback_improvement" || safeActiveView === "feedback_center") {
      void refreshFeedback();
    }
  }, [safeActiveView]);

  const stats = useMemo(
    () => [
      { title: "待处理反馈", value: feedbackSummary.open, suffix: "条" },
      { title: "会话消息", value: messages.length, suffix: "条" },
      { title: "审计日志", value: auditLogs.length, suffix: "条" },
    ],
    [auditLogs.length, feedbackSummary.open, messages.length],
  );

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");

    if (!storedToken) {
      return;
    }

    void refreshAutomationTasks(storedToken, position || undefined);
    void refreshErpScopes(storedToken, role);
    void refreshErpDashboardOverview(storedToken, erpDashboardMarket, erpDashboardDateRange, erpDashboardStore);
    void refreshAiWorkflows(storedToken);
    void refreshPlatformDrafts(storedToken);
    if (canUseBusinessActionLoop(role, position)) {
      void refreshBusinessActionLoop(storedToken);
    }
    if (canUsePlatformExecutionTasks(role, position)) {
      void refreshPlatformExecutionTasks(storedToken);
    }
    if (canUseApprovalCenter(role, position)) {
      void refreshApprovals(storedToken);
    } else {
      setApprovals([]);
    }
    void refreshGeneratedFiles(storedToken);
    void refreshNotifications(storedToken);
    void refreshFeedback(storedToken);
    void refreshUserSettings(storedToken);
    void refreshChatThreads(storedToken, {
      activateLatest: viewFromPath(window.location.pathname) === "chat",
      silent: true,
    });
    if (canUseCustomerServiceInbox(role, position)) {
      void refreshCustomerServiceMessages(storedToken);
    }

    if (role === "admin") {
      void refreshRunRecords(storedToken);
      void refreshEffectAnalytics(storedToken);
      void refreshAutomationFlows(storedToken);
      void refreshAdminData(storedToken);
      void refreshUsers(storedToken);
      void refreshConnectors(storedToken);
      void refreshPlatformActionExecutors(storedToken);
      void refreshEvaluationCenter(storedToken);
      void refreshMonitoringCenter(storedToken);
    }
  }, []);

  async function handleLogin() {
    try {
      setIsLoginErrorOpen(false);
      const result = await login(username, password);
      closeLoginModal();
      setIsSessionExpiredOpen(false);
      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("username", result.username || username);
      localStorage.setItem("display_name", result.display_name || "");
      localStorage.setItem("user_email", result.email || "");
      setToken(result.access_token);
      setUsername(result.username || username);
      setDisplayName(result.display_name || "");
      setUserEmail(result.email || "");
      setProfileForm({
        displayName: result.display_name || "",
        email: result.email || "",
      });

      const nextRole = result.role || readRoleFromToken(result.access_token);
      const nextPosition = result.position || readPositionFromToken(result.access_token);
      localStorage.setItem("role", nextRole);
      if (nextPosition) {
        localStorage.setItem("position", nextPosition);
      } else {
        localStorage.removeItem("position");
      }
      const nextAllowedAiAppIds = result.allowed_ai_app_ids || [];
      localStorage.setItem("allowed_ai_app_ids", JSON.stringify(nextAllowedAiAppIds));
      setRole(nextRole);
      setPosition(nextPosition);
      setAllowedAiAppIds(nextAllowedAiAppIds);
      if (!canRoleAccessView(nextRole, activeView, nextPosition, nextAllowedAiAppIds)) {
        const text = "当前账号没有权限访问该页面，已返回概览。";
        setLastForbiddenPath(window.location.pathname);
        setStatusMessage(text);
        message.warning(text);
        navigateToView("dashboard", { replace: true });
      }
      setStatusMessage(`已登录：${username}`);
      message.success("登录成功");

      if (nextRole === "admin") {
        await refreshAdminData(result.access_token);
        await refreshUsers(result.access_token);
        await refreshConnectors(result.access_token);
        await refreshPlatformActionExecutors(result.access_token);
        await refreshEvaluationCenter(result.access_token);
      await refreshMonitoringCenter(result.access_token);
      await refreshRunRecords(result.access_token);
      await refreshEffectAnalytics(result.access_token, defaultEffectAnalyticsFilters(nextRole, nextPosition));
      await refreshAutomationFlows(result.access_token, defaultAutomationFlowFilters(nextRole, nextPosition));
      } else {
        setRunRecords([]);
        setRunRecordDetail(null);
        setIsRunRecordDetailOpen(false);
        setEffectAnalytics(null);
        setAutomationFlows([]);
        setAutomationFlowDetail(null);
        setIsAutomationFlowDetailOpen(false);
      }

      await refreshAutomationTasks(result.access_token, nextPosition || undefined);
      await refreshGeneratedFiles(result.access_token);
      await refreshUserSettings(result.access_token);
      await refreshChatThreads(result.access_token, {
        activateLatest: viewFromPath(window.location.pathname) === "chat",
        silent: true,
      });
      await refreshErpScopes(result.access_token, nextRole);
      await refreshErpDashboardOverview(result.access_token, erpDashboardMarket, erpDashboardDateRange, erpDashboardStore);
      setAiWorkflowFilters(defaultAiWorkflowFilters(nextRole, nextPosition));
      await refreshAiWorkflows(result.access_token);
      await refreshPlatformDrafts(result.access_token);
      if (canUseBusinessActionLoop(nextRole, nextPosition)) {
        await refreshBusinessActionLoop(result.access_token);
      } else {
        setBusinessActionLoop(null);
      }
      if (canUsePlatformExecutionTasks(nextRole, nextPosition)) {
        await refreshPlatformExecutionTasks(result.access_token, platformExecutionTaskFilters);
      } else {
        setPlatformExecutionTasks([]);
        setPlatformExecutionTaskDetail(null);
        setIsPlatformExecutionTaskDetailOpen(false);
      }
      if (canUseApprovalCenter(nextRole, nextPosition)) {
        await refreshApprovals(result.access_token);
      } else {
        setApprovals([]);
      }
      await refreshNotifications(result.access_token);
      await refreshFeedback(result.access_token);
      if (canUseCustomerServiceInbox(nextRole, nextPosition)) {
        await refreshCustomerServiceMessages(result.access_token);
      } else {
        setCustomerMessages([]);
        setCustomerMessageDetail(null);
        setCustomerProcessResult(null);
      }
    } catch (error) {
      setPassword("");
      const rawMessage = error instanceof Error ? error.message : "登录失败";
      const isInvalidCredentials = rawMessage.includes("用户名或密码错误");
      const text = isInvalidCredentials ? "账号密码错误" : rawMessage;
      setStatusMessage(text);
      if (isInvalidCredentials) {
        setIsLoginErrorOpen(true);
      } else {
        message.error(text);
      }
    }
  }

  function closeLoginModal() {
    setIsLoginModalOpen(false);
    setPassword("");
  }

  function clearAuthenticatedState(options: { publicHome?: boolean } = {}) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("display_name");
    localStorage.removeItem("user_email");
    localStorage.removeItem("role");
    localStorage.removeItem("position");
    localStorage.removeItem("allowed_ai_app_ids");
    setToken("");
    setUsername("");
    setDisplayName("");
    setUserEmail("");
    setPassword("");
    setIsLoginModalOpen(false);
    setRole("employee");
    setPosition(null);
    setAllowedAiAppIds(null);
    setLastForbiddenPath("");
    setMessages([]);
    setActiveThreadId("");
    setChatThreads([]);
    setThreadSearch("");
    setThreadRetentionDays(15);
    setApprovals([]);
    setRefunds([]);
    setAuditLogs([]);
    setRunRecords([]);
    setGeneratedFiles([]);
    setUserSettings(null);
    setProfileForm({ displayName: "", email: "" });
    setPasswordForm({ oldPassword: "", newPassword: "", confirmPassword: "" });
    setGeneratedFileFilters({ search: "", dateRange: "30d", fileType: "all" });
    setDownloadingFileId("");
    setRunRecordDetail(null);
    setIsRunRecordDetailOpen(false);
    setEffectAnalytics(null);
    setEffectAnalyticsFilters({ dateRange: "30d", position: "all" });
    setEvaluationCenter(null);
    setRunningEvaluationId("");
    setMonitoringCenter(null);
    setMonitoringCenterFilters({ dateRange: "30d" });
    setAiWorkflows([]);
    setAiWorkflowDetail(null);
    setIsAiWorkflowDetailOpen(false);
    setAiWorkflowRunResult(null);
    setAiWorkflowInputs({});
    setAiWorkflowFilters({ position: "all", category: "" });
    setRunningAiWorkflowId("");
    setPlatformDrafts([]);
    setPlatformDraftDetail(null);
    setIsPlatformDraftDetailOpen(false);
    setPlatformDraftFilters({ draftType: "all", status: "all" });
    setPlatformDraftReviewComment("");
    setPlatformDraftActionKey("");
    setBusinessActionLoop(null);
    setIsBusinessActionLoopLoading(false);
    setPlatformExecutionTasks([]);
    setPlatformExecutionTaskFilters({ status: "all" });
    setPlatformExecutionTaskDetail(null);
    setIsPlatformExecutionTaskDetailOpen(false);
    setRetryingPlatformExecutionTaskId("");
    setNotifications([]);
    setNotificationFilters({ status: "all" });
    setMarkingNotificationId("");
    setIsMarkingAllNotificationsRead(false);
    setFeedbackItems([]);
    setFeedbackSummary({ total: 0, open: 0, completed: 0 });
    setFeedbackFilters({ status: "all" });
    setFeedbackForm({ category: "功能建议", priority: "normal", title: "", description: "" });
    setCompletingFeedbackId("");
    setAutomationFlows([]);
    setAutomationFlowDetail(null);
    setIsAutomationFlowDetailOpen(false);
    setAutomationFlowFilters({ position: "all", category: "" });
    setCustomerMessages([]);
    setCustomerMessageDetail(null);
    setCustomerProcessResult(null);
    setCustomerInboxFilters({ status: "all", riskLevel: "all" });
    setProcessingCustomerMessageId("");
    setConnectors([]);
    setConnectorSummary(null);
    setConnectorDetail(null);
    setIsConnectorDetailOpen(false);
    setPlatformActionExecutors([]);
    setPlatformActionExecutorSummary(null);
    setPlatformActionExecutorActionOptions([]);
    setPlatformActionExecutorTypeOptions([]);
    resetPlatformActionExecutorForm();
    setCheckingPlatformActionExecutorId("");
    setDeletingPlatformActionExecutorId("");
    setUsers([]);
    setAutomationTasks([]);
    setFinanceReportFiles([]);
    setFinanceReportSummary("");
    setFinanceExcelFile(null);
    setErpResources([]);
    setErpStatus(null);
    setErpDiagnostics(null);
    setErpDashboardOverview(null);
    setErpDashboardMarket("all");
    setErpDashboardDateRange("all");
    setErpDashboardStore("all");
    setErpRecordDetail(null);
    setIsErpRecordDetailOpen(false);
    setSelectedErpResource("");
    setErpQueryResult(null);
    setThreadSummary("");
    setThreadStateText("");
    if (options.publicHome) {
      window.history.replaceState(null, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    } else {
      navigateToView("dashboard", { replace: true });
    }
  }

  function generatedFileFilterPayload(filters = generatedFileFilters): GeneratedFileFilters {
    return {
      search: filters.search.trim() || undefined,
      date_range: filters.dateRange,
      file_type: filters.fileType,
      limit: 80,
    };
  }

  function applyUserSettings(item: UserSettingsItem) {
    const nextDisplayName = item.display_name || "";
    const nextEmail = item.email || "";
    setUserSettings(item);
    setDisplayName(nextDisplayName);
    setUserEmail(nextEmail);
    setProfileForm({
      displayName: nextDisplayName,
      email: nextEmail,
    });
    localStorage.setItem("display_name", nextDisplayName);
    localStorage.setItem("user_email", nextEmail);
  }

  async function refreshUserSettings(activeToken = token) {
    if (!activeToken) {
      setUserSettings(null);
      return;
    }

    setIsLoadingUserSettings(true);
    try {
      const result = await getMySettings(activeToken);
      applyUserSettings(result.item);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "用户设置加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsLoadingUserSettings(false);
    }
  }

  async function handleSaveUserProfile() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsSavingProfile(true);
    try {
      const result = await updateMyProfile(token, {
        display_name: profileForm.displayName.trim() || null,
        email: profileForm.email.trim() || null,
      });
      applyUserSettings(result.item);
      setStatusMessage("用户资料已保存");
      message.success("用户资料已保存");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "用户资料保存失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleSaveUserPassword() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setStatusMessage("两次输入的新密码不一致");
      message.warning("两次输入的新密码不一致");
      return;
    }

    setIsSavingPassword(true);
    try {
      await updateMyPassword(token, {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      });
      setPasswordForm({ oldPassword: "", newPassword: "", confirmPassword: "" });
      setStatusMessage("密码已修改");
      message.success("密码已修改");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "密码修改失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSavingPassword(false);
    }
  }

  async function refreshGeneratedFiles(activeToken = token, filters = generatedFileFilters) {
    if (!activeToken) {
      setGeneratedFiles([]);
      setIsGeneratedFilesLoading(false);
      return;
    }

    setIsGeneratedFilesLoading(true);

    try {
      const result = await listGeneratedFiles(activeToken, generatedFileFilterPayload(filters));
      setGeneratedFiles(result.items);
      setStatusMessage("文件下载列表已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "文件下载列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsGeneratedFilesLoading(false);
    }
  }

  async function handleDownloadGeneratedFile(file: GeneratedFileItem) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setDownloadingFileId(file.id);
    try {
      const result = await downloadGeneratedFile(token, file.id);
      downloadBlob(result.blob, result.filename || file.name);
      setStatusMessage(`已开始下载：${result.filename || file.name}`);
      message.success("文件已开始下载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "文件下载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setDownloadingFileId("");
    }
  }

  function handleLogout() {
    clearAuthenticatedState();
    setStatusMessage("已退出登录");
    message.success("已退出登录");
  }

  function navigateToPath(path: string, options: { replace?: boolean } = {}) {
    if (window.location.pathname !== path) {
      if (options.replace) {
        window.history.replaceState(null, "", path);
      } else {
        window.history.pushState(null, "", path);
      }
    }
    setActiveView(viewFromPath(path));
  }

  async function refreshAdminData(activeToken = token) {
    if (!activeToken) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      const backendActionFilter = auditBackendActionFilter(auditActionFilter);
      const [refundResult, auditResult, userResult, feedbackResult] = await Promise.all([
        listRefunds(activeToken),
        listAuditLogs(activeToken, {
          action: backendActionFilter,
          resource_type: auditResourceFilter,
          position: auditPositionFilter,
          limit: 80,
        }),
        listUsers(activeToken),
        listFeedback(activeToken, { status: feedbackFilters.status, limit: 80 }),
      ]);

      setApprovals([]);
      setRefunds(refundResult.items.map(mapRefund));
      setAuditLogs(auditResult.items.map(mapAuditLog));
      setUsers(userResult.items.map(mapUser));
      setFeedbackItems(feedbackResult.items);
      setFeedbackSummary(feedbackResult.summary);
      setStatusMessage("后台数据已刷新");
      message.success("后台数据已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "刷新失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function refreshApprovals(activeToken = token) {
    if (!activeToken) {
      setApprovals([]);
      return;
    }

    try {
      const result = await listApprovals(activeToken);
      setApprovals(result.items.map(mapApproval));
      setStatusMessage("退款审批已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "退款审批加载失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function refreshAuditLogs(activeToken = token) {
    if (!activeToken) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      const backendActionFilter = auditBackendActionFilter(auditActionFilter);
      const result = await listAuditLogs(activeToken, {
        action: backendActionFilter,
        resource_type: auditResourceFilter,
        position: auditPositionFilter,
        limit: 80,
      });
      setAuditLogs(result.items.map(mapAuditLog));
      setStatusMessage("审计日志已刷新");
      message.success("审计日志已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "审计日志刷新失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  function runRecordFilterPayload(filters = runRecordFilters): RunRecordFilters {
    return {
      status: filters.status === "all" ? undefined : filters.status,
      run_type: filters.runType.trim() || undefined,
      app_id: filters.appId.trim() || undefined,
      position: filters.position,
      resource_type: filters.resourceType.trim() || undefined,
      resource_id: filters.resourceId.trim() || undefined,
      flow_key: filters.flowKey.trim() || undefined,
      limit: 80,
    };
  }

  async function refreshRunRecords(activeToken = token, filters = runRecordFilters) {
    if (!activeToken || !hasAdminAccess(role, activeToken)) {
      setRunRecords([]);
      setIsRunRecordsLoading(false);
      return;
    }

    setIsRunRecordsLoading(true);

    try {
      const result = await listRunRecords(activeToken, runRecordFilterPayload(filters));
      setRunRecords(result.items);
      setStatusMessage("运行记录已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "运行记录加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsRunRecordsLoading(false);
    }
  }

  async function openRunRecordDetail(runId: string) {
    if (!token || !hasAdminAccess(role, token)) {
      const text = token ? "只有管理员可以查看运行记录详情" : "请先登录";
      setStatusMessage(text);
      message.warning(text);
      return;
    }

    setIsRunRecordDetailOpen(true);
    setIsRunRecordDetailLoading(true);
    setRunRecordDetail(null);

    try {
      setRunRecordDetail(await getRunRecordDetail(token, runId));
      setStatusMessage("运行记录详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "运行记录详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsRunRecordDetailLoading(false);
    }
  }

  function effectAnalyticsPayload(filters = effectAnalyticsFilters) {
    return {
      date_range: filters.dateRange,
      position: filters.position,
    };
  }

  async function refreshEffectAnalytics(activeToken = token, filters = effectAnalyticsFilters) {
    if (!activeToken || !hasAdminAccess(role, activeToken)) {
      setEffectAnalytics(null);
      setIsEffectAnalyticsLoading(false);
      return;
    }

    setIsEffectAnalyticsLoading(true);

    try {
      const result = await getEffectAnalytics(activeToken, effectAnalyticsPayload(filters));
      setEffectAnalytics(result);
      setStatusMessage("效果分析已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "效果分析加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsEffectAnalyticsLoading(false);
    }
  }

  async function refreshEvaluationCenter(activeToken = token) {
    if (!activeToken) {
      return;
    }

    setIsEvaluationCenterLoading(true);

    try {
      const result = await getEvaluationCenter(activeToken);
      setEvaluationCenter(result);
      setStatusMessage("AI 评测中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "AI 评测中心加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsEvaluationCenterLoading(false);
    }
  }

  async function refreshMonitoringCenter(activeToken = token, filters = monitoringCenterFilters) {
    if (!activeToken) {
      return;
    }

    setIsMonitoringCenterLoading(true);

    try {
      const result = await getMonitoringCenter(activeToken, {
        date_range: filters.dateRange,
      });
      setMonitoringCenter(result);
      setStatusMessage("监控中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "监控中心加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsMonitoringCenterLoading(false);
    }
  }

  async function runEvaluation(datasetId: string) {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    setRunningEvaluationId(datasetId);

    try {
      const result = await runRagEvaluation(token, datasetId, 5);
      setStatusMessage(`评测完成：${result.report.dataset_name}`);
      message.success("RAG 评测已完成");
      await refreshEvaluationCenter(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "RAG 评测运行失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setRunningEvaluationId("");
    }
  }

  async function refreshAiWorkflows(activeToken = token) {
    if (!activeToken) {
      return;
    }

    setIsAiWorkflowsLoading(true);

    try {
      const result = await listAiWorkflows(activeToken);
      setAiWorkflows(result.items);
      setStatusMessage("AI 工作流已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "AI 工作流加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsAiWorkflowsLoading(false);
    }
  }

  function platformDraftFilterPayload(filters = platformDraftFilters) {
    return {
      draft_type: filters.draftType === "all" ? undefined : filters.draftType,
      status: filters.status,
      limit: 80,
    };
  }

  async function refreshPlatformDrafts(activeToken = token, filters = platformDraftFilters) {
    if (!activeToken) {
      setPlatformDrafts([]);
      setIsPlatformDraftsLoading(false);
      return;
    }

    setIsPlatformDraftsLoading(true);

    try {
      const result = await listPlatformDrafts(activeToken, platformDraftFilterPayload(filters));
      setPlatformDrafts(result.items);
      setStatusMessage("草稿审核中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "草稿列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsPlatformDraftsLoading(false);
    }
  }

  async function refreshBusinessActionLoop(activeToken = token) {
    const activeRole = activeToken ? readRoleFromToken(activeToken) : role;
    const activePosition = activeToken ? readPositionFromToken(activeToken) || position : position;
    if (!activeToken || !canUseBusinessActionLoop(activeRole, activePosition)) {
      setBusinessActionLoop(null);
      setIsBusinessActionLoopLoading(false);
      return;
    }

    setIsBusinessActionLoopLoading(true);

    try {
      setBusinessActionLoop(await getBusinessActionLoop(activeToken, { limit: 80 }));
      setStatusMessage("业务动作闭环已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "业务动作闭环加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsBusinessActionLoopLoading(false);
    }
  }

  function platformExecutionTaskFilterPayload(filters = platformExecutionTaskFilters) {
    return {
      status: filters.status,
      limit: 80,
    };
  }

  async function refreshPlatformExecutionTasks(activeToken = token, filters = platformExecutionTaskFilters) {
    const activeRole = activeToken ? readRoleFromToken(activeToken) : role;
    const activePosition = activeToken ? readPositionFromToken(activeToken) || position : position;

    if (!activeToken || !canUsePlatformExecutionTasks(activeRole, activePosition)) {
      setPlatformExecutionTasks([]);
      setIsPlatformExecutionTasksLoading(false);
      return;
    }

    setIsPlatformExecutionTasksLoading(true);

    try {
      const result = await listPlatformExecutionTasks(activeToken, platformExecutionTaskFilterPayload(filters));
      setPlatformExecutionTasks(result.items);
      setStatusMessage("执行任务中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "执行任务列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsPlatformExecutionTasksLoading(false);
    }
  }

  async function openPlatformExecutionTaskDetail(taskId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsPlatformExecutionTaskDetailOpen(true);
    setIsPlatformExecutionTaskDetailLoading(true);
    setPlatformExecutionTaskDetail(null);

    try {
      const result = await getPlatformExecutionTask(token, taskId);
      setPlatformExecutionTaskDetail(result.item);
      setStatusMessage("执行任务详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "执行任务详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsPlatformExecutionTaskDetailLoading(false);
    }
  }

  async function handleRetryPlatformExecutionTask(taskId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setRetryingPlatformExecutionTaskId(taskId);

    try {
      const result = await retryPlatformExecutionTask(token, taskId);
      const nextTask = result.task || result.item || null;

      if (nextTask) {
        setPlatformExecutionTasks((current) => upsertPlatformExecutionTask(current, nextTask));
        setPlatformExecutionTaskDetail((current) => current?.id === nextTask.id ? nextTask : current);
      }
      if (result.draft) {
        setPlatformDrafts((current) => current.map((item) => item.id === result.draft?.id ? result.draft : item));
      }

      const status = nextTask?.status || "";
      const text = status === "waiting_callback"
        ? "任务已重新派发，等待外部执行器回调"
        : status === "failed"
          ? "任务重试完成，但外部执行仍失败"
          : "任务已重新派发";
      setStatusMessage(text);
      if (status === "failed") {
        message.error(text);
      } else {
        message.success(text);
      }
      void refreshPlatformExecutionTasks(token);
      void refreshBusinessActionLoop(token);
      void refreshNotifications(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "任务重试失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setRetryingPlatformExecutionTaskId("");
    }
  }

  function notificationFilterPayload(filters = notificationFilters) {
    return {
      status: filters.status,
      limit: 80,
    };
  }

  async function refreshNotifications(activeToken = token, filters = notificationFilters) {
    if (!activeToken) {
      setNotifications([]);
      setIsNotificationsLoading(false);
      return;
    }

    setIsNotificationsLoading(true);

    try {
      const result = await listNotifications(activeToken, notificationFilterPayload(filters));
      setNotifications(result.items);
      setStatusMessage("通知中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "通知列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsNotificationsLoading(false);
    }
  }

  async function handleMarkNotificationRead(notificationId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setMarkingNotificationId(notificationId);

    try {
      const result = await markNotificationRead(token, notificationId);
      setNotifications((current) =>
        current.map((item) => item.id === notificationId
          ? result.item || { ...item, status: "read", read_at: new Date().toISOString() }
          : item),
      );
      setStatusMessage("通知已标记为已读");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "通知已读操作失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setMarkingNotificationId("");
    }
  }

  async function handleMarkAllNotificationsRead() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsMarkingAllNotificationsRead(true);

    try {
      await markAllNotificationsRead(token);
      const readAt = new Date().toISOString();
      setNotifications((current) => current.map((item) => ({ ...item, status: "read", read_at: item.read_at || readAt })));
      setStatusMessage("通知已全部标记为已读");
      message.success("通知已全部标记为已读");
      void refreshNotifications(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "全部已读操作失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsMarkingAllNotificationsRead(false);
    }
  }

  function feedbackFilterPayload(filters = feedbackFilters) {
    return {
      status: filters.status,
      limit: 120,
    };
  }

  async function refreshFeedback(activeToken = token, filters = feedbackFilters) {
    if (!activeToken) {
      setFeedbackItems([]);
      setFeedbackSummary({ total: 0, open: 0, completed: 0 });
      setIsFeedbackLoading(false);
      return;
    }

    setIsFeedbackLoading(true);

    try {
      const result = await listFeedback(activeToken, feedbackFilterPayload(filters));
      setFeedbackItems(result.items);
      setFeedbackSummary(result.summary);
      setStatusMessage(role === "admin" ? "反馈中心已刷新" : "我的反馈已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "反馈列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsFeedbackLoading(false);
    }
  }

  async function handleSubmitFeedback() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    const title = feedbackForm.title.trim();
    const description = feedbackForm.description.trim();
    if (!title || !description) {
      message.warning("请填写反馈标题和具体内容");
      return;
    }

    setIsSubmittingFeedback(true);

    try {
      const result = await createFeedback(token, {
        category: feedbackForm.category,
        priority: feedbackForm.priority,
        title,
        description,
      });
      setFeedbackItems((current) => [result.item, ...current.filter((item) => item.id !== result.item.id)]);
      setFeedbackSummary((current) => ({
        total: current.total + 1,
        open: current.open + 1,
        completed: current.completed,
      }));
      setFeedbackForm({ category: "功能建议", priority: "normal", title: "", description: "" });
      setStatusMessage("反馈已提交，管理员可在反馈中心查看");
      message.success("反馈已提交");
      void refreshFeedback(token);
      void refreshNotifications(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "反馈提交失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  async function handleCompleteFeedback(feedbackId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setCompletingFeedbackId(feedbackId);

    try {
      const result = await completeFeedback(token, feedbackId, "管理员已完成该反馈处理。");
      setFeedbackItems((current) => current.map((item) => item.id === feedbackId ? result.item : item));
      setFeedbackSummary((current) => ({
        total: current.total,
        open: Math.max(0, current.open - 1),
        completed: current.completed + 1,
      }));
      setStatusMessage("反馈已标记为完成");
      message.success("反馈已完成");
      void refreshFeedback(token);
      void refreshNotifications(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "反馈完成操作失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setCompletingFeedbackId("");
    }
  }

  function handleOpenNotificationResource(item: NotificationItem) {
    const resourceType = item.resource_type || "";
    const resourceId = item.resource_id || "";

    if (!resourceId) {
      return;
    }

    if (resourceType === "platform_execution_task") {
      if (!canUsePlatformExecutionTasks(role, position)) {
        message.warning("当前账号没有执行任务中心权限");
        return;
      }
      navigateToView("platform_execution_tasks");
      void openPlatformExecutionTaskDetail(resourceId);
      return;
    }

    if (resourceType === "platform_draft") {
      navigateToView("platform_draft_review");
      void openPlatformDraftDetail(resourceId);
      return;
    }

    if (resourceType === "feedback") {
      navigateToView(role === "admin" ? "feedback_center" : "feedback_improvement");
      void refreshFeedback(token);
    }
  }

  async function openPlatformDraftDetail(draftId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsPlatformDraftDetailOpen(true);
    setIsPlatformDraftDetailLoading(true);
    setPlatformDraftDetail(null);

    try {
      setPlatformDraftDetail(await getPlatformDraftDetail(token, draftId));
      setPlatformDraftReviewComment("");
      setStatusMessage("草稿详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "草稿详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsPlatformDraftDetailLoading(false);
    }
  }

  async function handleReviewPlatformDraft(draftId: string, decision: "approved" | "rejected") {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setPlatformDraftActionKey(`${draftId}:${decision}`);

    try {
      const result = await reviewPlatformDraft(token, draftId, {
        decision,
        comment: platformDraftReviewComment.trim() || undefined,
      });
      setPlatformDrafts((current) => current.map((item) => item.id === draftId ? result.item : item));
      setPlatformDraftDetail((current) => current && current.item.id === draftId
        ? { ...current, item: result.item }
        : current);
      setPlatformDraftReviewComment("");
      setStatusMessage(decision === "approved" ? "草稿已审核通过" : "草稿已驳回");
      message.success(decision === "approved" ? "草稿已审核通过" : "草稿已驳回");
      void refreshPlatformDrafts(token);
      void refreshBusinessActionLoop(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "草稿审核失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setPlatformDraftActionKey("");
    }
  }

  async function handlePublishPlatformDraft(draftId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setPlatformDraftActionKey(`${draftId}:publish`);

    try {
      const result = await publishPlatformDraft(token, draftId);
      setPlatformDrafts((current) => current.map((item) => item.id === draftId ? result.draft : item));
      setPlatformDraftDetail((current) => current && current.item.id === draftId
        ? { item: result.draft, executions: [result.execution, ...current.executions.filter((item) => item.id !== result.execution.id)] }
        : current);
      if (result.task) {
        setPlatformExecutionTasks((current) => upsertPlatformExecutionTask(current, result.task as PlatformExecutionTaskItem));
        setPlatformExecutionTaskDetail((current) => current?.id === result.task?.id ? result.task || current : current);
      }

      const taskStatus = result.task?.status || result.execution.status;
      if (taskStatus === "succeeded" || result.execution.status === "succeeded") {
        setStatusMessage(platformDraftPublishSuccessLabel(result.draft));
        message.success(platformDraftPublishSuccessLabel(result.draft));
      } else if (isWaitingPlatformTaskStatus(taskStatus) || result.execution.status === "waiting_executor") {
        const text = taskStatus === "waiting_callback"
          ? "外部执行器已接收，正在等待回调"
          : "已进入外部执行任务队列";
        setStatusMessage(text);
        message.info(text);
      } else {
        setStatusMessage(result.message || "发布/发送失败");
        message.error(result.message || "发布/发送失败");
      }
      void refreshPlatformDrafts(token);
      void refreshBusinessActionLoop(token);
      if (canUsePlatformExecutionTasks(role, position)) {
        void refreshPlatformExecutionTasks(token);
      }
      void refreshNotifications(token);
      if (role === "admin") {
        void refreshRunRecords(token);
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "发布/发送失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setPlatformDraftActionKey("");
    }
  }

  async function openAiWorkflowDetail(workflowId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsAiWorkflowDetailOpen(true);
    setIsAiWorkflowDetailLoading(true);
    setAiWorkflowDetail(null);

    try {
      setAiWorkflowDetail(await getAiWorkflowDetail(token, workflowId));
      setStatusMessage("AI 工作流详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "AI 工作流详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsAiWorkflowDetailLoading(false);
    }
  }

  async function handleRunAiWorkflow(workflowId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    const inputText = (aiWorkflowInputs[workflowId] || "").trim();
    if (!inputText) {
      setStatusMessage("请输入工作流任务内容");
      message.warning("请输入工作流任务内容");
      return;
    }

    setRunningAiWorkflowId(workflowId);
    setStatusMessage("AI 工作流正在运行");

    try {
      const result = await runAiWorkflow(token, workflowId, inputText);
      setAiWorkflowRunResult(result);
      setStatusMessage(`${result.workflow.name}运行完成`);
      message.success("AI 工作流运行完成");
      if (result.platform_draft) {
        void refreshPlatformDrafts(token);
        void refreshBusinessActionLoop(token);
      }
      if (hasAdminAccess(role, token)) {
        await refreshRunRecords(token, {
          status: "all",
          runType: "ai_workflow",
          appId: "",
          position: "all",
          resourceType: "",
          resourceId: "",
          flowKey: "",
        });
        void refreshEffectAnalytics(token);
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "AI 工作流运行失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setRunningAiWorkflowId("");
    }
  }

  async function refreshAutomationFlows(activeToken = token, filters = automationFlowFilters) {
    if (!activeToken || !hasAdminAccess(role, activeToken)) {
      setAutomationFlows([]);
      setIsAutomationFlowsLoading(false);
      return;
    }

    setIsAutomationFlowsLoading(true);

    try {
      const result = await listAutomationFlows(activeToken, filters);
      setAutomationFlows(result.items);
      setStatusMessage("流程配置已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "流程配置加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsAutomationFlowsLoading(false);
    }
  }

  async function openAutomationFlowDetail(flowId: string) {
    if (!token || !hasAdminAccess(role, token)) {
      const text = token ? "只有管理员可以查看流程配置详情" : "请先登录";
      setStatusMessage(text);
      message.warning(text);
      return;
    }

    setIsAutomationFlowDetailOpen(true);
    setIsAutomationFlowDetailLoading(true);
    setAutomationFlowDetail(null);

    try {
      setAutomationFlowDetail(await getAutomationFlowDetail(token, flowId));
      setStatusMessage("流程配置详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "流程配置详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsAutomationFlowDetailLoading(false);
    }
  }

  async function refreshCustomerServiceMessages(activeToken = token, filters = customerInboxFilters) {
    if (!activeToken || !canUseCustomerServiceInbox(role, position)) {
      return;
    }

    setIsCustomerInboxLoading(true);

    try {
      const result = await listCustomerServiceMessages(activeToken, {
        status: filters.status,
        risk_level: filters.riskLevel,
        limit: 80,
      });
      setCustomerMessages(result.items);
      setStatusMessage("客服自动化收件箱已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "客服收件箱加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsCustomerInboxLoading(false);
    }
  }

  async function openCustomerServiceMessageDetail(messageId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    try {
      const detail = await getCustomerServiceMessageDetail(token, messageId);
      setCustomerMessageDetail(detail);
      setStatusMessage("客服消息详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "客服消息详情加载失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function handleCreateCustomerMessage() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!customerInboxForm.message.trim()) {
      setStatusMessage("请输入客户原话");
      message.warning("请输入客户原话");
      return;
    }

    const payload: CustomerServiceMessageCreatePayload = {
      channel: customerInboxForm.channel,
      buyer_name: customerInboxForm.buyerName.trim() || null,
      buyer_email: customerInboxForm.buyerEmail.trim() || null,
      buyer_language: customerInboxForm.buyerLanguage || "auto",
      marketplace: customerInboxForm.marketplace.trim() || null,
      order_no: customerInboxForm.orderNo.trim() || null,
      tracking_no: customerInboxForm.trackingNo.trim() || null,
      sku: customerInboxForm.sku.trim() || null,
      subject: customerInboxForm.subject.trim() || null,
      message: customerInboxForm.message.trim(),
    };

    setIsCreatingCustomerMessage(true);

    try {
      const detail = await createCustomerServiceMessage(token, payload);
      setCustomerMessageDetail(detail);
      setCustomerMessages((current) => [detail.item, ...current]);
      setStatusMessage("客户消息已进入收件箱");
      message.success("客户消息已进入收件箱");
      setCustomerInboxForm((current) => ({
        ...current,
        subject: "",
        message: "",
      }));
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "创建客户消息失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsCreatingCustomerMessage(false);
    }
  }

  async function handleProcessCustomerMessage(messageId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setProcessingCustomerMessageId(messageId);
    setStatusMessage("AI 正在处理客服消息");

    try {
      const result = await processCustomerServiceMessage(token, messageId);
      setCustomerProcessResult(result);
      setCustomerMessageDetail({ item: result.item, events: result.events });
      setCustomerMessages((current) =>
        current.map((item) => item.id === result.item.id ? result.item : item),
      );
      setStatusMessage("客服消息处理完成");
      message.success("客服消息处理完成");
      void refreshRunRecords(token, {
        status: "all",
        runType: "customer_service_automation",
        appId: "",
        position: "all",
        resourceType: "",
        resourceId: "",
        flowKey: "",
      });
      if (role === "admin") {
        void refreshAdminData(token);
      }
      if (canUseApprovalCenter(role, position)) {
        void refreshApprovals(token);
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "客服消息处理失败";
      setStatusMessage(text);
      message.error(text);
      void refreshCustomerServiceMessages(token);
    } finally {
      setProcessingCustomerMessageId("");
    }
  }

  async function refreshConnectors(activeToken = token) {
    if (!activeToken) {
      return;
    }

    setIsConnectorsLoading(true);

    try {
      const result = await listConnectors(activeToken);
      setConnectors(result.items);
      setConnectorSummary(result.summary);
      setStatusMessage("连接器中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "连接器中心加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsConnectorsLoading(false);
    }
  }

  async function openConnectorDetail(connectorId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsConnectorDetailOpen(true);
    setIsConnectorDetailLoading(true);
    setConnectorDetail(null);

    try {
      setConnectorDetail(await getConnectorDetail(token, connectorId));
      setStatusMessage("连接器详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "连接器详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsConnectorDetailLoading(false);
    }
  }

  async function refreshPlatformActionExecutors(activeToken = token) {
    if (!activeToken || readRoleFromToken(activeToken) !== "admin") {
      return;
    }

    setIsPlatformActionExecutorsLoading(true);

    try {
      const result = await listPlatformActionExecutors(activeToken);
      setPlatformActionExecutors(result.items);
      setPlatformActionExecutorSummary(result.summary);
      setPlatformActionExecutorActionOptions(result.action_types);
      setPlatformActionExecutorTypeOptions(result.executor_types);
      setStatusMessage("外部执行器配置已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "外部执行器配置加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsPlatformActionExecutorsLoading(false);
    }
  }

  function resetPlatformActionExecutorForm() {
    setPlatformActionExecutorForm({
      id: null,
      name: "",
      executorType: "webhook",
      actionTypes: [],
      webhookUrl: "",
      apiKey: "",
      timeoutSeconds: 12,
      enabled: true,
    });
  }

  function editPlatformActionExecutor(item: PlatformActionExecutorItem) {
    if (item.is_environment_fallback) {
      message.info("环境变量兜底执行器为只读配置");
      return;
    }
    setPlatformActionExecutorForm({
      id: item.id,
      name: item.name,
      executorType: item.executor_type,
      actionTypes: item.action_types,
      webhookUrl: "",
      apiKey: "",
      timeoutSeconds: item.timeout_seconds || 12,
      enabled: item.enabled,
    });
    setStatusMessage(`正在编辑执行器：${item.name}`);
  }

  function buildPlatformActionExecutorPayload(): PlatformActionExecutorPayload | null {
    const name = platformActionExecutorForm.name.trim();
    const webhookUrl = platformActionExecutorForm.webhookUrl.trim();
    if (!name) {
      message.warning("请填写执行器名称");
      return null;
    }
    if (!platformActionExecutorForm.actionTypes.length) {
      message.warning("请选择至少一个平台动作");
      return null;
    }
    if (!webhookUrl && !platformActionExecutorForm.id) {
      message.warning("请填写 Webhook URL");
      return null;
    }

    const payload: PlatformActionExecutorPayload = {
      name,
      executor_type: platformActionExecutorForm.executorType,
      action_types: platformActionExecutorForm.actionTypes,
      webhook_url: webhookUrl || "__UNCHANGED__",
      timeout_seconds: platformActionExecutorForm.timeoutSeconds,
      enabled: platformActionExecutorForm.enabled,
    };
    const apiKey = platformActionExecutorForm.apiKey.trim();
    if (apiKey) {
      payload.api_key = apiKey;
    } else if (!platformActionExecutorForm.id) {
      payload.api_key = null;
    }
    return payload;
  }

  async function savePlatformActionExecutor() {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    const payload = buildPlatformActionExecutorPayload();
    if (!payload) {
      return;
    }

    setIsSavingPlatformActionExecutor(true);
    try {
      if (platformActionExecutorForm.id) {
        await updatePlatformActionExecutor(token, platformActionExecutorForm.id, payload);
        message.success("外部执行器已更新");
      } else {
        await createPlatformActionExecutor(token, payload);
        message.success("外部执行器已创建");
      }
      resetPlatformActionExecutorForm();
      await refreshPlatformActionExecutors(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "外部执行器保存失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSavingPlatformActionExecutor(false);
    }
  }

  async function checkPlatformActionExecutor(item: PlatformActionExecutorItem) {
    if (!token) {
      return;
    }
    setCheckingPlatformActionExecutorId(item.id);
    try {
      const result = await checkPlatformActionExecutorHealth(token, item.id);
      setPlatformActionExecutors((current) => upsertPlatformActionExecutor(current, result.item));
      message.success("健康检查已完成");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "健康检查失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setCheckingPlatformActionExecutorId("");
    }
  }

  function removePlatformActionExecutor(item: PlatformActionExecutorItem) {
    if (!token || item.is_environment_fallback) {
      return;
    }

    Modal.confirm({
      title: "删除外部执行器",
      content: `确认删除“${item.name}”？已有历史任务记录不会被删除。`,
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        setDeletingPlatformActionExecutorId(item.id);
        try {
          await deletePlatformActionExecutor(token, item.id);
          setPlatformActionExecutors((current) => current.filter((executor) => executor.id !== item.id));
          if (platformActionExecutorForm.id === item.id) {
            resetPlatformActionExecutorForm();
          }
          message.success("外部执行器已删除");
          void refreshPlatformActionExecutors(token);
        } catch (error) {
          if (isAuthExpiredError(error)) {
            return;
          }
          const text = error instanceof Error ? error.message : "外部执行器删除失败";
          setStatusMessage(text);
          message.error(text);
        } finally {
          setDeletingPlatformActionExecutorId("");
        }
      },
    });
  }

  async function refreshUsers(activeToken = token) {
    if (!activeToken) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      const result = await listUsers(activeToken);
      setUsers(result.items.map(mapUser));
      setStatusMessage("用户列表已刷新");
      message.success("用户列表已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "用户列表刷新失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function refreshAutomationTasks(activeToken = token, forcedPosition?: Position | undefined) {
    if (!activeToken) {
      return;
    }

    try {
      const result = await listAutomationTasks(activeToken);
      if (forcedPosition && result.position !== forcedPosition && role !== "admin") {
        return;
      }

      setAutomationTasks((current) => mergeAutomationTasks(result.items, current));
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "岗位任务加载失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function refreshErpScopes(activeToken = token, activeRole = role) {
    if (!activeToken) {
      return;
    }

    try {
      const [scopeResult, statusResult] = await Promise.all([
        getErpScopes(activeToken),
        getErpStatus(activeToken),
      ]);
      setErpResources(scopeResult.resources);
      setErpStatus(statusResult);
      if (activeRole === "admin") {
        try {
          setErpDiagnostics(await getErpDiagnostics(activeToken));
        } catch {
          setErpDiagnostics(null);
        }
      } else {
        setErpDiagnostics(null);
      }
      setSelectedErpResource((current) => {
        if (current && scopeResult.resources.some((item) => item.resource === current)) {
          return current;
        }

        return scopeResult.resources[0]?.resource || "";
      });
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "ERP 权限加载失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function refreshErpDashboardOverview(
    activeToken = token,
    market = erpDashboardMarket,
    dateRange = erpDashboardDateRange,
    store = erpDashboardStore,
  ) {
    if (!activeToken) {
      setErpDashboardOverview(null);
      return;
    }

    try {
      setErpDashboardOverview(await getErpDashboardOverview(activeToken, market, dateRange, store));
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      setErpDashboardOverview(null);
      const text = error instanceof Error ? error.message : "岗位数据概览加载失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  function handleDashboardMarketChange(value: DashboardMarket) {
    setErpDashboardMarket(value);
    void refreshErpDashboardOverview(token, value, erpDashboardDateRange, erpDashboardStore);
  }

  function handleDashboardDateRangeChange(value: DashboardDateRange) {
    setErpDashboardDateRange(value);
    void refreshErpDashboardOverview(token, erpDashboardMarket, value, erpDashboardStore);
  }

  function handleDashboardStoreChange(value: DashboardStore) {
    setErpDashboardStore(value);
    void refreshErpDashboardOverview(token, erpDashboardMarket, erpDashboardDateRange, value);
  }

  async function handleOpenErpRecordDetail(resource: string, item: Record<string, unknown>) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    const recordId = overviewRecordId(item);
    if (!recordId) {
      setStatusMessage("该 ERP 记录缺少可查询 ID");
      message.warning("该 ERP 记录缺少可查询 ID");
      return;
    }

    setIsErpRecordDetailOpen(true);
    setIsErpRecordDetailLoading(true);
    setErpRecordDetail(null);

    try {
      const result = await getErpRecordDetail(token, resource, recordId);
      setErpRecordDetail(result);
      setStatusMessage(result.message);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "ERP 记录详情加载失败";
      setErpRecordDetail(null);
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsErpRecordDetailLoading(false);
    }
  }

  async function handleErpQuery() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!selectedErpResource) {
      setStatusMessage("请选择 ERP 资源");
      message.warning("请选择 ERP 资源");
      return;
    }

    let filters: Record<string, unknown> | unknown[] | null = null;
    const trimmedFilters = erpFiltersText.trim();

    if (trimmedFilters && trimmedFilters !== "{}") {
      try {
        const parsed = JSON.parse(trimmedFilters) as unknown;
        if (!Array.isArray(parsed) && (typeof parsed !== "object" || parsed === null)) {
          throw new Error("filters 必须是 JSON 对象或数组");
        }
        filters = parsed as Record<string, unknown> | unknown[];
      } catch (error) {
        const text = error instanceof Error ? error.message : "filters JSON 格式错误";
        setStatusMessage(text);
        message.error(text);
        return;
      }
    }

    setIsErpLoading(true);
    setStatusMessage("正在查询 ERP");

    try {
      const result = await queryErp(token, {
        resource: selectedErpResource,
        query: erpQueryText.trim() || undefined,
        filters,
        limit: erpLimit,
      });
      setErpQueryResult(result);
      setStatusMessage(result.ok ? "ERP 查询完成" : "ERP 查询未返回可用数据");
      if (result.ok) {
        message.success("ERP 查询完成");
      } else {
        message.warning(result.message || "ERP 未返回可用数据");
      }
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "ERP 查询失败";
      const failedResource = erpResources.find((item) => item.resource === selectedErpResource);
      setErpQueryResult({
        ok: false,
        configured: Boolean(erpStatus?.configured),
        status: "error",
        provider: erpStatus?.provider || "erpnext",
        provider_label: erpStatus?.provider_label || "ERP",
        resource: selectedErpResource,
        resource_label: failedResource?.label || selectedErpResource,
        provider_resource: failedResource?.provider_refs[erpStatus?.provider || "erpnext"] || selectedErpResource,
        message: text,
        items: [],
        raw: null,
      });
      setStatusMessage("ERP 查询失败");
      message.error("ERP 查询失败，请查看连接结果");
    } finally {
      setIsErpLoading(false);
    }
  }

  async function handleGenerateAutomation(taskId: string, inputText: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!inputText.trim()) {
      setStatusMessage("请输入任务内容");
      message.warning("请输入任务内容");
      return;
    }

    setAutomationLoadingTaskId(taskId);

    try {
      const result = await generateAutomation(token, taskId, inputText);
      setAutomationTasks((current) =>
        current.map((item) =>
          item.task_id === taskId
            ? {
              ...item,
              inputText,
              output: result.answer,
              platformDraft: result.platform_draft || null,
            }
            : item,
        ),
      );
      setStatusMessage(
        result.platform_draft
          ? `${result.position_label}任务已生成并保存草稿`
          : `${result.position_label}任务生成完成`,
      );
      message.success(result.platform_draft ? "已生成并保存草稿" : "生成完成");
      if (result.platform_draft) {
        void refreshPlatformDrafts(token);
        void refreshBusinessActionLoop(token);
      }
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "生成失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setAutomationLoadingTaskId("");
    }
  }

  async function handleAnalyzeFinanceReport() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (financeReportFiles.length === 0 && !financeReportInstruction.trim()) {
      setStatusMessage("请上传财务报表文件，或手动输入财务报表内容");
      message.warning("请上传财务报表文件，或手动输入财务报表内容");
      return;
    }

    setIsAnalyzingFinanceReport(true);
    setStatusMessage("正在解析财务报表并生成分析文件");

    try {
      const result = await analyzeFinanceReport(
        token,
        financeReportFiles,
        financeReportInstruction,
        financeReportOutputFormat,
      );
      downloadBlob(result.blob, result.filename);
      const summary = `财务报表分析已生成：${result.filename}`;
      setFinanceReportSummary(summary);
      setStatusMessage(summary);
      message.success("财务报表分析已生成");
      void refreshGeneratedFiles();
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "财务报表分析失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsAnalyzingFinanceReport(false);
    }
  }

  async function handleTransformFinanceExcel() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!financeExcelFile && financeExcelErpResources.length === 0 && !financeExcelInstruction.trim()) {
      const text = "请上传 Excel、选择财务 ERP 表，或输入要生成的新表要求";
      setStatusMessage(text);
      message.warning(text);
      return;
    }

    setIsTransformingFinanceExcel(true);
    setStatusMessage(financeExcelFile ? "正在生成财务 Excel" : "正在根据财务 ERP 数据生成 Excel");

    try {
      const result = await transformFinanceExcel(
        token,
        financeExcelFile,
        financeExcelInstruction,
        financeExcelErpResources,
      );
      downloadBlob(result.blob, result.filename);
      setStatusMessage("财务 Excel 已生成并开始下载");
      message.success("财务 Excel 已生成");
      void refreshGeneratedFiles();
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "财务 Excel 生成失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsTransformingFinanceExcel(false);
    }
  }

  async function handleExportFinanceSalary() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!financeSalaryMessage.trim()) {
      setStatusMessage("请输入工资表请求");
      message.warning("请输入工资表请求");
      return;
    }

    setIsExportingFinanceSalary(true);
    setStatusMessage("正在识别工资导出意图并查询 ERP");

    try {
      const result = await exportFinanceSalary(token, financeSalaryMessage);
      downloadBlob(result.blob, result.filename);
      const summary = `已识别为 ${result.intent || "finance_salary_export"}，期间 ${result.period || "当前月份"}，生成 ${result.employeeCount || 0} 名员工工资表：${result.filename}`;
      setFinanceSalaryExportSummary(summary);
      setStatusMessage(summary);
      message.success("工资 Excel 已生成");
      void refreshGeneratedFiles();
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "工资 Excel 生成失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsExportingFinanceSalary(false);
    }
  }

  async function handleReconcileFinanceFiles() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (financeReconciliationFiles.length === 0) {
      setStatusMessage("请选择对账 Excel 文件");
      message.warning("请选择对账 Excel 文件");
      return;
    }

    setIsReconcilingFinance(true);
    setStatusMessage("正在生成财务对账表");

    try {
      const result = await reconcileFinanceFiles(
        token,
        financeReconciliationFiles,
        financeReconciliationInstruction,
        financeReconciliationCurrency,
      );
      downloadBlob(result.blob, result.filename);
      setStatusMessage("财务对账表已生成并开始下载");
      message.success("财务对账表已生成");
      void refreshGeneratedFiles();
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "财务对账失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsReconcilingFinance(false);
    }
  }

  async function handleCreateUser() {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    const payload: UserCreatePayload = {
      username: newUser.username.trim(),
      password: newUser.password,
      role: newUser.role,
      position: newUser.role === "employee" ? newUser.position : null,
      department: newUser.department.trim() || null,
    };

    if (!payload.username || !payload.password) {
      setStatusMessage("请输入用户名和密码");
      message.warning("请输入用户名和密码");
      return;
    }

    setIsCreatingUser(true);

    try {
      const result = await createUser(token, payload);
      setUsers((current) => [mapUser(result.item), ...current]);
      setNewUser({
        username: "",
        password: "",
        role: "employee",
        position: "customer_service",
        department: "",
      });
      setStatusMessage("用户创建成功");
      message.success("用户创建成功");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "创建用户失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsCreatingUser(false);
    }
  }

  async function handleToggleUserAiApp(userId: string, appId: string, enabled: boolean) {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    const key = `${userId}:${appId}`;
    setUpdatingUserAppKey(key);

    try {
      const result = await updateUserAiAppPermission(token, userId, appId, enabled);
      const updatedUser = mapUser(result.item);
      setUsers((current) =>
        current.map((item) => item.id === updatedUser.id ? updatedUser : item),
      );
      setStatusMessage(enabled ? "AI 应用已启用" : "AI 应用已禁用");
      message.success(enabled ? "AI 应用已启用" : "AI 应用已禁用");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "AI 应用权限更新失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setUpdatingUserAppKey("");
    }
  }

  async function handleDeleteUser(userId: string) {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    setDeletingUserId(userId);

    try {
      await deleteUser(token, userId);
      setUsers((current) => current.filter((item) => item.id !== userId));
      setStatusMessage("用户已删除");
      message.success("用户已删除");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "删除用户失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setDeletingUserId("");
    }
  }

  async function refreshChatThreads(
    activeToken = token,
    options: { search?: string; activateLatest?: boolean; silent?: boolean } = {},
  ) {
    if (!activeToken) {
      setChatThreads([]);
      setActiveThreadId("");
      return [];
    }

    setIsThreadListLoading(true);

    try {
      const result = await listThreads(activeToken, {
        search: options.search ?? threadSearch,
        limit: 80,
      });
      setChatThreads(result.items);
      setThreadRetentionDays(result.retention_days || 15);

      if (options.activateLatest) {
        const pathThreadId = threadIdFromPathname(window.location.pathname);
        const latestId = pathThreadId || result.items[0]?.id || "";
        if (latestId) {
          await openChatThread(latestId, {
            activeToken,
            replacePath: true,
            silent: true,
          });
        } else {
          setActiveThreadId("");
          setMessages([]);
          setThreadSummary("");
          setThreadStateText("");
        }
      }

      return result.items;
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return [];
      }
      const text = error instanceof Error ? error.message : "会话列表加载失败";
      setStatusMessage(text);
      if (!options.silent) {
        message.error(text);
      }
      return [];
    } finally {
      setIsThreadListLoading(false);
    }
  }

  async function openChatThread(
    threadId: string,
    options: { activeToken?: string; replacePath?: boolean; silent?: boolean } = {},
  ) {
    const activeToken = options.activeToken || token;
    if (!activeToken) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!threadId) {
      setActiveThreadId("");
      setMessages([]);
      setThreadSummary("");
      setThreadStateText("");
      navigateToPath("/chat", { replace: options.replacePath });
      return;
    }

    try {
      const result = await getThreadMessages(activeToken, threadId);
      setActiveThreadId(threadId);
      setMessages(result.messages.map(mapThreadMessage));
      setThreadSummary(String(result.summary.summary || ""));
      setThreadStateText(JSON.stringify(result.state, null, 2));
      navigateToPath(`/chat/${encodeURIComponent(threadId)}`, { replace: options.replacePath });
      setStatusMessage("会话已加载");
      if (!options.silent) {
        message.success("会话已加载");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "会话加载失败";
      setStatusMessage(text);
      if (!options.silent) {
        message.error(text);
      }
    }
  }

  async function handleCreateChatThread() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsCreatingThread(true);

    try {
      const result = await createThread(token);
      setActiveThreadId(result.item.id);
      setMessages([]);
      setThreadSummary("");
      setThreadStateText("");
      setChatThreads((current) => [result.item, ...current.filter((item) => item.id !== result.item.id)]);
      navigateToPath(`/chat/${encodeURIComponent(result.item.id)}`);
      setStatusMessage("已创建新会话");
      message.success("已创建新会话");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "创建会话失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsCreatingThread(false);
    }
  }

  async function handleRenameChatThread(title: string) {
    const nextTitle = title.trim();

    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return false;
    }

    if (!activeThreadId) {
      message.warning("请先创建或打开一个会话");
      return false;
    }

    if (!nextTitle) {
      message.warning("会话标题不能为空");
      return false;
    }

    setIsRenamingThread(true);

    try {
      const result = await updateThreadTitle(token, activeThreadId, nextTitle);
      const savedTitle = result.item.title || nextTitle;
      setChatThreads((current) =>
        current.map((item) =>
          item.id === activeThreadId
            ? {
                ...item,
                title: savedTitle,
              }
            : item,
        ),
      );
      setStatusMessage("会话标题已更新");
      message.success("会话标题已更新");
      void refreshChatThreads(token, { silent: true });
      return true;
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return false;
      }
      const text = error instanceof Error ? error.message : "修改会话标题失败";
      setStatusMessage(text);
      message.error(text);
      return false;
    } finally {
      setIsRenamingThread(false);
    }
  }

  async function sendMessage() {
    const messageText = messageInput.trim();

    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!messageText || isChatLoading) {
      return;
    }

    const pendingThreadId = activeThreadId || `pending-${Date.now()}`;
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      threadId: pendingThreadId,
      role: "user",
      content: messageText,
      createdAt: "刚刚",
    };
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      threadId: pendingThreadId,
      role: "assistant",
      content: "",
      createdAt: "正在生成",
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setMessageInput("");
    setIsChatLoading(true);
    setStatusMessage("正在流式生成回答");

    try {
      await sendChatStream(token, messageText, activeThreadId || undefined, {
        onStart: (payload) => {
          const nextThreadId = payload.thread_id || pendingThreadId;
          if (payload.thread_id) {
            setActiveThreadId(payload.thread_id);
            navigateToPath(`/chat/${encodeURIComponent(payload.thread_id)}`, { replace: !activeThreadId });
          }
          setMessages((current) =>
            current.map((item) =>
              item.threadId === pendingThreadId
                ? { ...item, threadId: nextThreadId }
                : item,
            ),
          );
        },
        onNode: (payload) => {
          if (payload.node) {
            setStatusMessage(`正在执行节点：${payload.node}`);
          }
        },
        onContent: (payload) => {
          const chunk = payload.content || "";
          const nextThreadId = payload.thread_id || activeThreadId || pendingThreadId;

          if (payload.thread_id) {
            setActiveThreadId(payload.thread_id);
          }
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessageId
                ? {
                    ...item,
                    threadId: nextThreadId,
                    content: item.content + chunk,
                  }
                : item,
            ),
          );
        },
        onDone: (payload) => {
          const finalThreadId = payload.thread_id || activeThreadId || pendingThreadId;

          if (payload.thread_id) {
            setActiveThreadId(payload.thread_id);
            navigateToPath(`/chat/${encodeURIComponent(payload.thread_id)}`, { replace: !activeThreadId });
          }
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessageId
                ? {
                    ...item,
                    threadId: finalThreadId,
                    content: item.content || payload.answer || "",
                    createdAt: "刚刚",
                    route: routeFromIntent(payload.intent ?? null, payload.risk_level ?? null),
                    erpReferences: payload.erp_references || [],
                    attachments: payload.attachments || [],
                    platformDraft: payload.platform_draft || null,
                  }
                : item,
            ),
          );
        },
        onError: (payload) => {
          throw new Error(payload.message || "流式聊天失败");
        },
      });

      setStatusMessage("聊天完成");
      void refreshChatThreads(token, { silent: true });
      void refreshBusinessActionLoop(token);
      void refreshRunRecords();

      if (role === "admin") {
        await refreshAdminData();
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId && !item.content
            ? {
                ...item,
                content: "生成失败，请稍后重试。",
                createdAt: "刚刚",
              }
            : item,
        ),
      );
      const text = error instanceof Error ? error.message : "发送失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsChatLoading(false);
    }
  }

  async function sendPublicLLMMessage() {
    const messageText = publicLLMInput.trim();

    if (!messageText || isPublicLLMLoading) {
      return;
    }

    const userMessage: PublicLLMChatMessage = {
      id: `public-user-${Date.now()}`,
      role: "user",
      content: messageText,
    };

    const history = [...publicLLMMessages, userMessage]
      .filter((item) => item.id !== "welcome")
      .map(({ role, content }) => ({ role, content }));

    const assistantMessageId = `public-assistant-${Date.now()}`;
    const assistantMessage: PublicLLMChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
    };

    setPublicLLMMessages((current) => [...current, userMessage, assistantMessage]);
    setPublicLLMInput("");
    setIsPublicLLMLoading(true);

    try {
      await sendPublicLLMChatStream(messageText, history, (chunk) => {
        if (!chunk) {
          return;
        }

        setPublicLLMMessages((current) =>
          current.map((item) =>
            item.id === assistantMessageId
              ? {
                  ...item,
                  content: item.content + chunk,
                }
              : item,
          ),
        );
      });

      setPublicLLMMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId && !item.content
            ? {
                ...item,
                content: "我暂时没有生成回答。",
              }
            : item,
        ),
      );
    } catch (error) {
      const text = error instanceof Error ? error.message : "大模型聊天失败";
      setPublicLLMMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId
            ? {
                ...item,
                content: `发送失败：${text}`,
              }
            : item,
        ),
      );
    } finally {
      setIsPublicLLMLoading(false);
    }
  }

  async function reviewApproval(id: string, approved: boolean) {
    if (!token) {
      setStatusMessage("请先登录客服账号");
      message.warning("请先登录客服账号");
      return;
    }

    try {
      await reviewApprovalApi(token, id, approved);
      await refreshApprovals();
      const text = approved ? "审批已通过" : "审批已拒绝";
      setStatusMessage(text);
      message.success(text);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "审批失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function handleUploadDocument(uploadAccess?: DocumentUploadAccessPayload) {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    if (!documentFile) {
      setStatusMessage("请选择要上传的文件");
      message.warning("请选择要上传的文件");
      return;
    }

    setIsUploading(true);
    setStatusMessage("正在上传并入库");

    try {
      await uploadDocument(
        token,
        documentFile,
        documentVisibility,
        documentDepartment,
        documentPositionScope === "all" ? null : documentPositionScope,
        documentMarketScope === "all" ? null : documentMarketScope,
        documentStoreScope === "all" ? null : documentStoreScope,
        documentFieldScope === "all" ? null : documentFieldScope,
        documentSensitivityLevel,
        uploadAccess,
      );
      setDocumentFile(null);
      setStatusMessage("文档上传并入库成功");
      message.success("文档上传并入库成功");

      if (role === "admin") {
        await refreshAdminData();
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "上传失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsUploading(false);
    }
  }

  if (!token) {
    return (
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: "#1677ff",
            borderRadius: 6,
            wireframe: false,
          },
        }}
      >
        <AntApp>
          <PublicPortal
            language={language}
            onLanguageChange={() => setLanguage((current) => (current === "zh" ? "en" : "zh"))}
            onLoginClick={() => setIsLoginModalOpen(true)}
            onLLMClick={() => setIsPublicLLMOpen(true)}
          />
          <PublicLLMChatWidget
            open={isPublicLLMOpen}
            input={publicLLMInput}
            messages={publicLLMMessages}
            isLoading={isPublicLLMLoading}
            setInput={setPublicLLMInput}
            onClose={() => setIsPublicLLMOpen(false)}
            onSend={sendPublicLLMMessage}
          />
          <LoginModal
            open={isLoginModalOpen}
            username={username}
            password={password}
            setUsername={setUsername}
            setPassword={setPassword}
            onCancel={closeLoginModal}
            onLogin={handleLogin}
          />
          <LoginErrorModal
            open={isLoginErrorOpen}
            onClose={() => setIsLoginErrorOpen(false)}
          />
          <SessionExpiredModal
            open={isSessionExpiredOpen}
            onLogin={() => {
              setIsSessionExpiredOpen(false);
              setIsLoginModalOpen(true);
            }}
            onClose={() => setIsSessionExpiredOpen(false)}
          />
        </AntApp>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 6,
          wireframe: false,
        },
      }}
    >
      <ProConfigProvider hashed={false}>
        <AntApp>
          <ProLayout
            title="企业内部后台管理系统"
            logo={<SafetyCertificateOutlined />}
            route={route}
            location={{ pathname: currentPath }}
            layout="mix"
            splitMenus={false}
            siderWidth={224}
            siderMenuType="group"
            menuProps={{
              motion: {
                motionAppear: false,
                motionEnter: false,
                motionLeave: false,
                motionDeadline: 0,
              },
              subMenuOpenDelay: 0,
              subMenuCloseDelay: 0,
            }}
            menuItemRender={(item, dom) => (
              <button
                className="menuButton"
                type="button"
                data-nav-path={String(item.path || "")}
                onClick={() => {
                  const matched = flatVisibleNavItems.find((nav) => nav.path === item.path);
                  if (matched?.chatAction === "new") {
                    void handleCreateChatThread();
                    return;
                  }
                  if (matched?.threadId) {
                    void openChatThread(matched.threadId);
                    return;
                  }
                  if (matched) {
                    navigateToView(resolveNavTargetView(matched, role, position));
                  }
                }}
              >
                {dom}
              </button>
            )}
            actionsRender={() =>
              role === "admin"
                ? [
                    <Button key="refresh" icon={<ReloadOutlined />} onClick={() => refreshAdminData()}>
                      刷新
                    </Button>,
                  ]
                : []
            }
            avatarProps={{
              src: undefined,
              title: token ? username : "未登录",
              render: () => (
                <UserMenu
                  username={username}
                  displayName={displayName}
                  role={role}
                  position={position}
                  token={token}
                  openLogin={() => setIsLoginModalOpen(true)}
                  logout={handleLogout}
                />
              ),
            }}
            token={{
              header: {
                colorBgHeader: "#ffffff",
              },
              sider: {
                colorMenuBackground: "#ffffff",
              },
            }}
          >
            <PageContainer
              title={titleForView(safeActiveView)}
              subTitle={pageSubtitle(role, position)}
              extra={[
                <Text key="status" type="secondary">
                  {statusMessage}
                </Text>,
              ]}
            >
              <Space direction="vertical" size={16} className="pageStack">
                {safeActiveView === "dashboard" && (
	                  <Dashboard
	                    stats={stats}
	                    role={role}
                    position={position}
                    erpOverview={erpDashboardOverview}
                    erpDashboardMarket={erpDashboardMarket}
                    setErpDashboardMarket={handleDashboardMarketChange}
                    erpDashboardDateRange={erpDashboardDateRange}
                    setErpDashboardDateRange={handleDashboardDateRangeChange}
                    erpDashboardStore={erpDashboardStore}
                    setErpDashboardStore={handleDashboardStoreChange}
                    refreshErpOverview={() => refreshErpDashboardOverview()}
                    onOpenRecordDetail={handleOpenErpRecordDetail}
                    onNavigate={navigateToView}
                  />
                )}
                {safeActiveView === "ai_apps" && (
                  <AiAppsPanel
                    role={role}
                    position={position}
                    tasks={automationTasks}
                    erpResources={erpResources}
                    pendingApprovals={pendingCount}
                    chatMessageCount={messages.length}
                    allowedAiAppIds={allowedAiAppIds}
                    onNavigate={navigateToView}
                  />
                )}
                {safeActiveView === "run_records" && role === "admin" && (
                  <RunRecordsPanel
                    role={role}
                    records={runRecords}
                    filters={runRecordFilters}
                    setFilters={setRunRecordFilters}
                    loading={isRunRecordsLoading}
                    refreshRecords={() => refreshRunRecords()}
                    openDetail={openRunRecordDetail}
                  />
                )}
                {safeActiveView === "file_downloads" && (
                  <GeneratedFilesPanel
                    role={role}
                    files={generatedFiles}
                    filters={generatedFileFilters}
                    setFilters={setGeneratedFileFilters}
                    loading={isGeneratedFilesLoading}
                    downloadingFileId={downloadingFileId}
                    refreshFiles={() => refreshGeneratedFiles()}
                    downloadFile={handleDownloadGeneratedFile}
                  />
                )}
                {safeActiveView === "effect_analytics" && role === "admin" && (
                  <EffectAnalyticsPanel
                    role={role}
                    analytics={effectAnalytics}
                    filters={effectAnalyticsFilters}
                    setFilters={setEffectAnalyticsFilters}
                    loading={isEffectAnalyticsLoading}
                    refreshAnalytics={() => refreshEffectAnalytics()}
                  />
                )}
                {safeActiveView === "evaluation_center" && role === "admin" && (
                  <EvaluationCenterPanel
                    data={evaluationCenter}
                    loading={isEvaluationCenterLoading}
                    runningEvaluationId={runningEvaluationId}
                    refreshEvaluationCenter={() => refreshEvaluationCenter()}
                    runEvaluation={runEvaluation}
                  />
                )}
                {safeActiveView === "monitoring_center" && role === "admin" && (
                  <MonitoringCenterPanel
                    data={monitoringCenter}
                    filters={monitoringCenterFilters}
                    setFilters={setMonitoringCenterFilters}
                    loading={isMonitoringCenterLoading}
                    refreshMonitoringCenter={() => refreshMonitoringCenter()}
                  />
                )}
                {isAiWorkflowView(safeActiveView) && (
                  <AiWorkflowsPanel
                    role={role}
                    workflows={aiWorkflows}
                    filters={aiWorkflowFilters}
                    setFilters={setAiWorkflowFilters}
                    selectedWorkflowId={workflowIdFromView(safeActiveView)}
                    inputs={aiWorkflowInputs}
                    setInputs={setAiWorkflowInputs}
                    runResult={aiWorkflowRunResult}
                    loading={isAiWorkflowsLoading}
                    runningWorkflowId={runningAiWorkflowId}
                    refreshWorkflows={() => refreshAiWorkflows()}
                    runWorkflow={handleRunAiWorkflow}
                    openDetail={openAiWorkflowDetail}
                    onNavigate={navigateToView}
                  />
                )}
                {safeActiveView === "business_action_loop" && (
                  <BusinessActionLoopPanel
                    role={role}
                    position={position}
                    data={businessActionLoop}
                    loading={isBusinessActionLoopLoading}
                    refreshLoop={() => refreshBusinessActionLoop()}
                    openDraft={openPlatformDraftDetail}
                    openTask={openPlatformExecutionTaskDetail}
                    navigateToView={navigateToView}
                  />
                )}
                {safeActiveView === "platform_draft_review" && (
                  <PlatformDraftReviewPanel
                    role={role}
                    position={position}
                    drafts={platformDrafts}
                    filters={platformDraftFilters}
                    setFilters={setPlatformDraftFilters}
                    loading={isPlatformDraftsLoading}
                    actionKey={platformDraftActionKey}
                    refreshDrafts={() => refreshPlatformDrafts()}
                    openDetail={openPlatformDraftDetail}
                    reviewDraft={handleReviewPlatformDraft}
                    publishDraft={handlePublishPlatformDraft}
                  />
                )}
                {safeActiveView === "platform_execution_tasks" && (
                  <PlatformExecutionTasksPanel
                    role={role}
                    position={position}
                    tasks={platformExecutionTasks}
                    filters={platformExecutionTaskFilters}
                    setFilters={setPlatformExecutionTaskFilters}
                    loading={isPlatformExecutionTasksLoading}
                    retryingTaskId={retryingPlatformExecutionTaskId}
                    refreshTasks={() => refreshPlatformExecutionTasks()}
                    openDetail={openPlatformExecutionTaskDetail}
                    retryTask={handleRetryPlatformExecutionTask}
                  />
                )}
                {safeActiveView === "notifications" && (
                  <NotificationsPanel
                    notifications={notifications}
                    filters={notificationFilters}
                    setFilters={setNotificationFilters}
                    loading={isNotificationsLoading}
                    markingNotificationId={markingNotificationId}
                    markingAllRead={isMarkingAllNotificationsRead}
                    refreshNotifications={() => refreshNotifications()}
                    markRead={handleMarkNotificationRead}
                    markAllRead={handleMarkAllNotificationsRead}
                    openResource={handleOpenNotificationResource}
                  />
                )}
                {safeActiveView === "feedback_improvement" && role === "employee" && (
                  <FeedbackImprovementPanel
                    items={feedbackItems}
                    summary={feedbackSummary}
                    filters={feedbackFilters}
                    setFilters={setFeedbackFilters}
                    form={feedbackForm}
                    setForm={setFeedbackForm}
                    loading={isFeedbackLoading}
                    submitting={isSubmittingFeedback}
                    refreshFeedback={() => refreshFeedback()}
                    submitFeedback={handleSubmitFeedback}
                  />
                )}
                {safeActiveView === "feedback_center" && role === "admin" && (
                  <FeedbackCenterPanel
                    items={feedbackItems}
                    summary={feedbackSummary}
                    filters={feedbackFilters}
                    setFilters={setFeedbackFilters}
                    loading={isFeedbackLoading}
                    completingFeedbackId={completingFeedbackId}
                    refreshFeedback={() => refreshFeedback()}
                    completeFeedback={(feedback) => handleCompleteFeedback(feedback.id)}
                  />
                )}
                {safeActiveView === "automation_flows" && role === "admin" && (
                  <AutomationFlowsPanel
                    role={role}
                    flows={automationFlows}
                    filters={automationFlowFilters}
                    setFilters={setAutomationFlowFilters}
                    loading={isAutomationFlowsLoading}
                    refreshFlows={() => refreshAutomationFlows()}
                    openDetail={openAutomationFlowDetail}
                  />
                )}
                {safeActiveView === "connectors" && role === "admin" && (
                  <ConnectorsPanel
                    connectors={connectors}
                    summary={connectorSummary}
                    loading={isConnectorsLoading}
                    refreshConnectors={() => refreshConnectors()}
                    openDetail={openConnectorDetail}
                  />
                )}
                {safeActiveView === "platform_action_executors" && role === "admin" && (
                  <PlatformActionExecutorsPanel
                    executors={platformActionExecutors}
                    summary={platformActionExecutorSummary}
                    actionOptions={platformActionExecutorActionOptions}
                    typeOptions={platformActionExecutorTypeOptions}
                    form={platformActionExecutorForm}
                    setForm={setPlatformActionExecutorForm}
                    loading={isPlatformActionExecutorsLoading}
                    saving={isSavingPlatformActionExecutor}
                    checkingId={checkingPlatformActionExecutorId}
                    deletingId={deletingPlatformActionExecutorId}
                    refresh={() => refreshPlatformActionExecutors()}
                    save={savePlatformActionExecutor}
                    edit={editPlatformActionExecutor}
                    reset={resetPlatformActionExecutorForm}
                    checkHealth={checkPlatformActionExecutor}
                    remove={removePlatformActionExecutor}
                  />
                )}
                {isAutomationView(safeActiveView) && (
                  <AutomationPanel
                    role={role}
                    position={position}
                    selectedPosition={automationPositionFromView(safeActiveView, role, position)}
                    selectedTaskId={automationTaskIdFromView(safeActiveView)}
                    selectedFinanceTool={automationFinanceToolFromView(safeActiveView)}
                    tasks={automationTasks}
                    financeReportFiles={financeReportFiles}
                    setFinanceReportFiles={setFinanceReportFiles}
                    financeReportInstruction={financeReportInstruction}
                    setFinanceReportInstruction={setFinanceReportInstruction}
                    financeReportOutputFormat={financeReportOutputFormat}
                    setFinanceReportOutputFormat={setFinanceReportOutputFormat}
                    financeReportSummary={financeReportSummary}
                    isAnalyzingFinanceReport={isAnalyzingFinanceReport}
                    financeExcelFile={financeExcelFile}
                    setFinanceExcelFile={setFinanceExcelFile}
                    financeExcelInstruction={financeExcelInstruction}
                    setFinanceExcelInstruction={setFinanceExcelInstruction}
                    financeExcelErpResources={financeExcelErpResources}
                    setFinanceExcelErpResources={setFinanceExcelErpResources}
                    erpResources={erpResources}
                    isTransformingFinanceExcel={isTransformingFinanceExcel}
                    financeSalaryMessage={financeSalaryMessage}
                    setFinanceSalaryMessage={setFinanceSalaryMessage}
                    financeSalaryExportSummary={financeSalaryExportSummary}
                    isExportingFinanceSalary={isExportingFinanceSalary}
                    financeReconciliationFiles={financeReconciliationFiles}
                    setFinanceReconciliationFiles={setFinanceReconciliationFiles}
                    financeReconciliationInstruction={financeReconciliationInstruction}
                    setFinanceReconciliationInstruction={setFinanceReconciliationInstruction}
                    financeReconciliationCurrency={financeReconciliationCurrency}
                    setFinanceReconciliationCurrency={setFinanceReconciliationCurrency}
                    isReconcilingFinance={isReconcilingFinance}
                    onGenerate={handleGenerateAutomation}
                    onAnalyzeFinanceReport={handleAnalyzeFinanceReport}
                    onTransformFinanceExcel={handleTransformFinanceExcel}
                    onReconcileFinanceFiles={handleReconcileFinanceFiles}
                    onNavigate={navigateToView}
                    onInputChange={(taskId, value) =>
                      setAutomationTasks((current) =>
                        current.map((item) =>
                          item.task_id === taskId
                            ? { ...item, inputText: value }
                            : item,
                        ),
                      )
                    }
                    loadingTaskId={automationLoadingTaskId}
                    onExportFinanceSalary={handleExportFinanceSalary}
                  />
                )}
                {safeActiveView === "customer_service_inbox" && (
                  <CustomerServiceInboxPanel
                    role={role}
                    position={position}
                    messages={customerMessages}
                    detail={customerMessageDetail}
                    processResult={customerProcessResult}
                    filters={customerInboxFilters}
                    setFilters={setCustomerInboxFilters}
                    form={customerInboxForm}
                    setForm={setCustomerInboxForm}
                    loading={isCustomerInboxLoading}
                    creating={isCreatingCustomerMessage}
                    processingMessageId={processingCustomerMessageId}
                    refreshMessages={(nextFilters) => refreshCustomerServiceMessages(token, nextFilters || customerInboxFilters)}
                    createMessage={handleCreateCustomerMessage}
                    processMessage={handleProcessCustomerMessage}
                    openDetail={openCustomerServiceMessageDetail}
                  />
                )}
                {isErpView(safeActiveView) && (
                  <ErpPanel
                    role={role}
                    position={position}
                    activeView={safeActiveView}
                    status={erpStatus}
                    diagnostics={erpDiagnostics}
                    resources={erpResources}
                    selectedResource={selectedErpResource}
                    setSelectedResource={setSelectedErpResource}
                    queryText={erpQueryText}
                    setQueryText={setErpQueryText}
                    filtersText={erpFiltersText}
                    setFiltersText={setErpFiltersText}
                    limit={erpLimit}
                    setLimit={setErpLimit}
                    result={erpQueryResult}
                    isLoading={isErpLoading}
                    onRefresh={() => refreshErpScopes()}
                    onQuery={handleErpQuery}
                  />
                )}
                {safeActiveView === "chat" && (
                  <ChatPanel
                    messageInput={messageInput}
                    setMessageInput={setMessageInput}
                    activeThread={chatThreads.find((item) => item.id === activeThreadId) || null}
                    activeThreadId={activeThreadId}
                    createThread={handleCreateChatThread}
                    renameThread={handleRenameChatThread}
                    sendMessage={sendMessage}
                    messages={messages}
                    isLoading={isChatLoading}
                    isCreatingThread={isCreatingThread}
                    isRenamingThread={isRenamingThread}
                    position={position}
                  />
                )}
                {safeActiveView === "user_settings" && (
                  <UserSettingsPanel
                    username={username}
                    displayName={displayName}
                    email={userEmail}
                    role={role}
                    position={position}
                    profileForm={profileForm}
                    setProfileForm={setProfileForm}
                    passwordForm={passwordForm}
                    setPasswordForm={setPasswordForm}
                    loading={isLoadingUserSettings}
                    savingProfile={isSavingProfile}
                    savingPassword={isSavingPassword}
                    refreshSettings={() => refreshUserSettings()}
                    saveProfile={handleSaveUserProfile}
                    savePassword={handleSaveUserPassword}
                  />
                )}
                {safeActiveView === "documents" && role === "admin" && (
                  <DocumentsPanel
                    token={token}
                    file={documentFile}
                    setFile={setDocumentFile}
                    visibility={documentVisibility}
                    setVisibility={setDocumentVisibility}
                    department={documentDepartment}
                    setDepartment={setDocumentDepartment}
                    positionScope={documentPositionScope}
                    setPositionScope={setDocumentPositionScope}
                    marketScope={documentMarketScope}
                    setMarketScope={setDocumentMarketScope}
                    storeScope={documentStoreScope}
                    setStoreScope={setDocumentStoreScope}
                    fieldScope={documentFieldScope}
                    setFieldScope={setDocumentFieldScope}
                    sensitivityLevel={documentSensitivityLevel}
                    setSensitivityLevel={setDocumentSensitivityLevel}
                    uploadDocument={handleUploadDocument}
                    role={role}
                    users={users}
                    isUploading={isUploading}
                  />
                )}
                {safeActiveView === "users" && role === "admin" && (
                  <UsersPanel
                    users={users}
                    newUser={newUser}
                    setNewUser={setNewUser}
                    createUser={handleCreateUser}
                    deleteUser={handleDeleteUser}
                    toggleUserAiApp={handleToggleUserAiApp}
                    refreshUsers={() => refreshUsers()}
                    isCreating={isCreatingUser}
                    deletingUserId={deletingUserId}
                    updatingUserAppKey={updatingUserAppKey}
                    currentUsername={username}
                  />
                )}
                {safeActiveView === "approvals" && canUseApprovalCenter(role, position) && (
                  <ApprovalsPanel approvals={approvals} reviewApproval={reviewApproval} role={role} position={position} />
                )}
                {safeActiveView === "refunds" && role === "admin" && <RefundsPanel refunds={refunds} />}
                {safeActiveView === "audit" && role === "admin" && (
                  <AuditPanel
                    logs={auditLogs}
                    actionFilter={auditActionFilter}
                    setActionFilter={setAuditActionFilter}
                    resourceFilter={auditResourceFilter}
                    setResourceFilter={setAuditResourceFilter}
                    positionFilter={auditPositionFilter}
                    setPositionFilter={setAuditPositionFilter}
                    refreshLogs={() => refreshAuditLogs()}
                  />
                )}
                {safeActiveView === "threads" && (
                  <ThreadsPanel
                    threads={chatThreads}
                    activeThreadId={activeThreadId}
                    threadSearch={threadSearch}
                    setThreadSearch={setThreadSearch}
                    refreshThreads={() => refreshChatThreads()}
                    openThread={(threadId) => openChatThread(threadId)}
                    messages={messages}
                    summary={threadSummary}
                    stateText={threadStateText}
                    loading={isThreadListLoading}
                    role={role}
                    retentionDays={threadRetentionDays}
                  />
                )}
              </Space>
            </PageContainer>
            <LoginModal
              open={isLoginModalOpen}
              username={username}
              password={password}
              setUsername={setUsername}
              setPassword={setPassword}
              onCancel={closeLoginModal}
              onLogin={handleLogin}
            />
            <LoginErrorModal
              open={isLoginErrorOpen}
              onClose={() => setIsLoginErrorOpen(false)}
            />
            <SessionExpiredModal
              open={isSessionExpiredOpen}
              onLogin={() => {
                setIsSessionExpiredOpen(false);
                setIsLoginModalOpen(true);
              }}
              onClose={() => setIsSessionExpiredOpen(false)}
            />
            <ErpRecordDetailModal
              open={isErpRecordDetailOpen}
              loading={isErpRecordDetailLoading}
              detail={erpRecordDetail}
              onClose={() => setIsErpRecordDetailOpen(false)}
            />
            <RunRecordDetailModal
              open={isRunRecordDetailOpen}
              loading={isRunRecordDetailLoading}
              detail={runRecordDetail}
              onClose={() => setIsRunRecordDetailOpen(false)}
            />
            <PlatformDraftDetailModal
              open={isPlatformDraftDetailOpen}
              loading={isPlatformDraftDetailLoading}
              detail={platformDraftDetail}
              role={role}
              actionKey={platformDraftActionKey}
              reviewComment={platformDraftReviewComment}
              setReviewComment={setPlatformDraftReviewComment}
              reviewDraft={handleReviewPlatformDraft}
              publishDraft={handlePublishPlatformDraft}
              onClose={() => setIsPlatformDraftDetailOpen(false)}
            />
            <PlatformExecutionTaskDetailModal
              open={isPlatformExecutionTaskDetailOpen}
              loading={isPlatformExecutionTaskDetailLoading}
              task={platformExecutionTaskDetail}
              role={role}
              retryingTaskId={retryingPlatformExecutionTaskId}
              retryTask={handleRetryPlatformExecutionTask}
              onClose={() => setIsPlatformExecutionTaskDetailOpen(false)}
            />
            <AutomationFlowDetailModal
              open={isAutomationFlowDetailOpen}
              loading={isAutomationFlowDetailLoading}
              detail={automationFlowDetail}
              token={token}
              onClose={() => setIsAutomationFlowDetailOpen(false)}
            />
            <AiWorkflowDetailModal
              open={isAiWorkflowDetailOpen}
              loading={isAiWorkflowDetailLoading}
              detail={aiWorkflowDetail}
              onClose={() => setIsAiWorkflowDetailOpen(false)}
            />
            <ConnectorDetailModal
              open={isConnectorDetailOpen}
              loading={isConnectorDetailLoading}
              detail={connectorDetail}
              onClose={() => setIsConnectorDetailOpen(false)}
            />
          </ProLayout>
        </AntApp>
      </ProConfigProvider>
    </ConfigProvider>
  );
}

function PublicPortal(props: {
  language: Language;
  onLanguageChange: () => void;
  onLoginClick: () => void;
  onLLMClick: () => void;
}) {
  return (
    <main className="portfolioShell">
      <Navbar
        language={props.language}
        onLanguageChange={props.onLanguageChange}
        onLoginClick={props.onLoginClick}
        onLLMClick={props.onLLMClick}
      />
      <Hero language={props.language} />
      <Skills language={props.language} />
      <Projects language={props.language} />
      <Contact language={props.language} />
    </main>
  );
}

function PublicLLMChatWidget(props: {
  open: boolean;
  input: string;
  messages: PublicLLMChatMessage[];
  isLoading: boolean;
  setInput: (value: string) => void;
  onClose: () => void;
  onSend: () => void;
}) {
  if (!props.open) {
    return null;
  }

  return (
    <div className="publicLlmWidget">
      <div className="publicLlmHeader">
        <div>
          <Text strong>大模型聊天</Text>
          <Paragraph type="secondary" className="publicLlmSubtitle">
            普通 AI 对话，不接入 RAG
          </Paragraph>
        </div>
        <Button size="small" type="text" icon={<StopOutlined />} onClick={props.onClose} />
      </div>

      <div className="publicLlmMessages">
        {props.messages.map((item) => (
          <div key={item.id} className={`publicLlmMessageRow ${item.role}`}>
            <div className={`publicLlmBubble ${item.role}`}>
              {item.content || (props.isLoading && item.role === "assistant" ? "正在思考..." : "")}
            </div>
          </div>
        ))}
      </div>

      <div className="publicLlmComposer">
        <TextArea
          value={props.input}
          placeholder="问我任何普通问题"
          autoSize={{ minRows: 2, maxRows: 4 }}
          onChange={(event) => props.setInput(event.target.value)}
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              props.onSend();
            }
          }}
        />
        <Button
          type="primary"
          shape="circle"
          icon={<SendOutlined />}
          loading={props.isLoading}
          onClick={props.onSend}
        />
      </div>
    </div>
  );
}

function UserMenu(props: {
  username: string;
  displayName: string;
  role: Role;
  position: Position | null;
  token: string;
  openLogin: () => void;
  logout: () => void;
}) {
  if (!props.token) {
    return (
      <Button type="text" icon={<LoginOutlined />} onClick={props.openLogin}>
        未登录
      </Button>
    );
  }
  const label = props.displayName || props.username;

  return (
    <Dropdown
      menu={{
        items: [
          {
            key: "logout",
            icon: <LogoutOutlined />,
            label: "退出登录",
            onClick: props.logout,
          },
        ],
      }}
      trigger={["click"]}
    >
      <Button type="text" className="userMenuButton">
        <Space size={8}>
          <Avatar size="small" style={{ backgroundColor: "#1677ff" }}>
            {label.slice(0, 1).toUpperCase()}
          </Avatar>
          <Text>{label}</Text>
          <Tag color={props.role === "admin" ? "blue" : "green"}>{roleLabel(props.role)}</Tag>
          {props.position ? <Tag color="purple">{positionLabel(props.position)}</Tag> : null}
          <DownOutlined />
        </Space>
      </Button>
    </Dropdown>
  );
}

function LoginModal(props: {
  open: boolean;
  username: string;
  password: string;
  setUsername: (value: string) => void;
  setPassword: (value: string) => void;
  onCancel: () => void;
  onLogin: () => void;
}) {
  return (
    <Modal
      title="登录企业内部后台"
      open={props.open}
      okText="登录"
      cancelText="取消"
      centered
      onOk={props.onLogin}
      onCancel={props.onCancel}
    >
      <Form layout="vertical" className="loginModalForm" autoComplete="off">
        <Form.Item label="用户名">
          <Input
            value={props.username}
            onChange={(event) => props.setUsername(event.target.value)}
            onPressEnter={props.onLogin}
            autoComplete="off"
          />
        </Form.Item>
        <Form.Item label="密码">
          <Input.Password
            value={props.password}
            onChange={(event) => props.setPassword(event.target.value)}
            onPressEnter={props.onLogin}
            autoComplete="new-password"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function LoginErrorModal(props: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Modal
      title="登录失败"
      open={props.open}
      width={360}
      centered
      okText="知道了"
      cancelButtonProps={{ style: { display: "none" } }}
      onOk={props.onClose}
      onCancel={props.onClose}
    >
      <Paragraph style={{ marginBottom: 0 }}>账号密码错误，请重新输入。</Paragraph>
    </Modal>
  );
}

function SessionExpiredModal(props: {
  open: boolean;
  onLogin: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      open={props.open}
      title="登录失效"
      onCancel={props.onClose}
      footer={[
        <Button key="close" onClick={props.onClose}>
          稍后登录
        </Button>,
        <Button key="login" type="primary" onClick={props.onLogin}>
          重新登录
        </Button>,
      ]}
    >
      <Paragraph style={{ marginBottom: 0 }}>登录失效，需要重新登录。</Paragraph>
    </Modal>
  );
}

function Dashboard({
  stats,
  role,
  position,
  erpOverview,
  erpDashboardMarket,
  setErpDashboardMarket,
  erpDashboardDateRange,
  setErpDashboardDateRange,
  erpDashboardStore,
  setErpDashboardStore,
  refreshErpOverview,
  onOpenRecordDetail,
  onNavigate,
}: {
  stats: Array<{ title: string; value: number; suffix: string }>;
  role: Role;
  position: Position | null;
  erpOverview: ErpDashboardOverviewResponse | null;
  erpDashboardMarket: DashboardMarket;
  setErpDashboardMarket: (value: DashboardMarket) => void;
  erpDashboardDateRange: DashboardDateRange;
  setErpDashboardDateRange: (value: DashboardDateRange) => void;
  erpDashboardStore: DashboardStore;
  setErpDashboardStore: (value: DashboardStore) => void;
  refreshErpOverview: () => void;
  onOpenRecordDetail: (resource: string, item: Record<string, unknown>) => void;
  onNavigate: (view: View) => void;
}) {
  const visibleStats = role === "admin"
    ? stats
    : stats.filter((item) => item.title === "会话消息");
  const shortcuts = dashboardShortcuts(role, position);

  return (
    <Space direction="vertical" size={16} className="pageStack">
      {role !== "admin" ? (
        <DashboardOverviewSection
          role={role}
          erpOverview={erpOverview}
          erpDashboardMarket={erpDashboardMarket}
          setErpDashboardMarket={setErpDashboardMarket}
          erpDashboardDateRange={erpDashboardDateRange}
          setErpDashboardDateRange={setErpDashboardDateRange}
          erpDashboardStore={erpDashboardStore}
          setErpDashboardStore={setErpDashboardStore}
          refreshErpOverview={refreshErpOverview}
          onOpenRecordDetail={onOpenRecordDetail}
        />
      ) : (
        <StatisticCard.Group direction="row" className="dashboardStatsGroup">
          {visibleStats.map((item) => (
            <StatisticCard
              key={item.title}
              statistic={{
                title: item.title,
                value: item.value,
                suffix: item.suffix,
              }}
            />
          ))}
        </StatisticCard.Group>
      )}

      <ProCard
        title={role === "admin" ? "管理员快捷入口" : "岗位快捷入口"}
        subTitle={role === "admin" ? "常用后台维护和诊断" : position ? `${positionLabel(position)}常用功能` : "未绑定岗位"}
        bordered
      >
        <Row gutter={[role === "admin" ? 12 : 8, role === "admin" ? 12 : 8]} className={role === "admin" ? undefined : "dashboardShortcutCompactGrid"}>
          {shortcuts.map((item) => (
            <Col xs={24} md={12} xl={8} key={item.view} className="dashboardShortcutCol">
              <Card size="small" className={role === "admin" ? "contextCard dashboardShortcutCard" : "contextCard dashboardShortcutCard compact"}>
                <div className="dashboardShortcutBody">
                  <Space className="dashboardShortcutTitle">
                    {item.icon}
                    <Tooltip title={item.description} placement="right">
                      <Text strong className="dashboardShortcutTitleText">{item.title}</Text>
                    </Tooltip>
                  </Space>
                  <Button
                    className="dashboardShortcutButton"
                    aria-label={`打开 ${item.title}`}
                    type="primary"
                    onClick={() => onNavigate(item.view)}
                  >
                    打开
                  </Button>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </ProCard>

      {role === "admin" ? (
        <DashboardOverviewSection
          role={role}
          erpOverview={erpOverview}
          erpDashboardMarket={erpDashboardMarket}
          setErpDashboardMarket={setErpDashboardMarket}
          erpDashboardDateRange={erpDashboardDateRange}
          setErpDashboardDateRange={setErpDashboardDateRange}
          erpDashboardStore={erpDashboardStore}
          setErpDashboardStore={setErpDashboardStore}
          refreshErpOverview={refreshErpOverview}
          onOpenRecordDetail={onOpenRecordDetail}
        />
      ) : null}

      {role !== "admin" ? (
        <ProCard title="岗位工作台" bordered>
          {position ? (
            <Space direction="vertical" size={12} style={{ width: "100%" }}>
              <Text type="secondary">当前岗位：{positionLabel(position)}</Text>
              <Row gutter={[12, 12]}>
                {positionConfigs[position].capabilities.map((item) => (
                  <Col xs={24} md={12} key={item} className="capabilityCardCol">
                    <Card size="small" className="contextCard capabilityCard">
                      <Text strong>{item}</Text>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Space>
          ) : (
            <Empty description="当前账号尚未绑定岗位" />
          )}
        </ProCard>
      ) : null}
    </Space>
  );
}

function DashboardOverviewSection({
  role,
  erpOverview,
  erpDashboardMarket,
  setErpDashboardMarket,
  erpDashboardDateRange,
  setErpDashboardDateRange,
  erpDashboardStore,
  setErpDashboardStore,
  refreshErpOverview,
  onOpenRecordDetail,
}: {
  role: Role;
  erpOverview: ErpDashboardOverviewResponse | null;
  erpDashboardMarket: DashboardMarket;
  setErpDashboardMarket: (value: DashboardMarket) => void;
  erpDashboardDateRange: DashboardDateRange;
  setErpDashboardDateRange: (value: DashboardDateRange) => void;
  erpDashboardStore: DashboardStore;
  setErpDashboardStore: (value: DashboardStore) => void;
  refreshErpOverview: () => void;
  onOpenRecordDetail: (resource: string, item: Record<string, unknown>) => void;
}) {
  const isEmployee = role !== "admin";
  const marketSelectOptions = dashboardMarketSelectOptions(erpOverview);

  return (
    <ProCard
      title={role === "admin" ? "平台数据概览" : "岗位数据概览"}
      subTitle={role === "admin" ? erpOverview?.message || "从 ERP 权限范围内加载关键数据" : undefined}
      bordered
      className={isEmployee ? "dashboardOverviewSection compact" : "dashboardOverviewSection"}
    >
      {erpOverview ? (
        <Space direction="vertical" size={isEmployee ? 12 : 16} className="pageStack">
          <div className={isEmployee ? "dashboardOverviewToolbar compact" : "dashboardOverviewToolbar"}>
            {role === "admin" ? (
              <Space size={8} wrap>
                <Text strong>{erpOverview.title}</Text>
                <Tag color="blue">{erpOverview.market_label}</Tag>
                <Tag color="geekblue">{erpOverview.store_label}</Tag>
                <Tag color="cyan">{erpOverview.date_range_label}</Tag>
              </Space>
            ) : null}
            <Space size={8} wrap>
              <Select<DashboardMarket>
                size="small"
                value={erpDashboardMarket}
                className="dashboardMarketSelect"
                options={marketSelectOptions}
                onChange={setErpDashboardMarket}
              />
              <Segmented<DashboardDateRange>
                size="small"
                value={erpDashboardDateRange}
                options={dashboardDateRangeOptions}
                onChange={setErpDashboardDateRange}
              />
              <Segmented<DashboardStore>
                size="small"
                value={erpDashboardStore}
                options={dashboardStoreOptions}
                onChange={setErpDashboardStore}
              />
              <Button size="small" icon={<ReloadOutlined />} onClick={refreshErpOverview}>
                刷新
              </Button>
            </Space>
          </div>

          <StatisticCard.Group
            direction="row"
            className={isEmployee ? "dashboardMetricGroup compact" : "dashboardMetricGroup"}
          >
            {erpOverview.metrics.map((item) => (
              <StatisticCard
                key={item.title}
                statistic={{
                  title: item.title,
                  value: item.value,
                  suffix: item.suffix,
                  status: metricStatus(item.status),
                  description: role === "admin" ? item.description : undefined,
                }}
              />
            ))}
          </StatisticCard.Group>

          {erpOverview.sections.length ? (
            <Row gutter={[12, 12]}>
              {erpOverview.sections.map((section) => (
                <Col xs={24} xl={8} key={section.resource} className="dashboardOverviewCol">
                  <Card
                    size="small"
                    className={isEmployee ? "contextCard dashboardOverviewCard compact" : "contextCard dashboardOverviewCard"}
                    title={
                      <Space size={6}>
                        <Text>{section.title}</Text>
                        {role === "admin" ? <Tag color={section.ok ? "green" : "gold"}>{section.status}</Tag> : null}
                      </Space>
                    }
                  >
                    <div className={isEmployee ? "dashboardOverviewBody compact" : "dashboardOverviewBody"}>
                      {role === "admin" ? (
                        <>
                          <Paragraph type="secondary" className="dashboardOverviewDescription">
                            {section.message}
                          </Paragraph>
                          <Space size={[6, 6]} wrap>
                            <Tag color="blue">匹配 {section.total_count} 条</Tag>
                            {section.amount_total !== null && section.amount_total !== undefined ? (
                              <Tag color="green">
                                {section.amount_label || "金额合计"} {formatAmount(section.amount_total)}
                              </Tag>
                            ) : null}
                          </Space>
                        </>
                      ) : section.amount_total !== null && section.amount_total !== undefined ? (
                        <Text className="dashboardOverviewAmount">
                          {section.amount_label || "金额合计"} {formatAmount(section.amount_total)}
                        </Text>
                      ) : null}
                      <div className={isEmployee ? "dashboardRecordList compact" : "dashboardRecordList"}>
                        {section.items.length ? (
                          section.items.slice(0, isEmployee ? 2 : 3).map((item, index) => (
                            <div className="compactRecord" key={`${section.resource}-${index}`}>
                              <div className="compactRecordHeader">
                                <Text strong className="compactRecordPrimary">{overviewPrimaryText(item)}</Text>
                                <Button
                                  size="small"
                                  type="link"
                                  aria-label={`查看 ${section.title} ERP 详情`}
                                  onClick={() => onOpenRecordDetail(section.resource, item)}
                                >
                                  详情
                                </Button>
                              </div>
                              {role === "admin" ? (
                                <Text type="secondary" className="compactRecordSecondary">
                                  {overviewSecondaryText(item)}
                                </Text>
                              ) : null}
                            </div>
                          ))
                        ) : (
                          <div className="dashboardOverviewEmpty">
                            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无记录" />
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          ) : null}
        </Space>
      ) : (
        <Empty description="暂无岗位数据概览，点击刷新重新加载" />
      )}
    </ProCard>
  );
}

function dashboardMarketSelectOptions(
  erpOverview: ErpDashboardOverviewResponse | null,
): Array<{ label: string; value: DashboardMarket }> {
  const options = erpOverview?.market_options?.length
    ? erpOverview.market_options
    : fallbackDashboardMarketOptions.map((item) => ({ ...item, count: 0 }));

  return options.map((item) => ({
    value: item.value,
    label: item.count > 0 ? `${item.label}（${item.count}）` : item.label,
  }));
}

function ChatPanel(props: {
  messageInput: string;
  setMessageInput: (value: string) => void;
  activeThread: ThreadListItem | null;
  activeThreadId: string;
  createThread: () => void;
  renameThread: (title: string) => Promise<boolean>;
  sendMessage: () => void;
  messages: ChatMessage[];
  isLoading: boolean;
  isCreatingThread: boolean;
  isRenamingThread: boolean;
  position: Position | null;
}) {
  const title = props.activeThread
    ? threadDisplayTitle(props.activeThread, "employee")
    : props.activeThreadId ? shortThreadId(props.activeThreadId) : "新会话";
  const titleDraftSource = props.activeThread?.title?.trim() || title;
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(titleDraftSource);

  useEffect(() => {
    if (!isEditingTitle) {
      setTitleDraft(titleDraftSource);
    }
  }, [isEditingTitle, titleDraftSource]);

  async function saveTitle() {
    const ok = await props.renameThread(titleDraft);
    if (ok) {
      setIsEditingTitle(false);
    }
  }

  return (
    <ProCard bordered className="chatWorkspace" bodyStyle={{ padding: 0, height: "100%" }}>
      <div className="chatMessagesPane">
        <MessageList messages={props.messages} />
      </div>

      <div className="chatComposerWrap">
        <div className="chatThreadBar">
          <Space size={8} className="chatThreadInfo">
            <MessageOutlined />
            <span className="chatThreadTitleGroup">
              {isEditingTitle ? (
                <Input
                  size="small"
                  className="chatThreadTitleInput"
                  value={titleDraft}
                  maxLength={120}
                  autoFocus
                  onChange={(event) => setTitleDraft(event.target.value)}
                  onPressEnter={() => void saveTitle()}
                />
              ) : (
                <Text strong className="chatThreadTitle">{title}</Text>
              )}
              {props.activeThreadId ? (
                isEditingTitle ? (
                  <>
                    <Button
                      size="small"
                      type="primary"
                      aria-label="保存会话标题"
                      loading={props.isRenamingThread}
                      disabled={!titleDraft.trim()}
                      onClick={() => void saveTitle()}
                    >
                      保存
                    </Button>
                    <Button
                      size="small"
                      aria-label="取消修改会话标题"
                      disabled={props.isRenamingThread}
                      onClick={() => {
                        setTitleDraft(titleDraftSource);
                        setIsEditingTitle(false);
                      }}
                    >
                      取消
                    </Button>
                  </>
                ) : (
                  <Tooltip title="修改会话标题">
                    <Button
                      size="small"
                      aria-label="修改会话标题"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setTitleDraft(titleDraftSource);
                        setIsEditingTitle(true);
                      }}
                    />
                  </Tooltip>
                )
              ) : null}
            </span>
            <Tag color={props.activeThreadId ? "blue" : "default"}>
              {props.activeThreadId ? "已保存" : "待创建"}
            </Tag>
          </Space>
          <Space size={8} className="chatThreadActions">
            {props.activeThreadId ? (
              <Tooltip title={props.activeThreadId}>
                <Text type="secondary" className="chatThreadReadonlyId">
                  {shortThreadId(props.activeThreadId)}
                </Text>
              </Tooltip>
            ) : null}
            <Button
              size="small"
              icon={<CommentOutlined />}
              loading={props.isCreatingThread}
              onClick={props.createThread}
            >
              新会话
            </Button>
          </Space>
        </div>
        <div className="chatComposer">
          <TextArea
            variant="borderless"
            placeholder="输入当前岗位权限内的问题，按按钮发送到后端"
            value={props.messageInput}
            onChange={(event) => props.setMessageInput(event.target.value)}
            autoSize={{ minRows: 3, maxRows: 8 }}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                props.sendMessage();
              }
            }}
          />
          <div className="chatComposerFooter">
            <Space size={8}>
              <Tag color="blue">SSE 流式</Tag>
              <Tag color="green">LangGraph</Tag>
              {props.position ? <Tag color="purple">{positionLabel(props.position)}</Tag> : null}
            </Space>
            <Button
              type="primary"
              shape="circle"
              icon={<CommentOutlined />}
              loading={props.isLoading}
              onClick={props.sendMessage}
            />
          </div>
        </div>
      </div>
    </ProCard>
  );
}

function UserSettingsPanel({
  username,
  displayName,
  email,
  role,
  position,
  profileForm,
  setProfileForm,
  passwordForm,
  setPasswordForm,
  loading,
  savingProfile,
  savingPassword,
  refreshSettings,
  saveProfile,
  savePassword,
}: {
  username: string;
  displayName: string;
  email: string;
  role: Role;
  position: Position | null;
  profileForm: UserProfileFormState;
  setProfileForm: React.Dispatch<React.SetStateAction<UserProfileFormState>>;
  passwordForm: UserPasswordFormState;
  setPasswordForm: React.Dispatch<React.SetStateAction<UserPasswordFormState>>;
  loading: boolean;
  savingProfile: boolean;
  savingPassword: boolean;
  refreshSettings: () => void;
  saveProfile: () => void;
  savePassword: () => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="userSettingsSummaryRow">
        <Col xs={24} lg={8}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">账号</Text>
            <Title level={3}>{username || "-"}</Title>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">显示名称</Text>
            <Title level={3}>{displayName || "未设置"}</Title>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">邮箱</Text>
            <Title level={3}>{email || "未设置"}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="账号资料"
        subTitle="账号不可修改；AI 邮件自动发送会读取这里设置的邮箱"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshSettings} loading={loading}>
            刷新
          </Button>
        }
      >
        <Form layout="vertical" className="userSettingsForm">
          <Form.Item label="账号">
            <Input value={username} disabled />
          </Form.Item>
          <Form.Item label="角色">
            <Input value={roleLabel(role)} disabled />
          </Form.Item>
          <Form.Item label="岗位">
            <Input value={position ? positionLabel(position) : "管理员"} disabled />
          </Form.Item>
          <Form.Item label="名称">
            <Input
              value={profileForm.displayName}
              maxLength={80}
              placeholder="例如：财务主管"
              onChange={(event) =>
                setProfileForm((current) => ({
                  ...current,
                  displayName: event.target.value,
                }))
              }
            />
          </Form.Item>
          <Form.Item label="邮箱">
            <Input
              value={profileForm.email}
              maxLength={180}
              placeholder="例如：finance@example.com"
              onChange={(event) =>
                setProfileForm((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
            />
          </Form.Item>
          <Form.Item className="userSettingsActions">
            <Button type="primary" icon={<EditOutlined />} loading={savingProfile} onClick={saveProfile}>
              保存资料
            </Button>
          </Form.Item>
        </Form>
      </ProCard>

      <ProCard title="修改密码" subTitle="修改后下一次登录请使用新密码" bordered>
        <Form layout="vertical" className="userSettingsForm password">
          <Form.Item label="当前密码">
            <Input.Password
              value={passwordForm.oldPassword}
              onChange={(event) =>
                setPasswordForm((current) => ({
                  ...current,
                  oldPassword: event.target.value,
                }))
              }
            />
          </Form.Item>
          <Form.Item label="新密码">
            <Input.Password
              value={passwordForm.newPassword}
              onChange={(event) =>
                setPasswordForm((current) => ({
                  ...current,
                  newPassword: event.target.value,
                }))
              }
            />
          </Form.Item>
          <Form.Item label="确认新密码">
            <Input.Password
              value={passwordForm.confirmPassword}
              onChange={(event) =>
                setPasswordForm((current) => ({
                  ...current,
                  confirmPassword: event.target.value,
                }))
              }
              onPressEnter={savePassword}
            />
          </Form.Item>
          <Form.Item className="userSettingsActions">
            <Button type="primary" loading={savingPassword} onClick={savePassword}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </ProCard>
    </Space>
  );
}

function AiAppsPanel({
  role,
  position,
  tasks,
  erpResources,
  pendingApprovals,
  chatMessageCount,
  allowedAiAppIds,
  onNavigate,
}: {
  role: Role;
  position: Position | null;
  tasks: AutomationTaskRecord[];
  erpResources: ErpResourceItem[];
  pendingApprovals: number;
  chatMessageCount: number;
  allowedAiAppIds: string[] | null;
  onNavigate: (view: View) => void;
}) {
  const apps = filterAiAppsByPermission(aiAppsForUser(role, position, tasks), role, allowedAiAppIds);
  const enabledApps = apps.filter((item) => item.status === "enabled").length;
  const metricColXl = role === "admin" ? 8 : 6;
  const visiblePositions = role === "admin"
    ? (["operations", "customer_service", "finance"] as Position[])
    : position ? [position] : [];

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="AI 应用中心"
        subTitle="统一查看企业内部 AI 自动化能力、岗位权限和可进入的工作台"
        bordered
      >
        <Row gutter={[12, 12]} className="aiAppMetricRow">
          <Col xs={24} md={12} xl={metricColXl}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">可见应用</Text>
              <Title level={3}>{apps.length}</Title>
              <Text type="secondary">按当前账号权限过滤</Text>
            </Card>
          </Col>
          <Col xs={24} md={12} xl={metricColXl}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">已启用</Text>
              <Title level={3}>{enabledApps}</Title>
              <Text type="secondary">现有功能入口可直接使用</Text>
            </Card>
          </Col>
          <Col xs={24} md={12} xl={metricColXl}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">ERP 资源</Text>
              <Title level={3}>{erpResources.length}</Title>
              <Text type="secondary">来自真实岗位 ERP scope</Text>
            </Card>
          </Col>
          {role !== "admin" ? (
            <Col xs={24} md={12} xl={6}>
              <Card size="small" className="aiAppMetricCard">
                <Text type="secondary">待处理审批</Text>
                <Title level={3}>{pendingApprovals}</Title>
                <Text type="secondary">{position === "customer_service" ? "客服可进入退款审批处理" : "当前账号可处理的审批"}</Text>
              </Card>
            </Col>
          ) : null}
        </Row>
      </ProCard>

      <ProCard
        title="岗位应用目录"
        subTitle={role === "admin" ? "执行数据已接入运行记录页面；应用目录保留为岗位能力入口" : "应用目录保留为岗位能力入口"}
        bordered
      >
        {apps.length ? (
          <Row gutter={[12, 12]}>
            {apps.map((app) => (
              <Col xs={24} lg={12} xl={8} key={app.id} className="aiAppCardCol">
                <Card size="small" className="contextCard aiAppCard">
                  <div className="aiAppCardBody">
                    <div className="aiAppHeader">
                      <Space size={8} className="aiAppTitleWrap">
                        <AppstoreOutlined />
                        <Tooltip title={app.description} placement="topLeft">
                          <Text strong className="aiAppTitle tooltipTitle">{app.name}</Text>
                        </Tooltip>
                      </Space>
                      <Tag color={app.status === "enabled" ? "green" : "gold"}>
                        {app.status === "enabled" ? "已启用" : "规划中"}
                      </Tag>
                    </div>
                    <div className="aiAppMetaGrid">
                      <div>
                        <Text type="secondary">岗位</Text>
                        <Text strong>{app.positionLabel}</Text>
                      </div>
                      <div>
                        <Text type="secondary">类别</Text>
                        <Text strong>{app.category}</Text>
                      </div>
                      <div>
                        <Text type="secondary">负责人</Text>
                        <Text strong>{app.owner}</Text>
                      </div>
                      <div>
                        <Text type="secondary">运行数据</Text>
                        <Text strong>待接入</Text>
                      </div>
                    </div>
                    <Space size={[6, 6]} wrap className="aiAppSourceList">
                      {app.dataSources.map((item) => (
                        <Tag key={`${app.id}-${item}`}>{item}</Tag>
                      ))}
                    </Space>
                    <div className="aiAppFooter">
                      <Button
                        type="primary"
                        onClick={() => onNavigate(app.entryView)}
                        disabled={app.status !== "enabled"}
                      >
                        {app.entryLabel}
                      </Button>
                    </div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description="当前账号暂无可用 AI 应用，请联系管理员分配岗位" />
        )}
      </ProCard>

      <ProCard title="岗位权限视图" bordered>
        {visiblePositions.length ? (
          <Row gutter={[12, 12]}>
            {visiblePositions.map((item) => {
              const config = positionConfigs[item];
              const taskCount = tasks.filter((task) => task.position === item).length;

              return (
                <Col xs={24} xl={8} key={item} className="aiAppRoleCol">
                  <Card size="small" className="contextCard aiAppRoleCard">
                    <div className="aiAppRoleBody">
                      <Space size={8}>
                        <Tag color="blue">{config.label}</Tag>
                        <Text strong>{config.department}</Text>
                      </Space>
                      <Paragraph type="secondary" className="aiAppRoleDescription">
                        已接入 {taskCount} 个岗位自动化任务，允许访问 {config.erpScopes.length} 类 ERP 资源。
                      </Paragraph>
                      <Space size={[6, 6]} wrap>
                        {config.erpScopes.map((scope) => (
                          <Tag key={`${item}-${scope}`} color="geekblue">
                            {scope}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
        ) : (
          <Empty description="当前账号尚未绑定岗位" />
        )}
      </ProCard>

      {chatMessageCount > 0 ? (
        <Text type="secondary">当前浏览器会话已加载 {chatMessageCount} 条聊天消息，可在 AI 对话或会话详情继续查看。</Text>
      ) : null}
    </Space>
  );
}

function AiWorkflowsPanel({
  role,
  workflows,
  filters,
  setFilters,
  selectedWorkflowId,
  inputs,
  setInputs,
  runResult,
  loading,
  runningWorkflowId,
  refreshWorkflows,
  runWorkflow,
  openDetail,
  onNavigate,
}: {
  role: Role;
  workflows: AiWorkflowItem[];
  filters: AiWorkflowFilterState;
  setFilters: React.Dispatch<React.SetStateAction<AiWorkflowFilterState>>;
  selectedWorkflowId: string | null;
  inputs: Record<string, string>;
  setInputs: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  runResult: AiWorkflowRunResponse | null;
  loading: boolean;
  runningWorkflowId: string;
  refreshWorkflows: () => void;
  runWorkflow: (workflowId: string) => void;
  openDetail: (workflowId: string) => void;
  onNavigate: (view: View) => void;
}) {
  const visibleWorkflows = filterAiWorkflows(workflows, filters);
  const categories = Array.from(new Set(workflows.map((item) => item.category))).filter(Boolean);
  const executableCount = visibleWorkflows.filter((item) => item.executable).length;
  const approvalCount = visibleWorkflows.filter((item) => item.requires_approval).length;
  const savedMinutes = visibleWorkflows.reduce((total, item) => total + item.saved_minutes, 0);
  const groupedWorkflows = groupAiWorkflows(visibleWorkflows);
  const selectedWorkflow = selectedWorkflowId
    ? workflows.find((item) => item.id === selectedWorkflowId) || null
    : null;
  const scopedRunResult = selectedWorkflowId && runResult?.workflow.id !== selectedWorkflowId
    ? null
    : runResult;

  if (selectedWorkflowId) {
    if (!selectedWorkflow) {
      return (
        <ProCard
          title="AI 工作流详情"
          subTitle="当前页面按左侧子菜单独立展示一个工作流"
          bordered
          extra={
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshWorkflows} loading={loading}>
              刷新
            </Button>
          }
        >
          <Empty description={loading ? "正在加载 AI 工作流" : "当前账号无权查看该 AI 工作流，或数据尚未加载"} />
        </ProCard>
      );
    }

    const inputValue = inputs[selectedWorkflow.id] || "";
    const targetView = workflowEntryViewForWorkflow(selectedWorkflow);
    const automatedStageCount = selectedWorkflow.stages.filter((stage) => stage.automated).length;

    return (
      <Space direction="vertical" size={16} className="pageStack">
        <div className="aiWorkflowFocusedHero">
          <div className="aiWorkflowFocusedMain">
            <Space size={[8, 8]} wrap>
              <Tag color="blue">{selectedWorkflow.position_label}</Tag>
              <Tag color="geekblue">{selectedWorkflow.category}</Tag>
              <Tag color={selectedWorkflow.executable ? "green" : "gold"}>
                {selectedWorkflow.executable ? "可直接运行" : "专用入口"}
              </Tag>
              <Tag color={selectedWorkflow.requires_approval ? "gold" : "cyan"}>
                {selectedWorkflow.requires_approval ? "需审批" : "无需审批"}
              </Tag>
            </Space>
            <Title level={3} className="aiWorkflowFocusedTitle">{selectedWorkflow.name}</Title>
            <Paragraph className="aiWorkflowFocusedScenario">{selectedWorkflow.scenario}</Paragraph>
          </div>
          <div className="aiWorkflowFocusedActions">
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshWorkflows} loading={loading}>
              刷新
            </Button>
            <Button size="small" onClick={() => openDetail(selectedWorkflow.id)}>
              详情
            </Button>
          </div>
        </div>

        <div className="aiWorkflowFocusedMetricGrid">
          <div>
            <Text type="secondary">执行模式</Text>
            <Text strong>{executionModeLabel(selectedWorkflow.execution_mode)}</Text>
          </div>
          <div>
            <Text type="secondary">自动阶段</Text>
            <Text strong>{automatedStageCount} / {selectedWorkflow.stages.length}</Text>
          </div>
          <div>
            <Text type="secondary">预计节省</Text>
            <Text strong>{selectedWorkflow.saved_minutes} 分钟</Text>
          </div>
          <div>
            <Text type="secondary">版本</Text>
            <Text strong>{selectedWorkflow.version}</Text>
          </div>
        </div>

        <Row gutter={[12, 12]}>
          <Col xs={24} lg={12}>
            <ProCard title="业务场景" bordered>
              <Paragraph className="aiWorkflowDetailPreview">{selectedWorkflow.scenario}</Paragraph>
              <Paragraph className="aiWorkflowDetailPreview compact">{selectedWorkflow.business_value}</Paragraph>
            </ProCard>
          </Col>
          <Col xs={24} lg={12}>
            <ProCard title="输出与审批" bordered>
              <Paragraph className="aiWorkflowDetailPreview">{selectedWorkflow.output_contract}</Paragraph>
              <Paragraph className="aiWorkflowDetailPreview compact">{selectedWorkflow.approval_policy}</Paragraph>
            </ProCard>
          </Col>
        </Row>

        <ProCard title="步骤链路" bordered>
          <Table
            rowKey="key"
            size="small"
            dataSource={selectedWorkflow.stages}
            pagination={false}
            scroll={{ x: 760 }}
            columns={[
              { title: "阶段", dataIndex: "label", width: 120, render: (value) => <Text strong>{String(value)}</Text> },
              { title: "自动化", dataIndex: "automated", width: 96, render: (value) => <Tag color={value ? "green" : "default"}>{value ? "自动" : "人工"}</Tag> },
              { title: "说明", dataIndex: "description", render: (value) => <Text className="aiWorkflowText">{String(value)}</Text> },
            ]}
          />
        </ProCard>

        <Row gutter={[12, 12]}>
          <Col xs={24} lg={12}>
            <ProCard title="工具与 ERP" bordered>
              <Space direction="vertical" size={12} className="pageStack">
                <div>
                  <Text type="secondary">允许工具</Text>
                  <Space size={[6, 6]} wrap className="aiWorkflowTagBlock">
                    {selectedWorkflow.tools.map((item) => (
                      <Tag color="blue" key={item}>{item}</Tag>
                    ))}
                  </Space>
                </div>
                <div>
                  <Text type="secondary">ERP 资源</Text>
                  <Space size={[6, 6]} wrap className="aiWorkflowTagBlock">
                    {selectedWorkflow.erp_resources.map((item) => (
                      <Tag color="geekblue" key={item}>{item}</Tag>
                    ))}
                  </Space>
                </div>
                <div className="aiWorkflowFocusedInfoGrid">
                  <AiWorkflowDetailItem label="写回目标" value={selectedWorkflow.writeback_target} />
                  <AiWorkflowDetailItem label="通知目标" value={selectedWorkflow.notification_target} />
                </div>
              </Space>
            </ProCard>
          </Col>
          <Col xs={24} lg={12}>
            <ProCard title="运行区" bordered>
              <Space direction="vertical" size={12} className="pageStack">
                {selectedWorkflow.executable ? (
                  <>
                    <TextArea
                      className="aiWorkflowFocusedInput"
                      value={inputValue}
                      placeholder={selectedWorkflow.input_placeholder}
                      autoSize={false}
                      rows={6}
                      onChange={(event) =>
                        setInputs((current) => ({
                          ...current,
                          [selectedWorkflow.id]: event.target.value,
                        }))
                      }
                    />
                    <div className="aiWorkflowFooter">
                      {role === "admin" ? (
                        <Button onClick={() => onNavigate("run_records")} icon={<HistoryOutlined />}>
                          运行记录
                        </Button>
                      ) : null}
                      <Button
                        type="primary"
                        icon={<SendOutlined />}
                        aria-label={`运行${selectedWorkflow.name}`}
                        loading={runningWorkflowId === selectedWorkflow.id}
                        onClick={() => runWorkflow(selectedWorkflow.id)}
                      >
                        运行工作流
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <Paragraph className="aiWorkflowFocusedExternalHint">
                      {selectedWorkflow.output_contract}
                    </Paragraph>
                    <div className="aiWorkflowFooter">
                      {role === "admin" ? (
                        <Button onClick={() => onNavigate("run_records")} icon={<HistoryOutlined />}>
                          运行记录
                        </Button>
                      ) : null}
                      <Button
                        type="primary"
                        icon={<CloudUploadOutlined />}
                        onClick={() => onNavigate(targetView)}
                      >
                        {selectedWorkflow.entry_label}
                      </Button>
                    </div>
                  </>
                )}
              </Space>
            </ProCard>
          </Col>
        </Row>

        {scopedRunResult ? (
          <AiWorkflowRunResultCard
            runResult={scopedRunResult}
            canViewRunRecords={role === "admin"}
            onNavigate={onNavigate}
          />
        ) : null}
      </Space>
    );
  }

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="aiWorkflowMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="aiWorkflowMetricCard">
            <Text type="secondary">可见工作流</Text>
            <Title level={3}>{visibleWorkflows.length}</Title>
            <Text type="secondary">按当前账号权限过滤</Text>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="aiWorkflowMetricCard">
            <Text type="secondary">可直接运行</Text>
            <Title level={3}>{executableCount}</Title>
            <Text type="secondary">调用真实 LLM/ERP 能力</Text>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="aiWorkflowMetricCard">
            <Text type="secondary">需人工审批</Text>
            <Title level={3}>{approvalCount}</Title>
            <Text type="secondary">退款/工资等高风险场景</Text>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="aiWorkflowMetricCard">
            <Text type="secondary">预计节省</Text>
            <Title level={3}>{savedMinutes}</Title>
            <Text type="secondary">分钟 / 单次完整处理</Text>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="AI 工作流中心"
        subTitle={role === "admin" ? "管理员查看全部岗位工作流，执行时仍按工作流岗位限制 ERP 资源" : "当前账号只能查看和运行自己岗位的工作流"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshWorkflows} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className={role === "admin" ? "aiWorkflowFilterGrid admin" : "aiWorkflowFilterGrid"}>
          {role === "admin" ? (
            <Select
              size="small"
              value={filters.position}
              onChange={(value) => setFilters((current) => ({ ...current, position: value }))}
              options={[
                { label: "全部岗位", value: "all" },
                { label: "运营", value: "operations" },
                { label: "客服", value: "customer_service" },
                { label: "财务", value: "finance" },
              ]}
            />
          ) : null}
          <Select
            size="small"
            allowClear
            value={filters.category || undefined}
            placeholder="工作流类别"
            onChange={(value) => setFilters((current) => ({ ...current, category: value || "" }))}
            options={categories.map((item) => ({ label: item, value: item }))}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshWorkflows} loading={loading}>
            查询
          </Button>
        </div>

        {visibleWorkflows.length ? (
          <Space direction="vertical" size={16} className="pageStack">
            {groupedWorkflows.map((group) => (
              <div className="aiWorkflowGroupBlock" key={group.key}>
                <Space size={8} className="aiWorkflowGroupTitle">
                  <Tag color="blue">{group.label}</Tag>
                  <Text type="secondary">{group.items.length} 个工作流</Text>
                </Space>
                <Row gutter={[12, 12]}>
                  {group.items.map((workflow) => {
                    const inputValue = inputs[workflow.id] || "";
                    const targetView = workflowEntryViewForWorkflow(workflow);

                    return (
                      <Col xs={24} xl={12} xxl={8} key={workflow.id} className="aiWorkflowCardCol">
                        <Card size="small" className="contextCard aiWorkflowCard">
                          <div className="aiWorkflowCardBody">
                            <div className="aiWorkflowHeader">
                              <Space size={8} className="aiWorkflowTitleWrap">
                                <RobotOutlined />
                                <Tooltip title={workflow.scenario} placement="topLeft">
                                  <Text strong className="aiWorkflowTitle tooltipTitle">{workflow.name}</Text>
                                </Tooltip>
                              </Space>
                              <Tag color={workflow.executable ? "green" : "gold"}>
                                {workflow.executable ? "可运行" : "专用入口"}
                              </Tag>
                            </div>

                            <div className="aiWorkflowMetaGrid">
                              <div>
                                <Text type="secondary">岗位</Text>
                                <Text strong>{workflow.position_label}</Text>
                              </div>
                              <div>
                                <Text type="secondary">类别</Text>
                                <Text strong>{workflow.category}</Text>
                              </div>
                              <div>
                                <Text type="secondary">模式</Text>
                                <Text strong>{executionModeLabel(workflow.execution_mode)}</Text>
                              </div>
                              <div>
                                <Text type="secondary">节省</Text>
                                <Text strong>{workflow.saved_minutes} 分钟</Text>
                              </div>
                            </div>

                            <div className="aiWorkflowStageList">
                              {workflow.stages.map((stage) => (
                                <div className="aiWorkflowStageItem" key={`${workflow.id}-${stage.key}`}>
                                  <Text strong>{stage.label}</Text>
                                  <Tag color={stage.automated ? "green" : "default"}>
                                    {stage.automated ? "自动" : "人工"}
                                  </Tag>
                                </div>
                              ))}
                            </div>

                            <Space size={[6, 6]} wrap className="aiWorkflowTagList">
                              <Tag color="purple">{workflowAutomationLevelLabel(workflow.automation_level)}</Tag>
                              <Tag color={workflow.requires_approval ? "gold" : "blue"}>
                                {workflow.requires_approval ? "需审批" : "无需审批"}
                              </Tag>
                              {workflow.erp_resources.slice(0, 3).map((resource) => (
                                <Tag key={`${workflow.id}-${resource}`} color="geekblue">{resource}</Tag>
                              ))}
                            </Space>

                            <div className="aiWorkflowRunBox">
                              {workflow.executable ? (
                                <>
                                  <TextArea
                                    className="aiWorkflowInput"
                                    value={inputValue}
                                    placeholder={workflow.input_placeholder}
                                    autoSize={false}
                                    rows={4}
                                    onChange={(event) =>
                                      setInputs((current) => ({
                                        ...current,
                                        [workflow.id]: event.target.value,
                                      }))
                                    }
                                  />
                                  <div className="aiWorkflowFooter">
                                    <Button size="small" onClick={() => openDetail(workflow.id)}>
                                      详情
                                    </Button>
                                    <Button
                                      size="small"
                                      type="primary"
                                      icon={<SendOutlined />}
                                      aria-label={`运行${workflow.name}`}
                                      loading={runningWorkflowId === workflow.id}
                                      onClick={() => runWorkflow(workflow.id)}
                                    >
                                      运行工作流
                                    </Button>
                                  </div>
                                </>
                              ) : (
                                <>
                                  <Paragraph className="aiWorkflowExternalHint">
                                    {workflow.output_contract}
                                  </Paragraph>
                                  <div className="aiWorkflowFooter">
                                    <Button size="small" onClick={() => openDetail(workflow.id)}>
                                      详情
                                    </Button>
                                    <Button
                                      size="small"
                                      type="primary"
                                      icon={<CloudUploadOutlined />}
                                      onClick={() => onNavigate(targetView)}
                                    >
                                      {workflow.entry_label}
                                    </Button>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </Card>
                      </Col>
                    );
                  })}
                </Row>
              </div>
            ))}
          </Space>
        ) : (
          <Empty description="当前筛选条件下暂无 AI 工作流" />
        )}
      </ProCard>

      {scopedRunResult ? (
        <AiWorkflowRunResultCard
          runResult={scopedRunResult}
          canViewRunRecords={role === "admin"}
          onNavigate={onNavigate}
        />
      ) : null}
    </Space>
  );
}

function AiWorkflowRunResultCard({
  runResult,
  canViewRunRecords,
  onNavigate,
}: {
  runResult: AiWorkflowRunResponse;
  canViewRunRecords: boolean;
  onNavigate: (view: View) => void;
}) {
  return (
    <ProCard
      title="最近运行结果"
      subTitle={`${runResult.workflow.name} / ${formatTime(runResult.created_at)}`}
      bordered
      extra={canViewRunRecords ? (
        <Button size="small" icon={<HistoryOutlined />} onClick={() => onNavigate("run_records")}>
          运行记录
        </Button>
      ) : null}
    >
      <Space direction="vertical" size={12} className="pageStack">
        <Space size={[8, 8]} wrap>
          <StatusTag value={runResult.status} />
          <Tag color="blue">Run ID：{runResult.run_id}</Tag>
          {runResult.platform_draft ? (
            <Tag color="green">已保存平台草稿</Tag>
          ) : null}
          <Tag color={runResult.erp_references.length ? "geekblue" : "default"}>
            ERP 引用 {runResult.erp_references.length}
          </Tag>
        </Space>
        {runResult.platform_draft ? (
          <PlatformDraftSummary draft={runResult.platform_draft} />
        ) : null}
        <Table<AiWorkflowRunStep>
          rowKey={(record) => `${record.step_order}-${record.step_name}`}
          size="small"
          dataSource={runResult.steps}
          pagination={false}
          scroll={{ x: 620 }}
          columns={[
            { title: "顺序", dataIndex: "step_order", width: 70 },
            { title: "步骤", dataIndex: "step_name", render: (value) => <Text className="aiWorkflowMono">{String(value)}</Text> },
            { title: "状态", dataIndex: "status", width: 100, render: (value) => <StatusTag value={String(value)} /> },
            { title: "耗时", dataIndex: "duration_ms", width: 100, render: (value) => formatDuration(value) },
          ]}
        />
        {runResult.erp_references.length ? (
          <Space size={[6, 6]} wrap>
            {runResult.erp_references.map((reference) => (
              <Tag color="geekblue" key={`${reference.resource}-${reference.record_id}`}>
                {reference.resource_label} / {reference.record_id}
              </Tag>
            ))}
          </Space>
        ) : null}
        <Paragraph className="aiWorkflowAnswer">{runResult.answer}</Paragraph>
      </Space>
    </ProCard>
  );
}

function PlatformDraftSummary({ draft }: { draft: PlatformDraftItem }) {
  const [currentDraft, setCurrentDraft] = useState(draft);
  const [latestExecution, setLatestExecution] = useState<PlatformActionExecutionItem | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  useEffect(() => {
    setCurrentDraft(draft);
    setLatestExecution(null);
  }, [draft]);

  const runExternalWriteback = async () => {
    const storedToken = localStorage.getItem("access_token") || "";
    if (!storedToken) {
      message.warning("请先登录");
      return;
    }

    setIsExecuting(true);
    try {
      const result = await executePlatformDraft(storedToken, currentDraft.id);
      setCurrentDraft(result.draft);
      setLatestExecution(result.execution);
      if (result.execution.status === "succeeded") {
        message.success("外部写回执行成功");
      } else if (result.execution.status === "waiting_executor") {
        message.info("已进入等待外部执行器状态");
      } else {
        message.error(result.message || "外部写回执行失败");
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : "外部写回执行失败");
    } finally {
      setIsExecuting(false);
    }
  };

  const metadataExecutionStatus = textFromUnknown(currentDraft.metadata.latest_execution_status || "");
  const metadataExecutionId = textFromUnknown(currentDraft.metadata.latest_execution_id || "");
  const latestStatus = latestExecution?.status || metadataExecutionStatus;
  const latestExecutionId = latestExecution?.id || metadataExecutionId;

  return (
    <Card
      size="small"
      title="平台草稿写回"
      className="contextCard"
      extra={
        <Button
          size="small"
          icon={<CloudUploadOutlined />}
          loading={isExecuting}
          onClick={runExternalWriteback}
        >
          执行外部写回
        </Button>
      }
    >
      <div className="platformDraftSummaryGrid">
        <DetailText label="草稿 ID" value={currentDraft.id} mono />
        <DetailText label="类型" value={platformDraftTypeLabel(currentDraft.draft_type)} />
        <DetailText label="状态" value={platformDraftStatusLabel(currentDraft.status)} />
        <DetailText label="写回目标" value={currentDraft.external_target} mono />
        <DetailText label="写回状态" value={platformDraftWritebackLabel(currentDraft.writeback_status)} />
        <DetailText label="平台" value={currentDraft.platform} />
      </div>
      {latestStatus ? (
        <Space size={[6, 6]} wrap className="platformExecutionStatus">
          <Tag color={platformExecutionStatusColor(latestStatus)}>
            执行：{platformExecutionStatusLabel(latestStatus)}
          </Tag>
          {latestExecutionId ? <Tag>执行 ID：{latestExecutionId}</Tag> : null}
          {latestExecution?.executor_type ? <Tag>{platformExecutorTypeLabel(latestExecution.executor_type)}</Tag> : null}
        </Space>
      ) : null}
      {currentDraft.writeback_message ? (
        <Paragraph className="automationTaskResultText">{currentDraft.writeback_message}</Paragraph>
      ) : null}
    </Card>
  );
}

function AiWorkflowDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: AiWorkflowDetailResponse | null;
  onClose: () => void;
}) {
  const workflow = detail?.item || null;

  return (
    <Modal
      open={open}
      title={workflow ? `AI 工作流 / ${workflow.name}` : "AI 工作流"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width="min(980px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载 AI 工作流详情" />
      ) : workflow ? (
        <Tabs
          className="aiWorkflowDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <div className="aiWorkflowDetailGrid">
                  <AiWorkflowDetailItem label="工作流 ID" value={workflow.id} mono />
                  <AiWorkflowDetailItem label="版本" value={workflow.version} mono />
                  <AiWorkflowDetailItem label="岗位" value={workflow.position_label} />
                  <AiWorkflowDetailItem label="类别" value={workflow.category} />
                  <AiWorkflowDetailItem label="触发方式" value={workflowTriggerLabel(workflow.trigger_type)} />
                  <AiWorkflowDetailItem label="执行模式" value={executionModeLabel(workflow.execution_mode)} />
                  <AiWorkflowDetailItem label="审批" value={workflow.requires_approval ? "需要审批" : "无需审批"} />
                  <AiWorkflowDetailItem label="预计节省" value={`${workflow.saved_minutes} 分钟`} />
                </div>
              ),
            },
            {
              key: "scenario",
              label: "场景",
              children: (
                <Row gutter={[12, 12]} className="aiWorkflowDetailTabGrid">
                  <Col xs={24} md={12}>
                    <Card title="业务场景" size="small" className="aiWorkflowDetailSectionCard">
                      <Paragraph className="aiWorkflowDetailPreview">{workflow.scenario}</Paragraph>
                      <Paragraph className="aiWorkflowDetailPreview compact">{workflow.business_value}</Paragraph>
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="输出与审批" size="small" className="aiWorkflowDetailSectionCard">
                      <Paragraph className="aiWorkflowDetailPreview">{workflow.output_contract}</Paragraph>
                      <Paragraph className="aiWorkflowDetailPreview compact">{workflow.approval_policy}</Paragraph>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "stages",
              label: `步骤 ${workflow.stages.length}`,
              children: (
                <Table
                  rowKey="key"
                  size="small"
                  dataSource={workflow.stages}
                  pagination={false}
                  scroll={{ x: 760 }}
                  columns={[
                    { title: "阶段", dataIndex: "label", width: 110, render: (value) => <Text strong>{String(value)}</Text> },
                    {
                      title: "自动化",
                      dataIndex: "automated",
                      width: 96,
                      render: (value) => <Tag color={value ? "green" : "default"}>{value ? "自动" : "人工"}</Tag>,
                    },
                    {
                      title: "说明",
                      dataIndex: "description",
                      render: (value) => <Text className="aiWorkflowText">{String(value)}</Text>,
                    },
                  ]}
                />
              ),
            },
            {
              key: "resources",
              label: "资源写回",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <Row gutter={[12, 12]} className="aiWorkflowDetailTabGrid">
                    <Col xs={24} md={8}>
                      <Card title="允许工具" size="small" className="aiWorkflowDetailSectionCard">
                        <Space size={[6, 6]} wrap className="aiWorkflowTagBlock">
                          {workflow.tools.map((item) => (
                            <Tag color="blue" key={item}>{item}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="ERP 资源" size="small" className="aiWorkflowDetailSectionCard">
                        <Space size={[6, 6]} wrap className="aiWorkflowTagBlock">
                          {workflow.erp_resources.map((item) => (
                            <Tag color="geekblue" key={item}>{item}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="入口" size="small" className="aiWorkflowDetailSectionCard">
                        <Paragraph className="aiWorkflowDetailPreview compact">
                          {workflow.entry_label} / {workflow.entry_view}
                        </Paragraph>
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={[12, 12]} className="aiWorkflowDetailTabGrid">
                    <Col xs={24} md={12}>
                      <Card title="写回目标" size="small" className="aiWorkflowDetailSectionCard">
                        <Paragraph className="aiWorkflowDetailPreview compact">{workflow.writeback_target}</Paragraph>
                      </Card>
                    </Col>
                    <Col xs={24} md={12}>
                      <Card title="通知目标" size="small" className="aiWorkflowDetailSectionCard">
                        <Paragraph className="aiWorkflowDetailPreview compact">{workflow.notification_target}</Paragraph>
                      </Card>
                    </Col>
                  </Row>
                </Space>
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一个 AI 工作流" />
      )}
    </Modal>
  );
}

function AiWorkflowDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="aiWorkflowDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "aiWorkflowMono" : "aiWorkflowText"}>{value}</Text>
    </div>
  );
}

function AutomationPanel({
  role,
  position,
  selectedPosition,
  selectedTaskId,
  selectedFinanceTool,
  tasks,
  financeReportFiles,
  setFinanceReportFiles,
  financeReportInstruction,
  setFinanceReportInstruction,
  financeReportOutputFormat,
  setFinanceReportOutputFormat,
  financeReportSummary,
  isAnalyzingFinanceReport,
  financeExcelFile,
  setFinanceExcelFile,
  financeExcelInstruction,
  setFinanceExcelInstruction,
  financeExcelErpResources,
  setFinanceExcelErpResources,
  erpResources,
  isTransformingFinanceExcel,
  financeSalaryMessage,
  setFinanceSalaryMessage,
  financeSalaryExportSummary,
  isExportingFinanceSalary,
  financeReconciliationFiles,
  setFinanceReconciliationFiles,
  financeReconciliationInstruction,
  setFinanceReconciliationInstruction,
  financeReconciliationCurrency,
  setFinanceReconciliationCurrency,
  isReconcilingFinance,
  onGenerate,
  onAnalyzeFinanceReport,
  onTransformFinanceExcel,
  onExportFinanceSalary,
  onReconcileFinanceFiles,
  onNavigate,
  onInputChange,
  loadingTaskId,
}: {
  role: Role;
  position: Position | null;
  selectedPosition: Position | null;
  selectedTaskId: string | null;
  selectedFinanceTool: FinanceAutomationTool | null;
  tasks: AutomationTaskRecord[];
  financeReportFiles: File[];
  setFinanceReportFiles: React.Dispatch<React.SetStateAction<File[]>>;
  financeReportInstruction: string;
  setFinanceReportInstruction: (value: string) => void;
  financeReportOutputFormat: "word" | "excel";
  setFinanceReportOutputFormat: (value: "word" | "excel") => void;
  financeReportSummary: string;
  isAnalyzingFinanceReport: boolean;
  financeExcelFile: File | null;
  setFinanceExcelFile: (value: File | null) => void;
  financeExcelInstruction: string;
  setFinanceExcelInstruction: (value: string) => void;
  financeExcelErpResources: string[];
  setFinanceExcelErpResources: (value: string[]) => void;
  erpResources: ErpResourceItem[];
  isTransformingFinanceExcel: boolean;
  financeSalaryMessage: string;
  setFinanceSalaryMessage: (value: string) => void;
  financeSalaryExportSummary: string;
  isExportingFinanceSalary: boolean;
  financeReconciliationFiles: File[];
  setFinanceReconciliationFiles: React.Dispatch<React.SetStateAction<File[]>>;
  financeReconciliationInstruction: string;
  setFinanceReconciliationInstruction: (value: string) => void;
  financeReconciliationCurrency: string;
  setFinanceReconciliationCurrency: (value: string) => void;
  isReconcilingFinance: boolean;
  onGenerate: (taskId: string, inputText: string) => void;
  onAnalyzeFinanceReport: () => void;
  onTransformFinanceExcel: () => void;
  onExportFinanceSalary: () => void;
  onReconcileFinanceFiles: () => void;
  onNavigate: (view: View) => void;
  onInputChange: (taskId: string, value: string) => void;
  loadingTaskId: string;
}) {
  const positions = selectedPosition ? [selectedPosition] : [];

  if (positions.length === 0) {
    return (
      <ProCard title="岗位应用" bordered>
        <Empty description="当前账号尚未绑定岗位，请联系管理员分配岗位" />
      </ProCard>
    );
  }

  const activePosition = positions[0];
  const config = positionConfigs[activePosition];
  const visibleTasks = tasks.filter((task) => task.position === activePosition);
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title={`${config.label} AI 自动化`}
        subTitle={role === "admin" ? `管理员预览 ${config.label} 岗位能力` : `ERP 权限范围：${config.erpScopes.join("、")}`}
        bordered
      >
        <Space size={[6, 6]} wrap>
          <Tag color="blue">{config.department}</Tag>
          {config.erpScopes.map((scope) => (
            <Tag color="geekblue" key={`${activePosition}-${scope}`}>{scope}</Tag>
          ))}
        </Space>
      </ProCard>

      {selectedFinanceTool === "report_analysis" ? (
        <FinanceReportAnalysisDetail
          financeReportFiles={financeReportFiles}
          setFinanceReportFiles={setFinanceReportFiles}
          financeReportInstruction={financeReportInstruction}
          setFinanceReportInstruction={setFinanceReportInstruction}
          financeReportOutputFormat={financeReportOutputFormat}
          setFinanceReportOutputFormat={setFinanceReportOutputFormat}
          financeReportSummary={financeReportSummary}
          isAnalyzingFinanceReport={isAnalyzingFinanceReport}
          onAnalyzeFinanceReport={onAnalyzeFinanceReport}
        />
      ) : selectedFinanceTool === "salary_export" ? (
        <FinanceSalaryExportDetail
          financeSalaryMessage={financeSalaryMessage}
          setFinanceSalaryMessage={setFinanceSalaryMessage}
          financeSalaryExportSummary={financeSalaryExportSummary}
          isExportingFinanceSalary={isExportingFinanceSalary}
          onExportFinanceSalary={onExportFinanceSalary}
        />
      ) : selectedTaskId ? (
        <AutomationTaskDetail
          task={visibleTasks.find((task) => task.task_id === selectedTaskId) || null}
          loadingTaskId={loadingTaskId}
          onGenerate={onGenerate}
          onInputChange={onInputChange}
        />
      ) : selectedFinanceTool === "excel_upload" ? (
        <FinanceExcelUploadDetail
          financeExcelFile={financeExcelFile}
          setFinanceExcelFile={setFinanceExcelFile}
          financeExcelInstruction={financeExcelInstruction}
          setFinanceExcelInstruction={setFinanceExcelInstruction}
          financeExcelErpResources={financeExcelErpResources}
          setFinanceExcelErpResources={setFinanceExcelErpResources}
          erpResources={erpResources}
          isTransformingFinanceExcel={isTransformingFinanceExcel}
          onTransformFinanceExcel={onTransformFinanceExcel}
        />
      ) : selectedFinanceTool === "reconciliation" ? (
        <FinanceReconciliationDetail
          financeReconciliationFiles={financeReconciliationFiles}
          setFinanceReconciliationFiles={setFinanceReconciliationFiles}
          financeReconciliationInstruction={financeReconciliationInstruction}
          setFinanceReconciliationInstruction={setFinanceReconciliationInstruction}
          financeReconciliationCurrency={financeReconciliationCurrency}
          setFinanceReconciliationCurrency={setFinanceReconciliationCurrency}
          isReconcilingFinance={isReconcilingFinance}
          onReconcileFinanceFiles={onReconcileFinanceFiles}
        />
      ) : (
        <AutomationDirectory
          position={activePosition}
          tasks={visibleTasks}
          onNavigate={onNavigate}
        />
      )}
    </Space>
  );
}

function AutomationDirectory({
  position,
  tasks,
  onNavigate,
}: {
  position: Position;
  tasks: AutomationTaskRecord[];
  onNavigate: (view: View) => void;
}) {
  const directoryItems = [
    ...tasks.map((task) => ({
      key: task.task_id,
      title: task.label,
      description: task.output_format,
      tag: task.position === "operations" && task.task_id === "listing"
        ? "草稿写回"
        : task.position === "finance" && task.task_id === "salary_summary" ? "ERP+Excel" : "文本生成",
      view: automationTaskView(position, task.task_id),
      icon: task.position === "operations" && task.task_id === "listing"
        ? <CloudUploadOutlined />
        : task.position === "finance" && task.task_id === "salary_summary" ? <TableOutlined /> : <RobotOutlined />,
    })).filter((item) => !(position === "finance" && item.key === "excel_transform")),
    ...(position === "finance"
      ? [
          {
            key: "finance-excel-upload",
            title: "财务 Excel 生成",
            description: "选择或上传财务 Excel，并选择权限内 ERP 表生成新工作簿。",
            tag: "文件自动化",
            view: "automation_finance_excel_transform" as View,
            icon: <CloudUploadOutlined />,
          },
          {
            key: "finance-reconciliation",
            title: "财务对账自动化",
            description: "上传结算、物流、采购、广告和汇率表，自动生成订单利润表和异常账单。",
            tag: "财务对账",
            view: "automation_finance_reconciliation" as View,
            icon: <AuditOutlined />,
          },
        ]
      : []),
  ];

  return (
    <ProCard
      title="功能目录"
      subTitle="每个功能已拆到左侧子菜单，当前页面只保留入口目录"
      bordered
    >
      <Row gutter={[12, 12]}>
        {directoryItems.map((item) => (
          <Col xs={24} md={12} xl={8} key={item.key} className="automationTaskCol">
            <Card size="small" className="contextCard automationDirectoryCard">
              <div className="automationDirectoryBody">
                <div className="automationDirectoryTitle">
                  <Space size={8}>
                    {item.icon}
                    <Tooltip title={item.description} placement="topLeft">
                      <Text strong className="tooltipTitle">{item.title}</Text>
                    </Tooltip>
                  </Space>
                  <Tag color="blue">{item.tag}</Tag>
                </div>
                <Button
                  type="primary"
                  onClick={() => item.view ? onNavigate(item.view) : undefined}
                  disabled={!item.view}
                >
                  打开
                </Button>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </ProCard>
  );
}

function AutomationTaskDetail({
  task,
  loadingTaskId,
  onGenerate,
  onInputChange,
}: {
  task: AutomationTaskRecord | null;
  loadingTaskId: string;
  onGenerate: (taskId: string, inputText: string) => void;
  onInputChange: (taskId: string, value: string) => void;
}) {
  if (!task) {
    return (
      <ProCard title="岗位自动化" bordered>
        <Empty description="当前账号无权查看该功能，或任务尚未加载" />
      </ProCard>
    );
  }

  return (
    <ProCard title={task.label} subTitle={task.output_format} bordered>
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={10}>
          <Card size="small" className="contextCard automationInfoCard">
            <Space direction="vertical" size={10} className="pageStack">
              <Tag color="blue">{task.position_label}</Tag>
              <Paragraph className="automationTaskDetailText">{task.instruction}</Paragraph>
              <Paragraph className="automationTaskDetailText">{task.output_format}</Paragraph>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card size="small" className="contextCard automationTaskCard">
            <div className="automationTaskFocusedBody">
              <Input.TextArea
                className="automationTaskFocusedInput"
                value={task.inputText}
                placeholder={task.placeholder}
                autoSize={false}
                rows={7}
                onChange={(event) => onInputChange(task.task_id, event.target.value)}
              />
              <div className="automationTaskFooter">
                <Button
                  type="primary"
                  icon={task.task_id === "listing" ? <CloudUploadOutlined /> : undefined}
                  loading={loadingTaskId === task.task_id}
                  onClick={() => onGenerate(task.task_id, task.inputText)}
                >
                  {task.task_id === "listing" ? "生成并保存草稿" : "生成"}
                </Button>
              </div>
              {task.output ? (
                <Card size="small" title="生成结果" className="automationTaskResult">
                  {task.platformDraft ? (
                    <PlatformDraftSummary draft={task.platformDraft} />
                  ) : null}
                  <Paragraph className="automationTaskResultText">
                    {task.output}
                  </Paragraph>
                </Card>
              ) : null}
            </div>
          </Card>
        </Col>
      </Row>
    </ProCard>
  );
}

function FinanceSalaryExportDetail({
  financeSalaryMessage,
  setFinanceSalaryMessage,
  financeSalaryExportSummary,
  isExportingFinanceSalary,
  onExportFinanceSalary,
}: {
  financeSalaryMessage: string;
  setFinanceSalaryMessage: (value: string) => void;
  financeSalaryExportSummary: string;
  isExportingFinanceSalary: boolean;
  onExportFinanceSalary: () => void;
}) {
  return (
    <ProCard title="统计工资" subTitle="输入简略财务请求，系统自动识别期间、查询 ERP 工资单并生成 Excel" bordered>
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={10}>
          <Card size="small" className="contextCard automationInfoCard">
            <Space direction="vertical" size={10} className="pageStack">
              <Tag color="blue">财务</Tag>
              <Text strong>自动化链路</Text>
              <Paragraph className="automationTaskDetailText">
                自然语言识别 → ERPNext Salary Slip 查询 → 工资明细 Excel → 运行记录产物。
              </Paragraph>
              <Space size={[6, 6]} wrap>
                <Tag color="geekblue">Salary Slip</Tag>
                <Tag color="green">真实 ERP</Tag>
                <Tag color="purple">Excel</Tag>
              </Space>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card size="small" className="contextCard automationTaskCard">
            <div className="automationTaskFocusedBody">
              <Input.TextArea
                className="automationTaskFocusedInput"
                value={financeSalaryMessage}
                placeholder="例如：把这个月所有员工的工资表发我"
                autoSize={false}
                rows={5}
                onChange={(event) => setFinanceSalaryMessage(event.target.value)}
              />
              <div className="automationTaskFooter">
                <Button
                  type="primary"
                  icon={<TableOutlined />}
                  loading={isExportingFinanceSalary}
                  onClick={onExportFinanceSalary}
                >
                  生成工资 Excel
                </Button>
              </div>
              {financeSalaryExportSummary ? (
                <Card size="small" title="自动化结果" className="automationTaskResult">
                  <Paragraph className="automationTaskResultText">
                    {financeSalaryExportSummary}
                  </Paragraph>
                </Card>
              ) : null}
            </div>
          </Card>
        </Col>
      </Row>
    </ProCard>
  );
}

function FinanceReportAnalysisDetail({
  financeReportFiles,
  setFinanceReportFiles,
  financeReportInstruction,
  setFinanceReportInstruction,
  financeReportOutputFormat,
  setFinanceReportOutputFormat,
  financeReportSummary,
  isAnalyzingFinanceReport,
  onAnalyzeFinanceReport,
}: {
  financeReportFiles: File[];
  setFinanceReportFiles: React.Dispatch<React.SetStateAction<File[]>>;
  financeReportInstruction: string;
  setFinanceReportInstruction: (value: string) => void;
  financeReportOutputFormat: "word" | "excel";
  setFinanceReportOutputFormat: (value: "word" | "excel") => void;
  financeReportSummary: string;
  isAnalyzingFinanceReport: boolean;
  onAnalyzeFinanceReport: () => void;
}) {
  const reportFileList: UploadFile[] = financeReportFiles.map((file) => ({
    uid: file.name,
    name: file.name,
    status: "done",
  }));

  return (
    <ProCard title="分析财务报表" subTitle="上传财务报表文件，AI 解析后生成 Word 或 Excel 分析报告" bordered>
      <div className="financeUploadControls focused">
        <Upload.Dragger
          className="financeUploadDragger"
          accept=".xlsx,.xls,.csv,.docx,.pdf,.txt,.md"
          multiple
          maxCount={6}
          fileList={reportFileList}
          beforeUpload={(file) => {
            setFinanceReportFiles((current) => {
              const withoutDuplicate = current.filter((itemFile) => itemFile.name !== file.name);
              return [...withoutDuplicate, file];
            });
            return false;
          }}
          onRemove={(file) => {
            setFinanceReportFiles((current) =>
              current.filter((itemFile) => itemFile.name !== file.name)
            );
          }}
        >
          <p className="uploadIcon">
            <CloudUploadOutlined />
          </p>
          <p className="uploadTitle">选择财务报表文件</p>
          <p className="uploadHint">可只粘贴内容，也可上传 Excel、Word、PDF、CSV、TXT，最多 6 个文件</p>
        </Upload.Dragger>
        <div className="financeUploadActionPane focused">
          <Segmented
            value={financeReportOutputFormat}
            onChange={(value) => setFinanceReportOutputFormat(value as "word" | "excel")}
            options={[
              { label: "Word 报告", value: "word" },
              { label: "Excel 报告", value: "excel" },
            ]}
          />
          <Input.TextArea
            className="financeUploadInstruction focused"
            value={financeReportInstruction}
            placeholder="可粘贴财务报表内容或输入分析要求，例如：分析利润率变化、费用异常、现金流风险，并给出复核建议。"
            autoSize={false}
            rows={6}
            onChange={(event) => setFinanceReportInstruction(event.target.value)}
          />
          <div className="automationTaskFooter">
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              loading={isAnalyzingFinanceReport}
              disabled={(financeReportFiles.length === 0 && !financeReportInstruction.trim()) || isAnalyzingFinanceReport}
              onClick={onAnalyzeFinanceReport}
            >
              生成分析报告
            </Button>
          </div>
          {financeReportSummary ? (
            <Card size="small" title="生成结果" className="automationTaskResult">
              <Paragraph className="automationTaskResultText">
                {financeReportSummary}
              </Paragraph>
            </Card>
          ) : null}
        </div>
      </div>
    </ProCard>
  );
}

function FinanceExcelUploadDetail({
  financeExcelFile,
  setFinanceExcelFile,
  financeExcelInstruction,
  setFinanceExcelInstruction,
  financeExcelErpResources,
  setFinanceExcelErpResources,
  erpResources,
  isTransformingFinanceExcel,
  onTransformFinanceExcel,
}: {
  financeExcelFile: File | null;
  setFinanceExcelFile: (value: File | null) => void;
  financeExcelInstruction: string;
  setFinanceExcelInstruction: (value: string) => void;
  financeExcelErpResources: string[];
  setFinanceExcelErpResources: (value: string[]) => void;
  erpResources: ErpResourceItem[];
  isTransformingFinanceExcel: boolean;
  onTransformFinanceExcel: () => void;
}) {
  const financeScopeSet = new Set(positionConfigs.finance.erpScopes);
  const financeErpResourceOptions = erpResources
    .filter((item) => financeScopeSet.has(item.resource))
    .map((item) => ({
      label: item.label,
      value: item.resource,
    }));
  const financeFileList: UploadFile[] = financeExcelFile
    ? [
        {
          uid: financeExcelFile.name,
          name: financeExcelFile.name,
          status: "done",
        },
      ]
    : [];
  const canGenerateFinanceExcel = Boolean(financeExcelFile)
    || financeExcelErpResources.length > 0
    || financeExcelInstruction.trim().length > 0;

  return (
    <ProCard title="财务 Excel 生成" subTitle="可上传 Excel，也可直接用口语化要求或 ERP 财务表生成新工作簿" bordered>
      <div className="financeUploadControls focused">
        <Upload.Dragger
          className="financeUploadDragger"
          accept=".xlsx,.xls"
          multiple={false}
          maxCount={1}
          fileList={financeFileList}
          beforeUpload={(file) => {
            setFinanceExcelFile(file);
            return false;
          }}
          onRemove={() => setFinanceExcelFile(null)}
        >
          <p className="uploadIcon">
            <CloudUploadOutlined />
          </p>
          <p className="uploadTitle">选择或上传 Excel（可选）</p>
          <p className="uploadHint">不上传时，AI 会根据下方要求和财务 ERP 表生成新文件</p>
        </Upload.Dragger>
        <div className="financeUploadActionPane focused">
          <Select
            className="fullWidthControl"
            mode="multiple"
            allowClear
            placeholder="选择财务 ERP 表"
            value={financeExcelErpResources}
            options={financeErpResourceOptions}
            maxTagCount="responsive"
            onChange={setFinanceExcelErpResources}
          />
          <Input.TextArea
            className="financeUploadInstruction focused"
            value={financeExcelInstruction}
            placeholder="直接描述要生成的新表，例如：把本月销售发票和收付款单合成收款核对表，按客户汇总并标记未收款。"
            autoSize={false}
            rows={6}
            onChange={(event) => setFinanceExcelInstruction(event.target.value)}
          />
          <div className="automationTaskFooter">
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={isTransformingFinanceExcel}
              disabled={!canGenerateFinanceExcel || isTransformingFinanceExcel}
              onClick={onTransformFinanceExcel}
            >
              AI 生成并下载 Excel
            </Button>
          </div>
        </div>
      </div>
    </ProCard>
  );
}

function FinanceReconciliationDetail({
  financeReconciliationFiles,
  setFinanceReconciliationFiles,
  financeReconciliationInstruction,
  setFinanceReconciliationInstruction,
  financeReconciliationCurrency,
  setFinanceReconciliationCurrency,
  isReconcilingFinance,
  onReconcileFinanceFiles,
}: {
  financeReconciliationFiles: File[];
  setFinanceReconciliationFiles: React.Dispatch<React.SetStateAction<File[]>>;
  financeReconciliationInstruction: string;
  setFinanceReconciliationInstruction: (value: string) => void;
  financeReconciliationCurrency: string;
  setFinanceReconciliationCurrency: (value: string) => void;
  isReconcilingFinance: boolean;
  onReconcileFinanceFiles: () => void;
}) {
  const reconciliationFileList: UploadFile[] = financeReconciliationFiles.map((file) => ({
    uid: file.name,
    name: file.name,
    status: "done",
  }));

  return (
    <ProCard title="财务对账自动化" subTitle="独立处理结算、物流、采购、广告和汇率表，生成订单利润表" bordered>
      <div className="financeUploadControls focused">
        <Upload.Dragger
          className="financeUploadDragger"
          accept=".xlsx,.xls"
          multiple
          maxCount={8}
          fileList={reconciliationFileList}
          beforeUpload={(file) => {
            setFinanceReconciliationFiles((current) => {
              const withoutDuplicate = current.filter((itemFile) => itemFile.name !== file.name);
              return [...withoutDuplicate, file];
            });
            return false;
          }}
          onRemove={(file) => {
            setFinanceReconciliationFiles((current) =>
              current.filter((itemFile) => itemFile.name !== file.name)
            );
          }}
        >
          <p className="uploadIcon">
            <CloudUploadOutlined />
          </p>
          <p className="uploadTitle">选择对账 Excel</p>
          <p className="uploadHint">支持 Amazon 结算、物流、采购、广告、汇率等多张 .xlsx / .xls</p>
        </Upload.Dragger>
        <div className="financeUploadActionPane focused">
          <Select
            className="fullWidthControl"
            value={financeReconciliationCurrency}
            options={[
              { label: "人民币 CNY", value: "CNY" },
              { label: "美元 USD", value: "USD" },
              { label: "欧元 EUR", value: "EUR" },
              { label: "日元 JPY", value: "JPY" },
            ]}
            onChange={setFinanceReconciliationCurrency}
          />
          <Input.TextArea
            className="financeUploadInstruction focused"
            value={financeReconciliationInstruction}
            placeholder="输入对账要求，例如：按订单号/SKU 匹配，输出亏损订单、缺采购成本、缺物流费和未匹配广告费。"
            autoSize={false}
            rows={6}
            onChange={(event) => setFinanceReconciliationInstruction(event.target.value)}
          />
          <div className="automationTaskFooter">
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={isReconcilingFinance}
              disabled={financeReconciliationFiles.length === 0 || isReconcilingFinance}
              onClick={onReconcileFinanceFiles}
            >
              生成订单利润表
            </Button>
          </div>
        </div>
      </div>
    </ProCard>
  );
}

function CustomerServiceInboxPanel({
  role,
  position,
  messages,
  detail,
  processResult,
  filters,
  setFilters,
  form,
  setForm,
  loading,
  creating,
  processingMessageId,
  refreshMessages,
  createMessage,
  processMessage,
  openDetail,
}: {
  role: Role;
  position: Position | null;
  messages: CustomerServiceMessageItem[];
  detail: CustomerServiceMessageDetailResponse | null;
  processResult: CustomerServiceProcessResponse | null;
  filters: CustomerServiceInboxFilters;
  setFilters: (value: CustomerServiceInboxFilters) => void;
  form: CustomerServiceInboxForm;
  setForm: (value: CustomerServiceInboxForm | ((current: CustomerServiceInboxForm) => CustomerServiceInboxForm)) => void;
  loading: boolean;
  creating: boolean;
  processingMessageId: string;
  refreshMessages: (nextFilters?: CustomerServiceInboxFilters) => void;
  createMessage: () => void;
  processMessage: (messageId: string) => void;
  openDetail: (messageId: string) => void;
}) {
  if (!canUseCustomerServiceInbox(role, position)) {
    return (
      <ProCard title="客服自动化收件箱" bordered>
        <Empty description="当前账号无权使用客服自动化收件箱" />
      </ProCard>
    );
  }

  const stats = [
    { title: "消息总数", value: messages.length, status: "processing" },
    { title: "低风险待发送", value: messages.filter((item) => item.status === "auto_reply_ready").length, status: "success" },
    { title: "转人工", value: messages.filter((item) => item.status === "human_handoff").length, status: "warning" },
    { title: "处理失败", value: messages.filter((item) => item.status === "failed").length, status: "error" },
  ];

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]}>
        {stats.map((item) => (
          <Col xs={12} md={6} key={item.title}>
            <StatisticCard
              statistic={{
                title: item.title,
                value: item.value,
                suffix: "条",
                status: metricStatus(item.status),
              }}
            />
          </Col>
        ))}
      </Row>

      <ProCard title="客服自动化工作台" bordered className="customerInboxWorkspace">
        <Tabs
          items={[
            {
              key: "queue",
              label: "消息处理",
              children: (
                <CustomerInboxQueueAndResult
                  messages={messages}
                  detail={detail}
                  processResult={processResult}
                  filters={filters}
                  setFilters={setFilters}
                  loading={loading}
                  processingMessageId={processingMessageId}
                  refreshMessages={refreshMessages}
                  processMessage={processMessage}
                  openDetail={openDetail}
                />
              ),
            },
            {
              key: "manual",
              label: "手动补录",
              children: (
                <CustomerInboxManualEntry
                  form={form}
                  setForm={setForm}
                  creating={creating}
                  loading={loading}
                  createMessage={createMessage}
                  refreshMessages={refreshMessages}
                />
              ),
            },
            {
              key: "webhook",
              label: "Webhook 接入",
              children: <CustomerInboxWebhookInfo />,
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function CustomerInboxQueueAndResult({
  messages,
  detail,
  processResult,
  filters,
  setFilters,
  loading,
  processingMessageId,
  refreshMessages,
  processMessage,
  openDetail,
}: {
  messages: CustomerServiceMessageItem[];
  detail: CustomerServiceMessageDetailResponse | null;
  processResult: CustomerServiceProcessResponse | null;
  filters: CustomerServiceInboxFilters;
  setFilters: (value: CustomerServiceInboxFilters) => void;
  loading: boolean;
  processingMessageId: string;
  refreshMessages: (nextFilters?: CustomerServiceInboxFilters) => void;
  processMessage: (messageId: string) => void;
  openDetail: (messageId: string) => void;
}) {
  const selected = detail?.item || null;

  return (
    <Space direction="vertical" size={12} className="customerInboxTabPane">
      <ProCard title="消息队列" bordered>
        <Space direction="vertical" size={12} className="pageStack">
          <Space wrap className="customerInboxToolbar">
            <Select
              value={filters.status}
              style={{ width: 132 }}
              options={[
                { label: "全部状态", value: "all" },
                { label: "新消息", value: "new" },
                { label: "处理中", value: "processing" },
                { label: "草稿", value: "drafted" },
                { label: "待发送", value: "auto_reply_ready" },
                { label: "转人工", value: "human_handoff" },
                { label: "失败", value: "failed" },
              ]}
              onChange={(value) => {
                const next = { ...filters, status: value };
                setFilters(next);
                refreshMessages(next);
              }}
            />
            <Select
              value={filters.riskLevel}
              style={{ width: 120 }}
              options={[
                { label: "全部风险", value: "all" },
                { label: "未处理", value: "unprocessed" },
                { label: "低风险", value: "low" },
                { label: "中风险", value: "medium" },
                { label: "高风险", value: "high" },
              ]}
              onChange={(value) => {
                const next = { ...filters, riskLevel: value };
                setFilters(next);
                refreshMessages(next);
              }}
            />
          </Space>
          <Table<CustomerServiceMessageItem>
            rowKey="id"
            size="small"
            dataSource={messages}
            loading={loading}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            columns={[
              {
                title: "客户消息",
                dataIndex: "message",
                width: 310,
                render: (_, record) => (
                  <Space direction="vertical" size={2} className="customerInboxMessageCell">
                    <Text strong ellipsis>
                      {record.subject || record.buyer_name || record.channel}
                    </Text>
                    <Text type="secondary" className="customerInboxPreview">
                      {record.message}
                    </Text>
                    <Space size={[4, 4]} wrap>
                      {record.order_no ? <Tag>{record.order_no}</Tag> : null}
                      {record.tracking_no ? <Tag color="geekblue">{record.tracking_no}</Tag> : null}
                    </Space>
                  </Space>
                ),
              },
              {
                title: "意图",
                dataIndex: "intent",
                width: 130,
                render: (value) => <Tag>{customerIntentLabel(String(value || "未识别"))}</Tag>,
              },
              {
                title: "风险",
                dataIndex: "risk_level",
                width: 100,
                render: (value) => <RiskTag value={String(value)} />,
              },
              {
                title: "状态",
                dataIndex: "status",
                width: 110,
                render: (value) => <CustomerStatusTag value={String(value)} />,
              },
              {
                title: "渠道",
                dataIndex: "channel",
                width: 90,
                render: (value) => <Tag color="blue">{String(value)}</Tag>,
              },
              {
                title: "创建时间",
                dataIndex: "created_at",
                width: 130,
                render: (value) => formatTime(String(value || "")),
              },
              {
                title: "操作",
                key: "actions",
                fixed: "right",
                width: 170,
                render: (_, record) => (
                  <Space size={6} wrap>
                    <Button size="small" onClick={() => openDetail(record.id)}>
                      详情
                    </Button>
                    <Button
                      size="small"
                      type="primary"
                      loading={processingMessageId === record.id}
                      disabled={processingMessageId === record.id}
                      onClick={() => processMessage(record.id)}
                    >
                      AI 处理
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Space>
      </ProCard>

      <ProCard title="处理结果" bordered>
        {selected ? (
          <Space direction="vertical" size={12} className="pageStack">
            <Space size={[6, 6]} wrap>
              <CustomerStatusTag value={selected.status} />
              <RiskTag value={selected.risk_level} />
              {selected.intent ? <Tag>{customerIntentLabel(selected.intent)}</Tag> : null}
              {selected.automation_decision ? (
                <Tag color="purple">{customerDecisionLabel(selected.automation_decision)}</Tag>
              ) : null}
            </Space>

            <div className="customerInboxDetailGrid">
              <DetailText label="订单号" value={selected.order_no || "-"} />
              <DetailText label="物流单号" value={selected.tracking_no || "-"} />
              <DetailText label="站点" value={selected.marketplace || "-"} />
              <DetailText label="语言" value={selected.buyer_language || "-"} />
              <DetailText label="运行记录" value={selected.run_id || "-"} mono />
              <DetailText label="审批 ID" value={selected.approval_id || "-"} mono />
              <DetailText label="草稿 ID" value={textFromUnknown(selected.metadata.platform_draft_id || "-")} mono />
              <DetailText label="写回状态" value={platformDraftWritebackLabel(textFromUnknown(selected.metadata.writeback_status || "-"))} />
            </div>

            <ResultBlock title="客户原话" content={selected.message} />
            <ResultBlock title="AI 回复草稿" content={selected.reply_draft || "尚未处理"} />
            {selected.metadata.writeback_message ? (
              <ResultBlock title="自动化写回" content={textFromUnknown(selected.metadata.writeback_message)} />
            ) : null}
            <ResultBlock title="ERP 摘要" content={selected.erp_summary || "暂无 ERP 摘要"} />
            <ResultBlock title="知识库摘要" content={selected.rag_summary || "暂无知识库摘要"} />
            {selected.handoff_reason ? (
              <ResultBlock title="转人工原因" content={selected.handoff_reason} />
            ) : null}

            {selected.erp_references.length ? (
              <Space size={[6, 6]} wrap>
                {selected.erp_references.map((reference) => (
                  <Tag color="geekblue" key={`${reference.resource}-${reference.record_id}`}>
                    {reference.resource_label} / {reference.record_id}
                  </Tag>
                ))}
              </Space>
            ) : null}

            {detail?.events.length ? (
              <ProCard title="事件时间线" bordered size="small">
                <Space direction="vertical" size={8} className="pageStack">
                  {detail.events.map((event) => (
                    <div className="customerInboxEvent" key={event.id}>
                      <Text strong>{customerEventLabel(event.event_type)}</Text>
                      <Text type="secondary">{formatTime(event.created_at)}</Text>
                      <Text className="customerInboxPreview">{event.content}</Text>
                    </div>
                  ))}
                </Space>
              </ProCard>
            ) : null}

            {processResult?.item.id === selected.id ? (
              <Table
                rowKey={(record) => `${record.step_order}-${record.step_name}`}
                size="small"
                dataSource={processResult.steps}
                pagination={false}
                columns={[
                  {
                    title: "步骤",
                    dataIndex: "step_name",
                    render: (value) => <Text className="aiWorkflowMono">{String(value)}</Text>,
                  },
                  {
                    title: "状态",
                    dataIndex: "status",
                    width: 92,
                    render: (value) => <StatusTag value={String(value)} />,
                  },
                  {
                    title: "耗时",
                    dataIndex: "duration_ms",
                    width: 92,
                    render: (value) => formatDuration(value),
                  },
                ]}
              />
            ) : null}
          </Space>
        ) : (
          <Empty description="请选择或创建一条客户消息" />
        )}
      </ProCard>
    </Space>
  );
}

function CustomerInboxManualEntry({
  form,
  setForm,
  creating,
  loading,
  createMessage,
  refreshMessages,
}: {
  form: CustomerServiceInboxForm;
  setForm: (value: CustomerServiceInboxForm | ((current: CustomerServiceInboxForm) => CustomerServiceInboxForm)) => void;
  creating: boolean;
  loading: boolean;
  createMessage: () => void;
  refreshMessages: (nextFilters?: CustomerServiceInboxFilters) => void;
}) {
  return (
    <div className="customerInboxTabPane">
      <Row gutter={[12, 12]} align="top">
        <Col xs={24} md={6}>
          <Select
            className="fullWidthControl"
            value={form.channel}
            options={[
              { label: "手动录入", value: "manual" },
              { label: "Amazon", value: "amazon" },
              { label: "邮箱", value: "email" },
              { label: "工单", value: "ticket" },
              { label: "API", value: "api" },
            ]}
            onChange={(value) => setForm((current) => ({ ...current, channel: value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.buyerName}
            placeholder="客户姓名"
            onChange={(event) => setForm((current) => ({ ...current, buyerName: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.buyerEmail}
            placeholder="客户邮箱"
            onChange={(event) => setForm((current) => ({ ...current, buyerEmail: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Select
            className="fullWidthControl"
            value={form.buyerLanguage}
            options={[
              { label: "自动识别", value: "auto" },
              { label: "English", value: "English" },
              { label: "中文", value: "Chinese" },
              { label: "Deutsch", value: "German" },
              { label: "日本語", value: "Japanese" },
            ]}
            onChange={(value) => setForm((current) => ({ ...current, buyerLanguage: value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.marketplace}
            placeholder="站点，例如 Amazon US"
            onChange={(event) => setForm((current) => ({ ...current, marketplace: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.orderNo}
            placeholder="订单号"
            onChange={(event) => setForm((current) => ({ ...current, orderNo: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.trackingNo}
            placeholder="物流单号"
            onChange={(event) => setForm((current) => ({ ...current, trackingNo: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={6}>
          <Input
            value={form.sku}
            placeholder="SKU"
            onChange={(event) => setForm((current) => ({ ...current, sku: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={8}>
          <Input
            value={form.subject}
            placeholder="主题"
            onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))}
          />
        </Col>
        <Col xs={24} md={16}>
          <Input.TextArea
            value={form.message}
            placeholder="客户原话，例如：Where is my order?"
            autoSize={false}
            rows={3}
            onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
          />
        </Col>
        <Col xs={24}>
          <Space wrap>
            <Button type="primary" icon={<MessageOutlined />} loading={creating} onClick={createMessage}>
              加入收件箱
            </Button>
            <Button icon={<ReloadOutlined />} loading={loading} onClick={() => refreshMessages()}>
              刷新列表
            </Button>
          </Space>
        </Col>
      </Row>
    </div>
  );
}

function CustomerInboxWebhookInfo() {
  return (
    <div className="customerInboxTabPane">
      <div className="customerWebhookInfo">
        <div>
          <Text strong>Webhook</Text>
          <Text className="customerWebhookUrl">POST /api/customer-service/webhooks/messages</Text>
        </div>
        <div>
          <Text type="secondary">鉴权</Text>
          <Text>客服岗位 Bearer token 或 X-Customer-Service-Webhook-Secret</Text>
        </div>
        <div>
          <Text type="secondary">动作</Text>
          <Text>收到外部客户消息后自动入库、识别意图、查 ERP/RAG、生成回复并按风险流转</Text>
        </div>
      </div>
    </div>
  );
}

function DetailText({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="customerInboxDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "aiWorkflowMono" : "aiWorkflowText"}>{value}</Text>
    </div>
  );
}

function ResultBlock({ title, content }: { title: string; content: string }) {
  return (
    <div className="customerInboxResultBlock">
      <Text strong>{title}</Text>
      <Paragraph className="customerInboxResultText">{content}</Paragraph>
    </div>
  );
}

function ErpPanel({
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
          <ErpQueryResultView result={result} columns={resultColumns} />
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
          { title: "资源", dataIndex: "resource", width: 170 },
          { title: "名称", dataIndex: "label", width: 140 },
          { title: "说明", dataIndex: "description" },
          {
            title: "当前 Provider 对象",
            width: 180,
            render: (_, item) => {
              const provider = status?.provider || "erpnext";
              return item.provider_refs[provider] || "-";
            },
          },
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

function ErpQueryResultView({
  result,
  columns,
}: {
  result: ErpQueryResponse;
  columns: ReturnType<typeof buildErpResultColumns>;
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

      <Collapse
        ghost
        items={[
          {
            key: "debug",
            label: "查看原始返回数据",
            children: <pre className="statePre">{JSON.stringify(result, null, 2)}</pre>,
          },
        ]}
      />
    </Space>
  );
}

function DocumentsPanel(props: {
  token: string;
  file: File | null;
  setFile: (value: File | null) => void;
  visibility: Role;
  setVisibility: (value: Role) => void;
  department: string;
  setDepartment: (value: string) => void;
  positionScope: DocumentPositionScope;
  setPositionScope: (value: DocumentPositionScope) => void;
  marketScope: DocumentMarketScope;
  setMarketScope: (value: DocumentMarketScope) => void;
  storeScope: DocumentStoreScope;
  setStoreScope: (value: DocumentStoreScope) => void;
  fieldScope: DocumentFieldScope;
  setFieldScope: (value: DocumentFieldScope) => void;
  sensitivityLevel: DocumentSensitivityLevel;
  setSensitivityLevel: (value: DocumentSensitivityLevel) => void;
  uploadDocument: (uploadAccess?: DocumentUploadAccessPayload) => Promise<void>;
  role: Role;
  users: UserRecord[];
  isUploading: boolean;
}) {
  const disabled = props.role !== "admin" || props.isUploading;
  const [teams, setTeams] = useState<RagTeamItem[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [members, setMembers] = useState<RagTeamMemberItem[]>([]);
  const [teamForm, setTeamForm] = useState<RagTeamFormState>(emptyRagTeamForm());
  const [memberForm, setMemberForm] = useState<RagTeamMemberFormState>({
    userId: "",
    memberRole: "member",
    expiresAt: "",
  });
  const [isLoadingTeams, setIsLoadingTeams] = useState(false);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [savingTeamKey, setSavingTeamKey] = useState("");
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [removingMemberKey, setRemovingMemberKey] = useState("");
  const [uploadAccessForm, setUploadAccessForm] = useState<DocumentAccessFormState>({
    accessMode: "open",
    ownerUserId: "",
    ownerTeamId: "",
  });
  const [uploadGrantForm, setUploadGrantForm] = useState<DocumentGrantFormState>({
    subjectType: "user",
    subjectId: "",
    accessLevel: "read",
    reason: "",
    expiresAt: "",
  });
  const [documents, setDocuments] = useState<DocumentAccessItem[]>([]);
  const [documentSearch, setDocumentSearch] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [documentAccess, setDocumentAccess] = useState<DocumentAccessItem | null>(null);
  const [isDocumentAuthDrawerOpen, setIsDocumentAuthDrawerOpen] = useState(false);
  const [documentAccessForm, setDocumentAccessForm] = useState<DocumentAccessFormState>({
    accessMode: "open",
    ownerUserId: "",
    ownerTeamId: "",
  });
  const [documentGrants, setDocumentGrants] = useState<DocumentGrantItem[]>([]);
  const [documentGrantForm, setDocumentGrantForm] = useState<DocumentGrantFormState>({
    subjectType: "user",
    subjectId: "",
    accessLevel: "read",
    reason: "",
    expiresAt: "",
  });
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isLoadingDocumentAccess, setIsLoadingDocumentAccess] = useState(false);
  const [isSavingDocumentAccess, setIsSavingDocumentAccess] = useState(false);
  const [isCreatingGrant, setIsCreatingGrant] = useState(false);
  const [revokingGrantId, setRevokingGrantId] = useState("");

  useEffect(() => {
    if (!props.token || props.role !== "admin") {
      setTeams([]);
      setMembers([]);
      setDocuments([]);
      setDocumentAccess(null);
      setDocumentGrants([]);
      setIsDocumentAuthDrawerOpen(false);
      return;
    }

    void refreshRagTeams({ silent: true });
    void refreshDocuments({ silent: true });
  }, [props.token, props.role]);

  const uploadFileList: UploadFile[] = props.file
    ? [
        {
          uid: props.file.name,
          name: props.file.name,
          status: "done",
        },
      ]
    : [];

  const userOptions = useMemo(
    () =>
      props.users.map((user) => ({
        label: userLabel(user),
        value: user.id,
      })),
    [props.users],
  );
  const activeTeamOptions = useMemo(
    () =>
      teams
        .filter((team) => team.status === "active")
        .map((team) => ({
          label: `${team.name} / ${team.team_key}`,
          value: team.id,
        })),
    [teams],
  );
  const ownerTeamOptions = useMemo(
    () =>
      teams
        .filter((team) => team.status !== "archived")
        .map((team) => ({
          label: `${team.name} / ${team.team_key}`,
          value: team.id,
        })),
    [teams],
  );
  const grantSubjectOptions = documentGrantForm.subjectType === "team" ? activeTeamOptions : userOptions;

  async function refreshRagTeams(options: { silent?: boolean; preferredTeamId?: string } = {}) {
    if (!props.token) {
      return;
    }

    setIsLoadingTeams(true);
    try {
      const result = await listRagTeams(props.token);
      setTeams(result.items);
      const nextTeam =
        result.items.find((item) => item.id === options.preferredTeamId)
        || result.items.find((item) => item.id === selectedTeamId)
        || result.items[0]
        || null;

      if (nextTeam) {
        setSelectedTeamId(nextTeam.id);
        setTeamForm(teamFormFromItem(nextTeam));
        await refreshRagTeamMembers(nextTeam.id, { silent: true });
      } else {
        setSelectedTeamId("");
        setTeamForm(emptyRagTeamForm());
        setMembers([]);
      }

      if (!options.silent) {
        message.success("RAG 团队已刷新");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "RAG 团队加载失败");
    } finally {
      setIsLoadingTeams(false);
    }
  }

  async function refreshRagTeamMembers(teamId = selectedTeamId, options: { silent?: boolean } = {}) {
    if (!props.token || !teamId) {
      setMembers([]);
      return;
    }

    setIsLoadingMembers(true);
    try {
      const result = await listRagTeamMembers(props.token, teamId);
      setMembers(result.items);
      if (!options.silent) {
        message.success("团队成员已刷新");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "团队成员加载失败");
    } finally {
      setIsLoadingMembers(false);
    }
  }

  function selectTeam(team: RagTeamItem) {
    setSelectedTeamId(team.id);
    setTeamForm(teamFormFromItem(team));
    void refreshRagTeamMembers(team.id);
  }

  function startNewTeam() {
    setSelectedTeamId("");
    setTeamForm(emptyRagTeamForm());
    setMembers([]);
  }

  async function saveTeam() {
    if (!props.token) {
      message.warning("请先登录管理员账号");
      return;
    }
    if (!teamForm.name.trim()) {
      message.warning("团队名称不能为空");
      return;
    }
    if (!selectedTeamId && !teamForm.teamKey.trim()) {
      message.warning("团队 key 不能为空");
      return;
    }

    const basePayload = {
      name: teamForm.name.trim(),
      description: teamForm.description.trim() || null,
      position_scope: teamForm.positionScope === "all" ? null : teamForm.positionScope,
      market_scope: teamForm.marketScope === "all" ? null : teamForm.marketScope as RagMarketScope,
      store_scope: teamForm.storeScope === "all" ? null : teamForm.storeScope as RagStoreScope,
      status: teamForm.status,
    };

    setSavingTeamKey(selectedTeamId || "new");
    try {
      const result = selectedTeamId
        ? await updateRagTeam(props.token, selectedTeamId, basePayload)
        : await createRagTeam(props.token, {
            ...basePayload,
            team_key: teamForm.teamKey.trim().toLowerCase(),
          });
      setSelectedTeamId(result.item.id);
      setTeamForm(teamFormFromItem(result.item));
      await refreshRagTeams({ silent: true, preferredTeamId: result.item.id });
      message.success(selectedTeamId ? "RAG 团队已保存" : "RAG 团队已创建");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "RAG 团队保存失败");
    } finally {
      setSavingTeamKey("");
    }
  }

  async function addMember() {
    if (!props.token || !selectedTeamId) {
      message.warning("请选择 RAG 团队");
      return;
    }
    if (!memberForm.userId) {
      message.warning("请选择成员");
      return;
    }

    setIsAddingMember(true);
    try {
      await addRagTeamMember(props.token, selectedTeamId, {
        user_id: memberForm.userId,
        member_role: memberForm.memberRole,
        expires_at: optionalIsoText(memberForm.expiresAt),
      });
      setMemberForm((current) => ({ ...current, userId: "", expiresAt: "" }));
      await Promise.all([
        refreshRagTeamMembers(selectedTeamId, { silent: true }),
        refreshRagTeams({ silent: true, preferredTeamId: selectedTeamId }),
      ]);
      message.success("团队成员已添加");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "团队成员添加失败");
    } finally {
      setIsAddingMember(false);
    }
  }

  function removeMember(item: RagTeamMemberItem) {
    if (!props.token || !selectedTeamId) {
      return;
    }

    Modal.confirm({
      title: "移除团队成员",
      content: `确认移除“${item.display_name || item.username}”？`,
      okText: "移除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        setRemovingMemberKey(item.user_id);
        try {
          await removeRagTeamMember(props.token, selectedTeamId, item.user_id);
          await Promise.all([
            refreshRagTeamMembers(selectedTeamId, { silent: true }),
            refreshRagTeams({ silent: true, preferredTeamId: selectedTeamId }),
          ]);
          message.success("团队成员已移除");
        } catch (error) {
          if (isAuthExpiredError(error)) {
            return;
          }
          message.error(error instanceof Error ? error.message : "团队成员移除失败");
        } finally {
          setRemovingMemberKey("");
        }
      },
    });
  }

  async function uploadDocumentWithAccess() {
    if (uploadAccessForm.accessMode === "owner_only" && !uploadAccessForm.ownerUserId) {
      message.warning("仅归属人模式需要选择 owner 用户");
      return;
    }
    if (uploadAccessForm.accessMode === "team_only" && !uploadAccessForm.ownerTeamId) {
      message.warning("仅归属团队模式需要选择 owner 团队");
      return;
    }

    const uploadGrant = uploadGrantForm.subjectId
      ? {
          grant_subject_type: uploadGrantForm.subjectType,
          grant_subject_id: uploadGrantForm.subjectId,
          grant_access_level: uploadGrantForm.accessLevel,
          grant_reason: uploadGrantForm.reason.trim() || null,
          grant_expires_at: optionalIsoText(uploadGrantForm.expiresAt),
        }
      : {};

    await props.uploadDocument({
      access_mode: uploadAccessForm.accessMode,
      owner_user_id: uploadAccessForm.ownerUserId || null,
      owner_team_id: uploadAccessForm.ownerTeamId || null,
      ...uploadGrant,
    });
    await refreshDocuments({ silent: true });
  }

  async function refreshDocuments(options: { silent?: boolean } = {}) {
    if (!props.token) {
      setDocuments([]);
      return;
    }

    setIsLoadingDocuments(true);
    try {
      const result = await listRagDocuments(props.token, {
        search: documentSearch.trim() || undefined,
        status: "active",
        limit: 50,
      });
      setDocuments(result.items);
      if (!options.silent) {
        message.success("文档列表已刷新");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档列表加载失败");
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  function selectDocument(item: DocumentAccessItem, options: { openDrawer?: boolean } = {}) {
    setDocumentId(item.id);
    if (options.openDrawer) {
      setIsDocumentAuthDrawerOpen(true);
    }
    void loadDocumentAuthorization(item.id);
  }

  async function loadDocumentAuthorization(targetDocumentId = documentId) {
    const normalizedDocumentId = targetDocumentId.trim();
    if (!props.token) {
      message.warning("请先登录管理员账号");
      return;
    }
    if (!normalizedDocumentId) {
      message.warning("文档 ID 不能为空");
      return;
    }

    setIsLoadingDocumentAccess(true);
    try {
      const [accessResult, grantsResult] = await Promise.all([
        getDocumentAccess(props.token, normalizedDocumentId),
        listDocumentGrants(props.token, normalizedDocumentId),
      ]);
      setDocumentId(normalizedDocumentId);
      setDocumentAccess(accessResult.item);
      setDocuments((current) =>
        current.map((item) => item.id === accessResult.item.id ? accessResult.item : item),
      );
      setDocumentAccessForm({
        accessMode: accessResult.item.access_mode,
        ownerUserId: accessResult.item.owner_user_id || "",
        ownerTeamId: accessResult.item.owner_team_id || "",
      });
      setDocumentGrants(grantsResult.items);
      message.success("文档授权已加载");
    } catch (error) {
      setDocumentAccess(null);
      setDocumentGrants([]);
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档授权加载失败");
    } finally {
      setIsLoadingDocumentAccess(false);
    }
  }

  async function saveDocumentAccess() {
    if (!props.token || !documentAccess) {
      message.warning("请先加载文档");
      return;
    }
    if (documentAccessForm.accessMode === "owner_only" && !documentAccessForm.ownerUserId) {
      message.warning("仅归属人模式需要选择 owner 用户");
      return;
    }
    if (documentAccessForm.accessMode === "team_only" && !documentAccessForm.ownerTeamId) {
      message.warning("仅归属团队模式需要选择 owner 团队");
      return;
    }

    setIsSavingDocumentAccess(true);
    try {
      const result = await updateDocumentAccess(props.token, documentAccess.id, {
        access_mode: documentAccessForm.accessMode,
        owner_user_id: documentAccessForm.ownerUserId || null,
        owner_team_id: documentAccessForm.ownerTeamId || null,
      });
      setDocumentAccess(result.item);
      setDocuments((current) =>
        current.map((item) => item.id === result.item.id ? result.item : item),
      );
      setDocumentAccessForm({
        accessMode: result.item.access_mode,
        ownerUserId: result.item.owner_user_id || "",
        ownerTeamId: result.item.owner_team_id || "",
      });
      message.success("文档访问模式已保存");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档访问模式保存失败");
    } finally {
      setIsSavingDocumentAccess(false);
    }
  }

  async function createGrant() {
    if (!props.token || !documentAccess) {
      message.warning("请先加载文档");
      return;
    }
    if (!documentGrantForm.subjectId) {
      message.warning("请选择授权对象");
      return;
    }

    setIsCreatingGrant(true);
    try {
      await createDocumentGrant(props.token, documentAccess.id, {
        subject_type: documentGrantForm.subjectType,
        subject_id: documentGrantForm.subjectId,
        access_level: documentGrantForm.accessLevel,
        reason: documentGrantForm.reason.trim() || null,
        expires_at: optionalIsoText(documentGrantForm.expiresAt),
      });
      setDocumentGrantForm((current) => ({
        ...current,
        subjectId: "",
        reason: "",
        expiresAt: "",
      }));
      const result = await listDocumentGrants(props.token, documentAccess.id);
      setDocumentGrants(result.items);
      message.success("文档授权已添加");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档授权添加失败");
    } finally {
      setIsCreatingGrant(false);
    }
  }

  async function revokeGrant(item: DocumentGrantItem) {
    if (!props.token || !documentAccess) {
      return;
    }

    setRevokingGrantId(item.id);
    try {
      await revokeDocumentGrant(props.token, documentAccess.id, item.id);
      const result = await listDocumentGrants(props.token, documentAccess.id);
      setDocumentGrants(result.items);
      message.success("文档授权已撤销");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档授权撤销失败");
    } finally {
      setRevokingGrantId("");
    }
  }

  const teamColumns: TableColumnsType<RagTeamItem> = [
    {
      title: "团队",
      dataIndex: "name",
      width: 220,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.name}</Text>
          <Text type="secondary" copyable>{item.team_key}</Text>
        </Space>
      ),
    },
    {
      title: "范围",
      dataIndex: "position_scope",
      render: (_, item) => renderTeamScopeTags(item),
    },
    {
      title: "成员",
      dataIndex: "member_count",
      width: 80,
      render: (value) => <Tag color="blue">{Number(value || 0)}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (value) => renderRagTeamStatus(String(value) as RagTeamStatus),
    },
    {
      title: "操作",
      key: "actions",
      width: 92,
      render: (_, item) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => selectTeam(item)}>
          编辑
        </Button>
      ),
    },
  ];

  const memberColumns: TableColumnsType<RagTeamMemberItem> = [
    {
      title: "成员",
      dataIndex: "username",
      width: 220,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.display_name || item.username}</Text>
          <Text type="secondary">{item.username}</Text>
        </Space>
      ),
    },
    {
      title: "岗位",
      dataIndex: "position",
      width: 110,
      render: (value) => value && isPosition(value) ? positionLabel(value) : roleLabel("admin"),
    },
    {
      title: "角色",
      dataIndex: "member_role",
      width: 90,
      render: (value) => <Tag>{ragTeamMemberRoleLabels[String(value) as RagTeamMemberRole] || String(value)}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (value) => <StatusTag value={String(value)} />,
    },
    {
      title: "过期时间",
      dataIndex: "expires_at",
      width: 140,
      render: (value) => formatTime(value ? String(value) : null),
    },
    {
      title: "操作",
      key: "actions",
      width: 92,
      render: (_, item) => (
        <Button
          danger
          size="small"
          icon={<DeleteOutlined />}
          disabled={item.status !== "active"}
          loading={removingMemberKey === item.user_id}
          onClick={() => removeMember(item)}
        >
          移除
        </Button>
      ),
    },
  ];

  const documentColumns: TableColumnsType<DocumentAccessItem> = [
    {
      title: "文档",
      dataIndex: "title",
      width: 300,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.title}</Text>
          <Text type="secondary">{item.source || "-"}</Text>
          <Text type="secondary" copyable>{item.id}</Text>
        </Space>
      ),
    },
    {
      title: "范围",
      key: "scope",
      width: 300,
      render: (_, item) => renderDocumentScopeTags(item),
    },
    {
      title: "访问",
      dataIndex: "access_mode",
      width: 118,
      render: (value) => <Tag color="blue">{ragDocumentAccessModeLabels[String(value) as RagDocumentAccessMode] || String(value)}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (value) => <StatusTag value={String(value)} />,
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      width: 142,
      render: (value) => formatTime(value ? String(value) : null),
    },
    {
      title: "操作",
      key: "actions",
      width: 116,
      fixed: "right",
      render: (_, item) => (
        <Button
          size="small"
          icon={<SafetyCertificateOutlined />}
          loading={isLoadingDocumentAccess && documentId === item.id}
          onClick={() => selectDocument(item, { openDrawer: true })}
        >
          授权详情
        </Button>
      ),
    },
  ];

  const grantColumns: TableColumnsType<DocumentGrantItem> = [
    {
      title: "对象",
      dataIndex: "subject_name",
      width: 220,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.subject_name || item.subject_id}</Text>
          <Text type="secondary">{item.subject_type === "team" ? "团队" : "用户"}</Text>
        </Space>
      ),
    },
    {
      title: "级别",
      dataIndex: "access_level",
      width: 90,
      render: (value) => <Tag color={value === "manage" ? "purple" : "blue"}>{ragGrantAccessLevelLabels[String(value) as RagGrantAccessLevel] || String(value)}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (value) => <StatusTag value={String(value)} />,
    },
    {
      title: "原因",
      dataIndex: "reason",
      ellipsis: true,
      render: (value) => value ? String(value) : "-",
    },
    {
      title: "过期时间",
      dataIndex: "expires_at",
      width: 140,
      render: (value) => formatTime(value ? String(value) : null),
    },
    {
      title: "操作",
      key: "actions",
      width: 92,
      render: (_, item) => (
        <Popconfirm
          title="撤销文档授权"
          description={`确认撤销“${item.subject_name || item.subject_id}”的授权？`}
          okText="撤销"
          okButtonProps={{ danger: true, className: "documentGrantRevokeConfirmButton" }}
          cancelText="取消"
          disabled={item.status !== "active"}
          onConfirm={() => revokeGrant(item)}
        >
          <Button
            danger
            size="small"
            icon={<StopOutlined />}
            disabled={item.status !== "active"}
            loading={revokingGrantId === item.id}
          >
            撤销
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const documentAccessEditor = documentAccess ? (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Space direction="vertical" size={4}>
        <Text strong>{documentAccess.title}</Text>
        <Text type="secondary">{documentAccess.source || "-"}</Text>
        <Text type="secondary" copyable>{documentAccess.id}</Text>
      </Space>
      {renderDocumentScopeTags(documentAccess)}
      <Form layout="vertical">
        <Form.Item label="访问模式">
          <Select<RagDocumentAccessMode>
            value={documentAccessForm.accessMode}
            onChange={(value) => setDocumentAccessForm((current) => ({ ...current, accessMode: value }))}
            options={ragDocumentAccessModeOptions}
            virtual={false}
          />
        </Form.Item>
        <Form.Item label="owner 用户">
          <Select
            allowClear
            showSearch
            value={documentAccessForm.ownerUserId || undefined}
            onChange={(value) => setDocumentAccessForm((current) => ({ ...current, ownerUserId: value || "" }))}
            options={userOptions}
            virtual={false}
            optionFilterProp="label"
          />
        </Form.Item>
        <Form.Item label="owner 团队">
          <Select
            allowClear
            showSearch
            value={documentAccessForm.ownerTeamId || undefined}
            onChange={(value) => setDocumentAccessForm((current) => ({ ...current, ownerTeamId: value || "" }))}
            options={ownerTeamOptions}
            virtual={false}
            optionFilterProp="label"
          />
        </Form.Item>
        <Button
          type="primary"
          block
          icon={<SaveOutlined />}
          loading={isSavingDocumentAccess}
          onClick={saveDocumentAccess}
        >
          保存访问模式
        </Button>
      </Form>
    </Space>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档授权数据" />
  );

  const documentGrantEditor = documentAccess ? (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Row gutter={[12, 12]} align="bottom">
        <Col xs={24} md={5}>
          <Form.Item label="对象类型">
            <Select<RagGrantSubjectType>
              value={documentGrantForm.subjectType}
              onChange={(value) =>
                setDocumentGrantForm((current) => ({
                  ...current,
                  subjectType: value,
                  subjectId: "",
                }))
              }
              options={ragGrantSubjectTypeOptions}
              virtual={false}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={7}>
          <Form.Item label="授权对象">
            <Select
              showSearch
              value={documentGrantForm.subjectId || undefined}
              onChange={(value) => setDocumentGrantForm((current) => ({ ...current, subjectId: value }))}
              options={grantSubjectOptions}
              virtual={false}
              optionFilterProp="label"
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={4}>
          <Form.Item label="授权级别">
            <Select<RagGrantAccessLevel>
              value={documentGrantForm.accessLevel}
              onChange={(value) => setDocumentGrantForm((current) => ({ ...current, accessLevel: value }))}
              options={ragGrantAccessLevelOptions}
              virtual={false}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={4}>
          <Form.Item label="过期时间">
            <Input
              value={documentGrantForm.expiresAt}
              onChange={(event) => setDocumentGrantForm((current) => ({ ...current, expiresAt: event.target.value }))}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={4}>
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
            loading={isCreatingGrant}
            onClick={createGrant}
          >
            添加授权
          </Button>
        </Col>
        <Col xs={24}>
          <Form.Item label="授权原因">
            <Input
              value={documentGrantForm.reason}
              onChange={(event) => setDocumentGrantForm((current) => ({ ...current, reason: event.target.value }))}
            />
          </Form.Item>
        </Col>
      </Row>
      <Table<DocumentGrantItem>
        rowKey="id"
        size="small"
        columns={grantColumns}
        dataSource={documentGrants}
        loading={isLoadingDocumentAccess}
        pagination={{ pageSize: 6 }}
        scroll={{ x: 860 }}
      />
    </Space>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档授权数据" />
  );

  const documentAuthorizationDrawerContent = documentAccess ? (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <ProCard title="访问模式" bordered className="splitCard">
        {documentAccessEditor}
      </ProCard>
      <ProCard title="显式授权" bordered className="splitCard">
        {documentGrantEditor}
      </ProCard>
    </Space>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档授权数据" />
  );

  const uploadPanel = (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10} className="splitCardCol">
        <ProCard title="上传知识库" bordered className="splitCard">
          <Form layout="vertical">
            <Form.Item label="文件">
              <Upload.Dragger
                accept=".txt,.md,.pdf,.docx,.csv,.xlsx,.xls"
                multiple={false}
                maxCount={1}
                fileList={uploadFileList}
                beforeUpload={(file) => {
                  props.setFile(file);
                  return false;
                }}
                onRemove={() => props.setFile(null)}
              >
                <p className="uploadIcon">
                  <CloudUploadOutlined />
                </p>
                <p className="uploadTitle">点击或拖拽文件到此区域</p>
                <p className="uploadHint">支持 .txt / .md / .pdf / .docx / .csv / .xlsx / .xls</p>
              </Upload.Dragger>
            </Form.Item>
            <Form.Item label="可见范围">
              <Radio.Group
                optionType="button"
                buttonStyle="solid"
                value={props.visibility}
                onChange={(event) => props.setVisibility(event.target.value)}
                options={[
                  { label: "员工", value: "employee" },
                  { label: "管理员", value: "admin" },
                ]}
              />
            </Form.Item>
            <Form.Item label="部门">
              <Input value={props.department} onChange={(event) => props.setDepartment(event.target.value)} />
            </Form.Item>
            <Form.Item label="岗位范围">
              <Select<DocumentPositionScope>
                value={props.positionScope}
                onChange={props.setPositionScope}
                virtual={false}
                options={[
                  { label: "不限岗位", value: "all" },
                  ...(Object.keys(positionConfigs) as Position[]).map((item) => ({
                    label: `${positionConfigs[item].label}专属`,
                    value: item,
                  })),
                ]}
              />
            </Form.Item>
            <Form.Item label="站点范围">
              <Select<DocumentMarketScope>
                value={props.marketScope}
                onChange={props.setMarketScope}
                virtual={false}
                options={documentMarketScopeOptions}
              />
            </Form.Item>
            <Form.Item label="店铺范围">
              <Select<DocumentStoreScope>
                value={props.storeScope}
                onChange={props.setStoreScope}
                virtual={false}
                options={documentStoreScopeOptions}
              />
            </Form.Item>
            <Form.Item label="字段分类">
              <Select<DocumentFieldScope>
                value={props.fieldScope}
                onChange={props.setFieldScope}
                virtual={false}
                options={documentFieldScopeOptions}
              />
            </Form.Item>
            <Form.Item label="敏感级别">
              <Select<DocumentSensitivityLevel>
                value={props.sensitivityLevel}
                onChange={props.setSensitivityLevel}
                virtual={false}
                options={documentSensitivityLevelOptions}
              />
            </Form.Item>
            <Form.Item label="上传访问模式">
              <Select<RagDocumentAccessMode>
                value={uploadAccessForm.accessMode}
                onChange={(value) => setUploadAccessForm((current) => ({ ...current, accessMode: value }))}
                virtual={false}
                options={ragDocumentAccessModeOptions}
              />
            </Form.Item>
            <Form.Item label="上传 owner 用户">
              <Select
                allowClear
                showSearch
                value={uploadAccessForm.ownerUserId || undefined}
                onChange={(value) => setUploadAccessForm((current) => ({ ...current, ownerUserId: value || "" }))}
                options={userOptions}
                virtual={false}
                optionFilterProp="label"
              />
            </Form.Item>
            <Form.Item label="上传 owner 团队">
              <Select
                allowClear
                showSearch
                value={uploadAccessForm.ownerTeamId || undefined}
                onChange={(value) => setUploadAccessForm((current) => ({ ...current, ownerTeamId: value || "" }))}
                options={ownerTeamOptions}
                virtual={false}
                optionFilterProp="label"
              />
            </Form.Item>
            <Form.Item label="初始授权对象类型">
              <Select<RagGrantSubjectType>
                value={uploadGrantForm.subjectType}
                onChange={(value) =>
                  setUploadGrantForm((current) => ({
                    ...current,
                    subjectType: value,
                    subjectId: "",
                  }))
                }
                options={ragGrantSubjectTypeOptions}
                virtual={false}
              />
            </Form.Item>
            <Form.Item label="初始授权对象">
              <Select
                allowClear
                showSearch
                value={uploadGrantForm.subjectId || undefined}
                onChange={(value) => setUploadGrantForm((current) => ({ ...current, subjectId: value || "" }))}
                options={uploadGrantForm.subjectType === "team" ? activeTeamOptions : userOptions}
                virtual={false}
                optionFilterProp="label"
              />
            </Form.Item>
            <Form.Item label="初始授权级别">
              <Select<RagGrantAccessLevel>
                value={uploadGrantForm.accessLevel}
                onChange={(value) => setUploadGrantForm((current) => ({ ...current, accessLevel: value }))}
                options={ragGrantAccessLevelOptions}
                virtual={false}
              />
            </Form.Item>
            <Form.Item label="初始授权过期时间">
              <Input
                value={uploadGrantForm.expiresAt}
                onChange={(event) => setUploadGrantForm((current) => ({ ...current, expiresAt: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="初始授权原因">
              <Input
                value={uploadGrantForm.reason}
                onChange={(event) => setUploadGrantForm((current) => ({ ...current, reason: event.target.value }))}
              />
            </Form.Item>
            <Button
              type="primary"
              block
              icon={<CloudUploadOutlined />}
              disabled={disabled}
              loading={props.isUploading}
              onClick={uploadDocumentWithAccess}
            >
              上传到后端
            </Button>
          </Form>
        </ProCard>
      </Col>
      <Col xs={24} xl={14} className="splitCardCol">
        <ProCard title="入库流程" bordered className="splitCard">
          <div className="processList">
            {[
              "管理员上传文档",
              "LangChain Loader 解析原始文件",
              "LangChain Splitter 切分文档",
              "阿里百炼生成 embedding",
              "PGVector 写入向量库",
              "审计日志记录上传行为",
            ].map((item, index) => (
              <div className="processItem" key={item}>
                <Avatar size="small" style={{ backgroundColor: "#1677ff" }}>
                  {index + 1}
                </Avatar>
                <Text>{item}</Text>
              </div>
            ))}
          </div>
        </ProCard>
      </Col>
    </Row>
  );

  const teamsPanel = (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={8} className="splitCardCol">
        <ProCard
          title={selectedTeamId ? "编辑团队" : "创建团队"}
          bordered
          className="splitCard"
          extra={
            <Space>
              <Tooltip title="刷新团队">
                <Button icon={<ReloadOutlined />} loading={isLoadingTeams} onClick={() => refreshRagTeams()} />
              </Tooltip>
              <Tooltip title="新建团队">
                <Button icon={<PlusOutlined />} onClick={startNewTeam} />
              </Tooltip>
            </Space>
          }
        >
          <Form layout="vertical">
            <Form.Item label="团队 key">
              <Input
                value={teamForm.teamKey}
                disabled={Boolean(selectedTeamId)}
                onChange={(event) => setTeamForm((current) => ({ ...current, teamKey: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="团队名称">
              <Input
                value={teamForm.name}
                onChange={(event) => setTeamForm((current) => ({ ...current, name: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="描述">
              <TextArea
                rows={3}
                value={teamForm.description}
                onChange={(event) => setTeamForm((current) => ({ ...current, description: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="岗位范围">
              <Select<DocumentPositionScope>
                value={teamForm.positionScope}
                onChange={(value) => setTeamForm((current) => ({ ...current, positionScope: value }))}
                virtual={false}
                options={[
                  { label: "不限岗位", value: "all" },
                  ...(Object.keys(positionConfigs) as Position[]).map((item) => ({
                    label: `${positionConfigs[item].label}专属`,
                    value: item,
                  })),
                ]}
              />
            </Form.Item>
            <Form.Item label="站点范围">
              <Select<DocumentMarketScope>
                value={teamForm.marketScope}
                onChange={(value) => setTeamForm((current) => ({ ...current, marketScope: value }))}
                virtual={false}
                options={documentMarketScopeOptions}
              />
            </Form.Item>
            <Form.Item label="店铺范围">
              <Select<DocumentStoreScope>
                value={teamForm.storeScope}
                onChange={(value) => setTeamForm((current) => ({ ...current, storeScope: value }))}
                virtual={false}
                options={documentStoreScopeOptions}
              />
            </Form.Item>
            <Form.Item label="状态">
              <Select<RagTeamStatus>
                value={teamForm.status}
                onChange={(value) => setTeamForm((current) => ({ ...current, status: value }))}
                virtual={false}
                options={ragTeamStatusOptions}
              />
            </Form.Item>
            <Button
              type="primary"
              block
              icon={<SaveOutlined />}
              loading={savingTeamKey === (selectedTeamId || "new")}
              onClick={saveTeam}
            >
              {selectedTeamId ? "保存团队" : "创建团队"}
            </Button>
          </Form>
        </ProCard>
      </Col>
      <Col xs={24} xl={16} className="splitCardCol">
        <ProCard title="团队列表" bordered className="splitCard">
          <Table<RagTeamItem>
            rowKey="id"
            size="small"
            columns={teamColumns}
            dataSource={teams}
            loading={isLoadingTeams}
            pagination={{ pageSize: 6 }}
            scroll={{ x: 760 }}
          />
        </ProCard>
      </Col>
      <Col xs={24} className="splitCardCol">
        <ProCard
          title={selectedTeamId ? `团队成员：${teams.find((item) => item.id === selectedTeamId)?.name || ""}` : "团队成员"}
          bordered
          className="splitCard"
          extra={
            <Tooltip title="刷新成员">
              <Button
                icon={<ReloadOutlined />}
                disabled={!selectedTeamId}
                loading={isLoadingMembers}
                onClick={() => refreshRagTeamMembers()}
              />
            </Tooltip>
          }
        >
          <Row gutter={[12, 12]} align="bottom">
            <Col xs={24} md={8}>
              <Form.Item label="成员">
                <Select
                  showSearch
                  value={memberForm.userId || undefined}
                  onChange={(value) => setMemberForm((current) => ({ ...current, userId: value }))}
                  options={userOptions}
                  virtual={false}
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={5}>
              <Form.Item label="成员角色">
                <Select<RagTeamMemberRole>
                  value={memberForm.memberRole}
                  onChange={(value) => setMemberForm((current) => ({ ...current, memberRole: value }))}
                  options={ragTeamMemberRoleOptions}
                  virtual={false}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={7}>
              <Form.Item label="过期时间">
                <Input
                  value={memberForm.expiresAt}
                  onChange={(event) => setMemberForm((current) => ({ ...current, expiresAt: event.target.value }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={4}>
              <Button
                type="primary"
                block
                icon={<UserAddOutlined />}
                disabled={!selectedTeamId}
                loading={isAddingMember}
                onClick={addMember}
              >
                添加成员
              </Button>
            </Col>
          </Row>
          <Table<RagTeamMemberItem>
            rowKey="id"
            size="small"
            columns={memberColumns}
            dataSource={members}
            loading={isLoadingMembers}
            pagination={{ pageSize: 6 }}
            scroll={{ x: 820 }}
          />
        </ProCard>
      </Col>
    </Row>
  );

  const documentAccessPanel = (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10} className="splitCardCol">
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <ProCard
            title="文档列表"
            bordered
            className="splitCard"
            extra={
              <Tooltip title="刷新文档">
                <Button icon={<ReloadOutlined />} loading={isLoadingDocuments} onClick={() => refreshDocuments()} />
              </Tooltip>
            }
          >
            <Form layout="vertical">
              <Row gutter={[12, 12]} align="bottom">
                <Col xs={24} md={16}>
                  <Form.Item label="搜索文档">
                    <Input
                      value={documentSearch}
                      placeholder="标题、来源或文档 ID"
                      onChange={(event) => setDocumentSearch(event.target.value)}
                      onPressEnter={() => refreshDocuments()}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Button
                    type="primary"
                    block
                    icon={<SearchOutlined />}
                    loading={isLoadingDocuments}
                    onClick={() => refreshDocuments()}
                  >
                    搜索
                  </Button>
                </Col>
              </Row>
            </Form>
            <Table<DocumentAccessItem>
              rowKey="id"
              size="small"
              columns={documentColumns}
              dataSource={documents}
              loading={isLoadingDocuments}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可选文档" /> }}
              pagination={{ pageSize: 5 }}
              scroll={{ x: 1034 }}
            />
          </ProCard>

          <ProCard title="文档访问模式" bordered className="splitCard">
            <Form layout="vertical">
              <Form.Item label="文档 ID">
                <Input
                  value={documentId}
                  onChange={(event) => setDocumentId(event.target.value)}
                  onPressEnter={() => loadDocumentAuthorization()}
                />
              </Form.Item>
              <Button
                type="primary"
                block
                icon={<SearchOutlined />}
                loading={isLoadingDocumentAccess}
                onClick={() => loadDocumentAuthorization()}
              >
                加载文档
              </Button>
            </Form>

            <div className="documentAuthorizationInline">
              {documentAccessEditor}
            </div>
          </ProCard>
        </Space>
      </Col>
      <Col xs={24} xl={14} className="splitCardCol">
        <ProCard
          title="文档授权名单"
          bordered
          className="splitCard"
          extra={
            <Tooltip title="刷新授权">
              <Button
                icon={<ReloadOutlined />}
                disabled={!documentAccess}
                loading={isLoadingDocumentAccess}
                onClick={() => loadDocumentAuthorization(documentAccess?.id || documentId)}
              />
            </Tooltip>
          }
        >
          {documentGrantEditor}
        </ProCard>
      </Col>
    </Row>
  );

  return (
    <>
      <Tabs
        items={[
          {
            key: "upload",
            label: (
              <Space size={6}>
                <CloudUploadOutlined />
                上传入库
              </Space>
            ),
            children: uploadPanel,
          },
          {
            key: "teams",
            label: (
              <Space size={6}>
                <TeamOutlined />
                团队管理
              </Space>
            ),
            children: teamsPanel,
          },
          {
            key: "authorization",
            label: (
              <Space size={6}>
                <SafetyCertificateOutlined />
                文档授权
              </Space>
            ),
            children: documentAccessPanel,
          },
        ]}
      />
      <Drawer
        title="文档授权详情"
        open={isDocumentAuthDrawerOpen}
        rootClassName="documentAuthorizationDrawer"
        width="min(760px, 100vw)"
        onClose={() => setIsDocumentAuthDrawerOpen(false)}
      >
        {isLoadingDocumentAccess && !documentAccess ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="正在加载文档授权" />
        ) : (
          documentAuthorizationDrawerContent
        )}
      </Drawer>
    </>
  );
}

function emptyRagTeamForm(): RagTeamFormState {
  return {
    teamKey: "",
    name: "",
    description: "",
    positionScope: "all",
    marketScope: "all",
    storeScope: "all",
    status: "active",
  };
}

function teamFormFromItem(item: RagTeamItem): RagTeamFormState {
  return {
    teamKey: item.team_key,
    name: item.name,
    description: item.description || "",
    positionScope: item.position_scope || "all",
    marketScope: item.market_scope || "all",
    storeScope: item.store_scope || "all",
    status: item.status,
  };
}

function optionalIsoText(value: string) {
  const normalized = value.trim();
  return normalized || null;
}

function userLabel(user: UserRecord) {
  const name = user.displayName || user.username;
  const scope = user.position ? positionLabel(user.position) : roleLabel(user.role);
  return `${name} / ${scope} / ${user.username}`;
}

function labelFromOptions<T extends string>(
  options: Array<{ label: string; value: T }>,
  value: T,
) {
  return options.find((item) => item.value === value)?.label || value;
}

function renderRagTeamStatus(value: RagTeamStatus) {
  return <Tag color={ragTeamStatusColors[value] || "default"}>{ragTeamStatusLabels[value] || value}</Tag>;
}

function renderTeamScopeTags(item: RagTeamItem) {
  return (
    <Space size={[4, 4]} wrap>
      <Tag>{item.position_scope ? `${positionLabel(item.position_scope)}专属` : "不限岗位"}</Tag>
      <Tag>{labelFromOptions(documentMarketScopeOptions, item.market_scope || "all")}</Tag>
      <Tag>{labelFromOptions(documentStoreScopeOptions, item.store_scope || "all")}</Tag>
    </Space>
  );
}

function renderDocumentScopeTags(item: DocumentAccessItem) {
  return (
    <Space size={[4, 4]} wrap>
      <Tag>{item.visibility === "employee" ? "员工可见" : "管理员可见"}</Tag>
      <Tag>{item.position_scope ? `${positionLabel(item.position_scope)}专属` : "不限岗位"}</Tag>
      <Tag>{labelFromOptions(documentMarketScopeOptions, item.market_scope || "all")}</Tag>
      <Tag>{labelFromOptions(documentStoreScopeOptions, item.store_scope || "all")}</Tag>
      <Tag>{labelFromOptions(documentFieldScopeOptions, (item.field_scope || "all") as DocumentFieldScope)}</Tag>
      <Tag color={item.sensitivity_level === "restricted" ? "red" : "blue"}>
        {labelFromOptions(documentSensitivityLevelOptions, (item.sensitivity_level || "internal") as DocumentSensitivityLevel)}
      </Tag>
    </Space>
  );
}

function UsersPanel(props: {
  users: UserRecord[];
  newUser: NewUserForm;
  setNewUser: (value: NewUserForm) => void;
  createUser: () => void;
  deleteUser: (userId: string) => void;
  toggleUserAiApp: (userId: string, appId: string, enabled: boolean) => void;
  refreshUsers: () => void;
  isCreating: boolean;
  deletingUserId: string;
  updatingUserAppKey: string;
  currentUsername: string;
}) {
  const selectedPosition = props.newUser.position || "customer_service";

  function patchNewUser(patch: Partial<NewUserForm>) {
    props.setNewUser({
      ...props.newUser,
      ...patch,
    });
  }

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard title="管理员创建用户" bordered>
        <Form layout="vertical" className="userCreateForm">
          <Form.Item label="用户名">
            <Input
              value={props.newUser.username}
              onChange={(event) => patchNewUser({ username: event.target.value })}
              placeholder="例如 service_01"
            />
          </Form.Item>
          <Form.Item label="密码">
            <Input.Password
              value={props.newUser.password}
              onChange={(event) => patchNewUser({ password: event.target.value })}
              placeholder="至少 6 位"
            />
          </Form.Item>
          <Form.Item label="系统角色">
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              value={props.newUser.role}
              onChange={(event) => {
                const nextRole = event.target.value as Role;
                patchNewUser({
                  role: nextRole,
                  position: nextRole === "employee" ? selectedPosition : null,
                });
              }}
              options={[
                { label: "员工", value: "employee" },
                { label: "管理员", value: "admin" },
              ]}
            />
          </Form.Item>
          {props.newUser.role === "employee" ? (
            <Form.Item label="岗位">
              <Select
                value={selectedPosition}
                onChange={(value) =>
                  patchNewUser({
                    position: value,
                    department: props.newUser.department || positionConfigs[value].department,
                  })
                }
                options={(Object.keys(positionConfigs) as Position[]).map((item) => ({
                  label: positionConfigs[item].label,
                  value: item,
                }))}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="部门">
            <Input
              value={props.newUser.department}
              onChange={(event) => patchNewUser({ department: event.target.value })}
              placeholder={props.newUser.role === "employee" ? positionConfigs[selectedPosition].department : "管理部"}
            />
          </Form.Item>
          <Form.Item className="userCreateActions">
            <Space>
              <Button type="primary" loading={props.isCreating} onClick={props.createUser}>
                创建用户
              </Button>
              <Button icon={<ReloadOutlined />} onClick={props.refreshUsers}>
                刷新
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </ProCard>

      <ProCard title="用户详细与 AI 应用权限" bordered>
        <Table<UserRecord>
          rowKey="id"
          dataSource={props.users}
          locale={{ emptyText: <Empty description="暂无用户数据" /> }}
          scroll={{ x: 980 }}
          expandable={{
            expandedRowRender: (user) => (
              <UserAiAppPermissionGrid
                user={user}
                updatingUserAppKey={props.updatingUserAppKey}
                toggleUserAiApp={props.toggleUserAiApp}
              />
            ),
            rowExpandable: (user) => user.aiAppPermissions.length > 0,
          }}
          columns={[
            { title: "用户名", dataIndex: "username", width: 150 },
            { title: "角色", dataIndex: "role", width: 110, render: (value) => <Tag>{roleLabel(value as Role)}</Tag> },
            {
              title: "岗位",
              dataIndex: "position",
              width: 110,
              render: (value) => value ? <Tag color="purple">{positionLabel(value as Position)}</Tag> : "-",
            },
            { title: "部门", dataIndex: "department", width: 130 },
            {
              title: "AI 应用",
              dataIndex: "capabilities",
              render: (_, user) => (
                <Space size={[4, 4]} wrap>
                  <Tag color="green">{user.allowedAiAppIds.length} 个已启用</Tag>
                  <Tag>{user.aiAppPermissions.length} 个可配置</Tag>
                </Space>
              ),
            },
            { title: "创建时间", dataIndex: "createdAt", width: 150 },
            {
              title: "操作",
              width: 120,
              fixed: "right",
              render: (_, user) => {
                const canDelete = user.username !== props.currentUsername;
                return (
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    disabled={!canDelete}
                    loading={props.deletingUserId === user.id}
                    onClick={() => {
                      Modal.confirm({
                        title: `删除用户 ${user.username}`,
                        content: "删除后该用户无法再登录，历史记录中的用户关联会按数据库外键规则处理。",
                        okText: "确认删除",
                        cancelText: "取消",
                        okButtonProps: { danger: true },
                        onOk: () => props.deleteUser(user.id),
                      });
                    }}
                  >
                    删除
                  </Button>
                );
              },
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function UserAiAppPermissionGrid({
  user,
  updatingUserAppKey,
  toggleUserAiApp,
}: {
  user: UserRecord;
  updatingUserAppKey: string;
  toggleUserAiApp: (userId: string, appId: string, enabled: boolean) => void;
}) {
  return (
    <div className="userAiAppGrid">
      {user.aiAppPermissions.map((app) => {
        const loading = updatingUserAppKey === `${user.id}:${app.id}`;

        return (
          <div key={`${user.id}-${app.id}`} className="userAiAppItem">
            <div className="userAiAppInfo">
              <Text strong>{app.name}</Text>
              <Space size={[4, 4]} wrap>
                <Tag>{app.position_label}</Tag>
                <Tag color="blue">{app.category}</Tag>
              </Space>
            </div>
            <Switch
              checked={app.enabled}
              loading={loading}
              checkedChildren="启用"
              unCheckedChildren="禁用"
              onChange={(checked) => toggleUserAiApp(user.id, app.id, checked)}
            />
          </div>
        );
      })}
    </div>
  );
}

function ApprovalsPanel({
  approvals,
  reviewApproval,
  role,
  position,
}: {
  approvals: Approval[];
  reviewApproval: (id: string, approved: boolean) => void;
  role: Role;
  position: Position | null;
}) {
  const canReview = canUseApprovalCenter(role, position);

  return (
    <ProCard title="退款审批列表" subTitle="客服岗位处理用户退款、售后升级和高风险客服消息" bordered>
      <Table<Approval>
        rowKey="id"
        dataSource={approvals}
        locale={{ emptyText: <Empty description="暂无待处理退款审批" /> }}
        scroll={{ x: 1120 }}
        columns={[
          { title: "审批用途", dataIndex: "summary", width: 360, render: (value) => <Text className="approvalSummaryText">{String(value || "-")}</Text> },
          { title: "类型", dataIndex: "actionLabel", width: 150 },
          { title: "订单", dataIndex: "orderNo", width: 140 },
          { title: "金额", dataIndex: "amount", width: 140 },
          { title: "状态", dataIndex: "status", width: 120, render: (value) => <StatusTag value={String(value)} /> },
          { title: "原始原因", dataIndex: "reason", width: 220, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
          { title: "审批 ID", dataIndex: "id", width: 180, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
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
              </Space>
            ),
          },
        ]}
      />
    </ProCard>
  );
}

function RefundsPanel({ refunds }: { refunds: Refund[] }) {
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

function AuditPanel({
  logs,
  actionFilter,
  setActionFilter,
  resourceFilter,
  setResourceFilter,
  positionFilter,
  setPositionFilter,
  refreshLogs,
}: {
  logs: AuditLog[];
  actionFilter: string;
  setActionFilter: (value: string) => void;
  resourceFilter: string;
  setResourceFilter: (value: string) => void;
  positionFilter: Position | "all";
  setPositionFilter: (value: Position | "all") => void;
  refreshLogs: () => void;
}) {
  const normalizedActionFilter = actionFilter.trim().toLowerCase();
  const visibleLogs = normalizedActionFilter
    ? logs.filter((item) => {
        const searchable = `${item.action} ${item.actionLabel}`.toLowerCase();
        return searchable.includes(normalizedActionFilter);
      })
    : logs;

  return (
    <ProCard
      title="审计日志"
      bordered
      extra={
        <Space size={8} wrap>
          <Input
            size="small"
            value={actionFilter}
            placeholder="动作筛选"
            onChange={(event) => setActionFilter(event.target.value)}
            style={{ width: 180 }}
          />
          <Input
            size="small"
            value={resourceFilter}
            placeholder="资源类型"
            onChange={(event) => setResourceFilter(event.target.value)}
            style={{ width: 120 }}
          />
          <Select
            size="small"
            value={positionFilter}
            onChange={setPositionFilter}
            style={{ width: 130 }}
            options={[
              { label: "全部岗位", value: "all" },
              { label: "运营", value: "operations" },
              { label: "客服", value: "customer_service" },
              { label: "财务", value: "finance" },
            ]}
          />
          <Button size="small" icon={<SearchOutlined />} onClick={refreshLogs}>
            查询
          </Button>
        </Space>
      }
    >
      <Table<AuditLog>
        rowKey="id"
        dataSource={visibleLogs}
        locale={{ emptyText: <Empty description="暂无审计日志" /> }}
        scroll={{ x: 980 }}
        columns={[
          { title: "动作", dataIndex: "actionLabel", width: 260, ellipsis: true, render: (_, record) => <AuditActionText record={record} /> },
          { title: "资源", dataIndex: "resourceTypeLabel", width: 150, ellipsis: true, render: (_, record) => <AuditResourceTypeText record={record} /> },
          { title: "操作者", dataIndex: "actor", width: 160, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
          {
            title: "岗位",
            dataIndex: "position",
            width: 100,
            render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
          },
          { title: "时间", dataIndex: "createdAt", width: 160 },
          { title: "资源 ID", dataIndex: "resourceId", width: 220, ellipsis: true, render: (value) => <EllipsisText value={value} /> },
        ]}
      />
    </ProCard>
  );
}

function RunRecordsPanel({
  role,
  records,
  filters,
  setFilters,
  loading,
  refreshRecords,
  openDetail,
}: {
  role: Role;
  records: RunRecordItem[];
  filters: RunRecordFilterState;
  setFilters: React.Dispatch<React.SetStateAction<RunRecordFilterState>>;
  loading: boolean;
  refreshRecords: () => void;
  openDetail: (runId: string) => void;
}) {
  const statusCounts = {
    succeeded: records.filter((item) => item.status === "succeeded").length,
    failed: records.filter((item) => item.status === "failed").length,
    blocked: records.filter((item) => item.status === "blocked").length,
    running: records.filter((item) => item.status === "running").length,
  };

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="runRecordMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">记录总数</Text>
            <Title level={3}>{records.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">成功</Text>
            <Title level={3}>{statusCounts.succeeded}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">失败</Text>
            <Title level={3}>{statusCounts.failed}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">越权拦截</Text>
            <Title level={3}>{statusCounts.blocked}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="运行记录"
        subTitle={role === "admin" ? "管理员查看全平台脱敏摘要" : "当前账号只能查看自己的运行记录"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshRecords} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="runRecordFilterGrid">
          <Select
            size="small"
            value={filters.status}
            onChange={(value) => setFilters((current) => ({ ...current, status: value }))}
            options={[
              { label: "全部状态", value: "all" },
              { label: "成功", value: "succeeded" },
              { label: "失败", value: "failed" },
              { label: "拦截", value: "blocked" },
              { label: "运行中", value: "running" },
            ]}
          />
          <Input
            size="small"
            value={filters.runType}
            placeholder="类型"
            onChange={(event) => setFilters((current) => ({ ...current, runType: event.target.value }))}
          />
          <Input
            size="small"
            value={filters.appId}
            placeholder="应用 ID"
            onChange={(event) => setFilters((current) => ({ ...current, appId: event.target.value }))}
          />
          {role === "admin" && (
            <Select
              size="small"
              value={filters.position}
              onChange={(value) => setFilters((current) => ({ ...current, position: value }))}
              options={[
                { label: "全部岗位", value: "all" },
                { label: "运营", value: "operations" },
                { label: "客服", value: "customer_service" },
                { label: "财务", value: "finance" },
              ]}
            />
          )}
          <Input
            size="small"
            value={filters.resourceType}
            placeholder="资源类型"
            onChange={(event) => setFilters((current) => ({ ...current, resourceType: event.target.value }))}
          />
          <Input
            size="small"
            value={filters.resourceId}
            placeholder="资源 ID"
            onChange={(event) => setFilters((current) => ({ ...current, resourceId: event.target.value }))}
          />
          <Input
            size="small"
            value={filters.flowKey}
            placeholder="流程 Key"
            onChange={(event) => setFilters((current) => ({ ...current, flowKey: event.target.value }))}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshRecords} loading={loading}>
            查询
          </Button>
        </div>

        <Table<RunRecordItem>
          rowKey="id"
          loading={loading}
          dataSource={records}
          className="runRecordTable"
          scroll={{ x: 1260 }}
          locale={{ emptyText: <Empty description="暂无运行记录" /> }}
          columns={[
            {
              title: "应用",
              dataIndex: "app_name",
              width: 210,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{value}</Text>
                  <Text type="secondary" className="runRecordMono">{record.app_id}</Text>
                </Space>
              ),
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 92,
              render: (value) => <StatusTag value={String(value)} />,
            },
            {
              title: "类型",
              dataIndex: "run_type",
              width: 150,
              render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
            },
            {
              title: "流程版本",
              dataIndex: "flow_key",
              width: 210,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordMono">{value || "-"}</Text>
                  <Text type="secondary" className="runRecordMono">{record.flow_version || "-"}</Text>
                </Space>
              ),
            },
            {
              title: "用户/岗位",
              dataIndex: "username",
              width: 140,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text>{value || "-"}</Text>
                  {isPosition(record.position) ? <Tag color="purple">{positionLabel(record.position)}</Tag> : <Tag>管理员</Tag>}
                </Space>
              ),
            },
            {
              title: "资源",
              dataIndex: "resource_id",
              width: 180,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text type="secondary">{record.resource_type || "-"}</Text>
                  <Text className="runRecordMono">{value || "-"}</Text>
                </Space>
              ),
            },
            {
              title: "摘要",
              dataIndex: "output_preview",
              width: 260,
              render: (value, record) => (
                <Text className="runRecordPreview">
                  {record.error_message || value || record.input_preview || "-"}
                </Text>
              ),
            },
            {
              title: "耗时",
              dataIndex: "duration_ms",
              width: 90,
              render: (value) => formatDuration(value),
            },
            {
              title: "步骤/产物",
              dataIndex: "step_count",
              width: 100,
              render: (value, record) => `${value}/${record.artifact_count}`,
            },
            {
              title: "时间",
              dataIndex: "started_at",
              width: 170,
              render: (value) => formatTime(value),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 96,
              render: (value) => (
                <Button size="small" type="link" onClick={() => openDetail(String(value))}>
                  详情
                </Button>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function RunRecordDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: RunRecordDetailResponse | null;
  onClose: () => void;
}) {
  return (
    <Modal
      open={open}
      title={detail ? `运行记录 / ${detail.run.app_name}` : "运行记录"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={920}
    >
      {loading ? (
        <Empty description="正在加载运行记录详情" />
      ) : detail ? (
        <Tabs
          className="runRecordDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="runRecordDetailGrid">
                    <RunRecordDetailItem label="状态" value={<StatusTag value={detail.run.status} />} />
                    <RunRecordDetailItem label="类型" value={detail.run.run_type} mono />
                    <RunRecordDetailItem label="应用 ID" value={detail.run.app_id} mono />
                    <RunRecordDetailItem label="入口" value={detail.run.entrypoint} mono />
                    <RunRecordDetailItem label="流程 Key" value={detail.run.flow_key || "-"} mono />
                    <RunRecordDetailItem label="流程版本" value={detail.run.flow_version || "-"} mono />
                    <RunRecordDetailItem label="版本 ID" value={detail.run.flow_version_id || "-"} mono />
                    <RunRecordDetailItem label="发布指针" value={detail.run.publication_id || "-"} mono />
                    <RunRecordDetailItem label="执行来源" value={detail.run.execution_source || "-"} mono />
                    <RunRecordDetailItem label="用户" value={detail.run.username || "-"} />
                    <RunRecordDetailItem
                      label="岗位"
                      value={isPosition(detail.run.position) ? positionLabel(detail.run.position) : "管理员"}
                    />
                    <RunRecordDetailItem
                      label="资源"
                      value={`${detail.run.resource_type || "-"} / ${detail.run.resource_id || "-"}`}
                      mono
                    />
                    <RunRecordDetailItem label="耗时" value={formatDuration(detail.run.duration_ms)} />
                    <RunRecordDetailItem label="开始时间" value={formatTime(detail.run.started_at)} />
                    <RunRecordDetailItem label="结束时间" value={formatTime(detail.run.finished_at)} />
                  </div>
                </Space>
              ),
            },
            {
              key: "io",
              label: "输入输出",
              children: (
                <Row gutter={[12, 12]} className="runRecordDetailIoGrid">
                  <Col xs={24} md={12}>
                    <Card size="small" title="输入摘要" className="runRecordDetailSectionCard">
                      <Paragraph className="runRecordDetailPreview">{detail.run.input_preview || "-"}</Paragraph>
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card size="small" title="输出/错误摘要" className="runRecordDetailSectionCard">
                      <Paragraph className="runRecordDetailPreview">
                        {detail.run.error_message || detail.run.output_preview || "-"}
                      </Paragraph>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "steps",
              label: `执行步骤 ${detail.steps.length}`,
              children: (
                <Table
                  rowKey="id"
                  dataSource={detail.steps}
                  pagination={false}
                  scroll={{ x: 760 }}
                  locale={{ emptyText: <Empty description="暂无步骤" /> }}
                  columns={[
                    { title: "序号", dataIndex: "step_order", width: 70 },
                    {
                      title: "步骤",
                      dataIndex: "step_name",
                      width: 180,
                      render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
                    },
                    {
                      title: "状态",
                      dataIndex: "status",
                      width: 92,
                      render: (value) => <StatusTag value={String(value)} />,
                    },
                    { title: "Provider", dataIndex: "provider", width: 120 },
                    {
                      title: "资源",
                      dataIndex: "resource_id",
                      width: 160,
                      render: (value) => <Text className="runRecordMono">{value || "-"}</Text>,
                    },
                    {
                      title: "摘要",
                      dataIndex: "output_preview",
                      render: (value, record) => (
                        <Text className="runRecordPreview">
                          {record.error_message || value || record.input_preview || "-"}
                        </Text>
                      ),
                    },
                    {
                      title: "耗时",
                      dataIndex: "duration_ms",
                      width: 90,
                      render: (value) => formatDuration(value),
                    },
                  ]}
                />
              ),
            },
            {
              key: "artifacts",
              label: `产物引用 ${detail.artifacts.length}`,
              children: (
                <Table
                  rowKey="id"
                  dataSource={detail.artifacts}
                  pagination={false}
                  scroll={{ x: 680 }}
                  locale={{ emptyText: <Empty description="暂无产物引用" /> }}
                  columns={[
                    { title: "类型", dataIndex: "artifact_type", width: 130 },
                    {
                      title: "名称",
                      dataIndex: "name",
                      render: (value) => <Text className="runRecordText">{String(value)}</Text>,
                    },
                    {
                      title: "引用",
                      dataIndex: "external_ref",
                      width: 180,
                      render: (value) => <Text className="runRecordMono">{value || "-"}</Text>,
                    },
                    { title: "大小", dataIndex: "size_bytes", width: 100, render: (value) => formatBytes(value) },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一条运行记录" />
      )}
    </Modal>
  );
}

function RunRecordDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="runRecordDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "runRecordMono" : "runRecordText"}>{value}</Text>
    </div>
  );
}

function PlatformDraftReviewPanel({
  role,
  position,
  drafts,
  filters,
  setFilters,
  loading,
  actionKey,
  refreshDrafts,
  openDetail,
  reviewDraft,
  publishDraft,
}: {
  role: Role;
  position: Position | null;
  drafts: PlatformDraftItem[];
  filters: PlatformDraftFilterState;
  setFilters: React.Dispatch<React.SetStateAction<PlatformDraftFilterState>>;
  loading: boolean;
  actionKey: string;
  refreshDrafts: () => void;
  openDetail: (draftId: string) => void;
  reviewDraft: (draftId: string, decision: "approved" | "rejected") => void;
  publishDraft: (draftId: string) => void;
}) {
  const pendingCount = drafts.filter((item) => item.status === "pending_review").length;
  const approvedCount = drafts.filter((item) => item.status === "approved").length;
  const publishedCount = drafts.filter((item) => item.status === "published").length;
  const rejectedCount = drafts.filter((item) => item.status === "rejected").length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="platformDraftMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">待审核</Text>
            <Title level={3}>{pendingCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">已通过</Text>
            <Title level={3}>{approvedCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">已发布/发送</Text>
            <Title level={3}>{publishedCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">已驳回</Text>
            <Title level={3}>{rejectedCount}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="AI 草稿审核中心"
        subTitle={role === "admin" ? "管理员可审核全部岗位草稿" : position ? `${positionLabel(position)}岗位草稿发布闸门` : "当前账号未绑定岗位"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshDrafts} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="platformDraftToolbar">
          <Segmented
            size="small"
            value={filters.status}
            onChange={(value) => setFilters((current) => ({ ...current, status: value as PlatformDraftFilterState["status"] }))}
            options={[
              { label: "全部", value: "all" },
              { label: "待审核", value: "pending_review" },
              { label: "已通过", value: "approved" },
              { label: "已发布", value: "published" },
              { label: "已驳回", value: "rejected" },
            ]}
          />
          <Select
            size="small"
            className="platformDraftTypeSelect"
            value={filters.draftType}
            onChange={(value) => setFilters((current) => ({ ...current, draftType: value }))}
            options={[
              { label: "全部类型", value: "all" },
              { label: "Listing 草稿", value: "listing" },
              { label: "客服回复草稿", value: "customer_reply" },
            ]}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshDrafts} loading={loading}>
            查询
          </Button>
        </div>

        <Table<PlatformDraftItem>
          rowKey="id"
          loading={loading}
          dataSource={drafts}
          className="platformDraftTable"
          scroll={{ x: 1120 }}
          locale={{ emptyText: <Empty description="暂无平台草稿" /> }}
          columns={[
            {
              title: "草稿",
              dataIndex: "title",
              width: 260,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortDraftId(record.id)}</Text>
                </Space>
              ),
            },
            {
              title: "类型",
              dataIndex: "draft_type",
              width: 130,
              render: (value) => <Tag color={value === "listing" ? "blue" : "cyan"}>{platformDraftTypeLabel(String(value))}</Tag>,
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 96,
              render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
            },
            {
              title: "审核状态",
              dataIndex: "status",
              width: 118,
              render: (value) => <PlatformDraftStatusTag value={String(value)} />,
            },
            {
              title: "写回状态",
              dataIndex: "writeback_status",
              width: 140,
              render: (value) => <Tag color={platformDraftWritebackColor(String(value))}>{platformDraftWritebackLabel(String(value))}</Tag>,
            },
            {
              title: "目标",
              dataIndex: "external_target",
              width: 180,
              render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 220,
              render: (_, record) => (
                <Space size={6} wrap className="platformDraftActionCell">
                  <Button size="small" type="link" onClick={() => openDetail(record.id)}>
                    详情
                  </Button>
                  <Button
                    size="small"
                    disabled={!canReviewPlatformDraft(record)}
                    loading={actionKey === `${record.id}:approved`}
                    onClick={() => reviewDraft(record.id, "approved")}
                  >
                    通过
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={!canRejectPlatformDraft(record)}
                    loading={actionKey === `${record.id}:rejected`}
                    onClick={() => reviewDraft(record.id, "rejected")}
                  >
                    驳回
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    icon={record.draft_type === "customer_reply" ? <SendOutlined /> : <CloudUploadOutlined />}
                    disabled={record.status !== "approved"}
                    loading={actionKey === `${record.id}:publish`}
                    onClick={() => publishDraft(record.id)}
                  >
                    {platformDraftPublishButtonLabel(record)}
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function BusinessActionLoopPanel({
  role,
  position,
  data,
  loading,
  refreshLoop,
  openDraft,
  openTask,
  navigateToView,
}: {
  role: Role;
  position: Position | null;
  data: BusinessActionLoopResponse | null;
  loading: boolean;
  refreshLoop: () => void;
  openDraft: (draftId: string) => void;
  openTask: (taskId: string) => void;
  navigateToView: (view: View) => void;
}) {
  const summary = data?.summary || {
    total: 0,
    pending_review: 0,
    waiting_external: 0,
    succeeded: 0,
    failed: 0,
    unread_notifications: 0,
  };
  const items = data?.items || [];

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="businessActionMetricRow">
        <Col xs={12} lg={4}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">闭环总数</Text>
            <Title level={3}>{summary.total}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={4}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">待审核</Text>
            <Title level={3}>{summary.pending_review}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={4}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">外部执行中</Text>
            <Title level={3}>{summary.waiting_external}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={4}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">已完成</Text>
            <Title level={3}>{summary.succeeded}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={4}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">失败</Text>
            <Title level={3}>{summary.failed}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={4}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">未读通知</Text>
            <Title level={3}>{summary.unread_notifications}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="业务动作闭环"
        subTitle={role === "admin" ? "查看运营和客服 AI 触发后的草稿、审核、外部写回、发布或发送状态" : position ? `${positionLabel(position)}岗位业务动作状态` : "当前账号未绑定岗位"}
        bordered
        extra={
          <Space size={8} wrap>
            <Button size="small" onClick={() => navigateToView("platform_draft_review")}>
              草稿审核
            </Button>
            <Button size="small" onClick={() => navigateToView("platform_execution_tasks")}>
              执行任务
            </Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshLoop} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table<BusinessActionLoopItem>
          rowKey="draft_id"
          loading={loading}
          dataSource={items}
          className="businessActionLoopTable"
          scroll={{ x: 1120 }}
          locale={{ emptyText: <Empty description="暂无业务动作闭环" /> }}
          columns={[
            {
              title: "业务动作",
              dataIndex: "title",
              width: 280,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortDraftId(record.draft_id)}</Text>
                </Space>
              ),
            },
            {
              title: "类型",
              dataIndex: "draft_type",
              width: 130,
              render: (value) => <Tag color={value === "listing" ? "blue" : "cyan"}>{platformDraftTypeLabel(String(value))}</Tag>,
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 96,
              render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
            },
            {
              title: "闭环进度",
              dataIndex: "stage",
              width: 420,
              render: (_, record) => <BusinessActionLoopTimeline item={record} />,
            },
            {
              title: "外部引用",
              dataIndex: "external_reference",
              width: 170,
              render: (value) => <Text className="runRecordMono">{value ? String(value) : "-"}</Text>,
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "draft_id",
              fixed: "right",
              width: 170,
              render: (_, record) => (
                <Space size={6} wrap className="businessActionLoopActions">
                  <Button size="small" type="link" onClick={() => openDraft(record.draft_id)}>
                    草稿
                  </Button>
                  <Button
                    size="small"
                    disabled={!record.latest_task_id}
                    onClick={() => record.latest_task_id && openTask(record.latest_task_id)}
                  >
                    任务
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function BusinessActionLoopTimeline({ item }: { item: BusinessActionLoopItem }) {
  const timelineItems = businessActionLoopTimelineItems(item);
  const nextText = item.stage === "failed"
    ? item.last_error || item.writeback_message || item.next_action
    : item.next_action;

  return (
    <Space direction="vertical" size={8} className="businessLoopTimelineWrap">
      <Space size={6} wrap>
        <Tag color={businessActionStageColor(item.stage)}>{item.stage_label}</Tag>
        {item.latest_action_label ? <Tag color="blue">{item.latest_action_label}</Tag> : null}
      </Space>
      <div className="businessLoopTimeline">
        {timelineItems.map((step) => (
          <Tooltip key={step.key} title={step.description}>
            <span className={`businessLoopTimelineStep ${step.tone}`}>
              <span className="businessLoopTimelineDot" />
              <span className="businessLoopTimelineLabel">{step.label}</span>
            </span>
          </Tooltip>
        ))}
      </div>
      <Text className={item.stage === "failed" ? "runRecordPreview dangerText" : "runRecordPreview"}>
        {nextText}
      </Text>
    </Space>
  );
}

function PlatformExecutionTasksPanel({
  role,
  position,
  tasks,
  filters,
  setFilters,
  loading,
  retryingTaskId,
  refreshTasks,
  openDetail,
  retryTask,
}: {
  role: Role;
  position: Position | null;
  tasks: PlatformExecutionTaskItem[];
  filters: PlatformExecutionTaskFilterState;
  setFilters: React.Dispatch<React.SetStateAction<PlatformExecutionTaskFilterState>>;
  loading: boolean;
  retryingTaskId: string;
  refreshTasks: () => void;
  openDetail: (taskId: string) => void;
  retryTask: (taskId: string) => void;
}) {
  const queuedCount = tasks.filter((item) => item.status === "queued" || item.status === "dispatching").length;
  const waitingCount = tasks.filter((item) => item.status === "waiting_callback").length;
  const succeededCount = tasks.filter((item) => item.status === "succeeded").length;
  const failedCount = tasks.filter((item) => item.status === "failed").length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="platformTaskMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">队列中</Text>
            <Title level={3}>{queuedCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">等待回调</Text>
            <Title level={3}>{waitingCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">成功</Text>
            <Title level={3}>{succeededCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">失败</Text>
            <Title level={3}>{failedCount}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="执行任务中心"
        subTitle={role === "admin" ? "查看外部执行器任务队列、回调和重试状态" : position ? `${positionLabel(position)}岗位外部执行任务` : "当前账号未绑定岗位"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshTasks} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="platformTaskToolbar">
          <Segmented
            size="small"
            value={filters.status}
            onChange={(value) => setFilters((current) => ({ ...current, status: value as PlatformExecutionTaskFilterState["status"] }))}
            options={[
              { label: "全部", value: "all" },
              { label: "队列中", value: "queued" },
              { label: "派发中", value: "dispatching" },
              { label: "等回调", value: "waiting_callback" },
              { label: "成功", value: "succeeded" },
              { label: "失败", value: "failed" },
            ]}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshTasks} loading={loading}>
            查询
          </Button>
        </div>

        <Table<PlatformExecutionTaskItem>
          rowKey="id"
          loading={loading}
          dataSource={tasks}
          className="platformTaskTable"
          scroll={{ x: 1180 }}
          locale={{ emptyText: <Empty description="暂无执行任务" /> }}
          columns={[
            {
              title: "任务",
              dataIndex: "id",
              width: 248,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong className="runRecordText">{platformTaskDraftTitle(record)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortTaskId(record.id)}</Text>
                </Space>
              ),
            },
            {
              title: "动作类型",
              dataIndex: "action_type",
              width: 158,
              render: (value) => <Tag color="blue">{platformActionTypeLabel(String(value))}</Tag>,
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 92,
              render: (_, record) => {
                const value = platformTaskPosition(record);
                return isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-";
              },
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 118,
              render: (value) => <PlatformExecutionTaskStatusTag value={String(value)} />,
            },
            {
              title: "外部引用",
              dataIndex: "external_reference",
              width: 170,
              render: (value) => <Text className="runRecordMono">{value ? String(value) : "-"}</Text>,
            },
            {
              title: "尝试",
              dataIndex: "attempt_count",
              width: 96,
              render: (_, record) => `${record.attempt_count}/${record.max_attempts}`,
            },
            {
              title: "错误",
              dataIndex: "last_error",
              width: 230,
              render: (value) => value ? (
                <Tooltip title={String(value)}>
                  <Text className="runRecordPreview" type="danger">{String(value)}</Text>
                </Tooltip>
              ) : "-",
            },
            {
              title: "更新时间",
              dataIndex: "updated_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 150,
              render: (_, record) => (
                <Space size={6} wrap className="platformTaskActionCell">
                  <Button size="small" type="link" onClick={() => openDetail(record.id)}>
                    详情
                  </Button>
                  <Button
                    size="small"
                    disabled={!canRetryPlatformTask(record)}
                    loading={retryingTaskId === record.id}
                    onClick={() => retryTask(record.id)}
                  >
                    重试
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function PlatformExecutionTaskDetailModal({
  open,
  loading,
  task,
  role,
  retryingTaskId,
  retryTask,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  task: PlatformExecutionTaskItem | null;
  role: Role;
  retryingTaskId: string;
  retryTask: (taskId: string) => void;
  onClose: () => void;
}) {
  const canViewTechnicalDetails = role === "admin";

  return (
    <Modal
      open={open}
      title={task ? `执行任务 / ${shortTaskId(task.id)}` : "执行任务详情"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="retry"
          disabled={!task || !canRetryPlatformTask(task)}
          loading={task ? retryingTaskId === task.id : false}
          onClick={() => task && retryTask(task.id)}
        >
          重试任务
        </Button>,
      ]}
      width="min(960px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载执行任务详情" />
      ) : task ? (
        <Tabs
          className="platformTaskDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="platformTaskDetailGrid">
                    <RunRecordDetailItem label="状态" value={<PlatformExecutionTaskStatusTag value={task.status} />} />
                    <RunRecordDetailItem label="动作类型" value={platformActionTypeLabel(task.action_type)} />
                    <RunRecordDetailItem label="草稿标题" value={platformTaskDraftTitle(task)} />
                    <RunRecordDetailItem
                      label="岗位"
                      value={isPosition(platformTaskPosition(task)) ? positionLabel(platformTaskPosition(task) as Position) : "-"}
                    />
                    <RunRecordDetailItem label="目标" value={task.target || "-"} mono />
                    <RunRecordDetailItem label="外部引用" value={task.external_reference || "-"} mono />
                    <RunRecordDetailItem label="尝试次数" value={`${task.attempt_count}/${task.max_attempts}`} />
                    <RunRecordDetailItem label="更新时间" value={formatTime(task.updated_at)} />
                    <RunRecordDetailItem label="完成时间" value={formatTime(task.completed_at)} />
                    <RunRecordDetailItem label="下次重试" value={formatTime(task.next_attempt_at)} />
                  </div>
                  {task.last_error ? (
                    <Paragraph className="platformTaskError">{task.last_error}</Paragraph>
                  ) : null}
                </Space>
              ),
            },
            {
              key: "business",
              label: "业务进度",
              children: (
                <PlatformExecutionTaskBusinessView
                  task={task}
                  canViewTechnicalDetails={canViewTechnicalDetails}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一条执行任务" />
      )}
    </Modal>
  );
}

function PlatformExecutionTaskBusinessView({
  task,
  canViewTechnicalDetails,
}: {
  task: PlatformExecutionTaskItem;
  canViewTechnicalDetails: boolean;
}) {
  const requestPayload = task.request_payload || {};
  const responsePayload = task.response_payload || {};
  const metadata = task.metadata || {};
  const content = task.draft?.content || recordFromUnknown(requestPayload.content);
  const draftType = task.draft?.draft_type || task.draft_type || textFromUnknown(requestPayload.draft_type || metadata.draft_type);
  const actionPhase = textFromUnknown(requestPayload.action_phase || "");
  const finalPublish = Boolean(metadata.final_publish) || actionPhase === "publish_or_send";
  const executorName = textFromUnknown(metadata.executor_name || metadata.executor_type || "");
  const businessTarget = platformTaskBusinessTarget(task, content);
  const successMessage = platformTaskBusinessResult(task, responsePayload);
  const nextAction = platformTaskNextAction(task, finalPublish);
  const failureReason = platformTaskFailureReason(task, responsePayload);

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <div className="businessTaskSummaryGrid">
        <RunRecordDetailItem label="当前状态" value={<PlatformExecutionTaskStatusTag value={String(task.status)} />} />
        <RunRecordDetailItem label="业务动作" value={platformActionTypeLabel(task.action_type)} />
        <RunRecordDetailItem label="草稿" value={platformTaskDraftTitle(task)} />
        <RunRecordDetailItem label="目标对象" value={businessTarget} mono />
        <RunRecordDetailItem label="外部系统" value={platformExternalTargetLabel(task.target || textFromUnknown(requestPayload.external_target || ""))} />
        <RunRecordDetailItem label="执行器" value={executorName || "等待配置"} />
        <RunRecordDetailItem label="外部引用" value={task.external_reference || textFromUnknown(responsePayload.external_reference || responsePayload.id || "-")} mono />
        <RunRecordDetailItem label="尝试次数" value={`${task.attempt_count}/${task.max_attempts}`} />
      </div>

      <Card size="small" title="业务时间线" className="businessDraftSectionCard">
        <div className="businessTaskTimeline">
          {platformTaskTimelineItems(task, finalPublish).map((item) => (
            <div key={item.key} className={`businessTaskTimelineItem ${item.tone}`}>
              <span className="businessTaskTimelineDot" />
              <div className="businessTaskTimelineBody">
                <Text strong>{item.title}</Text>
                <Text type="secondary" className="businessTaskTimelineText">{item.description}</Text>
                {item.time ? <Text type="secondary" className="runRecordMono">{item.time}</Text> : null}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {failureReason ? (
        <Card size="small" title="失败原因" className="businessDraftSectionCard">
          <Paragraph className="businessTaskFailureText">{failureReason}</Paragraph>
        </Card>
      ) : (
        <Card size="small" title={task.status === "succeeded" ? "执行结果" : "下一步"} className="businessDraftSectionCard">
          <Paragraph className="businessDraftText">
            {task.status === "succeeded" ? successMessage : nextAction}
          </Paragraph>
        </Card>
      )}

      {draftType === "listing" ? (
        <ListingTaskBusinessSummary content={content} />
      ) : draftType === "customer_reply" ? (
        <CustomerReplyTaskBusinessSummary content={content} />
      ) : null}

      {canViewTechnicalDetails ? (
        <Collapse
          size="small"
          className="technicalDetailsCollapse"
          items={[
            {
              key: "raw",
              label: "管理员技术详情",
              children: <PlatformExecutionTaskTechnicalView task={task} />,
            },
          ]}
        />
      ) : null}
    </Space>
  );
}

function ListingTaskBusinessSummary({ content }: { content: Record<string, unknown> }) {
  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} md={12}>
        <Card size="small" title="Listing 标题" className="businessDraftSectionCard">
          <Paragraph className="businessDraftText">{textFromUnknown(content.listing_title || "待确认")}</Paragraph>
        </Card>
      </Col>
      <Col xs={24} md={12}>
        <Card size="small" title="SKU / 站点" className="businessDraftSectionCard">
          <Space direction="vertical" size={6} className="pageStack">
            <RunRecordDetailItem label="SKU" value={textFromUnknown(content.sku || "待确认")} mono />
            <RunRecordDetailItem label="站点" value={textFromUnknown(content.marketplace || "待确认")} />
          </Space>
        </Card>
      </Col>
    </Row>
  );
}

function CustomerReplyTaskBusinessSummary({ content }: { content: Record<string, unknown> }) {
  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} md={12}>
        <Card size="small" title="客服回复摘要" className="businessDraftSectionCard">
          <Paragraph className="businessDraftText">{textFromUnknown(content.reply_draft || "待确认")}</Paragraph>
        </Card>
      </Col>
      <Col xs={24} md={12}>
        <Card size="small" title="订单与风险" className="businessDraftSectionCard">
          <Space direction="vertical" size={6} className="pageStack">
            <RunRecordDetailItem label="订单号" value={textFromUnknown(content.order_no || "待确认")} mono />
            <RunRecordDetailItem label="风险等级" value={<RiskTag value={textFromUnknown(content.risk_level || "unprocessed")} />} />
          </Space>
        </Card>
      </Col>
    </Row>
  );
}

function PlatformExecutionTaskTechnicalView({ task }: { task: PlatformExecutionTaskItem }) {
  return (
    <Space direction="vertical" size={12} className="pageStack">
      <Card size="small" title="请求内容" className="businessDraftSectionCard">
        <pre className="platformDraftPre">{JSON.stringify(task.request_payload || {}, null, 2)}</pre>
      </Card>
      <Card size="small" title="响应内容" className="businessDraftSectionCard">
        <pre className="platformDraftPre">{JSON.stringify(task.response_payload || {}, null, 2)}</pre>
      </Card>
      <Card size="small" title="元数据" className="businessDraftSectionCard">
        <pre className="platformDraftPre">{JSON.stringify(task.metadata || {}, null, 2)}</pre>
      </Card>
    </Space>
  );
}

function NotificationsPanel({
  notifications,
  filters,
  setFilters,
  loading,
  markingNotificationId,
  markingAllRead,
  refreshNotifications,
  markRead,
  markAllRead,
  openResource,
}: {
  notifications: NotificationItem[];
  filters: NotificationFilterState;
  setFilters: React.Dispatch<React.SetStateAction<NotificationFilterState>>;
  loading: boolean;
  markingNotificationId: string;
  markingAllRead: boolean;
  refreshNotifications: () => void;
  markRead: (notificationId: string) => void;
  markAllRead: () => void;
  openResource: (notification: NotificationItem) => void;
}) {
  const unreadCount = notifications.filter((item) => item.status === "unread").length;
  const readCount = notifications.filter((item) => item.status === "read").length;
  const actionableCount = notifications.filter((item) => item.resource_id).length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="notificationMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">未读</Text>
            <Title level={3}>{unreadCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">已读</Text>
            <Title level={3}>{readCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">关联资源</Text>
            <Title level={3}>{actionableCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">通知总数</Text>
            <Title level={3}>{notifications.length}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="通知中心"
        subTitle="接收草稿审核、外部执行器回调、重试结果等业务提醒"
        bordered
        extra={
          <Space size={8} wrap>
            <Button size="small" onClick={markAllRead} loading={markingAllRead} disabled={!unreadCount}>
              全部已读
            </Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshNotifications} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <div className="notificationToolbar">
          <Segmented
            size="small"
            value={filters.status}
            onChange={(value) => setFilters((current) => ({ ...current, status: value as NotificationFilterState["status"] }))}
            options={[
              { label: "全部", value: "all" },
              { label: "未读", value: "unread" },
              { label: "已读", value: "read" },
            ]}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshNotifications} loading={loading}>
            查询
          </Button>
        </div>

        <Table<NotificationItem>
          rowKey="id"
          loading={loading}
          dataSource={notifications}
          className="notificationTable"
          scroll={{ x: 1040 }}
          locale={{ emptyText: <Empty description="暂无通知" /> }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 96,
              render: (value) => <NotificationStatusTag value={String(value)} />,
            },
            {
              title: "通知",
              dataIndex: "title",
              width: 280,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text strong={record.status === "unread"} className="runRecordText">{String(value)}</Text>
                  <Text type="secondary" className="runRecordMono">{notificationTypeLabel(record.type)}</Text>
                </Space>
              ),
            },
            {
              title: "内容",
              dataIndex: "body",
              render: (value) => (
                <Tooltip title={String(value || "")}>
                  <Text className="runRecordPreview">{String(value || "-")}</Text>
                </Tooltip>
              ),
            },
            {
              title: "关联资源",
              dataIndex: "resource_id",
              width: 180,
              render: (_, record) => record.resource_id ? (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordText">{notificationResourceLabel(record.resource_type)}</Text>
                  <Text type="secondary" className="runRecordMono">{shortTaskId(record.resource_id)}</Text>
                </Space>
              ) : "-",
            },
            {
              title: "时间",
              dataIndex: "created_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 160,
              render: (_, record) => (
                <Space size={6} wrap className="notificationActionCell">
                  <Button
                    size="small"
                    type="link"
                    disabled={!record.resource_id}
                    onClick={() => openResource(record)}
                  >
                    查看
                  </Button>
                  <Button
                    size="small"
                    disabled={record.status === "read"}
                    loading={markingNotificationId === record.id}
                    onClick={() => markRead(record.id)}
                  >
                    已读
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function FeedbackImprovementPanel({
  items,
  summary,
  filters,
  setFilters,
  form,
  setForm,
  loading,
  submitting,
  refreshFeedback,
  submitFeedback,
}: {
  items: FeedbackItem[];
  summary: FeedbackSummary;
  filters: FeedbackFilterState;
  setFilters: React.Dispatch<React.SetStateAction<FeedbackFilterState>>;
  form: FeedbackFormState;
  setForm: React.Dispatch<React.SetStateAction<FeedbackFormState>>;
  loading: boolean;
  submitting: boolean;
  refreshFeedback: () => void;
  submitFeedback: () => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <FeedbackMetricRow summary={summary} />

      <ProCard
        title="提交反馈改进"
        subTitle="把平台不好用、重复操作仍然多、想新增的自动化流程提交给管理员处理"
        bordered
      >
        <Row gutter={[12, 12]} className="feedbackFormGrid">
          <Col xs={24} md={8} lg={6}>
            <Text type="secondary">反馈分类</Text>
            <Select<FeedbackCategory>
              className="fullWidthControl"
              value={form.category}
              options={feedbackCategoryOptions}
              onChange={(value) => setForm((current) => ({ ...current, category: value }))}
            />
          </Col>
          <Col xs={24} md={8} lg={6}>
            <Text type="secondary">优先级</Text>
            <Select<FeedbackPriority>
              className="fullWidthControl"
              value={form.priority}
              options={feedbackPriorityOptions}
              onChange={(value) => setForm((current) => ({ ...current, priority: value }))}
            />
          </Col>
          <Col xs={24} md={8} lg={12}>
            <Text type="secondary">标题</Text>
            <Input
              value={form.title}
              maxLength={120}
              placeholder="例如：财务工资表导出希望增加部门筛选"
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
            />
          </Col>
          <Col xs={24}>
            <Text type="secondary">具体内容</Text>
            <TextArea
              rows={4}
              maxLength={3000}
              showCount
              value={form.description}
              placeholder="请写清楚出现在哪个页面、现在要手工做什么、希望 AI 或自动化帮你做到什么程度。"
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </Col>
          <Col xs={24}>
            <Space className="feedbackFormActions">
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={submitting}
                onClick={submitFeedback}
              >
                提交反馈
              </Button>
              <Button icon={<ReloadOutlined />} onClick={refreshFeedback} loading={loading}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </ProCard>

      <ProCard
        title="我的反馈"
        subTitle="管理员完成后，这里会显示处理状态和完成说明"
        bordered
        extra={
          <Space size={8} wrap>
            <Segmented
              size="small"
              value={filters.status}
              onChange={(value) => setFilters((current) => ({ ...current, status: value as FeedbackFilterState["status"] }))}
              options={[
                { label: "全部", value: "all" },
                { label: "待处理", value: "open" },
                { label: "已完成", value: "completed" },
              ]}
            />
            <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshFeedback} loading={loading}>
              查询
            </Button>
          </Space>
        }
      >
        <Table<FeedbackItem>
          rowKey="id"
          loading={loading}
          dataSource={items}
          className="feedbackTable"
          scroll={{ x: 980 }}
          locale={{ emptyText: <Empty description="暂无反馈记录" /> }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              render: (value) => <FeedbackStatusTag value={String(value)} />,
            },
            {
              title: "反馈",
              dataIndex: "title",
              width: 320,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Tooltip title={record.description}>
                    <Text strong className="runRecordText">{String(value || "-")}</Text>
                  </Tooltip>
                  <Text type="secondary" className="runRecordPreview">{record.description}</Text>
                </Space>
              ),
            },
            {
              title: "分类",
              dataIndex: "category",
              width: 120,
              render: (value) => <Tag>{String(value || "-")}</Tag>,
            },
            {
              title: "优先级",
              dataIndex: "priority",
              width: 110,
              render: (value) => <FeedbackPriorityTag value={String(value)} />,
            },
            {
              title: "处理说明",
              dataIndex: "admin_note",
              render: (value) => (
                <Tooltip title={String(value || "管理员处理完成后会显示说明")}>
                  <Text className="runRecordPreview">{String(value || "-")}</Text>
                </Tooltip>
              ),
            },
            {
              title: "提交时间",
              dataIndex: "created_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "完成时间",
              dataIndex: "completed_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function FeedbackCenterPanel({
  items,
  summary,
  filters,
  setFilters,
  loading,
  completingFeedbackId,
  refreshFeedback,
  completeFeedback,
}: {
  items: FeedbackItem[];
  summary: FeedbackSummary;
  filters: FeedbackFilterState;
  setFilters: React.Dispatch<React.SetStateAction<FeedbackFilterState>>;
  loading: boolean;
  completingFeedbackId: string;
  refreshFeedback: () => void;
  completeFeedback: (feedback: FeedbackItem) => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <FeedbackMetricRow summary={summary} />

      <ProCard
        title="反馈中心"
        subTitle="集中处理员工提交的平台问题、体验建议和自动化改进需求"
        bordered
        extra={
          <Space size={8} wrap>
            <Segmented
              size="small"
              value={filters.status}
              onChange={(value) => setFilters((current) => ({ ...current, status: value as FeedbackFilterState["status"] }))}
              options={[
                { label: "全部", value: "all" },
                { label: "待处理", value: "open" },
                { label: "已完成", value: "completed" },
              ]}
            />
            <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshFeedback} loading={loading}>
              查询
            </Button>
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshFeedback} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table<FeedbackItem>
          rowKey="id"
          loading={loading}
          dataSource={items}
          className="feedbackTable"
          scroll={{ x: 1220 }}
          locale={{ emptyText: <Empty description="暂无员工反馈" /> }}
          columns={[
            {
              title: "状态",
              dataIndex: "status",
              width: 100,
              fixed: "left",
              render: (value) => <FeedbackStatusTag value={String(value)} />,
            },
            {
              title: "反馈内容",
              dataIndex: "title",
              width: 340,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Tooltip title={record.description}>
                    <Text strong className="runRecordText">{String(value || "-")}</Text>
                  </Tooltip>
                  <Text type="secondary" className="runRecordPreview">{record.description}</Text>
                </Space>
              ),
            },
            {
              title: "提交人",
              dataIndex: "username",
              width: 170,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Text className="runRecordText">{record.display_name || record.username}</Text>
                  <Text type="secondary" className="runRecordMono">{record.username}</Text>
                </Space>
              ),
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 100,
              render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
            },
            {
              title: "分类",
              dataIndex: "category",
              width: 120,
              render: (value) => <Tag>{String(value || "-")}</Tag>,
            },
            {
              title: "优先级",
              dataIndex: "priority",
              width: 110,
              render: (value) => <FeedbackPriorityTag value={String(value)} />,
            },
            {
              title: "处理说明",
              dataIndex: "admin_note",
              render: (value) => (
                <Tooltip title={String(value || "")}>
                  <Text className="runRecordPreview">{String(value || "-")}</Text>
                </Tooltip>
              ),
            },
            {
              title: "提交时间",
              dataIndex: "created_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 130,
              render: (_, record) => (
                <Button
                  size="small"
                  type={record.status === "open" ? "primary" : "default"}
                  disabled={record.status !== "open"}
                  loading={completingFeedbackId === record.id}
                  onClick={() => completeFeedback(record)}
                >
                  {record.status === "open" ? "完成" : "已完成"}
                </Button>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function FeedbackMetricRow({ summary }: { summary: FeedbackSummary }) {
  return (
    <Row gutter={[12, 12]} className="feedbackMetricRow">
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">待处理</Text>
          <Title level={3}>{summary.open}</Title>
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">已完成</Text>
          <Title level={3}>{summary.completed}</Title>
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">反馈总数</Text>
          <Title level={3}>{summary.total}</Title>
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card size="small" className="runRecordMetricCard feedbackMetricCard">
          <Text type="secondary">完成率</Text>
          <Title level={3}>{summary.total ? Math.round((summary.completed / summary.total) * 100) : 0}%</Title>
        </Card>
      </Col>
    </Row>
  );
}

function PlatformDraftDetailModal({
  open,
  loading,
  detail,
  role,
  actionKey,
  reviewComment,
  setReviewComment,
  reviewDraft,
  publishDraft,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: PlatformDraftDetailResponse | null;
  role: Role;
  actionKey: string;
  reviewComment: string;
  setReviewComment: (value: string) => void;
  reviewDraft: (draftId: string, decision: "approved" | "rejected") => void;
  publishDraft: (draftId: string) => void;
  onClose: () => void;
}) {
  const draft = detail?.item || null;
  const canViewTechnicalDetails = role === "admin";

  return (
    <Modal
      open={open}
      title={draft ? `草稿审核 / ${draft.title}` : "草稿审核"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="reject"
          danger
          disabled={!draft || !canRejectPlatformDraft(draft)}
          loading={draft ? actionKey === `${draft.id}:rejected` : false}
          onClick={() => draft && reviewDraft(draft.id, "rejected")}
        >
          驳回
        </Button>,
        <Button
          key="approve"
          disabled={!draft || !canReviewPlatformDraft(draft)}
          loading={draft ? actionKey === `${draft.id}:approved` : false}
          onClick={() => draft && reviewDraft(draft.id, "approved")}
        >
          审核通过
        </Button>,
        <Button
          key="publish"
          type="primary"
          disabled={!draft || draft.status !== "approved"}
          loading={draft ? actionKey === `${draft.id}:publish` : false}
          onClick={() => draft && publishDraft(draft.id)}
        >
          {draft ? platformDraftPublishButtonLabel(draft) : "发布/发送"}
        </Button>,
      ]}
      width={940}
    >
      {loading ? (
        <Empty description="正在加载草稿详情" />
      ) : draft ? (
        <Tabs
          className="platformDraftDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={14} className="pageStack">
                  <div className="platformDraftDetailGrid">
                    <RunRecordDetailItem label="类型" value={platformDraftTypeLabel(draft.draft_type)} />
                    <RunRecordDetailItem
                      label="岗位"
                      value={isPosition(draft.position) ? positionLabel(draft.position) : draft.position}
                    />
                    <RunRecordDetailItem label="审核状态" value={<PlatformDraftStatusTag value={draft.status} />} />
                    <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
                    <RunRecordDetailItem label="平台" value={draft.platform} />
                    <RunRecordDetailItem label="外部目标" value={draft.external_target} mono />
                    <RunRecordDetailItem label="创建时间" value={formatTime(draft.created_at)} />
                    <RunRecordDetailItem label="更新时间" value={formatTime(draft.updated_at)} />
                  </div>
                  {draft.writeback_message ? (
                    <Paragraph className="platformDraftMessage">{draft.writeback_message}</Paragraph>
                  ) : null}
                  <TextArea
                    value={reviewComment}
                    onChange={(event) => setReviewComment(event.target.value)}
                    placeholder="审核意见，可选"
                    autoSize={{ minRows: 2, maxRows: 4 }}
                  />
                </Space>
              ),
            },
            {
              key: "content",
              label: "业务内容",
              children: <PlatformDraftBusinessView draft={draft} canViewTechnicalDetails={canViewTechnicalDetails} />,
            },
            {
              key: "executions",
              label: `执行记录 ${detail?.executions.length || 0}`,
              children: (
                <Table<PlatformActionExecutionItem>
                  rowKey="id"
                  dataSource={detail?.executions || []}
                  pagination={false}
                  scroll={{ x: 780 }}
                  locale={{ emptyText: <Empty description="暂无执行记录" /> }}
                  columns={[
                    {
                      title: "动作",
                      dataIndex: "action_type",
                      width: 160,
                      render: (value) => <Text className="runRecordMono">{platformActionTypeLabel(String(value))}</Text>,
                    },
                    {
                      title: "状态",
                      dataIndex: "status",
                      width: 120,
                      render: (value) => <Tag color={platformExecutionStatusColor(String(value))}>{platformExecutionStatusLabel(String(value))}</Tag>,
                    },
                    { title: "执行器", dataIndex: "executor_type", width: 120, render: (value) => platformExecutorTypeLabel(String(value)) },
                    {
                      title: "目标",
                      dataIndex: "target",
                      render: (value) => <Text className="runRecordMono">{String(value)}</Text>,
                    },
                    { title: "时间", dataIndex: "created_at", width: 150, render: (value) => formatTime(String(value || "")) },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一条草稿" />
      )}
    </Modal>
  );
}

function PlatformDraftBusinessView({
  draft,
  canViewTechnicalDetails,
}: {
  draft: PlatformDraftItem;
  canViewTechnicalDetails: boolean;
}) {
  return (
    <Space direction="vertical" size={14} className="pageStack">
      {draft.draft_type === "listing" ? (
        <ListingDraftBusinessView draft={draft} />
      ) : draft.draft_type === "customer_reply" ? (
        <CustomerReplyDraftBusinessView draft={draft} />
      ) : (
        <GenericDraftBusinessView draft={draft} />
      )}
      {canViewTechnicalDetails ? (
        <Collapse
          size="small"
          className="technicalDetailsCollapse"
          items={[
            {
              key: "raw",
              label: "管理员技术详情",
              children: (
                <pre className="platformDraftPre">
                  {JSON.stringify(draft.content, null, 2)}
                </pre>
              ),
            },
          ]}
        />
      ) : null}
    </Space>
  );
}

function ListingDraftBusinessView({ draft }: { draft: PlatformDraftItem }) {
  const content = draft.content || {};
  const bullets = stringListFromUnknown(content.five_bullets);
  const fullPackage = textFromUnknown(content.full_listing_package || "");

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <div className="businessDraftSummaryGrid">
        <RunRecordDetailItem label="SKU" value={textFromUnknown(content.sku || "待确认")} mono />
        <RunRecordDetailItem label="站点" value={textFromUnknown(content.marketplace || "待确认")} />
        <RunRecordDetailItem label="审核要求" value={content.review_required ? "需要运营人工审核" : "无需人工审核"} />
        <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
      </div>

      <Card size="small" title="Listing 标题" className="businessDraftSectionCard">
        <Paragraph className="businessDraftText">{textFromUnknown(content.listing_title || draft.title)}</Paragraph>
      </Card>

      <Card size="small" title="五点描述" className="businessDraftSectionCard">
        {bullets.length ? (
          <ol className="businessDraftList">
            {bullets.map((item, index) => (
              <li key={`${index}-${item}`}>{item}</li>
            ))}
          </ol>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无五点描述" />
        )}
      </Card>

      <Row gutter={[12, 12]}>
        <Col xs={24} md={12}>
          <Card size="small" title="后台关键词" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">{textFromUnknown(content.backend_search_terms || "待补充")}</Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="促销文案" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">{textFromUnknown(content.promo_copy || "待补充")}</Paragraph>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="发布策略" className="businessDraftSectionCard">
        <Paragraph className="businessDraftText">
          {textFromUnknown(content.publish_policy || "AI 已保存草稿，必须由运营人工审核后发布。")}
        </Paragraph>
      </Card>

      {fullPackage ? (
        <Card size="small" title="完整 Listing 草稿" className="businessDraftSectionCard">
          <Paragraph className="businessDraftLongText">{fullPackage}</Paragraph>
        </Card>
      ) : null}
    </Space>
  );
}

function CustomerReplyDraftBusinessView({ draft }: { draft: PlatformDraftItem }) {
  const content = draft.content || {};
  const riskLevel = textFromUnknown(content.risk_level || "unprocessed");
  const intent = textFromUnknown(content.intent || "general_question");

  return (
    <Space direction="vertical" size={14} className="pageStack">
      <div className="businessDraftSummaryGrid">
        <RunRecordDetailItem label="客户消息 ID" value={textFromUnknown(content.customer_message_id || "-")} mono />
        <RunRecordDetailItem label="订单号" value={textFromUnknown(content.order_no || "待确认")} mono />
        <RunRecordDetailItem label="物流单号" value={textFromUnknown(content.tracking_no || "待确认")} mono />
        <RunRecordDetailItem label="渠道" value={textFromUnknown(content.channel || draft.platform || "-")} />
        <RunRecordDetailItem label="语言" value={textFromUnknown(content.buyer_language || "待确认")} />
        <RunRecordDetailItem label="问题类型" value={customerIntentLabel(intent)} />
        <RunRecordDetailItem label="风险等级" value={<RiskTag value={riskLevel} />} />
        <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
      </div>

      <Card size="small" title="客服回复草稿" className="businessDraftSectionCard">
        <Paragraph className="businessDraftLongText">
          {textFromUnknown(content.reply_draft || "尚未生成回复草稿")}
        </Paragraph>
      </Card>

      <Row gutter={[12, 12]}>
        <Col xs={24} md={12}>
          <Card size="small" title="自动化判断" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">
              {textFromUnknown(content.automation_decision || "待客服人工复核")}
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title="转人工原因" className="businessDraftSectionCard">
            <Paragraph className="businessDraftText">
              {textFromUnknown(content.handoff_reason || (riskLevel === "high" ? "高风险问题，需要人工审核。" : "暂无转人工原因。"))}
            </Paragraph>
          </Card>
        </Col>
      </Row>

      <Card size="small" title="发送策略" className="businessDraftSectionCard">
        <Paragraph className="businessDraftText">
          {textFromUnknown(content.send_policy || "AI 已保存客服回复草稿，发送前必须由客服确认。")}
        </Paragraph>
      </Card>
    </Space>
  );
}

function GenericDraftBusinessView({ draft }: { draft: PlatformDraftItem }) {
  return (
    <Card size="small" title="业务摘要" className="businessDraftSectionCard">
      <Space direction="vertical" size={10} className="pageStack">
        <div className="businessDraftSummaryGrid">
          <RunRecordDetailItem label="草稿类型" value={platformDraftTypeLabel(draft.draft_type)} />
          <RunRecordDetailItem label="平台" value={draft.platform} />
          <RunRecordDetailItem label="外部目标" value={draft.external_target} mono />
          <RunRecordDetailItem label="写回状态" value={platformDraftWritebackLabel(draft.writeback_status)} />
        </div>
        <Paragraph className="businessDraftText">
          当前草稿类型还没有专用业务视图。请由管理员在技术详情中确认字段，再补充岗位化展示模板。
        </Paragraph>
      </Space>
    </Card>
  );
}

function GeneratedFilesPanel({
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
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">可下载文件</Text>
            <Title level={3}>{files.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">Excel</Text>
            <Title level={3}>{excelCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
            <Text type="secondary">Word</Text>
            <Title level={3}>{wordCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="runRecordMetricCard">
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

function GeneratedFileBusinessSummary({ file }: { file: GeneratedFileItem }) {
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

function EffectAnalyticsPanel({
  role,
  analytics,
  filters,
  setFilters,
  loading,
  refreshAnalytics,
}: {
  role: Role;
  analytics: EffectAnalyticsResponse | null;
  filters: EffectAnalyticsFilterState;
  setFilters: React.Dispatch<React.SetStateAction<EffectAnalyticsFilterState>>;
  loading: boolean;
  refreshAnalytics: () => void;
}) {
  const summary = analytics?.summary;
  const maxTrend = Math.max(1, ...(analytics?.trend || []).map((item) => item.total_runs));
  const maxStatus = Math.max(1, ...(analytics?.status_distribution || []).map((item) => item.count));

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="效果分析"
        subTitle={role === "admin" ? "基于真实运行记录和审计事件的全平台只读指标" : "当前账号仅查看自己的执行效果"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshAnalytics} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className={role === "admin" ? "effectAnalyticsToolbar admin" : "effectAnalyticsToolbar"}>
          <Segmented
            size="small"
            value={filters.dateRange}
            onChange={(value) => setFilters((current) => ({ ...current, dateRange: value as EffectAnalyticsFilterState["dateRange"] }))}
            options={[
              { label: "近7天", value: "7d" },
              { label: "近30天", value: "30d" },
              { label: "近90天", value: "90d" },
              { label: "全部", value: "all" },
            ]}
          />
          {role === "admin" && (
            <Select
              size="small"
              value={filters.position}
              onChange={(value) => setFilters((current) => ({ ...current, position: value }))}
              options={[
                { label: "全部岗位", value: "all" },
                { label: "运营", value: "operations" },
                { label: "客服", value: "customer_service" },
                { label: "财务", value: "finance" },
              ]}
            />
          )}
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshAnalytics} loading={loading}>
            查询
          </Button>
        </div>
      </ProCard>

      <Row gutter={[12, 12]} className="effectMetricRow">
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard">
            <Text type="secondary">自动化次数</Text>
            <Title level={3}>{summary?.total_runs ?? 0}</Title>
            <Text type="secondary">{analytics?.scope.date_range_label || "近 30 天"}</Text>
          </Card>
        </Col>
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard">
            <Text type="secondary">成功率</Text>
            <Title level={3}>{formatPercent(summary?.success_rate)}</Title>
            <Text type="secondary">{summary?.succeeded_runs ?? 0} 次成功</Text>
          </Card>
        </Col>
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard">
            <Text type="secondary">越权拦截</Text>
            <Title level={3}>{summary?.blocked_runs ?? 0}</Title>
            <Text type="secondary">{formatPercent(summary?.blocked_rate)} 拦截率</Text>
          </Card>
        </Col>
        <Col xs={12} xl={6}>
          <Card size="small" className="effectMetricCard">
            <Text type="secondary">估算节省</Text>
            <Title level={3}>{summary?.estimated_saved_hours ?? 0}h</Title>
            <Text type="secondary">按成功执行保守估算</Text>
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={14} className="effectPanelCol">
          <ProCard title="执行趋势" bordered className="effectPanelCard">
            {analytics?.trend.length ? (
              <div className="effectTrendChart" aria-label="执行趋势">
                {analytics.trend.map((item) => (
                  <div className="effectTrendBar" key={item.date}>
                    <div className="effectTrendDate">{item.date.slice(5)}</div>
                    <div className="effectTrendTrack">
                      <span className="effectTrendSucceeded" style={{ height: `${Math.max(8, (item.succeeded_runs / maxTrend) * 100)}%` }} />
                      <span className="effectTrendFailed" style={{ height: `${Math.max(item.failed_runs ? 8 : 0, (item.failed_runs / maxTrend) * 100)}%` }} />
                      <span className="effectTrendBlocked" style={{ height: `${Math.max(item.blocked_runs ? 8 : 0, (item.blocked_runs / maxTrend) * 100)}%` }} />
                    </div>
                    <Text className="effectTrendTotal">{item.total_runs}</Text>
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无趋势数据" />
            )}
          </ProCard>
        </Col>
        <Col xs={24} xl={10} className="effectPanelCol">
          <ProCard title="状态分布" bordered className="effectPanelCard">
            <div className="effectStatusList">
              {(analytics?.status_distribution || []).map((item) => (
                <div className="effectStatusItem" key={item.status}>
                  <div className="effectStatusHeader">
                    <StatusTag value={item.status} />
                    <Text strong>{item.count}</Text>
                  </div>
                  <div className="effectProgressTrack">
                    <span className={`effectProgressBar ${item.status}`} style={{ width: `${(item.count / maxStatus) * 100}%` }} />
                  </div>
                </div>
              ))}
              {!analytics?.status_distribution.length && <Empty description="暂无状态数据" />}
            </div>
          </ProCard>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12} className="effectPanelCol">
          <ProCard title="岗位效果排行" bordered className="effectPanelCard">
            <Table
              rowKey="position"
              size="small"
              dataSource={analytics?.position_ranking || []}
              pagination={false}
              scroll={{ x: 560 }}
              locale={{ emptyText: <Empty description="暂无岗位数据" /> }}
              columns={[
                { title: "岗位", dataIndex: "position_label", width: 110, render: (value) => <Text strong>{String(value)}</Text> },
                { title: "次数", dataIndex: "total_runs", width: 78 },
                { title: "成功率", dataIndex: "success_rate", width: 92, render: (value) => formatPercent(value) },
                { title: "失败", dataIndex: "failed_runs", width: 72 },
                { title: "拦截", dataIndex: "blocked_runs", width: 72 },
                { title: "节省", dataIndex: "estimated_saved_minutes", render: (value) => `${value} 分钟` },
              ]}
            />
          </ProCard>
        </Col>
        <Col xs={24} xl={12} className="effectPanelCol">
          <ProCard title="应用使用排行" bordered className="effectPanelCard">
            <Table
              rowKey="app_id"
              size="small"
              dataSource={analytics?.app_ranking || []}
              pagination={false}
              scroll={{ x: 680 }}
              locale={{ emptyText: <Empty description="暂无应用数据" /> }}
              columns={[
                {
                  title: "应用",
                  dataIndex: "app_name",
                  width: 210,
                  render: (value, record) => (
                    <Space direction="vertical" size={2} className="effectCellStack">
                      <Text strong className="effectText">{String(value)}</Text>
                      <Text className="effectMono">{record.app_id}</Text>
                    </Space>
                  ),
                },
                { title: "次数", dataIndex: "total_runs", width: 78 },
                { title: "成功率", dataIndex: "success_rate", width: 92, render: (value) => formatPercent(value) },
                { title: "最近运行", dataIndex: "last_run_at", render: (value) => formatTime(value) },
              ]}
            />
          </ProCard>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12} className="effectPanelCol">
          <ProCard title="失败与拦截原因" bordered className="effectPanelCard">
            <Table
              rowKey={(record) => `${record.status}-${record.reason}`}
              size="small"
              dataSource={analytics?.failure_reasons || []}
              pagination={false}
              scroll={{ x: 640 }}
              locale={{ emptyText: <Empty description="暂无失败或拦截" /> }}
              columns={[
                { title: "状态", dataIndex: "status", width: 92, render: (value) => <StatusTag value={String(value)} /> },
                { title: "原因", dataIndex: "reason", render: (value) => <Text className="effectText">{String(value)}</Text> },
                { title: "次数", dataIndex: "count", width: 76 },
                { title: "最近", dataIndex: "last_seen_at", width: 130, render: (value) => formatTime(value) },
              ]}
            />
          </ProCard>
        </Col>
        <Col xs={24} xl={12} className="effectPanelCol">
          <ProCard title="审计安全摘要" bordered className="effectPanelCard">
            <div className="effectAuditSummary">
              <div>
                <Text type="secondary">审计事件</Text>
                <Title level={4}>{analytics?.audit_summary.total_events ?? 0}</Title>
              </div>
              <div>
                <Text type="secondary">权限拦截</Text>
                <Title level={4}>{analytics?.audit_summary.blocked_events ?? 0}</Title>
              </div>
              <div>
                <Text type="secondary">审批事件</Text>
                <Title level={4}>{analytics?.audit_summary.approval_events ?? 0}</Title>
              </div>
            </div>
            <Table
              rowKey={(record) => `${record.action}-${record.resource_type}`}
              size="small"
              dataSource={analytics?.audit_summary.top_actions || []}
              pagination={false}
              scroll={{ x: 560 }}
              locale={{ emptyText: <Empty description="暂无审计事件" /> }}
              columns={[
                { title: "动作", dataIndex: "action", render: (value) => <Text className="effectMono">{String(value)}</Text> },
                { title: "资源", dataIndex: "resource_type", width: 110, render: (value) => value || "-" },
                { title: "次数", dataIndex: "count", width: 76 },
                { title: "最近", dataIndex: "last_seen_at", width: 130, render: (value) => formatTime(value) },
              ]}
            />
          </ProCard>
        </Col>
      </Row>

      <ProCard title="估算口径" bordered>
        <div className="effectEstimateGrid">
          {(analytics?.estimate_model || []).map((item) => (
            <div className="effectEstimateItem" key={item.run_type}>
              <Text className="effectMono">{item.run_type}</Text>
              <Text strong>{item.saved_minutes_per_run} 分钟/次</Text>
              <Text type="secondary" className="effectText">{item.description}</Text>
            </div>
          ))}
        </div>
      </ProCard>
    </Space>
  );
}

function EvaluationCenterPanel({
  data,
  loading,
  runningEvaluationId,
  refreshEvaluationCenter,
  runEvaluation,
}: {
  data: EvaluationCenterResponse | null;
  loading: boolean;
  runningEvaluationId: string;
  refreshEvaluationCenter: () => void;
  runEvaluation: (datasetId: string) => void;
}) {
  const summary = data?.summary;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="AI 评测中心"
        subTitle="管理员专属，只展示真实评测摘要和发布闸门，不返回原始 chunk 内容"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshEvaluationCenter} loading={loading}>
            刷新
          </Button>
        }
      >
        <Row gutter={[12, 12]} className="evaluationMetricRow">
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard">
              <Text type="secondary">评测集</Text>
              <Title level={3}>{summary?.dataset_count ?? 0}</Title>
              <Text type="secondary">真实 JSONL 资产</Text>
            </Card>
          </Col>
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard">
              <Text type="secondary">样本数</Text>
              <Title level={3}>{summary?.total_cases ?? 0}</Title>
              <Text type="secondary">RAG + 回归套件</Text>
            </Card>
          </Col>
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard">
              <Text type="secondary">平均通过率</Text>
              <Title level={3}>{formatPercent(summary?.average_pass_rate)}</Title>
              <Text type="secondary">基于已有报告</Text>
            </Card>
          </Col>
          <Col xs={12} xl={6}>
            <Card size="small" className="evaluationMetricCard">
              <Text type="secondary">回归套件</Text>
              <Title level={3}>{summary?.regression_suite_count ?? 0}</Title>
              <Text type="secondary">真实脚本覆盖</Text>
            </Card>
          </Col>
        </Row>
      </ProCard>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={14} className="evaluationPanelCol">
          <ProCard title="评测集资产" bordered className="evaluationPanelCard">
            <Table
              rowKey="id"
              loading={loading}
              dataSource={data?.datasets || []}
              pagination={false}
              scroll={{ x: 820 }}
              locale={{ emptyText: <Empty description="暂无评测集" /> }}
              columns={[
                {
                  title: "评测集",
                  dataIndex: "name",
                  width: 230,
                  render: (value, record) => (
                    <Space direction="vertical" size={2} className="evaluationCellStack">
                      <Text strong className="evaluationText">{String(value)}</Text>
                      <Text className="evaluationMono">{record.path}</Text>
                    </Space>
                  ),
                },
                { title: "类型", dataIndex: "category", width: 92, render: (value) => <Tag color="blue">{String(value)}</Tag> },
                { title: "样本", dataIndex: "case_count", width: 82 },
                { title: "正/拒答", dataIndex: "positive_cases", width: 108, render: (value, record) => `${value}/${record.refusal_cases}` },
                { title: "报告", dataIndex: "has_report", width: 82, render: (value) => <Tag color={value ? "green" : "default"}>{value ? "已有" : "暂无"}</Tag> },
                { title: "更新", dataIndex: "report_updated_at", width: 132, render: (value) => formatTime(value) },
                {
                  title: "操作",
                  dataIndex: "id",
                  fixed: "right",
                  width: 112,
                  render: (value, record) => (
                    <Button
                      size="small"
                      type="primary"
                      disabled={!record.can_run || record.id !== "rag_smoke"}
                      loading={runningEvaluationId === record.id}
                      onClick={() => runEvaluation(String(value))}
                    >
                      运行
                    </Button>
                  ),
                },
              ]}
            />
          </ProCard>
        </Col>
        <Col xs={24} xl={10} className="evaluationPanelCol">
          <ProCard title="发布闸门" bordered className="evaluationPanelCard">
            <div className="evaluationGateList">
              {(data?.release_gates || []).map((item) => (
                <div className="evaluationGateItem" key={item.id}>
                  <div className="evaluationGateHeader">
                    <Text strong className="evaluationText">{item.name}</Text>
                    <Tag color={evaluationGateColor(item.status)}>{labelForBadge(item.status)}</Tag>
                  </div>
                  <Text type="secondary" className="evaluationText">阈值：{item.threshold}</Text>
                  <Text className="evaluationMono">{item.actual}</Text>
                </div>
              ))}
              {!data?.release_gates.length && <Empty description="暂无发布闸门" />}
            </div>
          </ProCard>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={13} className="evaluationPanelCol">
          <ProCard title="最近评测报告" bordered className="evaluationPanelCard">
            <Table
              rowKey="dataset_id"
              dataSource={data?.reports || []}
              pagination={false}
              scroll={{ x: 760 }}
              locale={{ emptyText: <Empty description="暂无评测报告" /> }}
              columns={[
                {
                  title: "报告",
                  dataIndex: "dataset_name",
                  width: 220,
                  render: (value, record) => (
                    <Space direction="vertical" size={2} className="evaluationCellStack">
                      <Text strong className="evaluationText">{String(value)}</Text>
                      <Text className="evaluationMono">{record.dataset_id}</Text>
                    </Space>
                  ),
                },
                { title: "通过率", dataIndex: "pass_rate", width: 92, render: (value) => formatPercent(value) },
                { title: "Hit@5", dataIndex: "metrics", width: 88, render: (value) => formatPercent(metricValue(value, "hit@5")) },
                { title: "MRR", dataIndex: "metrics", width: 88, render: (value) => formatNumber(metricValue(value, "MRR")) },
                { title: "拒答", dataIndex: "metrics", width: 88, render: (value) => formatPercent(metricValue(value, "refusal_accuracy")) },
                { title: "样本", dataIndex: "counts", width: 78, render: (value) => String(metricValue(value, "total_cases") ?? 0) },
                { title: "更新", dataIndex: "updated_at", render: (value) => formatTime(value) },
              ]}
            />
          </ProCard>
        </Col>
        <Col xs={24} xl={11} className="evaluationPanelCol">
          <ProCard title="失败样例摘要" bordered className="evaluationPanelCard">
            <div className="evaluationFailureList">
              {(data?.reports || []).flatMap((report) => report.failed_cases.map((item) => ({
                ...(item as Record<string, unknown>),
                dataset: report.dataset_name,
              } as Record<string, unknown>))).slice(0, 8).map((item) => (
                <div className="evaluationFailureItem" key={`${item.dataset}-${String(item.id)}`}>
                  <div className="evaluationGateHeader">
                    <Text strong className="evaluationText">{String(item.id || "-")}</Text>
                    <Tag color="red">{String(item.type || "failed")}</Tag>
                  </div>
                  <Text type="secondary" className="evaluationText">{String(item.dataset)}</Text>
                  <Text className="evaluationText">{String(item.reason || "-")}</Text>
                </div>
              ))}
              {!data?.reports.some((report) => report.failed_cases.length) && <Empty description="暂无失败样例" />}
            </div>
          </ProCard>
        </Col>
      </Row>

      <ProCard title="真实回归套件" bordered>
        <Table
          rowKey="id"
          dataSource={data?.regression_suites || []}
          pagination={false}
          scroll={{ x: 860 }}
          locale={{ emptyText: <Empty description="暂无回归套件" /> }}
          columns={[
            {
              title: "套件",
              dataIndex: "name",
              width: 220,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="evaluationCellStack">
                  <Text strong className="evaluationText">{String(value)}</Text>
                  <Text type="secondary" className="evaluationText">{record.description}</Text>
                </Space>
              ),
            },
            { title: "类型", dataIndex: "category", width: 110, render: (value) => <Tag color="purple">{String(value)}</Tag> },
            { title: "用例", dataIndex: "case_count", width: 72 },
            { title: "真实服务", dataIndex: "real_services", width: 220, render: (value: string[]) => <Space size={[4, 4]} wrap>{value.map((item) => <Tag key={item}>{item}</Tag>)}</Space> },
            { title: "命令", dataIndex: "command", render: (value) => <Text className="evaluationMono">{String(value)}</Text> },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function MonitoringCenterPanel({
  data,
  filters,
  setFilters,
  loading,
  refreshMonitoringCenter,
}: {
  data: MonitoringCenterResponse | null;
  filters: MonitoringCenterFilterState;
  setFilters: React.Dispatch<React.SetStateAction<MonitoringCenterFilterState>>;
  loading: boolean;
  refreshMonitoringCenter: () => void;
}) {
  const summary = data?.run_summary;
  const maxTrend = Math.max(1, ...(data?.run_trend || []).map((item) => item.total_runs));

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="监控中心"
        subTitle="管理员专属，聚合真实 API、数据库、ERP、连接器、运行记录、审计和 AI 评测状态"
        bordered
        extra={
          <Space size={8} wrap>
            <Tag color={monitoringStatusColor(data?.overall_status || "unknown")}>
              {monitoringStatusLabel(data?.overall_status || "unknown")}
            </Tag>
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshMonitoringCenter} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <div className="monitoringToolbar">
          <Segmented
            size="small"
            value={filters.dateRange}
            onChange={(value) => setFilters({ dateRange: value as MonitoringCenterFilterState["dateRange"] })}
            options={[
              { label: "近7天", value: "7d" },
              { label: "近30天", value: "30d" },
              { label: "近90天", value: "90d" },
              { label: "全部", value: "all" },
            ]}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshMonitoringCenter} loading={loading}>
            查询
          </Button>
          <Text type="secondary" className="monitoringGeneratedAt">
            生成时间：{formatTime(data?.scope.generated_at || null)}
          </Text>
        </div>
      </ProCard>

      <Row gutter={[12, 12]} className="monitoringMetricRow">
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">运行总数</Text>
            <Title level={3}>{summary?.total_runs ?? 0}</Title>
            <Text type="secondary">{data?.scope.date_range_label || "近 30 天"}</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">成功率</Text>
            <Title level={3}>{formatPercent(summary?.success_rate)}</Title>
            <Text type="secondary">{summary?.succeeded_runs ?? 0} 次成功</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">问题事件</Text>
            <Title level={3}>{(summary?.failed_runs ?? 0) + (summary?.blocked_runs ?? 0)}</Title>
            <Text type="secondary">失败 + 权限拦截</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <Card size="small" className="monitoringMetricCard">
            <Text type="secondary">P95 耗时</Text>
            <Title level={3}>{formatDuration(summary?.p95_duration_ms)}</Title>
            <Text type="secondary">平均 {formatDuration(summary?.avg_duration_ms)}</Text>
          </Card>
        </Col>
      </Row>

      <Tabs
        className="monitoringCenterTabs"
        items={[
          {
            key: "overview",
            label: "总览",
            children: (
              <Space direction="vertical" size={12} className="pageStack">
                <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                  <Col xs={24} xl={15} className="monitoringPanelCol">
                    <ProCard title="服务健康" bordered className="monitoringPanelCard">
                      <div className="monitoringHealthGrid">
                        {(data?.service_health || []).map((item) => (
                          <div className="monitoringHealthItem" key={item.id}>
                            <div className="monitoringHealthHeader">
                              <Text strong className="monitoringText">{item.name}</Text>
                              <Tag color={monitoringStatusColor(item.status)}>{monitoringStatusLabel(item.status)}</Tag>
                            </div>
                            <Text className="monitoringMetricText">{item.metric}</Text>
                            <Text type="secondary" className="monitoringText">{item.message}</Text>
                          </div>
                        ))}
                        {!data?.service_health.length && <Empty description="暂无服务健康数据" />}
                      </div>
                    </ProCard>
                  </Col>
                  <Col xs={24} xl={9} className="monitoringPanelCol">
                    <ProCard title="基础资产" bordered className="monitoringPanelCard">
                      <div className="monitoringAssetGrid">
                        <MonitoringAsset label="用户" value={data?.users.total_users ?? 0} hint={`${data?.users.items.length ?? 0} 个角色/岗位桶`} />
                        <MonitoringAsset label="文档" value={data?.knowledge.active_documents ?? 0} hint={`${data?.knowledge.child_chunks ?? 0} 个向量切片`} />
                        <MonitoringAsset label="连接器" value={data?.connectors.summary.total ?? 0} hint={`${data?.connectors.summary.healthy ?? 0} 个健康`} />
                        <MonitoringAsset label="评测样本" value={data?.evaluation.summary.total_cases ?? 0} hint={`${data?.evaluation.summary.report_count ?? 0} 份报告`} />
                      </div>
                    </ProCard>
                  </Col>
                </Row>

                <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                  <Col xs={24} xl={14} className="monitoringPanelCol">
                    <ProCard title="运行趋势" bordered className="monitoringPanelCard">
                      {data?.run_trend.length ? (
                        <div className="monitoringTrendChart" aria-label="运行趋势">
                          {data.run_trend.map((item) => (
                            <div className="monitoringTrendBar" key={item.date}>
                              <div className="monitoringTrendDate">{item.date.slice(5)}</div>
                              <div className="monitoringTrendTrack">
                                <span className="monitoringTrendSucceeded" style={{ height: `${Math.max(8, (item.succeeded_runs / maxTrend) * 100)}%` }} />
                                <span className="monitoringTrendFailed" style={{ height: `${Math.max(item.failed_runs ? 8 : 0, (item.failed_runs / maxTrend) * 100)}%` }} />
                                <span className="monitoringTrendBlocked" style={{ height: `${Math.max(item.blocked_runs ? 8 : 0, (item.blocked_runs / maxTrend) * 100)}%` }} />
                              </div>
                              <Text className="monitoringTrendTotal">{item.total_runs}</Text>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty description="暂无运行趋势" />
                      )}
                    </ProCard>
                  </Col>
                  <Col xs={24} xl={10} className="monitoringPanelCol">
                    <ProCard title="ERP 与 AI 评测" bordered className="monitoringPanelCard">
                      <div className="monitoringSignalList">
                        <div className="monitoringSignalItem">
                          <div className="monitoringHealthHeader">
                            <Text strong className="monitoringText">ERP 连接</Text>
                            <Tag color={monitoringStatusColor(data?.erp_health.ok ? "ok" : data?.erp_health.status || "unknown")}>
                              {data?.erp_health.provider_label || "ERP"}
                            </Tag>
                          </div>
                          <Text type="secondary" className="monitoringText">{data?.erp_health.message || "-"}</Text>
                        </div>
                        <div className="monitoringSignalItem">
                          <div className="monitoringHealthHeader">
                            <Text strong className="monitoringText">AI 评测通过率</Text>
                            <Tag color={monitoringStatusColor(data?.evaluation.status || "unknown")}>
                              {monitoringStatusLabel(data?.evaluation.status || "unknown")}
                            </Tag>
                          </div>
                          <Text className="monitoringMetricText">{formatPercent(data?.evaluation.summary.average_pass_rate)}</Text>
                          <Text type="secondary" className="monitoringText">最近报告：{formatTime(data?.evaluation.latest_report_at || null)}</Text>
                        </div>
                      </div>
                    </ProCard>
                  </Col>
                </Row>
              </Space>
            ),
          },
          {
            key: "issues",
            label: "运行问题",
            children: (
              <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="最近问题" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="id"
                      size="small"
                      loading={loading}
                      dataSource={data?.recent_issues || []}
                      pagination={false}
                      scroll={{ x: 560 }}
                      locale={{ emptyText: <Empty description="暂无失败或拦截事件" /> }}
                      columns={[
                        { title: "状态", dataIndex: "status", width: 82, render: (value) => <StatusTag value={String(value)} /> },
                        {
                          title: "应用",
                          dataIndex: "app_name",
                          width: 190,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">{String(value)}</Text>
                              <Text type="secondary" className="monitoringText">{record.summary || record.run_type_label}</Text>
                            </Space>
                          ),
                        },
                        { title: "岗位", dataIndex: "position_label", width: 76 },
                        { title: "时间", dataIndex: "occurred_at", render: (value) => formatTime(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="慢任务 Top" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="id"
                      size="small"
                      loading={loading}
                      dataSource={data?.slow_runs || []}
                      pagination={false}
                      scroll={{ x: 560 }}
                      locale={{ emptyText: <Empty description="暂无耗时记录" /> }}
                      columns={[
                        {
                          title: "应用",
                          dataIndex: "app_name",
                          width: 190,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">{String(value)}</Text>
                              <Text className="monitoringMono">{record.run_type}</Text>
                            </Space>
                          ),
                        },
                        { title: "状态", dataIndex: "status", width: 82, render: (value) => <StatusTag value={String(value)} /> },
                        { title: "岗位", dataIndex: "position_label", width: 76 },
                        { title: "耗时", dataIndex: "duration_ms", render: (value) => formatDuration(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "distribution",
            label: "分布分析",
            children: (
              <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="岗位运行分布" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="position"
                      size="small"
                      dataSource={data?.position_summary || []}
                      pagination={false}
                      scroll={{ x: 620 }}
                      locale={{ emptyText: <Empty description="暂无岗位运行数据" /> }}
                      columns={[
                        { title: "岗位", dataIndex: "position_label", width: 110, render: (value) => <Text strong>{String(value)}</Text> },
                        { title: "次数", dataIndex: "total_runs", width: 78 },
                        { title: "成功率", dataIndex: "success_rate", width: 92, render: (value) => formatPercent(value) },
                        { title: "失败", dataIndex: "failed_runs", width: 72 },
                        { title: "拦截", dataIndex: "blocked_runs", width: 72 },
                        { title: "均耗时", dataIndex: "avg_duration_ms", render: (value) => formatDuration(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="自动化类型分布" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="run_type"
                      size="small"
                      dataSource={data?.run_type_summary || []}
                      pagination={false}
                      scroll={{ x: 720 }}
                      locale={{ emptyText: <Empty description="暂无类型运行数据" /> }}
                      columns={[
                        {
                          title: "类型",
                          dataIndex: "label",
                          width: 190,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">{String(value)}</Text>
                              <Text className="monitoringMono">{record.run_type}</Text>
                            </Space>
                          ),
                        },
                        { title: "次数", dataIndex: "total_runs", width: 78 },
                        { title: "成功率", dataIndex: "success_rate", width: 92, render: (value) => formatPercent(value) },
                        { title: "均耗时", dataIndex: "avg_duration_ms", width: 92, render: (value) => formatDuration(value) },
                        { title: "最近", dataIndex: "latest_run_at", render: (value) => formatTime(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
          {
            key: "connectors",
            label: "连接审计",
            children: (
              <Row gutter={[12, 12]} className="monitoringCenterTabGrid">
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="连接器状态" bordered className="monitoringPanelCard">
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={data?.connectors.items || []}
                      pagination={false}
                      scroll={{ x: 620 }}
                      locale={{ emptyText: <Empty description="暂无连接器状态" /> }}
                      columns={[
                        {
                          title: "连接器",
                          dataIndex: "label",
                          width: 180,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="monitoringCellStack">
                              <Text strong className="monitoringText">{String(value)}</Text>
                              <Text type="secondary" className="monitoringText">{record.category}</Text>
                            </Space>
                          ),
                        },
                        { title: "状态", dataIndex: "status", width: 96, render: (value) => <ConnectorStatusTag status={String(value)} /> },
                        { title: "检查", dataIndex: "supports_real_health_check", width: 72, render: (value) => value ? "已接入" : "未接入" },
                        { title: "说明", dataIndex: "health_message", render: (value) => <Text className="monitoringText">{String(value)}</Text> },
                      ]}
                    />
                  </ProCard>
                </Col>
                <Col xs={24} xl={12} className="monitoringPanelCol">
                  <ProCard title="审计动作 Top" bordered className="monitoringPanelCard">
                    <div className="monitoringAuditSummary">
                      <MonitoringAsset label="审计事件" value={data?.audit_summary.total_events ?? 0} hint="当前筛选范围" />
                      <MonitoringAsset label="权限事件" value={data?.audit_summary.security_events ?? 0} hint="拦截/拒绝/权限" />
                      <MonitoringAsset label="审批事件" value={data?.audit_summary.approval_events ?? 0} hint="审批相关" />
                    </div>
                    <Table
                      rowKey={(record) => `${record.action}-${record.resource_type}`}
                      size="small"
                      dataSource={data?.audit_actions || []}
                      pagination={false}
                      scroll={{ x: 620 }}
                      locale={{ emptyText: <Empty description="暂无审计动作" /> }}
                      columns={[
                        { title: "动作", dataIndex: "action", render: (value) => <Text className="monitoringMono">{String(value)}</Text> },
                        { title: "资源", dataIndex: "resource_type", width: 110, render: (value) => value || "-" },
                        { title: "次数", dataIndex: "count", width: 78 },
                        { title: "最近", dataIndex: "last_seen_at", width: 132, render: (value) => formatTime(value) },
                      ]}
                    />
                  </ProCard>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </Space>
  );
}

function MonitoringAsset({ label, value, hint }: { label: string; value: React.ReactNode; hint: string }) {
  return (
    <div className="monitoringAssetItem">
      <Text type="secondary">{label}</Text>
      <Title level={4}>{value}</Title>
      <Text type="secondary" className="monitoringText">{hint}</Text>
    </div>
  );
}

function AutomationFlowsPanel({
  role,
  flows,
  filters,
  setFilters,
  loading,
  refreshFlows,
  openDetail,
}: {
  role: Role;
  flows: AutomationFlowItem[];
  filters: AutomationFlowFilterState;
  setFilters: React.Dispatch<React.SetStateAction<AutomationFlowFilterState>>;
  loading: boolean;
  refreshFlows: () => void;
  openDetail: (flowId: string) => void;
}) {
  const enabledCount = flows.filter((item) => item.status === "enabled").length;
  const categories = Array.from(new Set(flows.map((item) => item.category))).filter(Boolean);
  const erpResourceCount = new Set(
    flows.flatMap((item) => item.allowed_erp_resources.map((resource) => resource.resource)),
  ).size;
  const approvalCount = flows.filter((item) => item.approval_policy.includes("审批")).length;

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="flowConfigMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">流程总数</Text>
            <Title level={3}>{flows.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">已发布</Text>
            <Title level={3}>{enabledCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">ERP 资源</Text>
            <Title level={3}>{erpResourceCount}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="flowConfigMetricCard">
            <Text type="secondary">审批策略</Text>
            <Title level={3}>{approvalCount}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="自动化流程配置"
        subTitle={role === "admin" ? "管理员查看全平台只读流程定义" : "当前账号只能查看自己岗位的流程定义"}
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshFlows} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className={role === "admin" ? "flowConfigFilterGrid admin" : "flowConfigFilterGrid"}>
          {role === "admin" ? (
            <Select
              size="small"
              value={filters.position}
              onChange={(value) => setFilters((current) => ({ ...current, position: value }))}
              options={[
                { label: "全部岗位", value: "all" },
                { label: "运营", value: "operations" },
                { label: "客服", value: "customer_service" },
                { label: "财务", value: "finance" },
              ]}
            />
          ) : null}
          <Select
            size="small"
            allowClear
            value={filters.category || undefined}
            placeholder="流程类别"
            onChange={(value) => setFilters((current) => ({ ...current, category: value || "" }))}
            options={categories.map((item) => ({ label: item, value: item }))}
          />
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshFlows} loading={loading}>
            查询
          </Button>
        </div>

        <Table<AutomationFlowItem>
          rowKey="id"
          loading={loading}
          dataSource={flows}
          className="flowConfigTable"
          scroll={{ x: 1160 }}
          locale={{ emptyText: <Empty description="暂无流程配置" /> }}
          columns={[
            {
              title: "流程",
              dataIndex: "name",
              width: 230,
              render: (value, record) => (
                <Space direction="vertical" size={2} className="flowConfigCellStack">
                  <Text strong className="flowConfigText">{value}</Text>
                  <Text type="secondary" className="flowConfigMono">{record.app_id}</Text>
                </Space>
              ),
            },
            {
              title: "岗位",
              dataIndex: "position_label",
              width: 96,
              render: (value, record) => (
                <Tag color={record.position ? "purple" : "blue"}>{String(value)}</Tag>
              ),
            },
            {
              title: "类别",
              dataIndex: "category",
              width: 130,
              render: (value) => <Text className="flowConfigText">{String(value)}</Text>,
            },
            {
              title: "入口",
              dataIndex: "entrypoint",
              width: 210,
              render: (value) => <Text className="flowConfigMono">{String(value)}</Text>,
            },
            {
              title: "状态",
              dataIndex: "status",
              width: 92,
              render: (value) => <StatusTag value={String(value)} />,
            },
            {
              title: "版本",
              dataIndex: "version",
              width: 110,
              render: (value) => <Text className="flowConfigMono">{String(value)}</Text>,
            },
            {
              title: "允许资源",
              dataIndex: "allowed_erp_resources",
              width: 170,
              render: (value: ErpResourceItem[]) => (
                <Space size={[4, 4]} wrap>
                  {value.length ? (
                    <>
                      <Tag color="geekblue">{value.length} 项</Tag>
                      {value.slice(0, 2).map((item) => (
                        <Tag key={item.resource}>{item.label}</Tag>
                      ))}
                    </>
                  ) : (
                    <Text type="secondary">无 ERP 资源</Text>
                  )}
                </Space>
              ),
            },
            {
              title: "说明",
              dataIndex: "description",
              width: 260,
              render: (value) => <Text className="flowConfigPreview">{String(value)}</Text>,
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 96,
              render: (value) => (
                <Button size="small" type="link" onClick={() => openDetail(String(value))}>
                  详情
                </Button>
              ),
            },
          ]}
        />
      </ProCard>
    </Space>
  );
}

function schemaDraftJson(items: Array<Record<string, unknown>> | null | undefined) {
  return JSON.stringify(items || [], null, 2);
}

function toolParametersDraftJson(modelConfig: Record<string, unknown> | null | undefined) {
  const parameters = modelConfig?.tool_parameters;
  if (!parameters || typeof parameters !== "object" || Array.isArray(parameters)) {
    return "{}";
  }
  return JSON.stringify(parameters, null, 2);
}

function AutomationFlowDetailModal({
  open,
  loading,
  detail,
  token,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: AutomationFlowDetailResponse | null;
  token: string;
  onClose: () => void;
}) {
  const flow = detail?.item || null;
  const [versions, setVersions] = useState<AutomationFlowVersionSummary[]>([]);
  const [isVersionListLoading, setIsVersionListLoading] = useState(false);
  const [versionActionKey, setVersionActionKey] = useState("");
  const [editingVersionId, setEditingVersionId] = useState("");
  const [versionPreflightResult, setVersionPreflightResult] = useState<AutomationFlowVersionPreflightResponse | null>(null);
  const [versionEvidenceResult, setVersionEvidenceResult] = useState<AutomationFlowVerificationEvidenceListResponse | null>(null);
  const [isVersionEvidenceLoading, setIsVersionEvidenceLoading] = useState(false);
  const [versionEvidenceLoadingId, setVersionEvidenceLoadingId] = useState("");
  const [versionForm, setVersionForm] = useState<AutomationFlowVersionFormState>({
    version: "",
    changeSummary: "",
    approvalPolicy: "",
    failureStrategy: "",
    publishNotes: "",
    promptSummary: "",
    promptTemplatePreview: "",
    inputSchemaJson: "[]",
    outputSchemaJson: "[]",
    toolParametersJson: "{}",
    allowedTools: [],
    allowedErpResources: [],
    selectedStepIds: [],
    publishEnvironment: "production",
  });

  useEffect(() => {
    if (!open) {
      setVersions([]);
      setVersionActionKey("");
      setEditingVersionId("");
      setVersionPreflightResult(null);
      setVersionEvidenceResult(null);
      setIsVersionEvidenceLoading(false);
      setVersionEvidenceLoadingId("");
      return;
    }

    if (!flow || !token) {
      return;
    }

    resetVersionForm(flow);
    setVersionPreflightResult(null);
    setVersionEvidenceResult(null);
    setVersionEvidenceLoadingId("");
    void refreshVersions();
  }, [open, flow?.id, token]);

  function resetVersionForm(nextFlow = flow) {
    setVersionForm({
      version: "",
      changeSummary: "",
      approvalPolicy: nextFlow?.approval_policy || "",
      failureStrategy: nextFlow?.failure_strategy || "",
      publishNotes: "",
      promptSummary: nextFlow?.prompt_summary || "",
      promptTemplatePreview: nextFlow?.prompt_template_preview || "",
      inputSchemaJson: schemaDraftJson(nextFlow?.input_schema),
      outputSchemaJson: schemaDraftJson(nextFlow?.output_schema),
      toolParametersJson: toolParametersDraftJson(nextFlow?.model_config),
      allowedTools: nextFlow?.allowed_tools || [],
      allowedErpResources: nextFlow?.allowed_erp_resources || [],
      selectedStepIds: nextFlow?.steps.map((item) => item.id) || [],
      publishEnvironment: "production",
    });
    setEditingVersionId("");
  }

  async function refreshVersions() {
    if (!flow || !token) {
      setVersions([]);
      return;
    }

    setIsVersionListLoading(true);
    try {
      const result = await listAutomationFlowVersions(token, flow.id);
      setVersions(result.items);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "流程版本列表加载失败";
      message.error(text);
    } finally {
      setIsVersionListLoading(false);
    }
  }

  function buildCreatePayload(): AutomationFlowVersionCreatePayload | null {
    const changeSummary = versionForm.changeSummary.trim();
    const approvalPolicy = versionForm.approvalPolicy.trim();
    const failureStrategy = versionForm.failureStrategy.trim();

    if (!changeSummary) {
      message.warning("请填写变更摘要");
      return null;
    }
    if (!approvalPolicy) {
      message.warning("请填写审批策略");
      return null;
    }
    if (!failureStrategy) {
      message.warning("请填写失败策略");
      return null;
    }

    return {
      version: versionForm.version.trim() || undefined,
      change_summary: changeSummary,
      approval_policy: approvalPolicy,
      failure_strategy: failureStrategy,
      publish_notes: versionForm.publishNotes.trim() || undefined,
    };
  }

  function parseSchemaJson(textValue: string, label: string): Array<Record<string, unknown>> | null {
    const text = textValue.trim();
    if (!text) {
      message.warning(`请填写${label} JSON`);
      return null;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "格式不正确";
      message.warning(`${label} JSON 解析失败：${detail}`);
      return null;
    }

    if (!Array.isArray(parsed)) {
      message.warning(`${label} 必须是数组`);
      return null;
    }
    if (!parsed.length) {
      message.warning(`${label} 至少保留一项`);
      return null;
    }
    if (!parsed.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      message.warning(`${label} 数组项必须是对象`);
      return null;
    }

    return parsed as Array<Record<string, unknown>>;
  }

  function parseToolParametersJson(): Record<string, Record<string, unknown>> | null {
    const text = versionForm.toolParametersJson.trim();
    if (!text) {
      message.warning("请填写工具参数 JSON");
      return null;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "格式不正确";
      message.warning(`工具参数 JSON 解析失败：${detail}`);
      return null;
    }

    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      message.warning("工具参数必须是对象");
      return null;
    }
    if (!Object.values(parsed).every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      message.warning("工具参数每个工具的值都必须是对象");
      return null;
    }

    return parsed as Record<string, Record<string, unknown>>;
  }

  function buildUpdatePayload(): AutomationFlowVersionUpdatePayload | null {
    const changeSummary = versionForm.changeSummary.trim();
    const approvalPolicy = versionForm.approvalPolicy.trim();
    const failureStrategy = versionForm.failureStrategy.trim();
    const promptSummary = versionForm.promptSummary.trim();
    const promptTemplatePreview = versionForm.promptTemplatePreview.trim();
    const allowedTools = Array.from(new Set(versionForm.allowedTools.map((item) => item.trim()).filter(Boolean)));
    const projectionResourcesByKey = new Map(flow?.allowed_erp_resources.map((item) => [item.resource, item]) || []);
    const allowedErpResources = Array.from(new Set(versionForm.allowedErpResources.map((item) => item.resource)))
      .map((resource) => projectionResourcesByKey.get(resource))
      .filter((item): item is ErpResourceItem => Boolean(item));
    const projectionStepsById = new Map(flow?.steps.map((item) => [item.id, item]) || []);
    const steps = Array.from(new Set(versionForm.selectedStepIds))
      .map((stepId) => projectionStepsById.get(stepId))
      .filter((item): item is AutomationFlowStepItem => Boolean(item));

    if (!editingVersionId) {
      message.warning("请先载入一个草稿版本");
      return null;
    }
    if (!changeSummary) {
      message.warning("请填写变更摘要");
      return null;
    }
    if (!approvalPolicy) {
      message.warning("请填写审批策略");
      return null;
    }
    if (!failureStrategy) {
      message.warning("请填写失败策略");
      return null;
    }
    if (!promptSummary) {
      message.warning("请填写 Prompt 摘要");
      return null;
    }
    if (!promptTemplatePreview) {
      message.warning("请填写 Prompt 模板预览");
      return null;
    }
    const inputSchema = parseSchemaJson(versionForm.inputSchemaJson, "输入 Schema");
    if (!inputSchema) {
      return null;
    }
    const outputSchema = parseSchemaJson(versionForm.outputSchemaJson, "输出 Schema");
    if (!outputSchema) {
      return null;
    }
    const toolParameters = parseToolParametersJson();
    if (!toolParameters) {
      return null;
    }
    if (!allowedTools.length) {
      message.warning("允许工具至少保留一项");
      return null;
    }
    if (!steps.length) {
      message.warning("执行步骤至少保留一项");
      return null;
    }

    return {
      change_summary: changeSummary,
      approval_policy: approvalPolicy,
      failure_strategy: failureStrategy,
      publish_notes: versionForm.publishNotes.trim() || undefined,
      prompt_summary: promptSummary,
      prompt_template_preview: promptTemplatePreview,
      input_schema: inputSchema,
      output_schema: outputSchema,
      tool_parameters: toolParameters,
      allowed_tools: allowedTools,
      allowed_erp_resources: allowedErpResources,
      steps,
    };
  }

  function moveSelectedStep(stepId: string, direction: -1 | 1) {
    setVersionForm((current) => {
      const nextStepIds = [...current.selectedStepIds];
      const index = nextStepIds.indexOf(stepId);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= nextStepIds.length) {
        return current;
      }
      [nextStepIds[index], nextStepIds[nextIndex]] = [nextStepIds[nextIndex], nextStepIds[index]];
      return {
        ...current,
        selectedStepIds: nextStepIds,
      };
    });
  }

  async function runVersionAction(actionKey: string, successText: string, action: () => Promise<void>) {
    if (!token) {
      message.warning("请先登录管理员账号");
      return;
    }

    setVersionActionKey(actionKey);
    try {
      await action();
      await refreshVersions();
      message.success(successText);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "流程版本操作失败";
      message.error(text);
    } finally {
      setVersionActionKey("");
    }
  }

  async function createDraftVersion() {
    if (!flow) {
      return;
    }
    const payload = buildCreatePayload();
    if (!payload) {
      return;
    }

    await runVersionAction("create", "草稿版本已创建", async () => {
      await createAutomationFlowVersion(token, flow.id, payload);
      resetVersionForm(flow);
    });
  }

  async function saveDraftVersion() {
    const payload = buildUpdatePayload();
    if (!payload) {
      return;
    }

    await runVersionAction(`${editingVersionId}:save`, "草稿治理字段已保存", async () => {
      await updateAutomationFlowVersion(token, editingVersionId, payload);
      resetVersionForm(flow);
    });
  }

  async function loadDraftVersion(record: AutomationFlowVersionSummary) {
    if (record.status !== "draft") {
      message.info("只有草稿版本可以载入编辑");
      return;
    }

    setVersionActionKey(`${record.id}:load`);
    try {
      const detailResult = await getAutomationFlowVersion(token, record.id);
      const version = detailResult.item;
      setEditingVersionId(version.id);
      setVersionForm((current) => ({
        ...current,
        version: version.version,
        changeSummary: version.change_summary || "",
        approvalPolicy: version.approval_policy,
        failureStrategy: version.failure_strategy,
        publishNotes: version.publish_notes || "",
        promptSummary: version.prompt_summary || "",
        promptTemplatePreview: version.prompt_template_preview || "",
        inputSchemaJson: schemaDraftJson(version.input_schema),
        outputSchemaJson: schemaDraftJson(version.output_schema),
        toolParametersJson: toolParametersDraftJson(version.model_config),
        allowedTools: version.allowed_tools || [],
        allowedErpResources: version.allowed_erp_resources || [],
        selectedStepIds: (version.steps || [])
          .map((item) => String(item.id || "").trim())
          .filter(Boolean),
      }));
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "草稿版本详情加载失败";
      message.error(text);
    } finally {
      setVersionActionKey("");
    }
  }

  function submitVersionReview(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:submit`, "版本已提交审核", async () => {
      await submitAutomationFlowVersionReview(token, record.id);
    });
  }

  function approveVersion(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:approve`, "版本已批准", async () => {
      await approveAutomationFlowVersion(token, record.id);
    });
  }

  function preflightVersion(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:preflight`, "发布前预检已完成", async () => {
      const result = await preflightAutomationFlowVersion(token, record.id);
      setVersionPreflightResult(result);
      if (!result.ok) {
        message.warning(`预检未通过：${result.blocking_failures} 项阻断`);
      }
    });
  }

  async function loadVersionEvidence(record: AutomationFlowVersionSummary) {
    if (!token) {
      message.warning("请先登录管理员账号");
      return;
    }

    setIsVersionEvidenceLoading(true);
    setVersionEvidenceLoadingId(record.id);
    try {
      const result = await listAutomationFlowVersionEvidence(token, record.id);
      setVersionEvidenceResult(result);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "发布证据加载失败";
      message.error(text);
    } finally {
      setIsVersionEvidenceLoading(false);
      setVersionEvidenceLoadingId("");
    }
  }

  function publishVersion(record: AutomationFlowVersionSummary) {
    void runVersionAction(`${record.id}:publish`, "版本已发布", async () => {
      await publishAutomationFlowVersion(token, record.id, {
        environment: versionForm.publishEnvironment,
        reason: versionForm.publishNotes.trim() || `发布流程版本 ${record.version}`,
      });
    });
  }

  function rollbackPublication(record: AutomationFlowVersionSummary) {
    if (!record.active_publication_id) {
      return;
    }

    void runVersionAction(`${record.id}:rollback`, "发布版本已回滚", async () => {
      await rollbackAutomationFlowPublication(token, record.active_publication_id || "", {
        reason: versionForm.publishNotes.trim() || `回滚流程版本 ${record.version}`,
      });
    });
  }

  return (
    <Modal
      open={open}
      title={flow ? `流程配置 / ${flow.name}` : "流程配置"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width={980}
    >
      {loading ? (
        <Empty description="正在加载流程配置详情" />
      ) : flow ? (
        <Tabs
          className="flowConfigDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <div className="flowConfigDetailGrid">
                  <FlowConfigDetailItem label="流程 ID" value={flow.id} mono />
                  <FlowConfigDetailItem label="应用 ID" value={flow.app_id} mono />
                  <FlowConfigDetailItem label="岗位" value={flow.position_label} />
                  <FlowConfigDetailItem label="类别" value={flow.category} />
                  <FlowConfigDetailItem label="入口" value={flow.entrypoint} mono />
                  <FlowConfigDetailItem label="触发方式" value={flow.trigger_type} mono />
                  <FlowConfigDetailItem label="版本" value={flow.version} mono />
                  <FlowConfigDetailItem label="负责人" value={flow.owner} />
                </div>
              ),
            },
            {
              key: "schema",
              label: "Schema",
              children: (
                <Row gutter={[12, 12]} className="flowConfigDetailTabGrid">
                  <Col xs={24} md={12}>
                    <Card title="输入 Schema" size="small" className="flowConfigDetailSectionCard">
                      <SchemaTable items={flow.input_schema} />
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="输出 Schema" size="small" className="flowConfigDetailSectionCard">
                      <SchemaTable items={flow.output_schema} />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "prompt",
              label: "Prompt",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <Row gutter={[12, 12]} className="flowConfigDetailTabGrid">
                    <Col xs={24} md={12}>
                      <Card title="Prompt 摘要" size="small" className="flowConfigDetailSectionCard">
                        <Paragraph className="flowConfigDetailPreview">{flow.prompt_summary || "-"}</Paragraph>
                      </Card>
                    </Col>
                    <Col xs={24} md={12}>
                      <Card title="模板预览" size="small" className="flowConfigDetailSectionCard">
                        <pre className="flowConfigPre">{flow.prompt_template_preview || "无独立 Prompt。"}</pre>
                      </Card>
                    </Col>
                  </Row>
                  <Space size={[6, 6]} wrap>
                    {Object.entries(flow.model_config).map(([key, value]) => (
                      <Tag key={key} color={key === "secrets_visible" ? "green" : "blue"}>
                        {key}: {textFromUnknown(value)}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              ),
            },
            {
              key: "permissions",
              label: "权限",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <Row gutter={[12, 12]} className="flowConfigDetailTabGrid">
                    <Col xs={24} md={8}>
                      <Card title="允许工具" size="small" className="flowConfigDetailSectionCard">
                        <Space size={[6, 6]} wrap className="flowConfigTagBlock">
                          {flow.allowed_tools.map((item) => (
                            <Tag color="blue" key={item}>{item}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="审批策略" size="small" className="flowConfigDetailSectionCard">
                        <Paragraph className="flowConfigDetailPreview compact">{flow.approval_policy}</Paragraph>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card title="失败策略" size="small" className="flowConfigDetailSectionCard">
                        <Paragraph className="flowConfigDetailPreview compact">{flow.failure_strategy}</Paragraph>
                      </Card>
                    </Col>
                  </Row>
                  <Card title="允许资源" size="small" className="flowConfigDetailSectionCard">
                    <div className="flowConfigResourceList">
                      {flow.allowed_erp_resources.length ? (
                        flow.allowed_erp_resources.map((resource) => (
                          <Tag color="geekblue" key={resource.resource}>
                            {resource.label} / {resource.resource}
                          </Tag>
                        ))
                      ) : (
                        <Text type="secondary">该流程不直接访问 ERP 资源</Text>
                      )}
                    </div>
                  </Card>
                  <Card title="权限规则" size="small" className="flowConfigDetailSectionCard">
                    <div className="flowConfigRuleList">
                      {flow.permission_rules.map((item) => (
                        <div className="flowConfigRuleItem" key={item}>{item}</div>
                      ))}
                    </div>
                  </Card>
                </Space>
              ),
            },
            {
              key: "governance",
              label: "版本治理",
              children: (
                <Space direction="vertical" size={12} className="pageStack flowGovernancePanel">
                  <Card
                    title={editingVersionId ? "编辑草稿治理字段" : "创建草稿版本"}
                    size="small"
                    className="flowConfigDetailSectionCard"
                    extra={
                      <Button size="small" onClick={() => resetVersionForm(flow)}>
                        清空
                      </Button>
                    }
                  >
                    <div className="flowGovernanceDraftGrid">
                      <div className="flowGovernanceField">
                        <Text type="secondary">版本号</Text>
                        <Input
                          aria-label="版本号"
                          value={versionForm.version}
                          disabled={Boolean(editingVersionId)}
                          placeholder="留空自动递增"
                          onChange={(event) => setVersionForm((current) => ({ ...current, version: event.target.value }))}
                        />
                      </div>
                      <div className="flowGovernanceField">
                        <Text type="secondary">发布环境</Text>
                        <Select
                          value={versionForm.publishEnvironment}
                          options={[
                            { label: "生产", value: "production" },
                            { label: "预发", value: "staging" },
                            { label: "开发", value: "dev" },
                          ]}
                          onChange={(value) => setVersionForm((current) => ({
                            ...current,
                            publishEnvironment: value as AutomationFlowVersionFormState["publishEnvironment"],
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">变更摘要</Text>
                        <Input.TextArea
                          aria-label="变更摘要"
                          rows={2}
                          value={versionForm.changeSummary}
                          placeholder="说明这次流程配置变更"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            changeSummary: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField">
                        <Text type="secondary">审批策略</Text>
                        <Input.TextArea
                          aria-label="审批策略"
                          rows={3}
                          value={versionForm.approvalPolicy}
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            approvalPolicy: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField">
                        <Text type="secondary">失败策略</Text>
                        <Input.TextArea
                          aria-label="失败策略"
                          rows={3}
                          value={versionForm.failureStrategy}
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            failureStrategy: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">发布说明</Text>
                        <Input.TextArea
                          aria-label="发布说明"
                          rows={2}
                          value={versionForm.publishNotes}
                          placeholder="用于发布或回滚原因"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            publishNotes: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">Prompt 摘要</Text>
                        <Input.TextArea
                          aria-label="Prompt 摘要"
                          rows={3}
                          value={versionForm.promptSummary}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑该流程的 Prompt 摘要"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            promptSummary: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">Prompt 模板预览</Text>
                        <Input.TextArea
                          aria-label="Prompt 模板预览"
                          rows={6}
                          value={versionForm.promptTemplatePreview}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑该流程的 Prompt 模板"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            promptTemplatePreview: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">输入 Schema JSON</Text>
                        <Input.TextArea
                          aria-label="输入 Schema JSON"
                          rows={8}
                          value={versionForm.inputSchemaJson}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑输入 Schema"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            inputSchemaJson: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">输出 Schema JSON</Text>
                        <Input.TextArea
                          aria-label="输出 Schema JSON"
                          rows={8}
                          value={versionForm.outputSchemaJson}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑输出 Schema"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            outputSchemaJson: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">工具参数 JSON</Text>
                        <Input.TextArea
                          aria-label="工具参数 JSON"
                          rows={8}
                          value={versionForm.toolParametersJson}
                          disabled={!editingVersionId}
                          placeholder="载入草稿后，可编辑白名单工具参数"
                          className="flowGovernancePromptInput"
                          onChange={(event) => setVersionForm((current) => ({
                            ...current,
                            toolParametersJson: event.target.value,
                          }))}
                        />
                      </div>
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <Text type="secondary">允许工具</Text>
                        <Checkbox.Group
                          className="flowGovernanceToolGroup"
                          value={versionForm.allowedTools}
                          disabled={!editingVersionId}
                          onChange={(values) => setVersionForm((current) => ({
                            ...current,
                            allowedTools: values.map((item) => String(item)),
                          }))}
                        >
                          <Space size={[8, 6]} wrap>
                            {flow.allowed_tools.map((item) => (
                              <Checkbox key={item} value={item}>{item}</Checkbox>
                            ))}
                          </Space>
                        </Checkbox.Group>
                      </div>
                      {flow.allowed_erp_resources.length ? (
                        <div className="flowGovernanceField flowGovernanceWideField">
                          <Text type="secondary">允许 ERP 资源</Text>
                          <Checkbox.Group
                            className="flowGovernanceToolGroup"
                            value={versionForm.allowedErpResources.map((item) => item.resource)}
                            disabled={!editingVersionId}
                            onChange={(values) => setVersionForm((current) => {
                              const selected = new Set(values.map((item) => String(item)));
                              return {
                                ...current,
                                allowedErpResources: flow.allowed_erp_resources.filter((item) => selected.has(item.resource)),
                              };
                            })}
                          >
                            <Space size={[8, 6]} wrap>
                              {flow.allowed_erp_resources.map((item) => (
                                <Checkbox key={item.resource} value={item.resource}>
                                  {item.label} / {item.resource}
                                </Checkbox>
                              ))}
                            </Space>
                          </Checkbox.Group>
                        </div>
                      ) : null}
                      <div className="flowGovernanceField flowGovernanceWideField">
                        <div className="flowGovernanceFieldHeader">
                          <Text type="secondary">执行步骤编排</Text>
                          <Tooltip title="当前只允许选择代码投影内步骤并调整安全顺序，不能编辑步骤对象内容或新增任意步骤">
                            <Tag color="cyan">投影步骤</Tag>
                          </Tooltip>
                        </div>
                        <Checkbox.Group
                          className="flowGovernanceToolGroup"
                          value={versionForm.selectedStepIds}
                          disabled={!editingVersionId}
                          onChange={(values) => setVersionForm((current) => ({
                            ...current,
                            selectedStepIds: [
                              ...current.selectedStepIds.filter((stepId) => values.includes(stepId)),
                              ...values.map((item) => String(item)).filter((stepId) => !current.selectedStepIds.includes(stepId)),
                            ],
                          }))}
                        >
                          <Space size={[8, 6]} wrap>
                            {flow.steps.map((item) => (
                              <Checkbox key={item.id} value={item.id}>
                                {item.name} / {item.id}
                              </Checkbox>
                            ))}
                          </Space>
                        </Checkbox.Group>
                        <div className="flowGovernanceStepOrderList">
                          {versionForm.selectedStepIds.length ? (
                            versionForm.selectedStepIds.map((stepId, index) => {
                              const step = flow.steps.find((item) => item.id === stepId);
                              return (
                                <div className="flowGovernanceStepOrderItem" key={stepId}>
                                  <div className="flowGovernanceStepOrderText">
                                    <Text strong>{index + 1}. {step?.name || stepId}</Text>
                                    <Text type="secondary" className="flowConfigMono">{stepId}</Text>
                                  </div>
                                  <Space size={4} className="flowGovernanceStepOrderActions">
                                    <Tooltip title="上移步骤">
                                      <Button
                                        aria-label={`上移步骤 ${stepId}`}
                                        icon={<UpOutlined />}
                                        size="small"
                                        disabled={!editingVersionId || index === 0}
                                        onClick={() => moveSelectedStep(stepId, -1)}
                                      />
                                    </Tooltip>
                                    <Tooltip title="下移步骤">
                                      <Button
                                        aria-label={`下移步骤 ${stepId}`}
                                        icon={<DownOutlined />}
                                        size="small"
                                        disabled={!editingVersionId || index === versionForm.selectedStepIds.length - 1}
                                        onClick={() => moveSelectedStep(stepId, 1)}
                                      />
                                    </Tooltip>
                                  </Space>
                                </div>
                              );
                            })
                          ) : (
                            <Text type="secondary">至少保留一个投影内步骤</Text>
                          )}
                        </div>
                      </div>
                      <div className="flowGovernanceActions flowGovernanceWideField">
                        <Space size={8} wrap>
                          <Button
                            icon={<SaveOutlined />}
                            disabled={!editingVersionId}
                            loading={versionActionKey === `${editingVersionId}:save`}
                            onClick={saveDraftVersion}
                          >
                            保存草稿
                          </Button>
                          <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            loading={versionActionKey === "create"}
                            onClick={createDraftVersion}
                          >
                            创建草稿
                          </Button>
                        </Space>
                      </div>
                    </div>
                  </Card>

                  <Card
                    title="版本列表"
                    size="small"
                    className="flowConfigDetailSectionCard"
                    extra={
                      <Button size="small" icon={<ReloadOutlined />} loading={isVersionListLoading} onClick={refreshVersions}>
                        刷新
                      </Button>
                    }
                  >
                    <Table<AutomationFlowVersionSummary>
                      rowKey="id"
                      size="small"
                      dataSource={versions}
                      loading={isVersionListLoading}
                      className="flowGovernanceTable"
                      scroll={{ x: 1080 }}
                      locale={{ emptyText: <Empty description="暂无流程版本" /> }}
                      columns={[
                        {
                          title: "版本",
                          dataIndex: "version",
                          width: 150,
                          render: (_, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Text strong className="flowConfigMono">{record.version}</Text>
                              <Text type="secondary" className="flowConfigMono">No.{record.version_number}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "状态",
                          dataIndex: "status",
                          width: 112,
                          render: (value) => <StatusTag value={String(value)} />,
                        },
                        {
                          title: "编辑",
                          dataIndex: "id",
                          width: 112,
                          render: (_, record) => {
                            const canEdit = record.status === "draft";
                            return (
	                              <Button
	                                size="small"
                                  aria-label="载入"
	                                disabled={!canEdit}
	                                loading={versionActionKey === `${record.id}:load`}
	                                onClick={() => void loadDraftVersion(record)}
	                              >
                                载入
                              </Button>
                            );
                          },
                        },
                        {
                          title: "证据",
                          dataIndex: "id",
                          width: 112,
                          render: (_, record) => (
	                            <Button
	                              size="small"
                                aria-label="证据"
	                              icon={<FileTextOutlined />}
	                              loading={isVersionEvidenceLoading && versionEvidenceLoadingId === record.id}
	                              onClick={() => loadVersionEvidence(record)}
	                            >
                              证据
                            </Button>
                          ),
                        },
                        {
                          title: "变更摘要",
                          dataIndex: "change_summary",
                          width: 260,
                          render: (value, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Text className="flowConfigPreview">{value || "-"}</Text>
                              {record.publish_notes ? (
                                <Text type="secondary" className="flowConfigPreview">{record.publish_notes}</Text>
                              ) : null}
                            </Space>
                          ),
                        },
                        {
                          title: "审批",
                          dataIndex: "approved_by_username",
                          width: 170,
                          render: (_, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Text className="flowConfigText">{record.approved_by_username || "-"}</Text>
                              <Text type="secondary" className="flowConfigMono">{formatTime(record.approved_at || "")}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "发布",
                          dataIndex: "published_by_username",
                          width: 190,
                          render: (_, record) => (
                            <Space direction="vertical" size={2} className="flowConfigCellStack">
                              <Space size={4} wrap>
                                <Text className="flowConfigText">{record.published_by_username || "-"}</Text>
                                {record.active_publication_environment ? (
                                  <Tag color="green">{record.active_publication_environment}</Tag>
                                ) : null}
                              </Space>
                              <Text type="secondary" className="flowConfigMono">{formatTime(record.published_at || "")}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: "操作",
                          dataIndex: "id",
                          fixed: "right",
                          width: 310,
                          render: (_, record) => {
                            const canEdit = record.status === "draft";
                            const canSubmit = record.status === "draft" || record.status === "rejected";
                            const canApprove = record.status === "reviewing";
                            const canPublish = record.status === "approved" || record.status === "published";
                            const canRollback = Boolean(record.active_publication_id);

                            return (
                              <Space size={6} wrap className="flowGovernanceActionCell">
	                                <Button
	                                  size="small"
                                    aria-label="载入"
	                                  disabled={!canEdit}
	                                  loading={versionActionKey === `${record.id}:load`}
	                                  onClick={() => void loadDraftVersion(record)}
	                                >
                                  载入
                                </Button>
	                                <Button
	                                  size="small"
                                    aria-label="提交审核"
	                                  disabled={!canSubmit}
	                                  loading={versionActionKey === `${record.id}:submit`}
	                                  onClick={() => submitVersionReview(record)}
	                                >
                                  提交审核
                                </Button>
		                                <Button
		                                  size="small"
                                      aria-label="批准"
		                                  icon={<CheckCircleOutlined />}
		                                  disabled={!canApprove}
		                                  loading={versionActionKey === `${record.id}:approve`}
	                                  onClick={() => approveVersion(record)}
	                                >
	                                  批准
	                                </Button>
	                                <Button
	                                  size="small"
                                    aria-label="预检"
	                                  icon={<SafetyCertificateOutlined />}
	                                  loading={versionActionKey === `${record.id}:preflight`}
	                                  onClick={() => preflightVersion(record)}
                                >
                                  预检
                                </Button>
	                                <Popconfirm
	                                  title="发布流程版本"
	                                  okText="发布"
                                  cancelText="取消"
                                  disabled={!canPublish}
                                  onConfirm={() => publishVersion(record)}
                                >
	                                  <Button
	                                    size="small"
                                      aria-label="发布"
	                                    type={canPublish ? "primary" : "default"}
	                                    icon={<CloudUploadOutlined />}
	                                    disabled={!canPublish}
                                    loading={versionActionKey === `${record.id}:publish`}
                                  >
                                    发布
                                  </Button>
                                </Popconfirm>
                                <Popconfirm
                                  title="回滚发布版本"
                                  okText="回滚"
                                  cancelText="取消"
                                  disabled={!canRollback}
                                  onConfirm={() => rollbackPublication(record)}
                                >
	                                  <Button
	                                    size="small"
                                      aria-label="回滚"
	                                    danger
	                                    icon={<HistoryOutlined />}
	                                    disabled={!canRollback}
                                    loading={versionActionKey === `${record.id}:rollback`}
                                  >
                                    回滚
                                  </Button>
                                </Popconfirm>
                              </Space>
                            );
                          },
                        },
	                      ]}
	                    />
	                  </Card>
                  {versionEvidenceResult ? (
                    <Card
                      title="发布证据"
                      size="small"
                      className="flowConfigDetailSectionCard flowEvidenceCard"
                      extra={
                        <Space size={6} wrap>
                          <Tag color="blue">{versionEvidenceResult.version}</Tag>
                          <Tag color="purple">{versionEvidenceResult.total} 条</Tag>
                        </Space>
                      }
                    >
                      <div className="flowEvidenceSummary">
                        <Text className="flowConfigMono">
                          {versionEvidenceResult.flow_key}
                        </Text>
                        <Text type="secondary" className="flowConfigMono">
                          快照：{versionEvidenceResult.snapshot_hash.slice(0, 12)}
                        </Text>
                      </div>
                      <Table<AutomationFlowVerificationEvidence>
                        rowKey="id"
                        size="small"
                        dataSource={versionEvidenceResult.items}
                        loading={isVersionEvidenceLoading}
                        pagination={false}
                        className="flowEvidenceTable"
                        scroll={{ x: 980 }}
                        locale={{ emptyText: <Empty description="暂无发布证据" /> }}
                        columns={[
                          {
                            title: "报告",
                            dataIndex: "report_id",
                            width: 220,
                            render: (value, record) => (
                              <Space direction="vertical" size={2} className="flowConfigCellStack">
                                <Text strong className="flowConfigMono">{String(value)}</Text>
                                <Text type="secondary" className="flowConfigPreview">{record.summary || "-"}</Text>
                              </Space>
                            ),
                          },
                          {
                            title: "状态",
                            dataIndex: "status",
                            width: 150,
                            render: (_, record) => (
                              <Space size={4} wrap>
                                <Tag color={record.status === "passed" ? "green" : "red"}>
                                  {record.status === "passed" ? "通过" : "失败"}
                                </Tag>
                                {record.is_publish_eligible ? (
                                  <Tag color="cyan">可发布</Tag>
                                ) : null}
                                {!record.matches_current_snapshot ? (
                                  <Tag color="gold">旧快照</Tag>
                                ) : null}
                              </Space>
                            ),
                          },
                          {
                            title: "脚本",
                            dataIndex: "script",
                            width: 260,
                            render: (_, record) => (
                              <Space direction="vertical" size={2} className="flowConfigCellStack">
                                <Text className="flowConfigMono">{record.script}</Text>
                                <Text type="secondary" className="flowConfigMono">{record.command}</Text>
                              </Space>
                            ),
                          },
                          {
                            title: "范围",
                            dataIndex: "evidence_scope",
                            width: 130,
                            render: (_, record) => (
                              <Space size={4} wrap>
                                <Tag color={record.is_current_version ? "blue" : "geekblue"}>
                                  {record.is_current_version ? "当前版本" : "同快照复用"}
                                </Tag>
                                <Tag color={record.profile === "release" ? "purple" : "cyan"}>{record.profile}</Tag>
                              </Space>
                            ),
                          },
                          {
                            title: "时间",
                            dataIndex: "verified_at",
                            width: 190,
                            render: (_, record) => (
                              <Space direction="vertical" size={2} className="flowConfigCellStack">
                                <Text className="flowConfigMono">{formatTime(record.verified_at)}</Text>
                                <Text type="secondary" className="flowConfigMono">有效至 {formatTime(record.expires_at)}</Text>
                              </Space>
                            ),
                          },
                        ]}
                      />
                    </Card>
                  ) : null}
                  {versionPreflightResult ? (
                    <Card
                      title="发布前预检"
                      size="small"
                      className="flowConfigDetailSectionCard flowPreflightCard"
                      extra={
                        <Tag color={versionPreflightResult.ok ? "green" : "red"}>
                          {versionPreflightResult.ok ? "预检通过" : `${versionPreflightResult.blocking_failures} 项阻断`}
                        </Tag>
                      }
                    >
                      <div className="flowPreflightSummary">
                        <Text className="flowConfigMono">
                          {versionPreflightResult.flow_key} / {versionPreflightResult.version}
                        </Text>
                        <Text type="secondary" className="flowConfigMono">
                          记录：{versionPreflightResult.preflight_run_id || "-"} / {formatTime(versionPreflightResult.created_at || "")}
                        </Text>
                      </div>
                      <div className="flowPreflightCheckGrid">
                        {versionPreflightResult.checks.map((item) => (
                          <div className="flowPreflightCheckItem" key={item.key}>
                            <Space size={6} wrap>
                              <Tag color={item.status === "passed" ? "green" : "red"}>
                                {item.status === "passed" ? "通过" : "失败"}
                              </Tag>
                              <Text strong>{item.label}</Text>
                            </Space>
                            <Paragraph className="flowPreflightMessage">{item.message}</Paragraph>
                            {item.artifacts.length ? (
                              <div className="flowPreflightArtifactList">
                                <Text strong>发布验证</Text>
                                {item.artifacts.map((artifact) => (
                                  <div className="flowPreflightArtifactItem" key={`${artifact.script}:${artifact.command}`}>
                                    <Space size={6} wrap>
	                                      <Tag color={artifact.profile === "release" ? "blue" : "cyan"}>
	                                        {artifact.profile}
	                                      </Tag>
                                        {artifact.publish_evidence_required ? (
                                          <Tag color="volcano">关键证据</Tag>
                                        ) : null}
	                                      <Text className="flowPreflightArtifactLabel">{artifact.label}</Text>
	                                    </Space>
                                    <Text className="flowPreflightArtifactCommand">{artifact.command}</Text>
                                    {artifact.latest_evidence ? (
                                      <Text className="flowPreflightArtifactEvidence">
                                        证据：{artifact.latest_evidence.report_id} / {formatTime(artifact.latest_evidence.verified_at)} / 有效至 {formatTime(artifact.latest_evidence.expires_at)}
                                      </Text>
                                    ) : (
                                      <Text type="secondary" className="flowPreflightArtifactEvidence">
                                        证据：发布前需补最近通过记录
                                      </Text>
                                    )}
                                  </div>
                                ))}
                              </div>
                            ) : null}
                            {item.repair_hints.length ? (
                              <div className="flowPreflightRepairList">
                                <Text strong>修复建议</Text>
                                {item.repair_hints.map((hint) => (
                                  <div className="flowPreflightRepairItem" key={`${hint.code}:${hint.field_path}:${hint.message}`}>
                                    <Space size={6} wrap>
                                      <Tag color={hint.severity === "blocking" ? "red" : "gold"}>
                                        {hint.severity === "blocking" ? "阻断" : hint.severity}
                                      </Tag>
                                      <Text className="flowPreflightRepairPath">{hint.field_path}</Text>
                                    </Space>
                                    <Paragraph className="flowPreflightRepairSuggestion">
                                      {hint.suggestion}
                                    </Paragraph>
                                  </div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </Card>
                  ) : null}
	                </Space>
	              ),
	            },
            {
              key: "steps",
              label: `步骤 ${flow.steps.length}`,
              children: (
                <Table
                  rowKey="id"
                  dataSource={flow.steps}
                  pagination={false}
                  scroll={{ x: 680 }}
                  locale={{ emptyText: <Empty description="暂无步骤" /> }}
                  columns={[
                    {
                      title: "步骤 ID",
                      dataIndex: "id",
                      width: 190,
                      render: (value) => <Text className="flowConfigMono">{String(value)}</Text>,
                    },
                    {
                      title: "步骤名称",
                      dataIndex: "name",
                      width: 240,
                      render: (value) => <Text className="flowConfigText">{String(value)}</Text>,
                    },
                    {
                      title: "输入",
                      dataIndex: "inputs",
                      render: (value: string[]) => (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => <Tag key={item}>{item}</Tag>)}
                        </Space>
                      ),
                    },
                    {
                      title: "可重试",
                      dataIndex: "retryable",
                      width: 90,
                      render: (value) => <Tag color={value ? "green" : "gold"}>{value ? "是" : "否"}</Tag>,
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一个流程配置" />
      )}
    </Modal>
  );
}

function FlowConfigDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flowConfigDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "flowConfigMono" : "flowConfigText"}>{value}</Text>
    </div>
  );
}

function SchemaTable({ items }: { items: Array<Record<string, unknown>> }) {
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

function ConnectorsPanel({
  connectors,
  summary,
  loading,
  refreshConnectors,
  openDetail,
}: {
  connectors: ConnectorItem[];
  summary: ConnectorsResponse["summary"] | null;
  loading: boolean;
  refreshConnectors: () => void;
  openDetail: (connectorId: string) => void;
}) {
  const categories = Array.from(new Set(connectors.map((item) => item.category))).filter(Boolean);

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="connectorMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">连接器</Text>
            <Title level={3}>{summary?.total ?? connectors.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">已配置</Text>
            <Title level={3}>{summary?.configured ?? connectors.filter((item) => item.configured).length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">健康</Text>
            <Title level={3}>{summary?.healthy ?? connectors.filter((item) => item.status === "healthy").length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">待配置</Text>
            <Title level={3}>{summary?.needs_config ?? connectors.filter((item) => item.status === "not_configured").length}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title="系统连接器"
        subTitle="集中查看外部系统连接、真实健康状态、配置掩码、资源映射和岗位权限范围"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshConnectors} loading={loading}>
            刷新
          </Button>
        }
      >
        <Space direction="vertical" size={16} className="pageStack">
          {categories.map((category) => (
            <div key={category} className="connectorCategoryBlock">
              <Space size={8} className="connectorCategoryTitle">
                <Tag color="blue">{category}</Tag>
                <Text type="secondary">
                  {connectors.filter((item) => item.category === category).length} 个连接器
                </Text>
              </Space>
              <Row gutter={[12, 12]}>
                {connectors
                  .filter((item) => item.category === category)
                  .map((connector) => (
                    <Col xs={24} lg={12} xl={8} key={connector.id} className="connectorCardCol">
                      <Card size="small" className="contextCard connectorCard">
                        <div className="connectorCardBody">
                          <div className="connectorHeader">
                            <Space size={8} className="connectorTitleWrap">
                              <ApiOutlined />
                              <Tooltip title={connector.description} placement="topLeft">
                                <Text strong className="connectorTitle tooltipTitle">{connector.label}</Text>
                              </Tooltip>
                            </Space>
                            <ConnectorStatusTag status={connector.status} />
                          </div>
                          <div className="connectorMetaGrid">
                            <div>
                              <Text type="secondary">鉴权</Text>
                              <Text strong>{connector.auth_type}</Text>
                            </div>
                            <div>
                              <Text type="secondary">管理范围</Text>
                              <Text strong>{connector.managed_by}</Text>
                            </div>
                            <div>
                              <Text type="secondary">资源</Text>
                              <Text strong>{connector.resources.length} 项</Text>
                            </div>
                            <div>
                              <Text type="secondary">真实健康检查</Text>
                              <Text strong>{connector.supports_real_health_check ? "已接入" : "未接入"}</Text>
                            </div>
                          </div>
                          <Space size={[6, 6]} wrap className="connectorTagList">
                            {connector.position_scope_labels.map((item) => (
                              <Tag key={`${connector.id}-${item}`} color="purple">{item}</Tag>
                            ))}
                          </Space>
                          <Paragraph className="connectorHealthMessage">
                            {connector.health_message}
                          </Paragraph>
                          <div className="connectorFooter">
                            <Button size="small" type="primary" onClick={() => openDetail(connector.id)}>
                              详情
                            </Button>
                          </div>
                        </div>
                      </Card>
                    </Col>
                  ))}
              </Row>
            </div>
          ))}
        </Space>
      </ProCard>
    </Space>
  );
}

function PlatformActionExecutorsPanel({
  executors,
  summary,
  actionOptions,
  typeOptions,
  form,
  setForm,
  loading,
  saving,
  checkingId,
  deletingId,
  refresh,
  save,
  edit,
  reset,
  checkHealth,
  remove,
}: {
  executors: PlatformActionExecutorItem[];
  summary: PlatformActionExecutorsResponse["summary"] | null;
  actionOptions: PlatformActionExecutorOption[];
  typeOptions: PlatformActionExecutorOption[];
  form: PlatformActionExecutorFormState;
  setForm: React.Dispatch<React.SetStateAction<PlatformActionExecutorFormState>>;
  loading: boolean;
  saving: boolean;
  checkingId: string;
  deletingId: string;
  refresh: () => void;
  save: () => void;
  edit: (item: PlatformActionExecutorItem) => void;
  reset: () => void;
  checkHealth: (item: PlatformActionExecutorItem) => void;
  remove: (item: PlatformActionExecutorItem) => void;
}) {
  return (
    <Space direction="vertical" size={16} className="pageStack">
      <Row gutter={[12, 12]} className="platformExecutorMetricRow">
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">执行器</Text>
            <Title level={3}>{summary?.total ?? executors.length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">启用</Text>
            <Title level={3}>{summary?.enabled ?? executors.filter((item) => item.enabled).length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">已配置</Text>
            <Title level={3}>{summary?.configured ?? executors.filter((item) => item.configured).length}</Title>
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card size="small" className="connectorMetricCard">
            <Text type="secondary">健康</Text>
            <Title level={3}>{summary?.healthy ?? executors.filter((item) => item.health_status === "healthy").length}</Title>
          </Card>
        </Col>
      </Row>

      <ProCard
        title={form.id ? "编辑外部执行器" : "新增外部执行器"}
        subTitle="按平台动作路由到 Amazon SP-API、影刀、n8n、客服系统或通用 Webhook"
        bordered
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
            刷新
          </Button>
        }
      >
        <div className="platformExecutorFormGrid">
          <div className="platformExecutorField">
            <Text type="secondary">名称</Text>
            <Input
              value={form.name}
              placeholder="例如：Amazon Listing 发布执行器"
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </div>
          <div className="platformExecutorField">
            <Text type="secondary">类型</Text>
            <Select
              value={form.executorType}
              options={typeOptions.length ? typeOptions : [{ value: "webhook", label: "通用 Webhook" }]}
              onChange={(value) => setForm((current) => ({ ...current, executorType: value }))}
            />
          </div>
          <div className="platformExecutorField platformExecutorWideField">
            <Text type="secondary">动作路由</Text>
            <Select
              mode="multiple"
              value={form.actionTypes}
              placeholder="选择该执行器负责的动作"
              options={actionOptions}
              maxTagCount="responsive"
              onChange={(value) => setForm((current) => ({ ...current, actionTypes: value }))}
            />
          </div>
          <div className="platformExecutorField platformExecutorWideField">
            <Text type="secondary">Webhook URL</Text>
	            <Input
	              value={form.webhookUrl}
	              placeholder={form.id ? "留空表示不修改" : "https://example.com/platform-action/execute"}
	              onChange={(event) => setForm((current) => ({ ...current, webhookUrl: event.target.value }))}
	            />
          </div>
          <div className="platformExecutorField">
            <Text type="secondary">API Key</Text>
            <Input.Password
              value={form.apiKey}
              placeholder={form.id ? "留空表示不修改" : "可选"}
              onChange={(event) => setForm((current) => ({ ...current, apiKey: event.target.value }))}
            />
          </div>
          <div className="platformExecutorField">
            <Text type="secondary">超时秒数</Text>
            <InputNumber
              min={1}
              max={120}
              value={form.timeoutSeconds}
              onChange={(value) => setForm((current) => ({ ...current, timeoutSeconds: Number(value || 12) }))}
            />
          </div>
          <div className="platformExecutorSwitchRow">
            <Switch
              checked={form.enabled}
              onChange={(checked) => setForm((current) => ({ ...current, enabled: checked }))}
            />
            <Text>{form.enabled ? "启用执行器" : "暂停执行器"}</Text>
          </div>
          <div className="platformExecutorButtonRow">
            <Button onClick={reset}>清空</Button>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={save} loading={saving}>
              {form.id ? "保存修改" : "创建执行器"}
            </Button>
          </div>
        </div>
      </ProCard>

      <ProCard title="动作执行器路由" bordered>
        <Table<PlatformActionExecutorItem>
          rowKey="id"
          loading={loading}
          dataSource={executors}
          className="platformExecutorTable"
          scroll={{ x: 1180 }}
          locale={{ emptyText: <Empty description="暂无外部执行器配置" /> }}
          columns={[
            {
              title: "执行器",
              dataIndex: "name",
              width: 240,
              render: (_, record) => (
                <Space direction="vertical" size={2} className="runRecordCellStack">
                  <Space size={6}>
                    <Text strong className="runRecordText">{record.name}</Text>
                    {record.is_environment_fallback ? <Tag>环境变量</Tag> : null}
                  </Space>
                  <Text type="secondary" className="runRecordMono">{record.id}</Text>
                </Space>
              ),
            },
            {
              title: "类型",
              dataIndex: "executor_type_label",
              width: 150,
              render: (_, record) => <Tag color="blue">{record.executor_type_label || platformActionExecutorTypeLabel(record.executor_type)}</Tag>,
            },
            {
              title: "动作",
              dataIndex: "action_type_labels",
              width: 260,
              render: (value: string[]) => (
                <Space size={[4, 4]} wrap>
                  {(value || []).map((item) => <Tag key={item} color="purple">{item}</Tag>)}
                </Space>
              ),
            },
            {
              title: "Webhook",
              dataIndex: "webhook_url_preview",
              width: 240,
              render: (value) => <Text className="runRecordMono">{value || "-"}</Text>,
            },
            {
              title: "状态",
              dataIndex: "health_status",
              width: 118,
              render: (_, record) => (
                <Space direction="vertical" size={2}>
                  <ConnectorStatusTag status={record.enabled ? record.health_status : "disabled"} />
                  <Text type="secondary">{record.enabled ? "启用" : "已暂停"}</Text>
                </Space>
              ),
            },
            {
              title: "密钥",
              dataIndex: "api_key_configured",
              width: 96,
              render: (value) => <Tag color={value ? "green" : "default"}>{value ? "已配置" : "未配置"}</Tag>,
            },
            {
              title: "最近检查",
              dataIndex: "last_checked_at",
              width: 150,
              render: (value) => formatTime(String(value || "")),
            },
            {
              title: "操作",
              dataIndex: "id",
              fixed: "right",
              width: 220,
              render: (_, record) => (
                <Space size={6} wrap className="platformExecutorActionCell">
                  <Button size="small" onClick={() => checkHealth(record)} loading={checkingId === record.id}>
                    检查
                  </Button>
                  <Button size="small" type="link" disabled={record.is_environment_fallback} onClick={() => edit(record)}>
                    编辑
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={record.is_environment_fallback}
                    loading={deletingId === record.id}
                    onClick={() => remove(record)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
          expandable={{
            expandedRowRender: (record) => (
              <div className="platformExecutorExpanded">
                <Text type="secondary">健康信息</Text>
                <Paragraph>{record.health_message || "尚未执行健康检查。"}</Paragraph>
              </div>
            ),
          }}
        />
      </ProCard>
    </Space>
  );
}

function ConnectorDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: ConnectorDetailResponse | null;
  onClose: () => void;
}) {
  const connector = detail?.item || null;

  return (
    <Modal
      open={open}
      title={connector ? `连接器 / ${connector.label}` : "连接器"}
      onCancel={onClose}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
      ]}
      width="min(980px, calc(100vw - 32px))"
    >
      {loading ? (
        <Empty description="正在加载连接器详情" />
      ) : connector ? (
        <Tabs
          className="connectorDetailTabs"
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <div className="connectorDetailGrid">
                  <ConnectorDetailItem label="连接器 ID" value={connector.id} mono />
                  <ConnectorDetailItem label="类别" value={connector.category} />
                  <ConnectorDetailItem label="状态" value={<ConnectorStatusTag status={connector.status} />} />
                  <ConnectorDetailItem label="健康状态" value={connector.health_status} mono />
                  <ConnectorDetailItem label="鉴权方式" value={connector.auth_type} />
                  <ConnectorDetailItem label="管理范围" value={connector.managed_by} />
                  <ConnectorDetailItem label="真实健康检查" value={connector.supports_real_health_check ? "已接入" : "未接入"} />
                  <ConnectorDetailItem label="最后检查" value={formatTime(connector.last_checked_at)} mono />
                </div>
              ),
            },
            {
              key: "health",
              label: "健康",
              children: (
                <Card title="健康信息" size="small" className="connectorDetailSectionCard">
                  <Paragraph className="connectorDetailPreview">{connector.health_message}</Paragraph>
                  <Space size={[6, 6]} wrap className="connectorTagBlock">
                    {connector.capabilities.map((item) => (
                      <Tag color="blue" key={item}>{item}</Tag>
                    ))}
                    {connector.position_scope_labels.map((item) => (
                      <Tag color="purple" key={item}>{item}</Tag>
                    ))}
                  </Space>
                </Card>
              ),
            },
            {
              key: "config",
              label: "配置",
              children: (
                <Row gutter={[12, 12]} className="connectorDetailTabGrid">
                  <Col xs={24} md={12}>
                    <Card title="配置项" size="small" className="connectorDetailSectionCard">
                      <ConnectorConfigTable fields={connector.config_fields} />
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="下一步" size="small" className="connectorDetailSectionCard">
                      <div className="connectorRuleList">
                        {connector.next_steps.map((item) => (
                          <div className="connectorRuleItem" key={item}>{item}</div>
                        ))}
                      </div>
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "resources",
              label: "资源映射",
              children: (
                <Table
                  rowKey={(record) => `${record.resource}-${record.provider_resource}`}
                  dataSource={connector.resources}
                  pagination={false}
                  scroll={{ x: 820 }}
                  locale={{ emptyText: <Empty description="暂无资源映射" /> }}
                  columns={[
                    {
                      title: "资源",
                      dataIndex: "label",
                      width: 170,
                      render: (value, record) => (
                        <Space direction="vertical" size={2} className="connectorCellStack">
                          <Text strong className="connectorText">{String(value)}</Text>
                          <Text className="connectorMono">{record.resource}</Text>
                        </Space>
                      ),
                    },
                    {
                      title: "外部对象",
                      dataIndex: "provider_resource",
                      width: 190,
                      render: (value) => <Text className="connectorMono">{value || "-"}</Text>,
                    },
                    {
                      title: "岗位范围",
                      dataIndex: "position_scope_labels",
                      width: 190,
                      render: (value: string[]) => (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => <Tag color="purple" key={item}>{item}</Tag>)}
                        </Space>
                      ),
                    },
                    {
                      title: "字段",
                      dataIndex: "fields",
                      render: (value: string[]) => value.length ? (
                        <Space size={[4, 4]} wrap>
                          {value.map((item) => <Tag key={item}>{item}</Tag>)}
                        </Space>
                      ) : (
                        <Text type="secondary">-</Text>
                      ),
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      ) : (
        <Empty description="请选择一个连接器" />
      )}
    </Modal>
  );
}

function ConnectorConfigTable({ fields }: { fields: ConnectorConfigField[] }) {
  return (
    <Table
      rowKey="name"
      size="small"
      dataSource={fields}
      pagination={false}
      scroll={{ x: 540 }}
      locale={{ emptyText: <Empty description="无需环境变量配置" /> }}
      columns={[
        { title: "配置项", dataIndex: "name", width: 190, render: (value) => <Text className="connectorMono">{String(value)}</Text> },
        {
          title: "状态",
          dataIndex: "configured",
          width: 92,
          render: (value) => <Tag color={value ? "green" : "default"}>{value ? "已配置" : "未配置"}</Tag>,
        },
        {
          title: "值",
          dataIndex: "value_preview",
          width: 130,
          render: (value, record) => (
            <Text className="connectorMono">{value || (record.secret ? "****" : "-")}</Text>
          ),
        },
        { title: "说明", dataIndex: "description", render: (value) => <Text className="connectorText">{String(value)}</Text> },
      ]}
    />
  );
}

function ConnectorDetailItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="connectorDetailItem">
      <Text type="secondary">{label}</Text>
      <Text className={mono ? "connectorMono" : "connectorText"}>{value}</Text>
    </div>
  );
}

function ConnectorStatusTag({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    healthy: "green",
    degraded: "gold",
    unhealthy: "red",
    disabled: "default",
    unknown: "default",
    not_configured: "default",
    not_implemented: "gold",
    configured_pending: "blue",
  };

  return <Tag color={colorMap[status] || "default"}>{labelForConnectorStatus(status)}</Tag>;
}

function ErpRecordDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: ErpRecordDetailResponse | null;
  onClose: () => void;
}) {
  const item = detail?.item || null;
  const rows = item ? Object.entries(item).filter(([, value]) => value !== null && value !== "") : [];
  const rawDetail = detail ? {
    ...detail,
    item: item || null,
  } : null;

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
          items={[
            {
              key: "summary",
              label: "基础信息",
              children: (
                <Space direction="vertical" size={12} className="pageStack">
                  <div className="erpRecordDetailGrid">
                    <ErpRecordDetailItem
                      label="状态"
                      value={<Tag color={detail.ok ? "green" : "gold"}>{detail.ok ? "已找到" : "未找到"}</Tag>}
                    />
                    <ErpRecordDetailItem label="Provider" value={detail.provider_label} />
                    <ErpRecordDetailItem label="资源" value={detail.resource_label} />
                    <ErpRecordDetailItem label="外部对象" value={detail.provider_resource} mono />
                    <ErpRecordDetailItem label="记录 ID" value={detail.record_id} mono />
                    <ErpRecordDetailItem label="资源 Key" value={detail.resource} mono />
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
                  pagination={{ pageSize: 10, hideOnSinglePage: true }}
                  scroll={{ x: 680 }}
                  dataSource={rows.map(([field, value]) => ({
                    field,
                    value: textFromUnknown(value),
                  }))}
                  columns={[
                    {
                      title: "字段",
                      dataIndex: "field",
                      width: 190,
                      render: (value) => <Text className="erpRecordMono">{String(value)}</Text>,
                    },
                    {
                      title: "值",
                      dataIndex: "value",
                      render: (value) => <Text className="erpRecordText">{String(value)}</Text>,
                    },
                  ]}
                />
              ) : (
                <Empty description="暂无详情字段" />
              ),
            },
            {
              key: "raw",
              label: "原始数据",
              children: (
                <Card title="原始返回数据" size="small" className="erpRecordDetailSectionCard">
                  <pre className="erpRecordRawPre">{JSON.stringify(rawDetail, null, 2)}</pre>
                </Card>
              ),
            },
          ]}
        />
      ) : (
        <Empty description="暂无 ERP 记录详情" />
      )}
    </Modal>
  );
}

function ErpRecordDetailItem({
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

function ThreadsPanel({
  threads,
  activeThreadId,
  threadSearch,
  setThreadSearch,
  refreshThreads,
  openThread,
  messages,
  summary,
  stateText,
  loading,
  role,
  retentionDays,
}: {
  threads: ThreadListItem[];
  activeThreadId: string;
  threadSearch: string;
  setThreadSearch: (value: string) => void;
  refreshThreads: () => void;
  openThread: (threadId: string) => void;
  messages: ChatMessage[];
  summary: string;
  stateText: string;
  loading: boolean;
  role: Role;
  retentionDays: number;
}) {
  const activeThread = threads.find((item) => item.id === activeThreadId) || null;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9} className="splitCardCol">
        <ProCard
          title="会话记录"
          bordered
          className="splitCard"
          extra={
            <Button size="small" icon={<ReloadOutlined />} onClick={refreshThreads} loading={loading}>
              刷新
            </Button>
          }
        >
          <Space direction="vertical" size={12} className="pageStack">
            <Input.Search
              value={threadSearch}
              onChange={(event) => setThreadSearch(event.target.value)}
              onSearch={refreshThreads}
              placeholder={role === "admin" ? "搜索标题、账号、岗位或会话 ID" : "搜索我的会话"}
              allowClear
            />
            <Text type="secondary">仅显示近 {retentionDays} 天会话，过期记录会自动清理。</Text>
            <div className="threadHistoryList">
              {threads.length ? (
                threads.map((thread) => (
                  <button
                    key={thread.id}
                    type="button"
                    className={`threadHistoryItem ${thread.id === activeThreadId ? "active" : ""}`}
                    onClick={() => openThread(thread.id)}
                  >
                    <div className="threadHistoryTitleRow">
                      <Text strong className="threadHistoryTitle">
                        {threadDisplayTitle(thread, role)}
                      </Text>
                      <Tag color={thread.status === "closed" ? "default" : "green"}>{thread.status}</Tag>
                    </div>
                    <Text type="secondary" className="threadHistoryPreview">
                      {thread.last_message_preview || shortThreadId(thread.id)}
                    </Text>
                    <div className="threadHistoryMeta">
                      <Text type="secondary">{formatTime(thread.updated_at)}</Text>
                      <Text type="secondary">{thread.message_count} 条</Text>
                    </div>
                  </button>
                ))
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无会话记录" />
              )}
            </div>
          </Space>

        </ProCard>
      </Col>
      <Col xs={24} xl={15} className="splitCardCol">
        <ProCard
          title={activeThread ? threadDisplayTitle(activeThread, role) : "消息记录"}
          bordered
          className="splitCard"
          extra={activeThreadId ? <Tag color="blue">{shortThreadId(activeThreadId)}</Tag> : null}
        >
          <Space direction="vertical" size={14} className="pageStack">
            <MessageList messages={messages} />
            {summary ? (
              <Card size="small" title="会话摘要" className="contextCard">
                <Paragraph>{summary}</Paragraph>
              </Card>
            ) : null}

            {stateText ? (
              <Card size="small" title="业务状态" className="contextCard">
                <pre className="statePre">{stateText}</pre>
              </Card>
            ) : null}
          </Space>
        </ProCard>
      </Col>
    </Row>
  );
}

function MessageList({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="chatEmptyState">
        <Empty description="暂无消息，开始一次 AI 对话" />
      </div>
    );
  }

  return (
    <div className="messageList">
      {messages.map((item) => (
        <div key={item.id} className={`messageRow ${item.role}`}>
          <div className={`messageBubble ${item.role}`}>
            <div className="messageHeader">
              <Space size={8}>
                <Tag color={roleColor(item.role)}>{roleLabelForMessage(item.role)}</Tag>
                {item.route ? <Tag color={routeColor(item.route)}>{labelForRoute(item.route)}</Tag> : null}
              </Space>
              <Text type="secondary">{item.createdAt}</Text>
            </div>
            <Paragraph className="messageContent">{item.content || "正在生成..."}</Paragraph>
            {item.erpReferences?.length ? (
              <Space size={[6, 6]} wrap className="erpReferenceList">
                {item.erpReferences.map((reference) => (
                  <Tag color="geekblue" key={`${reference.resource}-${reference.record_id}`}>
                    引用：{reference.resource_label} / {reference.record_id}
                  </Tag>
                ))}
              </Space>
            ) : null}
            {item.attachments?.length ? (
              <Space direction="vertical" size={8} className="messageAttachmentList">
                {item.attachments.map((attachment) => (
                  <div className="messageAttachmentItem" key={`${attachment.filename}-${attachment.size_bytes || 0}`}>
                    <Space size={8}>
                      <TableOutlined />
                      <Text strong>{attachment.filename}</Text>
                      {attachment.size_bytes ? <Text type="secondary">{formatBytes(attachment.size_bytes)}</Text> : null}
                    </Space>
                    <Button
                      size="small"
                      type="primary"
                      disabled={!attachment.content_base64}
                      onClick={() => downloadBase64Attachment(attachment)}
                    >
                      下载 Excel
                    </Button>
                  </div>
                ))}
              </Space>
            ) : null}
            {item.platformDraft ? (
              <div className="messagePlatformDraft">
                <PlatformDraftSummary draft={item.platformDraft} />
              </div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusTag({ value }: { value: string }) {
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

function PlatformDraftStatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    pending_review: "gold",
    approved: "green",
    published: "blue",
    rejected: "red",
  };

  return <Tag color={colorMap[value] || "default"}>{platformDraftStatusLabel(value)}</Tag>;
}

function RiskTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    unprocessed: "default",
    low: "green",
    medium: "gold",
    high: "red",
  };

  return <Tag color={colorMap[value] || "default"}>{riskLabel(value)}</Tag>;
}

function CustomerStatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    new: "blue",
    processing: "processing",
    drafted: "gold",
    auto_reply_ready: "green",
    human_handoff: "red",
    closed: "default",
    failed: "volcano",
  };

  return <Tag color={colorMap[value] || "default"}>{customerStatusLabel(value)}</Tag>;
}

function EllipsisText({ value }: { value: unknown }) {
  const text = String(value ?? "-");

  return (
    <Tooltip title={text}>
      <Text className="tableEllipsisText">{text}</Text>
    </Tooltip>
  );
}

function AuditActionText({ record }: { record: AuditLog }) {
  return (
    <Tooltip title={`原始动作：${record.action}`}>
      <Text className="tableEllipsisText" strong>
        {record.actionLabel}
      </Text>
    </Tooltip>
  );
}

function AuditResourceTypeText({ record }: { record: AuditLog }) {
  return (
    <Tooltip title={`原始类型：${record.resourceType}`}>
      <Text className="tableEllipsisText">{record.resourceTypeLabel}</Text>
    </Tooltip>
  );
}

function auditActionLabel(action: string) {
  const normalized = action.trim();

  if (!normalized) {
    return "-";
  }

  return auditActionLabels[normalized] || fallbackAuditActionLabel(normalized);
}

function auditResourceTypeLabel(resourceType: string) {
  const normalized = resourceType.trim();

  if (!normalized || normalized === "-") {
    return "-";
  }

  return auditResourceTypeLabels[normalized] || fallbackAuditActionLabel(normalized);
}

function auditBackendActionFilter(value: string) {
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

function fallbackAuditActionLabel(value: string) {
  return value
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => auditActionWordLabels[part.toLowerCase()] || part)
    .join(" / ");
}

function defaultAutomationFlowFilters(role: Role, position: Position | null): AutomationFlowFilterState {
  return {
    position: role === "admin" ? "all" : position || "all",
    category: "",
  };
}

function defaultAiWorkflowFilters(role: Role, position: Position | null): AiWorkflowFilterState {
  return {
    position: role === "admin" ? "all" : position || "all",
    category: "",
  };
}

function defaultEffectAnalyticsFilters(role: Role, position: Position | null): EffectAnalyticsFilterState {
  return {
    dateRange: "30d",
    position: role === "admin" ? "all" : position || "all",
  };
}

function filterAiWorkflows(items: AiWorkflowItem[], filters: AiWorkflowFilterState) {
  return items.filter((item) => {
    if (filters.position !== "all" && item.position !== filters.position) {
      return false;
    }

    if (filters.category && item.category !== filters.category) {
      return false;
    }

    return true;
  });
}

function groupAiWorkflows(items: AiWorkflowItem[]) {
  const groups = new Map<string, { key: string; label: string; items: AiWorkflowItem[] }>();

  items.forEach((item) => {
    const key = `${item.position}-${item.category}`;
    const label = `${item.position_label} / ${item.category}`;
    const group = groups.get(key) || { key, label, items: [] };
    group.items.push(item);
    groups.set(key, group);
  });

  return Array.from(groups.values());
}

function workflowEntryView(value: string): View {
  if (value === "customer_service_inbox") {
    return "customer_service_inbox";
  }

  if (value === "automation_customer_service") {
    return "automation_customer_service";
  }

  if (value === "automation_finance") {
    return "automation_finance";
  }

  if (value === "automation_operations") {
    return "automation_operations";
  }

  return "ai_workflows";
}

function workflowEntryViewForWorkflow(workflow: AiWorkflowItem): View {
  if (workflow.id === "finance_excel_settlement") {
    return "automation_finance_excel_transform";
  }

  if (workflow.id === "finance_reconciliation") {
    return "automation_finance_reconciliation";
  }

  if (workflow.execution_mode === "external_existing_endpoint") {
    return workflowEntryView(workflow.entry_view);
  }

  if (workflow.source_task_id) {
    const taskView = automationTaskView(workflow.position, workflow.source_task_id);
    if (taskView) {
      return taskView;
    }
  }

  return workflowIdViewMap[workflow.id] || workflowEntryView(workflow.entry_view);
}

function executionModeLabel(value: string) {
  const labels: Record<string, string> = {
    llm_generate: "LLM 生成",
    erp_then_llm: "ERP + LLM",
    external_existing_endpoint: "专用真实入口",
  };

  return labels[value] ?? value;
}

function workflowAutomationLevelLabel(value: string) {
  const labels: Record<string, string> = {
    draft_auto: "草稿自动化",
    assist_auto: "辅助自动化",
    tool_auto: "工具自动化",
    case_loop_auto: "闭环自动化",
  };

  return labels[value] ?? value;
}

function workflowTriggerLabel(value: string) {
  const labels: Record<string, string> = {
    manual_form: "人工表单触发",
    manual_file_upload: "人工文件上传",
    external_message: "外部消息触发",
  };

  return labels[value] ?? value;
}

function metricStatus(value: string): "success" | "processing" | "error" | "default" | "warning" {
  if (value === "success" || value === "processing" || value === "error" || value === "warning") {
    return value;
  }

  return "default";
}

function overviewPrimaryText(item: Record<string, unknown>) {
  return textFromUnknown(
    item.name
      || item.po_no
      || item.lr_no
      || item.subject
      || item.item_code
      || item.customer
      || item.account
      || item.party
      || "-",
  );
}

function overviewRecordId(item: Record<string, unknown>) {
  const value = item.name || item.po_no || item.lr_no || item.subject || item.item_code;
  return value ? textFromUnknown(value) : "";
}

function overviewSecondaryText(item: Record<string, unknown>) {
  const parts = [
    item.customer || item.customer_name || item.supplier || item.account || item.item_name,
    item.status,
    item.grand_total ? `金额 ${item.grand_total}` : null,
    item.outstanding_amount ? `未收 ${item.outstanding_amount}` : null,
    item.price_list_rate ? `价格 ${item.price_list_rate}` : null,
    item.posting_date || item.transaction_date || item.modified,
  ]
    .filter(Boolean)
    .map(textFromUnknown);

  return parts.length ? parts.join(" / ") : "暂无更多字段";
}

function textFromUnknown(value: unknown) {
  return String(value ?? "").slice(0, 120);
}

function recordFromUnknown(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return {};
}

function stringListFromUnknown(value: unknown) {
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

function formatAmount(value: number) {
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const erpFieldLabels: Record<string, string> = {
  name: "编号",
  id: "编号",
  customer: "客户",
  customer_name: "客户名称",
  supplier: "供应商",
  account: "科目",
  party: "往来方",
  item_code: "SKU",
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

const preferredErpFields = [
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

function buildErpResultColumns(result: ErpQueryResponse | null): TableColumnsType<Record<string, unknown>> {
  if (!result?.items.length) {
    return [];
  }

  const availableFields = new Set<string>();
  result.items.forEach((item) => {
    Object.keys(item).forEach((key) => availableFields.add(key));
  });

  const orderedFields = [
    ...preferredErpFields.filter((field) => availableFields.has(field)),
    ...Array.from(availableFields)
      .filter((field) => !preferredErpFields.includes(field))
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

function renderErpCell(value: unknown, field: string) {
  if (value === null || value === undefined || value === "") {
    return <Text type="secondary">-</Text>;
  }

  if (field === "status" || field === "priority" || field === "payment_type") {
    return <Tag>{textFromUnknown(value)}</Tag>;
  }

  if (typeof value === "number" && isAmountField(field)) {
    return formatAmount(value);
  }

  if (typeof value === "object") {
    return <Text className="erpResultSmallText">{JSON.stringify(value)}</Text>;
  }

  return textFromUnknown(value);
}

function isAmountField(field: string) {
  return [
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

function resultStatusLabel(result: ErpQueryResponse) {
  if (result.ok) {
    return result.items.length ? "查询成功" : "连接正常";
  }

  if (!result.configured) {
    return "未配置";
  }

  return result.status || "查询异常";
}

function dashboardShortcuts(role: Role, position: Position | null): Array<{
  title: string;
  description: string;
  view: View;
  icon: React.ReactNode;
}> {
  if (role === "admin") {
    return [
      {
        title: "用户管理",
        description: "创建员工账号，分配运营、客服、财务岗位。",
        view: "users",
        icon: <SafetyCertificateOutlined />,
      },
      {
        title: "AI 应用中心",
        description: "查看运营、客服、财务 AI 应用目录和岗位权限。",
        view: "automation_flows",
        icon: <AppstoreOutlined />,
      },
      {
        title: "知识库上传",
        description: "上传 RAG 文档，维护企业规则和业务资料。",
        view: "documents",
        icon: <CloudUploadOutlined />,
      },
      {
        title: "审计日志",
        description: "查看越权拦截、ERP 查询和自动化调用记录。",
        view: "audit",
        icon: <AuditOutlined />,
      },
    ];
  }

  if (position === "operations") {
    return [
      {
        title: "运营 AI 自动化",
        description: "生成 Listing、标题、五点描述、关键词和促销文案。",
        view: "automation_operations",
        icon: <RobotOutlined />,
      },
      {
        title: "AI 对话",
        description: "直接询问商品、价格、销售订单等问题，系统会自动查询岗位权限内的数据。",
        view: "chat",
        icon: <MessageOutlined />,
      },
    ];
  }

  if (position === "finance") {
    return [
      {
        title: "财务 Excel 生成",
        description: "上传 Excel，并可选择财务 ERP 表辅助生成新工作簿。",
        view: "automation_finance_excel_transform",
        icon: <CloudUploadOutlined />,
      },
      {
        title: "财务对账自动化",
        description: "合并结算、物流、采购、广告和汇率表，生成订单利润表。",
        view: "automation_finance_reconciliation",
        icon: <AuditOutlined />,
      },
      {
        title: "财务 AI 对话",
        description: "直接询问报表、工资、发票和收付款问题，系统会自动查询岗位权限内的数据。",
        view: "chat",
        icon: <MessageOutlined />,
      },
    ];
  }

  if (position === "customer_service") {
    return [
      {
        title: "客服自动化收件箱",
        description: "客户消息进入后自动识别意图、查 ERP/RAG、生成回复并判断转人工。",
        view: "customer_service_inbox",
        icon: <CommentOutlined />,
      },
      {
        title: "客服 AI 对话",
        description: "处理物流、售后、退款话术和多语言回复。",
        view: "chat",
        icon: <MessageOutlined />,
      },
      {
        title: "退款审批",
        description: "处理用户退款、售后升级和高风险客服消息审批。",
        view: "approvals",
        icon: <CheckCircleOutlined />,
      },
      {
        title: "客服自动化",
        description: "生成智能客服回复、自动回复和退款售后话术。",
        view: "automation_customer_service",
        icon: <RobotOutlined />,
      },
    ];
  }

  return [
    {
      title: "AI 对话",
      description: "联系管理员绑定岗位后，可使用岗位专属能力。",
      view: "chat",
      icon: <MessageOutlined />,
    },
  ];
}

function aiAppsForUser(
  role: Role,
  position: Position | null,
  tasks: AutomationTaskRecord[],
): AiAppRecord[] {
  const allowedPositions = role === "admin"
    ? (["operations", "customer_service", "finance"] as Position[])
    : position ? [position] : [];
  const apps: AiAppRecord[] = [];

  allowedPositions.forEach((item) => {
    const config = positionConfigs[item];
    const taskApps = tasks
      .filter((task) => task.position === item)
      .filter((task) => !(item === "finance" && task.task_id === "excel_transform"))
      .map((task) => ({
        id: `automation-${task.task_id}`,
        name: task.label,
        description: task.output_format || task.instruction,
        category: "岗位自动化",
        position: item,
        positionLabel: config.label,
        status: "enabled" as const,
        dataSources: ["岗位输入", "大模型", ...config.erpScopes.slice(0, 2)],
        owner: config.department,
        entryView: automationTaskView(item, task.task_id) || automationViewForPosition(item),
        entryLabel: "打开自动化",
      }));

    apps.push(...taskApps);

    if (item === "finance") {
      apps.push({
        id: "finance-excel-transform",
        name: "财务 Excel 生成",
        description: "上传真实 Excel 文件，并选择财务权限内 ERP 表生成处理摘要、数值汇总、AI 建议和新工作簿。",
        category: "文件自动化",
        position: item,
        positionLabel: config.label,
        status: "enabled",
        dataSources: ["Excel 文件", "财务 ERP 表", "大模型"],
        owner: config.department,
        entryView: "automation_finance_excel_transform",
        entryLabel: "上传 Excel",
      });
      apps.push({
        id: "finance-reconciliation",
        name: "财务对账自动化",
        description: "上传 Amazon 结算表、物流账单、采购成本表、广告费表和汇率表，自动生成订单利润表和异常账单。",
        category: "财务对账",
        position: item,
        positionLabel: config.label,
        status: "enabled",
        dataSources: ["Amazon 结算表", "物流账单", "采购成本表", "广告费表", "汇率表"],
        owner: config.department,
        entryView: "automation_finance_reconciliation",
        entryLabel: "打开对账中心",
      });
    }

    if (item === "customer_service") {
      if (role !== "admin") {
        apps.push({
          id: "customer-service-refund-approvals",
          name: "退款审批",
          description: "客服岗位处理用户退款、售后升级、投诉、差评和拒付等高风险消息审批，管理员不审批用户退款。",
          category: "客服售后",
          position: item,
          positionLabel: config.label,
          status: "enabled",
          dataSources: ["审批请求", "订单信息", "客服消息", "退款流水"],
          owner: config.department,
          entryView: "approvals",
          entryLabel: "处理审批",
        });
      }
      apps.push({
        id: "customer-service-message-loop",
        name: "客服消息自动化闭环",
        description: "客户消息进入收件箱后，AI 自动识别意图、查订单/物流/知识库、生成对应语种回复，并按风险进入待发送或转人工。",
        category: "客服售后",
        position: item,
        positionLabel: config.label,
        status: "enabled",
        dataSources: ["客户消息", "ERP 客服资源", "RAG 知识库", "运行记录"],
        owner: config.department,
        entryView: "customer_service_inbox",
        entryLabel: "打开收件箱",
      });
    }

    apps.push({
      id: `${item}-erp-query`,
      name: role === "admin" ? `${config.label} ERP 查询` : `${config.label}数据问答助手`,
      description: role === "admin"
        ? `按${config.label}岗位权限查询 ERP 资源，并在 AI 对话和概览中引用真实记录。`
        : `直接用自然语言询问${config.label}相关数据，系统会自动查询岗位权限内的 ERP 记录并整理成可读回答。`,
      category: "数据查询",
      position: item,
      positionLabel: config.label,
      status: "enabled",
      dataSources: config.erpScopes.slice(0, 4),
      owner: config.department,
      entryView: role === "admin" ? "erp_query" : "chat",
      entryLabel: role === "admin" ? "查询 ERP" : "打开对话",
    });

    apps.push({
      id: `${item}-chat-agent`,
      name: `${config.label} AI 对话`,
      description: `在${config.label}岗位权限内进行 RAG、ERP 和业务流程问答，越权问题会被拦截。`,
      category: "AI Agent",
      position: item,
      positionLabel: config.label,
      status: "enabled",
      dataSources: ["RAG 知识库", "ERP 权限资源", "会话上下文"],
      owner: config.department,
      entryView: "chat",
      entryLabel: "打开对话",
    });
  });

  if (role === "admin") {
    apps.push(
      {
        id: "admin-knowledge",
        name: "知识库维护",
        description: "上传企业规则、客服话术、财务制度和运营资料，进入真实 RAG 入库流程。",
        category: "知识治理",
        position: "platform",
        positionLabel: "平台",
        status: "enabled",
        dataSources: ["DOCX", "PDF", "Excel", "Markdown"],
        owner: "管理员",
        entryView: "documents",
        entryLabel: "维护知识库",
      },
      {
        id: "admin-audit",
        name: "审计与权限追踪",
        description: "查看越权拦截、ERP 查询、用户创建、审批处理等真实审计事件。",
        category: "安全治理",
        position: "platform",
        positionLabel: "平台",
        status: "enabled",
        dataSources: ["审计日志", "用户权限", "岗位元数据"],
        owner: "管理员",
        entryView: "audit",
        entryLabel: "查看审计",
      },
    );
  }

  return apps;
}

function filterAiAppsByPermission(
  apps: AiAppRecord[],
  role: Role,
  allowedAiAppIds: string[] | null,
) {
  if (role === "admin" || allowedAiAppIds === null) {
    return apps;
  }

  return apps.filter((app) => allowedAiAppIds.includes(app.id));
}

function automationViewForPosition(position: Position): View {
  if (position === "customer_service") {
    return "automation_customer_service";
  }

  if (position === "finance") {
    return "automation_finance";
  }

  return "automation_operations";
}

function automationTaskView(position: Position, taskId: string): View | null {
  return automationTaskIdViewMap[`${position}:${taskId}`] || null;
}

function readStoredRole(): Role {
  if (!localStorage.getItem("access_token")) {
    return "employee";
  }

  return localStorage.getItem("role") === "admin" ? "admin" : "employee";
}

function readStoredPosition(): Position | null {
  const value = localStorage.getItem("position");
  return isPosition(value) ? value : null;
}

function readStoredAllowedAiAppIds(): string[] | null {
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

function visibleNavigationForUser(
  role: Role,
  position: Position | null,
  allowedAiAppIds: string[] | null,
): NavItem[] {
  return filterNavItemsForUser(navItems, role, position, allowedAiAppIds);
}

function withChatThreadNavigation(
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

function filterNavItemsForUser(
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

function canAccessNavItem(
  item: NavItem,
  role: Role,
  position: Position | null,
  allowedAiAppIds: string[] | null = readStoredAllowedAiAppIds(),
) {
  return item.roles.includes(role)
    && (role === "admin" || !item.positions?.length || item.positions.includes(position as Position))
    && (item.type === "group" || isViewAllowedByAiApp(item.id, role, allowedAiAppIds));
}

function isViewAllowedByAiApp(view: View, role: Role, allowedAiAppIds: string[] | null) {
  if (role === "admin" || allowedAiAppIds === null) {
    return true;
  }

  const appId = aiAppIdForView(view);
  return !appId || allowedAiAppIds.includes(appId);
}

function aiAppIdForView(view: View): string | null {
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

function aiAppIdForWorkflowId(workflowId: string): string {
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

function flattenNavItems(items: NavItem[]): NavItem[] {
  return items.flatMap((item) => [item, ...flattenNavItems(item.children || [])]);
}

function isNavigableNavItem(item: NavItem): item is NavigableNavItem {
  return item.type !== "group";
}

function flattenNavigableNavItems(items: NavItem[]): NavigableNavItem[] {
  return flattenNavItems(items).filter(isNavigableNavItem);
}

function allNavItems(): NavigableNavItem[] {
  return flattenNavigableNavItems(navItems);
}

function viewFromPath(pathname: string): View {
  if (pathname === "/chat/new" || pathname.startsWith("/chat/")) {
    return "chat";
  }

  if (pathname === "/automation/finance/excel-upload") {
    return "automation_finance_excel_transform";
  }

  const matched = allNavItems().find((item) => item.path === pathname);
  return matched?.id || "dashboard";
}

function pathForView(view: View) {
  if (view === "automation") {
    const storedPosition = readStoredPosition();
    if (storedPosition === "customer_service") {
      return "/automation/customer-service-inbox";
    }
    if (storedPosition === "finance") {
      return "/automation/finance";
    }
    return "/automation/operations";
  }

  if (view === "erp") {
    return "/erp/query";
  }

  if (view === "automation_finance_excel_upload") {
    return "/automation/finance/excel-transform";
  }

  return allNavItems().find((item) => item.id === view)?.path || "/dashboard";
}

function threadIdFromPathname(pathname: string) {
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

function navigateToView(view: View, options: { replace?: boolean } = {}) {
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

function resolveNavTargetView(item: NavItem, role: Role, position: Position | null): View {
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

function readRoleFromToken(token: string): Role {
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

function readPositionFromToken(token: string): Position | null {
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

function toBase64(value: string) {
  return value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
}

function titleForView(view: View) {
  const found = allNavItems().find((item) => item.id === view);
  return found?.name ?? "概览";
}

function canRoleAccessView(
  role: Role,
  view: View,
  position: Position | null = readStoredPosition(),
  allowedAiAppIds: string[] | null = readStoredAllowedAiAppIds(),
) {
  const item = allNavItems().find((nav) => nav.id === view);
  return item ? canAccessNavItem(item, role, position, allowedAiAppIds) : false;
}

function hasAdminAccess(role: Role, token?: string) {
  return token ? readRoleFromToken(token) === "admin" : role === "admin";
}

function isAutomationView(view: View) {
  return view === "automation" || view.startsWith("automation_");
}

function isAiWorkflowView(view: View) {
  return view === "ai_workflows" || view.startsWith("ai_workflow_");
}

function workflowIdFromView(view: View) {
  return aiWorkflowViewMap[view] || null;
}

function automationTaskIdFromView(view: View) {
  return automationTaskViewMap[view] || null;
}

function automationFinanceToolFromView(view: View): FinanceAutomationTool | null {
  return automationFinanceToolViewMap[view] || null;
}

function canUseCustomerServiceInbox(role: Role, position: Position | null) {
  return role === "admin" || position === "customer_service";
}

function canUseApprovalCenter(role: Role, position: Position | null) {
  return role === "employee" && position === "customer_service";
}

function canUseBusinessActionLoop(role: Role, position: Position | null) {
  return role === "admin" || position === "operations" || position === "customer_service";
}

function canUsePlatformExecutionTasks(role: Role, position: Position | null) {
  return role === "admin" || position === "operations" || position === "customer_service";
}

function isErpView(view: View) {
  return view === "erp"
    || view === "erp_query"
    || view === "erp_resources"
    || view === "erp_diagnostics";
}

function automationPositionFromView(
  view: View,
  role: Role,
  position: Position | null,
): Position | null {
  if (role !== "admin") {
    return position;
  }

  if (view === "automation_customer_service" || view.startsWith("automation_customer_service_")) {
    return "customer_service";
  }

  if (view === "automation_finance" || view.startsWith("automation_finance_")) {
    return "finance";
  }

  return "operations";
}

function pageSubtitle(role: Role, position: Position | null) {
  if (role === "admin") {
    return "RAG、LangGraph、Agent、用户岗位和后台维护中心";
  }

  return position ? `${positionLabel(position)}岗位 AI 自动化工作台` : "员工工作台";
}

function approvalActionLabel(actionType: string) {
  const labels: Record<string, string> = {
    refund: "退款审批",
    customer_service_refund: "客服退款审批",
    customer_service_complaint: "客服投诉审批",
    customer_service_bad_review: "差评风险审批",
    customer_service_chargeback: "拒付风险审批",
  };

  return labels[actionType] || `${actionType.replace(/_/g, " ")} 审批`;
}

function buildApprovalSummaryFallback(actionType: string, payload: Record<string, unknown>) {
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

function approvalReviewerLabel(actionType: string) {
  return actionType === "refund" || actionType.startsWith("customer_service_") ? "客服" : "管理员";
}

function normalizeApprovalReviewerText(actionType: string, value: string) {
  if (approvalReviewerLabel(actionType) !== "客服") {
    return value;
  }

  return value
    .replace(/需要管理员确认/g, "需要客服确认")
    .replace(/需要管理员审批/g, "需要客服审批")
    .replace(/管理员决定/g, "客服决定");
}

function compactDisplayText(value: string, limit: number) {
  const text = value.replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit)}...` : text;
}

function mapApproval(item: ApprovalItem): Approval {
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
    orderNo,
    amount,
    reason: fallbackReason,
    summary: String(item.summary_cn || payload.summary_cn || buildApprovalSummaryFallback(item.action_type, payload)),
    createdAt: formatDate(item.created_at),
  };
}

function mapRefund(item: RefundItem): Refund {
  return {
    id: item.id,
    approvalId: item.approval_id,
    orderNo: item.order_no,
    amount: formatCents(item.amount_cents),
    status: item.status,
    createdAt: formatDate(item.created_at),
  };
}

function mapAuditLog(item: AuditLogItem): AuditLog {
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

function mapUser(item: UserItem): UserRecord {
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

function mergeAutomationTasks(
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

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadBase64Attachment(attachment: ChatAttachment) {
  if (!attachment.content_base64) {
    return;
  }

  const binary = atob(attachment.content_base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const blob = new Blob([bytes], {
    type: attachment.mime_type || "application/octet-stream",
  });
  downloadBlob(blob, attachment.filename || "attachment.xlsx");
}

function mapThreadMessage(item: ThreadMessageItem): ChatMessage {
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
  };
}

function parseErpReferences(value: unknown): ErpReference[] {
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

function parseChatAttachments(value: unknown): ChatAttachment[] {
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

function parsePlatformDraft(value: unknown): PlatformDraftItem | null {
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

function moneyFromOrderResult(value: unknown) {
  if (typeof value === "object" && value !== null && "amount" in value) {
    return String((value as { amount?: unknown }).amount || "-");
  }

  return "-";
}

function formatCents(value: number) {
  return `${(value / 100).toFixed(2)}元`;
}

function formatDate(value: string) {
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

function formatTime(value: string | null) {
  if (!value) {
    return "-";
  }

  return formatDate(value);
}

function shortThreadId(threadId: string) {
  if (!threadId) {
    return "";
  }

  return threadId.length > 18 ? `${threadId.slice(0, 14)}...` : threadId;
}

function threadDisplayTitle(thread: ThreadListItem, role: Role) {
  const baseTitle = (thread.title || thread.last_message_preview || shortThreadId(thread.id) || "未命名会话").trim();
  const cleanTitle = baseTitle.length > 28 ? `${baseTitle.slice(0, 28)}...` : baseTitle;

  if (role !== "admin") {
    return cleanTitle;
  }

  const owner = thread.display_name || thread.username || "未知用户";
  const positionText = thread.position ? positionLabel(thread.position) : roleLabel((thread.role || "employee") as Role);
  return `${cleanTitle} / ${positionText} / ${owner}`;
}

function formatDuration(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  if (value < 1000) {
    return `${value}ms`;
  }

  return `${(value / 1000).toFixed(1)}s`;
}

function formatPercent(value: unknown) {
  if (typeof value !== "number") {
    return "0%";
  }

  return `${Math.round(value * 1000) / 10}%`;
}

function formatNumber(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  return value.toFixed(3);
}

function metricValue(metrics: unknown, key: string) {
  if (!metrics || typeof metrics !== "object") {
    return null;
  }

  const value = (metrics as Record<string, unknown>)[key];
  return typeof value === "number" ? value : null;
}

function formatBytes(value: unknown) {
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

function isExcelFile(file: GeneratedFileItem) {
  const mime = (file.mime_type || "").toLowerCase();
  const name = file.name.toLowerCase();
  return mime.includes("spreadsheet") || name.endsWith(".xlsx") || name.endsWith(".xls");
}

function isWordFile(file: GeneratedFileItem) {
  const mime = (file.mime_type || "").toLowerCase();
  const name = file.name.toLowerCase();
  return mime.includes("wordprocessingml") || name.endsWith(".docx");
}

function fileTypeLabel(file: GeneratedFileItem) {
  if (isExcelFile(file)) {
    return "Excel";
  }

  if (isWordFile(file)) {
    return "Word";
  }

  return file.artifact_type || "文件";
}

function generatedFileBusinessSummary(file: GeneratedFileItem): {
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

function countLabel(value: unknown, unit: string) {
  if (typeof value !== "number") {
    return "-";
  }

  return `${value.toLocaleString("zh-CN")}${unit}`;
}

function moneyLabel(value: unknown) {
  if (typeof value !== "number") {
    return "-";
  }

  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function runStatusLabel(value: string) {
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

function routeFromIntent(intent: string | null, riskLevel: string | null): ChatRoute | undefined {
  if (intent === "refund" || riskLevel === "high") {
    return "refund_workflow";
  }

  if (intent === "order") {
    return "order_agent";
  }

  if (intent === "policy" || intent === "agent") {
    return "knowledge_rag";
  }

  if (intent === "finance_salary_export") {
    return "finance_salary_export";
  }

  return undefined;
}

function labelForRoute(route: ChatRoute) {
  const labels: Record<ChatRoute, string> = {
    refund_workflow: "高风险退款审批",
    order_agent: "订单工具查询",
    knowledge_rag: "知识库问答",
    finance_salary_export: "工资表自动导出",
  };

  return labels[route];
}

function routeColor(route: ChatRoute) {
  const colors: Record<ChatRoute, string> = {
    refund_workflow: "gold",
    order_agent: "blue",
    knowledge_rag: "green",
    finance_salary_export: "purple",
  };

  return colors[route];
}

function roleLabel(role: Role) {
  return role === "admin" ? "管理员" : "员工";
}

function positionLabel(position: Position) {
  return positionConfigs[position].label;
}

function isPosition(value: unknown): value is Position {
  return value === "operations" || value === "customer_service" || value === "finance";
}

function roleLabelForMessage(role: ChatMessage["role"]) {
  const labels: Record<ChatMessage["role"], string> = {
    user: "用户",
    assistant: "助手",
    system: "系统",
    tool: "工具",
  };

  return labels[role];
}

function roleColor(role: ChatMessage["role"]) {
  const colors: Record<ChatMessage["role"], string> = {
    user: "blue",
    assistant: "green",
    system: "gold",
    tool: "purple",
  };

  return colors[role];
}

function labelForBadge(value: string) {
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

function riskLabel(value: string) {
  const labels: Record<string, string> = {
    unprocessed: "未处理",
    low: "低风险",
    medium: "中风险",
    high: "高风险",
  };

  return labels[value] ?? value;
}

function customerStatusLabel(value: string) {
  const labels: Record<string, string> = {
    new: "新消息",
    processing: "处理中",
    drafted: "草稿待确认",
    auto_reply_ready: "待发送",
    human_handoff: "转人工",
    closed: "已关闭",
    failed: "失败",
  };

  return labels[value] ?? value;
}

function customerIntentLabel(value: string) {
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

function platformDraftTypeLabel(value: string) {
  const labels: Record<string, string> = {
    listing: "Listing 草稿",
    customer_reply: "客服回复草稿",
  };

  return labels[value] ?? value;
}

function platformDraftStatusLabel(value: string) {
  const labels: Record<string, string> = {
    pending_review: "待人工审核",
    approved: "已审核",
    published: "已发布",
    rejected: "已驳回",
  };

  return labels[value] ?? value;
}

function PlatformExecutionTaskStatusTag({ value }: { value: string }) {
  return (
    <Tag color={platformExecutionTaskStatusColor(value)}>
      {platformExecutionTaskStatusLabel(value)}
    </Tag>
  );
}

function platformExecutionTaskStatusLabel(value: string) {
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

function platformExecutionTaskStatusColor(value: string) {
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

function platformTaskBusinessTarget(task: PlatformExecutionTaskItem, content: Record<string, unknown>) {
  if (task.action_type === "write_listing_draft" || task.action_type === "publish_listing") {
    return textFromUnknown(content.sku || task.draft?.external_target || task.target || "待确认 SKU");
  }

  if (task.action_type === "write_customer_reply" || task.action_type === "send_customer_reply") {
    return textFromUnknown(content.order_no || content.customer_message_id || task.draft?.external_target || task.target || "待确认客户消息");
  }

  return textFromUnknown(task.draft?.external_target || task.target || "-");
}

function platformTaskBusinessResult(
  task: PlatformExecutionTaskItem,
  responsePayload: Record<string, unknown>,
) {
  const message = textFromUnknown(responsePayload.message || responsePayload.detail || responsePayload.status_message || "");
  if (message) {
    return message;
  }

  if (task.action_type === "publish_listing") {
    return task.external_reference
      ? `Listing 已提交到外部平台，外部引用：${task.external_reference}`
      : "Listing 已提交到外部平台。";
  }

  if (task.action_type === "send_customer_reply") {
    return task.external_reference
      ? `客服回复已发送，外部引用：${task.external_reference}`
      : "客服回复已发送。";
  }

  return task.external_reference
    ? `外部执行器已处理完成，外部引用：${task.external_reference}`
    : "外部执行器已处理完成。";
}

function platformTaskNextAction(task: PlatformExecutionTaskItem, finalPublish: boolean) {
  if (task.status === "queued") {
    if (task.last_error) {
      return "当前任务等待外部执行器接入或重试。请先确认执行器配置，配置完成后可点击重试。";
    }
    return "任务已进入队列，系统会派发给外部执行器。";
  }

  if (task.status === "dispatching") {
    return "系统正在把任务发送给外部执行器，请等待执行结果。";
  }

  if (task.status === "waiting_callback") {
    return "外部执行器已接收任务，当前正在等待平台回调确认完成结果。";
  }

  if (task.status === "cancelled") {
    return "任务已取消。如仍需处理，请回到草稿重新发起。";
  }

  if (finalPublish) {
    return "请关注外部平台是否完成发布或发送。";
  }

  return "请回到草稿审核中心继续审核或发布。";
}

function platformTaskFailureReason(
  task: PlatformExecutionTaskItem,
  responsePayload: Record<string, unknown>,
) {
  if (task.status !== "failed" && !task.last_error) {
    return "";
  }

  const raw = textFromUnknown(
    task.last_error
      || responsePayload.message
      || responsePayload.error
      || responsePayload.detail
      || "外部执行任务失败，请稍后重试或联系管理员。",
  );
  const lower = raw.toLowerCase();

  if (lower.includes("timeout") || lower.includes("timed out")) {
    return "外部系统响应超时，任务没有确认完成。请稍后重试，或让管理员检查外部执行器连接。";
  }

  if (lower.includes("http") || lower.includes("url") || lower.includes("connection")) {
    return "外部执行器连接异常，任务没有成功提交。请让管理员检查执行器地址、网络和鉴权配置。";
  }

  if (lower.includes("executor") || lower.includes("webhook") || lower.includes("not configured")) {
    return "外部执行器还没有配置完成，草稿已保存，但暂时不能自动写回外部平台。";
  }

  return raw;
}

function platformTaskTimelineItems(task: PlatformExecutionTaskItem, finalPublish: boolean) {
  const createdTime = formatTime(task.created_at || "");
  const updatedTime = formatTime(task.updated_at || "");
  const completedTime = formatTime(task.completed_at || "");
  const items: Array<{ key: string; title: string; description: string; time: string; tone: string }> = [
    {
      key: "created",
      title: "任务已创建",
      description: finalPublish ? "草稿已审核通过，系统准备发布或发送。" : "系统已保存草稿，并准备写回外部平台。",
      time: createdTime,
      tone: "done",
    },
  ];

  if (["dispatching", "waiting_callback", "succeeded", "failed"].includes(String(task.status))) {
    items.push({
      key: "dispatching",
      title: "已派发执行器",
      description: "系统已把业务动作发送给外部执行器处理。",
      time: updatedTime,
      tone: task.status === "failed" ? "warning" : "done",
    });
  } else {
    items.push({
      key: "dispatching",
      title: "等待派发",
      description: "任务正在队列中等待外部执行器处理。",
      time: "",
      tone: "pending",
    });
  }

  if (["waiting_callback", "succeeded", "failed"].includes(String(task.status))) {
    items.push({
      key: "callback",
      title: task.status === "waiting_callback" ? "等待外部回调" : "已收到外部结果",
      description: task.status === "waiting_callback"
        ? "外部平台仍在处理，系统会等待回调更新最终状态。"
        : "外部执行器已返回处理结果。",
      time: task.status === "waiting_callback" ? updatedTime : completedTime || updatedTime,
      tone: task.status === "waiting_callback" ? "active" : task.status === "failed" ? "warning" : "done",
    });
  } else {
    items.push({
      key: "callback",
      title: "等待外部结果",
      description: "任务完成后会在这里显示结果和外部引用。",
      time: "",
      tone: "pending",
    });
  }

  items.push({
    key: "finished",
    title: task.status === "succeeded" ? "业务动作完成" : task.status === "failed" ? "业务动作失败" : "等待完成",
    description: task.status === "succeeded"
      ? "员工可以继续后续业务处理。"
      : task.status === "failed"
        ? "请根据失败原因修改配置、草稿或重试任务。"
        : "系统还没有收到最终完成结果。",
    time: task.status === "succeeded" || task.status === "failed" ? completedTime || updatedTime : "",
    tone: task.status === "succeeded" ? "done" : task.status === "failed" ? "danger" : "pending",
  });

  return items;
}

function platformExternalTargetLabel(value: string) {
  const normalized = value.trim();
  const labels: Record<string, string> = {
    amazon_seller_central: "Amazon Seller Central",
    amazon: "Amazon",
    customer_service_system: "客服系统",
    erp: "ERP 系统",
  };

  if (!normalized) {
    return "外部平台";
  }

  if (/^https?:\/\//i.test(normalized)) {
    return "外部执行器 Webhook";
  }

  return labels[normalized] ?? normalized;
}

function NotificationStatusTag({ value }: { value: string }) {
  return <Tag color={value === "unread" ? "blue" : "default"}>{value === "unread" ? "未读" : "已读"}</Tag>;
}

function FeedbackStatusTag({ value }: { value: string }) {
  return <Tag color={value === "completed" ? "green" : "gold"}>{value === "completed" ? "已完成" : "待处理"}</Tag>;
}

function FeedbackPriorityTag({ value }: { value: string }) {
  const colors: Record<string, string> = {
    low: "default",
    normal: "blue",
    high: "orange",
    urgent: "red",
  };

  return <Tag color={colors[value] || "default"}>{feedbackPriorityLabel(value)}</Tag>;
}

function feedbackPriorityLabel(value: string) {
  const labels: Record<string, string> = {
    low: "较低",
    normal: "普通",
    high: "较高",
    urgent: "紧急",
  };

  return labels[value] ?? value;
}

function notificationTypeLabel(value: string) {
  const labels: Record<string, string> = {
    "feedback.submitted": "新反馈",
    "feedback.completed": "反馈完成",
    platform_draft_review: "草稿审核",
    platform_execution_task: "执行任务",
    platform_execution_succeeded: "执行成功",
    platform_execution_failed: "执行失败",
    platform_execution_waiting: "等待回调",
    platform_execution_retry: "任务重试",
  };

  return labels[value] ?? (value || "系统通知");
}

function notificationResourceLabel(value: string | null) {
  const labels: Record<string, string> = {
    feedback: "反馈",
    platform_execution_task: "执行任务",
    platform_draft: "平台草稿",
    run_record: "运行记录",
  };

  return value ? labels[value] ?? value : "-";
}

function platformDraftWritebackLabel(value: string) {
  const labels: Record<string, string> = {
    draft_saved: "已保存草稿",
    rpa_ready: "RPA/连接器就绪",
    external_synced: "已同步外部平台",
    failed: "写回失败",
  };

  return labels[value] ?? value;
}

function platformDraftWritebackColor(value: string) {
  const colors: Record<string, string> = {
    draft_saved: "default",
    rpa_ready: "gold",
    external_synced: "green",
    failed: "red",
  };

  return colors[value] ?? "default";
}

function platformActionTypeLabel(value: string) {
  const labels: Record<string, string> = {
    write_listing_draft: "写入 Listing 草稿",
    write_customer_reply: "写入客服回复草稿",
    publish_listing: "发布 Listing",
    send_customer_reply: "发送客服回复",
  };

  return labels[value] ?? value;
}

function shortDraftId(draftId: string) {
  return draftId.length > 18 ? `${draftId.slice(0, 8)}...${draftId.slice(-6)}` : draftId;
}

function shortTaskId(taskId: string | null) {
  if (!taskId) {
    return "-";
  }

  return taskId.length > 18 ? `${taskId.slice(0, 8)}...${taskId.slice(-6)}` : taskId;
}

function platformTaskDraftTitle(task: PlatformExecutionTaskItem) {
  return task.draft?.title || task.draft_title || textFromUnknown(task.metadata?.draft_title || "") || shortDraftId(task.draft_id);
}

function platformTaskPosition(task: PlatformExecutionTaskItem) {
  return task.draft?.position || task.draft_position || task.position || task.metadata?.position || null;
}

function canRetryPlatformTask(task: PlatformExecutionTaskItem) {
  return task.status === "failed" || task.status === "queued";
}

function isWaitingPlatformTaskStatus(status: string) {
  return status === "queued" || status === "dispatching" || status === "waiting_callback";
}

function businessActionStageColor(value: string) {
  const colors: Record<string, string> = {
    draft_saved: "default",
    needs_review: "gold",
    ready_to_publish: "blue",
    external_running: "processing",
    done: "green",
    failed: "red",
    rejected: "default",
  };

  return colors[value] ?? "default";
}

function businessActionLoopTimelineItems(item: BusinessActionLoopItem) {
  const draftDone = ["pending_review", "approved", "published", "rejected"].includes(item.draft_status);
  const reviewDone = ["approved", "published"].includes(item.draft_status);
  const executionActive = isWaitingPlatformTaskStatus(item.latest_task_status || "");
  const executionDone = item.latest_task_status === "succeeded" || item.draft_status === "published";
  const failed = item.stage === "failed";
  const rejected = item.stage === "rejected";

  return [
    {
      key: "draft",
      label: "草稿",
      description: item.writeback_status_label || platformDraftWritebackLabel(item.writeback_status),
      tone: failed && item.writeback_status === "failed" ? "danger" : draftDone ? "done" : "pending",
    },
    {
      key: "review",
      label: "审核",
      description: item.draft_status_label || platformDraftStatusLabel(item.draft_status),
      tone: rejected ? "danger" : reviewDone ? "done" : item.draft_status === "pending_review" ? "active" : "pending",
    },
    {
      key: "execute",
      label: "执行",
      description: item.latest_task_status_label || (item.latest_task_status ? platformExecutionTaskStatusLabel(item.latest_task_status) : "等待发起外部执行"),
      tone: failed && item.latest_task_status === "failed" ? "danger" : executionDone ? "done" : executionActive ? "active" : "pending",
    },
    {
      key: "finish",
      label: "完成",
      description: item.external_reference ? `外部引用：${item.external_reference}` : "等待外部平台返回最终结果",
      tone: item.stage === "done" ? "done" : failed ? "danger" : "pending",
    },
  ];
}

function upsertPlatformExecutionTask(
  items: PlatformExecutionTaskItem[],
  nextTask: PlatformExecutionTaskItem,
) {
  const exists = items.some((item) => item.id === nextTask.id);
  const merged = exists
    ? items.map((item) => item.id === nextTask.id ? nextTask : item)
    : [nextTask, ...items];

  return merged.sort((a, b) => String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")));
}

function upsertPlatformActionExecutor(
  items: PlatformActionExecutorItem[],
  nextItem: PlatformActionExecutorItem,
) {
  const exists = items.some((item) => item.id === nextItem.id);
  const merged = exists
    ? items.map((item) => item.id === nextItem.id ? nextItem : item)
    : [nextItem, ...items];

  return merged.sort((a, b) => Number(b.enabled) - Number(a.enabled) || String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")));
}

function canReviewPlatformDraft(draft: PlatformDraftItem) {
  return draft.status === "pending_review" || draft.status === "rejected";
}

function canRejectPlatformDraft(draft: PlatformDraftItem) {
  return draft.status === "pending_review" || draft.status === "approved";
}

function platformDraftPublishButtonLabel(draft: PlatformDraftItem) {
  return draft.draft_type === "customer_reply" ? "发送" : "发布";
}

function platformDraftPublishSuccessLabel(draft: PlatformDraftItem) {
  return draft.draft_type === "customer_reply" ? "客服回复已发送" : "Listing 已发布";
}

function platformExecutionStatusLabel(value: string) {
  const labels: Record<string, string> = {
    waiting_executor: "等待外部执行器",
    running: "执行中",
    succeeded: "执行成功",
    failed: "执行失败",
  };

  return labels[value] ?? value;
}

function platformExecutionStatusColor(value: string) {
  const colors: Record<string, string> = {
    waiting_executor: "gold",
    running: "processing",
    succeeded: "green",
    failed: "red",
  };

  return colors[value] ?? "default";
}

function platformExecutorTypeLabel(value: string) {
  const labels: Record<string, string> = {
    webhook: "Webhook 执行器",
    manual_waiting: "等待配置",
  };

  return labels[value] ?? value;
}

function platformActionExecutorTypeLabel(value: string) {
  const labels: Record<string, string> = {
    webhook: "通用 Webhook",
    amazon_sp_api: "Amazon SP-API",
    n8n: "n8n 工作流",
    yingdao: "影刀 RPA",
    customer_service_system: "客服系统",
    erp_writeback: "ERP 写回",
  };

  return labels[value] ?? value;
}

function customerDecisionLabel(value: string) {
  const labels: Record<string, string> = {
    handoff_required: "必须转人工",
    draft_only: "仅生成草稿",
    low_risk_auto_reply_ready: "低风险待发送",
  };

  return labels[value] ?? value;
}

function customerEventLabel(value: string) {
  const labels: Record<string, string> = {
    created: "创建",
    processing_started: "开始处理",
    processed: "处理完成",
    failed: "失败",
  };

  return labels[value] ?? value;
}

function evaluationGateColor(value: string) {
  const colors: Record<string, string> = {
    passed: "green",
    ready: "blue",
    warning: "gold",
    failed: "red",
  };

  return colors[value] || "default";
}

function labelForConnectorStatus(value: string) {
  const labels: Record<string, string> = {
    healthy: "健康",
    degraded: "异常",
    unhealthy: "异常",
    disabled: "已暂停",
    unknown: "未检查",
    not_configured: "未配置",
    not_implemented: "待接入",
    configured_pending: "已配置待联调",
  };

  return labels[value] ?? value;
}

function monitoringStatusLabel(value: string) {
  const labels: Record<string, string> = {
    ok: "正常",
    healthy: "健康",
    success: "正常",
    warning: "需关注",
    failed: "异常",
    degraded: "异常",
    not_configured: "未配置",
    not_implemented: "待接入",
    configured_pending: "待联调",
    http_error: "接口异常",
    connection_error: "连接异常",
    timeout: "超时",
    unknown: "未知",
  };

  return labels[value] ?? value;
}

function monitoringStatusColor(value: string) {
  const colors: Record<string, string> = {
    ok: "green",
    healthy: "green",
    success: "green",
    warning: "gold",
    failed: "red",
    degraded: "gold",
    not_configured: "default",
    not_implemented: "gold",
    configured_pending: "blue",
    http_error: "red",
    connection_error: "red",
    timeout: "red",
  };

  return colors[value] || "default";
}

createRoot(document.getElementById("root")!).render(<App />);
