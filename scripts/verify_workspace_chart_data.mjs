import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ts = require("../frontend/node_modules/typescript");
const source = await readFile(
  new URL("../frontend/src/components/chartData.ts", import.meta.url),
  "utf8",
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022 },
});
const {
  safeChartNumber,
  chartMaximum,
  aggregateTrend,
  chartDate,
  trendTimeDomain,
} = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
);

assert.deepEqual(
  [0, -2, NaN, Infinity, null, "3"].map(safeChartNumber),
  [0, 0, 0, 0, 0, 0],
);
assert.equal(safeChartNumber(0.25), 0.25);
assert.equal(chartMaximum([0, 0]), 4);
assert(chartMaximum([72, 0, 18]) >= 72);
assert.deepEqual(aggregateTrend([]), []);
assert.equal(chartDate("2026-02-30"), undefined);
assert.equal(chartDate("not-a-date"), undefined);

// Dense historical data must retain every source observation and every series total.
const sourceDays = Array.from({ length: 121 }, (_, index) => ({
  label: new Date(Date.UTC(2026, 0, 1 + index)).toISOString().slice(0, 10),
  values: { succeeded: index, failed: index % 3, blocked: 0 },
}));
const grouped = aggregateTrend(sourceDays, 30);
assert(grouped.length <= 30);
assert(grouped[0].label.startsWith(sourceDays[0].label));
assert(grouped.at(-1).label.endsWith(sourceDays.at(-1).label));
for (const series of ["succeeded", "failed", "blocked"]) {
  assert.equal(
    grouped.reduce((sum, point) => sum + point.values[series], 0),
    sourceDays.reduce((sum, point) => sum + point.values[series], 0),
  );
}
assert(trendTimeDomain(grouped));

// Sparse dates keep their real calendar span; absent dates never become zero-valued records.
const sparse = aggregateTrend([
  { label: "2026-10-01", values: { runs: 0 } },
  { label: "2026-10-03", values: { runs: 2 } },
  { label: "2026-10-21", values: { runs: 4 } },
]);
const domain = trendTimeDomain(sparse);
assert.equal(domain.end - domain.start, 21 * 86_400_000);
assert.equal(sparse.length, 3);
assert.equal(sparse[0].values.runs, 0);
assert.equal(
  (sparse[2].timestamp - sparse[1].timestamp) /
    (sparse[1].timestamp - sparse[0].timestamp),
  9,
);
assert.equal(
  trendTimeDomain(aggregateTrend([{ label: "Batch A", values: { runs: 1 } }])),
  undefined,
);
assert.equal(trendTimeDomain(aggregateTrend([...sparse].reverse())), undefined);
console.log(
  "PASS: chart zero values, invalid data, aggregation totals, calendar gaps and empty datasets",
);
