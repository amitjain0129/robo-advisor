"""
robo_stooq_load_hardcoded.py
ONE-TIME Stooq load (Glue Python Shell). Hardcoded config — NO job parameters
needed, to sidestep parameter-resolution issues. Reads the staged parquet and
writes it to the partitioned raw zone.
"""
import io
import datetime as dt
import pandas as pd
import boto3

# ---- hardcoded config (no getResolvedOptions, no argparse, no params) ----
BUCKET = "mgmt59900-group1-robo-advisor-tt"
STAGING_KEY = "staging/stooq/stooq_sp500_ohlcv.parquet"

INGESTION_DATE = dt.date.today().isoformat()
RAW_KEY = f"raw/stooq/ingestion_date={INGESTION_DATE}/stooq_sp500_ohlcv.parquet"

s3 = boto3.client("s3")
EXPECTED_COLS = ["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]


def main():
    print(f"=== stooq stage load -> s3://{BUCKET}/{RAW_KEY} ===")
    print(f"[stooq] reading staged file s3://{BUCKET}/{STAGING_KEY}")
    obj = s3.get_object(Bucket=BUCKET, Key=STAGING_KEY)
    prices = pd.read_parquet(io.BytesIO(obj["Body"].read()), engine="pyarrow")
    print(f"[stooq] loaded {len(prices):,} rows, "
          f"{prices.shape[1]} cols: {list(prices.columns)}")

    missing = [c for c in EXPECTED_COLS if c not in prices.columns]
    if missing:
        print(f"[stooq] WARNING: expected columns missing: {missing}")
    if "Ticker" in prices.columns:
        print(f"[stooq] distinct tickers: {prices['Ticker'].nunique()}")
    if "Date" in prices.columns:
        print(f"[stooq] date range: {prices['Date'].min()} -> {prices['Date'].max()}")
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in prices.columns:
            n_neg = int((prices[col] < 0).sum())
            n_null = int(prices[col].isna().sum())
            if n_neg or n_null:
                print(f"[stooq]   {col}: {n_neg} negative, {n_null} null")
    if {"High", "Low"}.issubset(prices.columns):
        bad = int((prices["High"] < prices["Low"]).sum())
        print(f"[stooq] rows where High < Low (should be 0): {bad}")

    buf = io.BytesIO()
    prices.to_parquet(buf, index=False, engine="pyarrow")
    s3.put_object(Bucket=BUCKET, Key=RAW_KEY, Body=buf.getvalue())
    print(f"[stooq] wrote s3://{BUCKET}/{RAW_KEY}  ({buf.getbuffer().nbytes:,} bytes)")
    print("=== done ===")


if __name__ == "__main__":
    main()
