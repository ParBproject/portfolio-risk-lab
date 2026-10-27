// Same calculations as src/risklab/risk.py and attribution.py.
// tests/metrics.test.js compares them with results/summary.json.

export const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
export const std = (a) => {
  const m = mean(a);
  return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1));
};

export function netReturns(v, costBps) {
  return v.gross.map((g, i) => g - (v.turnover[i] * costBps) / 1e4);
}

export function wealth(r) {
  let w = 1;
  return r.map((x) => (w *= 1 + x));
}

export function drawdowns(r) {
  let peak = -Infinity;
  return wealth(r).map((w) => {
    peak = Math.max(peak, w);
    return w / peak - 1;
  });
}

// numpy.quantile default ("linear") interpolation
export function quantile(a, q) {
  const s = [...a].sort((x, y) => x - y);
  const h = (s.length - 1) * q;
  const lo = Math.floor(h);
  return s[lo] + (h - lo) * ((s[Math.min(lo + 1, s.length - 1)] ?? s[lo]) - s[lo]);
}

export function varCvar(r, level = 0.95) {
  const q = quantile(r, 1 - level);
  const tail = r.filter((x) => x <= q);
  return { var95: -q, cvar95: -mean(tail) };
}

export function summary(r, rf, turnover) {
  const n = r.length;
  const ex = r.map((x, i) => x - (rf[i] ?? 0));
  const { var95, cvar95 } = varCvar(r);
  return {
    cagr: wealth(r)[n - 1] ** (12 / n) - 1,
    vol: std(r) * Math.sqrt(12),
    sharpe: (mean(ex) / std(ex)) * Math.sqrt(12),
    max_drawdown: Math.min(...drawdowns(r)),
    var95_monthly: var95,
    cvar95_monthly: cvar95,
    worst_month: Math.min(...r),
    avg_monthly_turnover: turnover ? mean(turnover.slice(1)) : null,
  };
}

// Solve A x = b (Gauss-Jordan with partial pivoting); returns x and A^-1.
function solve(A, b) {
  const n = A.length;
  const M = A.map((row, i) => [...row, b[i], ...row.map((_, j) => (i === j ? 1 : 0))]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    [M[c], M[p]] = [M[p], M[c]];
    const d = M[c][c];
    for (let k = 0; k < M[c].length; k++) M[c][k] /= d;
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c];
      for (let k = 0; k < M[r].length; k++) M[r][k] -= f * M[c][k];
    }
  }
  return { x: M.map((row) => row[n]), inv: M.map((row) => row.slice(n + 1)) };
}

export const FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"];

// OLS of excess returns on FF5 + momentum, plain standard errors (as in attribution.py).
export function attribution(r, rf, factors) {
  const rows = [];
  r.forEach((x, i) => {
    if (rf[i] == null || FACTORS.some((f) => factors[f][i] == null)) return;
    rows.push({ y: x - rf[i], X: [1, ...FACTORS.map((f) => factors[f][i])] });
  });
  const k = 7;
  const XtX = Array.from({ length: k }, () => Array(k).fill(0));
  const Xty = Array(k).fill(0);
  for (const { y, X } of rows) {
    for (let a = 0; a < k; a++) {
      Xty[a] += X[a] * y;
      for (let b = 0; b < k; b++) XtX[a][b] += X[a] * X[b];
    }
  }
  const { x: beta, inv } = solve(XtX, Xty);
  const resid = rows.map(({ y, X }) => y - X.reduce((s, v, j) => s + v * beta[j], 0));
  const ys = rows.map((d) => d.y);
  const s2 = resid.reduce((s, e) => s + e * e, 0) / (rows.length - k);
  const varPop = (a) => {
    const m = mean(a);
    return a.reduce((s, x) => s + (x - m) ** 2, 0) / a.length;
  };
  return {
    alpha_annual: beta[0] * 12,
    alpha_t: beta[0] / Math.sqrt(s2 * inv[0][0]),
    r2: 1 - varPop(resid) / varPop(ys),
    months: rows.length,
    betas: Object.fromEntries(FACTORS.map((f, j) => [f, beta[j + 1]])),
  };
}
