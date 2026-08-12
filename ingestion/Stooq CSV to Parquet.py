import pandas as pd

CSV_PATH = r"C:\Purdue\Classes\MGMT 59900 Big Data Analytics in the Cloud\Group 1 Project\stooq_sp500_ohlcv.csv"
PARQUET_PATH = r"C:\Purdue\Classes\MGMT 59900 Big Data Analytics in the Cloud\Group 1 Project\stooq_sp500_ohlcv.parquet"

# --- Read the CSV, parsing Date back to a real datetime ---
prices = pd.read_csv(CSV_PATH, parse_dates=["Date"])

# --- Write Parquet ---
prices.to_parquet(PARQUET_PATH, index=False)

# --- Confirm ---
import os
csv_mb = os.path.getsize(CSV_PATH) / 1e6
pq_mb  = os.path.getsize(PARQUET_PATH) / 1e6
print(f"Rows: {len(prices):,} | Tickers: {prices['Ticker'].nunique()}")
print(f"CSV:     {csv_mb:.1f} MB")
print(f"Parquet: {pq_mb:.1f} MB  ({csv_mb/pq_mb:.1f}x smaller)")
print(prices.dtypes)