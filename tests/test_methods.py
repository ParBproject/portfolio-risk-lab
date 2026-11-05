import math

import numpy as np
import pandas as pd
import pytest

from risklab import backtest, optimize, risk


def _cov():
    rng = np.random.default_rng(0)
    return optimize.shrink_cov(rng.normal(0, 0.04, (120, 5)) @ np.diag([1, 1.5, 2, 0.5, 1]))


def test_risk_parity_equalises_contributions():
    cov = _cov()
    rc = optimize.risk_contributions(optimize.risk_parity(cov), cov)
    assert np.allclose(rc, 0.2, atol=1e-3)


def test_black_litterman_with_prior_views_returns_prior():
    cov = _cov()
    w = np.full(5, 0.2)
    pi = 2.5 * cov @ w
    assert np.allclose(optimize.black_litterman(cov, w, pi), pi)


def test_mean_variance_respects_bounds():
    w = optimize.mean_variance(np.array([0.02, 0.01, 0.0, 0.005, 0.01]), _cov())
    assert abs(w.sum() - 1) < 1e-8 and w.min() >= 0 and w.max() <= optimize.CAP + 1e-8


def test_var_cvar_known():
    r = pd.Series(np.arange(-10, 10) / 100)
    var, cvar = risk.hist_var_cvar(r, 0.95)
    assert abs(var - 0.0905) < 1e-9 and abs(cvar - 0.10) < 1e-9


def test_drawdown():
    assert risk.drawdown(pd.Series([0.1, -0.5, 0.2])).min() == -0.5


def test_no_lookahead():
    idx = pd.date_range("2000-01-31", periods=70, freq="ME")
    r = pd.DataFrame(0.01, index=idx, columns=["SPY", "IEF"])
    r.iloc[-1] = [10.0, 10.0]  # a future shock must not change earlier weights
    # The default 30% cap cannot be fully invested across two assets.
    _, w, _ = backtest.run(r, "mean_variance", cap=1.0)
    _, w2, _ = backtest.run(r.iloc[:-1], "mean_variance", cap=1.0)
    assert np.allclose(w.iloc[:-1], w2)


def test_summary_known_series():
    # Wealth 1 -> 1.1 -> 0.55 -> 0.66, so CAGR is 0.66 ** 4 - 1.
    # Sample variance of r is 43/300, so annualised vol is sqrt(43)/5.
    # rf is 1% a month, so the excess mean is -0.23/3 and Sharpe is -4.6/sqrt(43).
    # The 95% linear quantile is -0.44; only the -50% month is in that tail.
    r = pd.Series([0.10, -0.50, 0.20])
    rf = pd.Series([0.01, 0.01, 0.01])
    m = risk.summary(r, rf)
    assert m["months"] == 3
    assert m["cagr"] == pytest.approx(0.66**4 - 1)
    assert m["vol"] == pytest.approx(math.sqrt(43) / 5)
    assert m["sharpe"] == pytest.approx(-4.6 / math.sqrt(43))
    assert m["max_drawdown"] == -0.5
    assert m["worst_month"] == -0.5
    assert m["var95_monthly"] == pytest.approx(0.44)
    assert m["cvar95_monthly"] == pytest.approx(0.5)


def test_static_strategies_turnover_and_cost():
    # Two out-of-sample months: +10%/0, then -5%/+2%. Costs are turnover * bps / 1e4.
    # Month 0 is a deployment from cash, so turnover is 1. Month 1 rebalances back
    # from weights that drifted with the first month's returns.
    idx = pd.date_range("2000-01-31", periods=backtest.LOOKBACK + 2, freq="ME")
    spy = np.zeros(len(idx))
    ief = np.zeros(len(idx))
    spy[-2], ief[-2] = 0.10, 0.00
    spy[-1], ief[-1] = -0.05, 0.02
    r = pd.DataFrame({"SPY": spy, "IEF": ief}, index=idx)
    bps = 10.0

    net, w, to = backtest.run(r, "equal_weight", cost_bps=bps)
    assert list(net.index) == list(idx[-2:])
    assert np.allclose(w, 0.5)
    assert to.iloc[0] == 1.0
    assert net.iloc[0] == pytest.approx(0.05 - bps / 1e4)
    # 0.5*1.10 and 0.5*1.00 drift to 11/21 and 10/21; L1 distance back to 1/2 is 1/21.
    assert to.iloc[1] == pytest.approx(1 / 21)
    assert net.iloc[1] == pytest.approx(-0.015 - (1 / 21) * bps / 1e4)
    net_default, _, _ = backtest.run(r, "equal_weight")
    assert np.allclose(net_default, net)

    net, w, to = backtest.run(r, "sixty_forty", cost_bps=bps)
    assert np.allclose(w["SPY"], 0.6) and np.allclose(w["IEF"], 0.4)
    assert to.iloc[0] == 1.0
    assert net.iloc[0] == pytest.approx(0.06 - bps / 1e4)
    # 0.6*1.10 and 0.4*1.00 drift to 33/53 and 20/53; L1 distance back is 12/265.
    assert to.iloc[1] == pytest.approx(12 / 265)
    assert net.iloc[1] == pytest.approx(-0.022 - (12 / 265) * bps / 1e4)

    net, w, to = backtest.run(r, "spy", cost_bps=bps)
    assert np.allclose(w["SPY"], 1.0) and np.allclose(w["IEF"], 0.0)
    assert to.iloc[0] == 1.0
    assert net.iloc[0] == pytest.approx(0.10 - bps / 1e4)
    # A one-asset book does not drift off its target, so the second month is free.
    assert to.iloc[1] == pytest.approx(0.0)
    assert net.iloc[1] == pytest.approx(-0.05)
    gross, _, _ = backtest.run(r, "spy", cost_bps=0.0)
    assert gross.iloc[0] == pytest.approx(0.10)
    assert gross.iloc[1] == pytest.approx(-0.05)


def test_mean_variance_infeasible_cap_raises():
    # cap * 5 = 0.5 < 1, so no long-only portfolio can be fully invested.
    # Previously this returned 20% each, above the cap.
    mu = np.array([0.02, 0.01, 0.0, 0.005, 0.01])
    with pytest.raises(ValueError, match="infeasible weight cap"):
        optimize.mean_variance(mu, np.eye(5) * 0.01, cap=0.1)


def test_mean_variance_at_binding_cap_stays_feasible():
    # cap * 4 = 1, so the only feasible portfolio is every weight equal to the cap.
    mu = np.array([0.02, 0.01, 0.0, 0.005])
    w = optimize.mean_variance(mu, np.eye(4) * 0.01, cap=0.25)
    assert np.allclose(w, 0.25)
