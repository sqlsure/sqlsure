# Do text-to-SQL benchmarks tell models the truth about their own schemas?

*November 2026 · a cross-benchmark census of the relationship layer*

A text-to-SQL benchmark ships two artifacts that have to agree: the
databases, and the schema it publishes as the description of those
databases. Models see the schema. Graders execute against the database.
Nothing in either benchmark's test suite checks that the two match.

We built [`verify_fk_annotations.py`](../../benchmarks/verify_fk_annotations.py)
to diff them after finding two foreign keys missing from BIRD's published
dev schema ([bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37),
reported and since fixed). This report applies the same diff to every
benchmark that publishes both halves.

## Method

For each benchmark: read the foreign keys the shipped databases declare
(`PRAGMA foreign_key_list`, resolving `REFERENCES parent` with no column
list to the parent's primary key), read the foreign keys the published
schema declares, and diff. Read-only, stdlib only, no model involved.
Every number below is reproducible from the two scripts in
[`benchmarks/`](../../benchmarks/) against the benchmarks' own public
downloads.

## Results

| Benchmark | published schema artifact | FKs the databases declare | FKs the schema declares | covered |
|---|---|---|---|---|
| BIRD Mini-Dev (2026 release) | `baseline_inference/schemas/` | 104 | 104 | **100%** |
| BIRD dev (`dev.zip`, still shipping) | `dev_tables.json` | 104 | 102 | 98% |
| Spider 2.0-lite, SQLite subset | `DDL.csv` + per-table JSON | 178 | **0** | **0%** |

Primary keys, same comparison, Spider 2.0-lite's SQLite subset: 186 of
412 shipped tables declare one; 0 of the published schema's tables do.

Across all of Spider 2.0 — 305 published schemas, 13,986 tables, all
three platforms — **0 tables declare a primary key and 4 declare a
foreign key.** The published schema format has no field for either: each
table's JSON carries `column_names`, `column_types`, `description` and
`sample_rows`, and nothing else. Spider 2.0's own CodeS baseline reads
`table_data.get("foreign_keys", [])`, so a schema with no relationships
yields an empty join graph with no error raised.

The 178 edges come from 10 databases; the other 20 declare none
themselves. 147 of the 178 fall in 9 databases that are published sample
schemas with documented relationship graphs — Sakila and Pagila (22
each), Chinook and its `music` variant (11 each), two Oracle sample sets
(45 together), and three from the *SQL Queries for Mere Mortals* set (36
together). The remaining 31 are `EU_soccer`. The information was not
unavailable; it was not carried across.

Of Spider 2.0-lite's 547 questions, 135 run against these local SQLite
databases, and 37 against the 10 whose relationship graph was dropped
entirely.

### The same two edges, in two benchmarks

Spider 2.0's `EU_soccer` and BIRD's `european_football_2` are both built
from the same public Kaggle European Soccer database. Among Spider 2.0's
178 dropped foreign keys are `match.country_id → country.id` and
`match.league_id → league.id` — precisely the two edges we reported
missing from BIRD and that BIRD's 2026 release added. One source
database, two benchmarks, the same two relationships lost twice,
for two unrelated reasons.

## Schemas we could not diff

| Benchmark | published schema | databases | status |
|---|---|---|---|
| BIRD train (`train.zip`) | `train_tables.json` — 424 FKs over 69 DBs; **13 DBs declare none**, incl. `mondial_geo` (34 tables, 0 FKs) | nested zip, not extracted | FK diff not run; the [train audit](bird-train-audit.md) found 788 of 9,560 gold-query joins unbacked by any declared relationship |
| KaggleDBQA | `KaggleDBQA_tables.json` — 6 FKs over 8 DBs, 17 tables; **5 of 8 DBs declare none** | sourced from Kaggle, not redistributed | no database files to diff against |
| Spider 1.0 | `tables.json` | Google Drive zip | not yet run |

## Caveats, stated plainly

- **BigQuery and Snowflake genuinely differ.** Both support only
  unenforced key constraints, and most public BigQuery datasets declare
  none. For those 275 schemas, "no foreign keys published" may faithfully
  describe the source. The claim there is narrower: the join graph is
  absent, so no tool can verify a join — not that information was lost.
- **The SQLite subset has no such defense.** The databases are files the
  benchmark distributes; 178 foreign keys are in them and 0 reached the
  published schema.
- **20 of 30 SQLite databases declare no foreign keys themselves.** Those
  contribute nothing to the 178 and no defect is claimed for them.
- **This measures metadata, not model scores.** We have not run any model
  and make no claim about how much accuracy a complete schema would buy.
  What is established is that models are graded on joins the schema
  given to them cannot justify.

## Why it matters

A benchmark's schema is the contract it offers a model: these are your
tables, these are the relationships you may rely on. When the
relationship layer is empty, every join in every gold query is an
unverifiable claim — the model must infer the join graph from column
names, and any checker that trusts the published schema must call
correct SQL unverifiable. The leaderboard still produces a number, and
the number is still reported to three significant figures.

Benchmark metadata is code. It ships, it is depended on, and it is the
one artifact in the pipeline with no test. The diff that produced this
report takes one command and no model:

```bash
python benchmarks/audit_spider2_schemas.py census  --ddl-root <spider2>/spider2-lite/resource/databases
python benchmarks/audit_spider2_schemas.py convert --ddl-root <spider2>/spider2-lite/resource/databases \
    --db-dir <unzipped local_sqlite> --out-dir layout
python benchmarks/verify_fk_annotations.py --db-dir layout/dbs --annotations layout/annotations.json
```

Exit 0 when the published schema covers every relationship the databases
declare. Exit 1, today, for Spider 2.0-lite and for BIRD's `dev.zip`.
