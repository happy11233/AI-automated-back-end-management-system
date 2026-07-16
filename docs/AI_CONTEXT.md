# AI_CONTEXT

## 项目路径

/Users/xiaoxiang/Documents/Codex/2026-06-23/react-vue/company-rag-agent

## 当前目标

我要在这个已有项目上新增和修改功能。

## 开发规则

- 先分析项目，不要直接改代码
- 每次只做一个小功能
- 不要一次性大改
- 优先复用已有代码
- 不要破坏已有功能
- 修改后要运行项目或测试验证
- 每次完成后更新 docs/TASKS.md 和 docs/CHANGELOG_AI.md

## AI 每次开始前必须先读

- docs/AI_CONTEXT.md
- docs/TASKS.md
- docs/CHANGELOG_AI.md
- docs/LOOP_ENGINEERING_PLAN.md
- docs/REAL_TESTING_POLICY.md
- docs/SECURITY_CHECKLIST.md
- docs/UI_QUALITY_CHECKLIST.md

## 当前状态

项目已完成初步分析和岗位/ERP/权限/审计/首页概览等多轮最小闭环。后续目标升级为企业级 AI 自动化平台，应遵循 Loop Engineering：小步开发、多 Agent 分工、优先复用、真实测试、截图验收、同步更新文档。

### Loop Engineering 硬规则

- 后续每个 loop 必须先明确目标、文件边界、验收标准和真实测试方式。
- 不允许把 mock、stub、fake provider、monkeypatch 或模拟响应测试写进项目代码。
- 验收必须尽量使用真实后端、真实数据库、真实登录账号、真实 ERPNext、真实浏览器和真实文件上传下载。
- 涉及前端布局时必须用浏览器截图检查桌面和移动端，重点检查卡片、表格、输入框、按钮和弹窗是否溢出。
- 涉及权限、ERP、AI 上下文、审计和 token 时必须按 `docs/SECURITY_CHECKLIST.md` 做真实验证。
- 每个 loop 完成后更新 `docs/TASKS.md`、`docs/CHANGELOG_AI.md`，通过验证后再进入下一个 loop。

## 项目技术栈

### 后端

- FastAPI
- Pydantic / pydantic-settings
- psycopg / psycopg_pool
- JWT / PyJWT
- pwdlib[argon2]
- PostgreSQL 16 + pgvector

### AI / RAG / Agent

- LangChain
- LangGraph
- LangChain PGVector
- rank-bm25
- jieba
- LangChain Text Splitters
- 阿里百炼 DashScope OpenAI Compatible API
- 默认聊天模型：qwen-plus
- 默认 Embedding 模型：text-embedding-v4

### 前端

- React 19
- Vite 7
- TypeScript
- Ant Design
- Ant Design Pro Components
- Tailwind CSS
- framer-motion
- lucide-react

### 部署与集成

- Docker Compose
- MCP 本地 Server
- 可选飞书文档 / 飞书多维表格工单集成

## 项目启动方式

### Docker Compose 启动后端和数据库

```bash
cp .env.example .env
docker compose up --build
```

初始化演示数据：

```bash
docker compose exec api python scripts/seed_data.py
docker compose exec api python scripts/set_password.py
```

服务地址：

- API: http://127.0.0.1:8001
- Swagger: http://127.0.0.1:8001/docs
- PostgreSQL: localhost:5433

### 本机启动后端

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres
uvicorn app.main:app --reload --port 8001
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

- http://127.0.0.1:5173

前端通过 Vite proxy 将 `/api` 转发到 `http://127.0.0.1:8001`。

## 前端目录结构

```text
frontend/
  package.json              前端依赖和 npm scripts
  vite.config.ts            Vite 配置和 /api 代理
  tailwind.config.js        Tailwind 配置
  src/
    main.tsx                主应用：公共门户、登录后后台、聊天、审批等页面
    api.ts                  后端接口封装和 SSE 解析
    styles.css              全局样式、聊天 UI、门户样式
    portal/
      components/           Navbar、Hero、Skills、Projects、Contact
      data/content.ts       中英文门户文案、项目和技能数据
```

## 后端目录结构

```text
app/
  main.py                   FastAPI 入口，注册路由和聊天、上传、MCP 接口
  config.py                 环境变量配置
  db.py                     PostgreSQL 连接池和查询封装
  llm.py                    百炼 ChatOpenAI 和 Embedding 封装
  api/                      auth、approvals、refunds、audit_logs、threads
  auth/                     JWT、登录用户解析、admin 权限
  graph/                    LangGraph 客服流程
  rag/                      文档解析、入库、检索、rerank、问答
  services/                 上下文记忆、日志、审批、退款、MCP 服务
  tools/                    LangChain tools：知识库、订单、审批
  agents/                   低风险工具调用 Agent
  mcp_servers/              本地文档系统、工单系统 MCP server
  feishu/                   可选飞书 API 客户端
scripts/                    种子数据、密码设置、评测、清理脚本
sql/                        schema 和迁移 SQL
eval/                       RAG 评测集和报告
docs/                       项目上下文、任务、变更记录、示例文档
```

## 已有功能

- JWT 登录，支持 admin / employee 角色。
- 企业客服聊天接口：`/chat` 和 `/chat/stream`。
- SSE 流式聊天，包含 start、node、content、done、error 事件。
- LangGraph 客服工作流：意图识别、订单号抽取、订单查询、知识库检索、退款风险判断、人工审批、答案生成。
- RAG 知识库：支持 txt、md、pdf、docx、csv、xlsx、xls 上传并向量化入库。
- 高级检索：向量检索、BM25 关键词检索、混合召回、query rewrite、rerank、父子文档检索、相似度阈值拒答。
- 权限过滤：文档 visibility、department；员工只能查询自己的订单。
- 上下文记忆：最近消息、会话摘要、当前业务状态、用户长期记忆、过期清理。
- 审批与退款：高风险退款生成审批，管理员审核，通过后执行退款并记录流水。
- 审计日志：聊天、文档上传、审批、MCP 操作等会写入审计记录。
- MCP 集成：同步本地或飞书文档到 RAG，创建和查询外部工单。
- 公共普通 LLM 聊天：`/public/llm/chat` 和 `/public/llm/chat/stream`，不接入 RAG 和业务工具。
- 前端公共门户：个人首页、语言切换、普通 LLM 浮窗。
- 前端后台：登录、客服聊天、文档上传、审批处理、退款流水、审计日志、会话详情。

## 数据库和数据存储

主存储为 PostgreSQL + pgvector，核心表包括：

- `users`
- `orders`
- `documents`
- `document_parent_chunks`
- `document_chunks`
- `chat_threads`
- `chat_messages`
- `chat_thread_summaries`
- `chat_thread_state`
- `user_memories`
- `approval_requests`
- `refund_transactions`
- `audit_logs`

未配置飞书工单时，外部工单会落到本地文件：

- `data/tickets.jsonl`

## 后续开发原则

- 每次只实现一个小功能。
- 优先新增 API 或前端页面的小闭环，不要一次性重构。
- 后端新增功能优先放到对应 `app/api/`、`app/services/`、`app/tools/` 或 `app/rag/` 模块。
- 前端新增功能优先复用 `frontend/src/api.ts` 的请求封装和 `frontend/src/main.tsx` 的现有页面结构。
- 涉及数据库结构变化时，必须新增 SQL 迁移，并说明验证方式。
- 修改后至少运行相关构建、脚本、接口或手工流程验证。

## 新增业务方向：亚马逊跨境电商 AI 应用平台

项目目标从通用公司客服 RAG 系统升级为企业内部 AI 应用平台，服务亚马逊跨境电商团队，通过 AI 自动化减少运营、客服、财务等部门重复工作。

### 系统角色与岗位

- `role=admin`：系统管理员，可以维护知识库、审批、审计、创建用户和分配岗位。
- `role=employee`：普通员工，必须绑定一个岗位，只能使用岗位权限内的 AI 能力。
- `position=operations`：运营岗位。
- `position=customer_service`：客服岗位。
- `position=finance`：财务岗位。

系统角色和岗位不能混用：`role` 决定是否拥有管理员后台权限，`position` 决定员工可以看到哪些自动化功能、AI 对话可以回答哪些内容、未来可以调用哪些 ERPNext API。

### 岗位 AI 能力范围

运营岗位：

- 生成 Amazon Listing
- 生成标题
- 生成五点描述
- 生成关键词
- 生成促销文案
- 竞品分析

客服岗位：

- 智能客服
- 自动回复
- 退款售后话术
- 多语言客服翻译

财务岗位：

- 分析财务报表
- 统计工资
- 上传 Excel 后按财务要求生成新 Excel 表

财务 Excel 生成功能：

- 后端接口：`POST /automation/finance/excel-transform`
- 权限：仅 `position=finance` 的员工或管理员可用。
- 前端入口：`/automation` 岗位应用页，财务区域的“上传 Excel 生成新表”。
- 支持 `.xlsx` / `.xls`，当前限制 8MB。
- 生成的新工作簿包含 `处理摘要`、`数值汇总`、`AI建议` 和整理后的源数据 sheet。
- 服务实现：`app/services/finance_excel_service.py`

### ERPNext 集成原则

外部 ERP 系统路径：

```text
/Users/xiaoxiang/Desktop/erpnext
```

ERPNext/Frappe 具备 REST API 能力。AI 平台后续应在本项目内封装 ERPNext API 客户端，而不是直接修改 ERPNext 项目本体。每个岗位只能调用自己岗位允许的 ERP API 或 DocType，所有 ERP 工具调用都要带用户、岗位、请求内容和结果摘要审计。

本地 ERPNext 当前通过 Docker 暴露在宿主机 `http://127.0.0.1:8080`。如果 `company-rag-api` 也运行在 Docker 容器里，`.env` 里的 `ERP_BASE_URL` 应配置为 `http://host.docker.internal:8080`；如果后端直接在宿主机运行，则使用 `http://127.0.0.1:8080`。已确认当前 ERPNext 应用版本为 Frappe 16.26.3 / ERPNext 16.27.0。

ERP 诊断入口：

- 管理员接口：`GET /erp/diagnostics`
- 命令行脚本：`python -m scripts.erp_diagnostics`
- 诊断只显示密钥是否配置和掩码预览，不输出 `ERP_API_SECRET` 原文。

ERPNext 真实联调状态：

- 专用 API 用户：`company_rag_api@example.com`
- 本项目 Docker API 容器使用 `ERP_BASE_URL=http://host.docker.internal:8080`
- `/erp/status` 已验证返回 `ok`
- 已验证岗位查询：运营 `Item`，客服 `Customer` / `Delivery Note`，财务 `GL Entry` / `Sales Invoice`
- 已验证客服查询 `Salary Slip` 会被平台 403 拦截
- 维护 ERPNext API 用户的脚本：`scripts/erpnext_api_user.py`

Amazon 业务测试数据：

- 种子脚本：`scripts/erpnext_amazon_seed.py`
- 商品 SKU：`AMZ-AIR-PUMP-001`、`AMZ-LED-DESK-002`、`AMZ-CABLE-USB-C-003`
- Amazon 订单号：`AMZ-US-112-4589012-7783401`、`AMZ-DE-305-7712468-1290045`、`AMZ-JP-250-6630188-4402197`
- 物流单号：`1ZAMZUS202607150001`、`DHL-DE-AMZ-2026071502`、`YAMATO-JP-2026071503`
- 已验证平台可按 SKU、客户名、Amazon 订单号、物流单号、售后主题和发票订单号查询 ERPNext。

AI 对话 ERP 查询状态：

- `/chat` 已可通过自然语言查询 Amazon ERP 测试数据。
- 示例：运营问 `帮我查一下 Amazon 订单 AMZ-DE-305-7712468-1290045 的销售订单`，返回 Sales Order。
- 示例：客服问 `帮我查一下 AMZ-DE-305-7712468-1290045 的物流`，返回 Delivery Note。
- 示例：客服问 `帮我查一下 AMZ-US-112-4589012-7783401 的售后工单`，返回 Issue。
- 示例：财务问 `帮我查一下 AMZ-JP-250-6630188-4402197 的销售发票`，返回 Sales Invoice。
- 回归脚本：`python3 scripts/verify_erp_chat.py`
- 岗位越权回归脚本：`python3 scripts/verify_position_permissions.py`
- 前端权限可见性回归脚本：`NODE_PATH=/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/verify_frontend_permissions.mjs`
- 统一验证脚本：`python3 scripts/verify_all.py`
- 统一验证会依次执行后端编译、API `/health`、管理员 ERP 诊断、ERP 对话权限回归、岗位越权权限回归、财务 Excel 生成回归、前端构建、前端权限可见性回归。
- 如 API 不在默认端口，可用 `VERIFY_API_BASE_URL=http://127.0.0.1:8001 python3 scripts/verify_all.py` 指定地址。

前端 ERP 诊断面板：

- ERP 页面：`/erp`
- 管理员登录后会显示“管理员 ERP 诊断”，包含连接状态、provider 配置、岗位资源映射和下一步建议。
- 员工登录后只显示当前岗位 ERP 查询，不显示诊断面板，也不请求 `/erp/diagnostics`。
- 已浏览器验证：`admin_demo` 可见诊断面板，`employee_demo` 不可见诊断面板。
- 已自动化验证：管理员可见 ERP 诊断；客服不可见 ERP 诊断、用户管理、知识库；财务可见 Excel 上传入口；运营/客服不可见财务 Excel 上传入口。

前端 URL 路由状态：

- 后台页面已支持根据 URL 初始化当前视图，例如 `/dashboard`、`/automation`、`/erp`、`/chat`、`/documents`、`/users`、`/approvals`、`/refunds`、`/audit`、`/threads`。
- 菜单点击会同步更新浏览器 URL，浏览器前进/后退会同步 `activeView`。
- 已登录状态刷新页面后会自动加载岗位任务、ERP scope 和管理员数据。
- 员工访问管理员专属 URL 时会显示“当前账号没有权限访问该页面，已返回概览。”，并回到 `/dashboard`。
- 前端权限可见性回归已覆盖直接访问 `/automation`、`/erp`、浏览器后退、员工访问 `/users` 被提示并跳回概览。

前端首页快捷入口状态：

- 首页 `/dashboard` 会按账号身份显示快捷入口。
- 管理员显示“管理员快捷入口”：用户管理、ERP 诊断、知识库上传、审计日志。
- 运营显示：运营 AI 自动化、运营 ERP 查询、AI 对话。
- 客服显示：客服 AI 对话、客服 ERP 查询、客服自动化。
- 财务显示：财务 Excel 生成、财务 ERP 查询、财务 AI 对话。
- 快捷入口使用现有 URL 路由跳转，按钮带 `aria-label`，前端权限可见性回归已覆盖四类账号首页入口的可见性和部分跳转。

前端首页 ERP 数据概览状态：

- 后端接口：`GET /erp/dashboard-overview`
- 支持站点筛选参数：`market=all|us|de|jp`，分别代表全部站点、美国站、德国站、日本站。
- 支持时间范围筛选参数：`date_range=all|today|7d|30d`，分别代表全部时间、今天、近 7 天、近 30 天。
- 支持店铺筛选参数：`store=all|us_store|de_store|jp_store`，分别代表全部店铺、US Store、DE Store、JP Store。
- 管理员首页显示“平台数据概览”：ERP 连接、可用 Provider、岗位 ERP 资源；不直接展开岗位业务数据。
- 运营首页显示“运营数据概览”：销售订单、商品资料、商品价格。
- 客服首页显示“客服数据概览”：物流/出库单、售后工单、客户资料。
- 财务首页显示“财务数据概览”：销售发票、收付款单、总账分录。
- 首页有“全部、美国、德国、日本”分段筛选；订单、物流、售后、销售发票按 Amazon 站点标记过滤。
- 首页有“全部时间、今天、近7天、近30天”分段筛选；后端按 `posting_date`、`transaction_date`、`modified`、`creation`、`due_date`、`start_date`、`end_date` 做轻量日期过滤。
- 首页有“全部店铺、US Store、DE Store、JP Store”分段筛选；订单、物流、售后、销售发票按店铺标记过滤。
- 商品、价格、总账、收付款等全局资源当前保持全站展示，不按站点硬过滤。
- 每个概览分组返回 `total_count`、`amount_total`、`amount_label`，前端展示“匹配 N 条”和金额合计。
- 首页指标卡会展示岗位内关键金额，例如运营订单金额、财务发票金额、收付款金额、总账借贷发生额等。
- 概览接口复用 ERP provider 和 `ensure_erp_resource_allowed` 岗位权限校验，员工不会拿到跨岗位资源。
- 前端首页展示概览指标和每类资源最近 3 条 ERP 记录，记录行有“详情”按钮。
- 记录详情接口：`GET /erp/records/{resource}/{record_id}`，会再次检查岗位 ERP 权限。
- 前端详情弹窗标题为“ERP 记录详情 / 资源名称”，展示 provider、资源、记录 ID 和字段表格。
- 岗位越权回归已覆盖概览接口只返回本岗位资源、站点筛选、店铺筛选、时间范围筛选和记录详情权限；前端权限可见性回归已覆盖四类账号首页概览、站点/店铺/时间控件、金额指标和运营打开 ERP 记录详情。

AI 对话 ERP 引用状态：

- ERP 意图会调用 `query_erp_for_current_user`，只查询当前岗位允许的资源。
- ERP 查询回答中会带 `[ERP-1]` 编号，并在末尾列出“引用 ERP 记录”。
- `/chat` 响应字段包含 `erp_references`，`/chat/stream` 的 `done` 事件也包含 `erp_references`。
- 聊天消息 metadata 保存 `erp_references`，前端聊天气泡展示“引用：资源 / 记录 ID”。
- 回归脚本 `scripts/verify_erp_chat.py` 已验证运营、客服、财务 ERP 对话均返回引用文本。

管理员审计状态：

- 审计接口：`GET /admin/audit-logs`
- 支持参数：`action`、`resource_type`、`position=operations|customer_service|finance`、`limit`
- 前端审计页 `/audit` 提供动作、资源类型、岗位筛选和查询按钮。
- 管理员创建用户时会写入 `admin.user.create` 和 `admin.user.permission_assignment` 两条审计。
- ERP 聊天审计会记录 `erp_reference_count`。
- 发布前稳定化脚本会验证审计筛选返回的数据符合 action/resource/position 条件。

### 对话权限原则

- AI 对话必须先判断当前用户岗位权限，再进入 RAG、Agent 或 ERP 工具调用。
- 客服不能查询财务报表、工资、利润、成本等财务数据。
- 运营不能查询财务报表、工资等财务数据，也不能查询客服私有售后会话。
- 财务不能查询客服私有会话或运营私有数据。
- 越权问题要拒答或返回权限不足，不允许模型自由发挥。
- 权限过滤应尽量放在工具调用和检索之前，避免敏感信息进入模型上下文。
- 岗位越权回归当前覆盖：自动化任务跨岗位调用、ERP 资源跨岗位查询、聊天敏感词、财务 Excel 上传、管理员用户接口、ERP 诊断接口、岗位首页概览资源隔离、站点筛选和时间范围筛选。
- 岗位越权回归当前覆盖：自动化任务跨岗位调用、ERP 资源跨岗位查询、聊天敏感词、财务 Excel 上传、管理员用户接口、ERP 诊断接口、岗位首页概览资源隔离、站点筛选、店铺筛选、时间范围筛选和 ERP 记录详情权限。
- 前端权限可见性回归当前覆盖：管理员/员工 ERP 页面差异、财务 Excel 上传入口、运营/客服/财务岗位应用互斥展示、员工菜单隐藏用户管理和知识库、四类账号首页快捷入口隔离、四类账号首页 ERP 概览、站点/店铺/时间筛选、金额指标、记录详情弹窗和审计筛选控件。
- 发布前稳定化回归脚本：`python3 scripts/verify_release_ready.py`，覆盖店铺筛选 + 金额指标、记录详情权限、AI 对话 ERP 引用和管理员审计筛选。
