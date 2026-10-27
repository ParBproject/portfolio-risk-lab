"""Write README.md from results/summary.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
META = json.loads((ROOT / "data" / "raw" / "meta.json").read_text())
MANIFEST = json.loads((ROOT / "data" / "MANIFEST.json").read_text())
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
verdict = (
    f"{', '.join(beat)} beat the better of SPY and 60/40 on Sharpe."
    if beat
    else "None of the three optimizers beat the better of SPY and 60/40 on Sharpe."
)
sig = [NAMES[k] for k in st if abs(st[k]["attribution"]["alpha_t"]) >= 2]
alpha_line = (
    "Alpha t-stat of 2 or more: " + ", ".join(sig) + "."
    if sig
    else "No alpha t-stat reaches 2."
)
rows = "\n".join(
    f"| {NAMES[k]} | {pct(m['cagr'])} | {pct(m['vol'])} | {m['sharpe']:.2f} | {pct(m['max_drawdown'])} | "
    f"{pct(m['var95_monthly'])} | {pct(m['cvar95_monthly'])} | {pct(m['avg_monthly_turnover'])} |"
    for k, m in st.items())
arows = "\n".join(
    f"| {NAMES[k]} | {pct(m['attribution']['alpha_annual'])} | {m['attribution']['alpha_t']:.2f} | "
    + " | ".join(f"{m['attribution']['betas'][f]:.2f}" for f in ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"))
    + f" | {m['attribution']['r2']:.2f} |" for k, m in st.items())
tickers = ", ".join(S["universe"])
att = st["mean_variance"]["attribution"]
rp, spy = st["risk_parity"], st["spy"]
text = f"""# portfolio-risk-lab

[![CI](https://github.com/ParBproject/portfolio-risk-lab/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ParBproject/portfolio-risk-lab/actions/workflows/ci.yml)

Walk-forward mean-variance, risk parity, and Black-Litterman on {len(S['universe'])} ETFs,
net of trading costs, compared with SPY, 60/40, and equal weight. Monthly historical VaR and CVaR,
drawdowns, and an OLS regression on the Fama-French five factors plus momentum.

App: [parbproject.github.io/portfolio-risk-lab](https://parbproject.github.io/portfolio-risk-lab/)

![Demo](docs/img/demo.gif)

| Desktop | Mobile |
|---|---|
| ![Overview](docs/img/overview.png) | ![Mobile](docs/img/mobile.png) |

## Results

{sm['backtest_start']} to {sm['returns_end']}, after {cfg['cost_bps_per_turnover']:.0f} bps per unit of turnover.
Weights each month use only the prior {cfg['lookback_months']} months.

{NAMES[best]} has the highest Sharpe, {st[best]['sharpe']:.2f}. {verdict}
Risk parity's max drawdown is {pct(rp['max_drawdown'])}, against {pct(spy['max_drawdown'])} for SPY,
with volatility {pct(rp['vol'])} versus {pct(spy['vol'])}. {alpha_line}
Mean-variance alpha is {pct(att['alpha_annual'])} a year (t = {att['alpha_t']:.2f}).

| Strategy | CAGR | Vol | Sharpe | Max DD | VaR95 (1m) | CVaR95 (1m) | Avg turnover / month |
|---|---|---|---|---|---|---|---|
{rows}

### Factor regression ({att['start']} to {att['end']})

| Strategy | Alpha (ann.) | t(alpha) | Mkt-RF | SMB | HML | RMW | CMA | MOM | R² |
|---|---|---|---|---|---|---|---|---|---|
{arows}

## Data

Prices: {META['prices']}, from Yahoo Finance via `yfinance`, {len(META['tickers'])} ETFs,
requested {META['start']} to {META['end_exclusive']} (end exclusive).
Factors: {META['factors']}.

Month-end simple returns run from {sm['returns_start']} to {sm['returns_end']}.
The factor files end in {sm['factors_end']}. Tickers: {tickers}.

`data/raw/` has {len(MANIFEST)} files. `data/MANIFEST.json` holds a SHA-256 for each one,
and `make all` fails if a file has changed. `make fetch` downloads a new copy and will change
the hashes and the results. The prices are stored so the study can be rerun offline;
Yahoo's terms still apply. The French factors are published for research use.

## Method

- Sample covariance, shrunk {cfg['cov_shrinkage']:.0%} toward its diagonal.
  Long only. Mean-variance and Black-Litterman cap each ETF at {cfg['weight_cap']:.0%}.
  Risk parity is uncapped.
- Mean-variance: maximise w'mu - (lambda/2) w'Σw, lambda = {cfg['mv_risk_aversion']}.
  mu is the trailing sample mean.
- Risk parity: equal risk contribution.
- Black-Litterman: equal-weight prior (delta = {cfg['bl_delta']}, tau = {cfg['bl_tau']}).
  Absolute views ({cfg['bl_views']}) on every ETF. The posterior mean goes into the same
  mean-variance optimizer.
- Historical {cfg['var_level']:.0%} VaR and CVaR on monthly net returns.
  Drawdowns are taken from the net wealth path.
- The regression uses Mkt-RF, SMB, HML, RMW, CMA, and MOM. t-stats are classical OLS,
  not Newey-West.

## Caveats

- The Black-Litterman prior is equal weight. There is no market-cap portfolio for this ETF list.
- Black-Litterman turnover averages {pct(st['black_litterman']['avg_monthly_turnover'])} a month,
  because the views follow recent returns. Costs are deducted.
- The ETFs were all still listed when the list was chosen in 2026, so funds that had already
  closed are not in the sample.

## Run

```bash
pip install -e ".[dev]"
make all      # check hashes, rerun the backtest, rewrite this file, ruff, pytest
make fetch    # re-download prices and factors (online; changes the hashes)
make web      # export the app data, run the Node tests, build the app (Node 20+)
make deploy   # publish web/dist to the gh-pages branch
```

`scripts/build_readme.py` fills the tables from `results/summary.json`.
At the default settings (cap {cfg['weight_cap']:.0%}, {cfg['cost_bps_per_turnover']:.0f} bps) the web app
matches those figures; `make web` checks that.
"""
(ROOT / "README.md").write_text(text)
print("README.md written")
