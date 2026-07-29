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
  const salaryPage = await runSalaryPageCase();
  const chatPage = await runSalaryChatCase();

  console.log(JSON.stringify({
    ok: true,
    results: [salaryPage, chatPage],
    note: "real browser, real frontend login, real salary export API/chat stream, real download event; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runSalaryPageCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-finance-salary-export-page.png";
  await page.goto(`${FRONTEND_URL}/automation/finance/salary-summary`, { waitUntil: "networkidle" });
  await login(page, FINANCE_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/automation/finance/salary-summary`, { waitUntil: "networkidle" });
  await page.getByText("统计工资", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  for (const text of ["财务 AI 自动化", "统计工资", "把这个月所有员工的工资表发我", "生成工资 Excel", "Salary Slip"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`salary_page: expected visible text ${text}`);
    }
  }

  const downloadPromise = page.waitForEvent("download", { timeout: 90000 });
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("/api/automation/finance/salary-export") && response.status() === 200,
    { timeout: 90000 },
  );
  await page.getByRole("button", { name: "生成工资 Excel" }).click();
  const [download, response] = await Promise.all([downloadPromise, responsePromise]);
  await page.getByText("已识别为 finance_salary_export", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.getByText("生成 5 名员工工资表", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const overflow = await assertNoHorizontalOverflow(page, "salary_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  const suggestedFilename = download.suggestedFilename();
  await page.close();

  return {
    label: "finance_salary_export_page",
    screenshot,
    status: response.status(),
    suggestedFilename,
    overflow,
  };
}

async function runSalaryChatCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-finance-salary-chat.png";
  await page.goto(`${FRONTEND_URL}/chat`, { waitUntil: "networkidle" });
  await login(page, FINANCE_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/chat`, { waitUntil: "networkidle" });
  await page.getByText("会话 ID", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  await page.locator(".chatComposer textarea").fill("把这个月所有员工的工资表发我");
  const responsePromise = page.waitForResponse(
    (response) => response.url().includes("/api/chat/stream") && response.status() === 200,
    { timeout: 90000 },
  );
  await page.locator(".chatComposer button.ant-btn-primary").click();
  await responsePromise;
  await page.getByText("工资表自动导出", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 90000,
  });
  await page.getByText("附件：finance_salary_202607.xlsx", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 90000,
  });
  await page.getByRole("button", { name: "下载 Excel" }).waitFor({
    state: "visible",
    timeout: 30000,
  });

  const overflow = await assertNoHorizontalOverflow(page, "salary_chat");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label: "finance_salary_chat_attachment",
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
  const modal = page.locator(".ant-modal").filter({ hasText: /登录/ }).first();
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_finance_salary_export_frontend.mjs");
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
