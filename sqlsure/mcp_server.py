"""MCP door: expose the inspector as tools any MCP agent can call.

Run:
    python -m sqlsure.mcp_server --model model.example.json
    python -m sqlsure.mcp_server --manifest path/to/target/manifest.json

Register with Claude Code:
    claude mcp add sqlsure -- python -m sqlsure.mcp_server --model /abs/path/model.json

The intended agent loop: draft SQL -> check_sql -> if not approved, apply
the `fix` hints and re-check -> execute only approved SQL.
"""
from __future__ import annotations

import argparse
import json

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # core install is dependency-light; MCP is an extra
    raise SystemExit(
        "The MCP server needs the `mcp` package: pip install \"sqlsure[mcp]\""
    )

from .checker import check
from .model import SemanticModel

mcp = FastMCP(
    "sqlsure",
    instructions=(
        "Semantic inspector for SQL. Call check_sql on EVERY SQL query "
        "before executing it against the warehouse. If approved is false, "
        "rewrite the query following each violation's `fix` hint and call "
        "check_sql again; only execute approved SQL. Call describe_model "
        "first to learn the tables, grains, measures, and safe join paths."
    ),
)

_model: SemanticModel = SemanticModel()


@mcp.tool()
def check_sql(sql: str, dialect: str | None = None) -> dict:
    """Validate a SQL query against the semantic model before execution.

    Returns {approved, violations:[{rule, severity, message, fix}]}.
    `approved` is false when errors or policy violations exist; apply each
    violation's `fix` and re-submit. Warnings do not block but should be
    surfaced to the user.
    """
    violations = check(sql, _model, dialect=dialect)
    return {
        "approved": not any(v.severity in ("error", "policy")
                            for v in violations),
        "violations": [v.to_dict() for v in violations],
    }


@mcp.tool()
def describe_model() -> dict:
    """The semantic rulebook: tables with grain/measures/sensitive columns,
    and declared join edges with cardinality and keys. Use this to plan
    safe queries before writing SQL."""
    return {
        "tables": {
            t.name: {
                "grain": t.grain,
                "measures": {m.name: m.additivity
                             for m in t.measures.values()},
                "sensitive": sorted(t.sensitive),
            }
            for t in _model.tables.values()
        },
        "joins": [
            {"left": j.left, "right": j.right,
             "cardinality": j.cardinality,
             "keys": [list(k) for k in j.keys]}
            for j in _model.joins.values()
        ],
    }


def main(argv: list[str] | None = None) -> None:
    global _model
    p = argparse.ArgumentParser(prog="sqlsure-mcp")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--model", help="semantic model JSON file")
    src.add_argument("--manifest", help="dbt manifest.json to extract from")
    args = p.parse_args(argv)

    if args.model:
        with open(args.model) as f:
            _model = SemanticModel.from_dict(json.load(f))
    else:
        from .dbt_loader import load_manifest
        _model = load_manifest(args.manifest)

    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
