"""Verify a benchmark's declared foreign keys against the databases it ships.

Text-to-SQL benchmarks hand models a schema — tables, keys, and foreign-key
relationships — and grade them on the SQL that comes back. When a foreign
key exists in the shipped database but is missing from the published schema
annotations, every model is told a relationship does not exist, and every
join over it looks unbacked to any tool that trusts the annotations.

This script reads the FKs the databases actually declare and diffs them
against the published annotations, in whichever of the two formats the
benchmark ships:

  tables.json  — BIRD/Spider index format (column_names_original +
                 foreign_keys index pairs)
  schemas.json — {db_id: "CREATE TABLE ... FOREIGN KEY ..."} DDL text,
                 as in BIRD Mini-Dev's baseline_inference/schemas/

Stdlib only, no install, read-only: it opens each database read-only and
runs PRAGMA foreign_key_list. One wrinkle worth keeping — SQLite allows
`REFERENCES parent` with no column list, meaning the parent's implicit
primary key; a naive reader drops those, which is how the two
european_football_2 edges went missing from BIRD dev in the first place.

    python verify_fk_annotations.py --db-dir dev_databases --annotations dev_tables.json
    python verify_fk_annotations.py --db-dir dev_databases --annotations schemas/sqlite.json

Exit code 0 when the annotations cover every declared FK, 1 otherwise.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys

FK = tuple  # (child, child_col, parent, parent_col), all lowercased


def fks_from_sqlite(path: str) -> set:
    """What the database itself declares."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")]
        pk = {}
        for t in tables:
            info = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
            pk[t.lower()] = [r[1].lower() for r in
                             sorted((r for r in info if r[5]), key=lambda r: r[5])]
        out = set()
        for t in tables:
            child = t.lower()
            by_id: dict = {}
            for row in conn.execute(f'PRAGMA foreign_key_list("{t}")'):
                by_id.setdefault(row[0], []).append(row)
            for rows in by_id.values():
                rows.sort(key=lambda r: r[1])          # seq
                parent = rows[0][2].lower()
                for i, r in enumerate(rows):
                    frm = r[3].lower()
                    # r[4] is None for `REFERENCES parent` with no column
                    # list: the FK targets the parent's implicit PK
                    to = r[4].lower() if r[4] else (
                        pk.get(parent, [None] * (i + 1))[i] or frm)
                    out.add((child, frm, parent, to))
        return out
    finally:
        conn.close()


def fks_from_tables_json(entry: dict) -> set:
    cols = entry["column_names_original"]
    tbls = entry["table_names_original"]
    out = set()
    for a, b in entry.get("foreign_keys", []):
        (ta, ca), (tb, cb) = cols[a], cols[b]
        out.add((tbls[ta].lower(), ca.lower(), tbls[tb].lower(), cb.lower()))
    return out


_CREATE = re.compile(r'CREATE TABLE\s+`?(\w+)`?\s*\((.*?)(?=CREATE TABLE|\Z)',
                     re.S | re.I)
_FK = re.compile(r'FOREIGN KEY\s*\(\s*`?(\w+)`?\s*\)\s*REFERENCES\s*'
                 r'`?(\w+)`?\s*\(\s*`?(\w+)`?\s*\)', re.I)


def fks_from_ddl(ddl: str) -> set:
    out = set()
    for blk in _CREATE.finditer(ddl):
        child, body = blk.group(1).lower(), blk.group(2)
        for m in _FK.finditer(body):
            out.add((child, m.group(1).lower(),
                     m.group(2).lower(), m.group(3).lower()))
    return out


def load_annotations(path: str) -> dict:
    """-> {db_id: set of FK tuples}, accepting either published format."""
    doc = json.load(open(path))
    if isinstance(doc, list):                       # tables.json
        return {e["db_id"]: fks_from_tables_json(e) for e in doc}
    if isinstance(doc, dict):                       # {db_id: DDL text}
        return {k: fks_from_ddl(v) for k, v in doc.items()
                if isinstance(v, str)}
    raise SystemExit(f"unrecognized annotation format: {path}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--db-dir", required=True,
                   help="directory holding <db_id>/<db_id>.sqlite")
    p.add_argument("--annotations", required=True,
                   help="tables.json or a {db_id: DDL} schemas json")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)

    declared = load_annotations(args.annotations)
    rows, missing_total, extra_total = [], 0, 0

    for db_id in sorted(declared):
        sqlite_path = os.path.join(args.db_dir, db_id, f"{db_id}.sqlite")
        if not glob.glob(sqlite_path):
            rows.append({"db_id": db_id, "status": "no database file"})
            continue
        actual = fks_from_sqlite(sqlite_path)
        missing = sorted(actual - declared[db_id])   # in the db, not annotated
        extra = sorted(declared[db_id] - actual)     # annotated, not in the db
        missing_total += len(missing)
        extra_total += len(extra)
        rows.append({"db_id": db_id, "annotated": len(declared[db_id]),
                     "in_database": len(actual),
                     "missing_from_annotations": [list(m) for m in missing],
                     "annotated_but_not_in_database": [list(e) for e in extra]})

    if args.json:
        print(json.dumps({"missing_total": missing_total,
                          "extra_total": extra_total, "databases": rows},
                         indent=2))
        return 1 if missing_total else 0

    print(f"{'database':<28}{'annotated':>10}{'in db':>8}{'missing':>9}{'extra':>7}")
    for r in rows:
        if r.get("status"):
            print(f"{r['db_id']:<28}{r['status']:>34}")
            continue
        print(f"{r['db_id']:<28}{r['annotated']:>10}{r['in_database']:>8}"
              f"{len(r['missing_from_annotations']):>9}"
              f"{len(r['annotated_but_not_in_database']):>7}")
    if missing_total:
        print(f"\nforeign keys the databases declare but the annotations omit "
              f"({missing_total}):")
        for r in rows:
            for c, cc, pa, pc in r.get("missing_from_annotations", []):
                print(f"  {r['db_id']}: {c}.{cc} -> {pa}.{pc}")
    else:
        print("\nevery foreign key declared by the databases is annotated.")
    if extra_total:
        print(f"\nannotated but absent from the databases ({extra_total}) — "
              f"usually intentional soft links, listed for review:")
        for r in rows:
            for c, cc, pa, pc in r.get("annotated_but_not_in_database", [])[:10]:
                print(f"  {r['db_id']}: {c}.{cc} -> {pa}.{pc}")
    return 1 if missing_total else 0


if __name__ == "__main__":
    sys.exit(main())
