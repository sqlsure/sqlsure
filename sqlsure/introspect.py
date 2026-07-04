"""Build a SemanticModel from a live database's own declared constraints.

The "we have no semantic layer" objection, answered: every database already
declares facts in its catalog — primary keys (grain) and foreign keys (join
cardinality). This module reads them, so a bare LLM -> SQL -> DB agent setup
gets a rulebook with zero authoring:

    from sqlsure.introspect import model_from_sqlite
    model = model_from_sqlite("app.db")
    violations = check(sql, model, dialect="sqlite")

Two entry points:

- model_from_sqlite(path_or_conn): stdlib-only, tested against real BIRD
  benchmark databases. Handles FKs that reference a parent's implicit
  primary key (``REFERENCES parent`` with no column list) — the exact
  extraction gap behind bird-bench/mini_dev#37.
- model_from_information_schema(cursor, dialect=...): PK/FK via the
  standard information_schema views for postgres and mysql servers.
  Requires a live connection; queries are standard but bring your own
  server to verify against your setup.

Cardinality: an FK edge is child -> parent MANY_TO_ONE, upgraded to
ONE_TO_ONE when the child-side key is itself unique (the child's PK or a
unique index), since then each parent row matches at most one child.

Introspected models cover grain and join edges only. Additivity and column
policy are judgment calls the catalog can't make — declare those in
``meta.sqlsure`` (dbt) or a model JSON. Export the proposed rulebook for
human review with ``SemanticModel.to_dict()``.
"""
from __future__ import annotations

import sqlite3

from .model import MANY_TO_ONE, ONE_TO_ONE, Join, SemanticModel, Table


# ------------------------------------------------------------- sqlite ---

def model_from_sqlite(db: str | sqlite3.Connection) -> SemanticModel:
    """PRAGMA-based extraction: table_info -> grain, foreign_key_list -> edges."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True) if isinstance(db, str) else db
    try:
        m = SemanticModel()
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")]
        pk_cols: dict[str, list[str]] = {}
        for t in tables:
            info = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
            # column 5 is pk ordinal (0 = not part of pk)
            pks = [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]
            pk_cols[t.lower()] = [c.lower() for c in pks]
            m.tables[t.lower()] = Table(t.lower(), grain=[c.lower() for c in pks])

        for t in tables:
            child = t.lower()
            unique_keys = _sqlite_unique_keys(conn, t, pk_cols[child])
            # group FK rows by constraint id: composite keys share an id,
            # separate ids to the same parent are role-playing dims
            by_id: dict[int, list] = {}
            for row in conn.execute(f'PRAGMA foreign_key_list("{t}")'):
                by_id.setdefault(row[0], []).append(row)
            for rows in by_id.values():
                rows.sort(key=lambda r: r[1])  # seq
                parent = rows[0][2].lower()
                keys = []
                for i, r in enumerate(rows):
                    frm = r[3].lower()
                    # r[4] is None for `REFERENCES parent` with no column
                    # list: the FK targets the parent's implicit PK
                    to = r[4].lower() if r[4] else (
                        pk_cols.get(parent, [None] * (i + 1))[i] or frm)
                    keys.append((frm, to))
                card = ONE_TO_ONE if frozenset(k for k, _ in keys) in unique_keys \
                    else MANY_TO_ONE
                existing = m.joins.get((child, parent))
                if existing:
                    existing.keys.extend(keys)
                else:
                    m.joins[(child, parent)] = Join(child, parent, card, keys)
        return m
    finally:
        if isinstance(db, str):
            conn.close()


def _sqlite_unique_keys(conn, table: str, pk: list[str]) -> set[frozenset]:
    """Column sets guaranteed unique in `table`: the PK plus unique indexes."""
    uniques = {frozenset(pk)} if pk else set()
    for idx in conn.execute(f'PRAGMA index_list("{table}")'):
        if idx[2]:  # unique flag
            cols = [r[2].lower() for r in
                    conn.execute(f'PRAGMA index_info("{idx[1]}")') if r[2]]
            if cols:
                uniques.add(frozenset(cols))
    return uniques


# --------------------------------------------------- information_schema ---

_PK_SQL = """
SELECT kcu.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = {ph}
ORDER BY kcu.table_name, kcu.ordinal_position
"""

_FK_SQL = {
    "postgres": """
SELECT tc.constraint_name, kcu.table_name, kcu.column_name,
       ccu.table_name, ccu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON tc.constraint_name = ccu.constraint_name
 AND tc.table_schema = ccu.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = {ph}
ORDER BY tc.constraint_name, kcu.ordinal_position
""",
    "mysql": """
SELECT kcu.constraint_name, kcu.table_name, kcu.column_name,
       kcu.referenced_table_name, kcu.referenced_column_name
FROM information_schema.key_column_usage kcu
WHERE kcu.referenced_table_name IS NOT NULL AND kcu.table_schema = {ph}
ORDER BY kcu.constraint_name, kcu.ordinal_position
""",
}

_PLACEHOLDER = {"postgres": "%s", "mysql": "%s"}


def model_from_information_schema(cursor, dialect: str = "postgres",
                                  schema: str = "public") -> SemanticModel:
    """PK/FK from information_schema on a live DBAPI cursor.

    dialect: "postgres" (also fits most information_schema-compliant
    warehouses) or "mysql" (uses referenced_table_name; pass the database
    name as `schema`).
    """
    if dialect not in _FK_SQL:
        raise ValueError(f"unsupported dialect {dialect!r}; "
                         f"expected one of {sorted(_FK_SQL)}")
    ph = _PLACEHOLDER[dialect]
    m = SemanticModel()

    cursor.execute(_PK_SQL.format(ph=ph), (schema,))
    for tname, col in cursor.fetchall():
        t = m.tables.setdefault(tname.lower(), Table(tname.lower()))
        t.grain.append(col.lower())

    cursor.execute(_FK_SQL[dialect].format(ph=ph), (schema,))
    by_constraint: dict[str, list] = {}
    for row in cursor.fetchall():
        by_constraint.setdefault(row[0], []).append(row)
    for rows in by_constraint.values():
        child, parent = rows[0][1].lower(), rows[0][3].lower()
        m.tables.setdefault(child, Table(child))
        m.tables.setdefault(parent, Table(parent))
        keys = [(r[2].lower(), r[4].lower()) for r in rows]
        card = ONE_TO_ONE if m.tables[child].grain and \
            frozenset(k for k, _ in keys) == frozenset(m.tables[child].grain) \
            else MANY_TO_ONE
        existing = m.joins.get((child, parent))
        if existing:
            existing.keys.extend(keys)
        else:
            m.joins[(child, parent)] = Join(child, parent, card, keys)
    return m


# ---------------------------------------------------------------- demo ---

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m sqlsure.introspect <db.sqlite> [--json]")
        sys.exit(2)
    model = model_from_sqlite(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(model.to_dict(), indent=2))
    else:
        n_edges = len(model.joins)
        print(f"{sys.argv[1]}: {len(model.tables)} tables, {n_edges} join edges")
        for (a, b), j in sorted(model.joins.items()):
            print(f"  {a} -> {b}: {j.cardinality} on {j.keys}")
        bare = [t for t, spec in sorted(model.tables.items()) if not spec.grain]
        if bare:
            print(f"  no declared grain (add unique tests or PKs): {', '.join(bare)}")
