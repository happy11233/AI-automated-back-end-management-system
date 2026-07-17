import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = requirePlaywright();

const FRONTEND_URL = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
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
  const adminDesktop = await runWorkflowCase({
    label: "admin_ai_workflows_desktop",
    account: ACCOUNTS.admin,
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-ai-workflows-admin-desktop.png",
    visible: ["AI 工作流中心", "运营 Listing 上架准备", "客服退款售后处理", "客服消息自动化闭环", "财务 Excel 结算整理", "可见工作流"],
    hidden: ["Bearer abc.def.ghi", "api_key=secret-value", "buyer@example.com", "13812345678"],
    openDetailText: "客服退款售后处理",
  });

  const operationsDesktop = await runWorkflowCase({
    label: "operations_ai_workflows_desktop",
    account: ACCOUNTS.operations,
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-ai-workflows-operations-desktop.png",
    visible: ["AI 工作流中心", "运营 Listing 上架准备", "运营竞品分析", "运行工作流"],
    hidden: ["客服退款售后处理", "财务工资统计", "财务 Excel 结算整理"],
    openDetailText: "运营竞品分析",
  });

  const financeMobile = await runWorkflowCase({
    label: "finance_ai_workflows_mobile",
    account: ACCOUNTS.finance,
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-ai-workflows-finance-mobile.png",
    visible: ["AI 工作流中心", "财务报表分析", "财务工资统计", "财务 Excel 结算整理"],
    hidden: ["运营竞品分析", "客服退款售后处理"],
    openDetailText: "财务 Excel 结算整理",
  });

  const runResult = await runOperationsWorkflow();

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, operationsDesktop, financeMobile, runResult],
    note: "real browser, real frontend, real API login/run; no mock/stub/fake",
  }, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

process.exit(0);

async function runWorkflowCase({ label, account, viewport, screenshot, visible, hidden, openDetailText }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}/ai-workflows`, { waitUntil: "networkidle" });
  await login(page, account);

  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes("/api/ai-workflows") && response.status() === 200,
      { timeout: 30000 },
    ),
    page.goto(`${FRONTEND_URL}/ai-workflows`, { waitUntil: "networkidle" }),
  ]);
  await page.getByText("AI 工作流中心", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.waitForTimeout(800);

  for (const text of visible) {
    const count = await page.getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`${label}: expected visible text ${text}`);
    }
  }

  for (const text of hidden) {
    const count = await page.getByText(text, { exact: false }).count();
    if (count > 0) {
      throw new Error(`${label}: unexpected text ${text}`);
    }
  }

  await openWorkflowDetail(page, openDetailText);
  await page.getByText("步骤链路", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await page.getByText("工具、ERP 与写回", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await page.locator(".ant-modal-footer button").first().click();

  const overflow = await assertNoHorizontalOverflow(page, label);
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label,
    screenshot,
    overflow,
  };
}

async function runOperationsWorkflow() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await page.goto(`${FRONTEND_URL}/ai-workflows`, { waitUntil: "networkidle" });
  await login(page, ACCOUNTS.operations);
  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes("/api/ai-workflows") && response.status() === 200,
      { timeout: 30000 },
    ),
    page.goto(`${FRONTEND_URL}/ai-workflows`, { waitUntil: "networkidle" }),
  ]);

  const card = page.locator(".aiWorkflowCard", { hasText: "运营竞品分析" }).first();
  await card.waitFor({ state: "visible", timeout: 30000 });
  await card.locator("textarea").fill(
    "竞品价格 19.99 USD，卖点是保温和防漏，差评是杯盖漏水；请给出差异化分析。Bearer abc.def.ghi api_key=secret-value buyer@example.com 13812345678",
  );
  const runResponse = page.waitForResponse(
    (response) => response.url().includes("/api/ai-workflows/operations_competitor_analysis/run") && response.status() === 200,
    { timeout: 180000 },
  );
  await card.getByRole("button", { name: "运行运营竞品分析" }).click();
  await runResponse;
  await page.getByText("最近运行结果", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.getByText("ai_generate_decision", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const resultPanelText = await page.locator(".ant-pro-card", { hasText: "最近运行结果" }).last().innerText();
  for (const text of ["Bearer abc.def.ghi", "api_key=secret-value", "buyer@example.com", "13812345678"]) {
    if (resultPanelText.includes(text)) {
      throw new Error(`operations_run: leaked sensitive text in result panel ${text}`);
    }
  }

  const overflow = await assertNoHorizontalOverflow(page, "operations_ai_workflow_run");
  const screenshot = "/tmp/company-rag-ai-workflows-operations-run.png";
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label: "operations_ai_workflow_run",
    screenshot,
    overflow,
  };
}

async function openWorkflowDetail(page, text) {
  const card = page.locator(".aiWorkflowCard", { hasText: text }).first();
  await card.scrollIntoViewIfNeeded();
  await card.locator("button").first().click({ timeout: 15000 });
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_ai_workflows_frontend.mjs");
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
