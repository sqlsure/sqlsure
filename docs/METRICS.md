# sqlsure — Utility Metrics: Measured, Measurable, and Claimed

*How we quantify whether this tool is actually useful — what's proven today,
what gets instrumented next, and what we will never claim without data.*

---

## 1. Measured today (run `python benchmarks/benchmark.py`)

### Engine quality — [reports/benchmark.md](reports/benchmark.md), 2026-07-01

| Metric | Value | Meaning |
|---|---|---|
| **Detection recall** | 100% (11/11) | every labeled bug class flagged with the correct rule, incl. CTE-buried fanout |
| **Hard false-positive rate** | 0% (0/10) | no *errors* raised on clean queries, incl. near-misses (COUNT DISTINCT under fanout, pre-aggregate-then-join, snapshot-grain sums) |
| **Soft-flag rate** | 0/10 | no warnings on clean queries either |
| **Fix-hint actionability** | 10/10 | applying the `fix` text verbatim yields a passing query — the agent self-repair loop closes |
| **Latency (median / p95)** | 0.1 ms / 0.4 ms | ~4 orders of magnitude cheaper than one LLM call — effectively free inside a generation loop or CI |

**Integrity caveat, stated plainly:** the corpus and the rules share an
author. These numbers prove *the engine does what it claims on its target
bug classes with zero collateral noise* — they do not prove real-world
recall. Hardening path: §4.

### Repo reality — [TEST-REPORTS.md](TEST-REPORTS.md)

| Metric | jaffle shop | fivetran/hubspot | mattermost (production) |
|---|---|---|---|
| models w/ declared grain | 5/5 (100%) | 5/90 (6%) | 92/355 (26%) |
| declared join edges | 1 | 0 | 17 |
| joins in SQL verifiable | n/a (CTE-style) | 0/0 | **0/128** |
| files parseable (raw-SQL mode) | 5/5 | 73/190 | 206/489 |

These four numbers *are* the product's first quantitative artifact: the
**semantic coverage score** of a repo. A design-partner engagement starts by
measuring it and ends by improving it.

### External-corpus results — the numbers that aren't author-graded
*(Spider + BIRD audits, 2026-07-01 — [TEST-REPORTS.md](TEST-REPORTS.md) §9–10)*

| Metric | Value | Meaning |
|---|---|---|
| Externally-authored gold queries scanned | **2,568** (Spider dev 1,034 + BIRD dev 1,534) | SQL written by strangers, before sqlsure existed |
| Parse rate | 100% on both | the engine survives real-world SQL |
| Anomaly candidates raised | 45 | 30 Spider + 15 BIRD |
| **Candidates confirmed real or fragile** | **45/45 — zero spurious** | external-corpus precision: 100% |
| Empirically proven wrong gold answer | 1 (BIRD #571, **8× off**) | verified by executing the shipped database |
| Overlap with independent expert corrections (Arcwise/UIUC, VLDB'26) | **10/15 BIRD flags** | a 2-second mechanical pass converges with expert manual review |
| Upstream impact | [bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37) filed | root cause diagnosed (implicit-PK FK extraction bug); only 2 missing FKs in the whole dev set, both found |

This partially retires the §1 integrity caveat: precision is now
demonstrated on code we didn't write. Open half: *recall* on external
corpora (how much experts found that we missed) — measurable against the
498 expert-corrected questions, which is the next experiment.

## 2. Product metrics to instrument (leading indicators)

Telemetry the CLI/Action/MCP server should emit (opt-in, anonymized):

| Metric | Formula | Healthy signal |
|---|---|---|
| Violations caught / week / repo | count of error-severity findings on new SQL | > 0 and stable (0 = miscoverage or no usage) |
| **Agent auto-repair rate** | % of MCP rejections followed by a passing re-submission within the session | > 70% — the killer stat for the AI story |
| Time-to-first-violation | install → first error caught | < 1 week (wedge validation) |
| Suppress rate | `sqlsure: ignore` comments ÷ total findings | < 10% (>25% = rule miscalibrated — investigate, don't celebrate volume) |
| Gate survival | % of repos where the Action is still enforcing after 90 days | > 80% — the single best proxy for trust |
| Coverage delta | verifiable-joins % at day 0 vs day 90 | rising — proves teams invest in declarations because of sqlsure |

## 3. Business / outcome metrics (lagging, per design partner)

- **Incidents prevented (counterfactual):** retro-scan the repo's merge
  history; every error-severity finding in *merged* code is a bug that
  shipped. Count × the org's own estimate of incident cost (wrong exec
  number, restated dashboard, re-run analysis). This is the ROI slide, and
  it's their data, not our claim.
- **PR review time on models touching joins/aggregations** — before/after
  (ask reviewers to tag; crude but persuasive).
- **PHI findings** — for healthcare: count of policy violations caught
  pre-merge; each one is a sentence in a compliance report.
- External anchor: error analyses of LLM text-to-SQL consistently rank
  aggregation-structure and join errors among the dominant failure classes
  (see SQLens and ICL-error-repair studies below) — the bug classes sqlsure
  targets are the documented ones, not invented ones.

## 4. Hardening the numbers (roadmap from "author-graded" to "adversarial")

1. **LLM-generated corpus:** prompt several models to answer analytical
   questions against the healthcare + jaffle schemas; hand-label the output;
   measure recall/FP on SQL we didn't write. *(First real-world recall
   number; target for v0.2.)*
2. **Mutation testing at scale:** mechanically inject the 9 bug classes
   into parsed clean queries from public repos; thousands of cases, no
   author bias in the buggy set.
3. **Third-party labels:** ✅ *partially done* — 10/15 BIRD flags
   independently confirmed by the Arcwise/UIUC expert corrections. Next:
   the inverse direction (recall vs. their 498 corrected questions), and
   design-partner adjudication on production SQL.
4. **Benchmark-suite check:** ✅ *done* — 2,568 Spider/BIRD gold queries,
   45/45 candidates real-or-fragile, one gold answer proven wrong by
   execution, one upstream issue filed. See external-corpus table above.

## 5. Qualitative metrics (structured, not vibes)

Collected quarterly from each active team:

- **The disable question:** *"If we turned sqlsure off tomorrow, what would you
  do?"* (shrug / re-enable it / escalate) — the qualitative twin of gate
  survival.
- **Fix-hint usefulness:** per-finding thumbs-up/down on the `fix` text
  (built into the PR comment) — direct rule-quality signal.
- **Trust trajectory:** "do you read the finding or just re-run until
  green?" — detects alert fatigue before suppress rate shows it.
- **War-story capture:** every "it caught X before the board meeting"
  anecdote logged with date and severity — these become the case studies.
- **Vocabulary adoption:** do PR discussions start using *grain / fan-out /
  additive* unprompted? Cheap proxy for the tool teaching the team.

## 6. What we will not claim

- No "X% of all SQL bugs caught" — recall over an open universe is
  unknowable; we state recall *on defined bug classes* only.
- No incident-cost dollars invented by us — only partner-computed ROI.
- No coverage numbers without the denominator (0 errors on a repo with 0
  declared edges is silence, not safety — the scanner reports both).

Sources: [SQLens: error detection & correction in text-to-SQL](https://arxiv.org/pdf/2506.04494) ·
[Understanding, Detecting, and Repairing Real-World ICL Text-to-SQL Errors](https://arxiv.org/pdf/2501.09310) ·
[BIRD benchmark noise analysis](https://arxiv.org/pdf/2402.12243) ·
[Pervasive annotation errors in text-to-SQL benchmarks](https://arxiv.org/pdf/2601.08778)
