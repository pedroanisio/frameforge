---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-15"
title: "Tutorial"
---

# Tutorial

Learning-oriented walkthroughs: each lesson takes one concrete artifact from
nothing to a verified FrameForge document, and shows the **actual tool calls**
that got it there — including the ones that went wrong.

These are distinct from the neighbouring pages:

| Page | Answers |
|---|---|
| **Tutorial** (here) | *"Teach me the method by building one real thing."* |
| [Python SDK guide](../sdk.md) | *"What are the SDK's parts?"* |
| [Examples cookbook](../examples.md) | *"Show me a client that already does X."* |
| [Specification](../spec.md) | *"What is the normative rule?"* |

## Lessons

| # | Lesson | Builds | Introduces |
|---|---|---|---|
| 01 | [Reconstruct a book cover](lesson-01/index.md) | a photographed 1918 cloth binding, rebuilt as vectors | `measure_image`, `detect_regions`, `run_sdk_code`, `run_sdk_client`, `compare_images`; solving type from real font metrics; verifying by geometry diff |
| 02 | [Reconstruct a geometric cover](lesson-02/index.md) | a modern mosaic cover, its lattice derived from the pixels | deriving geometry by Hough + half-plane arrangement; publishing a per-face `spread` column; solving type when no installed face fits; reading `compare_images` metrics where NCC inverts |
| 03 | [Reconstruct a typeset page](lesson-03/index.md) | a chapter opening — ornament, drop cap, nine justified lines | solving a face from *word* widths under justification; `text_align: justify` as a silent SVG no-op; computing justification via `word_spacing`; deriving the baseline rule from font metrics; closing the measure≠render gap |
| 04 | [When not to reconstruct](lesson-04/index.md) | a pixel-art game screenshot — attempted, then refused | `vectorize_image` (`auto` misroutes, `region` floods validation past the token cap); testing for an upscaled pixel grid; why 94.5% pixel-match can mean *nothing at all*; metrics that fail in opposite directions; refusal as a deliverable |

## The through-line

Every lesson holds the same line, which is the repository's own
(`CLAUDE.md`, PALS's Law):

> **Output you have not verified is a claim, not a result.**

So each lesson ends with a measurement, not a screenshot — and each is candid
about what it did *not* match. A tutorial that only shows the path that worked
teaches the wrong thing: the recoveries are where the method actually lives.

---

*Back to [the site index](../index.md).*
