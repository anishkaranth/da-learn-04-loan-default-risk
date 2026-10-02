# Build the Power BI report (Power BI Desktop, Windows)

1. *Get data > Text/CSV* and load the six files in `powerbi/data/` (or `data/clean_full/star/` after a full run).
   Check types: keys and counts = Whole number, amounts/rates = Decimal, `month_start` = Date.
2. *Model view*: create the five relationships listed in `model.md` (single direction, many-to-one).
3. Set *Sort by column*: `dim_grade[grade]` by `grade_rank`. Mark `dim_date` as date table (`month_start`).
4. Create a `_Measures` table and paste the measures from `measures.dax`; format Default Rate, Loss Rate,
   Net Return, Avg Interest Rate and Share 60 Month as percentages.
5. Build the two pages in `dashboard_spec.md`.
6. Validate with the full star: Default Rate must show 14.59% and Loans 39,717 (the 49-loan sample shows 12.77%).
