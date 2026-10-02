#!/usr/bin/env python3
"""Run the SQL pipeline (sql/00..05) on DuckDB and export clean/star tables, KPI tables, metrics.json, JSON.shot and SVG charts.

Usage
  python run_pipeline.py --source sample   # repo subset (data/raw)       -> powerbi/data (sample star), results/sample/
  python run_pipeline.py --source full     # full data   (data/raw_full)  -> data/clean_full/, results/  (run scripts/download_full_data.py first)
Project-specific settings (files, star tables, snapshot queries) live in pipeline.json.
"""
import argparse, csv, json, pathlib, platform, time
import duckdb

ROOT = pathlib.Path(__file__).resolve().parent
CFG = json.loads((ROOT / "pipeline.json").read_text())
SQL_FILES = ["00_duckdb_compat.sql", "01_staging.sql", "02_cleaning.sql", "03_model.sql",
             "04_analysis.sql", "05_quality_checks.sql"]


def split_sql(text):
    """Split on ';' at end of line after removing -- comments (scripts contain no ';' inside strings)."""
    stmts, buf = [], []
    for line in text.splitlines():
        i = line.find("--")
        if i >= 0 and line[:i].count("'") % 2 == 0:
            line = line[:i]
        if not line.strip():
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            s = "\n".join(buf).strip().rstrip(";").strip()
            if s:
                stmts.append(s)
            buf = []
    return stmts


def jsonable(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if v.__class__.__name__ == "Decimal":
        return float(v)
    return v


def rows(con, q):
    cur = con.execute(q)
    cols = [d[0] for d in cur.description]
    return [{k: jsonable(v) for k, v in zip(cols, r)} for r in cur.fetchall()]


def export(con, query, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cur = con.execute(query)
    cols = [d[0] for d in cur.description]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in cur.fetchall():
            w.writerow(["" if v is None else jsonable(v) for v in r])


def run_sql(con, raw):
    timings = {}
    for f in SQL_FILES:
        t0 = time.time()
        text = (ROOT / "sql" / f).read_text().replace("{{RAW_DIR}}", raw.as_posix())
        for s in split_sql(text):
            con.execute(s)
        timings[f] = round(time.time() - t0, 3)
        print(f"ran {f:24s} {timings[f]:7.2f}s", flush=True)
    return timings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["sample", "full"], default="sample")
    ap.add_argument("--no-charts", action="store_true")
    a = ap.parse_args()
    raw = ROOT / ("data/raw" if a.source == "sample" else "data/raw_full")
    res = ROOT / ("results/sample" if a.source == "sample" else "results")
    for f in CFG["raw_files"]:
        if not (raw / f).exists():
            raise SystemExit(f"missing {raw}/{f}; run scripts/download_full_data.py (full) or scripts/make_sample.py (sample)")

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    timings = run_sql(con, raw)

    if a.source == "full":
        for t in CFG["star"]:
            export(con, f"SELECT * FROM {t} ORDER BY ALL", ROOT / "data/clean_full/star" / f"{t}.csv")
    # Power BI kit: star schema exported from the SAMPLE run (repo-sized); full star is in data/clean_full/star
    if a.source == "sample":
        for t in CFG["star"]:
            export(con, f"SELECT * FROM {t} ORDER BY ALL", ROOT / "powerbi/data" / f"{t}.csv")
    tables = [r["table_name"] for r in rows(con, "SELECT table_name FROM information_schema.tables "
              "WHERE table_name LIKE 'a\\_%' ESCAPE '\\' OR table_name LIKE 'dq\\_%' ESCAPE '\\' ORDER BY 1")]
    for t in tables:
        export(con, f"SELECT * FROM {t} ORDER BY ALL", res / "tables" / f"{t}.csv")

    kpi = rows(con, "SELECT * FROM a_kpi_headline")[0]
    dq = {
        "row_counts": rows(con, "SELECT * FROM dq_row_counts"),
        "null_rates": rows(con, "SELECT * FROM dq_null_rates"),
        "issues": {r["check_name"]: r["affected_rows"] for r in rows(con, "SELECT * FROM dq_issues")},
        "assertions": {r["check_name"]: r["status"] for r in rows(con, "SELECT * FROM dq_assertions")},
    }
    table_rows = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in CFG["core_tables"]}
    metrics = {"project": CFG["project"], "dataset": CFG["dataset"], "source_mode": a.source,
               "units": CFG.get("units", ""), "kpis": kpi, "table_rows": table_rows, "data_quality": dq,
               "engine": {"duckdb": duckdb.__version__, "python": platform.python_version()},
               "sql_timings_s": timings}
    res.mkdir(parents=True, exist_ok=True)
    (res / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")

    shot = {"snapshot": "headline KPIs + key breakdowns + run config", "project": CFG["project"],
            "source_mode": a.source, "config": dict(CFG["shot_config"], engine=f"duckdb {duckdb.__version__}"),
            "headline": {k: kpi[k] for k in CFG["shot_headline"]}}
    for name, q in CFG["shot_queries"].items():
        shot[name] = rows(con, q)
    shot["assertions_passed"] = sum(1 for v in dq["assertions"].values() if v == "PASS")
    shot["assertions_total"] = len(dq["assertions"])
    (res / "JSON.shot").write_text(json.dumps(shot, indent=2) + "\n")
    json.loads((res / "JSON.shot").read_text())
    print(json.dumps(shot["headline"], indent=2))
    print("assertions", shot["assertions_passed"], "/", shot["assertions_total"])

    if not a.no_charts:
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_charts", ROOT / "scripts" / "make_charts.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.make_all(res / "tables", res / "charts")


if __name__ == "__main__":
    main()
