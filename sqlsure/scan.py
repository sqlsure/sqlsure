"""Repo scanner: point sqlsure at any dbt repo, get a coverage + violation report.

    python -m sqlsure.scan path/to/repo [--dialect snowflake] [--report out.md]

Works without dbt installed:
- rulebook: target/manifest.json if present, else schema .yml files
  (unique tests -> grain, relationships tests -> many-to-one edges,
  dbt_utils.unique_combination_of_columns -> composite grain, meta.sqlsure)
- SQL: compiled_code from the manifest if present, else raw model .sql
  with best-effort Jinja stripping (files that still fail to parse are
  counted as skipped, never guessed at)
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml

from .checker import check, extract
from .dbt_loader import load_manifest
from .model import MANY_TO_ONE, Join, Measure, SemanticModel, Table

_REF = re.compile(r"\{\{\s*ref\(([^)]*)\)\s*\}\}")
_SOURCE = re.compile(r"\{\{\s*source\(([^)]*)\)\s*\}\}")
_QUOTED = re.compile(r"['\"]([^'\"]+)['\"]")
_BLOCK = re.compile(r"\{%.*?%\}", re.S)
_COMMENT = re.compile(r"\{#.*?#\}", re.S)
_EXPR = re.compile(r"\{\{.*?\}\}", re.S)
_REF_IN_YML = re.compile(r"ref\(\s*['\"]([^'\"]+)['\"]\s*\)")


def strip_jinja(sql: str) -> str:
    def last_quoted(m):
        names = _QUOTED.findall(m.group(1))
        return names[-1] if names else "unknown_ref"
    sql = _COMMENT.sub("", sql)
    sql = _REF.sub(last_quoted, sql)
    sql = _SOURCE.sub(last_quoted, sql)
    sql = _BLOCK.sub("", sql)
    sql = _EXPR.sub("NULL", sql)
    return sql


def _tests_of(node: dict) -> list:
    return (node.get("tests") or []) + (node.get("data_tests") or [])


def load_yaml_model(project_dir: Path) -> SemanticModel:
    """Build a semantic model straight from schema .yml files (no dbt run)."""
    m = SemanticModel()
    for path in list(project_dir.rglob("*.yml")) + list(project_dir.rglob("*.yaml")):
        if "dbt_packages" in path.parts or "target" in path.parts:
            continue
        try:
            docs = list(yaml.safe_load_all(path.read_text()))
        except Exception:
            continue
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            for node in doc.get("models") or []:
                if not isinstance(node, dict) or "name" not in node:
                    continue
                name = node["name"]
                t = m.tables.setdefault(name, Table(name))

                for test in _tests_of(node):  # model-level tests
                    if isinstance(test, dict):
                        combo = (test.get("dbt_utils.unique_combination_of_columns")
                                 or {}).get("combination_of_columns")
                        if combo:
                            t.grain = list(combo)

                meta = node.get("meta") or (node.get("config") or {}).get("meta") or {}
                spec = meta.get("sqlsure") or {}
                for mname, mspec in (spec.get("measures") or {}).items():
                    if isinstance(mspec, str):
                        t.measures[mname] = Measure(mname, mspec)
                    else:
                        t.measures[mname] = Measure(
                            mname, mspec.get("additivity", "additive"),
                            mspec.get("semi_additive_over"))
                t.sensitive |= set(spec.get("sensitive") or [])

                for col in node.get("columns") or []:
                    if not isinstance(col, dict):
                        continue
                    cname = col.get("name")
                    for test in _tests_of(col):
                        if test == "unique" and cname and cname not in t.grain:
                            t.grain.append(cname)
                        if isinstance(test, dict) and "relationships" in test:
                            rel = test["relationships"] or {}
                            ref = _REF_IN_YML.search(str(rel.get("to", "")))
                            field = rel.get("field")
                            if ref and field and cname:
                                parent = ref.group(1)
                                m.tables.setdefault(parent, Table(parent))
                                m.joins[(name, parent)] = Join(
                                    name, parent, MANY_TO_ONE, [(cname, field)])
    return m


def scan(repo: str, dialect: str | None = None) -> dict:
    root = Path(repo)
    manifest = next((p for p in root.rglob("target/manifest.json")
                     if "dbt_packages" not in p.parts), None)
    projects = [p.parent for p in root.rglob("dbt_project.yml")
                if "dbt_packages" not in p.parts]
    if not projects:
        projects = [root]

    if manifest:
        model, model_source = load_manifest(str(manifest)), f"manifest ({manifest})"
    else:
        model = SemanticModel()
        for proj in projects:
            sub = load_yaml_model(proj)
            model.tables.update(sub.tables)
            model.joins.update(sub.joins)
        model_source = f"schema .yml files ({len(projects)} project(s))"

    sql_files = []
    for proj in projects:
        models_dir = proj / "models"
        sql_files += sorted((models_dir if models_dir.exists() else proj).rglob("*.sql"))
    sql_files = [f for f in sql_files
                 if "dbt_packages" not in f.parts and "target" not in f.parts]

    results, skipped = [], []
    joins_total = joins_verifiable = joins_unknown = 0
    for f in sql_files:
        sql = strip_jinja(f.read_text())
        try:
            scopes = extract(sql, dialect=dialect)
            violations = check(sql, model, dialect=dialect)
        except Exception as e:
            skipped.append((f, str(e).splitlines()[0][:100]))
            continue
        for facts in scopes:
            for j in facts.joins:
                joins_total += 1
                known = (facts.base in model.tables and j.table in model.tables
                         and facts.base not in facts.cte_names
                         and j.table not in facts.cte_names)
                if known:
                    if model.edge(facts.base, j.table):
                        joins_verifiable += 1
                else:
                    joins_unknown += 1
        if violations:
            results.append((f, violations))

    with_grain = sum(1 for t in model.tables.values() if t.grain)
    return {
        "repo": str(root), "model_source": model_source, "dialect": dialect,
        "tables": len(model.tables), "with_grain": with_grain,
        "edges": len(model.joins),
        "files": len(sql_files), "parsed": len(sql_files) - len(skipped),
        "skipped": skipped, "results": results,
        "joins": (joins_total, joins_verifiable, joins_unknown),
    }


def to_markdown(s: dict) -> str:
    jt, jv, ju = s["joins"]
    by_rule: dict[str, int] = {}
    n_err = n_warn = n_pol = 0
    for _, vs in s["results"]:
        for v in vs:
            by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
            n_err += v.severity == "error"
            n_warn += v.severity == "warning"
            n_pol += v.severity == "policy"

    lines = [
        f"# sqlsure scan report — {s['repo']}",
        f"*{datetime.date.today()} · rulebook from {s['model_source']}"
        f" · dialect: {s['dialect'] or 'default'}*",
        "",
        "## Rulebook coverage",
        f"- models in rulebook: **{s['tables']}**, with declared grain: "
        f"**{s['with_grain']}** "
        f"({100 * s['with_grain'] // max(s['tables'], 1)}%)",
        f"- declared join edges: **{s['edges']}**",
        f"- joins seen in SQL: **{jt}** — verifiable: **{jv}**, between known "
        f"tables but undeclared: **{jt - jv - ju}**, involving unknown "
        f"tables/CTE output: **{ju}**",
        "",
        "## SQL scanned",
        f"- files: **{s['files']}**, parsed: **{s['parsed']}**, "
        f"skipped (jinja/parse): **{len(s['skipped'])}**",
        "",
        f"## Violations — {n_err} errors, {n_warn} warnings, {n_pol} policy",
    ]
    if by_rule:
        lines += ["", "| rule | count |", "|---|---|"]
        lines += [f"| {r} | {c} |"
                  for r, c in sorted(by_rule.items(), key=lambda x: -x[1])]
    lines.append("")
    for f, vs in s["results"][:60]:
        lines.append(f"### {f}")
        for v in vs:
            lines.append(f"- **[{v.severity}] {v.rule}** — {v.message}")
            if v.fix:
                lines.append(f"  - fix: {v.fix}")
        lines.append("")
    if s["skipped"]:
        lines.append("## Skipped files (best-effort jinja strip failed)")
        for f, err in s["skipped"][:30]:
            lines.append(f"- {f} — `{err}`")
        if len(s["skipped"]) > 30:
            lines.append(f"- … and {len(s['skipped']) - 30} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sqlsure scan-repo")
    p.add_argument("repo")
    p.add_argument("--dialect", default=None)
    p.add_argument("--report", default=None, help="write markdown report here")
    args = p.parse_args(argv)
    s = scan(args.repo, dialect=args.dialect)
    md = to_markdown(s)
    if args.report:
        Path(args.report).write_text(md)
        jt, jv, ju = s["joins"]
        print(f"scanned {s['parsed']}/{s['files']} files · "
              f"{s['tables']} models ({s['with_grain']} with grain) · "
              f"{s['edges']} edges · joins {jv}/{jt} verifiable · "
              f"{sum(len(v) for _, v in s['results'])} violations → {args.report}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
