# Expressiveness corpus (public domain)

Real-world documents that FrameForge aims to represent and render faithfully —
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
ui/               ← GENERATED high-def UI rasters (PNG)
ui/_src/          ← the CC0 UI source pages they are rendered from
```

## Generated UI rasters

Real app screenshots are copyrighted, so the `ui/` PNGs are high-DPI renders of
original, self-contained, public-domain (CC0) mockups under `ui/_src/*.html` —
a mobile app screen (@3x) and an analytics dashboard (@2x). They exercise the
raster-UI surface (layered cards, gradients, shadows, inline-SVG charts).

```bash
npm --prefix viewer ci                              # installs playwright (a viewer devDep)
npx --prefix viewer playwright install chromium     # one-time browser download
node viewer/dev/render-ui-corpus.cjs                # render ui/_src/*.html -> ui/*.png
python tooling/fetch_corpus.py                       # re-pin the produced bytes in the lockfile
```

The PNGs are committed; `make corpus-check` verifies their bytes like any other
corpus file. Re-render only when a source page changes.

## Manage it

Driven by `tooling/fetch_corpus.py` (stdlib + PyYAML, no new deps):

```bash
make corpus                 # download missing/changed entries; refresh lock + provenance
make corpus-check           # OFFLINE: verify on-disk files match the lockfile (CI gate)
python tooling/fetch_corpus.py --list
python tooling/fetch_corpus.py --tier vector --force
```

To add a document: append an entry to `manifest.yaml` (public domain **or**
permissive per the two-class policy above — record its `license` and
`license_url`) and run `make corpus`. The lockfile and
`PROVENANCE.md` regenerate automatically; do not hand-edit them.

## Why these documents

| Tier | Stresses (FrameForge surface) |
|---|---|
| `vector` | `path` / gradients / nested layer groups / transforms / clip — the modeled-but-unrendered effect surface |
| `reference` | one isolated effect per SVG (filter, mask, clipPath, gradient, pattern, stroke, shape, text) — the fidelity-coverage gate |
| `documents` | pages & masters, `TableObject`, running headers, embedded-font pinning |
| `flow` | `Flowable` story, pagination, long-form line-breaking |
| `html` | the `Style` + `tokens.styles` cascade, typography fidelity |
| `ebook` | packaged reflowable layout (XHTML + CSS in a container) |
| `ui` | raster UI: layered cards, gradients, shadows, inline-SVG charts |

## Open gaps (not yet sourced)

- **Layered `.psd`** and clean-licensed **`.ai` / `.docx` / `.pptx`** — best
  added once a verified permissive/PD direct source (or a generation step) is in
  place.

---

← Back to the [project README](../../../README.md).
