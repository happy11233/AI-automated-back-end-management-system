import { useSession } from "./hooks/useSession";
import { useWorkspaceLoading } from "./hooks/useWorkspaceLoading";
import { useAccountSettings } from "./hooks/useAccountSettings";
import { useExecutionInsights } from "./hooks/useExecutionInsights";
import { useIntegrationAdmin } from "./hooks/useIntegrationAdmin";
import {
  EMPTY_NOTIFICATION_SUMMARY,
  chatAttachmentTypeFromFilename,
  chatMessageContainsArtifact,
  auditBackendActionFilter,
  defaultAutomationFlowFilters,
  defaultAiWorkflowFilters,
  defaultEffectAnalyticsFilters,
  overviewRecordId,
  visibleNavigationForUser,
  withChatThreadNavigation,
  legacyAgentRoutes,
  viewFromPath,
  pathForView,
  threadIdFromPathname,
  navigateToView,
  resolveNavTargetView,
  readRoleFromToken,
  readPositionFromToken,
  titleForView,
  hasAdminAccess,
  isAiWorkflowView,
  workflowIdFromView,
  canUseBusinessActionLoop,
  canUsePlatformExecutionTasks,
  isErpView,
  workspacePageDescription,
  mapApproval,
  mapRefund,
  mapAuditLog,
  mapUser,
  mergeAutomationTasks,
  mapThreadMessage,
  normalizeBusinessProgress,
  routeFromIntent,
  upsertPlatformExecutionTask,
  platformDraftPublishSuccessLabel,
} from "./workspace/appHelpers";
import {
  PublicLLMChatWidget,
  UserMenu,
  LoginModal,
  LoginErrorModal,
  SessionExpiredModal,
} from "./components/SessionControls";
import { lazy, useEffect, useMemo, useRef, useState } from "react";
import { SafetyCertificateOutlined } from "@ant-design/icons";
import { App as AntApp, Button, ConfigProvider, Space, message, theme } from "antd";
import "./styles.css";
import "./workspace.css";
import { AsyncBoundary } from "./components/AsyncBoundary";
import {
  completeFeedback,
  confirmEnterpriseWechatFileSend,
  confirmEmailFileSend,
  createThread,
  createFeedback,
  createUser,
  deleteUser,
  getBusinessActionLoop,
  getPlatformDraftDetail,
  getPlatformExecutionTask,
  getAiWorkflowDetail,
  getDesktopReleaseDownloadUrl,
  getAutomationFlowDetail,
  analyzeFinanceReport,
  downloadGeneratedFile,
  generateAutomation,
  createCustomerServiceMessage,
  getCustomerServiceMessageDetail,
  isAuthExpiredError,
  exportFinanceSalary,
  listCustomerServiceMessages,
  listDesktopDownloads,
  reconcileFinanceFiles,
  transformFinanceExcel,
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
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  publishPlatformDraft,
  retryPlatformExecutionTask,
  sendPublicLLMChatStream,
  sendChatStream,
  uploadDocument,
  listApprovals,
  listAuditLogs,
  listRefunds,
  listUsers,
  getThreadMessages,
  listAutomationFlows,
  listAiWorkflows,
  listThreads,
  queryErp,
  processCustomerServiceMessage,
  updateUserAiAppPermission,
  updateThreadTitle,
  reviewApproval as reviewApprovalApi,
  retryRefundApproval as retryRefundApprovalApi,
  reviewPlatformDraft,
  type ChatAttachment,
  type AiWorkflowDetailResponse,
  type AiWorkflowItem,
  type AutomationFlowDetailResponse,
  type AutomationFlowItem,
  type BusinessActionLoopResponse,
  type CustomerServiceMessageCreatePayload,
  type CustomerServiceMessageDetailResponse,
  type CustomerServiceMessageItem,
  type CustomerServiceProcessResponse,
  type DocumentUploadAccessPayload,
  type DesktopDownloadItem,
  type DesktopPlatform,
  type GeneratedFileFilters,
  type GeneratedFileItem,
  type EnterpriseWechatFileSendConfirmPayload,
  type EmailFileSendConfirmPayload,
  type FeedbackItem,
  type FeedbackSummary,
  type ErpDashboardOverviewResponse,
  type ErpDiagnosticsResponse,
  type ErpQueryResponse,
  type ErpRecordDetailResponse,
  type ErpResourceItem,
  type ErpStatusResponse,
  type Position,
  type PlatformDraftItem,
  type PlatformDraftDetailResponse,
  type PlatformExecutionTaskItem,
  type NotificationItem,
  type NotificationSummary,
  type ThreadListItem,
  type UserCreatePayload,
} from "./api";
import type { Language } from "./portal/data/content";
import { workflowIdViewMap } from "./workspace/shared";
import type {
  View,
  Role,
  PublicLLMChatMessage,
  ChatMessage,
  Approval,
  Refund,
  AuditLog,
  GeneratedFileFilterState,
  AiWorkflowFilterState,
  PlatformDraftFilterState,
  PlatformExecutionTaskFilterState,
  NotificationFilterState,
  FeedbackFilterState,
  FeedbackFormState,
  AutomationFlowFilterState,
  CustomerServiceInboxFilters,
  CustomerServiceInboxForm,
  UserRecord,
  AutomationTaskRecord,
  DashboardMarket,
  DashboardDateRange,
  DashboardStore,
  NewUserForm,
  DocumentPositionScope,
  DocumentMarketScope,
  DocumentStoreScope,
  DocumentFieldScope,
  DocumentSensitivityLevel,
} from "./workspace/types";
import {
  canUseApprovalCenter,
  flattenNavigableNavItems,
  canUseCustomerServiceInbox,
  canRoleAccessView,
  downloadBlob,
  enterpriseWechatConfirmKey,
  isWaitingPlatformTaskStatus,
  recordFromUnknown,
} from "./workspace/shared";

const PublicPortal = lazy(() => import("./portal/PublicPortal").then((module) => ({ default: module.PublicPortal })));
const Dashboard = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.Dashboard })));
const DesktopDownloadsPanel = lazy(() => import("./pages/DesktopDownloadsPanel").then((module) => ({ default: module.DesktopDownloadsPanel })));
const ChatPanel = lazy(() => import("./pages/ChatPanel").then((module) => ({ default: module.ChatPanel })));
const UserSettingsPanel = lazy(() => import("./pages/UserSettingsPanel").then((module) => ({ default: module.UserSettingsPanel })));
const CustomerServiceInboxPanel = lazy(() => import("./pages/CustomerServiceInboxPanel").then((module) => ({ default: module.CustomerServiceInboxPanel })));
const ErpPanel = lazy(() => import("./pages/ErpPanel").then((module) => ({ default: module.ErpPanel })));
const DocumentsPanel = lazy(() => import("./pages/DocumentsPanel").then((module) => ({ default: module.DocumentsPanel })));
const UsersPanel = lazy(() => import("./pages/UsersPanel").then((module) => ({ default: module.UsersPanel })));
const ApprovalsPanel = lazy(() => import("./pages/ApprovalsPanel").then((module) => ({ default: module.ApprovalsPanel })));
const RefundsPanel = lazy(() => import("./pages/RefundsPanel").then((module) => ({ default: module.RefundsPanel })));
const AuditPanel = lazy(() => import("./pages/AuditPanel").then((module) => ({ default: module.AuditPanel })));
const RunRecordsPanel = lazy(() => import("./pages/RunRecordsPanel").then((module) => ({ default: module.RunRecordsPanel })));
const PlatformDraftReviewPanel = lazy(() => import("./pages/PlatformDraftReviewPanel").then((module) => ({ default: module.PlatformDraftReviewPanel })));
const BusinessActionLoopPanel = lazy(() => import("./pages/BusinessActionLoopPanel").then((module) => ({ default: module.BusinessActionLoopPanel })));
const PlatformExecutionTasksPanel = lazy(() => import("./pages/PlatformExecutionTasksPanel").then((module) => ({ default: module.PlatformExecutionTasksPanel })));
const NotificationsPanel = lazy(() => import("./pages/NotificationsPanel").then((module) => ({ default: module.NotificationsPanel })));
const FeedbackImprovementPanel = lazy(() => import("./pages/FeedbackImprovementPanel").then((module) => ({ default: module.FeedbackImprovementPanel })));
const FeedbackCenterPanel = lazy(() => import("./pages/FeedbackCenterPanel").then((module) => ({ default: module.FeedbackCenterPanel })));
const GeneratedFilesPanel = lazy(() => import("./pages/GeneratedFilesPanel").then((module) => ({ default: module.GeneratedFilesPanel })));
const EffectAnalyticsPanel = lazy(() => import("./pages/EffectAnalyticsPanel").then((module) => ({ default: module.EffectAnalyticsPanel })));
const EvaluationCenterPanel = lazy(() => import("./pages/EvaluationCenterPanel").then((module) => ({ default: module.EvaluationCenterPanel })));
const MonitoringCenterPanel = lazy(() => import("./pages/MonitoringCenterPanel").then((module) => ({ default: module.MonitoringCenterPanel })));
const AutomationFlowsPanel = lazy(() => import("./pages/AutomationFlowsPanel").then((module) => ({ default: module.AutomationFlowsPanel })));
const ConnectorsPanel = lazy(() => import("./pages/ConnectorsPanel").then((module) => ({ default: module.ConnectorsPanel })));
const McpToolsPanel = lazy(() => import("./pages/McpToolsPanel").then((module) => ({ default: module.McpToolsPanel })));
const PlatformActionExecutorsPanel = lazy(() => import("./pages/PlatformActionExecutorsPanel").then((module) => ({ default: module.PlatformActionExecutorsPanel })));
const ThreadsPanel = lazy(() => import("./pages/ThreadsPanel").then((module) => ({ default: module.ThreadsPanel })));
const DesktopDownloadSelectionModal = lazy(() => import("./dialogs/DesktopDownloadSelectionModal").then((module) => ({ default: module.DesktopDownloadSelectionModal })));
const ErpRecordDetailModal = lazy(() => import("./dialogs/ErpRecordDetailModal").then((module) => ({ default: module.ErpRecordDetailModal })));
const RunRecordDetailModal = lazy(() => import("./dialogs/RunRecordDetailModal").then((module) => ({ default: module.RunRecordDetailModal })));
const PlatformDraftDetailModal = lazy(() => import("./dialogs/PlatformDraftDetailModal").then((module) => ({ default: module.PlatformDraftDetailModal })));
const PlatformExecutionTaskDetailModal = lazy(() => import("./dialogs/PlatformExecutionTaskDetailModal").then((module) => ({ default: module.PlatformExecutionTaskDetailModal })));
const AutomationFlowDetailModal = lazy(() => import("./dialogs/AutomationFlowDetailModal").then((module) => ({ default: module.AutomationFlowDetailModal })));
const AiWorkflowDetailModal = lazy(() => import("./dialogs/AiWorkflowDetailModal").then((module) => ({ default: module.AiWorkflowDetailModal })));
const ConnectorDetailModal = lazy(() => import("./dialogs/ConnectorDetailModal").then((module) => ({ default: module.ConnectorDetailModal })));

export const AgentWorkspace = lazy(() => import("./components/AgentWorkspace").then((module) => ({ default: module.AgentWorkspace })));
const CompetitorMonitor = lazy(() => import("./components/CompetitorMonitor").then((module) => ({ default: module.CompetitorMonitor })));
const ProductScenePanel = lazy(() => import("./pages/ProductScenePanel").then((module) => ({ default: module.ProductScenePanel })));

export const WorkspaceLayout = lazy(() => import("./components/WorkspaceLayout").then((module) => ({ default: module.WorkspaceLayout })));

export const WorkspacePage = lazy(() => import("./components/WorkspaceLayout").then((module) => ({ default: module.WorkspacePage })));

export function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [activeView, setActiveView] = useState<View>(() => viewFromPath(window.location.pathname));
  const {
    role,
    position,
    allowedAiAppIds,
    username,
    setUsername,
    displayName,
    setDisplayName,
    userEmail,
    setUserEmail,
    password,
    setPassword,
    token,
    isLoginModalOpen,
    setIsLoginModalOpen,
    setPendingProjectTarget,
    isLoginErrorOpen,
    setIsLoginErrorOpen,
    isSessionExpiredOpen,
    setIsSessionExpiredOpen,
    lastForbiddenPath,
    setLastForbiddenPath,
    handleLogin,
    closeLoginModal,
    resetSession,
  } = useSession({
    activeView, setStatusMessage: (value) => setStatusMessage(value),
    onAuthenticated: (result, nextRole, nextPosition) => {
      setProfileForm({ displayName: result.display_name || "", email: result.email || "" });
      setAiWorkflowFilters(defaultAiWorkflowFilters(nextRole, nextPosition));
      setEffectAnalyticsFilters(defaultEffectAnalyticsFilters(nextRole, nextPosition));
      setAutomationFlowFilters(defaultAutomationFlowFilters(nextRole, nextPosition));
    },
  });

  const [statusMessage, setStatusMessage] = useState("系统就绪");
  const [isPublicLLMOpen, setIsPublicLLMOpen] = useState(false);
  const [publicLLMInput, setPublicLLMInput] = useState("");
  const [publicLLMMessages, setPublicLLMMessages] = useState<PublicLLMChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好，有什么可以帮你的？",
    },
  ]);
  const [isPublicLLMLoading, setIsPublicLLMLoading] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const [messageInput, setMessageInput] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [chatThreads, setChatThreads] = useState<ThreadListItem[]>([]);
  const [threadSearch, setThreadSearch] = useState("");
  const [threadRetentionDays, setThreadRetentionDays] = useState(15);
  const [isThreadListLoading, setIsThreadListLoading] = useState(false);
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [isRenamingThread, setIsRenamingThread] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatAbortControllerRef = useRef<AbortController | null>(null);

  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditActionFilter, setAuditActionFilter] = useState("");
  const [auditResourceFilter, setAuditResourceFilter] = useState("");
  const [auditPositionFilter, setAuditPositionFilter] = useState<Position | "all">("all");
  const {
    runRecords,
    runRecordFilters,
    setRunRecordFilters,
    runRecordDetail,
    isRunRecordDetailOpen,
    setIsRunRecordDetailOpen,
    isRunRecordDetailLoading,
    isRunRecordsLoading,
    effectAnalytics,
    effectAnalyticsFilters,
    setEffectAnalyticsFilters,
    isEffectAnalyticsLoading,
    evaluationCenter,
    isEvaluationCenterLoading,
    runningEvaluationId,
    monitoringCenter,
    monitoringCenterFilters,
    setMonitoringCenterFilters,
    isMonitoringCenterLoading,
    refreshRunRecords,
    openRunRecordDetail,
    refreshEffectAnalytics,
    refreshEvaluationCenter,
    refreshMonitoringCenter,
    runEvaluation,
    resetExecutionInsights } = useExecutionInsights({ token,
    role,
    setStatusMessage,
  });

  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileItem[]>([]);
  const [generatedFileFilters, setGeneratedFileFilters] = useState<GeneratedFileFilterState>({
    search: "",
    dateRange: "30d",
    fileType: "all",
  });
  const [isGeneratedFilesLoading, setIsGeneratedFilesLoading] = useState(false);
  const {
    profileForm,
    setProfileForm,
    passwordForm,
    setPasswordForm,
    isLoadingUserSettings,
    isSavingProfile,
    isSavingPassword,
    refreshUserSettings,
    handleSaveUserProfile,
    handleSaveUserPassword,
    resetAccountSettings } = useAccountSettings({ token,
    setUsername,
    setDisplayName,
    setUserEmail,
    setStatusMessage,
  });

  const [downloadingFileId, setDownloadingFileId] = useState("");
  const [desktopDownloads, setDesktopDownloads] = useState<DesktopDownloadItem[]>([]);
  const [isDesktopDownloadsLoading, setIsDesktopDownloadsLoading] = useState(false);
  const [isDesktopDownloadModalOpen, setIsDesktopDownloadModalOpen] = useState(false);
  const [downloadingDesktopPlatform, setDownloadingDesktopPlatform] = useState<DesktopPlatform | "">("");
  const desktopDownloadAutoOpenRef = useRef(false);
  const [confirmingEnterpriseWechatKey, setConfirmingEnterpriseWechatKey] = useState("");
  const [aiWorkflows, setAiWorkflows] = useState<AiWorkflowItem[]>([]);
  const [aiWorkflowFilters, setAiWorkflowFilters] = useState<AiWorkflowFilterState>({
    position: "all",
    category: "",
  });
  const [aiWorkflowDetail, setAiWorkflowDetail] = useState<AiWorkflowDetailResponse | null>(null);
  const [isAiWorkflowDetailOpen, setIsAiWorkflowDetailOpen] = useState(false);
  const [isAiWorkflowDetailLoading, setIsAiWorkflowDetailLoading] = useState(false);
  const [isAiWorkflowsLoading, setIsAiWorkflowsLoading] = useState(false);
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
  const platformExecutionTaskFiltersRef = useRef(platformExecutionTaskFilters);
  const platformExecutionTaskRequestRef = useRef(0);
  const [platformExecutionTaskDetail, setPlatformExecutionTaskDetail] = useState<PlatformExecutionTaskItem | null>(null);
  const [isPlatformExecutionTasksLoading, setIsPlatformExecutionTasksLoading] = useState(false);
  const [isPlatformExecutionTaskDetailOpen, setIsPlatformExecutionTaskDetailOpen] = useState(false);
  const [isPlatformExecutionTaskDetailLoading, setIsPlatformExecutionTaskDetailLoading] = useState(false);
  const [retryingPlatformExecutionTaskId, setRetryingPlatformExecutionTaskId] = useState("");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationSummary, setNotificationSummary] = useState<NotificationSummary>(EMPTY_NOTIFICATION_SUMMARY);
  const [notificationFilters, setNotificationFilters] = useState<NotificationFilterState>({
    status: "all",
    page: 1,
    pageSize: 10,
  });
  const notificationFiltersRef = useRef(notificationFilters);
  const notificationRequestRef = useRef(0);
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
  const feedbackFiltersRef = useRef(feedbackFilters);
  const feedbackRequestRef = useRef(0);
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
  const {
    connectors,
    connectorSummary,
    connectorDetail,
    isConnectorDetailOpen,
    setIsConnectorDetailOpen,
    isConnectorDetailLoading,
    isConnectorsLoading,
    mcpTools,
    mcpToolSummary,
    isMcpToolsLoading,
    checkingMcpToolId,
    updatingMcpToolId,
    platformActionExecutors,
    platformActionExecutorSummary,
    platformActionExecutorActionOptions,
    platformActionExecutorTypeOptions,
    platformActionExecutorForm,
    setPlatformActionExecutorForm,
    isPlatformActionExecutorsLoading,
    isSavingPlatformActionExecutor,
    checkingPlatformActionExecutorId,
    deletingPlatformActionExecutorId,
    refreshConnectors,
    openConnectorDetail,
    refreshMcpTools,
    toggleMcpTool,
    checkMcpTool,
    refreshPlatformActionExecutors,
    resetPlatformActionExecutorForm,
    editPlatformActionExecutor,
    savePlatformActionExecutor,
    checkPlatformActionExecutor,
    removePlatformActionExecutor,
    resetIntegrationAdmin } = useIntegrationAdmin({ token,
    setStatusMessage,
    refreshAuditLogs,
  });

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
  const [threadState, setThreadState] = useState<Record<string, unknown> | null>(null);

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

  const openChatThreadRef = useRef(openChatThread);
  openChatThreadRef.current = openChatThread;

  useEffect(() => {
    function handlePopState() {
      setActiveView(viewFromPath(window.location.pathname));
      const threadIdFromPath = threadIdFromPathname(window.location.pathname);
      if (threadIdFromPath) {
        setActiveThreadId(threadIdFromPath);
        void openChatThreadRef.current(threadIdFromPath, { silent: true, replacePath: true });
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
    if (activeView !== safeActiveView) return;
    const pathname = window.location.pathname;
    if (legacyAgentRoutes[pathname] || /^\/ai-workflows(?:\/|$)/.test(pathname)) {
      window.history.replaceState(null, "", pathForView(safeActiveView) + window.location.search);
    }
  }, [activeView, safeActiveView]);

  useEffect(() => {
    if (!isErpView(safeActiveView) && statusMessage.startsWith("ERP 查询")) {
      setStatusMessage("系统就绪");
    }
  }, [safeActiveView, statusMessage]);

  useEffect(() => {
    if (safeActiveView !== "desktop_downloads") {
      desktopDownloadAutoOpenRef.current = false;
      return;
    }

    if (!desktopDownloadAutoOpenRef.current) {
      desktopDownloadAutoOpenRef.current = true;
      setIsDesktopDownloadModalOpen(true);
    }
  }, [safeActiveView]);

  useEffect(() => {
    if (!token || safeActiveView !== "monitoring_center" || !hasAdminAccess(role, token)) {
      return;
    }

    const intervalSeconds = Math.max(
      60,
      monitoringCenter?.aiops?.summary.poll_interval_seconds || 300,
    );
    const intervalId = window.setInterval(() => {
      void refreshMonitoringCenter(token, monitoringCenterFilters);
    }, intervalSeconds * 1000);

    return () => window.clearInterval(intervalId);
  }, [
    token,
    role,
    safeActiveView,
    monitoringCenterFilters.dateRange,
    monitoringCenter?.aiops?.summary.poll_interval_seconds,
  ]);

  useWorkspaceLoading({
    token, role, position, view: safeActiveView,
    loaders: {
      sidebarThreads: () => refreshChatThreads(token, { silent: true }),
      chat: () => refreshChatThreads(token, {
        activateLatest: !activeThreadId || Boolean(threadIdFromPathname(window.location.pathname) && threadIdFromPathname(window.location.pathname) !== activeThreadId),
        silent: true,
      }),
      threads: () => refreshChatThreads(token, { silent: true }),
      dashboard: () => Promise.all([
        refreshErpDashboardOverview(),
        ...(role === "admin" ? [refreshFeedback(), refreshAuditLogs()] : []),
      ]),
      settings: () => refreshUserSettings(),
      desktopDownloads: () => refreshDesktopDownloads(),
      files: () => refreshGeneratedFiles(),
      approvals: () => refreshApprovals(),
      refunds: () => refreshRefunds(),
      audit: () => refreshAuditLogs(),
      runs: () => refreshRunRecords(),
      analytics: () => refreshEffectAnalytics(),
      evaluation: () => refreshEvaluationCenter(),
      monitoring: () => refreshMonitoringCenter(),
      workflows: () => refreshAiWorkflows(),
      automation: () => refreshAutomationTasks(token, position || undefined),
      flows: () => refreshAutomationFlows(),
      drafts: () => refreshPlatformDrafts(),
      businessLoop: () => refreshBusinessActionLoop(),
      executionTasks: () => refreshPlatformExecutionTasks(),
      notifications: () => refreshNotifications(),
      feedback: () => refreshFeedback(),
      customerInbox: () => refreshCustomerServiceMessages(),
      connectors: () => refreshConnectors(),
      mcpTools: () => refreshMcpTools(),
      executors: () => refreshPlatformActionExecutors(),
      users: () => refreshUsers(),
      erp: () => refreshErpScopes(),
    },
  });

  const stats = useMemo(
    () => [
      { title: "待处理反馈", value: feedbackSummary.open, suffix: "条" },
      { title: "会话消息", value: messages.length, suffix: "条" },
      { title: "审计日志", value: auditLogs.length, suffix: "条" },
    ],
    [auditLogs.length, feedbackSummary.open, messages.length],
  );

  function clearAuthenticatedState(options: { publicHome?: boolean } = {}) {
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    resetSession();
    setIsThreadListLoading(false);
    setIsCreatingThread(false);
    setIsRenamingThread(false);
    setAuditActionFilter("");
    setAuditResourceFilter("");
    setAuditPositionFilter("all");
    setIsGeneratedFilesLoading(false);
    setConfirmingEnterpriseWechatKey("");
    setIsAiWorkflowDetailLoading(false);
    setIsAiWorkflowsLoading(false);
    setIsPlatformDraftsLoading(false);
    setIsPlatformDraftDetailLoading(false);
    setIsPlatformExecutionTaskDetailLoading(false);
    setIsSubmittingFeedback(false);
    setIsAutomationFlowDetailLoading(false);
    setIsAutomationFlowsLoading(false);
    setCustomerInboxForm({
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
    setIsCustomerInboxLoading(false);
    setIsCreatingCustomerMessage(false);
    setIsErpRecordDetailLoading(false);
    setErpLimit(10);
    setIsErpLoading(false);
    setIsCreatingUser(false);
    setUpdatingUserAppKey("");
    setDeletingUserId("");
    setAutomationLoadingTaskId("");
    setFinanceReportInstruction("请分析上传的财务报表，输出摘要、关键指标、异常项、风险和下一步复核建议。");
    setFinanceReportOutputFormat("word");
    setIsAnalyzingFinanceReport(false);
    setFinanceExcelInstruction("根据本月销售发票和收付款单生成收款核对表，按客户/店铺汇总金额并标记未收款、金额不一致等异常。");
    setFinanceExcelErpResources([]);
    setIsTransformingFinanceExcel(false);
    setFinanceSalaryMessage("把这个月所有员工的工资表发我");
    setFinanceSalaryExportSummary("");
    setIsExportingFinanceSalary(false);
    setFinanceReconciliationInstruction("请按订单号和 SKU 匹配 Amazon 结算表、物流账单、采购成本表、广告费表和汇率表，生成订单利润表并标记异常账单。");
    setFinanceReconciliationCurrency("CNY");
    setIsReconcilingFinance(false);
    setDocumentVisibility("employee");
    setDocumentDepartment("");
    setDocumentPositionScope("all");
    setDocumentMarketScope("all");
    setDocumentStoreScope("all");
    setDocumentFieldScope("all");
    setDocumentSensitivityLevel("internal");
    setIsUploading(false);
    setMessages([]);
    setMessageInput("");
    setIsChatLoading(false);
    setChatAttachments([]);
    setActiveThreadId("");
    setChatThreads([]);
    setThreadSearch("");
    setThreadRetentionDays(15);
    setApprovals([]);
    setRefunds([]);
    setAuditLogs([]);
    setGeneratedFiles([]);
    resetAccountSettings();
    setGeneratedFileFilters({ search: "", dateRange: "30d", fileType: "all" });
    setDownloadingFileId("");
    setDesktopDownloads([]);
    setIsDesktopDownloadsLoading(false);
    setIsDesktopDownloadModalOpen(false);
    setDownloadingDesktopPlatform("");
    desktopDownloadAutoOpenRef.current = false;
    resetExecutionInsights();
    setAiWorkflows([]);
    setAiWorkflowDetail(null);
    setIsAiWorkflowDetailOpen(false);
    setAiWorkflowFilters({ position: "all", category: "" });
    setPlatformDrafts([]);
    setPlatformDraftDetail(null);
    setIsPlatformDraftDetailOpen(false);
    setPlatformDraftFilters({ draftType: "all", status: "all" });
    setPlatformDraftReviewComment("");
    setPlatformDraftActionKey("");
    setBusinessActionLoop(null);
    setIsBusinessActionLoopLoading(false);
    setPlatformExecutionTasks([]);
    platformExecutionTaskRequestRef.current += 1;
    platformExecutionTaskFiltersRef.current = { status: "all" };
    setIsPlatformExecutionTasksLoading(false);
    setPlatformExecutionTaskFilters({ status: "all" });
    setPlatformExecutionTaskDetail(null);
    setIsPlatformExecutionTaskDetailOpen(false);
    setRetryingPlatformExecutionTaskId("");
    setNotifications([]);
    setNotificationSummary(EMPTY_NOTIFICATION_SUMMARY);
    notificationRequestRef.current += 1;
    notificationFiltersRef.current = { status: "all", page: 1, pageSize: 10 };
    setNotificationFilters(notificationFiltersRef.current);
    setIsNotificationsLoading(false);
    setMarkingNotificationId("");
    setIsMarkingAllNotificationsRead(false);
    setFeedbackItems([]);
    setFeedbackSummary({ total: 0, open: 0, completed: 0 });
    setFeedbackFilters({ status: "all" });
    feedbackRequestRef.current += 1;
    feedbackFiltersRef.current = { status: "all" };
    setIsFeedbackLoading(false);
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
    resetIntegrationAdmin();
    setUsers([]);
    setNewUser({ username: "", password: "", role: "employee", position: "customer_service", department: "" });
    setDocumentFile(null);
    setFinanceReconciliationFiles([]);
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
    setErpQueryText("");
    setErpFiltersText("{}");
    setThreadSummary("");
    setThreadState(null);
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

  async function refreshDesktopDownloads(activeToken = token) {
    if (!activeToken) {
      setDesktopDownloads([]);
      setIsDesktopDownloadsLoading(false);
      return;
    }

    setIsDesktopDownloadsLoading(true);
    try {
      const result = await listDesktopDownloads(activeToken);
      setDesktopDownloads(result.items);
      setStatusMessage("桌面端下载列表已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "桌面端下载列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsDesktopDownloadsLoading(false);
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

  async function handleDownloadGeneratedArtifact(artifactId: string, filename?: string | null) {
    const cleanArtifactId = artifactId.trim();
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return false;
    }

    if (!cleanArtifactId) {
      message.warning("没有找到可下载的文件");
      return false;
    }

    setDownloadingFileId(cleanArtifactId);
    try {
      const result = await downloadGeneratedFile(token, cleanArtifactId);
      const downloadName = result.filename && result.filename !== "generated_file"
        ? result.filename
        : filename || result.filename || "generated_file";
      downloadBlob(result.blob, downloadName);
      setStatusMessage(`已开始下载：${downloadName}`);
      message.success("文件已开始下载");
      return true;
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return false;
      }
      const text = error instanceof Error ? error.message : "文件下载失败";
      setStatusMessage(text);
      message.error(text);
      return false;
    } finally {
      setDownloadingFileId("");
    }
  }

  async function handleDownloadDesktopRelease(platform: DesktopPlatform) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    const item = desktopDownloads.find((entry) => entry.platform === platform) || null;
    const downloadName = item?.filename || `enterprise-internal-workbench-${platform}.zip`;
    const link = document.createElement("a");
    link.href = getDesktopReleaseDownloadUrl(platform);
    link.download = downloadName;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setStatusMessage(`已开始下载：${item?.label || downloadName}`);
    message.success(item?.label || "桌面端安装包已开始下载");
    setIsDesktopDownloadModalOpen(false);
  }

  async function handleConfirmEnterpriseWechatSend(payload: EnterpriseWechatFileSendConfirmPayload) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    const confirmKey = enterpriseWechatConfirmKey(
      payload.artifact_id,
      payload.recipient_candidate_id || payload.recipient_name,
    );
    setConfirmingEnterpriseWechatKey(confirmKey);
    try {
      const result = await confirmEnterpriseWechatFileSend(token, payload);
      const nextThreadId = payload.thread_id || activeThreadId || result.run_id;
      const nextAttachment: ChatAttachment = {
        type: chatAttachmentTypeFromFilename(result.filename),
        filename: result.filename,
        metadata: {
          artifact_id: result.artifact_id,
          download_path: result.download_path || `/files/${result.artifact_id}/download`,
        },
      };
      setMessages((current) =>
        current.map((item) =>
          item.id === payload.source_message_id || chatMessageContainsArtifact(item, result.artifact_id)
            ? {
              ...item,
              threadId: nextThreadId,
              content: result.answer,
              createdAt: item.createdAt === "正在生成" ? "刚刚" : item.createdAt,
              route: routeFromIntent("enterprise_wechat_file_send", null),
              attachments: [nextAttachment],
              approvalResult: {
                status: result.status,
                status_label: result.status_label,
              },
              automation: {
                type: "enterprise_wechat_file_send",
                workflow_id: payload.source_workflow_id || "enterprise_wechat_file_send",
                status: result.status,
                status_label: result.status_label,
                artifact_id: result.artifact_id,
                filename: result.filename,
                download_path: result.download_path || `/files/${result.artifact_id}/download`,
                wechat_send: result.execution,
              },
              businessProgress: null,
            }
            : item,
        ),
      );
      setStatusMessage(result.status_label || "企业微信发送流程已处理");
      if (result.status === "completed") {
        message.success("企业微信文件已发送");
      } else {
        message.warning(result.answer || result.status_label || "企业微信发送还需要管理员处理");
      }
      void refreshChatThreads(token, { silent: true });
      void refreshGeneratedFiles(token);
      void refreshBusinessActionLoop(token);
      void refreshRunRecords();
      if (role === "admin") {
        await refreshAuditLogs();
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "企业微信发送确认失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setConfirmingEnterpriseWechatKey("");
    }
  }

  async function handleConfirmEmailSend(payload: EmailFileSendConfirmPayload) {
    if (!token) {
      message.warning("请先登录");
      return;
    }
    try {
      const result = await confirmEmailFileSend(token, payload);
      setMessages((current) => current.map((item) => {
        const approval = item.approvalResult;
        if (approval?.confirmation_id !== payload.confirmation_id) return item;
        const nextApproval = result.status !== "failed"
          ? { status: result.status, status_label: result.status_label }
          : { ...approval, message: result.error || result.status_label };
        return {
          ...item,
          approvalResult: nextApproval,
          automation: result.status !== "failed"
            ? { ...(item.automation || {}), status: result.status, confirmation_card: nextApproval }
            : item.automation,
          content: result.status === "sent"
            ? `${item.content}\n邮件已发送至 ${result.recipient}` : item.content,
        };
      }));
      setStatusMessage(result.status_label);
      if (result.status === "sent") message.success(result.status_label);
      else message.error(result.error || result.status_label);
      void refreshRunRecords();
    } catch (error) {
      if (isAuthExpiredError(error)) return;
      const text = error instanceof Error ? error.message : "邮件确认失败";
      setStatusMessage(text);
      message.error(text);
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
  async function refreshRefunds(activeToken = token) {
    if (!activeToken || role !== "admin") return;
    try {
      const result = await listRefunds(activeToken);
      setRefunds(result.items.map(mapRefund));
    } catch (error) {
      if (isAuthExpiredError(error)) return;
      const text = error instanceof Error ? error.message : "退款记录加载失败";
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

  function handlePlatformExecutionTaskStatusChange(status: PlatformExecutionTaskFilterState["status"]) {
    const filters = { status };
    platformExecutionTaskFiltersRef.current = filters;
    setPlatformExecutionTaskFilters(filters);
    setPlatformExecutionTasks([]);
    void refreshPlatformExecutionTasks(token, filters);
  }

  async function refreshPlatformExecutionTasks(activeToken = token, filters = platformExecutionTaskFiltersRef.current) {
    const requestId = ++platformExecutionTaskRequestRef.current;
    const isCurrentRequest = () => requestId === platformExecutionTaskRequestRef.current
      && activeToken === localStorage.getItem("access_token");
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
      if (!isCurrentRequest()) return;
      setPlatformExecutionTasks(result.items);
      setStatusMessage("执行任务中心已刷新");
    } catch (error) {
      if (!isCurrentRequest() || isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "执行任务列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      if (isCurrentRequest()) setIsPlatformExecutionTasksLoading(false);
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
        setPlatformExecutionTasks((current) => upsertPlatformExecutionTask(current, nextTask)
          .filter((item) => platformExecutionTaskFiltersRef.current.status === "all"
            || item.status === platformExecutionTaskFiltersRef.current.status));
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

  function handleNotificationFiltersChange(filters: NotificationFilterState) {
    notificationFiltersRef.current = filters;
    setNotificationFilters(filters);
    setNotifications([]);
    void refreshNotifications(token, filters);
  }

  function notificationFilterPayload(filters = notificationFiltersRef.current) {
    return {
      status: filters.status,
      limit: filters.pageSize,
      offset: (filters.page - 1) * filters.pageSize,
    };
  }

  async function refreshNotifications(activeToken = token, filters = notificationFiltersRef.current): Promise<void> {
    const requestId = ++notificationRequestRef.current;
    const isCurrentRequest = () => requestId === notificationRequestRef.current
      && activeToken === localStorage.getItem("access_token");
    if (!activeToken) {
      setNotifications([]);
      setNotificationSummary(EMPTY_NOTIFICATION_SUMMARY);
      setIsNotificationsLoading(false);
      return;
    }

    setIsNotificationsLoading(true);

    try {
      const result = await listNotifications(activeToken, notificationFilterPayload(filters));
      if (!isCurrentRequest()) return;
      setNotificationSummary({
        unread_count: result.unread_count,
        read_count: result.read_count,
        total_count: result.total_count,
        resource_count: result.resource_count,
      });
      const total = filters.status === "unread" ? result.unread_count
        : filters.status === "read" ? result.read_count : result.total_count;
      const lastPage = Math.max(1, Math.ceil(total / filters.pageSize));
      if (filters.page > lastPage) {
        const correctedFilters = { ...filters, page: lastPage };
        notificationFiltersRef.current = correctedFilters;
        setNotificationFilters(correctedFilters);
        return refreshNotifications(activeToken, correctedFilters);
      }
      setNotifications(result.items);
      setStatusMessage("通知中心已刷新");
    } catch (error) {
      if (!isCurrentRequest() || isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "通知列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      if (isCurrentRequest()) setIsNotificationsLoading(false);
    }
  }

  async function handleMarkNotificationRead(notificationId: string) {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setMarkingNotificationId(notificationId);
    const activeToken = token;
    const wasUnread = notifications.some((item) => item.id === notificationId && item.status === "unread");

    try {
      const result = await markNotificationRead(token, notificationId);
      if (activeToken !== localStorage.getItem("access_token")) return;
      setNotifications((current) =>
        current.map((item) => item.id === notificationId
          ? result.item || { ...item, status: "read", read_at: new Date().toISOString() }
          : item).filter((item) => notificationFiltersRef.current.status === "all"
            || item.status === notificationFiltersRef.current.status),
      );
      if (wasUnread) {
        setNotificationSummary((current) => ({
          ...current,
          unread_count: Math.max(0, current.unread_count - 1),
          read_count: Math.min(current.total_count, current.read_count + 1),
        }));
      }
      void refreshNotifications(activeToken);
      setStatusMessage("通知已标记为已读");
    } catch (error) {
      if (activeToken !== localStorage.getItem("access_token") || isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "通知已读操作失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      if (activeToken === localStorage.getItem("access_token")) setMarkingNotificationId("");
    }
  }

  async function handleMarkAllNotificationsRead() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsMarkingAllNotificationsRead(true);
    const activeToken = token;

    try {
      await markAllNotificationsRead(token);
      if (activeToken !== localStorage.getItem("access_token")) return;
      const readAt = new Date().toISOString();
      setNotifications((current) => notificationFiltersRef.current.status === "unread" ? []
        : current.map((item) => ({ ...item, status: "read", read_at: item.read_at || readAt })));
      setNotificationSummary((current) => ({ ...current, unread_count: 0, read_count: current.total_count }));
      setStatusMessage("通知已全部标记为已读");
      message.success("通知已全部标记为已读");
      void refreshNotifications(token);
    } catch (error) {
      if (activeToken !== localStorage.getItem("access_token") || isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "全部已读操作失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      if (activeToken === localStorage.getItem("access_token")) setIsMarkingAllNotificationsRead(false);
    }
  }

  function feedbackFilterPayload(filters = feedbackFilters) {
    return {
      status: filters.status,
      limit: 120,
    };
  }

  function handleFeedbackStatusChange(status: FeedbackFilterState["status"]) {
    const filters = { status };
    feedbackFiltersRef.current = filters;
    setFeedbackFilters(filters);
    setFeedbackItems([]);
    void refreshFeedback(token, filters);
  }

  async function refreshFeedback(activeToken = token, filters = feedbackFiltersRef.current) {
    const requestId = ++feedbackRequestRef.current;
    const isCurrentRequest = () => requestId === feedbackRequestRef.current
      && activeToken === localStorage.getItem("access_token");
    if (!activeToken) {
      setFeedbackItems([]);
      setFeedbackSummary({ total: 0, open: 0, completed: 0 });
      setIsFeedbackLoading(false);
      return;
    }

    setIsFeedbackLoading(true);

    try {
      const result = await listFeedback(activeToken, feedbackFilterPayload(filters));
      if (!isCurrentRequest()) return;
      setFeedbackItems(result.items);
      setFeedbackSummary(result.summary);
      setStatusMessage(role === "admin" ? "反馈中心已刷新" : "我的反馈已刷新");
    } catch (error) {
      if (!isCurrentRequest() || isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "反馈列表加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      if (isCurrentRequest()) setIsFeedbackLoading(false);
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
      setFeedbackItems((current) => [result.item, ...current.filter((item) => item.id !== result.item.id)]
        .filter((item) => feedbackFiltersRef.current.status === "all" || item.status === feedbackFiltersRef.current.status));
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
      setFeedbackItems((current) => current.map((item) => item.id === feedbackId ? result.item : item)
        .filter((item) => feedbackFiltersRef.current.status === "all" || item.status === feedbackFiltersRef.current.status));
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

    if (resourceType === "agent") {
      const target = workflowIdViewMap[resourceId];
      if (target && canRoleAccessView(role, target, position, allowedAiAppIds)) navigateToView(target);
      else message.warning("当前账号没有该 Agent 的访问权限");
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
        void refreshAuditLogs(token);
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
          setThreadState(null);
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
    options: { activeToken?: string; replacePath?: boolean; silent?: boolean; navigate?: boolean } = {},
  ) {
    const activeToken = options.activeToken || token;
    const shouldNavigate = options.navigate !== false;
    if (!activeToken) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!threadId) {
      setActiveThreadId("");
      setMessages([]);
      setThreadSummary("");
      setThreadState(null);
      navigateToPath("/chat", { replace: options.replacePath });
      return;
    }

    try {
      const result = await getThreadMessages(activeToken, threadId);
      setActiveThreadId(threadId);
      setMessages(result.messages.map(mapThreadMessage));
      setThreadSummary(String(result.summary.summary || ""));
      setThreadState(recordFromUnknown(result.state));
      if (shouldNavigate) {
        navigateToPath(`/chat/${encodeURIComponent(threadId)}`, { replace: options.replacePath });
      }
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
      setThreadState(null);
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
      attachments: chatAttachments,
    };
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      threadId: pendingThreadId,
      role: "assistant",
      content: "",
      createdAt: "正在生成",
    };

    const abortController = new AbortController();
    chatAbortControllerRef.current = abortController;

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
        onBusinessProgress: (payload) => {
          const progress = normalizeBusinessProgress(payload);
          if (progress?.label) {
            setStatusMessage(progress.label);
          }
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessageId
                ? {
                  ...item,
                  businessProgress: progress,
                }
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
                  approvalResult: payload.approval_result || null,
                  automation: payload.automation || null,
                  businessProgress: null,
                }
                : item,
            ),
          );
        },
        onError: (payload) => {
          throw new Error(payload.message || "流式聊天失败");
        },
      }, chatAttachments, abortController.signal);

      setChatAttachments([]);
      setStatusMessage("聊天完成");
      void refreshChatThreads(token, { silent: true });
      void refreshBusinessActionLoop(token);
      void refreshRunRecords();

      if (role === "admin") {
        await refreshAuditLogs();
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const isAborted = error instanceof DOMException && error.name === "AbortError";
      if (isAborted) {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantMessageId
              ? {
                ...item,
                content: item.content || "已终止",
                createdAt: "已终止",
                businessProgress: null,
              }
              : item,
          ),
        );
        setStatusMessage("已终止当前回答");
        message.info("已终止当前回答");
        return;
      }
      const text = error instanceof Error ? error.message : "发送失败";
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId
            ? {
              ...item,
              content: item.content
                ? `${item.content}\n\n执行没有完成：${text}`
                : `执行没有完成：${text}`,
              createdAt: "刚刚",
              businessProgress: null,
            }
            : item,
        ),
      );
      setStatusMessage(text);
      message.error(text);
    } finally {
      if (chatAbortControllerRef.current === abortController) {
        chatAbortControllerRef.current = null;
      }
      setIsChatLoading(false);
    }
  }

  function stopMessage() {
    chatAbortControllerRef.current?.abort();
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
      const result = await reviewApprovalApi(token, id, approved);
      await refreshApprovals();
      const refundResult = result.refund_result as { success?: boolean; message?: string } | null;
      const text = approved && refundResult?.success === false
        ? `审批已通过，退款未完成：${refundResult.message || '请核对后重试'}`
        : approved ? "审批已通过" : "审批已拒绝";
      setStatusMessage(text);
      if (refundResult?.success === false) message.warning(text);
      else message.success(text);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "审批失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function retryRefundApproval(id: string) {
    if (!token) return;
    try {
      const result = await retryRefundApprovalApi(token, id);
      await refreshApprovals();
      const refundResult = result.refund_result as { success?: boolean; message?: string } | null;
      const text = refundResult?.message || '退款状态已更新';
      setStatusMessage(text);
      if (refundResult?.success) message.success(text);
      else message.warning(text);
    } catch (error) {
      if (isAuthExpiredError(error)) return;
      const text = error instanceof Error ? error.message : '退款重试失败';
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
        await refreshAuditLogs();
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
          <AsyncBoundary>
            <PublicPortal
              language={language}
              onLanguageChange={() => setLanguage((current) => (current === "zh" ? "en" : "zh"))}
              onLLMClick={() => setIsPublicLLMOpen(true)}
              isAuthenticated={Boolean(token)}
              onProjectClick={(target) => {
                setPendingProjectTarget(target);
                if (token) {
                  if (target === "gateway") {
                    window.location.assign(import.meta.env.VITE_GATEWAY_URL || "http://localhost:8082");
                  } else {
                    navigateToView("dashboard");
                  }
                  setPendingProjectTarget(null);
                } else {
                  setIsLoginModalOpen(true);
                }
              }}
            />
          </AsyncBoundary>
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
          colorPrimary: "#3973ff",
          colorBgLayout: "#f6f7fb",
          colorBgContainer: "#ffffff",
          colorBorder: "#e3e8f0",
          colorBorderSecondary: "#e8ecf3",
          colorText: "#202630",
          colorTextSecondary: "#727e94",
          borderRadius: 8,
          controlHeight: 36,
          fontSize: 14,
          wireframe: false,
        },
        components: {
          Button: { primaryShadow: "none", defaultShadow: "none" },
          Card: { headerFontSize: 15, headerHeight: 52 },
          Table: { headerBg: "#f8f9fc", headerColor: "#657189", cellPaddingBlockSM: 12 },
          Segmented: { trackBg: "#f3f5fa", itemSelectedBg: "#3973ff", itemSelectedColor: "#ffffff" },
          Menu: { itemSelectedBg: "#edf3ff", itemSelectedColor: "#3973ff", itemBorderRadius: 8 },
        },
      }}
    >
      <AntApp>
        <AsyncBoundary>
          <WorkspaceLayout
            className="workspaceLayout"
            title={false}
            logo={false}
            route={route}
            location={{ pathname: currentPath }}
            layout="side"
            headerRender={false}
            splitMenus={false}
            siderWidth={216}
            collapsed={isSidebarCollapsed}
            onCollapse={(nextCollapsed) => setIsSidebarCollapsed(nextCollapsed)}
            contentStyle={{ background: "#f6f7fb", padding: 24 }}
            siderMenuType="group"
            menuHeaderRender={() =>
              isSidebarCollapsed ? (
                <div className="sidebarBrand sidebarBrandCollapsed">
                  <div className="sidebarBrandIcon">
                    <SafetyCertificateOutlined />
                  </div>
                </div>
              ) : (
                <div className="sidebarBrand">
                  <div className="sidebarBrandIcon">
                    <SafetyCertificateOutlined />
                  </div>
                  <span>企业内部工作台</span>
                </div>
              )
            }
            menuFooterRender={() => (
              <div className={isSidebarCollapsed ? "sidebarUserDock compact" : "sidebarUserDock"}>
                <UserMenu
                  username={username}
                  displayName={displayName}
                  role={role}
                  position={position}
                  token={token}
                  collapsed={isSidebarCollapsed}
                  openLogin={() => setIsLoginModalOpen(true)}
                  logout={handleLogout}
                />
              </div>
            )}
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
                  if (matched?.id === "desktop_downloads") {
                    navigateToView("desktop_downloads");
                    setIsDesktopDownloadModalOpen(true);
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
            token={{
              sider: {
                colorMenuBackground: "#ffffff",
              },
            }}
          >
            <WorkspacePage
              className={safeActiveView === "chat" ? "workspacePageContainer workspaceChatPage" : "workspacePageContainer"}
              title={safeActiveView === "chat" ? false : titleForView(safeActiveView)}
              subTitle={safeActiveView === "chat" ? false : workspacePageDescription(safeActiveView, role, position)}
              style={{ minHeight: "calc(100vh - 48px)" }}
              childrenContentStyle={{ padding: 0 }}
            >
              <AsyncBoundary resetKey={safeActiveView}>
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
                  {safeActiveView === "desktop_downloads" && (
                    <DesktopDownloadsPanel
                      downloads={desktopDownloads}
                      loading={isDesktopDownloadsLoading}
                      openSelector={() => setIsDesktopDownloadModalOpen(true)}
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
                      token={token}
                      data={monitoringCenter}
                      filters={monitoringCenterFilters}
                      setFilters={setMonitoringCenterFilters}
                      loading={isMonitoringCenterLoading}
                      refreshMonitoringCenter={() => refreshMonitoringCenter()}
                    />
                  )}
                  {safeActiveView === "operations_product_scene" && (
                    <ProductScenePanel token={token} onNavigate={navigateToView} />
                  )}
                  {isAiWorkflowView(safeActiveView) && (
                    workflowIdFromView(safeActiveView) === 'operations_competitor_analysis' ?
                    <CompetitorMonitor key={token} token={token} role={role} onNavigate={(view) => navigateToView(view as View)} /> : <AgentWorkspace
                      key={token + ":" + (workflowIdFromView(safeActiveView) || "all")}
                      token={token}
                      role={role}
                      workflows={aiWorkflows}
                      selectedWorkflowId={workflowIdFromView(safeActiveView)}
                      loading={isAiWorkflowsLoading}
                      refreshWorkflows={() => refreshAiWorkflows()}
                      openTechnicalDetail={openAiWorkflowDetail}
                      onOpenWorkflow={(id) => navigateToView(workflowIdViewMap[id] || "ai_workflows")}
                      onNavigate={(view) => navigateToView(view as View)}
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
                      onStatusChange={handlePlatformExecutionTaskStatusChange}
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
                      summary={notificationSummary}
                      filters={notificationFilters}
                      onFiltersChange={handleNotificationFiltersChange}
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
                      onStatusChange={handleFeedbackStatusChange}
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
                      onStatusChange={handleFeedbackStatusChange}
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
                  {safeActiveView === "mcp_tools" && role === "admin" && (
                    <McpToolsPanel
                      tools={mcpTools}
                      summary={mcpToolSummary}
                      loading={isMcpToolsLoading}
                      checkingId={checkingMcpToolId}
                      updatingId={updatingMcpToolId}
                      refresh={() => refreshMcpTools()}
                      toggle={toggleMcpTool}
                      checkHealth={checkMcpTool}
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
                      token={token}
                      messageInput={messageInput}
                      setMessageInput={setMessageInput}
                      attachments={chatAttachments}
                      setAttachments={setChatAttachments}
                      openSupportedApps={() => navigateToView("ai_workflows")}
                      activeThread={chatThreads.find((item) => item.id === activeThreadId) || null}
                      activeThreadId={activeThreadId}
                      createThread={handleCreateChatThread}
                      renameThread={handleRenameChatThread}
                      sendMessage={sendMessage}
                      stopMessage={stopMessage}
                      messages={messages}
                      isLoading={isChatLoading}
                      statusMessage={statusMessage}
                      isCreatingThread={isCreatingThread}
                      isRenamingThread={isRenamingThread}
                      position={position}
                      confirmingEnterpriseWechatKey={confirmingEnterpriseWechatKey}
                      downloadingArtifactId={downloadingFileId}
                      confirmEnterpriseWechatSend={handleConfirmEnterpriseWechatSend}
                      confirmEmailSend={handleConfirmEmailSend}
                      downloadGeneratedArtifact={handleDownloadGeneratedArtifact}
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
                    <ApprovalsPanel approvals={approvals} reviewApproval={reviewApproval}
                      retryRefund={retryRefundApproval} role={role} position={position} />
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
                      openThread={(threadId, options) => openChatThread(threadId, options)}
                      messages={messages}
                      summary={threadSummary}
                      state={threadState}
                      loading={isThreadListLoading}
                      role={role}
                      retentionDays={threadRetentionDays}
                    />
                  )}
                </Space>
              </AsyncBoundary>
            </WorkspacePage>
            {isDesktopDownloadModalOpen && <AsyncBoundary><DesktopDownloadSelectionModal
              open={isDesktopDownloadModalOpen}
              downloads={desktopDownloads}
              loading={isDesktopDownloadsLoading}
              downloadingPlatform={downloadingDesktopPlatform}
              onCancel={() => setIsDesktopDownloadModalOpen(false)}
              onSelectPlatform={(platform) => void handleDownloadDesktopRelease(platform)}
            /></AsyncBoundary>}
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
            {isErpRecordDetailOpen && <AsyncBoundary><ErpRecordDetailModal
              open={isErpRecordDetailOpen}
              loading={isErpRecordDetailLoading}
              detail={erpRecordDetail}
              role={role}
              onClose={() => setIsErpRecordDetailOpen(false)}
            /></AsyncBoundary>}
            {isRunRecordDetailOpen && <AsyncBoundary><RunRecordDetailModal
              open={isRunRecordDetailOpen}
              loading={isRunRecordDetailLoading}
              detail={runRecordDetail}
              onClose={() => setIsRunRecordDetailOpen(false)}
            /></AsyncBoundary>}
            {isPlatformDraftDetailOpen && <AsyncBoundary><PlatformDraftDetailModal
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
            /></AsyncBoundary>}
            {isPlatformExecutionTaskDetailOpen && <AsyncBoundary><PlatformExecutionTaskDetailModal
              open={isPlatformExecutionTaskDetailOpen}
              loading={isPlatformExecutionTaskDetailLoading}
              task={platformExecutionTaskDetail}
              role={role}
              retryingTaskId={retryingPlatformExecutionTaskId}
              retryTask={handleRetryPlatformExecutionTask}
              onClose={() => setIsPlatformExecutionTaskDetailOpen(false)}
            /></AsyncBoundary>}
            {isAutomationFlowDetailOpen && <AsyncBoundary><AutomationFlowDetailModal
              open={isAutomationFlowDetailOpen}
              loading={isAutomationFlowDetailLoading}
              detail={automationFlowDetail}
              token={token}
              onClose={() => setIsAutomationFlowDetailOpen(false)}
            /></AsyncBoundary>}
            {isAiWorkflowDetailOpen && <AsyncBoundary><AiWorkflowDetailModal
              open={isAiWorkflowDetailOpen}
              loading={isAiWorkflowDetailLoading}
              detail={aiWorkflowDetail}
              onClose={() => setIsAiWorkflowDetailOpen(false)}
            /></AsyncBoundary>}
            {isConnectorDetailOpen && <AsyncBoundary><ConnectorDetailModal
              open={isConnectorDetailOpen}
              loading={isConnectorDetailLoading}
              detail={connectorDetail}
              token={token}
              refreshConnectors={() => refreshConnectors()}
              onClose={() => setIsConnectorDetailOpen(false)}
            /></AsyncBoundary>}
          </WorkspaceLayout>
        </AsyncBoundary>
      </AntApp>
    </ConfigProvider>
  );
}
