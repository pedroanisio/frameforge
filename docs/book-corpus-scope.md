---
disclaimer:
  notice: >-
    No information within this document should be taken for granted. Any
    statement or premise not backed by a real logical definition or a
    verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-24"
---

# Book Corpus Scope

`tooling/fetch_book_corpus.py` defines a small EPUB/PDF corpus for inspecting book import scope without vendoring large binaries into the repository.

Run:

```bash
uv run python tooling/fetch_book_corpus.py --list
uv run python tooling/fetch_book_corpus.py --dry-run
uv run python tooling/fetch_book_corpus.py --format epub
uv run python tooling/fetch_book_corpus.py --format pdf
uv run python tooling/fetch_book_corpus.py --check
```

Default output is `_tmp/book-corpus/`, with downloaded files under `files/`, plus `lockfile.json`, `PROVENANCE.md`, and `SCOPE.md`.

## Licensing Scope

The starter corpus admits only public-domain/CC0 or attribution-only Creative Commons entries. It rejects NonCommercial, NoDerivatives, and unknown licenses by default.

The default lanes are:

- Project Gutenberg EPUBs: U.S. copyright-unrestricted/public-domain classics. Keep Project Gutenberg trademark/license constraints in mind for redistribution.
- OpenStax PDFs: openly licensed textbooks resolved through the official OpenStax books API and attributed as CC BY 4.0 works.

## Product Scope Check

This is enough for the first book-import surface if we want to inspect:

- EPUB spine/chapter structure, front matter, paragraph flow, image assets, and inline semantic text.
- PDF page geometry, headings, tables, figures, captions, formulas, sidebars, references, and dense textbook typography.
- Whether imported books can become live FrameGraph pages/objects rather than opaque rasters.

It is not enough for OCR-only scans, right-to-left scripts, math-heavy EPUB, magazines, DRM/proprietary formats, or multilingual typography. Those should be added only after the EPUB/PDF import contract is explicit.
