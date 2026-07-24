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
  const adminPage = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await adminPage.goto(`${FRONTEND_URL}/dashboard`, { waitUntil: "networkidle" });
  await login(adminPage, "admin_demo", "Admin123456");

  await adminPage.goto(`${FRONTEND_URL}/dashboard`, { waitUntil: "networkidle" });
  await mainContent(adminPage).getByText("管理员快捷入口", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 20000,
  });
  await assertTextHidden(adminPage, "退款成功");
  await assertTextHidden(adminPage, "最近退款");
  await assertTextHidden(adminPage, "退款审批列表");
  const dashboardOverflow = await assertNoHorizontalOverflow(adminPage, "admin_dashboard");
  await adminPage.screenshot({ path: "/tmp/company-rag-admin-dashboard-no-refunds.png", fullPage: true });

  await adminPage.goto(`${FRONTEND_URL}/approvals`, { waitUntil: "networkidle" });
  await mainContent(adminPage).getByText("概览", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 20000,
  });
  await assertTextHidden(adminPage, "退款审批列表");
  const adminApprovalForbiddenOverflow = await assertNoHorizontalOverflow(adminPage, "admin_approval_forbidden");
  await adminPage.close();

  const customerPage = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await customerPage.goto(`${FRONTEND_URL}/approvals`, { waitUntil: "networkidle" });
  await login(customerPage, "employee_demo", "Employee123456");
  await customerPage.goto(`${FRONTEND_URL}/approvals`, { waitUntil: "networkidle" });
  await mainContent(customerPage).getByText("退款审批列表", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 20000,
  });
  for (const text of ["审批用途", "类型", "原始原因", "通过", "拒绝"]) {
    await assertTextVisible(customerPage, text);
  }
  await assertTextHidden(customerPage, "customer_service_refund");
  const approvalOverflow = await assertNoHorizontalOverflow(customerPage, "customer_service_refund_approvals");
  await customerPage.screenshot({ path: "/tmp/company-rag-customer-service-refund-approvals.png", fullPage: true });
  await customerPage.close();

  console.log(JSON.stringify({
    ok: true,
    dashboardOverflow,
    adminApprovalForbiddenOverflow,
    approvalOverflow,
    screenshots: [
      "/tmp/company-rag-admin-dashboard-no-refunds.png",
      "/tmp/company-rag-customer-service-refund-approvals.png",
    ],
  }, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

process.exit(0);

async function login(page, username, password) {
  const loginButton = page.getByRole("button", { name: "登录" });
  if (await loginButton.count()) {
    await loginButton.first().click();
  }
  const modal = page.locator(".ant-modal").filter({ hasText: "登录 Company RAG Agent" }).first();
  await modal.waitFor({ state: "visible", timeout: 10000 });
  await modal.locator("input").nth(0).fill(username);
  await modal.locator("input").nth(1).fill(password);
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

async function assertTextVisible(page, text) {
  const count = await mainContent(page).getByText(text, { exact: false }).count();
  if (count === 0) {
    throw new Error(`expected visible text: ${text}`);
  }
}

async function assertTextHidden(page, text) {
  const count = await mainContent(page).getByText(text, { exact: false }).count();
  if (count > 0) {
    throw new Error(`unexpected visible text: ${text}`);
  }
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_admin_approval_ui_frontend.mjs");
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
