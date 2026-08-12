//** Portfolio Allocation for a Selected Risk Tier **//

SELECT
    tier_name,
    ticker,
    ROUND(AVG(weight) * 100, 2) AS allocation_pct
FROM fact_tier_weights
WHERE tier_name = 'moderate'
GROUP BY
    tier_name,
    ticker
ORDER BY
    allocation_pct DESC;


//** Growth of Selected Portfolio vs. SPY **//

SELECT
    date,
    tier_name,
    ROUND(equity, 3) AS growth_of_1
FROM fact_backtest
WHERE tier_name IN ('moderate', 'SPY_benchmark')
ORDER BY
    date,
    tier_name;

//* Maximum Drawdown: Risk Tier vs. SPY **//

SELECT
    tier_name,
    ROUND(MIN(drawdown) * 100, 2) AS max_drawdown_pct
FROM fact_backtest
WHERE tier_name IN ('moderate', 'SPY_benchmark')
GROUP BY
    tier_name
ORDER BY
    max_drawdown_pct DESC;

//** Top 10 S&P 500 Stocks YTD  **//

SELECT
    ticker,
    ROUND(ytd_return * 100, 2) AS ytd_return_pct
FROM fact_stock_screener
WHERE ytd_return IS NOT NULL
ORDER BY
    ytd_return DESC
LIMIT 10;