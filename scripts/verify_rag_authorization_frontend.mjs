import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
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
};

const browser = await chromium.launch({
  headless: true,
  executablePath: CHROME_EXECUTABLE_PATH,
});

try {
  const adminDesktop = await runAdminDocumentsCase({
    label: "admin_rag_authorization_desktop",
    viewport: { width: 1440, height: 960 },
    screenshot: "/tmp/company-rag-authorization-admin-desktop.png",
    mutate: true,
  });
  const adminMobile = await runAdminDocumentsCase({
    label: "admin_rag_authorization_mobile",
    viewport: { width: 390, height: 844 },
    screenshot: "/tmp/company-rag-authorization-admin-mobile.png",
    mutate: false,
  });
  const employeeForbidden = await runEmployeeForbiddenCase();

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, adminMobile, employeeForbidden],
    note: "real browser, real frontend, real API login/mutations; no mock/stub/fake",
  }, null, 2));
} finally {
  await Promise.race([
    browser.close(),
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
}

process.exit(0);

async function runAdminDocumentsCase({ label, viewport, screenshot, mutate }) {
  const page = await browser.newPage({ viewport });
  let token = "";
  let createdTeamId = "";
  let createdMemberUserId = "";
  let uploadedDocumentId = "";
  let createdDrawerGrantId = "";
  let drawerOperationResult = null;
  let listedDocuments = { items: [], total: 0 };

  try {
    await page.goto(`${FRONTEND_URL}/documents`, { waitUntil: "networkidle" });
    token = await login(page, ACCOUNTS.admin);
    listedDocuments = await apiRequest(token, "/documents?limit=1", { method: "GET" });

    const teamLoad = page.waitForResponse(
      (response) => responseMatches(response, "/rag-teams", "GET", 200),
      { timeout: 30000 },
    ).catch(() => null);
    await page.goto(`${FRONTEND_URL}/documents`, { waitUntil: "networkidle" });
    await teamLoad;
    await mainContent(page).getByText("上传入库", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 30000,
    });

    await assertVisibleTexts(page, label, ["上传入库", "团队管理", "文档授权"]);
    await openDocumentsTab(page, "上传入库");
    await assertVisibleTexts(page, label, [
      "上传知识库",
      "上传访问模式",
      "上传 owner 用户",
      "上传 owner 团队",
      "初始授权对象类型",
      "初始授权对象",
      "初始授权级别",
      "初始授权原因",
    ]);
    await openDocumentsTab(page, "团队管理");
    await assertVisibleTexts(page, label, ["团队 key", "团队名称", "团队列表", "团队成员", "添加成员"]);

    if (mutate) {
      const marker = `verify_rag_ui_${Date.now()}`;
      const teamCard = mainContent(page).locator(".ant-pro-card", { hasText: "团队 key" }).first();
      if (await formInput(teamCard, "团队 key").isDisabled()) {
        await teamCard.locator(".ant-pro-card-extra .ant-btn").nth(1).click({ force: true });
        await page.waitForTimeout(200);
      }
      await formInput(teamCard, "团队 key").fill(marker);
      await formInput(teamCard, "团队名称").fill(`${marker} 授权组`);
      await formTextArea(teamCard, "描述").fill("RAG 授权管理前端真实验证临时团队");

      const [createTeamResult] = await Promise.all([
        page.waitForResponse(
          (response) => responseMatches(response, "/rag-teams", "POST", 200),
          { timeout: 30000 },
        ),
        teamCard.getByRole("button", { name: /创建团队/ }).click(),
      ]);
      const teamPayload = await createTeamResult.json();
      createdTeamId = teamPayload.item.id;
      await mainContent(page).getByText(marker, { exact: false }).first().waitFor({
        state: "visible",
        timeout: 15000,
      });

      const memberCard = mainContent(page).locator(".ant-pro-card", { hasText: "团队成员" }).first();
      await selectAntOption(page, formItem(memberCard, "成员"), "operations_demo");
      const [createMemberResult] = await Promise.all([
        page.waitForResponse(
          (response) => responsePathPattern(response, /^\/(?:api\/)?rag-teams\/[^/]+\/members$/, "POST", 200),
          { timeout: 30000 },
        ),
        memberCard.getByRole("button", { name: /添加成员/ }).click(),
      ]);
      const memberPayload = await createMemberResult.json();
      if (memberPayload.item.team_id !== createdTeamId) {
        throw new Error(`created member team mismatch: ${JSON.stringify(memberPayload.item)}`);
      }
      createdMemberUserId = memberPayload.item.user_id;
      await memberCard.getByText("operations_demo", { exact: false }).first().waitFor({
        state: "visible",
        timeout: 15000,
      });
    }

    await openDocumentsTab(page, "文档授权");
    await assertVisibleTexts(page, label, [
      "文档列表",
      "搜索文档",
      "搜索",
      "文档访问模式",
      "文档 ID",
      "加载文档",
      "文档授权名单",
    ]);

    if (mutate) {
      drawerOperationResult = await runDrawerAuthorizationMutation(page, token);
      uploadedDocumentId = drawerOperationResult.documentId;
      createdDrawerGrantId = drawerOperationResult.grantId;
      await refreshDocumentListFromUi(page, drawerOperationResult.marker);
    }

    const targetDocument = mutate && uploadedDocumentId
      ? { id: uploadedDocumentId, title: drawerOperationResult.title }
      : listedDocuments.items[0];

    if (!mutate && targetDocument) {
      const documentListCard = mainContent(page).locator(".ant-pro-card", { hasText: "文档列表" }).first();
      const documentSearch = formInput(documentListCard, "搜索文档");
      await documentListCard.getByRole("button", { name: /授权详情/ }).first().waitFor({
        state: "visible",
        timeout: 15000,
      });
      await documentSearch.fill(targetDocument.title);

      const accessResponse = page.waitForResponse(
        (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/access$/, "GET", 200),
        { timeout: 30000 },
      );
      const grantsResponse = page.waitForResponse(
        (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/grants$/, "GET", 200),
        { timeout: 30000 },
      );
      await documentListCard.getByRole("button", { name: /授权详情/ }).first().click();
      const [accessResult] = await Promise.all([accessResponse, grantsResponse]);
      const accessPayload = await accessResult.json();
      await mainContent(page).getByText(accessPayload.item.id, { exact: false }).first().waitFor({
        state: "visible",
        timeout: 15000,
      });
      const drawer = page.locator(".ant-drawer").filter({ hasText: "文档授权详情" }).first();
      await drawer.waitFor({ state: "visible", timeout: 15000 });
      for (const text of ["访问模式", "owner 用户", "owner 团队", "保存访问模式", "显式授权", "添加授权"]) {
        await drawer.getByText(text, { exact: false }).first().waitFor({
          state: "visible",
          timeout: 15000,
        });
      }
    }

    const overflow = await assertNoHorizontalOverflow(page, label);
    await page.screenshot({ path: screenshot, fullPage: true });

    return {
      label,
      screenshot,
      createdTeamId,
      uploadedDocumentId,
      drawerOperationResult,
      documentListTotal: listedDocuments.total,
      overflow,
    };
  } finally {
    if (token && createdDrawerGrantId && uploadedDocumentId) {
      await apiRequest(token, `/documents/${uploadedDocumentId}/grants/${createdDrawerGrantId}`, { method: "DELETE" })
        .catch(() => null);
    }
    if (drawerOperationResult?.marker) {
      await cleanupUploadedDocuments(drawerOperationResult.marker);
    }
    if (token && createdTeamId && createdMemberUserId) {
      await apiRequest(token, `/rag-teams/${createdTeamId}/members/${createdMemberUserId}`, { method: "DELETE" });
    }
    if (token && createdTeamId) {
      await apiRequest(token, `/rag-teams/${createdTeamId}`, {
        method: "PATCH",
        body: {
          status: "archived",
        },
      });
    }
    await page.close();
  }
}

async function runEmployeeForbiddenCase() {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await page.goto(`${FRONTEND_URL}/documents`, { waitUntil: "networkidle" });
  await login(page, ACCOUNTS.operations);
  await page.goto(`${FRONTEND_URL}/documents`, { waitUntil: "networkidle" });
  await mainContent(page).getByText("概览", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  for (const text of ["团队管理", "文档授权", "上传知识库"]) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count > 0) {
      throw new Error(`employee should not see RAG authorization text: ${text}`);
    }
  }

  const overflow = await assertNoHorizontalOverflow(page, "employee_rag_authorization_forbidden");
  const currentUrl = page.url();
  await page.close();
  return {
    label: "employee_rag_authorization_forbidden",
    currentUrl,
    overflow,
  };
}

async function runDrawerAuthorizationMutation(page, token) {
  const marker = `verify_rag_ui_drawer_${Date.now()}`;
  const title = `${marker}.txt`;
  try {
    const operationsUser = await findUserByUsername(token, "operations_demo");
    const uploaded = await uploadTemporaryDocument(token, {
      filename: title,
      content: `${marker} 文档授权详情抽屉真实操作回归。`,
      data: {
        visibility: "employee",
        position_scope: "operations",
        field_scope: "operations_listing",
        sensitivity_level: "internal",
        access_mode: "open",
      },
    });
    const documentId = uploaded.document_id;

    await refreshDocumentListFromUi(page, marker);
    const drawer = await openAuthorizationDrawer(page, title);

    await selectAntOption(page, formItem(drawer, "访问模式"), "显式授权");
    const [accessSaveResult] = await Promise.all([
      page.waitForResponse(
        (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/access$/, "PATCH", 200),
        { timeout: 30000 },
      ),
      drawer.getByRole("button", { name: /保存访问模式/ }).click(),
    ]);
    const accessPayload = await accessSaveResult.json();
    if (accessPayload.item.access_mode !== "explicit_grants") {
      throw new Error(`drawer access save did not persist explicit_grants: ${JSON.stringify(accessPayload.item)}`);
    }
    await drawer.getByText("文档访问模式已保存", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    }).catch(() => null);

    await selectAntOption(page, formItem(drawer, "授权对象"), "operations_demo");
    await formInput(drawer, "授权原因").fill("verify-rag-ui-drawer-grant");
    const [createGrantResult] = await Promise.all([
      page.waitForResponse(
        (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/grants$/, "POST", 200),
        { timeout: 30000 },
      ),
      drawer.getByRole("button", { name: /添加授权/ }).click(),
    ]);
    const grantPayload = await createGrantResult.json();
    const grant = grantPayload.item;
    if (grant.document_id !== documentId || grant.subject_id !== operationsUser.id || grant.status !== "active") {
      throw new Error(`drawer grant create mismatch: ${JSON.stringify(grant)}`);
    }
    await drawer.getByText("operations_demo", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });

    const grantRow = drawer.locator(".ant-table-row", { hasText: "verify-rag-ui-drawer-grant" })
      .filter({ hasText: "启用" })
      .first();
    const grantsTable = drawer.locator(".ant-table-wrapper", { hasText: "verify-rag-ui-drawer-grant" }).first();
    await grantsTable.locator(".ant-table-body, .ant-table-content").first().evaluate((element) => {
      element.scrollLeft = element.scrollWidth;
    }).catch(() => null);
    const revokeButton = grantRow.getByRole("button", { name: /撤销/ }).first();
    await revokeButton.waitFor({ state: "visible", timeout: 15000 });
    const confirmPopover = page.locator(".ant-popover", { hasText: "撤销文档授权" }).first();
    await revokeButton.scrollIntoViewIfNeeded();
    await revokeButton.click({ force: true });
    await confirmPopover.waitFor({ state: "visible", timeout: 15000 });
    await confirmPopover.getByText("撤销文档授权", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    const [revokeGrantResult] = await Promise.all([
      page.waitForResponse(
        (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/grants\/[^/]+$/, "DELETE", 200),
        { timeout: 30000 },
      ),
      confirmPopover.locator(".documentGrantRevokeConfirmButton").click(),
    ]);
    const revokedPayload = await revokeGrantResult.json();
    if (revokedPayload.item.status !== "revoked") {
      throw new Error(`drawer grant revoke mismatch: ${JSON.stringify(revokedPayload.item)}`);
    }
    await drawer.getByText("已撤销", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });

    return {
      marker,
      title,
      documentId,
      accessMode: accessPayload.item.access_mode,
      grantId: grant.id,
      revokedStatus: revokedPayload.item.status,
    };
  } catch (error) {
    await cleanupUploadedDocuments(marker).catch(() => null);
    throw error;
  }
}

async function refreshDocumentListFromUi(page, marker) {
  const authorizationDrawer = page.locator(".ant-drawer", { hasText: "文档授权详情" }).first();
  if (await authorizationDrawer.isVisible().catch(() => false)) {
    await page.goto(`${FRONTEND_URL}/documents`, { waitUntil: "networkidle" });
    await mainContent(page).getByText("上传入库", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 30000,
    });
    await openDocumentsTab(page, "文档授权");
  }
  const documentListCard = mainContent(page).locator(".ant-pro-card", { hasText: "文档列表" }).first();
  const documentSearch = formInput(documentListCard, "搜索文档");
  await documentSearch.fill(marker);
  const [listResponse] = await Promise.all([
    page.waitForResponse(
      (response) => responseMatches(response, "/documents", "GET", 200),
      { timeout: 30000 },
    ),
    documentListCard.getByRole("button", { name: /搜索/ }).click(),
  ]);
  await listResponse;
  await documentListCard.getByText(marker, { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
}

async function openAuthorizationDrawer(page, title) {
  const documentListCard = mainContent(page).locator(".ant-pro-card", { hasText: "文档列表" }).first();
  const accessResponse = page.waitForResponse(
    (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/access$/, "GET", 200),
    { timeout: 30000 },
  );
  const grantsResponse = page.waitForResponse(
    (response) => responsePathPattern(response, /^\/(?:api\/)?documents\/[^/]+\/grants$/, "GET", 200),
    { timeout: 30000 },
  );
  await documentListCard.locator(".ant-table-row", { hasText: title }).first().getByRole("button", { name: /授权详情/ }).click();
  await Promise.all([accessResponse, grantsResponse]);
  const drawer = page.locator(".ant-drawer").filter({ hasText: "文档授权详情" }).first();
  await drawer.waitFor({ state: "visible", timeout: 15000 });
  await drawer.getByText(title, { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  return drawer;
}

async function findUserByUsername(token, username) {
  const users = await apiRequest(token, "/admin/users", { method: "GET" });
  const user = users.items.find((item) => item.username === username);
  if (!user) {
    throw new Error(`cannot find required user: ${username}`);
  }
  return user;
}

async function uploadTemporaryDocument(token, { filename, content, data }) {
  const form = new FormData();
  form.append("file", new Blob([content], { type: "text/plain" }), filename);
  for (const [key, value] of Object.entries(data)) {
    form.append(key, value);
  }

  const response = await fetch(`${API_BASE_URL}/admin/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });
  if (!response.ok) {
    throw new Error(`temporary document upload failed: HTTP ${response.status} ${await response.text()}`);
  }
  return response.json();
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
    (response) => responseMatches(response, "/auth/login", "POST", 200),
    { timeout: 30000 },
  );
  await page.locator(".ant-modal-footer .ant-btn-primary").click();
  const response = await loginResponse;
  const payload = await response.json();
  await page.waitForFunction(() => Boolean(window.localStorage.getItem("access_token")), null, {
    timeout: 10000,
  });
  return payload.access_token;
}

async function openDocumentsTab(page, name) {
  const tab = mainContent(page).locator(".ant-tabs-tab", { hasText: name }).first();
  await tab.click({ force: true });
  await page.waitForTimeout(300);
}

async function assertVisibleTexts(page, label, texts) {
  for (const text of texts) {
    const count = await mainContent(page).getByText(text, { exact: false }).count();
    if (count === 0) {
      throw new Error(`${label}: expected visible text ${text}`);
    }
  }
}

function formItem(scope, label) {
  return scope.locator(".ant-form-item", { hasText: label }).first();
}

function formInput(scope, label) {
  return formItem(scope, label).locator("input").first();
}

function formTextArea(scope, label) {
  return formItem(scope, label).locator("textarea").first();
}

async function selectAntOption(page, item, text) {
  const selector = item.locator(".ant-select-selector").first();
  await selector.waitFor({ state: "visible", timeout: 15000 });
  try {
    await selector.click({ force: true });
  } catch (error) {
    if (!String(error).includes("outside of the viewport")) {
      throw error;
    }
    await selector.evaluate((element) => {
      if (window.PointerEvent) {
        element.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, cancelable: true, button: 0 }));
        element.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, cancelable: true, button: 0 }));
      }
      element.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
      element.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true }));
      element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    });
  }
  const option = page.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option", {
    hasText: text,
  }).first();
  await option.waitFor({ state: "visible", timeout: 15000 });
  await option.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    const eventInit = {
      bubbles: true,
      cancelable: true,
      button: 0,
      buttons: 1,
      clientX: rect.left + Math.min(rect.width / 2, 24),
      clientY: rect.top + Math.min(rect.height / 2, 16),
    };
    if (window.PointerEvent) {
      element.dispatchEvent(new PointerEvent("pointerdown", eventInit));
      element.dispatchEvent(new PointerEvent("pointerup", { ...eventInit, buttons: 0 }));
    }
    element.dispatchEvent(new MouseEvent("mousedown", eventInit));
    element.dispatchEvent(new MouseEvent("mouseup", { ...eventInit, buttons: 0 }));
    element.dispatchEvent(new MouseEvent("click", { ...eventInit, buttons: 0 }));
  });
  await item.locator(".ant-select-selection-item", { hasText: text }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  await page.waitForTimeout(200);
}

function mainContent(page) {
  return page.locator(".ant-pro-page-container").first();
}

function responseMatches(response, path, method, status) {
  const url = new URL(response.url());
  return response.request().method() === method
    && response.status() === status
    && (url.pathname === path || url.pathname === `/api${path}`);
}

function responsePathPattern(response, pattern, method, status) {
  const url = new URL(response.url());
  return response.request().method() === method
    && response.status() === status
    && pattern.test(url.pathname);
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

async function apiRequest(token, path, options) {
  const headers = {
    Authorization: `Bearer ${token}`,
    ...(options.body ? { "Content-Type": "application/json" } : {}),
  };
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`${path} cleanup failed: HTTP ${response.status} ${await response.text()}`);
  }
  return response.json();
}

async function cleanupUploadedDocuments(marker) {
  const python = path.join(process.cwd(), ".venv", "bin", "python");
  const pythonExecutable = fs.existsSync(python) ? python : "python3";
  const script = `
from app.config import settings
import psycopg

marker = ${JSON.stringify(marker)}
with psycopg.connect(settings.database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE source LIKE %s;", (f"upload/{marker}%",))
    conn.commit()
`;
  const { spawnSync } = require("node:child_process");
  const result = spawnSync(pythonExecutable, ["-c", script], {
    cwd: process.cwd(),
    encoding: "utf-8",
    env: process.env,
  });
  if (result.status !== 0) {
    throw new Error(`cleanup uploaded documents failed: ${result.stderr || result.stdout}`);
  }
}

function requirePlaywright() {
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_rag_authorization_frontend.mjs");
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
