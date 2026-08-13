"""
robo-advisor-source-ingestion-onetime-spy-history.py
ONE-TIME benchmark history load (Glue Python Shell). Hardcoded config,
NO job parameters (same pattern as the Stooq staged-load).

Pulls SPY's full daily history from yfinance (SPY inception ~1993) and lands
it in the raw zone as the benchmark series. The DAILY yfinance-OHLCV job
keeps SPY current going forward (SPY appended to its universe).

Modules: yfinance==0.2.65,pandas==2.2.3,pyarrow==16.1.0,boto3

Writes to:
  raw/benchmark/ingestion_date=YYYY-MM-DD/spy_history.parquet
Same 7-col schema as fact_prices sources so it curates identically:
  Ticker, Date, Open, High, Low, Close, Volume
"""

import io
import datetime as dt

import pandas as pd
import boto3

BUCKET = "mgmt59900-group1-robo-advisor-tt"
BENCHMARK = "SPY"
RAW = "raw"

INGESTION_DATE = dt.date.today().isoformat()
RAW_KEY = f"{RAW}/benchmark/ingestion_date={INGESTION_DATE}/spy_history.parquet"

EXPECTED_COLS = ["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]

s3 = boto3.client("s3")


def main():
    import yfinance as yf
    print(f"=== benchmark history load ({BENCHMARK}) -> s3://{BUCKET}/{RAW_KEY} ===")

    # period='max' pulls full available history (SPY -> ~1993).
    # auto_adjust=False keeps raw OHLC, matching the Stooq/daily convention.
    h = yf.Ticker(BENCHMARK).history(period="max", auto_adjust=False)
    if h is None or h.empty:
        raise RuntimeError(f"[benchmark] no data returned for {BENCHMARK}")

    h = h.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
    h["Date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()
    h.insert(0, "Ticker", BENCHMARK)
    h = h[EXPECTED_COLS].sort_values("Date").reset_index(drop=True)

    print(f"[benchmark] {len(h):,} rows, "
          f"date range {h['Date'].min()} -> {h['Date'].max()}")

    # integrity check (same one used across the pipeline)
    bad = int((h["High"] < h["Low"]).sum())
    print(f"[benchmark] rows where High < Low (should be 0): {bad}")

    buf = io.BytesIO()
    h.to_parquet(buf, index=False, engine="pyarrow")
    s3.put_object(Bucket=BUCKET, Key=RAW_KEY, Body=buf.getvalue())
    print(f"[benchmark] wrote s3://{BUCKET}/{RAW_KEY}  ({buf.getbuffer().nbytes:,} bytes)")
    print("=== done ===")


if __name__ == "__main__":
    main()
