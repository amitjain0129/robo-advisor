import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Purdue\Classes\MGMT 59900 Big Data Analytics in the Cloud\Group 1 Project\Datasets\d_us_txt\data\daily\us")

def norm(t):
    """Normalize a ticker to a common key: uppercase, strip .US, unify separators."""
    t = str(t).upper().replace(".US", "")
    t = t.replace(".", "").replace("-", "")   # BRK.B / BRK-B / BRKB -> BRKB
    return t

# --- 1. Inventory ALL Stooq files (ticker -> filepath) ---
stooq = {}
for f in BASE.rglob("*.us.txt"):
    raw = f.name.replace(".us.txt", "").upper()   # e.g. BRK-B
    stooq[norm(raw)] = (raw, f)                    # key on normalized, keep raw + path
print(f"Stooq inventory: {len(stooq)} US tickers")

# --- 2. Read Wikipedia universe ---
wiki = pd.read_csv("sp500_constituents.csv")
wiki["key"] = wiki["ticker"].apply(norm)
print(f"Wikipedia universe: {len(wiki)} tickers")

# --- 3. Match on normalized key ---
matched   = wiki[wiki["key"].isin(stooq)]
unmatched = wiki[~wiki["key"].isin(stooq)]
print(f"Matched: {len(matched)} | Unmatched: {len(unmatched)}")
if len(unmatched):
    print("Unmatched constituents:", unmatched["ticker"].tolist())

# --- 4. Load only the matched files ---
frames = []
for _, r in matched.iterrows():
    raw, path = stooq[r["key"]]
    df = pd.read_csv(path)
    df.columns = (df.columns.str.replace("<","",regex=False)
                            .str.replace(">","",regex=False).str.strip().str.title())
    df = df.drop(columns=[c for c in df.columns if c == "Ticker"])
    df["Ticker"] = r["ticker"]        # use the Wikipedia ticker as canonical
    frames.append(df)

prices = pd.concat(frames, ignore_index=True).rename(columns={"Vol": "Volume"})
prices["Date"] = pd.to_datetime(prices["Date"], format="%Y%m%d")
prices = prices[["Ticker","Date","Open","High","Low","Close","Volume"]]
prices = prices.sort_values(["Ticker","Date"]).reset_index(drop=True)

prices.to_csv("stooq_sp500_ohlcv.csv", index=False)
print(f"\nLoaded {prices['Ticker'].nunique()} tickers, {len(prices):,} rows")
