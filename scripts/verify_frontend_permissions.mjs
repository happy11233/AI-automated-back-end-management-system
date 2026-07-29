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
  operations: {
    username: "operations_demo",
    password: "Operations123456",
  },
  customer_service: {
    username: "employee_demo",
    password: "Employee123456",
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
  const cases = [
    {
      label: "admin_erp_diagnostics_visible",
      account: ACCOUNTS.admin,
      path: "/erp/diagnostics",
      waitFor: "岗位资源映射",
      visible: ["管理员 ERP 诊断", "ERPNext", "岗位资源映射"],
      hidden: [],
    },
    {
      label: "admin_ai_apps_visible",
      account: ACCOUNTS.admin,
      path: "/ai-apps",
      waitFor: "岗位应用目录",
      visible: ["AI 应用中心", "岗位应用目录", "运营 ERP 查询", "客服 ERP 查询", "财务 ERP 查询", "知识库维护", "审计与权限追踪"],
      hidden: [],
    },
    {
      label: "admin_documents_scope_controls_visible",
      account: ACCOUNTS.admin,
      path: "/documents",
      waitFor: "上传知识库",
      visible: ["上传知识库", "可见范围", "部门", "岗位范围", "站点范围", "店铺范围", "字段分类", "敏感级别", "入库流程"],
      hidden: [],
      afterChecks: async (page) => {
        const positionScope = await checkFormSelectOptions(page, {
          label: "岗位范围",
          optionLabels: ["不限岗位", "运营专属", "客服专属", "财务专属"],
          selectLabel: "运营专属",
        });
        const marketScope = await checkFormSelectOptions(page, {
          label: "站点范围",
          optionLabels: ["不限站点", "美国站", "德国站", "日本站"],
          selectLabel: "德国站",
        });
        const storeScope = await checkFormSelectOptions(page, {
          label: "店铺范围",
          optionLabels: ["不限店铺", "US Store", "DE Store", "JP Store"],
          selectLabel: "DE Store",
        });
        const fieldScope = await checkFormSelectOptions(page, {
          label: "字段分类",
          optionLabels: ["不限字段", "运营 Listing", "客服售后", "财务工资"],
          selectLabel: "财务工资",
        });
        const sensitivityLevel = await checkFormSelectOptions(page, {
          label: "敏感级别",
          optionLabels: ["内部", "保密", "受限"],
          selectLabel: "受限",
        });
        return {
          ok: positionScope.ok && marketScope.ok && storeScope.ok && fieldScope.ok && sensitivityLevel.ok,
          positionScope,
          marketScope,
          storeScope,
          fieldScope,
          sensitivityLevel,
        };
      },
    },
    {
      label: "finance_ai_apps_scoped",
      account: ACCOUNTS.finance,
      path: "/ai-apps",
      waitFor: "财务数据问答助手",
      visible: ["AI 应用中心", "财务数据问答助手", "财务 AI 对话", "财务 Excel 生成", "财务对账自动化", "应用目录保留为岗位能力入口"],
      hidden: ["运营 ERP 查询", "客服 ERP 查询", "知识库维护", "审计与权限追踪", "执行数据已接入运行记录页面"],
    },
    {
      label: "admin_dashboard_shortcuts_visible",
      account: ACCOUNTS.admin,
      path: "/dashboard",
      waitFor: "ERP 连接",
      visible: ["管理员快捷入口", "用户管理", "AI 应用中心", "知识库上传", "审计日志", "平台数据概览", "ERP 连接", "全部站点", "全部时间", "今天", "近7天", "近30天", "全部店铺", "US Store", "DE Store", "JP Store"],
      hidden: [],
      afterChecks: async (page) => {
        await clickShortcut(page, "用户管理");
        await page.waitForURL("**/users", { timeout: 10000 });
        return {
          ok: await isTextVisible(page, "管理员创建用户"),
          currentUrl: page.url(),
        };
      },
    },
    {
      label: "customer_service_erp_diagnostics_hidden",
      account: ACCOUNTS.customer_service,
      path: "/erp",
      waitFor: "客户资料",
      visible: ["概览", "岗位数据概览", "客户资料"],
      hidden: ["ERP 连接查询", "管理员 ERP 诊断", "用户管理", "知识库"],
      afterChecks: async (page) => ({
        ok: page.url().endsWith("/dashboard"),
        currentUrl: page.url(),
      }),
    },
    {
      label: "finance_excel_visible",
      account: ACCOUNTS.finance,
      path: "/automation/finance/excel-transform",
      waitFor: "财务 Excel 生成",
      visible: ["财务 AI 自动化", "财务 Excel 生成", "选择或上传 Excel", "选择财务 ERP 表", "生成并下载 Excel"],
      hidden: ["客服 AI 自动化", "运营 AI 自动化", "用户管理", "知识库"],
    },
    {
      label: "finance_dashboard_shortcuts_visible",
      account: ACCOUNTS.finance,
      path: "/dashboard",
      waitFor: "岗位数据概览",
      visible: ["岗位快捷入口", "财务 Excel 生成", "财务对账自动化", "财务 AI 对话", "岗位数据概览"],
      hidden: ["财务 ERP 查询", "ERP 连接查询", "用户管理", "知识库上传", "客服 AI 对话", "运营 AI 自动化", "财务数据概览", "已查询 ERPNext", "全部站点 / 全部店铺 / 全部时间", "匹配 8 条"],
      afterChecks: async (page) => {
        const marketOptionVisible = await selectMarket(page, "其他/未识别站点");
        await page.getByText("销售发票", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        const otherMarketVisible = await isTextVisible(page, "销售发票");
        await clickShortcut(page, "财务 Excel 生成");
        await page.waitForURL("**/automation/finance/excel-transform", { timeout: 10000 });
        return {
          ok: marketOptionVisible
            && otherMarketVisible
            && await isTextVisible(page, "选择或上传 Excel")
            && await isTextVisible(page, "选择财务 ERP 表")
            && await isTextVisible(page, "生成并下载 Excel"),
          currentUrl: page.url(),
          marketOptionVisible,
          otherMarketVisible,
        };
      },
    },
    {
      label: "customer_service_excel_hidden",
      account: ACCOUNTS.customer_service,
      path: "/automation",
      waitFor: "退款售后话术",
      visible: ["客服 AI 自动化", "退款售后话术"],
      hidden: ["选择或上传 Excel", "财务对账自动化", "财务 AI 自动化", "用户管理", "知识库"],
    },
    {
      label: "customer_service_dashboard_shortcuts_visible",
      account: ACCOUNTS.customer_service,
      path: "/dashboard",
      waitFor: "物流/出库单",
      visible: ["岗位快捷入口", "客服自动化收件箱", "客服 AI 对话", "岗位数据概览", "物流/出库单", "售后工单", "客户资料"],
      hidden: ["客服 ERP 查询", "ERP 连接查询", "用户管理", "知识库上传", "财务 Excel 生成", "财务对账自动化", "运营 AI 自动化", "客服数据概览", "已查询 ERPNext", "全部站点 / 全部店铺 / 全部时间", "匹配 8 条"],
    },
    {
      label: "operations_position_visible_only",
      account: ACCOUNTS.operations,
      path: "/automation",
      waitFor: "竞品分析",
      visible: ["运营 AI 自动化", "竞品分析"],
      hidden: ["客服 AI 自动化", "财务 AI 自动化", "选择或上传 Excel", "财务对账自动化", "用户管理", "知识库"],
    },
    {
      label: "operations_dashboard_shortcuts_visible",
      account: ACCOUNTS.operations,
      path: "/dashboard",
      waitFor: "销售订单",
      visible: ["岗位快捷入口", "运营 AI 自动化", "AI 对话", "岗位数据概览", "销售订单", "商品资料", "商品价格", "订单金额"],
      hidden: ["运营 ERP 查询", "ERP 连接查询", "用户管理", "知识库上传", "财务 Excel 生成", "财务对账自动化", "客服 AI 对话", "运营数据概览", "已查询 ERPNext", "全部站点 / 全部店铺 / 全部时间", "匹配 8 条"],
      afterChecks: async (page) => {
        const marketOptionVisible = await selectMarket(page, "其他/未识别站点");
        await page.waitForTimeout(800);
        const otherOverviewVisible = await isTextVisible(page, "销售订单");
        await selectMarket(page, "德国站");
        await clickSegmentedItem(page, "近30天");
        await clickSegmentedItem(page, "DE Store");
        await page.waitForTimeout(800);
        await page.getByText("销售订单", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        const overviewVisible = await isTextVisible(page, "岗位数据概览") && await isTextVisible(page, "销售订单");
        await page.locator(".dashboardOverviewCard").first().getByRole("button", { name: /ERP 详情/ }).first().click();
        await page.getByText("ERP 记录详情", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        const detailVisible = await isTextVisible(page, "ERP 记录详情");
        return {
          ok: marketOptionVisible && otherOverviewVisible && overviewVisible && detailVisible,
          currentUrl: page.url(),
          marketOptionVisible,
          otherOverviewVisible,
          overviewVisible,
          detailVisible,
        };
      },
    },
    {
      label: "admin_audit_filters_visible",
      account: ACCOUNTS.admin,
      path: "/audit",
      waitFor: "审计日志",
      visible: ["审计日志", "全部岗位", "查询"],
      hidden: [],
      afterChecks: async (page) => ({
        ok: await page.getByPlaceholder("动作筛选").isVisible()
          && await page.getByPlaceholder("资源类型").isVisible(),
      }),
    },
    {
      label: "url_route_and_back_navigation",
      account: ACCOUNTS.finance,
      path: "/chat",
      waitForPlaceholder: "输入当前岗位权限内的问题，按按钮发送到后端",
      visible: ["财务"],
      hidden: [],
      afterChecks: async (page) => {
        await page.goto(`${FRONTEND_URL}/ai-apps`, { waitUntil: "networkidle" });
        await page.waitForURL("**/ai-apps", { timeout: 10000 });
        const automationVisible = await isTextVisible(page, "财务 Excel 生成");
        await page.goBack({ waitUntil: "networkidle" });
        await page.waitForURL((url) => url.pathname === "/chat" || url.pathname.startsWith("/chat/"), { timeout: 10000 });
        const chatVisible = await page.getByPlaceholder("输入当前岗位权限内的问题，按按钮发送到后端").isVisible();

        return {
          ok: automationVisible && chatVisible,
          automationUrl: page.url().includes("/chat") ? "checked_after_back" : page.url(),
          automationVisible,
          chatVisible,
        };
      },
    },
    {
      label: "employee_admin_url_shows_forbidden_hint",
      account: ACCOUNTS.customer_service,
      path: "/users",
      visible: ["概览"],
      hidden: ["用户管理"],
      afterChecks: async (page) => ({
        ok: page.url().endsWith("/dashboard"),
        currentUrl: page.url(),
      }),
    },
    {
      label: "employee_run_records_hidden",
      account: ACCOUNTS.finance,
      path: "/run-records",
      visible: ["概览"],
      hidden: ["运行记录"],
      afterChecks: async (page) => ({
        ok: page.url().endsWith("/dashboard"),
        currentUrl: page.url(),
      }),
    },
    {
      label: "employee_effect_analytics_hidden",
      account: ACCOUNTS.operations,
      path: "/effect-analytics",
      visible: ["概览"],
      hidden: ["效果分析"],
      afterChecks: async (page) => ({
        ok: page.url().endsWith("/dashboard"),
        currentUrl: page.url(),
      }),
    },
    {
      label: "employee_automation_flows_hidden",
      account: ACCOUNTS.customer_service,
      path: "/automation-flows",
      visible: ["概览"],
      hidden: ["自动化流程配置", "流程配置"],
      afterChecks: async (page) => ({
        ok: page.url().endsWith("/dashboard"),
        currentUrl: page.url(),
      }),
    },
  ];

  const results = [];
  for (const item of cases) {
    const result = await runCase(item);
    results.push(result);
    console.log(JSON.stringify(result));
  }

  const failed = results.filter((item) => !item.ok);
  if (failed.length > 0) {
    throw new Error(`frontend permission verification failed: ${failed.map((item) => item.label).join(", ")}`);
  }
} finally {
  await browser.close();
}


async function runCase({ label, account, path, navText, waitFor, waitForPlaceholder, visible, hidden, afterChecks }) {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });

  try {
    await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
    await clearLoginState(page);
    await loginThroughUi(page, account.username, account.password);
    if (path) {
      await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
    } else {
      await clickMenu(page, navText);
    }
    await page.waitForTimeout(500);
    if (waitFor) {
      await page.getByText(waitFor, { exact: false }).first().waitFor({
        state: "visible",
        timeout: 15000,
      });
    }
    if (waitForPlaceholder) {
      await page.getByPlaceholder(waitForPlaceholder).first().waitFor({
        state: "visible",
        timeout: 15000,
      });
    }

    const visibleChecks = [];
    for (const text of visible) {
      visibleChecks.push({
        text,
        ok: await isTextVisible(page, text),
      });
    }

    const hiddenChecks = [];
    for (const text of hidden) {
      hiddenChecks.push({
        text,
        ok: !(await isTextVisible(page, text)),
      });
    }

    const afterResult = afterChecks ? await afterChecks(page) : { ok: true };
    const ok = visibleChecks.every((item) => item.ok)
      && hiddenChecks.every((item) => item.ok);

    return {
      label,
      ok: ok && afterResult.ok,
      visibleChecks,
      hiddenChecks,
      afterResult,
    };
  } finally {
    await page.close();
  }
}


async function clearLoginState(page) {
  await page.evaluate(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    localStorage.removeItem("position");
  });
  await page.reload({ waitUntil: "networkidle" });
}


async function loginThroughUi(page, username, password) {
  await page.getByRole("button", { name: /登录|未登录/ }).first().click();

  const modal = page.locator(".ant-modal").filter({
    hasText: /登录/,
  }).first();
  await modal.waitFor({ state: "visible", timeout: 15000 });
  await modal.locator("input").nth(0).fill(username);
  await modal.locator("input").nth(1).fill(password);
  await modal.locator(".ant-btn-primary").click();
  await page.waitForFunction(() => Boolean(localStorage.getItem("access_token")), undefined, {
    timeout: 20000,
  });
  await page.waitForLoadState("networkidle");
}


async function clickMenu(page, text) {
  const button = page.getByRole("button", { name: new RegExp(text) }).first();
  await button.waitFor({ state: "visible", timeout: 15000 });
  await button.click();
}


async function clickShortcut(page, blockText) {
  const block = page.locator(".dashboardShortcutCard").filter({
    hasText: blockText,
  }).first();
  await block.waitFor({ state: "visible", timeout: 15000 });
  await block.getByRole("button", { name: `打开 ${blockText}` }).click();
}


async function clickSegmentedItem(page, text) {
  const item = page.locator(".ant-segmented-item").filter({
    hasText: text,
  }).first();
  await item.waitFor({ state: "visible", timeout: 15000 });
  await item.click();
}


async function selectMarket(page, text) {
  const selector = page.locator(".dashboardMarketSelect").first();
  await selector.waitFor({ state: "visible", timeout: 15000 });
  await selector.click();
  const dropdown = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last();
  await dropdown.waitFor({ state: "visible", timeout: 15000 });
  const option = dropdown.locator(".ant-select-item-option").filter({
    hasText: text,
  }).first();
  await option.waitFor({ state: "visible", timeout: 15000 });
  await option.click();
  return true;
}


async function checkFormSelectOptions(page, { label, optionLabels, selectLabel }) {
  const formItem = page.locator(".ant-form-item").filter({
    hasText: label,
  }).first();
  await formItem.waitFor({ state: "visible", timeout: 15000 });
  await formItem.locator(".ant-select").click();
  const dropdown = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)").last();
  await dropdown.waitFor({ state: "visible", timeout: 15000 });
  const optionChecks = [];
  for (const labelText of optionLabels) {
    optionChecks.push({
      text: labelText,
      ok: await isDropdownOptionVisible(dropdown, labelText),
    });
  }
  await dropdown.locator(".ant-select-item-option").filter({ hasText: selectLabel }).first().click();
  await page.waitForTimeout(200);
  const selectedText = await formItem.locator(".ant-select-selection-item").first().textContent();
  const selected = String(selectedText || "").includes(selectLabel);
  return {
    ok: optionChecks.every((item) => item.ok) && selected,
    optionChecks,
    selected,
  };
}


async function isDropdownOptionVisible(dropdown, text) {
  try {
    await dropdown.locator(".ant-select-item-option").filter({ hasText: text }).first().waitFor({
      state: "visible",
      timeout: 5000,
    });
    return true;
  } catch {
    return false;
  }
}


async function isTextVisible(page, text) {
  try {
    return await page.getByText(text, { exact: false }).first().isVisible({
      timeout: 2500,
    });
  } catch {
    return false;
  }
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_frontend_permissions.mjs");
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
