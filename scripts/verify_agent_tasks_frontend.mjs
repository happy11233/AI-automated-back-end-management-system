import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const npx = join(homedir(), ".npm/_npx");
let playwright;
for (const name of [process.env.PLAYWRIGHT_MODULE_PATH, "playwright", ...(existsSync(npx) ? readdirSync(npx).map((name) => join(npx, name, "node_modules/playwright")) : [])].filter(Boolean)) {
  try { const runtime = require(name); if (existsSync(runtime.chromium.executablePath())) { playwright = runtime; break; } } catch {}
}
assert(playwright, "An installed Playwright Chromium runtime is required");
const state = JSON.parse(readFileSync(process.argv[2], "utf8"));
const browser = await playwright.chromium.launch({ headless: true, args: ["--no-proxy-server"] });
const errors = [], checks = [];
const contexts = [];
async function login(name) {
  const account = state.accounts[name];
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  contexts.push(context);
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(name + ": " + error.message));
  await page.goto(state.frontend + "/agents", { waitUntil: "domcontentloaded" });
  const loginEntry = page.getByText("登录后进入项目", { exact: true }).first();
  if (await loginEntry.count()) await loginEntry.click();
  else await page.getByRole("button", { name: "未登录", exact: true }).click();
  const modal = page.getByRole("dialog", { name: "登录企业内部后台" });
  await modal.locator("input").nth(0).fill(account.username);
  await modal.locator("input[type=password]").fill(account.password);
  const response = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/auth/login") && response.request().method() === "POST");
  await modal.getByRole("button", { name: "登 录", exact: true }).click();
  assert.equal((await response).status(), 200, "real browser login " + name);
  await modal.waitFor({ state: "hidden" });
  await page.goto(state.frontend + "/agents?agent_center_tab=tasks", { waitUntil: "domcontentloaded" });
  await page.locator(".businessTasks").waitFor();
  return { context, page };
}
async function loaded(page) {
  await page.locator(".businessTasks .ant-spin-spinning").waitFor({ state: "hidden" });
}
async function overflow(page, label) {
  const sizes = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  assert(sizes.scroll <= sizes.width + 2, label + ": " + JSON.stringify(sizes));
}
async function choose(page, field, text) {
  await page.locator(field).click();
  await page.locator(".ant-select-dropdown:visible").getByText(text, { exact: true }).click();
}
try {
  const { page } = await login("operations");
  await loaded(page);
  assert.equal(await page.locator(".businessTaskRow").count(), 10);
  await page.locator(".businessTasks .ant-pagination-item-2").click();
  await loaded(page);
  assert.equal(await page.locator(".businessTaskRow").count(), 2);
  checks.push("pagination");
  await page.getByRole("button", { name: "登记任务", exact: true }).click();
  const modal = page.getByRole("dialog", { name: "登记业务任务" });
  await modal.getByText("保存后为已登记状态，不会自动执行或操作店铺。", { exact: true }).waitFor();
  await choose(page, ".ant-modal:visible #store_id", "浏览器隔离验收店铺 · amazon / US");
  const goal = "浏览器创建：整理上架资料，等待人工复核";
  await modal.locator("#goal").fill(goal);
  await modal.locator("#expected_outputs").fill("上架资料检查单\n待审核商品草稿");
  await modal.locator("#completion_criteria").fill("人工复核通过\n取得平台回执");
  const createdResponse = page.waitForResponse((response) => new URL(response.url()).pathname.endsWith("/agent-tasks") && response.request().method() === "POST");
  await modal.getByRole("button", { name: "保存任务", exact: true }).click();
  const created = await createdResponse;
  assert.equal(created.status(), 201);
  const task = (await created.json()).item;
  assert.equal(task.status, "draft");
  assert.equal(task.store_id, state.store_id);
  assert.deepEqual(task.expected_outputs, ["上架资料检查单", "待审核商品草稿"]);
  const drawer = page.locator(".ant-drawer:visible");
  await drawer.getByText(goal, { exact: true }).waitFor();
  await drawer.getByText("已登记 · 未执行", { exact: true }).waitFor();
  await drawer.getByText("暂无关联运行证据，任务尚未执行", { exact: true }).waitFor();
  await drawer.locator(".ant-drawer-close").click();
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator(".businessTaskRow").filter({ hasText: goal }).waitFor();
  checks.push("create_with_store_outputs_criteria_and_reload");
  await choose(page, ".businessTaskFilters .ant-select", "业务已完成");
  await loaded(page);
  await page.getByText("暂无符合条件的业务任务", { exact: true }).waitFor();
  assert.equal(await page.locator(".businessTaskRow").count(), 0);
  await choose(page, ".businessTaskFilters .ant-select", "已登记 · 未执行");
  await loaded(page);
  await page.locator(".businessTaskRow").first().waitFor();
  checks.push("status_filter_and_empty");

  // Deliver a real API response, lose it in transit, then retry the same form.
  await page.getByRole("button", { name: "登记任务", exact: true }).click();
  const retryGoal = "请求中断重试，只登记一次";
  await modal.locator("#goal").fill(retryGoal);
  let loseResponse = true;
  const postKeys = [];
  const lostRoute = async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    postKeys.push(route.request().headers()["idempotency-key"]);
    const response = await route.fetch();
    if (loseResponse) { loseResponse = false; await route.abort("failed"); }
    else await route.fulfill({ response });
  };
  await page.route("**/agent-tasks", lostRoute);
  await modal.getByRole("button", { name: "保存任务", exact: true }).click();
  await modal.getByText("Failed to fetch", { exact: true }).waitFor();
  await modal.getByRole("button", { name: "保存任务", exact: true }).click();
  await drawer.getByText(retryGoal, { exact: true }).waitFor();
  assert.equal(postKeys.length, 2);
  assert(postKeys[0] && postKeys[0] === postKeys[1]);
  await page.unroute("**/agent-tasks", lostRoute);
  await drawer.locator(".ant-drawer-close").click();
  await loaded(page);
  assert.equal(await page.locator(".businessTaskRow").filter({ hasText: retryGoal }).count(), 1);
  checks.push("lost_response_retry_reuses_idempotency_key");

  const listFault = async (route) => {
    if (route.request().method() === "GET") await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "验收用网络故障" }) });
    else await route.continue();
  };
  await page.route("**/agent-tasks?*", listFault);
  await page.getByRole("button", { name: "刷新任务", exact: true }).click();
  await page.getByText("业务任务加载失败", { exact: true }).waitFor();
  assert.equal(await page.locator(".businessTaskRow").count(), 0, "failed fetch must clear stale data");
  await page.unroute("**/agent-tasks?*", listFault);
  await page.getByRole("button", { name: "重试", exact: true }).click();
  await page.locator(".businessTaskRow").first().waitFor();
  checks.push("network_failure_and_recovery");
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await overflow(page, "task list " + width);
    await page.locator(".businessTaskRow").first().getByRole("button", { name: "任务详情", exact: true }).click();
    await drawer.locator(".businessTaskDetail").waitFor();
    await overflow(page, "task drawer " + width);
    await page.screenshot({ path: join(state.evidence_dir, "tasks-" + width + ".png"), fullPage: true });
    await drawer.locator(".ant-drawer-close").click();
    checks.push("responsive_" + width);
  }
  for (const name of ["finance", "customer_service", "admin", "other_operations"]) {
    const { page } = await login(name);
    await loaded(page);
    if (name === "other_operations") {
      await page.getByText("暂无符合条件的业务任务", { exact: true }).waitFor();
      const denial = await page.evaluate(async ({ api, taskId }) => {
        const response = await fetch(api + "/agent-tasks/" + taskId, { headers: { Authorization: "Bearer " + localStorage.getItem("access_token") } });
        return response.status;
      }, { api: state.api, taskId: state.accounts.operations.task_id });
      assert.equal(denial, 404, "another employee must not read the task");
    } else {
      await page.locator(".businessTaskRow").first().waitFor();
      if (name !== "admin") {
        assert.equal(await page.locator(".businessTaskRow").count(), 1);
        const path = name === "finance" ? "/agents/finance-reconciliation?agent_tab=tasks" : "/agents/customer-service-message-loop?agent_tab=tasks";
        await page.goto(state.frontend + path, { waitUntil: "domcontentloaded" });
        await page.locator(".businessTaskRow").first().waitFor();
        await page.getByRole("tab", { name: "业务任务", selected: true }).waitFor();
      }
    }
    checks.push(name + "_real_login_and_task_scope");
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ok: true, browser: "Chromium", api: "real full FastAPI app + isolated PostgreSQL", checks, errors }, null, 2));
} finally {
  for (const context of contexts) await context.close();
  await browser.close();
}
