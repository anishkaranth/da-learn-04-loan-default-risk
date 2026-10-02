-- 04_analysis.sql  Business KPIs (Spark SQL dialect)
-- Default rate = charged-off loans / completed loans (Fully Paid + Charged Off). 'Current' loans (1,140) are
-- still running, so they are excluded from every rate; they are counted in volume KPIs only.
-- Net return = (total payments received - funded amount) / funded amount on completed loans.

CREATE OR REPLACE TABLE a_kpi_headline AS
SELECT
  COUNT(*)                                                                     AS loans,
  SUM(is_completed)                                                            AS completed_loans,
  SUM(1 - is_completed)                                                        AS current_loans,
  SUM(is_default)                                                              AS defaults,
  ROUND(100.0 * SUM(is_default) / SUM(is_completed), 2)                        AS default_rate_pct,
  ROUND(SUM(funded_amount), 0)                                                 AS funded_total,
  ROUND(AVG(funded_amount), 0)                                                 AS avg_funded_amount,
  ROUND(AVG(int_rate_pct), 2)                                                  AS avg_int_rate_pct,
  ROUND(median(annual_income), 0)                                              AS median_annual_income,
  ROUND(median(dti), 2)                                                        AS median_dti,
  ROUND(100.0 * SUM(CASE WHEN term_months = 60 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_60_month,
  ROUND(SUM(principal_loss), 0)                                                AS principal_lost,
  ROUND(100.0 * SUM(principal_loss) / SUM(CASE WHEN is_completed = 1 THEN funded_amount END), 2) AS loss_rate_pct,
  ROUND(100.0 * (SUM(CASE WHEN is_completed = 1 THEN total_payment END)
               - SUM(CASE WHEN is_completed = 1 THEN funded_amount END))
        / SUM(CASE WHEN is_completed = 1 THEN funded_amount END), 2)           AS net_return_pct,
  MIN(issue_month)                                                             AS first_issue_month,
  MAX(issue_month)                                                             AS last_issue_month
FROM cln_loans;

-- Q1: How does default risk scale with Lending Club's grade, and is the interest rate enough to pay for it?
CREATE OR REPLACE TABLE a_default_by_grade AS
SELECT grade, instr('ABCDEFG', grade) AS grade_rank,
       COUNT(*) AS loans, SUM(is_default) AS defaults,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2)                               AS default_rate_pct,
       ROUND(AVG(int_rate_pct), 2)                                                AS avg_int_rate_pct,
       ROUND(SUM(funded_amount), 0)                                               AS funded,
       ROUND(SUM(principal_loss), 0)                                              AS principal_loss,
       ROUND(100.0 * (SUM(total_payment) - SUM(funded_amount)) / SUM(funded_amount), 2) AS net_return_pct
FROM cln_loans WHERE is_completed = 1
GROUP BY grade;

CREATE OR REPLACE TABLE a_default_by_subgrade AS
SELECT sub_grade, grade, COUNT(*) AS loans,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
       ROUND(AVG(int_rate_pct), 2)                  AS avg_int_rate_pct
FROM cln_loans WHERE is_completed = 1
GROUP BY sub_grade, grade;

-- Q2: Which loan purposes default most?
CREATE OR REPLACE TABLE a_default_by_purpose AS
SELECT purpose, purpose_label, COUNT(*) AS loans, SUM(is_default) AS defaults,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2)                        AS default_rate_pct,
       ROUND(AVG(funded_amount), 0)                                         AS avg_funded_amount,
       ROUND(AVG(int_rate_pct), 2)                                          AS avg_int_rate_pct,
       ROUND(SUM(principal_loss), 0)                                        AS principal_loss
FROM cln_loans WHERE is_completed = 1
GROUP BY purpose, purpose_label;

-- Q3: Does income protect against default?
CREATE OR REPLACE TABLE a_default_by_income AS
SELECT income_band, COUNT(*) AS loans,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
       ROUND(median(annual_income), 0)              AS median_income,
       ROUND(AVG(funded_amount), 0)                 AS avg_funded_amount,
       ROUND(AVG(installment_to_income_pct), 2)     AS avg_installment_to_income_pct
FROM cln_loans WHERE is_completed = 1
GROUP BY income_band;

-- Q4: Does debt-to-income (DTI) predict default?
CREATE OR REPLACE TABLE a_default_by_dti AS
SELECT dti_band, COUNT(*) AS loans,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
       ROUND(AVG(dti), 2)                           AS avg_dti,
       ROUND(AVG(int_rate_pct), 2)                  AS avg_int_rate_pct
FROM cln_loans WHERE is_completed = 1
GROUP BY dti_band;

-- Q5: Is DTI still informative once grade is known? (grade x DTI band)
CREATE OR REPLACE TABLE a_grade_dti_matrix AS
SELECT grade, dti_band, COUNT(*) AS loans,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
FROM cln_loans WHERE is_completed = 1
GROUP BY grade, dti_band;

-- Q6: Term and other borrower attributes
CREATE OR REPLACE TABLE a_default_by_profile AS
SELECT 'term' AS attribute, CONCAT(CAST(term_months AS STRING), ' months') AS value, COUNT(*) AS loans,
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
FROM cln_loans WHERE is_completed = 1 GROUP BY term_months
UNION ALL
SELECT 'home_ownership', home_ownership, COUNT(*), ROUND(100.0 * SUM(is_default) / COUNT(*), 2)
FROM cln_loans WHERE is_completed = 1 GROUP BY home_ownership
UNION ALL
SELECT 'verification_status', verification_status, COUNT(*), ROUND(100.0 * SUM(is_default) / COUNT(*), 2)
FROM cln_loans WHERE is_completed = 1 GROUP BY verification_status
UNION ALL
SELECT 'emp_length', emp_length_band, COUNT(*), ROUND(100.0 * SUM(is_default) / COUNT(*), 2)
FROM cln_loans WHERE is_completed = 1 GROUP BY emp_length_band
UNION ALL
SELECT 'public_record', CASE WHEN public_records > 0 THEN 'has record' ELSE 'none' END, COUNT(*),
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2)
FROM cln_loans WHERE is_completed = 1 GROUP BY CASE WHEN public_records > 0 THEN 'has record' ELSE 'none' END
UNION ALL
SELECT 'inquiries_6m', CASE WHEN inquiries_6m >= 3 THEN '3+' ELSE CAST(inquiries_6m AS STRING) END, COUNT(*),
       ROUND(100.0 * SUM(is_default) / COUNT(*), 2)
FROM cln_loans WHERE is_completed = 1 GROUP BY CASE WHEN inquiries_6m >= 3 THEN '3+' ELSE CAST(inquiries_6m AS STRING) END;

-- Q7: Vintage view - volume growth and default rate by issue year
CREATE OR REPLACE TABLE a_vintage AS
SELECT issue_year, COUNT(*) AS loans, ROUND(SUM(funded_amount), 0) AS funded,
       SUM(is_completed) AS completed_loans,
       ROUND(100.0 * SUM(is_default) / SUM(is_completed), 2) AS default_rate_pct,
       ROUND(AVG(int_rate_pct), 2) AS avg_int_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN term_months = 60 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_60_month
FROM cln_loans GROUP BY issue_year;

CREATE OR REPLACE TABLE a_monthly_issuance AS
SELECT d.year_month, d.month_start, COUNT(*) AS loans, ROUND(SUM(f.funded_amount), 0) AS funded
FROM fact_loan f JOIN dim_date d ON f.issue_month_key = d.month_key
GROUP BY d.year_month, d.month_start;

-- Q8: Geography - states with at least 500 completed loans
CREATE OR REPLACE TABLE a_state_default AS
SELECT g.state, g.census_region, COUNT(*) AS loans,
       ROUND(100.0 * SUM(f.is_default) / COUNT(*), 2) AS default_rate_pct
FROM fact_loan f JOIN dim_geography g ON f.geo_key = g.geo_key
WHERE f.is_completed = 1
GROUP BY g.state, g.census_region
HAVING COUNT(*) >= 500;
