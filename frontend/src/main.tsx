import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ApiOutlined,
  AppstoreOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  CommentOutlined,
  DatabaseOutlined,
  LoginOutlined,
  DownOutlined,
  FileTextOutlined,
  HistoryOutlined,
  LogoutOutlined,
  MessageOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  SearchOutlined,
  StopOutlined,
} from "@ant-design/icons";
import {
  App as AntApp,
  Avatar,
  Button,
  Card,
  Col,
  ConfigProvider,
  Empty,
  Form,
  Input,
  InputNumber,
  Dropdown,
  Modal,
  Radio,
  Row,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
  theme,
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
  createUser,
  getEffectAnalytics,
  getConnectorDetail,
  getAutomationFlowDetail,
  generateAutomation,
  isAuthExpiredError,
  transformFinanceExcel,
  getErpDashboardOverview,
  getErpDiagnostics,
  getErpRecordDetail,
  getErpScopes,
  getErpStatus,
  listAutomationTasks,
  listRunRecords,
  sendPublicLLMChatStream,
  sendChatStream,
  uploadDocument,
  listApprovals,
  listAuditLogs,
  listRefunds,
  listUsers,
  getThreadMessages,
  getRunRecordDetail,
  listConnectors,
  listAutomationFlows,
  queryErp,
  reviewApproval as reviewApprovalApi,
  type ApprovalItem,
  type AuditLogItem,
  type AutomationFlowDetailResponse,
  type AutomationFlowItem,
  type ConnectorConfigField,
  type ConnectorDetailResponse,
  type ConnectorItem,
  type ConnectorsResponse,
  type EffectAnalyticsResponse,
  type AutomationTaskItem,
  type ErpDashboardOverviewResponse,
  type ErpDiagnosticsResponse,
  type ErpQueryResponse,
  type ErpRecordDetailResponse,
  type ErpReference,
  type ErpResourceItem,
  type ErpStatusResponse,
  type Position,
  type PublicLLMMessage,
  type RefundItem,
  type RunRecordDetailResponse,
  type RunRecordFilters,
  type RunRecordItem,
  type ThreadMessageItem,
  type UserCreatePayload,
  type UserItem,
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
type ChatRoute = "refund_workflow" | "order_agent" | "knowledge_rag";
type View =
  | "dashboard"
  | "ai_apps"
  | "run_records"
  | "effect_analytics"
  | "automation_flows"
  | "connectors"
  | "automation"
  | "automation_operations"
  | "automation_customer_service"
  | "automation_finance"
  | "erp"
  | "erp_query"
  | "erp_resources"
  | "erp_diagnostics"
  | "chat"
  | "documents"
  | "users"
  | "approvals"
  | "refunds"
  | "audit"
  | "threads";

type NavItem = {
  path: string;
  id: View;
  name: string;
  icon: React.ReactNode;
  roles: Role[];
  positions?: Position[];
  children?: NavItem[];
};

type ChatMessage = {
  id: string;
  threadId: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: string;
  route?: ChatRoute;
  erpReferences?: ErpReference[];
};

type PublicLLMChatMessage = PublicLLMMessage & {
  id: string;
};

type Approval = {
  id: string;
  threadId: string;
  actionType: string;
  status: string;
  orderNo: string;
  amount: string;
  reason: string;
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
  resourceType: string;
  resourceId: string;
  actor: string;
  position: string;
  createdAt: string;
};

type UserRecord = {
  id: string;
  username: string;
  role: Role;
  department: string;
  position: Position | null;
  capabilities: string[];
  erpScopes: string[];
  createdAt: string;
};

type AutomationTaskRecord = AutomationTaskItem & {
  inputText: string;
  output: string;
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
};

type EffectAnalyticsFilterState = {
  dateRange: "7d" | "30d" | "90d" | "all";
  position: Position | "all";
};

type AutomationFlowFilterState = {
  position: Position | "all";
  category: string;
};

type DashboardMarket = "all" | "us" | "de" | "jp";
type DashboardDateRange = "all" | "today" | "7d" | "30d";
type DashboardStore = "all" | "us_store" | "de_store" | "jp_store";

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

const navItems: NavItem[] = [
  { path: "/dashboard", id: "dashboard", name: "概览", icon: <DatabaseOutlined />, roles: ["admin", "employee"] },
  { path: "/ai-apps", id: "ai_apps", name: "AI 应用中心", icon: <AppstoreOutlined />, roles: ["admin", "employee"] },
  { path: "/run-records", id: "run_records", name: "运行记录", icon: <HistoryOutlined />, roles: ["admin", "employee"] },
  { path: "/effect-analytics", id: "effect_analytics", name: "效果分析", icon: <AuditOutlined />, roles: ["admin", "employee"] },
  { path: "/automation-flows", id: "automation_flows", name: "流程配置", icon: <AuditOutlined />, roles: ["admin", "employee"] },
  { path: "/connectors", id: "connectors", name: "连接器中心", icon: <ApiOutlined />, roles: ["admin"] },
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
      },
      {
        path: "/automation/customer-service",
        id: "automation_customer_service",
        name: "客服 AI 自动化",
        icon: <MessageOutlined />,
        roles: ["admin", "employee"],
        positions: ["customer_service"],
      },
      {
        path: "/automation/finance",
        id: "automation_finance",
        name: "财务 AI 自动化",
        icon: <CloudUploadOutlined />,
        roles: ["admin", "employee"],
        positions: ["finance"],
      },
    ],
  },
  {
    path: "/erp",
    id: "erp",
    name: "ERP 查询",
    icon: <ApiOutlined />,
    roles: ["admin", "employee"],
    children: [
      {
        path: "/erp/query",
        id: "erp_query",
        name: "ERP 连接查询",
        icon: <SearchOutlined />,
        roles: ["admin", "employee"],
      },
      {
        path: "/erp/resources",
        id: "erp_resources",
        name: "ERP 资源列表",
        icon: <DatabaseOutlined />,
        roles: ["admin", "employee"],
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
  { path: "/chat", id: "chat", name: "客服对话", icon: <MessageOutlined />, roles: ["admin", "employee"] },
  { path: "/documents", id: "documents", name: "知识库", icon: <FileTextOutlined />, roles: ["admin"] },
  { path: "/users", id: "users", name: "用户管理", icon: <SafetyCertificateOutlined />, roles: ["admin"] },
  { path: "/approvals", id: "approvals", name: "审批", icon: <CheckCircleOutlined />, roles: ["admin"] },
  { path: "/refunds", id: "refunds", name: "退款流水", icon: <HistoryOutlined />, roles: ["admin"] },
  { path: "/audit", id: "audit", name: "审计日志", icon: <AuditOutlined />, roles: ["admin"] },
  { path: "/threads", id: "threads", name: "会话详情", icon: <RobotOutlined />, roles: ["admin", "employee"] },
];

const dashboardMarketOptions: Array<{ label: string; value: DashboardMarket }> = [
  { label: "全部", value: "all" },
  { label: "美国", value: "us" },
  { label: "德国", value: "de" },
  { label: "日本", value: "jp" },
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

function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [activeView, setActiveView] = useState<View>(() => viewFromPath(window.location.pathname));
  const [role, setRole] = useState<Role>(readStoredRole);
  const [position, setPosition] = useState<Position | null>(readStoredPosition);
  const [username, setUsername] = useState(localStorage.getItem("username") ?? "");
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
      content: "你好，有什么可以帮你的？（当前知识截止2024.6.18，未接入联网搜索）",
    },
  ]);
  const [isPublicLLMLoading, setIsPublicLLMLoading] = useState(false);

  const [messageInput, setMessageInput] = useState("");
  const [threadInput, setThreadInput] = useState("thread-10086");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditActionFilter, setAuditActionFilter] = useState("");
  const [auditResourceFilter, setAuditResourceFilter] = useState("");
  const [auditPositionFilter, setAuditPositionFilter] = useState<Position | "all">("all");
  const [runRecords, setRunRecords] = useState<RunRecordItem[]>([]);
  const [runRecordFilters, setRunRecordFilters] = useState<RunRecordFilterState>({
    status: "all",
    runType: "",
    appId: "",
    position: "all",
    resourceType: "",
    resourceId: "",
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
  const [automationFlows, setAutomationFlows] = useState<AutomationFlowItem[]>([]);
  const [automationFlowFilters, setAutomationFlowFilters] = useState<AutomationFlowFilterState>({
    position: "all",
    category: "",
  });
  const [automationFlowDetail, setAutomationFlowDetail] = useState<AutomationFlowDetailResponse | null>(null);
  const [isAutomationFlowDetailOpen, setIsAutomationFlowDetailOpen] = useState(false);
  const [isAutomationFlowDetailLoading, setIsAutomationFlowDetailLoading] = useState(false);
  const [isAutomationFlowsLoading, setIsAutomationFlowsLoading] = useState(false);
  const [connectors, setConnectors] = useState<ConnectorItem[]>([]);
  const [connectorSummary, setConnectorSummary] = useState<ConnectorsResponse["summary"] | null>(null);
  const [connectorDetail, setConnectorDetail] = useState<ConnectorDetailResponse | null>(null);
  const [isConnectorDetailOpen, setIsConnectorDetailOpen] = useState(false);
  const [isConnectorDetailLoading, setIsConnectorDetailLoading] = useState(false);
  const [isConnectorsLoading, setIsConnectorsLoading] = useState(false);
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
  const [automationLoadingTaskId, setAutomationLoadingTaskId] = useState("");
  const [financeExcelFile, setFinanceExcelFile] = useState<File | null>(null);
  const [financeExcelInstruction, setFinanceExcelInstruction] = useState(
    "请整理财务表格，生成数值汇总，标记需要人工复核的异常。",
  );
  const [isTransformingFinanceExcel, setIsTransformingFinanceExcel] = useState(false);

  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentVisibility, setDocumentVisibility] = useState<Role>("employee");
  const [documentDepartment, setDocumentDepartment] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const [threadFilter, setThreadFilter] = useState("thread-10086");
  const [threadSummary, setThreadSummary] = useState("");
  const [threadStateText, setThreadStateText] = useState("");

  const pendingCount = approvals.filter((item) => item.status === "pending").length;
  const succeededRefunds = refunds.filter((item) => item.status === "succeeded").length;
  const visibleNavItems = useMemo(
    () => visibleNavigationForUser(role, position),
    [position, role],
  );
  const flatVisibleNavItems = useMemo(
    () => flattenNavItems(visibleNavItems),
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
  const currentPath = flatVisibleNavItems.find((item) => item.id === safeActiveView)?.path || "/dashboard";

  useEffect(() => {
    function handlePopState() {
      setActiveView(viewFromPath(window.location.pathname));
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

  const stats = useMemo(
    () => [
      { title: "待审批", value: pendingCount, suffix: "条" },
      { title: "退款成功", value: succeededRefunds, suffix: "笔" },
      { title: "会话消息", value: messages.length, suffix: "条" },
      { title: "审计日志", value: auditLogs.length, suffix: "条" },
    ],
    [auditLogs.length, messages.length, pendingCount, succeededRefunds],
  );

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");

    if (!storedToken) {
      return;
    }

    void refreshAutomationTasks(storedToken, position || undefined);
    void refreshErpScopes(storedToken, role);
    void refreshErpDashboardOverview(storedToken, erpDashboardMarket, erpDashboardDateRange, erpDashboardStore);
    void refreshRunRecords(storedToken);
    void refreshEffectAnalytics(storedToken);
    void refreshAutomationFlows(storedToken);

    if (role === "admin") {
      void refreshAdminData(storedToken);
      void refreshUsers(storedToken);
      void refreshConnectors(storedToken);
    }
  }, []);

  async function handleLogin() {
    try {
      setIsLoginErrorOpen(false);
      const result = await login(username, password);
      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("username", result.username || username);
      setToken(result.access_token);
      setUsername(result.username || username);

      const nextRole = result.role || readRoleFromToken(result.access_token);
      const nextPosition = result.position || readPositionFromToken(result.access_token);
      localStorage.setItem("role", nextRole);
      if (nextPosition) {
        localStorage.setItem("position", nextPosition);
      } else {
        localStorage.removeItem("position");
      }
      setRole(nextRole);
      setPosition(nextPosition);
      if (!canRoleAccessView(nextRole, activeView)) {
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
      }

      await refreshAutomationTasks(result.access_token, nextPosition || undefined);
      await refreshErpScopes(result.access_token, nextRole);
      await refreshErpDashboardOverview(result.access_token, erpDashboardMarket, erpDashboardDateRange, erpDashboardStore);
      await refreshRunRecords(result.access_token);
      await refreshEffectAnalytics(result.access_token, defaultEffectAnalyticsFilters(nextRole, nextPosition));
      await refreshAutomationFlows(result.access_token, defaultAutomationFlowFilters(nextRole, nextPosition));

      setIsLoginModalOpen(false);
    } catch (error) {
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

  function clearAuthenticatedState(options: { publicHome?: boolean } = {}) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    localStorage.removeItem("position");
    setToken("");
    setRole("employee");
    setPosition(null);
    setLastForbiddenPath("");
    setMessages([]);
    setApprovals([]);
    setRefunds([]);
    setAuditLogs([]);
    setRunRecords([]);
    setRunRecordDetail(null);
    setIsRunRecordDetailOpen(false);
    setEffectAnalytics(null);
    setEffectAnalyticsFilters({ dateRange: "30d", position: "all" });
    setAutomationFlows([]);
    setAutomationFlowDetail(null);
    setIsAutomationFlowDetailOpen(false);
    setAutomationFlowFilters({ position: "all", category: "" });
    setConnectors([]);
    setConnectorSummary(null);
    setConnectorDetail(null);
    setIsConnectorDetailOpen(false);
    setUsers([]);
    setAutomationTasks([]);
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

  function handleLogout() {
    clearAuthenticatedState();
    setStatusMessage("已退出登录");
    message.success("已退出登录");
  }

  async function refreshAdminData(activeToken = token) {
    if (!activeToken) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      const [approvalResult, refundResult, auditResult, userResult] = await Promise.all([
        listApprovals(activeToken),
        listRefunds(activeToken),
        listAuditLogs(activeToken, {
          action: auditActionFilter,
          resource_type: auditResourceFilter,
          position: auditPositionFilter,
          limit: 80,
        }),
        listUsers(activeToken),
      ]);

      setApprovals(approvalResult.items.map(mapApproval));
      setRefunds(refundResult.items.map(mapRefund));
      setAuditLogs(auditResult.items.map(mapAuditLog));
      setUsers(userResult.items.map(mapUser));
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

  async function refreshAuditLogs(activeToken = token) {
    if (!activeToken) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      const result = await listAuditLogs(activeToken, {
        action: auditActionFilter,
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
      limit: 80,
    };
  }

  async function refreshRunRecords(activeToken = token, filters = runRecordFilters) {
    if (!activeToken) {
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
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
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
    if (!activeToken) {
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

  async function refreshAutomationFlows(activeToken = token, filters = automationFlowFilters) {
    if (!activeToken) {
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
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
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
              }
            : item,
        ),
      );
      setStatusMessage(`${result.position_label}任务生成完成`);
      message.success("生成完成");
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

  async function handleTransformFinanceExcel() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!financeExcelFile) {
      setStatusMessage("请选择 Excel 文件");
      message.warning("请选择 Excel 文件");
      return;
    }

    setIsTransformingFinanceExcel(true);
    setStatusMessage("正在生成财务 Excel");

    try {
      const result = await transformFinanceExcel(
        token,
        financeExcelFile,
        financeExcelInstruction,
      );
      downloadBlob(result.blob, result.filename);
      setStatusMessage("财务 Excel 已生成并开始下载");
      message.success("财务 Excel 已生成");
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

    const threadId = threadInput.trim() || `thread-${Date.now()}`;
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      threadId,
      role: "user",
      content: messageText,
      createdAt: "刚刚",
    };
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      threadId,
      role: "assistant",
      content: "",
      createdAt: "正在生成",
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setMessageInput("");
    setIsChatLoading(true);
    setStatusMessage("正在流式生成回答");

    try {
      await sendChatStream(token, messageText, threadId, {
        onStart: (payload) => {
          const nextThreadId = payload.thread_id || threadId;
          setThreadInput(nextThreadId);
          setThreadFilter(nextThreadId);
        },
        onNode: (payload) => {
          if (payload.node) {
            setStatusMessage(`正在执行节点：${payload.node}`);
          }
        },
        onContent: (payload) => {
          const chunk = payload.content || "";
          const nextThreadId = payload.thread_id || threadId;

          setThreadInput(nextThreadId);
          setThreadFilter(nextThreadId);
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
          const finalThreadId = payload.thread_id || threadId;

          setThreadInput(finalThreadId);
          setThreadFilter(finalThreadId);
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
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      await reviewApprovalApi(token, id, approved);
      await refreshAdminData();
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

  async function handleUploadDocument() {
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
      await uploadDocument(token, documentFile, documentVisibility, documentDepartment);
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

  async function loadThreadMessages() {
    const threadId = threadFilter.trim();

    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!threadId) {
      setStatusMessage("请输入 Thread ID");
      message.warning("请输入 Thread ID");
      return;
    }

    try {
      const result = await getThreadMessages(token, threadId);

      setMessages(result.messages.map(mapThreadMessage));
      setThreadSummary(String(result.summary.summary || ""));
      setThreadStateText(JSON.stringify(result.state, null, 2));
      setStatusMessage("会话已加载");
      message.success("会话已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "查询会话失败";
      setStatusMessage(text);
      message.error(text);
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
            onCancel={() => setIsLoginModalOpen(false)}
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
            title="Company RAG Agent"
            logo={<SafetyCertificateOutlined />}
            route={route}
            location={{ pathname: currentPath }}
            layout="mix"
            splitMenus={false}
            siderWidth={224}
            menuItemRender={(item, dom) => (
              <button
                className="menuButton"
                type="button"
                onClick={() => {
                  const matched = flatVisibleNavItems.find((nav) => nav.path === item.path);
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
                    approvals={approvals}
                    refunds={refunds}
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
                    onNavigate={navigateToView}
                  />
                )}
                {safeActiveView === "run_records" && (
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
                {safeActiveView === "effect_analytics" && (
                  <EffectAnalyticsPanel
                    role={role}
                    analytics={effectAnalytics}
                    filters={effectAnalyticsFilters}
                    setFilters={setEffectAnalyticsFilters}
                    loading={isEffectAnalyticsLoading}
                    refreshAnalytics={() => refreshEffectAnalytics()}
                  />
                )}
                {safeActiveView === "automation_flows" && (
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
                {isAutomationView(safeActiveView) && (
                  <AutomationPanel
                    role={role}
                    position={position}
                    selectedPosition={automationPositionFromView(safeActiveView, role, position)}
                    tasks={automationTasks}
                    financeExcelFile={financeExcelFile}
                    setFinanceExcelFile={setFinanceExcelFile}
                    financeExcelInstruction={financeExcelInstruction}
                    setFinanceExcelInstruction={setFinanceExcelInstruction}
                    isTransformingFinanceExcel={isTransformingFinanceExcel}
                    onGenerate={handleGenerateAutomation}
                    onTransformFinanceExcel={handleTransformFinanceExcel}
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
                    threadInput={threadInput}
                    setThreadInput={setThreadInput}
                    sendMessage={sendMessage}
                    messages={messages}
                    isLoading={isChatLoading}
                    position={position}
                  />
                )}
                {safeActiveView === "documents" && role === "admin" && (
                  <DocumentsPanel
                    file={documentFile}
                    setFile={setDocumentFile}
                    visibility={documentVisibility}
                    setVisibility={setDocumentVisibility}
                    department={documentDepartment}
                    setDepartment={setDocumentDepartment}
                    uploadDocument={handleUploadDocument}
                    role={role}
                    isUploading={isUploading}
                  />
                )}
                {safeActiveView === "users" && role === "admin" && (
                  <UsersPanel
                    users={users}
                    newUser={newUser}
                    setNewUser={setNewUser}
                    createUser={handleCreateUser}
                    refreshUsers={() => refreshUsers()}
                    isCreating={isCreatingUser}
                  />
                )}
                {safeActiveView === "approvals" && role === "admin" && (
                  <ApprovalsPanel approvals={approvals} reviewApproval={reviewApproval} role={role} />
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
                    threadFilter={threadFilter}
                    setThreadFilter={setThreadFilter}
                    loadThreadMessages={loadThreadMessages}
                    messages={messages.filter((item) => item.threadId === threadFilter)}
                    summary={threadSummary}
                    stateText={threadStateText}
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
              onCancel={() => setIsLoginModalOpen(false)}
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
            <AutomationFlowDetailModal
              open={isAutomationFlowDetailOpen}
              loading={isAutomationFlowDetailLoading}
              detail={automationFlowDetail}
              onClose={() => setIsAutomationFlowDetailOpen(false)}
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
            {props.username.slice(0, 1).toUpperCase()}
          </Avatar>
          <Text>{props.username}</Text>
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
      title="登录 Company RAG Agent"
      open={props.open}
      okText="登录"
      cancelText="取消"
      centered
      onOk={props.onLogin}
      onCancel={props.onCancel}
    >
      <Form layout="vertical" className="loginModalForm">
        <Form.Item label="用户名">
          <Input
            value={props.username}
            onChange={(event) => props.setUsername(event.target.value)}
            onPressEnter={props.onLogin}
          />
        </Form.Item>
        <Form.Item label="密码">
          <Input.Password
            value={props.password}
            onChange={(event) => props.setPassword(event.target.value)}
            onPressEnter={props.onLogin}
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
  approvals,
  refunds,
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
  approvals: Approval[];
  refunds: Refund[];
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

      <ProCard
        title={role === "admin" ? "管理员快捷入口" : "岗位快捷入口"}
        subTitle={role === "admin" ? "常用后台维护和诊断" : position ? `${positionLabel(position)}常用功能` : "未绑定岗位"}
        bordered
      >
        <Row gutter={[12, 12]}>
          {shortcuts.map((item) => (
            <Col xs={24} md={12} xl={8} key={item.view} className="dashboardShortcutCol">
              <Card size="small" className="contextCard dashboardShortcutCard">
                <div className="dashboardShortcutBody">
                  <Space className="dashboardShortcutTitle">
                    {item.icon}
                    <Text strong>{item.title}</Text>
                  </Space>
                  <Paragraph type="secondary" className="dashboardShortcutDescription">
                    {item.description}
                  </Paragraph>
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

      <ProCard
        title={role === "admin" ? "平台数据概览" : "岗位数据概览"}
        subTitle={erpOverview?.message || "从 ERP 权限范围内加载关键数据"}
        bordered
      >
        {erpOverview ? (
          <Space direction="vertical" size={16} className="pageStack">
            <div className="dashboardOverviewToolbar">
              <Space size={8} wrap>
                <Text strong>{erpOverview.title}</Text>
                <Tag color="blue">{erpOverview.market_label}</Tag>
                <Tag color="geekblue">{erpOverview.store_label}</Tag>
                <Tag color="cyan">{erpOverview.date_range_label}</Tag>
              </Space>
              <Space size={8} wrap>
                <Segmented<DashboardMarket>
                  size="small"
                  value={erpDashboardMarket}
                  options={dashboardMarketOptions}
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
            <StatisticCard.Group direction="row" className="dashboardMetricGroup">
              {erpOverview.metrics.map((item) => (
                <StatisticCard
                  key={item.title}
                  statistic={{
                    title: item.title,
                    value: item.value,
                    suffix: item.suffix,
                    status: metricStatus(item.status),
                    description: item.description,
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
                      className="contextCard dashboardOverviewCard"
                      title={
                        <Space size={6}>
                          <Text>{section.title}</Text>
                          <Tag color={section.ok ? "green" : "gold"}>{section.status}</Tag>
                        </Space>
                      }
                    >
                      <div className="dashboardOverviewBody">
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
                        <div className="dashboardRecordList">
                          {section.items.length ? (
                            section.items.slice(0, 3).map((item, index) => (
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
                                <Text type="secondary" className="compactRecordSecondary">
                                  {overviewSecondaryText(item)}
                                </Text>
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

      {role === "admin" ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={14} className="dashboardTableCol">
            <ProCard title="待处理事项" bordered className="dashboardTableCard">
              <Table<Approval>
                rowKey="id"
                size="middle"
                pagination={false}
                dataSource={approvals.slice(0, 5)}
                locale={{ emptyText: <Empty description="暂无待审批数据" /> }}
                columns={[
                  { title: "订单", dataIndex: "orderNo" },
                  { title: "金额", dataIndex: "amount" },
                  { title: "状态", dataIndex: "status", render: (value) => <StatusTag value={String(value)} /> },
                  { title: "创建时间", dataIndex: "createdAt" },
                ]}
              />
            </ProCard>
          </Col>
          <Col xs={24} xl={10} className="dashboardTableCol">
            <ProCard title="最近退款" bordered className="dashboardTableCard">
              <Table<Refund>
                rowKey="id"
                size="middle"
                pagination={false}
                dataSource={refunds.slice(0, 5)}
                locale={{ emptyText: <Empty description="暂无退款流水" /> }}
                columns={[
                  { title: "订单", dataIndex: "orderNo" },
                  { title: "金额", dataIndex: "amount" },
                  { title: "状态", dataIndex: "status", render: (value) => <StatusTag value={String(value)} /> },
                ]}
              />
            </ProCard>
          </Col>
        </Row>
      ) : (
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
      )}
    </Space>
  );
}

function ChatPanel(props: {
  messageInput: string;
  setMessageInput: (value: string) => void;
  threadInput: string;
  setThreadInput: (value: string) => void;
  sendMessage: () => void;
  messages: ChatMessage[];
  isLoading: boolean;
  position: Position | null;
}) {
  return (
    <ProCard bordered className="chatWorkspace" bodyStyle={{ padding: 0, height: "100%" }}>
      <div className="chatMessagesPane">
        <MessageList messages={props.messages} />
      </div>

      <div className="chatComposerWrap">
        <div className="chatThreadBar">
          <Text type="secondary">会话 ID</Text>
          <Input
            size="small"
            value={props.threadInput}
            onChange={(event) => props.setThreadInput(event.target.value)}
          />
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

function AiAppsPanel({
  role,
  position,
  tasks,
  erpResources,
  pendingApprovals,
  chatMessageCount,
  onNavigate,
}: {
  role: Role;
  position: Position | null;
  tasks: AutomationTaskRecord[];
  erpResources: ErpResourceItem[];
  pendingApprovals: number;
  chatMessageCount: number;
  onNavigate: (view: View) => void;
}) {
  const apps = aiAppsForUser(role, position, tasks);
  const enabledApps = apps.filter((item) => item.status === "enabled").length;
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
          <Col xs={24} md={12} xl={6}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">可见应用</Text>
              <Title level={3}>{apps.length}</Title>
              <Text type="secondary">按当前账号权限过滤</Text>
            </Card>
          </Col>
          <Col xs={24} md={12} xl={6}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">已启用</Text>
              <Title level={3}>{enabledApps}</Title>
              <Text type="secondary">现有功能入口可直接使用</Text>
            </Card>
          </Col>
          <Col xs={24} md={12} xl={6}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">ERP 资源</Text>
              <Title level={3}>{erpResources.length}</Title>
              <Text type="secondary">来自真实岗位 ERP scope</Text>
            </Card>
          </Col>
          <Col xs={24} md={12} xl={6}>
            <Card size="small" className="aiAppMetricCard">
              <Text type="secondary">待处理审批</Text>
              <Title level={3}>{pendingApprovals}</Title>
              <Text type="secondary">管理员可进入审批中心处理</Text>
            </Card>
          </Col>
        </Row>
      </ProCard>

      <ProCard
        title="岗位应用目录"
        subTitle="执行数据已接入运行记录页面；应用目录保留为岗位能力入口"
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
                        <Text strong className="aiAppTitle">{app.name}</Text>
                      </Space>
                      <Tag color={app.status === "enabled" ? "green" : "gold"}>
                        {app.status === "enabled" ? "已启用" : "规划中"}
                      </Tag>
                    </div>
                    <Paragraph type="secondary" className="aiAppDescription">
                      {app.description}
                    </Paragraph>
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
        <Text type="secondary">当前浏览器会话已加载 {chatMessageCount} 条聊天消息，可在客服对话或会话详情继续查看。</Text>
      ) : null}
    </Space>
  );
}

function AutomationPanel({
  role,
  position,
  selectedPosition,
  tasks,
  financeExcelFile,
  setFinanceExcelFile,
  financeExcelInstruction,
  setFinanceExcelInstruction,
  isTransformingFinanceExcel,
  onGenerate,
  onTransformFinanceExcel,
  onInputChange,
  loadingTaskId,
}: {
  role: Role;
  position: Position | null;
  selectedPosition: Position | null;
  tasks: AutomationTaskRecord[];
  financeExcelFile: File | null;
  setFinanceExcelFile: (value: File | null) => void;
  financeExcelInstruction: string;
  setFinanceExcelInstruction: (value: string) => void;
  isTransformingFinanceExcel: boolean;
  onGenerate: (taskId: string, inputText: string) => void;
  onTransformFinanceExcel: () => void;
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

  return (
    <Space direction="vertical" size={16} className="pageStack">
      {positions.map((item) => {
        const config = positionConfigs[item];
        const visibleTasks = tasks.filter((task) => task.position === item);
        const financeFileList: UploadFile[] = financeExcelFile
          ? [
              {
                uid: financeExcelFile.name,
                name: financeExcelFile.name,
                status: "done",
              },
            ]
          : [];

        return (
          <ProCard
            key={item}
            title={`${config.label} AI 自动化`}
            subTitle={role === "admin" ? `管理员预览 ${config.label} 岗位能力` : `ERP 权限范围：${config.erpScopes.join("、")}`}
            bordered
          >
            <Row gutter={[12, 12]}>
              {visibleTasks.map((task) => (
                <Col xs={24} xl={12} key={task.task_id} className="automationTaskCol">
                  <Card size="small" className="contextCard automationTaskCard">
                    <div className="automationTaskBody">
                      <Text strong className="automationTaskTitle">{task.label}</Text>
                      <Paragraph type="secondary" className="automationTaskDescription">
                        {task.output_format}
                      </Paragraph>
                      <Input.TextArea
                        className="automationTaskInput"
                        value={task.inputText}
                        placeholder={task.placeholder}
                        autoSize={false}
                        rows={3}
                        onChange={(event) => onInputChange(task.task_id, event.target.value)}
                      />
                      <div className="automationTaskFooter">
                        <Button
                          type="primary"
                          loading={loadingTaskId === task.task_id}
                          onClick={() => onGenerate(task.task_id, task.inputText)}
                        >
                          生成
                        </Button>
                      </div>
                      {task.output ? (
                        <Card size="small" title="生成结果" className="automationTaskResult">
                          <Paragraph style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>
                            {task.output}
                          </Paragraph>
                        </Card>
                      ) : null}
                    </div>
                  </Card>
                </Col>
              ))}
              {item === "finance" ? (
                <Col xs={24} className="automationTaskCol">
                  <Card size="small" className="contextCard automationTaskCard financeUploadTaskCard">
                    <div className="financeUploadTaskBody">
                      <Text strong className="automationTaskTitle">上传 Excel 生成新表</Text>
                      <Paragraph type="secondary" className="automationTaskDescription">
                        上传财务 Excel，系统会生成处理摘要、数值汇总、AI 建议和整理后的数据 Sheet。
                      </Paragraph>
                      <div className="financeUploadControls">
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
                          <p className="uploadTitle">选择财务 Excel</p>
                          <p className="uploadHint">支持 .xlsx / .xls，生成后自动下载新文件</p>
                        </Upload.Dragger>
                        <div className="financeUploadActionPane">
                          <Input.TextArea
                            className="financeUploadInstruction"
                            value={financeExcelInstruction}
                            placeholder="输入财务整理要求，例如：按部门统计工资、汇总各店铺销售额、标记负数和空值。"
                            autoSize={false}
                            rows={3}
                            onChange={(event) => setFinanceExcelInstruction(event.target.value)}
                          />
                          <div className="automationTaskFooter">
                            <Button
                              type="primary"
                              icon={<CloudUploadOutlined />}
                              loading={isTransformingFinanceExcel}
                              disabled={!financeExcelFile || isTransformingFinanceExcel}
                              onClick={onTransformFinanceExcel}
                            >
                              生成并下载 Excel
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                </Col>
              ) : null}
            </Row>
          </ProCard>
        );
      })}
    </Space>
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

  const queryPanel = (
    <Space direction="vertical" size={16} className="pageStack">
      <ProCard
        title="ERP 连接查询"
        subTitle={role === "admin" ? "管理员可查看全部岗位资源" : position ? `${positionLabel(position)}岗位` : "未绑定岗位"}
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
                    <Form.Item label="Filters JSON">
                      <TextArea
                        value={filtersText}
                        rows={4}
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
          <Space direction="vertical" size={12} className="pageStack">
            <Space size={[8, 8]} wrap>
              <Tag color={result.ok ? "green" : "gold"}>{result.status}</Tag>
              <Tag>{result.provider_label}</Tag>
              <Tag>{result.resource_label}</Tag>
              <Tag>{result.items.length} 条</Tag>
            </Space>
            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              {result.message}
            </Paragraph>
            <pre className="statePre">{JSON.stringify(result, null, 2)}</pre>
          </Space>
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

function DocumentsPanel(props: {
  file: File | null;
  setFile: (value: File | null) => void;
  visibility: Role;
  setVisibility: (value: Role) => void;
  department: string;
  setDepartment: (value: string) => void;
  uploadDocument: () => void;
  role: Role;
  isUploading: boolean;
}) {
  const disabled = props.role !== "admin" || props.isUploading;
  const uploadFileList: UploadFile[] = props.file
    ? [
        {
          uid: props.file.name,
          name: props.file.name,
          status: "done",
        },
      ]
    : [];

  return (
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
            <Button
              type="primary"
              block
              icon={<CloudUploadOutlined />}
              disabled={disabled}
              loading={props.isUploading}
              onClick={props.uploadDocument}
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
}

function UsersPanel(props: {
  users: UserRecord[];
  newUser: NewUserForm;
  setNewUser: (value: NewUserForm) => void;
  createUser: () => void;
  refreshUsers: () => void;
  isCreating: boolean;
}) {
  const selectedPosition = props.newUser.position || "customer_service";

  function patchNewUser(patch: Partial<NewUserForm>) {
    props.setNewUser({
      ...props.newUser,
      ...patch,
    });
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9} className="splitCardCol">
        <ProCard title="管理员创建用户" bordered className="splitCard">
          <Form layout="vertical">
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
            <Space>
              <Button type="primary" loading={props.isCreating} onClick={props.createUser}>
                创建用户
              </Button>
              <Button icon={<ReloadOutlined />} onClick={props.refreshUsers}>
                刷新
              </Button>
            </Space>
          </Form>
        </ProCard>
      </Col>
      <Col xs={24} xl={15} className="splitCardCol">
        <ProCard title="用户与岗位权限" bordered className="splitCard">
          <Table<UserRecord>
            rowKey="id"
            dataSource={props.users}
            locale={{ emptyText: <Empty description="暂无用户数据" /> }}
            columns={[
              { title: "用户名", dataIndex: "username", width: 140 },
              { title: "角色", dataIndex: "role", width: 110, render: (value) => <Tag>{roleLabel(value as Role)}</Tag> },
              {
                title: "岗位",
                dataIndex: "position",
                width: 110,
                render: (value) => value ? <Tag color="purple">{positionLabel(value as Position)}</Tag> : "-",
              },
              { title: "部门", dataIndex: "department", width: 120 },
              {
                title: "AI 能力",
                dataIndex: "capabilities",
                render: (value: string[]) => (
                  <Space size={[4, 4]} wrap>
                    {value.length ? value.map((item) => <Tag key={item}>{item}</Tag>) : <Text type="secondary">-</Text>}
                  </Space>
                ),
              },
              { title: "创建时间", dataIndex: "createdAt", width: 150 },
            ]}
          />
        </ProCard>
      </Col>
    </Row>
  );
}

function ApprovalsPanel({
  approvals,
  reviewApproval,
  role,
}: {
  approvals: Approval[];
  reviewApproval: (id: string, approved: boolean) => void;
  role: Role;
}) {
  return (
    <ProCard title="审批列表" bordered>
      <Table<Approval>
        rowKey="id"
        dataSource={approvals}
        locale={{ emptyText: <Empty description="暂无审批记录，发送退款请求后会产生审批" /> }}
        columns={[
          { title: "审批 ID", dataIndex: "id", ellipsis: true },
          { title: "订单", dataIndex: "orderNo", width: 140 },
          { title: "金额", dataIndex: "amount", width: 140 },
          { title: "状态", dataIndex: "status", width: 120, render: (value) => <StatusTag value={String(value)} /> },
          { title: "原因", dataIndex: "reason", ellipsis: true },
          { title: "时间", dataIndex: "createdAt", width: 150 },
          {
            title: "操作",
            width: 150,
            render: (_, item) => (
              <Space>
                <Button
                  size="small"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  disabled={role !== "admin" || item.status !== "pending"}
                  onClick={() => reviewApproval(item.id, true)}
                >
                  通过
                </Button>
                <Button
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  disabled={role !== "admin" || item.status !== "pending"}
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
        columns={[
          { title: "订单", dataIndex: "orderNo" },
          { title: "金额", dataIndex: "amount" },
          { title: "状态", dataIndex: "status", render: (value) => <StatusTag value={String(value)} /> },
          { title: "时间", dataIndex: "createdAt" },
          { title: "审批 ID", dataIndex: "approvalId", ellipsis: true },
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
            style={{ width: 160 }}
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
        dataSource={logs}
        locale={{ emptyText: <Empty description="暂无审计日志" /> }}
        columns={[
          { title: "动作", dataIndex: "action" },
          { title: "资源", dataIndex: "resourceType" },
          { title: "操作者", dataIndex: "actor" },
          {
            title: "岗位",
            dataIndex: "position",
            width: 100,
            render: (value) => isPosition(value) ? <Tag color="purple">{positionLabel(value)}</Tag> : "-",
          },
          { title: "时间", dataIndex: "createdAt" },
          { title: "资源 ID", dataIndex: "resourceId", ellipsis: true },
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
          <Button size="small" type="primary" icon={<SearchOutlined />} onClick={refreshRecords} loading={loading}>
            查询
          </Button>
        </div>

        <Table<RunRecordItem>
          rowKey="id"
          loading={loading}
          dataSource={records}
          className="runRecordTable"
          scroll={{ x: 1080 }}
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
        <Space direction="vertical" size={14} className="pageStack">
          <div className="runRecordDetailGrid">
            <RunRecordDetailItem label="状态" value={<StatusTag value={detail.run.status} />} />
            <RunRecordDetailItem label="类型" value={detail.run.run_type} mono />
            <RunRecordDetailItem label="应用 ID" value={detail.run.app_id} mono />
            <RunRecordDetailItem label="入口" value={detail.run.entrypoint} mono />
            <RunRecordDetailItem label="用户" value={detail.run.username || "-"} />
            <RunRecordDetailItem label="岗位" value={isPosition(detail.run.position) ? positionLabel(detail.run.position) : "管理员"} />
            <RunRecordDetailItem label="资源" value={`${detail.run.resource_type || "-"} / ${detail.run.resource_id || "-"}`} mono />
            <RunRecordDetailItem label="耗时" value={formatDuration(detail.run.duration_ms)} />
            <RunRecordDetailItem label="开始时间" value={formatTime(detail.run.started_at)} />
            <RunRecordDetailItem label="结束时间" value={formatTime(detail.run.finished_at)} />
          </div>

          <ProCard title="输入输出摘要" bordered size="small">
            <Row gutter={[12, 12]}>
              <Col xs={24} md={12}>
                <Text type="secondary">输入摘要</Text>
                <Paragraph className="runRecordDetailPreview">{detail.run.input_preview || "-"}</Paragraph>
              </Col>
              <Col xs={24} md={12}>
                <Text type="secondary">输出/错误摘要</Text>
                <Paragraph className="runRecordDetailPreview">
                  {detail.run.error_message || detail.run.output_preview || "-"}
                </Paragraph>
              </Col>
            </Row>
          </ProCard>

          <ProCard title="执行步骤" bordered size="small">
            <Table
              rowKey="id"
              dataSource={detail.steps}
              pagination={false}
              scroll={{ x: 760 }}
              locale={{ emptyText: <Empty description="暂无步骤" /> }}
              columns={[
                { title: "序号", dataIndex: "step_order", width: 70 },
                { title: "步骤", dataIndex: "step_name", width: 180, render: (value) => <Text className="runRecordMono">{String(value)}</Text> },
                { title: "状态", dataIndex: "status", width: 92, render: (value) => <StatusTag value={String(value)} /> },
                { title: "Provider", dataIndex: "provider", width: 120 },
                { title: "资源", dataIndex: "resource_id", width: 160, render: (value) => <Text className="runRecordMono">{value || "-"}</Text> },
                { title: "摘要", dataIndex: "output_preview", render: (value, record) => <Text className="runRecordPreview">{record.error_message || value || record.input_preview || "-"}</Text> },
                { title: "耗时", dataIndex: "duration_ms", width: 90, render: (value) => formatDuration(value) },
              ]}
            />
          </ProCard>

          <ProCard title="产物与引用" bordered size="small">
            <Table
              rowKey="id"
              dataSource={detail.artifacts}
              pagination={false}
              scroll={{ x: 680 }}
              locale={{ emptyText: <Empty description="暂无产物引用" /> }}
              columns={[
                { title: "类型", dataIndex: "artifact_type", width: 130 },
                { title: "名称", dataIndex: "name", render: (value) => <Text className="runRecordText">{String(value)}</Text> },
                { title: "引用", dataIndex: "external_ref", width: 180, render: (value) => <Text className="runRecordMono">{value || "-"}</Text> },
                { title: "大小", dataIndex: "size_bytes", width: 100, render: (value) => formatBytes(value) },
              ]}
            />
          </ProCard>
        </Space>
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

function AutomationFlowDetailModal({
  open,
  loading,
  detail,
  onClose,
}: {
  open: boolean;
  loading: boolean;
  detail: AutomationFlowDetailResponse | null;
  onClose: () => void;
}) {
  const flow = detail?.item || null;

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
        <Space direction="vertical" size={14} className="pageStack">
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

          <Row gutter={[12, 12]}>
            <Col xs={24} md={12}>
              <ProCard title="输入 Schema" bordered size="small">
                <SchemaTable items={flow.input_schema} />
              </ProCard>
            </Col>
            <Col xs={24} md={12}>
              <ProCard title="输出 Schema" bordered size="small">
                <SchemaTable items={flow.output_schema} />
              </ProCard>
            </Col>
          </Row>

          <ProCard title="Prompt 与模型" bordered size="small">
            <Row gutter={[12, 12]}>
              <Col xs={24} md={12}>
                <Text type="secondary">Prompt 摘要</Text>
                <Paragraph className="flowConfigDetailPreview">{flow.prompt_summary || "-"}</Paragraph>
              </Col>
              <Col xs={24} md={12}>
                <Text type="secondary">模板预览</Text>
                <pre className="flowConfigPre">{flow.prompt_template_preview || "无独立 Prompt。"}</pre>
              </Col>
              <Col xs={24}>
                <Space size={[6, 6]} wrap>
                  {Object.entries(flow.model_config).map(([key, value]) => (
                    <Tag key={key} color={key === "secrets_visible" ? "green" : "blue"}>
                      {key}: {textFromUnknown(value)}
                    </Tag>
                  ))}
                </Space>
              </Col>
            </Row>
          </ProCard>

          <ProCard title="权限、工具与 ERP 资源" bordered size="small">
            <Row gutter={[12, 12]}>
              <Col xs={24} md={8}>
                <Text type="secondary">允许工具</Text>
                <Space size={[6, 6]} wrap className="flowConfigTagBlock">
                  {flow.allowed_tools.map((item) => (
                    <Tag color="blue" key={item}>{item}</Tag>
                  ))}
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Text type="secondary">审批策略</Text>
                <Paragraph className="flowConfigDetailPreview compact">{flow.approval_policy}</Paragraph>
              </Col>
              <Col xs={24} md={8}>
                <Text type="secondary">失败策略</Text>
                <Paragraph className="flowConfigDetailPreview compact">{flow.failure_strategy}</Paragraph>
              </Col>
              <Col xs={24}>
                <Text type="secondary">允许资源</Text>
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
              </Col>
              <Col xs={24}>
                <Text type="secondary">权限规则</Text>
                <div className="flowConfigRuleList">
                  {flow.permission_rules.map((item) => (
                    <div className="flowConfigRuleItem" key={item}>{item}</div>
                  ))}
                </div>
              </Col>
            </Row>
          </ProCard>

          <ProCard title="执行步骤" bordered size="small">
            <Table
              rowKey="id"
              dataSource={flow.steps}
              pagination={false}
              scroll={{ x: 680 }}
              locale={{ emptyText: <Empty description="暂无步骤" /> }}
              columns={[
                { title: "步骤 ID", dataIndex: "id", width: 190, render: (value) => <Text className="flowConfigMono">{String(value)}</Text> },
                { title: "步骤名称", dataIndex: "name", width: 240, render: (value) => <Text className="flowConfigText">{String(value)}</Text> },
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
          </ProCard>
        </Space>
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
                              <Text strong className="connectorTitle">{connector.label}</Text>
                            </Space>
                            <ConnectorStatusTag status={connector.status} />
                          </div>
                          <Paragraph type="secondary" className="connectorDescription">
                            {connector.description}
                          </Paragraph>
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
      width={980}
    >
      {loading ? (
        <Empty description="正在加载连接器详情" />
      ) : connector ? (
        <Space direction="vertical" size={14} className="pageStack">
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

          <ProCard title="健康信息" bordered size="small">
            <Paragraph className="connectorDetailPreview">{connector.health_message}</Paragraph>
            <Space size={[6, 6]} wrap>
              {connector.capabilities.map((item) => (
                <Tag color="blue" key={item}>{item}</Tag>
              ))}
              {connector.position_scope_labels.map((item) => (
                <Tag color="purple" key={item}>{item}</Tag>
              ))}
            </Space>
          </ProCard>

          <Row gutter={[12, 12]}>
            <Col xs={24} md={12}>
              <ProCard title="配置项" bordered size="small">
                <ConnectorConfigTable fields={connector.config_fields} />
              </ProCard>
            </Col>
            <Col xs={24} md={12}>
              <ProCard title="下一步" bordered size="small">
                <div className="connectorRuleList">
                  {connector.next_steps.map((item) => (
                    <div className="connectorRuleItem" key={item}>{item}</div>
                  ))}
                </div>
              </ProCard>
            </Col>
          </Row>

          <ProCard title="资源映射" bordered size="small">
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
          </ProCard>
        </Space>
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
      width={760}
    >
      {loading ? (
        <Empty description="正在加载 ERP 记录详情" />
      ) : detail ? (
        <Space direction="vertical" size={12} className="pageStack">
          <Space size={[8, 8]} wrap>
            <Tag color={detail.ok ? "green" : "gold"}>{detail.ok ? "已找到" : "未找到"}</Tag>
            <Tag>{detail.provider_label}</Tag>
            <Tag>{detail.provider_resource}</Tag>
            <Tag>{detail.record_id}</Tag>
          </Space>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {detail.message}
          </Paragraph>
          {rows.length ? (
            <Table
              rowKey="field"
              size="small"
              pagination={false}
              dataSource={rows.map(([field, value]) => ({
                field,
                value: textFromUnknown(value),
              }))}
              columns={[
                { title: "字段", dataIndex: "field", width: 190 },
                { title: "值", dataIndex: "value" },
              ]}
            />
          ) : (
            <Empty description="暂无详情字段" />
          )}
        </Space>
      ) : (
        <Empty description="暂无 ERP 记录详情" />
      )}
    </Modal>
  );
}

function ThreadsPanel({
  threadFilter,
  setThreadFilter,
  loadThreadMessages,
  messages,
  summary,
  stateText,
}: {
  threadFilter: string;
  setThreadFilter: (value: string) => void;
  loadThreadMessages: () => void;
  messages: ChatMessage[];
  summary: string;
  stateText: string;
}) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9} className="splitCardCol">
        <ProCard title="查询会话" bordered className="splitCard">
          <Form layout="vertical">
            <Form.Item label="Thread ID">
              <Input value={threadFilter} onChange={(event) => setThreadFilter(event.target.value)} />
            </Form.Item>
            <Button type="primary" block icon={<SearchOutlined />} onClick={loadThreadMessages}>
              查询后端会话
            </Button>
          </Form>

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
        </ProCard>
      </Col>
      <Col xs={24} xl={15} className="splitCardCol">
        <ProCard title="消息记录" bordered className="splitCard">
          <MessageList messages={messages} />
        </ProCard>
      </Col>
    </Row>
  );
}

function MessageList({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="chatEmptyState">
        <Empty description="暂无消息，开始一次客服对话" />
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
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    enabled: "green",
    published: "green",
    pending: "gold",
    approved: "green",
    rejected: "red",
    succeeded: "green",
    failed: "red",
    blocked: "volcano",
    running: "blue",
  };

  return <Tag color={colorMap[value] || "default"}>{labelForBadge(value)}</Tag>;
}

function defaultAutomationFlowFilters(role: Role, position: Position | null): AutomationFlowFilterState {
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

function formatAmount(value: number) {
  return Number(value).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
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
        view: "automation_flows",
        icon: <RobotOutlined />,
      },
      {
        title: "运营 ERP 查询",
        description: "查询商品、价格、销售订单和销售发票摘要。",
        view: "erp",
        icon: <ApiOutlined />,
      },
      {
        title: "AI 对话",
        description: "在运营权限内询问订单、商品和平台资料。",
        view: "chat",
        icon: <MessageOutlined />,
      },
    ];
  }

  if (position === "finance") {
    return [
      {
        title: "财务 Excel 生成",
        description: "上传 Excel，生成处理摘要、数值汇总和 AI 建议。",
        view: "automation_flows",
        icon: <CloudUploadOutlined />,
      },
      {
        title: "财务 ERP 查询",
        description: "查询总账分录、收付款、工资单和发票。",
        view: "erp",
        icon: <ApiOutlined />,
      },
      {
        title: "财务 AI 对话",
        description: "在财务权限内分析报表、工资和发票问题。",
        view: "chat",
        icon: <MessageOutlined />,
      },
    ];
  }

  if (position === "customer_service") {
    return [
      {
        title: "客服 AI 对话",
        description: "处理物流、售后、退款话术和多语言回复。",
        view: "chat",
        icon: <MessageOutlined />,
      },
      {
        title: "客服 ERP 查询",
        description: "查询客户资料、销售订单、物流出库单和售后工单。",
        view: "erp",
        icon: <ApiOutlined />,
      },
      {
        title: "客服自动化",
        description: "生成智能客服回复、自动回复和退款售后话术。",
        view: "automation_flows",
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
        entryView: automationViewForPosition(item),
        entryLabel: "打开自动化",
      }));

    apps.push(...taskApps);

    if (item === "finance") {
      apps.push({
        id: "finance-excel-transform",
        name: "财务 Excel 生成",
        description: "上传真实 Excel 文件，生成处理摘要、数值汇总、AI 建议和整理后的新工作簿。",
        category: "文件自动化",
        position: item,
        positionLabel: config.label,
        status: "enabled",
        dataSources: ["Excel 文件", "财务规则", "大模型"],
        owner: config.department,
        entryView: "automation_finance",
        entryLabel: "上传 Excel",
      });
    }

    apps.push({
      id: `${item}-erp-query`,
      name: `${config.label} ERP 查询`,
      description: `按${config.label}岗位权限查询 ERP 资源，并在 AI 对话和概览中引用真实记录。`,
      category: "数据查询",
      position: item,
      positionLabel: config.label,
      status: "enabled",
      dataSources: config.erpScopes.slice(0, 4),
      owner: config.department,
      entryView: "erp_query",
      entryLabel: "查询 ERP",
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

function automationViewForPosition(position: Position): View {
  if (position === "customer_service") {
    return "automation_customer_service";
  }

  if (position === "finance") {
    return "automation_finance";
  }

  return "automation_operations";
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

function visibleNavigationForUser(role: Role, position: Position | null): NavItem[] {
  return navItems
    .filter((item) => item.roles.includes(role))
    .map((item) => {
      if (!item.children?.length) {
        return item;
      }

      const children = item.children.filter((child) =>
        child.roles.includes(role)
        && (role === "admin" || !child.positions?.length || child.positions.includes(position as Position)),
      );

      return {
        ...item,
        children,
      };
    })
    .filter((item) => !item.children || item.children.length > 0);
}

function flattenNavItems(items: NavItem[]): NavItem[] {
  return items.flatMap((item) => [item, ...flattenNavItems(item.children || [])]);
}

function allNavItems(): NavItem[] {
  return flattenNavItems(navItems);
}

function viewFromPath(pathname: string): View {
  const matched = allNavItems().find((item) => item.path === pathname);
  return matched?.id || "dashboard";
}

function pathForView(view: View) {
  if (view === "automation") {
    const storedPosition = readStoredPosition();
    if (storedPosition === "customer_service") {
      return "/automation/customer-service";
    }
    if (storedPosition === "finance") {
      return "/automation/finance";
    }
    return "/automation/operations";
  }

  if (view === "erp") {
    return "/erp/query";
  }

  return allNavItems().find((item) => item.id === view)?.path || "/dashboard";
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
    return "automation_customer_service";
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

function canRoleAccessView(role: Role, view: View) {
  const item = allNavItems().find((nav) => nav.id === view);
  return item ? item.roles.includes(role) : false;
}

function isAutomationView(view: View) {
  return view === "automation"
    || view === "automation_operations"
    || view === "automation_customer_service"
    || view === "automation_finance";
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

  if (view === "automation_customer_service") {
    return "customer_service";
  }

  if (view === "automation_finance") {
    return "finance";
  }

  return "operations";
}

function pageSubtitle(role: Role, position: Position | null) {
  if (role === "admin") {
    return "RAG、LangGraph、Agent、用户岗位和后台审批控制台";
  }

  return position ? `${positionLabel(position)}岗位 AI 自动化工作台` : "员工工作台";
}

function mapApproval(item: ApprovalItem): Approval {
  const payload = item.payload || {};
  const orderNo = String(payload.order_no || "待确认");
  const amount = moneyFromOrderResult(payload.order_result);

  return {
    id: item.id,
    threadId: item.thread_id,
    actionType: item.action_type,
    status: item.status,
    orderNo,
    amount,
    reason: String(payload.user_input || item.action_type),
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
    resourceType: item.resource_type || "-",
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
    role: item.role,
    department: item.department || "-",
    position: item.position,
    capabilities: item.capabilities || [],
    erpScopes: item.erp_scopes || [],
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

  return undefined;
}

function labelForRoute(route: ChatRoute) {
  const labels: Record<ChatRoute, string> = {
    refund_workflow: "高风险退款审批",
    order_agent: "订单工具查询",
    knowledge_rag: "知识库问答",
  };

  return labels[route];
}

function routeColor(route: ChatRoute) {
  const colors: Record<ChatRoute, string> = {
    refund_workflow: "gold",
    order_agent: "blue",
    knowledge_rag: "green",
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
    published: "已发布",
    pending: "待审批",
    approved: "已通过",
    rejected: "已拒绝",
    succeeded: "成功",
    failed: "失败",
    blocked: "已拦截",
    running: "运行中",
  };

  return labels[value] ?? value;
}

function labelForConnectorStatus(value: string) {
  const labels: Record<string, string> = {
    healthy: "健康",
    degraded: "异常",
    not_configured: "未配置",
    not_implemented: "待接入",
    configured_pending: "已配置待联调",
  };

  return labels[value] ?? value;
}

createRoot(document.getElementById("root")!).render(<App />);
