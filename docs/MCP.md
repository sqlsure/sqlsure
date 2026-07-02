# sqlsure MCP Server

Give any MCP-capable agent (Claude Code, Claude Desktop, Cursor, or your
own) a semantic inspector it must pass before touching the warehouse.
Deterministic verdicts in 0.1 ms — no extra LLM calls, no network, no data
access.

## Install & register

```bash
pip install "sqlsure[mcp]"
```

**Claude Code:**
```bash
claude mcp add sqlsure -- python -m sqlsure.mcp_server --model /abs/path/model.json
```

**Claude Desktop / Cursor** (`claude_desktop_config.json` / `mcp.json`):
```json
{
  "mcpServers": {
    "sqlsure": {
      "command": "python",
      "args": ["-m", "sqlsure.mcp_server", "--model", "/abs/path/model.json"]
    }
  }
}
```

**Rulebook source** — pick one:
- `--model model.json` — hand-written semantic model
  ([example](../model.example.json))
- `--manifest target/manifest.json` — extracted from your dbt project's
  tests automatically (`unique` → grain, `relationships` → join
  cardinality, `meta.sqlsure` → additivity/policy)

## Tools

### `check_sql(sql, dialect?) → {approved, violations[]}`

Validate a query **before executing it**. Response:

```json
{
  "approved": false,
  "violations": [{
    "rule": "FANOUT",
    "severity": "error",
    "message": "SUM(cost) after one-to-many join to ['dim_diagnosis'] — cost will be double-counted.",
    "fix": "Pre-aggregate fct_encounters to [encounter_id] in a CTE before joining ['dim_diagnosis']."
  }]
}
```

- `approved: false` when any `error` or `policy` violation exists —
  **do not execute**; rewrite applying each `fix`, then re-check.
- `warning` violations don't block but should be surfaced to the user.
- The `fix` strings are written to be applied verbatim by an agent
  (10/10 actionability in our benchmark).

### `describe_model() → {tables, joins}`

The rulebook: every table's grain, measures (with additivity), sensitive
columns, and every declared join edge with cardinality and keys. **Call
this first** and plan queries along declared join paths — prevention
beats repair.

## The agent loop

```
user question
   → describe_model()          # learn safe paths
   → draft SQL
   → check_sql(draft)          # judge
       approved? → execute
       rejected? → apply fixes → check_sql(again) → execute
```

The server's instructions field teaches this loop to the agent
automatically; you don't need to prompt for it.

## What it will and won't do

- ✅ Deterministic: same SQL + same rulebook = same verdict, always
- ✅ Offline: no network, no database connection, never reads your data
- ✅ Honest: undeclared relationships come back "can't verify," never "fine"
- ❌ Never generates or rewrites SQL — the agent stays the author,
  sqlsure stays the judge

## Troubleshooting

- **Every join is "unverifiable"** → your rulebook has no declared
  relationships. Run `python -m sqlsure.scan your-repo` for a coverage
  report showing exactly which dbt tests to add.
- **Dialect errors** → pass `dialect` in the `check_sql` call
  (`snowflake`, `bigquery`, `postgres`, `sqlite`, …).
- **Model file changed** → restart the server (the rulebook loads at
  startup).
