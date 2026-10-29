# Company RAG Agent 缺陷修复 Loop 计划

制定日期：2026-10-27。依据：docs/BUG_FIX_PLAN.md 的 FIX-001 至 FIX-017。

## 范围与当前判断

- 本文件是执行计划，不代表缺陷已经修复或回归已经通过。原审查为静态审查；实施前按当前代码重新复现，不能直接沿用旧行号或旧测试结果。
- 工作区已有大量未提交的前后端改动。每轮先核对目标文件的当前 diff；保留既有修改，不重置、不覆盖、不代为提交。
- 已见部分实现迹象：对话意图有新 guard 和评测脚本，复杂计划有 waiting_email_confirmation，平台回调对普通响应隐藏 token。仍可见回调先读状态再更新、重试不换 token、部分路径直接调用 SMTP、MCP 高风险阻断未覆盖 chat_plan_execute、后台任务普通异常直接失败，以及 /agent/chat 使用 InMemorySaver。这些只作为优先核验点。
- 项目已有 scripts/verify_*.py 和前端验证脚本，暂无统一 tests/ 目录。每轮沿用现有验证入口，补针对性回归；涉及真实外部动作时使用隔离库和可验证的沙箱或 mock 出站端点。

## 每轮固定闭环

1. **现状与复现**：记录目标文件 diff、当前 API/数据库/队列状态；用最小案例重现或证伪该缺陷，留 request ID 和失败证据。
2. **锁定契约**：写明状态转换、权限边界、幂等键、超时和失败语义；先补失败用例，再改代码。
3. **小范围修复**：一次只处理本轮清单，不做无关重构；有表结构变化时同时更新增量迁移、新库 schema 和迁移登记。
4. **分层验证**：运行本轮单元/接口用例，再用 PostgreSQL、Redis、RabbitMQ 与等价外部回调环境做并发或故障注入；记录成功、失败和未覆盖项。
5. **收口**：核对审计、运行记录、通知和业务状态的同一 request ID；复跑原复现案例。任何验收未通过，保持本轮“待修复”，不得把后续 Loop 标为完成。

状态统一使用：待执行 / 进行中 / 待修复 / 代码已验证·待外部联调 / 已验收。每轮更新实际改动文件、验证命令、环境、证据、耗时变化和剩余风险。延迟记录按入口、工作流和步骤统计 P50/P95；先采基线，再比较修复前后，不预设未经测量的数字。

## 执行顺序

| Loop | 覆盖项 | 主要交付 | 本轮通过条件 | 状态 |
| --- | --- | --- | --- | --- |
| 00 基线 | FIX-001–017 | 逐项核验当前实现、复现脚本、权限与外部动作清单；建立隔离测试数据和延迟基线 | 17 项均有“已复现/已修复待验/不适用”证据；不触发真实发送、退款、发布 | 进行中 |
| 01 外发与工具闸门 | FIX-005、FIX-006 | 工资/财务文件统一确认卡；确认绑定收件人、artifact 版本和有效期；MCP 执行器服务端校验审批与来源 | /chat、stream、复杂计划和直接 MCP 入口未确认时均不调用 SMTP/高风险工具；改收件人或文件后旧确认失效，拒绝有审计 | 代码已验证·待外部联调 |
| 02 平台回调 | FIX-002、FIX-003 | 条件更新实现一次性状态转换；每次 attempt 新 callback token；事件唯一键和重复回调结果复用 | 成功/失败并发只有一个胜出；重复、乱序、旧 attempt 回调均无重复写回或通知，当前 attempt 正常完成 | 代码已验证·待外部联调 |
| 03 会话一致性 | FIX-001、FIX-009 | 同一 thread 分布式串行化或数据库 advisory lock；context_version CAS；明确指代才继承订单号 | 同 thread 不串线、不同 thread 可并行；锁超时可见且异常/取消释放；无明确指代不沿用旧订单 | 代码已验证·待外部联调 |
| 04 任务与流式生命周期 | FIX-004、FIX-010、FIX-016 | 临时异常分类重试；canonical step ID 与版本/输入/产物匹配；取消时 finish_run 和资源清理 | 一次性故障自动恢复，永久错误直接失败；重复投递不重复产物/外部动作；断流后无永久 running | 代码已验证·待外部联调 |
| 05 退款与审批事务 | FIX-013、FIX-014、FIX-015 | 本地审批与 outbox 同事务；审批/退款分状态；申请人与审批人隔离；退款幂等和可恢复失败 | 自审批被拒；审批成功但退款失败状态准确；重试不重复扣款；外部工单失败可重试、可对账 | 代码已验证·待外部联调 |
| 06 并发性能与 Agent 状态 | FIX-007、FIX-008 | 同步重操作移至线程池/持久 worker；Agent 每轮从 PostgreSQL 上下文恢复，移除进程内记忆 | 慢 Excel/图片任务不阻塞健康检查；跨 worker 与重启可恢复；普通请求 P95 对照基线无异常放大 | 进行中 |
| 07 客服决策质量 | FIX-011、FIX-012、FIX-017 | 物流/订单资源按意图优先；ERP/RAG 分源降级；退款路由优先于普通订单查询 | 中英文物流、退款、订单状态集通过；单源失败只生成带缺失说明的有限草稿，高风险转人工 | 代码已验证·待外部联调 |
| 08 全链路回归 | 全部 | 复测 17 项、前端状态展示、权限、迁移、审计、性能与沙箱外部回执 | P1 全部有自动化及集成证据；P2 有针对性证据；无新增数据串线、越权动作、重复扣款或真实误发送 | 进行中 |

## 关键依赖与实施细节

- **Loop 01 先封住副作用入口**：同一确认对象必须包含账号、收件人、文件标识/hash、版本、动作和失效时间。LLM 输出的 confirmed、sensitive_confirmed 或步骤 JSON 不构成授权。
- **Loop 02 再处理外部回调**：状态机只允许 dispatching/waiting_callback 到 succeeded/failed；SQL 必须以旧状态和当前 attempt/execution ID 为条件，并检查影响行数。只让成功取得转换权的一方写草稿、审计与通知。旧 token 应立即失效，普通响应及日志只保留脱敏信息。
- **Loop 03 保证会话顺序**：锁必须覆盖读取、决策和上下文写入；CAS 防止锁异常或迟到结果覆盖新版本。流式请求的锁释放与 Loop 04 取消处理联测。
- **Loop 04 区分可重试与未知结果**：只对网络/数据库/队列短暂异常自动重试。外部发送、发布、退款的超时结果不明时先查询状态，不能盲目重放。
- **Loop 05 资金状态分离**：approved 是审批结果，不等于退款成功。外部工单和退款均需业务幂等键、失败补偿/对账路径和独立状态展示。
- **Loop 06/07 的性能与答案验收**：记录入口总耗时及 ERP、RAG、LLM、文件生成等步骤耗时；失败降级时不得编造缺失数据。

## 验证门槛

- 每轮先跑目标脚本及其相邻业务脚本；现有入口包括 scripts/verify_platform_execution_task_callback.py、scripts/verify_platform_action_executor.py、scripts/verify_customer_service_refund_approvals.py、scripts/verify_chat_threads_loop.py、scripts/verify_finance_salary_wechat_send.py、scripts/verify_chat_intent_routing.py 和 scripts/verify_production_foundations.py。脚本名字不等于已覆盖缺陷，需检查断言并补并发、乱序、断流与故障注入。
- 所有 P1 需要自动化用例和等价集成环境证据。P2 至少有单元、接口或故障注入证据；依赖真实 ERP/平台的部分单列“待外部联调”，不能写成已验收。
- 全局收口命令：python3 -m compileall -q app；项目后端回归脚本；npm --prefix frontend run build；git diff --check。迁移须在新库与已有库各跑一次；前端状态变化须做岗位与移动端检查。
- 测试真实发送默认关闭。SMTP、MCP、平台回调、退款与客服渠道使用明确的测试对象/沙箱；未获真实业务授权不对真实客户、商店或员工执行动作。

## 第一轮开始条件

从 Loop 00 开始，先为 FIX-005/006、002/003 和 001 建最小失败案例，按 Loop 01 → 02 → 03 推进。每轮只在代码和验收证据齐备后更新状态；若环境暂时无法联调，记录阻塞原因并继续独立的代码验证。

## 2026-10-27 执行记录：Loop 01

- 修复：`/chat`、`/chat/stream` 的工资表及财务组合文件改为持久化邮件确认卡；确认记录绑定账号、收件人、附件 ID、文件 SHA-256 与 30 分钟有效期。确认接口使用数据库条件更新抢占发送权，结果未知时禁止自动重试。发送状态写入审计、运行步骤和聊天卡片。无有效邮箱时仍返回生成文件。
- 修复：受管 MCP 的 `requires_approval` 在执行前强制核销后端签发、绑定用户/来源/参数哈希且 5 分钟有效的一次性许可；复杂计划和伪造参数无法直调。独立 `message_sender` MCP 的直发能力关闭，真实邮件只走认证确认接口。受控 n8n/RPA/Amazon 准备入口签发许可。
- 文件：`app/services/email_confirmation_service.py`、`app/services/mcp_tool_registry_service.py`、`app/mcp_servers/message_sender.py`、相关聊天/自动化 API 与前端确认卡；新增 `sql/026_email_send_confirmations.sql`、`sql/027_mcp_execution_approvals.sql`，已应用到本地 PostgreSQL，并登记在 `scripts/migrate_production.py` 和新库 schema。
- 验证：`.venv/bin/python scripts/verify_email_confirmation_gate.py`、`verify_mcp_approval_db.py`、`verify_mcp_tool_layer.py`、`verify_finance_salary_wechat_send.py` 均通过；`python3 -m compileall -q app`、`npm --prefix frontend run build`、`git diff --check` 均通过。本机隔离 API `/health` 与 `/ready` 均返回 200；未登录确认返回 401，伪造确认 ID 返回 404。测试未提交真实发送确认，SMTP、n8n、RPA 和企业微信均使用替身或阻断路径。
- 未完成：本机 `/chat` 财务示例在 ERPNext 主机解析处返回 400，未到文件建卡；因此 `/chat`、stream 的真实 ERP 端到端验收和前端浏览器点击、SMTP 沙箱回执仍待联调。本轮未采集完整客户反馈到任务完成的 P50/P95，不能用脚本运行秒数替代业务延迟基线。Loop 00 其余 15 项与 Loop 02 以后仍待执行。

## 2026-10-27 执行记录：Loop 02

- 修复：回调请求必须携带 `attempt_count`、`execution_id` 和 `external_event_id`，并继续通过时间戳及 HMAC 签名验证。任务状态用旧状态、当前 token、attempt 和 execution ID 的条件更新抢占；只有抢占成功者执行草稿写回、审计和终态通知。相同事件的重发读取终态结果，事件 ID 对应不同内容返回 409；旧 token 返回 404，当前 token 携带旧 execution ID 返回 409，拒绝原因写审计且不记录 token。
- 修复：重试派发生成新 token，清理上一 attempt 的处理标记。异步执行器响应的任务状态与草稿“等待回调”写回在同一事务内完成；提前到达的回调不会被迟到的派发结果覆盖。同步执行器响应也通过条件更新抢占终态，回调会等待其写回完成。回调的同步数据库逻辑移入线程池，允许单 worker 下真实并发请求。
- 文件：`app/api/platform_execution_tasks.py`、`app/services/platform_action_executor_service.py`、`app/services/platform_draft_service.py`、`scripts/verify_platform_execution_task_callback.py`；新增 `sql/028_platform_callback_events.sql`、`scripts/verify_platform_callback_atomic.py`。028 已应用到本地 PostgreSQL，并登记迁移脚本及新库 schema。
- 验证：隔离的本地 API + PostgreSQL 脚本 `.venv/bin/python scripts/verify_platform_callback_atomic.py` 通过：成功/失败并发只有 1 条终态审计和 1 条终态通知；重复签名 nonce/事件返回 200；旧 token 返回 404，错误 execution ID 返回 409，当前 attempt 返回 200；提前回调、3 组派发竞态和同步写回等待均通过。脚本使用本地数据库 fixture，不请求真实平台、不发布商品、不发送客服回复；执行后清理 fixture。`compileall` 与 `git diff --check` 通过。
- 待联调：真实执行器的回调字段升级与沙箱回执、跨多 worker/容器的故障注入尚未验收。若抢占终态后进程在草稿/通知写回前退出，任务会停在待人工核查的未完成收尾状态；本轮未实现持久化恢复 worker。Loop 00 的完整延迟 P50/P95 基线仍未采集，不能用本地脚本耗时代替。

## 2026-10-27 执行记录：Loop 03

- 修复：`/chat`、`/chat/stream`、`/agent/chat` 在读取上下文前取得按 thread ID 派生的 PostgreSQL session advisory lock，同 thread 串行、不同 thread 并行；5 秒未取得锁返回 423 和 `Retry-After`。流式响应保持锁到生成器结束，并在关闭/取消时释放。
- 修复：新增 `chat_thread_state.context_version`，每次写回要求调用方传入读取时版本，数据库条件更新失败返回 409；22 处普通/流式聊天写回传入同一请求的版本。用户消息自动保存请求 ID。未明确指代旧订单时清空状态订单号；“这个订单/刚才订单”等才继承，继承来源写入状态槽和审计。
- 文件：`app/services/chat_thread_lock_service.py`、`app/services/context_service.py`、`app/services/logging_service.py`、`app/graph/workflow.py`、`app/graph/extractors.py`、`app/graph/state.py`、`app/main.py`；新增 `sql/029_chat_context_version.sql`、`scripts/verify_chat_context_consistency.py`。029 已应用本地 PostgreSQL，并登记迁移脚本和新库 schema。
- 验证：`.venv/bin/python scripts/verify_chat_context_consistency.py` 通过版本冲突 409、同 thread 锁超时 423、不同 thread 并行、两个普通请求串行、流式完成/主动关闭释放锁、订单明确指代/非指代及继承审计；fixture 自动清理。后端重启后 `/health`、`/ready` 均为 200，三个聊天路由注册正确。
- 待联调：实际 ERP/LLM 长会话、跨 worker/容器及真实客户端断流仍需压测和故障注入；本轮无客户完整链路 P50/P95。流式运行记录取消时的终态收口属于 Loop 04，尚未修复。

## 2026-10-27 执行记录：Loop 04

- FIX-010：`chat_plan_execute_service.py` 改用版本化步骤 ID；续跑时核对输入、附件、权限哈希和计划版本。旧记录或外部执行结果未知时返回 409，不盲目重放外部动作。
- FIX-004：Celery 任务区分暂时性和永久错误，按数据库尝试次数指数退避并持久化下次执行时间；API 和前端显示重试状态。新增并在本地库应用 `sql/030_background_job_retries.sql`。
- FIX-016：流关闭或取消时结束活动步骤和运行记录，写取消审计和指标，释放会话锁。
- 验证：`verify_chat_plan_resume.py`、`verify_background_job_retries.py`、`verify_chat_context_consistency.py` 连续通过；财务后台任务故障注入覆盖一次故障恢复、永久失败和次数耗尽。未在真实 Celery worker/beat、跨容器或真实客户端断流环境联调。

## 2026-10-27 执行记录：Loop 05

- FIX-013：审批及 outbox 同事务写入，使用业务键幂等；外部工单失败可重试，结果未知时先对账。新增并应用 `sql/032_approval_ticket_outbox.sql`。本地 JSONL 工单写入加锁去重。
- FIX-014/015：审批与退款分状态，申请人自审批和自重试被拒；高风险退款要求有效客服主管成员资格；退款失败可重试，并以审批 ID 约束退款流水。新增并应用 `sql/031_refund_status.sql`。前端分别显示审批、退款、外部工单状态。
- 验证：`verify_refund_approval_state.py`、`verify_approval_ticket_outbox.py` 通过并发、重试和未知结果故障注入。`VERIFY_API_BASE_URL=http://127.0.0.1:8003 .venv/bin/python scripts/verify_customer_service_refund_approvals.py` 对当前后端通过；未指定端口时脚本默认命中旧 8001 服务并失败，不能把旧服务结果作为当前代码证据。前端构建、Python 编译及 `git diff --check` 通过。
- 待联调：本地后端以 `BACKGROUND_JOBS_ENABLED=false` 运行；outbox 尚未通过真实 Celery worker/beat 和飞书沙箱核查。未触发真实客户退款或外部工单。

## 2026-10-27 执行记录：Loop 06 与耗时基线

- FIX-007：图片生成、财报分析、Excel 生成与财务对账的同步重操作改在 API 线程池执行；`verify_nonblocking_automation.py` 用 180 ms 同步慢任务验证四条 async 路由期间事件循环继续调度。实际 LLM/ERP/图片服务和高并发 P95 尚未压测。
- FIX-008：`/agent/chat` 移除进程内 `InMemorySaver`；每次调用从 PostgreSQL 的消息、摘要、业务状态和用户记忆构造上下文，数据库是唯一跨进程状态源。`verify_agent_durable_context.py` 验证新 Python 进程可读持久消息及用户隔离的 thread ID；仍需多 worker 与重启后的真实 Agent API 验证。
- 新增只读 `scripts/report_automation_latency.py`，按应用、工作流、步骤、后台任务、客服消息和产品反馈分别统计完成状态的 P50/P95，单列零值及缺失样本。近 30 天本地记录：管理员聊天 87 个完成样本 P50 19.25 秒、P95 43.97 秒；财务聊天 57 个完成样本 P50 10.57 秒、P95 31.04 秒；客服消息循环 36 个完成样本 P50 2.36 秒、P95 21.70 秒。样本混有本地测试，不代表生产 SLA。
- 缺口：旧 `agent-chat-plan-execute` 39 条均无有效 `duration_ms`，也无成功完成样本；步骤 `started_at/finished_at` 在历史记录中不能替代 `duration_ms`。客户端发送至实际送达的时间尚无统一关联 ID 与终点事件，因此不能声称客户反馈到任务完成的 P50/P95。下一轮先追踪聊天慢步骤及真实端到端时间戳。

## 2026-10-27 执行记录：Loop 07

- FIX-011：客服物流/发货意图固定优先 `Delivery Note`，订单状态固定优先 `Sales Order`，并仍通过岗位 scope 校验。其他意图遇到多个相近资源匹配时返回置信度和候选资源，低置信度改为需澄清的草稿，避免误查。
- FIX-012：ERP 与 RAG 查询各自捕获异常，记录耗时、状态和错误类型；单源失败生成待人工核对草稿，双源失败转人工，阻断自动写回。缺失数据源在草稿上下文和审计元数据中标识。
- FIX-017：退款资格、退款申请先于普通订单数据查询判断；资格咨询仍查退款事实但不创建审批，实际申请维持高风险审批路径。中英混合意图加入评测集。
- 验证：`verify_customer_routing_degradation.py` 覆盖中英文物流、订单状态、歧义资源、ERP/RAG 单源和双源失败、退款资格与申请；`verify_chat_intent_routing.py` 模型不可用回退集 137/137 通过，`verify_customer_reply_contract.py` 5/5 通过。真实 ERP/RAG/LLM 输出质量及外部客服渠道沙箱仍待验收。

## 2026-10-27 执行记录：Loop 08（进行中）

- `verify_all.py --profile quick` 首次在迁移清单静态检查停止：`docs/DATABASE_MIGRATION_STRATEGY.md` 未登记 026–032。补齐登记后重跑 8/8 通过，耗时 86.0 秒；`verify_sql_migrations.py --mode runtime` 在 PostgreSQL 临时 schema 回放 27 个迁移通过，并自动删除临时 schema。Python 编译、前端构建及 `git diff --check` 通过。
- 尚未执行完整 release profile、真实多 worker/跨容器压测、真实 ERP/LLM 客服结果验证、SMTP/MCP/飞书/平台回调沙箱回执。以上证据齐备前 Loop 08 不标记已验收。
