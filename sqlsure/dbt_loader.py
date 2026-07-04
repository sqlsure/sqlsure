"""Extract a semantic model from a dbt manifest — the zero-config path.

Three sources, best-effort:
1. `meta.sqlsure` on a model node: explicit grain / measures / sensitive columns
   (same shape as SemanticModel.from_dict table entries).
2. dbt `relationships` tests: a relationships test from child.column to
   ref('parent') field implies a many-to-one edge child -> parent with that
   key pair. `unique` tests on a column imply it is (part of) the grain.
3. MetricFlow `semantic_models` (the dbt Semantic Layer's own declarations,
   present in the manifest or in schema YAML): `primary` entities -> grain,
   `foreign` entities -> join edges (MetricFlow links a foreign entity to
   the same-named primary entity in another semantic model), measure `agg`
   -> additivity (`non_additive_dimension` -> semi-additive over it).

This is what makes the inspector zero-config for dbt shops: the constraints
teams already declare — as tests or as Semantic Layer definitions — become
enforceable on arbitrary SQL, not just on queries routed through MetricFlow.
"""
from __future__ import annotations

import json
import re

from .model import (
    ADDITIVE,
    MANY_TO_ONE,
    NON_ADDITIVE,
    SEMI_ADDITIVE,
    Join,
    Measure,
    SemanticModel,
    Table,
)

_REF = re.compile(r"ref\(\s*['\"]([^'\"]+)['\"]\s*\)")
_IDENT = re.compile(r"^\w+$")

_ADDITIVE_AGGS = {"sum", "count", "count_distinct", "sum_boolean"}
_NON_ADDITIVE_AGGS = {"average", "avg", "median", "percentile", "min", "max"}


def load_manifest(path: str) -> SemanticModel:
    with open(path) as f:
        manifest = json.load(f)
    m = SemanticModel()
    nodes = manifest.get("nodes", {})

    for node in nodes.values():
        if node.get("resource_type") != "model":
            continue
        name = node.get("name")
        meta = node.get("meta") or node.get("config", {}).get("meta") or {}
        spec = meta.get("sqlsure") or {}
        grain = spec.get("grain", [])
        if isinstance(grain, str):
            grain = [grain]
        measures = {}
        for mname, mspec in spec.get("measures", {}).items():
            if isinstance(mspec, str):
                measures[mname] = Measure(mname, mspec)
            else:
                measures[mname] = Measure(
                    mname, mspec.get("additivity", "additive"),
                    mspec.get("semi_additive_over"))
        m.tables[name] = Table(name, grain, measures,
                               set(spec.get("sensitive", [])))

    for node in nodes.values():
        if node.get("resource_type") != "test":
            continue
        tm = node.get("test_metadata") or {}
        kwargs = tm.get("kwargs", {})
        column = kwargs.get("column_name") or node.get("column_name")
        deps = (node.get("depends_on") or {}).get("nodes", [])
        child = next((d.split(".")[-1] for d in deps), None)

        if tm.get("name") == "unique" and child and column:
            t = m.tables.setdefault(child, Table(child))
            if column not in t.grain:
                t.grain.append(column)

        if tm.get("name") == "relationships" and column:
            ref = _REF.search(kwargs.get("to", "") or "")
            parent = ref.group(1) if ref else None
            field = kwargs.get("field")
            child = next((d.split(".")[-1] for d in deps
                          if parent and d.split(".")[-1] != parent), child)
            if child and parent and field:
                m.tables.setdefault(child, Table(child))
                m.tables.setdefault(parent, Table(parent))
                existing = m.joins.get((child, parent))
                if existing:  # multiple FKs to one parent (role-playing dims)
                    if (column, field) not in existing.keys:
                        existing.keys.append((column, field))
                else:
                    m.joins[(child, parent)] = Join(
                        child, parent, MANY_TO_ONE, [(column, field)])

    sms = manifest.get("semantic_models") or {}
    if sms:
        apply_semantic_models(m, list(sms.values()))
    return m


def apply_semantic_models(m: SemanticModel, sms: list[dict]) -> SemanticModel:
    """Fold MetricFlow semantic_models entries into a SemanticModel.

    Joins are implicit in MetricFlow: a `foreign` entity on one semantic
    model resolves to the semantic model that declares the same entity
    name as `primary`. Key columns come from `expr` (falling back to the
    entity name, MetricFlow's own default).
    """
    def _table(sm: dict) -> str | None:
        ref = _REF.search(str(sm.get("model", "")))
        return ref.group(1).lower() if ref else None

    def _key(ent: dict) -> str | None:
        expr = str(ent.get("expr") or ent.get("name") or "")
        return expr.lower() if _IDENT.match(expr) else None

    primaries: dict[str, tuple[str, str]] = {}  # entity name -> (table, key col)
    for sm in sms:
        tbl = _table(sm)
        if not tbl:
            continue
        t = m.tables.setdefault(tbl, Table(tbl))
        for ent in sm.get("entities") or []:
            if ent.get("type") == "primary":
                key = _key(ent)
                if key:
                    primaries[str(ent.get("name", "")).lower()] = (tbl, key)
                    if not t.grain:
                        t.grain.append(key)

    for sm in sms:
        tbl = _table(sm)
        if not tbl:
            continue
        t = m.tables[tbl]
        for ent in sm.get("entities") or []:
            if ent.get("type") != "foreign":
                continue
            target = primaries.get(str(ent.get("name", "")).lower())
            key = _key(ent)
            if not target or not key or target[0] == tbl:
                continue
            parent, parent_key = target
            existing = m.joins.get((tbl, parent))
            if existing:
                if (key, parent_key) not in existing.keys:
                    existing.keys.append((key, parent_key))
            else:
                m.joins[(tbl, parent)] = Join(
                    tbl, parent, MANY_TO_ONE, [(key, parent_key)])

        for meas in sm.get("measures") or []:
            expr = str(meas.get("expr") or meas.get("name") or "")
            col = expr.lower() if _IDENT.match(expr) and expr != "1" else None
            if not col:
                continue
            agg = str(meas.get("agg", "")).lower()
            nad = meas.get("non_additive_dimension") or {}
            if nad.get("name"):
                t.measures.setdefault(col, Measure(
                    col, SEMI_ADDITIVE, str(nad["name"]).lower()))
            elif agg in _ADDITIVE_AGGS:
                t.measures.setdefault(col, Measure(col, ADDITIVE))
            elif agg in _NON_ADDITIVE_AGGS:
                t.measures.setdefault(col, Measure(col, NON_ADDITIVE))
    return m


def load_semantic_yaml(paths: list[str]) -> SemanticModel:
    """Rulebook from raw schema YAML files containing `semantic_models:`
    (no compiled manifest needed)."""
    import yaml

    sms: list[dict] = []
    for p in paths:
        with open(p) as f:
            doc = yaml.safe_load(f) or {}
        sms.extend(doc.get("semantic_models") or [])
    return apply_semantic_models(SemanticModel(), sms)
