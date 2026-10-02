-- 05_quality_checks.sql  Data-quality evidence (Spark SQL dialect): before/after counts, null rates, issues, assertions

CREATE OR REPLACE TABLE dq_row_counts AS
SELECT 'loans' AS entity, (SELECT COUNT(*) FROM stg_loans) AS raw_rows,
       (SELECT COUNT(DISTINCT id) FROM stg_loans) AS distinct_keys,
       (SELECT COUNT(*) FROM cln_loans) AS clean_rows, 'loan (id)' AS grain
UNION ALL SELECT 'fact_loan', NULL, NULL, (SELECT COUNT(*) FROM fact_loan), 'loan'
UNION ALL SELECT 'dim_date', NULL, NULL, (SELECT COUNT(*) FROM dim_date), 'issue month'
UNION ALL SELECT 'dim_grade', NULL, NULL, (SELECT COUNT(*) FROM dim_grade), 'sub-grade'
UNION ALL SELECT 'dim_purpose', NULL, NULL, (SELECT COUNT(*) FROM dim_purpose), 'purpose'
UNION ALL SELECT 'dim_geography', NULL, NULL, (SELECT COUNT(*) FROM dim_geography), 'state'
UNION ALL SELECT 'dim_borrower', NULL, NULL, (SELECT COUNT(*) FROM dim_borrower), 'home x verification x emp band x income band';

CREATE OR REPLACE TABLE dq_null_rates AS
SELECT 'loans' AS entity, 'emp_length' AS column_name,
  (SELECT ROUND(100.0 * SUM(CASE WHEN emp_length IS NULL OR trim(emp_length) IN ('', 'n/a') THEN 1 ELSE 0 END) / COUNT(*), 3) FROM stg_loans) AS raw_null_pct,
  (SELECT ROUND(100.0 * SUM(CASE WHEN emp_length_years IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) FROM cln_loans) AS clean_null_pct,
  '''n/a'' -> NULL, reported as band ''Unknown''' AS treatment
UNION ALL SELECT 'loans', 'revol_util',
  (SELECT ROUND(100.0 * SUM(CASE WHEN revol_util IS NULL OR trim(revol_util) = '' THEN 1 ELSE 0 END) / COUNT(*), 3) FROM stg_loans),
  (SELECT ROUND(100.0 * SUM(CASE WHEN revolving_util_pct IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) FROM cln_loans),
  'kept as NULL (not used in rates)'
UNION ALL SELECT 'loans', 'pub_rec_bankruptcies',
  (SELECT ROUND(100.0 * SUM(CASE WHEN TRY_CAST(pub_rec_bankruptcies AS INT) IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) FROM stg_loans),
  (SELECT ROUND(100.0 * SUM(CASE WHEN bankruptcies IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) FROM cln_loans),
  'kept as NULL'
UNION ALL SELECT 'loans', 'int_rate',
  (SELECT ROUND(100.0 * SUM(CASE WHEN TRY_CAST(replace(int_rate, '%', '') AS DOUBLE) IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) FROM stg_loans),
  (SELECT ROUND(100.0 * SUM(CASE WHEN int_rate_pct IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) FROM cln_loans),
  'required; ''%'' stripped and cast to DOUBLE';

CREATE OR REPLACE TABLE dq_issues AS
SELECT 'loans: duplicate or unusable rows removed' AS check_name,
       (SELECT COUNT(*) FROM stg_loans) - (SELECT COUNT(*) FROM cln_loans) AS affected_rows
UNION ALL SELECT 'loans: emp_length ''n/a'' (-> Unknown)', (SELECT SUM(dq_missing_emp_length) FROM cln_loans)
UNION ALL SELECT 'loans: revol_util missing', (SELECT SUM(dq_missing_revol_util) FROM cln_loans)
UNION ALL SELECT 'loans: home_ownership NONE/OTHER (-> OTHER)', (SELECT COUNT(*) FROM stg_loans WHERE trim(home_ownership) IN ('NONE', 'OTHER'))
UNION ALL SELECT 'loans: annual income outlier > Q3 + 3*IQR (kept, flagged)', (SELECT SUM(is_income_outlier_iqr3) FROM cln_loans)
UNION ALL SELECT 'loans: funded by investors < funded amount', (SELECT COUNT(*) FROM cln_loans WHERE funded_amount_investors < funded_amount - 0.01)
UNION ALL SELECT 'loans: still Current (excluded from default rates)', (SELECT SUM(1 - is_completed) FROM cln_loans)
UNION ALL SELECT 'loans: charged off with recoveries > 0', (SELECT COUNT(*) FROM cln_loans WHERE is_default = 1 AND recoveries > 0)
UNION ALL SELECT 'RI: fact without grade', (SELECT COUNT(*) FROM fact_loan WHERE grade_key IS NULL)
UNION ALL SELECT 'RI: fact without purpose', (SELECT COUNT(*) FROM fact_loan WHERE purpose_key IS NULL)
UNION ALL SELECT 'RI: fact without geography', (SELECT COUNT(*) FROM fact_loan WHERE geo_key IS NULL)
UNION ALL SELECT 'RI: fact without borrower profile', (SELECT COUNT(*) FROM fact_loan WHERE borrower_key IS NULL);

CREATE OR REPLACE TABLE dq_assertions AS
WITH c AS (
  SELECT 'fact_loan.loan_id unique' AS check_name, (SELECT COUNT(*) - COUNT(DISTINCT loan_id) FROM fact_loan) AS failed_rows
  UNION ALL SELECT 'fact_loan.grade_key -> dim_grade', (SELECT COUNT(*) FROM fact_loan WHERE grade_key IS NULL OR grade_key NOT IN (SELECT grade_key FROM dim_grade))
  UNION ALL SELECT 'fact_loan.purpose_key -> dim_purpose', (SELECT COUNT(*) FROM fact_loan WHERE purpose_key IS NULL OR purpose_key NOT IN (SELECT purpose_key FROM dim_purpose))
  UNION ALL SELECT 'fact_loan.geo_key -> dim_geography', (SELECT COUNT(*) FROM fact_loan WHERE geo_key IS NULL OR geo_key NOT IN (SELECT geo_key FROM dim_geography))
  UNION ALL SELECT 'fact_loan.borrower_key -> dim_borrower', (SELECT COUNT(*) FROM fact_loan WHERE borrower_key IS NULL OR borrower_key NOT IN (SELECT borrower_key FROM dim_borrower))
  UNION ALL SELECT 'fact_loan.issue_month_key -> dim_date', (SELECT COUNT(*) FROM fact_loan WHERE issue_month_key NOT IN (SELECT month_key FROM dim_date))
  UNION ALL SELECT 'every state mapped to a census region', (SELECT COUNT(*) FROM dim_geography WHERE census_region = 'Unknown')
  UNION ALL SELECT 'term is 36 or 60 months', (SELECT COUNT(*) FROM fact_loan WHERE term_months NOT IN (36, 60))
  UNION ALL SELECT 'interest rate between 5% and 25%', (SELECT COUNT(*) FROM fact_loan WHERE int_rate_pct < 5 OR int_rate_pct > 25)
  UNION ALL SELECT 'dti between 0 and 30', (SELECT COUNT(*) FROM fact_loan WHERE dti < 0 OR dti >= 30)
  UNION ALL SELECT 'funded amount <= requested amount', (SELECT COUNT(*) FROM fact_loan WHERE funded_amount > loan_amount)
  UNION ALL SELECT 'sub_grade starts with grade', (SELECT COUNT(*) FROM dim_grade WHERE substr(sub_grade, 1, 1) <> grade)
  UNION ALL SELECT 'earliest credit line before issue month', (SELECT COUNT(*) FROM cln_loans WHERE earliest_credit_line >= issue_month)
  UNION ALL SELECT 'principal loss only on charged-off loans', (SELECT COUNT(*) FROM fact_loan WHERE principal_loss > 0 AND is_default = 0)
  UNION ALL SELECT 'grade default rates rise A -> G', (SELECT COUNT(*) FROM a_default_by_grade a JOIN a_default_by_grade b
                                                         ON b.grade_rank = a.grade_rank + 1 WHERE b.default_rate_pct < a.default_rate_pct)
)
SELECT check_name, failed_rows, CASE WHEN failed_rows = 0 THEN 'PASS' ELSE 'FAIL' END AS status FROM c;
