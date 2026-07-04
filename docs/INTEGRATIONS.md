# sqlsure Integration Cookbook — physically, with the actual files

*Every integration answers the same question — "how does the SQL string
reach `check()` and how does the verdict get back?" — with a different
transport. For each: where your agent/author lives, the exact files or DDL
involved, and what physically happens at runtime.*

## The decision table (start here)

| Where does the SQL author live? | Use this door | Status |
|---|---|---|
| Engineers committing to a dbt repo | **GitHub Action / pre-commit** | recipe below, works today |
| Claude / Cursor / any MCP client writing SQL | **MCP server** | built, works today |
| Your own Python app / text-to-SQL product | **library import** | built, works today |
| **Snowflake Cortex Agent** (agent lives *inside* Snowflake) | **Python UDF registered as a custom agent tool** | recipe below |
| Nothing live — audit what already ran | **UDF over query history** | recipe below |

The same engine sits behind every door. MCP does **not** reach a Cortex
Agent directly — MCP is for agents *outside* the warehouse (Claude,
Cursor); an agent *inside* Snowflake calls tools that live inside
Snowflake, which is what the UDF is for. Both are below.

---

## Recipe 1 — On commit: GitHub Action (the CI gate)

**The files.** Your repo gains exactly one file:

`.github/workflows/sqlsure.yml`
```yaml
name: sqlsure
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install sqlsure
      - run: python -m sqlsure.scan . --report sqlsure-report.md
      - run: python -m sqlsure.cli --model model.json changed_model.sql  # exit 1 blocks merge
```

**What physically happens:** engineer pushes → GitHub spins up a Linux VM
→ `checkout` puts the repo's files on that VM's disk (SQL is now Habitat
1) → `sqlsure.scan` walks `models/**/*.sql`, strips Jinja, checks each →
prints violations → **the process exit code (0/1) is the entire
integration** — GitHub paints the PR red on exit 1. A comment-posting step
(via `gh pr comment`) turns the report into inline review comments.

**Pre-commit variant** (catches it before the push even happens) —
`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: sqlsure
        name: sqlsure semantic check
        entry: python -m sqlsure.cli --model model.json
        language: system
        files: \.sql$
```
Physically: git intercepts `git commit`, runs the command on staged `.sql`
files, nonzero exit aborts the commit on the engineer's own laptop.

---

## Recipe 2 — MCP: Claude / Cursor / any external agent (works today)

**The file.** One entry in the client's MCP config (Claude Code shown;
Cursor's `mcp.json` is the same shape):

```bash
claude mcp add sqlsure -- python -m sqlsure.mcp_server --model /abs/path/model.json
```

**What physically happens:** the client launches our Python process and
keeps it alive, connected by two pipes (stdin/stdout). When the agent
drafts SQL, the client writes a JSON-RPC message into our stdin:

```json
{"method":"tools/call","params":{"name":"check_sql",
 "arguments":{"sql":"SELECT SUM(f.cost) FROM ..."}}}
```

We parse the string, run `check()`, write the verdict JSON back to stdout.
The server's instructions field tells the agent: *check every query before
executing; if not approved, apply each fix and re-check.* The SQL never
touches disk; the whole loop is inter-process pipes on one machine.

---

## Recipe 3 — Snowflake: the UDF (the engine *inside* the warehouse)

sqlsure is pure Python with one dependency (sqlglot), which makes it
UDF-packable. **The DDL** (run once by an admin):

```sql
CREATE OR REPLACE FUNCTION SQLSURE_CHECK(sql_text STRING, model STRING)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('sqlglot')            -- in Snowflake's Anaconda channel;
                                  -- if version-pinned, upload a zip via IMPORTS instead
HANDLER = 'run'
AS $$
import json
from sqlsure.checker import check          # sqlsure shipped via IMPORTS zip
from sqlsure.model import SemanticModel

def run(sql_text, model):
    m = SemanticModel.from_dict(json.loads(model))
    vs = check(sql_text, m)
    return {"approved": not any(v.severity in ("error","policy") for v in vs),
            "violations": [v.to_dict() for v in vs]}
$$;
```

(The `sqlsure` package itself is attached with
`IMPORTS = ('@my_stage/sqlsure.zip')` — a zip of the `sqlsure/` folder uploaded to
a stage. ~30 KB.)

**What physically happens on a call:**

```sql
SELECT SQLSURE_CHECK(
  'SELECT p.patient_id, SUM(f.cost) FROM fct_encounters f JOIN dim_diagnosis d ON ...',
  (SELECT model_json FROM sqlsure_config)      -- rulebook stored in a table
);
-- → {"approved": false, "violations":[{"rule":"FANOUT", ...}]}
```

Snowflake runs our Python inside its sandboxed UDF runtime, in-warehouse,
no network egress. The rulebook JSON can live in a one-row config table,
regenerated by CI whenever the dbt manifest changes.

---

## Recipe 4 — Snowflake Cortex Agent: the UDF as a custom tool

Cortex Agents (the agents Snowflake hosts natively) support **custom
tools** — you register a function/procedure and describe when to use it;
the agent calls it like Claude calls an MCP tool. Sketch of the agent
spec (verify the exact field names against current Snowflake docs —
this API is evolving quarter to quarter):

```json
{
  "tools": [
    {"tool_spec": {"type": "generic", "name": "sqlsure_check",
      "description": "Validate SQL for semantic correctness (double counting, unsafe joins, policy) BEFORE executing. If approved=false, rewrite the SQL following each violation's fix and re-check.",
      "input_schema": {"sql_text": "string"}}}
  ],
  "tool_resources": {"sqlsure_check": {"type": "function", "identifier": "MYDB.PUBLIC.SQLSURE_CHECK"}},
  "instructions": "Never execute SQL that has not been approved by sqlsure_check."
}
```

**What physically happens:** user asks the Cortex Agent a question → the
agent (or Cortex Analyst behind it) drafts SQL → the agent invokes
`SQLSURE_CHECK` (the Recipe-3 UDF — a SQL function call inside the same
warehouse) → gets the verdict VARIANT back → obeys the fix hints or
proceeds. Same repair loop as MCP, different transport: **MCP = JSON over
process pipes; Cortex = a UDF call inside Snowflake's engine.**

Complementary fact: Snowflake also ships a **managed MCP server** that
exposes Cortex tools to *external* agents (Claude talking to Snowflake).
In that topology, our own MCP server (Recipe 2) simply sits beside
Snowflake's in the client's tool list — the external agent gets Snowflake
data tools and the sqlsure gate from the same menu.

---

## Recipe 5 — Audit mode: everything that already ran

Warehouses log every executed query. A scheduled task turns sqlsure into a
retroactive auditor:

```sql
CREATE TASK sqlsure_nightly_audit
  WAREHOUSE = audit_wh
  SCHEDULE = 'USING CRON 0 6 * * * UTC'
AS
INSERT INTO sqlsure_findings
SELECT query_id, start_time,
       SQLSURE_CHECK(query_text, (SELECT model_json FROM sqlsure_config)) AS verdict
FROM snowflake.account_usage.query_history
WHERE start_time > DATEADD('day', -1, CURRENT_TIMESTAMP())
  AND query_type = 'SELECT';
```

**What physically happens:** once a night, Snowflake feeds yesterday's
query texts (Habitat 5 — SQL at rest in a log table) through the UDF and
stores the verdicts. Result: a dashboard of "semantically suspect queries
that actually ran," per team, per day — the incident-prevention evidence
file, generated from data that already exists.

---

## One picture, all five

```
 engineer laptop        GitHub VM              Claude/Cursor           Snowflake
┌──────────────┐  push ┌──────────────┐      ┌──────────────┐      ┌─────────────────────────┐
│ git commit   │ ────► │ checkout     │      │ agent drafts │      │ Cortex Agent drafts SQL │
│  └ pre-commit│       │  └ sqlsure.scan  │      │  └ JSON-RPC ─┼──┐   │  └ CALL SQLSURE_CHECK(...) │
│    runs sqlsure  │       │    exit 0/1  │      │              │  │   │      (UDF, in-warehouse)│
└──────────────┘       └──────────────┘      └──────────────┘  │   │ nightly TASK over       │
        │                     │                                │   │ query_history           │
        ▼                     ▼                                ▼   └─────────────────────────┘
   same engine           same engine                      same engine        same engine
                        check(sql_string, semantic_model)  →  verdict + fixes
```
