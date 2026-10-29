import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync, existsSync, readdirSync } from "node:fs";
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
const base = process.env.VERIFY_FRONTEND_URL || "http://127.0.0.1:5173";
const browser = await playwright.chromium.launch({ headless: true, args: ["--no-proxy-server"] });
const errors = [], results = [];
async function session(name) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: "reduce" });
  await context.addInitScript((session) => {
    for (const key of ["access_token", "username", "role", "position"]) if (session[key]) localStorage.setItem(key, session[key]);
    localStorage.setItem("allowed_ai_app_ids", JSON.stringify(session.allowed_ai_app_ids));
  }, state.accounts[name].session);
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(name+": "+error.message));
  return { context, page };
}
async function go(page, path) {
  const competitor = path.includes('operations-competitor-analysis');
  const response = page.waitForResponse((response) => new URL(response.url()).pathname === (competitor ? '/api/competitor-monitor' : '/api/ai-workflows/activity'));
  await page.goto(base+path, { waitUntil: "domcontentloaded" });
  assert.equal((await response).status(), 200, path);
  if (competitor) {
    await page.locator('.competitorMonitor').waitFor();
    await page.getByRole('button', { name: '开始分析', exact: true }).waitFor();
    return;
  }
  await page.locator(".agentWorkspace").waitFor();
  await page.locator(".agentMetric strong").first().filter({ hasText: /^\d+$/ }).waitFor();
  if (new URL(page.url()).pathname !== "/agents") await page.locator(".agentMainGrid").waitFor();
  else await page.locator(".agentCatalogCard").first().waitFor();
}
async function tab(page, name) { const target=page.getByRole("tab", { name, exact:true }); await target.click(); assert.equal(await target.getAttribute("aria-selected"),"true"); }
async function overflow(page, label) {
  const sizes=await page.evaluate(() => ({ width:innerWidth, scroll:document.documentElement.scrollWidth }));
  assert(sizes.scroll<=sizes.width+2,label+": "+JSON.stringify(sizes));
}
try {
  const { context, page } = await session("admin");
  await go(page,"/agents");
  assert.equal(await page.getByText("岗位应用",{exact:true}).count(),0);
  assert.equal(await page.locator(".agentCatalogCard").count(),6);
  assert.equal(await page.locator(".agentWorkspace textarea").count(),0);
  const catalog=page.locator(".agentCatalogCard");
  await page.getByPlaceholder("搜索任务名称或业务场景").fill("__no_agent__");
  await page.getByText("没有匹配的 Agent",{exact:true}).waitFor();
  await page.getByPlaceholder("搜索任务名称或业务场景").fill("");
  await catalog.first().waitFor();
  const counts=await page.locator(".agentMetric strong").allTextContents();
  const response=page.waitForResponse((response)=>new URL(response.url()).pathname==="/api/ai-workflows/activity"&&new URL(response.url()).searchParams.get("status")==="failed");
  await page.locator(".agentMetric-red").click();
  assert.equal((await response).status(),200);
  await page.getByRole("tab",{name:"执行概览",selected:true}).waitFor();
  await page.locator(".agentRecordFilters .ant-select-selection-item").filter({hasText:"执行异常"}).waitFor();
  assert.deepEqual(await page.locator(".agentMetric strong").allTextContents(),counts);
  assert((await page.locator(".agentRunItem .ant-tag").allTextContents()).every((text)=>text==="执行异常"));
  await page.locator(".workspaceTrendSvg").waitFor();
  await go(page,"/agents/operations-listing-launch");
  for (const name of ["执行记录","业务成果","自动化规则","任务概况"]) await tab(page,name);
  assert.equal(await page.locator(".agentWorkspace textarea").count(),0);
  assert.equal(await page.getByRole("button",{name:"运行工作流",exact:true}).count(),0);
  await tab(page,"自动化规则");
  await page.getByRole("button",{name:"技术详情",exact:true}).click();
  await page.locator(".aiWorkflowDetailTabs").waitFor();
  await page.locator(".ant-modal:visible .ant-modal-close").click();
  for (const [legacy,target] of [
    ["/ai-apps","/agents"], ["/ai-workflows/operations-competitor-analysis","/agents/operations-competitor-analysis"],
    ["/automation/operations/title","/agents/operations-listing-launch"],
    ["/automation/customer-service/auto-reply","/agents/customer-service-message-loop"],
    ["/automation/finance/excel-upload","/agents/finance-excel-settlement"],
    ["/automation/finance/reconciliation","/agents/finance-reconciliation"],
  ]) { await go(page,legacy); await page.waitForURL(base+target); }
  results.push("legacy_routes_and_no_manual_generation");
  for(const width of [1440,1024,768,390]) {
    await page.setViewportSize({width,height:1000});
    for(const path of ["/agents","/agents/operations-listing-launch","/agents/customer-service-message-loop","/agents/finance-report-analysis"]) {
      await go(page,path); await overflow(page,path+" "+width);
      if(path!=="/agents") for(const name of ["执行记录","业务成果","自动化规则","任务概况"]) { await tab(page,name); await overflow(page,name+" "+width); }
      if(path!=="/agents") {
        const labels = await page.locator(".agentFlowSteps .ant-typography").evaluateAll((nodes) => nodes.map((node) => ({ width:node.getBoundingClientRect().width, height:node.getBoundingClientRect().height })));
        assert(labels.length===4 && labels.every((label)=>label.width>60 && label.height<60), "Flow labels must not collapse into narrow number badges");
      }
    }
    await go(page,"/agents/operations-listing-launch");
    await page.getByRole("tab", {name:"任务概况",selected:true}).waitFor();
    await page.screenshot({path:"/tmp/company-agent-workspace-"+width+".png",fullPage:true});
    results.push("responsive_"+width);
  }
  await context.close();
  for(const [name,path,forbidden] of [
    ["operations","/automation/operations/title","/agents/finance-report-analysis"],
    ["customer_service","/automation/customer-service/auto-reply","/agents/finance-report-analysis"],
    ["finance","/automation/finance/excel-upload","/agents/operations-listing-launch"],
  ]) {
    const {context,page}=await session(name);
    await go(page,path);
    await tab(page,"自动化规则");
    assert.equal(await page.getByRole("button",{name:"技术详情",exact:true}).count(),0);
    assert.equal(await page.getByText("岗位应用",{exact:true}).count(),0);
    await page.goto(base+forbidden,{waitUntil:"domcontentloaded"});
    await page.waitForURL("**/dashboard");
    await page.goto(base+"/dashboard",{waitUntil:"domcontentloaded"});
    await page.locator(".workspacePageContainer").waitFor();
    assert.equal(await page.getByText("岗位应用",{exact:true}).count(),0);
    if(name==="customer_service") {
      await page.goto(base+"/automation/customer-service-inbox",{waitUntil:"domcontentloaded"});
      await page.locator(".workspacePageContainer").waitFor();
      assert.equal(new URL(page.url()).pathname,"/automation/customer-service-inbox");
    }
    results.push(name+"_permissions_and_migration");
    await context.close();
  }
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({ok:true,results,browser:"Chromium",api:"real local API",errors},null,2));
} finally { await browser.close(); }
