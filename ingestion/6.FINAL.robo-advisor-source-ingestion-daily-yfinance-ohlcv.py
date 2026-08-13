"""
robo-advisor-source-ingestion-daily-yfinance-ohlcv-tt.py
DAILY yfinance OHLCV incremental (Glue Python Shell job).

Pulls a short recent window of daily prices for the S&P 500 universe and lands
it in the partitioned raw zone. Designed to run nightly on a schedule
(EventBridge). Deep history comes from the one-time Stooq load; this job keeps
the price fact current.

Config is hardcoded (no job parameters) to avoid Glue parameter-resolution
issues. Only --additional-python-modules is set on the job:
  yfinance==0.2.65,pandas==2.2.3,requests==2.32.5,lxml==5.3.0,html5lib==1.1,beautifulsoup4==4.12.3,pyarrow==16.1.0,boto3

Reads S&P 500 tickers from the latest Wikipedia constituents already in raw/.
Writes to:
  raw/yfinance/ohlcv/ingestion_date=YYYY-MM-DD/yfinance_ohlcv_<runid>.parquet
Rejected tickers to:
  rejected/yfinance/ohlcv/ingestion_date=YYYY-MM-DD/rejected_tickers_<runid>.txt
"""

import io
import time
import datetime as dt

import pandas as pd
import boto3

# ---- hardcoded config (no getResolvedOptions, no argparse, no params) ----
BUCKET = "mgmt59900-group1-robo-advisor-tt"
RAW = "raw"
# How many calendar days back to pull each run. A few days of overlap makes the
# job resilient to weekends/holidays/missed runs; downstream de-dups on
# (Ticker, Date) so re-pulling recent days is safe.
LOOKBACK_DAYS = 5

RUN_TS = dt.datetime.now(dt.timezone.utc)
INGESTION_DATE = RUN_TS.strftime("%Y-%m-%d")
RUN_ID = RUN_TS.strftime("%Y%m%dT%H%M%SZ")

OHLCV_KEY = (f"{RAW}/yfinance/ohlcv/ingestion_date={INGESTION_DATE}/"
             f"yfinance_ohlcv_{RUN_ID}.parquet")
REJECTED_KEY = (f"rejected/yfinance/ohlcv/ingestion_date={INGESTION_DATE}/"
                f"rejected_tickers_{RUN_ID}.txt")

EXPECTED_COLS = ["Ticker", "Date", "Open", "High", "Low", "Close", "Adj_Close", "Volume"]

s3 = boto3.client("s3")


def _latest_constituents_key():
    """Find the most recent Wikipedia constituents file already in raw/."""
    prefix = f"{RAW}/wikipedia/"
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".csv"):
                keys.append(obj["Key"])
    if not keys:
        raise RuntimeError(
            f"No constituents CSV found under s3://{BUCKET}/{prefix}. "
            f"Run the one-time source ingestion first."
        )
    # Keys embed ingestion_date=YYYY-MM-DD, so lexical max = most recent date.
    return sorted(keys)[-1]


def get_universe():
    key = _latest_constituents_key()
    print(f"[ohlcv] reading universe from s3://{BUCKET}/{key}")
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    df = pd.read_csv(io.BytesIO(obj["Body"].read()))
    col = "ticker" if "ticker" in df.columns else df.columns[0]
    tickers = df[col].astype(str).str.strip().tolist()
    # Non-constituent tickers: appended after the Wikipedia universe so they
    # never inflate the 503 constituent count. Split downstream by role:
    #   SPY      -> fact_benchmark   (measured against)
    #   ETFs     -> fact_asset_class (allocated into; back dim_risk_tier tiers)
    BENCHMARKS = ["SPY"]                        # US large-cap benchmark
    ASSET_CLASS = ["AGG", "VXUS", "GLD", "BIL"] # bonds, intl equity, gold, T-bills
    extra = [t for t in (BENCHMARKS + ASSET_CLASS) if t not in tickers]
    tickers = tickers + extra
    print(f"[ohlcv] universe: {len(tickers)} tickers "
          f"({len(BENCHMARKS)} benchmark + {len(ASSET_CLASS)} asset-class)")
    return tickers


def fetch_ohlcv(tickers):
    import yfinance as yf
    start = (RUN_TS.date() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    end = (RUN_TS.date() + dt.timedelta(days=1)).isoformat()  # yf end is exclusive
    print(f"[ohlcv] pulling {start} -> {end} for {len(tickers)} tickers...")

    frames, rejected = [], []
    for i, t in enumerate(tickers, 1):
        try:
            # yfinance uses '-' tickers directly (BRK-B); auto_adjust=False 
            h = yf.Ticker(t).history(start=start, end=end, auto_adjust=False)
            if h is None or h.empty:
                rejected.append(t)
                continue
            # auto_adjust=False returns a separate 'Adj Close'; keep it (renamed
            # Athena-safe) so downstream can compute total-return. Constituents
            # (Stooq) are price-return; capturing adj_close here lets fact_prices
            # be rebuilt on a total-return basis over the backtest window later.
            h = h.reset_index()[["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]]
            h = h.rename(columns={"Adj Close": "Adj_Close"})
            h["Date"] = pd.to_datetime(h["Date"]).dt.tz_localize(None).dt.normalize()
            h.insert(0, "Ticker", t)
            frames.append(h)
        except Exception as e:
            rejected.append(t)
            print(f"  reject {t}: {e}")
        if i % 50 == 0:
            print(f"  ...{i}/{len(tickers)}")
        time.sleep(0.3)  # be polite; yfinance rate-limits under load

    if not frames:
        raise RuntimeError("[ohlcv] no data pulled — all tickers failed/empty")

    prices = pd.concat(frames, ignore_index=True)
    prices = prices[EXPECTED_COLS]
    prices = prices.sort_values(["Ticker", "Date"]).reset_index(drop=True)
    return prices, rejected


def main():
    print(f"=== daily yfinance OHLCV -> s3://{BUCKET}/{OHLCV_KEY} ===")
    tickers = get_universe()
    prices, rejected = fetch_ohlcv(tickers)

    print(f"[ohlcv] pulled {len(prices):,} rows, "
          f"{prices['Ticker'].nunique()} tickers, "
          f"{len(rejected)} rejected")
    if "Date" in prices.columns and len(prices):
        print(f"[ohlcv] date range: {prices['Date'].min()} -> {prices['Date'].max()}")

    # integrity check (same one that caught 23 bad Stooq rows)
    if {"High", "Low"}.issubset(prices.columns):
        bad = int((prices["High"] < prices["Low"]).sum())
        print(f"[ohlcv] rows where High < Low (should be 0): {bad}")

    # write prices
    buf = io.BytesIO()
    prices.to_parquet(buf, index=False, engine="pyarrow")
    s3.put_object(Bucket=BUCKET, Key=OHLCV_KEY, Body=buf.getvalue())
    print(f"[ohlcv] wrote s3://{BUCKET}/{OHLCV_KEY}  "
          f"({buf.getbuffer().nbytes:,} bytes)")

    # write rejected list (if any)
    if rejected:
        s3.put_object(Bucket=BUCKET, Key=REJECTED_KEY,
                      Body=("\n".join(rejected)).encode("utf-8"))
        print(f"[ohlcv] wrote {len(rejected)} rejected -> s3://{BUCKET}/{REJECTED_KEY}")

    print("=== done ===")


if __name__ == "__main__":
    main()
