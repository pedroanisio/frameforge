# Expressiveness corpus (public domain)

Real-world documents that FrameGraph aims to represent and render faithfully —
the **expressiveness / completeness target**. If a `.fg` document can reproduce
each of these, the format and renderer cover the range of professional
vector/layered media they exercise.

Files come in two freely-vendorable licensing classes (share-alike and
no-derivative licenses are excluded):

- **Public domain** — CC0, expired-copyright, or U.S. federal works (17 U.S.C.
  §105): no obligations.
- **Permissive** — MIT / BSD / CC-BY: vendored *with attribution*, recorded
  per-file in `PROVENANCE.md` and aggregated in `NOTICE`.

## Layout

```
manifest.yaml     ← the source list (edit this to add documents)
lockfile.json     ← GENERATED: sha256 + size + content-type per file (integrity)
PROVENANCE.md     ← GENERATED: license + attribution table
NOTICE            ← GENERATED: attribution for permissive (non-PD) files
vector/           ← SVG (the HD / vectorizable / layered core)
reference/svg/    ← per-feature SVG suite (resvg, MIT) — one effect per file
documents/        ← paged PDFs (multi-page layout, tables, headers)
flow/             ← long-form plain text (story flow)
html/             ← HTML+CSS (typography + flow cascade)
ebook/            ← EPUB (packaged reflowable book)
```

## Manage it

Driven by `tooling/fetch_corpus.py` (stdlib + PyYAML, no new deps):

```bash
make corpus                 # download missing/changed entries; refresh lock + provenance
make corpus-check           # OFFLINE: verify on-disk files match the lockfile (CI gate)
python tooling/fetch_corpus.py --list
python tooling/fetch_corpus.py --tier vector --force
```

To add a document: append an entry to `manifest.yaml` (must be public domain —
record its `license` and `license_url`) and run `make corpus`. The lockfile and
`PROVENANCE.md` regenerate automatically; do not hand-edit them.

## Why these documents

| Tier | Stresses (FrameGraph surface) |
|---|---|
| `vector` | `path` / gradients / nested layer groups / transforms / clip — the modeled-but-unrendered effect surface |
| `reference` | one isolated effect per SVG (filter, mask, clipPath, gradient, pattern, stroke, shape, text) — the fidelity-coverage gate |
| `documents` | pages & masters, `TableObject`, running headers, embedded-font pinning |
| `flow` | `Flowable` story, pagination, long-form line-breaking |
| `html` | the `Style` + `tokens.styles` cascade, typography fidelity |
| `ebook` | packaged reflowable layout (XHTML + CSS in a container) |

## Open gaps (not yet sourced)

- **High-def UI rasters** — real app screenshots are copyrighted; CC0 sources
  (rawpixel) are download-gated and Wikimedia UI screenshots are uniformly
  CC-BY-**SA** (share-alike, excluded). The clean path is to render a
  public-domain UI (e.g. the U.S. Web Design System) to PNG ourselves — our own
  screenshot of PD content is PD.
- **Layered `.psd`** and clean-licensed **`.ai` / `.docx` / `.pptx`** — best
  added once a verified permissive/PD direct source (or a generation step) is in
  place.
