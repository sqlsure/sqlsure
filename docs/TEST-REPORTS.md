# sqlsure — Test & Validation Log

*Running record of every validation of the engine: unit tests, retro-scans
of real repos, findings, and honest limitations. Updated as tests are run.
Individual scan reports live in [reports/](reports/).*

---

## 1. Unit test suite

**What:** [tests/run_tests.py](../tests/run_tests.py) — 16 cases, one
positive and one negative per rule (fanout incl. COUNT and COUNT DISTINCT,
chasm, additivity, semi-additivity incl. GROUP BY ordinal resolution,
weighted-avg, join-key, undeclared-join, cross-join, sensitive columns).
**Status (2026-07-01):** 16/16 passing, including after the scope-aware
(CTE) refactor.

## 2. Demo model (healthcare)

**What:** [check.py](../check.py) against
[model.example.json](../model.example.json): 6 queries.
**Result:** 5 correctly rejected (fanout, additivity, semi-additive,
wrong join key, PHI policy ×2), 1 correctly approved. Also verified: the
same fanout is caught when buried inside a CTE (v0.1's blind spot, closed
by the scope-aware checker).

## 3. Retro-scan: dbt Labs jaffle_shop_duckdb (real manifest)

**Setup:** cloned the repo, ran `dbt build` with DuckDB (28/28 dbt tests
passed), pointed `sqlsure.dbt_loader` at the generated `target/manifest.json`.
**Zero-config extraction result:** 5 models with grain (from `unique`
tests), 1 join edge orders→customers many-to-one (from the `relationships`
test). Payments edge correctly *absent* — the repo doesn't declare it.

**Query checks against the extracted rulebook:**
| Query | Expected | Result |
|---|---|---|
| wrong join key (`o.order_id = c.customer_id`) | reject | ✅ rejected, correct key named |
| join to undeclared payments | flag unverifiable | ✅ warning, honest "cardinality unknown" |
| clean revenue per customer | approve | ✅ approved |
| revenue double-count via payments (after adding 1 test + 1 meta line) | reject | ✅ FANOUT with pre-aggregate fix |

**Finding #1 (calibration):** COUNT(\*) after a fan-out join was initially
an *error*, but counting the joined side's rows (orders per customer) is
legitimate — a real false-positive. **Fix applied:** downgraded to a
warning that explains both readings. This validated the red-team concern
that miscalibrated severity kills linter trust.

**Full-repo scan:** 5/5 files parsed, 0 violations — correct negative
control: jaffle marts pre-aggregate before joining, which is exactly the
pattern sqlsure recommends. Report: [reports/jaffle-shop.md](reports/jaffle-shop.md).

## 4. Scan: fivetran/dbt_hubspot (package ecosystem)

**Result:** 90 models discovered, only 5 with declared grain, **0 join
edges** (Fivetran packages don't use `relationships` tests); 73/190 SQL
files parsed — their macro-heavy Jinja defeats best-effort stripping.
**Finding #2:** package-style repos need compiled SQL (from a manifest)
rather than raw-file scanning; raw scanning is a fallback, not the primary
path. Report: [reports/fivetran-hubspot.md](reports/fivetran-hubspot.md).

## 5. Scan: mattermost/mattermost-data-warehouse (production, Snowflake)

The headline test — a real company's production dbt monorepo (2 projects,
489 model files).

**Results:** 355 models in rulebook, 92 with grain (26%), 17 declared
edges. 206/489 files parsed (Jinja limits again). 128 joins observed in
SQL: **0 verifiable**, 45 between known models with *undeclared*
relationships, 83 involving unknown tables/CTE outputs. 41 warnings,
0 errors, 0 policy.

**Finding #3 (the big one):** in a real production repo, *none* of the
observed joins could be verified, because relationship declarations don't
exist — e.g. `stg_stripe__subscriptions ↔ stg_stripe__customers`, exactly
the one-to-many shape where revenue fan-out hides. The absence of errors
isn't cleanliness; it's **undeclared semantics**. This inverts the pitch
for production repos: the first deliverable isn't caught bugs, it's the
coverage map — "your join-verification coverage is 0/128; these N
relationship tests would fix it." Report:
[reports/mattermost.md](reports/mattermost.md).

**Finding #4:** CTE names shadowing model names (jaffle's `customers` CTE
vs `customers` model) caused potential false attribution; fixed by treating
CTE-shadowed names as unknown in all join rules.

## 6. Not tested / blocked

- **gitlab-data/analytics** — was the ideal target (~2,000-model public
  production project) but is no longer anonymously accessible (API returns
  404; dbt docs site now behind auth). Kept on the list in case access
  returns; Mattermost serves as the production evidence meanwhile.

## 7. Honest limitations register (current)

1. Raw-SQL scanning parses ~40–100% of files depending on Jinja style;
   manifest `compiled_code` is the reliable path (needs `dbt compile`).
2. Fan-out detection requires declared cardinality + additivity; on
   undeclared repos sqlsure reports unverifiability rather than bugs (by
   design, but means retro-scans on bare repos yield coverage maps, not
   caught-bug counts).
3. Cardinality is evaluated base-table→joined-table per scope; dim-to-dim
   join chains within one scope aren't yet path-analyzed.
4. No column-level lineage through CTEs yet — a measure aliased in a CTE
   loses its additivity tag in the outer scope.

## 8. Utility benchmark (2026-07-01)

**What:** [benchmarks/benchmark.py](../benchmarks/benchmark.py) — 11 buggy +
10 clean labeled queries incl. near-miss clean patterns and repaired
versions implementing each fix hint. **Results:** 100% recall (11/11), 0%
hard false positives (0/10), 10/10 fix hints yield a passing query, 0.1 ms
median latency. Full numbers and the author-bias caveat:
[reports/benchmark.md](reports/benchmark.md) and [METRICS.md](METRICS.md).

## 9. Spider gold-query audit (2026-07-01) — first external-corpus result

**What:** [benchmarks/audit_spider.py](../benchmarks/audit_spider.py) — sqlsure's
extraction engine over all **1,034 gold queries** of the Spider validation
split, with the rulebook derived mechanically from Spider's own PK/FK
declarations. Conservative classification: only different-column joins
matching no FK, and predicate-less joins, count as anomaly candidates.

**Results:** 1,034/1,034 parsed (100%). 518 joins observed: 484 FK-backed
(93%), 2 shared-key (correctly not flagged), 0 cartesian, **30 unbacked
candidates — and manual review confirms all 30 trace to one genuine schema
defect in `flight_2`** (missing `flights.Airline → airlines.uid` FK plus a
wrong PK declaration), affecting 2.9% of the split's gold queries. **Zero
spurious anomalies on externally-authored SQL.** Full analysis:
[reports/spider-audit.md](reports/spider-audit.md).

**Why it matters:** prior work documents benchmark annotation errors via
manual/LLM review; this localizes a schema-level defect mechanically in
seconds with no labeling. It is the seed of the publishable result — next:
BIRD dev set (richer schemas, known-noisier annotations).

## 10. BIRD dev audit (2026-07-01) — empirically proven wrong gold answer

**What:** [benchmarks/audit_bird.py](../benchmarks/audit_bird.py) over all
**1,534 gold queries** of BIRD dev_20240627 (official dev set, 11
databases), rulebook from BIRD's own PK/FK declarations; candidates then
verified against the shipped SQLite databases.

**Results:** 1,534/1,534 parsed. 1,419 joins: 96% FK-backed, 34 shared-key
(correctly unflagged), 0 cartesian, **15 unbacked candidates → 13
annotation-gap symptoms + 1 empirically proven wrong gold answer + 1
adjudicated benign-but-fragile, 0 spurious**. Novelty cross-check: **10/15
candidates were independently flagged by the Arcwise/UIUC expert
corrections (VLDB'26)** — including #571, whose expert-corrected SQL
matches our diagnosis exactly; the `european_football_2` schema-layer FK
gap is *not* addressed by those per-question corrections and appears novel.
**Filed upstream 2026-07-01:**
[bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37),
after verifying the root cause against the shipped SQLite database: both
missing FKs use the implicit-PK form (`REFERENCES League` with no column),
which the schema-extraction script evidently fails to resolve — and a full
sweep of all 11 dev databases confirmed these are the *only two* missing FK
annotations in the dev set. Details:
- **13 queries** hit a confirmed annotation gap: `european_football_2`
  declares 29 FKs on `Match` (every player slot!) but omits
  `Match.league_id → League.id` — the edge its own gold queries use.
- **1 empirically wrong gold answer**: question #571 asks for a
  posts-to-votes ratio (true answer 0.375); the gold SQL's chasm-trap join
  (votes×posts per user) collapses the arithmetic to post count and
  returns **3.0 — 8× off**, verified by executing against the shipped
  database. Fan-out double-counting — sqlsure's core target class — inside a
  benchmark gold answer; models answering correctly are scored wrong.

Report: [reports/bird-audit.md](reports/bird-audit.md). Combined with the
Spider audit (§9): **2,568 gold queries scanned, 45 candidates, 44
confirmed real (43 annotation-gap symptoms + 1 proven wrong answer), 1
unadjudicated, 0 spurious.**

## 11. Scoreboard

| Validation | Verdict |
|---|---|
| Engine correctness (unit + demo) | ✅ 16/16 + 6/6 |
| Zero-config extraction from real manifest | ✅ works |
| Catches real bug classes on real schema | ✅ (jaffle retro-scan) |
| False-positive discipline | ✅ 1 found, fixed, documented |
| Production-repo scan runs end-to-end | ✅ (Mattermost, 489 files) |
| Production repos declare enough semantics | ❌ → coverage-map-first onboarding |
| Zero-noise anomaly detection on external corpus (Spider, 1,034 queries) | ✅ 30/30 candidates → 1 real schema defect |
| BIRD dev audit (1,534 queries + DB execution) | ✅ 14/15 confirmed incl. 1 proven wrong gold answer (8× off) |
