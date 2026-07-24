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
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const screenshot = "/tmp/company-rag-user-settings-finance.png";
  await page.goto(`${FRONTEND_URL}/settings`, { waitUntil: "networkidle" });
  await login(page, FINANCE_ACCOUNT);
  await page.goto(`${FRONTEND_URL}/settings`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("用户设置", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  for (const text of ["账号资料", "账号不可修改", "修改密码", "保存资料", "当前密码"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`user_settings_page: expected visible text ${text}`);
    }
  }

  const disabledUsernameCount = await mainContent(page).locator("input[disabled][value='finance_demo']").count();
  if (disabledUsernameCount === 0) {
    throw new Error("user_settings_page: username input should be disabled");
  }

  const profileResponse = page.waitForResponse(
    (response) => response.url().includes("/api/settings/me/profile") && response.status() === 200,
    { timeout: 30000 },
  );
  await mainContent(page).getByPlaceholder("例如：财务主管").fill("财务前端验证用户");
  await mainContent(page).getByPlaceholder("例如：finance@example.com").fill("finance-frontend@example.com");
  await mainContent(page).getByRole("button", { name: "保存资料" }).click();
  await profileResponse;
  await mainContent(page).getByText("finance-frontend@example.com", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 10000,
  });

  const overflow = await assertNoHorizontalOverflow(page, "user_settings_page");
  await page.screenshot({ path: screenshot, fullPage: true });
  await page.close();

  console.log(JSON.stringify({
    ok: true,
    screenshot,
    overflow,
    note: "real browser, real frontend login, real settings API; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_user_settings_frontend.mjs");
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
