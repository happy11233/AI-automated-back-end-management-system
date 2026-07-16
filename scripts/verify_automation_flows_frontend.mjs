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
  const adminDesktop = await runFlowCase({
    label: "admin_flow_configs_desktop",
    account: ACCOUNTS.admin,
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-automation-flows-admin-desktop.png",
    visible: ["自动化流程配置", "生成 Listing", "运营 ERP 查询", "详情"],
    hidden: [],
    openDetailText: "生成 Listing",
  });

  const operationsDesktop = await runFlowCase({
    label: "operations_flow_configs_desktop",
    account: ACCOUNTS.operations,
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-automation-flows-operations-desktop.png",
    visible: ["自动化流程配置", "生成 Listing", "竞品分析", "运营 ERP 查询"],
    hidden: ["退款售后话术", "财务 Excel 生成", "分析财务报表"],
    openDetailText: "竞品分析",
  });

  const financeMobile = await runFlowCase({
    label: "finance_flow_configs_mobile",
    account: ACCOUNTS.finance,
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-automation-flows-finance-mobile.png",
    visible: ["自动化流程配置", "财务 Excel 生成", "分析财务报表", "财务 ERP 查询"],
    hidden: ["生成 Listing", "退款售后话术"],
    openDetailText: "财务 Excel 生成",
  });

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, operationsDesktop, financeMobile],
    note: "real browser, real frontend, real API login; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runFlowCase({ label, account, viewport, screenshot, visible, hidden, openDetailText }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}/automation-flows`, { waitUntil: "networkidle" });
  await login(page, account);

  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes("/api/automation-flows") && response.status() === 200,
      { timeout: 30000 },
    ),
    page.goto(`${FRONTEND_URL}/automation-flows`, { waitUntil: "networkidle" }),
  ]);
  await page.getByText("自动化流程配置", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.waitForLoadState("networkidle");
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
      throw new Error(`${label}: expected hidden text ${text}`);
    }
  }

  for (const action of ["保存", "编辑", "删除"]) {
    const count = await page.getByRole("button", { name: action }).count();
    if (count > 0) {
      throw new Error(`${label}: unexpected writable action ${action}`);
    }
  }

  const detailResponse = page.waitForResponse(
    (response) => response.url().includes("/api/automation-flows/") && response.status() === 200,
    { timeout: 15000 },
  );
  const targetRow = page.locator(".ant-table-row", { hasText: openDetailText }).first();
  await targetRow.getByRole("button", { name: "详情" }).click();
  await detailResponse;
  await page.getByText("输入 Schema", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await page.getByText("Prompt 与模型", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await page.getByText("权限、工具与 ERP 资源", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await page.getByText("执行步骤", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

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
  await page.getByRole("button", { name: "登录" }).click();
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_automation_flows_frontend.mjs");
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
