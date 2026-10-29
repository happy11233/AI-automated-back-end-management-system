import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const state = JSON.parse(readFileSync(process.argv[2], "utf8"));
const npxRoot = join(homedir(), ".npm", "_npx");
const candidates = [process.env.PLAYWRIGHT_MODULE_PATH, "playwright",
  ...(existsSync(npxRoot) ? readdirSync(npxRoot).map((name) => join(npxRoot, name, "node_modules/playwright")) : [])];
let playwright;
for (const candidate of candidates.filter(Boolean)) {
  try {
    const runtime = require(candidate);
    if (process.env.VERIFY_CHROME_PATH || existsSync(runtime.chromium.executablePath())) {
      playwright = runtime;
      break;
    }
  } catch { /* Try another existing installation. */ }
}
assert(playwright, "Install Playwright or provide PLAYWRIGHT_MODULE_PATH and VERIFY_CHROME_PATH");
const base = (process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const browser = await playwright.chromium.launch({ headless: true, args: ["--no-proxy-server"],
  ...(process.env.VERIFY_CHROME_PATH ? { executablePath: process.env.VERIFY_CHROME_PATH } : {}) });
const errors = [];
const results = [];
const matches = (response, endpoint, status) => {
  const url = new URL(response.url());
  return url.pathname === "/api/" + endpoint && response.request().method() === "GET"
    && (status === undefined || (url.searchParams.get("status") || "all") === status);
};
const content = (page) => page.locator(".workspacePageContainer");
const rows = (page) => page.locator(".notificationTable .ant-table-tbody > tr.ant-table-row");

function waitResponse(page, predicate, options) {
  const pending = page.waitForResponse(predicate, options);
  void pending.catch(() => {});
  return pending;
}

async function session(name) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, reducedMotion: "reduce" });
  await context.addInitScript((session) => {
    localStorage.setItem("access_token", session.access_token);
    localStorage.setItem("username", session.username);
    localStorage.setItem("role", session.role);
    if (session.position) localStorage.setItem("position", session.position);
    localStorage.setItem("allowed_ai_app_ids", JSON.stringify(session.allowed_ai_app_ids));
  }, state.accounts[name].session);
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  return { context, page };
}
async function loaded(page, endpoint = "notifications") {
  const table = endpoint === "notifications" ? ".notificationTable" : endpoint === "feedback" ? ".feedbackTable" : ".platformTaskTable";
  await page.locator(table).waitFor();
  await page.locator(table + " .ant-spin-spinning").waitFor({ state: "hidden", timeout: 20000 });
}
async function go(page, route, endpoint) {
  const response = waitResponse(page, (response) => matches(response, endpoint), { timeout: 30000 });
  await page.goto(base + "/" + route, { waitUntil: "domcontentloaded" });
  assert.equal((await response).status(), 200);
  await content(page).waitFor();
  await loaded(page, endpoint);
}
async function select(page, label, endpoint, status) {
  const response = waitResponse(page, (response) => matches(response, endpoint, status));
  await content(page).locator(".ant-segmented-item").filter({ hasText: new RegExp("^" + label + "$") }).click();
  assert.equal((await response).status(), 200);
  await loaded(page, endpoint);
}
async function metrics(page, values) {
  await page.waitForFunction((values) => {
    const text = [...document.querySelectorAll(".notificationMetricRow h3")].map((node) => node.textContent);
    return text.join(",") === values.join(",");
  }, values);
}
async function allStatuses(page, status) {
  await page.waitForFunction((status) => {
    const cells = [...document.querySelectorAll(".notificationTable tr.ant-table-row td:first-child")];
    return cells.length > 0 && cells.every((cell) => cell.textContent.trim() === status);
  }, status);
}
async function overflow(page, label) {
  const size = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth }));
  assert(size.scroll <= size.viewport + 2, label + ": " + JSON.stringify(size));
  results.push(label);
}

try {
  const { page, context } = await session("admin");
  await go(page, "notifications", "notifications");
  await metrics(page, [21, 74, 48, 95]);
  assert.equal(await rows(page).count(), 10);
  assert.equal(await content(page).getByRole("button", { name: /^查\s*询$/ }).count(), 0);
  await select(page, "已读", "notifications", "read");
  await allStatuses(page, "已读");
  await metrics(page, [21, 74, 48, 95]);
  assert(await content(page).getByRole("button", { name: /全部已读/ }).isEnabled());
  await select(page, "未读", "notifications", "unread");
  await allStatuses(page, "未读");
  results.push("status_switch_fetches_without_query_and_preserves_global_counts");

  // Delay an older response while preserving the real API response body.
  let releaseOld, oldArrived;
  const arrived = new Promise((resolve) => { oldArrived = resolve; });
  const gate = new Promise((resolve) => { releaseOld = resolve; });
  const raceHandler = async (route) => {
    if (new URL(route.request().url()).searchParams.get("status") === "read") {
      const response = await route.fetch();
      oldArrived();
      await gate;
      await route.fulfill({ response });
    } else await route.continue();
  };
  await page.route("**/api/notifications?**", raceHandler);
  await content(page).locator(".ant-segmented-item").filter({ hasText: /^已读$/ }).click();
  await arrived;
  await select(page, "未读", "notifications", "unread");
  const oldDone = waitResponse(page, (response) => matches(response, "notifications", "read"));
  releaseOld();
  await oldDone;
  await page.waitForTimeout(200);
  await allStatuses(page, "未读");
  await page.unroute("**/api/notifications?**", raceHandler);
  results.push("older_response_cannot_replace_latest_status");

  // The third unread page contains one item; marking it read must return to page two.
  let response = waitResponse(page, (response) => matches(response, "notifications", "unread")
    && new URL(response.url()).searchParams.get("offset") === "20");
  await page.locator('.notificationTable .ant-pagination-item[title="3"]').click();
  await response;
  await loaded(page);
  assert.equal(await rows(page).count(), 1);
  const removedId = await rows(page).first().getAttribute("data-row-key");
  response = waitResponse(page, (response) => matches(response, "notifications", "unread")
    && new URL(response.url()).searchParams.get("offset") === "10");
  await rows(page).first().getByRole("button", { name: /^已\s*读$/ }).click();
  await response;
  await loaded(page);
  await metrics(page, [20, 75, 48, 95]);
  assert.equal(await rows(page).count(), 10);
  assert.equal(await page.locator('.notificationTable tr[data-row-key="' + removedId + '"]').count(), 0);
  await allStatuses(page, "未读");
  results.push("mark_read_removes_row_updates_counts_and_corrects_empty_page");

  await select(page, "已读", "notifications", "read");
  await page.locator('.notificationTable .ant-pagination-item[title="1"].ant-pagination-item-active').waitFor();
  await select(page, "全部", "notifications", "all");
  for (let index = 1; index <= 8; index++) {
    const offset = String(index * 10);
    response = waitResponse(page, (response) => matches(response, "notifications", "all")
      && new URL(response.url()).searchParams.get("offset") === offset);
    await page.locator(".notificationTable .ant-pagination-next").click();
    await response;
    await loaded(page);
  }
  assert.equal(await rows(page).count(), 10);
  assert((await rows(page).first().textContent()).includes(state.marker + "-admin-080"));
  results.push("server_pagination_reaches_records_beyond_80");

  await select(page, "未读", "notifications", "unread");
  response = waitResponse(page, (response) => matches(response, "notifications", "unread"));
  await content(page).getByRole("button", { name: /全部已读/ }).click();
  await response;
  await loaded(page);
  await page.getByText("暂无未读通知", { exact: true }).waitFor();
  await metrics(page, [0, 95, 48, 95]);
  assert(await content(page).getByRole("button", { name: /全部已读/ }).isDisabled());
  results.push("mark_all_clears_unread_view");

  await select(page, "已读", "notifications", "read");
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 960 });
    await page.waitForTimeout(150);
    await overflow(page, "notification_layout_" + width);
    await page.screenshot({ path: "/tmp/company-rag-notifications-" + width + ".png", fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 960 });
  await go(page, "platform-execution-tasks", "platform-execution-tasks");
  await select(page, "失败", "platform-execution-tasks", "failed");
  assert.equal(await content(page).getByRole("button", { name: /^查\s*询$/ }).count(), 0);
  await select(page, "全部", "platform-execution-tasks", "all");
  results.push("execution_task_status_fetches_immediately");

  await go(page, "feedback-center", "feedback");
  await select(page, "已完成", "feedback", "completed");
  assert.equal(await content(page).getByRole("button", { name: /^查\s*询$/ }).count(), 0);
  await page.locator(".feedbackTable").getByText(state.marker + "-completed", { exact: true }).waitFor();
  await select(page, "待处理", "feedback", "open");
  await page.locator(".feedbackTable").getByText(state.marker + "-open", { exact: true }).waitFor();
  results.push("admin_feedback_status_fetches_immediately");
  await context.close();

  const employee = await session("employee");
  await go(employee.page, "feedback", "feedback");
  await select(employee.page, "已完成", "feedback", "completed");
  await employee.page.locator(".feedbackTable").getByText(state.marker + "-completed", { exact: true }).waitFor();
  await select(employee.page, "待处理", "feedback", "open");
  await go(employee.page, "notifications", "notifications");
  await metrics(employee.page, [3, 0, 2, 3]);
  assert.equal(await rows(employee.page).count(), 3);
  assert(!(await content(employee.page).textContent()).includes(state.marker + "-admin-"));
  results.push("employee_feedback_and_notification_isolation");
  await employee.context.close();
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ok: true, results, errors,
    note: "Real frontend, API and PostgreSQL; race test delays a real response; fixtures are cleaned by the runner." }, null, 2));
} catch (error) {
  for (const context of browser.contexts()) {
    for (const page of context.pages()) {
      console.error("Current URL:", page.url());
      console.error((await page.locator("body").innerText().catch(() => "")).slice(-2400));
      await page.screenshot({ path: "/tmp/company-rag-notifications-failure.png", fullPage: true }).catch(() => {});
    }
  }
  throw error;
} finally {
  await browser.close();
}
