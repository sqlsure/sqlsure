# Security Policy

## What sqlsure does and doesn't touch

sqlsure is a static analyzer with a deliberately small attack surface:

- **No network access.** The engine makes zero network calls at check time.
- **No data access.** It parses SQL *text* and reads declared metadata
  (dbt manifests / schema files / JSON models). It never connects to a
  database and never reads rows.
- **No telemetry.** Nothing is collected, phoned home, or logged
  externally. Your SQL never leaves your machine.
- Dependencies: `sqlglot` (parsing) and `pyyaml` (rulebook files) only;
  `mcp` optionally for the MCP server.

## Reporting a vulnerability

Please report suspected vulnerabilities privately via
[GitHub Security Advisories](https://github.com/sqlsure/sqlsure/security/advisories/new)
rather than public issues. You can expect an acknowledgment within 72
hours. Relevant classes include: crafted SQL or YAML that causes code
execution or resource exhaustion in the parser path, and violations of
the no-network/no-data guarantees above.

## Supported versions

The latest minor release receives fixes. Pin exact versions in
production (`sqlsure==x.y.z`) and review the release notes before
upgrading — releases are published exclusively through GitHub Releases
via PyPI Trusted Publishing (OIDC), so every artifact is traceable to a
tagged commit and a public CI run.
