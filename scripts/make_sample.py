#!/usr/bin/env python3
"""Build the reproducible repo sample data/raw/loan.csv from data/raw_full/loan.csv (run download_full_data.py first).

Rule (deterministic): keep loans whose numeric id is divisible by 800 (49 of 39,717 loans), and only the 32 columns
that sql/01_staging.sql reads. Free-text / URL columns (emp_title, desc, title, url) and the 70+ columns that are
empty for this vintage are left out. Values are copied verbatim as strings; cleaning happens in sql/02_cleaning.sql.
"""
import pathlib, duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
FULL, OUT = (ROOT / "data/raw_full/loan.csv").as_posix(), ROOT / "data/raw"
COLS = ("id, member_id, loan_amnt, funded_amnt, funded_amnt_inv, term, int_rate, installment, grade, sub_grade, "
        "emp_length, home_ownership, annual_inc, verification_status, issue_d, loan_status, purpose, addr_state, dti, "
        "delinq_2yrs, earliest_cr_line, inq_last_6mths, open_acc, pub_rec, revol_bal, revol_util, total_acc, "
        "total_pymnt, total_rec_prncp, total_rec_int, recoveries, pub_rec_bankruptcies")
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
q = (f"SELECT {COLS} FROM read_csv('{FULL}', header = true, all_varchar = true) "
     "WHERE TRY_CAST(id AS BIGINT) % 800 = 0 ORDER BY TRY_CAST(id AS BIGINT)")
con.execute(f"COPY ({q}) TO '{(OUT / 'loan.csv').as_posix()}' (HEADER, DELIMITER ',')")
n = con.execute(f"SELECT COUNT(*) FROM read_csv('{(OUT / 'loan.csv').as_posix()}', header = true, all_varchar = true)").fetchone()[0]
print(f"loan.csv {n} rows")
