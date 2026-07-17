---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude (Anthropic) via Claude Code"
  date: "2026-07-06"
---

# Defect report — large tool-argument dropped in transit to the MCP server

## Summary

A `write_sdk_client` call carrying a ~21 KB `code` argument failed with
`ValueError: provide \`code\` … `. Investigation shows the FrameForge MCP server
received `code = None` — the argument was **dropped before it reached the
server**, in the client↔server tool-call transport (the Claude Code ↔ MCP
bridge), **not** by any FrameForge size limit. The FrameForge server and the
FastMCP layer both handle far larger arguments.

This report records the evidence, the root-cause localization, the fixes shipped
**inside this repo** (diagnostics, chunked-append, tests), and the one item that
must be filed **upstream** because it is outside this repo.

## Evidence

| Observation | Value | Source |
|---|---|---|
| Failing payload | 21,662 bytes | this session |
| A prior write that succeeded | 19,268 bytes | this session |
| FrameForge client-file cap (`MAX_CLIENT_BYTES`) | 2,000,000 bytes | `src/frameforge/mcp/config.py` |
| Server-side direct write, 300 KB | `ok: True` | `clients.write_sdk_client(...)` called in-process |
| FastMCP in-memory `call_tool`, 250 KB | file written, exact bytes | `create_server().call_tool("write_sdk_client", …)` |
| Error string origin | only reachable when `code is None` | `server.py` write dispatch |

The `"provide code"` branch fires **only** when `code` is `None`. Since the cap
is 2 MB and both the server function and the FastMCP tool layer accept
250–300 KB, the 21 KB argument must have been lost **above** FastMCP — in the
external MCP client transport.

**Empirical threshold:** 19 KB delivered, 21 KB arrived empty → a per-argument
limit of roughly **~20 KB** in that bridge.

## Root cause

The Claude Code ↔ MCP tool-call bridge appears to **silently drop (or truncate to
empty) a single tool argument above ~20 KB**. The receiving server then sees a
missing argument and cannot distinguish it from a genuine omission.

**Not verifiable from this repo:** the bridge source is not part of FrameForge,
so the exact mechanism and threshold cannot be confirmed here; the localization
above is inferred from server-side and FastMCP-side behaviour, which are
verifiable. This is a single failure data point plus a determinism argument, not
a threshold sweep.

## Why the green test suite did not catch it (coverage gap)

The MCP tests import the Python functions **in-process** and never round-trip the
real stdio JSON-RPC transport, so the failing layer was untested. Additionally,
`apply_anchored_edit` and the server write-dispatch branches had **zero**
coverage, and there was no large-payload or boundary test. "All green" reflected
the layer *below* the fault. (This coverage gap is closed by the fixes below.)

## Fixes shipped in this repo

- **Honest diagnostic (P1):** empty/`None` `code` now raises a message that names
  the likely cause (payload exceeded the client's per-argument transport limit)
  and the two size-safe escapes (anchored edit; chunked append) — `usecases.write_or_edit_client`.
- **Chunked append (P7):** `write_sdk_client(..., append=True, allow_partial=True)`
  builds a client in sub-limit chunks; the byte cap applies to the assembled file
  and the final (non-partial) chunk is compile-checked — `clients.write_sdk_client`.
- **Testable dispatch + coverage (P2/P3/P4):** the wrapper delegates to
  `write_or_edit_client`; `tests/test_mcp_write_dispatch.py` covers full replace,
  anchored edits (all error branches), chunked append, the 2 MB boundary, the
  improved diagnostic, and an **end-to-end FastMCP round-trip with a large
  argument** (which is what proves the fault is external).
- **Docs + log hygiene (P5/P6):** the `code` field documents the cap and the
  chunking escape; the guide explains it; `_logged_call` records `<N chars>`
  instead of the full body.

## Upstream action (N1 — cannot be fixed here)

File against the Claude Code ↔ MCP client bridge:

> **Title:** MCP tool argument silently dropped above ~20 KB
> **Repro:** call any MCP tool with a single string argument; at ~19 KB it
> arrives intact, at ~21 KB the server receives the argument as `None`/absent
> (no client-side error).
> **Expected:** either deliver the full argument (servers already accept MB-scale
> args) or return an explicit client-side error naming the size limit — never a
> silent drop.
> **Server-side proof it is not the server:** FastMCP `call_tool` accepts 250 KB
> in-process; the FrameForge cap is 2 MB.

Until fixed, the in-repo mitigations (anchored edit, chunked append) are the
recommended path for large clients over MCP.
