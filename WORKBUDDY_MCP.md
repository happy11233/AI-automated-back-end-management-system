# 在 WorkBuddy 操作项目 AI 自动化

项目级配置位于 .workbuddy/mcp.json。WorkBuddy 通过 stdio 启动 scripts/workbuddy_mcp.py，桥接服务调用项目现有 FastAPI，沿用项目登录、岗位权限、运行记录和审计。桥接脚本仅使用 Python 标准库。

## 连接步骤

1. 在 .workbuddy/mcp.json 把 COMPANY_RAG_MCP_USERNAME 填写为你的项目登录用户名。建议使用日常岗位账号。
2. 在 macOS 终端运行以下命令，把用户名替换为上一步的值；命令交互式输入密码，密码不会写进仓库：

   security add-generic-password -U -s company-rag-workbuddy -a '你的项目登录用户名' -w

3. 启动项目 API，确认 http://127.0.0.1:8001/health 可访问。执行工作流之前还应确认 /ready 返回 200。
4. 用 WorkBuddy 打开此项目，在「插件 → MCP 服务器 → 配置 MCP」检查 company-rag-agent 项目级配置，并刷新或连接；保存后确认连接状态。更改用户名后需重新连接。

需要在终端验证协议时，可运行 python3 scripts/check_workbuddy_mcp.py。此检查仅做握手、列工具和读取健康状态，不会运行任何自动化工作流。

## MCP 工具

| 工具 | 作用 |
| --- | --- |
| project_health | 检查 API 存活与依赖就绪，无需项目登录 |
| list_ai_workflows | 列出账号可见的流程及 workbuddy_can_run 标记 |
| get_ai_workflow | 查看输入要求、审批规则和专用页面入口 |
| run_ai_workflow | 执行个人获授权、通用入口可执行且无需审批的工作流 |
| workflow_activity | 查看账号可见的近期工作流运行记录 |
| list_agent_tasks、get_agent_task | 只读查看任务登记与详情 |

例如在 WorkBuddy 中说：“检查项目状态”“列出我能运行的 AI 工作流”“使用 operations_competitor_analysis 分析以下竞品信息：……”。运行工具会产生真实运行记录；重复调用会再次执行。通用运行接口是同步调用，MCP 等待响应上限 120 秒，实际耗时取决于模型、ERP 和后端。

审批、退款、对外发送、发布、薪资等流程，以及 executable=false 的专用页面流程，不通过这个 MCP 直接执行。get_ai_workflow 会返回相应页面入口。不要把密码或 JWT 放入 .workbuddy/mcp.json。跨机器使用时需改配置中的绝对路径；远程 API 地址只能使用 HTTPS。
