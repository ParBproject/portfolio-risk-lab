"""Check the summary figures printed in the README."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results" / "summary.json").read_text())
PINNED = {  # strategy: (cagr, vol, sharpe, max_drawdown, cvar95)
    "mean_variance": (0.1062, 0.1225, 0.7571, -0.2587, 0.0797),
    "risk_parity": (0.0530, 0.0545, 0.6823, -0.1272, 0.0293),
    "black_litterman": (0.0939, 0.1169, 0.6914, -0.1652, 0.0733),
    "equal_weight": (0.0826, 0.0957, 0.7107, -0.1861, 0.0565),
    "sixty_forty": (0.0916, 0.0899, 0.8442, -0.2052, 0.0514),
    "spy": (0.1445, 0.1403, 0.9225, -0.2393, 0.0832),
}


@pytest.mark.parametrize("name", list(PINNED))
def test_pinned(name):
    m = S["strategies"][name]
    got = (m["cagr"], m["vol"], m["sharpe"], m["max_drawdown"], m["cvar95_monthly"])
    assert got == pytest.approx(PINNED[name], abs=5e-4)


def test_sample():
    assert S["sample"] == {"returns_start": "2007-05", "returns_end": "2026-09", "factors_end": "2026-08",
                           "backtest_start": "2012-05"}


def test_risk_parity_converged():
    assert S["risk_parity_max_rc_gap"] < 1e-3


def test_readme_generated_from_results():
    readme = (ROOT / "README.md").read_text()
    for m in S["strategies"].values():
        assert f"{m['sharpe']:.2f}" in readme and f"{m['cagr'] * 100:.2f}%" in readme
