import subprocess
import sys
from pathlib import Path

from risklab import data

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_matches():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/manifest.py"), "--check"], capture_output=True)
    assert r.returncode == 0, r.stderr


def test_universe_is_etfs_only_and_complete():
    r = data.monthly_returns()
    assert set(r.columns) == set(data.meta()["tickers"]) == set(data.ASSET_CLASS)
    assert r.index[0].strftime("%Y-%m") == "2007-05"  # HYG launched 2007-04-11
    assert r.index[-1].strftime("%Y-%m") == "2026-09"
    assert r.notna().all().all()
    assert (r.abs() < 0.6).all().all()


def test_factors_parse():
    f = data.factors()
    assert list(f.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF", "MOM"]
    assert f.index[0].strftime("%Y-%m") == "1963-07"
    assert f["RF"].between(-0.001, 0.02).all()
