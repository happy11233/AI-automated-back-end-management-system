import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const npx = join(homedir(), ".npm/_npx");
let playwright;
for (const candidate of [process.env.PLAYWRIGHT_MODULE_PATH, "playwright", ...(existsSync(npx) ? readdirSync(npx).map((name) => join(npx, name, "node_modules/playwright")) : [])].filter(Boolean)) {
  try {
    const runtime = require(candidate);
    if (existsSync(runtime.chromium.executablePath())) { playwright = runtime; break; }
  } catch { /* Try the next installed browser runtime. */ }
}
assert(playwright, "Installed Playwright Chromium required");
const base = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const output = "data/verification/frontend-page-loading";
mkdirSync(output, { recursive: true });
const browser = await playwright.chromium.launch({ headless: true, args: ["--no-proxy-server"] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
const page = await context.newPage();
page.setDefaultTimeout(60000);
page.setDefaultNavigationTimeout(90000);
const requests = [], errors = [], failures = [], checks = [], measurements = {};
page.on("pageerror", (error) => errors.push(error.message));
page.on("request", (request) => {
  const url = new URL(request.url());
  if (url.pathname.startsWith("/api/")) requests.push({ path: url.pathname, method: request.method() });
});
page.on("response", (response) => {
  const path = new URL(response.url()).pathname;
  if (path.startsWith("/api/") && response.status() >= 400) failures.push({ path, status: response.status() });
});

function responseFor(path) {
  return page.waitForResponse((response) => new URL(response.url()).pathname === "/api" + path && response.request().method() === "GET", { timeout: 90000 });
}

async function settled() {
  await page.waitForLoadState("networkidle", { timeout: 90000 });
  assert.equal(await page.getByRole("alert").filter({ hasText: "页面加载失败" }).count(), 0);
}

async function login(username, password) {
  await page.getByRole("button", { name: /登录|未登录/ }).first().click();
  const modal = page.locator(".ant-modal:visible").first();
  await modal.locator("input").nth(0).fill(username);
  await modal.locator("input").nth(1).fill(password);
  const response = page.waitForResponse((r) => new URL(r.url()).pathname === "/api/auth/login");
  await modal.locator(".ant-modal-footer .ant-btn-primary").click();
  assert.equal((await response).status(), 200, username);
  await page.locator(".workspaceLayout").waitFor();
  await settled();
  checks.push("ui-login: " + username);
}

async function navigate(path, endpoint, { reload = false } = {}) {
  await settled();
  const start = requests.length;
  const response = responseFor(endpoint);
  if (reload) await page.goto(base + path, { waitUntil: "domcontentloaded" });
  else await page.evaluate((path) => {
    window.history.pushState(null, "", path);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
  assert.equal((await response).status(), 200, path);
  await page.locator(".pageStack > .ant-space-item").first().waitFor();
  await settled();
  const calls = requests.slice(start).filter((request) => request.method === "GET");
  assert.equal(calls.filter((request) => request.path === "/api" + endpoint).length, 1, path + " duplicated its primary request");
  measurements[(reload ? "reload:" : "spa:") + path] = calls.map((request) => request.path);
  checks.push((reload ? "reload: " : "spa: ") + path);
  console.log(JSON.stringify({ phase: "route", path, requests: calls.map((request) => request.path) }));
}

try {
  await page.goto(base + "/dashboard", { waitUntil: "domcontentloaded" });
  await page.locator(".portfolioShell").waitFor();
  await login("admin_demo", "Admin123456");
  const dashboard = requests.filter((request) => request.method === "GET").map((request) => request.path);
  const expected = ["/api/threads", "/api/erp/dashboard-overview", "/api/feedback", "/api/admin/audit-logs"].sort();
  assert.deepEqual([...dashboard].sort(), expected, "Dashboard should load only sidebar and dashboard data");
  measurements.adminLoginDashboard = dashboard;
  await page.screenshot({ path: join(output, "dashboard.png"), fullPage: true });

  for (const [path, endpoint] of [
    ["/connectors", "/connectors"],
    ["/mcp-tools", "/admin/mcp-tools"],
    ["/platform-action-executors", "/platform-action-executors"],
    ["/run-records", "/run-records"],
    ["/effect-analytics", "/effect-analytics"],
    ["/evaluation-center", "/evaluation-center"],
    ["/monitoring-center", "/monitoring-center"],
    ["/settings", "/settings/me"],
    ["/users", "/admin/users"],
    ["/notifications", "/notifications"],
    ["/automation-flows", "/automation-flows"],
    ["/platform-drafts/review", "/platform-drafts"],
    ["/files", "/files"],
    ["/audit", "/admin/audit-logs"],
  ]) await navigate(path, endpoint);

  await navigate("/connectors", "/connectors", { reload: true });
  await page.locator(".connectorCard").first().waitFor();
  const detail = page.getByRole("button", { name: /^详\s*情$/ }).first();
  await detail.click();
  await page.locator(".ant-modal:visible").first().waitFor();
  await page.locator(".ant-modal:visible .ant-modal-close").click();
  checks.push("extracted-connector-detail");

  // Exercise actual responses arriving after a session change. No interception,
  // delayed fake responses, or patched browser APIs are used.
  const stale = await page.evaluate(async () => {
    const api = await import("/src/api.ts");
    const originalToken = localStorage.getItem("access_token");
    let expiryEvents = 0;
    const onExpired = () => { expiryEvents += 1; };
    window.addEventListener("company-rag-auth-expired", onExpired);
    const capture = (pending) => pending.then(() => "unexpected-success", (error) => error.name);
    try {
      const pendingSuccess = capture(api.listConnectors(originalToken));
      localStorage.removeItem("access_token");
      const success = await pendingSuccess;
      localStorage.setItem("access_token", "invalid-session-verification");
      const pendingUnauthorized = capture(api.listConnectors("invalid-session-verification"));
      localStorage.setItem("access_token", originalToken);
      const unauthorized = await pendingUnauthorized;
      return { success, unauthorized, expiryEvents };
    } finally {
      localStorage.setItem("access_token", originalToken);
      window.removeEventListener("company-rag-auth-expired", onExpired);
    }
  });
  assert.deepEqual(stale, { success: "SessionChangedError", unauthorized: "SessionChangedError", expiryEvents: 0 });
  checks.push("real-stale-success-and-401-ignored");

  await page.locator(".userMenuButton").click();
  await page.getByText("退出登录", { exact: true }).click();
  await page.locator(".portfolioShell").waitFor();
  assert.equal(await page.evaluate(() => localStorage.getItem("access_token")), null);
  const switchStart = requests.length;
  await login("finance_demo", "Finance123456");
  const financeCalls = requests.slice(switchStart).filter((r) => r.method === "GET").map((r) => r.path);
  assert.deepEqual([...financeCalls].sort(), ["/api/threads", "/api/erp/dashboard-overview"].sort());
  measurements.financeLoginDashboard = financeCalls;
  assert.equal(await page.locator('[data-nav-path="/connectors"]').count(), 0);
  await navigate("/automation/finance/reconciliation", "/jobs");
  await page.setViewportSize({ width: 390, height: 844 });
  await settled();
  const mobile = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
  assert(mobile.content <= mobile.viewport + 2, "Mobile layout overflow: " + JSON.stringify(mobile));
  measurements.financeMobile = mobile;
  await page.screenshot({ path: join(output, "finance-mobile.png"), fullPage: true });
  checks.push("logout-and-switch-to-finance");

  await page.evaluate(() => localStorage.setItem("access_token", "invalid-session-verification"));
  await page.goto(base + "/dashboard", { waitUntil: "domcontentloaded" });
  await page.getByText("登录失效，需要重新登录。", { exact: true }).waitFor();
  await page.locator(".portfolioShell").waitFor();
  assert.equal(await page.evaluate(() => localStorage.getItem("access_token")), null);
  assert.equal(new URL(page.url()).pathname, "/");
  checks.push("real-401-expiry-clears-session");

  await page.setViewportSize({ width: 1440, height: 1000 });
  await login("employee_demo", "Employee123456");
  await navigate("/approvals", "/approvals");
  checks.push("customer-service-only-approvals");

  assert.deepEqual(errors, []);
  assert(failures.every((failure) => failure.status === 401), JSON.stringify(failures));
  const report = { passed: true, checkedAt: new Date().toISOString(), base, checks, measurements, stale, errors, expectedUnauthorizedResponses: failures, createdBusinessRecords: 0 };
  writeFileSync(join(output, "browser.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await page.screenshot({ path: join(output, "failure.png"), fullPage: true }).catch(() => {});
  writeFileSync(join(output, "failure.json"), JSON.stringify({ error: String(error), url: page.url(), requests, errors, failures, checks }, null, 2));
  throw error;
} finally {
  await browser.close();
}
