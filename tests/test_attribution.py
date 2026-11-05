"""OLS on an orthogonal design with a closed form."""
import numpy as np
import pandas as pd
import pytest

from risklab.attribution import FACTORS, regress


def _hadamard(n: int = 8) -> np.ndarray:
    """Sylvester Hadamard. Columns are orthogonal and each has squared length n."""
    h = np.array([[1.0]])
    while h.shape[0] < n:
        h = np.block([[h, h], [h, -h]])
    return h


def test_regress_recovers_known_factor_model():
    # 8 months, 7 regressors, so one residual degree of freedom.
    # excess = 0.02 + 0.5 * Mkt-RF + 0.1 * e, with e the unused Hadamard column.
    # s^2 = ||0.1 e||^2 / 1 = 0.08 and (X'X)^{-1}_00 = 1/8, so se(alpha) = 0.1.
    # R^2 = 1 - 0.1^2 / (0.5^2 + 0.1^2) = 25/26. Alpha is annualised by * 12.
    h = _hadamard(8)
    alpha, b_mkt, noise = 0.02, 0.5, 0.1
    excess = alpha * h[:, 0] + b_mkt * h[:, 1] + noise * h[:, 7]
    rf = 0.001 * h[:, 1]
    idx = pd.date_range("2020-01-31", periods=8, freq="ME")
    factors = pd.DataFrame(0.0, index=idx, columns=[*FACTORS, "RF"])
    for j, name in enumerate(FACTORS):
        factors[name] = h[:, j + 1]
    factors["RF"] = rf
    factors.loc[idx[-1] + pd.offsets.MonthEnd(1)] = 0.0  # outside the return sample
    out = regress(pd.Series(excess + rf, index=idx, name="port"), factors)

    assert out["months"] == 8
    assert out["start"] == "2020-01"
    assert out["end"] == "2020-08"
    assert out["alpha_annual"] == pytest.approx(alpha * 12)
    assert out["alpha_t"] == pytest.approx(alpha / noise)
    assert out["r2"] == pytest.approx(25 / 26)
    assert out["betas"]["Mkt-RF"] == pytest.approx(b_mkt)
    for name in FACTORS:
        if name != "Mkt-RF":
            assert out["betas"][name] == pytest.approx(0.0, abs=1e-12)
