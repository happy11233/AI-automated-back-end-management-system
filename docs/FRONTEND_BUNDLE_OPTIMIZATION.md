# 前端拆分与产物验收

日期：2026-10-21。本轮针对前端单个约 2.2 MB JavaScript 产物，执行“记录基线 → 拆分源码 → 检查依赖图与体积 → 真实浏览器回归”的循环。没有升级框架或增加运行时依赖。

## 源码结构

| 位置 | 职责 |
| --- | --- |
| `frontend/src/main.tsx` | 4 行 React 启动入口 |
| `frontend/src/App.tsx` | 会话、岗位权限、导航、现有业务状态与请求协调 |
| `frontend/src/pages/` | 27 个独立业务页面，通过 `React.lazy` 加载 |
| `frontend/src/dialogs/` | 8 个详情/下载弹窗，仅打开时挂载并加载 |
| `frontend/src/components/` | 共享展示组件、Agent 工作区、异步加载边界、工作台布局 |
| `frontend/src/portal/PublicPortal.tsx` | 门户及其动画依赖；登录后的工作台不加载门户 |
| `frontend/src/workspace/types.ts` | 页面与业务状态的共享类型 |
| `frontend/src/workspace/shared.tsx` | 共用标签、格式化、权限与导航定义 |
| `frontend/src/workspace/legacy.tsx` | 保留原先未被调用的旧入口辅助函数，不进入构建依赖图 |

业务页面不导入 `main.tsx` 或 `App.tsx`。工作台布局独立加载，页内 `Suspense` 保留导航外框；弹窗拥有独立加载边界。加载/渲染失败显示刷新入口，切换页面后可重置边界。

`vite.config.ts` 显式拆分应用协调层、React、图标、样式引擎和 UI 基础依赖，其他组件由 Rollup 根据真实依赖共享。保留标准 500 kB 阈值，并生成 Vite manifest 供验收。

## 构建结果

基线取自本轮开始前的实际 `dist/assets/index-CCZt0Qn0.js`，原始大小 2,216,085 字节，gzip 668,586 字节。优化后的冷加载大小包含入口、目标页面和所有共享 JavaScript 依赖，不以单个入口文件大小代替首屏大小。

| 指标 | 优化前原始字节 | 优化后原始字节 | 降幅 | 优化后 gzip 字节 |
| --- | ---: | ---: | ---: | ---: |
| 门户首屏 | 2,216,085 | 1,113,585 | 49.7% | 340,314 |
| 工作台概览首屏 | 2,216,085 | 1,442,099 | 34.9% | 450,776 |
| Agent 工作区首次进入 | 2,216,085 | 1,704,325 | 23.1% | 537,876 |
| 最大单个 JS 块 | 2,216,085 | 406,688 | 81.6% | 123,306 |

共 77 个 JavaScript 块，27 个页面和 8 个弹窗均为动态入口；无超过 500,000 字节的块，构建不再出现超大 chunk 警告。全站 JS 文件合计 2,269,983 字节，较基线增加约 2.4%，收益来自首次加载范围和缓存粒度的改善。gzip 值为各文件独立压缩后的合计估算；预览服务的实际网络传输耗时受本机负载影响，本轮不将体积降幅宣称为等比例加载提速。

体积预算：门户首屏小于基线 65%，工作台概览小于基线 85%，最大单块不超过 500,000 字节。检查已加入 `.github/workflows/production-checks.yml`；远端 CI 需提交后运行。

## 验证方式

```sh
npm --prefix frontend run build
node scripts/verify_frontend_bundle.mjs
npm --prefix frontend run preview -- --port 5174 --strictPort
VERIFY_FRONTEND_URL=http://127.0.0.1:5174 node scripts/verify_frontend_bundle_browser.mjs
```

浏览器使用真实本地 API 和 demo 账号；不拦截 HTTP、不注入模拟响应或伪造令牌。管理员通过门户登录表单登录，其余账号通过真实 `/auth/login` 获取会话。测试只读取业务数据、导航和打开详情，不提交业务执行任务。

构建报告位于 `data/verification/frontend-bundle/build.json`。真实 Chromium 回归通过：管理员表单登录、业务路由、设置页 SPA 导航与标签刷新、流程/连接器弹窗关闭重开、Agent 技术详情、390px 移动端、财务任务列表真实 API 200 与刷新恢复，以及 admin_demo、finance_demo、employee_demo、operations_demo 的权限跳转。浏览器实际加载资源累计与表中体积一致；浏览器错误、失败资源和失败 API 响应均为 0，未创建业务任务。报告为同目录的 `browser.json`，截图为 `portal.png`、`dashboard.png`、`mobile.png`、`finance-mobile.png`。

## 静态资源服务

`deploy/nginx.conf` 增加以下配置，并经真实 Nginx 1.27 检查：

- `index.html` 及 SPA 深层路由回退结果使用 `Cache-Control: no-cache`。
- `/assets/` 下的哈希资源使用一年 `immutable` 缓存，保留原有安全响应头。
- JavaScript/CSS 等文本资源启用 gzip；不压缩 SSE 的 `text/event-stream`。
- 不存在的分块返回 404，避免被 SPA 回退误返回 HTML。

本地临时 Nginx 容器已通过语法、深层路由、缓存头、gzip、安全响应头和缺失分块的真实 HTTP 检查，报告为 `data/verification/frontend-bundle/nginx.json`。验收容器用后删除；本轮未部署公网。

生产发布应先上传新哈希资源，再切换 HTML，并保留上一版本资源至既有会话过期；回滚同样使用完整构建产物。错误边界的刷新按钮可恢复新入口，但不能替代发布时的旧资源保留策略。

## 后续优化

上述指标和验证属于本轮页面/弹窗分块。后续会话、设置、集成管理和运行观测 hooks 及按页读取的改造，单独记录在 [前端状态与请求拆分](FRONTEND_STATE_OPTIMIZATION.md)。剩余聊天、ERP、文件及通知审批仍可继续拆分，Agent 内部任务表单也可进一步按需加载。
