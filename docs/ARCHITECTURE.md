# How sqlsure Physically Works — ELI5 to God Level

*One query, followed byte-by-byte through the whole machine — starting
with the question everyone skips: where is the SQL in the first place?
Every specimen below is a real file/output from this project, not an
idealized sketch.*

---

## Level 0 — Clear the biggest misconception first

**sqlsure never generates SQL. Ever.**

Someone else writes the SQL — a human in a PR, or an AI like Claude. sqlsure
is a *judge*: SQL text goes in, a verdict comes out. When you see the
"agent self-repair loop," the *AI* rewrites its own query using our error
message; we only re-judge the new attempt:

```
   AI writes SQL ──► sqlsure judges ──► REJECTED + "here's why + how to fix"
        ▲                                        │
        └────── AI rewrites its own SQL ◄────────┘
                     (sqlsure never touches the SQL itself)
   ...eventually...
   AI writes SQL ──► sqlsure judges ──► APPROVED ──► only NOW does it run
```

## Level 1 — Where does SQL physically live? (the skipped question)

SQL is always just **text**. But that text sits in five different physical
habitats, and sqlsure has a door for each. These are real specimens:

### Habitat 1: a `.sql` file in a dbt repo (with Jinja templating)

Physical location on this machine:
`scratchpad/jaffle_shop_duckdb/models/customers.sql` — an ordinary text
file an engineer wrote. First lines, verbatim:

```sql
with customers as (
    select * from {{ ref('stg_customers') }}
),
orders as (
    select * from {{ ref('stg_orders') }}
),
```

Note the `{{ ref('...') }}` — this file is a **template**, not runnable
SQL. dbt fills those in at compile time.
**How sqlsure gets it:** `scan.py` walks `models/**/*.sql`, calls
`open(path).read()`, and strips the Jinja best-effort (`{{ ref('x') }}` →
`x`). Honest limit: heavy macro use defeats stripping (Fivetran repos:
only 73/190 files parsed) — which is why Habitat 2 is preferred.

### Habitat 2: inside dbt's manifest (compiled, pure SQL, in JSON)

When anyone runs `dbt build`/`compile`, dbt writes
`target/manifest.json` — one big JSON inventory. The *same* model from
Habitat 1 now exists as a JSON string field, templates resolved:

```
manifest.json → "nodes" → "model.jaffle_shop.customers" → "compiled_code":
"with customers as (\n select * from \"jaffle_shop\".\"main\".\"stg_customers\" ..."
```

**How sqlsure gets it:** `json.load(open("target/manifest.json"))`, then reads
the `compiled_code` field per node. No dbt installation needed — it's
just a JSON file sitting in the repo's `target/` folder.

### Habitat 3: a pull request (the CI door)

A PR is Habitat 1 plus a diff: GitHub tells you *which* `.sql` files
changed. The GitHub Action checks out the branch (now they're files on the
runner's disk), runs `sqlsure check` on the changed files, exit code 1 blocks
the merge. Physically identical to Habitat 1 — just triggered
automatically.

### Habitat 4: an AI agent session (SQL that never touches disk)

When Claude answers "total cost per patient," the SQL exists **only as a
string in memory**, inside a JSON message between two processes. This is
the actual wire format the MCP door receives:

```json
{"method": "tools/call",
 "params": {"name": "check_sql",
            "arguments": {"sql": "SELECT p.patient_id, SUM(f.cost) ..."}}}
```

**How sqlsure gets it:** `mcp_server.py` is a long-lived process reading
JSON-RPC messages on stdin; the SQL is the `arguments.sql` field. No file
ever exists.

### Habitat 5: datasets and logs (SQL at rest, in bulk)

Benchmarks ship SQL as JSON fields — a real entry from
`birddata/dev_20240627/dev.json` that our audit read:

```json
{"question_id": 0,
 "db_id": "california_schools",
 "question": "What is the highest eligible free rate for K-12 students...",
 "SQL": "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE ..."}
```

The same shape exists inside every company: warehouses log **every query
ever executed** (e.g. Snowflake's `account_usage.query_history` table) —
that's the future "audit everything that already ran" mode.
**How sqlsure gets it:** `json.load(...)`, loop, `check()` each string — the
audits processed 2,568 of these.

**The takeaway:** every habitat converges to the same thing — *a Python
string containing SQL* — handed to the same single function,
`check(sql, model)`. The doors differ only in how the string arrives:
`open()`, JSON field, stdin, or RPC message.

## Level 2 — What physically exists (the tool itself)

No servers, no database connection, no network, no AI inside. Just:

```
sqlsure/                        one small Python package
├── model.py     the rulebook data structures  (~100 lines)
├── checker.py   SQL text → structured facts   (~180 lines)
├── rules.py     facts × rulebook → verdicts   (~230 lines)
├── dbt_loader.py  dbt manifest → rulebook     (~90 lines)
├── cli.py       terminal door
├── scan.py      whole-repo door
└── mcp_server.py  AI-agent door
```

When sqlsure "runs," a Python process starts, reads two strings (the SQL, the
rulebook), does pure in-memory computation for ~0.1 ms, prints a verdict,
and exits. That's the entire physical footprint.

## Level 3 — The assembly line

```
 "SELECT p.patient_id,        ┌────────────┐      ┌────────────┐
  SUM(f.cost) ..."   ───────► │  STATION 1 │ ───► │  STATION 2 │
   (string, from any          │  tokenize  │      │   parse    │
    habitat above)            │  (sqlglot) │      │  → AST     │
                              └────────────┘      └─────┬──────┘
                                                        │ tree
                                                        ▼
 rulebook (Level 9:           ┌────────────┐      ┌────────────┐
 dbt / Cube / Snowflake /     │  RULEBOOK  │ ───► │  STATION 3 │
 OSI / JSON)        ───────►  │  loader    │      │  extract   │
                              └────────────┘      │  → facts   │
                                                  └─────┬──────┘
                                                        │ facts + rulebook
                                                        ▼
                              ┌─────────────────────────────────┐
                              │  STATION 4: the 9 rules, each   │
                              │  a plain Python function        │
                              │  fanout(facts, model) → [..]    │
                              │  additivity(facts, model) → []  │
                              └─────────────┬───────────────────┘
                                            │ list of Violations
                                            ▼
                              APPROVED ✓  /  REJECTED + fix hints
```

**The specimen** we'll follow through every station (the classic
double-counter):

```sql
SELECT p.patient_id, SUM(f.cost) AS total_cost
FROM fct_encounters f
JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id
GROUP BY 1
```

## Level 4 — Station 1: tokenizing (string → LEGO pieces)

The SQL is just characters. First, sqlglot chops it into typed pieces,
exactly like splitting a sentence into words. Real output:

```
SELECT     'SELECT'
VAR        'p'
DOT        '.'
VAR        'patient_id'
COMMA      ','
VAR        'SUM'
L_PAREN    '('
VAR        'f'
DOT        '.'
VAR        'cost'
...
```

Nothing "understands" anything yet. It's the alphabet-soup stage.

## Level 5 — Station 2: parsing (LEGO pieces → the AST tree)

The tokens get assembled into a tree that mirrors the query's grammar —
the **AST** (abstract syntax tree). Real sqlglot output for our specimen,
trimmed:

```
Select(
  expressions=[
    Column(this=patient_id, table=p),
    Alias(
      this=Sum(this=Column(this=cost, table=f)),
      alias=total_cost)],
  from_=From(
    this=Table(this=fct_encounters, alias=f)),
  joins=[
    Join(
      this=Table(this=dim_diagnosis, alias=d),
      on=EQ(Column(encounter_id, table=f),
            Column(encounter_id, table=d)))],
  group=Group(expressions=[Literal(1)]))
```

Read it like a family tree: *a Select, whose FROM is fct_encounters
aliased f, with one Join to dim_diagnosis on f.encounter_id =
d.encounter_id, one SUM over f.cost, grouped by ordinal 1.*

Key insight: **the tree knows structure, not meaning.** It knows a SUM
wraps a Column. It has no idea whether summing that column is safe. That's
the gap the next stations fill.

## Level 6 — Station 3: extraction (tree → a handful of facts)

[checker.py](../sqlsure/checker.py) walks the tree and boils it down to a tiny
dataclass — the only facts the rules will ever need. Real output:

```python
QueryFacts(
  base       = 'fct_encounters',      # first table in FROM
  joins      = [QueryJoin(table='dim_diagnosis',
                          on_pairs=[('encounter_id','encounter_id')],
                          has_predicate=True)],
  aggregates = [Aggregate(func='SUM', column='cost',
                          table='fct_encounters', distinct=False)],
  group_by   = [('p', 'patient_id')],
)
```

How each fact was physically obtained:
- **base**: `tree.args["from_"].this.name` — the FROM table node's name.
- **joins**: for every `Join` node, take the table name and every
  `column = column` pair inside its ON clause. (No ON? We look for the
  key in the WHERE clause — old-style `FROM a, b WHERE a.id = b.id`.)
- **aggregates**: find every `Sum/Avg/Count/...` node; unwrap DISTINCT;
  resolve the alias `f` → `fct_encounters` via a `{alias: table}` dict
  built from the Table nodes.
- **group_by**: `GROUP BY 1` is resolved by index into the SELECT list.
- **CTEs/subqueries**: the walk runs once per `Select` scope in the tree,
  so a fanout hidden inside `WITH x AS (...)` is extracted from *its own*
  scope. CTE names are remembered so they're never mistaken for real
  tables.

## Level 7 — The rulebook (where "meaning" physically lives in memory)

The rules can't judge facts in a vacuum — they need the declared truths.
Those live in [model.py](../sqlsure/model.py) dataclasses. For our specimen:

```python
SemanticModel(
  tables = {
    'fct_encounters': Table(grain=['encounter_id'],
                            measures={'cost': Measure(additivity='additive'),
                                      'avg_los': Measure(additivity='non_additive')}),
    'dim_diagnosis':  Table(grain=['diagnosis_id']),
    ...
  },
  joins = {
    ('fct_encounters','dim_diagnosis'):
        Join(cardinality='one_to_many', keys=[('encounter_id','encounter_id')]),
    ('fct_encounters','dim_patient'):
        Join(cardinality='many_to_one', keys=[('patient_id','patient_id')]),
  })
```

Three kinds of knowledge, nothing more: *what one row means* (grain),
*what's safe to sum* (additivity), *what joins do to row counts*
(cardinality). Plus optional policy tags (sensitive columns).

## Level 8 — Station 4: the rules (facts × rulebook → verdict)

Every rule in [rules.py](../sqlsure/rules.py) is an ordinary function with the
same signature. The FANOUT rule's actual logic, annotated with our
specimen's values:

```
1. Which joined tables multiply the base's rows?
     edge('fct_encounters', 'dim_diagnosis').cardinality
       == 'one_to_many'                         ← rulebook lookup
     → fans = ['dim_diagnosis']                 ← non-empty: danger zone

2. Is anything being summed that shouldn't survive multiplication?
     aggregate: SUM(cost), distinct=False       ← from QueryFacts
     owner of 'cost' = 'fct_encounters' = base  ← alias resolution
     measures['cost'].additivity == 'additive'  ← rulebook lookup

3. Both true → emit:
     Violation(rule='FANOUT', severity='error',
       message="SUM(cost) after one-to-many join to ['dim_diagnosis']
                — cost will be double-counted.",
       fix="Pre-aggregate fct_encounters to [encounter_id] in a CTE
            before joining ['dim_diagnosis'].")
```

That's it. No AI, no probability, no database query — **two dictionary
lookups and an if-statement.** The other eight rules are the same shape.
This is why a check costs 0.1 ms and why the same input *always* produces
the same verdict — a property no LLM judge can offer.

## Level 9 — Where the rulebook physically comes from (dbt? Cube? OSI? all of them)

The answer to "is it only dbt?": **sqlsure needs three facts — grain,
additivity, cardinality. Anything that declares them can feed it.** Every
source below is just a different serialization of the same truths, and
they all funnel into the one `SemanticModel` class (the "narrow waist"):

```
 dbt manifest.json ──┐
 dbt schema.yml ─────┤
 hand-written JSON ──┼──► loader ──► SemanticModel ──► the 9 rules
 benchmark PK/FK ────┤              (grain, additivity,
 Cube YAML ──········┤               cardinality, policy)
 Snowflake Sem.Views ┤
 OSI YAML ──·········┘        (solid = built, dotted = roadmap)
```

| Source | Physical form | How it's read | Status |
|---|---|---|---|
| Hand-written | `model.example.json`, a file you type | `json.load()` | ✅ built |
| **dbt manifest** | `target/manifest.json` — test nodes carry the semantics | `dbt_loader.py` | ✅ built |
| **dbt schema.yml** | `models/**/*.yml` files in the repo | `scan.py` YAML walk | ✅ built |
| Benchmark schemas | `tables.json` with PK/FK index lists | audit scripts | ✅ built |
| **Cube** | YAML/JS files in the Cube project repo (`model/cubes/orders.yml`) | YAML parse (roadmap) | ⬜ |
| **Snowflake Semantic Views** | **not files** — live objects inside Snowflake | SQL over a connection (roadmap) | ⬜ |
| **OSI** | vendor-neutral YAML per the v1.0 spec (Jan 2026) | YAML parse (roadmap) | ⬜ |

### The dbt case, physically (built — this is what runs today)

A dbt engineer wrote this test in `schema.yml` months ago, for their own
reasons:

```yaml
- name: orders
  columns:
    - name: customer_id
      tests:
        - relationships:
            to: ref('customers')
            field: customer_id
```

After `dbt build`, that test exists inside `manifest.json` as a node —
real specimen from jaffle shop:

```
"test.jaffle_shop.relationships_orders_customer_id__customer_id__ref_cu..."
  test_metadata.kwargs = {"column_name": "customer_id",
                          "to": "ref('customers')",
                          "field": "customer_id", ...}
```

`dbt_loader.py` reads that node and mechanically concludes: *orders →
customers is many-to-one on (customer_id, customer_id)* — because that is
literally what a relationships test asserts. A `unique` test on a column
becomes grain the same way. **The engineer declared semantics without
knowing it; sqlsure just collects the confession.**

### The Cube case, physically (roadmap)

Cube projects are repos full of YAML like:

```yaml
cubes:
  - name: orders
    sql_table: public.orders
    joins:
      - name: customers
        relationship: many_to_one          # ← cardinality, declared!
        sql: "{orders.customer_id} = {customers.id}"
    measures:
      - name: revenue
        sql: amount
        type: sum                          # ← additivity, declared!
```

Same three facts, different spelling. A loader is ~80 lines of YAML
mapping — that's the entire "Cube integration."

### The Snowflake Semantic Views case, physically (roadmap — the odd one out)

These are **not files anywhere**. They're schema objects living *inside*
Snowflake, created by `CREATE SEMANTIC VIEW ... RELATIONSHIPS (...) FACTS
(...)`. To read them you must open a database connection and query them
(`SHOW SEMANTIC VIEWS`, `GET_DDL(...)`). This is the only rulebook source
that requires credentials and a network — which is why it's a connector,
not a parser, and why it comes later.

### The OSI case, physically (roadmap — the strategic one)

OSI (Open Semantic Interchange — Snowflake, dbt, Salesforce, Databricks;
v1.0 Jan 2026) is a vendor-neutral YAML format for exactly these
declarations. When tools export OSI files, one sqlsure loader covers every
participating vendor at once. Same narrow waist, biggest funnel.

## Level 9.5 — The conversion, byte by byte (a complete worked specimen)

Everything above described the stations; this section shows a **complete
tiny project actually being converted**, with nothing omitted. The
specimen is three files (this exact project exists in the scratchpad and
the outputs below are real):

```
mini_shop/
├── dbt_project.yml
└── models/
    ├── schema.yml            ← semantics live here (written by engineer)
    └── revenue_report.sql    ← SQL lives here (written by engineer)
```

**File 1 — `models/schema.yml`** (the engineer's ordinary dbt tests):

```yaml
models:
  - name: orders
    meta:
      sqlsure:
        measures:
          amount: additive          # ← one opt-in line for sqlsure
    columns:
      - name: order_id
        tests: [unique]             # ← ordinary dbt test
      - name: customer_id
        tests:
          - relationships:          # ← ordinary dbt test
              to: ref('customers')
              field: customer_id
  - name: customers
    columns:
      - name: customer_id
        tests: [unique]
```

### Conversion 1: YAML → SemanticModel (the "how does it convert" answer)

`load_yaml_model()` walks the YAML and applies three mechanical mappings:

| It sees (YAML) | Mapping logic | It builds (Python object) |
|---|---|---|
| `order_id: tests: [unique]` | "unique" *asserts* one row per value — that IS a grain claim | `Table('orders', grain=['order_id'])` |
| `customer_id: relationships: to: ref('customers')` | a relationships test *asserts* every orders.customer_id exists once in customers — that IS many-to-one | `Join(('orders','customers'), cardinality='many_to_one', keys=[('customer_id','customer_id')])` |
| `meta: sqlsure: measures: amount: additive` | explicit opt-in tag | `Measure('amount', 'additive')` |

Real program output, verbatim:

```
Table(name='orders',    grain=['order_id'],    measures={'amount': 'additive'})
Table(name='customers', grain=['customer_id'], measures={})
Join('orders','customers'): cardinality='many_to_one', keys=[('customer_id','customer_id')]
```

No inference, no AI: each mapping is "this dbt test *means* exactly this
constraint, by the test's own definition." The manifest path
(`dbt_loader.py`) is the same three mappings reading JSON nodes instead
of YAML.

### Conversion 2: raw model file → parseable SQL (`strip_jinja`)

**File 2 — `models/revenue_report.sql`**, before and after, verbatim:

```
BEFORE (bytes on disk)                  AFTER (what the parser receives)
with base as (                          with base as (
    select * from {{ ref('orders') }}       select * from orders
)                                       )
select c.customer_id,                   select c.customer_id,
  sum(b.amount) as revenue                sum(b.amount) as revenue
from base b                             from base b
join {{ ref('customers') }} c           join customers c
  on b.customer_id = c.customer_id        on b.customer_id = c.customer_id
group by 1                              group by 1
```

The strip is four regexes applied in order: delete `{# comments #}`,
replace `{{ ref('x') }}`/`{{ source('a','x') }}` with the last quoted name
(`x`), delete `{% ... %}` control blocks, replace any leftover `{{ ... }}`
with `NULL`. If the result still won't parse, the file is counted
*skipped* — never guessed at.

### Conversion 3: parseable SQL → facts, per scope

Real output — note there are **two** scopes because of the CTE:

```
scope 0 (outer): base='base'    joins=[('customers', [('customer_id','customer_id')])]
                                aggs=[('SUM','amount', table='base')]
scope 1 (CTE):   base='orders'  joins=[]   aggs=[]
```

And here is the machine being honest with itself: in scope 0 the base is
`base` — a CTE, not a real table. The rules see `base` is in the CTE-name
set, so they **decline to judge** the join's cardinality rather than
guess. If the engineer had joined `orders` to `customers` directly, the
rulebook edge from Conversion 1 would verify it as safe many-to-one.
Every conversion preserves one invariant: *claim only what was declared,
flag only what contradicts a declaration, and say "can't verify" for the
rest.*

## Level 10 — The three doors (physically, how a check gets invoked)

Same engine function every time — `check(sql, model) → [Violation]` —
three transport wrappers around it:

**Door 1: CLI / CI** — a shell process. SQL arrives via file or stdin
(Habitats 1–3); verdict leaves as printed text **and a process exit code**
(0 = approved, 1 = rejected). That exit code is the entire CI integration:

```
$ echo "SELECT SUM(cost) ..." | python -m sqlsure.cli --model m.json
  ✗ [ERROR] FANOUT: ...          ← stdout for humans
$ echo $?
  1                              ← exit code for machines
```

**Door 2: MCP** — a long-lived Python process speaking JSON-RPC over
stdin/stdout with the AI agent's host (Habitat 4). The agent sends a JSON
message; we send one back:

```
agent → {"method":"tools/call","params":{"name":"check_sql",
          "arguments":{"sql":"SELECT SUM(f.cost) ..."}}}
sqlsure   → {"approved": false,
         "violations":[{"rule":"FANOUT","severity":"error",
                        "message":"...","fix":"Pre-aggregate ..."}]}
```

The `fix` string is written *for the AI to obey* — that's why 10/10
repaired queries pass in the benchmark.

**Door 3: library** — no process boundary at all; another program's
Python code calls the function directly: `violations = check(sql, model)`.

## Level 11 — God level: the honest boundaries

- **It's static analysis.** sqlsure reads code; it never reads data. It can
  prove "this join *can* double-count" (structure) but not "row 384 is
  duplicated" (data). The BIRD #571 proof needed one extra manual step —
  executing the shipped database — precisely because static analysis
  stops at structure.
- **Verdicts are only as good as the rulebook.** Undeclared cardinality →
  sqlsure says "can't verify," never "fine." Silence and safety are different
  states, and the scanner reports the difference (Mattermost: 0/128
  verifiable — a coverage report, not a clean bill).
- **Scope-aware, not yet lineage-aware.** Each SELECT scope is checked
  independently; a measure renamed inside a CTE (`cost AS c`) loses its
  additivity tag in the outer scope. Column-level lineage through CTEs is
  the known next engine milestone.
- **Determinism is the moat.** Same input, same verdict, 0.1 ms, offline,
  auditable line-by-line. An LLM judging SQL can be argued with; a
  dictionary lookup cannot. That is why the judge must never also be the
  author — and why sqlsure will never generate SQL.

## The whole machine on one screen

```
 WHERE SQL LIVES              WHERE RULES LIVE
 .sql files / manifest        dbt tests / schema.yml / Cube YAML /
 PR diffs / agent messages    Snowflake Sem. Views / OSI / JSON
 datasets / query logs                 │
        │                              ▼
        │                    loader → SemanticModel
        ▼                              │
   a Python string ── tokenize ── AST ── facts ──┐
                                                 ▼
                              9 rule functions (dict lookups + ifs)
                                                 │
                    [] → APPROVED → run the query
                    [Violation…] → REJECTED → fix hints → author retries
```
