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
  const adminDesktop = await runRunRecordCase({
    label: "admin_run_records_desktop",
    account: ACCOUNTS.admin,
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-run-records-admin-desktop.png",
    visible: ["运行记录", "财务 Excel 生成", "财务对账自动化", "客服岗位无权查询 ERP 资源", "详情"],
    hidden: [],
    openDetail: true,
  });

  const financeDesktop = await runRunRecordCase({
    label: "finance_run_records_desktop",
    account: ACCOUNTS.finance,
    viewport: { width: 1366, height: 900 },
    screenshot: "/tmp/company-rag-run-records-finance-desktop.png",
    visible: ["运行记录", "财务 Excel 生成", "财务对账自动化", "财务 AI 对话"],
    hidden: ["运营 ERP 查询", "客服岗位无权查询 ERP 资源"],
    openDetail: true,
  });

  const financeMobile = await runRunRecordCase({
    label: "finance_run_records_mobile",
    account: ACCOUNTS.finance,
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-run-records-finance-mobile.png",
    visible: ["运行记录", "财务"],
    hidden: ["客服岗位无权查询 ERP 资源"],
    openDetail: false,
  });

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, financeDesktop, financeMobile],
    note: "real browser, real frontend, real API login; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runRunRecordCase({ label, account, viewport, screenshot, visible, hidden, openDetail }) {
  const page = await browser.newPage({ viewport });
  await page.goto(`${FRONTEND_URL}/run-records`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /登录/ }).click();
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
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1200);

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

  if (openDetail) {
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
      throw new Error(`${label}: no visible detail button`);
    }
    await detailResponse;
    await page.getByText("输入输出摘要", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await page.getByText("执行步骤", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
  }

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
