"""Run every strategy walk-forward and write results/summary.json + results/*.csv."""
import json
from pathlib import Path

import pandas as pd

from . import attribution, backtest, data, optimize, risk

OUT = Path(__file__).resolve().parents[2] / "results"


def main() -> dict:
    OUT.mkdir(exist_ok=True)
    r = data.monthly_returns()
    f = data.factors()
    rf = f["RF"]
    nets, weights = {}, {}
    res: dict = {"universe": {t: data.ASSET_CLASS[t] for t in r.columns},
                 "sample": {"returns_start": r.index[0].strftime("%Y-%m"),
                            "returns_end": r.index[-1].strftime("%Y-%m"),
                            "factors_end": f.index[-1].strftime("%Y-%m")},
                 "settings": {"lookback_months": backtest.LOOKBACK, "cost_bps_per_turnover": backtest.COST_BPS,
                              "weight_cap": optimize.CAP, "cov_shrinkage": 0.5, "mv_risk_aversion": 5.0,
                              "bl_delta": 2.5, "bl_tau": 0.05, "bl_views": "trailing 12m mean, skip 1m",
                              "var_level": 0.95},
                 "strategies": {}}
    for s in backtest.STRATEGIES:
        net, w, to = backtest.run(r, s)
        nets[s], weights[s] = net, w
        m = risk.summary(net, rf)
        m["avg_monthly_turnover"] = float(to.iloc[1:].mean())
        m["attribution"] = attribution.regress(net, f)
        res["strategies"][s] = m
    res["sample"]["backtest_start"] = next(iter(nets.values())).index[0].strftime("%Y-%m")
    cov = optimize.shrink_cov(r.iloc[-backtest.LOOKBACK - 1:-1].to_numpy())
    last = {s: weights[s].iloc[-1] for s in ("mean_variance", "risk_parity", "black_litterman")}
    res["latest_weights"] = {s: {k: round(float(v), 4) for k, v in w.items() if v > 0.005} for s, w in last.items()}
    rc = optimize.risk_contributions(last["risk_parity"].to_numpy(), cov)
    res["risk_parity_max_rc_gap"] = float(abs(rc - 1 / len(rc)).max())
    pd.DataFrame(nets).to_csv(OUT / "monthly_net_returns.csv", float_format="%.8f")
    pd.DataFrame({s: risk.drawdown(n) for s, n in nets.items()}).to_csv(OUT / "drawdowns.csv", float_format="%.6f")
    (OUT / "summary.json").write_text(json.dumps(res, indent=2) + "\n")
    return res


if __name__ == "__main__":
    out = main()
    for s, m in out["strategies"].items():
        print(f"{s:16s} CAGR {m['cagr']:.2%} vol {m['vol']:.2%} SR {m['sharpe']:.2f} MDD {m['max_drawdown']:.2%} "
              f"CVaR {m['cvar95_monthly']:.2%} TO {m['avg_monthly_turnover']:.2%} "
              f"a {m['attribution']['alpha_annual']:.2%} (t {m['attribution']['alpha_t']:.2f})")
