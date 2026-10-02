"""SVG charts for da-learn-04 from the KPI tables written by run_pipeline.py (pure vector, see svgcharts.py)."""
import csv, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import svgcharts as sc


def load(tables, name):
    with open(pathlib.Path(tables) / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_all(tables, out):
    out = pathlib.Path(out)
    f = lambda r, k: float(r[k])
    kpi = load(tables, "a_kpi_headline")[0]
    grade = sorted(load(tables, "a_default_by_grade"), key=lambda r: r["grade"])
    purpose = sorted(load(tables, "a_default_by_purpose"), key=lambda r: -f(r, "default_rate_pct"))
    income = sorted(load(tables, "a_default_by_income"), key=lambda r: r["income_band"])
    dti = sorted(load(tables, "a_default_by_dti"), key=lambda r: r["dti_band"])
    vint = sorted(load(tables, "a_vintage"), key=lambda r: r["issue_year"])
    prof = [r for r in load(tables, "a_default_by_profile") if r["attribute"] in ("term", "verification_status", "public_record")]
    mat = load(tables, "a_grade_dti_matrix")

    charts = {
        "default_by_grade": sc.vbar("Default rate % / avg interest rate % by grade", [r["grade"] for r in grade],
                                    [f(r, "default_rate_pct") for r in grade],
                                    notes=[f"{f(r, 'default_rate_pct'):.1f} / {f(r, 'avg_int_rate_pct'):.1f}" for r in grade], ylabel="default %"),
        "default_by_purpose": sc.hbar("Default rate % by loan purpose", [r["purpose_label"] for r in purpose],
                                      [f(r, "default_rate_pct") for r in purpose],
                                      notes=[f"{f(r, 'default_rate_pct'):.1f}%  n={int(r['loans']):,}" for r in purpose], label_w=120),
        "default_by_income": sc.vbar("Default rate % by annual income band", [r["income_band"][3:] for r in income],
                                     [f(r, "default_rate_pct") for r in income],
                                     notes=[f"{f(r, 'default_rate_pct'):.1f}%" for r in income], ylabel="default %"),
        "default_by_dti": sc.vbar("Default rate % by debt-to-income (DTI) band", [r["dti_band"][3:] for r in dti],
                                  [f(r, "default_rate_pct") for r in dti],
                                  notes=[f"{f(r, 'default_rate_pct'):.1f}%" for r in dti], ylabel="default %"),
    }
    # grade x DTI: collapse the 6 DTI bands into low (<10), mid (10-20), high (20+) using loan-weighted rates
    groups = {"DTI <10": ("1", "2"), "DTI 10-20": ("3", "4"), "DTI 20+": ("5", "6")}
    series = []
    for name, bands in groups.items():
        vals = []
        for g in [r["grade"] for r in grade]:
            rows = [r for r in mat if r["grade"] == g and r["dti_band"][0] in bands]
            n = sum(f(r, "loans") for r in rows)
            vals.append(round(sum(f(r, "loans") * f(r, "default_rate_pct") for r in rows) / n, 2) if n else 0)
        series.append(vals)
    charts["grade_x_dti"] = sc.vbar("Default rate % by grade and DTI", [r["grade"] for r in grade], series,
                                    names=list(groups), ylabel="default %")
    charts["vintage"] = sc.vbar("Loans issued per year (label: default rate)", [r["issue_year"] for r in vint],
                                [f(r, "loans") for r in vint],
                                notes=[f"{int(r['loans']):,} | {f(r, 'default_rate_pct'):.1f}%" for r in vint], ylabel="loans")
    charts["borrower_profile"] = sc.hbar("Default rate % by term / verification / public record",
                                         [f"{r['attribute'].replace('_', ' ')}: {r['value']}" for r in prof],
                                         [f(r, "default_rate_pct") for r in prof],
                                         notes=[f"{f(r, 'default_rate_pct'):.1f}%  n={int(r['loans']):,}" for r in prof], label_w=170)
    for name, panel in charts.items():
        sc.save(panel, out / f"{name}.svg")
    kpis = [(f"{int(float(kpi['loans'])):,}", "Loans"), (f"${float(kpi['funded_total']) / 1e6:,.0f}M", "Funded"),
            (f"{float(kpi['default_rate_pct']):.2f}%", "Default rate"), (f"{float(kpi['avg_int_rate_pct']):.2f}%", "Avg interest"),
            (f"${float(kpi['principal_lost']) / 1e6:,.1f}M", "Principal lost"), (f"{float(kpi['net_return_pct']):.2f}%", "Net return")]
    order = ["default_by_grade", "default_by_purpose", "default_by_income", "default_by_dti", "grade_x_dti", "vintage"]
    sc.dashboard(out / "dashboard.svg", "Lending Club 2007-2011: who defaults? (full data, completed loans)", kpis,
                 [charts[k] for k in order])
    print("charts ->", out, sorted(p.name for p in out.glob("*.svg")))


if __name__ == "__main__":
    make_all(sys.argv[1] if len(sys.argv) > 1 else "results/tables", sys.argv[2] if len(sys.argv) > 2 else "results/charts")
