# AWS Robo Advisor and Stock Screening Analytics Platform

## Project Overview

This project implements an end-to-end cloud-based Robo Advisor and stock analytics platform using Amazon Web Services (AWS). The system integrates financial market data ingestion, cloud storage, SQL-based transformation, machine learning, portfolio optimization, historical backtesting, and interactive business intelligence dashboards.

The primary business problem is to translate an investor's risk profile into an appropriate portfolio allocation and provide transparent analytics that allow the investor to understand the portfolio's historical return, volatility, drawdown, and performance relative to a market benchmark.

A secondary stock-screening capability provides market-level insights including top and bottom S&P 500 stocks by year-to-date return and sector-level return and volatility analysis.

## Repository Structure

The project repository is organized to provide the implementation artifacts used to build the AWS-based Robo Advisor and Stock Screening Analytics Platform.

- **[Architecture and Data Model](./architecture/)** – Contains the AWS end-to-end solution architecture and analytical data model diagrams.

- **[Data Ingestion Scripts](./ingestion/)** – Contains the Python scripts used to ingest financial market data from Stooq, yfinance, and Ken French data sources and prepare data for the S3 data lake.

- **[SageMaker ML and Backtesting Notebook](./notebooks/)** – Contains the SageMaker notebook used for machine learning, portfolio optimization, risk-tier construction, and historical backtesting.

- **[Athena SQL Queries](./sql/)** – Contains the Athena SQL used for data transformation, analytical queries, and datasets supporting the Amazon QuickSight dashboards.


## Architecture

The solution uses the following AWS services:

* **Amazon S3** – Raw and curated financial data storage
* **AWS Glue** – Data ingestion and metadata/catalog management
* **Amazon Athena** – Serverless SQL transformation and analytical querying
* **Amazon SageMaker** – Machine learning, covariance estimation, portfolio optimization, and historical backtesting
* **Amazon QuickSight** – Interactive Robo Advisor and stock-screening dashboards

The overall processing flow is:

**Data Sources → AWS Glue → Amazon S3 → Athena/Glue Data Catalog → SageMaker → Athena → QuickSight**

## Data Sources

The project incorporates multiple financial data sources, including:

* Stooq historical market data
* Yahoo Finance market data
* Ken French factor data
* SPY as the primary S&P 500 benchmark

Market data is transformed into curated analytical datasets before being consumed by the portfolio optimization and visualization layers.

## Data Model

The Athena analytical model contains dimension, fact, and model-output tables.

### Dimension Tables

* `dim_date`
* `dim_security`
* `dim_risk_tier`
* `dim_user_profile`

### Market and Analytical Fact Tables

* `fact_prices`
* `fact_asset_class`
* `fact_benchmark`
* `fact_factor_returns`
* `fact_stock_screener`

### Portfolio and Model Output Tables

* `fact_tier_weights`
* `fact_backtest`
* `fact_metrics`

The model separates reusable dimensions from market observations and machine-learning/optimization outputs, allowing the same datasets to support portfolio analysis, backtesting, benchmarking, and dashboard reporting.

## Risk-Tier Framework

The Robo Advisor supports five investor risk profiles:

1. Conservative
2. Moderate-Conservative
3. Moderate
4. Moderate-Aggressive
5. Aggressive

Investor questionnaire responses are converted into a risk score and combined with safety constraints to determine the final risk tier. Portfolio optimization then generates an asset allocation appropriate for each tier.

## Machine Learning and Portfolio Optimization

Amazon SageMaker is used for the analytical and portfolio optimization layer.

The implementation incorporates:

* Historical return analysis
* Volatility modeling
* Ledoit-Wolf covariance shrinkage
* Mean-variance portfolio optimization
* Risk-tier allocation constraints
* Portfolio rebalancing
* Transaction-cost assumptions
* Historical backtesting

## Backtest Results

The historical backtest covers approximately **July 2011 through August 2026**, representing **3,777 trading days and 180 rebalancing periods**.

The five Robo Advisor portfolios generated a structured progression of risk and return.

| Risk Tier             | Annual Return | Annual Volatility | Sharpe Ratio | Maximum Drawdown |
| --------------------- | ------------: | ----------------: | -----------: | ---------------: |
| Conservative          |         3.14% |             3.46% |       0.9077 |          -12.96% |
| Moderate-Conservative |         4.46% |             5.05% |       0.8834 |          -15.55% |
| Moderate              |         5.87% |             6.58% |       0.8924 |          -17.13% |
| Moderate-Aggressive   |         7.61% |             8.95% |       0.8494 |          -18.99% |
| Aggressive            |         9.00% |            10.75% |       0.8372 |          -22.20% |
| SPY Benchmark         |        12.57% |            17.25% |       0.7291 |          -34.10% |

Within this historical test period, all five Robo Advisor portfolios produced higher Sharpe ratios and lower maximum drawdowns than the SPY benchmark. These results represent historical backtesting and should not be interpreted as guarantees of future investment performance.

## QuickSight Dashboards

### Robo Advisor Dashboard

The Robo Advisor dashboard allows users to select an investor risk tier and review:

* Recommended portfolio allocation
* Average daily return
* Ending equity
* Maximum drawdown
* Portfolio growth over time
* SPY benchmark comparison

### Stock Screening Dashboard

The market analytics portion of the project provides:

* Top 10 S&P 500 stocks by YTD return
* Bottom 10 S&P 500 stocks by YTD return
* Sector-level YTD return
* Sector-level annual volatility
* Return-versus-risk comparisons

## Running the Project

1. Configure an AWS environment with access to Amazon S3, AWS Glue, Athena, SageMaker, and QuickSight.
2. Run the ingestion scripts to retrieve the required financial datasets.
3. Store the raw datasets in the appropriate Amazon S3 locations.
4. Execute the Athena SQL scripts to create and populate the curated analytical tables.
5. Run the SageMaker notebook to perform portfolio optimization and historical backtesting.
6. Store the resulting portfolio weights and performance metrics in the analytical layer.
7. Connect the Athena datasets to Amazon QuickSight.
8. Create or refresh the Robo Advisor and stock-screening dashboards.

## Cost-Control Strategy

The architecture emphasizes managed and serverless AWS services. S3 provides low-cost storage, while Athena allows SQL queries without maintaining a dedicated database server. Parquet storage and partitioning reduce unnecessary Athena data scans. SageMaker resources are used for model development and analytical processing rather than maintaining an always-running inference endpoint.

## Limitations

The portfolio results are based on historical market data and do not guarantee future investment performance. Mean-variance optimization remains sensitive to return, volatility, and covariance estimates. Real-world implementation would also need to consider taxes, bid-ask spreads, market impact, liquidity, investor-specific restrictions, regulatory requirements, and additional model-governance controls.

## Future Improvements

Potential future enhancements include:

* Automated model monitoring and retraining
* Expanded asset and ETF coverage
* Additional benchmark comparisons
* Scenario and stress testing
* Enhanced transaction-cost modeling
* Portfolio rebalancing alerts
* ML-supported stock selection
* Additional QuickSight drill-down and interactive analytics

## Academic Purpose

This project was developed as an academic cloud analytics and machine-learning implementation. The Robo Advisor outputs are intended for educational and analytical purposes and should not be interpreted as personalized financial or investment advice.

