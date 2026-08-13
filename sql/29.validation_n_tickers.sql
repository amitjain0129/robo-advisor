SELECT count(*) AS n_rows,
       count(DISTINCT ticker) AS n_tickers,
       count(*) FILTER (WHERE sector IS NULL) AS n_null_sector
FROM robo_advisor_tt.fact_stock_screener