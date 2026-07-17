from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    vector_database_url: str
    dashscope_api_key: str
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_chat_model: str = "qwen-plus"
    bailian_embedding_model: str = "text-embedding-v4"
    bailian_embedding_dimensions: int = 1024
    rag_vector_candidate_k: int = 20
    rag_keyword_candidate_k: int = 20
    rag_multi_query_count: int = 3
    rag_final_top_k: int = 5
    rag_min_score: float = 0.05
    rag_enable_llm_query_rewrite: bool = False
    rag_rerank_vector_weight: float = 0.5
    rag_rerank_keyword_weight: float = 0.35
    rag_rerank_overlap_weight: float = 0.15
    context_recent_message_limit: int = 12
    context_summary_message_limit: int = 24
    context_summary_interval: int = 6
    context_memory_limit: int = 20
    context_enable_llm_summary: bool = True
    chat_message_retention_days: int = 180
    audit_log_retention_days: int = 365
    closed_thread_retention_days: int = 365
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
