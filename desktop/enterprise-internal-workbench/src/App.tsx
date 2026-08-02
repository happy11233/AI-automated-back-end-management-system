import {
  type FormEvent,
  type KeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  AppWindow,
  Bot,
  Check,
  ChevronRight,
  CircleAlert,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FolderOpen,
  GripVertical,
  ListChecks,
  Loader2,
  LockKeyhole,
  LogOut,
  Maximize2,
  MessageSquareText,
  Minus,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Paperclip,
  Pencil,
  Play,
  Plus,
  Send,
  Settings,
  Sparkles,
  Square,
  Trash2,
  Workflow,
  X,
} from "lucide-react";
import "./App.css";
import {
  ApiError,
  type BusinessProgressPayload,
  type ChatStreamHandlers,
  DEFAULT_API_BASE_URL,
  confirmEnterpriseWechatFileSend,
  downloadGeneratedFile,
  getMySettings,
  listAiWorkflows,
  listGeneratedFiles,
  login,
  prepareSalaryWechatSendStream,
  sendChatStream,
  submitFeedback,
  type AiWorkflowItem,
  type ChatAttachment,
  type GeneratedFileItem,
  type LoginResponse,
  type Position,
  type UserSettingsItem,
} from "./api";

const SESSION_STORAGE_KEY = "enterprise-internal-workbench-session";
const LEGACY_CONVERSATION_STORAGE_KEY = "enterprise-internal-workbench-conversations";
const MAX_CONVERSATIONS = 5;

const WORKSPACE_ITEMS = [
  { id: "chat", label: "AI 对话", icon: MessageSquareText },
  { id: "automation", label: "自动化任务", icon: Workflow },
  { id: "apps", label: "当前支持应用", icon: AppWindow },
  { id: "files", label: "文档下载", icon: FileText },
] as const;

type ActiveView = (typeof WORKSPACE_ITEMS)[number]["id"];

type CurrentUser = {
  id: string;
  username: string;
  display_name: string | null;
  email: string | null;
  role: "admin" | "employee";
  department: string | null;
  position: Position | null;
  allowed_ai_app_ids?: string[];
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  intent?: string | null;
  riskLevel?: string | null;
  attachments?: ChatAttachment[];
  automation?: Record<string, unknown> | null;
  businessProgress?: BusinessProgressPayload | null;
};

type LocalConversation = {
  id: string;
  userId: string;
  title: string;
  threadId?: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
};

type StoredSession = {
  apiBase: string;
  token: string;
  user: CurrentUser;
};

type ConversationMenu = {
  conversationId: string;
  x: number;
  y: number;
};

type FileTypeFilter = "all" | "excel" | "word";
type SettingsPanel = "general" | "appearance" | "feedback";

const FILE_TYPE_LABELS: Record<FileTypeFilter, string> = {
  all: "全部类型",
  excel: "Excel",
  word: "Word",
};

function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function compactTitle(value: string) {
  return value.replace(/\s+/g, " ").trim().slice(0, 28) || "新对话";
}

function conversationStorageKey(userId: string) {
  return `enterprise-internal-workbench-conversations:${userId}`;
}

function effectiveApiBase(savedApiBase?: string | null) {
  const viteApiBase = String(import.meta.env.VITE_API_BASE_URL || "").trim();
  if (viteApiBase) return DEFAULT_API_BASE_URL;
  const cleanSavedApiBase = savedApiBase?.trim() || "";
  const isDesktopRuntime = typeof window !== "undefined" && Boolean(window.enterpriseBridge);
  const isLegacyRemoteApi = /^https?:\/\/175\.178\.225\.8(?::\d+)?(?:\/api)?\/?$/i.test(cleanSavedApiBase);
  if (isDesktopRuntime && (!cleanSavedApiBase || cleanSavedApiBase === "/api" || isLegacyRemoteApi)) {
    return DEFAULT_API_BASE_URL;
  }
  return cleanSavedApiBase || DEFAULT_API_BASE_URL;
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDateTime(value?: string | null) {
  if (!value) return "未知时间";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatBytes(value?: number | null) {
  if (!value) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function relativeTime(value: string) {
  const diffMs = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(diffMs / 60_000));
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  return `${Math.floor(hours / 24)}天前`;
}

function roleLabel(role: CurrentUser["role"]) {
  return role === "admin" ? "管理员" : "员工";
}

function positionLabel(position: Position | null) {
  if (position === "operations") return "运营";
  if (position === "customer_service") return "客服";
  if (position === "finance") return "财务";
  return "未分配岗位";
}

function riskLabel(riskLevel?: string | null) {
  if (!riskLevel) return "未标记";
  if (riskLevel === "high") return "高风险";
  if (riskLevel === "medium") return "中风险";
  if (riskLevel === "low") return "低风险";
  return riskLevel;
}

function salaryWechatStatusLabel(value: unknown, fallback?: unknown) {
  if (typeof fallback === "string" && fallback.trim()) return fallback;
  const status = typeof value === "string" ? value : "";
  if (status === "waiting_confirmation") return "等待确认";
  if (status === "waiting_generation") return "等待生成文件";
  if (status === "waiting_wechat_confirmation") return "等待准备微信确认";
  if (status === "generated") return "工资表已生成";
  if (status === "waiting_manual_send") return "等待人工发送";
  if (status === "waiting_executor") return "等待执行器";
  if (status === "waiting_callback") return "等待执行器回调";
  if (status === "completed") return "执行完成";
  if (status === "failed") return "执行失败";
  return "等待确认";
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function recordsFromArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.map((item) => asRecord(item)).filter((item): item is Record<string, unknown> => Boolean(item))
    : [];
}

function automationArtifacts(automation: Record<string, unknown> | null) {
  if (!automation) return [];
  const wechatSend = asRecord(automation.wechat_send) || asRecord(automation.executor);
  const confirmationCard = asRecord(automation.confirmation_card) || asRecord(wechatSend?.confirmation_card);
  return (
    recordsFromArray(confirmationCard?.artifacts)[0]
      ? recordsFromArray(confirmationCard?.artifacts)
      : recordsFromArray(wechatSend?.generated_artifacts)[0]
        ? recordsFromArray(wechatSend?.generated_artifacts)
        : recordsFromArray(automation.generated_artifacts)
  );
}

function automationSelectedRecipient(automation: Record<string, unknown> | null) {
  if (!automation) return null;
  const wechatSend = asRecord(automation.wechat_send) || asRecord(automation.executor);
  const confirmationCard = asRecord(automation.confirmation_card) || asRecord(wechatSend?.confirmation_card);
  return asRecord(confirmationCard?.selected_recipient) || asRecord(wechatSend?.recipient) || asRecord(automation.recipient);
}

function automationPlanForMessage(message: ChatMessage) {
  const automation = asRecord(message.automation);
  if (!automation) return null;
  const automationType = typeof automation.type === "string" ? automation.type : "";
  if (!["finance_salary_wechat_send", "agent_plan_execute", "enterprise_wechat_file_send", "message_send"].includes(automationType)) return null;
  const plan = asRecord(automation.execution_plan) || asRecord(automation.plan) || {};
  const rawSteps = Array.isArray(plan.steps) ? plan.steps : Array.isArray(automation.plan) ? automation.plan : [];
  const steps = rawSteps
        .map((item) => asRecord(item))
        .filter((item): item is Record<string, unknown> => Boolean(item));
  const artifacts = automationArtifacts(automation);
  return {
    automation,
    plan,
    steps,
    artifacts,
  };
}

function stopRunningProgress(progress?: BusinessProgressPayload | null): BusinessProgressPayload | null {
  if (!progress || progress.status !== "running") return progress || null;
  return {
    ...progress,
    label: "已停止当前任务",
    status: "stopped",
    detail: null,
  };
}

function stopRunningMessages(messages: ChatMessage[]) {
  return messages.map((message) =>
    message.businessProgress?.status === "running"
      ? {
          ...message,
          businessProgress: stopRunningProgress(message.businessProgress),
          content: message.content || "已停止当前任务。",
        }
      : message,
  );
}

function normalizeBusinessProgress(value: unknown): BusinessProgressPayload | null {
  const progress = asRecord(value);
  const label = typeof progress?.label === "string" ? progress.label.trim() : "";
  if (!label) return null;
  return {
    workflow_id: typeof progress?.workflow_id === "string" ? progress.workflow_id : undefined,
    step_key: typeof progress?.step_key === "string" ? progress.step_key : undefined,
    label,
    status: typeof progress?.status === "string" ? progress.status : "running",
    detail: typeof progress?.detail === "string" ? progress.detail : null,
    data: asRecord(progress?.data) || {},
  };
}

function automationArtifactForMessage(message: ChatMessage) {
  const automation = asRecord(message.automation);
  const artifactId = typeof automation?.artifact_id === "string" ? automation.artifact_id : "";
  if (!artifactId) return null;
  return {
    artifactId,
    filename: typeof automation?.filename === "string" ? automation.filename : "generated_file.xlsx",
  };
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "请求失败";
}

function isAbortError(error: unknown) {
  return error instanceof DOMException
    ? error.name === "AbortError"
    : error instanceof Error && error.name === "AbortError";
}

function userFromLogin(response: LoginResponse): CurrentUser {
  return {
    id: response.id,
    username: response.username,
    display_name: response.display_name,
    email: response.email,
    role: response.role,
    department: response.department,
    position: response.position,
    allowed_ai_app_ids: response.allowed_ai_app_ids,
  };
}

function mergeSettings(user: CurrentUser, settings: UserSettingsItem): CurrentUser {
  return {
    ...user,
    display_name: settings.display_name,
    email: settings.email,
    role: settings.role,
    department: settings.department,
    position: settings.position,
  };
}

function workflowStatusLabel(item: AiWorkflowItem) {
  if (!item.executable) return "不可执行";
  if (item.requires_approval) return "需要审批";
  return "可执行";
}

function workflowStatusClass(item: AiWorkflowItem) {
  if (!item.executable) return "muted";
  if (item.requires_approval) return "warning";
  return "success";
}

function sortAndLimitConversations(items: LocalConversation[]) {
  return [...items]
    .sort((first, second) => new Date(second.updatedAt).getTime() - new Date(first.updatedAt).getTime())
    .slice(0, MAX_CONVERSATIONS);
}

function createConversation(userId: string, title = "新对话"): LocalConversation {
  const now = new Date().toISOString();
  return {
    id: createId("conv"),
    userId,
    title,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

function normalizeConversation(value: unknown): LocalConversation | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Partial<LocalConversation>;
  if (!item.id || !item.userId || !Array.isArray(item.messages)) return null;
  return {
    id: String(item.id),
    userId: String(item.userId),
    title: item.title ? String(item.title) : "新对话",
    threadId: item.threadId ? String(item.threadId) : undefined,
    messages: item.messages.filter((message): message is ChatMessage => {
      return Boolean(
        message &&
          typeof message === "object" &&
          "id" in message &&
          "role" in message &&
          "content" in message &&
          "createdAt" in message,
      );
    }),
    createdAt: item.createdAt || new Date().toISOString(),
    updatedAt: item.updatedAt || item.createdAt || new Date().toISOString(),
  };
}

function WindowControls() {
  return (
    <div className="windowControls" aria-label="窗口控制">
      <button type="button" title="放大" onClick={() => void window.enterpriseBridge?.maximize()}>
        <Maximize2 size={14} />
      </button>
      <button type="button" title="隐藏" onClick={() => void window.enterpriseBridge?.minimize()}>
        <Minus size={15} />
      </button>
      <button type="button" title="关闭" onClick={() => void window.enterpriseBridge?.close()}>
        <X size={14} />
      </button>
    </div>
  );
}

function readTextFile(file: File) {
  return new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve(String(reader.result ?? ""));
    };
    reader.onerror = () => {
      resolve("");
    };
    reader.readAsText(file);
  });
}

function canReadAsText(file: File) {
  return file.type.startsWith("text/") || /\.(txt|md|csv|json|log|yaml|yml)$/i.test(file.name);
}

function base64ToBlob(contentBase64: string, mimeType?: string) {
  const binary = atob(contentBase64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType || "application/octet-stream" });
}

function App() {
  const [apiBase, setApiBase] = useState(DEFAULT_API_BASE_URL);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginPending, setLoginPending] = useState(false);
  const [capsLockOn, setCapsLockOn] = useState(false);
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(168);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsPanel, setSettingsPanel] = useState<SettingsPanel | null>(null);
  const [themeMode, setThemeMode] = useState<"light" | "system">("light");
  const [startupEnabled, setStartupEnabled] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [workflowPickerOpen, setWorkflowPickerOpen] = useState(false);
  const [fileTypeMenuOpen, setFileTypeMenuOpen] = useState(false);
  const [conversations, setConversations] = useState<LocalConversation[]>([]);
  const [conversationsReady, setConversationsReady] = useState(false);
  const [conversationStorePath, setConversationStorePath] = useState("");
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>();
  const [conversationMenu, setConversationMenu] = useState<ConversationMenu | null>(null);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [automationPendingMessageId, setAutomationPendingMessageId] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<AiWorkflowItem[]>([]);
  const [workflowsLoading, setWorkflowsLoading] = useState(false);
  const [workflowsError, setWorkflowsError] = useState("");
  const [selectedWorkflowId, setSelectedWorkflowId] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileItem[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesError, setFilesError] = useState("");
  const [fileSearch, setFileSearch] = useState("");
  const [fileQuery, setFileQuery] = useState("");
  const [fileType, setFileType] = useState<FileTypeFilter>("all");
  const [fileNotice, setFileNotice] = useState("");
  const [feedbackTitle, setFeedbackTitle] = useState("");
  const [feedbackDescription, setFeedbackDescription] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);
  const chatAbortRef = useRef<AbortController | null>(null);
  const activeAssistantMessageIdRef = useRef<string | null>(null);

  const selectedWorkflow = useMemo(
    () => workflows.find((item) => item.id === selectedWorkflowId) ?? null,
    [selectedWorkflowId, workflows],
  );

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeConversationId) ?? null,
    [activeConversationId, conversations],
  );

  const messages = activeConversation?.messages ?? [];

  useEffect(() => {
    if (!conversationMenu) return;
    if (!conversations.some((item) => item.id === conversationMenu.conversationId)) {
      setConversationMenu(null);
    }
  }, [conversationMenu, conversations]);

  useEffect(() => {
    const closeFloating = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target?.closest(
          ".floatingSurface, .floatingTrigger, .workflowPicker, .contextMenu",
        )
      ) {
        return;
      }
      setConversationMenu(null);
      setSettingsOpen(false);
      setUserMenuOpen(false);
      setWorkflowPickerOpen(false);
      setFileTypeMenuOpen(false);
    };
    window.addEventListener("pointerdown", closeFloating);
    return () => window.removeEventListener("pointerdown", closeFloating);
  }, []);

  useEffect(() => {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) {
      setAuthReady(true);
      return;
    }

    try {
      const saved = JSON.parse(raw) as StoredSession;
      const nextApiBase = effectiveApiBase(saved.apiBase);
      setApiBase(nextApiBase);
      setToken(saved.token);
      setUser(saved.user);
      void (async () => {
        try {
          const settings = await getMySettings(nextApiBase, saved.token);
          const nextUser = mergeSettings(saved.user, settings.item);
          setUser(nextUser);
          localStorage.setItem(
            SESSION_STORAGE_KEY,
            JSON.stringify({
              apiBase: nextApiBase,
              token: saved.token,
              user: nextUser,
            }),
          );
          setWorkflowsLoading(true);
          const response = await listAiWorkflows(nextApiBase, saved.token);
          setWorkflows(response.items);
          setWorkflowsError("");
          await loadLocalConversations(nextUser.id);
        } catch {
          localStorage.removeItem(SESSION_STORAGE_KEY);
          setToken(null);
          setUser(null);
          setWorkflows([]);
          setConversationsReady(true);
        } finally {
          setWorkflowsLoading(false);
          setAuthReady(true);
        }
      })();
    } catch {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      setAuthReady(true);
    }
  }, []);

  useEffect(() => {
    if (!conversationsReady || !user) return;
    if (window.enterpriseBridge?.saveConversations) {
      void window.enterpriseBridge.saveConversations({ userId: user.id, items: conversations });
      return;
    }
    localStorage.setItem(conversationStorageKey(user.id), JSON.stringify(conversations));
  }, [conversations, conversationsReady, user]);

  async function loadLocalConversations(userId: string) {
    setConversationsReady(false);
    let items: unknown[] = [];
    if (window.enterpriseBridge?.loadConversations) {
      const store = await window.enterpriseBridge.loadConversations({ userId });
      items = store.items;
      setConversationStorePath(store.path);
    } else {
      const storageKey = conversationStorageKey(userId);
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        try {
          items = JSON.parse(raw) as unknown[];
        } catch {
          items = [];
        }
      } else {
        const legacyRaw = localStorage.getItem(LEGACY_CONVERSATION_STORAGE_KEY);
        if (legacyRaw) {
          try {
            const legacyItems = JSON.parse(legacyRaw) as unknown[];
            if (Array.isArray(legacyItems)) {
              items = legacyItems.filter((item) => (
                item
                && typeof item === "object"
                && String((item as { userId?: unknown }).userId || "") === userId
              ));
              if (items.length) {
                localStorage.setItem(storageKey, JSON.stringify(items));
              }
            }
          } catch {
            items = [];
          }
        }
      }
      setConversationStorePath(`localStorage:${storageKey}`);
    }

    const nextConversations = sortAndLimitConversations(
      items
        .map(normalizeConversation)
        .filter((item): item is LocalConversation => Boolean(item && item.userId === userId)),
    );
    setConversations(nextConversations);
    setActiveConversationId(nextConversations[0]?.id);
    setConversationsReady(true);
  }

  async function refreshWorkflows(nextToken = token, nextApiBase = apiBase) {
    if (!nextToken) return;
    setWorkflowsLoading(true);
    setWorkflowsError("");
    try {
      const response = await listAiWorkflows(nextApiBase, nextToken);
      setWorkflows(response.items);
      if (selectedWorkflowId && !response.items.some((item) => item.id === selectedWorkflowId)) {
        setSelectedWorkflowId("");
      }
    } catch (error) {
      setWorkflowsError(getErrorMessage(error));
    } finally {
      setWorkflowsLoading(false);
    }
  }

  async function refreshGeneratedFiles(filters?: {
    search?: string;
    fileType?: FileTypeFilter;
  }) {
    if (!token) return;
    setFilesLoading(true);
    setFilesError("");
    try {
      const response = await listGeneratedFiles(apiBase, token, {
        search: filters?.search ?? fileQuery,
        fileType: filters?.fileType ?? fileType,
        dateRange: "30d",
        limit: 80,
      });
      setGeneratedFiles(response.items);
      setFileNotice(response.items.length ? "" : "当前筛选条件下暂无可下载文件");
    } catch (error) {
      setFilesError(getErrorMessage(error));
    } finally {
      setFilesLoading(false);
    }
  }

  function clearSession() {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setWorkflows([]);
    setSelectedWorkflowId("");
    setConversations([]);
    setConversationsReady(false);
    setActiveConversationId(undefined);
    setGeneratedFiles([]);
    setUserMenuOpen(false);
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanUsername = username.trim();
    const cleanApiBase = effectiveApiBase(apiBase);
    if (!cleanUsername || !password) {
      setLoginError("请输入账号和密码");
      return;
    }

    setLoginPending(true);
    setLoginError("");
    try {
      const response = await login(cleanApiBase, cleanUsername, password);
      const nextUser = userFromLogin(response);
      setToken(response.access_token);
      setUser(nextUser);
      setApiBase(cleanApiBase);
      setPassword("");
      localStorage.setItem(
        SESSION_STORAGE_KEY,
        JSON.stringify({ apiBase: cleanApiBase, token: response.access_token, user: nextUser }),
      );
      await refreshWorkflows(response.access_token, cleanApiBase);
      await loadLocalConversations(nextUser.id);
    } catch (error) {
      setLoginError(getErrorMessage(error));
    } finally {
      setLoginPending(false);
    }
  }

  function beginSidebarResize(event: ReactPointerEvent<HTMLDivElement>) {
    if (sidebarCollapsed) return;
    const startX = event.clientX;
    const startWidth = sidebarWidth;

    function handlePointerMove(moveEvent: PointerEvent) {
      const nextWidth = Math.min(280, Math.max(142, startWidth + moveEvent.clientX - startX));
      setSidebarWidth(nextWidth);
    }

    function handlePointerUp() {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  }

  function createNewConversation() {
    if (!user) return;
    const nextConversation = createConversation(user.id);
    setConversations((items) => sortAndLimitConversations([nextConversation, ...items]));
    setActiveConversationId(nextConversation.id);
    setActiveView("chat");
  }

  function openConversation(conversationId: string) {
    setConversationMenu(null);
    setActiveConversationId(conversationId);
    setActiveView("chat");
  }

  function activateWorkspace(view: ActiveView) {
    setActiveView(view);
    if (view === "chat") {
      if (!activeConversationId && conversations[0]) {
        setActiveConversationId(conversations[0].id);
      }
      if (!activeConversationId && !conversations[0]) {
        createNewConversation();
      }
    }
    if (view === "files") {
      void refreshGeneratedFiles();
    }
  }

  function updateConversation(
    conversationId: string,
    updater: (conversation: LocalConversation) => LocalConversation,
  ) {
    setConversations((items) =>
      sortAndLimitConversations(
        items.map((item) =>
          item.id === conversationId
            ? {
                ...updater(item),
                updatedAt: new Date().toISOString(),
              }
            : item,
        ),
      ),
    );
  }

  function stopVisibleRunningTasks() {
    setConversations((items) =>
      sortAndLimitConversations(
        items.map((item) => ({
          ...item,
          messages: stopRunningMessages(item.messages),
        })),
      ),
    );
  }

  function handleStopCurrentTask() {
    chatAbortRef.current?.abort();
    chatAbortRef.current = null;
    activeAssistantMessageIdRef.current = null;
    setIsSending(false);
    setAutomationPendingMessageId(null);
    stopVisibleRunningTasks();
  }

  async function buildMessagePayload(content: string) {
    if (!selectedFiles.length) return content;

    const fileBlocks = await Promise.all(
      selectedFiles.map(async (file) => {
        if (file.size > 220_000) {
          return `文件 ${file.name} 体积较大，桌面端第一版未把完整内容发送给 AI。`;
        }
        if (!canReadAsText(file)) {
          return `文件 ${file.name} 不是可直接读取的文本格式。`;
        }
        const text = await readTextFile(file);
        return `文件：${file.name}\n${text.slice(0, 12_000)}`;
      }),
    );

    return `${content}\n\n附件内容：\n${fileBlocks.join("\n\n")}`;
  }

  async function handleSend() {
    if (!token || !user || isSending) return;
    const content = draft.trim();
    if (!content) return;
    stopVisibleRunningTasks();

    let conversation = activeConversation;
    if (!conversation) {
      conversation = createConversation(user.id, compactTitle(content));
      setConversations((items) => sortAndLimitConversations([conversation as LocalConversation, ...items]));
      setActiveConversationId(conversation.id);
    }

    const conversationId = conversation.id;
    const createdAt = new Date().toISOString();
    const userMessage: ChatMessage = {
      id: createId("msg-user"),
      role: "user",
      content,
      createdAt,
    };
    const assistantMessageId = createId("msg-assistant");
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      createdAt,
      businessProgress: {
        label: "正在理解你的需求",
        status: "running",
      },
    };

    updateConversation(conversationId, (item) => ({
      ...item,
      title: item.title === "新对话" ? compactTitle(content) : item.title,
      messages: [...item.messages, userMessage, assistantMessage],
    }));
    setDraft("");
    setIsSending(true);
    const abortController = new AbortController();
    chatAbortRef.current = abortController;
    activeAssistantMessageIdRef.current = assistantMessageId;
    const isCurrentRequest = () => activeAssistantMessageIdRef.current === assistantMessageId;

    try {
      const messagePayload = await buildMessagePayload(
        selectedWorkflow ? `请按「${selectedWorkflow.name}」能力处理：${content}` : content,
      );
      const streamHandlers: ChatStreamHandlers = {
        signal: abortController.signal,
        onStart: (payload) => {
          if (!isCurrentRequest()) return;
          if (!payload.thread_id) return;
          updateConversation(conversationId, (item) => ({
            ...item,
            threadId: payload.thread_id,
            messages: item.messages.map((chatMessage) =>
              chatMessage.id === assistantMessageId
                ? { ...chatMessage, businessProgress: normalizeBusinessProgress(payload.business_progress) || chatMessage.businessProgress }
                : chatMessage,
            ),
          }));
        },
        onBusinessProgress: (progress) => {
          if (!isCurrentRequest()) return;
          updateConversation(conversationId, (item) => ({
            ...item,
            messages: item.messages.map((chatMessage) =>
              chatMessage.id === assistantMessageId
                ? { ...chatMessage, businessProgress: normalizeBusinessProgress(progress) }
                : chatMessage,
            ),
          }));
        },
        onContent: (payload) => {
          if (!isCurrentRequest()) return;
          const chunk = payload.content || "";
          if (!chunk && !payload.thread_id) return;
          updateConversation(conversationId, (item) => ({
            ...item,
            threadId: payload.thread_id || item.threadId,
            messages: item.messages.map((chatMessage) =>
              chatMessage.id === assistantMessageId
                ? {
                    ...chatMessage,
                    content: chatMessage.content + chunk,
                  }
                : chatMessage,
            ),
          }));
        },
        onDone: (payload) => {
          if (!isCurrentRequest()) return;
          updateConversation(conversationId, (item) => ({
            ...item,
            threadId: payload.thread_id || item.threadId,
            messages: item.messages.map((chatMessage) =>
              chatMessage.id === assistantMessageId
                ? {
                    ...chatMessage,
                    content: chatMessage.content || payload.answer || "",
                    createdAt: new Date().toISOString(),
                    intent: payload.intent,
                    riskLevel: payload.risk_level,
                    attachments: payload.attachments || [],
                    automation: payload.automation || null,
                    businessProgress: null,
                  }
                : chatMessage,
            ),
          }));
        },
        onError: (payload) => {
          if (!isCurrentRequest()) return;
          throw new Error(payload.message || "聊天处理失败");
        },
      };
      try {
        await sendChatStream(apiBase, token, messagePayload, conversation.threadId, streamHandlers);
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 404 || !conversation.threadId) {
          throw error;
        }

        updateConversation(conversationId, (item) => ({
          ...item,
          threadId: undefined,
          messages: item.messages.map((chatMessage) =>
            chatMessage.id === assistantMessageId
              ? {
                  ...chatMessage,
                  businessProgress: {
                    label: "正在创建新的个人会话",
                    status: "running",
                  },
                }
              : chatMessage,
          ),
        }));
        await sendChatStream(apiBase, token, messagePayload, undefined, streamHandlers);
      }
      setSelectedFiles([]);
    } catch (error) {
      if (!isCurrentRequest() || isAbortError(error)) {
        return;
      }
      const message = getErrorMessage(error);
      updateConversation(conversationId, (item) => ({
        ...item,
        messages: item.messages.map((chatMessage) =>
          chatMessage.id === assistantMessageId
            ? {
                ...chatMessage,
                content: message,
                createdAt: new Date().toISOString(),
                businessProgress: null,
              }
            : chatMessage,
        ),
      }));
    } finally {
      if (isCurrentRequest()) {
        chatAbortRef.current = null;
        activeAssistantMessageIdRef.current = null;
        setIsSending(false);
      }
    }
  }

  async function handleConfirmSalaryWechat(message: ChatMessage) {
    if (!token || !activeConversation) return;
    const automation = asRecord(message.automation);
    const wechatSend = asRecord(automation?.wechat_send) || asRecord(automation?.executor);
    const automationStatus = typeof automation?.status === "string"
      ? automation.status
      : typeof wechatSend?.status === "string"
        ? wechatSend.status
        : "";
    const automationType = typeof automation?.type === "string" ? automation.type : "";
    const sourceMessage = typeof automation?.source_message === "string" ? automation.source_message : "";
    const recipientName = typeof automation?.recipient_name === "string" ? automation.recipient_name : null;
    const artifactRecords = automationArtifacts(automation);
    const artifactIds = Array.from(new Set([
      ...artifactRecords
        .map((item) => (typeof item.artifact_id === "string" ? item.artifact_id : ""))
        .filter(Boolean),
      typeof automation?.artifact_id === "string" ? automation.artifact_id : "",
    ].filter(Boolean)));
    const artifactId = typeof automation?.artifact_id === "string" ? automation.artifact_id : artifactIds[0] || null;
    const filename = typeof automation?.filename === "string" ? automation.filename : null;
    const workflowId = typeof automation?.workflow_id === "string" ? automation.workflow_id : null;
    const selectedRecipient = automationSelectedRecipient(automation);
    const recipientCandidateId = typeof selectedRecipient?.id === "string" ? selectedRecipient.id : null;
    if (!recipientName) return;

    setAutomationPendingMessageId(message.id);
    updateConversation(activeConversation.id, (item) => ({
      ...item,
      messages: item.messages.map((chatMessage) =>
        chatMessage.id === message.id
          ? {
              ...chatMessage,
              businessProgress: {
                label: artifactId && ["waiting_wechat_confirmation", "waiting_manual_send", "waiting_executor", "failed"].includes(automationStatus)
                  ? "正在通过企业微信发送文件"
                  : "正在生成业务文件",
                status: "running",
              },
            }
          : chatMessage,
      ),
    }));
    try {
      if (artifactId && ["waiting_wechat_confirmation", "waiting_manual_send", "waiting_executor", "failed"].includes(automationStatus)) {
        const response = await confirmEnterpriseWechatFileSend(apiBase, token, {
          artifactId,
          artifactIds,
          recipientName,
          filename,
          sourceMessage: sourceMessage || message.content,
          sourceMessageId: message.id,
          sourceWorkflowId: workflowId,
          threadId: activeConversation.threadId,
          recipient: selectedRecipient,
          recipientCandidateId,
          sensitiveDataConfirmed: true,
        });
        updateConversation(activeConversation.id, (item) => ({
          ...item,
          messages: item.messages.map((chatMessage) =>
            chatMessage.id === message.id
              ? {
                  ...chatMessage,
                  content: `${response.answer || "企业微信文件发送流程已处理。"}${
                    response.filename ? `\n文件：${response.filename}` : ""
                  }`,
                  createdAt: new Date().toISOString(),
                  intent: "enterprise_wechat_file_send",
                  riskLevel: "high",
                  automation: {
                    ...automation,
                    type: automationType || "enterprise_wechat_file_send",
                    status: response.status,
                    status_label: response.status_label,
                    artifact_id: response.artifact_id,
                    download_path: response.download_path,
                    filename: response.filename,
                    recipient_name: response.recipient_name,
                    wechat_send: response.execution,
                    enterprise_wechat_run_id: response.run_id,
                    generated_artifacts: artifactRecords,
                    source_message: sourceMessage,
                  },
                  businessProgress: null,
                }
              : chatMessage,
          ),
        }));
        void refreshGeneratedFiles();
        return;
      }

      if (!sourceMessage) return;
      await prepareSalaryWechatSendStream(apiBase, token, {
        message: sourceMessage,
        recipientName,
        recipientConfirmed: false,
        sensitiveDataConfirmed: false,
      }, {
        onBusinessProgress: (progress) => {
          updateConversation(activeConversation.id, (item) => ({
            ...item,
            messages: item.messages.map((chatMessage) =>
              chatMessage.id === message.id
                ? { ...chatMessage, businessProgress: normalizeBusinessProgress(progress) }
                : chatMessage,
            ),
          }));
        },
        onDone: (payload) => {
          updateConversation(activeConversation.id, (item) => ({
            ...item,
            messages: item.messages.map((chatMessage) =>
              chatMessage.id === message.id
                ? {
                    ...chatMessage,
                    content: `${payload.answer || "工资表已生成，等待你人工确认并发送。"}${
                      payload.filename ? `\n文件：${payload.filename}` : ""
                    }`,
                    createdAt: new Date().toISOString(),
                    intent: "finance_salary_wechat_send",
                    riskLevel: "high",
                    automation: {
                      type: "finance_salary_wechat_send",
                      status: payload.status,
                      status_label: payload.status_label,
                      workflow_id: "finance_salary_wechat_send",
                      artifact_id: payload.artifact_id,
                      download_path: payload.download_path,
                      filename: payload.filename,
                      recipient_name: payload.recipient_name,
                      execution_plan: payload.plan,
                      executor: payload.execution,
                      source_message: sourceMessage,
                    },
                    businessProgress: null,
                  }
                : chatMessage,
            ),
          }));
        },
        onError: (payload) => {
          throw new Error(payload.message || "工资表生成失败");
        },
      });
      void refreshGeneratedFiles();
    } catch (error) {
      updateConversation(activeConversation.id, (item) => ({
        ...item,
        messages: item.messages.map((chatMessage) =>
          chatMessage.id === message.id
            ? {
                ...chatMessage,
                content: getErrorMessage(error),
                createdAt: new Date().toISOString(),
                businessProgress: null,
              }
            : chatMessage,
        ),
      }));
    } finally {
      setAutomationPendingMessageId(null);
    }
  }

  async function handleDownloadSalaryWechatArtifact(message: ChatMessage) {
    if (!token) return;
    const automation = asRecord(message.automation);
    const artifactId = typeof automation?.artifact_id === "string" ? automation.artifact_id : null;
    const filename = typeof automation?.filename === "string" ? automation.filename : "salary.xlsx";
    if (!artifactId) return;

    setFileNotice("");
    try {
      const saved = await downloadGeneratedFile(apiBase, token, artifactId, filename);
      setFileNotice(saved.path ? `已保存：${saved.path}` : `已下载：${saved.filename}`);
    } catch (error) {
      setFileNotice(getErrorMessage(error));
    }
  }

  function handleDraftKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing || composingRef.current) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  }

  function updateCapsLockState(event: KeyboardEvent<HTMLInputElement>) {
    setCapsLockOn(event.getModifierState("CapsLock"));
  }

  function removeSelectedFile(index: number) {
    setSelectedFiles((items) => items.filter((_, itemIndex) => itemIndex !== index));
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleFileTypeChange(nextFileType: FileTypeFilter) {
    setFileType(nextFileType);
    void refreshGeneratedFiles({
      search: fileQuery,
      fileType: nextFileType,
    });
  }

  function handleFileSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = fileSearch.trim();
    setFileQuery(nextQuery);
    void refreshGeneratedFiles({
      search: nextQuery,
      fileType,
    });
  }

  async function handleFeedbackSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const title = feedbackTitle.trim();
    const description = feedbackDescription.trim();
    if (title.length < 2 || description.length < 4) {
      setFeedbackStatus("请填写标题和至少 4 个字的反馈内容");
      return;
    }

    setFeedbackSubmitting(true);
    setFeedbackStatus("");
    try {
      await submitFeedback(apiBase, token, {
        category: "体验问题",
        priority: "normal",
        title,
        description,
      });
      setFeedbackTitle("");
      setFeedbackDescription("");
      setFeedbackStatus("已提交给管理员");
    } catch (error) {
      setFeedbackStatus(getErrorMessage(error));
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  async function copyText(value: string) {
    if (window.enterpriseBridge?.copyText) {
      await window.enterpriseBridge.copyText(value);
      return;
    }
    await navigator.clipboard.writeText(value);
  }

  async function copyConversationPath(conversationId: string) {
    setConversationMenu(null);
    const pathText = `${conversationStorePath || "localStorage:enterprise-internal-workbench-conversations"}#${conversationId}`;
    await copyText(pathText);
  }

  function renameConversation(conversationId: string) {
    setConversationMenu(null);
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) return;
    const nextTitle = window.prompt("重命名对话", conversation.title)?.trim();
    if (!nextTitle) return;
    updateConversation(conversationId, (item) => ({ ...item, title: compactTitle(nextTitle) }));
  }

  function deleteConversation(conversationId: string) {
    setConversationMenu(null);
    setConversations((items) => {
      const nextItems = items.filter((item) => item.id !== conversationId);
      if (activeConversationId === conversationId) {
        setActiveConversationId(nextItems[0]?.id);
      }
      return nextItems;
    });
  }

  async function saveAttachment(attachment: ChatAttachment, openAfterSave: boolean) {
    if (!attachment.content_base64) {
      setFileNotice("这个附件没有可保存的文件内容，请到文档下载页查看后端文件列表");
      setActiveView("files");
      void refreshGeneratedFiles();
      return;
    }

    if (window.enterpriseBridge?.saveBase64File) {
      const saved = await window.enterpriseBridge.saveBase64File({
        filename: attachment.filename,
        mimeType: attachment.mime_type,
        contentBase64: attachment.content_base64,
      });
      setFileNotice(`已保存：${saved.path}`);
      if (openAfterSave && window.enterpriseBridge?.openPath) {
        await window.enterpriseBridge.openPath(saved.path);
      }
      return;
    }

    const blob = base64ToBlob(attachment.content_base64, attachment.mime_type);
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = attachment.filename;
    link.click();
    URL.revokeObjectURL(href);
  }

  async function handleDownloadGeneratedFile(item: GeneratedFileItem, openAfterDownload: boolean) {
    if (!token || !item.downloadable) return;
    setFileNotice("");
    try {
      const saved = await downloadGeneratedFile(apiBase, token, item.id, item.name);
      setFileNotice(saved.path ? `已保存：${saved.path}` : `已下载：${saved.filename}`);
      if (openAfterDownload && saved.path && window.enterpriseBridge?.openPath) {
        await window.enterpriseBridge.openPath(saved.path);
      }
    } catch (error) {
      setFileNotice(getErrorMessage(error));
    }
  }

  if (!authReady) {
    return (
      <div className="bootScreen">
        <Sparkles size={22} />
        <span>正在启动企业内部工作台</span>
      </div>
    );
  }

  if (!token || !user) {
    return (
      <div className="loginShell">
        <header className="titlebar">
          <div className="brandMark">
            <Sparkles size={17} />
          </div>
          <span className="titlebarName">企业内部工作台</span>
          <WindowControls />
        </header>
        <main className="loginMain">
          <section className="loginPanel">
            <div className="loginCopy">
              <span className="eyebrow">Enterprise AI Workspace</span>
              <h1>企业内部工作台</h1>
              <p>登录后进入 AI 对话、自动化任务和当前支持应用。</p>
            </div>
            <form className="loginForm" onSubmit={handleLogin}>
              <label>
                <span>账号</span>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                />
              </label>
              <label>
                <span>密码</span>
                <div className="passwordField">
                  <input
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    onKeyDown={updateCapsLockState}
                    onKeyUp={updateCapsLockState}
                    type="password"
                    autoComplete="current-password"
                  />
                  {capsLockOn ? (
                    <span className="capsIcon" title="大写锁定已开启">
                      ⇧
                    </span>
                  ) : null}
                </div>
              </label>
              {loginError ? <div className="formError">{loginError}</div> : null}
              <button className="primaryButton" type="submit" disabled={loginPending}>
                {loginPending ? <Loader2 className="spin" size={17} /> : <LockKeyhole size={17} />}
                <span>{loginPending ? "正在登录" : "登录工作台"}</span>
              </button>
            </form>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="desktopShell">
      <header className="titlebar">
        <div className="brandMark">
          <Sparkles size={17} />
        </div>
        <span className="titlebarName">企业内部工作台</span>
        <button
          className="topIconButton"
          type="button"
          title={sidebarCollapsed ? "展开导航栏" : "折叠导航栏"}
          onClick={() => setSidebarCollapsed((value) => !value)}
        >
          {sidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
        </button>
        <div className="titlebarActions">
          <button
            className="floatingTrigger"
            type="button"
            title={rightPanelOpen ? "折叠任务详情" : "展开任务详情"}
            onClick={() => setRightPanelOpen((value) => !value)}
          >
            {rightPanelOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}
          </button>
          <button
            className="floatingTrigger"
            type="button"
            title="系统设置"
            onClick={() => {
              setSettingsOpen((value) => !value);
              setSettingsPanel(null);
              setUserMenuOpen(false);
            }}
          >
            <Settings size={17} />
          </button>
          <button
            className="avatarButton floatingTrigger"
            type="button"
            title="用户菜单"
            onClick={() => {
              setUserMenuOpen((value) => !value);
              setSettingsOpen(false);
            }}
          >
            {(user.display_name || user.username).slice(0, 1).toUpperCase()}
          </button>
          {settingsOpen ? (
            <div className="settingsPopover floatingSurface">
              <button
                type="button"
                onClick={() => {
                  setSettingsPanel("general");
                  setSettingsOpen(false);
                }}
              >
                <Settings size={15} />
                设置
              </button>
              <button
                type="button"
                onClick={() => {
                  setSettingsPanel("feedback");
                  setSettingsOpen(false);
                }}
              >
                <MessageSquareText size={15} />
                反馈
              </button>
              <button type="button" onClick={() => setStartupEnabled((value) => !value)}>
                <Check size={15} />
                开机自启动
                <span className={`miniSwitch ${startupEnabled ? "on" : ""}`}>
                  <span />
                </span>
              </button>
              <button type="button" onClick={() => void refreshWorkflows()}>
                <Workflow size={15} />
                刷新应用
              </button>
            </div>
          ) : null}
          {userMenuOpen ? (
            <div className="userPopover floatingSurface">
              <div className="userPopoverHeader">
                <div className="avatar large">{(user.display_name || user.username).slice(0, 1).toUpperCase()}</div>
                <div>
                  <strong>{user.display_name || user.username}</strong>
                  <span>
                    {roleLabel(user.role)} · {positionLabel(user.position)}
                  </span>
                </div>
              </div>
              <div className="userInfoRows">
                <span>账号：{user.username}</span>
                <span>部门：{user.department || "-"}</span>
                <span>邮箱：{user.email || "-"}</span>
              </div>
              <button type="button" onClick={clearSession}>
                <LogOut size={15} />
                退出登录
              </button>
            </div>
          ) : null}
          <WindowControls />
        </div>
      </header>

      <div className="workspace">
        <aside
          className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}
          style={{ width: sidebarCollapsed ? 58 : sidebarWidth }}
        >
          <nav className="navList" aria-label="主导航">
            <div className="navGroupLabel">工作区</div>
            {WORKSPACE_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={activeView === item.id ? "active" : ""}
                  title={sidebarCollapsed ? item.label : undefined}
                  onClick={() => activateWorkspace(item.id)}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
            <div className="conversationGroupHeader">
              <span>对话</span>
              <button type="button" title="新增对话" onClick={createNewConversation}>
                <Plus size={15} />
              </button>
            </div>
            <div className="conversationList">
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  className={activeConversationId === conversation.id && activeView === "chat" ? "active" : ""}
                  onClick={() => openConversation(conversation.id)}
                  onContextMenu={(event) => {
                    event.preventDefault();
                    setConversationMenu({
                      conversationId: conversation.id,
                      x: event.clientX,
                      y: event.clientY,
                    });
                  }}
                  title={sidebarCollapsed ? conversation.title : undefined}
                >
                  <MessageSquareText size={16} />
                  <span className="conversationText">
                    <span className="conversationTitle">{conversation.title}</span>
                    <span className="conversationTime">{relativeTime(conversation.updatedAt)}</span>
                  </span>
                </button>
              ))}
            </div>
          </nav>
          <div className="sidebarResizeHandle" onPointerDown={beginSidebarResize}>
            <GripVertical size={14} />
          </div>
        </aside>

        <main className="mainStage">
          {activeView === "chat" ? (
            <section className="chatView">
              <div className="messageList">
                {messages.length ? (
                  messages.map((message) => {
                    const downloadableAttachment = message.attachments?.find((attachment) =>
                      Boolean(attachment.content_base64),
                    );
                    const generatedArtifact = automationArtifactForMessage(message);
                    return (
                      <article key={message.id} className={`messageRow ${message.role}`}>
                        <div className="messageAvatar">{message.role === "user" ? "我" : <Bot size={16} />}</div>
                        <div className={`messageBubble ${message.role}`}>
                          <div className="messageMeta">
                            <span>{message.role === "user" ? "我" : "AI"}</span>
                            <div className="messageMetaRight">
                              {message.role === "assistant" ? (
                                <>
                                  <button type="button" title="复制回复" onClick={() => void copyText(message.content)}>
                                    <Copy size={14} />
                                  </button>
                                  {downloadableAttachment || generatedArtifact ? (
                                    <button
                                      type="button"
                                      title={generatedArtifact ? `下载 ${generatedArtifact.filename}` : "下载文件"}
                                      onClick={() => {
                                        if (generatedArtifact) {
                                          void handleDownloadSalaryWechatArtifact(message);
                                          return;
                                        }
                                        if (downloadableAttachment) void saveAttachment(downloadableAttachment, false);
                                      }}
                                    >
                                      <Download size={14} />
                                    </button>
                                  ) : null}
                                </>
                              ) : null}
                              <time>{formatTime(message.createdAt)}</time>
                            </div>
                          </div>
                          {message.businessProgress ? (
                            <div className="messageProgress">
                              {message.businessProgress.status === "running" ? (
                                <Loader2 className="spin" size={13} />
                              ) : (
                                <CircleAlert size={13} />
                              )}
                              <span>{message.businessProgress.label}</span>
                              {message.businessProgress.detail ? <small>{message.businessProgress.detail}</small> : null}
                            </div>
                          ) : null}
                          {message.content || !message.businessProgress ? (
                            <div className="messageContent">{message.content || "正在生成..."}</div>
                          ) : null}
                          {message.role === "assistant" ? (
                            <AutomationPlanCard
                              data={automationPlanForMessage(message)}
                              pending={automationPendingMessageId === message.id}
                              onConfirm={() => void handleConfirmSalaryWechat(message)}
                            />
                          ) : null}
                          {message.role === "assistant" && (message.intent || message.riskLevel) ? (
                            <div className="messageTags">
                              {message.intent ? <span>{message.intent}</span> : null}
                              {message.riskLevel ? <span>{riskLabel(message.riskLevel)}</span> : null}
                            </div>
                          ) : null}
                          {message.attachments?.some((attachment) => Boolean(attachment.content_base64)) ? (
                            <div className="attachmentList">
                              {message.attachments.filter((attachment) => Boolean(attachment.content_base64)).map((attachment) => (
                                <div className="attachmentItem" key={`${message.id}-${attachment.filename}`}>
                                  <FileText size={15} />
                                  <span>{attachment.filename}</span>
                                  <button
                                    type="button"
                                    title="浏览文件"
                                    onClick={() => void saveAttachment(attachment, true)}
                                  >
                                    <FolderOpen size={15} />
                                  </button>
                                  <button
                                    type="button"
                                    title="下载文件"
                                    onClick={() => void saveAttachment(attachment, false)}
                                  >
                                    <Download size={15} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </article>
                    );
                  })
                ) : (
                  <div className="emptyState">
                    <Bot size={28} />
                    <h2>开始一次企业 AI 对话</h2>
                  </div>
                )}
              </div>

              <div className="composer">
                {selectedFiles.length ? (
                  <div className="selectedFileList">
                    {selectedFiles.map((file, index) => (
                      <div className="selectedFile" key={`${file.name}-${file.lastModified}-${index}`}>
                        <FileText size={14} />
                        <span>{file.name}</span>
                        <button type="button" title="取消上传" onClick={() => removeSelectedFile(index)}>
                          <X size={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : null}
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={handleDraftKeyDown}
                  onCompositionStart={() => {
                    composingRef.current = true;
                  }}
                  onCompositionEnd={() => {
                    composingRef.current = false;
                  }}
                  placeholder="输入你要处理的问题或自动化指令"
                  rows={3}
                />
                <div className="composerActions">
                  <div className="composerToolGroup">
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
                    />
                    <button type="button" title="选择文件" onClick={() => fileInputRef.current?.click()}>
                      <Paperclip size={17} />
                    </button>
                    <button
                      type="button"
                      title="指定应用"
                      className={`floatingTrigger ${selectedWorkflow ? "activeTool" : ""}`}
                      onClick={() => setWorkflowPickerOpen((value) => !value)}
                    >
                      <AppWindow size={17} />
                    </button>
                    {workflowPickerOpen ? (
                      <div className="workflowPicker">
                        <button type="button" onClick={() => setSelectedWorkflowId("")}>
                          不指定应用
                        </button>
                        {workflows.map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            className={selectedWorkflowId === item.id ? "selected" : ""}
                            onClick={() => {
                              setSelectedWorkflowId(item.id);
                              setWorkflowPickerOpen(false);
                            }}
                          >
                            {item.name}
                          </button>
                        ))}
                      </div>
                    ) : null}
                    {selectedWorkflow ? <span className="toolText">{selectedWorkflow.name}</span> : null}
                    {selectedFiles.length ? <span className="toolText">{selectedFiles.length} 个文件</span> : null}
                  </div>
                  <div className="composerConversationBar">
                    <span>{activeConversation?.title || "AI 对话"}</span>
                    <button type="button" title="新增对话" onClick={createNewConversation}>
                      <Plus size={14} />
                    </button>
                  </div>
                  <div className="sendGroup">
                    <span className="positionText">{positionLabel(user.position)}</span>
                    <button
                      className={`sendButton ${isSending ? "stop" : ""}`}
                      type="button"
                      title={isSending ? "停止当前任务" : "发送"}
                      disabled={!isSending && !draft.trim()}
                      onClick={() => {
                        if (isSending) {
                          handleStopCurrentTask();
                          return;
                        }
                        void handleSend();
                      }}
                    >
                      {isSending ? <Square size={15} /> : <Send size={17} />}
                    </button>
                  </div>
                </div>
              </div>
            </section>
          ) : null}

          {activeView === "automation" ? (
            <section className="listView">
              <div className="stageHeader">
                <div>
                  <h1>自动化任务</h1>
                  <p>桌面端发起请求，后端执行岗位权限、应用启用、审批和审计。</p>
                </div>
                <button className="secondaryButton" type="button" onClick={() => activateWorkspace("chat")}>
                  <MessageSquareText size={16} />
                  <span>去对话发起</span>
                </button>
              </div>
              <WorkflowGrid
                items={workflows}
                loading={workflowsLoading}
                error={workflowsError}
                onRefresh={() => void refreshWorkflows()}
                onSelect={(id) => {
                  setSelectedWorkflowId(id);
                  activateWorkspace("chat");
                }}
              />
            </section>
          ) : null}

          {activeView === "apps" ? (
            <section className="listView">
              <div className="stageHeader">
                <div>
                  <h1>当前支持应用</h1>
                  <p>列表来自真实后端，按当前账号权限返回。</p>
                </div>
                <button className="secondaryButton" type="button" onClick={() => void refreshWorkflows()}>
                  <Loader2 className={workflowsLoading ? "spin" : ""} size={16} />
                  <span>刷新</span>
                </button>
              </div>
              <WorkflowGrid
                items={workflows}
                loading={workflowsLoading}
                error={workflowsError}
                onRefresh={() => void refreshWorkflows()}
                onSelect={(id) => setSelectedWorkflowId(id)}
              />
            </section>
          ) : null}

          {activeView === "files" ? (
            <section className="listView">
              <div className="stageHeader">
                <div>
                  <h1>文档下载</h1>
                  <p>查看后端保存的 AI 生成文件，按需下载或用本机软件打开。</p>
                </div>
                <button className="secondaryButton" type="button" onClick={() => void refreshGeneratedFiles()}>
                  <Loader2 className={filesLoading ? "spin" : ""} size={16} />
                  <span>刷新</span>
                </button>
              </div>
              <form className="fileToolbar" onSubmit={handleFileSearchSubmit}>
                <input
                  value={fileSearch}
                  onChange={(event) => setFileSearch(event.target.value)}
                  placeholder="搜索文件"
                />
                <div className="fileTypeSelect floatingTrigger">
                  <button type="button" onClick={() => setFileTypeMenuOpen((value) => !value)}>
                    {FILE_TYPE_LABELS[fileType]}
                    <ChevronRight size={14} />
                  </button>
                  {fileTypeMenuOpen ? (
                    <div className="fileTypeMenu floatingSurface">
                      {(Object.keys(FILE_TYPE_LABELS) as FileTypeFilter[]).map((item) => (
                        <button
                          key={item}
                          type="button"
                          className={fileType === item ? "active" : ""}
                          onClick={() => {
                            setFileTypeMenuOpen(false);
                            handleFileTypeChange(item);
                          }}
                        >
                          {FILE_TYPE_LABELS[item]}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
                <button type="submit">
                  查询
                </button>
              </form>
              <FileDownloadList
                items={generatedFiles}
                loading={filesLoading}
                error={filesError}
                notice={fileNotice}
                onDownload={(item) => void handleDownloadGeneratedFile(item, false)}
                onOpen={(item) => void handleDownloadGeneratedFile(item, true)}
              />
            </section>
          ) : null}
        </main>

        {rightPanelOpen ? (
          <aside className="detailPanel blankPanel" aria-label="任务详情留白">
            <div className="blankPanelHint">暂未开放</div>
          </aside>
        ) : null}

        {conversationMenu ? (
          <div
            className="contextMenu floatingSurface"
            style={{ left: conversationMenu.x, top: conversationMenu.y }}
            onClick={(event) => event.stopPropagation()}
          >
            <button type="button" onClick={() => openConversation(conversationMenu.conversationId)}>
              <MessageSquareText size={14} />
              打开
            </button>
            <button type="button" onClick={() => renameConversation(conversationMenu.conversationId)}>
              <Pencil size={14} />
              重命名
            </button>
            <button type="button" onClick={() => void copyConversationPath(conversationMenu.conversationId)}>
              <Copy size={14} />
              复制对话路径
            </button>
            <button
              type="button"
              onClick={() => {
                setConversationMenu(null);
                void copyText(conversationMenu.conversationId);
              }}
            >
              <Copy size={14} />
              复制对话 ID
            </button>
            <button type="button" className="danger" onClick={() => deleteConversation(conversationMenu.conversationId)}>
              <Trash2 size={14} />
              删除
            </button>
          </div>
        ) : null}
      </div>

      {settingsPanel ? (
        <div className="settingsPage">
          <aside className="settingsSide">
            <button type="button" className="backButton" onClick={() => setSettingsPanel(null)}>
              ← 返回应用
            </button>
            <button
              type="button"
              className={settingsPanel === "general" ? "active" : ""}
              onClick={() => setSettingsPanel("general")}
            >
              <Settings size={17} />
              常规
            </button>
            <button
              type="button"
              className={settingsPanel === "appearance" ? "active" : ""}
              onClick={() => setSettingsPanel("appearance")}
            >
              <Sparkles size={17} />
              外观
            </button>
            <button
              type="button"
              className={settingsPanel === "feedback" ? "active" : ""}
              onClick={() => setSettingsPanel("feedback")}
            >
              <MessageSquareText size={17} />
              反馈
            </button>
          </aside>
          <main className="settingsContent">
            {settingsPanel === "general" ? (
              <>
                <h1>常规</h1>
                <section className="settingsSection">
                  <div className="settingsRow">
                    <div>
                      <strong>开机自启动</strong>
                      <span>第一版先保存为本地偏好</span>
                    </div>
                    <button
                      type="button"
                      className={`switchButton ${startupEnabled ? "on" : ""}`}
                      onClick={() => setStartupEnabled((value) => !value)}
                    >
                      <span />
                    </button>
                  </div>
                </section>
              </>
            ) : null}

            {settingsPanel === "appearance" ? (
              <>
                <h1>外观</h1>
                <section className="settingsSection">
                  <div className="settingsRow">
                    <div>
                      <strong>主题</strong>
                      <span>先支持浅色和跟随系统，深色后续再完善</span>
                    </div>
                    <div className="segmented">
                      <button
                        type="button"
                        className={themeMode === "light" ? "active" : ""}
                        onClick={() => setThemeMode("light")}
                      >
                        浅色
                      </button>
                      <button
                        type="button"
                        className={themeMode === "system" ? "active" : ""}
                        onClick={() => setThemeMode("system")}
                      >
                        系统
                      </button>
                    </div>
                  </div>
                  <div className="settingsRow">
                    <div>
                      <strong>界面密度</strong>
                      <span>保持克制、紧凑、适合企业内部高频使用</span>
                    </div>
                    <span className="settingsValue">紧凑</span>
                  </div>
                </section>
              </>
            ) : null}

            {settingsPanel === "feedback" ? (
              <>
                <h1>反馈</h1>
                <form className="feedbackForm" onSubmit={handleFeedbackSubmit}>
                  <label>
                    <span>标题</span>
                    <input value={feedbackTitle} onChange={(event) => setFeedbackTitle(event.target.value)} />
                  </label>
                  <label>
                    <span>反馈内容</span>
                    <textarea
                      value={feedbackDescription}
                      onChange={(event) => setFeedbackDescription(event.target.value)}
                      rows={6}
                    />
                  </label>
                  {feedbackStatus ? <div className="feedbackStatus">{feedbackStatus}</div> : null}
                  <button type="submit" disabled={feedbackSubmitting}>
                    {feedbackSubmitting ? "正在提交" : "提交给管理员"}
                  </button>
                </form>
              </>
            ) : null}
          </main>
        </div>
      ) : null}
    </div>
  );
}

function WorkflowGrid({
  items,
  loading,
  error,
  onRefresh,
  onSelect,
}: {
  items: AiWorkflowItem[];
  loading: boolean;
  error: string;
  onRefresh: () => void;
  onSelect: (id: string) => void;
}) {
  if (loading) {
    return (
      <div className="emptyState inline">
        <Loader2 className="spin" size={24} />
        <h2>正在读取当前支持应用</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="emptyState inline">
        <CircleAlert size={24} />
        <h2>应用列表读取失败</h2>
        <p>{error}</p>
        <button className="secondaryButton" type="button" onClick={onRefresh}>
          <Loader2 size={16} />
          <span>重试</span>
        </button>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="emptyState inline">
        <ListChecks size={24} />
        <h2>暂无可用应用</h2>
      </div>
    );
  }

  return (
    <div className="workflowGrid">
      {items.map((item) => (
        <article className="workflowCard" key={item.id}>
          <div className="workflowTopline">
            <span>{item.position_label}</span>
            <span className={`stateBadge ${workflowStatusClass(item)}`}>{workflowStatusLabel(item)}</span>
          </div>
          <h2>{item.name}</h2>
          <p>{item.scenario}</p>
          <div className="workflowMeta">
            <span>{item.category}</span>
            <span>节省 {item.saved_minutes} 分钟</span>
          </div>
          <button type="button" onClick={() => onSelect(item.id)}>
            <Play size={15} />
            <span>{item.entry_label}</span>
          </button>
        </article>
      ))}
    </div>
  );
}

function AutomationPlanCard({
  data,
  pending,
  onConfirm,
}: {
  data: ReturnType<typeof automationPlanForMessage>;
  pending: boolean;
  onConfirm: () => void;
}) {
  if (!data) return null;

  const automationType = typeof data.automation.type === "string" ? data.automation.type : "";
  const contact = typeof data.automation.recipient_name === "string"
    ? data.automation.recipient_name
    : "待确认联系人";
  const status = salaryWechatStatusLabel(data.automation.status, data.automation.status_label);
  const filename = typeof data.automation.filename === "string" ? data.automation.filename : "";
  const artifactId = typeof data.automation.artifact_id === "string" ? data.automation.artifact_id : "";
  const rawStatus = typeof data.automation.status === "string" ? data.automation.status : "";
  const canGenerateFile = ["waiting_generation", "waiting_confirmation"].includes(rawStatus) && !artifactId;
  const isEnterpriseWechat = automationType === "enterprise_wechat_file_send" || automationType === "message_send";
  const canPrepareWechat = rawStatus === "waiting_wechat_confirmation" && Boolean(artifactId);
  const canRetryWechat = ["waiting_manual_send", "waiting_executor", "failed"].includes(rawStatus) && Boolean(artifactId);
  const buttonLabel = canPrepareWechat ? "确认发送" : canRetryWechat ? "重新发送" : "生成文件";
  const pendingLabel = canPrepareWechat || canRetryWechat ? "正在发送" : "正在生成文件";
  const title = isEnterpriseWechat
    ? "企业微信文件发送"
    : automationType === "agent_plan_execute"
      ? "财务月度资料微信发送"
      : "工资表微信发送准备";

  return (
    <div className="automationPlanCard">
      <div className="automationPlanHeader">
        <div>
          <strong>{title}</strong>
          <span>{filename ? `文件：${filename}` : `联系人：${contact}`}</span>
        </div>
        <span className="automationPlanStatus">{status}</span>
      </div>
      <div className="automationPlanSteps">
        {data.steps.map((step) => (
          <div key={String(step.key || step.label)} className="automationPlanStep">
            <Check size={13} />
            <span>{String(step.label || "业务步骤")}</span>
          </div>
        ))}
      </div>
      {data.artifacts.length ? (
        <div className="automationArtifactList">
          {data.artifacts.map((artifact) => (
            <span key={String(artifact.artifact_id || artifact.filename)}>
              {String(artifact.label || "文件")}：{String(artifact.filename || "-")}
            </span>
          ))}
        </div>
      ) : null}
      <p>{canPrepareWechat
        ? "文件已生成。确认后由后端通过企业微信发送文件，不附带正文说明。"
        : canRetryWechat
          ? "如果企业微信发送失败，可以重新确认发送；管理员可查看接口诊断和运行记录。"
          : "工资和财务数据属于敏感内容，文件生成后会在发送前让你确认一次。"}
      </p>
      {(canGenerateFile || canPrepareWechat || canRetryWechat) && contact !== "待确认联系人" ? (
        <button
          className="automationConfirmButton"
          type="button"
          disabled={pending}
          onClick={onConfirm}
        >
          {pending ? pendingLabel : buttonLabel}
        </button>
      ) : null}
    </div>
  );
}

function FileDownloadList({
  items,
  loading,
  error,
  notice,
  onDownload,
  onOpen,
}: {
  items: GeneratedFileItem[];
  loading: boolean;
  error: string;
  notice: string;
  onDownload: (item: GeneratedFileItem) => void;
  onOpen: (item: GeneratedFileItem) => void;
}) {
  if (loading) {
    return (
      <div className="emptyState inline">
        <Loader2 className="spin" size={24} />
        <h2>正在读取文档</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="emptyState inline">
        <CircleAlert size={24} />
        <h2>文档读取失败</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="fileListWrap">
      {notice ? <div className="fileNotice">{notice}</div> : null}
      {items.length ? (
        <div className="fileList">
          {items.map((item) => (
            <article className="fileRow" key={item.id}>
              <div className="fileIcon">
                <FileText size={17} />
              </div>
              <div className="fileMain">
                <strong>{item.name}</strong>
                <span>
                  {item.app_name} · {formatBytes(item.size_bytes)} · {formatDateTime(item.created_at)}
                </span>
              </div>
              <div className="fileActions">
                <button type="button" title="浏览文件" disabled={!item.downloadable} onClick={() => onOpen(item)}>
                  <ExternalLink size={16} />
                </button>
                <button type="button" title="下载文件" disabled={!item.downloadable} onClick={() => onDownload(item)}>
                  <Download size={16} />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="emptyState inline">
          <FileText size={24} />
          <h2>暂无可下载文档</h2>
        </div>
      )}
    </div>
  );
}

export default App;
