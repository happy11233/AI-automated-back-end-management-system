from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_environment: Literal['development', 'production'] = 'development'
    database_url: str
    db_pool_min_size: int = Field(default=1, ge=0)
    db_pool_max_size: int = Field(default=5, ge=2, le=200)
    db_pool_timeout_seconds: int = Field(default=10, ge=1, le=120)
    redis_url: str | None = None
    redis_key_prefix: str = 'company-rag'
    rate_limit_enabled: bool = False
    rate_limit_login_per_minute: int = Field(default=10, ge=1)
    rate_limit_ai_per_minute: int = Field(default=30, ge=1)
    cors_allowed_origins: str = ''
    artifact_storage_backend: Literal['local', 's3'] = 'local'
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_region: str = 'us-east-1'
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_key_prefix: str = 'generated-files'
    background_jobs_enabled: bool = False
    background_job_input_retention_days: int = Field(default=7, ge=1, le=365)
    materialized_file_retention_hours: int = Field(default=24, ge=1, le=168)
    metrics_token: str | None = None
    vector_database_url: str
    dashscope_api_key: str
    celery_broker_url: str = "amqp://rag_worker:local-change-me@127.0.0.1:5672/company_rag"
    celery_timezone: str = "Asia/Shanghai"
    celery_worker_concurrency: int = Field(default=2, ge=1, le=64)
    celery_task_soft_time_limit_seconds: int = Field(default=540, ge=1)
    celery_task_time_limit_seconds: int = Field(default=600, ge=1)
    context_cleanup_scheduler: Literal["api", "celery"] = "api"
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "company-rag-agent-dev"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str | None = None
    langsmith_hide_inputs: bool = True
    langsmith_hide_outputs: bool = True
    langsmith_tracing_sampling_rate: float = Field(default=0.1, ge=0, le=1)
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_image_api_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    bailian_image_edit_model: str = "qwen-image-2.0-pro"
    bailian_image_timeout_seconds: int = Field(default=180, ge=30, le=600)
    bailian_chat_model: str = "qwen-plus"
    bailian_fast_chat_model: str | None = None
    bailian_fast_chat_max_tokens: int = 512
    bailian_request_timeout_seconds: int = 60
    bailian_max_retries: int = 1
    bailian_embedding_model: str = "text-embedding-v4"
    bailian_embedding_dimensions: int = 1024
    rag_embedding_cache_ttl_seconds: int = 300
    rag_embedding_cache_max_entries: int = 512
    rag_vector_candidate_k: int = 20
    rag_keyword_candidate_k: int = 20
    rag_multi_query_count: int = 3
    rag_customer_multi_query_count: int = 1
    customer_context_parallel_enabled: bool = True
    rag_final_top_k: int = 5
    rag_context_max_chars: int = 12000
    rag_chunk_max_chars: int = 3000
    rag_min_score: float = 0.05
    rag_pdf_parser: str = "auto"
    rag_mineru_command: str = "mineru"
    rag_mineru_backend: str = "pipeline"
    rag_mineru_timeout_seconds: int = 180
    rag_mineru_model_source: str | None = None
    desktop_release_dir: str = "data/desktop-releases"
    rag_enable_llm_query_rewrite: bool = False
    rag_rerank_vector_weight: float = 0.5
    rag_rerank_keyword_weight: float = 0.35
    rag_rerank_overlap_weight: float = 0.15
    context_recent_message_limit: int = 12
    context_summary_message_limit: int = 24
    context_summary_interval: int = 6
    context_memory_limit: int = 20
    context_enable_llm_summary: bool = True
    chat_message_retention_days: int = 15
    audit_log_retention_days: int = 365
    chat_thread_retention_days: int = 15
    closed_thread_retention_days: int = 15
    user_memory_retention_days: int = 365
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_document_ids: str = ""
    feishu_bitable_app_token: str | None = None
    feishu_bitable_table_id: str | None = None
    feishu_ticket_id_field: str = "工单号"
    feishu_ticket_title_field: str = "标题"
    feishu_ticket_description_field: str = "描述"
    feishu_ticket_priority_field: str = "优先级"
    feishu_ticket_requester_field: str = "申请人"
    feishu_ticket_source_field: str = "来源"
    feishu_ticket_status_field: str = "状态"
    feishu_ticket_created_at_field: str = "创建时间"
    erp_provider: str = "erpnext"
    erp_base_url: str | None = None
    erp_api_key: str | None = None
    erp_api_secret: str | None = None
    erp_timeout_seconds: int = 8
    mcp_tool_timeout_seconds: int = 15
    erp_kingdee_base_url: str | None = None
    erp_kingdee_account_id: str | None = None
    erp_kingdee_app_id: str | None = None
    erp_kingdee_app_secret: str | None = None
    erp_yonyou_base_url: str | None = None
    erp_yonyou_tenant_id: str | None = None
    erp_yonyou_app_key: str | None = None
    erp_yonyou_app_secret: str | None = None
    customer_service_webhook_secret: str | None = None
    customer_service_webhook_secret_header: str = "X-Customer-Service-Webhook-Secret"
    generated_file_retention_days: int = 30
    generated_file_storage_dir: str = "data/generated_files"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = False
    smtp_use_starttls: bool = True
    smtp_timeout_seconds: int = 10
    platform_action_executor_webhook_url: str | None = None
    platform_action_executor_api_key: str | None = None
    platform_action_executor_timeout_seconds: int = 12
    platform_action_executor_allowed_hosts: str = ""
    platform_action_executor_allowed_schemes: str = "https"
    platform_action_executor_allowed_ports: str = "443"
    platform_action_executor_allow_private_network: bool = False
    platform_action_executor_require_allowlist: bool = True
    platform_action_execution_callback_secret: str | None = None
    platform_action_execution_callback_signature_header: str = "X-Platform-Callback-Signature"
    platform_action_execution_callback_timestamp_header: str = "X-Platform-Callback-Timestamp"
    platform_action_execution_callback_nonce_header: str = "X-Platform-Callback-Nonce"
    platform_action_execution_callback_tolerance_seconds: int = 300
    aiops_service_url: str = "http://127.0.0.1:9900"
    aiops_service_timeout_seconds: int = 8
    aiops_monitoring_poll_interval_seconds: int = 300
    aiops_probe_secret: str | None = None
    finance_wechat_executor_mode: str = "manual_final_click"
    finance_wechat_n8n_webhook_url: str | None = None
    finance_wechat_n8n_api_key: str | None = None
    finance_wechat_executor_timeout_seconds: int = 12
    finance_wechat_mac_rpa_enabled: bool = False
    finance_wechat_mac_app_name: str = "WeChat"
    desktop_agent_secret: str | None = None
    desktop_agent_mac_automation_enabled: bool = False
    desktop_agent_enterprise_wechat_app_name: str = "企业微信"
    desktop_agent_music_app_name: str = "Music"
    desktop_agent_allow_auto_send: bool = False
    amazon_playwright_enabled: bool = False
    amazon_seller_central_url: str = "https://sellercentral.amazon.com/"
    amazon_playwright_user_data_dir: str | None = None
    amazon_playwright_selector_profile: str | None = None
    amazon_playwright_timeout_seconds: int = 20
    amazon_playwright_browser_channel: str | None = "chrome"
    amazon_playwright_headless: bool = False
    message_sender_real_send_enabled: bool = False
    message_sender_allowed_email_domains: str = ""
    enterprise_wechat_webhook_url: str | None = None
    wechat_work_corp_id: str | None = None
    wechat_work_agent_id: str | None = None
    wechat_work_secret: str | None = None
    wechat_work_timeout_seconds: int = 12

    @model_validator(mode='after')
    def validate_production_options(self):
        if self.db_pool_min_size > self.db_pool_max_size:
            raise ValueError('DB_POOL_MIN_SIZE must not exceed DB_POOL_MAX_SIZE')
        if self.celery_task_soft_time_limit_seconds >= self.celery_task_time_limit_seconds:
            raise ValueError('Celery soft time limit must be shorter than the hard limit')
        if self.rate_limit_enabled and not self.redis_url:
            raise ValueError('RATE_LIMIT_ENABLED requires REDIS_URL')
        if self.artifact_storage_backend == 's3' and not self.s3_bucket:
            raise ValueError('S3_BUCKET is required for S3 artifact storage')
        if self.langsmith_tracing and not self.langsmith_endpoint.startswith('https://'):
            raise ValueError('LangSmith requires an HTTPS endpoint')
        if self.app_environment == 'production':
            from urllib.parse import unquote, urlparse
            for name, value in (
                ('JWT_SECRET_KEY', self.jwt_secret_key),
                ('METRICS_TOKEN', self.metrics_token),
                ('PLATFORM_ACTION_EXECUTION_CALLBACK_SECRET', self.platform_action_execution_callback_secret),
            ):
                if not value or len(value) < 32 or any(word in value.lower() for word in
                    ('replace_with', 'change-me', 'local-platform', 'do-not-deploy')):
                    raise ValueError(f'{name} must be an independent production secret with at least 32 characters')
            for value in (self.database_url, self.vector_database_url):
                password = unquote(urlparse(value).password or '')
                if not password or password in {'rag_password', 'postgres', 'password'}:
                    raise ValueError('Production database credentials must replace development defaults')
            if self.langsmith_tracing and not self.langsmith_api_key:
                raise ValueError('LANGSMITH_API_KEY is required when production tracing is enabled')
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # The shared .env also contains Compose-only variables such as POSTGRES_*.
        extra='ignore',
    )


settings = Settings()
