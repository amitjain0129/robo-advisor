CREATE TABLE robo_advisor_tt.dim_risk_tier
WITH (
  format = 'PARQUET',
  external_location = 's3://mgmt59900-group1-robo-advisor-tt/curated/dim_risk_tier/'
) AS
SELECT * FROM (
  VALUES
    -- tier_key, tier_name, risk_level, asset_class, ticker, min_weight, max_weight
    (1,'conservative',          1,'us_equity',   'SPY', 0.10, 0.30),
    (1,'conservative',          1,'intl_equity', 'VXUS',0.00, 0.10),
    (1,'conservative',          1,'fixed_income','AGG', 0.40, 0.70),
    (1,'conservative',          1,'alternatives','GLD', 0.00, 0.10),
    (1,'conservative',          1,'cash',        'BIL', 0.10, 0.30),

    (2,'moderate_conservative', 2,'us_equity',   'SPY', 0.20, 0.45),
    (2,'moderate_conservative', 2,'intl_equity', 'VXUS',0.05, 0.15),
    (2,'moderate_conservative', 2,'fixed_income','AGG', 0.30, 0.55),
    (2,'moderate_conservative', 2,'alternatives','GLD', 0.00, 0.10),
    (2,'moderate_conservative', 2,'cash',        'BIL', 0.05, 0.20),

    (3,'moderate',              3,'us_equity',   'SPY', 0.30, 0.55),
    (3,'moderate',              3,'intl_equity', 'VXUS',0.05, 0.20),
    (3,'moderate',              3,'fixed_income','AGG', 0.20, 0.45),
    (3,'moderate',              3,'alternatives','GLD', 0.00, 0.15),
    (3,'moderate',              3,'cash',        'BIL', 0.00, 0.15),

    (4,'moderate_aggressive',   4,'us_equity',   'SPY', 0.40, 0.70),
    (4,'moderate_aggressive',   4,'intl_equity', 'VXUS',0.10, 0.25),
    (4,'moderate_aggressive',   4,'fixed_income','AGG', 0.10, 0.30),
    (4,'moderate_aggressive',   4,'alternatives','GLD', 0.00, 0.15),
    (4,'moderate_aggressive',   4,'cash',        'BIL', 0.00, 0.10),

    (5,'aggressive',            5,'us_equity',   'SPY', 0.50, 0.85),
    (5,'aggressive',            5,'intl_equity', 'VXUS',0.10, 0.30),
    (5,'aggressive',            5,'fixed_income','AGG', 0.00, 0.20),
    (5,'aggressive',            5,'alternatives','GLD', 0.00, 0.20),
    (5,'aggressive',            5,'cash',        'BIL', 0.00, 0.05)
) AS t (tier_key, tier_name, risk_level, asset_class, ticker, min_weight, max_weight)