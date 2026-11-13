"""Census the relationship layer of Spider 2.0's published schemas.

Spider 2.0 hands models a schema per database in two in-repo artifacts:
a `DDL.csv` of CREATE TABLE statements and one JSON per table (columns,
types, descriptions, sample rows). Neither has a slot for a primary key
or a foreign key.

That omission is deliberate, not a defect: the maintainers state in
xlang-ai/Spider2#6 and #91 that Spider 2.0 provides no primary or
foreign keys, because the cloud warehouses it targets generally declare
none, and that the SQLite portion was left the same way for consistency.
This script does not report a bug. It measures the size of what the
choice withholds — for the SQLite subset, the relationship structure is
present in the .sqlite files the benchmark distributes — so the cost of
that design can be discussed with numbers instead of impressions.

This script measures two things, both from artifacts the benchmark ships:

  census  — how many tables in the published DDL declare a PRIMARY KEY
            or a FOREIGN KEY, across every platform (bigquery, snowflake,
            sqlite)
  convert — rewrite the SQLite subset's DDL.csv files into the
            {db_id: DDL} annotation format that verify_fk_annotations.py
            already reads, so the published schema can be diffed against
            the .sqlite files the benchmark distributes separately

Layout expected (as the repo ships it, plus the local_sqlite.zip contents):

    <repo>/spider2-lite/resource/databases/<platform>/<db>/DDL.csv
    <dbdir>/<db>.sqlite

    python audit_spider2_schemas.py census  --ddl-root <repo>/spider2-lite/resource/databases
    python audit_spider2_schemas.py convert --ddl-root ... --db-dir ... --out-dir ./layout

`convert` writes <out-dir>/annotations.json and a <out-dir>/dbs/<db>/<db>.sqlite
tree of symlinks, then prints the verify_fk_annotations.py command to run.

Stdlib only. Read-only: it never opens a database, only reads text.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys

csv.field_size_limit(10 ** 9)

HAS_PK = re.compile(r"\bPRIMARY\s+KEY\b", re.I)
HAS_FK = re.compile(r"\bFOREIGN\s+KEY\b|\bREFERENCES\b", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def read_ddl(path: str) -> list:
    """-> [(table_name, ddl_text)] from one DDL.csv."""
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return [(r.get("table_name") or "", r.get("DDL") or "")
                for r in csv.DictReader(fh)]


def find_ddl(ddl_root: str) -> list:
    """-> [(platform, db_id, path)] for every DDL.csv under the root."""
    out = []
    for path in sorted(glob.glob(os.path.join(ddl_root, "**", "DDL.csv"),
                                 recursive=True)):
        rel = os.path.relpath(path, ddl_root).split(os.sep)
        if len(rel) < 3:
            continue
        out.append((rel[0], rel[1], path))
    return out


def census(ddl_root: str, as_json: bool) -> int:
    per_platform: dict = {}
    per_db = []
    for platform, db_id, path in find_ddl(ddl_root):
        tables = read_ddl(path)
        pk = sum(1 for _, d in tables if HAS_PK.search(d))
        fk = sum(1 for _, d in tables if HAS_FK.search(d))
        s = per_platform.setdefault(platform, dict(
            files=0, tables=0, tables_with_pk=0, tables_with_fk=0))
        s["files"] += 1
        s["tables"] += len(tables)
        s["tables_with_pk"] += pk
        s["tables_with_fk"] += fk
        per_db.append(dict(platform=platform, db_id=db_id,
                           tables=len(tables), tables_with_pk=pk,
                           tables_with_fk=fk))
    if as_json:
        print(json.dumps(dict(per_platform=per_platform, per_db=per_db),
                         indent=2))
        return 0
    print(f"{'platform':12}{'schema files':>14}{'tables':>9}"
          f"{'tables w/ PK':>14}{'tables w/ FK':>14}")
    for platform in sorted(per_platform):
        s = per_platform[platform]
        print(f"{platform:12}{s['files']:14}{s['tables']:9}"
              f"{s['tables_with_pk']:14}{s['tables_with_fk']:14}")
    tot = dict(tables=sum(s["tables"] for s in per_platform.values()),
               pk=sum(s["tables_with_pk"] for s in per_platform.values()),
               fk=sum(s["tables_with_fk"] for s in per_platform.values()))
    print(f"\n{tot['tables']} tables in the published schemas: "
          f"{tot['pk']} declare a primary key, {tot['fk']} declare a "
          f"foreign key.")
    return 0


def convert(ddl_root: str, db_dir: str, out_dir: str) -> int:
    dbs = {_norm(os.path.basename(p)[: -len(".sqlite")]): os.path.abspath(p)
           for p in glob.glob(os.path.join(db_dir, "*.sqlite"))}
    if not dbs:
        sys.exit(f"no .sqlite files in {db_dir}")
    tree = os.path.join(out_dir, "dbs")
    os.makedirs(tree, exist_ok=True)
    annotations, unmatched = {}, []
    for platform, db_id, path in find_ddl(ddl_root):
        if platform != "sqlite":
            continue
        key = _norm(db_id)
        if key not in dbs:
            unmatched.append(db_id)
            continue
        annotations[db_id] = "\n".join(d for _, d in read_ddl(path))
        holder = os.path.join(tree, db_id)
        os.makedirs(holder, exist_ok=True)
        link = os.path.join(holder, db_id + ".sqlite")
        if not os.path.exists(link):
            os.symlink(dbs[key], link)
    ann_path = os.path.join(out_dir, "annotations.json")
    with open(ann_path, "w") as fh:
        json.dump(annotations, fh)
    print(f"matched {len(annotations)} databases to their published schema")
    if unmatched:
        print(f"no database file for: {', '.join(sorted(unmatched))}")
    orphan = sorted(set(dbs) - {_norm(k) for k in annotations})
    if orphan:
        print(f"no published schema for: {', '.join(orphan)}")
    print("\nnow diff the published schema against the shipped databases:\n")
    print(f"  python verify_fk_annotations.py --db-dir {tree} "
          f"--annotations {ann_path}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census", help="count PK/FK declarations in the "
                                      "published DDL")
    c.add_argument("--ddl-root", required=True)
    c.add_argument("--json", action="store_true")
    v = sub.add_parser("convert", help="build annotations.json + db tree for "
                                       "verify_fk_annotations.py")
    v.add_argument("--ddl-root", required=True)
    v.add_argument("--db-dir", required=True,
                   help="directory of <db>.sqlite from local_sqlite.zip")
    v.add_argument("--out-dir", default="spider2_layout")
    a = p.parse_args(argv)
    if a.cmd == "census":
        return census(a.ddl_root, a.json)
    return convert(a.ddl_root, a.db_dir, a.out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
