CREATE TABLE robo_advisor_tt.fact_asset_class
WITH (
  format = 'PARQUET',
  external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/fact_asset_class/'
) AS
WITH unioned AS (
  -- one-time backfill: deep history, carries true Adj_Close (total-return basis)
  SELECT
    ticker,
    CAST("date" AS date) AS price_date,
    open, high, low, close,
    adj_close,
    CAST(volume AS bigint) AS volume,
    1 AS source_priority,
    ingestion_date
  FROM robo_advisor_tt.raw_asset_class
  UNION ALL
  -- nightly job keeps sleeves current, but has no adj_close yet -> NULL.
  -- Until the nightly job captures Adj Close, recent-only days fall back to
  -- price-return via COALESCE below. Documented as a known basis seam.
  SELECT
    ticker,
    CAST("date" AS date) AS price_date,
    open, high, low, close,
    CAST(NULL AS double) AS adj_close,
    CAST(volume AS bigint) AS volume,
    2 AS source_priority,
    ingestion_date
  FROM robo_advisor_tt.raw_yfinance_ohlcv
  WHERE ticker IN ('AGG', 'VXUS', 'GLD', 'BIL')
),
deduped AS (
  SELECT *,
    row_number() OVER (
      PARTITION BY ticker, price_date
      ORDER BY source_priority ASC, ingestion_date DESC
    ) AS rn
  FROM unioned
),
one_per_key AS (
  SELECT ticker, price_date, open, high, low, close, adj_close, volume
  FROM deduped
  WHERE rn = 1
),
with_return AS (
  SELECT
    ticker, price_date, open, high, low, close, adj_close, volume,
    -- total-return where adj_close exists (deep history), price-return
    -- fallback on recent nightly-only days that lack adj_close.
    (COALESCE(adj_close, close)
       - lag(COALESCE(adj_close, close)) OVER (PARTITION BY ticker ORDER BY price_date))
    / NULLIF(lag(COALESCE(adj_close, close)) OVER (PARTITION BY ticker ORDER BY price_date), 0)
    AS daily_return
  FROM one_per_key
)
SELECT
  ticker,
  price_date,
  CAST(date_format(price_date, '%Y%m%d') AS integer) AS date_key,
  open, high, low, close,
  adj_close,
  volume,
  daily_return
FROM with_return