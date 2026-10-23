"""Performance and tail-risk metrics on monthly simple returns."""
import numpy as np
import pandas as pd


def drawdown(r: pd.Series) -> pd.Series:
    w = (1 + r).cumprod()
    return w / w.cummax() - 1


def hist_var_cvar(r: pd.Series, level: float = 0.95) -> tuple[float, float]:
    """Historical VaR/CVaR as positive monthly loss fractions."""
    q = np.quantile(r, 1 - level)
    return float(-q), float(-r[r <= q].mean())


def summary(r: pd.Series, rf: pd.Series) -> dict:
    ex = r - rf.reindex(r.index).fillna(0.0)
    n = len(r)
    var, cvar = hist_var_cvar(r)
    return {
        "cagr": float((1 + r).prod() ** (12 / n) - 1),
        "vol": float(r.std() * np.sqrt(12)),
        "sharpe": float(ex.mean() / ex.std() * np.sqrt(12)),
        "max_drawdown": float(drawdown(r).min()),
        "var95_monthly": var,
        "cvar95_monthly": cvar,
        "worst_month": float(r.min()),
        "months": n,
    }
