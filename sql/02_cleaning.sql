-- 02_cleaning.sql  Typed, standardised, de-duplicated loans (Spark SQL dialect; DuckDB via 00 shims)
-- Steps: trim + TRY_CAST every field, strip '%' / ' months', map emp_length to years, parse 'Mon-YY' dates,
-- standardise categoricals, dedupe on loan id, derive the default flag and risk bands, flag income outliers.

CREATE OR REPLACE TABLE cln_loans_typed AS
SELECT
  TRY_CAST(trim(id) AS BIGINT)                                        AS loan_id,
  TRY_CAST(trim(member_id) AS BIGINT)                                 AS member_id,
  TRY_CAST(trim(loan_amnt) AS DOUBLE)                                 AS loan_amount,
  TRY_CAST(trim(funded_amnt) AS DOUBLE)                               AS funded_amount,
  TRY_CAST(trim(funded_amnt_inv) AS DOUBLE)                           AS funded_amount_investors,
  TRY_CAST(trim(replace(term, 'months', '')) AS INT)                  AS term_months,
  TRY_CAST(trim(replace(int_rate, '%', '')) AS DOUBLE)                AS int_rate_pct,
  TRY_CAST(trim(installment) AS DOUBLE)                               AS installment,
  upper(trim(grade))                                                  AS grade,
  upper(trim(sub_grade))                                              AS sub_grade,
  CASE WHEN trim(emp_length) = '< 1 year' THEN 0
       WHEN trim(emp_length) = '10+ years' THEN 10
       ELSE TRY_CAST(trim(replace(replace(emp_length, 'years', ''), 'year', '')) AS INT) END AS emp_length_years,
  CASE WHEN upper(trim(home_ownership)) IN ('RENT', 'MORTGAGE', 'OWN') THEN upper(trim(home_ownership))
       ELSE 'OTHER' END                                               AS home_ownership,
  TRY_CAST(trim(annual_inc) AS DOUBLE)                                AS annual_income,
  CASE WHEN trim(verification_status) = 'Not Verified' THEN 'Not verified'
       WHEN trim(verification_status) = 'Source Verified' THEN 'Source verified'
       ELSE 'Verified' END                                            AS verification_status,
  -- 'Dec-11' -> 2011-12-01. Parsed by hand (month lookup + 2-digit year) so Spark and DuckDB agree.
  make_date(2000 + TRY_CAST(substr(trim(issue_d), 5, 2) AS INT),
            CAST((instr('JanFebMarAprMayJunJulAugSepOctNovDec', substr(trim(issue_d), 1, 3)) + 2) / 3 AS INT), 1) AS issue_month,
  trim(loan_status)                                                   AS loan_status,
  lower(trim(purpose))                                                AS purpose,
  upper(trim(addr_state))                                             AS state,
  TRY_CAST(trim(dti) AS DOUBLE)                                       AS dti,
  TRY_CAST(trim(delinq_2yrs) AS INT)                                  AS delinq_2yrs,
  -- earliest credit line 'Jan-85': 2-digit years > 11 are 19xx (the data stops in 2011)
  make_date(CASE WHEN TRY_CAST(substr(trim(earliest_cr_line), 5, 2) AS INT) > 11
                 THEN 1900 ELSE 2000 END + TRY_CAST(substr(trim(earliest_cr_line), 5, 2) AS INT),
            CAST((instr('JanFebMarAprMayJunJulAugSepOctNovDec', substr(trim(earliest_cr_line), 1, 3)) + 2) / 3 AS INT), 1) AS earliest_credit_line,
  TRY_CAST(trim(inq_last_6mths) AS INT)                               AS inquiries_6m,
  TRY_CAST(trim(open_acc) AS INT)                                     AS open_accounts,
  TRY_CAST(trim(pub_rec) AS INT)                                      AS public_records,
  TRY_CAST(trim(revol_bal) AS DOUBLE)                                 AS revolving_balance,
  TRY_CAST(trim(replace(revol_util, '%', '')) AS DOUBLE)              AS revolving_util_pct,
  TRY_CAST(trim(total_acc) AS INT)                                    AS total_accounts,
  ROUND(TRY_CAST(trim(total_pymnt) AS DOUBLE), 2)                     AS total_payment,
  ROUND(TRY_CAST(trim(total_rec_prncp) AS DOUBLE), 2)                 AS principal_received,
  ROUND(TRY_CAST(trim(total_rec_int) AS DOUBLE), 2)                   AS interest_received,
  ROUND(TRY_CAST(trim(recoveries) AS DOUBLE), 2)                      AS recoveries,
  TRY_CAST(trim(pub_rec_bankruptcies) AS INT)                         AS bankruptcies
FROM stg_loans;

-- Dedupe on loan_id (keep one row per id) and drop rows without the fields every metric needs
CREATE OR REPLACE TABLE cln_loans_dedup AS
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY issue_month DESC, funded_amount DESC) AS rn
  FROM cln_loans_typed
  WHERE loan_id IS NOT NULL AND funded_amount > 0 AND grade IS NOT NULL AND issue_month IS NOT NULL
    AND loan_status IN ('Fully Paid', 'Charged Off', 'Current')
) x WHERE rn = 1;

CREATE OR REPLACE TABLE cln_income_bounds AS
SELECT percentile(annual_income, 0.25) AS q1, percentile(annual_income, 0.75) AS q3
FROM cln_loans_dedup;

CREATE OR REPLACE TABLE cln_loans AS
SELECT
  d.loan_id, d.member_id, d.loan_amount, d.funded_amount, d.funded_amount_investors, d.term_months, d.int_rate_pct,
  d.installment, d.grade, d.sub_grade,
  CAST(substr(d.sub_grade, 2, 1) AS INT)                              AS sub_grade_step,
  d.emp_length_years,
  CASE WHEN d.emp_length_years IS NULL THEN 'Unknown'
       WHEN d.emp_length_years < 2 THEN '0-1 yrs'
       WHEN d.emp_length_years < 5 THEN '2-4 yrs'
       WHEN d.emp_length_years < 10 THEN '5-9 yrs'
       ELSE '10+ yrs' END                                             AS emp_length_band,
  d.home_ownership, d.annual_income,
  CASE WHEN d.annual_income < 30000 THEN '1: <30k'
       WHEN d.annual_income < 50000 THEN '2: 30-50k'
       WHEN d.annual_income < 75000 THEN '3: 50-75k'
       WHEN d.annual_income < 100000 THEN '4: 75-100k'
       WHEN d.annual_income < 150000 THEN '5: 100-150k'
       ELSE '6: 150k+' END                                            AS income_band,
  d.verification_status, d.issue_month, YEAR(d.issue_month) AS issue_year, d.loan_status, d.purpose,
  concat(upper(substr(d.purpose, 1, 1)), substr(replace(d.purpose, '_', ' '), 2)) AS purpose_label,
  d.state, d.dti,
  CASE WHEN d.dti < 5 THEN '1: 0-5'
       WHEN d.dti < 10 THEN '2: 5-10'
       WHEN d.dti < 15 THEN '3: 10-15'
       WHEN d.dti < 20 THEN '4: 15-20'
       WHEN d.dti < 25 THEN '5: 20-25'
       ELSE '6: 25-30' END                                            AS dti_band,
  d.delinq_2yrs, d.earliest_credit_line,
  CAST(FLOOR(datediff(d.issue_month, d.earliest_credit_line) / 365.25) AS INT) AS credit_history_years,
  d.inquiries_6m, d.open_accounts, d.public_records, d.revolving_balance, d.revolving_util_pct, d.total_accounts,
  d.total_payment, d.principal_received, d.interest_received, d.recoveries, d.bankruptcies,
  CASE WHEN d.loan_status = 'Current' THEN 0 ELSE 1 END              AS is_completed,
  CASE WHEN d.loan_status = 'Charged Off' THEN 1 ELSE 0 END          AS is_default,
  -- principal written off on charged-off loans (funded - principal repaid - recoveries)
  CASE WHEN d.loan_status = 'Charged Off'
       THEN ROUND(GREATEST(d.funded_amount - d.principal_received - d.recoveries, 0), 2) ELSE 0 END AS principal_loss,
  ROUND(d.installment * 12 / NULLIF(d.annual_income, 0) * 100, 2)    AS installment_to_income_pct,
  CASE WHEN d.annual_income > b.q3 + 3 * (b.q3 - b.q1) THEN 1 ELSE 0 END AS is_income_outlier_iqr3,
  CASE WHEN d.emp_length_years IS NULL THEN 1 ELSE 0 END             AS dq_missing_emp_length,
  CASE WHEN d.revolving_util_pct IS NULL THEN 1 ELSE 0 END           AS dq_missing_revol_util
FROM cln_loans_dedup d CROSS JOIN cln_income_bounds b;
