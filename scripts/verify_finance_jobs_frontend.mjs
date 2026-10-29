// Real browser/API/queue acceptance. Infrastructure must already be running.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { existsSync, readdirSync, readFileSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
const npx = join(homedir(), '.npm/_npx');
let playwright;
for (const name of [process.env.PLAYWRIGHT_MODULE_PATH, 'playwright', ...(existsSync(npx) ? readdirSync(npx).map((name) => join(npx, name, 'node_modules/playwright')) : [])].filter(Boolean)) {
  try { const runtime = require(name); if (existsSync(runtime.chromium.executablePath())) { playwright = runtime; break; } } catch {}
}
assert(playwright, 'Installed Playwright Chromium required');
const base = process.env.VERIFY_FRONTEND_URL || 'http://127.0.0.1:5173';
const api = process.env.VERIFY_API_BASE_URL || 'http://127.0.0.1:8001';
const fixture = process.argv[2];
const existingJobId = process.env.VERIFY_EXISTING_JOB_ID;
if (!existingJobId) assert(fixture && existsSync(fixture), 'Provide a real settlement.xlsx fixture path');
const output = 'data/verification/finance-jobs';
mkdirSync(output, { recursive: true });
const browser = await playwright.chromium.launch({ headless: true, args: ['--no-proxy-server'] });
const errors = [];
let context;
try {
  const login = await fetch(api + '/auth/login', { method: 'POST', body: new URLSearchParams({ username: 'finance_demo', password: 'Finance123456' }) });
  assert.equal(login.status, 200);
  const session = await login.json();
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  await context.addInitScript((session) => {
    for (const key of ['access_token', 'username', 'role', 'position']) if (session[key]) localStorage.setItem(key, session[key]);
    localStorage.setItem('allowed_ai_app_ids', JSON.stringify(session.allowed_ai_app_ids));
  }, session);
  const page = await context.newPage();
  page.on('pageerror', (error) => errors.push(error.message));
  const route = '/automation/finance/reconciliation';
  await page.goto(base + route, { waitUntil: 'domcontentloaded' });
  await page.getByTestId('finance-background-jobs').waitFor();
  await page.getByRole('tab', { name: '对账任务', selected: true }).waitFor();
  if (existingJobId) {
    await page.getByText(existingJobId.slice(0, 8), { exact: true }).waitFor();
    await page.goto(base + '/dashboard', { waitUntil: 'domcontentloaded' });
    await page.goto(base + route, { waitUntil: 'domcontentloaded' });
    await page.getByText(existingJobId.slice(0, 8), { exact: true }).waitFor();
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.getByText(existingJobId.slice(0, 8), { exact: true }).waitFor();
    await page.screenshot({ path: join(output, 'desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: join(output, 'mobile.png'), fullPage: true });
    const sizes = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
    assert(sizes.scroll <= sizes.width + 2, 'Mobile page must fit the viewport');
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ok: true, checks: ['legacy_route_defaults_to_jobs', 'persisted_job_survives_navigation_and_reload', 'mobile_layout'], screenshots: [output + '/desktop.png', output + '/mobile.png'], errors }));
  } else {
  await page.locator('input[type=file]').setInputFiles(fixture);
  const marker = 'finance-jobs-browser-' + Date.now();
  await page.getByRole('textbox', { name: '对账要求' }).fill(marker);
  const submitted = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/jobs/finance-reconciliation' && response.request().method() === 'POST');
  await page.getByRole('button', { name: '提交后台对账' }).click();
  const response = await submitted;
  assert.equal(response.status(), 202);
  const job = await response.json();
  assert.equal(job.status, 'queued');
  await page.getByText(job.id.slice(0, 8), { exact: true }).waitFor();
  const row = () => page.getByRole('row').filter({ hasText: job.id.slice(0, 8) });
  if (process.env.VERIFY_EXPECT_QUEUED === '1') await row().getByText('排队中', { exact: true }).waitFor();
  await page.goto(base + '/dashboard', { waitUntil: 'domcontentloaded' });
  await page.goto(base + route, { waitUntil: 'domcontentloaded' });
  await page.getByText(job.id.slice(0, 8), { exact: true }).waitFor();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByText(job.id.slice(0, 8), { exact: true }).waitFor();
  console.log(JSON.stringify({ phase: 'persisted_after_navigation_and_reload', job_id: job.id, request_id: response.headers()['x-request-id'], marker }));
  await row().getByText('已完成', { exact: true }).waitFor({ timeout: 240000 });
  const downloaded = page.waitForEvent('download');
  await row().getByRole('button', { name: '下载对账结果' }).click();
  const download = await downloaded;
  assert.equal(await download.failure(), null);
  await download.saveAs(join(output, 'result.xlsx'));
  assert.equal(readFileSync(join(output, 'result.xlsx')).subarray(0, 2).toString(), 'PK');
  await page.screenshot({ path: join(output, 'desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: join(output, 'mobile.png'), fullPage: true });
  const sizes = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  assert(sizes.scroll <= sizes.width + 2, 'Mobile page must fit the viewport');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ok: true, job_id: job.id, checks: ['real_login', '202_submission', 'navigation', 'reload', 'persistent_result', 'authenticated_download', 'mobile_layout'], screenshots: [output + '/desktop.png', output + '/mobile.png'], errors }));
  }
} finally { await context?.close(); await browser.close(); }
