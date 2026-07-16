# CHANGELOG_AI

这里记录 AI 每次修改项目的内容。

## 记录格式

### 日期：YYYY-MM-DD

#### 本次目标
- 

#### 修改内容
- 

#### 修改文件
- 

#### 验证方式
- 

#### 验证结果
- 

#### 后续待做
- 

### 日期：2026-07-15

#### 本次目标
- 为亚马逊跨境电商企业内部 AI 平台建立岗位与管理员注册基础，先打通运营、客服、财务三类岗位的权限骨架。

#### 修改内容
- 新增 `position` 岗位字段和迁移 SQL。
- 登录接口返回岗位、岗位能力和 ERP scope。
- 新增管理员用户管理 API，可创建带岗位的员工/管理员账号。
- 新增岗位权限模块，支持岗位能力映射、ERP scope、越权关键词拦截和审计。
- 前端新增岗位应用页和用户管理页，登录后可看到岗位能力和用户列表。
- 种子数据和密码脚本补齐运营、客服、财务 demo 账号。
- 更新 AI 文档，固化 Loop Engineering 的后续分阶段计划。

#### 修改文件
- `app/permissions.py`
- `app/api/auth.py`
- `app/api/users.py`
- `app/auth/security.py`
- `app/main.py`
- `app/graph/state.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `scripts/seed_data.py`
- `scripts/set_password.py`
- `sql/schema.sql`
- `sql/005_user_positions.sql`
- `docs/AI_CONTEXT.md`
- `docs/TASKS.md`

#### 验证方式
- `python -m compileall app scripts`
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `.venv/bin/python - <<'PY' ... from app.main import app ... PY`

#### 验证结果
- 后端源码编译通过。
- FastAPI 应用可导入，路由可注册。
- 前端构建通过，仅有 Vite chunk 体积警告。

#### 后续待做
- 做岗位专属自动化页面的真实按钮和表单。
- 接 ERPNext API 客户端和岗位级数据检索。
- 把聊天问答升级成按岗位路由到对应 AI 能力。

### 日期：2026-07-15

#### 本次目标
- 完成 Loop 2：让运营、客服、财务岗位应用从静态展示升级为可实际生成内容的 AI 自动化工作台。

#### 修改内容
- 新增岗位自动化任务模板，覆盖运营 6 个任务、客服 4 个任务、财务 3 个文本生成任务。
- 新增 `/automation/tasks` 接口，按当前用户岗位返回可用任务；管理员可查看全部岗位任务。
- 新增 `/automation/generate` 接口，按岗位和任务生成内容，并写入审计日志。
- 前端岗位应用页改为真实输入表单和生成结果区。
- 管理员和员工登录后均可进入岗位应用；员工只能看到自己岗位任务。
- 重建 Docker API 容器，应用 SQL 迁移，并刷新 demo 账号密码。

#### 修改文件
- `app/api/automation.py`
- `app/services/automation_service.py`
- `app/main.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker exec -i company-rag-postgres psql -U rag_user -d rag_agent < sql/004_document_incremental_update.sql`
- `docker exec -i company-rag-postgres psql -U rag_user -d rag_agent < sql/005_user_positions.sql`
- `docker compose up -d --build api`
- `docker compose exec -T api python -m scripts.seed_data`
- `docker compose exec -T api python -m scripts.set_password`
- 登录 `operations_demo`、`employee_demo`、`finance_demo` 调用 `/automation/tasks`
- 使用 `operations_demo` 调用 `/automation/generate` 的标题生成任务

#### 验证结果
- 后端编译通过。
- 前端构建通过，仅有 Vite chunk 体积警告。
- 当前 8001 服务 OpenAPI 已包含 `/automation/tasks` 和 `/automation/generate`。
- 运营账号返回 6 个任务，客服账号返回 4 个任务，财务账号返回 3 个任务。
- 运营标题生成已真实调用大模型并返回标题内容。

#### 后续待做
- 财务 Excel 文件上传、解析和下载新 Excel 文件。
- Loop 3：接入 ERPNext REST API 客户端。
- 按岗位限制 ERP DocType/API 访问范围。
- 把 AI 对话里的 ERP 类问题路由到岗位权限内的 ERP 检索工具。

### 日期：2026-07-15

#### 本次目标
- 完成 Loop 3 的 ERP 连接层骨架，做成可扩展到 ERPNext、金蝶、用友的统一适配层，并先把岗位权限和审计打通。

#### 修改内容
- 新增通用 ERP provider 接口层和资源目录，统一描述岗位可访问的 ERP 资源。
- 新增 ERPNext / 金蝶 / 用友 provider 骨架，ERPNext 使用 REST API + token 认证，后两者先保留适配位。
- 新增 `/erp/providers`、`/erp/status`、`/erp/scopes`、`/erp/query` 接口。
- 将 ERP 资源访问纳入岗位级权限校验，并写入审计日志。
- 前端新增 ERP 查询页，可查看当前岗位资源、连接状态和查询结果。
- 补充 ERP 相关配置到 `.env.example` 和项目上下文文档。

#### 修改文件
- `app/config.py`
- `app/main.py`
- `app/permissions.py`
- `app/api/erp.py`
- `app/erp/__init__.py`
- `app/erp/base.py`
- `app/erp/providers.py`
- `app/erp/resources.py`
- `app/erp/erpnext.py`
- `app/erp/kingdee.py`
- `app/erp/yonyou.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `.env.example`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `with TestClient(app)` 调用 `/erp/scopes` 和 `/erp/query`

#### 验证结果
- 后端编译通过。
- 前端构建通过，仅有现有的 chunk 体积警告。
- 客服 demo 账号可看到自己的 ERP scopes。
- 客服 demo 账号查询 `GL Entry` 会被 403 拦截。
- 客服 demo 账号查询 `Customer` 会通过权限校验，但因 ERPNext 未配置而返回 `not_configured`。

#### 后续待做
- 把 AI 对话里的 ERP 类问题路由到 `/erp/query`。
- 给 ERPNext 接真实线上/测试环境凭据并补字段映射。
- 补金蝶和用友的真实认证与查询协议适配。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：把 ERP 查询能力接入 AI 对话，让员工直接在客服对话页里按岗位权限查询 ERP 数据。

#### 修改内容
- 意图识别新增 `erp` 类型，用来识别客户、销售订单、物流、商品、工资、发票等 ERP 查询问题。
- LangGraph 新增 `query_erp` 节点，ERP 类问题会按当前账号岗位调用 ERP provider。
- ERP 资源目录增加关键词映射，用自然语言命中 ERP 资源。
- ERP 查询服务增加聊天和 agent 调用审计。
- `/agent/chat` 的低风险 agent 增加 `query_erp_data` 工具。
- 聊天消息 metadata 记录 ERP resource/status，便于后续审计和会话追踪。

#### 修改文件
- `app/graph/intent.py`
- `app/graph/state.py`
- `app/graph/workflow.py`
- `app/services/erp_service.py`
- `app/erp/resources.py`
- `app/agents/low_risk_agent.py`
- `app/main.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `TestClient(app)` 登录 `employee_demo` 后调用 `/chat`

#### 验证结果
- 后端编译通过。
- 前端构建通过，仅有现有的 chunk 体积警告。
- 客服账号询问“客户资料”返回 `intent=erp`。
- 客服账号询问“销售订单”返回 `intent=erp`。
- ERPNext 未配置时，会返回未配置提示，不会伪造数据。
- 客服账号询问“工资单”会被 403 拦截，不能进入模型生成。

#### 后续待做
- 给 ERPNext 配置真实 `ERP_BASE_URL`、`ERP_API_KEY`、`ERP_API_SECRET` 后做端到端联调。
- 增加自动化权限回归测试用例。
- 把 RAG 文档权限进一步按岗位字段细化，而不仅仅依赖 department。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：把 ERPNext 真实接入前的诊断能力做好，确认平台能定位配置、网络和岗位资源映射问题。

#### 修改内容
- 新增管理员专用 `/erp/diagnostics` 接口，返回激活 provider、健康检查、配置项是否存在、岗位资源映射和下一步建议。
- ERP 配置诊断只返回密钥掩码，不返回 `ERP_API_SECRET` 原文。
- 新增 `scripts/erp_diagnostics.py`，可在本地或容器环境输出 ERP 诊断 JSON，并检查 ERPNext 首页和登录用户接口连通性。
- `.env.example` 补充本地 ERPNext Docker 接入 URL：容器内 API 使用 `http://host.docker.internal:8080`，宿主机后端使用 `http://127.0.0.1:8080`。
- 已确认当前 ERPNext 容器可访问，版本为 Frappe 16.26.3 / ERPNext 16.27.0；未带 token 调用登录用户接口返回 403，符合未授权状态。

#### 修改文件
- `app/api/erp.py`
- `app/erp/diagnostics.py`
- `scripts/erp_diagnostics.py`
- `.env.example`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `docker ps`
- `docker exec frappe_docker-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend list-apps'`
- `docker exec -i company-rag-api python - <<'PY' ... PY`
- `.venv/bin/python -m compileall app scripts`
- `.venv/bin/python -m scripts.erp_diagnostics`
- `TestClient(app)` 登录管理员和客服账号后调用 `/erp/diagnostics`

#### 验证结果
- ERPNext/Frappe 容器正在运行，宿主机 `http://127.0.0.1:8080` 和 API 容器内 `http://host.docker.internal:8080` 可访问 ERPNext 首页。
- 未配置 token 时诊断脚本返回 `not_configured`，不会伪造连接成功。
- 管理员可访问 `/erp/diagnostics`，普通客服账号访问该接口返回 403。

#### 后续待做
- 在 ERPNext 管理员或专用 API 用户上生成 `api_key` / `api_secret`。
- 把 `.env` 中 `ERP_BASE_URL`、`ERP_API_KEY`、`ERP_API_SECRET` 填好并重启 API 容器。
- 使用运营、客服、财务三个账号分别做真实 ERP DocType 查询，补充 Amazon 订单号、SKU、物流单号等字段映射。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：把平台真正连上本地 ERPNext，并验证三个岗位能查到自己权限内的 ERPNext DocType。

#### 修改内容
- 新增 `scripts/erpnext_api_user.py`，用于在 ERPNext 里创建/维护专用 API 用户 `company_rag_api@example.com`。
- 为 API 用户补充销售、库存、客服、财务、人事等业务读取角色；平台内部仍通过岗位 ERP scope 做二次权限隔离。
- 将本项目 `.env` 配置为 Docker API 容器访问本地 ERPNext：`ERP_BASE_URL=http://host.docker.internal:8080`。
- 生成并配置 ERPNext token，诊断接口和脚本均显示连接正常。
- 重新构建并启动 `company-rag-api` 容器，让 ERP 配置生效。

#### 修改文件
- `.env`
- `scripts/erpnext_api_user.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `docker cp scripts/erpnext_api_user.py frappe_docker-backend-1:/home/frappe/frappe-bench/apps/frappe/frappe/company_rag_api_user.py`
- `docker exec frappe_docker-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend execute frappe.company_rag_api_user.ensure_company_rag_api_user'`
- `docker compose up -d --build api`
- `docker compose exec -T api python -m scripts.erp_diagnostics`
- 使用运营、客服、财务 demo 账号调用 `/erp/query`

#### 验证结果
- `/erp/status` 返回 `ok`，ERPNext 当前登录用户为 `company_rag_api@example.com`。
- 运营账号查询 `Item` 成功，返回 3 条记录。
- 客服账号查询 `Customer` 成功，返回 3 条记录；查询 `Delivery Note` 成功但当前测试库为 0 条。
- 财务账号查询 `GL Entry` 成功，返回 3 条记录；查询 `Sales Invoice` 成功，返回 3 条记录。
- 客服账号查询 `Salary Slip` 返回 403，平台岗位权限拦截仍然有效。

#### 后续待做
- 给 ERPNext 写入更贴近 Amazon 跨境电商的业务测试数据。
- 补前端管理员 ERP 诊断面板。
- 增加岗位权限和 ERP 查询的自动化回归测试。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：给 ERPNext 写入亚马逊跨境电商测试数据，并让平台能按业务字段查询。

#### 修改内容
- 新增 `scripts/erpnext_amazon_seed.py`，用于向 ERPNext 写入可重复执行的 Amazon 测试数据。
- 写入 3 个 SKU、3 个 Amazon 买家客户、3 条销售订单、3 条物流/出库单、3 条销售发票、3 条售后工单。
- Amazon 订单号写入 `Sales Order.po_no` / `Sales Invoice.po_no`，物流单号写入 `Delivery Note.lr_no`，售后内容写入 `Issue.subject` / `Issue.description`。
- ERPNext provider 的自然语言查询从单字段 `name` 扩展为业务字段 `or_filters`。
- ERP 资源返回字段补充 `po_no`、`lr_no`、`description`，便于前端和 AI 对话展示真实业务信息。

#### 修改文件
- `app/erp/erpnext.py`
- `app/erp/resources.py`
- `scripts/erpnext_amazon_seed.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `docker cp scripts/erpnext_amazon_seed.py frappe_docker-backend-1:/home/frappe/frappe-bench/apps/frappe/frappe/company_rag_amazon_seed.py`
- `docker exec frappe_docker-backend-1 bash -lc 'cd /home/frappe/frappe-bench && bench --site frontend execute frappe.company_rag_amazon_seed.seed_amazon_demo_data'`
- `docker compose up -d --build api`
- 使用运营、客服、财务 demo 账号调用 `/erp/query`

#### 验证结果
- 运营按 SKU `AMZ-AIR-PUMP-001` 查询 `Item` 成功。
- 运营按 Amazon 订单号 `AMZ-DE-305-7712468-1290045` 查询 `Sales Order` 成功。
- 客服按客户名 `Olivia` 查询 `Customer` 成功。
- 客服按物流单号 `DHL-DE-AMZ-2026071502` 查询 `Delivery Note` 成功。
- 客服按订单号查询售后 `Issue` 成功。
- 财务按订单号 `AMZ-JP-250-6630188-4402197` 查询 `Sales Invoice` 成功。
- 客服查询 `Salary Slip` 继续返回 403，岗位权限仍然有效。

#### 后续待做
- 在 AI 对话里验证“帮我查 AMZ-DE... 的物流/发票/售后”能自然命中这些数据。
- 补前端管理员 ERP 诊断面板。
- 给 ERP 查询加自动化回归测试。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：让 AI 对话直接查询 Amazon ERP 测试数据，并验证岗位权限闭环。

#### 修改内容
- 意图识别增加确定性规则兜底，带 Amazon 订单号且包含物流、销售订单、售后、发票、工资等业务关键词时优先走 ERP。
- ERP 服务层新增检索词抽取，自动从自然语言中提取 Amazon 订单号、SKU、物流单号。
- ERP 对话摘要补充展示 `po_no`、`lr_no`、`subject`、`description`、应收金额、到期日等字段。
- ERPNext Delivery Note 查询补充 `title` 字段，Issue 查询补充 `description` 搜索。
- 新增 `scripts/verify_erp_chat.py`，用于回归验证岗位对话 ERP 查询。

#### 修改文件
- `app/graph/intent.py`
- `app/services/erp_service.py`
- `app/erp/erpnext.py`
- `app/erp/resources.py`
- `scripts/verify_erp_chat.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `docker compose up -d --build api`
- 手工调用 `/chat` 验证运营、客服、财务三个岗位
- `python3 scripts/verify_erp_chat.py`

#### 验证结果
- 运营问“帮我查一下 Amazon 订单 AMZ-DE-305-7712468-1290045 的销售订单”返回销售订单和 `po_no`。
- 客服问“帮我查一下 AMZ-DE-305-7712468-1290045 的物流”返回 Delivery Note 和物流单号。
- 客服问“帮我查一下 AMZ-US-112-4589012-7783401 的售后工单”返回 Issue 和退款咨询内容。
- 财务问“帮我查一下 AMZ-JP-250-6630188-4402197 的销售发票”返回 Sales Invoice 和应收金额。
- 客服问工资单仍返回 403。

#### 后续待做
- 增加前端管理员 ERP 诊断面板。
- 把 `scripts/verify_erp_chat.py` 纳入统一测试命令。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：把 ERP 诊断能力做进前端管理员页面，减少只靠脚本和接口排查的问题。

#### 修改内容
- 前端 `api.ts` 增加 `/erp/diagnostics` 类型定义和请求方法。
- ERP 页面新增管理员诊断面板，展示连接状态、当前 provider、provider 配置项、岗位资源映射和 next steps。
- 诊断面板只在管理员角色显示；员工不请求诊断接口，也不显示诊断卡片。
- 登录管理员时会加载诊断数据，退出登录会清空诊断状态。

#### 修改文件
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `npm run build`
- `GET /erp/diagnostics` 接口冒烟验证
- 浏览器登录 `admin_demo` 打开 ERP 查询页
- 浏览器登录 `employee_demo` 打开 ERP 查询页

#### 验证结果
- 前端构建通过，仅保留现有 chunk 体积警告。
- 管理员 ERP 页面显示“管理员 ERP 诊断”，连接状态为 `ok`，当前用户为 `company_rag_api@example.com`。
- 管理员页面显示 `ERP_BASE_URL=http://host.docker.internal:8080`，`ERP_API_KEY` / `ERP_API_SECRET` 只显示掩码。
- 管理员页面显示 ERPNext、金蝶、用友 provider 配置状态，以及运营/客服/财务岗位资源映射。
- 客服账号 ERP 页面不显示“管理员 ERP 诊断”，只显示客服岗位允许的 ERP 资源。

#### 后续待做
- 增加前端自动化测试覆盖管理员/员工 ERP 页面差异。
- 把 ERP 对话验证脚本纳入统一测试命令。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：新增统一验证命令，把后端、ERP 真实连接、岗位对话权限和前端构建放到一个回归入口。

#### 修改内容
- 新增 `scripts/verify_all.py`，依次执行后端 Python 编译、API 健康检查、管理员 ERP 诊断、ERP 对话权限回归和前端构建。
- ERP 诊断验证会登录 `admin_demo`，调用 `/erp/diagnostics`，并断言 `active_health.status == ok`。
- `scripts/verify_erp_chat.py` 支持通过 `VERIFY_API_BASE_URL` 指定 API 地址，便于统一脚本和后续 CI 复用。
- 更新任务清单和上下文文档，把统一验证命令固化为后续每轮修改后的检查方式。

#### 修改文件
- `scripts/verify_all.py`
- `scripts/verify_erp_chat.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `python3 scripts/verify_all.py`

#### 验证结果
- 统一验证通过，总耗时约 25 秒。
- 后端 Python 编译通过。
- API `/health` 返回 `ok`。
- ERP 管理员诊断通过，当前 provider 为 `erpnext`，登录用户为 `company_rag_api@example.com`。
- ERP 对话权限回归通过：运营销售订单、客服物流、客服售后、财务发票均可查，客服查询工资单返回 403。
- 前端 `npm run build` 通过，仅保留 Vite chunk 体积警告。

#### 后续待做
- 将 `scripts/verify_all.py` 接入 CI 或发布前固定检查流程。
- 增加前端自动化测试覆盖管理员/员工 ERP 页面差异。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：让财务岗位可以上传 Excel，并按财务要求生成新的 Excel 工作簿用于下载。

#### 修改内容
- 新增财务 Excel 处理服务，读取 `.xlsx` / `.xls`，生成处理摘要、数值汇总、AI 建议和整理后的源数据 sheet。
- 新增 `POST /automation/finance/excel-transform`，只允许财务岗位或管理员使用。
- 前端岗位应用页的财务区域新增 Excel 上传、处理要求输入、生成并下载按钮。
- 统一验证脚本新增财务 Excel 生成回归，自动上传样例工作簿并验证返回文件可被打开。
- API 健康检查增加短重试，避免容器刚重启时端口尚未 ready 导致误失败。

#### 修改文件
- `app/api/automation.py`
- `app/services/finance_excel_service.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `scripts/verify_all.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker compose up -d --build api`
- `python3 scripts/verify_all.py`
- 使用本机 Chrome + Playwright 登录财务账号检查岗位应用页

#### 验证结果
- 后端 Python 编译通过。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- Docker API 容器已重建并启动。
- 统一验证 6/6 通过，总耗时约 43 秒。
- 财务 Excel 生成回归通过，生成文件包含 `处理摘要`、`数值汇总`、`AI建议`、`整理_Amazon销售明细`。
- ERP 管理员诊断和 ERP 对话权限回归仍然通过。
- 财务账号打开岗位应用页后，可见“上传 Excel 生成新表”和“生成并下载 Excel”按钮。

#### 后续待做
- 增强财务 Excel 生成规则：支持按用户要求输出工资表、利润表、费用分类表等更具体模板。
- 增加前端自动化测试覆盖管理员/员工 ERP 页面差异。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：新增岗位越权权限回归脚本，防止运营、客服、财务互相越权访问功能和数据。

#### 修改内容
- 新增 `scripts/verify_position_permissions.py`，用 demo 账号验证跨岗位权限边界。
- 覆盖自动化任务越权：运营不能用客服任务，客服不能用财务任务，财务不能用运营任务。
- 覆盖 ERP 越权：客服不能查 `GL Entry`，运营不能查 `Salary Slip`，财务不能查客服售后 `Issue`。
- 覆盖聊天越权：客服不能问财务报表/利润，运营不能问工资/薪资，财务不能问客服私有会话。
- 覆盖接口越权：客服不能使用财务 Excel 生成接口，员工不能访问管理员用户接口和 ERP 诊断接口。
- 保留正向校验：管理员仍可查看全部岗位自动化任务。
- 将岗位越权回归接入 `scripts/verify_all.py`，全量验证从 6 步扩展为 7 步。

#### 修改文件
- `scripts/verify_position_permissions.py`
- `scripts/verify_all.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `python3 scripts/verify_position_permissions.py`
- `.venv/bin/python -m compileall app scripts`
- `python3 scripts/verify_all.py`

#### 验证结果
- 岗位越权脚本单独通过，13 个权限用例均符合预期。
- 后端 Python 编译通过。
- 统一验证 7/7 通过，总耗时约 42 秒。
- ERP 管理员诊断、ERP 对话回归、岗位越权回归、财务 Excel 回归和前端构建均通过。

#### 后续待做
- 增加前端自动化测试覆盖管理员/员工 ERP 页面差异。
- 后续新增岗位或新功能时，把对应越权用例补进 `scripts/verify_position_permissions.py`。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：新增前端权限可见性回归，自动验证管理员和不同岗位员工看到的页面入口不同。

#### 修改内容
- 新增 `scripts/verify_frontend_permissions.mjs`，使用本机 Chrome + Playwright 做浏览器级验证。
- 脚本走真实登录流程，确保前端会触发任务、ERP scope 和诊断数据加载。
- 验证管理员 ERP 页面可见“管理员 ERP 诊断”、`ERPNext` 和岗位资源映射。
- 验证客服 ERP 页面不显示“管理员 ERP 诊断”，员工菜单不显示“用户管理”“知识库”。
- 验证财务岗位应用页显示“上传 Excel 生成新表”和“生成并下载 Excel”。
- 验证客服/运营岗位应用页不显示财务 Excel 上传入口，也不显示其他岗位自动化区域。
- 将前端权限可见性回归接入 `scripts/verify_all.py`，全量验证从 7 步扩展为 8 步。

#### 修改文件
- `scripts/verify_frontend_permissions.mjs`
- `scripts/verify_all.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `.venv/bin/python -m compileall app scripts`
- `python3 scripts/verify_all.py`

#### 验证结果
- 前端权限可见性脚本单独通过，5 个浏览器用例均符合预期。
- 后端 Python 编译通过。
- 统一验证 8/8 通过，总耗时约 89 秒。
- ERP 管理员诊断、ERP 对话回归、岗位越权回归、财务 Excel 回归、前端构建和前端权限可见性回归均通过。

#### 后续待做
- 后续新增页面或岗位时，把前端可见性断言补进 `scripts/verify_frontend_permissions.mjs`。
- 考虑给前端路由增加根据 URL 初始化 `activeView` 的能力，减少浏览器验证里必须点击菜单的步骤。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：让前端 URL 和当前页面状态同步，支持直接打开后台页面链接、刷新和浏览器后退。

#### 修改内容
- 前端初始化时根据 `window.location.pathname` 设置 `activeView`，例如直接打开 `/automation` 会进入岗位应用。
- 菜单点击时通过 History API 同步 URL。
- 监听 `popstate`，支持浏览器前进/后退切换后台页面。
- 如果员工访问管理员专属 URL，会自动回到 `/dashboard`。
- 已登录状态刷新页面后自动加载岗位任务、ERP scope、管理员数据，避免直接访问 `/automation` 或 `/erp` 时页面数据为空。
- 前端权限可见性回归脚本改为直接访问 `/automation`、`/erp`，并新增浏览器后退验证。

#### 修改文件
- `frontend/src/main.tsx`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `npm run build`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `.venv/bin/python -m compileall app scripts`
- `python3 scripts/verify_all.py`

#### 验证结果
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 前端权限可见性脚本通过，覆盖直接访问 `/automation`、`/erp` 和浏览器后退。
- 后端 Python 编译通过。
- 统一验证 8/8 通过，总耗时约 72 秒。

#### 后续待做
- 可继续增强前端体验：登录后若当前 URL 是员工无权访问的管理员页，显示一次提示再跳转。
- 后续新增页面时，需要把 URL 映射补进 `navItems` 并扩展前端可见性回归。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：员工访问管理员页面时给出明确权限提示，而不是静默跳回概览。

#### 修改内容
- 前端在检测到当前账号无权访问 `activeView` 时，显示“当前账号没有权限访问该页面，已返回概览。”。
- 同步更新页面状态栏提示，并跳转回 `/dashboard`。
- 增加 `lastForbiddenPath` 状态，避免同一个无权路径重复弹出提示。
- 前端权限可见性回归增加客服账号直接访问 `/users` 的验证，确认页面跳回 `/dashboard` 且提示可见。

#### 修改文件
- `frontend/src/main.tsx`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `npm run build`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `.venv/bin/python -m compileall app scripts`
- `python3 scripts/verify_all.py`

#### 验证结果
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 前端权限可见性脚本通过，新增 `/users` 无权访问提示用例通过。
- 后端 Python 编译通过。
- 统一验证 8/8 通过，总耗时约 89 秒。

#### 后续待做
- 可继续做前端体验：给管理员/员工不同首页增加更明确的岗位工作台快捷入口。
- 后续新增管理员专属页面时，继续复用这套无权访问提示和前端回归。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：给管理员和运营、客服、财务岗位首页增加常用功能快捷入口，让登录后第一屏更像岗位工作台。

#### 修改内容
- 首页 `/dashboard` 新增按身份显示的快捷入口区。
- 管理员快捷入口包含用户管理、ERP 诊断、知识库上传、审计日志。
- 运营快捷入口包含运营 AI 自动化、运营 ERP 查询、AI 对话。
- 客服快捷入口包含客服 AI 对话、客服 ERP 查询、客服自动化。
- 财务快捷入口包含财务 Excel 生成、财务 ERP 查询、财务 AI 对话。
- 快捷入口按钮复用现有 URL 路由跳转，并增加稳定 `aria-label`。
- 前端权限可见性回归扩展到四类账号首页快捷入口，并验证管理员和财务入口可跳到目标页面。

#### 修改文件
- `frontend/src/main.tsx`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `npm run build`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `.venv/bin/python -m compileall app scripts`
- `python3 scripts/verify_all.py`

#### 验证结果
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 前端权限可见性脚本通过，覆盖管理员、运营、客服、财务首页快捷入口。
- 后端 Python 编译通过。
- 统一验证 8/8 通过，总耗时约 103 秒。

#### 后续待做
- 可继续优化首页：把不同岗位的关键数据概览接入真实 ERP 指标，例如运营订单/商品、客服售后/物流、财务发票/收付款。
- 后续新增岗位或快捷入口时，同步补充 `dashboardShortcuts` 和前端权限可见性回归。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：把首页从“快捷入口”升级为“岗位工作台”，接入 ERP 数据概览，并继续保持岗位权限隔离。

#### 修改内容
- 新增 `GET /erp/dashboard-overview`，按当前账号身份返回首页概览。
- 管理员概览展示 ERP 连接、可用 Provider、岗位 ERP 资源，不直接展开岗位业务数据。
- 运营概览展示销售订单、商品资料、商品价格。
- 客服概览展示物流/出库单、售后工单、客户资料。
- 财务概览展示销售发票、收付款单、总账分录。
- 前端首页新增“平台数据概览/岗位数据概览”，展示指标和最近 3 条 ERP 记录。
- 概览接口复用 ERP provider、资源映射和岗位权限校验，并写入审计日志。
- 岗位越权回归和前端权限可见性回归都增加首页概览断言。

#### 修改文件
- `app/api/erp.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `scripts/verify_position_permissions.py`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker compose up -d --build api`
- 直测 `GET /erp/dashboard-overview` 的管理员、运营、客服、财务账号返回资源
- `python3 scripts/verify_position_permissions.py`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `python3 scripts/verify_all.py`

#### 验证结果
- 后端 Python 编译通过。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 新概览接口直测通过：运营只返回 `Sales Order`、`Item`、`Item Price`；客服只返回 `Delivery Note`、`Issue`、`Customer`；财务只返回 `Sales Invoice`、`Payment Entry`、`GL Entry`。
- 岗位越权回归通过，新增概览资源隔离用例通过。
- 前端权限可见性脚本通过，四类账号首页概览可见性通过。
- 统一验证 8/8 通过，总耗时约 113 秒。

#### 后续待做
- 可继续增强首页指标：按店铺/站点统计 Amazon 订单、售后、发票金额，而不仅是最近记录数量。
- 后续可以给首页概览增加筛选器，例如站点、店铺、时间范围。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：给岗位首页 ERP 概览增加站点筛选，让运营、客服、财务可以按 Amazon 美国站、德国站、日本站查看概览。

#### 修改内容
- `GET /erp/dashboard-overview` 新增 `market=all|us|de|jp` 参数。
- 后端增加站点标签：全部站点、美国站、德国站、日本站。
- 订单、物流、售后、销售发票按 Amazon 订单号、物流单号、主题等站点标记过滤。
- 商品、价格、总账、收付款等全局资源保持全站展示。
- 每个概览分组返回 `total_count`，前端展示“匹配 N 条”。
- 首页概览增加“全部、美国、德国、日本”分段筛选。
- 岗位越权回归增加站点筛选后的资源隔离断言。
- 前端权限可见性回归增加站点筛选控件和运营切换德国站验证。

#### 修改文件
- `app/api/erp.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `scripts/verify_position_permissions.py`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker compose up -d --build api`
- 直测 `GET /erp/dashboard-overview?market=de|us|jp`
- `python3 scripts/verify_position_permissions.py`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `python3 scripts/verify_all.py`

#### 验证结果
- 后端 Python 编译通过。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 直测通过：运营德国站命中 DE 销售订单；客服美国站命中 US 物流/售后；财务日本站命中 JP 销售发票。
- 岗位越权回归通过，站点筛选后仍只返回岗位内资源。
- 前端权限可见性脚本通过，分段筛选控件和运营切换德国站通过。
- 统一验证 8/8 通过，总耗时约 135 秒。

#### 后续待做
- 可继续增加时间范围筛选，例如今天、近 7 天、近 30 天。
- 后续可把全局资源也按店铺或站点维度增强，例如商品归属站点、价格表站点。

### 日期：2026-07-15

#### 本次目标
- 完成下一个 loop：给岗位首页 ERP 概览增加时间范围筛选，让站点筛选可以继续叠加“今天、近 7 天、近 30 天”。

#### 修改内容
- `GET /erp/dashboard-overview` 新增 `date_range=all|today|7d|30d` 参数。
- 后端增加时间范围标签：全部时间、今天、近 7 天、近 30 天。
- 后端按 `posting_date`、`transaction_date`、`modified`、`creation`、`due_date`、`start_date`、`end_date` 等字段做轻量日期过滤。
- 首页概览增加“全部时间、今天、近7天、近30天”分段筛选。
- 概览标题区域显示站点和时间范围标签，例如“德国站 / 近 30 天”。
- 前端权限回归的异步等待更稳，等待 ERP 数据或自动化任务加载完成后再断言。
- 前端权限回归使用 Ant Design `.ant-segmented-item` 点击分段项，避免点到重复文本。

#### 修改文件
- `app/api/erp.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `scripts/verify_position_permissions.py`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker compose up -d --build api`
- 直测 `GET /erp/dashboard-overview?market=de&date_range=30d`、`market=us&date_range=7d`、`market=jp&date_range=today`
- `python3 scripts/verify_position_permissions.py`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- `python3 scripts/verify_all.py`

#### 验证结果
- 后端 Python 编译通过。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 直测通过：运营德国站近 30 天、客服美国站近 7 天、财务日本站今天均返回对应标签和计数。
- 岗位越权回归通过，时间范围筛选后仍只返回岗位内资源。
- 前端权限可见性脚本通过，时间范围控件和运营切换德国站 + 近30天通过。
- 统一验证 8/8 通过，总耗时约 165 秒。

#### 后续待做
- 可继续做店铺维度筛选，例如 US Store、DE Store、JP Store。
- 后续可把日期范围筛选下沉到 ERP provider 查询条件，减少前端概览接口拉取后再过滤的数据量。

### 日期：2026-07-15

#### 本次目标
- 连续完成六个 loop：店铺筛选、首页关键金额指标、ERP 概览记录详情、AI 对话引用 ERP 结果、管理员权限与审计增强、发布前稳定化。

#### 修改内容
- `GET /erp/dashboard-overview` 新增 `store=all|us_store|de_store|jp_store`，首页概览新增“全部店铺、US Store、DE Store、JP Store”筛选。
- 概览 section 新增 `amount_total` 和 `amount_label`，首页指标卡展示订单金额、发票金额、收付款金额等关键金额。
- 新增 `GET /erp/records/{resource}/{record_id}`，记录详情接口复用岗位 ERP 权限校验。
- 首页 ERP 记录增加“详情”按钮和“ERP 记录详情”弹窗。
- ERP 对话回答增加 `[ERP-1]` 引用编号和“引用 ERP 记录”列表。
- `/chat` 和 `/chat/stream` 增加 `erp_references`，聊天消息 metadata 保存 ERP 引用，前端消息气泡展示引用标签。
- `GET /admin/audit-logs` 支持 `action`、`resource_type`、`position`、`limit` 筛选。
- 管理员创建用户时新增 `admin.user.permission_assignment` 审计。
- 前端审计页增加动作、资源类型、岗位筛选和查询按钮。
- 新增 `scripts/verify_release_ready.py`，并接入 `scripts/verify_all.py`。
- 修复前端回归中“详情”按钮选择器容易点到左侧菜单“会话详情”的问题：概览详情按钮新增稳定 `aria-label`。

#### 修改文件
- `app/api/erp.py`
- `app/api/audit_logs.py`
- `app/api/users.py`
- `app/main.py`
- `app/services/erp_service.py`
- `app/services/logging_service.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `scripts/verify_all.py`
- `scripts/verify_erp_chat.py`
- `scripts/verify_frontend_permissions.mjs`
- `scripts/verify_position_permissions.py`
- `scripts/verify_release_ready.py`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker compose up -d --build api`
- `python3 scripts/verify_position_permissions.py`
- `python3 scripts/verify_erp_chat.py`
- `python3 scripts/verify_release_ready.py`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`

#### 验证结果
- 后端 Python 编译通过。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- API 容器已重新 build 并启动。
- 岗位越权回归通过，新增店铺筛选、金额字段、记录详情权限用例通过。
- ERP 聊天回归通过，运营、客服、财务回答均包含 ERP 引用。
- 发布前稳定化脚本通过，覆盖店铺筛选 + 金额指标、记录详情权限、AI 对话 ERP 引用和审计筛选。
- 前端权限可见性脚本通过，覆盖店铺筛选控件、金额指标、ERP 记录详情弹窗和审计筛选控件。

#### 后续待做
- 可把首页概览筛选条件进一步下沉到 ERPNext provider 的 filters/or_filters，减少后端拉取后再过滤的数据量。
- 可给 ERP 记录详情增加“复制记录 ID”和“从详情发起 AI 追问”。
- 可把审计日志导出为 Excel，方便管理员做周期审计。

### 日期：2026-07-17

#### 本次目标
- 启动企业级 AI 自动化平台升级，先完成 Platform Loop 0：制定 Loop Engineering 多 Agent 工作规则、企业平台需求、真实测试政策、安全验收和 UI 质量清单。

#### 修改内容
- 新增 Loop Engineering 总计划，明确项目经理、架构、开发、Code Review、测试、安全、DevOps、文档、监控、页面格式 Agent 的职责。
- 新增企业 AI 平台需求文档，定义 AI 应用中心、自动化流程、运行记录、连接器中心、权限治理、效果分析和评测中心。
- 新增 UI 质量清单，要求后续前端 loop 用真实浏览器截图检查桌面、平板和移动端，重点检查卡片、表格、输入框、弹窗和内容溢出。
- 新增安全清单，覆盖岗位越权、字段越权、ERP 凭据、AI 上下文泄露、审计日志、token 失效和管理员操作。
- 新增真实测试政策，明确不得把 mock、stub、fake provider、monkeypatch 或模拟响应测试写进项目代码；验收必须使用真实后端、真实数据库、真实登录账号、真实 ERPNext、真实浏览器和真实文件上传下载。
- 更新长期上下文和任务清单，把后续企业级平台升级拆为 Platform Loop 1 到 Platform Loop 6。

#### 修改文件
- `docs/LOOP_ENGINEERING_PLAN.md`
- `docs/AI_PLATFORM_REQUIREMENTS.md`
- `docs/UI_QUALITY_CHECKLIST.md`
- `docs/SECURITY_CHECKLIST.md`
- `docs/REAL_TESTING_POLICY.md`
- `docs/AI_CONTEXT.md`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`

#### 验证方式
- `git diff --check`
- `ls docs`
- 人工检查新增文档覆盖真实测试、安全、UI 和 loop 规划要求

#### 验证结果
- 文档检查通过。
- `git diff --check` 无输出，未发现 whitespace 错误。
- 已确认新增文档包含真实测试红线、安全验收、UI 质量清单和后续 loop 规划。

#### 后续待做
- Platform Loop 1：企业级导航与只读 AI 应用中心。

### 日期：2026-07-17

#### 本次目标
- 完成 Platform Loop 1：新增企业级 AI 应用中心，把现有岗位自动化、ERP 查询、AI 对话、财务 Excel、知识库和审计能力统一展示为只读应用目录。

#### 修改内容
- 左侧导航新增“AI 应用中心”页面 `/ai-apps`。
- 新增 `AiAppsPanel`，按真实登录账号权限展示应用目录。
- 管理员可见运营、客服、财务和平台治理应用；财务等员工只可见本岗位应用。
- 应用卡片展示应用名称、岗位、类别、负责人、数据源和入口按钮。
- 页面明确标注运行数据将在统一运行记录中心接入后展示，不伪造运行次数或成功率。
- 首页快捷入口中的岗位自动化入口改为进入 AI 应用中心，原岗位自动化执行页仍保留并可从应用卡进入。
- 修复移动端 ProLayout 顶部用户区、ProCard 标题副标题导致的横向溢出问题。
- 前端权限回归脚本增加 AI 应用中心用例，并将 ERP 诊断验证改为直达 `/erp/diagnostics`。

#### 修改文件
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`

#### 验证方式
- `npm run build`
- 真实登录 API + 真实前端页面截图检查：
  - `admin_demo / Admin123456` 打开 `/ai-apps`
  - `finance_demo / Finance123456` 打开 `/ai-apps`
  - 390px 移动端打开 `/ai-apps`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`

#### 验证结果
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 管理员桌面 AI 应用中心截图通过，22 个应用卡，无横向溢出。
- 财务桌面 AI 应用中心截图通过，6 个应用卡，无横向溢出。
- 财务 390px 移动端 AI 应用中心截图通过，无横向溢出。
- 前端权限可见性真实回归全部通过，覆盖管理员、运营、客服、财务、ERP 诊断、AI 应用中心、首页快捷入口、路由后退和无权访问提示。

#### 后续待做
- Platform Loop 2：新增统一运行记录中心，用真实数据库记录 AI 应用和流程执行。

### 日期：2026-07-17

#### 本次目标
- 完成 Platform Loop 2：新增统一运行记录中心，用真实数据库记录 AI 应用、ERP 查询、财务 Excel 和 AI 对话的执行情况。

#### 修改内容
- 新增 `automation_runs`、`automation_run_steps`、`automation_run_artifacts` 三张真实运行记录表和迁移 SQL。
- 新增运行记录服务，统一写入 run、step、artifact，并对输入、输出、错误和 metadata 做脱敏、截断和敏感 key 过滤。
- 新增只读 API：`GET /run-records`、`GET /run-records/{run_id}`。
- 管理员可查看全平台脱敏运行记录；员工只能查看自己的同岗位运行记录。
- 接入真实业务路径：`/automation/generate`、`/automation/finance/excel-transform`、`/erp/query`、`/chat`、`/chat/stream`。
- ERP 越权查询会生成 `blocked` 运行记录，但不泄露被查资源内容。
- 前端新增 `/run-records` 页面，支持状态、类型、应用、岗位、资源筛选，展示运行列表、步骤、产物和详情弹窗。
- 新增真实后端验收脚本 `scripts/verify_run_records.py` 和真实浏览器验收脚本 `scripts/verify_run_records_frontend.mjs`。
- 前端权限回归脚本更新员工访问管理员 URL 的断言，按真实结果检查跳回 `/dashboard` 且隐藏管理员菜单。

#### 修改文件
- `app/api/automation.py`
- `app/api/erp.py`
- `app/api/run_records.py`
- `app/main.py`
- `app/services/run_record_service.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `scripts/verify_frontend_permissions.mjs`
- `scripts/verify_run_records.py`
- `scripts/verify_run_records_frontend.mjs`
- `sql/006_automation_runs.sql`
- `sql/schema.sql`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`

#### 验证方式
- `docker exec -i company-rag-postgres psql -U rag_user -d rag_agent < sql/006_automation_runs.sql`
- `docker compose up -d --build api`
- `curl -sS http://127.0.0.1:8001/health`
- `.venv/bin/python -m compileall app scripts`
- `.venv/bin/python scripts/verify_run_records.py`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_run_records_frontend.mjs`
- `npm run build`
- `NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`

#### 验证结果
- 真实数据库迁移成功，三张运行记录表存在。
- API 容器重建并启动，`/health` 返回 `ok`。
- 后端编译通过。
- 真实后端验收通过：生成 4 条 run、4 条 step、2 条 artifact；覆盖运营 ERP 成功、客服 ERP 越权拦截、财务 Excel 成功、财务聊天成功。
- 真实后端验收确认客服访问财务运行详情返回 403。
- 真实前端浏览器验收通过，截图：
  - `/tmp/company-rag-run-records-admin-desktop.png`
  - `/tmp/company-rag-run-records-finance-desktop.png`
  - `/tmp/company-rag-run-records-finance-mobile.png`
- 三个前端截图均无横向溢出。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- 前端权限可见性真实回归全部通过。
- 本轮验收未使用 mock、stub、fake provider、monkeypatch 或模拟响应。

#### 后续待做
- Platform Loop 3：自动化流程配置一期，先做只读配置、版本、输入 schema、Prompt、允许资源和审批规则展示。

### 日期：2026-07-17

#### 本次目标
- 完成 Platform Loop 3：新增只读自动化流程配置中心，让管理员和岗位员工能查看真实流程定义、权限规则、ERP 资源、Prompt 摘要、Schema 和执行步骤。

#### 修改内容
- 新增流程配置投影服务，从真实现有代码源生成只读配置，不新增模拟配置表，也不改变执行逻辑。
- 新增只读 API：`GET /automation-flows`、`GET /automation-flows/{flow_id}`。
- 流程配置覆盖运营/客服/财务岗位自动化任务、各岗位 ERP 查询、各岗位 AI 对话、财务 Excel 生成和管理员知识库维护。
- 后端响应包含流程版本、入口、触发方式、输入 schema、输出 schema、Prompt 摘要、模板预览、模型配置、允许工具、允许 ERP 资源、权限规则、审批策略、失败策略和执行步骤。
- 管理员可查看全部岗位和平台流程；员工只能查看自己岗位流程，跨岗位详情返回 404。
- 前端新增 `/automation-flows` 页面，展示流程指标、筛选、流程表格和只读详情弹窗。
- 详情弹窗展示输入/输出 Schema、Prompt 与模型、权限/工具/ERP 资源、审批策略、失败策略和执行步骤。
- 首页岗位快捷入口中的自动化入口改为进入流程配置中心，便于先查看能力和权限边界。
- 新增真实后端验收脚本 `scripts/verify_automation_flows.py`。
- 新增真实浏览器验收脚本 `scripts/verify_automation_flows_frontend.mjs`，并支持从本机真实 Playwright 安装或 npx 缓存解析。
- 更新前端权限回归脚本，使财务首页快捷入口断言匹配新的 `/automation-flows` 入口。

#### 修改文件
- `app/api/automation_flows.py`
- `app/main.py`
- `app/services/automation_flow_service.py`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `frontend/src/styles.css`
- `scripts/verify_automation_flows.py`
- `scripts/verify_automation_flows_frontend.mjs`
- `scripts/verify_frontend_permissions.mjs`
- `docs/TASKS.md`
- `docs/CHANGELOG_AI.md`
- `docs/AI_CONTEXT.md`

#### 验证方式
- `.venv/bin/python -m compileall app scripts`
- `npm run build`
- `docker compose up -d --build api`
- `curl -sS -i http://127.0.0.1:8001/health`
- `.venv/bin/python scripts/verify_automation_flows.py`
- `node scripts/verify_automation_flows_frontend.mjs`
- `NODE_PATH=/Users/xiaoxiang/.npm/_npx/e41f203b7505f1fb/node_modules node scripts/verify_run_records_frontend.mjs`
- `NODE_PATH=/Users/xiaoxiang/.npm/_npx/e41f203b7505f1fb/node_modules node scripts/verify_frontend_permissions.mjs`
- `git diff --check`

#### 验证结果
- 后端编译通过。
- 前端构建通过，仅保留 Vite chunk 体积警告。
- API 容器重建并启动，`/health` 返回 `ok`。
- 真实 API 验收通过：管理员 21 个流程，运营 8 个流程，客服 6 个流程，财务 6 个流程。
- 真实 API 验收确认运营无法查看财务 Excel 流程详情，员工流程 ERP 资源不超过本岗位 `/erp/scopes`。
- 真实 API 验收确认响应未泄露 `Bearer`、`api_secret`、`password`、`Authorization`、`api_key` 等敏感文本。
- 真实浏览器验收通过，截图：
  - `/tmp/company-rag-automation-flows-admin-desktop.png`
  - `/tmp/company-rag-automation-flows-operations-desktop.png`
  - `/tmp/company-rag-automation-flows-finance-mobile.png`
- 三个流程配置页面截图均无横向溢出，详情弹窗可打开，页面不存在“保存/编辑/删除”写入按钮。
- 运行记录页面真实浏览器回归通过，管理员桌面、财务桌面和财务移动端均无横向溢出。
- 前端权限可见性真实回归全部通过。
- 本轮验收未使用 mock、stub、fake provider、monkeypatch 或模拟响应。

#### 后续待做
- Platform Loop 4：连接器中心一期，展示 ERPNext、金蝶、用友、Amazon SP-API、物流、广告、飞书/企业微信、邮箱和 Excel 等连接器。
