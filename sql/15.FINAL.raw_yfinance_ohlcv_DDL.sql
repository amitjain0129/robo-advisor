CREATE EXTERNAL TABLE robo_advisor_tt.raw_yfinance_ohlcv ( ticker string, `date` timestamp, open double, high double, low double, close double, adj_close double, volume bigint
)
PARTITIONED BY (ingestion_date string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS PARQUET
LOCATION 's3://mgmt59900-group1-robo-advisor-tt/raw/yfinance/ohlcv'
TBLPROPERTIES ('parquet.column.index.access' = 'false')