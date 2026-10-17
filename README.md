# NexusMart Data Analytics - Cleaning Milestone

## Project overview

This repository prepares the CodeConnect'26 NexusMart retail exports for reliable analytics. The datasets cover customers, products, sellers, locations, orders, order items, payments, shipping, and returns. Monetary values are in PKR. The immediate goal is a documented, quality-checked flat dataset ready for SQL Server landing and staging.

The challenge requires core cleaning in Python rather than Power Query. The star schema, Airflow orchestration, and Power BI dashboard are future milestones and are not implemented here.

## Repository map

```text
notebooks/
  01_data_profiling_cleaning.ipynb   Executed raw profiling and investigation evidence
  02_data_cleaning_validation.ipynb  Read-only final milestone summary
src/
  profile_raw_data.py                Raw CSV profiler; writes reports/raw_profile.json
  finalize_cleaning.py               Finalizes already prepared processed files in place
data/
  *.csv                              Supplied raw exports (never modified by cleaning)
  processed/*.csv                   Retained, cleaned rows for staging
  rejected/*.csv                     Quarantined records and row-level review flags
reports/                              Baselines, mappings, decisions, and quality audits
```

## Cleaning workflow and evidence

The original profiling notebook and profiler inspect the raw exports. Exact duplicate counts are recorded before later removal from the processed path. The remaining history is represented by the processed/rejected outputs and audit reports: missing-value decisions, date review and quarantine, category/status normalization, numeric conversion and anomaly review, sentinel quarantine, invalid order-item quarantine, and reference-integrity checks. The finalization script then applies the documented remaining alias/type rules and writes consolidated validation reports.

**Reproducibility limitation:** the current repository does not contain all of the historical transformation cells or scripts that produced the earlier date, sentinel, and invalid-item quarantine files. The existing `data/processed/` and `data/rejected/` files are the continuation state. Neither the read-only milestone notebook nor `src/finalize_cleaning.py` rebuilds the full processed dataset from raw CSVs. Do not treat the finalizer as a raw-to-clean pipeline.

Key decisions include:

- Exact duplicate copies were removed from the processed path while raw CSVs were preserved. `orders.csv` had 3,200 removed copies and `payments.csv` had 3,296.
- Approved missing descriptive categories are labeled `Unknown`; blank discount codes are normalized to the documented no-discount value. Optional or unsupported missing values remain null. No customer or product records were merged based on names alone.
- Invalid audited dates, suspected sentinel records, and invalid order items were quarantined with reason codes. Registration dates that are invalid or ambiguous remain flagged rather than guessed.
- Clear category spelling and abbreviation variants are covered by `reports/category_value_mapping.csv`. Broader or potentially meaningful category distinctions remain separate.
- Negative numeric values still in processed data are flagged. Statistical IQR outliers are summarized and retained unless stronger business evidence establishes an error.
- Reference checks distinguish formatting-only city identifiers, missing references, references to quarantined parents, and true broken references.

## Verified milestone results

`reports/consolidated_quality_report.csv` reconciles every original row as retained, quarantined, or an explicitly removed exact duplicate.

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

The verified checks in `reports/cleaning_validation_report.csv` show 9/9 tables reconciled, zero remaining exact duplicates, zero duplicate primary-key occurrences, zero unparseable non-null numeric values, and 7,118 unique quarantined rows. The consolidated rejection rows are present locally at `data/rejected/all_reason_coded_rejections.csv`; generated dataset CSVs are intentionally excluded from Git.

The final reference report covers 10 relationships. It identifies 1,381 truly broken references and 7,937 references to quarantined parents, with 9,318 row-level exceptions in `reports/reference_exception_rows.csv`. Formatting-only city ID differences are counted separately. There are also 1,731 invalid or ambiguous customer registration-date values flagged for review and 988 negative values flagged in retained data.

These remaining items block foreign-key-constrained loading until dispositioned. The processed CSVs are ready for unconstrained SQL Server landing/staging with nullable fields and the exception reports preserved. Strict date typing also requires a decision for customer registration-date values.

## Data folders and reports

- `data/` contains the original challenge exports and `README_DATA.txt`; raw top-level CSV files are ignored by Git and must remain unchanged.
- `data/processed/` contains the retained cleaned rows. It is local staging input and is ignored by Git.
- `data/rejected/` contains reason-coded quarantines and review-only flags. These are not interchangeable: flags retain a corresponding row in processed data, while quarantine files contain records excluded from processed tables. This folder is also ignored by Git because row-level outputs can be large or sensitive.
- `reports/` contains compact baselines, mappings, decisions, reconciliation counts, and audits. Larger row-level candidate/review files are kept out of the proposed commit; they remain available locally.

## Safe execution notes

Prerequisites: Python 3 and pandas for the scripts; pandas and Jupyter for the notebooks. Run commands from the repository root.

```powershell
python src/profile_raw_data.py
```

This scans only the raw top-level CSVs and writes `reports/raw_profile.json`; it does not modify raw data. The original profiling notebook also reads raw CSVs and writes its baseline/key/date reports.

`src/finalize_cleaning.py` reads `data/processed/` and `data/rejected/`, then rewrites processed CSVs in place and refreshes final reports/flags. It does not rebuild from raw data. Only run it after confirming the prepared processed/rejected inputs are the intended checkpoint and keeping a recoverable copy. Do not rerun it merely to review documentation. The new `02_data_cleaning_validation.ipynb` reads existing reports only.

## Next milestone

Resolve or explicitly route the reference exceptions and date flags, then define SQL Server staging tables and load rules. Warehouse/star-schema development follows staging. Airflow orchestration and Power BI reporting come after the warehouse is established.
