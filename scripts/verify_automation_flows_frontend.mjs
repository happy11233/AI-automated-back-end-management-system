import { createRequire } from "node:module";


const require = createRequire(import.meta.url);
const { spawnSync } = require("node:child_process");
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
  const adminDesktop = await runAdminFlowCase();
  const forbiddenCases = [];
  for (const [name, account] of Object.entries(ACCOUNTS).filter(([name]) => name !== "admin")) {
    forbiddenCases.push(await runForbiddenRouteCase({
      label: `${name}_automation_flows_forbidden`,
      account,
      path: "/automation-flows",
      forbiddenText: "自动化流程配置",
    }));
  }
  const apiForbidden = await verifyApiForbidden("/automation-flows");

  console.log(JSON.stringify({
    ok: true,
    results: [adminDesktop, ...forbiddenCases],
    apiForbidden,
    note: "real browser, real frontend, real API login; flow config is admin-only; no mock/stub/fake",
  }, null, 2));
} finally {
  await browser.close();
}

async function runAdminFlowCase() {
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  const screenshot = "/tmp/company-rag-automation-flows-admin-desktop.png";
  const governanceMarker = `verify-flow-governance-ui-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  let cleanupResult = null;
  try {
    await loginAtPath(page, ACCOUNTS.admin, "/automation-flows");
    await Promise.all([
      page.waitForResponse(
        (response) => response.url().includes("/automation-flows") && response.status() === 200,
        { timeout: 30000 },
      ),
      page.goto(`${FRONTEND_URL}/automation-flows`, { waitUntil: "networkidle" }),
    ]);
    await page.getByText("自动化流程配置", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 30000,
    });
    await page.waitForTimeout(800);

    const listingFlowName = "Listing 全流程上架草稿";
    for (const text of ["自动化流程配置", listingFlowName, "详情"]) {
      const count = await page.getByText(text, { exact: false }).count();
      if (count === 0) {
        throw new Error(`admin_flow_configs_desktop: expected visible text ${text}`);
      }
    }

    const detailResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "GET"
        && response.url().includes("/automation-flows/")
        && !response.url().includes("/versions")
        && response.status() === 200
      ),
      { timeout: 15000 },
    );
    const targetRow = page.locator(".ant-table-row", { hasText: listingFlowName }).first();
    await targetRow.getByRole("button", { name: "详情" }).click();
    const flowDetailPayload = await (await detailResponse).json();
    const flowId = flowDetailPayload.item.id;
    let detailModal = flowDetailModal(page);
    await detailModal.getByRole("tab", { name: "基础信息" }).waitFor({
      state: "visible",
      timeout: 15000,
    });
    await openDetailTab(detailModal, "Schema");
    await detailModal.getByText("输入 Schema", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await openDetailTab(detailModal, "权限");
    await detailModal.getByText("允许工具", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await openDetailTab(detailModal, "步骤");
    await detailModal.getByText("步骤名称", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await openDetailTab(detailModal, "版本治理");
    await detailModal.getByText("版本列表", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });

    for (const text of ["版本治理", "创建草稿", "版本列表", "状态"]) {
      const count = await detailModal.getByText(text, { exact: false }).count();
      if (count === 0) {
        throw new Error(`admin_flow_governance_ui: expected visible text ${text}`);
      }
    }

    await detailModal.getByLabel("变更摘要").fill(`${governanceMarker} 前端版本治理入口验证`);
    await detailModal.getByLabel("审批策略").fill("前端治理入口验证：发布前由管理员确认。");
    await detailModal.getByLabel("失败策略").fill("前端治理入口验证：失败时保留运行记录并允许回滚。");
    await detailModal.getByLabel("发布说明").fill(`${governanceMarker} 发布说明`);

    const createdVersionPayload = await createFlowVersionByApi(flowId, governanceMarker);
    if (createdVersionPayload.item.status !== "draft") {
      throw new Error(`admin_flow_governance_ui: expected created draft, got ${createdVersionPayload.item.status}`);
    }

    await detailModal.locator(".ant-modal-footer .ant-btn").first().click();
    await detailModal.waitFor({ state: "hidden", timeout: 15000 });
    await page.goto(`${FRONTEND_URL}/automation-flows`, { waitUntil: "networkidle" });
    await page.getByText("自动化流程配置", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 30000,
    });
    await page.getByText(listingFlowName, { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    const reopenedDetailResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "GET"
        && response.url().includes("/automation-flows/")
        && !response.url().includes("/versions")
        && response.status() === 200
      ),
      { timeout: 15000 },
    );
    const reopenedTargetRow = page.locator(".ant-table-row", { hasText: listingFlowName }).first();
    await reopenedTargetRow.getByRole("button", { name: "详情" }).click();
    await reopenedDetailResponse;
    detailModal = flowDetailModal(page);
    await detailModal.getByRole("tab", { name: "基础信息" }).waitFor({
      state: "visible",
      timeout: 15000,
    });
    await openDetailTab(detailModal, "版本治理");
    await detailModal.getByText("版本列表", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });

    await expectFlowVersionInApi(flowId, createdVersionPayload.item.id, governanceMarker);
    const governanceRow = flowVersionRow(detailModal, createdVersionPayload.item.id);
    if (!(await governanceRow.count())) {
      await detailModal.locator(".ant-card", { hasText: "版本列表" })
        .first()
        .getByRole("button", { name: "刷新" })
        .click();
    }
    await governanceRow.waitFor({ state: "visible", timeout: 15000 });
    await governanceRow.getByText("草稿", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    for (const text of ["提交审核", "批准", "预检", "发布", "回滚"]) {
      const count = await governanceRow.getByText(text, { exact: false }).count();
      if (count === 0) {
        throw new Error(`admin_flow_governance_ui: expected row action ${text}`);
      }
    }

    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "载入");
    const promptSummaryText = `${governanceMarker} 前端低代码 Prompt 摘要编辑`;
    const promptTemplateText = `${createdVersionPayload.item.prompt_template_preview}\n\n# ${governanceMarker} 前端低代码 Prompt 模板编辑`;
    await detailModal.getByLabel("Prompt 摘要").fill(promptSummaryText);
    await detailModal.getByLabel("Prompt 模板预览").fill(promptTemplateText);
    const saveDraftResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedDraftPayload = await (await saveDraftResponse).json();
    if (savedDraftPayload.item.prompt_summary !== promptSummaryText) {
      throw new Error(`admin_flow_governance_ui: expected saved prompt summary, got ${JSON.stringify(savedDraftPayload)}`);
    }
    await expectFlowVersionPromptInApi(createdVersionPayload.item.id, promptSummaryText, governanceMarker);

    const editedInputSchema = JSON.parse(JSON.stringify(createdVersionPayload.item.input_schema || []));
    if (!editedInputSchema.length) {
      throw new Error(`admin_flow_governance_ui: expected non-empty input schema, got ${JSON.stringify(createdVersionPayload)}`);
    }
    editedInputSchema[0].label = `${governanceMarker} 输入字段治理编辑`;
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "载入");
    const inputSchemaEditor = detailModal.getByLabel("输入 Schema JSON");
    await inputSchemaEditor.waitFor({ state: "visible", timeout: 15000 });
    await inputSchemaEditor.fill(JSON.stringify(editedInputSchema, null, 2));
    const saveInputSchemaResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedInputSchemaPayload = await (await saveInputSchemaResponse).json();
    if (JSON.stringify(savedInputSchemaPayload.item.input_schema || []) !== JSON.stringify(editedInputSchema)) {
      throw new Error(`admin_flow_governance_ui: expected saved input schema, got ${JSON.stringify(savedInputSchemaPayload)}`);
    }
    await expectFlowVersionSchemaInApi(createdVersionPayload.item.id, "input_schema", editedInputSchema, "input schema");

    const editedOutputSchema = JSON.parse(JSON.stringify(createdVersionPayload.item.output_schema || []));
    if (!editedOutputSchema.length) {
      throw new Error(`admin_flow_governance_ui: expected non-empty output schema, got ${JSON.stringify(createdVersionPayload)}`);
    }
    editedOutputSchema[0].label = `${governanceMarker} 输出字段治理编辑`;
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "载入");
    const outputSchemaEditor = detailModal.getByLabel("输出 Schema JSON");
    await outputSchemaEditor.waitFor({ state: "visible", timeout: 15000 });
    await outputSchemaEditor.fill(JSON.stringify(editedOutputSchema, null, 2));
    const saveOutputSchemaResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedOutputSchemaPayload = await (await saveOutputSchemaResponse).json();
    if (JSON.stringify(savedOutputSchemaPayload.item.output_schema || []) !== JSON.stringify(editedOutputSchema)) {
      throw new Error(`admin_flow_governance_ui: expected saved output schema, got ${JSON.stringify(savedOutputSchemaPayload)}`);
    }
    await expectFlowVersionSchemaInApi(createdVersionPayload.item.id, "output_schema", editedOutputSchema, "output schema");

    const editedToolParameters = JSON.parse(JSON.stringify(createdVersionPayload.item.model_config?.tool_parameters || {}));
    if (!editedToolParameters["llm.chat"]) {
      throw new Error(`admin_flow_governance_ui: expected llm.chat tool parameters, got ${JSON.stringify(createdVersionPayload)}`);
    }
    editedToolParameters["llm.chat"].temperature = 0.4;
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "载入");
    const toolParametersEditor = detailModal.getByLabel("工具参数 JSON");
    await toolParametersEditor.waitFor({ state: "visible", timeout: 15000 });
    await toolParametersEditor.fill(JSON.stringify(editedToolParameters, null, 2));
    const saveToolParametersResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedToolParametersPayload = await (await saveToolParametersResponse).json();
    const savedToolParameters = savedToolParametersPayload.item.model_config?.tool_parameters || {};
    if (JSON.stringify(savedToolParameters) !== JSON.stringify(editedToolParameters)) {
      throw new Error(`admin_flow_governance_ui: expected saved tool parameters, got ${JSON.stringify(savedToolParametersPayload)}`);
    }
    await expectFlowVersionToolParametersInApi(createdVersionPayload.item.id, editedToolParameters);

    const preflightResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "POST"
        && response.url().includes("/automation-flow-versions/")
        && response.url().includes("/preflight")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "预检");
    const preflightPayload = await (await preflightResponse).json();
    if (preflightPayload.ok !== true) {
      throw new Error(`admin_flow_governance_ui: expected preflight ok, got ${JSON.stringify(preflightPayload)}`);
    }
    if (!preflightPayload.preflight_run_id) {
      throw new Error(`admin_flow_governance_ui: expected persisted preflight run id, got ${JSON.stringify(preflightPayload)}`);
    }
    if (!preflightPayload.checks.some((item) => item.key === "prompt_contract" && item.status === "passed")) {
      throw new Error(`admin_flow_governance_ui: expected prompt contract preflight, got ${JSON.stringify(preflightPayload)}`);
    }
    const regressionArtifacts = preflightPayload.checks
      .find((item) => item.key === "business_regression_binding")
      ?.artifacts || [];
    if (!regressionArtifacts.some((artifact) => artifact.script === "scripts/verify_platform_draft_automation.py")) {
      throw new Error(`admin_flow_governance_ui: expected business regression binding artifact, got ${JSON.stringify(preflightPayload)}`);
    }
    await detailModal.getByText("发布前预检", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("预检通过", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("Prompt 合同校验", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("发布验证", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("scripts/verify_platform_draft_automation.py", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });

    await setFlowVersionInputSchema(createdVersionPayload.item.id, [
      {
        name: "",
        label: "坏字段",
        type: "api_key",
      },
    ]);
    const failedPreflightResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "POST"
        && response.url().includes("/automation-flow-versions/")
        && response.url().includes("/preflight")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "预检");
    const failedPreflightPayload = await (await failedPreflightResponse).json();
    if (failedPreflightPayload.ok !== false) {
      throw new Error(`admin_flow_governance_ui: expected failed preflight, got ${JSON.stringify(failedPreflightPayload)}`);
    }
    const schemaRepairHints = failedPreflightPayload.checks
      .find((item) => item.key === "schema_contract")
      ?.repair_hints || [];
    if (!schemaRepairHints.some((hint) => hint.field_path === "input_schema[1].name")) {
      throw new Error(`admin_flow_governance_ui: expected schema repair hint, got ${JSON.stringify(failedPreflightPayload)}`);
    }
    await detailModal.getByText("修复建议", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("input_schema[1].name", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });

    await setFlowVersionInputSchema(createdVersionPayload.item.id, editedInputSchema);
    const restoredPreflightResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "POST"
        && response.url().includes("/automation-flow-versions/")
        && response.url().includes("/preflight")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "预检");
    const restoredPreflightPayload = await (await restoredPreflightResponse).json();
    if (restoredPreflightPayload.ok !== true) {
      throw new Error(`admin_flow_governance_ui: expected restored preflight ok, got ${JSON.stringify(restoredPreflightPayload)}`);
    }
    await detailModal.getByText("预检通过", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });

    const evidenceReportId = `${governanceMarker}-platform-draft-evidence`;
    await recordFlowVersionEvidence(createdVersionPayload.item.id, evidenceReportId);
    const evidencePayload = await expectFlowVersionEvidenceInApi(createdVersionPayload.item.id, evidenceReportId);
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "证据");
    if (!evidencePayload.items.some((item) => (
      item.report_id === evidenceReportId
      && item.is_current_version === true
      && item.matches_current_snapshot === true
      && item.is_publish_eligible === true
    ))) {
      throw new Error(`admin_flow_governance_ui: expected verification evidence list item, got ${JSON.stringify(evidencePayload)}`);
    }
    await detailModal.getByText("发布证据", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText(evidenceReportId, { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("可发布", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    await detailModal.getByText("scripts/verify_platform_draft_automation.py", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });

    const submitReviewResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "POST"
        && response.url().includes("/automation-flow-versions/")
        && response.url().includes("/submit-review")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "提交审核");
    const reviewingPayload = await (await submitReviewResponse).json();
    if (reviewingPayload.item.status !== "reviewing") {
      throw new Error(`admin_flow_governance_ui: expected reviewing, got ${reviewingPayload.item.status}`);
    }
    await governanceRow.getByText("审核中", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });

    const approveResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "POST"
        && response.url().includes("/automation-flow-versions/")
        && response.url().includes("/approve")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await clickFlowVersionAction(detailModal, createdVersionPayload.item.id, "批准");
    const approvedPayload = await (await approveResponse).json();
    if (approvedPayload.item.status !== "approved") {
      throw new Error(`admin_flow_governance_ui: expected approved, got ${approvedPayload.item.status}`);
    }
    await governanceRow.getByText("已通过", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });

    const publishButton = await visibleFlowVersionActionButton(detailModal, createdVersionPayload.item.id, "发布");
    if (!(await publishButton.isEnabled())) {
      throw new Error("admin_flow_governance_ui: publish entry is not enabled after approval");
    }
    const criticalEvidenceUi = await verifyCriticalEvidenceLabel(page, governanceMarker, {
      flowId: "automation:finance:salary-export",
      flowName: "统计工资",
      markerLabel: "高风险关键证据标签验证",
      expectedCriticalScripts: [
        "scripts/verify_chat_react_guardrails.py",
        "scripts/verify_finance_salary_export.py",
      ],
      subsetChecks: {
        removedTool: "openpyxl.write_workbook",
        retainedTool: "intent.recognizer",
        removedResource: "Salary Slip",
        removeLastStep: true,
      },
    });
    const customerServiceCriticalEvidenceUi = await verifyCriticalEvidenceLabel(page, governanceMarker, {
      flowId: "automation:customer_service:message-loop",
      flowName: "客服消息自动化闭环",
      markerLabel: "客服售后关键证据标签验证",
      expectedCriticalScripts: [
        "scripts/verify_customer_service_automation.py",
        "scripts/verify_customer_service_refund_approvals.py",
      ],
      subsetChecks: {
        reorderStep: {
          stepId: "rag_policy_lookup",
          previousStepId: "erp_permission_query",
        },
      },
    });

    const overflow = await assertNoHorizontalOverflow(page, "admin_flow_configs_desktop");
    await page.screenshot({ path: screenshot, fullPage: true });
    cleanupResult = await cleanupFlowGovernanceVersions(governanceMarker);

    return {
      label: "admin_flow_configs_desktop",
      screenshot,
      overflow,
      governance: {
        marker: governanceMarker,
        createdStatus: createdVersionPayload.item.status,
        preflightOk: preflightPayload.ok,
        preflightRunId: preflightPayload.preflight_run_id,
        regressionScript: regressionArtifacts[0]?.script,
        inputSchemaLabel: editedInputSchema[0]?.label,
        repairHintPath: schemaRepairHints[0]?.field_path,
        evidenceReportId,
        evidenceTotal: evidencePayload.total,
        criticalEvidenceUi,
        customerServiceCriticalEvidenceUi,
        submittedStatus: reviewingPayload.item.status,
        approvedStatus: approvedPayload.item.status,
        publishEntryEnabled: true,
        cleanup: cleanupResult,
      },
    };
  } finally {
    if (!cleanupResult) {
      await cleanupFlowGovernanceVersions(governanceMarker);
    }
    await context.close();
  }
}

async function verifyCriticalEvidenceLabel(page, marker, {
  flowId,
  flowName,
  markerLabel,
  expectedCriticalScripts,
  subsetChecks = null,
}) {
  const currentModal = flowDetailModal(page);
  if (await currentModal.count()) {
    await currentModal.locator(".ant-modal-footer .ant-btn").first().click();
    await currentModal.waitFor({ state: "hidden", timeout: 15000 });
  }

  const criticalVersionPayload = await createFlowVersionByApi(
    flowId,
    `${marker} ${markerLabel}`,
  );
  if (criticalVersionPayload.item.status !== "draft") {
    throw new Error(`admin_flow_governance_ui: expected critical evidence draft, got ${criticalVersionPayload.item.status}`);
  }

  await page.goto(`${FRONTEND_URL}/automation-flows`, { waitUntil: "networkidle" });
  await page.getByText("自动化流程配置", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 30000,
  });

  const detailResponse = page.waitForResponse(
    (response) => (
      response.request().method() === "GET"
      && response.url().includes("/automation-flows/")
      && !response.url().includes("/versions")
      && response.status() === 200
    ),
    { timeout: 15000 },
  );
  const flowRow = await findFlowConfigRow(page, flowName);
  await flowRow.getByRole("button", { name: "详情" }).click();
  const flowDetailPayload = await (await detailResponse).json();
  if (flowDetailPayload.item.id !== flowId) {
    throw new Error(`admin_flow_governance_ui: expected ${flowId} flow detail, got ${JSON.stringify(flowDetailPayload)}`);
  }

  const detailModal = flowDetailModal(page);
  await detailModal.getByRole("tab", { name: "基础信息" }).waitFor({
    state: "visible",
    timeout: 15000,
  });
  await openDetailTab(detailModal, "版本治理");
  await detailModal.getByText("版本列表", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });

  const criticalRow = flowVersionRow(detailModal, criticalVersionPayload.item.id);
  if (!(await criticalRow.count())) {
    await detailModal.locator(".ant-card", { hasText: "版本列表" })
      .first()
      .getByRole("button", { name: "刷新" })
      .click();
  }
  await criticalRow.waitFor({ state: "visible", timeout: 15000 });

  let savedTools = criticalVersionPayload.item.allowed_tools || [];
  let removedTool = null;
  let savedResources = criticalVersionPayload.item.allowed_erp_resources || [];
  let removedResource = null;
  const originalSteps = criticalVersionPayload.item.steps || [];
  let savedStepIds = originalSteps.map((item) => item.id);
  let removedStepId = null;
  let reorderedStepId = null;
  let reorderedPreviousStepId = null;

  if (subsetChecks?.removedTool) {
    await clickFlowVersionAction(detailModal, criticalVersionPayload.item.id, "载入");
    removedTool = subsetChecks.removedTool;
    await uncheckGovernanceCheckbox(detailModal, removedTool, removedTool);
    const saveToolsResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedToolsPayload = await (await saveToolsResponse).json();
    savedTools = savedToolsPayload.item.allowed_tools || [];
    if (savedTools.includes(removedTool) || (subsetChecks.retainedTool && !savedTools.includes(subsetChecks.retainedTool))) {
      throw new Error(`admin_flow_governance_ui: expected allowed tools subset, got ${JSON.stringify(savedToolsPayload)}`);
    }
    if (Object.hasOwn(savedToolsPayload.item.model_config?.tool_parameters || {}, removedTool)) {
      throw new Error(`admin_flow_governance_ui: expected removed tool parameters to be pruned, got ${JSON.stringify(savedToolsPayload)}`);
    }
    await expectFlowVersionAllowedToolsInApi(criticalVersionPayload.item.id, savedTools, [removedTool]);
  }

  if (subsetChecks?.removedResource) {
    await clickFlowVersionAction(detailModal, criticalVersionPayload.item.id, "载入");
    removedResource = subsetChecks.removedResource;
    await uncheckGovernanceCheckbox(detailModal, new RegExp(removedResource), removedResource);
    const saveResourcesResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedResourcesPayload = await (await saveResourcesResponse).json();
    savedResources = savedResourcesPayload.item.allowed_erp_resources || [];
    if (savedResources.some((item) => item.resource === removedResource)) {
      throw new Error(`admin_flow_governance_ui: expected allowed ERP resources subset, got ${JSON.stringify(savedResourcesPayload)}`);
    }
    await expectFlowVersionAllowedResourcesInApi(criticalVersionPayload.item.id, savedResources, [removedResource]);
  }

  if (subsetChecks?.removeLastStep && originalSteps.length > 1) {
    await clickFlowVersionAction(detailModal, criticalVersionPayload.item.id, "载入");
    const removedStep = originalSteps[originalSteps.length - 1];
    removedStepId = removedStep.id;
    await uncheckGovernanceCheckbox(detailModal, new RegExp(escapeRegExp(removedStep.id)), removedStep.id);
    const saveStepsResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedStepsPayload = await (await saveStepsResponse).json();
    const savedSteps = savedStepsPayload.item.steps || [];
    if (savedSteps.some((item) => item.id === removedStep.id) || !savedSteps.length) {
      throw new Error(`admin_flow_governance_ui: expected steps subset, got ${JSON.stringify(savedStepsPayload)}`);
    }
    savedStepIds = savedSteps.map((item) => item.id);
    await expectFlowVersionStepsInApi(criticalVersionPayload.item.id, savedSteps, [removedStep.id]);
  }

  if (subsetChecks?.reorderStep) {
    await clickFlowVersionAction(detailModal, criticalVersionPayload.item.id, "载入");
    await detailModal.getByText("投影步骤", { exact: false }).first().waitFor({ state: "visible", timeout: 15000 });
    reorderedStepId = subsetChecks.reorderStep.stepId;
    reorderedPreviousStepId = subsetChecks.reorderStep.previousStepId;
    const beforeOrder = await selectedStepOrderFromApi(criticalVersionPayload.item.id);
    const beforeIndex = beforeOrder.indexOf(reorderedStepId);
    const previousIndex = beforeOrder.indexOf(reorderedPreviousStepId);
    if (beforeIndex !== previousIndex + 1 || beforeIndex <= 0) {
      throw new Error(`admin_flow_governance_ui: expected adjacent reorderable steps, got ${JSON.stringify(beforeOrder)}`);
    }
    await detailModal.getByLabel(`上移步骤 ${reorderedStepId}`).click();
    const saveReorderedStepsResponse = page.waitForResponse(
      (response) => (
        response.request().method() === "PATCH"
        && response.url().includes("/automation-flow-versions/")
        && response.status() === 200
      ),
      { timeout: 30000 },
    );
    await detailModal.getByRole("button", { name: "保存草稿" }).click();
    const savedReorderedStepsPayload = await (await saveReorderedStepsResponse).json();
    const savedReorderedSteps = savedReorderedStepsPayload.item.steps || [];
    const reorderedIds = savedReorderedSteps.map((item) => item.id);
    if (reorderedIds.indexOf(reorderedStepId) !== previousIndex || reorderedIds.indexOf(reorderedPreviousStepId) !== beforeIndex) {
      throw new Error(`admin_flow_governance_ui: expected reordered steps, got ${JSON.stringify(savedReorderedStepsPayload)}`);
    }
    savedStepIds = reorderedIds;
    await expectFlowVersionStepsInApi(criticalVersionPayload.item.id, savedReorderedSteps, []);
  }

  const preflightResponse = page.waitForResponse(
    (response) => (
      response.request().method() === "POST"
      && response.url().includes("/automation-flow-versions/")
      && response.url().includes("/preflight")
      && response.status() === 200
    ),
    { timeout: 30000 },
  );
  await clickFlowVersionAction(detailModal, criticalVersionPayload.item.id, "预检");
  const preflightPayload = await (await preflightResponse).json();
  if (preflightPayload.ok !== true) {
    throw new Error(`admin_flow_governance_ui: expected critical evidence manual preflight ok, got ${JSON.stringify(preflightPayload)}`);
  }

  const regressionArtifacts = preflightPayload.checks
    .find((item) => item.key === "business_regression_binding")
    ?.artifacts || [];
  const criticalArtifacts = regressionArtifacts.filter((artifact) => artifact.publish_evidence_required === true);
  const criticalScripts = criticalArtifacts.map((artifact) => artifact.script).sort();
  const sortedExpectedCriticalScripts = [...expectedCriticalScripts].sort();
  if (JSON.stringify(criticalScripts) !== JSON.stringify(sortedExpectedCriticalScripts)) {
    throw new Error(`admin_flow_governance_ui: expected critical evidence scripts, got ${JSON.stringify(regressionArtifacts)}`);
  }

  await detailModal.getByText("关键证据", { exact: false }).first().waitFor({
    state: "visible",
    timeout: 15000,
  });
  for (const script of sortedExpectedCriticalScripts) {
    await detailModal.getByText(script, { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
  }
  const criticalTagCount = await detailModal
    .locator(".flowPreflightArtifactItem", { hasText: "关键证据" })
    .count();
  if (criticalTagCount !== expectedCriticalScripts.length) {
    throw new Error(`admin_flow_governance_ui: expected ${expectedCriticalScripts.length} critical evidence labels, got ${criticalTagCount}`);
  }

  return {
    versionId: criticalVersionPayload.item.id,
    flowKey: preflightPayload.flow_key,
    flowName,
    savedTools,
    removedTool,
    savedResources: savedResources.map((item) => item.resource),
    removedResource,
    savedStepIds,
    removedStepId,
    reorderedStepId,
    reorderedPreviousStepId,
    criticalScripts,
    criticalTagCount,
  };
}

async function runForbiddenRouteCase({ label, account, path, forbiddenText }) {
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await context.newPage();
  try {
    await loginAtPath(page, account, path);
    await page.waitForURL("**/dashboard", { timeout: 15000 });
    await page.getByText("概览", { exact: false }).first().waitFor({
      state: "visible",
      timeout: 15000,
    });
    await page.waitForTimeout(600);

    const forbiddenCount = await mainContent(page).getByText(forbiddenText, { exact: false }).count();
    if (forbiddenCount > 0) {
      throw new Error(`${label}: forbidden page text still visible`);
    }

    const overflow = await assertNoHorizontalOverflow(page, label);
    return {
      label,
      currentUrl: page.url(),
      overflow,
    };
  } finally {
    await context.close();
  }
}

async function verifyApiForbidden(path) {
  const results = [];
  for (const [name, account] of Object.entries(ACCOUNTS).filter(([name]) => name !== "admin")) {
    const token = await loginByApi(account);
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (response.status !== 403) {
      throw new Error(`${name}: expected ${path} to return 403, got ${response.status}: ${await response.text()}`);
    }
    results.push({ account: name, status: response.status });
  }
  return results;
}

async function expectFlowVersionInApi(flowId, versionId, marker) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flows/${encodeURIComponent(flowId)}/versions`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`list flow versions failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  if (!payload.items.some((item) => item.id === versionId && String(item.change_summary || "").includes(marker))) {
    throw new Error(`created flow version missing from API list: ${JSON.stringify(payload)}`);
  }
  return payload;
}

async function expectFlowVersionEvidenceInApi(versionId, reportId) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}/verification-evidence`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`list flow version evidence failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  if (!payload.items.some((item) => item.report_id === reportId)) {
    throw new Error(`created flow version evidence missing from API list: ${JSON.stringify(payload)}`);
  }
  return payload;
}

async function expectFlowVersionPromptInApi(versionId, promptSummary, promptMarker) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  const item = payload.item;
  if (item.prompt_summary !== promptSummary || !String(item.prompt_template_preview || "").includes(promptMarker)) {
    throw new Error(`saved prompt missing from API detail: ${JSON.stringify(payload)}`);
  }
  return payload;
}

async function expectFlowVersionSchemaInApi(versionId, fieldName, expectedSchema, schemaLabel) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version for ${schemaLabel} failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  const actualSchema = payload.item[fieldName] || [];
  if (JSON.stringify(actualSchema) !== JSON.stringify(expectedSchema)) {
    throw new Error(`saved ${schemaLabel} missing from API detail: ${JSON.stringify(payload)}`);
  }
  return payload;
}

async function expectFlowVersionToolParametersInApi(versionId, expectedToolParameters) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version for tool parameters failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  const actualToolParameters = payload.item.model_config?.tool_parameters || {};
  if (JSON.stringify(actualToolParameters) !== JSON.stringify(expectedToolParameters)) {
    throw new Error(`saved tool parameters missing from API detail: ${JSON.stringify(payload)}`);
  }
  return payload;
}

async function expectFlowVersionAllowedToolsInApi(versionId, expectedTools, removedTools = []) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version for tools failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  const actualTools = payload.item.allowed_tools || [];
  if (JSON.stringify(actualTools) !== JSON.stringify(expectedTools)) {
    throw new Error(`saved allowed tools missing from API detail: ${JSON.stringify(payload)}`);
  }
  for (const tool of removedTools) {
    if (actualTools.includes(tool)) {
      throw new Error(`removed allowed tool still present: ${tool} ${JSON.stringify(payload)}`);
    }
  }
  return payload;
}

async function expectFlowVersionAllowedResourcesInApi(versionId, expectedResources, removedResources = []) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version for ERP resources failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  const actualResources = payload.item.allowed_erp_resources || [];
  if (JSON.stringify(actualResources) !== JSON.stringify(expectedResources)) {
    throw new Error(`saved allowed ERP resources missing from API detail: ${JSON.stringify(payload)}`);
  }
  const actualKeys = actualResources.map((item) => item.resource);
  for (const resource of removedResources) {
    if (actualKeys.includes(resource)) {
      throw new Error(`removed allowed ERP resource still present: ${resource} ${JSON.stringify(payload)}`);
    }
  }
  return payload;
}

async function expectFlowVersionStepsInApi(versionId, expectedSteps, removedStepIds = []) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version for steps failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  const actualSteps = payload.item.steps || [];
  if (JSON.stringify(actualSteps) !== JSON.stringify(expectedSteps)) {
    throw new Error(`saved steps missing from API detail: ${JSON.stringify(payload)}`);
  }
  const actualStepIds = actualSteps.map((item) => item.id);
  for (const stepId of removedStepIds) {
    if (actualStepIds.includes(stepId)) {
      throw new Error(`removed step still present: ${stepId} ${JSON.stringify(payload)}`);
    }
  }
  return payload;
}

async function selectedStepOrderFromApi(versionId) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status !== 200) {
    throw new Error(`get flow version for step order failed: ${response.status} ${await response.text()}`);
  }
  const payload = await response.json();
  return (payload.item.steps || []).map((item) => item.id);
}

async function createFlowVersionByApi(flowId, marker) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flows/${encodeURIComponent(flowId)}/versions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      change_summary: `${marker} 前端版本治理入口验证`,
      approval_policy: "前端治理入口验证：发布前由管理员确认。",
      failure_strategy: "前端治理入口验证：失败时保留运行记录并允许回滚。",
      publish_notes: `${marker} 发布说明`,
    }),
  });
  if (response.status !== 200) {
    throw new Error(`create flow version failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

async function recordFlowVersionEvidence(versionId, reportId) {
  const token = await loginByApi(ACCOUNTS.admin);
  const response = await fetch(`${API_BASE_URL}/automation-flow-versions/${encodeURIComponent(versionId)}/verification-evidence`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      script: "scripts/verify_platform_draft_automation.py",
      command: ".venv/bin/python scripts/verify_platform_draft_automation.py",
      profile: "api",
      status: "passed",
      report_id: reportId,
      summary: "前端版本治理证据列表回归写入真实发布证据。",
      ttl_hours: 168,
      metadata: {
        verification: "real browser, real API, real PostgreSQL; no mock/stub/fake",
      },
    }),
  });
  if (response.status !== 200) {
    throw new Error(`record evidence failed: ${response.status} ${await response.text()}`);
  }
  return response.json();
}

async function uncheckGovernanceCheckbox(modal, roleName, wrapperText) {
  const checkbox = modal.getByRole("checkbox", { name: roleName }).first();
  await checkbox.waitFor({ state: "visible", timeout: 15000 });
  if (!(await checkbox.isChecked())) {
    return;
  }

  const wrapper = modal.locator(".ant-checkbox-wrapper", { hasText: wrapperText }).first();
  await wrapper.click();
  await modal.page().waitForTimeout(150);
  if (await checkbox.isChecked()) {
    await checkbox.click({ force: true });
    await modal.page().waitForTimeout(150);
  }
  if (await checkbox.isChecked()) {
    throw new Error(`checkbox should be unchecked: ${String(wrapperText)}`);
  }
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function openDetailTab(modal, name) {
  const page = modal.page();
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const candidates = [
      modal.getByRole("tab", { name }).first(),
      modal.locator(".ant-tabs-tab-btn", { hasText: name }).first(),
      modal.locator(".ant-tabs-tab", { hasText: name }).first(),
    ];
    for (const tab of candidates) {
      if (!(await tab.count())) {
        continue;
      }
      await tab.scrollIntoViewIfNeeded().catch(() => {});
      await tab.click({ force: true });
      await page.waitForTimeout(400);
      if (await modal.locator(".ant-tabs-tab-active", { hasText: name }).count()) {
        return;
      }
    }
  }

  throw new Error(`detail tab not active: ${name}`);
}

async function loginAtPath(page, account, path) {
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    localStorage.removeItem("position");
    localStorage.removeItem("allowed_ai_app_ids");
  });
  await page.goto(`${FRONTEND_URL}${path}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /登录|未登录/ }).first().click();
  const modal = page.locator(".ant-modal").filter({ hasText: /登录/ }).first();
  await modal.waitFor({ state: "visible", timeout: 10000 });
  await modal.locator("input").nth(0).fill(account.username);
  await modal.locator("input").nth(1).fill(account.password);
  const loginResponse = page.waitForResponse(
    (response) => response.url().includes("/auth/login") && response.status() === 200,
    { timeout: 30000 },
  );
  await page.locator(".ant-modal-footer .ant-btn-primary").click();
  await loginResponse;
  await page.waitForFunction(() => Boolean(window.localStorage.getItem("access_token")), null, {
    timeout: 10000,
  });
}

async function loginByApi(account) {
  const body = new URLSearchParams();
  body.set("username", account.username);
  body.set("password", account.password);
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
  if (response.status !== 200) {
    throw new Error(`login failed for ${account.username}: ${response.status} ${await response.text()}`);
  }
  return (await response.json()).access_token;
}

function mainContent(page) {
  return page.locator(".ant-pro-page-container").first();
}

function flowDetailModal(page) {
  return page.locator(".ant-modal:visible")
    .filter({ hasText: "流程配置 /" })
    .first();
}

function flowVersionRow(modal, versionId) {
  return modal.locator(`.ant-table-row[data-row-key="${versionId}"]`).first();
}

async function findFlowConfigRow(page, flowName) {
  const table = page.locator(".flowConfigTable").first();
  await table.waitFor({ state: "visible", timeout: 15000 });

  for (let pageIndex = 0; pageIndex < 8; pageIndex += 1) {
    const row = table.locator(".ant-table-row", { hasText: flowName }).first();
    if (await row.count()) {
      await row.scrollIntoViewIfNeeded();
      return row;
    }

    const nextButton = table.locator(".ant-pagination-next").first();
    if (!(await nextButton.count())) {
      break;
    }
    const className = await nextButton.getAttribute("class") || "";
    if (className.includes("ant-pagination-disabled")) {
      break;
    }
    await nextButton.click();
    await page.waitForTimeout(400);
  }

  throw new Error(`flow config row not visible: ${flowName}`);
}

async function visibleFlowVersionActionButton(modal, versionId, name) {
  const rows = modal.locator(`.ant-table-row[data-row-key="${versionId}"]`);
  await rows.first().waitFor({ state: "attached", timeout: 15000 });

  const exactButtons = rows.getByRole("button", { name });
  const count = await exactButtons.count();
  for (let index = 0; index < count; index += 1) {
    const button = exactButtons.nth(index);
    if (await button.isVisible()) {
      return button;
    }
  }

  const targetName = compactButtonName(name);
  const buttons = rows.getByRole("button");
  await buttons.first().waitFor({ state: "attached", timeout: 15000 });
  const fallbackCount = await buttons.count();
  for (let index = 0; index < fallbackCount; index += 1) {
    const button = buttons.nth(index);
    const accessibleName = await button.getAttribute("aria-label");
    const visibleText = await button.innerText();
    if (compactButtonName(accessibleName || visibleText) === targetName && await button.isVisible()) {
      return button;
    }
  }

  throw new Error(`flow version action button not visible: ${versionId} ${name}`);
}

async function clickFlowVersionAction(modal, versionId, name) {
  await (await visibleFlowVersionActionButton(modal, versionId, name)).click();
}

function compactButtonName(value) {
  return String(value || "").replace(/\s+/g, "");
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

async function setFlowVersionInputSchema(versionId, inputSchema) {
  const pythonBin = process.env.VERIFY_PYTHON || ".venv/bin/python";
  const updateCode = `
import json
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from app.config import settings

version_id = os.environ["VERIFY_FLOW_VERSION_ID"]
input_schema = json.loads(os.environ["VERIFY_FLOW_INPUT_SCHEMA"])
database_url = os.getenv("DATABASE_URL", settings.database_url)

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE automation_flow_versions
            SET input_schema = %s::jsonb, updated_at = now()
            WHERE id = %s;
            """,
            (json.dumps(input_schema, ensure_ascii=False), version_id),
        )
        if cur.rowcount != 1:
            raise RuntimeError(f"version not found: {version_id}")
    conn.commit()
`;
  const result = spawnSync(pythonBin, ["-c", updateCode], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      VERIFY_FLOW_VERSION_ID: versionId,
      VERIFY_FLOW_INPUT_SCHEMA: JSON.stringify(inputSchema),
    },
    encoding: "utf8",
  });

  if (result.status !== 0) {
    throw new Error(`flow version input schema update failed: ${result.stderr || result.stdout}`);
  }
}

async function cleanupFlowGovernanceVersions(marker) {
  const pythonBin = process.env.VERIFY_PYTHON || ".venv/bin/python";
  const cleanupCode = `
import json
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from app.config import settings

marker = os.environ["VERIFY_FLOW_GOVERNANCE_MARKER"]
database_url = os.getenv("DATABASE_URL", settings.database_url)

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM automation_flow_versions
            WHERE change_summary LIKE %s
               OR publish_notes LIKE %s;
            """,
            (f"%{marker}%", f"%{marker}%"),
        )
        version_ids = [str(row[0]) for row in cur.fetchall()]
        deleted_publications = 0
        deleted_versions = 0
        if version_ids:
            cur.execute(
                "DELETE FROM automation_flow_publications WHERE version_id = ANY(%s);",
                (version_ids,),
            )
            deleted_publications = cur.rowcount
            cur.execute(
                "DELETE FROM automation_flow_versions WHERE id = ANY(%s);",
                (version_ids,),
            )
            deleted_versions = cur.rowcount
    conn.commit()

print(json.dumps({
    "marker": marker,
    "deleted_versions": deleted_versions,
    "deleted_publications": deleted_publications,
}, ensure_ascii=False))
`;
  const result = spawnSync(pythonBin, ["-c", cleanupCode], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      VERIFY_FLOW_GOVERNANCE_MARKER: marker,
    },
    encoding: "utf8",
  });

  if (result.status !== 0) {
    throw new Error(`flow governance cleanup failed: ${result.stderr || result.stdout}`);
  }

  try {
    return JSON.parse(result.stdout.trim() || "{}");
  } catch {
    return { marker, stdout: result.stdout.trim() };
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

  throw new Error("Cannot find Playwright. Run with: npx -p playwright node scripts/verify_automation_flows_frontend.mjs");
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
