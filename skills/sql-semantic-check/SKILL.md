---
name: sql-semantic-check
description: Check SQL for silent semantic errors (fan-out double-counting, unsafe sums, wrong join keys, sensitive columns) BEFORE executing it against a database. Use whenever you are about to run a SELECT you or another model wrote — especially aggregates over joins. Deterministic, offline, ~0.1 ms per check.
---

# SQL semantic check (sqlsure)

Validate a SQL query against declared schema facts before execution. The
check is a lookup, not an LLM call: same input, same verdict, no tokens.

## Setup (once per session)

```bash
pip install sqlsure
```

## Get a rulebook (pick the first that applies)

1. **dbt project available** → use its manifest directly in step "Check".
2. **SQLite database available** → introspect it (PKs → grain, FKs → join
   cardinality):
   ```bash
   python -c "
   from sqlsure.introspect import model_from_sqlite
   import json
   json.dump(model_from_sqlite('PATH.db').to_dict(), open('model.json','w'))"
   ```
3. **Postgres/MySQL** → `sqlsure.introspect.model_from_information_schema(cursor)`.
4. **None of the above** → write a minimal `model.json` for the tables you
   are querying (see `model.example.json` in the repo): each table's grain
   (unique key), join edges with cardinality, and which measures are safe
   to sum.

## Check

```bash
python -m sqlsure.cli --model model.json query.sql        # or --manifest target/manifest.json
```

Or in Python:

```python
from sqlsure import SemanticModel, check
import json
model = SemanticModel.from_dict(json.load(open("model.json")))
violations = check(sql, model)   # [] means approved
```

## Act on the verdict

- **No violations** → execute the query.
- **error / policy** → do NOT execute. Each violation has a `fix` field
  with a concrete rewrite instruction (e.g. "pre-aggregate orders to
  [order_id] in a CTE before joining order_items"). Apply it, re-check,
  and only execute once clean.
- **warning** → execution is allowed but surface the warning to the user
  verbatim; it usually means "this join multiplies rows and your COUNT
  may not count what you think" or "this relationship is undeclared, so
  the result cannot be verified."

Never suppress an error by editing the rulebook to match the query.
