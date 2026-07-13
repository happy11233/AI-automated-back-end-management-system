const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type ChatResponse = {
  thread_id: string;
  answer: string;
  intent: string | null;
  risk_level: string | null;
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
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
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

export async function listAuditLogs(token: string) {
  return requestJson<{ items: AuditLogItem[] }>("/admin/audit-logs", {}, token);
}

export async function getThreadMessages(token: string, threadId: string) {
  return requestJson<ThreadDetailResponse>(
    `/threads/${encodeURIComponent(threadId)}/messages`,
    {},
    token,
  );
}
