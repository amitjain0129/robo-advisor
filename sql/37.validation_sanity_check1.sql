SELECT
    tier_name,
    ROUND(MIN(drawdown) * 100, 2) AS max_drawdown_pct
FROM fact_backtest
WHERE tier_name IN ('moderate', 'SPY_benchmark')
GROUP BY
    tier_name
ORDER BY
    max_drawdown_pct DESC