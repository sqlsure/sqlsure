"""The rulebook: each rule inspects query facts against the semantic model.

Every violation carries a machine-readable `fix` hint so an AI agent can
self-repair the query and re-submit — the check is designed to close the loop,
not just reject.
"""
from __future__ import annotations

from .checker import QueryFacts, Violation
from .model import (
    ADDITIVE, NON_ADDITIVE, SEMI_ADDITIVE,
    ONE_TO_MANY, MANY_TO_MANY,
    SemanticModel,
)

RULES = []


def rule(fn):
    RULES.append(fn)
    return fn


def _fanout_joins(facts: QueryFacts, model: SemanticModel) -> list[str]:
    """Joined tables that multiply the base table's rows."""
    if not facts.base or facts.base in facts.cte_names:
        return []
    out = []
    for j in facts.joins:
        if j.table in facts.cte_names:
            continue  # CTE output shadowing a model name — grain unknown
        edge = model.edge(facts.base, j.table)
        if edge and edge.cardinality in (ONE_TO_MANY, MANY_TO_MANY):
            out.append(j.table)
    return out


def _measure(facts: QueryFacts, model: SemanticModel, agg):
    if agg.column is None:
        return None, None
    owner = facts.owner(model, agg.table, agg.column)
    table = model.tables.get(owner) if owner else None
    if table is None:
        return owner, None
    return owner, table.measures.get(agg.column)


@rule
def fanout(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """SUM/COUNT of an additive measure after a row-multiplying join."""
    fans = _fanout_joins(facts, model)
    if not fans:
        return []
    out = []
    grain = ", ".join(model.tables[facts.base].grain) if facts.base in model.tables else "base grain"
    for agg in facts.aggregates:
        if agg.distinct:
            continue
        if agg.func == "COUNT":
            # warning, not error: counting the joined side's rows is often
            # intended — only counting base rows is inflated
            what = f"COUNT({agg.column})" if agg.column else "COUNT(*)"
            out.append(Violation(
                "FANOUT", "warning",
                f"{what} after one-to-many join to {fans} — this counts "
                f"{fans[0]} rows, not {facts.base} rows. If you meant to "
                f"count {facts.base}, the result is inflated.",
                f"To count {facts.base}, use COUNT(DISTINCT {grain}); to count "
                f"{fans[0]} rows, this query is fine as written."))
        elif agg.func == "SUM":
            owner, m = _measure(facts, model, agg)
            if m and m.additivity == ADDITIVE and owner == facts.base:
                out.append(Violation(
                    "FANOUT", "error",
                    f"SUM({agg.column}) after one-to-many join to {fans} — "
                    f"{agg.column} will be double-counted.",
                    f"Pre-aggregate {facts.base} to [{grain}] in a CTE before "
                    f"joining {fans}."))
            elif m is None and owner == facts.base:
                # additivity undeclared (e.g. rulebook introspected from
                # PK/FK only) — the join still repeats base rows, so the
                # sum is inflated whenever the column is a per-row amount
                out.append(Violation(
                    "FANOUT", "warning",
                    f"SUM({agg.column}) after one-to-many join to {fans} — "
                    f"{facts.base} rows repeat, so the sum is inflated if "
                    f"{agg.column} is a per-row amount (additivity not "
                    f"declared).",
                    f"Pre-aggregate {facts.base} to [{grain}] in a CTE before "
                    f"joining {fans}, or declare {agg.column}'s additivity "
                    f"to make this check exact."))
    return out


@rule
def chasm(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """Two or more fan-out joins multiply each other (chasm trap)."""
    fans = _fanout_joins(facts, model)
    if len(fans) < 2:
        return []
    return [Violation(
        "CHASM", "error",
        f"Multiple one-to-many joins ({fans}) from {facts.base} — row "
        f"multiplication is the product of both fan-outs; every aggregate in "
        f"this query is unreliable.",
        "Aggregate each one-to-many branch to the base grain in its own CTE, "
        "then join the pre-aggregated results.")]


@rule
def additivity(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """SUM of a measure that is never summable (rates, averages, percentiles)."""
    out = []
    for agg in facts.aggregates:
        if agg.func != "SUM":
            continue
        owner, m = _measure(facts, model, agg)
        if m and m.additivity == NON_ADDITIVE:
            grain = ", ".join(model.tables[owner].grain) if owner in model.tables else "declared grain"
            out.append(Violation(
                "ADDITIVITY", "error",
                f"SUM({agg.column}) is invalid — {agg.column} is non-additive.",
                f"Use AVG/MEDIAN at [{grain}] grain, or recompute from the "
                f"underlying additive components."))
    return out


@rule
def semi_additivity(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """SUM of a balance/census-style measure across its snapshot dimension."""
    out = []
    grouped = {c for _, c in facts.group_by}
    for agg in facts.aggregates:
        if agg.func != "SUM":
            continue
        owner, m = _measure(facts, model, agg)
        if m and m.additivity == SEMI_ADDITIVE and m.semi_additive_over \
                and m.semi_additive_over not in grouped:
            out.append(Violation(
                "SEMI_ADDITIVE", "error",
                f"SUM({agg.column}) across {m.semi_additive_over} — "
                f"{agg.column} is a point-in-time measure; summing it over "
                f"time double-counts the same units.",
                f"Keep {m.semi_additive_over} in GROUP BY, or take the "
                f"latest/average snapshot per period instead of SUM."))
    return out


@rule
def avg_after_fanout(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """AVG of a base-table measure after fan-out is silently re-weighted."""
    fans = _fanout_joins(facts, model)
    if not fans:
        return []
    out = []
    for agg in facts.aggregates:
        if agg.func != "AVG":
            continue
        owner, m = _measure(facts, model, agg)
        if m and owner == facts.base:
            out.append(Violation(
                "WEIGHTED_AVG", "warning",
                f"AVG({agg.column}) after one-to-many join to {fans} — rows "
                f"with more matches weigh more, silently biasing the mean.",
                f"Compute AVG({agg.column}) at {facts.base} grain before joining."))
    return out


@rule
def join_keys(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """Join uses different columns than the declared relationship keys."""
    out = []
    if not facts.base or facts.base in facts.cte_names:
        return out
    # a join may legitimately key off ANY table in the query, not just the
    # base (multi-hop: posts -> badges -> users), so collect every declared
    # edge between the joined table and any in-scope table
    in_scope = [facts.base] + [x.table for x in facts.joins]
    for j in facts.joins:
        if j.table in facts.cte_names or not j.on_pairs:
            continue
        declared: set = set()
        edges = []
        for other in in_scope:
            if other == j.table or other in facts.cte_names:
                continue
            edge = model.edge(other, j.table)
            if edge and edge.keys:
                edges.append(edge)
                declared |= {frozenset(k) for k in edge.keys}
        if not declared:
            continue
        used = {frozenset(p) for p in j.on_pairs}
        if not (declared & used):
            exp_keys = "; ".join(
                f"{e.left}->{e.right} on " +
                ", ".join(f"{l} = {r}" for l, r in e.keys) for e in edges)
            got = ", ".join(f"{a} = {b}" for a, b in j.on_pairs)
            out.append(Violation(
                "JOIN_KEY", "error",
                f"Join to {j.table} on ({got}) does not match any declared "
                f"relationship key ({exp_keys}).",
                f"Join {j.table} using one of the declared keys: {exp_keys}."))
    return out


@rule
def undeclared_join(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """Join between tables with no declared relationship — unmodeled path."""
    out = []
    for j in facts.joins:
        # only when both sides are known model tables — joins to CTEs or
        # tables outside the model can't be judged (CTE names shadow models)
        if (facts.base in model.tables and j.table in model.tables
                and facts.base not in facts.cte_names
                and j.table not in facts.cte_names
                and model.edge(facts.base, j.table) is None):
            out.append(Violation(
                "UNDECLARED_JOIN", "warning",
                f"No declared relationship between {facts.base} and {j.table} — "
                f"cardinality is unknown, so aggregates cannot be verified.",
                f"Declare the join (cardinality + keys) in the semantic model, "
                f"or route through a declared path."))
    return out


@rule
def cross_join(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """Join with no predicate = cartesian product."""
    return [Violation(
        "CROSS_JOIN", "error",
        f"Join to {j.table} has no join predicate — cartesian product.",
        f"Add an ON clause using the declared keys for {j.table}.")
        for j in facts.joins if not j.has_predicate]


@rule
def sensitive_columns(facts: QueryFacts, model: SemanticModel) -> list[Violation]:
    """Selecting a column marked restricted (e.g. PHI/PII) — policy gate."""
    out, seen = [], set()
    for tbl, col in facts.selected + facts.group_by:
        owner = facts.owner(model, tbl, col)
        t = model.tables.get(owner) if owner else None
        if t and col in t.sensitive and (owner, col) not in seen:
            seen.add((owner, col))
            out.append(Violation(
                "SENSITIVE_COLUMN", "policy",
                f"{owner}.{col} is marked sensitive (PHI/PII) — this query "
                f"exposes it in its output.",
                f"Drop {col}, or aggregate/pseudonymize it; request access "
                f"through governance if it is genuinely required."))
    return out
