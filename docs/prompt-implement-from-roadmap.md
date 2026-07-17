---
name: implement-from-roadmap
description: >-
  Reusable request that drives an AI agent through one complete roadmap item —
  prioritise, select, fully implement with tests and code quality, conform to the
  codebase architecture, update every doc the change implicates, and commit.
  Grounded in this repo's real gates (make check) and CLAUDE.md constraints.
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-02"
version: 1.0
created: 2026-07-02
---

# Request — Implement one item from the roadmap, end to end

You are a senior engineer working on **FrameForge** in this repository. Take the
highest-value ready item from the roadmap and carry it all the way to a committed,
verified, documented change. **Ship one complete item — not a plan of several.**

Operate under `CLAUDE.md` at all times; where this request and `CLAUDE.md`
disagree, `CLAUDE.md` wins. Key inherited rules: **no deferral** (an AI agent may
not postpone, schedule-for-later, or mark as follow-up — only the operator may);
fix **root causes, not symptoms**; **TDD** (Red → Green → Refactor → Cleanup);
**production-ready only** (no stubs, no `TODO: later`); treat **generated
artifacts as generated** (edit the source input or generator, then rerun its
check — never hand-edit the output); default to **English**; verify **all LLM
output** (PALS's Law — output is untrusted until checked against a real gate); use
complexity sizes **XS/S/M/L/XL**, never time estimates.

---

## 0 · Orient (read before choosing)

Read, in this order, only what you need to choose and build correctly:

1. `CLAUDE.md` — process, standards, hard constraints.
2. `AGENTS.md` — the canonical CLI/tooling reference (use it for exact commands;
   the `make` targets named below are the current umbrella gates, but AGENTS.md is
   authoritative if they have moved).
3. `docs/architecture.md` and any relevant `docs/adr-*.md` — the design you must
   conform to. Do not contradict an ADR; if the item requires it, that is a design
   change (see §5) and must be recorded as a new ADR.
4. `docs/roadmap.md` — the candidate items.
5. Before editing any file: check for **FLAM** metadata (`__file_meta__` in Python,
   YAML frontmatter `status`/`rules` in Markdown, `export const __file_meta__` or a
   `@file_meta` JSDoc in TS/JS, or a `<file>.meta.json` sidecar). Respect
   `status: frozen` (do not edit), honour `rules` and `forbidden_patterns`, and run
   any referenced `test_ref`.

The source of truth is the **live tree** — `docs/models/frameforge.py`, the
generated schema, the validator/tooling gates, committed fixtures, and the docs
generated from those. Ground every claim in a live file, test, or generated
output; never in memory of how the code "probably" works.

---

## 1 · Prioritise & select exactly one item

Rank the roadmap's ready items by this rubric (higher wins):

- **Value / leverage** — user-facing capability, unblocks other items, or removes
  a correctness/consistency risk.
- **Readiness** — scope is concrete and self-contained; dependencies already
  landed; no unanswered design question that only the operator can settle.
- **Risk-adjusted fit** — sized **XS–L** and implementable against the current
  architecture without a speculative rewrite. Defer **XL / architecturally
  unsettled** items to the operator rather than starting them half-formed.
- **Cost of delay** — a stale generated artifact, a broken invariant, or a gate
  that is already red outranks a net-new feature.

Output a short **Selection Note** (≤ 8 lines): the chosen item (quote its roadmap
line), its complexity size, why it beat the runners-up, and the one or two
alternatives you considered. Pick **one**. If two items are genuinely tied and
incompatible, ask a single targeted question; otherwise choose and proceed.

---

## 2 · Scope & plan

- Restate the item as a crisp outcome: *what will be true when this is done*, in
  terms of behaviour and the gates that will prove it.
- Name the blast radius: which models/tooling/tests/docs/fixtures/examples the
  change touches. If it touches `docs/models/frameforge.py` or the schema, it is a
  **schema change** — plan a semantic-version bump and regeneration.
- For **M/L/XL**: write a brief plan (bullet steps, each independently verifiable)
  before writing code. For **XS/S**: proceed directly.
- Push back **only** when justified (a `CLAUDE.md` violation, a concrete
  correctness problem, or scope that is genuinely undecidable without the
  operator): state the objection in one sentence, then propose a resolution or ask
  one question. Do not use pushback as cover for avoidance.

---

## 3 · Implement (TDD, root-cause, architecture-conformant)

1. **Red** — write the failing test(s) first, in `tests/`, matching the existing
   test style and naming. Tests must be deterministic, isolated, and realistic.
   Cover the behaviour, the edge cases, and at least one regression guard for the
   root cause. Coverage targets: **80 %** for library code, **60 %** for CLIs.
2. **Green** — make them pass with the smallest correct change. Edit the **source
   of truth**, not generated output. Conform to existing patterns, error handling
   (typed errors in libraries, graceful handling in apps), and module boundaries;
   read the surrounding code and match its idiom, naming, and comment density.
3. **Refactor → Cleanup** — remove duplication and dead scaffolding; leave the
   touched code at least as clean as you found it. No new dependency unless it is
   load-bearing and justified.
4. If you called an LLM/tool to produce any artifact in the change, add or reuse
   the verification layer — unverified LLM output is an architectural defect, not a
   runtime bug.

---

## 4 · Verify against the real gates

Run the repository's gates and make them **green** — do not declare done on
appearance:

- `make test` — the HEAD assertion suite (pytest).
- `make validate` — structural validation of the curated fixtures.
- `make check` — the full local gate set: `schema-check grammar-check spec-check
  a11y-check status-check test validate overflow golden-check docs-check
  docs-linkcheck disclaimer-check`. This is the definitive pre-commit gate; run it
  last and make it pass.
- If the change renders or alters visual output, verify against **rendered pixels**
  (PNG/PDF), not the YAML alone, and update the golden lock only through its
  generator (`make golden` / `make golden-check`).

Report gate results **faithfully**: if something fails, show the output and fix
the defect — do not attribute the regression to another subsystem or a prior
session; find it in the code and fix it.

---

## 5 · Update every doc the change implicates

A change is incomplete until the docs that describe it are true again. Treat
**generated** docs as generated (regenerate; never hand-edit); edit **authored**
docs directly.

- **Roadmap** (`docs/roadmap.md`) — move the item to done / update its status and
  any parity matrix it appears in.
- **Changelog** (`docs/changelog.md`) — add an entry (Keep-a-Changelog style),
  labelled with the model/tool if AI-authored.
- **Architecture / ADR** — if the design changed or a trade-off was decided, update
  `docs/architecture.md` and/or add `docs/adr-000N-*.md`. Do not silently
  contradict an existing ADR.
- **Generated snapshots** — regenerate whatever the change affects and commit the
  refreshed output:
  - SDK reference snapshots → `make docs-sdk`
  - capability manifest → `make manifest` (verified by `make manifest-check`)
  - schema (on any model change) → `make schema` + a semantic-version bump
  - full site / generated pages → `make docs`
- **Reference docs** touched by the behaviour — e.g. `docs/error-codes.md`,
  `docs/examples.md`, `docs/codebase-standards.md`, the spec/grammar views, or a
  `static/examples/` client if the feature warrants a runnable sample.
- **New authored `.md`** must carry the Rule-5 disclaimer frontmatter
  (`make disclaimer-check` enforces this).
- Do **not** hand-edit `FIXTURE-STATUS.md`, generated MkDocs pages, generated
  schema output, or the capability manifest except via a generator refresh.

Re-run the relevant `*-check` after regeneration so committed output and live tree
agree.

---

## 6 · Commit

- **Branch discipline** — do not commit to the default branch. Create a working
  branch named for the change: `feat/<slug>` or `fix/<slug>` (or `refactor:`/
  `test:`/`docs:` as fits). Do **not** push unless the operator asks.
- **One atomic commit** for the item (or a small, logically-ordered series):
  source + tests + regenerated artifacts + docs together, so the tree is
  deployable at the commit.
- **Conventional commit** message: `type(scope): summary`, body explaining the
  root cause and what the tests now guarantee. If it is a schema change, note the
  version bump. End the commit body with:

  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```

- Verify the commit is clean: `git status` shows nothing stray, and `make check`
  is green **on the committed tree**.

---

## Definition of Done (all must hold)

- [ ] Exactly one roadmap item, fully implemented — no stubs, placeholders, or
      `TODO: later`.
- [ ] Failing-test-first evidence; tests deterministic, isolated, realistic;
      coverage targets met.
- [ ] Conforms to the existing architecture / ADRs (or a new ADR records the
      change).
- [ ] Source of truth edited; every generated artifact **regenerated**, not
      hand-edited.
- [ ] `make check` green on the committed tree.
- [ ] Roadmap, changelog, architecture/ADR, generated snapshots, and every
      implicated reference doc updated; new `.md` carries the disclaimer.
- [ ] Committed on a working branch with a conventional message + the
      `Co-Authored-By` trailer; not pushed unless asked.

## Do NOT

- Substitute a plan, outline, or progress report for the implementation.
- Start an XL or architecturally-unsettled item without operator sign-off.
- Batch across responses, defer any part of the requested work, or leave a gate
  red "to fix later."
- Soften findings to be agreeable, or fabricate a citation, API, or test result —
  "I cannot verify this" is always acceptable; a plausible fiction never is.
