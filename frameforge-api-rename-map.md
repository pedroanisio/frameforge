---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code (review fixes applied 2026-07-17; original author: prior session)"
  date: "2026-07-17"
---

# frameforge.sdk — API rename & taxonomy map

**Assumption:** Decision #1 resolved as **module-qualified primary interface** (recommended).
If you choose flat instead, invert §2 (keep prefixes, extend them) and skip §3.
All renames — and all names *dropped* from the top level — ship with 1-release
deprecation aliases (§7). Target: v2.6 aliases, v3.0 removal.

**Counts are point-in-time.** The tree takes concurrent commits daily; regenerate
the export census (`python -c "import frameforge.sdk as S; print(len(S.__all__))"`
and the §6 acceptance numbers) at execution time rather than trusting the prose.
Verified 2026-07-17: `__all__` = 220 (248 module attrs incl. re-exported
submodules).

## 1. Curated top level (`frameforge.sdk.__init__`)

Shrink 220 → ~18 *documented* names. Everything else is imported
module-qualified. (See §7 for what "shrink" means at v2.6 vs v3.0 — the
runtime surface does NOT shrink until v3.0.)

```
Document, DocumentBuilder, PageBuilder, StackBuilder, MasterBuilder,
BookBuilder, ChapterBuilder, FlowBuilder, Handle,
Chart, Theme, ValidationReport, ValidationError,
validate, expand, from_markdown, assert_golden, HEAD_VERSION
```

Dropped from top level (not renamed — just no longer star-exported): all of
`paint.*`, `widgets.*`, `geometry.*`, `macros.*`, and the collision-prone
generics `parse, serialize, field, theme, md, span, table, stroke, dots,
effects, pattern, mirror, wave`.

> Corrected 2026-07-17: the earlier claim that a `manifold` function "shadows
> its own module" is not true in the live tree — `frameforge.sdk.manifold`
> resolves to the module and no function of that name exists inside it. The
> module name simply leaves the curated list like the other submodule
> re-exports; there is no shadow to fix.

## 2. Stutter renames (module prefix removed)

| Old | New |
|---|---|
| `clip.clip_circle` | `clip.circle` |
| `clip.clip_ellipse` | `clip.ellipse` |
| `clip.clip_inset` | `clip.inset` |
| `clip.clip_path` | `clip.path` |
| `clip.clip_polygon` | `clip.polygon` |
| `clip.clip_rect` | `clip.rect` |
| `clip.normalize_clip` | `clip.normalize` |
| `region.region_grade` | `region.grade` |
| `region.extract_objects` | `region.extract` |
| `region.object_bbox` | `region.bbox` |
| `region.place_region` | `region.place` |
| `figure.load_figure` | `figure.load` |
| `figure.place_figure` | `figure.place` |
| `figure.place_imported_figure` | `figure.place_imported` |
| `figure.merge_figure_defs` | `figure.merge_defs` |
| `markdown.from_markdown` | `markdown.parse` (top-level alias `from_markdown` kept) |

`lattices.lattice` stays as-is (decided 2026-07-17): module plural + function
singular is not a true stutter, and `make` says less than `lattice` does.

Name reuse across modules (`clip.inset` vs `layout.inset`, `figure.place` vs
`region.place`) is intended — the module is the disambiguator.

## 3. Module moves & splits

| Old | New | Why |
|---|---|---|
| `chevreul.contrast_ratio` | `a11y.contrast_ratio` | WCAG metric, not a Chevreul law; "contrast" currently means two things in one module |
| `chevreul.relative_luminance` | `a11y.relative_luminance` | same |
| `conform.render_page_svgs` | `render.page_svgs` | rendering ≠ conformance; `conform` keeps `page_hashes`, `assert_golden`, `write_golden` |
| `conform.render_pages_with_stats` | `render.pages_with_stats` | same |
| `chevreul` | keep; docstring cross-ref ("colour theory lives here") | consistent with the `canon.johnston_margins` decision below — a module alias would double the discovery surface (capability manifest + docs list both names forever) |
| `canon.johnston_margins` | keep; docstring cross-ref from `canon.margins` alias | same trade-off, cheaper fix |

## 4. Validation unification

```python
# validate/__init__.py — single entry point
def validate(doc, *, level="all") -> ValidationReport:
    """level: 'schema' (model rules) | 'static' (lint rules) | 'all'"""
```

- `validate.validate_document` → deprecated alias for `validate(doc, level="schema")`
  (corrected 2026-07-17: this lives in `frameforge.sdk.validate`, NOT
  `frameforge.model` — the model module has only pydantic's own
  `field_validator`/`model_validator`)
- `validate.validate_static_rules` → deprecated alias for `validate(doc, level="static")`
- `StaticValidationError` already exists as a class in `sdk.validate`
  (verified 2026-07-17) — the task is to VERIFY it subclasses
  `ValidationError` and fix the hierarchy only if it does not.
- Resolved (2026-07-17): schema and static ARE ordered stages —
  `validate_static_rules` walks the doc dict assuming model-legal shape, so a
  schema-invalid doc produces noise (or crashes) instead of diagnostics.
  `level="static"` implies schema first, fail-fast, one combined
  `ValidationReport`. Execution note: pin this with one malformed-doc test
  before hardcoding the ordering.

## 5. Spelling normalization (American canonical, British aliased)

| Old | New |
|---|---|
| `contrast_of_colours` | `contrast_of_colors` |
| `grey_document` | `gray_document` |
| `to_grey` | `to_gray` |

## 6. Doc-gen coverage gap — 22 exports have **no** module entry

These appear in `public_exports` but nowhere in `[[modules]]` (11% of surface
undocumented): `BookBuilder, BoxLike, ChapterBuilder, FlowBuilder, Hand,
HEAD_VERSION, Placement, apply_humanize, font_kern_pairs, function_plot,
kerned_spans, manifold, measure_text, multiview, parametric_curve, planar,
polar_plot, recolor, repeat_along_path, stroke_outline, text_height, wrap_text`.

Likely cause (UNVERIFIED — diagnose in the generator before fixing):
`gen_docs.py` skips re-exports without docstrings, type aliases (`BoxLike`,
`Placement`), and names re-exported from private modules.
Fix in the generator; acceptance check: the `public_exports` census in
`docs/capability-manifest.json` (regenerated by `gen_capability_manifest.py` —
this is a JSON artifact; no TOML exists in the tree as of 2026-07-17) equals
the documented-entry count. Bonus: the missing text/plot names suggest `text`
and `plot` modules that deserve first-class module sections.

## 7. Deprecation mechanism (standard, per module)

```python
_RENAMED = {"clip_circle": "circle", ...}

def __getattr__(name):
    if name in _RENAMED:
        warnings.warn(f"{name} is deprecated; use {_RENAMED[name]}",
                      DeprecationWarning, stacklevel=2)
        return globals()[_RENAMED[name]]
    raise AttributeError(name)
```

### 7b. Dropped top-level names & star imports (added 2026-07-17 — this was
the plan's contradiction: §1 shrank the surface at v2.6 while aliases covered
only renames, making v2.6 the break)

- **Every §1-dropped name stays importable at v2.6** via the same
  `sdk/__init__.__getattr__` shim (`_DEMOTED = {"span": "sdk.text", ...}` →
  warn + return). Removal happens at v3.0 only.
- **Star imports keep working AND warn at v2.6**: `from mod import *` iterates
  `__all__` and fetches each name with getattr semantics, so a name that is in
  `__all__` but *not* in module globals triggers PEP 562 `__getattr__` — the
  warning reaches star-importers. Mechanism: at v2.6, `__all__` stays fat
  (curated 18 + all demoted names), demoted names are DELETED from globals and
  served lazily with a `DeprecationWarning`; at v3.0, `__all__` shrinks to the
  §1 list and the shim is removed. The v2.6 *documented* surface (docs, MCP
  guide, capability manifest) lists only the §1 names.

## 8. Migration machinery (added 2026-07-17 — the sweep is not just the rename)

The repo ships its own callers; they migrate in the SAME commit or the release
teaches deprecated names:

1. **Codemod first.** Extend `tooling/codemod.py` with `--sdk-2-6`, driven
   mechanically by the §2/§3/§5 tables (the tables ARE the codemod spec; the
   `--from-v01` precedent shows the shape). Everything below then applies it.
2. **Cookbook** (`static/examples/*.py`): the MCP-visible SDK reference
   (`list_sdk_clients`/`read_sdk_client`) — agents copy from it. Run the
   codemod over it; re-run each client as the acceptance check.
3. **Capability manifest + MCP guide**: both introspect the SDK surface —
   rerun `gen_capability_manifest.py` and the guide regen, or the MCP layer
   advertises a dead surface (the manifest gate will catch this; don't fight
   it, regenerate).
4. **Tests**: codemod + `make test`; suites pinning old names are updated by
   the codemod, not by hand.
5. **Docs regen chain**: `make docs-sdk` (sdk-api), examples index, changelog
   entry. Diff `docs/capability-manifest.json` against this map as the review
   artifact.

Shared-tree note: this checkout takes concurrent commits from multiple
sessions daily. Land the sweep as ONE atomic commit under the `.agent-tasks/`
protocol; re-check `git log -1` immediately before committing.

## Rollout

1. v2.6: new names + §7/§7b shims + `DeprecationWarning`; fix gen_docs
   coverage (§6); run the full §8 machinery in the same commit.
2. v2.6 docs: regenerate `docs/capability-manifest.json` + sdk-api docs, diff
   against this map as the review artifact.
3. v3.0: delete the shims; `__all__` and the top level frozen to the §1 list.
