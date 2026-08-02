# 企业内部工作台

企业内部 AI 桌面工作台第一版。

## 启动

```bash
npm install
npm run dev
```

`npm run dev` 会同时启动 Vite 和 Electron。

如果只想浏览器预览：

```bash
npm run web:dev
```

浏览器地址：

```text
http://127.0.0.1:5174/
```

## 已接入接口

- 登录：`/auth/login`
- 当前用户：`/settings/me`
- 当前支持应用：`/ai-workflows`
- AI 对话：`/chat`
- 文档下载：`/files`

## 本地数据

对话记录按登录用户保存在系统应用数据目录中，最多保留 5 个对话。超过 5 个时会自动删除最旧对话。

在 macOS 上通常位于：

```text
~/Library/Application Support/企业内部工作台/conversations/<user_id>.json
```

旧版本的 `conversations.json` 会在首次读取时按用户迁移，并保留 `.legacy` 备份。

## 安全边界

桌面端只负责交互和发起请求。真实数据库连接、ERPNext 查询、自动化执行、权限校验、审批和审计都必须放在后端执行层。
