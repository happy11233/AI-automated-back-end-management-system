# Security Checklist

## Red Lines

- [ ] All security checks must use real login through `/auth/login`.
- [ ] All permission checks must call the real backend API.
- [ ] No mock, stub, monkeypatch, fake provider, or simulated response may be used as acceptance evidence.
- [ ] ERP checks must use real ERPNext diagnostics when ERP behavior changes.
- [ ] Audit checks must query real API or real database data.
- [ ] Frontend permission checks must use a real browser.
- [ ] Any unauthorized request returning `200` is a failure.

## Real Accounts

- `admin_demo / Admin123456`
- `operations_demo / Operations123456`
- `employee_demo / Employee123456`
- `finance_demo / Finance123456`

## Position Overreach

- [ ] Operations cannot use customer service automation tasks.
- [ ] Customer service cannot use finance automation tasks.
- [ ] Finance cannot use operations automation tasks.
- [ ] Customer service cannot query `GL Entry`, `Salary Slip`, or full finance details.
- [ ] Operations cannot query salary, payroll, or full finance reports.
- [ ] Finance cannot query customer service private conversations.
- [ ] Employees cannot access admin users, admin audit logs, approvals, or ERP diagnostics.
- [ ] Admin can inspect platform configuration without silently exposing all business data by default.

## Field Overreach

- [ ] ERP returned fields must respect resource field allowlists.
- [ ] Operations invoice summary cannot include full payment or salary details.
- [ ] Customer service issue data cannot include finance-only fields.
- [ ] Finance data cannot include customer service private chat context.
- [ ] ERP record detail endpoints must check resource permission before fetching details.
- [ ] Dashboard filters must not bypass position scope.

## ERP Credentials

- [ ] `/erp/diagnostics` is admin-only.
- [ ] ERP API key, secret, Kingdee secret, and Yonyou secret are masked.
- [ ] Employees receive `403` on diagnostics.
- [ ] ERP failures do not fake successful business data.
- [ ] Error messages do not leak Authorization headers, secrets, or connection strings.
- [ ] Audit logs record provider, resource, status, and count, not credentials.

## AI Context Leakage

- [ ] Chat uses only the current user's allowed context.
- [ ] Thread message APIs reject unauthorized thread access.
- [ ] Summaries, memories, and recent messages do not mix across users.
- [ ] Restricted finance, salary, profit, private service chat, and private operations data are blocked before model generation.
- [ ] ERP references in AI answers only include allowed resources.
- [ ] Prompts and metadata never contain secrets, JWTs, or DB URLs.

## Audit Logs

- [ ] Key actions write audit logs.
- [ ] Overreach blocks write audit logs.
- [ ] Logs include user, role, position, resource, status, and time.
- [ ] Logs store input preview, not full sensitive input.
- [ ] Employees cannot read audit logs.
- [ ] Admin can filter by action, resource type, and position.

## Token Expiry

- [ ] Expired token returns `401`.
- [ ] Malformed token returns `401`.
- [ ] Token without `sub` returns `401`.
- [ ] Old token for deleted user returns `401`.
- [ ] Frontend clears local storage and returns to login state on invalid token.

## Admin Operations

- [ ] Only admin can create users.
- [ ] New employees must have a valid position.
- [ ] User creation writes permission assignment audit.
- [ ] Only admin can review approvals.
- [ ] Approval and refund results are audited.
- [ ] Document upload and connector diagnostics are admin-controlled.

## Required Release Gate

Use real checks:

```bash
python3 scripts/verify_all.py
python3 scripts/verify_erp_chat.py
node scripts/verify_frontend_permissions.mjs
```

If a loop changes token behavior, also run:

```bash
node scripts/verify_token_expiry_frontend.mjs
```

