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
};

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const desktop = await runErpRecordDetailCase({
    label: "erp_record_detail_desktop",
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-erp-record-detail-desktop.png",
  });

  const mobile = await runErpRecordDetailCase({
    label: "erp_record_detail_mobile",
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-erp-record-detail-mobile.png",
  });

  console.log(JSON.stringify({
    ok: true,
    results: [desktop, mobile],
    note: "real browser, real frontend, real API login and ERP record detail; no mock/stub/fake",
  }, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

process.exit(0);

async function runErpRecordDetailCase({ label, viewport, screenshot }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}/dashboard`, { waitUntil: "networkidle" });
  await login(page, ACCOUNTS.operations);
  await page.goto(`${FRONTEND_URL}/dashboard`, { waitUntil: "networkidle" });
  await page.getByText("岗位数据概览", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.getByText("销售订单", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });
  await page.waitForTimeout(800);

  const detailButton = page.locator(".dashboardOverviewCard")
    .filter({ hasText: "销售订单" })
    .first()
    .getByRole("button", { name: /ERP 详情/ })
    .first();
  await detailButton.waitFor({
    state: "visible",
    timeout: 15000,
  });

  const detailResponse = page.waitForResponse(
    (response) => response.url().includes("/api/erp/records/") && response.status() === 200,
    { timeout: 30000 },
  );
  await detailButton.click();
  await detailResponse;

  const modal = page.locator(".ant-modal").filter({ hasText: "ERP 记录详情 /" }).first();
  await modal.waitFor({
    state: "visible",
    timeout: 15000,
  });
  await modal.getByRole("tab", { name: "基础信息" }).waitFor({
    state: "visible",
    timeout: 15000,
  });
  await modal.getByText("查询说明", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  await openDetailTab(modal, "业务字段");
  await modal.getByText("字段", { exact: true }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await modal.getByText("值", { exact: true }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  await openDetailTab(modal, "原始数据");
  await modal.getByText("原始返回数据", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await modal.getByText("record_id", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const overflow = await assertNoHorizontalOverflow(page, label);
  await page.screenshot({ path: screenshot, fullPage: true });
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_erp_record_detail_frontend.mjs");
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
