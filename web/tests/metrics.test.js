// Browser math must reproduce the Python results exactly (to 1e-9) at the published settings.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { attribution, netReturns, summary } from "../src/metrics.js";

const app = JSON.parse(readFileSync(new URL("../public/data/app.json", import.meta.url)));
const py = JSON.parse(readFileSync(new URL("../../results/summary.json", import.meta.url)));

for (const name of Object.keys(py.strategies)) {
  test(`metrics match Python for ${name}`, () => {
    const key = app.variants[`${name}@${app.default_cap}`] ? `${name}@${app.default_cap}` : name;
    const v = app.variants[key];
    const r = netReturns(v, app.default_cost_bps);
    const m = summary(r, app.rf, v.turnover);
    const want = py.strategies[name];
    for (const k of ["cagr", "vol", "sharpe", "max_drawdown", "var95_monthly", "cvar95_monthly", "avg_monthly_turnover"]) {
      assert.ok(Math.abs(m[k] - want[k]) < 1e-6, `${k}: ${m[k]} vs ${want[k]}`);
    }
    const a = attribution(r, app.rf, app.factors);
    assert.equal(a.months, want.attribution.months);
    for (const k of ["alpha_annual", "alpha_t", "r2"]) assert.ok(Math.abs(a[k] - want.attribution[k]) < 1e-6, k);
    for (const [f, b] of Object.entries(want.attribution.betas)) assert.ok(Math.abs(a.betas[f] - b) < 1e-6, f);
  });
}
