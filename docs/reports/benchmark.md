# sqlsure utility benchmark
*2026-07-01 · 11 buggy + 10 clean labeled queries · healthcare model*

| metric | value |
|---|---|
| Detection recall (buggy flagged with correct rule) | **100%** (11/11) |
| Hard false positives (errors on clean queries) | **0%** (0/10) |
| Soft flags (warnings on clean queries) | 0/10 |
| Fix-hint actionability (repaired query then passes) | **10/10** |
| Latency median / p95 per check | **0.1 ms / 0.4 ms** (n=210) |


Method: labeled corpus, one buggy case per rule plus a CTE-buried variant; clean set includes near-miss patterns (COUNT DISTINCT under fan-out, pre-aggregate-then-join, snapshot-grain sums). Repairs implement the violation's `fix` hint verbatim.