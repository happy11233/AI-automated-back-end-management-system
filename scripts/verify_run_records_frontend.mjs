import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = requirePlaywright();

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const API_BASE_URL = (process.env.VERIFY_API_BASE_URL || "http://127.0.0.1:8001").replace(/\/$/, "");
const CHROME_EXECUTABLE_PATH = process.env.VERIFY_CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const ACCOUNTS = {
  admin: {
    username: "admin_demo",
    password: "Admin123456",
  },
  operations: {
    username: "operations_demo",
    password: "Operations123456",
  },
  customer_service: {
    username: "employee_demo",
    password: "Employee123456",
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
  const adminDesktop = await runAdminRunRecordCase();
  const forbiddenCases = [];
  for (const [name, account] of Object.entries(ACCOUNTS).filter(([name]) => name !== "admin")) {
    forbiddenCases.push(await runForbiddenRouteCase({
      label: `${name}_run_records_forbidden`,
      account,
      path: "/run-records",
      forbiddenText: "运行记录",
    }));
  }
  const apiForbidden = await verifyApiForbidden("/run-records?limit=1");

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, ...forbiddenCases],
    apiForbidden,
    note: "real browser, real frontend, real API login; run records are admin-only; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runAdminRunRecordCase() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  const screenshot = "/tmp/company-rag-run-records-admin-desktop.png";
  try {
    await loginAtPath(page, ACCOUNTS.admin, "/run-records");
    await Promise.all([
      page.waitForResponse(
        (response) => response.url().includes("/api/run-records") && response.status() === 200,
        { timeout: 30000 },
      ),
      page.goto(`${FRONTEND_URL}/run-records`, { waitUntil: "networkidle" }),
    ]);
    await page.getByText("运行记录", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 30000,
    });
    await page.waitForTimeout(800);

    for (const text of ["运行记录", "记录总数", "全部岗位", "详情"]) {
      const count = await page.getByText(text, { exact: false }).count();
      if (count === 0) {
        throw new Error(`admin_run_records_desktop: expected visible text ${text}`);
      }
    }

    const detailResponse = page.waitForResponse(
      (response) => /\/api\/run-records\/[0-9a-f-]+/i.test(response.url()) && response.status() === 200,
      { timeout: 15000 },
    );
    const detailButtons = page.locator(".ant-table-cell-fix-right button", { hasText: "详情" });
    let buttonCount = await detailButtons.count();
    let clicked = false;
    for (let index = 0; index < buttonCount; index += 1) {
      const button = detailButtons.nth(index);
      if (await button.isVisible()) {
        await button.click();
        clicked = true;
        break;
      }
    }
    if (!clicked) {
      const fallbackButtons = page.getByRole("button", { name: "详情" });
      buttonCount = await fallbackButtons.count();
      for (let index = 0; index < buttonCount; index += 1) {
        const button = fallbackButtons.nth(index);
        if (await button.isVisible()) {
          await button.click({ force: true });
          clicked = true;
          break;
        }
      }
    }
    if (!clicked) {
      throw new Error("admin_run_records_desktop: no visible detail button");
    }
    await detailResponse;
    await page.getByRole("tab", { name: "基础信息" }).waitFor({
      state: "visible",
      timeout: 15000,
    });
    for (const text of ["流程 Key", "流程版本", "发布指针", "执行来源"]) {
      await page.getByText(text, { exact: false }).first().waitFor({
        state: "visible",
        timeout: 15000,
      });
    }
    await page.getByRole("tab", { name: "输入输出" }).click();
    await page.getByText("输入摘要", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await page.getByRole("tab", { name: /执行步骤/ }).click();
    await page.getByText("Provider", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });

    const overflow = await assertNoHorizontalOverflow(page, "admin_run_records_desktop");
    await page.screenshot({ path: screenshot, fullPage: true });

    return {
      label: "admin_run_records_desktop",
      screenshot,
      overflow,
    };
  } finally {
    await context.close();
  }
}

async function runForbiddenRouteCase({ label, account, path, forbiddenText }) {
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await context.newPage();
  try {
    await loginAtPath(page, account, path);
    await page.waitForURL("**/dashboard", { timeout: 15000 });
    await page.getByText("概览", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await page.waitForTimeout(600);

    const forbiddenCount = await mainContent(page).getByText(forbiddenText, { exact: false }).count();
    if (forbiddenCount > 0) {
      throw new Error(`${label}: forbidden page text still visible`);
    }

    const overflow = await assertNoHorizontalOverflow(page, label);
    return {
      label,
      currentUrl: page.url(),
      overflow,
    };
  } finally {
    await context.close();
  }
}

async function verifyApiForbidden(path) {
  const results = [];
  for (const [name, account] of Object.entries(ACCOUNTS).filter(([name]) => name !== "admin")) {
    const token = await loginByApi(account);
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (response.status !== 403) {
      throw new Error(`${name}: expected ${path} to return 403, got ${response.status}: ${await response.text()}`);
    }
    results.push({ account: name, status: response.status });
  }
  return results;
}

async function loginAtPath(page, account, path) {
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    localStorage.removeItem("position");
    localStorage.removeItem("allowed_ai_app_ids");
  });
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /登录|未登录/ }).first().click();
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

async function loginByApi(account) {
  const body = new URLSearchParams();
  body.set("username", account.username);
  body.set("password", account.password);
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  if (response.status !== 200) {
    throw new Error(`login failed for ${account.username}: ${response.status} ${await response.text()}`);
  }
  return (await response.json()).access_token;
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_run_records_frontend.mjs");
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
