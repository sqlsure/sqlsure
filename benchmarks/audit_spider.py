"""Audit Spider's gold queries with sqlsure's extraction engine.

For each of the 1,034 validation gold queries, derive the rulebook from
Spider's own schema (PKs -> grain, FKs -> join edges) and classify every
join the gold SQL performs:

  fk_backed   -- key pair matches a declared FK (verified-safe)
  shared_key  -- same column name both sides (shared-FK/self-join; legit)
  unbacked    -- different columns, matching NO declared FK  <- candidates
  cross_join  -- no join predicate anywhere (ON or WHERE)    <- candidates

Conservative by construction: only `unbacked` and `cross_join` are treated
as anomaly candidates, and they are reported for manual review, not claimed
as bugs. Name matching is normalization-robust (case/space/underscore).

Run: python benchmarks/audit_spider.py --data DIR --report out.md
DIR must contain spider_schema.json and spider_validation.json.
"""
import argparse
import datetime
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.checker import extract  # noqa: E402


def canon(name: str) -> str:
    return re.sub(r"[\s_]+", "", name.lower())


def load_schemas(path: Path) -> dict:
    """db_id -> {'fks': set of frozenset(canon col pairs), 'pks': set}"""
    dbs = {}
    for row in json.load(open(path)):
        fks, pks = set(), set()
        for part in (row.get("Foreign Keys") or "").split("|"):
            m = re.match(r"\s*\S.*?:\s*(.+?)\s+equals\s+.*?:\s*(.+?)\s*$", part)
            if m:
                fks.add(frozenset((canon(m.group(1)), canon(m.group(2)))))
        for part in (row.get("Primary Keys") or "").split("|"):
            if ":" in part:
                pks.add(canon(part.split(":", 1)[1]))
        dbs[row["db_id"]] = {"fks": fks, "pks": pks}
    return dbs


def audit(data_dir: Path):
    dbs = load_schemas(data_dir / "spider_schema.json")
    rows = json.load(open(data_dir / "spider_validation.json"))

    stats = Counter()
    candidates = {"unbacked": [], "cross_join": []}

    for row in rows:
        db, sql, q = row["db_id"], row["query"], row["question"]
        schema = dbs.get(db)
        if schema is None:
            stats["no_schema"] += 1
            continue
        stats["queries"] += 1
        try:
            scopes = extract(sql.lower(), dialect="sqlite")
        except Exception:
            stats["parse_failed"] += 1
            continue
        stats["parsed"] += 1

        for facts in scopes:
            for j in facts.joins:
                stats["joins"] += 1
                if not j.has_predicate:
                    stats["cross_join"] += 1
                    candidates["cross_join"].append((db, q, sql, j.table))
                    continue
                if not j.on_pairs:  # predicate exists but no col=col pair
                    stats["non_equi"] += 1
                    continue
                verdicts = []
                for l, r in j.on_pairs:
                    cl, cr = canon(l), canon(r)
                    if frozenset((cl, cr)) in schema["fks"]:
                        verdicts.append("fk_backed")
                    elif cl == cr:
                        verdicts.append("shared_key")
                    else:
                        verdicts.append("unbacked")
                if "fk_backed" in verdicts:
                    stats["fk_backed"] += 1
                elif "unbacked" in verdicts:
                    stats["unbacked"] += 1
                    pair = [p for p, v in zip(j.on_pairs, verdicts)
                            if v == "unbacked"][0]
                    candidates["unbacked"].append((db, q, sql, f"{pair[0]} = {pair[1]}"))
                else:
                    stats["shared_key"] += 1
    return stats, candidates


def to_markdown(stats: Counter, candidates: dict) -> str:
    jt = stats["joins"] or 1
    lines = [
        "# Spider gold-query audit — sqlsure join-safety pass",
        f"*{datetime.date.today()} · Spider validation split, "
        f"{stats['queries']} gold queries · rulebook derived from Spider's "
        f"own PK/FK declarations*",
        "",
        "| metric | value |",
        "|---|---|",
        f"| gold queries analyzed | {stats['queries']} |",
        f"| parsed by engine | {stats['parsed']} "
        f"({100 * stats['parsed'] // max(stats['queries'], 1)}%) |",
        f"| joins observed (all scopes incl. subqueries) | {stats['joins']} |",
        f"| joins backed by a declared FK | {stats['fk_backed']} "
        f"({100 * stats['fk_backed'] // jt}%) |",
        f"| shared-key joins (same column both sides, no FK) | "
        f"{stats['shared_key']} ({100 * stats['shared_key'] // jt}%) |",
        f"| non-equi join predicates | {stats['non_equi']} |",
        f"| **unbacked joins (different columns, no FK)** | "
        f"**{stats['unbacked']}** |",
        f"| **joins with no predicate at all (cartesian)** | "
        f"**{stats['cross_join']}** |",
        "",
        "`unbacked` and `cartesian` rows are *anomaly candidates for manual "
        "review*, not asserted bugs.",
        "",
    ]
    for kind, items in candidates.items():
        if not items:
            continue
        lines.append(f"## {kind} candidates ({len(items)})")
        for db, q, sql, detail in items[:40]:
            lines += [f"- **{db}** — *{q}*",
                      f"  - `{detail}`",
                      f"  - `{' '.join(sql.split())[:180]}`"]
        if len(items) > 40:
            lines.append(f"- … and {len(items) - 40} more")
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
    print(md if not args.report else md.split("\n\n")[0] + "\n(full report written)")
    for k in ("queries", "parsed", "joins", "fk_backed", "shared_key",
              "unbacked", "cross_join"):
        print(f"{k}: {stats[k]}")
