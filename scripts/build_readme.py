"""Generate README.md from results/summary.json (no hand-typed numbers)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
NAMES = {"mean_variance": "Mean-variance", "risk_parity": "Risk parity (ERC)", "black_litterman": "Black-Litterman",
         "equal_weight": "Equal weight (1/N)", "sixty_forty": "60/40 SPY/IEF", "spy": "SPY"}


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


st = S["strategies"]
sm = S["sample"]
cfg = S["settings"]
best = max(st, key=lambda k: st[k]["sharpe"])
OPT = ("mean_variance", "risk_parity", "black_litterman")
bench_sr = max(st["spy"]["sharpe"], st["sixty_forty"]["sharpe"])
beat = [NAMES[k] for k in OPT if st[k]["sharpe"] > bench_sr]
verdict = (f"Optimizers beating the best of SPY/60-40 on Sharpe: {', '.join(beat)}." if beat else
           "None of the three optimizers beat plain SPY or 60/40 on Sharpe over this window; they are reported as-is,"
           " not tuned until they do.")
sig = [NAMES[k] for k in st if abs(st[k]["attribution"]["alpha_t"]) >= 2]
alpha_line = ("Strategies with |t(alpha)| >= 2: " + ", ".join(sig) if sig else
              "No strategy shows a statistically significant factor alpha (all |t| < 2)")
rows = "\n".join(
    f"| {NAMES[k]} | {pct(m['cagr'])} | {pct(m['vol'])} | {m['sharpe']:.2f} | {pct(m['max_drawdown'])} | "
    f"{pct(m['var95_monthly'])} | {pct(m['cvar95_monthly'])} | {pct(m['avg_monthly_turnover'])} |"
    for k, m in st.items())
arows = "\n".join(
    f"| {NAMES[k]} | {pct(m['attribution']['alpha_annual'])} | {m['attribution']['alpha_t']:.2f} | "
    + " | ".join(f"{m['attribution']['betas'][f]:.2f}" for f in ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"))
    + f" | {m['attribution']['r2']:.2f} |" for k, m in st.items())
uni = ", ".join(f"{t} ({c})" for t, c in S["universe"].items())
att = st["mean_variance"]["attribution"]
text = f"""# portfolio-risk-lab

Mean-variance, risk-parity and Black-Litterman portfolios on a {len(S['universe'])}-ETF multi-asset universe,
tested **walk-forward** against SPY, 60/40 and 1/N **after trading costs**, with VaR/CVaR, drawdowns and
Fama-French 5 + momentum attribution. Every number below is generated from `results/summary.json` by
`scripts/build_readme.py` and pinned by tests.

## Headline (out-of-sample {sm['backtest_start']} to {sm['returns_end']}, net of {cfg['cost_bps_per_turnover']:.0f} bps/turnover)

- Best risk-adjusted result: **{NAMES[best]}**, Sharpe {st[best]['sharpe']:.2f}. {verdict}
- Risk parity cut max drawdown to {pct(st['risk_parity']['max_drawdown'])} vs {pct(st['spy']['max_drawdown'])} for SPY,
  at {pct(st['risk_parity']['vol'])} volatility vs {pct(st['spy']['vol'])}.
- {alpha_line}; mean-variance: {pct(att['alpha_annual'])} a year,
  t = {att['alpha_t']:.2f}.

| Strategy | CAGR | Vol | Sharpe | Max DD | VaR95 (1m) | CVaR95 (1m) | Avg turnover / month |
|---|---|---|---|---|---|---|---|
{rows}

### Fama-French 5 + momentum attribution ({att['start']} to {att['end']})

| Strategy | Alpha (ann.) | t(alpha) | Mkt-RF | SMB | HML | RMW | CMA | MOM | R² |
|---|---|---|---|---|---|---|---|---|---|
{arows}

## Method

- **Data:** dividend-adjusted daily closes (yfinance) for {uni}; month-end returns {sm['returns_start']} to
  {sm['returns_end']}. Factors: Ken French Data Library (through {sm['factors_end']}). Raw files are frozen and
  SHA-256 hashed in `data/MANIFEST.json`.
- **Walk-forward:** each month's weights use only the prior {cfg['lookback_months']} months. Covariance is shrunk
  {cfg['cov_shrinkage']:.0%} toward its diagonal. Long-only, {cfg['weight_cap']:.0%} cap per ETF (risk parity uncapped).
- **Mean-variance:** maximise w'mu - (lambda/2) w'Σw, lambda = {cfg['mv_risk_aversion']}, mu = trailing sample mean.
- **Risk parity:** equal risk contribution.
- **Black-Litterman:** equal-weight prior (delta = {cfg['bl_delta']}, tau = {cfg['bl_tau']}); absolute views from the
  {cfg['bl_views']}; posterior fed to the same mean-variance optimizer.
- **Risk:** historical {cfg['var_level']:.0%} VaR/CVaR on monthly net returns; drawdowns from the net wealth path.

## Limits

- Equal-weight is the BL prior because ETF market caps are not a meaningful "market portfolio" here.
- Momentum views make BL turnover high ({pct(st['black_litterman']['avg_monthly_turnover'])} a month); costs are charged.
- Attribution t-stats are plain OLS, not Newey-West. Survivorship is not an issue (all ETFs are live) but
  the universe was chosen in 2026.

## Reproduce

```bash
pip install -e .[dev]
make all      # verify hashes, run analysis, rebuild README, ruff, pytest (offline)
make fetch    # ONLINE: re-download (changes hashes)
```
"""
(ROOT / "README.md").write_text(text)
print("README.md written")
