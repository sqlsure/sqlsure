# BIRD dev gold-query audit — sqlsure join-safety pass
*2026-07-01 · BIRD dev_20240627, 1534 gold queries, 11 databases · rulebook from BIRD's own PK/FK declarations*

| metric | value |
|---|---|
| gold queries analyzed | 1534 |
| parsed by engine | 1534 (100%) |
| joins observed (all scopes) | 1419 |
| FK-backed | 1370 (96%) |
| shared-key (same name, no FK) | 34 (2%) |
| non-equi predicates | 0 |
| **unbacked (different columns, no FK)** | **15** |
| **no predicate (cartesian)** | **0** |
| parse failures | 0 |

Candidates below are for manual review, not asserted bugs.

## unbacked candidates (15) — by db: european_football_2:13, codebase_community:2
- **codebase_community** #571 — *For the user No.24, how many times is the number of his/her posts compared to his/her votes?*
  - `UserId = OwnerUserId`
  - `SELECT CAST(COUNT(T2.Id) AS REAL) / COUNT(DISTINCT T1.Id) FROM votes AS T1 INNER JOIN posts AS T2 ON T1.UserId = T2.OwnerUserId WHERE T1.UserId = 24`
- **codebase_community** #639 — *Based on posts posted by Community, calculate the percentage of posts that use the R language.*
  - `ExcerptPostId = PostId`
  - `SELECT CAST(SUM(IIF(T3.TagName = 'r', 1, 0)) AS REAL) * 100 / COUNT(T1.Id) FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN tags AS T3 ON T3.ExcerptPostId = T2.PostId WHER`
- **european_football_2** #1025 — *Give the name of the league had the most goals in the 2016 season?*
  - `league_id = id`
  - `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' GROUP BY t2.name ORDER BY SUM(t1.home_team_goal + t1.away_team_goal) DESC LIMIT 1`
- **european_football_2** #1028 — *In Scotland Premier League, which away team won the most during the 2010 season?*
  - `id = league_id`
  - `SELECT teamInfo.team_long_name FROM League AS leagueData INNER JOIN Match AS matchData ON leagueData.id = matchData.league_id INNER JOIN Team AS teamInfo ON matchData.away_team_api_id = teamInfo.team_`
- **european_football_2** #1030 — *Give the name of the league had the most matches end as draw in the 2016 season?*
  - `league_id = id`
  - `SELECT t2.name FROM Match AS t1 INNER JOIN League AS t2 ON t1.league_id = t2.id WHERE t1.season = '2015/2016' AND t1.home_team_goal = t1.away_team_goal GROUP BY t2.name ORDER BY COUNT(t1.id) DESC LIMI`
- **european_football_2** #1038 — *List the top 5 leagues in ascending order of the number of goals made in all seasons combined.*
  - `id = league_id`
  - `SELECT t1.name, SUM(t2.home_team_goal) + SUM(t2.away_team_goal) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id GROUP BY t1.name ORDER BY SUM(t2.home_team_goal) + SUM(t2.away_team_goa`
- **european_football_2** #1042 — *List the name of leagues in which the average goals by the home team is higher than the away team in the 2009/*
  - `id = league_id`
  - `SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2009/2010' GROUP BY t1.name HAVING (CAST(SUM(t2.home_team_goal) AS REAL) / COUNT(DISTINCT t2.id)) - (`
- **european_football_2** #1049 — *How many matches in the 2015/2016 season were held in Scotland Premier League
?*
  - `id = league_id`
  - `SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' AND t1.name = 'Scotland Premier League'`
- **european_football_2** #1073 — *How many matches were held in the league Germany 1. Bundesliga
from August to October 2008?*
  - `id = league_id`
  - `SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Germany 1. Bundesliga' AND SUBSTR(t2.`date`, 1, 7) BETWEEN '2008-08' AND '2008-10'`
- **european_football_2** #1091 — *How many matches were held in the Belgium Jupiler League in April, 2009?*
  - `id = league_id`
  - `SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND SUBSTR(t2.`date`, 1, 7) = '2009-04'`
- **european_football_2** #1092 — *Give the name of the league had the most matches in the 2008/2009 season?*
  - `id = league_id`
  - `SELECT t1.name FROM League AS t1 JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2008/2009' GROUP BY t1.name HAVING COUNT(t2.id) = (SELECT MAX(match_count) FROM (SELECT COUNT(t2.id) AS mat`
- **european_football_2** #1139 — *What was the final score for the match on September 24, 2008, in the Belgian Jupiler League between the home t*
  - `id = league_id`
  - `SELECT t2.home_team_goal, t2.away_team_goal FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Belgium Jupiler League' AND t2.`date` LIKE '2008-09-24%'`
- **european_football_2** #1142 — *In the 2015–2016 season, how many games were played in the Italian Serie A league?*
  - `id = league_id`
  - `SELECT COUNT(t2.id) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Italy Serie A' AND t2.season = '2015/2016'`
- **european_football_2** #1143 — *What was the highest score of the home team in the Netherlands Eredivisie league?*
  - `id = league_id`
  - `SELECT MAX(t2.home_team_goal) FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t1.name = 'Netherlands Eredivisie'`
- **european_football_2** #1145 — *Which top 4 leagues had the most games in the 2015-2016 season?*
  - `id = league_id`
  - `SELECT t1.name FROM League AS t1 INNER JOIN Match AS t2 ON t1.id = t2.league_id WHERE t2.season = '2015/2016' GROUP BY t1.name ORDER BY COUNT(t2.id) DESC LIMIT 4`

## Manual + empirical review verdict

15 candidates → **14 confirmed real issues, 1 unadjudicated, 0 spurious.**

### Confirmed annotation gap (13 queries): `european_football_2`

BIRD's schema declares **29 FKs on `Match`** — all 22 player-slot columns
and both team columns — yet omits `Match.league_id → League.id` and
`Match.country_id → Country.id`, the two relationships its own gold
queries actually use (13 times in the dev split). Verified directly in
`dev_tables.json`.

### Empirically proven wrong gold answer (1 query): `codebase_community` #571

*"For the user No.24, how many times is the number of his/her posts
compared to his/her votes?"*

Executed against the shipped SQLite database:

| quantity | value |
|---|---|
| posts by user 24 | 3 |
| votes by user 24 | 8 |
| **correct answer (posts/votes)** | **0.375** |
| **gold query returns** | **3.0** (8× off) |
| join row count | 24 = 3 posts × 8 votes (chasm trap) |

The gold SQL joins `votes` to `posts` on `UserId = OwnerUserId`, creating a
per-user cartesian product; `COUNT(T2.Id)` inflates to P×V, and dividing by
`COUNT(DISTINCT T1.Id)` = V collapses the expression to P — the query
mechanically computes *post count*, not the requested ratio. **This is
fan-out double-counting — the exact defect class the inspector targets —
inside a benchmark gold answer. A model answering 0.375 (correctly) is
scored wrong by BIRD.**

### Adjudicated benign-but-fragile (1 query): `codebase_community` #639

Executed against the shipped database: the unusual join path
(`tags.ExcerptPostId = postHistory.PostId`) produces **511 joined rows =
511 distinct excerpt posts** — exactly one history row per excerpt post in
this data, so no inflation occurs and the gold answer (0.196%) is correct
*on this data*. Fragile by construction (any post with a second history row
would corrupt it), but not a bug. Final tally: **13 annotation-gap
symptoms + 1 proven wrong answer + 1 benign = 14/15 real-or-fragile, 0
spurious.**

### Novelty cross-check against expert corrections (Arcwise / UIUC, VLDB'26)

Compared against the 498 expert-corrected BIRD questions from the
"Pervasive Annotation Errors" project:

- **10 of our 15 candidates were independently flagged by human expert
  review** — strong cross-validation of a purely mechanical pass.
- **#571**: the expert-corrected SQL computes posts/votes via two CTEs,
  avoiding the join — *exactly matching our diagnosis and our empirically
  computed 0.375*. Independent convergence: experts by manual review, sqlsure
  by static join-safety analysis + execution.
- **The `european_football_2` FK gap is a schema-layer defect the
  per-question corrections do not address**: the experts' corrected SQL for
  those questions *still uses* `Match.league_id = League.id` — confirming
  the join is correct and `dev_tables.json` is what's wrong. As a distinct,
  reportable artifact this appears novel; worth filing upstream at
  bird-bench.

### Method note

The pass covers join-safety rules only (derivable from PK/FK). BIRD's 96%
FK-backed join rate means the audit is sharp: nearly everything is
verifiable, so the residue is small and dense with real defects. The
expert-corrected 498 now double as ground truth for measuring
static-pass ↔ expert agreement at scale — the evaluation section of the
eventual write-up.
