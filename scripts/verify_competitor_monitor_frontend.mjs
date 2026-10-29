// UI-only regression: route fixtures come from the actual MockPriceProvider.
// Real PostgreSQL/authentication checks live in verify_competitor_monitor.py.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { existsSync, mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const require = createRequire(import.meta.url);
const npx = join(homedir(), '.npm/_npx');
let playwright;
for (const candidate of [process.env.PLAYWRIGHT_MODULE_PATH, 'playwright', ...(existsSync(npx) ? readdirSync(npx).map(name => join(npx, name, 'node_modules/playwright')) : [])].filter(Boolean)) {
  try { const runtime = require(candidate); if (existsSync(runtime.chromium.executablePath())) { playwright = runtime; break; } } catch {}
}
assert(playwright, 'Installed Playwright browser required');
const fixtures = JSON.parse(readFileSync(process.argv[2] || 'data/competitor-ui-fixtures.json', 'utf8'));
const base = process.env.VERIFY_FRONTEND_URL || 'http://127.0.0.1:5173';
const browser = await playwright.chromium.launch({ headless: true, args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
let history = [], failure = false, writes = 0;
const dashboard = () => ({ provider: 'mock', latest: history.at(-1) || null, history,
  schedule: { timezone: 'Asia/Shanghai', times: ['08:00', '11:00', '14:00', '16:00'], next_run_at: '2026-10-22T08:00:00+08:00', completed_today: 0, scheduler_healthy: false, status_label: '后台调度待就绪' },
  official_api: { status: 'not_connected', label: '官方开放 API 尚未接入' } });
await context.route('**/api/competitor-monitor**', async route => {
  if (route.request().method() === 'POST') {
    writes++;
    await new Promise(resolve => setTimeout(resolve, 150));
    if (failure) return route.fulfill({ status: 503, json: { detail: '测试中的模拟故障' } });
    const latest = fixtures[history.length % fixtures.length];
    history = [...history.filter(item => item.id !== latest.id), latest];
    return route.fulfill({ json: latest });
  }
  return route.fulfill({ json: dashboard() });
});
await context.route('**/__competitor_ui_test', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width, initial-scale=1" /><style>body{margin:0;padding:28px;background:#f4f6fa;font-family:system-ui}*{box-sizing:border-box}</style></head><body><div id="root"></div><script type="module">import RefreshRuntime from "/@react-refresh"; RefreshRuntime.injectIntoGlobalHook(window); window.$RefreshReg$=()=>{}; window.$RefreshSig$=()=>type=>type; window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">import React from "/node_modules/.vite/deps/react.js"; import ReactDOMClient from "/node_modules/.vite/deps/react-dom_client.js"; import {CompetitorMonitor} from "/src/components/CompetitorMonitor.tsx"; localStorage.setItem("access_token","competitor-ui-only"); ReactDOMClient.createRoot(document.getElementById("root")).render(React.createElement(CompetitorMonitor,{token:"competitor-ui-only",role:"admin",onNavigate:()=>{}}));</script></body></html>' }));
try {
  await page.goto(base + '/__competitor_ui_test', { waitUntil: 'domcontentloaded' });
  await page.getByText('还没有价格对比结果', { exact: true }).waitFor({ timeout: 60000 });
  assert.equal(await page.locator('.competitorHero button').count(), 2);
  for (const time of ['08:00', '11:00', '14:00', '16:00']) assert((await page.locator('.competitorSchedule').innerText()).includes(time));
  await page.getByRole('button', { name: '开始分析', exact: true }).click();
  await page.locator('.competitorProduct').first().waitFor();
  assert.equal(await page.locator('.competitorProduct').count(), 3);
  assert.equal(await page.locator('.competitorBarRow').count(), 12);
  assert.equal(writes, 1);
  await page.reload();
  await page.locator('.competitorProduct').first().waitFor();
  assert.equal(await page.locator('.competitorProduct').count(), 3);
  await page.getByRole('button', { name: '开始分析', exact: true }).click();
  await page.locator('.competitorHistory svg').first().waitFor();
  assert.equal(await page.locator('.competitorHistory svg').count(), 3);
  await page.getByRole('button', { name: /接入官方开放 API/ }).click();
  await page.getByText('尚未接入 · 当前继续使用模拟数据', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  mkdirSync('data/competitor-monitor-screenshots', { recursive: true });
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.waitForTimeout(150);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    assert(!overflow, 'Horizontal overflow at ' + width);
    if (width === 1440 || width === 390) await page.screenshot({ path: 'data/competitor-monitor-screenshots/' + width + '.png', fullPage: true });
  }
  failure = true;
  await page.getByRole('button', { name: '开始分析', exact: true }).click();
  await page.getByText('当前展示最近一次成功结果', { exact: true }).waitFor();
  assert.equal(await page.locator('.competitorProduct').count(), 3);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ok: true, evidence: 'UI-only routed fixtures from actual mock provider', checks: ['empty_state', 'two_actions_only', 'four_schedule_times', 'manual_charts', 'reload_restore', 'price_history', 'official_API_modal', 'responsive_1440_1024_768_390', 'failure_preserves_result', 'no_browser_errors'] }));
} catch (error) {
  console.error(JSON.stringify({browserErrors:errors,body:await page.locator("body").innerText()}));
  throw error;
} finally {
  await browser.close();
}
