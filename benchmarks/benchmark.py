"""sqlsure utility benchmark — measured, not claimed.

Labeled corpus of (clean | buggy | repaired) queries against the healthcare
model. Produces:
  - detection recall per rule (buggy queries flagged with the right rule)
  - hard false-positive rate (errors raised on clean queries)
  - soft-flag rate (warnings raised on clean queries)
  - fix actionability (repaired-per-hint queries that then pass)
  - latency (median / p95 per check)

Run: python benchmarks/benchmark.py [--report docs/reports/benchmark.md]
"""
import argparse
import datetime
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure import SemanticModel, check  # noqa: E402

spec = json.load(open(Path(__file__).parent.parent / "model.example.json"))
# second one-to-many edge so the chasm trap is testable
spec["tables"]["dim_procedure"] = {"grain": ["procedure_id"]}
spec["joins"].append({
    "left": "fct_encounters", "right": "dim_procedure",
    "cardinality": "one_to_many", "keys": [["encounter_id", "encounter_id"]]})
MODEL = SemanticModel.from_dict(spec)

# (name, expected_rule_or_None, severity_expected, sql, repaired_sql_or_None)
CASES = [
    # ---------- buggy: one per rule ----------
    ("fanout: sum after 1:N join", "FANOUT", "error", """
        SELECT p.patient_id, SUM(f.cost) AS total
        FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id
        JOIN dim_patient p ON f.patient_id = p.patient_id
        GROUP BY 1""", """
        WITH costs AS (
            SELECT patient_id, SUM(cost) AS total
            FROM fct_encounters GROUP BY 1)
        SELECT p.patient_id, c.total
        FROM dim_patient p JOIN costs c ON p.patient_id = c.patient_id"""),
    ("fanout: count(*) after 1:N join", "FANOUT", "warning", """
        SELECT COUNT(*) FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id""", """
        SELECT COUNT(DISTINCT f.encounter_id) FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id"""),
    ("chasm: two 1:N joins", "CHASM", "error", """
        SELECT SUM(f.cost) FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id
        JOIN dim_procedure pr ON f.encounter_id = pr.encounter_id""", """
        WITH costs AS (SELECT encounter_id, SUM(cost) AS total
                       FROM fct_encounters GROUP BY 1)
        SELECT SUM(total) FROM costs"""),
    ("additivity: summing an average", "ADDITIVITY", "error",
     "SELECT SUM(avg_los) FROM fct_encounters",
     "SELECT AVG(avg_los) FROM fct_encounters"),
    ("semi-additive: census over time", "SEMI_ADDITIVE", "error", """
        SELECT unit_id, SUM(occupied_beds) FROM fct_patient_census
        GROUP BY 1""", """
        SELECT census_date, unit_id, SUM(occupied_beds)
        FROM fct_patient_census GROUP BY 1, 2"""),
    ("weighted avg after fanout", "WEIGHTED_AVG", "warning", """
        SELECT AVG(f.cost) FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id""",
     "SELECT AVG(cost) FROM fct_encounters"),
    ("wrong join key", "JOIN_KEY", "error", """
        SELECT f.cost FROM fct_encounters f
        JOIN dim_patient p ON f.encounter_id = p.patient_id""", """
        SELECT f.cost FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id"""),
    ("cross join", "CROSS_JOIN", "error",
     "SELECT f.cost FROM fct_encounters f CROSS JOIN dim_patient p", """
        SELECT f.cost FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id"""),
    ("PHI exposure", "SENSITIVE_COLUMN", "policy", """
        SELECT p.ssn, SUM(f.cost) FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id GROUP BY 1""", """
        SELECT p.patient_id, SUM(f.cost) FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id GROUP BY 1"""),
    ("undeclared join", "UNDECLARED_JOIN", "warning", """
        SELECT f.cost FROM fct_encounters f
        JOIN fct_patient_census c ON f.encounter_id = c.unit_id""", None),
    ("fanout buried in CTE", "FANOUT", "error", """
        WITH base AS (
            SELECT f.patient_id, SUM(f.cost) AS total
            FROM fct_encounters f
            JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id
            GROUP BY 1)
        SELECT p.patient_id, b.total
        FROM dim_patient p JOIN base b ON p.patient_id = b.patient_id""", """
        WITH base AS (
            SELECT patient_id, SUM(cost) AS total
            FROM fct_encounters GROUP BY 1)
        SELECT p.patient_id, b.total
        FROM dim_patient p JOIN base b ON p.patient_id = b.patient_id"""),

    # ---------- clean: must NOT raise errors ----------
    ("clean: sum at base grain", None, None,
     "SELECT patient_id, SUM(cost) FROM fct_encounters GROUP BY 1", None),
    ("clean: many-to-one join + sum", None, None, """
        SELECT p.patient_id, SUM(f.cost) FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id GROUP BY 1""", None),
    ("clean: avg of non-additive", None, None,
     "SELECT AVG(avg_los) FROM fct_encounters", None),
    ("clean: count distinct under fanout", None, None, """
        SELECT COUNT(DISTINCT f.encounter_id) FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id""", None),
    ("clean: semi-additive at snapshot grain", None, None, """
        SELECT census_date, SUM(occupied_beds)
        FROM fct_patient_census GROUP BY 1""", None),
    ("clean: pre-aggregate CTE then join (recommended pattern)", None, None, """
        WITH costs AS (
            SELECT patient_id, SUM(cost) AS total
            FROM fct_encounters GROUP BY 1)
        SELECT p.patient_id, c.total
        FROM dim_patient p JOIN costs c ON p.patient_id = c.patient_id""", None),
    ("clean: filter + group by ordinal", None, None, """
        SELECT patient_id, SUM(cost) FROM fct_encounters
        WHERE cost > 0 GROUP BY 1""", None),
    ("clean: diagnosis dim without aggregates", None, None, """
        SELECT f.encounter_id, d.diagnosis_id FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id""", None),
    ("clean: min/max under fanout are grain-safe here", None, None, """
        SELECT MAX(f.cost) FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id""", None),
    ("clean: non-sensitive patient columns", None, None,
     "SELECT patient_id FROM dim_patient", None),
]


def run():
    detected, missed, fp_hard, soft_flags = [], [], [], []
    fixes_ok, fixes_fail = [], []
    latencies = []

    for name, rule, _sev, sql, repaired in CASES:
        t0 = time.perf_counter()
        vs = check(sql, MODEL)
        latencies.append((time.perf_counter() - t0) * 1000)
        rules_found = {v.rule for v in vs}
        errors_found = {v.rule for v in vs if v.severity in ("error", "policy")}

        if rule is None:
            if errors_found:
                fp_hard.append((name, errors_found))
            elif rules_found:
                soft_flags.append((name, rules_found))
        else:
            (detected if rule in rules_found else missed).append((name, rules_found))
            if repaired:
                rvs = [v for v in check(repaired, MODEL)
                       if v.severity in ("error", "policy")]
                (fixes_fail if rvs else fixes_ok).append(name)

    # latency over more iterations for stable percentiles
    for _ in range(9):
        for _, _, _, sql, _ in CASES:
            t0 = time.perf_counter()
            check(sql, MODEL)
            latencies.append((time.perf_counter() - t0) * 1000)

    buggy = [c for c in CASES if c[1]]
    clean = [c for c in CASES if not c[1]]
    lat_sorted = sorted(latencies)
    return {
        "buggy": len(buggy), "clean": len(clean),
        "recall": len(detected) / len(buggy),
        "missed": missed, "fp_hard": fp_hard, "soft_flags": soft_flags,
        "fp_rate": len(fp_hard) / len(clean),
        "fixes_ok": fixes_ok, "fixes_fail": fixes_fail,
        "lat_median": statistics.median(latencies),
        "lat_p95": lat_sorted[int(len(lat_sorted) * 0.95)],
        "checks": len(latencies),
    }


def to_markdown(r: dict) -> str:
    fix_total = len(r["fixes_ok"]) + len(r["fixes_fail"])
    lines = [
        "# sqlsure utility benchmark",
        f"*{datetime.date.today()} · {r['buggy']} buggy + {r['clean']} clean "
        f"labeled queries · healthcare model*",
        "",
        "| metric | value |",
        "|---|---|",
        f"| Detection recall (buggy flagged with correct rule) | "
        f"**{r['recall']:.0%}** ({r['buggy'] - len(r['missed'])}/{r['buggy']}) |",
        f"| Hard false positives (errors on clean queries) | "
        f"**{r['fp_rate']:.0%}** ({len(r['fp_hard'])}/{r['clean']}) |",
        f"| Soft flags (warnings on clean queries) | "
        f"{len(r['soft_flags'])}/{r['clean']} |",
        f"| Fix-hint actionability (repaired query then passes) | "
        f"**{len(r['fixes_ok'])}/{fix_total}** |",
        f"| Latency median / p95 per check | "
        f"**{r['lat_median']:.1f} ms / {r['lat_p95']:.1f} ms** "
        f"(n={r['checks']}) |",
        "",
    ]
    if r["missed"]:
        lines += ["## Missed detections"] + [
            f"- {n} (found: {f or 'nothing'})" for n, f in r["missed"]]
    if r["fp_hard"]:
        lines += ["## Hard false positives"] + [
            f"- {n}: {f}" for n, f in r["fp_hard"]]
    if r["soft_flags"]:
        lines += ["## Soft flags on clean queries"] + [
            f"- {n}: {f}" for n, f in r["soft_flags"]]
    if r["fixes_fail"]:
        lines += ["## Repairs that did not pass"] + [
            f"- {n}" for n in r["fixes_fail"]]
    lines += [
        "",
        "Method: labeled corpus, one buggy case per rule plus a CTE-buried "
        "variant; clean set includes near-miss patterns (COUNT DISTINCT "
        "under fan-out, pre-aggregate-then-join, snapshot-grain sums). "
        "Repairs implement the violation's `fix` hint verbatim.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--report", default=None)
    args = p.parse_args()
    r = run()
    md = to_markdown(r)
    if args.report:
        Path(args.report).write_text(md)
    print(md)
