# Contributing to sqlsure

Thanks for your interest! sqlsure is a semantic inspector for SQL — it
judges queries against declared semantics (grain, additivity, join
cardinality, policy) and never generates SQL.

## Ground rules

- **Determinism is sacred.** Rules are dictionary lookups + conditionals.
  No network calls, no LLM calls, no reading actual data inside the engine.
- **"Can't verify" ≠ "safe."** Rules only fire on declared facts; when the
  rulebook is silent, emit nothing or an honest warning — never guess.
- **False positives are the enemy.** A new rule needs both a firing test
  AND a near-miss test that must stay silent (see `tests/run_tests.py` and
  the clean set in `benchmarks/benchmark.py`).

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tests/run_tests.py          # 16 tests, must stay green
python benchmarks/benchmark.py     # recall/FP gate, must stay 100%/0%
```

## Adding a rule

1. Write the rule in `sqlsure/rules.py` with the `@rule` decorator —
   signature `fn(facts, model) -> list[Violation]`.
2. Every Violation needs a `fix` string an AI agent could apply verbatim.
3. Add a firing test and a near-miss test to `tests/run_tests.py`, and a
   buggy/clean/repaired triple to `benchmarks/benchmark.py`.
4. Run the two commands above; both gates must pass.

## Adding a rulebook loader (Cube, OSI, Snowflake, …)

Loaders convert an external format into `SemanticModel` (grain,
additivity, cardinality, policy) — see `sqlsure/dbt_loader.py` (~90 lines)
as the template. Loaders may not change the engine.

## Reporting real-world findings

Found a wrong-number bug sqlsure caught (or missed) on real SQL? Open an
issue with the minimal query + the relevant declared facts — anonymized.
Misses are especially valuable.
