# TASKS

## 阶段 0：项目分析

- [x] 分析项目技术栈
- [x] 分析项目启动方式
- [x] 分析前端目录结构
- [x] 分析后端目录结构
- [x] 分析已有功能
- [x] 分析数据库或数据存储方式
- [x] 总结适合新增功能的开发方式

## 阶段 1：我要新增的功能

- [ ] 功能1：增加 3 个岗位：运营、客服、财务
- [ ] 功能2：每个岗位登录后台后只看到自己岗位的 AI 自动化能力
- [ ] 功能3：管理员在后台创建用户，创建时选择岗位并设置账号密码
- [ ] 功能4：AI 平台连接外部 ERPNext API，按岗位限制可调用的 ERP 能力
- [ ] 功能5：AI 对话能根据用户问题检索岗位权限内的 ERP 内容并回答

## 阶段 2：我要修改的功能

- [ ] 修改1：AI 对话只能回答当前岗位权限内的问题
- [ ] 修改2：客服不能查询财务报表、工资、利润等财务数据
- [ ] 修改3：运营不能查询财务报表或客服私有售后数据
- [ ] 修改4：财务不能越权查询客服私有会话或运营私有数据
- [ ] 修改5：所有越权访问要被拦截，并尽量写入审计日志

## 当前完成进度

- [x] 第一轮最小闭环：岗位字段、管理员创建用户、登录返回岗位、前端岗位入口、基础聊天越权拦截
- [x] 第二轮最小闭环：岗位 AI 自动化任务接口、前端岗位表单、真实大模型生成、岗位任务权限校验
- [x] 第三轮最小闭环：ERP provider 连接层、岗位 ERP 查询页、岗位 ERP scope 强制校验
- [x] 第四轮最小闭环：AI 对话识别 ERP 问题，并按岗位权限调用 ERP 检索
- [x] 第五轮最小闭环：管理员 ERP 诊断接口、本地 ERPNext 连通性诊断脚本、ERPNext Docker 接入说明
- [x] 第六轮最小闭环：ERPNext 专用 API 用户、真实 token 配置、岗位真实 DocType 查询验证
- [x] 第七轮最小闭环：ERPNext 写入 Amazon 跨境电商测试数据，并支持按 SKU、订单号、物流单号查询
- [x] 第八轮最小闭环：AI 对话可直接查询 Amazon ERP 测试数据，并保持岗位越权拦截
- [x] 第九轮最小闭环：前端管理员 ERP 诊断面板，员工仍只看到岗位 ERP 查询
- [x] 第十轮最小闭环：统一验证命令，串联后端编译、ERP 诊断、ERP 对话回归和前端构建
- [x] 第十一轮最小闭环：财务岗位上传 Excel 后生成新 Excel 文件
- [x] 第十二轮最小闭环：岗位越权权限回归脚本，覆盖自动化、ERP、聊天、财务 Excel 和管理员接口
- [x] 第十三轮最小闭环：前端权限可见性回归脚本，覆盖管理员/员工页面差异和岗位应用入口
- [x] 第十四轮最小闭环：前端 URL 路由与页面状态同步，支持直达链接、刷新和浏览器后退
- [x] 第十五轮最小闭环：员工访问管理员页面时显示权限提示并跳回概览
- [x] 第十六轮最小闭环：岗位首页快捷入口，管理员和运营/客服/财务首页只显示对应常用功能
- [x] 第十七轮最小闭环：岗位首页接入 ERP 数据概览，按运营/客服/财务权限展示关键指标和最近记录

## 分阶段执行计划

### Loop 1：岗位与用户注册基础

- [x] 数据库 users 表增加 position 字段
- [x] 登录 token 和登录响应返回 position
- [x] 管理员后台新增用户管理入口
- [x] 管理员可以创建运营、客服、财务岗位用户
- [x] 员工登录后看到对应岗位自动化能力列表
- [x] 聊天入口增加岗位越权关键词拦截

### Loop 2：岗位 AI 自动化页面

- [x] 运营：Listing、标题、五点描述、关键词、促销文案、竞品分析
- [x] 客服：智能客服、自动回复、退款售后话术、多语言客服翻译
- [x] 财务：财务报表分析、工资统计、Excel 结构生成原型
- [x] 财务：上传 Excel 文件后生成新 Excel 文件

### Loop 3：ERPNext 连接层

- [x] 增加 ERPNext API 客户端配置
- [x] 为运营、客服、财务分别定义允许调用的 ERP DocType/API
- [x] 增加岗位级 ERP 工具调用审计
- [x] AI 对话按岗位调用 ERP 检索工具

### Loop 4：RAG 与 ERP 权限闭环

- [x] RAG 文档和 ERP 查询都带岗位权限过滤
- [x] 越权问题返回拒答，不进入模型生成
- [x] 增加越权测试用例
- [x] 增加岗位权限回归验证

### Loop 5：ERP 真实接入诊断闭环

- [x] 增加管理员专用 `/erp/diagnostics` 诊断接口
- [x] 诊断接口只返回配置是否存在和密钥掩码，不泄露原始密钥
- [x] 增加 `scripts/erp_diagnostics.py` 本地诊断脚本
- [x] 明确本地 ERPNext Docker 场景的 `ERP_BASE_URL` 配置方式
- [x] 在 ERPNext 用户里生成 API Key / API Secret 后做真实数据查询联调
- [x] 增加前端管理员 ERP 诊断面板

### Loop 6：ERPNext 真实查询联调

- [x] 创建 ERPNext 专用 API 用户 `company_rag_api@example.com`
- [x] 为 API 用户补充销售、库存、客服、财务、人事等只读查询所需业务角色
- [x] 将 `ERP_BASE_URL=http://host.docker.internal:8080` 和 token 配置写入 `.env`
- [x] 验证 `/erp/status` 返回 `ok`
- [x] 验证运营账号可查 `Item`
- [x] 验证客服账号可查 `Customer` 和 `Delivery Note`
- [x] 验证财务账号可查 `GL Entry` 和 `Sales Invoice`
- [x] 验证客服账号查询 `Salary Slip` 仍被平台 403 拦截
- [x] 给 ERPNext 写入更贴近 Amazon 业务的测试数据，例如订单号、SKU、物流单号、店铺、币种

### Loop 7：Amazon 业务测试数据和查询增强

- [x] 新增 `scripts/erpnext_amazon_seed.py`
- [x] 写入 3 个 Amazon SKU
- [x] 写入 3 个 Amazon 买家客户
- [x] 写入 3 条带 Amazon 订单号 `po_no` 的 Sales Order
- [x] 写入 3 条带物流单号 `lr_no` 的 Delivery Note
- [x] 写入 3 条带 Amazon 订单号的 Sales Invoice
- [x] 写入 3 条售后 Issue，覆盖退款、物流、补发场景
- [x] ERPNext 查询增强：按 SKU、客户名、订单号、物流单号、售后主题、发票订单号命中
- [x] 验证客服查询工资单仍然 403 拦截
- [x] 在 AI 对话里验证自然语言问题能正确路由到这些 Amazon 测试数据

### Loop 8：AI 对话 ERP 查询闭环

- [x] ERP 意图识别增加规则兜底，减少物流/订单类问题误走本地订单表
- [x] ERP 查询从自然语言中提取 Amazon 订单号、SKU、物流单号作为检索词
- [x] ERP 对话摘要展示 `po_no`、`lr_no`、`subject`、`description`、金额、状态等业务字段
- [x] 验证运营可在对话中查询 Amazon 销售订单
- [x] 验证客服可在对话中查询物流和售后工单
- [x] 验证财务可在对话中查询销售发票
- [x] 验证客服对话查询工资单仍然被 403 拦截
- [x] 新增 `scripts/verify_erp_chat.py` 作为回归验证脚本
- [x] 把 ERP 对话验证纳入正式测试命令或 CI

### Loop 9：前端管理员 ERP 诊断面板

- [x] 前端 API 增加 `/erp/diagnostics` 类型和请求方法
- [x] 管理员登录后自动加载 ERP 诊断数据
- [x] ERP 页面管理员可看到连接状态、当前 provider、配置项掩码、岗位资源映射和下一步建议
- [x] 普通员工不请求 `/erp/diagnostics`，只显示当前岗位 ERP 查询资源
- [x] 浏览器验证管理员面板显示 `ok`、`company_rag_api@example.com`、金蝶/用友预留配置和岗位映射
- [x] 浏览器验证客服账号不显示管理员 ERP 诊断面板
- [x] 增加前端自动化测试覆盖管理员/员工 ERP 页面差异

### Loop 10：统一验证命令

- [x] 新增 `scripts/verify_all.py`
- [x] 串联后端 Python 编译：`.venv/bin/python -m compileall app scripts`
- [x] 验证 API `/health` 可访问
- [x] 管理员登录后验证 `/erp/diagnostics` 的 `active_health.status == ok`
- [x] 调用 `scripts/verify_erp_chat.py` 验证运营、客服、财务 ERP 对话和客服越权拦截
- [x] 调用 `scripts/verify_position_permissions.py` 验证岗位越权权限边界
- [x] 验证财务账号上传 Excel 后能生成包含处理摘要、数值汇总、AI 建议的新工作簿
- [x] 执行前端 `npm run build`
- [x] 调用 `scripts/verify_frontend_permissions.mjs` 验证前端权限可见性
- [ ] 后续接入 CI 或发布前固定检查流程

### Loop 11：财务 Excel 上传生成

- [x] 新增财务 Excel 服务 `app/services/finance_excel_service.py`
- [x] 新增接口 `POST /automation/finance/excel-transform`
- [x] 接口只允许财务岗位或管理员使用，其他岗位返回 403
- [x] 支持上传 `.xlsx` / `.xls`，限制 8MB
- [x] 生成新工作簿，包含 `处理摘要`、`数值汇总`、`AI建议` 和整理后的源数据 sheet
- [x] 前端岗位应用页的财务区域增加 Excel 上传、处理要求输入和下载按钮
- [x] 统一验证脚本增加财务 Excel 生成回归
- [ ] 后续增强：按用户要求生成更具体的工资表、利润表、费用分类表模板

### Loop 12：岗位越权权限回归

- [x] 新增 `scripts/verify_position_permissions.py`
- [x] 验证运营不能使用客服自动化任务
- [x] 验证客服不能使用财务自动化任务
- [x] 验证财务不能使用运营自动化任务
- [x] 验证客服不能查询 `GL Entry`
- [x] 验证运营不能查询 `Salary Slip`
- [x] 验证财务不能查询客服售后 `Issue`
- [x] 验证客服聊天不能查询财务报表/利润
- [x] 验证运营聊天不能查询工资/薪资
- [x] 验证财务聊天不能查询客服私有会话
- [x] 验证客服不能使用财务 Excel 上传生成接口
- [x] 验证员工不能访问管理员用户接口和 ERP 诊断接口
- [x] 验证管理员仍可查看全部岗位自动化任务
- [x] 将岗位越权回归纳入 `scripts/verify_all.py`

### Loop 13：前端权限可见性回归

- [x] 新增 `scripts/verify_frontend_permissions.mjs`
- [x] 使用真实登录流程验证管理员 ERP 页面可见“管理员 ERP 诊断”
- [x] 验证客服 ERP 页面不显示“管理员 ERP 诊断”，且不显示“用户管理”“知识库”
- [x] 验证财务岗位应用页显示“上传 Excel 生成新表”和“生成并下载 Excel”
- [x] 验证客服岗位应用页不显示财务 Excel 上传入口
- [x] 验证运营岗位应用页只显示运营自动化，不显示客服/财务自动化
- [x] 将前端权限可见性回归纳入 `scripts/verify_all.py`

### Loop 14：前端 URL 路由同步

- [x] 页面初始化时根据 `window.location.pathname` 设置 `activeView`
- [x] 菜单点击时同步更新浏览器 URL
- [x] 支持浏览器前进/后退同步当前页面
- [x] 已登录状态刷新页面后自动加载岗位任务、ERP scope 和管理员数据
- [x] 员工访问管理员专属 URL 时自动回到 `/dashboard`
- [x] 前端权限回归脚本增加直接访问 `/automation`、`/erp` 和浏览器后退验证

### Loop 15：管理员页面无权访问提示

- [x] 员工访问管理员专属 URL 时显示“当前账号没有权限访问该页面，已返回概览。”
- [x] 跳转到 `/dashboard` 时同步更新状态栏提示
- [x] 避免同一路径重复弹出权限提示
- [x] 前端权限回归脚本增加 `/users` 无权访问提示验证

### Loop 16：岗位首页快捷入口

- [x] 管理员首页显示“管理员快捷入口”
- [x] 管理员快捷入口包含用户管理、ERP 诊断、知识库上传、审计日志
- [x] 运营首页显示运营 AI 自动化、运营 ERP 查询、AI 对话
- [x] 客服首页显示客服 AI 对话、客服 ERP 查询、客服自动化
- [x] 财务首页显示财务 Excel 生成、财务 ERP 查询、财务 AI 对话
- [x] 快捷入口按钮通过现有 URL 路由跳转到对应页面
- [x] 快捷入口按钮增加稳定 `aria-label`，便于无障碍访问和浏览器自动化验证
- [x] 前端权限回归脚本覆盖管理员、运营、客服、财务首页快捷入口可见性和跳转

### Loop 17：岗位首页 ERP 数据概览

- [x] 新增 `GET /erp/dashboard-overview`
- [x] 管理员首页显示平台数据概览：ERP 连接、可用 Provider、岗位 ERP 资源
- [x] 运营首页显示运营数据概览：销售订单、商品资料、商品价格
- [x] 客服首页显示客服数据概览：物流/出库单、售后工单、客户资料
- [x] 财务首页显示财务数据概览：销售发票、收付款单、总账分录
- [x] 概览接口复用 ERP provider 和岗位权限校验，不开放跨岗位资源
- [x] 前端首页展示概览指标和最近 3 条 ERP 记录
- [x] 岗位越权回归脚本验证概览接口只返回本岗位资源
- [x] 前端权限回归脚本验证四类账号首页概览可见性

### Loop 18：岗位首页站点筛选

- [x] `GET /erp/dashboard-overview` 支持 `market=all|us|de|jp`
- [x] 首页概览支持“全部、美国、德国、日本”分段筛选
- [x] 订单、物流、售后、销售发票按 Amazon 站点标记过滤
- [x] 商品、价格、总账、收付款等全局资源保持全站展示
- [x] 每个概览分组返回并展示 `total_count`
- [x] 岗位越权回归覆盖站点筛选后的资源隔离
- [x] 前端权限回归覆盖站点筛选控件和运营切换德国站

### Loop 19：岗位首页时间范围筛选

- [x] `GET /erp/dashboard-overview` 支持 `date_range=all|today|7d|30d`
- [x] 首页概览支持“全部时间、今天、近7天、近30天”分段筛选
- [x] 后端按 `posting_date`、`transaction_date`、`modified`、`creation`、`due_date` 等字段做轻量日期过滤
- [x] 概览消息显示站点和时间范围，例如“德国站 / 近 30 天”
- [x] 岗位越权回归覆盖时间范围参数下的资源隔离
- [x] 前端权限回归覆盖时间筛选控件和运营切换德国站 + 近30天

### Loop 20：岗位首页店铺筛选

- [x] `GET /erp/dashboard-overview` 支持 `store=all|us_store|de_store|jp_store`
- [x] 首页概览增加“全部店铺、US Store、DE Store、JP Store”分段筛选
- [x] 订单、物流、售后、销售发票按店铺标记过滤
- [x] 商品、价格、总账、收付款等全局资源继续保持全站/全部店铺展示
- [x] 概览审计日志记录 `store` 参数，便于管理员追踪筛选范围
- [x] 岗位越权回归覆盖店铺筛选后的资源隔离
- [x] 前端权限回归覆盖店铺筛选控件和运营切换 DE Store

### Loop 21：首页关键金额指标

- [x] 概览 section 返回 `amount_total` 和 `amount_label`
- [x] 首页指标卡增加订单金额、发票金额、出库金额、收付款金额、价格合计等关键金额指标
- [x] 概览卡片内展示当前筛选范围金额合计
- [x] 金额指标沿用岗位资源权限，不跨岗位聚合数据
- [x] 发布前稳定化脚本验证店铺筛选下能返回金额指标
- [x] 前端权限回归覆盖运营订单金额和财务发票金额展示

### Loop 22：ERP 概览记录详情

- [x] 新增 `GET /erp/records/{resource}/{record_id}`
- [x] 记录详情接口复用 `ensure_erp_resource_allowed`，员工只能打开本岗位允许资源
- [x] 首页概览最近记录增加“详情”按钮
- [x] 前端详情弹窗展示 provider、资源、记录 ID 和字段表格
- [x] 详情按钮增加稳定 `aria-label`，避免浏览器自动化点到菜单“会话详情”
- [x] 岗位越权回归覆盖客服可打开物流详情、不能打开财务总账详情
- [x] 前端权限回归覆盖运营首页打开 ERP 记录详情弹窗

### Loop 23：AI 对话引用 ERP 结果

- [x] ERP 查询摘要增加 `[ERP-1]` 形式的引用编号
- [x] `/chat` 响应增加 `erp_references`
- [x] `/chat/stream` 的 `done` 事件增加 `erp_references`
- [x] 聊天消息 metadata 保存 `erp_references`
- [x] 前端聊天气泡展示“引用：资源 / 记录 ID”
- [x] ERP 聊天回归验证运营、客服、财务查询回答包含“引用 ERP 记录”
- [x] 发布前稳定化脚本验证财务 ERP 对话返回引用数组

### Loop 24：管理员权限与审计增强

- [x] `GET /admin/audit-logs` 支持 `action`、`resource_type`、`position`、`limit` 筛选
- [x] 审计服务支持按 metadata 中的岗位过滤
- [x] 用户创建时额外写入 `admin.user.permission_assignment` 审计记录
- [x] ERP 聊天审计记录 `erp_reference_count`
- [x] 修复 ERP 聊天审计 metadata 中重复 `status` 字段
- [x] 前端审计页增加动作、资源类型、岗位筛选控件
- [x] 前端权限回归覆盖管理员审计筛选控件可见性

### Loop 25：发布前稳定化

- [x] 新增 `scripts/verify_release_ready.py`
- [x] 发布前脚本覆盖店铺筛选 + 金额指标
- [x] 发布前脚本覆盖记录详情权限
- [x] 发布前脚本覆盖 AI 对话 ERP 引用
- [x] 发布前脚本覆盖管理员审计筛选
- [x] `scripts/verify_all.py` 纳入发布前稳定化回归
- [x] 重新执行后端编译、前端构建、API 容器重建、岗位权限、ERP 聊天、发布前稳定化、前端权限可见性回归

## 企业级 AI 自动化平台升级

### Platform Loop 0：Loop Engineering 规则与验收清单

- [x] 新增 `docs/LOOP_ENGINEERING_PLAN.md`
- [x] 新增 `docs/AI_PLATFORM_REQUIREMENTS.md`
- [x] 新增 `docs/UI_QUALITY_CHECKLIST.md`
- [x] 新增 `docs/SECURITY_CHECKLIST.md`
- [x] 新增 `docs/REAL_TESTING_POLICY.md`
- [x] 明确多 Agent 分工：项目经理、架构、开发、Code Review、测试、安全、DevOps、文档、监控、页面格式
- [x] 明确真实测试红线：不把 mock / stub / fake provider / monkeypatch 测试写进项目代码
- [x] 明确每个 loop 必须做真实服务验证、文档更新、review 和截图验收

### Platform Loop 1：企业级导航与只读 AI 应用中心

- [x] 将后台导航升级为企业 AI 平台结构，新增 `/ai-apps`
- [x] 新增 AI 应用中心页面
- [x] 将现有运营、客服、财务、ERP、RAG、Excel 能力注册为 AI 应用目录
- [x] 管理员可见全部应用，员工只可见自己岗位应用
- [x] 保留现有自动化、ERP、聊天、知识库、用户、审批、审计页面入口
- [x] 首页快捷入口引导到 AI 应用中心，具体执行入口仍可进入原岗位自动化页
- [x] 真实前端构建和浏览器截图检查通过
- [x] 前端权限可见性真实回归脚本覆盖 AI 应用中心

### Platform Loop 2：统一运行记录中心

- [ ] 新增真实数据库运行记录表
- [ ] 记录自动化生成、财务 Excel、ERP 查询、AI 对话 ERP 查询等真实执行
- [ ] 新增运行记录页面
- [ ] 运行详情展示输入预览、输出预览、状态、耗时、岗位、用户、ERP/RAG 引用和错误原因
- [ ] 审计日志继续用于合规，不替代运行记录

### Platform Loop 3：自动化流程配置一期

- [ ] 新增自动化流程配置页面
- [ ] 管理员可查看应用的输入 schema、Prompt、输出格式、允许资源、审批规则
- [ ] 员工不可编辑流程配置
- [ ] 先做只读配置和版本展示，不一次性做完整低代码编排

### Platform Loop 4：连接器中心一期

- [ ] 新增系统连接器页面
- [ ] 注册 ERPNext、金蝶、用友、Amazon SP-API、物流、广告、飞书/企业微信、邮箱、Excel 等连接器
- [ ] ERPNext 连接状态使用真实诊断
- [ ] 管理员可见掩码配置和资源映射，员工不可见密钥和管理诊断

### Platform Loop 5：效果分析中心一期

- [ ] 基于真实运行记录和审计事件生成效果指标
- [ ] 展示自动化次数、成功率、失败率、人工接管率、审批拦截、ERP 查询数、节省时间估算
- [ ] 按岗位和应用维度展示使用排行与失败原因
- [ ] 页面布局通过桌面和移动端截图检查

### Platform Loop 6：AI 评测中心一期

- [ ] 新增 AI 评测中心页面
- [ ] 管理 RAG、ERP、权限拒答、自动化输出格式测试集
- [ ] 调用真实评测脚本或真实后端评测 API
- [ ] 输出通过率、失败样例、引用命中和越权拦截结果
