"""OSI (Open Semantic Interchange) loader — sqlsure as an OSI enforcer.

Reads an OSI semantic model (the vendor-neutral YAML standard from the
Snowflake / dbt / Salesforce / Databricks initiative, v1.0 2026) into a
sqlsure SemanticModel, making OSI-declared semantics *enforceable* on
arbitrary SQL:

  - concept `identify_by`                  -> grain
  - relationship `multiplicity` + `derived_by 'A.x == B.y'` -> join edge
  - metric expressions (`SUM(t.col)`, `AVG(t.col)`) -> measure additivity

Demo:  python integrations/osi_loader.py path/to/model.yaml
"""
from __future__ import annotations

import os
import re
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.model import (  # noqa: E402
    ADDITIVE, MANY_TO_ONE, NON_ADDITIVE, ONE_TO_MANY,
    Join, Measure, SemanticModel, Table,
)

_DERIVED = re.compile(
    r"(\w+)\.(\w+)\s*==\s*(\w+)\.(\w+)")
_AGG = re.compile(r"\b(SUM|AVG|COUNT|MIN|MAX|MEDIAN)\s*\(\s*(?:(\w+)\.)?(\w+)\s*\)", re.I)

_CARD = {"manytoone": MANY_TO_ONE, "onetomany": ONE_TO_MANY}
_SCALARS = {"string", "float", "integer", "boolean", "date", "datetime",
            "decimal", "number", "time", "timestamp"}


def load_osi(path: str) -> SemanticModel:
    doc = yaml.safe_load(open(path))
    m = SemanticModel()

    entity_names = set()
    for item in doc.get("ontology", []) or []:
        c = item.get("concept", {})
        if c.get("type") == "EntityType":
            entity_names.add(c["name"].lower())

    for item in doc.get("ontology", []) or []:
        c = item.get("concept", {})
        if c.get("type") != "EntityType":
            continue
        name = c["name"].lower()
        grain = [g.lower() for g in c.get("identify_by", [])]
        m.tables.setdefault(name, Table(name)).grain = grain

        for rel in item.get("relationships", []) or []:
            target = (rel.get("roles") or [{}])[0].get("concept", "")
            if target.lower() in _SCALARS or target.lower() not in entity_names:
                continue  # attribute, not an entity join
            card = _CARD.get((rel.get("multiplicity") or "").lower())
            keys = []
            for d in rel.get("derived_by", []) or []:
                g = _DERIVED.search(d)
                if g:
                    lt, lc, rt, rc = (x.lower() for x in g.groups())
                    # orient key pair as (this-entity col, target col)
                    keys.append((lc, rc) if lt == name else (rc, lc))
            if card and keys:
                edge = m.joins.get((name, target.lower()))
                if edge:
                    for k in keys:
                        if k not in edge.keys:
                            edge.keys.append(k)
                else:
                    m.joins[(name, target.lower())] = Join(
                        name, target.lower(), card, keys)

    # metrics: infer additivity from the aggregate in the expression
    for metric in doc.get("metrics", []) or []:
        for d in (metric.get("expression", {}) or {}).get("dialects", []) or []:
            g = _AGG.search(d.get("expression", "") or "")
            if not g:
                continue
            func, tbl, col = g.group(1).upper(), g.group(2), g.group(3)
            additivity = ADDITIVE if func in ("SUM", "COUNT") else NON_ADDITIVE
            owner = (tbl or "").lower()
            if owner and owner in m.tables:
                m.tables[owner].measures.setdefault(
                    col.lower(), Measure(col.lower(), additivity))
            break
    return m


if __name__ == "__main__":
    from sqlsure.checker import check

    path = sys.argv[1] if len(sys.argv) > 1 else "osi_flights.yaml"
    m = load_osi(path)
    print(f"OSI model loaded: {len(m.tables)} entities, {len(m.joins)} join edges")
    for (l, r), j in list(m.joins.items())[:5]:
        print(f"  {l} -> {r}: {j.cardinality} on {j.keys}")

    # demo: enforce OSI semantics on arbitrary SQL
    bad = """SELECT a.airportid, COUNT(*)
             FROM example_airport a
             JOIN example_runway r ON a.airportid = r.airportid
             GROUP BY 1"""
    wrong_key = """SELECT r.designator FROM example_runway r
                   JOIN example_airport a ON r.id = a.airportid"""
    for label, sql in [("COUNT after 1:N join", bad), ("wrong join key", wrong_key)]:
        vs = check(sql, m)
        print(f"\n{label}:")
        for v in vs:
            print(f"  [{v.severity}] {v.rule}: {v.message[:90]}")
        if not vs:
            print("  approved")
