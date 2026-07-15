const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  username: string;
  role: "admin" | "employee";
  department: string | null;
  position: Position | null;
  capabilities: string[];
  erp_scopes: string[];
};

export type Position = "operations" | "customer_service" | "finance";

export type ChatResponse = {
  thread_id: string;
  answer: string;
  intent: string | null;
  risk_level: string | null;
  erp_references?: ErpReference[];
  approval_result: Record<string, unknown> | null;
};

export type ChatStreamPayload = {
  thread_id?: string;
  message?: string;
  node?: string;
  data?: unknown;
  content?: string;
  answer?: string;
  intent?: string | null;
  risk_level?: string | null;
  erp_references?: ErpReference[];
  approval_result?: Record<string, unknown> | null;
};

export type ChatStreamHandlers = {
  onStart?: (payload: ChatStreamPayload) => void;
  onNode?: (payload: ChatStreamPayload) => void;
  onContent?: (payload: ChatStreamPayload) => void;
  onDone?: (payload: ChatStreamPayload) => void;
  onError?: (payload: ChatStreamPayload) => void;
};

export type ApprovalItem = {
  id: string;
  thread_id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
};

export type RefundItem = {
  id: string;
  approval_id: string;
  order_no: string;
  amount_cents: number;
  status: string;
  created_at: string;
};

export type AuditLogItem = {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type UserItem = {
  id: string;
  username: string;
  role: "admin" | "employee";
  department: string | null;
  position: Position | null;
  capabilities: string[];
  erp_scopes: string[];
  created_at: string;
};

export type UserCreatePayload = {
  username: string;
  password: string;
  role: "admin" | "employee";
  position: Position | null;
  department?: string | null;
};

export type AutomationTaskItem = {
  task_id: string;
  label: string;
  placeholder: string;
  instruction: string;
  output_format: string;
  position: Position;
  position_label: string;
};

export type AutomationTasksResponse = {
  position: Position;
  position_label: string;
  items: AutomationTaskItem[];
};

export type AutomationGenerateResponse = {
  position: Position;
  position_label: string;
  task_id: string;
  task_label: string;
  answer: string;
};

export type ErpProviderItem = {
  provider: string;
  label: string;
  description: string;
  active: boolean;
  configured: boolean;
};

export type ErpProvidersResponse = {
  active_provider: string;
  items: ErpProviderItem[];
};

export type ErpResourceItem = {
  resource: string;
  label: string;
  description: string;
  provider_refs: Record<string, string>;
};

export type ErpScopesResponse = {
  provider: string;
  provider_label: string;
  position: Position | null;
  position_label: string;
  resources: ErpResourceItem[];
};

export type ErpStatusResponse = {
  provider: string;
  provider_label: string;
  ok: boolean;
  configured: boolean;
  status: string;
  message: string;
  detail: unknown;
};

export type ErpDiagnosticsConfigField = {
  name: string;
  configured: boolean;
  secret: boolean;
  value_preview: string | null;
  description: string;
};

export type ErpDiagnosticsProvider = {
  provider: string;
  label: string;
  description: string;
  active: boolean;
  configured: boolean;
  config_fields: ErpDiagnosticsConfigField[];
};

export type ErpDiagnosticsMappedResource = {
  resource: string;
  label: string;
  provider_resource: string | null;
  supported: boolean;
  fields: string[];
};

export type ErpDiagnosticsPositionMapping = {
  position: Position;
  position_label: string;
  resources: ErpDiagnosticsMappedResource[];
};

export type ErpDiagnosticsResponse = {
  active_provider: string;
  active_provider_label: string;
  active_configured: boolean;
  active_health: {
    ok: boolean;
    configured: boolean;
    status: string;
    message: string;
    detail?: unknown;
  };
  providers: ErpDiagnosticsProvider[];
  position_resource_mappings: ErpDiagnosticsPositionMapping[];
  local_development: Record<string, unknown>;
  next_steps: string[];
};

export type ErpQueryPayload = {
  resource: string;
  query?: string;
  filters?: Record<string, unknown> | unknown[] | null;
  limit?: number;
};

export type ErpQueryResponse = {
  ok: boolean;
  configured: boolean;
  status: string;
  provider: string;
  provider_label: string;
  resource: string;
  resource_label: string;
  provider_resource: string;
  message: string;
  items: Array<Record<string, unknown>>;
  raw: Record<string, unknown> | null;
};

export type ErpReference = {
  resource: string;
  resource_label: string;
  record_id: string;
  title: string;
  provider: string | null;
  provider_resource: string | null;
};

export type ErpDashboardMetric = {
  title: string;
  value: string | number;
  suffix: string;
  description: string;
  status: string;
};

export type ErpDashboardSection = {
  resource: string;
  resource_label: string;
  title: string;
  ok: boolean;
  status: string;
  message: string;
  total_count: number;
  amount_total: number | null;
  amount_label: string | null;
  items: Array<Record<string, unknown>>;
};

export type ErpDashboardOverviewResponse = {
  provider: string;
  provider_label: string;
  role: "admin" | "employee";
  position: Position | null;
  position_label: string;
  market: string;
  market_label: string;
  store: string;
  store_label: string;
  date_range: string;
  date_range_label: string;
  title: string;
  message: string;
  metrics: ErpDashboardMetric[];
  sections: ErpDashboardSection[];
};

export type ErpRecordDetailResponse = {
  ok: boolean;
  provider: string;
  provider_label: string;
  resource: string;
  resource_label: string;
  provider_resource: string;
  record_id: string;
  message: string;
  item: Record<string, unknown> | null;
};

export async function sendPublicLLMChatStream(
  message: string,
  history: PublicLLMMessage[],
  onContent: (content: string) => void,
) {
  const response = await fetch(`${API_BASE_URL}/public/llm/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (!response.body) {
    throw new Error("浏览器不支持流式读取");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      dispatchPublicLLMStreamEvent(block, onContent);
    }
  }

  buffer += decoder.decode();

  if (buffer.trim()) {
    dispatchPublicLLMStreamEvent(buffer, onContent);
  }
}

function dispatchPublicLLMStreamEvent(
  block: string,
  onContent: (content: string) => void,
) {
  const parsed = parseStreamEvent(block);

  if (!parsed) {
    return;
  }

  if (parsed.event === "content") {
    onContent(parsed.data.content || "");
    return;
  }

  if (parsed.event === "error") {
    throw new Error(parsed.data.message || "大模型流式输出失败");
  }
}

export type ThreadMessageItem = {
  id: string;
  thread_id: string;
  user_id: string | null;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ThreadDetailResponse = {
  thread: Record<string, unknown>;
  summary: Record<string, unknown>;
  state: Record<string, unknown>;
  memories: Array<Record<string, unknown>>;
  messages: ThreadMessageItem[];
};

export type PublicLLMMessage = {
  role: "user" | "assistant";
  content: string;
};

export type PublicLLMChatResponse = {
  answer: string;
};

type JsonValue = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

const AUTH_EXPIRED_EVENT = "company-rag-auth-expired";

export class AuthExpiredError extends Error {
  readonly status = 401;

  constructor(message = "登录失效，需要重新登录") {
    super(message);
    this.name = "AuthExpiredError";
  }
}

export function isAuthExpiredError(error: unknown): error is AuthExpiredError {
  return error instanceof AuthExpiredError;
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  token = "",
): Promise<T> {
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw await buildRequestError(response, Boolean(token));
  }

  return response.json();
}

async function buildRequestError(response: Response, authenticatedRequest: boolean) {
  const message = await readErrorMessage(response);

  if (authenticatedRequest && response.status === 401) {
    emitAuthExpired(message);
    return new AuthExpiredError(message || "登录失效，需要重新登录");
  }

  return new Error(message);
}

function emitAuthExpired(message: string) {
  window.dispatchEvent(
    new CustomEvent(AUTH_EXPIRED_EVENT, {
      detail: {
        message: message || "登录失效，需要重新登录",
      },
    }),
  );
}

async function readErrorMessage(response: Response) {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : "请求失败";
  } catch {
    return "请求失败";
  }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const formData = new URLSearchParams();

  formData.append("username", username);
  formData.append("password", password);

  return requestJson<LoginResponse>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
  });
}

export async function sendPublicLLMChat(
  message: string,
  history: PublicLLMMessage[],
): Promise<PublicLLMChatResponse> {
  return requestJson<PublicLLMChatResponse>("/public/llm/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      history,
    }),
  });
}

export async function sendChat(
  token: string,
  message: string,
  threadId?: string,
): Promise<ChatResponse> {
  const body: JsonValue = {
    message,
    thread_id: threadId || null,
  };

  return requestJson<ChatResponse>(
    "/chat",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    },
    token,
  );
}

export async function sendChatStream(
  token: string,
  message: string,
  threadId: string | undefined,
  handlers: ChatStreamHandlers,
) {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      thread_id: threadId || null,
    }),
  });

  if (!response.ok) {
    throw await buildRequestError(response, true);
  }

  if (!response.body) {
    throw new Error("浏览器不支持流式读取");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      dispatchStreamEvent(block, handlers);
    }
  }

  buffer += decoder.decode();

  if (buffer.trim()) {
    dispatchStreamEvent(buffer, handlers);
  }
}

function dispatchStreamEvent(block: string, handlers: ChatStreamHandlers) {
  const parsed = parseStreamEvent(block);

  if (!parsed) {
    return;
  }

  if (parsed.event === "start") {
    handlers.onStart?.(parsed.data);
    return;
  }

  if (parsed.event === "node") {
    handlers.onNode?.(parsed.data);
    return;
  }

  if (parsed.event === "content") {
    handlers.onContent?.(parsed.data);
    return;
  }

  if (parsed.event === "done") {
    handlers.onDone?.(parsed.data);
    return;
  }

  if (parsed.event === "error") {
    handlers.onError?.(parsed.data);
  }
}

function parseStreamEvent(block: string): { event: string; data: ChatStreamPayload } | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  try {
    return {
      event,
      data: JSON.parse(dataLines.join("\n")) as ChatStreamPayload,
    };
  } catch {
    return {
      event,
      data: {
        message: dataLines.join("\n"),
      },
    };
  }
}

export async function uploadDocument(
  token: string,
  file: File,
  visibility: "admin" | "employee",
  department: string,
) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("visibility", visibility);

  if (department.trim()) {
    formData.append("department", department.trim());
  }

  return requestJson<Record<string, unknown>>(
    "/admin/documents/upload",
    {
      method: "POST",
      body: formData,
    },
    token,
  );
}

export async function listApprovals(token: string) {
  return requestJson<{ items: ApprovalItem[] }>("/admin/approvals", {}, token);
}

export async function reviewApproval(token: string, approvalId: string, approved: boolean) {
  return requestJson<Record<string, unknown>>(
    `/admin/approvals/${approvalId}/review`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ approved }),
    },
    token,
  );
}

export async function listRefunds(token: string) {
  return requestJson<{ items: RefundItem[] }>("/admin/refunds", {}, token);
}

export async function listAuditLogs(
  token: string,
  filters: { action?: string; resource_type?: string; position?: Position | "all"; limit?: number } = {},
) {
  const params = new URLSearchParams();

  if (filters.action?.trim()) {
    params.set("action", filters.action.trim());
  }

  if (filters.resource_type?.trim()) {
    params.set("resource_type", filters.resource_type.trim());
  }

  if (filters.position && filters.position !== "all") {
    params.set("position", filters.position);
  }

  params.set("limit", String(filters.limit || 50));

  return requestJson<{ items: AuditLogItem[] }>(`/admin/audit-logs?${params}`, {}, token);
}

export async function listUsers(token: string) {
  return requestJson<{ items: UserItem[] }>("/admin/users", {}, token);
}

export async function createUser(token: string, payload: UserCreatePayload) {
  return requestJson<{ item: UserItem }>(
    "/admin/users",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listAutomationTasks(token: string) {
  return requestJson<AutomationTasksResponse>("/automation/tasks", {}, token);
}

export async function generateAutomation(
  token: string,
  taskId: string,
  inputText: string,
) {
  return requestJson<AutomationGenerateResponse>(
    "/automation/generate",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        task_id: taskId,
        input_text: inputText,
      }),
    },
    token,
  );
}

export async function transformFinanceExcel(
  token: string,
  file: File,
  instruction: string,
) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("instruction", instruction.trim());

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/automation/finance/excel-transform`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    throw await buildRequestError(response, true);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";

  return {
    blob,
    filename: parseDownloadFilename(disposition) || "finance_ai_result.xlsx",
  };
}

export async function listErpProviders(token: string) {
  return requestJson<ErpProvidersResponse>("/erp/providers", {}, token);
}

export async function getErpStatus(token: string) {
  return requestJson<ErpStatusResponse>("/erp/status", {}, token);
}

export async function getErpScopes(token: string) {
  return requestJson<ErpScopesResponse>("/erp/scopes", {}, token);
}

export async function getErpDiagnostics(token: string) {
  return requestJson<ErpDiagnosticsResponse>("/erp/diagnostics", {}, token);
}

export async function getErpDashboardOverview(token: string, market = "all", dateRange = "all", store = "all") {
  const params = new URLSearchParams({ market, date_range: dateRange, store });
  return requestJson<ErpDashboardOverviewResponse>(`/erp/dashboard-overview?${params}`, {}, token);
}

export async function getErpRecordDetail(token: string, resource: string, recordId: string) {
  return requestJson<ErpRecordDetailResponse>(
    `/erp/records/${encodeURIComponent(resource)}/${encodeURIComponent(recordId)}`,
    {},
    token,
  );
}

export async function queryErp(token: string, payload: ErpQueryPayload) {
  return requestJson<ErpQueryResponse>(
    "/erp/query",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

function parseDownloadFilename(contentDisposition: string) {
  const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      return encodedMatch[1];
    }
  }

  const normalMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return normalMatch?.[1] || "";
}

export async function getThreadMessages(token: string, threadId: string) {
  return requestJson<ThreadDetailResponse>(
    `/threads/${encodeURIComponent(threadId)}/messages`,
    {},
    token,
  );
}
