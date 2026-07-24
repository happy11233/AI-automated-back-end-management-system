const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

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

export type Position = "operations" | "customer_service" | "finance";

export type ChatResponse = {
  thread_id: string;
  answer: string;
  intent: string | null;
  risk_level: string | null;
  erp_references?: ErpReference[];
  attachments?: ChatAttachment[];
  platform_draft?: PlatformDraftItem | null;
  approval_result: Record<string, unknown> | null;
};

export type ChatAttachment = {
  type?: string;
  filename: string;
  mime_type?: string;
  size_bytes?: number;
  content_base64?: string;
  metadata?: Record<string, unknown>;
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
  attachments?: ChatAttachment[];
  platform_draft?: PlatformDraftItem | null;
  approval_result?: Record<string, unknown> | null;
};

export type ChatStreamHandlers = {
  onStart?: (payload: ChatStreamPayload) => void;
  onNode?: (payload: ChatStreamPayload) => void;
  onContent?: (payload: ChatStreamPayload) => void;
  onDone?: (payload: ChatStreamPayload) => void;
  onError?: (payload: ChatStreamPayload) => void;
};

export type CustomerServiceMessageItem = {
  id: string;
  channel: string;
  external_id: string | null;
  buyer_name: string | null;
  buyer_email: string | null;
  buyer_language: string;
  marketplace: string | null;
  order_no: string | null;
  tracking_no: string | null;
  sku: string | null;
  subject: string | null;
  message: string;
  intent: string | null;
  risk_level: string;
  status: string;
  automation_decision: string | null;
  reply_draft: string | null;
  handoff_reason: string | null;
  erp_summary: string | null;
  rag_summary: string | null;
  erp_references: ErpReference[];
  citations: Array<Record<string, unknown>>;
  approval_id: string | null;
  run_id: string | null;
  assigned_to: string | null;
  created_by: string | null;
  processed_by: string | null;
  processed_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type CustomerServiceMessageEventItem = {
  id: string;
  message_id: string;
  event_type: string;
  actor_id: string | null;
  content: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type CustomerServiceMessagesResponse = {
  items: CustomerServiceMessageItem[];
};

export type CustomerServiceMessageDetailResponse = {
  item: CustomerServiceMessageItem;
  events: CustomerServiceMessageEventItem[];
};

export type CustomerServiceMessageCreatePayload = {
  channel: "manual" | "amazon" | "email" | "ticket" | "api";
  external_id?: string | null;
  buyer_name?: string | null;
  buyer_email?: string | null;
  buyer_language?: string;
  marketplace?: string | null;
  order_no?: string | null;
  tracking_no?: string | null;
  sku?: string | null;
  subject?: string | null;
  message: string;
  metadata?: Record<string, unknown>;
};

export type CustomerServiceWebhookMessagePayload = CustomerServiceMessageCreatePayload & {
  auto_process?: boolean;
};

export type CustomerServiceProcessResponse = {
  item: CustomerServiceMessageItem;
  run_id: string;
  steps: Array<{
    step_order: number;
    step_name: string;
    status: string;
    duration_ms: number;
  }>;
  events: CustomerServiceMessageEventItem[];
};

export type CustomerServiceWebhookMessageResponse = Omit<CustomerServiceProcessResponse, "run_id"> & {
  processed: boolean;
  run_id: string | null;
  webhook_auth: string;
};

export type ApprovalItem = {
  id: string;
  thread_id: string;
  action_type: string;
  payload: Record<string, unknown>;
  summary_cn?: string;
  summary_source?: string;
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
  display_name?: string | null;
  email?: string | null;
  role: "admin" | "employee";
  department: string | null;
  position: Position | null;
  capabilities: string[];
  erp_scopes: string[];
  allowed_ai_app_ids: string[];
  ai_app_permissions: UserAiAppPermissionItem[];
  created_at: string;
};

export type UserAiAppPermissionItem = {
  id: string;
  name: string;
  position: Position | "platform";
  position_label: string;
  category: string;
  enabled: boolean;
};

export type UserCreatePayload = {
  username: string;
  password: string;
  role: "admin" | "employee";
  position: Position | null;
  department?: string | null;
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

export type UserProfileUpdatePayload = {
  display_name?: string | null;
  email?: string | null;
};

export type UserPasswordUpdatePayload = {
  old_password: string;
  new_password: string;
};

export type RagTeamStatus = "active" | "paused" | "archived";
export type RagTeamMemberRole = "member" | "supervisor" | "auditor";
export type RagDocumentAccessMode = "open" | "owner_only" | "team_only" | "explicit_grants" | "owner_and_grants";
export type RagGrantSubjectType = "user" | "team";
export type RagGrantAccessLevel = "read" | "manage";
export type RagMarketScope = "us" | "de" | "jp";
export type RagStoreScope = "us_store" | "de_store" | "jp_store";

export type RagTeamItem = {
  id: string;
  team_key: string;
  name: string;
  description: string | null;
  position_scope: Position | null;
  market_scope: RagMarketScope | null;
  store_scope: RagStoreScope | null;
  status: RagTeamStatus;
  created_by: string | null;
  created_by_username: string | null;
  member_count: number;
  created_at: string;
  updated_at: string;
};

export type RagTeamMemberItem = {
  id: string;
  team_id: string;
  user_id: string;
  username: string;
  display_name: string | null;
  role: "admin" | "employee";
  position: Position | null;
  department: string | null;
  member_role: RagTeamMemberRole;
  status: string;
  expires_at: string | null;
  added_by: string | null;
  added_by_username: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentAccessItem = {
  id: string;
  title: string;
  source: string | null;
  visibility: string;
  department: string | null;
  position_scope: Position | null;
  market_scope: RagMarketScope | null;
  store_scope: RagStoreScope | null;
  field_scope: string | null;
  sensitivity_level: string | null;
  owner_user_id: string | null;
  owner_team_id: string | null;
  access_mode: RagDocumentAccessMode;
  status: string;
  created_at: string;
  updated_at: string;
};

export type DocumentGrantItem = {
  id: string;
  document_id: string;
  subject_type: RagGrantSubjectType;
  subject_id: string;
  subject_name: string | null;
  access_level: RagGrantAccessLevel;
  status: string;
  granted_by: string | null;
  granted_by_username: string | null;
  reason: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RagTeamCreatePayload = {
  team_key: string;
  name: string;
  description?: string | null;
  position_scope?: Position | null;
  market_scope?: RagMarketScope | null;
  store_scope?: RagStoreScope | null;
  status?: RagTeamStatus;
};

export type RagTeamUpdatePayload = {
  name?: string;
  description?: string | null;
  position_scope?: Position | null;
  market_scope?: RagMarketScope | null;
  store_scope?: RagStoreScope | null;
  status?: RagTeamStatus;
};

export type RagTeamMemberPayload = {
  user_id: string;
  member_role?: RagTeamMemberRole;
  expires_at?: string | null;
};

export type DocumentAccessUpdatePayload = {
  access_mode?: RagDocumentAccessMode;
  owner_user_id?: string | null;
  owner_team_id?: string | null;
};

export type DocumentUploadAccessPayload = {
  access_mode?: RagDocumentAccessMode;
  owner_user_id?: string | null;
  owner_team_id?: string | null;
  grant_subject_type?: RagGrantSubjectType | null;
  grant_subject_id?: string | null;
  grant_access_level?: RagGrantAccessLevel | null;
  grant_reason?: string | null;
  grant_expires_at?: string | null;
};

export type DocumentListFilters = {
  search?: string;
  status?: "active" | "deleted" | "all";
  limit?: number;
};

export type DocumentGrantCreatePayload = {
  subject_type: RagGrantSubjectType;
  subject_id: string;
  access_level?: RagGrantAccessLevel;
  reason?: string | null;
  expires_at?: string | null;
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
  date_range?: "today" | "7d" | "30d" | "all";
  file_type?: "all" | "excel" | "word";
  limit?: number;
};

export type AutomationGenerateResponse = {
  position: Position;
  position_label: string;
  task_id: string;
  task_label: string;
  answer: string;
  platform_draft?: PlatformDraftItem | null;
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

export type AutomationFlowVersionStatus =
  | "draft"
  | "reviewing"
  | "approved"
  | "published"
  | "deprecated"
  | "rejected"
  | "rolled_back";

export type AutomationFlowVersionSummary = {
  id: string;
  flow_id: string;
  flow_key: string;
  version: string;
  version_number: number;
  status: AutomationFlowVersionStatus | string;
  change_summary: string | null;
  trigger_type: string;
  entrypoint: string;
  approval_policy: string;
  failure_strategy: string;
  publish_notes: string | null;
  created_by: string | null;
  created_by_username: string | null;
  approved_by: string | null;
  approved_by_username: string | null;
  published_by: string | null;
  published_by_username: string | null;
  created_at: string | null;
  updated_at: string | null;
  approved_at: string | null;
  published_at: string | null;
  active_publication_id: string | null;
  active_publication_environment: string | null;
};

export type AutomationFlowVersionItem = AutomationFlowVersionSummary & {
  app_id: string;
  name: string;
  description: string | null;
  category: string;
  position: Position | null;
  flow_status: string;
  source: string;
  input_schema: Array<Record<string, unknown>>;
  output_schema: Array<Record<string, unknown>>;
  prompt_template_preview: string | null;
  prompt_summary: string | null;
  model_config: Record<string, unknown>;
  allowed_tools: string[];
  allowed_erp_resources: ErpResourceItem[];
  allowed_rag_scopes: Record<string, unknown>;
  permission_rules: string[];
  steps: Array<Record<string, unknown>>;
};

export type AutomationFlowVersionListResponse = {
  items: AutomationFlowVersionSummary[];
  total: number;
};

export type AutomationFlowVersionResponse = {
  item: AutomationFlowVersionItem;
};

export type AutomationFlowPublicationItem = {
  id: string;
  flow_id: string;
  flow_key: string;
  version_id: string;
  version: string;
  version_number: number;
  environment: "dev" | "staging" | "production" | string;
  status: string;
  rollout_percent: number;
  published_by: string | null;
  published_by_username: string | null;
  published_at: string | null;
  rollback_from_version_id: string | null;
  reason: string | null;
  created_at: string | null;
};

export type AutomationFlowPublicationResponse = {
  item: AutomationFlowPublicationItem;
};

export type AutomationFlowVersionPreflightRepairHint = {
  code: string;
  field_path: string;
  severity: "blocking" | "warning" | string;
  message: string;
  suggestion: string;
};

export type AutomationFlowVerificationEvidence = {
  id: string;
  flow_id: string;
  version_id: string | null;
  flow_key: string;
  version: string;
  version_status: string;
  snapshot_hash: string;
  script: string;
  command: string;
  profile: "api" | "release" | string;
  status: "passed" | "failed" | string;
  report_id: string;
  report_url: string | null;
  summary: string | null;
  metadata: Record<string, unknown>;
  verified_by: string | null;
  verified_by_username: string | null;
  verified_at: string;
  expires_at: string;
  created_at: string;
  is_current_version?: boolean | null;
  matches_current_snapshot?: boolean | null;
  is_publish_eligible?: boolean | null;
  evidence_scope?: "current_version" | "same_snapshot" | string | null;
};

export type AutomationFlowVerificationEvidenceListResponse = {
  items: AutomationFlowVerificationEvidence[];
  total: number;
  version_id: string;
  flow_id: string;
  flow_key: string;
  version: string;
  snapshot_hash: string;
};

export type AutomationFlowVersionPreflightArtifact = {
  label: string;
  command: string;
  script: string;
  profile: "api" | "release" | string;
  publish_evidence_required?: boolean;
  latest_evidence?: AutomationFlowVerificationEvidence | null;
};

export type AutomationFlowVersionPreflightCheck = {
  key: string;
  label: string;
  status: "passed" | "failed" | string;
  message: string;
  details: string[];
  repair_hints: AutomationFlowVersionPreflightRepairHint[];
  artifacts: AutomationFlowVersionPreflightArtifact[];
};

export type AutomationFlowVersionPreflightResponse = {
  preflight_run_id: string | null;
  ok: boolean;
  version_id: string;
  flow_id: string;
  flow_key: string;
  version: string;
  status: string;
  trigger_source: "manual" | "publish" | string;
  blocking_failures: number;
  checks: AutomationFlowVersionPreflightCheck[];
  created_by: string | null;
  created_by_username: string | null;
  created_at: string | null;
};

export type AutomationFlowVersionCreatePayload = {
  version?: string | null;
  change_summary?: string | null;
  approval_policy?: string | null;
  failure_strategy?: string | null;
  publish_notes?: string | null;
};

export type AutomationFlowVersionUpdatePayload = {
  change_summary?: string | null;
  approval_policy?: string | null;
  failure_strategy?: string | null;
  publish_notes?: string | null;
  prompt_summary?: string | null;
  prompt_template_preview?: string | null;
  input_schema?: Array<Record<string, unknown>> | null;
  output_schema?: Array<Record<string, unknown>> | null;
  tool_parameters?: Record<string, Record<string, unknown>> | null;
  allowed_tools?: string[] | null;
  allowed_erp_resources?: Array<Record<string, unknown>> | null;
  steps?: AutomationFlowStepItem[] | null;
};

export type AutomationFlowVersionPublishPayload = {
  environment?: "dev" | "staging" | "production";
  reason?: string | null;
};

export type AutomationFlowPublicationRollbackPayload = {
  reason?: string | null;
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
  platform_draft?: PlatformDraftItem | null;
  steps: AiWorkflowRunStep[];
  created_at: string;
};

export type BusinessActionLoopSummary = {
  total: number;
  pending_review: number;
  waiting_external: number;
  succeeded: number;
  failed: number;
  unread_notifications: number;
};

export type BusinessActionLoopItem = {
  draft_id: string;
  draft_type: "listing" | "customer_reply" | string;
  platform: string;
  external_target: string;
  title: string;
  draft_status: string;
  draft_status_label: string;
  position: Position | string;
  owner_user_id: string | null;
  source_run_id: string | null;
  source_resource_type: string | null;
  source_resource_id: string | null;
  writeback_status: string;
  writeback_status_label: string;
  writeback_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  latest_task_id: string | null;
  latest_action_type: string | null;
  latest_action_label: string | null;
  latest_task_status: string | null;
  latest_task_status_label: string | null;
  external_reference: string | null;
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  completed_at: string | null;
  task_updated_at: string | null;
  stage: string;
  stage_label: string;
  next_action: string;
};

export type BusinessActionLoopResponse = {
  summary: BusinessActionLoopSummary;
  items: BusinessActionLoopItem[];
};

export type PlatformDraftItem = {
  id: string;
  draft_type: "listing" | "customer_reply" | string;
  platform: string;
  external_target: string;
  title: string;
  status: string;
  position: Position | string;
  owner_user_id: string | null;
  source_run_id: string | null;
  source_resource_type: string | null;
  source_resource_id: string | null;
  content: Record<string, unknown>;
  writeback_status: string;
  writeback_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PlatformDraftsResponse = {
  items: PlatformDraftItem[];
};

export type PlatformDraftStatus = "pending_review" | "approved" | "published" | "rejected";

export type PlatformActionExecutionItem = {
  id: string;
  draft_id: string;
  action_type: string;
  executor_type: string;
  target: string;
  status: string;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  error_message: string | null;
  run_id: string | null;
  triggered_by: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
};

export type PlatformExecutionTaskStatus =
  | "queued"
  | "dispatching"
  | "waiting_callback"
  | "succeeded"
  | "failed"
  | "cancelled";

export type PlatformExecutionTaskItem = {
  id: string;
  draft_id: string;
  latest_execution_id: string | null;
  action_type: string;
  target: string;
  status: PlatformExecutionTaskStatus | string;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown>;
  external_reference: string | null;
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  requested_by: string | null;
  next_attempt_at: string | null;
  completed_at: string | null;
  metadata: Record<string, unknown>;
  draft?: PlatformDraftItem | null;
  draft_title?: string | null;
  draft_type?: string | null;
  draft_status?: string | null;
  draft_position?: Position | string | null;
  draft_writeback_status?: string | null;
  position?: Position | string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type PlatformExecutionTasksResponse = {
  items: PlatformExecutionTaskItem[];
};

export type PlatformExecutionTaskDetailResponse = {
  item: PlatformExecutionTaskItem;
};

export type PlatformExecutionTaskMutationResponse = {
  item?: PlatformExecutionTaskItem;
  task?: PlatformExecutionTaskItem;
  draft?: PlatformDraftItem;
  execution?: PlatformActionExecutionItem;
  run_id?: string;
  message?: string;
};

export type PlatformDraftDetailResponse = {
  item: PlatformDraftItem;
  executions: PlatformActionExecutionItem[];
};

export type PlatformDraftExecuteResponse = {
  draft: PlatformDraftItem;
  execution: PlatformActionExecutionItem;
  task?: PlatformExecutionTaskItem | null;
  run_id: string;
  message: string;
};

export type PlatformDraftReviewResponse = {
  item: PlatformDraftItem;
};

export type NotificationStatus = "unread" | "read";

export type NotificationItem = {
  id: string;
  user_id: string | null;
  type: string;
  title: string;
  body: string;
  status: NotificationStatus | string;
  resource_type: string | null;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at?: string | null;
  read_at?: string | null;
};

export type NotificationsResponse = {
  items: NotificationItem[];
  unread_count: number;
};

export type NotificationMutationResponse = {
  item?: NotificationItem;
  updated_count?: number;
  ok?: boolean;
};

export type FeedbackStatus = "open" | "completed";
export type FeedbackPriority = "low" | "normal" | "high" | "urgent";
export type FeedbackCategory = "功能建议" | "体验问题" | "数据问题" | "自动化需求" | "权限流程" | "其他";

export type FeedbackItem = {
  id: string;
  submitted_by: string | null;
  username: string;
  display_name: string | null;
  position: Position | null;
  category: FeedbackCategory | string;
  priority: FeedbackPriority | string;
  title: string;
  description: string;
  status: FeedbackStatus | string;
  admin_note: string | null;
  completed_by: string | null;
  completed_by_username: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type FeedbackSummary = {
  total: number;
  open: number;
  completed: number;
};

export type FeedbackResponse = {
  items: FeedbackItem[];
  summary: FeedbackSummary;
};

export type FeedbackCreatePayload = {
  category: FeedbackCategory;
  priority: FeedbackPriority;
  title: string;
  description: string;
};

export type FeedbackMutationResponse = {
  item: FeedbackItem;
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

export type PlatformActionExecutorOption = {
  value: string;
  label: string;
};

export type PlatformActionExecutorSummary = {
  total: number;
  enabled: number;
  configured: number;
  healthy: number;
  needs_config: number;
};

export type PlatformActionExecutorItem = {
  id: string;
  name: string;
  executor_type: string;
  executor_type_label: string;
  action_types: string[];
  action_type_labels: string[];
  webhook_url: string | null;
  webhook_url_preview: string | null;
  api_key_configured: boolean;
  api_key_preview: string | null;
  timeout_seconds: number;
  enabled: boolean;
  configured: boolean;
  health_status: string;
  health_message: string | null;
  last_checked_at: string | null;
  metadata: Record<string, unknown>;
  is_environment_fallback: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type PlatformActionExecutorsResponse = {
  summary: PlatformActionExecutorSummary;
  items: PlatformActionExecutorItem[];
  action_types: PlatformActionExecutorOption[];
  executor_types: PlatformActionExecutorOption[];
};

export type PlatformActionExecutorResponse = {
  item: PlatformActionExecutorItem;
};

export type PlatformActionExecutorPayload = {
  name?: string;
  executor_type?: string;
  action_types?: string[];
  webhook_url?: string | null;
  api_key?: string | null;
  timeout_seconds?: number;
  enabled?: boolean;
  metadata?: Record<string, unknown>;
};

export type PlatformActionExecutorDeleteResponse = {
  ok: boolean;
  id: string;
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

export type ErpDashboardFilterOption = {
  label: string;
  value: string;
  count: number;
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
  market_options: ErpDashboardFilterOption[];
  store_options: ErpDashboardFilterOption[];
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
  flow_id: string | null;
  flow_key: string | null;
  flow_version_id: string | null;
  flow_version: string | null;
  publication_id: string | null;
  execution_source: string | null;
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
  flow_key?: string;
  flow_version_id?: string;
  publication_id?: string;
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

export type ThreadListItem = {
  id: string;
  user_id: string | null;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  username?: string | null;
  display_name?: string | null;
  role?: "admin" | "employee" | null;
  position?: Position | null;
  message_count: number;
  last_message_preview?: string | null;
  last_message_role?: string | null;
};

export type ThreadListResponse = {
  items: ThreadListItem[];
  retention_days: number;
};

export type ThreadCreateResponse = {
  item: ThreadListItem;
};

export type ThreadUpdateResponse = {
  item: ThreadListItem;
};

export type ThreadLatestResponse = {
  item: ThreadListItem | null;
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
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (body.detail && typeof body.detail.message === "string") {
      return body.detail.message;
    }
    if (typeof body.message === "string") {
      return body.message;
    }
    return "请求失败";
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

export async function getMySettings(token: string) {
  return requestJson<{ item: UserSettingsItem }>("/settings/me", {}, token);
}

export async function updateMyProfile(
  token: string,
  payload: UserProfileUpdatePayload,
) {
  return requestJson<{ item: UserSettingsItem }>(
    "/settings/me/profile",
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function updateMyPassword(
  token: string,
  payload: UserPasswordUpdatePayload,
) {
  return requestJson<{ ok: boolean }>(
    "/settings/me/password",
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
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
  positionScope?: Position | null,
  marketScope?: string | null,
  storeScope?: string | null,
  fieldScope?: string | null,
  sensitivityLevel?: string | null,
  uploadAccess?: DocumentUploadAccessPayload,
) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("visibility", visibility);

  if (department.trim()) {
    formData.append("department", department.trim());
  }

  if (positionScope) {
    formData.append("position_scope", positionScope);
  }

  if (marketScope) {
    formData.append("market_scope", marketScope);
  }

  if (storeScope) {
    formData.append("store_scope", storeScope);
  }

  if (fieldScope) {
    formData.append("field_scope", fieldScope);
  }

  if (sensitivityLevel) {
    formData.append("sensitivity_level", sensitivityLevel);
  }

  if (uploadAccess?.access_mode) {
    formData.append("access_mode", uploadAccess.access_mode);
  }

  if (uploadAccess?.owner_user_id) {
    formData.append("owner_user_id", uploadAccess.owner_user_id);
  }

  if (uploadAccess?.owner_team_id) {
    formData.append("owner_team_id", uploadAccess.owner_team_id);
  }

  if (uploadAccess?.grant_subject_type) {
    formData.append("grant_subject_type", uploadAccess.grant_subject_type);
  }

  if (uploadAccess?.grant_subject_id) {
    formData.append("grant_subject_id", uploadAccess.grant_subject_id);
  }

  if (uploadAccess?.grant_access_level) {
    formData.append("grant_access_level", uploadAccess.grant_access_level);
  }

  if (uploadAccess?.grant_reason) {
    formData.append("grant_reason", uploadAccess.grant_reason);
  }

  if (uploadAccess?.grant_expires_at) {
    formData.append("grant_expires_at", uploadAccess.grant_expires_at);
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

export async function listRagTeams(token: string) {
  return requestJson<{ items: RagTeamItem[]; total: number }>("/rag-teams", {}, token);
}

export async function createRagTeam(token: string, payload: RagTeamCreatePayload) {
  return requestJson<{ item: RagTeamItem }>(
    "/rag-teams",
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

export async function updateRagTeam(token: string, teamId: string, payload: RagTeamUpdatePayload) {
  return requestJson<{ item: RagTeamItem }>(
    `/rag-teams/${teamId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listRagTeamMembers(token: string, teamId: string) {
  return requestJson<{ items: RagTeamMemberItem[]; total: number }>(`/rag-teams/${teamId}/members`, {}, token);
}

export async function addRagTeamMember(token: string, teamId: string, payload: RagTeamMemberPayload) {
  return requestJson<{ item: RagTeamMemberItem }>(
    `/rag-teams/${teamId}/members`,
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

export async function removeRagTeamMember(token: string, teamId: string, userId: string) {
  return requestJson<{ ok: boolean; team_id: string; user_id: string }>(
    `/rag-teams/${teamId}/members/${userId}`,
    {
      method: "DELETE",
    },
    token,
  );
}

export async function getDocumentAccess(token: string, documentId: string) {
  return requestJson<{ item: DocumentAccessItem }>(`/documents/${documentId}/access`, {}, token);
}

export async function listRagDocuments(token: string, filters: DocumentListFilters = {}) {
  const params = new URLSearchParams();
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return requestJson<{ items: DocumentAccessItem[]; total: number }>(
    query ? `/documents?${query}` : "/documents",
    {},
    token,
  );
}

export async function updateDocumentAccess(
  token: string,
  documentId: string,
  payload: DocumentAccessUpdatePayload,
) {
  return requestJson<{ item: DocumentAccessItem }>(
    `/documents/${documentId}/access`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function listDocumentGrants(token: string, documentId: string) {
  return requestJson<{ items: DocumentGrantItem[]; total: number }>(`/documents/${documentId}/grants`, {}, token);
}

export async function createDocumentGrant(token: string, documentId: string, payload: DocumentGrantCreatePayload) {
  return requestJson<{ item: DocumentGrantItem }>(
    `/documents/${documentId}/grants`,
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

export async function revokeDocumentGrant(token: string, documentId: string, grantId: string) {
  return requestJson<{ ok: boolean; item: DocumentGrantItem }>(
    `/documents/${documentId}/grants/${grantId}`,
    {
      method: "DELETE",
    },
    token,
  );
}

export async function listApprovals(token: string) {
  return requestJson<{ items: ApprovalItem[] }>("/approvals", {}, token);
}

export async function reviewApproval(token: string, approvalId: string, approved: boolean) {
  return requestJson<Record<string, unknown>>(
    `/approvals/${approvalId}/review`,
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

export async function updateUserAiAppPermission(
  token: string,
  userId: string,
  appId: string,
  enabled: boolean,
) {
  return requestJson<{ item: UserItem }>(
    `/admin/users/${encodeURIComponent(userId)}/ai-apps/${encodeURIComponent(appId)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled }),
    },
    token,
  );
}

export async function deleteUser(token: string, userId: string) {
  return requestJson<{ ok: boolean; deleted_user_id: string }>(
    `/admin/users/${encodeURIComponent(userId)}`,
    {
      method: "DELETE",
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

export async function listCustomerServiceMessages(
  token: string,
  filters: { status?: string; risk_level?: string; limit?: number } = {},
) {
  const params = new URLSearchParams();

  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }

  if (filters.risk_level && filters.risk_level !== "all") {
    params.set("risk_level", filters.risk_level);
  }

  params.set("limit", String(filters.limit || 50));
  return requestJson<CustomerServiceMessagesResponse>(`/customer-service/messages?${params}`, {}, token);
}

export async function createCustomerServiceMessage(
  token: string,
  payload: CustomerServiceMessageCreatePayload,
) {
  return requestJson<CustomerServiceMessageDetailResponse>(
    "/customer-service/messages",
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

export async function getCustomerServiceMessageDetail(token: string, messageId: string) {
  return requestJson<CustomerServiceMessageDetailResponse>(
    `/customer-service/messages/${encodeURIComponent(messageId)}`,
    {},
    token,
  );
}

export async function processCustomerServiceMessage(token: string, messageId: string) {
  return requestJson<CustomerServiceProcessResponse>(
    `/customer-service/messages/${encodeURIComponent(messageId)}/process`,
    {
      method: "POST",
    },
    token,
  );
}

export async function receiveCustomerServiceWebhookMessage(
  token: string,
  payload: CustomerServiceWebhookMessagePayload,
) {
  return requestJson<CustomerServiceWebhookMessageResponse>(
    "/customer-service/webhooks/messages",
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

export async function listAutomationFlowVersions(token: string, flowId: string) {
  return requestJson<AutomationFlowVersionListResponse>(
    `/automation-flows/${encodeURIComponent(flowId)}/versions`,
    {},
    token,
  );
}

export async function createAutomationFlowVersion(
  token: string,
  flowId: string,
  payload: AutomationFlowVersionCreatePayload,
) {
  return requestJson<AutomationFlowVersionResponse>(
    `/automation-flows/${encodeURIComponent(flowId)}/versions`,
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

export async function getAutomationFlowVersion(token: string, versionId: string) {
  return requestJson<AutomationFlowVersionResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}`,
    {},
    token,
  );
}

export async function updateAutomationFlowVersion(
  token: string,
  versionId: string,
  payload: AutomationFlowVersionUpdatePayload,
) {
  return requestJson<AutomationFlowVersionResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function submitAutomationFlowVersionReview(token: string, versionId: string) {
  return requestJson<AutomationFlowVersionResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}/submit-review`,
    { method: "POST" },
    token,
  );
}

export async function approveAutomationFlowVersion(token: string, versionId: string) {
  return requestJson<AutomationFlowVersionResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}/approve`,
    { method: "POST" },
    token,
  );
}

export async function preflightAutomationFlowVersion(token: string, versionId: string) {
  return requestJson<AutomationFlowVersionPreflightResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}/preflight`,
    { method: "POST" },
    token,
  );
}

export async function listAutomationFlowVersionEvidence(token: string, versionId: string) {
  return requestJson<AutomationFlowVerificationEvidenceListResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}/verification-evidence`,
    {},
    token,
  );
}

export async function publishAutomationFlowVersion(
  token: string,
  versionId: string,
  payload: AutomationFlowVersionPublishPayload,
) {
  return requestJson<AutomationFlowPublicationResponse>(
    `/automation-flow-versions/${encodeURIComponent(versionId)}/publish`,
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

export async function rollbackAutomationFlowPublication(
  token: string,
  publicationId: string,
  payload: AutomationFlowPublicationRollbackPayload,
) {
  return requestJson<AutomationFlowPublicationResponse>(
    `/automation-flow-publications/${encodeURIComponent(publicationId)}/rollback`,
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

export async function listPlatformDrafts(
  token: string,
  filters: { draft_type?: "listing" | "customer_reply"; status?: PlatformDraftStatus | "all"; limit?: number } = {},
) {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit || 50));
  if (filters.draft_type) {
    params.set("draft_type", filters.draft_type);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }

  return requestJson<PlatformDraftsResponse>(`/platform-drafts?${params}`, {}, token);
}

export async function getPlatformDraftDetail(token: string, draftId: string) {
  return requestJson<PlatformDraftDetailResponse>(
    `/platform-drafts/${encodeURIComponent(draftId)}`,
    {},
    token,
  );
}

export async function executePlatformDraft(token: string, draftId: string) {
  return requestJson<PlatformDraftExecuteResponse>(
    `/platform-drafts/${encodeURIComponent(draftId)}/execute`,
    {
      method: "POST",
    },
    token,
  );
}

export async function reviewPlatformDraft(
  token: string,
  draftId: string,
  payload: { decision: "approved" | "rejected"; comment?: string },
) {
  return requestJson<PlatformDraftReviewResponse>(
    `/platform-drafts/${encodeURIComponent(draftId)}/review`,
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

export async function publishPlatformDraft(token: string, draftId: string) {
  return requestJson<PlatformDraftExecuteResponse>(
    `/platform-drafts/${encodeURIComponent(draftId)}/publish`,
    {
      method: "POST",
    },
    token,
  );
}

export async function getBusinessActionLoop(token: string, filters: { limit?: number } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit || 80));
  return requestJson<BusinessActionLoopResponse>(`/business-action-loop?${params}`, {}, token);
}

export async function listPlatformExecutionTasks(
  token: string,
  filters: { status?: PlatformExecutionTaskStatus | "all" | string; limit?: number } = {},
) {
  const params = new URLSearchParams();

  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  params.set("limit", String(filters.limit || 80));

  return requestJson<PlatformExecutionTasksResponse>(`/platform-execution-tasks?${params}`, {}, token);
}

export async function getPlatformExecutionTask(token: string, taskId: string) {
  return requestJson<PlatformExecutionTaskDetailResponse>(
    `/platform-execution-tasks/${encodeURIComponent(taskId)}`,
    {},
    token,
  );
}

export async function retryPlatformExecutionTask(token: string, taskId: string) {
  return requestJson<PlatformExecutionTaskMutationResponse>(
    `/platform-execution-tasks/${encodeURIComponent(taskId)}/retry`,
    {
      method: "POST",
    },
    token,
  );
}

export async function listNotifications(
  token: string,
  filters: { status?: NotificationStatus | "all" | string; limit?: number } = {},
) {
  const params = new URLSearchParams();

  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  params.set("limit", String(filters.limit || 80));

  return requestJson<NotificationsResponse>(`/notifications?${params}`, {}, token);
}

export async function markNotificationRead(token: string, notificationId: string) {
  return requestJson<NotificationMutationResponse>(
    `/notifications/${encodeURIComponent(notificationId)}/read`,
    {
      method: "POST",
    },
    token,
  );
}

export async function markAllNotificationsRead(token: string) {
  return requestJson<NotificationMutationResponse>(
    "/notifications/read-all",
    {
      method: "POST",
    },
    token,
  );
}

export async function listFeedback(
  token: string,
  filters: { status?: FeedbackStatus | "all" | string; limit?: number } = {},
) {
  const params = new URLSearchParams();

  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  params.set("limit", String(filters.limit || 80));

  return requestJson<FeedbackResponse>(`/feedback?${params}`, {}, token);
}

export async function createFeedback(token: string, payload: FeedbackCreatePayload) {
  return requestJson<FeedbackMutationResponse>(
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

export async function completeFeedback(token: string, feedbackId: string, adminNote?: string) {
  return requestJson<FeedbackMutationResponse>(
    `/feedback/${encodeURIComponent(feedbackId)}/complete`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ admin_note: adminNote || "" }),
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

export async function listPlatformActionExecutors(token: string) {
  return requestJson<PlatformActionExecutorsResponse>("/platform-action-executors", {}, token);
}

export async function createPlatformActionExecutor(token: string, payload: PlatformActionExecutorPayload) {
  return requestJson<PlatformActionExecutorResponse>(
    "/platform-action-executors",
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

export async function updatePlatformActionExecutor(token: string, executorId: string, payload: PlatformActionExecutorPayload) {
  return requestJson<PlatformActionExecutorResponse>(
    `/platform-action-executors/${encodeURIComponent(executorId)}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function checkPlatformActionExecutorHealth(token: string, executorId: string) {
  return requestJson<PlatformActionExecutorResponse>(
    `/platform-action-executors/${encodeURIComponent(executorId)}/health-check`,
    {
      method: "POST",
    },
    token,
  );
}

export async function deletePlatformActionExecutor(token: string, executorId: string) {
  return requestJson<PlatformActionExecutorDeleteResponse>(
    `/platform-action-executors/${encodeURIComponent(executorId)}`,
    {
      method: "DELETE",
    },
    token,
  );
}

export async function transformFinanceExcel(
  token: string,
  file: File,
  instruction: string,
  erpResources: string[] = [],
) {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("instruction", instruction.trim());
  formData.append("erp_resources", JSON.stringify(erpResources));

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

export async function analyzeFinanceReport(
  token: string,
  files: File[],
  instruction: string,
  outputFormat: "word" | "excel",
) {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });
  formData.append("instruction", instruction.trim());
  formData.append("output_format", outputFormat);

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/automation/finance/report-analysis`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    throw await buildRequestError(response, true);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const fallback = outputFormat === "word" ? "finance_report_analysis.docx" : "finance_report_analysis.xlsx";

  return {
    blob,
    filename: parseDownloadFilename(disposition) || fallback,
    outputFormat: response.headers.get("x-automation-output-format") || outputFormat,
  };
}

export async function exportFinanceSalary(
  token: string,
  messageText: string,
) {
  const response = await fetch(`${API_BASE_URL}/automation/finance/salary-export`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: messageText.trim() || "把这个月所有员工的工资表发我",
    }),
  });

  if (!response.ok) {
    throw await buildRequestError(response, true);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";

  return {
    blob,
    filename: parseDownloadFilename(disposition) || "finance_salary.xlsx",
    intent: response.headers.get("x-automation-intent") || "",
    period: response.headers.get("x-automation-period") || "",
    employeeCount: Number(response.headers.get("x-automation-employee-count") || 0),
  };
}

export async function listGeneratedFiles(
  token: string,
  filters: GeneratedFileFilters = {},
) {
  const params = new URLSearchParams();
  if (filters.search?.trim()) {
    params.set("search", filters.search.trim());
  }
  params.set("date_range", filters.date_range || "30d");
  params.set("file_type", filters.file_type || "all");
  params.set("limit", String(filters.limit || 80));
  return requestJson<GeneratedFilesResponse>(`/files?${params}`, {}, token);
}

export async function downloadGeneratedFile(token: string, artifactId: string) {
  const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(artifactId)}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw await buildRequestError(response, true);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  return {
    blob,
    filename: parseDownloadFilename(disposition) || "generated_file",
  };
}

export async function reconcileFinanceFiles(
  token: string,
  files: File[],
  instruction: string,
  baseCurrency: string,
) {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });
  formData.append("instruction", instruction.trim());
  formData.append("base_currency", baseCurrency.trim() || "CNY");

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/automation/finance/reconciliation`, {
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
    filename: parseDownloadFilename(disposition) || "finance_reconciliation_result.xlsx",
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

  if (filters.flow_key?.trim()) {
    params.set("flow_key", filters.flow_key.trim());
  }

  if (filters.flow_version_id?.trim()) {
    params.set("flow_version_id", filters.flow_version_id.trim());
  }

  if (filters.publication_id?.trim()) {
    params.set("publication_id", filters.publication_id.trim());
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

export async function listThreads(
  token: string,
  filters: { search?: string; limit?: number } = {},
) {
  const params = new URLSearchParams();
  params.set("limit", String(filters.limit || 80));
  if (filters.search?.trim()) {
    params.set("search", filters.search.trim());
  }

  return requestJson<ThreadListResponse>(`/threads?${params}`, {}, token);
}

export async function createThread(token: string) {
  return requestJson<ThreadCreateResponse>("/threads", { method: "POST" }, token);
}

export async function updateThreadTitle(token: string, threadId: string, title: string) {
  return requestJson<ThreadUpdateResponse>(
    `/threads/${encodeURIComponent(threadId)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    },
    token,
  );
}

export async function getLatestThread(token: string) {
  return requestJson<ThreadLatestResponse>("/threads/latest", {}, token);
}
