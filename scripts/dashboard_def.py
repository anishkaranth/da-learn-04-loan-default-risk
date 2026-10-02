"""Lakeview dashboard + notebook visualization definitions for da-learn-04 (used by build_databricks.py)."""
from lakeview import ds, text, counter, chart, PCT, USD

VIZ = [
    ("Default rate by grade", "Bar: X = grade, Y = default_rate_pct (tooltip avg_int_rate_pct)",
     "SELECT grade, loans, default_rate_pct, avg_int_rate_pct, net_return_pct FROM a_default_by_grade ORDER BY grade_rank"),
    ("Default rate by purpose", "Horizontal bar: Y = purpose_label, X = default_rate_pct",
     "SELECT purpose_label, loans, default_rate_pct, principal_loss FROM a_default_by_purpose ORDER BY default_rate_pct DESC"),
    ("Default rate by income band", "Bar: X = income_band, Y = default_rate_pct",
     "SELECT income_band, loans, default_rate_pct, median_income FROM a_default_by_income ORDER BY income_band"),
    ("Default rate by DTI band", "Bar: X = dti_band, Y = default_rate_pct",
     "SELECT dti_band, loans, default_rate_pct, avg_dti FROM a_default_by_dti ORDER BY dti_band"),
    ("Grade x DTI", "Grouped bar: X = grade, Y = default_rate_pct, color = dti_band",
     "SELECT grade, dti_band, loans, default_rate_pct FROM a_grade_dti_matrix ORDER BY grade, dti_band"),
    ("Vintage", "Bar: X = issue_year, Y = loans (tooltip default_rate_pct)",
     "SELECT issue_year, loans, funded, default_rate_pct, pct_60_month FROM a_vintage ORDER BY issue_year"),
]


def dashboard(fq):
    q = lambda t: f"{fq}.{t}"
    datasets = [
        ds("kpi", "Headline KPIs", f"SELECT funded_total, default_rate_pct / 100 AS default_rate, loans, net_return_pct FROM {q('a_kpi_headline')}"),
        ds("grade", "By grade", f"SELECT grade, loans, default_rate_pct, avg_int_rate_pct FROM {q('a_default_by_grade')} ORDER BY grade_rank"),
        ds("purpose", "By purpose", f"SELECT purpose_label, loans, default_rate_pct FROM {q('a_default_by_purpose')}"),
        ds("income", "By income band", f"SELECT income_band, loans, default_rate_pct FROM {q('a_default_by_income')} ORDER BY income_band"),
        ds("dti", "By DTI band", f"SELECT dti_band, loans, default_rate_pct FROM {q('a_default_by_dti')} ORDER BY dti_band"),
        ds("grade_dti", "Grade x DTI", f"SELECT grade, dti_band, loans, default_rate_pct FROM {q('a_grade_dti_matrix')} ORDER BY grade, dti_band"),
        ds("vintage", "Vintage", f"SELECT CAST(issue_year AS STRING) AS issue_year, loans, default_rate_pct FROM {q('a_vintage')} ORDER BY issue_year"),
    ]
    p1 = [text("title", "## Lending Club 2007-2011 - default risk by grade and purpose (39,717 loans)", {"x": 0, "y": 0, "width": 6, "height": 1}),
          counter("kpi_default", "kpi", "default_rate", "Default rate (completed loans)", PCT, 0, w=2),
          counter("kpi_funded", "kpi", "funded_total", "Funded amount", USD, 2, w=2),
          text("note", "Default = Charged Off. Rates use completed loans only (Fully Paid + Charged Off); 1,140 Current loans excluded. Tables in workspace.da_learn_04.", {"x": 4, "y": 1, "width": 2, "height": 2}),
          chart("grade_bar", "bar", "grade", ("grade", "Grade"), ("default_rate_pct", "Default rate %"), "Default rate % by grade", {"x": 0, "y": 3, "width": 3, "height": 6}),
          chart("purpose_bar", "bar", "purpose", ("purpose_label", "Purpose"), ("default_rate_pct", "Default rate %"), "Default rate % by purpose", {"x": 3, "y": 3, "width": 3, "height": 6}, horizontal=True),
          chart("vintage_bar", "bar", "vintage", ("issue_year", "Issue year"), ("loans", "Loans"), "Loans issued per year", {"x": 0, "y": 9, "width": 6, "height": 5})]
    p2 = [text("title2", "## Affordability: income, debt-to-income and grade", {"x": 0, "y": 0, "width": 6, "height": 1}),
          chart("income_bar", "bar", "income", ("income_band", "Annual income band"), ("default_rate_pct", "Default rate %"), "Default rate % by income band", {"x": 0, "y": 1, "width": 3, "height": 6}),
          chart("dti_bar", "bar", "dti", ("dti_band", "DTI band"), ("default_rate_pct", "Default rate %"), "Default rate % by DTI band", {"x": 3, "y": 1, "width": 3, "height": 6}),
          chart("grade_dti_bar", "bar", "grade_dti", ("grade", "Grade"), ("default_rate_pct", "Default rate %"), "Default rate % by grade and DTI band", {"x": 0, "y": 7, "width": 6, "height": 6}, color=("dti_band", "DTI band"))]
    return {"datasets": datasets, "pages": [
        {"name": "overview", "displayName": "Overview", "pageType": "PAGE_TYPE_CANVAS", "layout": p1},
        {"name": "affordability", "displayName": "Affordability", "pageType": "PAGE_TYPE_CANVAS", "layout": p2}]}
