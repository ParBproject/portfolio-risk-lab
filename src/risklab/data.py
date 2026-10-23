"""Offline loaders for the frozen raw files in data/raw."""
import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"

ASSET_CLASS = {
    "SPY": "US equity", "IWM": "US small cap", "EFA": "Intl developed equity", "EEM": "Emerging equity",
    "IEF": "7-10y Treasuries", "TLT": "20y+ Treasuries", "SHY": "1-3y Treasuries", "LQD": "IG credit",
    "HYG": "High yield", "TIP": "TIPS", "GLD": "Gold", "DBC": "Commodities", "VNQ": "US REITs",
    "XLK": "Tech sector", "XLF": "Financials sector", "XLV": "Health care sector",
    "XLY": "Cons. discretionary sector", "XLP": "Cons. staples sector", "XLI": "Industrials sector",
    "XLU": "Utilities sector", "XLB": "Materials sector",
}


def meta() -> dict:
    return json.loads((RAW / "meta.json").read_text())


def daily_prices() -> pd.DataFrame:
    return pd.read_csv(RAW / "etf_adjclose_daily.csv", index_col=0, parse_dates=True).sort_index()


def monthly_returns() -> pd.DataFrame:
    """Simple total returns from month-end adjusted closes.

    First common full month is 2007-05 (HYG launched 2007-04-11)."""
    m = daily_prices().resample("ME").last()
    return m.pct_change().iloc[1:].dropna(how="any")


def _french(path: Path) -> pd.DataFrame:
    rows = []
    started = False
    for line in path.read_text(errors="ignore").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts[0] == "" and len(parts) > 1 and not started:
            cols = parts[1:]
            started = True
            continue
        if started:
            if len(parts[0]) == 6 and parts[0].isdigit():
                rows.append([parts[0]] + [float(x) for x in parts[1:]])
            elif rows:
                break
    df = pd.DataFrame(rows, columns=["ym"] + cols)
    df.index = pd.to_datetime(df.pop("ym"), format="%Y%m") + pd.offsets.MonthEnd(0)
    return df / 100.0


def factors() -> pd.DataFrame:
    """Monthly FF5 + momentum (decimal returns), month-end index."""
    ff = _french(RAW / "ff5_raw.csv")
    mom = _french(RAW / "mom_raw.csv")
    mom.columns = ["MOM"]
    return ff.join(mom, how="inner")
