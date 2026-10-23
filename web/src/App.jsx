import { useEffect, useMemo, useRef, useState } from "react";
import { FACTORS, attribution, drawdowns, netReturns, summary, varCvar, wealth } from "./metrics.js";

const NAMES = {
  mean_variance: "Mean-variance", risk_parity: "Risk parity", black_litterman: "Black-Litterman",
  equal_weight: "Equal weight", sixty_forty: "60/40", spy: "SPY",
};
const COLORS = { sel: "#10b981", spy: "#60a5fa", sixty_forty: "#fbbf24" };
const pct = (x, d = 1) => (x == null || Number.isNaN(x) ? "–" : `${(x * 100).toFixed(d)}%`);

// Charts draw in real pixels so labels stay readable on phones.
function useWidth() {
  const ref = useRef(null);
  const [w, setW] = useState(800);
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))));
    if (ref.current) ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

function variantKey(app, s, cap) {
  return app.variants[`${s}@${cap}`] ? `${s}@${cap}` : s;
}

function LineChart({ dates, series, hover, setHover, fmt, height = 260, zeroBase = false, label }) {
  const [ref, W] = useWidth();
  const H = W < 500 ? Math.round(height * 0.8) : height, L = 52, R = 12, T = 10, B = 24;
  const all = series.flatMap((s) => s.values);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (zeroBase) hi = 0;
  const pad = (hi - lo) * 0.05 || 0.01;
  lo -= pad; hi += zeroBase ? 0 : pad;
  const x = (i) => L + (i / Math.max(dates.length - 1, 1)) * (W - L - R);
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
  const every = Math.ceil((dates.length / 12) / Math.max(1, Math.floor(W / 70)));
  const years = dates.map((d, i) => [d, i]).filter(([d]) => d.endsWith("-01"))
    .filter((_, j) => j % every === 0);
  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - L) / (W - L - R)) * (dates.length - 1));
    setHover(Math.max(0, Math.min(dates.length - 1, i)));
  };
  return (
    <div ref={ref}><svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={label}
      onPointerMove={onMove} onPointerLeave={() => setHover(null)} style={{ touchAction: "pan-y" }}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="#1f2630" />
          <text x={L - 6} y={y(t) + 4} textAnchor="end">{fmt(t)}</text>
        </g>
      ))}
      {years.map(([d, i]) => (
        <text key={d} x={x(i)} y={H - 6} textAnchor="middle">{d.slice(0, 4)}</text>
      ))}
      {series.map((s) => (
        <path key={s.name} fill="none" stroke={s.color} strokeWidth={s.width || 1.5} opacity={s.opacity || 1}
          d={s.values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("")} />
      ))}
      {hover != null && (
        <g>
          <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="#9aa7b4" strokeDasharray="3 3" />
          {series.map((s) => <circle key={s.name} cx={x(hover)} cy={y(s.values[hover])} r={3.5} fill={s.color} />)}
          <text x={Math.min(x(hover) + 6, W - 150)} y={T + 12} style={{ fill: "#e6edf3" }}>
            {dates[hover]} · {series.map((s) => fmt(s.values[hover])).join(" / ")}
          </text>
        </g>
      )}
    </svg></div>
  );
}

function Histogram({ r, var95, cvar95 }) {
  const [ref, W] = useWidth();
  const H = 220, L = 12, R = 12, T = 10, B = 24, bins = 30;
  const lo = Math.min(...r), hi = Math.max(...r);
  const bw = (hi - lo) / bins;
  const counts = Array(bins).fill(0);
  r.forEach((v) => counts[Math.min(bins - 1, Math.floor((v - lo) / bw))]++);
  const mx = Math.max(...counts);
  const x = (v) => L + ((v - lo) / (hi - lo)) * (W - L - R);
  return (
    <div ref={ref}><svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Monthly return distribution with VaR and CVaR">
      {counts.map((c, i) => (
        <rect key={i} x={x(lo + i * bw) + 1} width={Math.max(x(lo + bw) - x(lo) - 2, 1)} y={T + (1 - c / mx) * (H - T - B)}
          height={(c / mx) * (H - T - B)} fill={lo + (i + 1) * bw <= -var95 ? "#f87171" : "#10b981"} opacity={0.8} />
      ))}
      {[["VaR 95%", -var95, "#fbbf24"], ["CVaR 95%", -cvar95, "#f87171"]].map(([n, v, c], j) => (
        <g key={n}>
          <line x1={x(v)} x2={x(v)} y1={T} y2={H - B} stroke={c} strokeWidth={2} />
          <text x={x(v) - 4} y={T + 12 + j * 16} textAnchor="end" style={{ fill: c }}>{n} {pct(-v)}</text>
        </g>
      ))}
      <text x={L} y={H - 6}>{pct(lo)}</text>
      <text x={W - R} y={H - 6} textAnchor="end">{pct(hi)}</text>
    </svg></div>
  );
}

function Bars({ items, fmt, diverging }) {
  const mx = Math.max(...items.map(([, v]) => Math.abs(v)), 1e-9);
  return (
    <div style={{ display: "grid", gap: 6 }}>
      {items.map(([k, v]) => (
        <div className="bar-row" key={k} title={k}>
          <span>{k}</span>
          <div className="track" style={diverging ? { position: "relative" } : undefined}>
            {diverging ? (
              <div className="fill" style={{
                position: "absolute", left: v >= 0 ? "50%" : `${50 - (Math.abs(v) / mx) * 50}%`,
                width: `${(Math.abs(v) / mx) * 50}%`, background: v >= 0 ? "#10b981" : "#f87171" }} />
            ) : (
              <div className="fill" style={{ width: `${(v / mx) * 100}%` }} />
            )}
          </div>
          <span style={{ textAlign: "right" }}>{fmt(v)}</span>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [app, setApp] = useState(null);
  const [strategy, setStrategy] = useState("mean_variance");
  const [cap, setCap] = useState(0.3);
  const [cost, setCost] = useState(10);
  const [start, setStart] = useState(0);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/app.json`).then((r) => r.json()).then((a) => {
      setApp(a);
      setCap(a.default_cap);
      setCost(a.default_cost_bps);
    });
  }, []);

  const view = useMemo(() => {
    if (!app) return null;
    const n = app.dates.length;
    const sl = (a) => a.slice(start, n);
    const calc = (s) => {
      const v = app.variants[variantKey(app, s, cap)];
      const r = sl(netReturns(v, cost));
      const m = summary(r, sl(app.rf), sl(v.turnover));
      const fac = Object.fromEntries(FACTORS.map((f) => [f, sl(app.factors[f])]));
      return { v, r, m, a: attribution(r, sl(app.rf), fac) };
    };
    const all = Object.fromEntries(Object.keys(NAMES).map((s) => [s, calc(s)]));
    return { all, dates: sl(app.dates), cur: all[strategy], weightsOf: (i) => all[strategy].v.weights[start + i] };
  }, [app, strategy, cap, cost, start]);

  if (!view) return <div className="wrap"><p className="note">Loading results…</p></div>;
  const { all, dates, cur } = view;
  const capped = strategy === "mean_variance" || strategy === "black_litterman";
  const wi = hover ?? dates.length - 1;
  const w = view.weightsOf(wi);
  const weightItems = app.tickers.map((t, i) => [t, w[i]]).filter(([, x]) => x > 0.0005).sort((a, b) => b[1] - a[1]);
  const isDefault = cap === app.default_cap && cost === app.default_cost_bps && start === 0;
  const eq = (s) => wealth(all[s].r);
  const lines = [
    { name: NAMES[strategy], color: COLORS.sel, values: eq(strategy), width: 2.2 },
    ...(strategy !== "spy" ? [{ name: "SPY", color: COLORS.spy, values: eq("spy"), opacity: 0.8 }] : []),
    ...(strategy !== "sixty_forty" ? [{ name: "60/40", color: COLORS.sixty_forty, values: eq("sixty_forty"), opacity: 0.8 }] : []),
  ];
  const { var95, cvar95 } = varCvar(cur.r);

  return (
    <div className="wrap">
      <header>
        <div className="eyebrow">Portfolio Risk Lab · walk-forward, after costs</div>
        <h1>Do optimizers beat <span>SPY and 60/40</span> on a 21-ETF universe?</h1>
        <p className="lede">
          Mean-variance, risk parity and Black-Litterman, re-estimated every month from the prior {app.settings.lookback_months}{" "}
          months only, {app.sample.backtest_start} to {app.sample.returns_end}. Every number is recomputed in your browser from the
          exported monthly returns and matches the Python results at the published settings.
        </p>
      </header>

      <section className="card span-12" aria-label="Controls" style={{ marginBottom: 16 }}>
        <div className="controls">
          <div className="pills" role="group" aria-label="Strategy">
            {Object.entries(NAMES).map(([k, n]) => (
              <button key={k} className="pill" aria-pressed={strategy === k} onClick={() => setStrategy(k)}>{n}</button>
            ))}
          </div>
          <div className="field">
            Max weight per ETF {capped ? "" : "(n/a for this strategy)"}
            <div className="pills" role="group" aria-label="Weight cap">
              {app.caps.map((c) => (
                <button key={c} className="pill" disabled={!capped} aria-pressed={capped && cap === c}
                  onClick={() => setCap(c)}>{pct(c, 0)}</button>
              ))}
            </div>
          </div>
          <label className="field">
            Trading cost: {cost} bps per unit turnover
            <input type="range" min={0} max={50} step={1} value={cost} onChange={(e) => setCost(+e.target.value)} />
          </label>
          <label className="field">
            Window start: {dates[0]}
            <input type="range" min={0} max={app.dates.length - 36} step={1} value={start}
              onChange={(e) => setStart(+e.target.value)} aria-label="Window start month" />
          </label>
        </div>
        <p className="note" style={{ margin: "8px 0 0" }}>
          {isDefault ? "Published settings: these numbers equal results/summary.json." :
            "Custom settings: recomputed live from the same monthly returns (not in the published results)."}
        </p>
      </section>

      <div className="kpis" style={{ marginBottom: 16 }}>
        {[["CAGR", pct(cur.m.cagr, 2)], ["Volatility", pct(cur.m.vol, 2)], ["Sharpe", cur.m.sharpe.toFixed(2)],
          ["Max drawdown", pct(cur.m.max_drawdown, 2)], ["VaR / CVaR 95% (1m)", `${pct(var95)} / ${pct(cvar95)}`],
          ["Turnover / month", pct(cur.m.avg_monthly_turnover)]].map(([l, v]) => (
          <div className="kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>
        ))}
      </div>

      <div className="grid">
        <section className="card span-8">
          <h2>Growth of $1 (net)</h2>
          <LineChart dates={dates} series={lines} hover={hover} setHover={setHover} fmt={(v) => `$${v.toFixed(2)}`}
            label="Equity curve versus SPY and 60/40" />
          <div className="legend">{lines.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}</div>
        </section>
        <section className="card span-4">
          <h2>Weights · {dates[wi]}</h2>
          <Bars items={weightItems} fmt={(v) => pct(v)} />
          <p className="note">Hover the charts to see the weights chosen that month.</p>
        </section>
        <section className="card span-8">
          <h2>Drawdown</h2>
          <LineChart dates={dates} hover={hover} setHover={setHover} fmt={(v) => pct(v, 0)} height={180} zeroBase
            series={[{ name: NAMES[strategy], color: "#f87171", values: drawdowns(cur.r), width: 1.8 },
              ...(strategy !== "spy" ? [{ name: "SPY", color: COLORS.spy, values: drawdowns(all.spy.r), opacity: 0.6 }] : [])]}
            label="Drawdown chart" />
        </section>
        <section className="card span-4">
          <h2>Fama-French 5 + momentum</h2>
          <Bars diverging items={FACTORS.map((f) => [f, cur.a.betas[f]])} fmt={(v) => v.toFixed(2)} />
          <p className="note">
            Alpha {pct(cur.a.alpha_annual, 2)}/yr, t = {cur.a.alpha_t.toFixed(2)}, R² = {cur.a.r2.toFixed(2)} ({cur.a.months} months;
            factors end {app.sample.factors_end}).
          </p>
        </section>
        <section className="card span-6">
          <h2>Monthly return distribution</h2>
          <Histogram r={cur.r} var95={var95} cvar95={cvar95} />
        </section>
        <section className="card span-6">
          <h2>All strategies, same settings</h2>
          <div className="scroll">
            <table>
              <thead><tr><th>Strategy</th><th>CAGR</th><th>Vol</th><th>Sharpe</th><th>Max DD</th><th>CVaR</th></tr></thead>
              <tbody>
                {Object.entries(all).sort((a, b) => b[1].m.sharpe - a[1].m.sharpe).map(([k, { m }]) => (
                  <tr key={k} className={k === strategy ? "sel" : ""} onClick={() => setStrategy(k)}>
                    <td>{NAMES[k]}</td><td>{pct(m.cagr)}</td><td>{pct(m.vol)}</td><td>{m.sharpe.toFixed(2)}</td>
                    <td>{pct(m.max_drawdown)}</td><td>{pct(m.cvar95_monthly)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">Click a row to select it. Sorted by Sharpe.</p>
        </section>
      </div>
      <footer>
        Data: yfinance dividend-adjusted ETF closes, Ken French Data Library. Past performance; not investment advice.{" "}
        <a href="https://github.com/ParBproject/portfolio-risk-lab">Code, method and limits on GitHub</a>.
      </footer>
    </div>
  );
}
