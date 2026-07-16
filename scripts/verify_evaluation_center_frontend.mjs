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
};

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const adminDesktop = await runEvaluationCase({
    label: "admin_evaluation_center_desktop",
    account: ACCOUNTS.admin,
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-evaluation-center-admin-desktop.png",
    visible: ["AI 评测中心", "评测集资产", "RAG 基础问答评测集", "公司规则类 RAG 大样本评测集", "真实回归套件", "发布闸门"],
    hidden: ["content_preview", "expected_evidence", "top_chunks", "Authorization", "api_secret"],
  });

  const adminMobile = await runEvaluationCase({
    label: "admin_evaluation_center_mobile",
    account: ACCOUNTS.admin,
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-evaluation-center-admin-mobile.png",
    visible: ["AI 评测中心", "评测集", "样本数", "评测集资产"],
    hidden: ["content_preview", "expected_evidence", "top_chunks", "Authorization", "api_secret"],
  });

  const employeeForbidden = await runEmployeeForbiddenCase();

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, adminMobile, employeeForbidden],
    note: "real browser, real frontend, real API login; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runEvaluationCase({ label, account, viewport, screenshot, visible, hidden }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}/evaluation-center`, { waitUntil: "networkidle" });
  await login(page, account);

  await Promise.all([
    page.waitForResponse(
      (response) => response.url().includes("/api/evaluation-center") && response.status() === 200,
      { timeout: 30000 },
    ),
    page.goto(`${FRONTEND_URL}/evaluation-center`, { waitUntil: "networkidle" }),
  ]);
  await page.getByText("AI 评测中心", { exact: false }).first().waitFor({
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
      throw new Error(`${label}: unexpected sensitive text ${text}`);
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

async function runEmployeeForbiddenCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await page.goto(`${FRONTEND_URL}/evaluation-center`, { waitUntil: "networkidle" });
  await login(page, ACCOUNTS.operations);
  await page.goto(`${FRONTEND_URL}/evaluation-center`, { waitUntil: "networkidle" });
  await page.getByText("概览", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const evaluationTextCount = await page.getByText("AI 评测中心", { exact: false }).count();
  if (evaluationTextCount > 0) {
    throw new Error("employee should not see evaluation center");
  }

  const overflow = await assertNoHorizontalOverflow(page, "employee_evaluation_center_forbidden");
  await page.close();

  return {
    label: "employee_evaluation_center_forbidden",
    currentUrl: page.url(),
    overflow,
  };
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_evaluation_center_frontend.mjs");
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
