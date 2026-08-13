CREATE TABLE robo_advisor_tt.fact_prices
WITH (
format = 'PARQUET',
partitioned_by = ARRAY['year'],
external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/fact_prices/'
) AS
WITH unioned AS (
SELECT
ticker,
CAST("date" AS date) AS price_date,
open, high, low, close,
CAST(volume AS bigint) AS volume,
1 AS source_priority,
ingestion_date
FROM robo_advisor_tt.raw_stooq
UNION ALL
SELECT
ticker,
CAST("date" AS date) AS price_date,
open, high, low, close,
CAST(volume AS bigint) AS volume,
2 AS source_priority,
ingestion_date
FROM robo_advisor_tt.raw_yfinance_ohlcv
WHERE ticker != 'SPY'
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
SELECT ticker, price_date, open, high, low, close, volume
FROM deduped
WHERE rn = 1
),
with_return AS (
SELECT
ticker, price_date, open, high, low, close, volume,
(close - lag(close) OVER (PARTITION BY ticker ORDER BY price_date))
/ NULLIF(lag(close) OVER (PARTITION BY ticker ORDER BY price_date), 0)
AS daily_return
FROM one_per_key
)
SELECT
ticker,
price_date,
CAST(date_format(price_date, '%Y%m%d') AS integer) AS date_key,
open, high, low, close, volume,
daily_return,
year(price_date) AS year
FROM with_return