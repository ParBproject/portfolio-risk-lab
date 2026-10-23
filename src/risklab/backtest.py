"""Walk-forward monthly backtest: weights at month t use only returns through month t-1."""
import numpy as np
import pandas as pd

from . import optimize as opt

LOOKBACK = 60       # months of history per estimate
COST_BPS = 10.0     # one-way cost per unit of turnover
MOM_WINDOW = 12     # BL views: trailing 12-month mean return, skipping the latest month


def strategy_weights(name: str, hist: pd.DataFrame) -> np.ndarray:
    n = hist.shape[1]
    cov = opt.shrink_cov(hist.to_numpy())
    cols = list(hist.columns)
    if name == "equal_weight":
        return np.full(n, 1.0 / n)
    if name == "sixty_forty":
        w = np.zeros(n)
        w[cols.index("SPY")], w[cols.index("IEF")] = 0.6, 0.4
        return w
    if name == "spy":
        w = np.zeros(n)
        w[cols.index("SPY")] = 1.0
        return w
    if name == "mean_variance":
        return opt.mean_variance(hist.mean().to_numpy(), cov)
    if name == "risk_parity":
        return opt.risk_parity(cov)
    if name == "black_litterman":
        w_mkt = np.full(n, 1.0 / n)
        q = hist.iloc[-MOM_WINDOW - 1:-1].mean().to_numpy()
        mu = opt.black_litterman(cov, w_mkt, q)
        return opt.mean_variance(mu, cov)
    raise ValueError(name)


STRATEGIES = ["mean_variance", "risk_parity", "black_litterman", "equal_weight", "sixty_forty", "spy"]


def run(returns: pd.DataFrame, name: str) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    """Returns (net monthly returns, weights per month, turnover per month)."""
    dates = returns.index[LOOKBACK:]
    rets, wts, tos = [], [], []
    w_prev = np.zeros(returns.shape[1])
    for i, d in enumerate(dates):
        hist = returns.iloc[i:i + LOOKBACK]
        assert hist.index[-1] < d
        w = strategy_weights(name, hist)
        to = np.abs(w - w_prev).sum() if i else 1.0
        gross = float(w @ returns.loc[d].to_numpy())
        net = gross - to * COST_BPS / 1e4
        rets.append(net)
        wts.append(w)
        tos.append(to)
        drift = w * (1 + returns.loc[d].to_numpy())
        w_prev = drift / drift.sum()
    return (pd.Series(rets, index=dates, name=name), pd.DataFrame(wts, index=dates, columns=returns.columns),
            pd.Series(tos, index=dates, name=name))
