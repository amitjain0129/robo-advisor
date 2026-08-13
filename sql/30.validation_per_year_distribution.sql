SELECT year, count(*) AS row_count, min(price_date) AS first_date, max(price_date) AS last_date
FROM robo_advisor_tt.fact_prices
GROUP BY year
ORDER BY year