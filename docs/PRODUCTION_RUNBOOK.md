# 生产运行手册

更新：2026-10-21。真实验收和本地当前运行状态见根目录 `PRODUCTION_LOOP.md`。本地开发 Compose 与公网生产覆盖配置分开启用。

## 部署形态

浏览器 → 外部 HTTPS 入口 → Nginx:8080 → FastAPI:8001 → PostgreSQL/pgvector、Redis。
财务异步任务：API 在同一 PostgreSQL 事务写入任务和 Outbox → Beat 触发投递 → RabbitMQ quorum 队列 → Celery Worker → 私有文件存储。
Agent、Skill、RAG、模型和 MCP 调用通过应用内显式 LangSmith 上下文追踪；业务运行记录保存 request/trace ID。服务重启后任务状态仍在 PostgreSQL。

当前 Compose 是单机部署：单 PostgreSQL、单 RabbitMQ、单 Redis，没有实现跨节点高可用。quorum 队列在单节点上也不是高可用集群。保留一个 API 进程以匹配当前 Prometheus 进程内统计；扩到多进程前接入 multiprocess collector 或独立指标采集方案。

## 配置准备

1. 在独立生产目录准备 `.env`，参考 `.env.example`；不要将真实密钥提交到 Git。按实际环境填写模型、ERP、邮件等配置。
2. 为 `POSTGRES_PASSWORD`、`RABBITMQ_PASSWORD`、`JWT_SECRET_KEY`、`METRICS_TOKEN`、`PLATFORM_ACTION_EXECUTION_CALLBACK_SECRET` 分别生成随机值，后三项至少 32 字符。Compose 拼接连接串的数据库/队列密码使用 URL-safe 字符。设置独立 `REDIS_KEY_PREFIX` 和生产 `CORS_ALLOWED_ORIGINS`。
3. PostgreSQL 已有数据卷不会因修改 `POSTGRES_PASSWORD` 自动改密码：先备份，再由数据库管理员显式轮换角色密码并同步应用配置。禁止为了改密码删除数据卷。
4. 生产覆盖配置强制生产模式、任务、共享限流，只绑定本机 API/web 端口，关闭数据库和 RabbitMQ 宿主机端口。Redis 仅在专用 Docker 网络使用；跨主机部署改为鉴权/TLS 连接。`/metrics` 在 Nginx 公共入口被拒绝，仅允许内部采集携带专用 Bearer token 访问 API。
5. 配置域名和 TLS，并将流式请求超时调至大于业务超时。配置真实代理网段后再允许 Uvicorn 信任转发地址；不要直接信任全网转发地址。当前限流按连接 IP 计数，代理不传递可信来源时多个用户会共享配额；尚未实现账号/租户消费额度。
6. 容器沿用项目原有运行用户。上线应配置非 root UID/GID 和数据目录权限；不要未经迁移直接修改现有目录属主。镜像精确摘要和 Python 依赖锁定仍需在发布流程补齐。

本地只启动 API 可设 `CONTEXT_CLEANUP_SCHEDULER=api`；Compose 使用独立 Beat。Beat 只启动一个，不能通过多实例扩容；不要使用 Celery `-B` 在每个 Worker 再启动调度器。

本地完整开发栈使用 `docker-compose.local.yml`，保留现有数据库卷/凭据，只启用异步任务和 Redis 限流。首次使用 RabbitMQ 前应在 `.env` 配置独立随机 URL-safe 密码，随后仅通过容器内命令轮换 RabbitMQ 凭据，并将 `.env` 保持 0600。启动方式：

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile monitoring up -d prometheus
```

Prometheus UI 在 `http://127.0.0.1:9091`，只绑定本机；`data/monitoring/metrics-token` 为私有 Bearer 凭据。配置和 11 条初始告警位于 `deploy/monitoring/`。规则采集 API、Agent/Skill、任务积压/失败/超时与 Worker/Beat 心跳。配置文件会创建可见告警，但不会向人发送消息；接收方确定后再接 Alertmanager。LangSmith 项目通知也需单独指定接收目的地。

## 迁移与启动

需要 Docker Compose 2.24.4 或更高版本，支持 `!override` / `!reset`。先完成备份和恢复演练。

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.production.yml build api worker beat web
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d postgres redis rabbitmq
# 已有库在启用异步任务前执行；新空库由 schema.sql 初始化。
docker compose -f docker-compose.yml -f docker-compose.production.yml run --rm --no-deps api python scripts/migrate_production.py
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d api worker beat web
curl --fail http://127.0.0.1:8001/ready
```

迁移工具显式应用 `022_background_jobs.sql` 和工作区已有的 `023_agent_business_events.sql`，均为幂等新增表迁移，不在 API 启动自动执行。历史 `ensure_*_schema` 尚未完全移出启动流程，账号仍需对应历史初始化权限；完整迁移管理和独立 DDL 角色留待下一轮。不要在生产植入 demo 账号，并清理/禁用既有演示账号。

RabbitMQ 4 使用持久化 quorum 队列，关闭 Celery 临时远程控制、mingle/gossip 队列。若既有 vhost 有同名 classic 队列，应先停投递并排空备份，再迁移类型，或使用新 vhost 并同步配置；有业务消息时不要直接删除队列。Worker 配置 publisher confirms、late ack、worker-lost redelivery、prefetch=1。

## 启用 LangSmith

目标 `.env` 配置后重新创建 API/Worker 容器：

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-private-key>
LANGSMITH_PROJECT=company-rag-agent-prod
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_WORKSPACE_ID=
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
LANGSMITH_TRACING_SAMPLING_RATE=0.1
```

endpoint 必须为 HTTPS，按实际账号区域选择。Key 仅进入私有客户端，不转交前端。默认输入为空，输出仅保留 token 用量，错误替换为通用错误，metadata 使用白名单，去除附件、事件和序列化运行时信息。采样默认 10%；验收可临时设 1.0，再恢复。
2026-10-21 已完成开发项目 company-rag-agent-dev 云端验收并更新本地 API。真实 Agent/Skill 请求、父子链路、模型 token 用量和默认隐私设置均经云端回读检查；证据见 PRODUCTION_LOOP.md。Key 仅保存在本地私有 .env（0600、Git 忽略）；生产仍应使用独立项目/凭证并配置告警。
可复验：python scripts/verify_langsmith_live.py；加 --model 会产生一次真实短模型调用及对应费用。仅验收进程强制 100% 采样，不改实际配置。受控错误节点用于错误脱敏验收。
导出失败记录通用警告，不让业务因监控服务故障失败。隐藏开关设 false 时仅尽力脱敏，不保证任意自由文本；企业场景建议保持 true。MCP 子进程禁用独立自动追踪，父进程记录 MCP 调用。异步 Worker 通过 request ID 关联原请求，不声称跨队列保持同一父子 trace。

## 异步任务接入

财务 Agent 的“对账任务”页使用新增持久入口。旧对账路由默认进入任务页；页面定时刷新最近 50 条本人任务，离开页面后可重返，成功后沿用生成文件接口鉴权下载。旧同步 API 保留给现有调用方。

```bash
curl --fail -X POST http://127.0.0.1:8001/jobs/finance-reconciliation \
  -H "Authorization: Bearer <finance-or-admin-token>" \
  -H "Idempotency-Key: <unique-key-at-least-8-characters>" \
  -F "files=@settlement.xlsx" -F "base_currency=CNY"
```

返回 202，按 `status_url` 轮询，成功后下载 `result.download_url`。1–8 个 xlsx/xls，单文件 ≤8MiB，总计 ≤32MiB。岗位和 `finance-reconciliation` 应用权限在入队及执行时检查；状态与文件隔离所属用户和岗位。相同用户+幂等键+相同文件摘要复用任务；不同输入返回 409。队列只携带任务 ID。
Outbox 每 5 秒投递，发布失败 30 秒后重试；已发布但 15 分钟未完成的任务再次投递。消费者用 PostgreSQL advisory lock 和终态检查去重，执行次数上限 3；崩溃在结果发布后可恢复既有产物。普通异常直接标记失败，当前队列仅接入文件对账生成，未自动重试外部发送/退款/发布。
终态任务输入默认保留 7 天，之后删除原文件并保留幂等摘要；输出遵循 generated-file 到期时间；S3 供 RPA 使用的本机副本默认 24 小时后在每日维护清理。上传后、数据库提交前突然崩溃产生的孤立对象尚未由数据库清理覆盖，应配置桶生命周期和定期对象对账。

## 文件存储

默认 `ARTIFACT_STORAGE_BACKEND=local`，API/Worker 共享私有 `data`。多实例切换 `s3`，配置桶、区域、可选 endpoint，优先云运行身份或专用受限 access key。禁止公共读，bucket/prefix 限最小权限，配置服务端加密、版本和生命周期。
历史本地引用仍需原共享目录，不会自动上传。S3 下载仍经 API 权限校验。适配已通过真实 MinIO CRUD 验证；云 IAM、加密和网络需实际环境验收。

## 备份、故障和回滚

`scripts/backup_database.sh /secure/backups` 使用 libpq `PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSFILE`，生成权限受限 custom dump 并检查目录；PGPASSFILE 必须 0600，密码不放命令参数。另存异地并加密，按实际 RPO/RTO 设置保留策略。必须在独立数据库执行 `pg_restore --exit-on-error --no-owner --no-acl` 后检查业务数据，dump 目录可读不等于恢复成功。本轮未创建实际备份定时任务。

- Redis 故障：缓存退回正常获取；受保护登录/AI 入口和 `/ready` 返回 503，避免绕过限流。
- RabbitMQ/Worker 故障：授权任务和 Outbox 仍可事务落库，恢复后继续投递；监控积压、最老等待时间、失败率、数据库连接、磁盘和内存。
- 回滚：停 Beat/Worker，等待文件任务完成，回退镜像并关闭 BACKGROUND_JOBS_ENABLED、RATE_LIMIT_ENABLED；旧同步入口继续使用。保留新增表，不做破坏性 down migration；LangSmith 可独立关闭。

## 验证命令

```bash
python -m compileall -q app scripts
python scripts/verify_sql_migrations.py --mode all
python scripts/verify_production_foundations.py --redis --api-base-url http://127.0.0.1:8001
npm --prefix frontend run build
bash -n scripts/backup_database.sh
```

API 脚本使用 finance_demo / operations_demo，只在测试库运行，不向生产植入 demo。`--worker-recovery` 故意改变测试任务状态，仅接受数据库名以 `_verification` 结尾的隔离库。CI 包含真实 PostgreSQL 迁移回放和 Redis 并发限流；完整 RabbitMQ/API/文件回归本轮本地通过，尚未配置每次 PR 的整栈自动验收。
