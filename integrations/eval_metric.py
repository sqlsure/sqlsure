"""Semantic-validity as an eval metric for NL2SQL harnesses.

Execution-accuracy (does the result match gold?) misses the case where the
generated SQL *and* the gold SQL share the same semantic bug (proven: BIRD
dev #571). This metric adds a second axis: does the SQL violate declared
semantics, regardless of what it returns?

    from eval_metric import semantic_report
    report = semantic_report(items, model)      # items: [{"id","sql"}]

Demo on real BIRD dev data (builds the rulebook from BIRD's own PK/FKs):
    python integrations/eval_metric.py birddata/dev_20240627
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.checker import check  # noqa: E402
from sqlsure.model import MANY_TO_ONE, Join, SemanticModel, Table  # noqa: E402


def semantic_report(items: list[dict], model: SemanticModel,
                    dialect: str | None = None) -> dict:
    """items: [{"id": ..., "sql": ...}] -> aggregate + per-item findings."""
    errors_n, warns_n, by_rule, details = 0, 0, Counter(), []
    parse_failed = 0
    for it in items:
        try:
            vs = check(it["sql"], model, dialect=dialect)
        except Exception:
            parse_failed += 1
            continue
        errors = [v for v in vs if v.severity in ("error", "policy")]
        if errors:
            errors_n += 1
        elif vs:
            warns_n += 1
        if vs:
            for v in vs:
                by_rule[v.rule] += 1
            details.append({"id": it["id"],
                            "findings": [v.to_dict() for v in vs]})
    n = len(items) - parse_failed
    return {
        "total": len(items), "checked": n, "parse_failed": parse_failed,
        "with_errors": errors_n, "with_warnings_only": warns_n,
        "semantic_pass_rate": round(1 - errors_n / max(n, 1), 4),
        "by_rule": dict(by_rule),
        "details": details,
    }


def model_from_bird_tables(tables_entry: dict) -> SemanticModel:
    """BIRD/Spider tables.json entry -> SemanticModel (PK->grain, FK->edge)."""
    m = SemanticModel()
    cols = tables_entry["column_names_original"]
    tbls = tables_entry["table_names_original"]
    for t in tbls:
        m.tables[t.lower()] = Table(t.lower())
    for pk in tables_entry.get("primary_keys", []):
        for idx in (pk if isinstance(pk, list) else [pk]):
            t_idx, col = cols[idx]
            m.tables[tbls[t_idx].lower()].grain.append(col.lower())
    for a, b in tables_entry.get("foreign_keys", []):
        (ta, ca), (tb, cb) = cols[a], cols[b]
        child, parent = tbls[ta].lower(), tbls[tb].lower()
        key = (ca.lower(), cb.lower())
        existing = m.joins.get((child, parent))
        if existing:  # multiple FKs to same parent (role-playing dims)
            existing.keys.append(key)
        else:
            m.joins[(child, parent)] = Join(child, parent, MANY_TO_ONE, [key])
    return m


# ---------------------------------------------------------------- demo ---
if __name__ == "__main__":
    data = sys.argv[1] if len(sys.argv) > 1 else "birddata/dev_20240627"
    db_id = sys.argv[2] if len(sys.argv) > 2 else "codebase_community"

    tables = {t["db_id"]: t for t in
              json.load(open(f"{data}/dev_tables.json"))}
    model = model_from_bird_tables(tables[db_id])
    items = [{"id": r["question_id"], "sql": r["SQL"].lower()}
             for r in json.load(open(f"{data}/dev.json"))
             if r["db_id"] == db_id]

    r = semantic_report(items, model, dialect="sqlite")
    print(f"db: {db_id} — {r['checked']} gold queries checked")
    print(f"semantic pass rate: {r['semantic_pass_rate']:.1%} "
          f"({r['with_errors']} with errors, "
          f"{r['with_warnings_only']} warnings-only)")
    print("findings by rule:", r["by_rule"])
    for d in r["details"][:5]:
        f = d["findings"][0]
        print(f"  #{d['id']}: {f['rule']} — {f['message'][:90]}")
