"""With/without sqlsure experiment on real BIRD data.

Arms (same first draft shared by A and B for fairness):
  A  bare:   LLM drafts SQL -> execute
  B  gated:  draft -> sqlsure check (rulebook introspected from the live
             sqlite DB, zero authoring) -> if flagged, ONE repair round with
             the fix hints -> execute
  C  judge:  an LLM judge reviews each draft (the industry-default pattern)
             -> if judge says fix, ONE repair round with judge feedback

Measures per arm: execution accuracy vs gold results (run on the real DB),
tokens and $ (from claude CLI usage reporting), wall latency of the check.
Generator/judge: haiku via `claude -p` headless.
"""
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sqlsure.checker import check  # noqa: E402
from sqlsure.introspect import model_from_sqlite  # noqa: E402

DATA = ROOT / "birddata/dev_20240627"
N_QUESTIONS = 24
MODEL_FLAG = ["--model", "haiku"]
OUT = Path(__file__).parent / "gate_vs_judge_results.json"


def db_path(db_id):
    return DATA / "dev_databases" / db_id / f"{db_id}.sqlite"


def llm(prompt: str) -> tuple[str, dict]:
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json", *MODEL_FLAG],
        capture_output=True, text=True, timeout=300)
    d = json.loads(r.stdout)
    u = d.get("usage", {})
    return d.get("result", ""), {
        "in": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
              + u.get("cache_read_input_tokens", 0),
        "out": u.get("output_tokens", 0),
        "usd": d.get("total_cost_usd", 0.0),
    }


def clean_sql(text: str) -> str:
    import sqlglot
    text = re.sub(r"```(sql)?", "", text).strip()
    m = re.search(r"(SELECT|WITH)\b.*", text, re.I | re.S)
    text = (m.group(0) if m else text).strip().rstrip(";")
    lines = text.splitlines()
    for end in range(len(lines), 0, -1):  # drop trailing prose lines
        cand = "\n".join(lines[:end]).strip().rstrip(";")
        try:
            sqlglot.parse_one(cand, read="sqlite")
            return cand
        except Exception:
            continue
    return text


def run_sql(sql: str, dbp):
    conn = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    conn.text_factory = lambda b: b.decode("utf-8", "replace")
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(5000)
        norm = set()
        for row in rows:
            norm.add(tuple(round(v, 4) if isinstance(v, float) else v
                           for v in row))
        return norm, None
    except Exception as e:
        return None, str(e)[:200]
    finally:
        conn.close()


def acc(sql: str, gold_rows, dbp) -> bool:
    rows, err = run_sql(sql, dbp)
    return err is None and rows == gold_rows


def main():
    agg = re.compile(r"\b(SUM|COUNT|AVG)\s*\(", re.I)
    all_rows = [r for r in json.load(open(DATA / "dev.json"))
                if "JOIN" in r["SQL"].upper() and agg.search(r["SQL"])]
    # spread across DBs: round-robin so no single schema dominates
    from collections import defaultdict, deque
    per_db = defaultdict(deque)
    for r in all_rows:
        per_db[r["db_id"]].append(r)
    rows, dbs = [], deque(sorted(per_db))
    while dbs and len(rows) < N_QUESTIONS:
        db = dbs.popleft()
        if per_db[db]:
            rows.append(per_db[db].popleft())
            dbs.append(db)

    schemas, models = {}, {}
    for db in {r["db_id"] for r in rows}:
        dbp = db_path(db)
        schemas[db] = "\n".join(
            x[0] for x in sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
            .execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"))
        models[db] = model_from_sqlite(str(dbp))

    results = []
    tok = {a: {"in": 0, "out": 0, "usd": 0.0} for a in "ABC"}

    for i, r in enumerate(rows):
        q, gold_sql = r["question"], r["SQL"]
        db = r["db_id"]
        dbp = db_path(db)
        schema_ddl, model = schemas[db], models[db]
        evidence = r.get("evidence", "")
        gold_rows, gold_err = run_sql(gold_sql, dbp)
        if gold_err:
            continue

        gen_prompt = (
            f"You write SQLite SQL. Schema:\n{schema_ddl}\n\n"
            f"Question: {q}\nHint: {evidence}\n"
            f"Reply with ONLY the SQL query. No markdown, no explanation, no commentary of any kind.")
        draft_raw, u = llm(gen_prompt)
        draft = clean_sql(draft_raw)
        for a in "ABC":  # all arms share the first draft's cost
            tok[a]["in"] += u["in"]; tok[a]["out"] += u["out"]; tok[a]["usd"] += u["usd"]

        rec = {"qid": r.get("question_id", i), "db": db, "question": q, "draft": draft}

        # --- Arm A: bare
        rec["A_correct"] = acc(draft, gold_rows, dbp)

        # --- Arm B: sqlsure gate (0 tokens for the check itself)
        t0 = time.perf_counter()
        vs = check(draft, model, dialect="sqlite")
        rec["gate_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        rec["gate_flags"] = [v.rule for v in vs]
        b_sql = draft
        if vs:
            hints = "\n".join(f"- {v.rule}: {v.message} FIX: {v.fix}" for v in vs)
            fix_prompt = (
                f"You wrote this SQLite query for: {q}\nHint: {evidence}\n"
                f"Query:\n{draft}\n\nA deterministic semantic checker "
                f"(using the database's real PK/FK constraints) found:\n{hints}\n"
                f"Schema:\n{schema_ddl}\n\nRewrite the query applying the "
                f"fixes ONLY if they are consistent with the question intent; "
                f"otherwise return the original. Reply with ONLY the SQL, no commentary.")
            fixed_raw, u = llm(fix_prompt)
            tok["B"]["in"] += u["in"]; tok["B"]["out"] += u["out"]; tok["B"]["usd"] += u["usd"]
            b_sql = clean_sql(fixed_raw)
        rec["B_sql"] = b_sql
        rec["B_correct"] = acc(b_sql, gold_rows, dbp)

        # --- Arm C: LLM-as-judge (the pattern sqlsure replaces)
        judge_prompt = (
            f"You are a SQL reviewer. Schema:\n{schema_ddl}\n\n"
            f"Question: {q}\nHint: {evidence}\nProposed SQL:\n{draft}\n\n"
            f"Check for semantic errors (double counting from join fan-out, "
            f"wrong join keys, wrong aggregation). Reply EXACTLY one of:\n"
            f"APPROVED\nor\nREJECTED: <one-line reason and fix>")
        verdict, u = llm(judge_prompt)
        tok["C"]["in"] += u["in"]; tok["C"]["out"] += u["out"]; tok["C"]["usd"] += u["usd"]
        rec["judge_verdict"] = verdict.strip()[:150]
        c_sql = draft
        if verdict.strip().upper().startswith("REJECT"):
            fix_prompt = (
                f"You wrote this SQLite query for: {q}\nHint: {evidence}\n"
                f"Query:\n{draft}\n\nA reviewer said: {verdict.strip()[:300]}\n"
                f"Schema:\n{schema_ddl}\n\nRewrite the query if the reviewer "
                f"is right; otherwise return the original. Reply ONLY SQL, no commentary.")
            fixed_raw, u = llm(fix_prompt)
            tok["C"]["in"] += u["in"]; tok["C"]["out"] += u["out"]; tok["C"]["usd"] += u["usd"]
            c_sql = clean_sql(fixed_raw)
        rec["C_correct"] = acc(c_sql, gold_rows, dbp)

        results.append(rec)
        done = {a: sum(x[f"{a}_correct"] for x in results) for a in "ABC"}
        print(f"[{i+1}/{len(rows)}] qid={rec['qid']} "
              f"A={rec['A_correct']} B={rec['B_correct']} C={rec['C_correct']} "
              f"flags={rec['gate_flags']} | running A/B/C: "
              f"{done['A']}/{done['B']}/{done['C']}", flush=True)
        json.dump({"tokens": tok, "results": results}, open(OUT, "w"), indent=1)

    n = len(results)
    print("\n=== SUMMARY ===")
    for a, label in [("A", "bare LLM"), ("B", "sqlsure gate"), ("C", "LLM judge")]:
        c = sum(r[f"{a}_correct"] for r in results)
        print(f"{label:14s} accuracy {c}/{n} ({c/n:.0%})  "
              f"tokens in/out {tok[a]['in']}/{tok[a]['out']}  "
              f"${tok[a]['usd']:.2f}")
    flagged = sum(1 for r in results if r["gate_flags"])
    print(f"gate flagged {flagged}/{n} drafts; median gate latency "
          f"{sorted(r['gate_ms'] for r in results)[n//2]} ms; gate token cost: 0")


if __name__ == "__main__":
    main()
