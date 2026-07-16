# Real Testing Policy

## Core Rule

Do not write mock, stub, fake provider, monkeypatch, or simulated-response tests into this project.

Acceptance testing must use real services and real user flows.

## What Counts As Real Testing

- Real backend API at `http://127.0.0.1:8001`
- Real frontend at `http://127.0.0.1:5173`
- Real PostgreSQL database used by the running project
- Real login through `/auth/login`
- Real JWT returned by the backend
- Real ERPNext when ERP behavior is involved
- Real browser automation for UI checks
- Real file upload and download for document and Excel workflows
- Real RAG indexing and retrieval for knowledge checks

## What Is Not Accepted

- Mocking HTTP responses
- Replacing ERP providers with fake success data
- Monkeypatching permission functions
- Testing React components without the real app route when the feature is page-level
- Bypassing auth for final acceptance
- Writing tests that only inspect static code but do not call real behavior
- Passing a loop based only on TypeScript compilation when UI behavior changed

## Allowed Setup

The project may use real seed data and demo accounts.

Allowed:

- Running existing seed scripts to initialize demo data.
- Creating real test records with unique names.
- Cleaning up records after the test.
- Using local development services.

Not allowed:

- Faking API success without the backend.
- Faking ERP success without ERPNext when ERP is in scope.
- Faking role permission results.

## Required Real Accounts

- Admin: `admin_demo / Admin123456`
- Operations: `operations_demo / Operations123456`
- Customer Service: `employee_demo / Employee123456`
- Finance: `finance_demo / Finance123456`

## Evidence Required

Each loop report should include the relevant evidence:

- Commands run
- API status or script result
- Browser screenshot path
- Build result
- Real account used
- ERP diagnostic status when relevant
- Confirmation that no mock/stub/fake test path was used

## Waiting Rules

Do not rely on arbitrary fixed sleeps as the only success condition.

Prefer waiting for:

- Real network response
- Real DOM state
- Real database state
- Real file download
- Real task status
- Real API response field

Short waits may be used only as stabilization around a real condition.

## Cleanup Rules

When tests create records, include a unique `testRunId` or recognizable prefix where possible.

Clean up:

- Database rows
- Uploaded files
- Downloaded files
- ERPNext records created for testing

If cleanup cannot safely run, document the remaining record IDs.

