CREATE TABLE robo_advisor_tt.fact_stock_screener
WITH (
    format = 'PARQUET',
    external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/fact_stock_screener/'
) AS
WITH
bounds AS (
    SELECT max(price_date) AS as_of_date, max(year) AS as_of_year
    FROM robo_advisor_tt.fact_prices
),
trailing_dates AS (
    SELECT price_date, row_number() OVER (ORDER BY price_date DESC) AS rn
    FROM (
        SELECT DISTINCT price_date
        FROM robo_advisor_tt.fact_prices
    ) d
),
trailing_bounds AS (
    SELECT min(price_date) AS window_start, max(price_date) AS window_end
    FROM trailing_dates
    WHERE rn <= 252
),
ytd_raw AS (
    SELECT
        p.ticker,
        FIRST_VALUE(p.close) OVER (
            PARTITION BY p.ticker ORDER BY p.price_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS year_open_close,
        LAST_VALUE(p.close) OVER (
            PARTITION BY p.ticker ORDER BY p.price_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS current_close
    FROM robo_advisor_tt.fact_prices p
    CROSS JOIN bounds b
    WHERE p.year = b.as_of_year
),
ytd AS (
    SELECT DISTINCT ticker, year_open_close, current_close,
        (current_close - year_open_close) / year_open_close AS ytd_return
    FROM ytd_raw
),
trailing_slice AS (
    SELECT p.ticker, p.price_date, p.close, p.daily_return, p.volume
    FROM robo_advisor_tt.fact_prices p
    JOIN trailing_bounds tb
      ON p.price_date BETWEEN tb.window_start AND tb.window_end
),
risk_liq AS (
    SELECT
        ticker,
        stddev_samp(daily_return) * sqrt(252) AS annual_vol,
        avg(close * volume)                   AS avg_dollar_volume,
        max(close)                            AS high_52w,
        min(close)                            AS low_52w
    FROM trailing_slice
    GROUP BY ticker
),
dd_running AS (
    SELECT
        ticker,
        close / max(close) OVER (
            PARTITION BY ticker ORDER BY price_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) - 1 AS drawdown
    FROM trailing_slice
),
dd AS (
    SELECT ticker, min(drawdown) AS max_drawdown
    FROM dd_running
    GROUP BY ticker
)
SELECT
    y.ticker,
    s.gics_sector                         AS sector,
    y.year_open_close,
    y.current_close,
    y.ytd_return,
    RANK() OVER (ORDER BY y.ytd_return DESC) AS rank_gainer,
    RANK() OVER (ORDER BY y.ytd_return ASC)  AS rank_loser,
    r.annual_vol,
    d.max_drawdown,
    r.high_52w,
    r.low_52w,
    (y.current_close - r.high_52w) / r.high_52w AS pct_from_52w_high,
    (y.current_close - r.low_52w)  / r.low_52w  AS pct_from_52w_low,
    r.avg_dollar_volume,
    s.marketcap,
    s.trailingpe,
    s.dividendyield,
    s.beta
FROM ytd y
LEFT JOIN risk_liq r ON y.ticker = r.ticker
LEFT JOIN dd       d ON y.ticker = d.ticker
LEFT JOIN robo_advisor_tt.dim_security s ON y.ticker = s.ticker
ORDER BY y.ytd_return DESC