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

export type AutomationFlowStepItem = {
  id: string;
  name: string;
  inputs: string[];
  retryable: boolean;
};

export type AutomationFlowItem = {
  id: string;
  app_id: string;
  name: string;
  description: string;
  category: string;
  position: Position | null;
  position_label: string;
  status: string;
  version: string;
  publish_status: string;
  owner: string;
  trigger_type: string;
  entrypoint: string;
  input_schema: Array<Record<string, unknown>>;
  output_schema: Array<Record<string, unknown>>;
  prompt_summary: string;
  prompt_template_preview: string;
  model_config: Record<string, unknown>;
  allowed_tools: string[];
  allowed_erp_resources: ErpResourceItem[];
  permission_rules: string[];
  approval_policy: string;
  failure_strategy: string;
  steps: AutomationFlowStepItem[];
  source: string;
};

export type AutomationFlowsResponse = {
  items: AutomationFlowItem[];
};

export type AutomationFlowDetailResponse = {
  item: AutomationFlowItem;
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

export type AiWorkflowDetailResponse = {
  item: AiWorkflowItem;
};

export type AiWorkflowRunStep = {
  step_order: number;
  step_name: string;
  status: "running" | "succeeded" | "failed" | "blocked" | string;
  duration_ms: number;
};

export type AiWorkflowRunResponse = {
  run_id: string;
  workflow: AiWorkflowItem;
  status: "succeeded" | "failed" | "blocked" | string;
  answer: string;
  erp_references: ErpReference[];
  steps: AiWorkflowRunStep[];
  created_at: string;
};

export type ConnectorConfigField = {
  name: string;
  configured: boolean;
  secret: boolean;
  value_preview: string | null;
  description: string;
};

export type ConnectorResourceItem = {
  resource: string;
  label: string;
  provider_resource: string | null;
  position_scopes: Array<Position | "platform">;
  position_scope_labels: string[];
  fields: string[];
};

export type ConnectorItem = {
  id: string;
  label: string;
  category: string;
  description: string;
  active: boolean;
  configured: boolean;
  status: string;
  health_status: string;
  health_message: string;
  auth_type: string;
  admin_only: boolean;
  supports_real_health_check: boolean;
  managed_by: string;
  capabilities: string[];
  position_scopes: Array<Position | "platform">;
  position_scope_labels: string[];
  config_fields: ConnectorConfigField[];
  resources: ConnectorResourceItem[];
  next_steps: string[];
  last_checked_at: string;
};

export type ConnectorsSummary = {
  total: number;
  configured: number;
  healthy: number;
  needs_config: number;
  pending: number;
};

export type ConnectorsResponse = {
  summary: ConnectorsSummary;
  items: ConnectorItem[];
};

export type ConnectorDetailResponse = {
  item: ConnectorItem;
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

export type RunRecordItem = {
  id: string;
  run_type: string;
  app_id: string;
  app_name: string;
  entrypoint: string;
  status: "running" | "succeeded" | "failed" | "blocked";
  user_id: string | null;
  username: string | null;
  role: "admin" | "employee" | null;
  position: Position | null;
  thread_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  input_preview: string | null;
  output_preview: string | null;
  error_message: string | null;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
  step_count: number;
  artifact_count: number;
};

export type RunRecordStepItem = {
  id: string;
  run_id: string;
  step_order: number;
  step_name: string;
  status: "running" | "succeeded" | "failed" | "blocked";
  provider: string | null;
  resource_type: string | null;
  resource_id: string | null;
  input_preview: string | null;
  output_preview: string | null;
  error_message: string | null;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
};

export type RunRecordArtifactItem = {
  id: string;
  run_id: string;
  artifact_type: string;
  name: string;
  mime_type: string | null;
  size_bytes: number | null;
  external_ref: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type RunRecordsResponse = {
  items: RunRecordItem[];
};

export type RunRecordDetailResponse = {
  run: RunRecordItem;
  steps: RunRecordStepItem[];
  artifacts: RunRecordArtifactItem[];
};

export type RunRecordFilters = {
  status?: string;
  run_type?: string;
  app_id?: string;
  position?: Position | "all";
  resource_type?: string;
  resource_id?: string;
  limit?: number;
};

export type EffectAnalyticsScope = {
  role: "admin" | "employee" | null;
  position: Position | null;
  position_label: string;
  date_range: string;
  date_range_label: string;
  since: string | null;
  generated_at: string;
};

export type EffectAnalyticsSummary = {
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  running_runs: number;
  success_rate: number;
  failure_rate: number;
  blocked_rate: number;
  avg_duration_ms: number;
  total_duration_ms: number;
  estimated_saved_minutes: number;
  estimated_saved_hours: number;
};

export type EffectStatusBucket = {
  status: string;
  count: number;
};

export type EffectTrendPoint = {
  date: string;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
};

export type EffectPositionStat = {
  position: Position | "platform";
  position_label: string;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  success_rate: number;
  estimated_saved_minutes: number;
};

export type EffectAppStat = {
  app_id: string;
  app_name: string;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  success_rate: number;
  last_run_at: string | null;
};

export type EffectRunTypeStat = {
  run_type: string;
  label: string;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  success_rate: number;
  avg_duration_ms: number;
};

export type EffectFailureReason = {
  status: string;
  reason: string;
  count: number;
  last_seen_at: string | null;
};

export type EffectAuditAction = {
  action: string;
  resource_type: string | null;
  count: number;
  last_seen_at: string | null;
};

export type EffectAuditSummary = {
  total_events: number;
  blocked_events: number;
  approval_events: number;
  top_actions: EffectAuditAction[];
};

export type EffectEstimateModelItem = {
  run_type: string;
  saved_minutes_per_run: number;
  description: string;
};

export type EffectAnalyticsResponse = {
  scope: EffectAnalyticsScope;
  summary: EffectAnalyticsSummary;
  status_distribution: EffectStatusBucket[];
  trend: EffectTrendPoint[];
  position_ranking: EffectPositionStat[];
  app_ranking: EffectAppStat[];
  run_type_ranking: EffectRunTypeStat[];
  failure_reasons: EffectFailureReason[];
  audit_summary: EffectAuditSummary;
  estimate_model: EffectEstimateModelItem[];
};

export type EffectAnalyticsFilters = {
  date_range?: "7d" | "30d" | "90d" | "all";
  position?: Position | "all";
};

export type EvaluationSummary = {
  dataset_count: number;
  report_count: number;
  regression_suite_count: number;
  total_cases: number;
  average_pass_rate: number;
};

export type EvaluationDataset = {
  id: string;
  name: string;
  category: string;
  description: string;
  path: string;
  report_path: string;
  runner: string;
  case_count: number;
  positive_cases: number;
  refusal_cases: number;
  has_report: boolean;
  can_run: boolean;
  updated_at: string | null;
  report_updated_at: string | null;
};

export type EvaluationReport = {
  dataset_id: string;
  dataset_name: string;
  metrics: Record<string, unknown>;
  counts: Record<string, unknown>;
  pass_rate: number | null;
  failed_cases: Array<Record<string, unknown>>;
  updated_at: string | null;
};

export type EvaluationRegressionSuite = {
  id: string;
  name: string;
  category: string;
  description: string;
  command: string;
  case_count: number;
  real_services: string[];
};

export type EvaluationReleaseGate = {
  id: string;
  name: string;
  status: string;
  threshold: string;
  actual: string;
};

export type EvaluationCenterResponse = {
  summary: EvaluationSummary;
  datasets: EvaluationDataset[];
  reports: EvaluationReport[];
  regression_suites: EvaluationRegressionSuite[];
  release_gates: EvaluationReleaseGate[];
};

export type RagEvaluationRunResponse = {
  dataset: EvaluationDataset;
  report: EvaluationReport;
};

export type MonitoringScope = {
  date_range: "7d" | "30d" | "90d" | "all";
  date_range_label: string;
  since: string | null;
  generated_at: string;
};

export type MonitoringRunSummary = {
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  running_runs: number;
  success_rate: number;
  failure_rate: number;
  blocked_rate: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  latest_run_at: string | null;
  active_users: number;
};

export type MonitoringTrendPoint = {
  date: string;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  running_runs: number;
};

export type MonitoringPositionSummary = {
  position: Position | "platform" | string;
  position_label: string;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  success_rate: number;
  avg_duration_ms: number;
};

export type MonitoringRunTypeSummary = {
  run_type: string;
  label: string;
  app_name: string | null;
  total_runs: number;
  succeeded_runs: number;
  failed_runs: number;
  blocked_runs: number;
  success_rate: number;
  avg_duration_ms: number;
  latest_run_at: string | null;
};

export type MonitoringRunEvent = {
  id: string;
  status: string;
  run_type: string;
  run_type_label: string;
  app_id: string;
  app_name: string;
  position: Position | "platform" | string | null;
  position_label: string;
  duration_ms: number | null;
  occurred_at?: string | null;
  started_at?: string | null;
  summary?: string | null;
};

export type MonitoringAuditSummary = {
  total_events: number;
  security_events: number;
  approval_events: number;
  user_admin_events: number;
  latest_event_at: string | null;
};

export type MonitoringAuditAction = {
  action: string;
  resource_type: string | null;
  count: number;
  last_seen_at: string | null;
};

export type MonitoringConnectorItem = {
  id: string;
  label: string;
  category: string;
  active: boolean;
  configured: boolean;
  status: string;
  health_status: string;
  health_message: string;
  supports_real_health_check: boolean;
  position_scope_labels: string[];
  last_checked_at: string;
};

export type MonitoringConnectors = {
  summary: ConnectorsSummary;
  items: MonitoringConnectorItem[];
};

export type MonitoringErpHealth = {
  provider: string;
  provider_label: string;
  configured: boolean;
  ok: boolean;
  status: string;
  message: string;
  checked_at: string;
};

export type MonitoringEvaluation = {
  summary: EvaluationSummary;
  release_gates: EvaluationReleaseGate[];
  latest_report_at: string | null;
  status: string;
};

export type MonitoringKnowledge = {
  total_documents: number;
  active_documents: number;
  latest_document_at: string | null;
  child_chunks: number;
  indexed_documents: number;
  latest_chunk_at: string | null;
  parent_chunks: number;
};

export type MonitoringUserBucket = {
  role: "admin" | "employee" | string;
  position: Position | "platform" | string;
  position_label: string;
  count: number;
};

export type MonitoringUsers = {
  total_users: number;
  items: MonitoringUserBucket[];
};

export type MonitoringDatabase = {
  status: string;
  message: string;
  checked_at: string | null;
  database_name: string;
};

export type MonitoringServiceHealthItem = {
  id: string;
  name: string;
  status: string;
  message: string;
  metric: string;
};

export type MonitoringCenterResponse = {
  scope: MonitoringScope;
  overall_status: string;
  database: MonitoringDatabase;
  run_summary: MonitoringRunSummary;
  run_trend: MonitoringTrendPoint[];
  position_summary: MonitoringPositionSummary[];
  run_type_summary: MonitoringRunTypeSummary[];
  recent_issues: MonitoringRunEvent[];
  slow_runs: MonitoringRunEvent[];
  audit_summary: MonitoringAuditSummary;
  audit_actions: MonitoringAuditAction[];
  connectors: MonitoringConnectors;
  erp_health: MonitoringErpHealth;
  evaluation: MonitoringEvaluation;
  knowledge: MonitoringKnowledge;
  users: MonitoringUsers;
  service_health: MonitoringServiceHealthItem[];
};

export type MonitoringCenterFilters = {
  date_range?: "7d" | "30d" | "90d" | "all";
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

export async function listAutomationFlows(
  token: string,
  filters: { position?: Position | "all"; category?: string } = {},
) {
  const params = new URLSearchParams();

  if (filters.position && filters.position !== "all") {
    params.set("position", filters.position);
  }

  if (filters.category?.trim()) {
    params.set("category", filters.category.trim());
  }

  const suffix = params.toString() ? `?${params}` : "";
  return requestJson<AutomationFlowsResponse>(`/automation-flows${suffix}`, {}, token);
}

export async function getAutomationFlowDetail(token: string, flowId: string) {
  return requestJson<AutomationFlowDetailResponse>(
    `/automation-flows/${encodeURIComponent(flowId)}`,
    {},
    token,
  );
}

export async function listAiWorkflows(token: string) {
  return requestJson<AiWorkflowsResponse>("/ai-workflows", {}, token);
}

export async function getAiWorkflowDetail(token: string, workflowId: string) {
  return requestJson<AiWorkflowDetailResponse>(
    `/ai-workflows/${encodeURIComponent(workflowId)}`,
    {},
    token,
  );
}

export async function runAiWorkflow(
  token: string,
  workflowId: string,
  inputText: string,
) {
  return requestJson<AiWorkflowRunResponse>(
    `/ai-workflows/${encodeURIComponent(workflowId)}/run`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input_text: inputText,
      }),
    },
    token,
  );
}

export async function listConnectors(token: string) {
  return requestJson<ConnectorsResponse>("/connectors", {}, token);
}

export async function getConnectorDetail(token: string, connectorId: string) {
  return requestJson<ConnectorDetailResponse>(
    `/connectors/${encodeURIComponent(connectorId)}`,
    {},
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

export async function listRunRecords(
  token: string,
  filters: RunRecordFilters = {},
) {
  const params = new URLSearchParams();

  if (filters.status?.trim()) {
    params.set("status", filters.status.trim());
  }

  if (filters.run_type?.trim()) {
    params.set("run_type", filters.run_type.trim());
  }

  if (filters.app_id?.trim()) {
    params.set("app_id", filters.app_id.trim());
  }

  if (filters.position && filters.position !== "all") {
    params.set("position", filters.position);
  }

  if (filters.resource_type?.trim()) {
    params.set("resource_type", filters.resource_type.trim());
  }

  if (filters.resource_id?.trim()) {
    params.set("resource_id", filters.resource_id.trim());
  }

  params.set("limit", String(filters.limit || 80));

  return requestJson<RunRecordsResponse>(`/run-records?${params}`, {}, token);
}

export async function getRunRecordDetail(token: string, runId: string) {
  return requestJson<RunRecordDetailResponse>(
    `/run-records/${encodeURIComponent(runId)}`,
    {},
    token,
  );
}

export async function getEffectAnalytics(
  token: string,
  filters: EffectAnalyticsFilters = {},
) {
  const params = new URLSearchParams();
  params.set("date_range", filters.date_range || "30d");

  if (filters.position && filters.position !== "all") {
    params.set("position", filters.position);
  }

  return requestJson<EffectAnalyticsResponse>(`/effect-analytics?${params}`, {}, token);
}

export async function getEvaluationCenter(token: string) {
  return requestJson<EvaluationCenterResponse>("/evaluation-center", {}, token);
}

export async function getMonitoringCenter(
  token: string,
  filters: MonitoringCenterFilters = {},
) {
  const params = new URLSearchParams();
  params.set("date_range", filters.date_range || "30d");
  return requestJson<MonitoringCenterResponse>(`/monitoring-center?${params}`, {}, token);
}

export async function runRagEvaluation(token: string, datasetId = "rag_smoke", topK = 5) {
  const params = new URLSearchParams();
  params.set("dataset_id", datasetId);
  params.set("top_k", String(topK));
  return requestJson<RagEvaluationRunResponse>(
    `/evaluation-center/run-rag?${params}`,
    { method: "POST" },
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
