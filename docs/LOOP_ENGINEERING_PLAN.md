# Loop Engineering Plan

## Goal

Upgrade Company RAG Agent into an enterprise AI automation platform for Amazon cross-border ecommerce teams.

The platform must evolve from role pages and AI chat into a controlled operating system for internal AI work:

- AI app catalog
- Automation flows
- Real run records
- Connector center
- Permission governance
- Effect analytics
- AI evaluation
- Monitoring and release checks

## Non-Negotiable Rules

- Work in small loops. Do not combine unrelated platform refactors with feature delivery.
- Keep compatibility with existing APIs until their replacement is fully verified.
- Do not revert user changes or unrelated files.
- Do not add mock, stub, fake provider, monkeypatch, or simulated response tests into the project code.
- Every validation must use real services where applicable: real backend, real database, real login accounts, real ERPNext, real browser, real file upload/download.
- Each loop must finish with verification, documentation, review notes, and a commit before the next loop starts.
- If a loop touches frontend layout, capture browser screenshots and check overflow.

## Agent Team

| Agent | Responsibility |
| --- | --- |
| Project Manager Agent | Defines loop scope, acceptance criteria, and completion decision. |
| Architecture Agent | Designs data model, API boundaries, module ownership, migration order, and compatibility strategy. |
| Development Agent | Implements backend and frontend changes within assigned file scopes. |
| Code Review Agent | Reviews defects, security risk, regressions, missing tests, and unclear ownership. |
| Testing Agent | Runs real API, real DB, real ERPNext, real browser, and real file workflow checks. |
| Security Agent | Checks RBAC, position scope, field scope, token expiry, credentials, audit logs, and AI context leakage. |
| DevOps Agent | Checks build, startup, Docker, environment, deployment notes, and Gitee state. |
| Documentation Agent | Updates long-term context, task list, changelog, user/admin docs, and operation notes. |
| Monitoring Agent | Designs run records, metrics, failure tracking, and operational visibility. |
| Page Quality Agent | Uses real browser screenshots and external SaaS/AI admin references to check modern layout quality. |

## Reference Products

These references guide product structure and quality expectations:

- Microsoft Copilot Studio: agent governance, DLP, connectors, analytics.
- Salesforce Agentforce: agent builder, actions, data, testing, deployment.
- ServiceNow AI Agent Studio: agent and workflow lifecycle.
- UiPath Orchestrator: jobs, queues, audit, monitoring.
- Zendesk and Intercom: customer service AI handoff, knowledge, analytics.

References are for product benchmarking, not for copying UI or proprietary text.

## Target Platform Modules

| Module | Existing Base | Target Direction |
| --- | --- | --- |
| AI App Center | `/automation/tasks`, chat, finance Excel, RAG | Register role AI capabilities as apps with status, owner, metrics, and version metadata. |
| Automation Flows | `automation_service.py`, LangGraph workflow, approvals | Add flow definitions, versions, triggers, steps, approval policies, and execution entry points. |
| Run Records | `chat_messages`, `audit_logs`, approvals | Add unified run and run step records for every AI app or workflow execution. |
| Connector Center | `app/erp/*`, MCP, Feishu | Register ERPNext, Kingdee, Yonyou, Amazon SP-API, logistics, ads, files, and office tools as connectors. |
| Permission Governance | role, position, ERP scopes | Move toward role + position + resource + field + store + marketplace scopes. |
| Effect Analytics | dashboard, audit logs | Show automation count, success rate, saved time, handoff rate, approval blocks, and failure reasons. |
| AI Evaluation Center | `eval/*.jsonl`, RAG scripts | Manage datasets, cases, evaluation runs, pass/fail results, and release gates. |
| Monitoring | health endpoint, diagnostics | Add service status, recent failures, latency, ERP health, AI call failure rate, and build version. |

## Loop Roadmap

### Loop 0: Engineering Rules And Acceptance Docs

Deliverables:

- `docs/LOOP_ENGINEERING_PLAN.md`
- `docs/AI_PLATFORM_REQUIREMENTS.md`
- `docs/UI_QUALITY_CHECKLIST.md`
- `docs/SECURITY_CHECKLIST.md`
- `docs/REAL_TESTING_POLICY.md`

Acceptance:

- Multi-agent responsibilities are clear.
- No-mock real testing policy is written as a hard rule.
- Future loops have clear scope and verification gates.
- Existing project memory is updated.

### Loop 1: Enterprise Navigation And Read-Only AI App Center

Scope:

- Add enterprise platform navigation shape without breaking existing pages.
- Add an AI App Center page that registers existing operations, customer service, finance, chat, RAG, ERP, and Excel capabilities.
- Keep execution logic unchanged.

Acceptance:

- Admin can see all app categories.
- Employees only see apps available to their role/position.
- Existing automation, ERP, chat, users, documents, approvals, audit, and thread pages still work.
- Real frontend build and browser layout checks pass.

### Loop 2: Unified Run Records

Scope:

- Add real database tables for `automation_runs`, `automation_run_steps`, and artifacts or references.
- Record existing `/automation/generate`, finance Excel, chat ERP, and ERP query executions.
- Keep audit logs for compliance; do not use audit logs as the only run record source.

Acceptance:

- Each supported real execution creates a queryable run record.
- Run details show input preview, status, duration, user, position, resource, and error if any.
- No secret or full sensitive input is stored.

### Loop 3: Automation Flow Configuration

Scope:

- Add flow metadata and version fields for current role tasks.
- Start with configuration views and read-only detail before allowing full editing.
- Keep existing hardcoded fallback until DB-backed flow config is fully verified.

Acceptance:

- Admin can inspect prompt, input schema, output schema, allowed resources, and approval policy.
- Employees cannot edit flow configuration.

### Loop 4: Connector Center

Scope:

- Register ERPNext, Kingdee, Yonyou, Amazon SP-API placeholder, logistics, ads, Feishu, email, and Excel connectors.
- Expose connector health, resource catalog, field mapping, and permission scope.

Acceptance:

- ERPNext real diagnostic remains `ok`.
- Employees cannot view secrets or admin connector diagnostics.
- Admin can see masked config and real status.

### Loop 5: Effect Analytics

Scope:

- Build analytics from real run records and audit events.
- Show saved time, app usage, success rate, failure rate, approval blocks, ERP query count, and role usage.

Acceptance:

- Metrics come from real persisted data.
- Empty state works when no run records exist.
- Cards and tables do not overflow.

### Loop 6: AI Evaluation Center

Scope:

- Wrap existing RAG and ERP evaluation scripts into a managed page and API.
- Support real dataset upload or selection, real evaluation execution, and result history.

Acceptance:

- Evaluations run against real backend and configured model/retriever.
- Permission and overreach cases are included.

## Per-Loop Gate

Each loop must pass the relevant subset:

- Real backend compile or startup check.
- Real API checks through HTTP.
- Real role login checks with demo accounts.
- Real ERPNext diagnostics if ERP or connector behavior changed.
- Real frontend build.
- Real browser screenshots for changed pages.
- Real permission regression checks.
- Code review and security review.
- Documentation update.
- Commit and push when complete.

## Demo Accounts For Real Verification

Use existing real demo accounts:

- `admin_demo / Admin123456`
- `operations_demo / Operations123456`
- `employee_demo / Employee123456`
- `finance_demo / Finance123456`

Do not bypass login in final acceptance. Browser setup may seed local storage only for exploratory debugging; acceptance must include real login flow when verifying auth and UI permissions.

