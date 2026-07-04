"""WrenAI MDL -> SemanticModel: enforce the context layer, don't just prompt with it.

WrenAI's Modeling Definition Language (MDL) is the declared heart of their
"open context engine": models with primary keys, relationships with explicit
join cardinality, cubes with aggregate measures. Today those declarations
are *context* — they inform generation but nothing verifies the generated
SQL against them. This loader turns an MDL manifest into a sqlsure rulebook
so the declarations become enforceable:

    from mdl_loader import load_mdl
    model = load_mdl("mdl.json")
    violations = check(sql, model)

Mapping (verified against Canner/WrenAI's shipped example
examples/v5-jaffle/apps/sales-report/mdl.json and core/wren-mdl/mdl.schema.json):

  models[].primaryKey / columns[].isPrimaryKey  -> Table.grain
  relationships[].joinType + condition          -> Join edge with keys
      ("orders.customer_id = customers.id", MANY_TO_ONE)
  cubes[].measures[].expression                 -> additivity of the
      underlying column (SUM/COUNT -> additive, AVG/MEDIAN/MIN/MAX -> not)

Demo: python integrations/mdl_loader.py path/to/mdl.json
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.model import (  # noqa: E402
    ADDITIVE,
    MANY_TO_MANY,
    MANY_TO_ONE,
    NON_ADDITIVE,
    ONE_TO_MANY,
    ONE_TO_ONE,
    Join,
    Measure,
    SemanticModel,
    Table,
)

_JOIN_TYPES = {
    "MANY_TO_ONE": MANY_TO_ONE,
    "ONE_TO_MANY": ONE_TO_MANY,
    "ONE_TO_ONE": ONE_TO_ONE,
    "MANY_TO_MANY": MANY_TO_MANY,
}

_EQ = re.compile(r'"?(\w+)"?\."?(\w+)"?\s*=\s*"?(\w+)"?\."?(\w+)"?')
_AGG = re.compile(r"^\s*(SUM|COUNT|AVG|MIN|MAX|MEDIAN)\s*\(\s*(?:\"?(\w+)\"?\.)?\"?([\w*]+)\"?\s*\)\s*$", re.I)


def load_mdl(source: str | dict) -> SemanticModel:
    """MDL manifest (path or parsed dict) -> SemanticModel."""
    doc = source if isinstance(source, dict) else json.load(open(source))
    m = SemanticModel()

    for model in doc.get("models", []) or []:
        name = model["name"].lower()
        grain = []
        pk = model.get("primaryKey")
        if pk:
            grain = [pk.lower()]
        else:
            grain = [c["name"].lower() for c in model.get("columns", [])
                     if c.get("isPrimaryKey")]
        m.tables[name] = Table(name, grain=grain)

    for rel in doc.get("relationships", []) or []:
        models = [x.lower() for x in rel.get("models", [])]
        if len(models) != 2:
            continue
        a, b = models
        card = _JOIN_TYPES.get((rel.get("joinType") or "").upper())
        if card is None:
            continue
        # condition: "orders.customer_id = customers.id" (AND-composites ok);
        # table order inside the condition is not guaranteed to match models[]
        keys = []
        for lt, lc, rt, rc in _EQ.findall(rel.get("condition", "") or ""):
            lt, lc, rt, rc = lt.lower(), lc.lower(), rt.lower(), rc.lower()
            if lt == a and rt == b:
                keys.append((lc, rc))
            elif lt == b and rt == a:
                keys.append((rc, lc))
        if not keys:
            continue
        existing = m.joins.get((a, b))
        if existing:  # multiple relationships between same pair (role-playing)
            existing.keys.extend(keys)
        else:
            m.joins[(a, b)] = Join(a, b, card, keys)

    # cubes: measures declare the aggregate; the underlying column is what
    # appears in raw SQL, so attach additivity there, on the base model
    for cube in doc.get("cubes", []) or []:
        base = (cube.get("baseObject") or "").lower()
        if base not in m.tables:
            continue
        for meas in cube.get("measures", []) or []:
            g = _AGG.match(meas.get("expression", "") or "")
            if not g:
                continue
            func, _tbl, col = g.group(1).upper(), g.group(2), g.group(3)
            if col == "*":
                continue
            additivity = ADDITIVE if func in ("SUM", "COUNT") else NON_ADDITIVE
            m.tables[base].measures.setdefault(
                col.lower(), Measure(col.lower(), additivity))

    return m


if __name__ == "__main__":
    from sqlsure.checker import check

    path = sys.argv[1] if len(sys.argv) > 1 else "wren-mdl-example.json"
    m = load_mdl(path)
    print(f"MDL loaded: {len(m.tables)} models, {len(m.joins)} relationship edges")
    for (l, r), j in m.joins.items():
        print(f"  {l} -> {r}: {j.cardinality} on {j.keys}")
    for t in m.tables.values():
        if t.measures:
            print(f"  measures on {t.name}: "
                  f"{ {k: v.additivity for k, v in t.measures.items()} }")

    # demo: enforce the MDL's declared semantics on arbitrary SQL
    cases = [
        ("COUNT(*) after one-to-many join (inflates customer counts)",
         "SELECT c.name, COUNT(*) FROM customers c "
         "JOIN orders o ON c.id = o.customer_id GROUP BY c.name"),
        ("join on a key the MDL does not declare",
         "SELECT o.amount FROM orders o JOIN customers c ON o.id = c.id"),
        ("clean: sum of the many side over the declared key",
         "SELECT c.name, SUM(o.amount) FROM customers c "
         "JOIN orders o ON c.id = o.customer_id GROUP BY c.name"),
    ]
    for label, sql in cases:
        vs = check(sql, m)
        print(f"\n{label}:")
        for v in vs:
            print(f"  [{v.severity}] {v.rule}: {v.message[:100]}")
        if not vs:
            print("  approved")
