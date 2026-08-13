CREATE TABLE robo_advisor_tt.dim_date
WITH (
  format = 'PARQUET',
  external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/dim_date/'
) AS
SELECT
  d                                             AS full_date,
  CAST(date_format(d, '%Y%m%d') AS integer)     AS date_key,
  year(d)                                       AS year,
  month(d)                                      AS month,
  quarter(d)                                    AS quarter,
  day_of_month(d)                               AS day_of_month,
  day_of_week(d)                                AS day_of_week,
  date_format(d, '%W')                          AS day_name,
  date_format(d, '%M')                          AS month_name,
  CASE WHEN day_of_week(d) <= 5 THEN true ELSE false END AS is_weekday,
  CASE WHEN d = last_day_of_month(d) THEN true ELSE false END AS is_month_end
FROM (
  SELECT date_add('day', s.n, DATE '1962-01-01') AS d
  FROM UNNEST(
    sequence(0, date_diff('day', DATE '1962-01-01', DATE '2030-12-31'))
  ) AS s(n)
)