import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

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
      label: "finance_ai_apps_scoped",
      account: ACCOUNTS.finance,
      path: "/ai-apps",
      waitFor: "财务 ERP 查询",
      visible: ["AI 应用中心", "财务 ERP 查询", "财务 AI 对话", "财务 Excel 生成", "运行记录中心接入后显示真实数据"],
      hidden: ["运营 ERP 查询", "客服 ERP 查询", "知识库维护", "审计与权限追踪"],
    },
    {
      label: "admin_dashboard_shortcuts_visible",
      account: ACCOUNTS.admin,
      path: "/dashboard",
      waitFor: "ERP 连接",
      visible: ["管理员快捷入口", "用户管理", "AI 应用中心", "知识库上传", "审计日志", "平台数据概览", "ERP 连接", "全部", "美国", "德国", "日本", "全部时间", "今天", "近7天", "近30天", "全部店铺", "US Store", "DE Store", "JP Store"],
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
      visible: ["客服岗位", "客户资料"],
      hidden: ["管理员 ERP 诊断", "用户管理", "知识库"],
    },
    {
      label: "finance_excel_visible",
      account: ACCOUNTS.finance,
      path: "/automation",
      waitFor: "上传 Excel 生成新表",
      visible: ["财务 AI 自动化", "上传 Excel 生成新表", "生成并下载 Excel"],
      hidden: ["客服 AI 自动化", "运营 AI 自动化", "用户管理", "知识库"],
    },
    {
      label: "finance_dashboard_shortcuts_visible",
      account: ACCOUNTS.finance,
      path: "/dashboard",
      waitFor: "财务数据概览",
      visible: ["岗位快捷入口", "财务 Excel 生成", "财务 ERP 查询", "财务 AI 对话", "岗位数据概览", "财务数据概览", "全部站点", "全部店铺", "全部时间", "销售发票", "收付款单", "总账分录", "匹配", "发票金额"],
      hidden: ["用户管理", "知识库上传", "客服 AI 对话", "运营 AI 自动化"],
      afterChecks: async (page) => {
        await clickShortcut(page, "财务 Excel 生成");
        await page.waitForURL("**/ai-apps", { timeout: 10000 });
        return {
          ok: await isTextVisible(page, "AI 应用中心") && await isTextVisible(page, "财务 Excel 生成"),
          currentUrl: page.url(),
        };
      },
    },
    {
      label: "customer_service_excel_hidden",
      account: ACCOUNTS.customer_service,
      path: "/automation",
      waitFor: "退款售后话术",
      visible: ["客服 AI 自动化", "退款售后话术"],
      hidden: ["上传 Excel 生成新表", "财务 AI 自动化", "用户管理", "知识库"],
    },
    {
      label: "customer_service_dashboard_shortcuts_visible",
      account: ACCOUNTS.customer_service,
      path: "/dashboard",
      waitFor: "客服数据概览",
      visible: ["岗位快捷入口", "客服 AI 对话", "客服 ERP 查询", "客服自动化", "岗位数据概览", "客服数据概览", "全部站点", "全部店铺", "全部时间", "物流/出库单", "售后工单", "客户资料", "匹配"],
      hidden: ["用户管理", "知识库上传", "财务 Excel 生成", "运营 AI 自动化"],
    },
    {
      label: "operations_position_visible_only",
      account: ACCOUNTS.operations,
      path: "/automation",
      waitFor: "竞品分析",
      visible: ["运营 AI 自动化", "竞品分析"],
      hidden: ["客服 AI 自动化", "财务 AI 自动化", "上传 Excel 生成新表", "用户管理", "知识库"],
    },
    {
      label: "operations_dashboard_shortcuts_visible",
      account: ACCOUNTS.operations,
      path: "/dashboard",
      waitFor: "运营数据概览",
      visible: ["岗位快捷入口", "运营 AI 自动化", "运营 ERP 查询", "AI 对话", "岗位数据概览", "运营数据概览", "全部站点", "全部店铺", "全部时间", "销售订单", "商品资料", "商品价格", "匹配", "订单金额"],
      hidden: ["用户管理", "知识库上传", "财务 Excel 生成", "客服 AI 对话"],
      afterChecks: async (page) => {
        await clickSegmentedItem(page, "德国");
        await clickSegmentedItem(page, "近30天");
        await clickSegmentedItem(page, "DE Store");
        await page.getByText("德国站", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        await page.getByText("DE Store", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        await page.getByText("近 30 天", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        await page.locator(".dashboardOverviewCard").first().getByRole("button", { name: /ERP 详情/ }).first().click();
        await page.getByText("ERP 记录详情", { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
        return {
          ok: await isTextVisible(page, "德国站") && await isTextVisible(page, "近 30 天") && await isTextVisible(page, "DE Store") && await isTextVisible(page, "ERP 记录详情"),
          currentUrl: page.url(),
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
      path: "/erp",
      waitFor: "总账分录",
      visible: ["财务岗位", "总账分录"],
      hidden: [],
      afterChecks: async (page) => {
        await page.goto(`${FRONTEND_URL}/ai-apps`, { waitUntil: "networkidle" });
        await page.waitForURL("**/ai-apps", { timeout: 10000 });
        const automationVisible = await isTextVisible(page, "财务 Excel 生成");
        await page.goBack({ waitUntil: "networkidle" });
        await page.waitForURL("**/erp", { timeout: 10000 });
        const erpVisible = await isTextVisible(page, "财务岗位");

        return {
          ok: automationVisible && erpVisible,
          automationUrl: page.url().includes("/erp") ? "checked_after_back" : page.url(),
          automationVisible,
          erpVisible,
        };
      },
    },
    {
      label: "employee_admin_url_shows_forbidden_hint",
      account: ACCOUNTS.customer_service,
      path: "/users",
      visible: ["概览", "当前账号没有权限访问该页面，已返回概览。"],
      hidden: ["用户管理"],
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


async function runCase({ label, account, path, navText, waitFor, visible, hidden, afterChecks }) {
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
    hasText: "登录 Company RAG Agent",
  });
  await modal.waitFor({ state: "visible", timeout: 15000 });
  await modal.locator("input").nth(0).fill(username);
  await modal.locator("input").nth(1).fill(password);
  await modal.locator(".ant-btn-primary").click();
  await page.waitForSelector(".ant-modal", {
    state: "hidden",
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


async function isTextVisible(page, text) {
  try {
    return await page.getByText(text, { exact: false }).first().isVisible({
      timeout: 2500,
    });
  } catch {
    return false;
  }
}
