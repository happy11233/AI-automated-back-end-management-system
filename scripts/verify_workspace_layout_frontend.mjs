import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { existsSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const npxRoot = join(homedir(), ".npm", "_npx");
const candidates = [
  process.env.PLAYWRIGHT_MODULE_PATH,
  "playwright",
  ...(existsSync(npxRoot)
    ? readdirSync(npxRoot).map((name) =>
        join(npxRoot, name, "node_modules/playwright"),
      )
    : []),
];
let playwright;
for (const candidate of candidates.filter(Boolean)) {
  try {
    playwright = require(candidate);
    break;
  } catch {
    /* Try the next installed runtime. */
  }
}
assert(playwright, "Install Playwright or set PLAYWRIGHT_MODULE_PATH");
const baseUrl = (
  process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173"
).replace(/\/$/, "");
const browser = await playwright.chromium.launch({
  headless: true,
  args: ["--no-proxy-server"],
  ...(process.env.VERIFY_CHROME_PATH
    ? { executablePath: process.env.VERIFY_CHROME_PATH }
    : {}),
});
const errors = [],
  results = [];
const routes = [
  "dashboard",
  "effect-analytics",
  "evaluation-center",
  "agents",
  "settings",
  "run-records",
  "documents",
  "users",
  "business-action-loop",
  "platform-execution-tasks",
  "platform-drafts/review",
  "automation/customer-service-inbox",
  "connectors",
  "mcp-tools",
  "platform-action-executors",
  "monitoring-center",
  "automation-flows",
  "notifications",
  "files",
  "audit",
  "feedback-center",
  "erp/query",
];
const responsiveWidths = (process.env.VERIFY_WIDTHS || "1440,1024,390")
  .split(",")
  .map(Number);

async function go(page, route) {
  await page.goto(`${baseUrl}/${route}`, { waitUntil: "domcontentloaded" });
  try {
    await page
      .locator(".ant-pro-layout-content .pageStack")
      .first()
      .waitFor({ timeout: 8000 });
  } catch (error) {
    const context = await page
      .locator("body")
      .innerText()
      .catch(() => "<body unavailable>");
    throw new Error(
      `route ${route} did not render page content; url=${page.url()}; body=${context.slice(0, 500)}`,
      {
        cause: error,
      },
    );
  }
  await page.waitForTimeout(400);
}
async function visible(locator) {
  await locator.first().waitFor({ state: "visible" });
}
async function tab(page, name) {
  const target = page.getByRole("tab", { name, exact: true });
  await target.click();
  assert.equal(await target.getAttribute("aria-selected"), "true", name);
}
async function overflow(page, label) {
  const size = await page.evaluate(() => ({
    viewport: innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  assert(
    size.scroll <= size.viewport + 2,
    `${label}: horizontal overflow ${JSON.stringify(size)}`,
  );
  return size;
}
async function login(context, username, password) {
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "domcontentloaded" });
  await page
    .getByRole("button", { name: /登录|未登录/ })
    .first()
    .click();
  const modal = page.locator(".ant-modal").filter({ hasText: /登录/ }).first();
  await modal.locator("input").nth(0).fill(username);
  await modal.locator("input").nth(1).fill(password);
  await modal.locator(".ant-modal-footer .ant-btn-primary").click();
  await page.locator(".workspacePageContainer").waitFor();
  return page;
}
async function closeDrawer(page) {
  const drawer = page.locator(".ant-drawer-content:visible");
  await drawer.locator(".ant-drawer-close").click();
  await drawer.waitFor({ state: "hidden" });
}

try {
  const admin = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    reducedMotion: "reduce",
  });
  const page = await login(admin, "admin_demo", "Admin123456");
  await go(page, "dashboard");
  await tab(page, "业务数据");
  await visible(page.getByText("平台数据概览", { exact: true }));
  await page.reload({ waitUntil: "domcontentloaded" });
  await visible(page.getByRole("tab", { name: "业务数据", selected: true }));
  await tab(page, "工作概览");
  await page
    .locator(".dashboardShortcutCard")
    .filter({ hasText: "Agent 中心" })
    .getByRole("button")
    .click();
  await page.waitForURL("**/agents");
  await visible(page.locator(".agentCatalogCard"));
  assert((await page.locator(".agentCatalogCard").count()) <= 6);
  await page.getByPlaceholder("搜索任务名称或业务场景").fill("__no_matching_agent__");
  await visible(page.getByText("没有匹配的 Agent", { exact: true }));
  await page.getByPlaceholder("搜索任务名称或业务场景").fill("财务");
  await visible(page.locator(".agentCatalogCard"));

  await go(page, "effect-analytics");
  await visible(page.locator(".workspaceChartPoint"));
  const zeroBars = await page
    .locator('rect[data-value="0"]')
    .evaluateAll((nodes) =>
      nodes.map((node) => Number(node.getAttribute("height"))),
    );
  assert(
    zeroBars.length > 0 && zeroBars.every((height) => height === 0),
    "zero bars must have zero height",
  );
  await page.locator(".workspaceChartPoint").first().focus();
  await visible(page.locator(".workspaceChartReadout strong"));
  await page
    .locator(".workspaceChartToolbar .ant-segmented-item")
    .filter({ hasText: "折线图" })
    .click();
  await visible(page.locator(".workspaceTrendSvg polyline"));
  await tab(page, "岗位与应用");
  await visible(page.getByRole("list", { name: "岗位执行次数排行" }));
  await page.getByText("查看岗位明细", { exact: true }).click();
  await visible(page.locator(".ant-table:visible"));
  await tab(page, "安全分析");
  await visible(page.getByText("审计安全摘要", { exact: true }));
  await tab(page, "估算口径");
  await visible(page.locator(".effectEstimateGrid"));

  await go(page, "evaluation-center");
  for (const [name, title] of [
    ["评测集", "评测集资产"],
    ["评测报告", "最近评测报告"],
    ["回归套件", "真实回归套件"],
    ["质量总览", "发布闸门"],
  ]) {
    await tab(page, name);
    await visible(page.getByText(title, { exact: true }));
  }
  await go(page, "settings");
  await tab(page, "账号安全");
  await visible(page.locator('input[type="password"]'));
  await tab(page, "基本资料");

  await go(page, "run-records");
  assert.equal(
    await page.getByPlaceholder("应用 ID", { exact: true }).isVisible(),
    false,
  );
  await page.getByText("高级筛选", { exact: true }).click();
  await page
    .getByPlaceholder("应用 ID", { exact: true })
    .fill("verification_only");
  await visible(page.getByText("1 项已设置", { exact: true }));
  await page.getByRole("button", { name: "清除高级条件" }).click();
  assert.equal(
    await page.getByPlaceholder("应用 ID", { exact: true }).inputValue(),
    "",
  );

  await go(page, "documents");
  assert.equal(await page.locator(".ant-upload-drag").isVisible(), false);
  await page.getByRole("button", { name: "上传文档" }).click();
  await visible(page.locator(".ant-upload-drag"));
  await page.getByText("高级访问控制与初始授权", { exact: true }).click();
  await visible(page.getByText("上传访问模式", { exact: true }));
  await closeDrawer(page);
  const authButton = page.getByRole("button", { name: "授权详情" }).first();
  if (await authButton.count()) {
    await authButton.click();
    await visible(
      page.locator(".ant-drawer-title").filter({ hasText: "文档授权详情" }),
    );
    await closeDrawer(page);
  }
  await tab(page, "团队管理");
  await visible(page.getByText("团队列表", { exact: true }));
  await tab(page, "文档授权");
  await visible(page.getByRole("textbox", { name: "文档 ID" }));
  for (const [route, button, input] of [
    ["users", "新建用户", ".userCreateForm"],
    ["platform-action-executors", "新增执行器", ".platformExecutorFormGrid"],
  ]) {
    await go(page, route);
    await page.getByRole("button", { name: button }).click();
    await visible(page.locator(input));
    await page.setViewportSize({ width: 390, height: 900 });
    await page.waitForFunction(() => {
      const bounds = document
        .querySelector(".ant-drawer-open .ant-drawer-content-wrapper")
        ?.getBoundingClientRect();
      return bounds && bounds.width <= innerWidth + 1 && bounds.x >= -1;
    });
    await overflow(page, `${route} drawer`);
    const bounds = await page
      .locator(".ant-drawer-content-wrapper:visible")
      .boundingBox();
    assert(
      bounds.width <= 391 && bounds.x >= -1,
      `${route}: drawer exceeds viewport`,
    );
    await closeDrawer(page);
    await page.setViewportSize({ width: 1440, height: 960 });
  }
  await go(page, "connectors");
  await page
    .getByRole("textbox", { name: "搜索连接器" })
    .fill("__no_matching_connector__");
  await visible(page.getByText("没有匹配的连接器", { exact: true }));
  await go(page, "ai-workflows/operations-competitor-analysis");
  await tab(page, "自动化规则");
  await tab(page, "任务概况");
  await visible(page.locator(".agentMainGrid"));
  assert.equal(await page.locator(".agentWorkspace textarea").count(), 0);
  await go(page, "monitoring-center");
  for (const name of ["AIOps 运维", "运行问题", "分布分析", "连接审计", "总览"])
    await tab(page, name);
  results.push({ label: "admin_navigation_charts_filters_drawers", ok: true });

  for (const width of responsiveWidths) {
    await page.setViewportSize({ width, height: 960 });
    for (const route of routes) {
      console.log(`Checking responsive route ${route} at ${width}px`);
      await go(page, route);
      await overflow(page, `${route} ${width}`);
    }
    results.push({
      label: `responsive_${width}`,
      pages: routes.length,
      ok: true,
    });
  }
  await admin.close();

  for (const [position, username, password, workflow] of [
    [
      "operations",
      "operations_demo",
      "Operations123456",
      "operations-competitor-analysis",
    ],
    [
      "customer_service",
      "employee_demo",
      "Employee123456",
      "customer-service-logistics-reply",
    ],
    ["finance", "finance_demo", "Finance123456", "finance-report-analysis"],
  ]) {
    const context = await browser.newContext({
      viewport: { width: 390, height: 900 },
      reducedMotion: "reduce",
    });
    const employee = await login(context, username, password);
    await go(employee, "dashboard");
    await tab(employee, "业务数据");
    await visible(employee.getByText("岗位数据概览", { exact: true }));
    await go(employee, `ai-workflows/${workflow}`);
    await tab(employee, "自动化规则");
    await tab(employee, "任务概况");
    for (const path of [
      "effect-analytics",
      "evaluation-center",
      "documents",
      "users",
      "run-records",
    ]) {
      await go(employee, path);
      await employee.waitForURL("**/dashboard");
    }
    await overflow(employee, `${position} permissions`);
    results.push({ label: `${position}_workflow_and_permissions`, ok: true });
    await context.close();
  }
  assert.deepEqual(errors, [], "browser runtime errors");
  console.log(
    JSON.stringify(
      {
        ok: true,
        results,
        errors,
        note: "Real UI and APIs; no uploads, saves, evaluations or business executions performed.",
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
