---
disclaimer:
  notice: >-
    No information within this document should be taken for granted. Any
    statement or premise not backed by a real logical definition or verifiable
    reference may be invalid, erroneous, or a hallucination.
  generated_by: "OpenAI Codex via purpose-md"
  date: "2026-06-23"
---

# FrameGraph

## Why We Built This

We believe important visual documents should not depend on guesswork. Too many
decks, diagrams, reports, and technical figures are easy to view but hard to
inspect, hard to reproduce, and hard to trust after they leave the tool that made
them.

The result is unnecessary friction: teams argue over screenshots, rebuild the
same layout by hand, and lose confidence in whether a document still matches the
rules it claims to follow. A useful document format should let people see the
work, check the work, and preserve the work without treating the final picture
as the only source of truth.

---

## How We Approach This

- **Truth before appearance** — A beautiful output is not enough; the underlying document must be structured, inspectable, and checkable.
- **Generated over remembered** — Living facts should be derived from checked sources whenever possible, not repeated by hand.
- **Validation over optimism** — If a claim can drift, an automated check should catch it. Unsupported behavior should be marked honestly instead of implied.
- **Authoring without lock-in** — Documents should remain readable, portable, and recoverable without a single proprietary editor.
- **Explicit limits** — The project should say what is proposed, partial, or out of scope so contributors can improve the right thing.

---

## What It Does

### Core Capabilities

- Defines FrameGraph v2, a structured document and graphics format for decks, diagrams, books, letters, fixtures, and generated visual artifacts.
- Maintains Pydantic models as the source of truth for schema, validation, migration, generated docs, and renderer checks.
- Provides tools to validate documents, migrate older documents, render proxy outputs, build documentation pages, and keep fixture status honest.
- Supplies a Python SDK and viewer experiments for authoring and inspecting FrameGraph documents.

### What This Is Not

This project does **not**:

- Promise that every renderer is conformant today.
- Treat screenshots or hand-written prose as authoritative when generated evidence exists.
- Optimize for quick demos at the expense of verifiable structure.
- Replace specialized design tools; it defines a portable, testable document substrate.

---

## Who This Is For

- **Format designers** — To evolve a visual document language with explicit trade-offs and tests.
- **Tool builders** — To create renderers, validators, viewers, and authoring helpers against a shared contract.
- **Technical authors** — To produce visual documents that can be checked, migrated, and regenerated.
- **Reviewers and maintainers** — To verify that examples, docs, and fixtures still match the current source of truth.
