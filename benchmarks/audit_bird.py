"""Audit BIRD dev gold queries with sqlsure's extraction engine.

Same conservative methodology as audit_spider.py, but consuming BIRD's
canonical tables.json format (column indices -> exact original names, so no
name-normalization heuristics are needed beyond case).

Join classification per gold query:
  fk_backed   -- equality pair matches a declared FK
  shared_key  -- same column name both sides (shared-FK/self-join; legit)
  unbacked    -- different columns, matching NO declared FK  <- candidates
  cross_join  -- no predicate anywhere (ON or WHERE)         <- candidates

Run: python benchmarks/audit_bird.py --data birddata/dev_20240627 --report out.md
"""
import argparse
import datetime
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.checker import extract  # noqa: E402


def load_schemas(path: Path) -> dict:
    """db_id -> {'fks': {frozenset((tbl,col),(tbl,col))}, 'fk_names': {frozenset(colnames)}}"""
    dbs = {}
    for db in json.load(open(path)):
        cols = db["column_names_original"]      # [ [table_idx, name], ... ]
        tbls = db["table_names_original"]

        def qual(idx):
            t_idx, name = cols[idx]
            return (tbls[t_idx].lower(), name.lower())

        fks, fk_names = set(), set()
        for a, b in db["foreign_keys"]:
            qa, qb = qual(a), qual(b)
            fks.add(frozenset((qa, qb)))
            fk_names.add(frozenset((qa[1], qb[1])))
        dbs[db["db_id"]] = {"fks": fks, "fk_names": fk_names}
    return dbs


def audit(data_dir: Path):
    import glob as _g
    tables = next(iter(_g.glob(str(data_dir / "*tables.json"))))
    questions = next(f for f in _g.glob(str(data_dir / "*.json")) if "tables" not in f)
    dbs = load_schemas(Path(tables))
    rows = json.load(open(questions))

    stats = Counter()
    candidates = {"unbacked": [], "cross_join": []}

    for qi, row in enumerate(rows):
        row.setdefault("question_id", qi)
        db, sql, q = row["db_id"], row["SQL"], row["question"]
        schema = dbs.get(db)
        if schema is None:
            stats["no_schema"] += 1
            continue
        stats["queries"] += 1
        try:
            scopes = extract(sql, dialect="sqlite")
        except Exception:
            stats["parse_failed"] += 1
            continue
        stats["parsed"] += 1

        for facts in scopes:
            for j in facts.joins:
                stats["joins"] += 1
                if not j.has_predicate:
                    stats["cross_join"] += 1
                    candidates["cross_join"].append(
                        (db, row["question_id"], q, sql, j.table))
                    continue
                if not j.on_pairs:
                    stats["non_equi"] += 1
                    continue
                verdicts = []
                for l, r in j.on_pairs:
                    cl, cr = l.lower(), r.lower()
                    if frozenset((cl, cr)) in schema["fk_names"] or cl == cr:
                        verdicts.append(
                            "fk_backed" if frozenset((cl, cr))
                            in schema["fk_names"] else "shared_key")
                    else:
                        verdicts.append("unbacked")
                if "fk_backed" in verdicts:
                    stats["fk_backed"] += 1
                elif "unbacked" in verdicts:
                    stats["unbacked"] += 1
                    pair = [p for p, v in zip(j.on_pairs, verdicts)
                            if v == "unbacked"][0]
                    candidates["unbacked"].append(
                        (db, row["question_id"], q, sql,
                         f"{pair[0]} = {pair[1]}"))
                else:
                    stats["shared_key"] += 1
    return stats, candidates


def to_markdown(stats: Counter, candidates: dict) -> str:
    jt = stats["joins"] or 1
    lines = [
        "# BIRD dev gold-query audit — sqlsure join-safety pass",
        f"*{datetime.date.today()} · BIRD dev_20240627, "
        f"{stats['queries']} gold queries, 11 databases · rulebook from "
        f"BIRD's own PK/FK declarations*",
        "",
        "| metric | value |",
        "|---|---|",
        f"| gold queries analyzed | {stats['queries']} |",
        f"| parsed by engine | {stats['parsed']} "
        f"({100 * stats['parsed'] // max(stats['queries'], 1)}%) |",
        f"| joins observed (all scopes) | {stats['joins']} |",
        f"| FK-backed | {stats['fk_backed']} "
        f"({100 * stats['fk_backed'] // jt}%) |",
        f"| shared-key (same name, no FK) | {stats['shared_key']} "
        f"({100 * stats['shared_key'] // jt}%) |",
        f"| non-equi predicates | {stats['non_equi']} |",
        f"| **unbacked (different columns, no FK)** | **{stats['unbacked']}** |",
        f"| **no predicate (cartesian)** | **{stats['cross_join']}** |",
        f"| parse failures | {stats['parse_failed']} |",
        "",
        "Candidates below are for manual review, not asserted bugs.",
        "",
    ]
    for kind, items in candidates.items():
        if not items:
            continue
        by_db = Counter(i[0] for i in items)
        lines.append(f"## {kind} candidates ({len(items)}) — by db: "
                     + ", ".join(f"{d}:{c}" for d, c in by_db.most_common()))
        for db, qid, q, sql, detail in items[:60]:
            lines += [f"- **{db}** #{qid} — *{q[:110]}*",
                      f"  - `{detail}`",
                      f"  - `{' '.join(sql.split())[:200]}`"]
        if len(items) > 60:
            lines.append(f"- … and {len(items) - 60} more")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--report", default=None)
    args = p.parse_args()
    stats, candidates = audit(Path(args.data))
    md = to_markdown(stats, candidates)
    if args.report:
        Path(args.report).write_text(md)
    for k in ("queries", "parsed", "parse_failed", "joins", "fk_backed",
              "shared_key", "non_equi", "unbacked", "cross_join"):
        print(f"{k}: {stats[k]}")
