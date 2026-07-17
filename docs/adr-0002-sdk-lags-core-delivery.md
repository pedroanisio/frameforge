---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: >-
    claude-opus-4-8 via Claude Code; worked example + status notes amended by
    Claude Fable 5 via Claude Code (2026-07-01)
  date: "2026-06-24 (amended 2026-07-01)"
---

# ADR 0002 — The SDK is a downstream consumer of the committed core; SDK support lags feature delivery

> **Path era.** This ADR pre-dates the 2026-07 src-layout refactor; read its
> paths through the mapping `frameforge/` → `src/frameforge/`, `models/` →
> `docs/models/`, `schema|grammar/` → `docs/…`, `fixtures/` → `tests/fixtures/`.
> The decision itself is unaffected.

## Status

Accepted. This ADR formalizes an invariant that already holds in the tree (see
the worked example); it records the rule and its consequences, it does not change
code.

## Context

FrameForge is built in two layers with a one-way dependency between them.

- **The core** is the capability contract: the Pydantic models
  (`models/frameforge.py`, the declared source of truth — see `CLAUDE.md`,
  "Project Overview"), the two grammars (`grammar/frameforge-v2*.ebnf`), the
  generated JSON Schema (`schema/frameforge-v2.schema.json`), the static-rule
  validator (`tooling/validate.py`), and the renderer (`frameforge/rendering/`).
  Together these *define and check* what a FrameForge document may say and how it
  is drawn. A capability **exists** when, and only when, the core admits it.
- **The SDK** (`frameforge/sdk/`) is an *authoring layer*: Python builders that
  lower convenient calls to a document, then validate and (optionally) render it
  through the core. The SDK produces documents; it does not define the contract.

The dependency direction is strict and verifiable in the tree:

- The SDK depends on the core. `frameforge/sdk/model.py` reaches the models via
  `model_module()`, and SDK validation/expansion checks its output against them.
- The core does not depend on the SDK. `models/frameforge.py` imports nothing
  from `frameforge.sdk` (grep confirms zero `sdk` imports). The grammar, schema,
  and validator likewise have no SDK dependency.

So the SDK is **strictly downstream**: it can only author what the committed core
already accepts. A capability the core has not admitted has nothing for the SDK
to lower *to*.

## Definitions

- **Capability** `C` — an authorable feature of the format: a new object type, a
  new field, a new accepted value shape (e.g. structured path segments), or a new
  rendered behaviour.
- **Core landing of `C`** — the merge into `main` at which `C`'s core contract
  (model + grammar + schema + validator + renderer, as applicable) is committed
  and green under `make check`. This is what "delivered to the codebase" means.
- **SDK exposure of `C`** — the merge into `main` at which an SDK builder can
  *author* `C` directly (emit the new shape, set the new field, call the new
  helper) rather than the author hand-writing the underlying document.
- **`main`** — the integration branch. "Committed into `main`" excludes work that
  exists only on a feature branch or in an open PR.

## Decision

**The SDK never leads the core. For every capability `C`, SDK exposure of `C` is
sequenced at or after the core landing of `C` in `main`; it is never before it.**

Formally, ordering merges into `main` by their position in history:

```
core_landing(C)  ≤  sdk_exposure(C)
```

with three consequences of the inequality:

1. **Floor (never before).** The SDK may not expose `C` before `C`'s core
   contract is committed to `main`. Building an SDK helper against an unmerged,
   still-mutable contract is disallowed — the contract it lowers to is not yet
   fixed.
2. **Equality is permitted.** `C` may land in core and gain SDK exposure in the
   *same* merge (one PR that adds the model field *and* the builder support). The
   SDK does not have to trail by a separate change; it must only not precede.
3. **Strict lag is the expected common case.** In practice SDK exposure trails
   core landing by one or more merges, because the core change is the deliverable
   that unblocks the SDK work, and the two are often staged separately. **An SDK
   that has not yet caught up to a committed core capability is a known,
   acceptable state — not a regression and not a defect.**

This is a *partial order on delivery*, not a mandated delay: the rule forbids the
SDK from running ahead of the committed contract; it does not require the SDK to
fall behind.

## Rationale

- **Source-of-truth discipline.** The models are the single source of truth; the
  schema, grammar, validator, and docs are *resolved views* of them. The SDK is
  another consumer of that truth. A consumer cannot correctly expose a contract
  that is not yet committed — it would be authoring against a moving target.
- **Stability of the lowering target.** The SDK's job is to lower to a *fixed*
  document shape and have it validate. If the shape is still in review (branch /
  open PR), SDK code written against it can be invalidated by the very review
  that finalizes the contract. Sequencing SDK work after the merge removes that
  rework.
- **Honest milestone accounting.** "The format can express `C`" and "the SDK can
  author `C` ergonomically" are *different* deliverables with different evidence.
  Conflating them produces the exact error this repo's roadmap has hit before:
  claiming "the SDK already ships `X`" when only the core does.

## Worked example (grounded, 2026-06-24; resolved by 2026-07-01): G-1 structured path segments

G-1 added a typed, schema-checkable structured form of a path's `d` (a
`list[PathSeg]` alongside the SVG path-data string). Its **core landing** is
committed: `models/frameforge.py` types `Path.d` as `Union[str, list[PathSeg]]`,
the grammar carries `PathSegList`/`PathSeg`/`PathCommand`, the JSON Schema
validates command + arity via `prefixItems`, and the renderer lowers the
structured form. All gated green.

At the time this ADR was written (2026-06-24), the **SDK had not yet caught
up**: `frameforge/sdk/geometry.py` authored only the string form, and no SDK
builder emitted a `list[PathSeg]`. That lag was the invariant in force — a
known, acceptable state, not a defect.

**SDK exposure has since landed (verified 2026-07-01):** `frameforge/sdk/geometry.py`
now maintains the structured form in parallel (`Path.segments()` returns the
typed `[cmd, *coords]` list) and `Path.object(structured=True)` emits `d` as a
`list[PathSeg]`; the default remains the byte-identical string form. G-1 has
therefore completed the full lifecycle this ADR describes:
`core_landing(C) < sdk_exposure(C)` — core first, SDK strictly after, exactly
the ordering the decision mandates. The generated
[capability manifest](capability-manifest.json) is the machine-readable place
this core-vs-SDK status is now tracked per capability.

## Consequences

- **Status tracking must separate the two states.** Any roadmap, status table, or
  review note must distinguish "in core" from "in SDK" as distinct milestones for
  the same capability. A claim that "the SDK ships `X`" must be verified against
  `frameforge/sdk/`, not against the model or grammar.
- **An SDK lag does not block a core merge.** Reviewers and agents must not gate a
  core capability on SDK parity, nor treat a not-yet-exposed capability as a
  regression. The follow-on SDK work is tracked as its own item.
- **SDK work presupposes a committed contract.** SDK helpers for `C` are scheduled
  only once `C` is merged to `main`; an SDK PR that depends on an unmerged core
  change waits for that merge first.
- **No deferral of the core work is implied.** This ADR governs *ordering*, not
  pace. It does not license postponing either deliverable; it only fixes their
  sequence (per `CLAUDE.md` §8, deferral remains an operator-only call).

## Non-goals

- It does **not** forbid landing core + SDK support in one PR (equality case).
- It does **not** mandate a fixed lag, a grace period, or a separate release.
- It does **not** apply to changes that are *purely* SDK-internal (ergonomics,
  refactors, new helpers over already-committed core contracts) — those have no
  core counterpart to trail.

[↑ Back to root README](../README.md)
