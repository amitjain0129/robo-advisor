SELECT
    date,
    tier_name,
    ROUND(equity, 3) AS growth_of_1
FROM fact_backtest
WHERE tier_name IN ('moderate', 'SPY_benchmark')
ORDER BY
    date,
    tier_name