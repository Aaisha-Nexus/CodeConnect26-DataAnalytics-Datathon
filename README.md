# NexusMart Data Analytics — CodeConnect’26

## Project overview

This repository is the official CodeConnect’26 NexusMart Datathon submission. It contains the Python data profiling and cleaning work, SQL Server staging and warehouse scripts, and the Airflow DAG used to validate the local warehouse. Dataset values are in PKR. The next major milestone is the Power BI dashboard; no completed dashboard is included here.

## Repository map

```text
notebooks/
  01_data_profiling_cleaning.ipynb   Raw profiling and cleaning investigation
  02_data_cleaning_validation.ipynb  Read-only final cleaning summary
src/
  profile_raw_data.py                Raw CSV profiler
  finalize_cleaning.py               Finalizes prepared processed outputs
  load_staging_data.py               Guarded batch loader for SQL Server staging
sql/                                 Database, staging, dimensions, fact, and checks
dags/
  nexusmart_datathon_pipeline.py     Airflow warehouse validation DAG
airflow/                             Astro runtime Dockerfile and Python dependency
data/
  *.csv                              Supplied raw exports (local; excluded from Git)
  processed/*.csv                    Retained rows (local; excluded from Git)
  rejected/*.csv                     Quarantines/review flags (local; excluded from Git)
reports/                              Compact cleaning reports and star-schema diagram
```

## Cleaning and data quality

Python-based profiling and cleaning covered the nine source tables: customers, locations, orders, order items, payments, products, returns, sellers, and shipping. Raw exports were preserved. Processed datasets retain accepted rows; reason-coded quarantine outputs hold excluded rows, with flags separated from full-row quarantines. The workflow includes row reconciliation, category/date/numeric audits, and reference-integrity checks.

The verified cleaning report records 9/9 tables reconciled; zero remaining exact duplicate rows and duplicate primary-key occurrences in processed data; zero unparseable non-null numeric values; and 7,118 unique quarantined rows. Reference checks found 1,381 truly broken references, 7,937 references to quarantined parent records, and 9,318 row-level reference exceptions. The review also flags 1,731 invalid or ambiguous customer registration dates and 988 negative values in retained data. See `reports/cleaning_validation_report.csv`, `reports/consolidated_quality_report.csv`, and `reports/final_reference_integrity_report.csv`.

The reconciliation report records each original row as retained, quarantined, or an explicitly removed exact duplicate:

| Table | Original rows | Retained | Quarantined | Exact copies removed |
|---|---:|---:|---:|---:|
| customers | 45,000 | 45,000 | 0 | 0 |
| locations | 650 | 650 | 0 | 0 |
| orders | 163,200 | 158,250 | 1,750 | 3,200 |
| order_items | 315,143 | 313,250 | 1,893 | 0 |
| payments | 168,111 | 163,586 | 1,229 | 3,296 |
| products | 3,200 | 3,200 | 0 | 0 |
| returns | 16,048 | 15,912 | 136 | 0 |
| sellers | 420 | 416 | 4 | 0 |
| shipping | 151,228 | 149,122 | 2,106 | 0 |

Exact duplicate copies were removed from the processed path while raw data remained unchanged (`orders.csv`: 3,200 copies; `payments.csv`: 3,296). Approved missing descriptive categories use `Unknown`; category and status variants are mapped only where supported. Invalid audited dates, suspected sentinel records, and invalid order items were quarantined with reasons. Negative values and statistical outliers that remain in the retained data are flagged for review rather than silently altered.

**Reproducibility limitation:** the repository does not contain all historical transformation steps that produced the existing date, sentinel, and invalid-item quarantine outputs. The processed/rejected files are continuation state. The read-only milestone notebook and `src/finalize_cleaning.py` do not rebuild the complete raw-to-clean pipeline from raw exports; do not treat the finalizer as that pipeline.

## SQL Server warehouse

The SQL scripts target the `NexusMartDW` database. Schema `stg` contains nine text-oriented staging tables corresponding to the source exports. Schema `dw` contains five dimensions—`DimDate`, `DimCustomer`, `DimProduct`, `DimSeller`, and `DimLocation`—and the `FactSales` fact table. The star-schema diagram is in [`reports/Star_Schema_Diagram.png`](reports/Star_Schema_Diagram.png).

`FactSales` is at order-item grain. The SQL scripts reference its order-item/order identifiers, five dimension keys (`DateKey`, `CustomerKey`, `ProductKey`, `SellerKey`, `LocationKey`), `Quantity`, `UnitPrice`, `DiscountAmount`, `MerchandiseSales`, gross/net/cost amounts, `AllocatedShippingFee`, refund/returned amounts, cancellation/return flags, order status, payment method, channel, shipping days, and return date/reason/status. The repository's fact scripts evolve an existing table rather than provide a complete base `CREATE TABLE`; `sql/07_audit_live_fact_schema.sql` queries the actual live columns and constraints. Population and later additions are in `sql/05_populate_fact_sales.sql`, `sql/08_add_fact_sales_measures.sql`, and `sql/09_complete_dim_date.sql`.

Available scripts include `sql/00_check_sql_server.sql`, `sql/01_create_staging_tables.sql`, `sql/02_validate_staging_data.sql`, `sql/03_create_dimensions.sql`, `sql/04_create_fact_sales.sql`, `sql/05_populate_fact_sales.sql`, `sql/06_quality_checks.sql`, and `sql/07_audit_live_fact_schema.sql` through `sql/11_add_unknown_date_and_relationships.sql`. Review each script and its assumptions before executing against an existing database; some create or alter warehouse objects.

Reconciliation is not yet complete. The staged order-items table contains 3,465 rows whose order IDs have no matching staged order; these relate to quarantined parent records and must remain visible in the quality report. The source shipping total also differs from the currently allocated fact shipping total (the current allocation takes the maximum staged shipping fee per order and divides it among that order’s item rows). See the missing-order and shipping reconciliation sections in `sql/06_quality_checks.sql`. These differences must not be presented as perfect source-to-fact coverage.

## Airflow validation

The DAG `nexusmart_datathon_pipeline` defines seven sequential tasks: `extract`, `validate_raw`, `clean`, `load_staging`, `build_dimensions`, `build_fact`, and `quality_checks`. A successful Airflow run was observed on October 18, 2026, with all seven tasks succeeding.

This run validates an already prepared state; it is not a complete end-to-end rebuild. `extract` checks for the nine processed CSVs, `validate_raw` checks their headers and non-empty rows, and `clean` verifies existing processed outputs rather than executing the full cleaning transformation. The remaining tasks verify that staging tables and dimensions already exist and contain data, that `FactSales` is populated and has unique order-item grain, and run warehouse quality checks. The DAG warns on the 3,465 staged order-item rows without a staged order and checks unresolved dimension keys. It does not load or rebuild the warehouse. Detailed per-file read/rejected/loaded accounting and full end-to-end idempotent loading remain improvements.

The DAG obtains SQL Server credentials from `NEXUSMART_SQL_SERVER`, `NEXUSMART_SQL_PORT`, `NEXUSMART_SQL_USER`, `NEXUSMART_SQL_PASSWORD`, and `NEXUSMART_SQL_DATABASE`. Set them in the local runtime environment; never commit `.env` or put credentials in this README. The ODBC staging loader and connection check also use `NEXUSMART_SQL_SERVER`, `NEXUSMART_SQL_DATABASE`, and optional `NEXUSMART_SQL_USER` / `NEXUSMART_SQL_PASSWORD` (otherwise they use trusted Windows authentication); `NEXUSMART_SQL_DRIVER` can select the installed ODBC driver.

### Local Astro/Docker runtime

The working Astro project remains separate at `C:\Users\LENOVO\local_airflow`. The main repository keeps its DAG in `dags/` and the reviewed runtime build files in `airflow/`; generated Docker volumes, container state, local Astro settings, processed data, and secrets are not included. To run locally, install the Astro CLI and Docker, place/copy the repository DAG into `C:\Users\LENOVO\local_airflow\dags\my_dag.py`, make the processed CSVs available at `C:\Users\LENOVO\local_airflow\include\processed\`, set the five environment variables above in that runtime, then run `astro dev start` from `C:\Users\LENOVO\local_airflow`. The DAG reads CSVs inside the container from `/usr/local/airflow/include/processed`.

## Data and report handling

Raw exports, processed/rejected row-level CSVs, temporary logs, Python caches, and large row-level review/audit dumps are local artifacts and are excluded from Git. Compact report summaries, decision logs, mappings, and the star-schema diagram are kept where useful. Do not rerun the finalizer merely to review documentation: it rewrites prepared processed files and refreshes reports.

The raw profiler can be run from the repository root with `python src/profile_raw_data.py`; it reads top-level raw CSVs and writes a profile report. The guarded SQL Server loader is `src/load_staging_data.py`; inspect its connection configuration and confirm all target staging tables are empty before running it. The SQL scripts should be applied deliberately, in dependency order, to the intended database.

## Current status and next milestone

Cleaning evidence is documented, a SQL Server staging/star-schema warehouse has been built, and the seven-task Airflow validation run succeeded. Known reference, missing-order, and shipping reconciliation issues remain under review. Airflow currently verifies existing processed and warehouse data; it does not recreate the full raw-to-warehouse pipeline. The next major milestone is the Power BI dashboard, followed by improving reproducibility, end-to-end idempotent loading, and source-to-fact reconciliation.
