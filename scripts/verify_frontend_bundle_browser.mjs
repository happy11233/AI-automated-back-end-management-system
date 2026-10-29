import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, join } from "node:path";
import { gzipSync } from "node:zlib";

const require = createRequire(import.meta.url);
const npx = join(homedir(), ".npm/_npx");
let playwright;
for (const candidate of [process.env.PLAYWRIGHT_MODULE_PATH, "playwright", ...(existsSync(npx) ? readdirSync(npx).map((name) => join(npx, name, "node_modules/playwright")) : [])].filter(Boolean)) {
  try {
    const runtime = require(candidate);
    if (existsSync(runtime.chromium.executablePath())) { playwright = runtime; break; }
  } catch { /* Check the next installed runtime. */ }
}
assert(playwright, "Installed Playwright Chromium required");
const base = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5174").replace(/\/$/, "");
const api = process.env.VERIFY_API_BASE_URL || "http://127.0.0.1:8001";
const output = "data/verification/frontend-bundle";
mkdirSync(output, { recursive: true });
const errors = [], failedAssets = [], failedApiRequests = [], checks = [], measurements = {};
const manifest = JSON.parse(readFileSync("frontend/dist/.vite/manifest.json", "utf8"));
const assetFor = (key) => basename(manifest[key].file);
const browser = await playwright.chromium.launch({ headless: true, args: ["--no-proxy-server"] });
let context;
let activePage;

function track(page) {
  activePage = page;
  page.setDefaultTimeout(30000);
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.origin === base && url.pathname.startsWith("/assets/") && response.status() >= 400) {
      failedAssets.push({ path: url.pathname, status: response.status() });
    }
    if (url.origin === base && url.pathname.startsWith("/api/") && response.status() >= 400) {
      failedApiRequests.push({ path: url.pathname, status: response.status() });
    }
  });
  page.on("requestfailed", (request) => {
    const url = new URL(request.url());
    if (url.origin === base && url.pathname.startsWith("/assets/")) failedAssets.push({ path: url.pathname, failure: request.failure()?.errorText });
  });
}

async function loadedAssets(page) {
  return page.evaluate(() => [...new Set(performance.getEntriesByType("resource")
    .map((entry) => new URL(entry.name).pathname)
    .filter((name) => name.startsWith("/assets/") && name.endsWith(".js")))]);
}

async function measure(page, label) {
  const assets = await loadedAssets(page);
  assert(assets.length, "Production JS assets must be loaded; Vite dev modules are not accepted");
  const buffers = assets.map((asset) => readFileSync(join("frontend/dist", asset)));
  measurements[label] = {
    bytes: buffers.reduce((sum, buffer) => sum + buffer.length, 0),
    gzip: buffers.reduce((sum, buffer) => sum + gzipSync(buffer).length, 0),
    assets,
  };
  return assets.map((asset) => basename(asset));
}

async function go(page, path) {
  await page.goto(base + path, { waitUntil: "domcontentloaded" });
  await page.locator(".pageStack > .ant-space-item").first().waitFor();
  assert.equal(await page.getByRole("alert").filter({ hasText: "页面加载失败" }).count(), 0, path);
  checks.push(path);
  console.log(JSON.stringify({ phase: "route", path }));
}

async function overflow(page, label) {
  const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  assert(dimensions.scroll <= dimensions.width + 2, label + ": " + JSON.stringify(dimensions));
}

async function openDetail(page, key) {
  const button = page.getByRole("button", { name: /^详\s*情$/ }).first();
  await button.waitFor();
  assert(!(await loadedAssets(page)).some((asset) => basename(asset) === assetFor(key)), key + " loaded before opening");
  await button.click();
  const dialog = page.locator(".ant-modal:visible").first();
  await dialog.waitFor();
  assert((await loadedAssets(page)).some((asset) => basename(asset) === assetFor(key)), key + " was not requested");
  await dialog.locator(".ant-modal-close").click();
  await dialog.waitFor({ state: "hidden" });
  await button.click();
  await dialog.waitFor();
  await dialog.locator(".ant-modal-close").click();
  await dialog.waitFor({ state: "hidden" });
  checks.push("open-close-reopen: " + key);
}

try {
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  track(page);
  await page.goto(base + "/dashboard", { waitUntil: "domcontentloaded" });
  await page.locator(".portfolioShell").waitFor();
  const portalAssets = await measure(page, "portal");
  assert(!portalAssets.includes(assetFor("src/components/WorkspaceLayout.tsx")), "Portal fetched workspace layout");
  assert(!portalAssets.includes(assetFor("src/components/AgentWorkspace.tsx")), "Portal fetched Agent UI");
  for (const key of Object.keys(manifest).filter((key) => /^src\/(pages|dialogs)\//.test(key))) {
    assert(!portalAssets.includes(assetFor(key)), "Portal fetched " + key);
  }
  await page.screenshot({ path: join(output, "portal.png"), fullPage: true });
  await page.getByRole("button", { name: /登录|未登录/ }).first().click();
  const modal = page.locator(".ant-modal:visible").first();
  await modal.locator("input").nth(0).fill("admin_demo");
  await modal.locator("input").nth(1).fill("Admin123456");
  const login = page.waitForResponse((response) => new URL(response.url()).pathname === "/api/auth/login" && response.request().method() === "POST");
  await modal.locator(".ant-modal-footer .ant-btn-primary").click();
  assert.equal((await login).status(), 200);
  await page.locator(".pageStack > .ant-space-item").first().waitFor();
  checks.push("real_admin_login_via_ui");

  await go(page, "/dashboard");
  const dashboardAssets = await measure(page, "dashboard");
  assert(!dashboardAssets.includes(assetFor("src/portal/PublicPortal.tsx")), "Dashboard fetched public portal");
  for (const key of Object.keys(manifest).filter((key) => key.startsWith("src/dialogs/"))) {
    assert(!dashboardAssets.includes(assetFor(key)), "Closed dialog eagerly downloaded: " + key);
  }
  await page.screenshot({ path: join(output, "dashboard.png"), fullPage: true });
  await page.locator('[data-nav-path="/settings"]').click();
  await page.waitForURL("**/settings");
  await page.getByRole("tab", { name: "账号安全", exact: true }).click();
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "账号安全", exact: true, selected: true }).waitFor();
  checks.push("spa_navigation_and_tab_reload");

  for (const path of [
    "/run-records", "/files", "/desktop-downloads", "/effect-analytics", "/evaluation-center",
    "/monitoring-center", "/agents", "/business-action-loop", "/platform-drafts/review",
    "/platform-execution-tasks", "/notifications", "/feedback-center", "/automation-flows",
    "/connectors", "/mcp-tools", "/platform-action-executors", "/automation/customer-service-inbox",
    "/erp/query", "/chat", "/documents", "/users", "/audit", "/threads",
  ]) await go(page, path);

  await go(page, "/automation-flows");
  await openDetail(page, "src/dialogs/AutomationFlowDetailModal.tsx");
  await go(page, "/connectors");
  await openDetail(page, "src/dialogs/ConnectorDetailModal.tsx");
  await go(page, "/agents/operations-listing-launch");
  await page.getByRole("tab", { name: "自动化规则", exact: true }).click();
  await page.getByRole("button", { name: "技术详情", exact: true }).click();
  await page.locator(".aiWorkflowDetailTabs").waitFor();
  await page.locator(".ant-modal:visible .ant-modal-close").click();
  checks.push("lazy_agent_technical_detail");

  for (const path of ["/dashboard", "/agents", "/settings", "/documents"]) {
    await page.setViewportSize({ width: 390, height: 844 });
    await go(page, path);
    await overflow(page, path);
  }
  await page.screenshot({ path: join(output, "mobile.png"), fullPage: true });
  await context.close();
  context = undefined;

  for (const account of [
    { username: "finance_demo", password: "Finance123456", route: "/automation/finance/reconciliation", forbidden: "/users" },
    { username: "employee_demo", password: "Employee123456", route: "/approvals", forbidden: "/documents" },
    { username: "operations_demo", password: "Operations123456", route: "/agents/operations-listing-launch", forbidden: "/monitoring-center" },
  ]) {
    const response = await fetch(api + "/auth/login", { method: "POST", body: new URLSearchParams({ username: account.username, password: account.password }) });
    assert.equal(response.status, 200, account.username);
    const session = await response.json();
    context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript((session) => {
      for (const key of ["access_token", "username", "role", "position"]) if (session[key]) localStorage.setItem(key, session[key]);
      localStorage.setItem("allowed_ai_app_ids", JSON.stringify(session.allowed_ai_app_ids));
    }, session);
    const employeePage = await context.newPage();
    track(employeePage);
    const jobsResponse = account.username === "finance_demo"
      ? employeePage.waitForResponse((response) => new URL(response.url()).pathname === "/api/jobs")
      : undefined;
    await go(employeePage, account.route);
    if (account.username === "finance_demo") {
      assert.equal((await jobsResponse).status(), 200, "Finance jobs must load from the real API");
      await employeePage.getByTestId("finance-background-jobs").waitFor();
      await employeePage.getByRole("tab", { name: "对账任务", selected: true }).waitFor();
      const reloadedJobs = employeePage.waitForResponse((response) => new URL(response.url()).pathname === "/api/jobs");
      await employeePage.reload({ waitUntil: "domcontentloaded" });
      assert.equal((await reloadedJobs).status(), 200);
      await employeePage.getByTestId("finance-background-jobs").waitFor();
      await measure(employeePage, "finance");
      await employeePage.screenshot({ path: join(output, "finance-mobile.png"), fullPage: true });
    }
    await overflow(employeePage, account.route);
    await go(employeePage, "/feedback");
    await employeePage.goto(base + account.forbidden, { waitUntil: "domcontentloaded" });
    await employeePage.waitForURL("**/dashboard");
    await employeePage.locator(".pageStack > .ant-space-item").first().waitFor();
    checks.push(account.username + ": allowed_routes_and_permission_redirect");
    await context.close();
    context = undefined;
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(failedAssets, []);
  assert(measurements.portal.bytes < 2216085 * 0.65);
  assert(measurements.dashboard.bytes < 2216085 * 0.85);
  const report = { ok: true, frontend: base, accounts: ["admin_demo", "finance_demo", "employee_demo", "operations_demo"], checks, measurements, errors, failedAssets, failedApiRequests, createdBusinessRecords: 0 };
  writeFileSync(join(output, "browser.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ ...report, measurements: Object.fromEntries(Object.entries(measurements).map(([key, value]) => [key, { bytes: value.bytes, gzip: value.gzip, chunks: value.assets.length }])) }, null, 2));
} catch (error) {
  await activePage?.screenshot({ path: join(output, "failure.png"), fullPage: true }).catch(() => {});
  writeFileSync(join(output, "failure.json"), JSON.stringify({ path: activePage?.url(), checks, errors, failedAssets, failedApiRequests }, null, 2) + "\n");
  throw error;
} finally {
  await context?.close();
  await browser.close();
}
