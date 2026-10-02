# Power BI model

Star schema exported by `run_pipeline.py --source sample` into `powerbi/data/` (49-loan sample; for the full
model run `--source full` and use `data/clean_full/star/`).

| Table | Grain | Key | Notes |
|---|---|---|---|
| fact_loan | one row per loan | loan_id | amounts, rate, DTI, income, status flags (is_completed, is_default), principal_loss |
| dim_date | issue month | month_key (yyyymm) | month_start, year, quarter, month, year_month |
| dim_grade | sub-grade | grade_key | sub_grade, grade, grade_rank (A=1..G=7), sub_grade_step |
| dim_purpose | purpose | purpose_key | purpose, purpose_label |
| dim_geography | US state | geo_key | state, census_region |
| dim_borrower | junk dimension | borrower_key | home_ownership, verification_status, emp_length_band, income_band |

Relationships (all many-to-one, single direction, dimension -> fact):
`fact_loan[issue_month_key] -> dim_date[month_key]`, `fact_loan[grade_key] -> dim_grade[grade_key]`,
`fact_loan[purpose_key] -> dim_purpose[purpose_key]`, `fact_loan[geo_key] -> dim_geography[geo_key]`,
`fact_loan[borrower_key] -> dim_borrower[borrower_key]`.

Sort `dim_grade[grade]` by `grade_rank`; `income_band` and `dti_band` carry a numeric prefix (`1: <30k`) so they
sort correctly as text. Mark `dim_date` as a date table on `month_start`.
