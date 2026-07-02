"""Parse SQL into per-scope query facts and run every rule against the model.

Every SELECT scope — the outer query, each CTE, each subquery — is checked
independently, so violations buried inside a mart's CTE pipeline are caught.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from .model import SemanticModel


@dataclass
class Violation:
    rule: str
    severity: str  # "error" | "warning" | "policy"
    message: str
    fix: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity,
                "message": self.message, "fix": self.fix}


@dataclass
class Aggregate:
    func: str                 # SUM / AVG / COUNT / ...
    column: str | None        # None for COUNT(*)
    table: str | None         # resolved table, if the column was qualified
    distinct: bool = False


@dataclass
class QueryJoin:
    table: str
    # column-name pairs from equality predicates in the ON clause
    on_pairs: list[tuple[str, str]] = field(default_factory=list)
    has_predicate: bool = True


@dataclass
class QueryFacts:
    base: str | None
    joins: list[QueryJoin]
    aggregates: list[Aggregate]
    group_by: list[tuple[str | None, str]]   # (resolved table, column)
    selected: list[tuple[str | None, str]]
    cte_names: set[str] = field(default_factory=set)

    def owner(self, model: SemanticModel, table: str | None, column: str) -> str | None:
        """Resolve which model table a column belongs to."""
        if table and table in model.tables:
            return table
        if table:  # qualified to a CTE/unknown table — don't guess
            return None
        return model.owner_of(column) or self.base


def _columns(node: exp.Expression, aliases: dict[str, str]) -> list[tuple[str | None, str]]:
    out = []
    for c in node.find_all(exp.Column):
        tbl = aliases.get(c.table, c.table) if c.table else None
        out.append((tbl or None, c.name))
    return out


def _in_scope(node: exp.Expression, select: exp.Select) -> bool:
    return node.find_ancestor(exp.Select) is select


def _scope_facts(select: exp.Select, cte_names: set[str]) -> QueryFacts:
    aliases = {t.alias_or_name: t.name
               for t in select.find_all(exp.Table) if _in_scope(t, select)}

    base = None
    frm = select.args.get("from_") or select.args.get("from")
    if frm is not None and isinstance(frm.this, exp.Table):
        base = frm.this.name

    # equality predicates in WHERE — old-style `FROM a, b WHERE a.id = b.id`
    # joins carry their key there instead of an ON clause
    where_pairs: list[tuple[str | None, str, str | None, str]] = []
    where = select.args.get("where")
    if where is not None:
        for eq in where.find_all(exp.EQ):
            l, r = eq.this, eq.expression
            if isinstance(l, exp.Column) and isinstance(r, exp.Column):
                lt = aliases.get(l.table, l.table) if l.table else None
                rt = aliases.get(r.table, r.table) if r.table else None
                where_pairs.append((lt, l.name, rt, r.name))

    joins: list[QueryJoin] = []
    for j in select.find_all(exp.Join):
        if not _in_scope(j, select) or not isinstance(j.this, exp.Table):
            continue
        on = j.args.get("on")
        pairs = []
        if on is not None:
            for eq in on.find_all(exp.EQ):
                l, r = eq.this, eq.expression
                if isinstance(l, exp.Column) and isinstance(r, exp.Column):
                    pairs.append((l.name, r.name))
        has_pred = on is not None or bool(j.args.get("using"))
        if not has_pred:
            jt = j.this.name
            for lt, lc, rt, rc in where_pairs:
                if jt in (lt, rt) and lt != rt:
                    pairs.append((lc, rc))
                    has_pred = True
        joins.append(QueryJoin(j.this.name, pairs, has_pred))

    aggregates: list[Aggregate] = []
    for node in select.find_all(exp.AggFunc):
        if not _in_scope(node, select):
            continue
        func = node.key.upper()
        arg = node.this
        distinct = isinstance(arg, exp.Distinct)
        if distinct:
            arg = arg.expressions[0] if arg.expressions else None
        if arg is None or isinstance(arg, exp.Star):
            aggregates.append(Aggregate(func, None, None, distinct))
            continue
        cols = _columns(arg, aliases)
        if not cols:
            aggregates.append(Aggregate(func, None, None, distinct))
        for tbl, col in cols:
            aggregates.append(Aggregate(func, col, tbl, distinct))

    group_by: list[tuple[str | None, str]] = []
    group = select.args.get("group")
    if group is not None:
        selects = getattr(select, "selects", [])
        for e in group.expressions:
            if isinstance(e, exp.Literal) and e.is_int:  # GROUP BY 1
                idx = int(e.this) - 1
                if 0 <= idx < len(selects):
                    e = selects[idx]
            group_by.extend(_columns(e, aliases))

    selected: list[tuple[str | None, str]] = []
    for e in getattr(select, "selects", []):
        selected.extend(_columns(e, aliases))

    return QueryFacts(base, joins, aggregates, group_by, selected, cte_names)


def extract(sql: str, dialect: str | None = None) -> list[QueryFacts]:
    """One QueryFacts per SELECT scope (outer query, CTEs, subqueries)."""
    tree = sqlglot.parse_one(sql, read=dialect)
    cte_names = {c.alias for c in tree.find_all(exp.CTE)}
    return [_scope_facts(s, cte_names) for s in tree.find_all(exp.Select)]


def check(sql: str, model: SemanticModel, dialect: str | None = None) -> list[Violation]:
    """The inspector: returns [] if the query is semantically safe."""
    from .rules import RULES
    violations: list[Violation] = []
    seen: set[tuple[str, str]] = set()
    for facts in extract(sql, dialect=dialect):
        for rule in RULES:
            for v in rule(facts, model):
                key = (v.rule, v.message)
                if key not in seen:
                    seen.add(key)
                    violations.append(v)
    order = {"error": 0, "policy": 1, "warning": 2}
    violations.sort(key=lambda v: order.get(v.severity, 3))
    return violations
