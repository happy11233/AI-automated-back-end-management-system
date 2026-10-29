# 前端状态与请求拆分

日期：2026-10-21。承接上一轮页面和弹窗分块，本轮继续拆分 `App.tsx` 的会话、后台管理状态和初始化请求。不新增运行时依赖。

## 模块职责

| 文件 | 职责 |
| --- | --- |
| `frontend/src/hooks/useSession.ts` | 登录、角色与岗位恢复、登录弹窗、会话持久化与退出清理 |
| `frontend/src/hooks/useAccountSettings.ts` | 个人资料、密码表单、设置读取与保存 |
| `frontend/src/hooks/useIntegrationAdmin.ts` | 连接器详情、MCP 工具、外部执行器配置和操作 |
| `frontend/src/hooks/useExecutionInsights.ts` | 运行记录及详情、效果分析、评测和监控数据 |
| `frontend/src/hooks/useWorkspaceLoading.ts` | 明确的页面到加载器映射，按登录身份和当前页面加载 |
| `frontend/src/components/SessionControls.tsx` | 登录、登录失败、会话失效弹窗，用户菜单和公开聊天控件 |
| `frontend/src/workspace/appHelpers.tsx` | 从入口移出的导航、业务数据映射和审计标签 |
| `frontend/src/App.tsx` | 页面组合、跨领域业务动作和其余待拆状态 |

各领域 hook 提供统一的 reset 方法，仅暴露当前组合层需要的状态和动作；页面、弹窗和 hooks 不反向导入应用入口。

## 请求策略

- 删除登录成功后的串行全量加载，以及应用挂载时的全量后台初始化。
- 登录身份变化时只加载侧栏会话列表；聊天和会话列表页面自己负责首次读取，避免与全局加载重复。
- 概览只读取 ERP 概览及侧栏会话；管理员额外读取反馈和审计数据，以保留概览统计。
- 连接器、MCP、执行器、运行记录、监控、评测、文件等数据在进入对应页面时读取，保留页面原有手动刷新和筛选动作。
- 用户和文档管理页面读取用户列表；ERP 页面才读取 ERP 权限、状态及诊断。
- 监控轮询保持仅在监控页且管理员已登录时运行，离页或退出时清除定时器。
- 退出会话时中断聊天流，清空业务表单、文件引用、详情及领域状态。
- JSON、流式和文件请求对照当前登录令牌；旧会话响应被忽略，旧会话 401 不触发新会话退出。
- 修复 `popstate` 监听器捕获首次渲染聊天回调的问题，使用当前回调处理历史导航。

没有加入 React Query、Redux 或新的路由框架。本轮先明确已有代码的状态边界和加载职责，避免在结构尚未稳定时同时迁移多个基础库。

## 验证

```sh
node frontend/node_modules/typescript/bin/tsc --noEmit -p frontend/tsconfig.json
node scripts/verify_frontend_page_loading.mjs
npm --prefix frontend run build
node scripts/verify_frontend_bundle.mjs
node scripts/verify_frontend_bundle_browser.mjs
git diff --check
```

新增浏览器验收脚本使用真实登录、真实 API 和真实 Chromium，覆盖：概览 GET 请求隔离、SPA 页面切换与直接刷新、连接器详情、真实旧会话成功/401 响应、退出后切换财务账号、财务任务页、移动端和真实 401 清理。负向测试会提交无效令牌给真实 API，以验证拒绝路径；不会把它当作有效身份。

脚本不拦截网络，不使用 mock、stub、fake provider 或 monkeypatch，不创建业务任务。通过后证据保存到 `data/verification/frontend-page-loading/browser.json` 和同目录截图；失败时保存 `failure.json` 和 `failure.png`。构建和四种岗位的完整分块回归沿用上一轮脚本。

当前验证进度：类型检查通过。真实浏览器首次登录遇到本地 PostgreSQL 连接中断，随后重试遭遇恢复期间的登录超时；后端 `/ready` 返回 503，数据库日志显示多个 PostgreSQL 子进程异常退出及自动恢复。正在等待真实服务恢复并重跑，尚未将本轮浏览器验收标记为通过。

## 继续拆分

聊天流和会话、ERP 查询与详情、文件及财务动作、通知反馈与审批等状态仍在组合层。后续可逐一迁入领域 hooks，再根据复用与取消需求决定是否引入统一查询缓存；不以本轮局部拆分宣称整个前端已完成重构。
