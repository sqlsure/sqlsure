# Spider gold-query audit — sqlsure join-safety pass
*2026-07-01 · Spider validation split, 1034 gold queries · rulebook derived from Spider's own PK/FK declarations*

| metric | value |
|---|---|
| gold queries analyzed | 1034 |
| parsed by engine | 1034 (100%) |
| joins observed (all scopes incl. subqueries) | 518 |
| joins backed by a declared FK | 484 (93%) |
| shared-key joins (same column both sides, no FK) | 2 (0%) |
| non-equi join predicates | 2 |
| **unbacked joins (different columns, no FK)** | **30** |
| **joins with no predicate at all (cartesian)** | **0** |

`unbacked` and `cartesian` rows are *anomaly candidates for manual review*, not asserted bugs.

## unbacked candidates (30)
- **flight_2** — *How many flights does airline 'JetBlue Airways' have?*
  - `airline = uid`
  - `SELECT count(*) FROM FLIGHTS AS T1 JOIN AIRLINES AS T2 ON T1.Airline = T2.uid WHERE T2.Airline = "JetBlue Airways"`
- **flight_2** — *Give the number of Jetblue Airways flights.*
  - `airline = uid`
  - `SELECT count(*) FROM FLIGHTS AS T1 JOIN AIRLINES AS T2 ON T1.Airline = T2.uid WHERE T2.Airline = "JetBlue Airways"`
- **flight_2** — *How many 'United Airlines' flights go to Airport 'ASY'?*
  - `airline = uid`
  - `SELECT count(*) FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T2.Airline = T1.uid WHERE T1.Airline = "United Airlines" AND T2.DestAirport = "ASY"`
- **flight_2** — *Count the number of United Airlines flights arriving in ASY Airport.*
  - `airline = uid`
  - `SELECT count(*) FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T2.Airline = T1.uid WHERE T1.Airline = "United Airlines" AND T2.DestAirport = "ASY"`
- **flight_2** — *How many 'United Airlines' flights depart from Airport 'AHD'?*
  - `airline = uid`
  - `SELECT count(*) FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T2.Airline = T1.uid WHERE T1.Airline = "United Airlines" AND T2.SourceAirport = "AHD"`
- **flight_2** — *Return the number of United Airlines flights leaving from AHD Airport.*
  - `airline = uid`
  - `SELECT count(*) FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T2.Airline = T1.uid WHERE T1.Airline = "United Airlines" AND T2.SourceAirport = "AHD"`
- **flight_2** — *How many United Airlines flights go to City 'Aberdeen'?*
  - `uid = airline`
  - `SELECT count(*) FROM FLIGHTS AS T1 JOIN AIRPORTS AS T2 ON T1.DestAirport = T2.AirportCode JOIN AIRLINES AS T3 ON T3.uid = T1.Airline WHERE T2.City = "Aberdeen" AND T3.Airline = "Un`
- **flight_2** — *Count the number of United Airlines flights that arrive in Aberdeen.*
  - `uid = airline`
  - `SELECT count(*) FROM FLIGHTS AS T1 JOIN AIRPORTS AS T2 ON T1.DestAirport = T2.AirportCode JOIN AIRLINES AS T3 ON T3.uid = T1.Airline WHERE T2.City = "Aberdeen" AND T3.Airline = "Un`
- **flight_2** — *Which airline has most number of flights?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline ORDER BY count(*) DESC LIMIT 1`
- **flight_2** — *What airline serves the most flights?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline ORDER BY count(*) DESC LIMIT 1`
- **flight_2** — *Find the abbreviation and country of the airline that has fewest number of flights?*
  - `uid = airline`
  - `SELECT T1.Abbreviation , T1.Country FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline ORDER BY count(*) LIMIT 1`
- **flight_2** — *What is the abbreviation of the airilne has the fewest flights and what country is it in?*
  - `uid = airline`
  - `SELECT T1.Abbreviation , T1.Country FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline ORDER BY count(*) LIMIT 1`
- **flight_2** — *What are airlines that have some flight departing from airport 'AHD'?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "AHD"`
- **flight_2** — *Which airlines have a flight with source airport AHD?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "AHD"`
- **flight_2** — *What are airlines that have flights arriving at airport 'AHD'?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.DestAirport = "AHD"`
- **flight_2** — *Which airlines have a flight with destination airport AHD?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.DestAirport = "AHD"`
- **flight_2** — *Find all airlines that have flights from both airports 'APG' and 'CVO'.*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "APG" INTERSECT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON`
- **flight_2** — *Find all airlines that have flights from both airports 'APG' and 'CVO'.*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "APG" INTERSECT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON`
- **flight_2** — *Which airlines have departing flights from both APG and CVO airports?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "APG" INTERSECT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON`
- **flight_2** — *Which airlines have departing flights from both APG and CVO airports?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "APG" INTERSECT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON`
- **flight_2** — *Find all airlines that have flights from airport 'CVO' but not from 'APG'.*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "CVO" EXCEPT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1`
- **flight_2** — *Find all airlines that have flights from airport 'CVO' but not from 'APG'.*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "CVO" EXCEPT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1`
- **flight_2** — *Which airlines have departures from CVO but not from APG airports?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "CVO" EXCEPT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1`
- **flight_2** — *Which airlines have departures from CVO but not from APG airports?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline WHERE T2.SourceAirport = "CVO" EXCEPT SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1`
- **flight_2** — *Find all airlines that have at least 10 flights.*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline HAVING count(*) > 10`
- **flight_2** — *Which airlines have at least 10 flights?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline HAVING count(*) > 10`
- **flight_2** — *Find all airlines that have fewer than 200 flights.*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline HAVING count(*) < 200`
- **flight_2** — *Which airlines have less than 200 flights?*
  - `uid = airline`
  - `SELECT T1.Airline FROM AIRLINES AS T1 JOIN FLIGHTS AS T2 ON T1.uid = T2.Airline GROUP BY T1.Airline HAVING count(*) < 200`
- **flight_2** — *What are flight numbers of Airline "United Airlines"?*
  - `uid = airline`
  - `SELECT T1.FlightNo FROM FLIGHTS AS T1 JOIN AIRLINES AS T2 ON T2.uid = T1.Airline WHERE T2.Airline = "United Airlines"`
- **flight_2** — *Which flight numbers correspond to United Airlines flights?*
  - `uid = airline`
  - `SELECT T1.FlightNo FROM FLIGHTS AS T1 JOIN AIRLINES AS T2 ON T2.uid = T1.Airline WHERE T2.Airline = "United Airlines"`

## Manual review verdict

All 30 unbacked-join candidates trace to **one confirmed schema-annotation
defect** in the `flight_2` database, affecting 30/1034 gold queries (2.9%
of the split):

1. **Missing FK.** Every flagged query joins `flights.Airline =
   airlines.uid`, and that relationship is real — but Spider's schema
   declares only `flights.SourceAirport/DestAirport → airports.AirportCode`.
   The airline FK is absent from the annotation.
2. **Wrong PK.** The schema annotation resolves the primary key of
   `flights` to `Airline` — a column that cannot uniquely identify a
   flight (an airline has many flights). (Possibly a flattening of a
   composite key in the source DB; the annotation as shipped is wrong
   either way.)
3. **Semantic trap.** `airlines.Airline` is the carrier *name* (text)
   while `flights.Airline` is a *number* referencing `airlines.uid` —
   the same column name means two different things in adjacent tables,
   exactly the ambiguity class that annotation-error studies flag.

**Precision of the pass: no spurious candidates.** Every anomaly the
inspector surfaced on 1,034 externally-authored queries traces to this
genuine defect; legitimate shared-key joins (2) were correctly classified
and not flagged. Prior work has documented pervasive annotation errors in
text-to-SQL benchmarks by manual/LLM review — this pass localizes a
schema-level defect **mechanically, in ~2 seconds, with zero human
labeling**, which is the point of the tool.

**Caveats:** this pass exercises only join-safety rules (PK/FK-derivable);
additivity/grain rules need measure annotations Spider doesn't carry.
Coverage is bounded by Spider's own FK declarations — a benchmark with
richer schemas (BIRD) would allow a deeper pass. BIRD's dev set requires a
Google-Drive download and is the natural next target.