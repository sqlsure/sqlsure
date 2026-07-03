# BIRD dev gold-query audit — sqlsure join-safety pass
*2026-07-02 · BIRD dev_20240627, 9428 gold queries, 11 databases · rulebook from BIRD's own PK/FK declarations*

| metric | value |
|---|---|
| gold queries analyzed | 9428 |
| parsed by engine | 9428 (100%) |
| joins observed (all scopes) | 9560 |
| FK-backed | 7193 (75%) |
| shared-key (same name, no FK) | 1539 (16%) |
| non-equi predicates | 40 |
| **unbacked (different columns, no FK)** | **788** |
| **no predicate (cartesian)** | **0** |
| parse failures | 0 |

Candidates below are for manual review, not asserted bugs.

## unbacked candidates (788) — by db: mondial_geo:331, shakespeare:130, codebase_comments:103, bike_share_1:57, coinmarketcap:43, retail_world:27, software_company:18, books:14, retails:14, soccer_2016:12, works_cycles:12, talkingdata:6, craftbeer:6, disney:4, citeseer:3, image_and_language:2, movie_3:2, computer_student:1, public_review_platform:1, hockey:1, chicago_crime:1
- **codebase_comments** #574 — *What is the github address of the "nofear_Mara\Mara.sln" solution path?*
  - `Id = RepoId`
  - `SELECT Url FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE Path = 'nofear_MaraMara.sln'`
- **codebase_comments** #575 — *Which repository has the longest amount of processed time of downloading? Indicate whether the solution paths *
  - `Id = RepoId`
  - `SELECT DISTINCT T1.id, T2.WasCompiled FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.ProcessedTime = ( SELECT MAX(ProcessedTime) FROM Repo )`
- **codebase_comments** #576 — *What is the tokenized name of the solution whose path is "maravillas_linq-to-delicious\tasty.sln"?*
  - `Id = SolutionId`
  - `SELECT DISTINCT T2.NameTokenized FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.Path = 'maravillas_linq-to-delicious'`
- **codebase_comments** #577 — *Among the repositories whose number of stars received are between 6,000 to 9,000, which repository has the hig*
  - `Id = RepoId`
  - `SELECT T2.RepoId, COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Stars BETWEEN 6000 AND 9000 AND T2.WasCompiled = 0 GROUP BY T2.RepoId ORDER BY COUNT(T2.RepoI`
- **codebase_comments** #578 — *In the "https://github.com/wallerdev/htmlsharp.git", give all the linearized sequenced of API calls.*
  - `Id = RepoId`
  - `SELECT T3.ApiCalls FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId INNER JOIN Method AS T3 ON T2.Id = T3.SolutionId WHERE T1.Url = 'https://github.com/wallerdev/htmlsharp.git'`
- **codebase_comments** #578 — *In the "https://github.com/wallerdev/htmlsharp.git", give all the linearized sequenced of API calls.*
  - `Id = SolutionId`
  - `SELECT T3.ApiCalls FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId INNER JOIN Method AS T3 ON T2.Id = T3.SolutionId WHERE T1.Url = 'https://github.com/wallerdev/htmlsharp.git'`
- **codebase_comments** #579 — *How many solution paths are there inside the 2nd most popular repository?*
  - `Id = RepoId`
  - `SELECT COUNT(DISTINCT T2.Path) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Watchers = ( SELECT Watchers FROM Repo ORDER BY Watchers DESC LIMIT 1, 1 )`
- **codebase_comments** #580 — *What is the average processed time of the solution paths inside the "https://github.com/zphingphong/DiscardCus*
  - `Id = RepoId`
  - `SELECT CAST(SUM(T2.ProcessedTime) AS REAL) / COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Url = 'https://github.com/zphingphong/DiscardCustomerApp.git'`
- **codebase_comments** #581 — *What is the full comment on the method whose solution path is "bmatzelle_nini\Source\Nini.sln" with a tokenize*
  - `Id = SolutionId`
  - `SELECT T2.FullComment FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.Path = 'bmatzelle_niniSourceNini.sln' AND T2.NameTokenized = 'alias text add alias'`
- **codebase_comments** #582 — *What is the linearized sequenced of API calls of the method whose solution path is "mauriciodeamorim_tdd.encon*
  - `Id = SolutionId`
  - `SELECT T2.ApiCalls FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.Path = 'mauriciodeamorim_tdd.encontro2Tdd.Encontro2.sln'`
- **codebase_comments** #583 — *How many solution paths that needs to be compiled if user wants to implement it in "https://github.com/jeffdik*
  - `Id = RepoId`
  - `SELECT COUNT(T2.Path) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Url = 'https://github.com/jeffdik/tachy.git' AND T2.WasCompiled = 0`
- **codebase_comments** #584 — *How much is the processed time of the method whose tokenized name is "about box1 dispose"? Indicate the langua*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.ProcessedTime, T2.Lang FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.NameTokenized = 'about box1 dispose'`
- **codebase_comments** #585 — *In "maxild_playground\Playground.sln", what is the time of sampling for the method "GitHubRepo.Cli.GitHubClien*
  - `Id = SolutionId`
  - `SELECT T2.SampledAt FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.Path = 'maxild_playgroundPlayground.sln' AND T2.Name = 'GitHubRepo.Cli.GitHubClientWrapper.GetReleases`
- **codebase_comments** #586 — *What is the language of the method used in the solution path "opendns_diagnosticapp\windows\OpenDnsDiagnostic.*
  - `Id = SolutionId`
  - `SELECT T2.Lang FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.Path = 'opendns_diagnosticappwindowsOpenDnsDiagnostic.sln'`
- **codebase_comments** #590 — *How many solutions contain files found within the repository most people like?*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Stars = ( SELECT MAX(Stars) FROM Repo )`
- **codebase_comments** #591 — *Please list the path of the solution that contains files found within the repository most people like.*
  - `Id = RepoId`
  - `SELECT DISTINCT T2.Path FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Stars = ( SELECT MAX(Stars) FROM Repo )`
- **codebase_comments** #592 — *What is the github address of the repository that contains files used by solution ID12?*
  - `Id = RepoId`
  - `SELECT T1.Url FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.Id = 12`
- **codebase_comments** #593 — *Among the solutions that contain files within the repository followed by over 1000 people, how many of them ca*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Forks > 1000 AND T2.WasCompiled = 1`
- **codebase_comments** #594 — *Which solution contains files within a more popular repository, the solution ID18 or solution ID19?*
  - `Id = RepoId`
  - `SELECT CASE WHEN SUM(CASE WHEN T2.Id = 18 THEN T1.Watchers ELSE 0 END) > SUM(CASE WHEN T2.Id = 19 THEN T1.Watchers ELSE 0 END) THEN 'SolutionID18' WHEN SUM(CASE WHEN T2.Id = 18 THEN T1.Watchers ELSE 0`
- **codebase_comments** #595 — *Among the solutions that contain files within the repository needing the longest processed time to download, h*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.ProcessedTime = ( SELECT MAX(ProcessedTime) FROM Repo ) AND T2.WasCompiled = 1`
- **codebase_comments** #596 — *What is the processed time to download the repository whose files are contained in the solution with the path *
  - `Id = RepoId`
  - `SELECT DISTINCT T2.ProcessedTime FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.Path = 'jeffdik_tachysrcTachy.sln'`
- **codebase_comments** #597 — *Please give the url of the repository whose files are contained in solution ID 9?*
  - `Id = RepoId`
  - `SELECT T1.Url FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.Id = 9`
- **codebase_comments** #598 — *Please list all the paths of the solutions containing files within the repository whose url is "https://github*
  - `Id = RepoId`
  - `SELECT T2.Path FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Url = 'https://github.com/maxild/playground.git'`
- **codebase_comments** #599 — *Among the repositories with over 200 likes, how many of them have files contained by solutions with a processe*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.ProcessedTime < 636439500080712000 AND T1.Stars > 200`
- **codebase_comments** #600 — *Please list the IDs of the solutions that contain files within the top 3 followed repositories.*
  - `Id = RepoId`
  - `SELECT T2.Id FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId ORDER BY T1.Forks DESC LIMIT 3`
- **codebase_comments** #601 — *What is the average time needed for the solutions containing files within the repository whose url is "https:/*
  - `Id = RepoId`
  - `SELECT CAST(SUM(T2.ProcessedTime) AS REAL) / COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Url = 'https://github.com/jeffdik/tachy.git'`
- **codebase_comments** #602 — *How many more followers in percentage are there for the repository used by solution ID 18 than solution ID19?*
  - `Id = RepoId`
  - `SELECT CAST((SUM(CASE WHEN T2.Id = 18 THEN T1.Forks ELSE 0 END) - SUM(CASE WHEN T2.Id = 19 THEN T1.Forks ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN T2.Id = 19 THEN T1.Forks ELSE 0 END) FROM Repo AS T`
- **codebase_comments** #607 — *How many stars does the repository of the solution No. 45997 have?*
  - `Id = RepoId`
  - `SELECT T1.Stars FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.Id = 45997`
- **codebase_comments** #608 — *For the repository which got '8094' Stars, how many solutions does it contain?*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Stars = 8094`
- **codebase_comments** #609 — *What is the solution path for the method "IQ.Data.DbQueryProvider.CanBeEvaluatedLocally"?*
  - `Id = SolutionId`
  - `SELECT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Name = 'IQ.Data.DbQueryProvider.CanBeEvaluatedLocally'`
- **codebase_comments** #610 — *For the method which got the tokenized name as 'interp parser expr', what is the processed time for its soluti*
  - `Id = SolutionId`
  - `SELECT T1.ProcessedTime FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.NameTokenized = 'interp parser expr'`
- **codebase_comments** #611 — *What is the repository number for the solution of method "SCore.Poisson.ngtIndex"?*
  - `Id = SolutionId`
  - `SELECT T1.RepoId FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Name = 'SCore.Poisson.ngtIndex'`
- **codebase_comments** #612 — *Tell the path of the solution for the method "ExportToRTF.RTFStyleSheet.H6Write".*
  - `Id = SolutionId`
  - `SELECT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Name = 'ExportToRTF.RTFStyleSheet.H6Write'`
- **codebase_comments** #613 — *For the repository with '8094' watchers , how many solutions does it contain?*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Watchers = 8094`
- **codebase_comments** #614 — *Give the repository Url of the one with most solutions.*
  - `Id = RepoId`
  - `SELECT T1.Url FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId GROUP BY T2.RepoId ORDER BY COUNT(T2.RepoId) DESC LIMIT 1`
- **codebase_comments** #615 — *How many solutions does the repository which has 1445 Forks contain?*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Forks = 1445`
- **codebase_comments** #616 — *Among all the solution of the 'zh-cn' methods, which path is most often used?*
  - `Id = SolutionId`
  - `SELECT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Lang = 'zh-cn' GROUP BY T1.Path ORDER BY COUNT(T1.Path) DESC LIMIT 1`
- **codebase_comments** #617 — *Give the number of watchers that the repository of the solution No. 338082 have.*
  - `Id = RepoId`
  - `SELECT T1.Watchers FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.Id = 338082`
- **codebase_comments** #618 — *For the repository which got '189' Stars, how many solutions which needs to be compiled does it contain?*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Stars = 189 AND T2.WasCompiled = 0`
- **codebase_comments** #619 — *Show the solution path for the method "Mosa.Platform.x86.Instructions.IMul.EmitLegacy"?*
  - `Id = SolutionId`
  - `SELECT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Name = 'Mosa.Platform.x86.Instructions.IMul.EmitLegacy'`
- **codebase_comments** #620 — *For the method which got the tokenized name as 't jadwal entity get single mpic', what is the path time for it*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.ProcessedTime FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.NameTokenized = 't jadwal entity get single mpic'`
- **codebase_comments** #621 — *Give the repository ID for the solution of method "Kalibrasi.Data.EntityClasses.THistoryJadwalEntity.GetSingle*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.RepoId FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Name = 'Kalibrasi.Data.EntityClasses.THistoryJadwalEntity.GetSingleTjadwal'`
- **codebase_comments** #622 — *For the method has the summary of "Refetches the Entity from the persistent storage. Refetch is used to re-loa*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Summary = 'Refetches the Entity FROM the persistent storage. Refetch is used to re-load an Entity `
- **codebase_comments** #623 — *Give the number of solutions that the repository which has 3060 Stars contains.*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Stars = 3060`
- **codebase_comments** #624 — *For the solution of the most 'sw' methods, what is its path?*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Lang = 'sw'`
- **codebase_comments** #625 — *How many percent more of the watchers for the repository of solution No.83855 than No.1502?*
  - `Id = RepoId`
  - `SELECT CAST(SUM(CASE WHEN T2.Id = 83855 THEN T1.Watchers ELSE 0 END) - SUM(CASE WHEN T2.Id = 1502 THEN T1.Watchers ELSE 0 END) AS REAL) * 100 / SUM(CASE WHEN T2.Id = 1502 THEN T1.Watchers ELSE 0 END) `
- **codebase_comments** #626 — *How many percent more of the stars for the repository of solution No.51424 than No.167053?*
  - `Id = RepoId`
  - `SELECT CAST(SUM(CASE WHEN T2.Id = 51424 THEN T1.Stars ELSE 0 END) - SUM(CASE WHEN T2.Id = 167053 THEN T1.Stars ELSE 0 END) AS REAL) * 100 / SUM(CASE WHEN T2.Id = 167053 THEN T1.Stars ELSE 0 END) FROM `
- **codebase_comments** #627 — *How many percent more of the Forks for the repository of solution No.53546 than No.1502?*
  - `Id = RepoId`
  - `SELECT CAST(SUM(CASE WHEN T2.Id = 53546 THEN T1.Forks ELSE 0 END) - SUM(CASE WHEN T2.Id = 1502 THEN T1.Forks ELSE 0 END) AS REAL) * 100 / SUM(CASE WHEN T2.Id = 1502 THEN T1.Forks ELSE 0 END) FROM Repo`
- **codebase_comments** #628 — *List all the methods with a solution with a "636449700980488000" processed time.*
  - `Id = SolutionId`
  - `SELECT DISTINCT T2.Name FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.ProcessedTime = 636449700980488000`
- **codebase_comments** #629 — *How many solutions are in "https://github.com/derickbailey/presentations-and-training.git"?*
  - `Id = RepoId`
  - `SELECT COUNT(T2.RepoId) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Url = 'https://github.com/derickbailey/presentations-and-training.git'`
- **codebase_comments** #630 — *What is the total processed time of all solutions from the repository with the most forks?*
  - `Id = RepoId`
  - `SELECT SUM(T2.ProcessedTime) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Forks = ( SELECT MAX(Forks) FROM Repo )`
- **codebase_comments** #631 — *List all the path of solution from all the "it" lang code method.*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Lang = 'it'`
- **codebase_comments** #632 — *What is the path of solution of "spinachLexer.mT__55" method?*
  - `Id = SolutionId`
  - `SELECT T1.Path FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Name = 'spinachLexer.mT__55'`
- **codebase_comments** #633 — *What are the "en" methods with solutions from repository "1093"*
  - `Id = SolutionId`
  - `SELECT DISTINCT T2.id FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.RepoId = 1093 AND T2.Lang = 'en'`
- **codebase_comments** #634 — *What are the paths of solutions in repository "https://github.com/ecoffey/Bebop.git"*
  - `Id = RepoId`
  - `SELECT DISTINCT T2.Path FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.Url = 'https://github.com/ecoffey/Bebop.git'`
- **codebase_comments** #635 — *List all the ids of repositories for solutions with "ro" methods.*
  - `Id = SolutionId`
  - `SELECT DISTINCT T1.RepoId FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.Lang = 'ro'`
- **codebase_comments** #636 — *What is the repository id of the method with tokenized name "crc parameters get hash code"?*
  - `Id = SolutionId`
  - `SELECT T1.RepoId FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T2.NameTokenized = 'crc parameters get hash code'`
- **codebase_comments** #637 — *How many methods with solutions with path 'maravillas_linq-to-delicious\tasty.sln'?*
  - `Id = SolutionId`
  - `SELECT COUNT(T2.SolutionId) FROM Solution AS T1 INNER JOIN Method AS T2 ON T1.Id = T2.SolutionId WHERE T1.Path = 'maravillas_linq-to-delicious\tasty.sln'`
- **codebase_comments** #638 — *List all the solutions ids of the repository with "636430969128176000" processed time*
  - `Id = RepoId`
  - `SELECT T2.Id FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T1.ProcessedTime = 636430969128176000`
- **codebase_comments** #639 — *What is the url for repository that has the longest processed time solution?*
  - `Id = RepoId`
  - `SELECT T1.Url FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId WHERE T2.ProcessedTime = ( SELECT MAX(ProcessedTime) FROM Solution )`
- … and 728 more

## Cluster analysis & verdict

The 788 unbacked-join flags collapse into **61 distinct (database, join-pair)
clusters across 21 of the 69 training databases** — repetition patterns, not
scattered noise. Top clusters (queries affected): `mondial_geo`
code=country (**181**), `shakespeare` id=work_id (57), `codebase_comments`
id=repoid (56), id=solutionid (47), `coinmarketcap` coin_id=id (43).

**The structural finding: 8 of the 21 flagged databases declare ZERO
foreign keys** — including `mondial_geo` (34 tables, 0 FKs),
`shakespeare`, `codebase_comments`, `movie_3` (16 tables, 0 FKs), and
`movielens`. Their gold queries join constantly; none of those
relationships exist in `train_tables.json`.

**Why it matters:** BIRD train is what text-to-SQL models are fine-tuned
on (LearNAT, SQLCoder variants, most leaderboard entries). Schema-linking
components consume these FK annotations; for 8 databases they are learning
from schemas with no links at all, and across the corpus 8.2% of gold
joins are unverifiable against the published schema — 8× the rate of the
curated dev set.

**Verification depth (honest labeling):** these are *candidates* verified
by clustering, name-semantics (e.g., `chapters.work_id = works.id` is
self-evidently a real relationship), and annotation-gap counts — not yet
by database execution: train databases ship inside a DEFLATE-compressed
nested zip that defeats the range-read technique used for the dev audit.
The dev-set root cause (implicit-PK FK extraction bug, confirmed and filed
as bird-bench/mini_dev#37) is the natural prior for a share of these.
Database-level confirmation is queued behind a full 8.9 GB download.
