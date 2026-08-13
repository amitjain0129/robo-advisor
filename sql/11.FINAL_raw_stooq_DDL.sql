CREATE EXTERNAL TABLE robo_advisor_tt.raw_stooq (
ticker string,
date timestamp,
open double,
high double,
low double,
close double,
volume double
)
PARTITIONED BY (ingestion_date string)
STORED AS PARQUET
LOCATION 's3://mgmt59900-group1-robo-advisor-tt/raw/stooq/'