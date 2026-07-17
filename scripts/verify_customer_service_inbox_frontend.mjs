import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = requirePlaywright();

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const CHROME_EXECUTABLE_PATH = process.env.VERIFY_CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const customerResult = await runInboxCase({
    label: "customer_service_inbox_desktop",
    account: { username: "employee_demo", password: "Employee123456" },
    viewport: { width: 1366, height: 900 },
    path: "/automation/customer-service-inbox",
    screenshot: "/tmp/company-rag-customer-service-inbox-desktop.png",
    visible: ["客服自动化收件箱", "客户消息录入", "消息队列", "处理结果", "加入收件箱"],
    hidden: ["财务 AI 自动化", "用户管理", "知识库"],
  });

  const financeForbidden = await runInboxCase({
    label: "finance_inbox_hidden",
    account: { username: "finance_demo", password: "Finance123456" },
    viewport: { width: 1366, height: 900 },
    path: "/automation/customer-service-inbox",
    screenshot: "/tmp/company-rag-customer-service-inbox-finance-hidden.png",
    visible: ["概览"],
    hidden: ["客服自动化收件箱", "客户消息录入"],
  });

  console.log(JSON.stringify({
    ok: true,
    results: [customerResult, financeForbidden],
    note: "real browser, real frontend, real API login; no mock/stub/fake",
  }, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

process.exit(0);

async function runInboxCase({ label, account, viewport, path, screenshot, visible, hidden }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await login(page, account);
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);

  for (const text of visible) {
    const count = await page.getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`${label}: expected visible text ${text}`);
    }
  }

  for (const text of hidden) {
    const count = await page.getByText(text, { exact: false }).count();
    if (count > 0) {
      throw new Error(`${label}: unexpected visible text ${text}`);
    }
  }

  const overflow = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    bodyWidth: document.body.scrollWidth,
  }));
  if (overflow.width > overflow.clientWidth + 2 || overflow.bodyWidth > overflow.clientWidth + 2) {
    throw new Error(`${label}: horizontal overflow ${JSON.stringify(overflow)}`);
  }

  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label,
    screenshot,
    overflow,
  };
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_customer_service_inbox_frontend.mjs");
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
