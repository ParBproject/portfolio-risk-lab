"""Long-only allocators. Callers pass a covariance estimated on past returns only."""
import numpy as np
from scipy.optimize import minimize

CAP = 0.30  # max weight per ETF


def shrink_cov(r: np.ndarray, delta: float = 0.5) -> np.ndarray:
    """Sample covariance shrunk toward its diagonal."""
    s = np.cov(r, rowvar=False)
    return (1 - delta) * s + delta * np.diag(np.diag(s))


def _solve(obj, n: int, cap: float = CAP) -> np.ndarray:
    x0 = np.full(n, 1.0 / n)
    res = minimize(obj, x0, method="SLSQP", bounds=[(0.0, cap)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
                   options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(res.x, 0, None)
    return w / w.sum()


def mean_variance(mu: np.ndarray, cov: np.ndarray, risk_aversion: float = 5.0, cap: float = CAP) -> np.ndarray:
    """max w'mu - (lambda/2) w'Σw, long-only, capped."""
    return _solve(lambda w: -(w @ mu) + 0.5 * risk_aversion * w @ cov @ w, len(mu), cap=cap)


def risk_parity(cov: np.ndarray) -> np.ndarray:
    """Equal risk contribution (long-only, uncapped)."""
    n = len(cov)

    def obj(w):
        rc = w * (cov @ w)
        return ((rc / rc.sum() - 1.0 / n) ** 2).sum() * 1e4

    return _solve(obj, n, cap=1.0)


def risk_contributions(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    rc = w * (cov @ w)
    return rc / rc.sum()


def black_litterman(cov: np.ndarray, w_mkt: np.ndarray, views_q: np.ndarray, delta: float = 2.5,
                    tau: float = 0.05) -> np.ndarray:
    """Posterior mean with absolute views on every asset (P = I), Omega = diag(tau Σ)."""
    pi = delta * cov @ w_mkt
    ts = tau * cov
    omega = np.diag(np.diag(ts))
    inv_ts = np.linalg.inv(ts)
    inv_om = np.linalg.inv(omega)
    return np.linalg.solve(inv_ts + inv_om, inv_ts @ pi + inv_om @ views_q)
