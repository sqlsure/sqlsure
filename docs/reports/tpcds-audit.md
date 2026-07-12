# TPC-DS audit: 99 textbook OLAP queries, 0 false errors — and 4 checker bugs found on the way

*2026-07-11 · script: [`benchmarks/audit_tpcds.py`](../../benchmarks/audit_tpcds.py) · provoked by an HN comment*

## Why this exists

A Hacker News commenter argued the fan-out class shouldn't survive proper
dimensional design: "an OLAP table should be designed so that values can be
summed." Fair challenge, testable claim. TPC-DS is the canonical
star-schema benchmark — 24 tables, 17 dimensions, 99 expert-written,
decades-vetted queries. If sqlsure raises false alarms there, our approach
has a problem. If it stays quiet, that's the dimensional-SQL receipt we
lacked.

The rulebook was derived mechanically from the TPC-DS spec: dimension
surrogate keys → grain, fact composite keys → grain, the spec's rigid
`*_sk` FK naming → 82 many-to-one edges, returns→sales one-to-one edges.

## Result

| metric | value |
|---|---|
| statements checked | 99/99 (0 parse failures) |
| **hard errors (false alarms)** | **0** |
| soft warnings | 27 — reviewed below |

Warning review: 17 CROSS_JOIN softs ("no predicate *visible*") on joins
involving CTE/derived columns the rulebook cannot attribute — honest
can't-verify, most are intentional scalar-CTE joins; 6 FANOUT warnings on
COUNT after genuinely row-multiplying joins (q72's flagged join is the one
that famously makes it TPC-DS's slowest query — the warning text explains
both readings); 1 CHASM warning on q6's double 1:N chain (COUNT(*) there
counts join rows — arguably what the spec intends, hence warning not
error); 3 UNDECLARED_JOIN on paths with no declared edge (true).

## The real value: what this corpus caught in *us*

Dimensional SQL is stylistically hostile in ways OLTP benchmarks never
exposed. The first run produced **259 false errors**; each traced to a
checker bug, all four now fixed with regression tests:

1. **Unqualified comma joins** (`FROM store_sales, date_dim WHERE
   ss_sold_date_sk = d_date_sk` — no table prefixes): predicate detection
   needed qualified columns → 253 phantom CROSS_JOINs. Fix: resolve bare
   columns against the rulebook's known columns per in-scope table.
2. **Key-blind fan-out matching**: rules checked whether a 1:N edge
   *exists* between two tables, not whether the join *uses* its keys. In
   a dense graph (customer→date_dim via first-sales-date) this called
   safe many-to-one joins CHASM. Fix: cardinality is judged by the edge
   the join's own key columns traverse.
3. **Shared-FK transitive joins** (`cs_item_sk = inv_item_sk`, both FKs
   to item): flagged JOIN_KEY. Fix: two columns co-referencing the same
   dimension key are transitively equal — and treated as many-to-many
   for fan-out purposes, which is exactly q72's row-explosion shape.
4. **Self-joins** (`web_sales ws1, web_sales ws2 ON order_number`):
   read as predicate-less → phantom cartesian. Fix: recognized.

Also hardened: CROSS_JOIN softens to a warning when the predicate may
exist but involves columns the rulebook cannot attribute (CTE/derived);
CHASM's severity now follows the aggregates present (SUM/AVG → error,
COUNT-only → warning, none → silent); unqualified aggregate columns are
never guessed to belong to the base table.

Regressions: none — full test suite (32), the paired benchmark (100%
recall, 0 FP, 10/10 fixes), and the BIRD dev spot-check all unchanged.

## What this proves, honestly

- On the most textbook dimensional corpus available, expert-written OLAP
  SQL draws **zero false errors** — the "your checker will cry wolf on
  proper star schemas" objection is now tested, not argued.
- It does NOT prove dimensional design eliminates the bug class: TPC-DS
  queries are correct by construction. The bug-catching evidence lives in
  the [BIRD/Spider audits](bird-audit.md) (experts writing an answer key
  produced fan-outs, one proven wrong 8× by execution) and the
  [gate-vs-judge run](gate-vs-judge-experiment.md).
- Adversarial-corpus testing works: one skeptical HN comment → four
  fixed false-positive classes in a day.

Reproduce: `pip install duckdb && python benchmarks/audit_tpcds.py`
(exit code 0 = no hard errors).
