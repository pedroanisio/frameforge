# RENDERER-PATCH — bringing the ReportLab renderer to HEAD

**Scope.** This specifies the changes the reference renderer (`render_framegraph.py`,
the ~3,522-line ReportLab engine from the first bundle) needs to conform to HEAD. It
is a **patch specification, not a re-emitted renderer.**

**Why not re-emit it.** Re-printing 3,522 lines of someone else's renderer — most of
it unrelated to these changes — from a partial read would be both impractical and a
fabrication risk (I would be reconstructing code I cannot fully see). The honest, safe
deliverable is: (1) the **runnable enforcement** of every HEAD rule lives in
`tooling/validate.py` (you can run it today), (2) the **migration** lives in
`tooling/codemod.py`, (3) the small proxy renderer is fully patched in
`tooling/render_fg_doc.py` as a worked example, and (4) the ReportLab edits are
specified precisely below so the maintainer can apply them to the real file.

The renderer was the *most* complete implementation but still lagged the spec; these
are the deltas (cross-referenced to the complement §6.3/§6.4).

---

## 1. Stroke single-form (P3) — required

**Today:** the renderer accepts `stroke` as paint, as an inline `{color,width,dash}`,
or as a `stroke_style` name, and treats `stroke_style` as a canonical alias (permissive
dual vocabulary).

**Change:** make the resolver normative.
- Read **paint** only from `stroke` (a colour/token). If `stroke` is a dict, **reject**
  it (or, in a lenient migration mode, warn once and treat it as the codemod would:
  `color → stroke`, geometry → `stroke_style`).
- Read **geometry** (`width`/`dash`/`linecap`/`linejoin`/`arrow_*`/`opacity`) only from
  `stroke_style` (token **or** inline). A `stroke_style` bundle's `color` is the default
  paint, overridden by `stroke`.

*Pointer:* in the stroke-resolution helper, delete the inline-`stroke`-geometry branch;
route geometry through the `stroke_style` path (which already exists).

## 2. `size` → `sizing` rename (P4) — required

**Today:** content sizing is read from `size`, which collides with `IconObject.size`.

**Change:** read the content-sizing object from **`sizing`**; keep `size` numeric only
on `icon` (font size). Accept legacy `size` objects only behind a deprecation warning
(or require the codemod). The measure–arrange logic itself is unchanged.

## 3. Group-opacity isolation (P1 §3.6d) — required for correctness

**Today:** `opacity` is applied per shape, so overlapping children inside a half-opaque
group double-darken.

**Change:** when a `group` (or any container) has `opacity < 1`, render its subtree to
an offscreen group/transparency group, **flatten, then apply the opacity once**
(ReportLab: draw the subtree into a `PDFTextObject`/form XObject or a separate canvas
and composite with the group alpha). Per-object opacity still applies before flattening.

## 4. Font-pinning precondition (P4 §9.6) — required

**Today:** fonts map to FreeFont stand-ins; nothing is pinned, and there is no check.

**Change:** before the measure pass, if any text object uses non-`fixed` `sizing`,
assert its resolved font is pinned (a `tokens.fonts` entry with both `src` and `hash`);
otherwise **error** (the determinism precondition). The same check is already
implemented in `validate.py` (`unpinned-font`) — call it, or mirror it. Additionally
specify the shaping model (GSUB/GPOS under `lang`, integer-rounded advances at DPI, no
hinting in advances) and treat residual variance as a tolerance, not exact identity.

---

## 5. Spec features to implement or declare unsupported (§8.5)

These are in the spec but not in the renderer. For each, either implement it or have
the renderer **declare it unsupported** and emit a diagnostic (never a silent blank):

| Feature | Spec | Minimum conformant behaviour if unsupported |
|---|---|---|
| `media: continuous` | §3.9 | refuse with a diagnostic, or render as one tall page |
| `Pattern` tiling | §3.8 | paint `background` (or nothing) + "pattern unsupported" |
| `dimension` | §3.10 | decompose to lines+text but keep the computed value |
| rich `caption`/`credit` | §6 | render caption text; ignore credit with a notice |
| `grid_span` | §3.6e | place 1×1 and warn |

## 6. Deprecated input normalisation (optional)

Accept `circle`/`polygon`/`curve` and gradient-stop `position` for now, but prefer the
codemod (`--normalize-aliases`) to rewrite them to `ellipse`/closed `polyline`/`path`
and `offset`. Long-term the renderer should only need the normative forms.

---

## Validation hook (do this regardless)

Run the validator as a pre-render gate so the renderer never has to guess on a
non-conformant document:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tooling"))
from validate import validate_doc           # noqa
_, findings, code = validate_doc(path)
if code:                                     # hard errors → refuse to render
    for f in findings:
        if f.severity == "ERROR":
            print(f)
    raise SystemExit("document is not HEAD-conformant; run tooling/codemod.py")
```
