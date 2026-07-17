---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "OpenAI Codex via purpose-md"
  date: "2026-07-17"
---

# FrameForge

## Why We Built This

Important visual work should not depend on guesswork.

Too many documents, interfaces, diagrams, reports, books, technical figures,
and visual assets are easy to view but difficult to inspect, reproduce,
validate, or modify after they leave the application that created them.

The final image often becomes the only surviving source of truth. Structure,
constraints, relationships, design decisions, semantic meaning, and generation
history are flattened into pixels or trapped inside proprietary project files.

This creates unnecessary friction:

* teams debate screenshots instead of inspecting structured evidence;
* layouts are repeatedly rebuilt by hand;
* visual rules drift without detection;
* source material and rendered output become disconnected;
* automation depends on fragile application-specific workflows;
* AI agents can generate visual approximations but cannot reliably prove,
  revise, or reproduce what they created.

A trustworthy visual system should allow people and machines to see the work,
inspect the work, validate the work, reproduce the work, and continue evolving
the work without treating the rendered result as its only source of truth.

FrameForge exists to provide that system.

---

## Our Goal

FrameForge is being built as a comprehensive rendering and visual-authoring
library for agentic creation.

Its goal is to enable people, applications, and AI agents to produce
professional-grade visual assets through a shared, structured, programmable
foundation, including:

* user interfaces;
* wireframes and prototypes;
* vector graphics;
* logos and identity assets;
* diagrams and schematics;
* presentations and slide decks;
* reports and technical documents;
* letters and formal correspondence;
* books and long-form publications;
* charts, figures, and data-driven graphics;
* reusable templates and generated visual systems.

FrameForge is not intended to be only another file format or rendering engine.
It is intended to become an agent-native creative substrate: a system through
which visual artifacts can be described, generated, inspected, validated,
rendered, revised, migrated, and reproduced.

Its long-term ambition is to consolidate workflows commonly distributed across
desktop publishing, vector illustration, interface design, presentation,
document-production, and creative-automation tools into one programmable SDK
and Model Context Protocol surface.

This ambition does not imply that every established creative application or
workflow can already be replaced. It defines the direction against which the
architecture, schemas, renderers, integrations, and conformance work should be
evaluated.

---

## How We Approach This

### Truth Before Appearance

A beautiful output is not sufficient. The underlying artifact must remain
structured, inspectable, and verifiable.

Visual quality and structural integrity are treated as complementary
requirements rather than competing priorities.

### Generated Over Remembered

Facts that can change should be derived from authoritative sources whenever
possible rather than copied manually into documents.

Generated evidence should take precedence over duplicated prose, screenshots,
or stale examples.

### Validation Over Optimism

If a claim, constraint, layout, reference, or capability can drift, an automated
check should detect it.

Unsupported, partial, experimental, or proposed behavior must be identified
honestly rather than implied through documentation or presentation.

### Determinism Over Accidental Output

Given the same inputs, configuration, assets, fonts, and renderer version, the
system should produce the same document structure and equivalent rendered
output.

Rendering should be reproducible, testable, and suitable for automated
comparison.

### Semantics Before Pixels

An element should be represented by what it is, not only by where its pixels
appear.

A heading, paragraph, button, diagram node, table, figure, citation, vector
path, page region, and reusable component should retain its semantic identity
through authoring, validation, rendering, and inspection.

### Agent-Native by Design

AI agents should interact with FrameForge through explicit schemas, constrained
operations, inspectable state, deterministic tools, and verifiable results.

Agents should be able to:

* create artifacts from structured intent;
* inspect existing artifacts;
* apply bounded modifications;
* validate constraints;
* compare revisions;
* render previews and production outputs;
* identify unsupported operations;
* preserve provenance and decision history.

### Authoring Without Lock-In

FrameForge documents should remain readable, portable, recoverable, and
transformable without depending on one proprietary editor, vendor, or hosted
service.

The source artifact must remain more durable than any individual interface used
to create it.

### Explicit Limits

The project must distinguish clearly among:

* implemented capabilities;
* partially supported capabilities;
* experimental capabilities;
* proposed capabilities;
* renderer-specific behavior;
* known limitations;
* out-of-scope functionality.

Clear boundaries allow contributors and users to improve the correct parts of
the system without relying on implied behavior.

---

## What It Does

### Structured Visual Representation

FrameForge defines structured representations for documents, publications,
interfaces, graphics, and generated visual artifacts.

These representations preserve relationships among content, layout, style,
geometry, assets, semantics, constraints, and rendering intent.

### Schema and Validation

Pydantic models serve as the executable source of truth for:

* document schemas;
* component definitions;
* validation rules;
* compatibility contracts;
* migrations;
* generated documentation;
* fixture verification;
* renderer conformance checks.

### Rendering

FrameForge provides or coordinates rendering pipelines for producing visual
outputs from structured source documents.

Target outputs may include:

* raster images;
* vector images;
* PDF documents;
* web documents;
* presentation formats;
* book and publication formats;
* interactive previews;
* renderer-specific intermediate representations.

A renderer must make its supported subset and limitations explicit.

### Typesetting and Layout

The system is designed to support sophisticated and flexible typesetting across
short-form and long-form artifacts.

This includes the eventual coordination of:

* typography;
* text shaping;
* line breaking;
* pagination;
* page geometry;
* grids;
* columns;
* flowing regions;
* footnotes and references;
* figures and captions;
* tables;
* section hierarchy;
* reusable styles;
* responsive layouts;
* print and screen output.

### Visual and Interface Composition

FrameForge extends beyond conventional document typesetting to support
structured visual composition for:

* application interfaces;
* responsive screens;
* wireframes;
* design systems;
* vector illustrations;
* diagrams;
* logos;
* iconography;
* reusable visual components.

### Tooling

The project provides tools to:

* create and edit FrameForge artifacts;
* validate documents;
* migrate older schema versions;
* inspect structure and provenance;
* render previews and production outputs;
* generate documentation;
* compare rendered results;
* verify fixtures;
* measure conformance;
* report unsupported behavior;
* maintain compatibility across versions.

### SDK and MCP Integration

FrameForge exposes a Python SDK for programmatic creation, transformation,
validation, inspection, and rendering.

Its MCP surface is intended to make these capabilities available to agentic
systems through explicit, bounded, and machine-readable operations.

The SDK and MCP interfaces should expose the same underlying document model
rather than creating separate sources of truth.

---

## What This Is Not

FrameForge does **not**:

* claim that every renderer is fully conformant today;
* claim that every creative workflow is already implemented;
* treat screenshots as authoritative when structured evidence exists;
* treat hand-written documentation as authoritative when generated evidence is
  available;
* hide incomplete functionality behind polished demonstrations;
* optimize for quick demos at the expense of verifiable structure;
* assume that visual similarity alone proves semantic or structural correctness;
* require one proprietary editor as the permanent owner of an artifact;
* promise immediate replacement of every specialized creative application.

FrameForge defines a portable, programmable, testable foundation from which
increasingly complete creative workflows can be built.

---

## Who This Is For

### Format Designers

To evolve a visual language through explicit contracts, testable behavior, and
documented trade-offs.

### Renderer Developers

To implement rendering backends against a shared schema and measurable
conformance requirements.

### Tool Builders

To create editors, viewers, validators, converters, inspectors, generators,
and automation systems around a common document model.

### AI and Agent Developers

To give agents a constrained and inspectable environment for professional
visual creation rather than relying exclusively on image generation or
unstructured application control.

### Interface and Visual Designers

To define reusable visual systems that can be generated, validated, rendered,
and maintained programmatically.

### Technical Authors and Publishers

To create documents and publications that can be checked, migrated,
regenerated, and reproduced across tools and renderer versions.

### Reviewers and Maintainers

To verify that documentation, examples, fixtures, schemas, and rendered outputs
remain aligned with the current source of truth.

### Organizations

To build visual-generation workflows whose artifacts remain portable,
auditable, automatable, and independent from a single editor or vendor.

---

## The Standard We Are Pursuing

FrameForge should make professional visual creation accessible to both humans
and agents without sacrificing structure, quality, portability, or trust.

A FrameForge artifact should not merely look complete. It should be possible to
determine:

* what it contains;
* how it is structured;
* which constraints govern it;
* where its content and assets originated;
* which renderer produced it;
* which capabilities were supported;
* which limitations were encountered;
* how to reproduce it;
* how to revise it safely;
* whether the rendered result still conforms to its declared intent.

The rendered artifact is the visible result.

The structured, validated, reproducible system behind it is the product.
