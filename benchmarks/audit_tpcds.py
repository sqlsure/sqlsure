"""Audit the 99 official TPC-DS queries — textbook dimensional (OLAP) SQL.

Provoked by an HN comment ("OLAP tables are designed to be summed; show me
this matters there"): TPC-DS is the canonical star-schema benchmark, its
queries are expert-written and decades-vetted, so it is the best available
false-positive stress test for dimensional SQL — 17 dimensions, dense edge
graph, old-style comma joins with unqualified columns, self-joins,
shared-dimension fact-to-fact joins. Exactly the shapes that break naive
checkers.

The rulebook is derived mechanically from the TPC-DS specification:
  - dimension PK = its surrogate key (d_date_sk, i_item_sk, ...)
  - fact PKs = the spec's composite keys (ss_item_sk+ss_ticket_number, ...)
  - FK edges by the spec's rigid *_sk suffix convention
  - returns->sales edges on (item, ticket/order), one-to-one per spec

Run:  python benchmarks/audit_tpcds.py         (needs `pip install duckdb`)
"""
from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.checker import check  # noqa: E402
from sqlsure.model import (  # noqa: E402
    MANY_TO_ONE, ONE_TO_ONE, Join, SemanticModel, Table,
)

FACT_PK = {
    "store_sales": ["ss_item_sk", "ss_ticket_number"],
    "store_returns": ["sr_item_sk", "sr_ticket_number"],
    "catalog_sales": ["cs_item_sk", "cs_order_number"],
    "catalog_returns": ["cr_item_sk", "cr_order_number"],
    "web_sales": ["ws_item_sk", "ws_order_number"],
    "web_returns": ["wr_item_sk", "wr_order_number"],
    "inventory": ["inv_date_sk", "inv_item_sk", "inv_warehouse_sk"],
}
DIM_PK = {
    "date_dim": "d_date_sk", "time_dim": "t_time_sk", "item": "i_item_sk",
    "customer": "c_customer_sk", "customer_demographics": "cd_demo_sk",
    "household_demographics": "hd_demo_sk", "customer_address": "ca_address_sk",
    "store": "s_store_sk", "warehouse": "w_warehouse_sk",
    "promotion": "p_promo_sk", "web_page": "wp_web_page_sk",
    "web_site": "web_site_sk", "call_center": "cc_call_center_sk",
    "catalog_page": "cp_catalog_page_sk", "ship_mode": "sm_ship_mode_sk",
    "reason": "r_reason_sk", "income_band": "ib_income_band_sk",
}
SUFFIX = {  # FK column suffix -> (dimension, its PK); longest suffix wins
    "call_center_sk": ("call_center", "cc_call_center_sk"),
    "catalog_page_sk": ("catalog_page", "cp_catalog_page_sk"),
    "web_page_sk": ("web_page", "wp_web_page_sk"),
    "web_site_sk": ("web_site", "web_site_sk"),
    "ship_mode_sk": ("ship_mode", "sm_ship_mode_sk"),
    "income_band_sk": ("income_band", "ib_income_band_sk"),
    "warehouse_sk": ("warehouse", "w_warehouse_sk"),
    "customer_sk": ("customer", "c_customer_sk"),
    "cdemo_sk": ("customer_demographics", "cd_demo_sk"),
    "hdemo_sk": ("household_demographics", "hd_demo_sk"),
    "addr_sk": ("customer_address", "ca_address_sk"),
    "store_sk": ("store", "s_store_sk"),
    "promo_sk": ("promotion", "p_promo_sk"),
    "reason_sk": ("reason", "r_reason_sk"),
    "date_sk": ("date_dim", "d_date_sk"),
    "time_sk": ("time_dim", "t_time_sk"),
    "item_sk": ("item", "i_item_sk"),
}
RETURNS = [
    ("store_returns", "store_sales",
     [("sr_item_sk", "ss_item_sk"), ("sr_ticket_number", "ss_ticket_number")]),
    ("catalog_returns", "catalog_sales",
     [("cr_item_sk", "cs_item_sk"), ("cr_order_number", "cs_order_number")]),
    ("web_returns", "web_sales",
     [("wr_item_sk", "ws_item_sk"), ("wr_order_number", "ws_order_number")]),
]


def build_model(con) -> SemanticModel:
    cols: dict[str, list[str]] = {}
    for t, c in con.execute(
            "SELECT table_name, column_name FROM information_schema.columns"
    ).fetchall():
        cols.setdefault(t, []).append(c.lower())

    m = SemanticModel()
    for t in cols:
        grain = FACT_PK.get(t) or ([DIM_PK[t]] if t in DIM_PK else [])
        m.tables[t] = Table(t, grain=list(grain))
    for t, cl in cols.items():
        for c in cl:
            if c == DIM_PK.get(t):
                continue
            for suf in sorted(SUFFIX, key=len, reverse=True):
                if c.endswith(suf):
                    dim, dpk = SUFFIX[suf]
                    if dim == t:
                        break
                    e = m.joins.get((t, dim))
                    if e:
                        if (c, dpk) not in e.keys:
                            e.keys.append((c, dpk))
                    else:
                        m.joins[(t, dim)] = Join(t, dim, MANY_TO_ONE, [(c, dpk)])
                    break
    for ret, sale, keys in RETURNS:
        m.joins[(ret, sale)] = Join(ret, sale, ONE_TO_ONE, keys)
    return m


def main() -> int:
    import duckdb

    con = duckdb.connect(":memory:")
    con.execute("INSTALL tpcds; LOAD tpcds;")
    con.execute("CALL dsdgen(sf=0)")  # schema only
    model = build_model(con)
    print(f"rulebook: {len(model.tables)} tables, {len(model.joins)} edges "
          f"(spec-derived)")

    parsed = failed = 0
    errors, warns = [], []
    by_rule: Counter = Counter()
    for nr, q in con.execute(
            "SELECT query_nr, query FROM tpcds_queries()").fetchall():
        for stmt in [x for x in q.split(";") if x.strip()]:
            try:
                vs = check(stmt, model, dialect="duckdb")
                parsed += 1
            except Exception:
                failed += 1
                continue
            for v in vs:
                by_rule[f"{v.rule}/{v.severity}"] += 1
                bucket = errors if v.severity in ("error", "policy") else warns
                bucket.append((nr, v.rule, v.message))

    print(f"statements parsed: {parsed}, parse failures: {failed}")
    print(f"findings: {dict(by_rule) or 'NONE'}")
    print(f"\nhard errors: {len(errors)}")
    for nr, r, msg in errors:
        print(f"  q{nr}: {r} — {msg[:110]}")
    print(f"warnings (honest can't-verify + soft flags): {len(warns)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
