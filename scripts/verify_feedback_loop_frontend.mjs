import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = requirePlaywright();

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const CHROME_EXECUTABLE_PATH = process.env.VERIFY_CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const OPERATIONS_ACCOUNT = {
  username: "operations_demo",
  password: "Operations123456",
};

const ADMIN_ACCOUNT = {
  username: "admin_demo",
  password: "Admin123456",
};

const marker = `feedback-ui-${Date.now()}`;

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const employeeSubmit = await runEmployeeSubmitCase();
  const adminComplete = await runAdminCompleteCase();
  const employeeCompleted = await runEmployeeCompletedCase();

  console.log(JSON.stringify({
    ok: true,
    marker,
    results: [employeeSubmit, adminComplete, employeeCompleted],
    note: "real browser, real frontend login, real feedback API lifecycle; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runEmployeeSubmitCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-feedback-employee-submit.png";
  await page.goto(`${FRONTEND_URL}/feedback`, { waitUntil: "networkidle" });
  await login(page, OPERATIONS_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/feedback`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("反馈改进", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  await mainContent(page).getByPlaceholder("例如：财务工资表导出希望增加部门筛选").fill(`${marker} 运营自动化反馈`);
  await mainContent(page).getByPlaceholder("请写清楚出现在哪个页面").fill(
    "运营希望 AI 能批量读取商品资料并自动生成 Listing 草稿，减少人工复制标题、五点描述和关键词。",
  );
  const createResponse = page.waitForResponse(
    (response) => response.url().includes("/api/feedback") && response.request().method() === "POST" && response.status() === 200,
    { timeout: 30000 },
  );
  await mainContent(page).getByRole("button", { name: "提交反馈" }).click();
  await createResponse;
  await mainContent(page).getByText(marker, { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const overflow = await assertNoHorizontalOverflow(page, "feedback_employee_submit_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();
  return {
    label: "employee_submit_feedback",
    screenshot,
    overflow,
  };
}

async function runAdminCompleteCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-feedback-admin-center.png";
  await page.goto(`${FRONTEND_URL}/feedback-center`, { waitUntil: "networkidle" });
  await login(page, ADMIN_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/feedback-center`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("反馈中心", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await mainContent(page).getByText("待处理", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const row = mainContent(page).locator(".ant-table-row").filter({ hasText: marker }).first();
  await row.waitFor({ state: "visible", timeout: 30000 });
  const completeResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/feedback/")
      && response.url().includes("/complete")
      && response.request().method() === "POST"
      && response.status() === 200,
    { timeout: 30000 },
  );
  await row.locator("button").filter({ hasText: /完\s*成/ }).first().click();
  await completeResponse;
  await row.getByText(/已\s*完\s*成/).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const overflow = await assertNoHorizontalOverflow(page, "feedback_admin_center_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();
  return {
    label: "admin_complete_feedback",
    screenshot,
    overflow,
  };
}

async function runEmployeeCompletedCase() {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const screenshot = "/tmp/company-rag-feedback-employee-mobile.png";
  await page.goto(`${FRONTEND_URL}/feedback`, { waitUntil: "networkidle" });
  await login(page, OPERATIONS_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/feedback`, { waitUntil: "networkidle" });
  await mainContent(page).getByText(marker, { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await mainContent(page).getByText("已完成", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const overflow = await assertNoHorizontalOverflow(page, "feedback_employee_mobile_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();
  return {
    label: "employee_completed_feedback_mobile",
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_feedback_loop_frontend.mjs");
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
