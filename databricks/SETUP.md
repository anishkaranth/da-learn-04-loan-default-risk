# Databricks run (done for real on 2026-10-02 IST)

| Item | Value |
|---|---|
| Warehouse | Serverless Starter Warehouse (shared; not stopped - auto-stop handles it) |
| Catalog.schema | `workspace.da_learn_04` |
| Raw data | full `loan.csv` (34.8 MB) uploaded to the UC volume `/Volumes/workspace/da_learn_04/raw/` via the Files API |
| Notebook | `/Workspace/Shared/da-learn-04-loan-default-risk/loan_default_pipeline_notebook` (export: `loan_default_pipeline_notebook.sql`) |
| Dashboard | **da-learn-04 Loan default risk** - published, 2 pages, 8 data widgets (export: `loan_default_dashboard.lvdash.json`) |
| Run log | `run_outputs/databricks_run.json` (38 statements, all OK) |
| Parity | `run_outputs/duckdb_vs_databricks.json`: all 8 core tables have identical row counts (stg/cln/fact 39,717; dim_date 55, dim_grade 35, dim_purpose 14, dim_geography 50, dim_borrower 316) and a_kpi_headline, a_default_by_grade/purpose/income/dti, dq_assertions, dq_issues match cell by cell |

## Reproduce
1. `CREATE SCHEMA IF NOT EXISTS workspace.da_learn_04; CREATE VOLUME IF NOT EXISTS workspace.da_learn_04.raw;`
2. Upload `data/raw_full/loan.csv` to `/Volumes/workspace/da_learn_04/raw/loan.csv` (Catalog Explorer > volume > Upload, or `databricks fs cp`).
3. Workspace > Import > `databricks/loan_default_pipeline_notebook.sql`, attach a SQL warehouse, *Run all*.
   Staging uses `read_files(..., format => 'csv', header => true, multiLine => true, escape => '"', inferColumnTypes => false)`
   because the source has multi-line quoted `desc` text; only 32 of 111 columns are selected.
4. Dashboards > Import > `loan_default_dashboard.lvdash.json` (datasets point to `workspace.da_learn_04.*`), then Publish.

## Dialect notes
- Dates such as `Dec-11` are parsed with `make_date` + a month lookup (`instr('JanFeb...', ...)`) so both engines agree
  (Spark `yy` would map `85` to 2085).
- `median()` / `percentile()` are exact in Spark; DuckDB uses the `00_duckdb_compat.sql` shim `percentile -> quantile_cont`.
- Avoid `''` inside string literals in labels: Spark concatenates adjacent literals (`'a''b'` -> `ab`).
