import numpy as np
import pandas as pd

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
    _, w, _ = backtest.run(r, "mean_variance")
    _, w2, _ = backtest.run(r.iloc[:-1], "mean_variance")
    assert np.allclose(w.iloc[:-1], w2)
