# AI Platform Requirements

## Product Positioning

Company RAG Agent is an internal enterprise AI automation platform for Amazon cross-border ecommerce teams.

The purpose is to reduce repeated work across operations, customer service, and finance while keeping data access controlled and auditable.

## Primary Users

| User | Goal |
| --- | --- |
| Admin | Configure users, permissions, apps, connectors, knowledge, approval, audit, monitoring, and release checks. |
| Operations | Generate Listing content, titles, bullet points, keywords, promotions, and competitor analysis. |
| Customer Service | Generate customer replies, refund scripts, logistics responses, multilingual replies, and ticket summaries. |
| Finance | Analyze reports, summarize salaries, process Excel files, inspect invoices, payments, and ledger entries. |

## Enterprise Capabilities

### AI App Center

The system must show AI applications as managed internal products.

Each app should have:

- Name
- Position
- Category
- Status
- Owner
- Description
- Allowed input
- Allowed data sources
- Today's run count
- Success rate
- Last run time
- Entry actions
- Run records link

### Automation Flow Management

The system must gradually support configurable automation flows.

Each flow should define:

- Trigger type
- Input schema
- Prompt template
- Model configuration
- Allowed tools
- Allowed ERP resources
- Allowed knowledge bases
- Output schema
- Approval policy
- Failure and retry strategy
- Version and publish status

### Run Records

Every AI automation execution should produce a real run record.

Required fields:

- Run ID
- App or flow ID
- Trigger user
- Role and position
- Status
- Input preview
- Output preview
- Duration
- Error message
- Tool calls
- ERP resources
- RAG references
- Approval status
- Created and completed time

Audit logs are not a replacement for run records. Audit logs are for compliance; run records are for operational visibility and analytics.

### Connector Center

The system should manage external systems as connectors.

Initial connector categories:

- ERPNext
- Kingdee
- Yonyou
- Amazon SP-API
- Logistics API
- Ads API
- Feishu or enterprise chat
- Email
- Excel or spreadsheet files
- Knowledge files

Each connector should expose:

- Status
- Provider
- Masked configuration
- Last diagnostic time
- Resource catalog
- Field mapping
- Permission scope
- Test connection action

### Permission Governance

Permission must be enforced before data reaches the model.

Layers:

- Role: admin or employee
- Position: operations, customer_service, finance
- Resource: order, invoice, salary, ledger, issue, customer, item
- Field: salary, profit, cost, customer phone, payment detail
- Marketplace: US, DE, JP
- Store: US Store, DE Store, JP Store
- Action: read, generate, export, approve, configure

### Effect Analytics

The system should prove work reduction with measurable data:

- AI automation count
- Success rate
- Failure rate
- Average duration
- Manual handoff rate
- Approval block count
- ERP query count
- Knowledge hit rate
- Estimated saved time
- Usage by position
- Failing apps and reasons

### AI Evaluation Center

The system must support regression checks for:

- RAG answer quality
- ERP query accuracy
- Permission refusal
- Role-specific answer boundaries
- Prompt output format
- Automation app result quality
- Citation and source correctness

## Non-Functional Requirements

- No sensitive credentials in UI or logs.
- No cross-position data leakage.
- No fake ERP success data.
- No mock test code as acceptance evidence.
- Frontend must remain readable on desktop and mobile.
- Long content must not overflow cards, tables, buttons, or modals.
- Every platform loop must preserve existing working user flows.

## Current-To-Target Mapping

| Current Feature | Target Module |
| --- | --- |
| Role automation page | AI App Center and Automation Flow Management |
| `/automation/generate` | App run endpoint and Run Records |
| Finance Excel transform | Finance AI app and Run Artifact |
| Chat and ERP conversation | Chat app, ERP app, Run Records, RAG references |
| ERP query and dashboard | Connector Center and role data dashboard |
| Audit logs | Compliance audit and security review |
| RAG upload | Knowledge connector and Evaluation Center |
| Permission scripts | Real regression gate |

