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
  const financeReportPage = await runFinanceReportPageCase();
  const fileDownloadsPage = await runFileDownloadsPageCase();

  console.log(JSON.stringify({
    ok: true,
    results: [financeReportPage, fileDownloadsPage],
    note: "real browser, real frontend login, real generated file list API; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runFinanceReportPageCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-finance-report-analysis-upload.png";
  await page.goto(`${FRONTEND_URL}/automation/finance/report-analysis`, { waitUntil: "networkidle" });
  await login(page, FINANCE_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/automation/finance/report-analysis`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("分析财务报表", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  for (const text of ["财务 AI 自动化", "选择财务报表文件", "Word 报告", "Excel 报告", "生成分析报告"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`finance_report_page: expected visible text ${text}`);
    }
  }

  const buttonDisabled = await page.getByRole("button", { name: "生成分析报告" }).isDisabled();
  if (buttonDisabled) {
    await mainContent(page).locator("textarea").fill("7月销售额128900，退款3280，广告费14500，净利润37120，请分析异常。");
  }
  const enabled = await page.getByRole("button", { name: "生成分析报告" }).isEnabled();
  if (!enabled) {
    throw new Error("finance_report_page: manual input should enable generation button");
  }

  const overflow = await assertNoHorizontalOverflow(page, "finance_report_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();
  return {
    label: "finance_report_analysis_upload_page",
    screenshot,
    overflow,
  };
}

async function runFileDownloadsPageCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-file-downloads-finance.png";
  await page.goto(`${FRONTEND_URL}/files`, { waitUntil: "networkidle" });
  await login(page, FINANCE_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/files`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("文件下载", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  for (const text of ["可下载文件", "保存期", "近30天", "全部类型", "查询", "下载", "业务摘要"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`file_downloads_page: expected visible text ${text}`);
    }
  }

  await page.getByPlaceholder("搜索文件、应用").fill("finance_report_analysis");
  await page.getByRole("button", { name: "查询" }).click();
  await page.waitForTimeout(1200);
  const hasFinanceReport = await mainContent(page).getByText("finance_report_analysis", { exact: false }).count();
  if (hasFinanceReport === 0) {
    throw new Error("file_downloads_page: expected generated finance report file in list");
  }
  for (const text of ["财务报告", "源文件", "解析文档"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`file_downloads_page: expected business summary text ${text}`);
    }
  }
  for (const hiddenText of ["metadata", "raw JSON", "request_payload", "response_payload"]) {
    const count = await mainContent(page).getByText(hiddenText, { exact: false }).count();
    if (count > 0) {
      throw new Error(`file_downloads_page: unexpected technical text ${hiddenText}`);
    }
  }

  const overflow = await assertNoHorizontalOverflow(page, "file_downloads_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();
  return {
    label: "file_downloads_finance_page",
    screenshot,
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_generated_files_frontend.mjs");
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
