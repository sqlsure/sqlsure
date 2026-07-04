"""Rule tests — runnable with no test framework: python tests/run_tests.py"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlsure import SemanticModel, check  # noqa: E402

MODEL = SemanticModel.from_dict(json.load(
    open(os.path.join(os.path.dirname(__file__), "..", "model.example.json"))))

PASSED = FAILED = 0


def expect(name: str, sql: str, rules: set[str]):
    global PASSED, FAILED
    got = {v.rule for v in check(sql, MODEL)}
    if got == rules:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL  {name}: expected {rules or '{}'}, got {got or '{}'}")


# fanout
expect("fanout on SUM of additive measure",
       "SELECT SUM(f.cost) FROM fct_encounters f "
       "JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id",
       {"FANOUT"})
expect("fanout on COUNT(*)",
       "SELECT COUNT(*) FROM fct_encounters f "
       "JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id",
       {"FANOUT"})
expect("COUNT(DISTINCT) is safe under fanout",
       "SELECT COUNT(DISTINCT f.encounter_id) FROM fct_encounters f "
       "JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id",
       set())
expect("many-to-one join is safe",
       "SELECT SUM(f.cost) FROM fct_encounters f "
       "JOIN dim_patient p ON f.patient_id = p.patient_id",
       set())

# chasm: needs a second one-to-many edge
CHASM_MODEL = SemanticModel.from_dict({
    "tables": {"fct": {"grain": "id", "measures": {"amt": "additive"}},
               "a": {"grain": "a_id"}, "b": {"grain": "b_id"}},
    "joins": [
        {"left": "fct", "right": "a", "cardinality": "one_to_many",
         "keys": [["id", "id"]]},
        {"left": "fct", "right": "b", "cardinality": "one_to_many",
         "keys": [["id", "id"]]},
    ]})
got = {v.rule for v in check(
    "SELECT SUM(f.amt) FROM fct f JOIN a ON f.id = a.id JOIN b ON f.id = b.id",
    CHASM_MODEL)}
if {"CHASM", "FANOUT"} <= got:
    PASSED += 1
    print("  ok  chasm trap on double fanout")
else:
    FAILED += 1
    print(f"FAIL  chasm trap: got {got}")

# additivity
expect("SUM of non-additive measure",
       "SELECT SUM(avg_los) FROM fct_encounters", {"ADDITIVITY"})
expect("AVG of non-additive measure is fine",
       "SELECT AVG(avg_los) FROM fct_encounters", set())

# semi-additive
expect("SUM of census across time",
       "SELECT unit_id, SUM(occupied_beds) FROM fct_patient_census GROUP BY 1",
       {"SEMI_ADDITIVE"})
expect("SUM of census within snapshot date is fine",
       "SELECT census_date, SUM(occupied_beds) FROM fct_patient_census GROUP BY 1",
       set())
expect("GROUP BY ordinal resolves to snapshot date",
       "SELECT census_date, SUM(occupied_beds) FROM fct_patient_census "
       "GROUP BY census_date",
       set())

# weighted average
expect("AVG after fanout warns",
       "SELECT AVG(f.cost) FROM fct_encounters f "
       "JOIN dim_diagnosis d ON f.encounter_id = d.encounter_id",
       {"WEIGHTED_AVG"})

# join keys
expect("wrong join key",
       "SELECT f.cost FROM fct_encounters f "
       "JOIN dim_patient p ON f.encounter_id = p.patient_id",
       {"JOIN_KEY"})

# undeclared join
expect("undeclared relationship warns",
       "SELECT f.cost FROM fct_encounters f "
       "JOIN fct_patient_census c ON f.encounter_id = c.unit_id",
       {"UNDECLARED_JOIN"})

# cross join
expect("cross join rejected",
       "SELECT f.cost FROM fct_encounters f CROSS JOIN dim_patient p",
       {"CROSS_JOIN"})

# sensitive columns
expect("PHI selection flagged",
       "SELECT p.ssn FROM dim_patient p", {"SENSITIVE_COLUMN"})
expect("non-sensitive dim column fine",
       "SELECT p.patient_id FROM dim_patient p", set())

# introspection: rulebook from a live sqlite catalog
import sqlite3  # noqa: E402

from sqlsure.introspect import model_from_sqlite  # noqa: E402

conn = sqlite3.connect(":memory:")
conn.executescript("""
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY,
  customer_id INTEGER REFERENCES customers(customer_id),
  total REAL);
CREATE TABLE order_items (
  item_id INTEGER PRIMARY KEY,
  order_id INTEGER REFERENCES orders,          -- implicit-PK reference
  qty INTEGER);
CREATE TABLE order_profiles (                  -- 1:1 child of orders
  order_id INTEGER PRIMARY KEY REFERENCES orders(order_id),
  notes TEXT);
CREATE TABLE messages (                        -- role-playing dim
  msg_id INTEGER PRIMARY KEY,
  sender_id INTEGER REFERENCES customers(customer_id),
  recipient_id INTEGER REFERENCES customers(customer_id));
""")
INTRO = model_from_sqlite(conn)


def check_intro(name, cond):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL  {name}")


check_intro("introspect: PK becomes grain",
            INTRO.tables["orders"].grain == ["order_id"])
e = INTRO.edge("orders", "customers")
check_intro("introspect: FK becomes many-to-one edge",
            e is not None and e.cardinality == "many_to_one"
            and e.keys == [("customer_id", "customer_id")])
e = INTRO.edge("order_items", "orders")
check_intro("introspect: implicit-PK reference resolved",
            e is not None and e.keys == [("order_id", "order_id")])
e = INTRO.edge("order_profiles", "orders")
check_intro("introspect: unique child key upgrades to one-to-one",
            e is not None and e.cardinality == "one_to_one")
e = INTRO.edge("messages", "customers")
check_intro("introspect: role-playing FKs merge into one edge",
            e is not None
            and sorted(e.keys) == [("recipient_id", "customer_id"),
                                   ("sender_id", "customer_id")])
got = {v.rule for v in check(
    "SELECT SUM(o.total) FROM orders o "
    "JOIN order_items i ON o.order_id = i.order_id", INTRO, dialect="sqlite")}
check_intro("introspect: fanout caught with zero-authoring rulebook",
            "FANOUT" in got)
check_intro("introspect: to_dict round-trips",
            SemanticModel.from_dict(INTRO.to_dict()).joins.keys()
            == INTRO.joins.keys())
conn.close()

print(f"\n{PASSED} passed, {FAILED} failed")
sys.exit(1 if FAILED else 0)
