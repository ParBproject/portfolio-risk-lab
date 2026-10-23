# portfolio-risk-lab

Mean-variance, risk-parity and Black-Litterman portfolios on a 21-ETF multi-asset universe,
tested **walk-forward** against SPY, 60/40 and 1/N **after trading costs**, with VaR/CVaR, drawdowns and
Fama-French 5 + momentum attribution. Every number below is generated from `results/summary.json` by
`scripts/build_readme.py` and pinned by tests.

## Headline (out-of-sample 2012-05 to 2026-09, net of 10 bps/turnover)

- Best risk-adjusted result: **SPY**, Sharpe 0.92. None of the three optimizers beat plain SPY or 60/40 on Sharpe over this window; they are reported as-is, not tuned until they do.
- Risk parity cut max drawdown to -12.72% vs -23.93% for SPY,
  at 5.45% volatility vs 14.03%.
- No strategy shows a statistically significant factor alpha (all |t| < 2); mean-variance: -2.20% a year,
  t = -1.63.

| Strategy | CAGR | Vol | Sharpe | Max DD | VaR95 (1m) | CVaR95 (1m) | Avg turnover / month |
|---|---|---|---|---|---|---|---|
| Mean-variance | 10.62% | 12.25% | 0.76 | -25.87% | 6.48% | 7.97% | 23.49% |
| Risk parity (ERC) | 5.30% | 5.45% | 0.68 | -12.72% | 2.42% | 2.93% | 8.85% |
| Black-Litterman | 9.39% | 11.69% | 0.69 | -16.52% | 5.23% | 7.33% | 52.33% |
| Equal weight (1/N) | 8.26% | 9.57% | 0.71 | -18.61% | 4.09% | 5.65% | 2.34% |
| 60/40 SPY/IEF | 9.16% | 8.99% | 0.84 | -20.52% | 4.00% | 5.14% | 1.58% |
| SPY | 14.45% | 14.03% | 0.92 | -23.93% | 6.10% | 8.32% | 0.00% |

### Fama-French 5 + momentum attribution (2012-05 to 2026-08)

| Strategy | Alpha (ann.) | t(alpha) | Mkt-RF | SMB | HML | RMW | CMA | MOM | R² |
|---|---|---|---|---|---|---|---|---|---|
| Mean-variance | -2.20% | -1.63 | 0.82 | -0.12 | -0.09 | 0.17 | 0.08 | 0.13 | 0.85 |
| Risk parity (ERC) | -0.28% | -0.32 | 0.31 | 0.00 | -0.07 | 0.08 | 0.12 | 0.01 | 0.66 |
| Black-Litterman | -1.92% | -0.97 | 0.69 | -0.03 | -0.03 | 0.07 | 0.24 | 0.32 | 0.64 |
| Equal weight (1/N) | -1.11% | -1.17 | 0.62 | 0.01 | -0.00 | 0.08 | 0.12 | -0.01 | 0.88 |
| 60/40 SPY/IEF | -0.39% | -0.56 | 0.61 | -0.07 | -0.07 | 0.05 | 0.05 | 0.01 | 0.92 |
| SPY | -0.13% | -0.54 | 0.99 | -0.11 | 0.02 | 0.05 | 0.02 | 0.00 | 1.00 |

## Method

- **Data:** dividend-adjusted daily closes (yfinance) for DBC (Commodities), EEM (Emerging equity), EFA (Intl developed equity), GLD (Gold), HYG (High yield), IEF (7-10y Treasuries), IWM (US small cap), LQD (IG credit), SHY (1-3y Treasuries), SPY (US equity), TIP (TIPS), TLT (20y+ Treasuries), VNQ (US REITs), XLB (Materials sector), XLF (Financials sector), XLI (Industrials sector), XLK (Tech sector), XLP (Cons. staples sector), XLU (Utilities sector), XLV (Health care sector), XLY (Cons. discretionary sector); month-end returns 2007-05 to
  2026-09. Factors: Ken French Data Library (through 2026-08). Raw files are frozen and
  SHA-256 hashed in `data/MANIFEST.json`.
- **Walk-forward:** each month's weights use only the prior 60 months. Covariance is shrunk
  50% toward its diagonal. Long-only, 30% cap per ETF (risk parity uncapped).
- **Mean-variance:** maximise w'mu - (lambda/2) w'Σw, lambda = 5.0, mu = trailing sample mean.
- **Risk parity:** equal risk contribution.
- **Black-Litterman:** equal-weight prior (delta = 2.5, tau = 0.05); absolute views from the
  trailing 12m mean, skip 1m; posterior fed to the same mean-variance optimizer.
- **Risk:** historical 95% VaR/CVaR on monthly net returns; drawdowns from the net wealth path.

## Limits

- Equal-weight is the BL prior because ETF market caps are not a meaningful "market portfolio" here.
- Momentum views make BL turnover high (52.33% a month); costs are charged.
- Attribution t-stats are plain OLS, not Newey-West. Survivorship is not an issue (all ETFs are live) but
  the universe was chosen in 2026.

## Reproduce

```bash
pip install -e .[dev]
make all      # verify hashes, run analysis, rebuild README, ruff, pytest (offline)
make fetch    # ONLINE: re-download (changes hashes)
```
