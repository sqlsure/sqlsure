"""Semantic model: the constraint graph that SQL is checked against.

In production this is auto-extracted from a dbt manifest (see dbt_loader.py);
it can also be hand-written as JSON/dict (see SemanticModel.from_dict).
"""
from __future__ import annotations

from dataclasses import dataclass, field

ADDITIVE = "additive"
SEMI_ADDITIVE = "semi_additive"
NON_ADDITIVE = "non_additive"

MANY_TO_ONE = "many_to_one"
ONE_TO_ONE = "one_to_one"
ONE_TO_MANY = "one_to_many"
MANY_TO_MANY = "many_to_many"

_FLIP = {
    MANY_TO_ONE: ONE_TO_MANY,
    ONE_TO_MANY: MANY_TO_ONE,
    ONE_TO_ONE: ONE_TO_ONE,
    MANY_TO_MANY: MANY_TO_MANY,
}


@dataclass
class Measure:
    name: str
    additivity: str = ADDITIVE
    # for semi-additive measures (balances, censuses): the column the query
    # must keep in its grouping to sum safely
    semi_additive_over: str | None = None


@dataclass
class Table:
    name: str
    grain: list[str] = field(default_factory=list)
    measures: dict[str, Measure] = field(default_factory=dict)
    sensitive: set[str] = field(default_factory=set)


@dataclass
class Join:
    left: str
    right: str
    cardinality: str  # FROM left TO right
    keys: list[tuple[str, str]] = field(default_factory=list)  # (left_col, right_col)


@dataclass
class SemanticModel:
    tables: dict[str, Table] = field(default_factory=dict)
    joins: dict[tuple[str, str], Join] = field(default_factory=dict)

    def edge(self, a: str, b: str) -> Join | None:
        """Declared relationship between a and b, oriented a -> b."""
        j = self.joins.get((a, b))
        if j:
            return j
        j = self.joins.get((b, a))
        if j:
            return Join(a, b, _FLIP[j.cardinality], [(r, l) for l, r in j.keys])
        return None

    def owner_of(self, column: str) -> str | None:
        """Best-effort table for an unqualified column name."""
        for t in self.tables.values():
            if column in t.measures or column in t.grain or column in t.sensitive:
                return t.name
        return None

    def to_dict(self) -> dict:
        """Inverse of from_dict — export for review, editing, or storage."""
        tables: dict = {}
        for t in self.tables.values():
            spec: dict = {}
            if t.grain:
                spec["grain"] = list(t.grain)
            if t.measures:
                spec["measures"] = {
                    m.name: (m.additivity if m.semi_additive_over is None
                             else {"additivity": m.additivity,
                                   "semi_additive_over": m.semi_additive_over})
                    for m in t.measures.values()}
            if t.sensitive:
                spec["sensitive"] = sorted(t.sensitive)
            tables[t.name] = spec
        return {
            "tables": tables,
            "joins": [{"left": j.left, "right": j.right,
                       "cardinality": j.cardinality,
                       "keys": [list(k) for k in j.keys]}
                      for j in self.joins.values()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SemanticModel":
        # identifiers are lowercased: unquoted SQL identifiers are
        # case-insensitive, and the checker normalizes the same way
        m = cls()
        for name, spec in d.get("tables", {}).items():
            name = name.lower()
            grain = spec.get("grain", [])
            if isinstance(grain, str):
                grain = [grain]
            grain = [g.lower() for g in grain]
            measures: dict[str, Measure] = {}
            for mname, mspec in spec.get("measures", {}).items():
                mname = mname.lower()
                if isinstance(mspec, str):
                    measures[mname] = Measure(mname, mspec)
                else:
                    measures[mname] = Measure(
                        mname,
                        mspec.get("additivity", ADDITIVE),
                        mspec.get("semi_additive_over"),
                    )
            m.tables[name] = Table(name, grain, measures,
                                   {s.lower() for s in spec.get("sensitive", [])})
        for j in d.get("joins", []):
            left, right = j["left"].lower(), j["right"].lower()
            keys = [(a.lower(), b.lower()) for a, b in j.get("keys", [])]
            m.joins[(left, right)] = Join(left, right, j["cardinality"], keys)
        return m
