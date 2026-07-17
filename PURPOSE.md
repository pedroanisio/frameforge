---
disclaimer:
  notice: >-
    Nothing here should be taken for granted. Any statement not backed by a
    logical definition or verifiable reference may be invalid, erroneous, or
    hallucinated.
  date: "2026-07-17"
---

# FrameForge

## The Problem

Most visual work survives only as its final image. Structure, constraints,
semantics, and generation history are flattened into pixels or trapped in
proprietary files. So teams debate screenshots instead of inspecting evidence,
layouts are rebuilt by hand, visual rules drift undetected, and AI agents
produce approximations they cannot prove, revise, or reproduce.

A trustworthy visual system lets people and machines see, inspect, validate,
reproduce, and evolve the work — without treating the rendered result as the
only source of truth.

## The Goal

FrameForge is a rendering and visual-authoring library for agentic creation:
one structured, programmable foundation for professional visual assets —
interfaces, wireframes, vector graphics, logos, diagrams, presentations,
reports, letters, books, charts, and reusable visual systems.

It is not another file format or rendering engine. It is an agent-native
creative substrate through which artifacts are described, generated,
inspected, validated, rendered, revised, migrated, and reproduced. The
long-term direction is to consolidate desktop publishing, illustration,
interface design, presentation, and document production into one SDK and
Model Context Protocol (MCP) surface. That direction sets the bar for the
architecture; it does not claim those tools are replaced today.

## Principles

**Truth before appearance.** A beautiful output is not enough. The artifact
must remain structured, inspectable, and verifiable.

**Generated over remembered.** Facts that can change are derived from
authoritative sources, never copied into documents by hand.

**Validation over optimism.** Anything that can drift gets an automated check.
Unsupported or experimental behavior is labeled, never implied.

**Determinism over accident.** Same inputs, assets, fonts, and renderer
version — same output. Rendering is reproducible and testable by comparison.

**Semantics before pixels.** A heading, button, table, diagram node, or vector
path keeps its identity through authoring, validation, rendering, and
inspection.

**Agent-native by design.** Agents work through explicit schemas, bounded
operations, inspectable state, and verifiable results — including knowing
exactly what is unsupported.

**Acceleration without prescription.** Templates, presets, design tokens, and
intelligent defaults speed creation, but every accelerator is optional,
transparent, and overridable. Authors keep full control of typography,
geometry, color, composition, and every other expressive decision. FrameForge
accelerates creation; it does not prescribe creativity.

**No lock-in.** Artifacts stay readable, portable, and recoverable without
any single editor, vendor, or hosted service. The source outlives the tools.

**Explicit limits.** Implemented, partial, experimental, proposed, and
out-of-scope capabilities are distinguished clearly — in schemas, renderers,
and documentation alike.

## What It Provides

Structured representations that preserve content, layout, style, geometry,
semantics, constraints, and rendering intent. Pydantic models as the
executable source of truth for schemas, validation, migrations, generated
documentation, and renderer conformance. Rendering pipelines for raster,
vector, PDF, web, presentation, and publication outputs — each renderer
declaring its supported subset. Typesetting across short- and long-form work
(shaping, pagination, grids, flowing regions, footnotes, figures, tables),
plus structured composition for interfaces, design systems, diagrams, and
illustration. Tooling to create, validate, migrate, inspect, render, compare,
and measure conformance. A Python SDK and MCP surface exposing the same
document model to humans and agents alike.

## What It Is Not

FrameForge does not claim full renderer conformance, hide incomplete features
behind polished demos, treat screenshots or hand-written prose as
authoritative when generated evidence exists, equate visual similarity with
structural correctness, or promise to replace every specialized creative
application. It is the foundation from which increasingly complete workflows
are built.

## Who It Serves

Format designers, renderer developers, tool builders, agent developers, visual
designers, technical authors, maintainers, and organizations that need visual
workflows which stay portable, auditable, automatable, and independent of any
single vendor.

## The Standard

A FrameForge artifact should not merely look complete. It must be possible to
determine what it contains, how it is structured, which constraints govern it,
where its content and assets originated, which renderer produced it, what was
supported and what was not, how to reproduce it, and how to revise it safely.

The rendered artifact is the visible result. The structured, validated,
reproducible system behind it is the product.