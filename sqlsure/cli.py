"""CLI door: `python -m sqlsure.cli --model model.json query.sql`

Exit code 1 on blocking violations, so it drops straight into CI or
pre-commit as a merge gate. `--json` emits machine-readable output for
agent loops (MCP server wraps the same call).
"""
from __future__ import annotations

import argparse
import json
import sys

from .checker import check
from .model import SemanticModel


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sqlsure", description="Semantic SQL inspector")
    p.add_argument("sql", nargs="?", help="SQL file to check (default: stdin)")
    p.add_argument("--model", required=True, help="semantic model JSON file")
    p.add_argument("--dialect", default=None, help="SQL dialect (e.g. snowflake)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--strict", action="store_true", help="warnings also fail")
    args = p.parse_args(argv)

    with open(args.model) as f:
        model = SemanticModel.from_dict(json.load(f))
    sql = open(args.sql).read() if args.sql else sys.stdin.read()

    violations = check(sql, model, dialect=args.dialect)
    blocking = [v for v in violations
                if v.severity in ("error", "policy") or args.strict]

    if args.json:
        print(json.dumps({
            "approved": not blocking,
            "violations": [v.to_dict() for v in violations],
        }, indent=2))
    else:
        if not violations:
            print("APPROVED ✓")
        else:
            print("REJECTED:" if blocking else "APPROVED (with warnings):")
            for v in violations:
                print(f"  ✗ [{v.severity.upper()}] {v.rule}: {v.message}")
                if v.fix:
                    print(f"      fix: {v.fix}")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
