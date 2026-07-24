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
    visible: ["AI 工作流中心", "运营 Listing 上架准备", "客服退款售后处理", "客服消息自动化闭环", "财务 Excel 生成", "财务对账自动化", "可见工作流"],
    hidden: ["Bearer abc.def.ghi", "api_key=secret-value", "buyer@example.com", "13812345678"],
    openDetailText: "客服退款售后处理",
  });

  const operationsDesktop = await runWorkflowCase({
    label: "operations_ai_workflows_desktop",
    account: ACCOUNTS.operations,
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-ai-workflows-operations-desktop.png",
    visible: ["AI 工作流中心", "运营 Listing 上架准备", "运营竞品分析", "运行工作流"],
    hidden: ["客服退款售后处理", "财务工资统计", "财务 Excel 生成", "财务对账自动化"],
    openDetailText: "运营竞品分析",
  });

  const financeMobile = await runWorkflowCase({
    label: "finance_ai_workflows_mobile",
    account: ACCOUNTS.finance,
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-ai-workflows-finance-mobile.png",
    visible: ["AI 工作流中心", "财务报表分析", "财务工资统计", "财务 Excel 生成", "财务对账自动化"],
    hidden: ["运营竞品分析", "客服退款售后处理"],
    openDetailText: "财务 Excel 生成",
  });

  const financeReportDetail = await runFocusedWorkflowCase({
    label: "finance_report_analysis_focused",
    account: ACCOUNTS.finance,
    path: "/ai-workflows/finance-report-analysis",
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-ai-workflows-finance-report-focused.png",
    visible: ["财务报表分析", "业务场景", "输出与审批", "步骤链路", "工具与 ERP", "运行区", "运行工作流"],
    hidden: ["运营竞品分析", "客服退款售后处理"],
  });

  const financeExcelUpload = await runAutomationRouteCase({
    label: "finance_excel_upload_focused",
    account: ACCOUNTS.finance,
    path: "/automation/finance/excel-transform",
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-automation-finance-excel-upload.png",
    visible: ["财务 AI 自动化", "财务 Excel 生成", "选择或上传 Excel", "选择财务 ERP 表", "生成并下载 Excel"],
    hidden: ["分析财务报表", "统计工资", "生成订单利润表"],
  });

  const financeReconciliation = await runAutomationRouteCase({
    label: "finance_reconciliation_focused",
    account: ACCOUNTS.finance,
    path: "/automation/finance/reconciliation",
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-automation-finance-reconciliation.png",
    visible: ["财务 AI 自动化", "财务对账自动化", "选择对账 Excel", "生成订单利润表"],
    hidden: ["选择或上传 Excel", "分析财务报表", "统计工资"],
  });

  const runResult = await runOperationsWorkflow();

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, operationsDesktop, financeMobile, financeReportDetail, financeExcelUpload, financeReconciliation, runResult],
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
  const detailModal = page.locator(".ant-modal").filter({ hasText: "AI 工作流 /" }).first();
  await detailModal.getByRole("tab", { name: "基础信息" }).waitFor({
    state: "visible",
    timeout: 15000,
  });
  await openDetailTab(detailModal, "场景");
  await detailModal.getByText("业务场景", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await detailModal.getByText("输出与审批", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await openDetailTab(detailModal, "步骤");
  await detailModal.getByText("阶段", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await openDetailTab(detailModal, "资源写回");
  await detailModal.getByText("允许工具", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await detailModal.getByText("写回目标", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const overflow = await assertNoHorizontalOverflow(page, label);
  await page.screenshot({ path: screenshot, fullPage: true });
  await detailModal.locator(".ant-modal-footer button").first().click();
  await detailModal.waitFor({ state: "hidden", timeout: 10000 });
  await page.close();

  return {
    label,
    screenshot,
    overflow,
  };
}

async function openDetailTab(modal, name) {
  const exactTab = modal.getByRole("tab", { name });
  if (await exactTab.count()) {
    await exactTab.click({ force: true });
    await modal.page().waitForTimeout(300);
    return;
  }

  const tab = modal.locator(".ant-tabs-tab", { hasText: name }).first();
  await tab.click({ force: true });
  await modal.page().waitForTimeout(300);
}

async function runFocusedWorkflowCase({ label, account, path, viewport, screenshot, visible, hidden }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await login(page, account);

  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes("/api/ai-workflows") && response.status() === 200,
      { timeout: 30000 },
    ),
    page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" }),
  ]);

  for (const text of visible) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`${label}: expected visible text ${text}`);
    }
  }

  for (const text of hidden) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count > 0) {
      throw new Error(`${label}: unexpected text ${text}`);
    }
  }

  const overlap = await assertNoVisibleOverlap(page, label);
  const overflow = await assertNoHorizontalOverflow(page, label);
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label,
    screenshot,
    overflow,
    overlap,
  };
}

async function runAutomationRouteCase({ label, account, path, viewport, screenshot, visible, hidden }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await login(page, account);
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);

  for (const text of visible) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`${label}: expected visible text ${text}`);
    }
  }

  for (const text of hidden) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count > 0) {
      throw new Error(`${label}: unexpected text ${text}`);
    }
  }

  const overlap = await assertNoVisibleOverlap(page, label);
  const overflow = await assertNoHorizontalOverflow(page, label);
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  return {
    label,
    screenshot,
    overflow,
    overlap,
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

async function assertNoVisibleOverlap(page, label) {
  const collisions = await page.evaluate(() => {
    const selectors = [
      ".aiWorkflowFocusedHero",
      ".aiWorkflowFocusedMetricGrid > div",
      ".ant-pro-card",
      ".automationDirectoryCard",
      ".automationInfoCard",
      ".automationTaskCard",
      ".financeUploadDragger",
    ];
    const elements = selectors
      .flatMap((selector) => Array.from(document.querySelectorAll(selector)))
      .filter((element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== "none"
          && style.visibility !== "hidden"
          && rect.width > 0
          && rect.height > 0;
      })
      .map((element, index) => {
        const rect = element.getBoundingClientRect();
        return {
          index,
          element,
          className: element.className,
          text: (element.textContent || "").trim().slice(0, 80),
          left: rect.left,
          top: rect.top,
          right: rect.right,
          bottom: rect.bottom,
          width: rect.width,
          height: rect.height,
        };
      });

    const results = [];
    for (let i = 0; i < elements.length; i += 1) {
      for (let j = i + 1; j < elements.length; j += 1) {
        const a = elements[i];
        const b = elements[j];
        if (a.element.contains(b.element) || b.element.contains(a.element)) {
          continue;
        }
        const xOverlap = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const yOverlap = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        const area = xOverlap * yOverlap;
        const minArea = Math.min(a.width * a.height, b.width * b.height);
        if (area > 0 && area / Math.max(minArea, 1) > 0.88) {
          const { element: _aElement, ...aInfo } = a;
          const { element: _bElement, ...bInfo } = b;
          results.push({ a: aInfo, b: bInfo, ratio: area / Math.max(minArea, 1) });
        }
      }
    }
    return results;
  });

  if (collisions.length > 0) {
    throw new Error(`${label}: visible layout overlap ${JSON.stringify(collisions.slice(0, 3))}`);
  }

  return collisions;
}

function mainContent(page) {
  return page.locator(".ant-pro-page-container").first();
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
