CREATE EXTERNAL TABLE robo_advisor_tt.raw_wikipedia ( `ticker` string, `company_name` string, `gics_sector` string, `gics_sub_industry` string
)
PARTITIONED BY (`ingestion_date` string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES ( 'separatorChar' = ',', 'quoteChar' = '"', 'escapeChar' = '\\'
)
STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://mgmt59900-group1-robo-advisor-tt/raw/wikipedia'
TBLPROPERTIES ('skip.header.line.count'='1')