"""Export everything the web app needs to web/public/data/app.json (from the same code as results/)."""
import json
from pathlib import Path

import numpy as np

from risklab import backtest, data

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data" / "app.json"
CAPS = [0.2, 0.3, 0.5]
CAPPED = ("mean_variance", "black_litterman")


def main() -> None:
    S = json.loads((ROOT / "results" / "summary.json").read_text())
    r = data.monthly_returns()
    f = data.factors()
    variants = {}
    for s in backtest.STRATEGIES:
        for cap in CAPS if s in CAPPED else [None]:
            net, w, to = backtest.run(r, s, cap=cap if cap else 0.3, cost_bps=0.0)
            key = f"{s}@{cap}" if cap else s
            variants[key] = {
                "strategy": s, "cap": cap,
                "gross": [round(float(x), 8) for x in net],
                "turnover": [round(float(x), 8) for x in to],
                "weights": [[round(float(x), 4) for x in row] for row in w.to_numpy()],
            }
            print(key, "done")
    dates = [d.strftime("%Y-%m") for d in r.index[backtest.LOOKBACK:]]
    fx = f.reindex(r.index[backtest.LOOKBACK:])
    app = {
        "dates": dates, "tickers": list(r.columns), "asset_class": S["universe"],
        "rf": [round(float(x), 6) if not np.isnan(x) else None for x in fx["RF"]],
        "factors": {k: [round(float(x), 6) if not np.isnan(x) else None for x in fx[k]]
                    for k in ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM")},
        "default_cap": 0.3, "default_cost_bps": S["settings"]["cost_bps_per_turnover"], "caps": CAPS,
        "settings": S["settings"], "sample": S["sample"], "summary": S["strategies"], "variants": variants,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
