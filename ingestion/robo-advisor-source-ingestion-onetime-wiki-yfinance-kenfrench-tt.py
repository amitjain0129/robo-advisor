"""
robo_advisor_source_ingestion_onetime.py

ONE-TIME source ingestion for the Robo Advisor project (Glue Python Shell job).
Fetches the three live-fetchable one-time sources and lands them in the S3 raw
zone, partitioned by ingestion_date (Hive-style) for Glue crawler / Athena
auto-detection.

Sources ingested here (live fetch):
  1. Wikipedia   -> S&P 500 constituent list (also used as ticker list)
  2. yfinance    -> per-ticker fundamentals (security dimension enrichment)
  3. Ken French  -> Fama/French 3 factors + RF (monthly factor fact)

NOT ingested here:
  * Stooq bulk OHLCV -> its bulk endpoint is behind a CAPTCHA + per-IP daily
    limit that blocks automated download. Acquired once manually via browser
    and uploaded to raw/stooq/ separately. (ingest_stooq/norm kept below,
    unused, to document the attempted live-fetch approach.)

Runtime: AWS Glue Python Shell.
Job parameters:
  --additional-python-modules yfinance==0.2.65,pandas==2.2.3,requests==2.32.5,lxml==5.3.0,html5lib==1.1,beautifulsoup4==4.12.3,pyarrow==16.1.0
  --BUCKET   mgmt59900-group1-robo-advisor-tt
NOTE: boto3 is preinstalled in Glue Python Shell; do not pin it.

The daily yfinance-OHLCV job is a SEPARATE script (this one is one-time only).
"""

import sys
import io
import os
import time
import zipfile
import datetime as dt

import requests
import pandas as pd
import boto3

# ----- Glue job parameters -------------------------------------------------
# In Glue this comes via getResolvedOptions; kept import-light for local testing.
try:
    from awsglue.utils import getResolvedOptions
    _args = getResolvedOptions(sys.argv, ["BUCKET"])
    BUCKET = _args["BUCKET"]
except Exception:
    BUCKET = os.environ.get("BUCKET", "mgmt59900-group1-robo-advisor-tt")

INGESTION_DATE = dt.date.today().isoformat()  # YYYY-MM-DD
RAW = "raw"

s3 = boto3.client("s3")

# Browser-like header: Wikipedia 403s bare requests; Stooq is picky too.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
STOOQ_BULK_URL = "https://stooq.com/db/d/?b=d_us_txt"
FF_ZIP_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_CSV.zip"
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _key(source, filename):
    """Build the raw-zone S3 key. Note: bare key, NO s3:// scheme, no leading /."""
    return f"{RAW}/{source}/ingestion_date={INGESTION_DATE}/{filename}"


def _put_bytes(source, filename, data: bytes):
    key = _key(source, filename)
    s3.put_object(Bucket=BUCKET, Key=key, Body=data)
    print(f"  wrote s3://{BUCKET}/{key}  ({len(data):,} bytes)")


def _put_df_parquet(source, filename, df: pd.DataFrame):
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    _put_bytes(source, filename, buf.getvalue())


def _put_df_csv(source, filename, df: pd.DataFrame):
    _put_bytes(source, filename, df.to_csv(index=False).encode("utf-8"))


def norm(t: str) -> str:
    """
    Normalize a ticker to a bare-alphanumeric matching key, stripping ALL
    separators on both sides so BRK.B / BRK-B / BRKB all collapse to BRKB.
    (Learned the hard way: a simple .->- swap silently drops share-class
    tickers whose Stooq convention doesn't line up with Wikipedia's.)
    """
    t = str(t).upper().replace(".US", "")
    t = t.replace(".", "").replace("-", "")
    return t


# ---------------------------------------------------------------------------
# 1. Wikipedia — S&P 500 constituents  (also returns the ticker filter list)
# ---------------------------------------------------------------------------
def ingest_wikipedia():
    print("[wikipedia] fetching constituent list...")
    resp = requests.get(WIKI_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    # read_html needs a file-like object on newer pandas; wrap in StringIO.
    sp500 = pd.read_html(io.StringIO(resp.text))[0]  # first table = constituents
    # Select + rename to the schema we actually want (locks the dim spine).
    raw = sp500[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
    raw.columns = ["ticker", "company_name", "gics_sector", "gics_sub_industry"]
    # CANONICAL TICKER FORMAT = hyphen form (BRK-B). Every source must emit this
    # so dim_security joins line up downstream.
    raw["ticker"] = raw["ticker"].str.replace(".", "-", regex=False)
    _put_df_csv("wikipedia", "sp500_constituents.csv", raw)
    tickers = raw["ticker"].tolist()
    print(f"[wikipedia] {len(tickers)} tickers")
    return tickers


# ---------------------------------------------------------------------------
# 2. Stooq — bulk US OHLCV, filtered to S&P 500
# ---------------------------------------------------------------------------
def ingest_stooq(tickers):
    print("[stooq] downloading bulk US txt archive (large)...")
    # Map normalized key -> canonical (hyphen) Wikipedia ticker.
    wanted = {norm(t): t for t in tickers}

    # Stream to a temp file rather than holding the whole ZIP in memory.
    tmp_zip = "/tmp/stooq_us.zip"
    with requests.get(STOOQ_BULK_URL, headers=HEADERS, stream=True, timeout=600) as r:
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "unknown")
        clen = r.headers.get("Content-Length", "unknown")
        print(f"[stooq] HTTP {r.status_code}, Content-Type={ctype}, "
              f"Content-Length={clen}")
        with open(tmp_zip, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    size = os.path.getsize(tmp_zip)
    print(f"[stooq] archive saved ({size:,} bytes)")

    # DIAGNOSTIC: a real ZIP starts with magic bytes b'PK\x03\x04'.
    # If Stooq gated us, we got an HTML page instead — capture proof.
    with open(tmp_zip, "rb") as fh:
        head = fh.read(512)
    if not head.startswith(b"PK"):
        preview = head.decode("utf-8", errors="replace")
        print("[stooq] !! NOT A ZIP — Stooq returned non-archive content.")
        print("[stooq] first 512 bytes below:")
        print(preview)
        # Save the full response to S3 as evidence for the writeup.
        with open(tmp_zip, "rb") as fh:
            _put_bytes("stooq", "stooq_gate_response.html", fh.read())
        raise RuntimeError(
            "[stooq] bulk download was gated (not a ZIP). "
            "See stooq_gate_response.html and log preview above. "
            "This justifies landing the prepared stooq parquet via upload."
        )
    print("[stooq] ZIP magic OK; scanning...")

    frames = []
    found = set()
    with zipfile.ZipFile(tmp_zip) as zf:
        for info in zf.infolist():
            name = info.filename.lower()
            if not name.endswith(".us.txt"):
                continue
            stem = os.path.basename(name).replace(".us.txt", "")  # e.g. brk-b
            key = norm(stem)                                      # -> BRKB
            if key not in wanted:
                continue
            with zf.open(info) as fp:
                try:
                    df = pd.read_csv(fp)
                except Exception as e:
                    print(f"  skip {stem}: {e}")
                    continue
            if df.empty:
                continue
            # Stooq headers look like <TICKER>,<PER>,<DATE>,<OPEN>,... ; clean them.
            df.columns = (df.columns.str.replace("<", "", regex=False)
                                    .str.replace(">", "", regex=False)
                                    .str.strip().str.title())
            # Drop Stooq's own ticker col; use the canonical Wikipedia ticker.
            df = df.drop(columns=[c for c in df.columns if c == "Ticker"])
            df["Ticker"] = wanted[key]
            frames.append(df)
            found.add(key)

    if not frames:
        raise RuntimeError("[stooq] no matching tickers found — check normalization")

    prices = pd.concat(frames, ignore_index=True).rename(columns={"Vol": "Volume"})
    # Stooq dates are YYYYMMDD integers.
    prices["Date"] = pd.to_datetime(prices["Date"], format="%Y%m%d")
    prices = prices[["Ticker", "Date", "Open", "High", "Low", "Close", "Volume"]]
    prices = prices.sort_values(["Ticker", "Date"]).reset_index(drop=True)

    _put_df_parquet("stooq", "stooq_sp500_ohlcv.parquet", prices)
    missing = sorted(wanted[k] for k in (set(wanted) - found))
    if missing:
        _put_bytes("stooq", "stooq_missing_symbols.txt",
                   ("\n".join(missing)).encode("utf-8"))
        print(f"[stooq] {len(prices):,} rows, {prices['Ticker'].nunique()} tickers; "
              f"{len(missing)} not found: {missing}")
    else:
        print(f"[stooq] {len(prices):,} rows, {prices['Ticker'].nunique()} tickers; "
              f"all found")


# ---------------------------------------------------------------------------
# 3. yfinance — per-ticker fundamentals (slow, fragile: per-ticker try/except)
# ---------------------------------------------------------------------------
def ingest_yfinance_fundamentals(tickers):
    import yfinance as yf
    print(f"[yfinance] pulling fundamentals for {len(tickers)} tickers...")
    # tickers already arrive in canonical hyphen form (BRK-B), which yfinance
    # accepts; keep 'ticker' as the join key to match dim_security.
    fields = [
        "sector", "industry", "marketCap", "trailingPE",
        "forwardPE", "beta", "dividendYield", "currency", "quoteType",
    ]
    rows, rejected = [], []
    for i, t in enumerate(tickers, 1):
        try:
            info = yf.Ticker(t).info
            if not info or info.get("quoteType") is None:
                rejected.append(t)
                continue
            row = {"ticker": t}
            row.update({f: info.get(f) for f in fields})
            rows.append(row)
        except Exception as e:
            rejected.append(t)
            print(f"  reject {t}: {e}")
        if i % 50 == 0:
            print(f"  ...{i}/{len(tickers)}")
        time.sleep(0.4)  # be polite; yfinance rate-limits under load

    fund = pd.DataFrame(rows)
    _put_df_csv("yfinance/fundamentals", "yfinance_fundamentals_full.csv", fund)
    if rejected:
        _put_bytes("yfinance/fundamentals", "rejected_tickers.txt",
                   ("\n".join(rejected)).encode("utf-8"))
    print(f"[yfinance] {len(fund)} ok, {len(rejected)} rejected")


# ---------------------------------------------------------------------------
# 4. Ken French — Fama/French 3 factors + RF (monthly section only)
# ---------------------------------------------------------------------------
def ingest_french():
    print("[french] downloading factor zip...")
    resp = requests.get(FF_ZIP_URL, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        raw_text = zf.read(csv_name).decode("utf-8", errors="replace")

    # The CSV has a text preamble, then the MONTHLY table, then a blank line,
    # then an ANNUAL table. Keep only the monthly block:
    #   - data rows start where the first cell is a 6-digit YYYYMM
    #   - stop at the first blank line after data begins.
    lines = raw_text.splitlines()
    data_lines, started = [], False
    header = "Date,Mkt-RF,SMB,HML,RF"
    for ln in lines:
        cell0 = ln.split(",")[0].strip()
        if cell0.isdigit() and len(cell0) == 6:  # YYYYMM -> monthly row
            started = True
            data_lines.append(ln)
        elif started and ln.strip() == "":
            break  # end of monthly block (annual section follows)
    ff = pd.read_csv(io.StringIO(header + "\n" + "\n".join(data_lines)))
    _put_df_csv("french-factors", "ff_factors_monthly.csv", ff)
    print(f"[french] {len(ff)} monthly rows")


# ---------------------------------------------------------------------------
def main():
    print(f"=== one-time ingestion -> s3://{BUCKET}/{RAW}/  "
          f"(ingestion_date={INGESTION_DATE}) ===")
    # NOTE: Stooq bulk OHLCV is NOT fetched here — its bulk endpoint is behind a
    # CAPTCHA + per-IP daily limit that blocks automated download. It is acquired
    # once manually via browser and loaded to raw/stooq/ separately. This script
    # covers the three sources that CAN be fetched live.
    tickers = ingest_wikipedia()   # must run first: feeds yfinance
    ingest_yfinance_fundamentals(tickers)
    ingest_french()
    print("=== done ===")


if __name__ == "__main__":
    main()