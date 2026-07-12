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
    # every equality pair in WHERE, tables possibly None (unqualified columns
    # — TPC-DS-style comma joins); resolved against the model in check()
    where_pairs: list[tuple[str | None, str, str | None, str]] = field(default_factory=list)
    # True when a WHERE equality had an unqualified column no in-scope table
    # is known to own (CTE/derived columns) — join predicates may exist that
    # the rulebook cannot see, so cross-join claims must soften
    unresolved_where: bool = False

    def tables_in_scope(self) -> list[str]:
        return [t for t in [self.base, *(j.table for j in self.joins)] if t]

    def owner(self, model: SemanticModel, table: str | None, column: str) -> str | None:
        """Resolve which model table a column belongs to."""
        if table and table in model.tables:
            return table
        if table:  # qualified to a CTE/unknown table — don't guess
            return None
        # unqualified: prefer the unique in-scope table known to own it
        candidates = [t for t in self.tables_in_scope()
                      if t in model.tables and column in _known_columns(model, t)]
        if len(candidates) == 1:
            return candidates[0]
        return model.owner_of(column)


def _known_columns(model: SemanticModel, table: str) -> set[str]:
    """Every column the rulebook associates with `table` — grain, measures,
    sensitive, and any join-key column on an edge touching it."""
    t = model.tables.get(table)
    if t is None:
        return set()
    cols = set(t.grain) | set(t.measures) | set(t.sensitive)
    for (l, r), j in model.joins.items():
        for lc, rc in j.keys:
            if l == table:
                cols.add(lc)
            if r == table:
                cols.add(rc)
    return cols


def _n(s: str | None) -> str | None:
    """Unquoted SQL identifiers are case-insensitive; models are lowercase."""
    return s.lower() if s else s


def _columns(node: exp.Expression, aliases: dict[str, str]) -> list[tuple[str | None, str]]:
    out = []
    for c in node.find_all(exp.Column):
        tbl = aliases.get(_n(c.table), _n(c.table)) if c.table else None
        out.append((tbl or None, _n(c.name)))
    return out


def _in_scope(node: exp.Expression, select: exp.Select) -> bool:
    return node.find_ancestor(exp.Select) is select


def _scope_facts(select: exp.Select, cte_names: set[str]) -> QueryFacts:
    aliases = {_n(t.alias_or_name): _n(t.name)
               for t in select.find_all(exp.Table) if _in_scope(t, select)}

    base = None
    frm = select.args.get("from_") or select.args.get("from")
    if frm is not None and isinstance(frm.this, exp.Table):
        base = _n(frm.this.name)

    # equality predicates in WHERE — old-style `FROM a, b WHERE a.id = b.id`
    # joins carry their key there instead of an ON clause
    where_pairs: list[tuple[str | None, str, str | None, str]] = []
    where = select.args.get("where")
    if where is not None:
        for eq in where.find_all(exp.EQ):
            l, r = eq.this, eq.expression
            if isinstance(l, exp.Column) and isinstance(r, exp.Column):
                lt = aliases.get(_n(l.table), _n(l.table)) if l.table else None
                rt = aliases.get(_n(r.table), _n(r.table)) if r.table else None
                where_pairs.append((lt, _n(l.name), rt, _n(r.name)))

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
                    pairs.append((_n(l.name), _n(r.name)))
        has_pred = on is not None or bool(j.args.get("using"))
        if not has_pred:
            jt = _n(j.this.name)
            for lt, lc, rt, rc in where_pairs:
                if jt in (lt, rt) and lt != rt:
                    pairs.append((lc, rc))
                    has_pred = True
        joins.append(QueryJoin(_n(j.this.name), pairs, has_pred))

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

    return QueryFacts(base, joins, aggregates, group_by, selected, cte_names,
                      where_pairs=where_pairs)


def extract(sql: str, dialect: str | None = None) -> list[QueryFacts]:
    """One QueryFacts per SELECT scope (outer query, CTEs, subqueries)."""
    tree = sqlglot.parse_one(sql, read=dialect)
    cte_names = {_n(c.alias) for c in tree.find_all(exp.CTE)}
    return [_scope_facts(s, cte_names) for s in tree.find_all(exp.Select)]


def _resolve_comma_joins(facts: QueryFacts, model: SemanticModel) -> None:
    """Old-style `FROM a, b WHERE x = y` joins with UNQUALIFIED columns
    (TPC-DS style — column names globally unique) leave joins predicate-less
    at extraction time, because resolving a bare column to a table needs the
    rulebook. Do that resolution now: a pair joins tables A and B when each
    side's column is known (grain/measure/sensitive/edge key) to exactly one
    in-scope table."""
    in_scope = [t for t in facts.tables_in_scope()
                if t in model.tables and t not in facts.cte_names]
    known = {t: _known_columns(model, t) for t in in_scope}

    def resolve(tbl: str | None, col: str) -> str | None:
        if tbl:
            return tbl
        cands = [t for t in in_scope if col in known[t]]
        return cands[0] if len(cands) == 1 else None

    for lt, lc, rt, rc in facts.where_pairs:
        if (lt is None and resolve(lt, lc) is None) or \
                (rt is None and resolve(rt, rc) is None):
            facts.unresolved_where = True
            break

    for j in facts.joins:
        if j.has_predicate:
            continue
        for lt, lc, rt, rc in facts.where_pairs:
            a, b = resolve(lt, lc), resolve(rt, rc)
            if a and a == b == j.table:
                # self-join (two aliases of one table) — the pair IS the
                # predicate, though key verification doesn't apply
                j.has_predicate = True
                continue
            if a and b and a != b and j.table in (a, b):
                pair = (lc, rc) if j.table == b else (rc, lc)
                # orient as (other-side col, joined-table col)? rules compare
                # unordered against edge keys; keep extraction convention
                if (lc, rc) not in j.on_pairs and (rc, lc) not in j.on_pairs:
                    j.on_pairs.append((lc, rc) if b == j.table else (rc, lc))
                j.has_predicate = True


def check(sql: str, model: SemanticModel, dialect: str | None = None) -> list[Violation]:
    """The inspector: returns [] if the query is semantically safe."""
    from .rules import RULES
    violations: list[Violation] = []
    seen: set[tuple[str, str]] = set()
    for facts in extract(sql, dialect=dialect):
        _resolve_comma_joins(facts, model)
        for rule in RULES:
            for v in rule(facts, model):
                key = (v.rule, v.message)
                if key not in seen:
                    seen.add(key)
                    violations.append(v)
    order = {"error": 0, "policy": 1, "warning": 2}
    violations.sort(key=lambda v: order.get(v.severity, 3))
    return violations
