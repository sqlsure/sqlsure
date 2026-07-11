# sqlsure

[![CI](https://github.com/sqlsure/sqlsure/actions/workflows/ci.yml/badge.svg)](https://github.com/sqlsure/sqlsure/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlsure)](https://pypi.org/project/sqlsure/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/sqlsure)](https://pypi.org/project/sqlsure/)

**AI writes your SQL. sqlsure makes sure it's right.**

A query can be perfectly valid, run without error, and return a number
that's silently wrong — revenue double-counted by a join, an average
summed, a patient identifier exposed. Databases don't catch this.
Linters don't catch this. LLMs reviewing their own SQL don't catch this.

sqlsure does — deterministically, in 0.1 ms, before the query runs.

> **Proof, not promises:** we ran sqlsure over the gold answers of the two
> benchmarks every text-to-SQL model is graded on. **2,568 expert-written
> queries, 45 flags, zero false alarms** — including a BIRD dev gold answer
> that is [provably wrong by 8×](docs/reports/bird-audit.md) from the exact
> bug class sqlsure targets, and a schema defect
> [now filed upstream](https://github.com/bird-bench/mini_dev/issues/37).

## How it works

sqlsure judges SQL against facts your team already declared — dbt `unique`
tests become grain, `relationships` tests become join cardinality, one-line
`meta` tags mark what's safe to sum. No new language to learn, no model to
maintain by hand. Rules are dictionary lookups, not LLM calls: same input,
same verdict, every time, offline.

Every rejection carries a machine-actionable `fix`, so AI agents
self-repair: **draft → check → fix → check → execute.** In our benchmark,
applying the fix verbatim produced a passing query 10/10 times.

## Quick start

```bash
pip install sqlsure
```

```python
from sqlsure import SemanticModel, check
violations = check(sql, model)   # [] means semantically safe
```

Or clone and run the 30-second demo:

```bash
python check.py                   # 5 wrong queries rejected, 1 approved — with fixes
python -m sqlsure.scan path/to/dbt-repo --report report.md   # audit any dbt repo
```

## Three doors, one engine

**1. CI gate** — blocks the merge when a PR double-counts:

```bash
python -m sqlsure.cli --model model.json query.sql   # exit 1 on violations
```

**2. MCP server** — your AI agent must pass inspection before executing:

```bash
claude mcp add sqlsure -- python -m sqlsure.mcp_server --model /abs/path/model.json
```

See [docs/MCP.md](docs/MCP.md) for tool reference and agent-loop patterns.

**3. Library** — embed `check()` inside any text-to-SQL product or agent
framework. A drop-in [SemanticGate](integrations/semantic_gate.py) wraps
Vanna/WrenAI-style generators; a
[semantic eval metric](integrations/eval_metric.py) scores NL2SQL output
where execution-accuracy is blind.

## The rules (v0.1)

| Rule | Severity | Catches |
|---|---|---|
| FANOUT | error | SUM/COUNT of additive measure after one-to-many join |
| CHASM | error | two+ fan-out joins multiplying each other |
| ADDITIVITY | error | SUM of a non-additive measure (rates, averages) |
| SEMI_ADDITIVE | error | balances/censuses summed across their snapshot dimension |
| JOIN_KEY | error | join on columns matching no declared relationship |
| CROSS_JOIN | error | join with no predicate |
| WEIGHTED_AVG | warning | AVG silently re-weighted by fan-out |
| UNDECLARED_JOIN | warning | join with no declared relationship (unverifiable ≠ safe) |
| SENSITIVE_COLUMN | policy | PHI/PII column exposed in query output |

When sqlsure can't verify something, it says "can't verify" — never "looks
fine." Honest uncertainty is a feature.

## Trust properties

- **Deterministic** — same SQL + same rulebook = same verdict, always;
  rules are dictionary lookups, auditable line by line
- **Offline** — zero network calls; **your SQL never leaves your machine**
- **No data access** — parses query *text*; never connects to a database
- **No telemetry** — nothing collected, ever ([SECURITY.md](SECURITY.md))
- **Supply chain** — releases ship exclusively via PyPI Trusted Publishing
  (OIDC) from tagged commits with public CI runs; two runtime deps

## Where the rulebook comes from

- **dbt** (works today): `manifest.json` or `schema.yml` — the tests teams
  already wrote become enforceable semantics, zero config
- **Plain PK/FK declarations** (works today — powered the benchmark audits)
- **The live database itself** (works today): no semantic layer at all?
  `sqlsure.introspect` builds the rulebook from the catalog — SQLite
  PRAGMAs or `information_schema` PK/FK (postgres/mysql). Introspecting
  BIRD's own database files recovered 2 foreign keys missing from the
  benchmark's published schema
  ([bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37))

  ```python
  from sqlsure.introspect import model_from_sqlite
  model = model_from_sqlite("app.db")   # PK -> grain, FK -> join edges
  ```
- **Hand-written JSON** — [model.example.json](model.example.json)
- **OSI and WrenAI MDL** (working loaders in
  [integrations/](integrations/)): [OSI](integrations/osi_loader.py)
  demonstrated on the spec's published examples;
  [WrenAI MDL](integrations/mdl_loader.py) demonstrated on WrenAI's own
  shipped example manifest — `primaryKey` → grain, relationship
  `joinType` + `condition` → join edges, cube measures → additivity
- Cube, Snowflake Semantic Views — adapters on the roadmap; the
  engine only ever sees one `SemanticModel`

## Validated on

- **16/16 rule tests, 100% recall / 0% false positives** on the paired
  benchmark ([docs/METRICS.md](docs/METRICS.md))
- **Real production repos** (Mattermost's warehouse, Fivetran packages,
  dbt's jaffle shop) — [docs/TEST-REPORTS.md](docs/TEST-REPORTS.md)
- **Spider + BIRD gold queries** — the zero-noise external audit above

## Learn more

- [docs/EVIDENCE.md](docs/EVIDENCE.md) — what it does for you, every
  claim linked to a rerunnable measurement
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how it physically works,
  ELI5 → god level, with real intermediate outputs
- [docs/FOR-DUMMIES.md](docs/FOR-DUMMIES.md) — every concept from zero
- [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) — GitHub Action, pre-commit,
  MCP, Snowflake UDF / Cortex Agent tool, query-history audit
- [docs/MCP.md](docs/MCP.md) — MCP server documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) — adding rules and loaders

Apache-2.0 · [sqlsure.ai](https://sqlsure.ai)

<!-- mcp-name: io.github.sqlsure/sqlsure -->
mcp-name: io.github.sqlsure/sqlsure
