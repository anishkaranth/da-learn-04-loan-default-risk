# Power BI dashboard spec (mirrors the Lakeview dashboard)

Page 1 - Overview
- Cards: Loans, Funded, Default Rate, Avg Interest Rate, Principal Lost, Net Return
- Clustered column: dim_grade[grade] x [Default Rate] (tooltip Avg Interest Rate, Net Return)
- Bar: dim_purpose[purpose_label] x [Default Rate], sorted descending
- Column: dim_date[year] x [Loans], line on secondary axis [Default Rate]

Page 2 - Affordability
- Column: dim_borrower[income_band] x [Default Rate]
- Column: fact_loan[dti_band] x [Default Rate]
- Matrix: rows dim_grade[grade], columns fact_loan[dti_band], values [Default Rate] with a red-green colour scale
- Slicers: fact_loan[term_months], dim_borrower[verification_status], dim_geography[census_region]

Expected full-data values for checking: Default Rate 14.59%, Funded $434.8M, grade A 5.99% / G 33.78%,
small business 27.08%, 60-month 25.31%.
