# sqlsure for Dummies

*Every concept in this project, explained simply. No prior data-engineering
knowledge assumed. Read top to bottom — each idea builds on the last.*

---

## 1. The problem in one story

You ask a question of your company's data: *"How much did we spend per
patient?"* Someone — or some AI — writes a SQL query. The database runs it
happily. A number comes out: **$4.2M**.

The real answer is $2.1M. The query counted every dollar twice. **No error
message. No warning. Nothing looked wrong.** That's the entire problem sqlsure
exists to solve: SQL that is *valid* but *wrong*, and wrong silently.

## 2. Why does SQL double-count? (the "fan-out")

Imagine a spreadsheet of hospital visits — one row per visit:

| visit | patient | cost |
|---|---|---|
| V1 | Ana | $100 |
| V2 | Ben | $200 |

Now you "join" it to a list of diagnoses. But **one visit can have many
diagnoses**. V1 had two diagnoses, so after joining, V1's row appears twice:

| visit | patient | cost | diagnosis |
|---|---|---|---|
| V1 | Ana | $100 | flu |
| V1 | Ana | **$100** | dehydration |
| V2 | Ben | $200 | fracture |

Sum the cost column now and you get **$400 instead of $300**. The join
"fanned out" — one row became two — and the money duplicated with it.

**Important: nobody designed that doubled table, and it is not stored
anywhere.** Both source tables are perfectly normalized — visits hold one
fact per row, diagnoses hold one fact per row; a textbook schema. The
doubled table is the *intermediate result the database engine builds in
the middle of your query*, invisibly, whenever you join one-to-many. So
this is not a bad-database-design problem you could fix upstream: any
schema with a one-to-many relationship — which is every schema — produces
this intermediate the moment a query joins across it and sums the "one"
side. The design is fine; the *query* summed at the wrong moment. That's
why it's the most expensive silent bug in analytics, and why databases do
not catch it: nothing is *technically* wrong.

## 3. The vocabulary (five words, that's all)

- **Grain** — what one row means. "One row per visit." "One row per
  patient." Mixing grains without care is how numbers go wrong.
- **Fan-out** — a join that turns one row into many (visit → diagnoses).
  Sums and counts inflate.
- **Additive** — safe to sum. Cost is additive: $100 + $200 makes sense.
- **Non-additive** — never sum it. An *average* length of stay of 3 days
  plus another of 4 days is not "7 days of average." Averages, rates, and
  percentages can't be added.
- **Semi-additive** — summable in some directions but not across time.
  Hospital beds occupied: you can sum across wards *on one day*, but summing
  Monday's 30 beds + Tuesday's 30 beds ≠ 60 beds — it's the same 30 beds
  counted twice.

## 4. What is a "semantic model"?

Just a small file of facts about your tables — the rulebook:

- `fct_encounters` has one row per `encounter_id` *(grain)*
- `cost` is additive; `avg_los` is non-additive *(what's safe to sum)*
- joining encounters→diagnoses fans out; encounters→patients doesn't
  *(join safety)*
- `patient_name` and `ssn` are private health information *(policy)*

Good news: **most teams already declare much of this** — dbt tests
("this column is unique," "this key must exist in that table") imply grain
and join safety. sqlsure reads those declarations; nobody writes the rulebook
from scratch.

## 5. What is sqlsure, in one sentence?

**A building inspector for SQL.** You hand it a query (the blueprint) and
the rulebook. It answers APPROVED or REJECTED — *before* the query runs —
and when it rejects, it tells you exactly how to fix it:

```
✗ FANOUT: SUM(cost) after one-to-many join to dim_diagnosis
  — cost will be double-counted.
  fix: Pre-aggregate fct_encounters to encounter_id first.
```

sqlsure does not write SQL. It does not run SQL. It only *judges* SQL. That
narrowness is deliberate — judges that also play the game stop being
trusted.

## 6. How does it actually work inside? (30 seconds of engineering)

1. A parser (sqlglot) turns the SQL text into a tree — an **AST** — the way
   grammar breaks a sentence into subject/verb/object. Pure structure, no
   meaning.
2. sqlsure walks that tree and pulls out facts: base table, joins and their
   keys, what's being summed, what's grouped.
3. Each **rule** compares those facts to the rulebook. Summing an additive
   measure after a fan-out join? Violation. Joining on the wrong key?
   Violation. Selecting an SSN? Policy violation.

AST = the grammar of one query. Semantic model = the meaning and the rules.
sqlsure = the thing that holds both and says yes or no.

## 7. Why now? (the AI angle)

Humans wrote wrong SQL occasionally. **AI writes SQL constantly** — Claude,
Cursor, and every "chat with your data" product generate thousands of
queries, and they make exactly these mistakes: wrong join keys, fan-outs,
summed averages. An occasional problem became an hourly one.

But there's a flip side: an AI, unlike a human, will *instantly obey* a fix
hint. So the loop becomes: **AI drafts → sqlsure rejects with fix → AI repairs →
sqlsure approves → query runs.** The wrong number never reaches a human. That
loop is the product.

## 8. How do people actually use it? (the three doors)

Same engine, three entrances:

1. **GitHub / CI** — installed once on a repo; every pull request gets
   checked automatically and violations appear as PR comments. Humans do
   nothing; that's the point.
2. **MCP** — the plug standard AI assistants use for tools. Register sqlsure,
   and the AI *itself* calls `check_sql` before running anything.
3. **Library / API** — companies building data-AI products embed
   `check(sql, model)` inside their own loop.

## 9. What sqlsure is NOT (as important as what it is)

- **Not a semantic layer** (dbt/Cube/Looker define metrics; sqlsure *enforces*
  what's already defined — it consumes their rulebooks, it doesn't compete).
- **Not a SQL generator** — it never writes or rewrites queries itself.
- **Not a style linter** (SQLFluff cares about formatting; sqlsure cares about
  whether the *number is right*).
- **Not omniscient** — when it can't verify something (an undeclared join),
  it says "can't verify," never "looks fine." Honest uncertainty is a
  feature.

## 10. The words you'll hear, decoded

| Term | Plain meaning |
|---|---|
| dbt | The standard tool teams use to build data tables with SQL + tests |
| manifest.json | dbt's machine-readable inventory of all models and tests — sqlsure's favorite food |
| Semantic layer | A curated menu of official metrics (dbt SL, Cube, Looker) |
| Snowflake Semantic Views | Snowflake's built-in rulebook format — sqlsure can read it |
| OSI | New industry standard (2026) so every tool shares one rulebook format |
| MCP | The USB port that lets AI assistants call tools like sqlsure |
| Fan-out / chasm trap | One row becomes many after a join / two fan-outs multiplying |
| CI | Robots that check code automatically on every change |
| PHI / PII | Private health / personal info — columns sqlsure can gate by policy |

## 11. The tests we ran, explained simply

We tested sqlsure four ways, each harder and more honest than the last. Think
of sqlsure as a **smoke detector for SQL** — here's how you'd test a smoke
detector, and what each test can and cannot prove.

### Test 1: The factory check (unit tests — 16/16 passed)

**What we did:** for each of the 9 rules, we wrote one tiny example that
*should* set it off and one that *shouldn't*, and checked both.
**What it measures:** does each part do its one job?
**Why it's a fair measure:** it's the same reason every appliance gets
tested before leaving the factory. It proves the parts work.
**What it can't prove:** anything about the real world. A detector that
passes the factory check can still miss a real fire.

### Test 2: Controlled fires and candles (the utility benchmark)

**What we did:** wrote 11 queries each hiding one known bug ("fires") and
10 correct queries deliberately built to *look* suspicious ("candles" —
things that resemble bugs but are fine). Then we followed the tool's own
fix instructions word-for-word and re-checked. And we timed everything.
**Results, in plain words:**
- Caught **all 11 fires**, and named the right problem each time.
- Stayed **silent on all 10 candles** — no crying wolf. This matters most:
  a smoke detector that shrieks at toast gets its battery pulled.
- Following the fix text produced a passing query **10 out of 10 times** —
  so an AI can fix itself using our message alone.
- Each check takes **a tenth of a millisecond** — checking is free.
**What it can't prove:** we lit the fires ourselves. We knew where they
were. This is a rigged demo *by design* — legitimate for "does the machine
do what the label says," useless for "how good is it in the wild."

### Test 3: Walking into real kitchens (the repo scans)

**What we did:** pointed the scanner at real companies' public code — dbt's
own demo project, a Fivetran package, and Mattermost's actual production
data warehouse (489 files).
**What it measures:** does the tool survive contact with messy reality —
weird templating, huge files, code written by strangers?
**Result, in plain words:** it ran end-to-end, and found something nobody
expected: in Mattermost's production code, **0 of the 128 table-joins could
be verified** — not because they're wrong, but because nobody ever wrote
down the rules (which joins are safe, what one row means). Like inspecting
a building and discovering there are no blueprints on file.
**Why that's still a win:** "you have no blueprints" is a sellable finding.
The first thing sqlsure gives a real team isn't caught bugs — it's a map of
what *can't be checked* and the shortest list of declarations to fix that.

### Test 4: Grading the answer key (the Spider & BIRD audits) — the big one

**The setup, simply:** Spider and BIRD are the two famous exams used to
grade AI systems that write SQL. Each exam ships an **answer key** —
human-written "gold" queries. Thousands of AI models are scored against
these keys. If the key has wrong answers, everyone's grades are wrong.

**What we did:** ran sqlsure over the *answer keys themselves* — 2,568 gold
queries total — using each exam's own published table-relationship rules
as the rulebook. No human labeling; the machine flagged, then we verified
every flag by hand (and, for BIRD, by running the actual data).

**What it measures — and this is the key point:** this is the first test
where the queries were written by *other people*, with no idea our tool
would ever exist. It measures two things at once:
1. **Does the tool cry wolf on strangers' code?** (precision)
2. **Can it find real problems nobody planted?** (usefulness)

**Results, in plain words:**
- Out of 2,568 queries, sqlsure raised its hand **45 times**. Every single
  raise traced to something genuinely wrong or genuinely fragile —
  **zero false alarms on code we didn't write.**
- On Spider: all 30 flags pointed to one real defect — a database whose
  declared "primary key" is impossible (it says an airline identifies a
  flight — but one airline has many flights) and whose most important
  table-link was never declared.
- On BIRD: 13 flags exposed a missing link declaration (the schema
  carefully declares 29 links on the Match table — every player slot! —
  but forgot the league link its own answers use 13 times). And **one flag
  found an actually-wrong answer in the answer key**: a question asks
  "posts compared to votes" (true answer: 3 ÷ 8 = 0.375) but the gold
  query's bad join makes it answer **3.0 — eight times off**. We proved it
  by running the exam's own database. Any AI that answers this question
  *correctly* is marked *wrong*.
- **Independent confirmation:** a university team (VLDB 2026) had experts
  manually fix errors in BIRD. **10 of our 15 flags match what their
  humans found** — including the wrong answer above, where their expert
  fix computes exactly the number we computed. Their humans took an expert
  review process; our machine took two seconds. And one of our findings
  (the missing link declaration) is a layer their fixes never touched —
  likely a new discovery to report to the benchmark's maintainers.

**Why this is a good measure:** it has the three things Test 2 lacked —
strangers' code (no rigging possible), ground truth (real databases to
execute against), and independent judges (the expert corrections we didn't
know about until after our results). When a mechanical two-second pass
agrees with a panel of human experts and additionally proves its case by
running the data, that's as close to "objectively useful" as a young tool
gets.

**The one-sentence takeaway:** *the smoke detector walked into the exam
hall that grades all the other smoke detectors, and found smoke.*

## 12. The elevator pitch, three ways

- **To an engineer:** "A deterministic semantic gate for SQL — catches
  fan-out double-counting, additivity violations, and wrong join keys in CI
  and in agent loops, from the tests you already wrote."
- **To a data leader:** "Your AI and your analysts ship numbers to execs.
  This is the automatic check that the numbers aren't silently double-
  counted — with an audit trail."
- **To your parent:** "Computers answer money questions by gluing
  spreadsheets together, and there's a classic way the gluing counts things
  twice. I built the checker that catches it before anyone sees the wrong
  number."

## 13. The results, one line each

| Test | Plain-words result |
|---|---|
| Factory check | All 9 rules do their job (16/16) |
| Fires & candles | Caught every planted bug, zero false alarms, fixes itself, costs nothing to run |
| Real kitchens | Survives production code; revealed that real teams have no "blueprints" to check against — which is itself the sales pitch |
| Grading the answer key | 2,568 strangers' queries → 45 flags → all real, none false; one exam answer proven wrong by 8×; 10/15 flags independently confirmed by human experts |

---

# The Study Plan — own this project in five sittings

*Goal: by the end, you can explain every piece of sqlsure — what it is, what
was proven, and why it matters — to an engineer, an investor, or a
skeptic, without notes. Each sitting is ~45 minutes: read, run, then
explain out loud. The explaining is the actual study method — if you can't
say it simply, you don't have it yet.*

## Sitting 1 — The problem (why this exists)

**Read:** §1–3 of this doc (the wrong-number story, the fan-out
spreadsheet, the five vocabulary words).
**Run:**
```bash
python check.py
```
Watch five bad queries get rejected and one good one pass. For each
rejection, read the `fix:` line and connect it to the vocabulary word
(fan-out → pre-aggregate; non-additive → use AVG; PHI → policy).
**Explain out loud:** the two-row hospital table from §2 — why does $300
become $400? If you can draw it on a napkin, sitting 1 is done.
**Self-test:** Why doesn't the database itself catch this? *(Because the
query is syntactically valid — the database checks grammar, not meaning.)*

## Sitting 2 — The machine (how it works)

**Read:** §4–6 (semantic model, the inspector, AST vs rulebook), then skim
the actual rule code in [sqlsure/rules.py](../sqlsure/rules.py) — read just the
docstrings and the message strings; ignore the mechanics.
**Run:**
```bash
python tests/run_tests.py
python -m sqlsure.cli --model model.example.json --json <<< "SELECT SUM(avg_los) FROM fct_encounters"
```
**Explain out loud:** the three parts — parser (SQL → tree), model (the
facts), rules (tree × facts → violations) — and why sqlsure *judges* SQL but
never writes it.
**Self-test:** What's the difference between an AST and the semantic
model? *(AST = grammar of one query, no meaning; model = the meaning and
the rules the query is judged against.)*

## Sitting 3 — The measurements (what was proven, honestly)

**Read:** §11–13 above (the four tests), then
[reports/benchmark.md](reports/benchmark.md).
**Run:**
```bash
python benchmarks/benchmark.py
```
**Explain out loud:** why "zero false alarms" matters more than "caught
everything" *(one wrong shriek and the battery gets pulled)*, and why the
fires-and-candles test is legitimate but not sufficient *(we lit the fires
ourselves)*.
**Self-test:** Which single number in the benchmark proves the AI
self-repair loop works? *(Fix-hint actionability, 10/10 — following the
error message verbatim always produced a passing query.)*

## Sitting 4 — The discovery (the benchmark audits)

**Read:** [reports/spider-audit.md](reports/spider-audit.md) and
[reports/bird-audit.md](reports/bird-audit.md) — the verdict sections
especially — plus the filed issue:
[bird-bench/mini_dev#37](https://github.com/bird-bench/mini_dev/issues/37).
**Run (the proof, yourself):**
```bash
python benchmarks/audit_bird.py --data birddata/dev_20240627
```
**Explain out loud, in order:** (1) what Spider/BIRD are *(the exams that
grade SQL-writing AIs)*; (2) what we did *(inspected the answer keys)*;
(3) the three escalating proofs — flagged mechanically → verified by hand
→ proven by running the actual database; (4) the 8×-wrong answer story
end-to-end: 3 posts, 8 votes, correct answer 0.375, gold says 3.0, because
the join multiplied rows 3×8=24.
**Self-test:** Why does 10/15 overlap with expert corrections make our
result *stronger* rather than redundant? *(Independent convergence: humans
via expert review and a machine via a 2-second static pass found the same
errors — each validates the other. And the machine found a schema-layer
defect the human per-question fixes never touched.)*

## Sitting 5 — The positioning (why this and not something else)

**Read:** [METRICS.md](METRICS.md) (skim the tables) and
[INTEGRATIONS.md](INTEGRATIONS.md) (the decision table at the top).
**Explain out loud:** the three doors (CI, MCP, library) and why
*placement* beats *more rules* — a check nobody runs is documentation.
**Self-test:** Someone says "dbt Fusion will just add this." Your answer?
*(Fusion checks compilation — columns, types — explicitly not fan-out or
additivity; it only covers dbt projects, not arbitrary agent SQL; and if
they do add it, they validate the category while sqlsure holds the
vendor-neutral position.)*

## The final exam (no notes)

Answer these five out loud in under three minutes total:
1. What does sqlsure do, in one sentence, to your parent?
2. What's a fan-out, on a napkin?
3. What did the benchmark audit prove, and what made the proof airtight?
4. Why is "zero false alarms on strangers' code" the number that matters?
5. Why does a smarter SQL-writing model not make the judge unnecessary?

If all five come out clean, you don't just have a project — you have the
talk and the blog post already rehearsed.

## Map of every document

| Doc | One-liner | Audience |
|---|---|---|
| [README.md](../README.md) | What it is + how to run it | engineers |
| this file | Every concept from zero + study plan | everyone |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The machine, physically: tokens → AST → facts → rules, with real outputs | Sitting 2 companion |
| [INTEGRATIONS.md](INTEGRATIONS.md) | CI, MCP, Snowflake, audit-mode recipes | deployers |
| [MCP.md](MCP.md) | The MCP server, tool reference, agent loop | agent builders |
| [METRICS.md](METRICS.md) | What's measured vs claimed | skeptics |
| [TEST-REPORTS.md](TEST-REPORTS.md) | Validation log, all findings | reviewers |
| [reports/](reports/) | Raw generated scan/audit reports | evidence |
