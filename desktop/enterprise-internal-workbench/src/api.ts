const ENV_API_BASE_URL = String(import.meta.env.VITE_API_BASE_URL || "").trim();

export const REMOTE_API_BASE_URL = ENV_API_BASE_URL || "http://127.0.0.1:8001";

export const DEFAULT_API_BASE_URL =
  ENV_API_BASE_URL ||
  (typeof window !== "undefined" && window.enterpriseBridge ? REMOTE_API_BASE_URL : "/api");

export type Position = "operations" | "customer_service" | "finance";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  id: string;
  username: string;
  display_name: string | null;
  email: string | null;
  role: "admin" | "employee";
  department: string | null;
  position: Position | null;
  capabilities: string[];
  erp_scopes: string[];
  allowed_ai_app_ids: string[];
};

export type UserSettingsItem = {
  id: string;
  username: string;
  role: "admin" | "employee";
  department: string | null;
  position: Position | null;
  display_name: string | null;
  email: string | null;
  created_at: string;
};

export type ChatAttachment = {
  type?: string;
  filename: string;
  mime_type?: string;
  size_bytes?: number;
  content_base64?: string;
  metadata?: Record<string, unknown>;
};

export type ErpReference = {
  provider: string;
  resource: string;
  record_id: string;
  title: string;
  summary: string;
  metadata?: Record<string, unknown>;
};

export type ChatResponse = {
  thread_id: string;
  answer: string;
  intent: string | null;
  risk_level: string | null;
  erp_references?: ErpReference[];
  attachments?: ChatAttachment[];
  platform_draft?: Record<string, unknown> | null;
  approval_result: Record<string, unknown> | null;
  automation?: Record<string, unknown> | null;
};

export type BusinessProgressPayload = {
  thread_id?: string;
  workflow_id?: string;
  step_key?: string;
  label?: string;
  status?: string;
  detail?: string | null;
  data?: Record<string, unknown>;
};

export type ChatStreamPayload = ChatResponse & {
  thread_id?: string;
  message?: string;
  node?: string;
  data?: unknown;
  content?: string;
  business_progress?: BusinessProgressPayload;
  status?: string;
  status_label?: string;
  filename?: string;
  artifact_id?: string | null;
  download_path?: string | null;
  recipient_name?: string;
  plan?: Record<string, unknown>;
  execution?: Record<string, unknown>;
};

export type ChatStreamHandlers = {
  onStart?: (payload: ChatStreamPayload) => void;
  onBusinessProgress?: (payload: BusinessProgressPayload) => void;
  onNode?: (payload: ChatStreamPayload) => void;
  onContent?: (payload: ChatStreamPayload) => void;
  onDone?: (payload: ChatStreamPayload) => void;
  onError?: (payload: ChatStreamPayload) => void;
  signal?: AbortSignal;
};

export type GeneratedFileItem = {
  id: string;
  run_id: string;
  artifact_type: string;
  name: string;
  mime_type: string | null;
  size_bytes: number | null;
  external_ref: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  expires_at: string | null;
  downloadable: boolean;
  app_id: string;
  app_name: string;
  run_type: string;
  status: string;
  username: string | null;
  position: Position | null;
};

export type GeneratedFilesResponse = {
  items: GeneratedFileItem[];
};

export type GeneratedFileFilters = {
  search?: string;
  dateRange?: "today" | "7d" | "30d" | "all";
  fileType?: "all" | "excel" | "word";
  limit?: number;
};

export type FeedbackCreatePayload = {
  category: "功能建议" | "体验问题" | "数据问题" | "自动化需求" | "权限流程" | "其他";
  priority: "low" | "normal" | "high" | "urgent";
  title: string;
  description: string;
};

export type FeedbackItem = {
  id: string;
  category: string;
  priority: string;
  title: string;
  description: string;
  status: string;
  created_at: string | null;
};

export type SalaryWechatSendResponse = {
  run_id: string;
  status: string;
  status_label: string;
  answer: string;
  filename: string;
  artifact_id: string | null;
  download_path: string | null;
  recipient_name: string;
  plan: Record<string, unknown>;
  execution: Record<string, unknown>;
};

export type SalaryWechatStatusResponse = {
  run_id: string;
  run_status: string;
  status: string;
  status_label: string;
  answer?: string | null;
  filename?: string | null;
  artifact_id?: string | null;
  download_path?: string | null;
  recipient_name?: string | null;
  executor_type?: string | null;
  manual_final_send_required: boolean;
  steps: Record<string, unknown>[];
  logs: Record<string, unknown>[];
};

export type WechatAttachmentPrepareResponse = {
  run_id: string;
  status: string;
  status_label: string;
  answer: string;
  filename: string;
  artifact_id: string;
  download_path: string | null;
  recipient_name: string;
  execution: Record<string, unknown>;
};

export type EnterpriseWechatSendConfirmResponse = {
  run_id: string;
  status: string;
  status_label: string;
  answer: string;
  filename: string;
  artifact_id: string;
  download_path: string | null;
  recipient_name: string;
  execution: Record<string, unknown>;
};

export type AiWorkflowStage = {
  key: string;
  label: string;
  description: string;
  automated: boolean;
};

export type AiWorkflowItem = {
  id: string;
  name: string;
  position: Position;
  position_label: string;
  category: string;
  scenario: string;
  business_value: string;
  trigger_type: string;
  automation_level: string;
  execution_mode: string;
  entry_view: string;
  entry_label: string;
  source_task_id: string;
  input_placeholder: string;
  output_contract: string;
  requires_approval: boolean;
  approval_policy: string;
  tools: string[];
  erp_resources: string[];
  writeback_target: string;
  notification_target: string;
  saved_minutes: number;
  version: string;
  executable: boolean;
  stages: AiWorkflowStage[];
};

export type AiWorkflowsResponse = {
  items: AiWorkflowItem[];
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/+$/, "");
}

function buildUrl(baseUrl: string, path: string, useDesktopBridge: boolean) {
  const normalized = normalizeBaseUrl(baseUrl);
  if (normalized.startsWith("/")) {
    return useDesktopBridge ? `${REMOTE_API_BASE_URL}${path}` : `${normalized}${path}`;
  }
  return `${normalized}${path}`;
}

async function parseError(response: { status: number; statusText: string; body: string }) {
  if (!response.body) return response.statusText || "请求失败";
  if (response.body.trim().startsWith("<")) {
    const title = response.body.match(/<h1>(.*?)<\/h1>/i)?.[1] ?? response.statusText;
    return `${response.status} ${title || "请求失败"}`;
  }
  try {
    const data = JSON.parse(response.body) as { detail?: unknown; message?: unknown };
    const detail = data.detail ?? data.message;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => JSON.stringify(item)).join("\n");
    if (detail) return JSON.stringify(detail);
  } catch {
    return response.body;
  }
  return response.statusText || "请求失败";
}

async function requestJson<T>(
  baseUrl: string,
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {};
  const optionHeaders = new Headers(options.headers);

  optionHeaders.forEach((value, key) => {
    headers[key] = value;
  });

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const body = typeof options.body === "string" ? options.body : undefined;
  const method = options.method ?? "GET";
  const useDesktopBridge = Boolean(window.enterpriseBridge?.apiRequest);
  const url = buildUrl(baseUrl, path, useDesktopBridge);

  if (useDesktopBridge && window.enterpriseBridge?.apiRequest) {
    const response = await window.enterpriseBridge.apiRequest({
      url,
      method,
      headers,
      body,
    });

    if (!response.ok) {
      throw new ApiError(await parseError(response), response.status);
    }

    return response.body ? (JSON.parse(response.body) as T) : ({} as T);
  }

  const response = await fetch(url, {
    ...options,
    method,
    headers,
    body,
  });
  const responseBody = await response.text();

  if (!response.ok) {
    throw new ApiError(
      await parseError({
        status: response.status,
        statusText: response.statusText,
        body: responseBody,
      }),
      response.status,
    );
  }

  return responseBody ? (JSON.parse(responseBody) as T) : ({} as T);
}

export async function login(baseUrl: string, username: string, password: string) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  return requestJson<LoginResponse>(baseUrl, "/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });
}

export async function getMySettings(baseUrl: string, token: string) {
  return requestJson<{ item: UserSettingsItem }>(baseUrl, "/settings/me", {}, token);
}

export async function listAiWorkflows(baseUrl: string, token: string) {
  return requestJson<AiWorkflowsResponse>(baseUrl, "/ai-workflows", {}, token);
}

export async function listGeneratedFiles(
  baseUrl: string,
  token: string,
  filters: GeneratedFileFilters = {},
) {
  const params = new URLSearchParams();
  if (filters.search?.trim()) {
    params.set("search", filters.search.trim());
  }
  params.set("date_range", filters.dateRange || "30d");
  params.set("file_type", filters.fileType || "all");
  params.set("limit", String(filters.limit || 80));
  return requestJson<GeneratedFilesResponse>(baseUrl, `/files?${params}`, {}, token);
}

export async function submitFeedback(
  baseUrl: string,
  token: string,
  payload: FeedbackCreatePayload,
) {
  return requestJson<{ item: FeedbackItem }>(
    baseUrl,
    "/feedback",
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

function parseDownloadFilename(disposition: string, fallback: string) {
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  return plainMatch?.[1] || fallback;
}

export async function downloadGeneratedFile(
  baseUrl: string,
  token: string,
  artifactId: string,
  fallbackFilename = "generated_file",
) {
  const useDesktopBridge = Boolean(window.enterpriseBridge?.downloadFile);
  const url = buildUrl(
    baseUrl,
    `/files/${encodeURIComponent(artifactId)}/download`,
    useDesktopBridge,
  );
  const headers = {
    Authorization: `Bearer ${token}`,
  };

  if (useDesktopBridge && window.enterpriseBridge?.downloadFile) {
    return window.enterpriseBridge.downloadFile({
      url,
      headers,
      filename: fallbackFilename,
    });
  }

  const response = await fetch(url, {
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(body || response.statusText, response.status);
  }

  const blob = await response.blob();
  const filename = parseDownloadFilename(
    response.headers.get("content-disposition") || "",
    fallbackFilename,
  );
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(href);

  return {
    filename,
    path: "",
  };
}

export async function sendChat(
  baseUrl: string,
  token: string,
  message: string,
  threadId?: string,
) {
  return requestJson<ChatResponse>(
    baseUrl,
    "/chat",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        thread_id: threadId || null,
      }),
    },
    token,
  );
}

export async function sendChatStream(
  baseUrl: string,
  token: string,
  message: string,
  threadId: string | undefined,
  handlers: ChatStreamHandlers,
) {
  await readSseStream(
    baseUrl,
    "/chat/stream",
    {
      message,
      thread_id: threadId || null,
    },
    token,
    handlers,
  );
}

export async function prepareSalaryWechatSend(
  baseUrl: string,
  token: string,
  payload: {
    message: string;
    recipientName?: string | null;
    recipientConfirmed?: boolean;
    sensitiveDataConfirmed?: boolean;
  },
) {
  return requestJson<SalaryWechatSendResponse>(
    baseUrl,
    "/automation/finance/salary-wechat-send",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: payload.message,
        recipient_name: payload.recipientName || null,
        recipient_confirmed: Boolean(payload.recipientConfirmed),
        sensitive_data_confirmed: Boolean(payload.sensitiveDataConfirmed),
      }),
    },
    token,
  );
}

export async function prepareSalaryWechatSendStream(
  baseUrl: string,
  token: string,
  payload: {
    message: string;
    recipientName?: string | null;
    recipientConfirmed?: boolean;
    sensitiveDataConfirmed?: boolean;
  },
  handlers: ChatStreamHandlers,
) {
  await readSseStream(
    baseUrl,
    "/automation/finance/salary-wechat-send/stream",
    {
      message: payload.message,
      recipient_name: payload.recipientName || null,
      recipient_confirmed: Boolean(payload.recipientConfirmed),
      sensitive_data_confirmed: Boolean(payload.sensitiveDataConfirmed),
    },
    token,
    handlers,
  );
}

export async function prepareWechatAttachment(
  baseUrl: string,
  token: string,
  payload: {
    artifactId: string;
    recipientName: string;
    filename?: string | null;
    sourceMessage?: string | null;
    sourceWorkflowId?: string | null;
  },
) {
  return requestJson<WechatAttachmentPrepareResponse>(
    baseUrl,
    "/automation/finance/wechat-attachment/prepare",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        artifact_id: payload.artifactId,
        recipient_name: payload.recipientName,
        filename: payload.filename || null,
        source_message: payload.sourceMessage || null,
        source_workflow_id: payload.sourceWorkflowId || null,
        recipient_confirmed: true,
        sensitive_data_confirmed: true,
      }),
    },
    token,
  );
}

export async function confirmEnterpriseWechatFileSend(
  baseUrl: string,
  token: string,
  payload: {
    artifactId: string;
    artifactIds?: string[];
    recipientName: string;
    filename?: string | null;
    sourceMessage?: string | null;
    sourceMessageId?: string | null;
    sourceWorkflowId?: string | null;
    threadId?: string | null;
    recipient?: Record<string, unknown> | null;
    recipientCandidateId?: string | null;
    sensitiveDataConfirmed?: boolean;
  },
) {
  return requestJson<EnterpriseWechatSendConfirmResponse>(
    baseUrl,
    "/automation/files/enterprise-wechat-send/confirm",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        artifact_id: payload.artifactId,
        artifact_ids: payload.artifactIds || [],
        recipient_name: payload.recipientName,
        recipient_candidate_id: payload.recipientCandidateId || null,
        recipient: payload.recipient || null,
        filename: payload.filename || null,
        source_message: payload.sourceMessage || null,
        source_message_id: payload.sourceMessageId || null,
        source_workflow_id: payload.sourceWorkflowId || null,
        thread_id: payload.threadId || null,
        recipient_confirmed: true,
        sensitive_data_confirmed: payload.sensitiveDataConfirmed ?? true,
      }),
    },
    token,
  );
}

export async function getSalaryWechatStatus(
  baseUrl: string,
  token: string,
  runId: string,
) {
  return requestJson<SalaryWechatStatusResponse>(
    baseUrl,
    `/automation/finance/salary-wechat-send/${encodeURIComponent(runId)}/status`,
    {},
    token,
  );
}

async function readSseStream(
  baseUrl: string,
  path: string,
  payload: Record<string, unknown>,
  token: string,
  handlers: ChatStreamHandlers,
) {
  const useDesktopStream = Boolean(window.enterpriseBridge?.apiStream);
  const url = buildUrl(baseUrl, path, useDesktopStream);
  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  const body = JSON.stringify(payload);
  let buffer = "";

  const appendChunk = (chunk: string) => {
    buffer += chunk;
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      dispatchStreamEvent(block, handlers);
    }
  };

  if (useDesktopStream && window.enterpriseBridge?.apiStream) {
    const bridge = window.enterpriseBridge;
    if (handlers.signal?.aborted) {
      throw new DOMException("已停止当前任务", "AbortError");
    }
    const requestId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `stream-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const abortStream = () => bridge.abortApiStream?.(requestId);
    handlers.signal?.addEventListener("abort", abortStream, { once: true });
    const response = await (async () => {
      try {
        return await bridge.apiStream(
          {
            url,
            method: "POST",
            headers,
            body,
            requestId,
          },
          appendChunk,
        );
      } finally {
        handlers.signal?.removeEventListener("abort", abortStream);
      }
    })();

    if (handlers.signal?.aborted) {
      throw new DOMException("已停止当前任务", "AbortError");
    }

    if (!response.ok) {
      throw new ApiError(await parseError(response), response.status);
    }

    if (buffer.trim()) {
      dispatchStreamEvent(buffer, handlers);
      buffer = "";
    }
    return;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body,
    signal: handlers.signal,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(body || response.statusText, response.status);
  }

  if (!response.body) {
    throw new ApiError("当前环境不支持流式读取", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    appendChunk(decoder.decode(value, { stream: true }));
  }

  appendChunk(decoder.decode());
  if (buffer.trim()) {
    dispatchStreamEvent(buffer, handlers);
  }
}

function dispatchStreamEvent(block: string, handlers: ChatStreamHandlers) {
  const parsed = parseStreamEvent(block);
  if (!parsed) return;

  if (parsed.event === "start") {
    handlers.onStart?.(parsed.data);
    return;
  }

  if (parsed.event === "business_progress") {
    handlers.onBusinessProgress?.(parsed.data as BusinessProgressPayload);
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

  if (!dataLines.length) return null;

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
      } as ChatStreamPayload,
    };
  }
}
