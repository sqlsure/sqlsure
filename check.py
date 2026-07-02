"""Demo: the inspector catching semantically-wrong-but-valid SQL.

Run: python check.py
"""
import json

from sqlsure import SemanticModel, check

MODEL = SemanticModel.from_dict(json.load(open("model.example.json")))

QUERIES = {
    "FANOUT (double-counted cost)": """
        SELECT p.patient_id, SUM(f.cost) AS total_cost
        FROM fct_encounters f
        JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id
        JOIN dim_patient p   ON f.patient_id   = p.patient_id
        GROUP BY 1
    """,
    "ADDITIVITY (summing an average)": """
        SELECT SUM(avg_los) AS total_los
        FROM fct_encounters
    """,
    "SEMI-ADDITIVE (summing a census over time)": """
        SELECT unit_id, SUM(occupied_beds) AS beds
        FROM fct_patient_census
        GROUP BY 1
    """,
    "WRONG JOIN KEY": """
        SELECT p.patient_id, f.cost
        FROM fct_encounters f
        JOIN dim_patient p ON f.encounter_id = p.patient_id
    """,
    "PHI EXPOSURE (policy)": """
        SELECT p.patient_name, p.ssn, SUM(f.cost) AS total_cost
        FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id
        GROUP BY 1, 2
    """,
    "PASSING QUERY": """
        SELECT p.patient_id, SUM(f.cost) AS total_cost
        FROM fct_encounters f
        JOIN dim_patient p ON f.patient_id = p.patient_id
        GROUP BY 1
    """,
}

for name, sql in QUERIES.items():
    violations = check(sql, MODEL)
    print(f"\n=== {name} ===")
    print("REJECTED:" if violations else "APPROVED ✓")
    for v in violations:
        print(f"  ✗ [{v.severity.upper()}] {v.rule}: {v.message}")
        if v.fix:
            print(f"      fix: {v.fix}")
