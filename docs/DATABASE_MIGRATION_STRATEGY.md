# 数据库迁移策略

## 目标

这个项目使用 PostgreSQL 16 + pgvector。数据库变更必须同时满足两条路径：

- 新环境可以用 `sql/schema.sql` 初始化完整结构。
- 已有环境可以按 `sql/NNN_*.sql` 增量迁移到同一结构。

`schema.sql` 是当前全量快照；`NNN_*.sql` 是历史增量记录。后续新增表、字段、索引或约束时，必须同时更新全量快照和新增迁移文件。

## 文件约定

- 全量快照固定为 `sql/schema.sql`。
- 增量迁移文件命名为 `sql/NNN_slug.sql`。
- `NNN` 使用三位递增编号。
- 新迁移必须使用下一个连续编号，不再新增未说明的编号缺口。
- 迁移 SQL 应尽量幂等，例如使用 `CREATE TABLE IF NOT EXISTS`、`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`、`CREATE INDEX IF NOT EXISTS`。
- 迁移文件可以包含必要的数据修复，但必须能在已有结构上安全重复执行。
- 运行时 `ensure_*_schema()` 只作为本地开发和历史环境兜底，不能替代正式迁移文件。

## 历史编号缺口

当前仓库保留以下历史缺口，不再回填同编号文件：

| 编号 | 状态 | 原因 |
| --- | --- | --- |
| 001 | 保留缺口 | 初始基础表已沉淀到 `schema.sql`，早期没有独立 `001_initial_schema.sql`。 |
| 008 | 保留缺口 | 历史平台化 loop 使用运行时 ensure schema 交付，未形成独立迁移文件。 |
| 009 | 保留缺口 | 历史平台化 loop 使用运行时 ensure schema 交付，未形成独立迁移文件。 |
| 010 | 保留缺口 | 历史平台化 loop 使用运行时 ensure schema 交付，未形成独立迁移文件。 |
| 011 | 保留缺口 | 历史平台化 loop 使用运行时 ensure schema 交付，未形成独立迁移文件。 |

后续如果新增 `015_*.sql` 后又跳到 `017_*.sql`，验证脚本必须失败，除非先在本文件中登记并解释新的历史缺口。

## 当前迁移清单

| 文件 | 作用 |
| --- | --- |
| `sql/002_advanced_rag.sql` | 给 RAG 增加部门、父 chunk 和父子 chunk 关联。 |
| `sql/003_context_memory.sql` | 增加会话摘要、会话状态和用户长期记忆。 |
| `sql/004_document_incremental_update.sql` | 增加文档 hash、版本、状态和更新时间。 |
| `sql/005_user_positions.sql` | 给用户增加岗位字段、岗位约束和岗位索引。 |
| `sql/006_automation_runs.sql` | 增加自动化运行记录、步骤和产物表。 |
| `sql/007_customer_service_automation.sql` | 增加客服消息闭环和事件表。 |
| `sql/012_rag_position_scope.sql` | 给 RAG 文档增加岗位 scope。 |
| `sql/013_rag_business_scope.sql` | 给 RAG 文档增加站点和店铺 scope。 |
| `sql/014_rag_field_sensitivity_scope.sql` | 给 RAG 文档增加字段分类和敏感级别 scope。 |
| `sql/015_rag_user_team_authorization.sql` | 给 RAG 增加团队、成员、文档 owner、访问模式和显式授权 grant。 |
| `sql/016_automation_flow_versions.sql` | 增加自动化流程、流程版本和发布指针治理表。 |
| `sql/017_automation_run_flow_references.sql` | 给自动化运行记录增加流程、版本和发布指针引用字段。 |
| `sql/018_automation_flow_preflight_runs.sql` | 增加自动化流程版本发布前预检记录表。 |
| `sql/019_automation_flow_verification_evidence.sql` | 增加自动化流程版本真实验证证据表，用于保存最近通过记录和报告 ID。 |
| `sql/020_enterprise_wechat_contacts.sql` | 增加企业微信成员、群聊和部门候选缓存表，用于发送前搜索和重名点选。 |
| `sql/021_enterprise_wechat_settings.sql` | 增加企业微信后台配置、真实发送开关和同步诊断缓存表。 |

## 运行时 ensure schema 的处理原则

当前仍存在多个 `ensure_*_schema()` 函数，主要用于历史环境和本地开发兜底。后续策略：

- 新增数据库结构时，先写迁移文件，再保留或补充必要的 ensure schema。
- 只改服务层 ensure schema 而不写迁移文件，不能算数据库 loop 完成。
- 如果发现已有 ensure schema 覆盖了 `schema.sql` 中的表或字段，但没有迁移文件，应在后续数据库迁移整理 loop 中补迁移或登记为历史缺口。

## 验证入口

使用：

```bash
python scripts/verify_sql_migrations.py --mode static
python scripts/verify_sql_migrations.py --mode runtime
python scripts/verify_sql_migrations.py --mode all
```

验证含义：

- `static`：不连接数据库，检查迁移命名、编号缺口、迁移清单登记，以及迁移中的表、字段和索引是否被 `schema.sql` 覆盖。
- `runtime`：连接真实 PostgreSQL，在临时 schema 中回放 `schema.sql` 和所有迁移文件，最后删除临时 schema，不写入业务表。
- `all`：同时执行静态检查和真实 PostgreSQL 回放。

`scripts/verify_all.py` 已把静态检查纳入 `quick` / `api` / `release`，把真实 PostgreSQL 回放纳入 `api` / `release`。

## 生产化后台任务

- `sql/022_background_jobs.sql`：持久后台任务及事务 Outbox；默认关闭，发布时显式迁移。
- `sql/023_agent_business_events.sql`：工作区已有 Agent 业务事件去重和运行关联表；纳入统一迁移契约验证。
- `sql/024_agent_tasks.sql`：统一业务任务、店铺岗位授权、跨店业务对象标识、运行尝试关联；显式迁移，不由 API 启动自动应用。

- sql/025_competitor_monitor.sql：按账号隔离的商品竞品快照、运行记录关联及巡检时段唯一约束；显式迁移。
- `sql/026_email_send_confirmations.sql`：敏感文件邮件发送确认记录、文件版本绑定与一次性状态转换。
- `sql/027_mcp_execution_approvals.sql`：受管 MCP 高风险工具的一次性执行许可与核销记录。
- `sql/028_platform_callback_events.sql`：平台回调事件去重、当前执行尝试绑定与回执状态。
- `sql/029_chat_context_version.sql`：会话上下文版本号与 CAS 写入基础字段。
- `sql/030_background_job_retries.sql`：后台任务最大尝试次数和下次重试时间。
- `sql/031_refund_status.sql`：审批、退款执行状态分离和退款流水幂等约束。
- `sql/032_approval_ticket_outbox.sql`：审批外部工单的事务 outbox、重试和对账字段。
