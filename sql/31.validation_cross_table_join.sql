WITH latest_prices AS (
    SELECT
        ticker,
        date_key,
        close,
        ROW_NUMBER() OVER (
            PARTITION BY ticker
            ORDER BY date_key DESC
        ) AS row_num
    FROM fact_prices
)
SELECT
    s.ticker,
    s.company_name,
    s.gics_sector,
    p.date_key AS latest_price_date,
    ROUND(p.close, 2) AS latest_close
FROM latest_prices p
JOIN dim_security s
    ON p.ticker = s.ticker
WHERE p.row_num = 1
ORDER BY s.gics_sector, s.company_name
LIMIT 25