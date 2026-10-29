import assert from "node:assert/strict";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { gzipSync } from "node:zlib";

const dist = resolve(process.argv[2] || "frontend/dist");
const manifest = JSON.parse(readFileSync(resolve(dist, ".vite/manifest.json"), "utf8"));
const baseline = { bytes: 2216085, gzip: 668586 };

// Static chunk cycles can break initialization even when source modules are acyclic.
const visited = new Set();
const visiting = new Set();
function checkStaticImports(key, path = []) {
  assert(!visiting.has(key), `Static chunk import cycle: ${[...path, key].join(" -> ")}`);
  if (visited.has(key)) return;
  assert(manifest[key], `Missing manifest entry: ${key}`);
  visiting.add(key);
  for (const dependency of manifest[key].imports || []) checkStaticImports(dependency, [...path, key]);
  visiting.delete(key);
  visited.add(key);
}
for (const key of Object.keys(manifest)) checkStaticImports(key);

function closure(key, seen = new Set()) {
  assert(manifest[key], `Missing manifest entry: ${key}`);
  if (seen.has(key)) return seen;
  seen.add(key);
  for (const dependency of manifest[key].imports || []) closure(dependency, seen);
  return seen;
}

function size(keys) {
  const files = [...new Set([...keys].map((key) => manifest[key].file))].filter((file) => file.endsWith(".js"));
  const sizes = files.map((file) => {
    const buffer = readFileSync(resolve(dist, file));
    return { file, bytes: buffer.length, gzip: gzipSync(buffer).length };
  });
  return {
    bytes: sizes.reduce((sum, item) => sum + item.bytes, 0),
    gzip: sizes.reduce((sum, item) => sum + item.gzip, 0),
    files: sizes,
  };
}

const entry = Object.keys(manifest).find((key) => manifest[key].isEntry);
assert(entry, "A Vite build entry is required");
const initial = closure(entry);
const pages = Object.keys(manifest).filter((key) => /^src\/pages\/.*\.tsx$/.test(key));
const dialogs = Object.keys(manifest).filter((key) => /^src\/dialogs\/.*\.tsx$/.test(key));
assert.equal(pages.length, 28, "Every extracted workspace page must be emitted as a dynamic entry");
assert.equal(dialogs.length, 8, "Detail dialogs must remain dynamically loaded");
for (const key of [...pages, ...dialogs, "src/portal/PublicPortal.tsx", "src/components/WorkspaceLayout.tsx", "src/components/AgentWorkspace.tsx"]) {
  assert(manifest[key]?.isDynamicEntry, `${key} must be a dynamic entry`);
  assert(!initial.has(key), `${key} leaked into the static entry dependency graph`);
}
function route(...entries) {
  const keys = new Set(initial);
  for (const key of entries) closure(key, keys);
  return size(keys);
}
const report = {
  baseline,
  entry: size(initial),
  portal: route("src/portal/PublicPortal.tsx"),
  dashboard: route("src/components/WorkspaceLayout.tsx", "src/pages/Dashboard.tsx"),
  agent: route("src/components/WorkspaceLayout.tsx", "src/components/AgentWorkspace.tsx"),
  chunks: size(Object.keys(manifest)),
  pages: pages.length,
  dialogs: dialogs.length,
};
// Enforce a real cold-load reduction, including shared dependencies.
assert(report.portal.bytes < baseline.bytes * 0.65, "Portal cold-load JS exceeded its 65% baseline budget");
assert(report.dashboard.bytes < baseline.bytes * 0.85, "Dashboard cold-load JS exceeded its 85% baseline budget");
const oversized = report.chunks.files.filter((chunk) => chunk.bytes > 500000);
assert.deepEqual(oversized, [], "A JS chunk exceeded the standard Vite 500 kB warning threshold");
mkdirSync("data/verification/frontend-bundle", { recursive: true });
writeFileSync("data/verification/frontend-bundle/build.json", JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({
  ok: true,
  pages: report.pages,
  dialogs: report.dialogs,
  chunks: report.chunks.files.length,
  largest: report.chunks.files.toSorted((a, b) => b.bytes - a.bytes).slice(0, 5),
  baseline,
  portal: { bytes: report.portal.bytes, gzip: report.portal.gzip },
  dashboard: { bytes: report.dashboard.bytes, gzip: report.dashboard.gzip },
  agent: { bytes: report.agent.bytes, gzip: report.agent.gzip },
}, null, 2));
