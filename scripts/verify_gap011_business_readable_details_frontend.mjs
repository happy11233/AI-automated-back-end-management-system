import { spawn } from "node:child_process";

const scripts = [
  "scripts/verify_erp_record_detail_frontend.mjs",
  "scripts/verify_run_records_frontend.mjs",
];

const results = [];

for (const script of scripts) {
  const result = await runScript(script);
  results.push(result);
}

console.log(JSON.stringify({
  ok: true,
  scripts: results,
  note: "GAP-011 business-readable frontend regression: ERP details plus run record details.",
}, null, 2));

function runScript(script) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script], {
      cwd: process.cwd(),
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`${script} failed with code ${code}\n${stderr || stdout}`));
        return;
      }
      resolve({
        script,
        ok: true,
        output: parseJsonOutput(stdout),
      });
    });
  });
}

function parseJsonOutput(output) {
  try {
    return JSON.parse(output);
  } catch {
    return output.trim();
  }
}
