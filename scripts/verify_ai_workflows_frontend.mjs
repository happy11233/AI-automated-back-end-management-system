// Compatibility entrypoint for the Agent workspace UI regression.
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const api = (process.env.VERIFY_API_BASE_URL || "http://127.0.0.1:8001").replace(/\/$/, "");
const directory = mkdtempSync(join(tmpdir(), "agent-workspace-verification-"));
const path = join(directory, "sessions.json");
try {
  const accounts = {};
  for (const [name, username, password] of [
    ["admin", "admin_demo", "Admin123456"],
    ["operations", "operations_demo", "Operations123456"],
    ["customer_service", "employee_demo", "Employee123456"],
    ["finance", "finance_demo", "Finance123456"],
  ]) {
    const response = await fetch(api + "/auth/login", { method: "POST", body: new URLSearchParams({ username, password }) });
    if (!response.ok) throw new Error("Verification account login failed: " + name + " (" + response.status + ")");
    accounts[name] = { session: await response.json() };
  }
  writeFileSync(path, JSON.stringify({ accounts }), { mode: 0o600 });
  process.argv[2] = path;
  await import("./verify_agent_workspace_frontend.mjs");
} finally { rmSync(directory, { recursive: true, force: true }); }
