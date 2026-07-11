# What sqlsure does for you — with receipts

Every claim below links to a measurement you can rerun. Pick your seat at
the table.

## If you build a text-to-SQL / NL2SQL product

- **Your generator's fan-out mistakes never reach the warehouse.** The
  gate catches the "valid SQL, silently wrong number" class by lookup:
  100% recall, 0 false positives on the paired benchmark
  ([METRICS.md](METRICS.md)), 0 wrongly blocked queries on live agent
  drafts ([gate-vs-judge](reports/gate-vs-judge-experiment.md)).
- **One repair round instead of several.** Rejections carry a
  machine-actionable fix; applied verbatim it produced a passing query
  10/10 times ([METRICS.md](METRICS.md)).
- **It speaks your users' metadata already**: dbt tests, MetricFlow
  semantic models, WrenAI MDL, OSI (both spec shapes), PK/FK, live
  catalog introspection ([README](../README.md#where-the-rulebook-comes-from)).
  Integration is one function call around your generator
  ([integrations/semantic_gate.py](../integrations/semantic_gate.py)).

## If you run data/analytics for a company

- **Wrong numbers are expensive twice.** On real BIRD databases, the
  fan-out version of a loan-total query returned a result **271.9× too
  high** and did **~8,000× the row-work** (0.1 ms → 568 ms on the same
  engine) — work your warehouse bills for, on every scheduled refresh
  ([blog + queries](https://sqlsure.ai/blog/compute-bill-of-being-wrong/)).
- **And sometimes wrong is *cheap*** — a filter+multiply double bug ran
  *faster* than the correct query and returned 3.1× the true total. Cost
  monitoring can't catch this class; a cardinality check can.
- **Column policy runs on every query**: SENSITIVE_COLUMN flags
  PII/PHI-touching SQL before execution — deterministic, offline, no data
  ever read.

## If you build AI agents

- **The check is effectively free**: 0.7 ms median on live agent drafts,
  $0, zero tokens, same verdict every time. The LLM-as-judge alternative
  measured ~$0.03 and seconds per check (small-model prices) — and its
  only rejections in 44 checks were false alarms on correct queries
  ([gate-vs-judge](reports/gate-vs-judge-experiment.md)).
- **Agents can self-repair**: the MCP server's rejections include fix
  hints; the loop is draft → check → fix → check → execute
  ([MCP docs](MCP.md); registry: `io.github.sqlsure/sqlsure`).
- **No rulebook? No problem**: `sqlsure.introspect` builds one from the
  live database catalog — and doing so on BIRD's own databases recovered
  2 foreign keys missing from the benchmark's published schema
  ([bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37)).

## If you evaluate models or maintain benchmarks

- **A second axis next to execution accuracy**: semantic pass rate
  ([integrations/eval_metric.py](../integrations/eval_metric.py)).
- Auditing 2,568 Spider+BIRD gold queries produced 45 flags and 0
  spurious ones; one official gold answer was proven wrong by 8× by
  executing the benchmark's own database; 10 of 15 BIRD flags were
  independently confirmed by a later expert review
  ([spider](reports/spider-audit.md) · [bird](reports/bird-audit.md) ·
  [the story](https://sqlsure.ai/blog/bird-benchmark-wrong-gold/)).

## The waste argument (dollars, and watts)

Guardrail tokens that change no outcomes are pure waste — on every axis.
Using Google's published median for a Gemini text prompt (0.24 Wh, 0.26 mL
water, 0.03 gCO₂e per prompt, Aug 2025) as a *floor* — our measured judge
calls process ~23k tokens, well above a median prompt — replacing
judge-per-query with a deterministic gate at 10,000 checks/day saves at
minimum ~0.9 MWh and ~950 L of water per year, per deployment. Honestly
stated: that's modest for one company — the point is that it's **zero-value
compute**, and the same reasoning applies to the warehouse side, where the
fan-out class does 20×–8,000× measured extra row-work. Correctness and
efficiency are the same fix here.

## What it does not do (so you can trust the rest)

- It never generates SQL and never reads your data.
- It doesn't judge intent — a query that misreads the question but obeys
  the schema passes. That class needs human/LLM judgment (and is ~41% of
  benchmark questions per CIDR'24).
- Undeclared relationships come back "can't verify," never "looks fine."

Everything above is reproducible from this repository: the benchmark
(`benchmarks/benchmark.py`), the audits (`benchmarks/audit_*.py`), the
A/B harness (`benchmarks/experiment_gate_vs_judge.py`), and the fan-out
cost queries (in the blog post).
