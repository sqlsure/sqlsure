# Deterministic gate vs LLM-as-judge: a measured comparison

*2026-07-04 · script: [`benchmarks/experiment_gate_vs_judge.py`](../../benchmarks/experiment_gate_vs_judge.py)*

## Question

When an AI agent generates SQL, what does each guardrail pattern actually
buy you — in accuracy, tokens, dollars, and latency?

## Setup

Three arms share the same first draft per question (Claude Haiku via
headless CLI, schema-in-prompt, BIRD dev databases, execution-accuracy
scored against gold query results on the real SQLite files):

- **A — bare:** draft → execute.
- **B — sqlsure gate:** draft → `check()` against a rulebook
  **introspected from the live database** (`sqlsure.introspect`, zero
  authoring) → if flagged, ONE repair round with the violation fix hints →
  execute.
- **C — LLM-as-judge:** draft → a judge model reviews for semantic errors
  (the industry-default pattern) → if rejected, ONE repair round with the
  judge's feedback → execute.

Main run: 24 questions whose gold SQL contains JOIN + SUM/COUNT/AVG
(fan-out-prone shapes), round-robined across BIRD dev databases.

## Results (main run, n=24)

| arm | execution accuracy | guardrail tokens (in/out) | guardrail $ | check latency |
|---|---|---|---|---|
| A bare | 15/24 (62%) | — | — | — |
| B sqlsure gate | 15/24 (62%) | 103k/5.4k (repairs only; checks: **0**) | **$0.12** | **0.7 ms** median |
| C LLM judge | 15/24 (62%) | 518k/44.5k | **$0.71** | seconds per check |

(Guardrail cost = arm total minus the shared draft cost of $0.61.)

- **Same accuracy in all three arms.** Every failure was an
  interpretation miss (wrong column, missing filter) identical across
  arms — the ambiguity class that CIDR'24 "NL2SQL is a solved problem…
  Not!" estimates at ~41% of benchmark questions. No guardrail fixes
  intent; that is judgment work, not verification work.
- **The judge's only rejections were false alarms.** Across both runs
  (44 checks total) the judge rejected 2 drafts — both were actually
  correct. Verdict quality did not justify the spend: ~42k tokens and
  ~$0.05–0.06 per check to change zero outcomes.
- **The gate flagged 5/24 drafts** (3 FANOUT warnings on genuinely
  fan-out-shaped joins, 2 UNDECLARED_JOIN), all soft; the repair round
  never degraded a correct query (5/5 outcome-preserving). The check
  itself costs nothing and runs in under a millisecond.
- Extrapolated to 10,000 agent queries/day: judge-per-query ≈ **$550/day**
  at these rates; the deterministic gate ≈ **$0/day** plus repair tokens
  only when something is actually flagged.

## What the dry run caught (and why we publish it)

The first run (n=20, codebase_community) showed the gate arm *losing*
accuracy: 14/20 vs 18/20 bare. Root causes, both real and both fixed:

1. **A shipping bug in sqlsure:** identifier comparison was
   case-sensitive, so CamelCase drafts (`posts.OwnerUserId = users.Id`)
   drew spurious JOIN_KEY errors against lowercase rulebooks — 13/20
   drafts falsely flagged. After normalizing (unquoted SQL identifiers
   are case-insensitive), re-checking the same stored drafts yields
   **1/20 flagged** (a legitimate FANOUT warning). Fixed in
   `checker.py`/`model.py` with regression tests.
2. A harness bug: the repair model sometimes appended prose to its SQL;
   the extractor now trims to the longest parseable statement.

## Honest limits

- n=44 total drafts, one generator (Haiku), one repair round, BIRD dev
  only. Gold execution results are treated as ground truth even though
  our own audit shows the gold set contains defects.
- **No accuracy gain observed for either guardrail.** On short
  benchmark questions, a competent generator rarely commits the fan-out
  class the gate exists for; the catastrophic cases documented elsewhere
  (BIRD #571's 8×, multi-fact enterprise joins) are tail events. The
  measured claim is therefore about **cost, latency, consistency, and
  false-alarm quality** — not average-case accuracy on this set.
- Judge verdict variance across repeated calls was not measured here
  (single-shot verdicts); it is documented in the literature.

## Takeaway

Same accuracy, three orders of magnitude less latency, and a guardrail
bill of $0 instead of ~$0.05/query: for the checkable-by-lookup class of
SQL errors, spend tokens on ambiguity, not on arithmetic.
