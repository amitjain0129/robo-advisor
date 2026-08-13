CREATE TABLE robo_advisor_tt.fact_factor_returns
WITH (
format = 'PARQUET',
external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/fact_factor_returns/'
) AS
WITH src AS (
SELECT "date" AS yyyymm, mkt_rf, smb, hml, rf
FROM robo_advisor_tt.raw_french
WHERE ingestion_date = (
SELECT max(ingestion_date) FROM robo_advisor_tt.raw_french
)
AND regexp_like("date", '^[0-9]{6}$')
),
dated AS (
SELECT
yyyymm,
date_parse(yyyymm || '01', '%Y%m%d') AS month_start,
mkt_rf, smb, hml, rf
FROM src
)
SELECT
CAST(substr(yyyymm, 1, 4) AS integer) AS year,
CAST(substr(yyyymm, 5, 2) AS integer) AS month,
CAST(last_day_of_month(month_start) AS date) AS month_end_date,
CAST(date_format(last_day_of_month(month_start), '%Y%m%d') AS integer) AS date_key,
mkt_rf,
smb,
hml,
rf
FROM dated