"""ONLINE ONLY: download monthly ETF total-return prices and Fama-French factors. Outputs are frozen."""
import io
import json
import urllib.request
import zipfile
from pathlib import Path

import yfinance as yf

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
START, END = "2007-01-01", "2026-10-01"  # frozen window: month-ends through 2026-09
TICKERS = ["SPY", "IWM", "EFA", "EEM", "IEF", "TLT", "SHY", "LQD", "HYG", "TIP",
           "GLD", "DBC", "VNQ", "XLK", "XLF", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
px = yf.download(TICKERS, start=START, end=END, auto_adjust=True, progress=False)["Close"]
px.round(6).to_csv(RAW / "etf_adjclose_daily.csv")
FF = {"ff5": "F-F_Research_Data_5_Factors_2x3_CSV.zip", "mom": "F-F_Momentum_Factor_CSV.zip"}
for k, f in FF.items():
    url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/" + f
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    (RAW / f"{k}_raw.csv").write_bytes(z.read(z.namelist()[0]))
(RAW / "meta.json").write_text(json.dumps({"tickers": TICKERS, "start": START, "end_exclusive": END,
    "prices": "yfinance auto_adjust=True (dividend/split-adjusted close)",
    "factors": "Kenneth R. French Data Library, FF5 2x3 + Momentum, monthly"}, indent=2))
print(px.shape, px.first_valid_index(), px.index[-1])
