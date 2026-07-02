"""Extract a semantic model from a dbt manifest — the zero-config path.

Two sources, best-effort:
1. `meta.sqlsure` on a model node: explicit grain / measures / sensitive columns
   (same shape as SemanticModel.from_dict table entries).
2. dbt `relationships` tests: a relationships test from child.column to
   ref('parent') field implies a many-to-one edge child -> parent with that
   key pair. `unique` tests on a column imply it is (part of) the grain.

This is what makes the inspector zero-config for dbt shops: the constraints
teams already declare as tests become enforceable semantics.
"""
from __future__ import annotations

import json
import re

from .model import MANY_TO_ONE, Join, Measure, SemanticModel, Table

_REF = re.compile(r"ref\(\s*['\"]([^'\"]+)['\"]\s*\)")


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
    return m
