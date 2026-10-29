# 生产化修改循环计划

更新：2026-10-21。执行方式：检查现状 → 小步修改 → 真实验证 → 修复 → 记录结果。原有未提交业务/前端修改保留；本轮启用了本地完整队列栈，没有部署公网生产环境。

## 本轮结果

| 循环 | 已交付 | 验收状态 |
| --- | --- | --- |
| 1：Agent 观测 | LangSmith 私有追踪、Agent/Skill/RAG/模型/MCP 链路、SSE 生命周期、采样与隐私；Prometheus 运行/延迟/错误指标及 11 条告警 | Agent/Skill 与 Worker 任务 trace 均经云端回读；Prometheus 抓取健康、11 条规则已加载；通知渠道待配置 |
| 2：异步执行 | Celery Worker/Beat、RabbitMQ 4 quorum 队列、JSON 序列化、publisher confirms、late ack、独立任务路由、数据库锁 | 真实 broker/worker 调度、路由、重复投递和恢复通过 |
| 3：共享缓存 | Redis embedding/企业微信 token 缓存、固定窗口原子限流、连接池配置 | 真实 Redis CRUD、20 并发仅放行 5、HTTP 429、停 Redis 后 503 与缓存降级通过 |
| 4：存储与部署 | 本地/S3 文件适配、权限复用、Nginx/SSE、ready/metrics、生产密钥检查、Compose 覆盖、备份工具 | 真实 MinIO CRUD、权限下载、配置检查、独立库备份恢复通过；云存储策略/TLS/非 root 部署待环境验收 |
| 5：持久任务 | PostgreSQL jobs + 事务 Outbox、财务对账异步 API 与 Agent 页面、幂等键、岗位复核、孤立投递恢复、过期输入/临时文件清理、CI 基础回归 | 真实登录→上传→202→离页重返/刷新→任务完成→XLSX 下载通过；API/Worker 重启后 Outbox 恢复通过 |
| 6：前端拆分 | 27 个页面、8 个弹窗、门户和工作台布局按需加载；独立公共组件与类型；体积预算 CI；Nginx 缓存与 gzip | 真实构建与四种岗位浏览器回归通过；门户首屏 JS 降 49.7%、工作台概览降 34.9%；最大块 407 kB，无超大块警告 |
| 7：状态与请求拆分 | 会话、个人设置、集成管理、运行观测与按页加载 5 个 hooks；旧会话响应保护和退出清理 | 类型检查通过；真实浏览器重跑中，本地 PostgreSQL 异常恢复曾导致登录 500/超时；详见本轮报告 |

## 核心文件

- 观测：`app/observability.py`；应用入口和业务运行记录接入。
- 执行：`app/celery_app.py`、`app/tasks.py`、`app/api/jobs.py`、`app/services/background_job_service.py`。
- 存储/保护：`app/cache.py`、`app/rate_limit.py`、`app/artifact_storage.py`、`app/production_health.py`。
- 部署：`docker-compose.production.yml`、`deploy/`、`scripts/migrate_production.py`、`scripts/backup_database.sh`。
- 运行说明：[docs/PRODUCTION_RUNBOOK.md](docs/PRODUCTION_RUNBOOK.md)。

## 第一轮真实验证证据（配置 LangSmith 前）

使用隔离 PostgreSQL 数据库 `company_rag_loop_verification`，独立 RabbitMQ 4、Redis 7、MinIO 容器和 API/Worker/Beat；没有更改既有演示库，未调用真实外部业务发送或模型计费。测试账号通过真实 `/auth/login` 登录：finance_demo / operations_demo。没有使用 mock、stub、fake provider、monkeypatch 或模拟成功响应。

| 命令/操作 | 结果 |
| --- | --- |
| `python -m compileall -q app scripts` | 通过 |
| `python scripts/verify_production_foundations.py --redis --api-base-url http://127.0.0.1:18091 --worker-recovery` | 本地 wrappers/隐私/线程/存储、Redis 并发、真实登录、403 岗位拦截、202 入队、相同输入复用、409 冲突、404 任务隔离、XLSX 解析、403 文件隔离、重复投递/产物恢复/15 分钟 Outbox 修复均通过 |
| 最终全链路测试任务 | `7a83169b-fe1a-4afe-a4ca-bd44b5831273`；最终 topic 路由版全部通过，测试记录随隔离库清理，不是生产任务 |
| 真实 RabbitMQ 路由检查 | 无消费者时各投递 1 条业务/维护任务，各队列正好 1 条；修复初始共享路由键问题 |
| 真实 Redis 中断 | 缓存读返回 miss；受保护 HTTP 和 ready=503；恢复服务后可重新 ready |
| 终态文件清理 | 8 天前任务输入删除、摘要保留、重复清理=0；过期临时文件删除、新文件保留 |
| `python scripts/verify_sql_migrations.py --mode all` | 18 个迁移、38 表、135 索引，临时 schema 回放后删除；补齐工作区已有 023 的快照/登记 |
| `python scripts/migrate_production.py` | 在隔离库幂等应用 022 和 023 成功 |
| `ARTIFACT_STORAGE_BACKEND=s3 ... verify_production_foundations.py` | 真实 MinIO 写入、存在、读取、删除通过；未上传企业数据 |
| `bash scripts/backup_database.sh /tmp/company-rag-loop-backups` + `pg_restore --exit-on-error --no-owner --no-acl` | 真实备份恢复到 `company_rag_loop_restore_verification`；users/jobs/artifacts 均为 3/3/3，与备份时源库一致 |
| 生产 Settings + Compose config | 开发密码被生产模式拒绝；独立密钥可启动；数据库/队列不映射宿主机端口；API/web 仅 loopback |
| `nginx -t`、`bash -n scripts/backup_database.sh`、`git diff --check` | 通过 |
| `npm --prefix frontend run build` | TypeScript/Vite 通过，14356 modules；JS 约 2.2MB，仍有 chunk 大于 500KB 提示 |

CI 已增加真实 PostgreSQL 迁移回放、Redis 并发验证和前端构建，GitHub Actions 远端运行结果仍待提交后验证。本轮补上真实 Chromium 浏览器验收。

## 当前运行环境与本轮 Loop 验收（2026-10-21）

- 本地 `docker compose -f docker-compose.yml -f docker-compose.local.yml up -d` 运行 API、PostgreSQL、Redis、RabbitMQ、Worker 和单实例 Beat。Prometheus 使用 `--profile monitoring` 单独启动，端口只绑定回环地址。
- 增量迁移 022/023/024 已提交到本地数据库；变更前 custom dump：`data/backups/before-jobs-20261021T061410Z.dump`，权限 0600。
- `company-rag-api`、Worker、Beat、RabbitMQ、Redis、Prometheus 全部运行；API `/ready=200`，Prometheus target `api:8001` 为 `up`，监控规则组已加载 11 条告警。
- `.env` 保留 0600；本地 RabbitMQ 密码在启用队列前已轮换为随机值，API/Worker/Beat 使用容器网络内的连接地址；没有将连接凭据打印到日志或仓库。
- 真实浏览器验收：`node scripts/verify_finance_jobs_frontend.mjs data/verification/finance-jobs/settlement.xlsx`。finance_demo 登录并真实上传；服务返回 202；从财务对账旧入口打开时默认显示任务页；离开页面、返回和刷新后仍能看到同一任务；Worker 生成并下载有效 XLSX；390px 视口无横向溢出。截图：`data/verification/finance-jobs/desktop.png`、`mobile.png`。
- 真实权限验收：finance_demo 可查看本人任务；operations_demo 对任务列表和其他岗位任务均返回 404。
- 持久恢复验收：停 Worker 时任务和 Outbox 保存在 PostgreSQL；API 重启、重新启用 Beat/Worker 后，同一任务完成，`attempt_count=1`。
- LangSmith Worker 验收：临时仅对验收 Worker 使用 100% 采样，重置为正常 10% 后云端回读。Root run `01a15d5a-7f5a-7872-ab43-27d107565517`；request ID `bab93de8-aebc-4a63-91c3-8388e932de67` 与 task ID 匹配，输入/输出仍隐藏；API/Worker/Beat 最终采样均恢复 10%。跨队列使用 request/task metadata 关联，不把它标记成同一父子 trace。
- 验收测试创建的 3 个任务、上传件、结果文件和运行记录均在验收后删除；只保留无业务内容的桌面与移动端截图和云端追踪审计记录。
- `npm --prefix frontend run build`、`python -m compileall -q app scripts`、`node --check scripts/verify_finance_jobs_frontend.mjs`、`git diff --check`、`docker compose ... config --quiet`、`promtool check rules` 均通过。前端 bundle 仍约 2.2MB，Vite 提示需要后续拆分。

Prometheus 规则覆盖 scrape/API 不可用、Redis/metrics 采集失败、Worker/Beat 心跳、Outbox 与任务积压、任务超时、任务失败、Agent 错误/延迟和 HTTP 错误率/延迟。规则可在本地 Prometheus `/alerts` 查看；目前没有 Alertmanager 收件人，也未配置 LangSmith 云端通知目的地，所以本轮只确认采集及规则加载，没有声称主动发送通知。

## 后续 Loop

前端拆分验收详见 [docs/FRONTEND_BUNDLE_OPTIMIZATION.md](docs/FRONTEND_BUNDLE_OPTIMIZATION.md)。本地生产产物预览为 `http://127.0.0.1:5174`；管理员表单登录、业务路由、设置页导航/刷新、流程和连接器弹窗开关/重开、Agent 技术详情、390px 布局、财务任务 GET/刷新、四种账号的岗位跳转均通过。浏览器实际请求的 JS 累计大小与 manifest 预算一致，`pageerror`、失败分块及失败 API 响应均为 0；未创建业务任务。证据位于 `data/verification/frontend-bundle/`；临时 Nginx 验收容器已删除。没有部署公网，也没有触发远端 CI。

前端状态与请求拆分见 [docs/FRONTEND_STATE_OPTIMIZATION.md](docs/FRONTEND_STATE_OPTIMIZATION.md)。会话、设置、集成管理和运行观测已拆成 hooks，全量初始化已改为按页加载；剩余聊天、ERP、文件及通知审批仍可按领域继续拆分。本轮真实验收状态单独记录，不沿用上一轮通过结果。

1. 配置并验收 LangSmith 与 Alertmanager 的实际通知接收方及告警去重/恢复通知。
2. 把其余需长时间运行的 Agent 工作流逐步迁入持久队列；完善队列取消、人工重试、按账号/租户限额。外部副作用继续采用独立幂等和审批。
3. 增加整栈 PR CI、依赖锁定/镜像摘要、非 root 运行和供应链扫描。
4. 全量数据库迁移版本管理、DDL/业务账号隔离、SSO/HttpOnly 会话、密钥托管。
5. TLS/域名、对象存储 IAM/加密/生命周期、异地备份与 RPO/RTO 验证；按容量决定高可用集群。

LangSmith 仓库默认关闭，缺 API Key 时不上传。当前生产基础能力已落代码并完成列出的本地真实验收，尚不能等同于已上线或全系统完成生产认证。

## LangSmith 实际接入验收（2026-10-21）

- 用户提供的 API Key 已写入 Git 忽略的本地 `.env`，文件权限 0600；未写入代码、镜像或文档。
- 真实认证通过，创建项目 `company-rag-agent-dev`，project ID `3cf5f8c4-6e10-4b17-b08f-c28a6f63f362`。
- `python scripts/verify_langsmith_live.py --model` 通过真实云端上传和回读：5 个运行节点，包含同步/异步/线程传播、受控错误和真实 ChatOpenAI 子调用。
- 通过 trace：`01a15d01-c909-7db0-91be-2fd69f70728f`；模型 token 数 26；输入为空、输出只保留用量、错误已替换、隐私 canary 未上传。
- 验收进程临时强制采样 100%，实际配置保留 10%；没有切换业务模型配置。
- 真实 API/Skill：登录 → Excel 上传 → skill.execute → Excel 下载 → 云端回读；root trace 01a15d05-5776-70d2-800b-a05e9660b05d。
- 真实 Agent：/agent/chat → LangGraph → 模型 → 云端回读；root trace 01a15d06-2a3a-7b13-8065-7e1dc4266171，8 个节点，模型用量可见。
- 已更新本地 company-rag-api，真实登录通过，10% 采样请求回读获得 3 条 trace；例 01a15d08-4faa-7b02-b6ac-2cdc23611f1f。
- 上一版停止容器 company-rag-api-pre-langsmith 保留供回滚；验收 canary 容器、验收文件/运行记录/会话已清理，云端验收 trace 留作证据。
- 最终本地 API 状态 running/healthy；ready=200，request ID、真实财务登录和身份校验通过。当前只启动 API，Worker/Beat 全栈启用仍依照运行手册单独部署。
