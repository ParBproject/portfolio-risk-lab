"""Fama-French 5 + momentum time-series regression (OLS with Newey-West-free plain t-stats)."""
import numpy as np
import pandas as pd

FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]


def regress(r: pd.Series, f: pd.DataFrame) -> dict:
    d = pd.concat([r.rename("r"), f], axis=1, join="inner").dropna()
    y = (d["r"] - d["RF"]).to_numpy()
    X = np.column_stack([np.ones(len(d)), d[FACTORS].to_numpy()])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    s2 = resid @ resid / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    r2 = 1 - resid.var() / y.var()
    out = {"alpha_annual": float(beta[0] * 12), "alpha_t": float(beta[0] / se[0]), "r2": float(r2),
           "months": len(y), "start": d.index[0].strftime("%Y-%m"), "end": d.index[-1].strftime("%Y-%m")}
    out["betas"] = {k: float(b) for k, b in zip(FACTORS, beta[1:], strict=True)}
    return out
