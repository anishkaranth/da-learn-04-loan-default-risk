-- 03_model.sql  Star schema: fact_loan + dim_date (issue month), dim_grade, dim_purpose, dim_geography, dim_borrower

CREATE OR REPLACE TABLE dim_date AS
SELECT
  YEAR(issue_month) * 100 + MONTH(issue_month) AS month_key,
  issue_month                                     AS month_start,
  YEAR(issue_month)                               AS year,
  QUARTER(issue_month)                            AS quarter,
  MONTH(issue_month)                              AS month,
  concat(CAST(YEAR(issue_month) AS STRING), '-', lpad(CAST(MONTH(issue_month) AS STRING), 2, '0')) AS year_month
FROM (SELECT DISTINCT issue_month FROM cln_loans) d;

CREATE OR REPLACE TABLE dim_grade AS
SELECT
  ROW_NUMBER() OVER (ORDER BY sub_grade)          AS grade_key,
  sub_grade, grade,
  instr('ABCDEFG', grade)                         AS grade_rank,
  sub_grade_step
FROM (SELECT DISTINCT sub_grade, grade, sub_grade_step FROM cln_loans) g;

CREATE OR REPLACE TABLE dim_purpose AS
SELECT ROW_NUMBER() OVER (ORDER BY purpose) AS purpose_key, purpose, purpose_label
FROM (SELECT DISTINCT purpose, purpose_label FROM cln_loans) p;

-- US state -> Census region (50 states + DC)
CREATE OR REPLACE TABLE dim_geography AS
SELECT ROW_NUMBER() OVER (ORDER BY state) AS geo_key, state,
  CASE WHEN state IN ('CT','ME','MA','NH','RI','VT','NJ','NY','PA') THEN 'Northeast'
       WHEN state IN ('IL','IN','MI','OH','WI','IA','KS','MN','MO','NE','ND','SD') THEN 'Midwest'
       WHEN state IN ('DE','DC','FL','GA','MD','NC','SC','VA','WV','AL','KY','MS','TN','AR','LA','OK','TX') THEN 'South'
       WHEN state IN ('AZ','CO','ID','MT','NV','NM','UT','WY','AK','CA','HI','OR','WA') THEN 'West'
       ELSE 'Unknown' END AS census_region
FROM (SELECT DISTINCT state FROM cln_loans) s;

-- Junk dimension: borrower profile attributes captured at application
CREATE OR REPLACE TABLE dim_borrower AS
SELECT ROW_NUMBER() OVER (ORDER BY home_ownership, verification_status, emp_length_band, income_band) AS borrower_key,
       home_ownership, verification_status, emp_length_band, income_band
FROM (SELECT DISTINCT home_ownership, verification_status, emp_length_band, income_band FROM cln_loans) b;

CREATE OR REPLACE TABLE fact_loan AS
SELECT
  l.loan_id,
  YEAR(l.issue_month) * 100 + MONTH(l.issue_month) AS issue_month_key,
  g.grade_key, p.purpose_key, geo.geo_key, b.borrower_key,
  l.term_months, l.loan_amount, l.funded_amount, l.int_rate_pct, l.installment,
  l.annual_income, l.dti, l.dti_band, l.revolving_util_pct, l.credit_history_years, l.inquiries_6m,
  l.delinq_2yrs, l.public_records, l.loan_status, l.is_completed, l.is_default,
  l.total_payment, l.principal_received, l.interest_received, l.recoveries, l.principal_loss,
  l.is_income_outlier_iqr3
FROM cln_loans l
LEFT JOIN dim_grade g ON l.sub_grade = g.sub_grade
LEFT JOIN dim_purpose p ON l.purpose = p.purpose
LEFT JOIN dim_geography geo ON l.state = geo.state
LEFT JOIN dim_borrower b ON l.home_ownership = b.home_ownership AND l.verification_status = b.verification_status
                         AND l.emp_length_band = b.emp_length_band AND l.income_band = b.income_band;
