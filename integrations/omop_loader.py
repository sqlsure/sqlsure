"""OMOP CDM rulebook — the standard clinical-research ontology, enforceable.

OMOP (OHDSI's Common Data Model) is the ontology-shaped schema hundreds of
hospitals and research networks standardize on. Its structure is public and
machine-readable: the field-level spec CSV declares every primary key and
foreign key. This loader turns that spec into a sqlsure rulebook, then adds
the clinical semantics the spec implies but SQL cannot see:

  - measures: costs/quantities are additive; clinical values
    (measurement.value_as_number) are NON-additive — summing lab results is
    always a bug
  - sensitive: *_source_value identifier columns and location address
    fields are flagged for the SENSITIVE_COLUMN policy rule

The classic bug this catches: cohort queries that count persons after
joining one-to-many clinical events (visits, drug exposures) — the
double-counted-patients mistake.

Usage:
    from omop_loader import load_omop
    model = load_omop("OMOP_CDMv5.4_Field_Level.csv")   # or bundled fetch
    violations = check(sql, model)

Spec source: github.com/OHDSI/CommonDataModel (inst/csv, v5.4).
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.model import (  # noqa: E402
    ADDITIVE, MANY_TO_ONE, NON_ADDITIVE,
    Join, Measure, SemanticModel, Table,
)

# clinical semantics the spec's PK/FK data can't express
_ADDITIVE = {
    ("cost", "total_charge"), ("cost", "total_cost"), ("cost", "total_paid"),
    ("cost", "paid_by_payer"), ("cost", "paid_by_patient"),
    ("cost", "paid_patient_copay"), ("cost", "paid_patient_coinsurance"),
    ("cost", "paid_patient_deductible"), ("cost", "paid_by_primary"),
    ("drug_exposure", "quantity"), ("drug_exposure", "days_supply"),
    ("drug_exposure", "refills"),
    ("procedure_occurrence", "quantity"),
}
_NON_ADDITIVE = {
    ("measurement", "value_as_number"),   # lab values — never summable
    ("observation", "value_as_number"),
    ("person", "year_of_birth"), ("person", "month_of_birth"),
    ("person", "day_of_birth"),
}
_SENSITIVE_SUFFIX = "_source_value"
_SENSITIVE_EXTRA = {
    ("location", "address_1"), ("location", "address_2"),
    ("location", "zip"), ("location", "latitude"), ("location", "longitude"),
    ("person", "birth_datetime"),
}


def load_omop(csv_path: str) -> SemanticModel:
    m = SemanticModel()
    rows = list(csv.DictReader(open(csv_path)))

    def yes(v: str | None) -> bool:
        return (v or "").strip().lower() in ("yes", "true")

    for r in rows:
        t = r["cdmTableName"].strip().lower()
        c = r["cdmFieldName"].strip().lower()
        tbl = m.tables.setdefault(t, Table(t))
        if yes(r.get("isPrimaryKey")):
            tbl.grain.append(c)
        if (t, c) in _ADDITIVE:
            tbl.measures[c] = Measure(c, ADDITIVE)
        elif (t, c) in _NON_ADDITIVE:
            tbl.measures[c] = Measure(c, NON_ADDITIVE)
        if c.endswith(_SENSITIVE_SUFFIX) or (t, c) in _SENSITIVE_EXTRA:
            tbl.sensitive.add(c)

    for r in rows:
        if not yes(r.get("isForeignKey")):
            continue
        child = r["cdmTableName"].strip().lower()
        col = r["cdmFieldName"].strip().lower()
        parent = (r.get("fkTableName") or "").strip().lower()
        pcol = (r.get("fkFieldName") or "").strip().lower()
        if not (parent and pcol):
            continue
        m.tables.setdefault(parent, Table(parent))
        e = m.joins.get((child, parent))
        if e:
            if (col, pcol) not in e.keys:
                e.keys.append((col, pcol))
        else:
            m.joins[(child, parent)] = Join(child, parent, MANY_TO_ONE,
                                            [(col, pcol)])
    return m


if __name__ == "__main__":
    from sqlsure.checker import check

    path = sys.argv[1] if len(sys.argv) > 1 else "omop_fields.csv"
    m = load_omop(path)
    edges = len(m.joins)
    sens = sum(len(t.sensitive) for t in m.tables.values())
    print(f"OMOP CDM rulebook: {len(m.tables)} tables, {edges} join edges, "
          f"{sens} sensitive columns — from the published spec, zero authoring")

    cases = [
        ("cohort size counted after joining visits (double-counted patients)",
         "SELECT COUNT(p.person_id) FROM person p "
         "JOIN visit_occurrence v ON p.person_id = v.person_id "
         "WHERE v.visit_start_date >= '2024-01-01'"),
        ("summing lab values",
         "SELECT SUM(m.value_as_number) FROM measurement m "
         "WHERE m.measurement_concept_id = 3004249"),
        ("exposing an identifier column",
         "SELECT p.person_source_value, COUNT(*) FROM person p GROUP BY 1"),
        ("clean: distinct persons across visits",
         "SELECT COUNT(DISTINCT p.person_id) FROM person p "
         "JOIN visit_occurrence v ON p.person_id = v.person_id"),
    ]
    for label, sql in cases:
        vs = check(sql, m)
        print(f"\n{label}:")
        for v in vs:
            print(f"  [{v.severity}] {v.rule}: {v.message[:110]}")
        if not vs:
            print("  approved")
