# Security Policy

## Supported Versions

Security fixes target the current `main` branch and the latest published release
line. Older unreleased snapshots are not maintained as separate security
branches unless a maintainer states otherwise.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Use one of these private channels:

- GitHub private vulnerability reporting, if enabled for the repository.
- Email the maintainer listed in `pyproject.toml`.

Include:

- the affected version, commit, or release
- a minimal reproduction or proof of concept
- expected impact
- any logs, rendered artifacts, or input documents needed to reproduce

The maintainer will acknowledge the report, investigate, and coordinate a fix or
public disclosure when appropriate.

## Scope

FrameForge includes tools that execute user-provided SDK snippets in the MCP
workflow. Treat that execution boundary as sensitive. Reports about sandbox
escape, environment leakage, unsafe file access, denial of service, dependency
confusion, or malicious document handling are in scope.

Do not include real secrets in reports. Use synthetic tokens or redacted values.
