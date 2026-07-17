---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-17"
---

# FrameForge

## The Problem

Most visual work survives only as its final rendered image. Its structure,
constraints, semantics, source assets, and generation history are flattened
into pixels or trapped inside proprietary files.

As a result, teams debate screenshots instead of inspecting evidence. Layouts
are rebuilt manually. Visual rules drift without detection. AI agents produce
approximations they cannot prove, revise safely, or reproduce reliably.

A trustworthy visual system must allow people and machines to inspect,
validate, reproduce, and evolve the work without treating the rendered result
as the sole source of truth.

## The Goal

FrameForge is a rendering and visual-authoring library for agentic creation: a
structured, programmable foundation for producing professional visual
artifacts, including interfaces, wireframes, vector graphics, logos, diagrams,
presentations, reports, letters, books, charts, and reusable design systems.

FrameForge is not merely another file format, editor, or rendering engine. It
is an agent-native creative substrate through which artifacts can be
described, generated, inspected, validated, rendered, revised, migrated, and
reproduced.

Its long-term direction is to provide a unified SDK and Model Context Protocol
(MCP) surface for workflows spanning desktop publishing, illustration,
interface design, presentation design, technical documentation, and document
production. This direction defines the architectural standard. It does not
imply that every specialized tool or workflow has already been replaced.

## Principles

**Truth before appearance.**
A beautiful output is not sufficient. The artifact must remain structured,
inspectable, traceable, and verifiable.

**Generated over remembered.**
Information that can change should be derived from authoritative sources
rather than copied manually into artifacts.

**Validation over optimism.**
Anything that can drift should be checked automatically. Unsupported,
incomplete, or experimental behavior must be labeled explicitly rather than
implied through polished output.

**Determinism over accident.**
Given identical inputs, assets, fonts, configuration, and renderer versions,
the system should produce identical outputs. Rendering must be reproducible
and testable through structural and visual comparison.

**Semantics before pixels.**
A heading, button, table, diagram node, vector path, or figure must retain its
identity throughout authoring, validation, rendering, migration, and
inspection.

**Agent-native by design.**
Agents operate through explicit schemas, bounded operations, inspectable state,
and verifiable results. They must be able to determine precisely what is
supported, partially supported, experimental, or unavailable.

**Acceleration without prescription.**
Templates, presets, design tokens, layout systems, and intelligent defaults may
accelerate common constructions, but every accelerator must remain optional,
transparent, inspectable, and overridable.

Authors retain full control over typography, geometry, color, composition,
style, hierarchy, and every other expressive decision. FrameForge accelerates
creation; it does not prescribe creativity.

**Ergonomics without abstraction lock-in.**
The public API should make common constructions concise and practical while
continuing to expose the low-level primitives required to create, override, or
escape any predefined composition.

**No lock-in.**
Artifacts must remain readable, portable, recoverable, and transformable
without depending on a single editor, vendor, runtime, or hosted service. The
source must outlive the tools that created it.

**Explicit limits.**
Implemented, partial, experimental, proposed, deprecated, and out-of-scope
capabilities must be distinguished clearly across schemas, APIs, renderers,
validation results, and documentation.

## What It Provides

FrameForge provides structured representations that preserve content, layout,
style, geometry, semantics, constraints, relationships, provenance, and
rendering intent.

Pydantic models serve as the executable source of truth for schemas,
validation, migrations, generated documentation, compatibility checks, and
renderer conformance.

Rendering pipelines target raster, vector, PDF, web, presentation, and
publication outputs. Each renderer declares the exact subset of the document
model it supports and reports any unsupported or degraded behavior.

The system supports typesetting and composition across short- and long-form
work, including text shaping, pagination, grids, flowing regions, footnotes,
figures, tables, interfaces, design systems, diagrams, illustrations, and
reusable visual components.

Its tooling enables users and agents to create, validate, migrate, inspect,
render, compare, measure, and test artifacts.

The Python SDK and MCP surface expose the same underlying artifact model,
capabilities, validation rules, and renderer contracts to human developers and
software agents.

## What It Is Not

FrameForge does not claim complete renderer conformance where none exists.

It does not hide incomplete features behind polished demonstrations, treat
screenshots or manually maintained prose as authoritative when generated
evidence is available, equate visual similarity with structural correctness,
or promise to replace every specialized creative application.

It is the foundation from which increasingly complete, trustworthy, and
interoperable visual workflows can be built.

## Who It Serves

FrameForge serves format designers, renderer developers, tool builders, agent
developers, visual designers, technical authors, maintainers, and
organizations that require visual workflows to remain portable, auditable,
automatable, reproducible, and independent of any single vendor.

## The Standard

FrameForge will provide a useful and ergonomic API surface for accelerating
common constructions while always exposing the low-level primitives required
to build beyond, beneath, or outside any predefined composition.

A FrameForge artifact should not merely appear complete. It must be possible to
determine:

* what it contains;
* how it is structured;
* which constraints govern it;
* where its content, data, fonts, and assets originated;
* which renderer and configuration produced it;
* which capabilities were fully supported, degraded, or unavailable;
* how to reproduce it;
* how to compare it with another version; and
* how to revise or migrate it safely.

The rendered artifact is the visible result.

The structured, validated, inspectable, and reproducible system behind it is
the product.
