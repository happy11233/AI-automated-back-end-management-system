import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = requirePlaywright();

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const CHROME_EXECUTABLE_PATH = process.env.VERIFY_CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FINANCE_ACCOUNT = {
  username: "finance_demo",
  password: "Finance123456",
};

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const screenshot = "/tmp/company-rag-chat-threads-finance.png";

  await page.goto(`${FRONTEND_URL}/chat`, { waitUntil: "networkidle" });
  await login(page, FINANCE_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/chat`, { waitUntil: "networkidle" });

  await mainContent(page).getByText("客服对话", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const editableThreadInputCount = await mainContent(page)
    .locator("input")
    .filter({ hasText: /thread-/ })
    .count();
  if (editableThreadInputCount > 0) {
    throw new Error("chat_page: should not expose editable thread id input");
  }

  const createThreadResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/threads") &&
      response.request().method() === "POST" &&
      response.status() === 200,
    { timeout: 30000 },
  );
  await mainContent(page).getByRole("button", { name: "新会话" }).click();
  const createThreadResponse = await createThreadResponsePromise;
  const createThreadBody = await createThreadResponse.json();
  const firstThreadId = createThreadBody.item.id;
  await page.waitForFunction(
    (threadId) => window.location.pathname === `/chat/${threadId}`,
    firstThreadId,
    { timeout: 10000 },
  );
  await mainContent(page).getByText("已保存", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  if (!firstThreadId.startsWith("thread-")) {
    throw new Error(`chat_page: expected server generated thread id, got ${firstThreadId}`);
  }

  await mainContent(page).locator("textarea").fill("前端会话历史验证：只需要回复一句收到。");
  await mainContent(page).getByRole("button").filter({ has: page.locator(".anticon-comment") }).last().click();
  await mainContent(page).getByText("收到", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 90000,
  });

  await page.reload({ waitUntil: "networkidle" });
  await mainContent(page).getByText("已保存", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  const reloadThreadId = decodeURIComponent(new URL(page.url()).pathname.replace(/^\/chat\//, ""));
  if (reloadThreadId !== firstThreadId) {
    throw new Error(`chat_page: reload should reopen latest thread ${firstThreadId}, got ${reloadThreadId}`);
  }

  const renamedTitle = `前端改名验证 ${Date.now()}`;
  await mainContent(page).getByRole("button", { name: "修改会话标题" }).click();
  await mainContent(page).locator(".chatThreadTitleInput").fill(renamedTitle);
  await mainContent(page).getByRole("button", { name: "保存会话标题" }).click();
  await mainContent(page).getByText(renamedTitle, { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const leftNavNewConversationRouteCount = await page
    .locator('.ant-pro-sider .menuButton[data-nav-path="/chat/new"]')
    .count();
  if (leftNavNewConversationRouteCount > 0) {
    throw new Error("chat_page: left navigation should not contain create-new-conversation entry");
  }

  const leftNavThreadRouteCount = await page
    .locator('.ant-pro-sider .menuButton[data-nav-path^="/chat/thread-"]')
    .count();
  if (leftNavThreadRouteCount > 5) {
    throw new Error(`chat_page: left navigation should show at most 5 recent threads, got ${leftNavThreadRouteCount}`);
  }

  const leftNavThreadTitleCount = await page.locator(".ant-pro-sider").getByText(renamedTitle, { exact: false }).count();
  if (leftNavThreadTitleCount === 0) {
    throw new Error("chat_page: left navigation should contain the renamed recent thread");
  }

  await page.goto(`${FRONTEND_URL}/threads`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("会话记录", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  const manualThreadIdLabelCount = await mainContent(page).getByText("Thread ID", { exact: true }).count();
  if (manualThreadIdLabelCount > 0) {
    throw new Error("threads_page: should not show manual Thread ID query field");
  }

  const overflow = await assertNoHorizontalOverflow(page, "chat_threads_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  console.log(JSON.stringify({
    ok: true,
    firstThreadId,
    renamedTitle,
    leftNavNewConversationRouteCount,
    leftNavThreadRouteCount,
    leftNavThreadTitleCount,
    screenshot,
    overflow,
    note: "real browser, real frontend, real backend chat/thread APIs; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function login(page, account) {
  const loginButton = page.getByRole("button", { name: "登录" });
  const count = await loginButton.count();
  if (count > 0) {
    await loginButton.first().click();
  }
  const modal = page.locator(".ant-modal").filter({ hasText: "登录 Company RAG Agent" }).first();
  await modal.waitFor({ state: "visible", timeout: 10000 });
  await modal.locator("input").nth(0).fill(account.username);
  await modal.locator("input").nth(1).fill(account.password);
  const loginResponse = page.waitForResponse(
    (response) => response.url().includes("/api/auth/login") && response.status() === 200,
    { timeout: 30000 },
  );
  await page.locator(".ant-modal-footer .ant-btn-primary").click();
  await loginResponse;
  await page.waitForFunction(() => Boolean(window.localStorage.getItem("access_token")), null, {
    timeout: 10000,
  });
}

function mainContent(page) {
  return page.locator(".ant-pro-page-container").first();
}

async function assertNoHorizontalOverflow(page, label) {
  const overflow = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyWidth: document.body.scrollWidth,
  }));
  if (overflow.width > overflow.clientWidth + 2 || overflow.bodyWidth > overflow.clientWidth + 2) {
    throw new Error(`${label}: horizontal overflow ${JSON.stringify(overflow)}`);
  }
  return overflow;
}

function requirePlaywright() {
  const fs = require("node:fs");
  const os = require("node:os");
  const path = require("node:path");
  const candidates = [
    "playwright",
    `${process.cwd()}/node_modules/playwright`,
    `${process.cwd()}/frontend/node_modules/playwright`,
    process.env.PLAYWRIGHT_MODULE_PATH,
    ...findNpxPlaywrightInstalls(fs, os, path),
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {
      // Try the next real installation path.
    }
  }

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_chat_threads_frontend.mjs");
}

function findNpxPlaywrightInstalls(fs, os, path) {
  const npxRoot = path.join(os.homedir(), ".npm", "_npx");
  if (!fs.existsSync(npxRoot)) {
    return [];
  }

  return fs.readdirSync(npxRoot)
    .map((entry) => path.join(npxRoot, entry, "node_modules", "playwright"))
    .filter((candidate) => fs.existsSync(path.join(candidate, "package.json")));
}
