CREATE TABLE robo_advisor_tt.dim_security
WITH (
  format = 'PARQUET',
  external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/dim_security/'
) AS
WITH wiki AS (
  SELECT ticker, company_name, gics_sector, gics_sub_industry
  FROM robo_advisor_tt.raw_wikipedia
  WHERE ingestion_date = (
    SELECT max(ingestion_date) FROM robo_advisor_tt.raw_wikipedia
  )
),
fund AS (
  SELECT ticker, sector, industry, marketcap, trailingpe,
         forwardpe, beta, dividendyield, currency, quotetype
  FROM robo_advisor_tt.raw_fundamentals
  WHERE ingestion_date = (
    SELECT max(ingestion_date) FROM robo_advisor_tt.raw_fundamentals
  )
)
SELECT
  w.ticker,
  w.company_name,
  w.gics_sector,
  w.gics_sub_industry,
  f.sector          AS yf_sector,
  f.industry        AS yf_industry,
  f.marketcap,
  f.trailingpe,
  f.forwardpe,
  f.beta,
  f.dividendyield,
  f.currency,
  f.quotetype
FROM wiki w
LEFT JOIN fund f
  ON w.ticker = f.ticker