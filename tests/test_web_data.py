"""The web app's exported data must reproduce results/summary.json at the published settings."""
import json
from pathlib import Path

import pandas as pd
import pytest

from risklab import data, risk

ROOT = Path(__file__).resolve().parents[1]
APP = json.loads((ROOT / "web" / "public" / "data" / "app.json").read_text())
S = json.loads((ROOT / "results" / "summary.json").read_text())


@pytest.mark.parametrize("name", list(S["strategies"]))
def test_exported_returns_reproduce_summary(name):
    key = f"{name}@{APP['default_cap']}" if f"{name}@{APP['default_cap']}" in APP["variants"] else name
    v = APP["variants"][key]
    idx = pd.PeriodIndex(APP["dates"], freq="M").to_timestamp("M")
    net = pd.Series(v["gross"], index=idx) - pd.Series(v["turnover"], index=idx) * APP["default_cost_bps"] / 1e4
    m = risk.summary(net, data.factors()["RF"].reindex(idx).fillna(0.0).set_axis(idx))
    for k in ("cagr", "vol", "sharpe", "max_drawdown", "cvar95_monthly"):
        assert m[k] == pytest.approx(S["strategies"][name][k], abs=1e-6)


def test_weights_valid():
    for v in APP["variants"].values():
        for row in v["weights"]:
            assert abs(sum(row) - 1) < 2e-3 and min(row) >= 0
            if v["cap"]:
                assert max(row) <= v["cap"] + 1e-4
