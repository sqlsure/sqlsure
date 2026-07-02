"""SemanticGate — wrap ANY NL2SQL generator with the sqlsure inspector.

Works with Vanna, WrenAI, or any object exposing `generate_sql(question)`
(duck-typed; no dependency on either project). The gate:

  1. asks the generator for SQL
  2. checks it against the semantic model
  3. if rejected, feeds the fix hints back to the generator and retries
  4. returns only approved SQL (or raises after max_retries)

Vanna example (once installed):
    vn = MyVanna(...)                      # any Vanna subclass
    gate = SemanticGate(vn, model)
    sql = gate.generate_sql("total cost per patient")   # only approved SQL

Run the self-contained demo (fake generator, no deps):
    python integrations/semantic_gate.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure.checker import check  # noqa: E402
from sqlsure.model import SemanticModel  # noqa: E402


class RejectedSQL(Exception):
    def __init__(self, sql: str, violations: list):
        self.sql, self.violations = sql, violations
        super().__init__(
            f"SQL rejected after retries: "
            + "; ".join(v.message for v in violations))


class SemanticGate:
    def __init__(self, generator, model: SemanticModel,
                 dialect: str | None = None, max_retries: int = 2):
        self.generator = generator
        self.model = model
        self.dialect = dialect
        self.max_retries = max_retries

    def _feedback(self, violations) -> str:
        lines = ["The previous SQL was rejected by a semantic checker. "
                 "Rewrite it, applying every fix below:"]
        for v in violations:
            lines.append(f"- {v.rule}: {v.message} FIX: {v.fix}")
        return "\n".join(lines)

    def generate_sql(self, question: str) -> str:
        sql = self.generator.generate_sql(question)
        for _ in range(self.max_retries + 1):
            violations = check(sql, self.model, dialect=self.dialect)
            blocking = [v for v in violations
                        if v.severity in ("error", "policy")]
            if not blocking:
                return sql
            feedback = self._feedback(blocking)
            # prefer a dedicated repair hook if the generator has one
            if hasattr(self.generator, "repair_sql"):
                sql = self.generator.repair_sql(sql, feedback)
            else:
                sql = self.generator.generate_sql(
                    f"{question}\n\n{feedback}")
        raise RejectedSQL(sql, blocking)


# ---------------------------------------------------------------- demo ---
if __name__ == "__main__":
    import json

    class FakeNL2SQL:
        """Stands in for Vanna/WrenAI: first draft has the classic
        fan-out bug; on feedback it produces the repaired version."""
        def generate_sql(self, prompt: str) -> str:
            if "semantic checker" in prompt:  # feedback round
                return """WITH costs AS (
                    SELECT patient_id, SUM(cost) AS total FROM fct_encounters GROUP BY 1)
                    SELECT p.patient_id, c.total
                    FROM dim_patient p JOIN costs c ON p.patient_id = c.patient_id"""
            return """SELECT p.patient_id, SUM(f.cost) AS total
                    FROM fct_encounters f
                    JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id
                    JOIN dim_patient p ON f.patient_id = p.patient_id GROUP BY 1"""

    model = SemanticModel.from_dict(json.load(open(
        os.path.join(os.path.dirname(__file__), "..", "model.example.json"))))
    gate = SemanticGate(FakeNL2SQL(), model)

    print("question: total cost per patient")
    draft = FakeNL2SQL().generate_sql("total cost per patient")
    print("\ndraft 1 (what the generator produced):")
    print(" ", " ".join(draft.split())[:100], "...")
    print("  -> inspector:",
          [v.rule for v in check(draft, model)] or "APPROVED")
    final = gate.generate_sql("total cost per patient")
    print("\nfinal (what the gate returned to the caller):")
    print(" ", " ".join(final.split())[:100], "...")
    print("  -> inspector:",
          [v.rule for v in check(final, model)] or "APPROVED ✓")
