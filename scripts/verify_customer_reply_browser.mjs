import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawn } from "node:child_process";

const require = createRequire(import.meta.url);
const cache = join(homedir(), ".npm/_npx");
let playwright;
for (const candidate of [process.env.PLAYWRIGHT_MODULE_PATH, "playwright", ...(existsSync(cache) ? readdirSync(cache).map((name) => join(cache, name, "node_modules/playwright")) : [])].filter(Boolean)) {
  try {
    const runtime = require(candidate);
    if (existsSync(runtime.chromium.executablePath())) { playwright = runtime; break; }
  } catch { /* Try the next installed runtime. */ }
}
assert(playwright, "Installed Playwright Chromium required");
const api = process.env.VERIFY_API_BASE_URL;
assert(api && process.env.VERIFY_REPLY_USERNAME && process.env.VERIFY_REPLY_PASSWORD);
const base = "http://127.0.0.1:5188";
const output = join(process.cwd(), "data/verification/customer-reply");
mkdirSync(output, { recursive: true });
const vite = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5188", "--strictPort"], {
  cwd: join(process.cwd(), "frontend"), env: { ...process.env, VITE_API_BASE_URL: api }, stdio: "ignore",
});
let browser;
try {
  const deadline = Date.now() + 30000;
  while (true) {
    if (vite.exitCode !== null) throw new Error("Isolated frontend server failed to start");
    try {
      if ((await fetch(base, { signal: AbortSignal.timeout(1000) })).ok) break;
    } catch { /* Await the real frontend response. */ }
    assert(Date.now() < deadline, "Frontend startup timeout");
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  browser = await playwright.chromium.launch({ headless: true, args: ["--no-proxy-server"] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.setDefaultTimeout(30000);
  await page.goto(base + "/automation/customer-service-inbox", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /登录|未登录/ }).first().click();
  const modal = page.locator(".ant-modal:visible").first();
  await modal.locator("input").nth(0).fill(process.env.VERIFY_REPLY_USERNAME);
  await modal.locator("input").nth(1).fill(process.env.VERIFY_REPLY_PASSWORD);
  const login = page.waitForResponse((r) => r.url() === api + "/auth/login" && r.request().method() === "POST");
  await modal.locator(".ant-modal-footer .ant-btn-primary").click();
  assert.equal((await login).status(), 200);
  await page.goto(base + "/automation/customer-service-inbox", { waitUntil: "domcontentloaded" });
  const row = page.locator("tr").filter({ hasText: process.env.VERIFY_REPLY_SUBJECT }).first();
  await row.waitFor();
  await row.getByRole("button", { name: /^详\s*情$/ }).click();
  await page.getByText("客户回复正文（草稿）", { exact: true }).waitFor();
  await page.getByText("客服内部处理建议", { exact: true }).waitFor();
  await page.getByText("需要人工复核", { exact: true }).waitFor();
  const blocks = page.locator(".customerInboxResultBlock");
  const customerText = await blocks.filter({ hasText: "客户回复正文（草稿）" }).locator(".customerInboxResultText").innerText();
  const staffText = await blocks.filter({ hasText: "客服内部处理建议" }).locator(".customerInboxResultText").innerText();
  assert(customerText.trim() && staffText.trim() && customerText !== staffText);
  await page.screenshot({ path: join(output, "desktop.png"), fullPage: true });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator("tr").filter({ hasText: process.env.VERIFY_REPLY_SUBJECT }).first().getByRole("button", { name: /^详\s*情$/ }).click();
  await page.getByText("客户回复正文（草稿）", { exact: true }).waitFor();
  assert.equal(await blocks.filter({ hasText: "客户回复正文（草稿）" }).locator(".customerInboxResultText").innerText(), customerText);
  assert.equal(await blocks.filter({ hasText: "客服内部处理建议" }).locator(".customerInboxResultText").innerText(), staffText);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByText("客服内部处理建议", { exact: true }).scrollIntoViewIfNeeded();
  const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  assert(dimensions.scroll <= dimensions.width + 2, JSON.stringify(dimensions));
  await page.screenshot({ path: join(output, "mobile.png"), fullPage: true });
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ok: true, realLogin: true, isolatedApi: api,
    checks: ["customer_staff_blocks", "review_required", "reload_persistence", "mobile_overflow"],
    screenshots: [join(output, "desktop.png"), join(output, "mobile.png")] }));
} finally {
  await browser?.close();
  if (vite.exitCode === null) {
    const stopped = new Promise((resolve) => vite.once("exit", resolve));
    vite.kill("SIGTERM");
    await stopped;
  }
}
