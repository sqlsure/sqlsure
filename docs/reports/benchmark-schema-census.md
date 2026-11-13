# What text-to-SQL benchmarks declare about their own schemas

*November 2026 · a cross-benchmark census of the relationship layer*

A text-to-SQL benchmark ships two artifacts: the databases, and the
schema it publishes as the description of those databases. Models see
the schema. Graders execute against the database. This report measures,
for every benchmark that publishes both, how much of the databases'
relationship structure survives into the schema the model is shown.

The answer differs by benchmark, and so does the reason. One case is a
defect that has been fixed. The other is a deliberate design choice with
a consequence worth naming. They should not be described in the same
words, so this report keeps them apart.

## Method

Read the foreign keys the shipped databases declare (`PRAGMA
foreign_key_list`, resolving `REFERENCES parent` with no column list to
the parent's primary key), read the foreign keys the published schema
declares, and diff. Read-only, stdlib only, no model involved. Both
scripts are in [`benchmarks/`](../../benchmarks/) and run against the
benchmarks' own public downloads.

## Case 1 — BIRD: a defect, reported and fixed

BIRD publishes foreign keys and intends them to be complete. Two were
missing from `european_football_2`, which we reported in
[bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37).
The 2026 Mini-Dev release added exactly those two edges.

| BIRD artifact | FKs the databases declare | FKs the schema declares | covered |
|---|---|---|---|
| Mini-Dev 2026 `baseline_inference/schemas/` | 104 | 104 | **100%** |
| `dev.zip` (unchanged since 2024-06-29, still shipping) | 104 | 102 | 98% |

This is the whole case for treating benchmark metadata as code: the
annotation disagreed with the database, nothing in the pipeline could
have noticed, a one-command diff found it, and the maintainers shipped
the fix.

`train.zip`'s 69 databases publish 424 foreign keys, with **13
databases declaring none at all** — `mondial_geo` has 34 tables and no
relationships. We have not diffed those against their databases (nested
zip, not extracted), so no defect is claimed. The separate
[train audit](bird-train-audit.md) found 788 of 9,560 gold-query joins
unbacked by any declared relationship.

## Case 2 — Spider 2.0: withheld by design

Spider 2.0 publishes **no primary keys and no foreign keys anywhere**:
across 305 published schemas and 13,986 tables on all three platforms,
0 tables declare a primary key and 4 declare a foreign key. The schema
format has no field for either — each table's JSON carries
`column_names`, `column_types`, `description` and `sample_rows`.

**This is intentional, and the maintainers have said so twice.** Asked
whether key constraints exist
([#6](https://github.com/xlang-ai/Spider2/issues/6), Oct 2024):

> "for the Spider 2.0 databases, we did not provide primary keys and
> foreign keys, nor did we find them in BigQuery."

Asked specifically why the *SQLite* databases have none
([#91](https://github.com/xlang-ai/Spider2/issues/91), May 2025):

> "our dataset does not provide primary keys or foreign keys. Because we
> mainly focus on cloud databases, these DBs typically do not provide
> primary keys and foreign keys. To maintain consistency, we have not
> provided support for the SQLite portion in the dataset either."

That rationale is sound on its own terms. BigQuery and Snowflake support
only unenforced key constraints and most public datasets declare none,
so a benchmark aiming at enterprise realism has a real argument for
presenting schemas the same way. A third user asked again in Sept 2025
([#142](https://github.com/xlang-ai/Spider2/issues/142), unanswered),
which suggests the choice is surprising often enough to be worth
documenting in the paper rather than in issue replies.

### What the choice costs, measured

The SQLite subset is where the decision becomes visible, because there
the relationship structure demonstrably exists in files the benchmark
distributes:

| Spider 2.0-lite, SQLite subset | in the shipped databases | in the published schema |
|---|---|---|
| foreign keys | **178** | 0 |
| tables declaring a primary key | **186** of 412 | 0 |

The 178 edges come from 10 of the 30 databases; the other 20 declare
none themselves. 147 of the 178 are in databases that are published
sample schemas with documented relationship graphs — Sakila and Pagila
(22 each), Chinook and its `music` variant (11 each), two Oracle sample
sets (45 together), three from the *SQL Queries for Mere Mortals* set
(36 together). The remaining 31 are `EU_soccer`.

Of Spider 2.0-lite's 547 questions, 135 run against these local SQLite
databases and 37 against the 10 whose relationship graph is withheld.

### The same two edges, in both benchmarks

Spider 2.0's `EU_soccer` and BIRD's `european_football_2` are built from
the same public Kaggle European Soccer database. Two of Spider 2.0's 178
withheld edges are `match.country_id → country.id` and
`match.league_id → league.id` — precisely the two that were missing from
BIRD by accident and that BIRD's 2026 release added. One source
database, two benchmarks: the same two relationships absent from both
published schemas, in one case as a bug now fixed and in the other as
policy.

## Schemas we could not diff

| Benchmark | published schema | why not |
|---|---|---|
| KaggleDBQA | `KaggleDBQA_tables.json` — 6 FKs over 8 databases and 17 tables; 5 of 8 declare none | databases sourced from Kaggle, not redistributed |
| Spider 1.0 | `tables.json` | databases are a Google Drive zip; the HF mirror ships questions and SQL only |
| BIRD train | `train_tables.json` | databases in a nested zip, not extracted |

## What this does and does not establish

- **For BIRD:** a real defect existed, a one-command diff found it, and
  it is fixed. Benchmark metadata is code — it ships, it is depended on,
  and it was the one artifact in the pipeline with no test.
- **For Spider 2.0:** no defect is claimed. The relationship layer is
  absent on purpose. What the numbers establish is the *size* of what
  that choice withholds — 178 foreign keys and 186 primary keys present
  in distributed files — and its consequence: on this benchmark a model
  must infer the join graph from column names, and no deterministic
  checker can verify a join at all. The benchmark cannot distinguish a
  model that knows a relationship from one that guessed it correctly.
- **The realism argument has a gap worth stating.** It is true that
  enterprise warehouses rarely declare foreign keys. It is also true
  that enterprise *analysts* rarely work without a substitute — dbt
  tests, a semantic layer, a data dictionary, tribal knowledge. Spider
  2.0 removes the keys and supplies no substitute, so it models the
  warehouse's metadata poverty without modelling the context that makes
  real analysts able to join correctly anyway.
- **No model was run.** Nothing here claims how much accuracy a complete
  schema would buy.

## Reproducing

```bash
python benchmarks/audit_spider2_schemas.py census  --ddl-root <spider2>/spider2-lite/resource/databases
python benchmarks/audit_spider2_schemas.py convert --ddl-root <spider2>/spider2-lite/resource/databases \
    --db-dir <unzipped local_sqlite> --out-dir layout
python benchmarks/verify_fk_annotations.py --db-dir layout/dbs --annotations layout/annotations.json
```

For BIRD, `verify_fk_annotations.py` alone, against `dev_tables.json`
(exit 1 today) or the 2026 Mini-Dev schemas (exit 0).
