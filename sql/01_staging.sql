-- 01_staging.sql
-- Land the Lending Club loan file as an all-STRING staging table (only the 32 columns used downstream).
-- {{RAW_DIR}} is substituted by run_pipeline.py (data/raw = repo sample, data/raw_full = complete file).
-- Databricks equivalent (databricks/loan_default_pipeline_notebook.sql):
--   SELECT <same columns> FROM read_files('/Volumes/workspace/da_learn_04/raw/loan.csv', format => 'csv',
--          header => true, multiLine => true, escape => '"', inferColumnTypes => false)
CREATE OR REPLACE TABLE stg_loans AS
SELECT id, member_id, loan_amnt, funded_amnt, funded_amnt_inv, term, int_rate, installment, grade, sub_grade,
       emp_length, home_ownership, annual_inc, verification_status, issue_d, loan_status, purpose, addr_state, dti,
       delinq_2yrs, earliest_cr_line, inq_last_6mths, open_acc, pub_rec, revol_bal, revol_util, total_acc,
       total_pymnt, total_rec_prncp, total_rec_int, recoveries, pub_rec_bankruptcies
FROM read_csv('{{RAW_DIR}}/loan.csv', header = true, all_varchar = true);
