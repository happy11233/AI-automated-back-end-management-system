import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = requirePlaywright();

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const CHROME_EXECUTABLE_PATH = process.env.VERIFY_CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const ACCOUNTS = {
  operations: {
    username: "operations_demo",
    password: "Operations123456",
  },
  finance: {
    username: "finance_demo",
    password: "Finance123456",
  },
};

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const operationsDesktop = await runLoopPageCase({
    label: "operations_business_action_loop_desktop",
    account: ACCOUNTS.operations,
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-business-action-loop-operations-desktop.png",
  });

  const operationsMobile = await runLoopPageCase({
    label: "operations_business_action_loop_mobile",
    account: ACCOUNTS.operations,
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-business-action-loop-operations-mobile.png",
  });

  const financeForbidden = await runFinanceForbiddenCase();

  console.log(JSON.stringify({
    ok: true,
    results: [operationsDesktop, operationsMobile, financeForbidden],
    note: "real browser, real frontend, real API login/list; no mock/stub/fake",
  }, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

process.exit(0);

async function runLoopPageCase({ label, account, viewport, screenshot }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}/business-action-loop`, { waitUntil: "networkidle" });
  await login(page, account);

  await page.goto(`${FRONTEND_URL}/business-action-loop`, { waitUntil: "networkidle" });

  await mainContent(page).getByText("业务动作闭环", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.waitForTimeout(800);

  for (const text of ["闭环总数", "待审核", "外部执行中", "已完成", "未读通知", "草稿审核", "执行任务", "闭环进度", "审核", "完成"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`${label}: expected visible text ${text}`);
    }
  }

  for (const hiddenText of ["callback_token", "business-loop-secret", "Authorization: Bearer", "request_payload", "response_payload"]) {
    const count = await mainContent(page).getByText(hiddenText, { exact: false }).count();
    if (count > 0) {
      throw new Error(`${label}: unexpected sensitive text ${hiddenText}`);
    }
  }

  const overflow = await assertNoHorizontalOverflow(page, label);
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label,
    screenshot,
    overflow,
  };
}

async function runFinanceForbiddenCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await page.goto(`${FRONTEND_URL}/business-action-loop`, { waitUntil: "networkidle" });
  await login(page, ACCOUNTS.finance);
  await page.goto(`${FRONTEND_URL}/business-action-loop`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("概览", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const forbiddenTextCount = await mainContent(page).getByText("业务动作闭环", { exact: false }).count();
  if (forbiddenTextCount > 0) {
    throw new Error("finance user should not see business action loop page");
  }

  const overflow = await assertNoHorizontalOverflow(page, "finance_business_action_loop_forbidden");
  await page.close();
  return {
    label: "finance_business_action_loop_forbidden",
    currentUrl: page.url(),
    overflow,
  };
}

async function login(page, account) {
  await page.evaluate(() => window.localStorage.clear());
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
    (response) => response.url().includes("/auth/login"),
    { timeout: 30000 },
  );
  await page.locator(".ant-modal-footer .ant-btn-primary").click();
  const response = await loginResponse;
  if (response.status() !== 200) {
    throw new Error(`login failed for ${account.username}: HTTP ${response.status()}`);
  }
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_business_action_loop_frontend.mjs");
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
