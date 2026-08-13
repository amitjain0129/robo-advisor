SELECT count(*) AS shifted_rows
FROM robo_advisor_tt.raw_fundamentals
WHERE ingestion_date = (SELECT max(ingestion_date) FROM robo_advisor_tt.raw_fundamentals)
  AND (sector LIKE '%"%' OR industry LIKE '%"%' OR quotetype LIKE '%"%')