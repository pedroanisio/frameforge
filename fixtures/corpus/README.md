# Expressiveness corpus (public domain)

Real-world documents that FrameGraph aims to represent and render faithfully —
the **expressiveness / completeness target**. If a `.fg` document can reproduce
each of these, the format and renderer cover the range of professional
vector/layered media they exercise.

Everything here is **public domain** — CC0, expired-copyright, or a U.S.
federal-government work (17 U.S.C. §105) — so the bytes are vendored directly
with no attribution or no-derivatives obligation.

## Layout

```
manifest.yaml     ← the source list (edit this to add documents)
lockfile.json     ← GENERATED: sha256 + size + content-type per file (integrity)
PROVENANCE.md     ← GENERATED: human-readable license table
vector/           ← SVG (the HD / vectorizable / layered core)
documents/        ← paged PDFs (multi-page layout, tables, headers)
flow/             ← long-form plain text (story flow)
html/             ← HTML+CSS (typography + flow cascade)
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
| `documents` | pages & masters, `TableObject`, running headers, embedded-font pinning |
| `flow` | `Flowable` story, pagination, long-form line-breaking |
| `html` | the `Style` + `tokens.styles` cascade, typography fidelity |

Known gaps a public-domain-only constraint imposes (best filled by **authoring
CC0 fixtures in-repo** rather than sourcing): a per-feature SVG reference suite
(resvg/W3C/WPT are permissive but not PD) and layered `.psd` files.
