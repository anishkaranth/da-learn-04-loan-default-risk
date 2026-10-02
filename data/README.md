# Data

| Folder | In git? | Content |
|---|---|---|
| `data/raw/loan.csv` | yes | reproducible sample: 49 loans x 32 columns (6 Charged Off, 2 Current) |
| `data/raw_full/loan.csv` | no (.gitignore) | complete file, 39,717 loans x 111 columns, 34,813,575 bytes - `python scripts/download_full_data.py` |
| `data/clean_full/star/` | no | star-schema CSVs from the full run (`run_pipeline.py --source full`) |

**Sample rule** (`scripts/make_sample.py`): keep loans whose numeric `id` is divisible by 800, ordered by id,
and only the 32 columns read by `sql/01_staging.sql`. Free-text and URL columns (`emp_title`, `desc`, `title`, `url`)
and the ~70 columns that are entirely empty for the 2007-2011 vintage are dropped. Values are copied verbatim as
strings (e.g. `int_rate = '11.97%'`, `term = ' 36 months'`, `issue_d = 'Mar-08'`) so the cleaning SQL is exercised.

The sample is for smoke-testing and the Power BI kit only; every reported number uses the full file. With 49 loans
the assertion "grade default rates rise A -> G" is expected to FAIL on the sample (it passes on the full data).

Source: Kaggle `imsparsh/lending-club-loan-dataset-2007-2011` (LendingClub LoanStats3a), mirrored on GitHub -
see the *Complete dataset* section of the main README for URLs, checksum and licence notes.
