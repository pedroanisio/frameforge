# FrameForge v2 — CHANGELOG (HEAD)

**Version:** `2.4.1` · **Status:** PROPOSED / partially-implemented · **Date:** 2026-07-03

---

## Unreleased — feat(render): `--to audit` design-token + feature census (2026-07-17)

New render target `audit` (`frameforge_render.py <doc> --to audit`, wired in
`cli.py` `TARGETS`; core `src/frameforge/rendering/application/audit.py`) writes a
`<stem>.audit.json` + `.audit.md` report and prints a one-line verdict. It is
**drift-proof by construction**: visual tokens (font family/size/weight/style,
letter-spacing, fill/stroke colour, width/dash, opacity, gradients, plus an
`other_properties` catch-all) are read off the **emitted SVG** — the sink every
visual feature must pass through — and structural features come from a **generic
model walk** (every `type`/`kind`/key), so a feature added later is captured with
no new code. Health flags: `type-scale-sprawl` (>6 sizes), `near-duplicate-sizes`
(≤1px), `palette-sprawl` (>14 colours), `mixed-weight-encoding`. Tests:
`tests/test_audit.py`; front-door registry test updated. Not surfaced in the
capability manifest (it introspects `render_*.py`, and `audit` is a `cli.py`
target). Prose home: `docs/output-space.md`.

## Unreleased — fix(render): the flow renderer injects no undefined style ([ADR-0006](docs/adr-0006-no-injected-style.md), 2026-07-17)

The `mode: flow` renderer discarded resolved styles for headings, lists, TOC
entries, captions, and paragraph indent, falling back to scattered hardcoded
literals (`serif`/`#1c1c1c` base, TOC-title `18`, table `#f1f3f5`/`#fafafa`/
`#d8d8d8`/`#222`, caption `#666`, cell size `8`) — so an Inter document rendered
serif headings and grey table chrome, and the output did not trace to the
document. Now (spec §5.2.2): the flow default text style `base` is the document's
reserved **`body`** style (single documented fallback otherwise); `caption` is
resolved for figure/table captions; headings/lists/`toc` resolve their own
`style`; tables read `header_fill`/`header_text`/`cell_text`/`zebra_fill`/
`grid_color`/`cell_size` from their `style` (undefined chrome not drawn); an
explicit `text_indent` (incl. `0`) overrides the positional indent default. No
font/size/colour literal remains in the flow renderer beyond the one fallback.
Fixtures relying on a `body` style / injected table chrome re-rendered; golden
oracle re-pinned (`make golden`, 8 fixtures / 85 pages). Fixtures without a
`body` style are unaffected. 2009 tests green.

## Unreleased — fix(render): honor grid_span in the grid layout engine (refine pass, 2026-07-05)

`ObjBase.grid_span: [column_span, row_span]` (§3.6e) was a documented field the
layout engine silently ignored — every grid child occupied exactly one cell. The
engine now places children by **sparse occupancy** (skipped cells are not
back-filled, per the spec): a spanning child claims a `cs×rs` block and neighbours
flow around it; a filling child is sized to the full span width/height; `cs`
beyond the grid width clamps gracefully (the validator still flags `grid_span`
under a non-grid parent).

**Output-preserving** — with every span `[1, 1]` (the default, and every current
fixture — 0 use `grid_span`) the placement reproduces the former
`(i%columns, i//columns)` fill exactly, so all goldens are byte-for-byte unmoved
(`make golden-check` green). Additive, no schema change (§A.0). 5 red-first tests
(`tests/test_layout_grid_span.py`) cover column-span neighbour flow, span-width
sizing, row-span reservation, and a no-span regression lock; the existing
`group-layout` oracle is unchanged.

## Unreleased — fix(sdk): typed errors + dead-code removal (refine pass, 2026-07-05)

Library-polish follow-ups from the wiring audit:

* **Typed edge-case errors** (the SDK convention is `ValueError`, e.g.
  `layout.grid`). `widgets.dropdown(items, selected=)` raised a bare `IndexError`
  when `selected` was out of range (plausible when a dropdown re-renders after its
  item list shrank); `fields.VectorField.render` / `ScalarField.heatmap` / `.contours`
  raised `ZeroDivisionError` on `steps_x=0` / `steps_y=0`. Both now raise a
  descriptive `ValueError`. 5 red-first tests (`tests/test_sdk_error_conventions.py`).
* **Dead-code removal.** `vision…regions.extract_smooth_regions` (a superseded
  single-run variant of `consensus_smooth_regions`, advertised in `__all__` with
  zero callers anywhere) and `vision…workspace.region_from_viewport` (module-level,
  unexported, referenced nowhere) are removed. No public SDK surface affected;
  `_smooth_regions_from_mask` retains its live caller in `consensus_smooth_regions`.

Additive/subtractive-internal, no schema change (§A.0).

## Unreleased — fix(mcp): wire the CG-canon + region/clip surfaces into MCP discovery (refine pass, 2026-07-05)

A wiring/polish audit found capabilities that shipped in code + gates but were
invisible to MCP clients through the guide, and one ledger inconsistency:

* **`color_guide` was missing from the capability manifest.** `chevreul.color_guide`
  is advertised in the guide, the `_HEADLINE_SURFACES` gate, and the server
  handshake, but was never re-exported from `frameforge.sdk` — so the introspected
  ledger (built from `sdk.__all__`) could not see it. Now re-exported top-level.
* **`FRAMEFORGE_GUIDE` was stale.** It now advertises the CG-canon geometry batch
  (`bezier_patch`/`bspline_patch`, 3-D + curve intersections, `surface_curvature`,
  `convex_hull_3d`/`aabb3`/`obb`, `window_to_viewport`/`ViewingPipeline`, the named
  manifold surfaces, and `Scene3D.render(near_clip=)`), plus the previously
  guide-invisible `clip` (masking) and `region` (selection/grading) modules and the
  `lattices`/`Lattice` and `macros` capabilities.
* **The guide-coverage gate was one-directional.** `test_mcp_capabilities` now
  checks `live − (_CAPABILITY_MODULES ∪ _PLUMBING_EXEMPT)` is empty, so a NEW sdk
  module can no longer slip through unclassified and silently escape the guide.

Additive, no schema change (§A.0). `capability-manifest.json` + `sdk-api.md`
regenerated; `test_mcp_capabilities.py` extended (bidirectional gate, new headline
surfaces, a `color_guide` top-level-export lock).

## Unreleased — docs(examples): CG-canon residual-geometry cookbook page (DevX, 2026-07-05)

Closes the surface-completeness gap the roadmap's Definition-of-Done flags: the
new geometry (B5 patches, B8 curve intersections, B9 surface curvature, B10 3D
hull) shipped as SDK + ledger but had **zero** runnable examples — "code-complete,
not surface-complete". `static/examples/cg_canon_residuals_demo.py` is a single
diagram page whose every figure is live SDK output: `bezier_patch` vs
`bspline_patch` rendered side by side, a cubic Bézier crossed by a line with
`segment_curve_intersections` marking the two hits, a `surface_curvature` table
printing the API's own K/H for a sphere / saddle / plane, and the projected
`convex_hull_3d` of a 10-point cloud (24 faces). Pixel-verified at authoring;
renders to a scratch `out/` path (not a locked golden). `docs/examples.md`
regenerated (`make examples-index`).

## Unreleased — feat(sdk): B2 residual — near-plane Sutherland–Hodgman clip (CG-canon, 2026-07-05)

Advances B2's G4 residual — near-plane clipping. `Scene3D.render(near_clip=True)`
Sutherland–Hodgman-clips each face against the ``w >= near_eps`` half-space in
homogeneous clip space (the same boundary `Mat4.try_project` uses) and keeps the
retained front polygon, instead of the default behaviour of culling any face with
a vertex at/behind the plane. A triangle straddling the plane becomes the front
quad; a fully-behind face is dropped; a fully-front face is returned unchanged.

**Opt-in and default-off** — the `near_clip=False` default path is the exact prior
code, so every existing render (and golden) is byte-for-byte unmoved
(`make golden-check` green); `_avg_z` was refactored to share one depth-key
computation with the clip path (`_avg_z_h`) with no change to its arithmetic.
Additive, no schema change (§A.0). 5 red-first tests
(`tests/test_scene3d_near_clip.py`) cover the default cull, the retained front
portion, the fully-behind drop, the fully-front identity, and the default-false
guard. Residual narrows to a depth-buffer strategy (today: per-face painter's
order); the clip half of G4 is done.

## Unreleased — refactor(sdk): B1 residual — Scene3D.render adopts the window→viewport primitive (CG-canon, 2026-07-05)

Closes B1's last documented residual — "adopt inside `Scene3D.render`". The
renderer formerly hand-rolled its isotropic fit as `scale = min(bw/ww, bh/wh)`, a
second copy of exactly the mapping `sdk.geometry.window_to_viewport` computes.
`render` now takes that fit scale from the named pipeline primitive, so there is a
**single source of truth** for the window→viewport fit.

**Output-preserving** — `window_to_viewport(uniform=True).a` is *bit-identical* to
the former inline expression (verified over a 2 880-point projected scene: raw
byte-equal), so the centring and per-point mapping are unchanged and every golden
render is byte-for-byte unmoved (`make golden-check` green). This is a
consolidation refactor, not a behaviour change; a focused contract test
(`tests/test_scene3d_viewport_fit.py`) locks that render's fit *is* the primitive's
fit and pins the exact rendered coordinates so the two can never silently diverge.
No schema change (§A.0). B1 residual closed; robust clip/cull/depth remain B2.

## Unreleased — feat(sdk): B5 residual — uniform bicubic B-spline surface patch (CG-canon, 2026-07-05)

Closes B5's last documented residual — the B-spline half of "curved-surface
patches". `bspline_patch(control, ...)` and `bspline_patch_point(control, u, v)`
in `frameforge.sdk.manifold` evaluate a uniform (non-clamped) bicubic B-spline
surface over an m×n control net (m,n ≥ 4) by the tensor product of the uniform
cubic basis, tessellating `steps_u × steps_v` quads into a `Scene3D`. Unlike a
Bézier patch the surface does **not** interpolate its corner controls — it lies
inside the control net's convex hull (the basis is a partition of unity).

Additive geometry, **no schema change** (§A.0). 6 red-first tests
(`tests/test_manifold_bspline.py`) verify a planar net stays planar, the inward
corner pull to known values, convex-hull containment, an interior bulge, the
tessellation face count, and the too-small / ragged-net guards. Re-exported from
`frameforge.sdk`; `sdk-api.md` + `capability-manifest.json` regenerated. B5
residual closed (both Bézier and B-spline patches now ship).

## Unreleased — feat(sdk): B9 residual — parametric-surface curvature (CG-canon, 2026-07-05)

Closes B9's last documented residual — surface curvature completes the
curvature/arc-length family (curves already ship `CubicBezier.{curvature,
arc_length}`). `surface_curvature(fn, u, v)` in `frameforge.sdk.geometry` returns
the Gaussian curvature `K` and mean curvature `H` of a parametric surface
`r(u,v)=fn(u,v)` via the first and second fundamental forms (Mortenson §8.5). The
partial derivatives are central finite differences (step `h`); the induced normal
is `r_u x r_v`. Closed-form correct: `K=1/R^2`, `|H|=1/R` on a sphere of radius R;
`K=H=0` on a plane; `K<0` on a saddle. A degenerate point (`r_u`, `r_v` parallel)
raises `ValueError`.

Additive geometry, **no schema change** (§A.0). 5 red-first tests
(`tests/test_geometry_surface_curvature.py`) verify the unit sphere, the
1/R scaling on radius 2, a flat plane, a hyperbolic saddle (K=-4, H=0 at centre),
and the degenerate-point guard. Re-exported from `frameforge.sdk`; `sdk-api.md` +
`capability-manifest.json` regenerated. B9 residual closed — with B8 and B10 this
turn, the CG-canon curvature / intersection / hull backlog is now residual-free.

## Unreleased — feat(sdk): B8 residual — line/segment × cubic Bézier intersection (CG-canon, 2026-07-05)

Closes B8's last documented residual. `segment_curve_intersections(a0, a1, curve)`
and `line_curve_intersections(a0, a1, curve)` in `frameforge.sdk.geometry` return
every point where a query segment / infinite line crosses a cubic Bézier. The
solver is recursive de Casteljau subdivision (Mortenson §7): a sub-curve is pruned
when all four control points lie on one side of the query line, otherwise it is
split at its midpoint until the control polygon is flat, then its chord is
intersected — so a curve that meets the line up to three times yields all hits.
`tolerance` bounds the flatten error; adjacent-leaf duplicates are merged.

Additive geometry, **no schema change** (§A.0). 5 red-first tests
(`tests/test_geometry_intersect_curve.py`) cover a straight cubic's exact crossing,
a symmetric arch crossed twice, a clean miss, the bounded-segment-vs-infinite-line
distinction, and a degenerate point query. Re-exported from `frameforge.sdk`;
`sdk-api.md` + `capability-manifest.json` regenerated. B8 residual closed.

## Unreleased — feat(sdk): B10 residual — the 3D convex hull (CG-canon, 2026-07-05)

Completes B10's last documented residual: `convex_hull_3d(points)` in
`frameforge.sdk.geometry` returns the 3D hull as **outward-oriented triangular
faces** (each a tuple of three Vec3 whose normal points away from the centroid).
Brute-force face enumeration — a triple is a hull face iff every other point lies
on one side of its plane — O(n^4), intended for modest point counts (bounding a
mesh, hit-test acceleration); duplicates collapse and a fully-coplanar set yields
no faces.

Additive geometry, **no schema change**. 5 red-first tests
(`tests/test_geometry_hull_3d.py`) verify a tetrahedron's four faces, that interior
points are excluded, that every face is oriented outward, and that a cube keeps all
eight corners and drops its centre. Re-exported from `frameforge.sdk`; `sdk-api.md`
+ `capability-manifest.json` regenerated. B10 residual closed (3D hull done).

## Unreleased — feat(sdk): B5 — bicubic Bézier surface patches (CG-canon backlog, 2026-07-05)

`frameforge.sdk.manifold` gains the curved-surface patch the CG-canon backlog
(Harrington Ch11) approved — unblocked by B2:

- `bezier_patch_point(control, u, v)` — evaluate a bicubic Bézier surface at
  `(u, v)` in [0,1]² by the Bernstein tensor product over a 4×4 control net; the
  four corners are interpolated exactly.
- `bezier_patch(control, steps_u=, steps_v=)` — the same surface tessellated into a
  `Scene3D` (steps_u × steps_v quads), rendering like any manifold —
  `.render(shading="phong", cull_backfaces=True)`.

Additive SDK, **no schema change**. 5 red-first tests (`tests/test_manifold_patch.py`)
pin corner interpolation, that a coplanar control net gives a planar surface, that a
raised interior bulges off the corner plane, the tessellation face count, and the
4×4-net guard. Pixel-verified: a raised patch renders as a real curved, shaded
solid. Re-exported from `frameforge.sdk`; `sdk-api.md` + `capability-manifest.json`
regenerated. Roadmap backlog B5 -> DELIVERED (bicubic Bézier; B-spline patch the residual).

## Unreleased — docs(examples): the CG-canon capability showcase — a 60-page A4 book (2026-07-05)

`static/examples/cg_canon_showcase.py` composes *Twelve Hours of Geometry* — a
polished 60-page A4 document demonstrating every API shipped in the CG-canon
session (roadmap B1–B10 plus the 2D/3D intersection, hull, OBB, curvature, and
shading work). Every figure is **live API output**: the reflections from
`Mat3.reflect`, the crossings from the intersection primitives, the hulls from
`convex_hull`, the combs from `CubicBezier.curvature`, the fractals from
`sdk.fractal`, and the shaded solids from `Scene3D.render(shading="phong")`.

The book is itself a FrameForge document — a multi-page A4 `mode: page` composition
authored through the SDK, validated against the model + static rules on build, and
lowered to one vector PDF by `tooling/render_pdf.py`. `docs/examples.md`
regenerated; the root render artifact is gitignored.

## Unreleased — feat(sdk): B6 — shading completion: Phong specular (CG-canon, 2026-07-04)

`Scene3D` already had flat (`lambert`) and smooth (`gouraud`) *diffuse* shading;
B6 completes the canon's shading leg (Harrington Ch10) with a `phong` mode — a
**Blinn-Phong specular** highlight (`specular·max(0, n·h)^shininess` along the
halfway vector between light and viewer) layered over the diffuse base. The view
direction is taken from the camera (`eye − target`; a `+z` headlight for the
isometric path); `specular`/`shininess` are tunable via `render(...)`.

**Opt-in, output-preserving:** the default stays `shading="none"`, so existing
renders are untouched — `make golden-check` passes unchanged (8 fixtures / 88
pages). 5 red-first tests (`tests/test_scene3d_shading.py`) verify the highlight
brightens a light-and-view-facing face, that `specular=0` collapses to Lambert,
and that the highlight is **view-dependent** (weakens off-axis). `sdk-api.md` +
`capability-manifest.json` regenerated. Roadmap backlog B6 → **DELIVERED**.

## Unreleased — feat(sdk): B10 (residual) — oriented bounding box + 3D AABB (CG-canon, 2026-07-04)

Completes B10's documented residual in `frameforge.sdk.geometry`:

- `obb(points)` — the **minimum-area oriented bounding box** as 4 corners
  (rotating calipers on the convex hull; the min-area rectangle shares an edge
  with the hull, Mortenson §21);
- `aabb3(points)` — the 3D axis-aligned box (the 3D analogue of `aabb`).

Additive geometry, **no schema change**. 5 red-first tests
(`tests/test_geometry_obb.py`) verify the OBB matches an axis-aligned rectangle,
is **strictly tighter than the AABB for a rotated square** (area 2 vs 4), is never
looser than the AABB in general, and that `aabb3` bounds 3D points. Re-exported
from `frameforge.sdk`; `sdk-api.md` + `capability-manifest.json` regenerated.
Roadmap B10 residual: OBB + 3D AABB done (3D convex hull remains).

## Unreleased — feat(sdk): B8 (residual) — 3D plane / triangle intersections (CG-canon, 2026-07-04)

Completes B8's documented residual (the 3D-plane and triangle intersections) in
`frameforge.sdk.geometry` — foundational for 3D hit-testing, snapping, and B2's
clip stage:

- `ray_plane_intersection` / `segment_plane_intersection` — a plane as
  `(point, normal)`; parallel or one-sided misses return `None`;
- `ray_triangle_intersection` — Möller–Trumbore ray/triangle test (parallel,
  barycentric-miss, and behind-origin all return `None`).

Additive geometry, **no schema change**. 7 red-first tests
(`tests/test_geometry_intersect_3d.py`) pin the hits, the parallel/behind/short
misses, and the barycentric boundary. Re-exported from `frameforge.sdk`;
`sdk-api.md` + `capability-manifest.json` regenerated. Roadmap B8 residual: the
3D-plane/triangle case is now done (curve intersections remain).

## Unreleased — feat(sdk): B2 — 3D pipeline correctness: robust projection + clip + cull (CG-canon, 2026-07-04)

Fixes the highest-severity gaps in `cg-canon-3d-alignment.md` (unblocked by B1):

- **G1 (crash / mirror-flip).** `Mat4.project` raised on `w≈0` and inverted on
  `w<0`, and `Scene3D.render` projected *every* vertex — so a vertex crossing
  behind the eye (e.g. an `orbit()` sweep, or a near camera) **crashed** or
  mirror-flipped the silhouette. New `Mat4.try_project(point)` returns `None`
  at/behind the near plane instead of raising, and the renderer drops any face
  with a vertex there (near-plane **culling**, G2).
- **G3 (back-face removal).** `Scene3D.render(cull_backfaces=True)` removes faces
  whose projected polygon winds away from the camera (screen-space winding test).
  **Opt-in, default off.**

**Output-preserving:** a scene fully in front of the camera projects byte-for-byte
as before — `make golden-check` passes unchanged (8 fixtures / 88 pages), and for
in-front points `try_project` equals `project`. The existing goldens passing is
itself proof no fixture straddled the near plane. 4 red-first tests
(`tests/test_scene3d_pipeline.py`). Residual (B2 continuation): full Sutherland–
Hodgman near-plane *clipping* (split, don't drop) and a depth-strategy option
(G4, z-buffer / face split). `sdk-api.md` + `capability-manifest.json` regenerated.
Roadmap backlog B2 → **DELIVERED** (robust projection + clip + cull; G4 residual).

## Unreleased — feat(sdk): B1 — the formal viewing pipeline (CG-canon backlog, 2026-07-04)

`frameforge.sdk.geometry` gains the named viewing pipeline the CG-canon backlog's
recommended first pull calls for (Harrington ¶43/Ch6/8) — the abstraction the ad-hoc
coordinate handling in `Scene3D.render` was missing:

- `window_to_viewport(window, viewport, uniform=…)` — the affine mapping one
  `[x,y,w,h]` rect onto another; `uniform=True` is the aspect-preserving, centred
  "fit" (the classic 2D windowing transform, Harrington Ch6);
- `ViewingPipeline(camera, box)` — world → view → projection → **clip** → NDC →
  viewport; `.project(points)` fits the in-front projected points into the box,
  dropping points behind the near plane.

**Output-preserving:** the renderer is untouched (goldens unmoved). 7 red-first
tests (`tests/test_geometry_viewport.py`) pin the corner/aspect maps, the
degenerate-window guard, near-plane clipping, and — the key one — that
`ViewingPipeline` **reproduces the exact projection-fit `Scene3D.render` computes**
(bounds → uniform scale → centre), proving the equivalence. Robust segment
near-plane clipping, back-face culling, and depth ordering are B2 (which now has a
clean coordinate seam to build on). Re-exported from `frameforge.sdk`; `sdk-api.md`
+ `capability-manifest.json` regenerated. Roadmap backlog B1 → **DELIVERED**
(abstraction; adopting it inside `Scene3D.render` output-preservingly is a follow-on).

## Unreleased — feat(sdk): B4 — fractal / procedural generator (CG-canon backlog, 2026-07-04)

New module `frameforge.sdk.fractal`: a small, deterministic **L-system + turtle**
engine (Harrington Ch11, ¶39) that lowers self-similar curves to plain FrameForge
polylines — nothing here changes the schema (§A.0, the SDK computes and emits 2D):

- `lsystem(axiom, rules, iterations)` — parallel string rewriting;
- `turtle(commands, angle_deg, step, …)` — interprets `F`/`G` (draw), `+`/`-`
  (turn), `[`/`]` (branch → separate polyline); returns a list of polylines;
- presets `koch_curve`, `dragon_curve`, `sierpinski_arrowhead`.

Additive, **no schema change**. 7 red-first tests (`tests/test_sdk_fractal.py`)
pin the string rewriting, the turtle coordinate maps, the **exact** Koch generator
(the classic bump `(0,0)→(3,0)→(4.5, 3·sin60°)→(6,0)→(9,0)`), and the growth laws
(Koch `4ⁿ` segments, Dragon `2ⁿ`). One real bug caught red-first: `[` was
splitting the trunk polyline; the branch now saves/restores the trunk so it stays
unbroken. Re-exported from `frameforge.sdk`; registered in the gen-docs module
list, the MCP capability guide, and `test_mcp_capabilities`; `sdk-api.md` +
`capability-manifest.json` regenerated. Roadmap backlog B4 → **DELIVERED**.

## Unreleased — feat(sdk): B10 — convex hull + computational-geometry primitives (CG-canon backlog, 2026-07-04)

`frameforge.sdk.geometry` gains the comp-geometry primitives the CG-canon backlog
(Mortenson §21) approved — broad-phase bounding for B8, layout/packing, hit-test
acceleration:

- `convex_hull(points)` — 2D Andrew's monotone chain (O(n log n)); duplicates
  collapsed, collinear edge points excluded, 0/1/2-point inputs degrade cleanly;
- `aabb(points)` — axis-aligned bounds as `(min, max)`;
- `polygon_area(ring)` — signed shoelace (sign = winding, `abs` = area);
- `point_in_polygon(point, ring)` — even-odd ray crossing.

Additive SDK, **no schema change**. 8 red-first tests
(`tests/test_geometry_hull.py`) verify the hull against a **brute-force O(n³)
oracle** on a non-collinear set, pin the collinear/duplicate/degenerate
conventions, assert the returned ring is convex, and check the signed-area sign
flip. Re-exported from `frameforge.sdk`; `sdk-api.md` + `capability-manifest.json`
regenerated. Roadmap backlog B10 → **DELIVERED** (2D; 3D hull + OBB the residual).

## Unreleased — feat(sdk): B9 — curvature & arc-length for curves (CG-canon backlog, 2026-07-04)

`frameforge.sdk.geometry.CubicBezier` gains the differential-geometry surface the
CG-canon backlog (Mortenson §6.7) approved — it upgrades tessellation/outline and
aids the B5 patch work:

- `derivative(t)` / `second_derivative(t)` — the hodograph B'(t) and B''(t);
- `curvature(t)` — signed κ = (x'y'' − y'x'') / (x'² + y'²)^{3/2} (`|κ| = 1/R`,
  sign = bend direction; 0 at a cusp);
- `arc_length(tolerance)` — ∫₀¹ |B'(t)| dt by adaptive Simpson on the speed;
- module `polyline_length(points)` — the exact discrete analogue.

Additive SDK, **no schema change**. 8 red-first tests
(`tests/test_geometry_curvature.py`) verify against **analytic truths**, not just
each other: a straight-line cubic has κ ≡ 0 and length == chord; the κ
quarter-circle Bézier integrates to ≈ π/2 with curvature ≈ 1/R at its midpoint;
mirror-bent cubics have opposite-signed curvature; and every arc length lies
strictly between its chord and its control-polygon length. Re-exported from
`frameforge.sdk`; `sdk-api.md` + `capability-manifest.json` regenerated. Roadmap
backlog B9 → **DELIVERED**.

## Unreleased — feat(sdk): B8 — 2D geometric-intersection primitives (CG-canon backlog, 2026-07-04)

`frameforge.sdk.geometry` gains the intersection primitives the CG-canon backlog
flags as foundational for hit-testing / snapping / clipping:

- `line_intersection(a0, a1, b0, b1)` — the two infinite lines' crossing;
- `segment_intersection(a0, a1, b0, b1)` — two segments (bounded on both);
- `ray_segment_intersection(origin, direction, s0, s1)` — a ray against a segment;
- `segment_polygon_intersections(a0, a1, polygon)` — every edge crossing,
  de-duplicated at shared vertices.

Each is one parametric 2D cross-product solve; parallel and collinear inputs
return no crossing (`None` / `[]`), so a collinear overlap is never mis-reported
as a single point. **Scoped to the 2D primitive core** — the 3D-plane and
curve intersections also named in B8 are the item's documented expansion.

Additive SDK, **no schema change**. 12 red-first tests
(`tests/test_geometry_intersect.py`) cover crossings, T-junctions, shared
endpoints, the segment-vs-line distinction (a pair whose *lines* cross but whose
*segments* don't reach), ray direction, and polygon entry/exit. Re-exported from
`frameforge.sdk`; `sdk-api.md` + `capability-manifest.json` regenerated. Roadmap
backlog B8 → **DELIVERED** (2D core).

## Unreleased — feat(sdk): B7 — reflection / mirror transform (CG-canon backlog, 2026-07-04)

`frameforge.sdk.geometry` gains the reflection transform the CG-canon backlog
(Mortenson §3.6) approved:

- `Mat3.reflect(axis)` — the reflection matrix across the x-axis (`"x"`, `y→-y`),
  the y-axis (`"y"`, `x→-x`), or an arbitrary line given as two points `(p0, p1)`
  (mirror through that line, wherever it sits — computed by conjugating the
  through-origin reflection `[[cos2θ, sin2θ],[sin2θ, -cos2θ]]` with a translation).
- `mirror(points, axis)` — apply it to a sequence of points; the primitive for
  building a symmetric shape from one half.

Additive SDK, **no schema change** (§A.0 — the SDK computes, the document
receives plain 2D geometry). 8 red-first tests (`tests/test_geometry_reflect.py`)
pin the coordinate maps *and* the two structural invariants — reflection is
orientation-reversing (`det == -1`) and an involution (`reflect ∘ reflect == I`).
Re-exported from `frameforge.sdk`; `sdk-api.md` + `capability-manifest.json`
regenerated. Roadmap backlog B7 → **DELIVERED**.

## Unreleased — feat(dx): `.pre-commit-config.yaml` — the same gate, earlier (§16 row 6, 2026-07-04)

Closes §16 row 6. A committed `.pre-commit-config.yaml` runs the repo's own gates
as git hooks:

- **commit time** → `make ruff-check` (the fast F811 redefinition gate), so a name
  collision is caught the instant it's committed;
- **push time** → the full `make check`, byte-for-byte the same command CI runs.

Both are `local` / `language: system` hooks that shell out to the Makefile, so
pre-commit pins **no** tool versions of its own — it cannot drift from
`pyproject.toml`/`uv.lock`, and the hook surface cannot drift from the gate list
(it *is* `make check`). Opt-in per clone with `make hooks`
(`uvx pre-commit install --install-hooks`).

Verified functionally (not just parsed): `pre-commit validate-config` passes and
`pre-commit run ruff-check --all-files` executes the hook green.
`tests/test_precommit_config.py` pins that the config exists, parses, and runs
both `make check` and `make ruff-check` (the anti-drift guard, mirroring
`test_ci_make_check_sync`). codebase-standards §10 flips the pre-commit `[Target]`
to `[Adopted]` and corrects the stale "fourteen gates" → **thirteen**; AGENTS.md's
make-target table gains `ruff-check` + `hooks`; row 6 leaves the §16 ledger.

- **Not a schema change** — no version bump.

## Unreleased — fix(model): resolve the `Image` alias/class name collision + gate F811 (2026-07-04)

The source-of-truth model bound `Image` to two different meanings: a paint-value
type alias `Image = Union[Gradient, UrlImage, str]` (line 187) **and** the `Image`
object class (the `type: "image"` visual object). Under `from __future__ import
annotations`, field annotations resolve lazily against the module namespace, so
which `Image` a field binds to is **definition-order dependent** — the three
fields annotated `Image` (`BackgroundLayer.image`, `Style/StrokeStyle/
TextStyle.background_image`, `.mask`) resolve to the alias *only* because their
classes are defined before line 1089 rebinds the name to the class. A field added
after the class would silently bind to the OBJECT instead. ruff flags it F811.

Fixed at root: the alias is renamed `ImagePaint` (the object class keeps `Image`);
the three annotations updated. **Schema is byte-identical** — the resolved field
types are unchanged (`Union[Gradient, UrlImage, str]`), verified by
`build_schema.py --check` — so this is **not** a schema change and carries no
version bump. The second F811 in the tree — `tests/test_sdk.py` shadowed the
imported `hatch()` helper with a local of the same name, so the helper went
untested — is fixed by actually calling `hatch(...)` (real coverage) under a
distinct local name.

Guards (PALS's Law — the fix ships with the gate that prevents its return):

- `tests/test_model_no_name_collisions.py` — a dependency-free AST check that no
  module-level name in the model is bound to **both** a class and a type alias.
- `make ruff-check` (new, **thirteenth** gate in `make check`) runs
  `ruff check --select F811`; a committed `[tool.ruff]` section pins
  `target-version = "py310"` and documents the tiering. This lands the gating
  half of codebase-standards §16 row 1 (scoped to F811; broadening to F401/F841
  and `ruff format` is the row's remaining expansion). `make lint` stays the full
  informational (non-gating) ruff run.

## Unreleased — feat(packaging): honest 3.10–3.12 support — CI matrix + classifiers (§16 row 8, 2026-07-04)

Closes §16 row 8 and fixes a live correctness gap: the `>=3.10` support claim
was **false**. `tests/test_docs_in_sync.py` bare-imported `tomllib` — a stdlib
module that only exists on **3.11+** — so `make check` (and any 3.10 CI leg)
crashed at import on the minimum Python the project claims. The `tomli` backport
its sibling `check_package_readiness.py` falls back to was never declared either;
it was present only transitively via pytest, an accident rather than a contract.

Made the claim true at root:

- **The floor is runnable.** `test_docs_in_sync.py` now uses the same guarded
  `import tomllib / except ModuleNotFoundError: import tomli` idiom the tooling
  uses, and `tomli>=2 ; python_version < "3.11"` is a declared `dev` dependency
  (a no-op on 3.11+). Behaviourally verified: with `tomllib` masked, the fallback
  resolves via `tomli` and parses. `uv.lock` refreshed (+1 direct edge).
- **The versions are exercised, not just asserted.** `ci.yml`'s python-gates job
  runs a `["3.10","3.11","3.12"]` matrix (`fail-fast: false`,
  `uv sync --python ${{ matrix.python-version }}`); it still `run: make check`, so
  the CI ⇄ make lockstep test stays green.
- **The metadata is declared.** `pyproject` gains `classifiers` (naming 3.10/3.11/
  3.12, no `Typing :: Typed` — py.typed is still a gap), `authors`, `[project.urls]`,
  and `keywords`. This closes the `publish metadata polish` gap in
  `make package-check`, whose verdict drops to **3 blockers, 1 gap** (only the §1
  `py.typed` target remains).

Regression gates: `tests/test_python_version_support.py` (no gate module
bare-imports `tomllib` without the `tomli` fallback; the backport is declared with
its `<3.11` marker; classifiers ⇄ `requires-python`) and a new assertion in
`tests/test_ci_make_check_sync.py` (the matrix covers all three). `test_package_readiness.py`
updated to the 1-gap verdict; codebase-standards §1 flips the classifiers/CI-matrix
`[Target]` to `[Enforced]`, §9/§16 re-count, and row 8 leaves the ledger (rule of
motion).

- **Not a schema change** (no model/schema touched) — no version bump.

## Unreleased — fix(tooling): repair the package-emit checker for the src layout (2026-07-04)

`tooling/check_package_readiness.py` went stale in the 2026-07-02 folder
refactor. It still inspected `ROOT/frameforge`, `ROOT/models`, `ROOT/schema`
— paths that moved to `src/frameforge`, `docs/models`, `docs/schema` — so it
passed *vacuously* over locations that no longer exist and emitted a **false
verdict**:

- it **dropped a live blocker** — `docs/models/frameforge.py` still shadows the
  `frameforge` dist name, but the checker looked in the empty `ROOT/models` and
  reported "no collision"; and
- it **reported a closed gap as open** — row 7 landed
  `frameforge.__version__` in `src/frameforge/__init__.py` (2026-07-04), but the
  checker read the nonexistent `ROOT/frameforge/__init__.py` and still flagged
  the `__version__` gap.

A verification tool that inspects a moved path passes vacuously — the PALS's-Law
failure mode (a broken verification layer is a design defect, not a runtime bug).

Fixed at root: the checker now inspects the live `src/frameforge` package and the
`docs/models`/`docs/schema` reference sources. Its verdict is true again —
**3 blockers, 2 gaps** (was mis-reporting 2 blockers, 3 gaps). New regression
`tests/test_package_readiness.py` pins the corrected verdict and guards the
inspected paths against going stale a second time (they must exist, or the gate
fails loudly). `codebase-standards.md` §9/§16 updated to the true counts;
`test_package_boundary.py`'s claim that the checker "asserts the same thing" is
accurate again.

- **Not a schema change** (no model/schema touched) — no version bump.

## Unreleased — docs(grammar): the `graph` authoring object + an expansion-form coverage gate (2026-07-04)

Item 1 shipped the declarative `type: graph` object but left the format
grammar stale: the EBNF documented the sibling pre-expansion forms
(`UseObject`, `ComponentObject`) yet not `GraphObject`. The core
grammar-check gate could not catch this — these forms have no Pydantic
model (they lower via `sdk.expand` before validation), so nothing forced
their presence. Closed at root:

- `GraphObject` (+ `GraphNode`/`GraphEdge`) added to the EBNF as a
  `VisualObject` alternative, matching how `use`/`component` are
  documented; the spec's extended-objects list now names graphs and
  explains that `use`/`component`/`graph` are pre-expansion authoring
  forms lowered by `sdk.expand`.
- a new gate (`tests/test_grammar_sync.py`) pins the invariant: the set of
  authoring types `sdk.expand` dispatches (`use`/`component`/`graph`) is
  exactly the set the grammar documents — so a future expansion form can't
  silently miss the grammar again. grammar-check stays green (the new type
  is one more non-blocking out-of-profile WARN: 29→30, 0 errors).

## Unreleased — chore: runtime `frameforge.__version__` + `make release` (§16 row 7, 2026-07-04)

Closes the runtime-version half of the package-emit gap. `frameforge.__version__`
is now a real attribute on the package — a fifth version literal that `make bump`
moves in lockstep and `tests/test_docs_in_sync.py` gates against `[project]
version`, so the package can report its own version and it can never drift. A
plain literal (not `importlib.metadata`) because this is a virtual, uninstalled
project. New `make release VERSION=X.Y.Z` runs the whole recipe end to end — bump
every site → regenerate schema/manifest/SDK-snapshots/status/examples-index →
`make check` — leaving only the git-tag and CI-publish steps by hand (it prints
them). RELEASE.md updated to five literals + the `I2b` invariant; codebase-standards
§9/§16 row 7 marked done.

## Unreleased — item 1: declarative graph auto-layout (the render-time bridge, 2026-07-04)

`sdk.topology.Graph` already computed node placements from declared edges,
but only author-side (call a layout method, bake the coordinates). This
wires it as a DECLARATIVE, expansion-tier form (roadmap item 1 — the
missing render-time bridge; the placement math was already done):

- A grammar-level `type: graph` object (`nodes` + `edges` + `algorithm`) is
  lowered by `sdk.expand` into a positioned core `group` — the SDK computes,
  the document receives plain `ellipse`/`polyline`/`text` geometry (§A.0).
  `algorithm: auto` infers grid/radial/layered/spring from structure; a
  node's `pos` OVERRIDES the computed position. **No schema change**: `graph`
  is a pre-expansion authoring type, exactly like `use`/`component`, and
  never reaches the validated document.
- `Graph.to_object(box=…, algorithm=…)` emits that declarative form fluently
  (positions NOT baked — the same declaration always lays out the same way).
- The `expand` early-return now also detects self-contained `graph` objects,
  so a document with no `defs.symbols`/`components` still lowers them; a
  document with no expansion form is byte-identical through `expand` (golden
  stability preserved).

13 red-first tests (`tests/test_sdk_graph_expand.py`); fixture
`graph-autolayout.fg.yaml` (four graphs: auto→layered/radial/spring + an
explicit circular override), pixel-verified 0 clipped/0 uncontained;
runnable `static/examples/graph_autolayout_demo.py`; MCP guide bullet
(drift-gated). Roadmap item 1 → **DONE** (residual: optional ELK binding).

## Unreleased — fix(pdf-tex): transforms reach text; effect + appearance stacks render (2026-07-04, issue #53)

Three silent-fidelity gaps on the `--to pdf-tex` path (the
`latex.tikz.FigureTikz` transpiler), all operator-reported from the book
PDF and verified in rasterized pixels:

- **`style.transform` now reaches text.** A TikZ scope transform moves
  `\node` ANCHORS but leaves glyphs unscaled/unrotated — a 0.5-scaled
  group painted full-size text over shrunken geometry. The transform scope
  now carries `transform shape`, so text obeys it (repro: scaled "SCALED?"
  text ended at x≈331 of 400 before, x≈175 after). Fixed in both the
  transpiler and the injectable `TikzPainter`; the painter's `raw`
  transform branch also now parses SVG-syntax `scale(0.5)` into valid TikZ
  `xscale/yscale` (it was emitting invalid `scale(0.5)` the TeX engine
  ignored).
- **The 2.4.0 `effects` stack renders.** The ordered stack was dropped
  silently — only the legacy `shadow`/`glow` fields got the flat
  approximation. Stack entries now get the same shadow/spread-glow
  approximation (blur is approximated, never silent).
- **The 2.4.0 `appearance` stack renders.** Multiple paint passes were
  collapsed to the bare geometry; each pass now paints its own path,
  bottom→top, mirroring the Renderer's `_appearance_stack`.

The `TikzPainter` ScenePainter port (no filter primitive at all) declares
`supports_filters = False` and the Renderer warns per dropped effect
rather than losing it silently (#44). 12 red-first tests
(`tests/test_tikz_fidelity.py`); the pinned latex-scope assertions that
encoded the old bug were corrected. SVG output is byte-identical (goldens
unmoved).

## Unreleased — item 8: the Book composition API (2026-07-03)

`frameforge.sdk.book` — the semantic authoring layer above pages
(roadmap implementation-sequence step 5; zero grammar change):
`BookBuilder(title=, author=)` composes front matter and
chapters/sections into ONE validated flow document, lowered through
`FlowBuilder` and paginated by the ADR-0003 engine. Numbering is computed
at build time (§A.0 — the renderer has no counter engine): chapters `1`,
sections `1.1`, per-chapter figure labels folded into captions
(`Figure 2.1 — …`). Chapters open on fresh pages; `keep_with_caption`
holds a figure and its caption together (`break_inside: avoid`). Two
defects caught by pixel verification and fixed in the design: the book no
longer lists ITSELF in its own Contents (the title is front-matter
display, not a heading), and a BOXLESS figure object (e.g. a computed
`stroke_outline` path) gets its size derived from the geometry instead of
silently reserving zero flow height and painting over the next block.
10 red-first tests (`tests/test_sdk_book.py`, incl. the render gate:
clipped == 0, numbered captions reach the pixels); fixture
`book-composition.fg.yaml` (corpus 37→38, 0/0); runnable
`static/examples/book_builder_demo.py`; MCP guide bullet (drift-gated).

## Unreleased — PALS PT-BR migrated; gradient fill tokens now lift AND paint (2026-07-03, issue #33)

Third corpus deck: the 15-slide PALS PT-BR deck lands as
`tests/fixtures/pals-genai-arch-ptbr.fg.yaml` (corpus 36→37; 0 errors, two
honest tabular advisories on the hand-positioned math appendix). One new
dialect corner, closed in two layers:

- **Lift** (`codemod.py --from-v01`): v0.1 gradient fill tokens
  (`tokens.fill_styles` `{type: linear_gradient, from/to points, stops
  with offset+opacity}`) become v2 `Gradient` paints — from/to vector →
  CSS `angle`, `offset` → `position`, stop `opacity` folded into an
  8-digit hex against the pack palette (v2 stops carry no opacity field).
- **Renderer**: `Tokens.fill_styles` was model-declared but NEVER read —
  a string fill naming a fill-styles key silently emitted invalid SVG
  paint. `paint()` now dereferences `tokens.fill_styles` first, so named
  gradient/pattern fills actually paint (regression-tested).

Verified page-by-page against the sibling's own renderer (15/15 pages;
deltas are the known cross-renderer font face + in-box wrapping, no
content loss — `clipped == 0`, spill only via the explicit v0.1 policy).
3 new red-first tests (19 total). Checklist honesty: **faz-ai and
code-base-mapper are #30-gated** (49/57 `type: uml` objects — the
unabsorbed UML composers); GTDS awaits the token-pack decision.

## 2.4.1 — parity W1: the planar geometry kernel + the DocumentRenderer port (2026-07-03, issue #45)

Also in this patch: the **`DocumentRenderer` output port** (hexagonal seam)
— the CLI's html / pdf-tex targets render through in-process backends
(`rendering/infrastructure/backends/`) instead of shelling out to our own
scripts; one registry adapter per `--to` target
(`tests/test_document_backends.py` locks the contract).

`frameforge.sdk.planar` — one expansion-tier kernel closes five rows, zero
schema change (§A.0: the SDK computes, documents receive even-odd `path`
objects): **booleans** `union`/`intersect`/`subtract`/`divide`
(Greiner–Hormann on flattened rings; degenerate touching/shared-edge inputs
resolved by a deterministic direction-cycling perturbation that prefers the
ENGAGED answer; holes emitted natively as multi-ring even-odd paths —
AI-04 PARTIAL→HAS, AI-05 NONE→REFRAMED), **path surgery** `split_at`
(arc-length scissors) + `cut_along` (knife via half-plane booleans —
AI-06 NONE→HAS), **`offset_polygon`** (closed, miter-exact corners,
collapse detected by edge-direction reversal, not just area sign — a
double-inverted shrink traces a *positively*-oriented ring — AI-47
NONE→HAS), and **`fill_regions`** (Live-Paint decomposition as boolean
atoms, authoring scope ≤8 shapes — AI-17 PARTIAL→HAS). Stdlib-only, pure,
deterministic. 18 property tests (areas, ring counts, membership, length
conservation); fixture `planar-kernel.fg.yaml` (corpus 35→36, 0/0)
pixel-verified — holes punch through, divide partitions, nested offset
rings, knife halves, region faces each their own colour. Teardown + audit
regenerated: **25 HAS / 5 PARTIAL / 11 REFRAMED / 10 NONE** (full 49 %,
reachable 80 %) — **the maturity-gap pool is now empty**.

## 2.4.0 — parity W4: style & colour richness (2026-07-03, issue #48)

**Schema minor bump 2.3.0 → 2.4.0** — two ADDITIVE model fields on ObjBase,
both outside the deep-core profile (§8.5, charts precedent; grammar core
untouched, schema regenerated to 85 $defs):

- **`effects`** (AI-30 PARTIAL→HAS): an ORDERED effect stack — entries
  `{kind: shadow|glow, preset?, color/blur/dx/dy/opacity?}` apply
  first→last and a kind may repeat (the single `shadow`/`glow` fields
  cannot); presets seed params, explicit keys override. Absence is
  identity (effect-free renders are byte-identical; golden gate green).
- **`appearance`** (AI-32 PARTIAL→HAS): multiple paint passes over one
  geometry — each pass paints only what it declares (fill / stroke /
  stroke_style / opacity), bottom→top; clones drop ids/binds so identity
  appears once; object-level effects and opacity wrap the whole stack.
- **`sdk.recolor(doc, mapping)`** (AI-16 PARTIAL→HAS): one-call palette
  remap — `defs.tokens.colors` by name or value, paint literals under
  paint keys only (a hex inside text content is never rewritten), and
  gradient stops; case-insensitive, input never mutated.
- **`chevreul.color_guide(base)`** (AI-18 PARTIAL→HAS): the six Chevreul
  harmonies for any base colour (snapped to its nearest wheel station),
  ready to feed `closed_palette` / `recolor`.

13 red-first tests (`tests/test_style_richness.py`); fixture
`style-richness.fg.yaml` (corpus 34→35, 0/0 — the effect filters are
structurally verified in the SVG; the cairosvg proxy ignores filter
primitives, browsers render them); runnable
`static/examples/style_richness_showcase.py`. Teardown + audit
regenerated: **21 HAS / 7 PARTIAL / 10 REFRAMED / 13 NONE** (full 41 %,
reachable 75 %).

## Unreleased — parity W2: the stroke-outline engine + curve/type finesse (2026-07-03, issue #46)

`frameforge.sdk.outline` — one shared filled-outline emitter closes three
verdicts and two finesse rows, all at author time (nothing new enters the
schema): `stroke_outline(points, width, …)` lowers a stroke centre-line to
a CLOSED filled `path` — constant width is Outline Stroke (AI-48 NONE→HAS),
a `profile(t)` callable is the Width tool (AI-12 NONE→HAS), a calligraphic
pen (`pen_angle`/`pen_thin`: width `w·√(cos²Δ+thin²·sin²Δ)` vs the tangent)
is the calligraphic brush, and `repeat_along_path` (arc-length placements
with tangent rotation, `stamp=` for direct object copies) is the
scatter/pattern half (AI-49 NONE→PARTIAL — art-brush stretch and Blob stay
honest gaps). Caps butt/square/round (round routed explicitly through the
outward direction — the shorter-sweep arc is ambiguous at π), joins
miter/bevel/round. `Path.through()` (Catmull-Rom) verified + tested as the
declarative curvature tool (AI-09 PARTIAL→REFRAMED). Kerning (AI-24
PARTIAL→HAS): `kerned_spans` (explicit pairs as grammar-native span
styles) + `font_kern_pairs` (the resolved font's kern table via fontTools;
degrades to `{}`). **Renderer fix found by pixel-verifying this feature**:
structured-`d` segments arrive as TUPLES from a pydantic model dump and
all three painters (SVG + both TikZ sites) only lowered lists — every
structured path silently rendered as a stringified Python tuple (garbage
that also hangs cairosvg). 16 red-first tests (`tests/test_sdk_outline.py`)
incl. the round-trip regression; fixture `stroke-outline.fg.yaml` (0/0),
runnable `static/examples/stroke_outline_showcase.py`. Teardown + audit
regenerated: **17 HAS / 11 PARTIAL / 10 REFRAMED / 13 NONE** (full 33 %,
reachable 75 %).

## Unreleased — parity W6: six teardown verdicts corrected by documentation (2026-07-03, issue #50)

The cheapest scoreboard movement, delivered exactly as scoped: zero schema
change, every claim verified against live code before any doc moved (PALS).
Five rows re-verdicted **PARTIAL → REFRAMED ·H** — anchor editing (restate
the coordinate: MCP `workspace` pin/nudge/snap + `construct_vectors`),
isolation mode (name the nested id; the cursor hazard has no declarative
analogue), the Bézier pen (coordinates are the pen; `construct_vectors` +
coach are the assistive half), artboards (pages + per-page canvas + render
targets, by design), guides/rulers/snap (exactness by construction +
`canon.content_box` grids + `workspace` snap). AI-40 verified in code:
`Scene3D.extrude`/`.revolve`/`Material` are real and project to 2D vector
faces — evidence corrected, verdict honestly stays **PARTIAL ·H** (no
bevel). Bonus: the REFRAMED narrative example mislabeled Image Trace as
AI-40 (it is AI-39) — fixed. Teardown deck + git-stamped audit regenerated:
**14 HAS / 12 PARTIAL / 9 REFRAMED / 16 NONE**; reachable-by-any-route
stays 69 % (W6 adds no capability, by design). Roadmap Appendix B + the
workstream table re-verdicted to match.

## Unreleased — PALS EN deck migrated; the v0.1 lift learns the deck dialect (2026-07-03, issue #33)

Second corpus deck: the 8-slide PALS GenAI architecture deck (EN) lands as
`tests/fixtures/pals-genai-architecture.fg.yaml` (corpus 32→33; 0 errors,
one honest tabular-box-model advisory on the hand-positioned slide-8
matrix). Four dialect corners closed in `codemod.py --from-v01`, red-first:

- **`chip_row`** (v0.1 compositional pill row) lowers to a core `group` of
  decorative pill rects + centered texts — same cursor/gap layout, the
  `chip` component def's fill/text_style/radius baked in; a consumed def is
  dropped (lossless), unconsumed defs are kept.
- **Flat span styles** (`{text, weight, color}`) nest into a translated
  inline `style` (v2 `Span` allows text/style/lang only).
- **Flat object `stroke_width`** moves into `stroke_style` (P3).
- **v0.1 wrap semantics pinned**: text wrapped only under `wrap: true`, and
  overflow painted past the box — styles without `wrap` now get
  `white_space: nowrap` and deck-form pages get
  `rendering.text.overflow: visible`. Found the hard way: under v2's
  wrap-then-clip default, slide 3's consequence sentence was silently
  truncated mid-word — exactly the #44 failure class; the gate now asserts
  `clipped == 0` and spill only via the explicit policy, and the genai
  fixture regenerated under the same rules moved *closer* to its v0.1
  reference (RMSE 14.7 → 13.3). PALS renders verified page-by-page against
  the sibling's own renderer (mean RMSE 18.4/255, differences are font
  rasterization and tighter in-card wrapping, no content loss). 6 new
  red-first tests (16 total in `tests/test_codemod_v01.py`).

## Unreleased — font determinism end to end (ADR-0004, 2026-07-03)

The measure==render loop is closed, host-independently
([ADR-0004](docs/adr-0004-single-engine-layout.md)):

- **Browser-faithful font resolution** in the layout metric, and a
  **screaming `font_substitution` warning** (diagnostics + stderr, once per
  family) whenever a requested content font is not installed — silent
  substitution is banned (PALS's Law applied to fonts: an unverified
  measurement is a defect).
- **`fg-font` is a real console command**: implementation moved in-package
  (`frameforge.fontpack`), registered under `[project.scripts]` — resolves
  after install (this tree stays a virtual project, where the
  `tooling/fg_font.py` launcher and `make font-*` targets keep working).
  `--list` resolvable families · `--check DOC` determinism gate · `--pack
  DOC --out P.fp` portable font pack (exact TTFs + sha256 manifest).
- **`fg-font --pack --fetch` — a Google Fonts proxy**: families the authoring
  host lacks are provisioned from the open `google/fonts` corpus and stamped
  `source: "google-fonts:<slug>"` in the manifest, so a reproducible pack can be
  built from a thin machine (no font-rich image needed) and `--check --fetch`
  becomes self-healing.
- **`render_chromium.py --font-pack P.fp`** consumes a pack: fontconfig is
  scoped to the pack (real metrics forced) before Chromium launches, so the
  layout metric and the browser resolve the identical faces — produce →
  consume → render in one flag.
- Justified flow lines no longer get cavernous letterspacing when a line is
  lone or underfull (follow-up fix to the Knuth–Plass batch below).

## Unreleased — v0.1 deck-corpus conversion path (2026-07-03, issue #33)

`tooling/codemod.py --from-v01` lifts both v0.1 envelope forms to v2 —
scene-form (`scene:`/`semantic:`/`visual:` → one page carrying the semantic
block and rendering contract) and deck-form (`deck:`/`slides:` → defs +
one page per slide) — then the standard HEAD rules finish (P3 stroke split,
`stroke_styles` Style projection). The lift also fixes the two silent
semantic traps: v0.1 text-style keys (`font`/`size`/`weight`/`v_align`)
and stroke bundles validate in v2 as unrelated CSS props and must be
renamed, not carried. Unknown top-level keys ride in `meta`. Conversion
proof per the issue's own AC: the genai-ecosystem production diagram —
committed v0.1 source (`tests/data/v01/`) → fixture
`genai-ecosystem.fg.yaml` (corpus 31→32, 0 errors 0 warnings), rendered
98.8 % pixel-identical to the v0.1 reference (RMSE 14.7/255; one label
wrap point). 10 red-first tests (`tests/test_codemod_v01.py`); recipe at
`docs/migration-v01.md`; remaining decks tracked on #33 as on-demand.

## Unreleased — content library: themes, symbol packs, generators (2026-07-03, issue #32)

`frameforge.library` — the predecessor project's content library absorbed
as committed v2 data (§13 bounded context). 7 consulting token packs
(`bain`/`bcg`/`deloitte`/`ey`/`kpmg`/`mckinsey`/`pwc`) translated to
`defs.tokens` fragments; 4 symbol packs (`covers`, `sections`, `shared`,
`hex` — 13 symbols) lowered through `sdk.expand`; the two data-driven
generators (`honeycomb_capability_map`, `module_hub_radial`) ported with
their geometry and committed example data. Translation notes: v0.1 style
field renames (`font`→`font_family` lists, `size`/`weight`→`font_*`,
`v_align`→`vertical_align`), P3 stroke split with Style-bag names
(`stroke`/`stroke_width`/`stroke_dasharray`), `ellipse` → center/rx/ry;
generators drop v0.1's `hash()`-derived color tokens (nondeterministic)
for literal pass-through, auto-grow the honeycomb canvas instead of
clipping, and paint the hub detail block above the node layer. Gates:
`tests/test_library.py` (7 theme render probes, symbol expansion, both
generators reproduce their examples, zero uncontained text everywhere);
fixture `library-honeycomb.fg.yaml` (corpus 30→31, 0 errors 0 warnings);
runnable `static/examples/library_showcase.py`. Docs: `docs/library.md`.

## Unreleased — backend-neutral flow layout · Knuth–Plass + hyphenation (2026-07-02)

Flow-mode prose gets a single backend-neutral layout engine
(`frameforge.rendering.domain.services.flow_layout`); see
[ADR-0003](docs/adr-0003-backend-neutral-flow-layout.md). *Own the breaks, delegate
the spacing.*

- **Line breaking** is Knuth–Plass total-fit (1981); **hyphenation** is Liang
  patterns via `pyphen` (new runtime dependency) — replacing greedy,
  estimate-based, left-aligned wrapping that produced rivers and lopsided margins.
- **Column geometry** resolves from the page master (explicit region → margin →
  the Johnston canon, **mirrored recto/verso**) instead of a hard-coded symmetric
  `margin = 56`; the flowed body finally honours authored geometry and mirrors the
  way the running header already did.
- Each line is emitted as **one text element**, justified to its column via SVG
  `textLength` — **flush on browser/PDF, tight hyphenated ragged on the cairosvg
  proxy** (which ignores it). First-line indent + no inter-paragraph gap.
- **Page mode too.** `render_text` (page-mode `wrap:true` boxes) also routes
  `align:"justify"` through the engine — it previously mapped justify → the
  `start` anchor and could not justify at all. Justification now exists
  document-wide (flow + page mode), including **span-aware** justification:
  inline bold/italic survive a justified wrapped block (runs are re-sliced onto
  each line by char offset).
- **Render change (golden re-pin)**: the four flow fixtures + one page-mode deck
  (`amazon-proxy-2026`, which uses justified prose) re-pinned; all other decks
  byte-unchanged.
- **Adversarial multi-agent review** fixed six confirmed defects in the new code:
  justify+`shrink_to_fit` over-shrink; the justification params crashing the TikZ
  backend; `content_box` not coercing `Length` margins, not clamping non-positive
  area, and not mirroring an asymmetric master margin; recto/verso parity using a
  section-local instead of document-global page number; and a single unbreakable
  token (a URL) dropping the whole paragraph to greedy.
- *Limit:* tight **flush** justification needs a **pinned body font** (layout
  metric = render font); unpinned, flush over-stretches (uniformly airy, not
  rivers) — tight ragged is the safe default.

## Unreleased — pattern compose: filled patterns become pages (2026-07-02, issue #29)

`frameforge.patterns.compose(pattern_id, fill)` bridges the #28 catalog to
rendered output: payload validated through the fill contract first (layout
never runs on unvalidated content), zone boxes computed deterministically
from the anchor vocabulary (column bands / quadrant grids / mixed BMC
columns; regions and relative placements stack in declaration order as a
documented approximation), enterprise-layout treatments applied (card
fill/stroke/corner, accent bars, label slots with slot typography), and
content emitted per content_type as plain core objects — nothing new enters
the schema, and the returned document is pre-validated. Acceptance gate as a
test: all 17 sidecared example fills compose, validate, and render with zero
uncontained text; SWOT/BMC/Diagnostic verified against rendered pixels.
Sample: `static/examples/pattern_compose_deck.py`. 6 red-first tests.

## Unreleased — pattern catalog + fill contract absorbed as data (2026-07-02, issue #28)

New bounded context `frameforge.patterns`: the predecessor's 375-pattern
slide-template catalog and 17 fill sidecars land as committed data with a
strict Pydantic contract — controlled vocabularies for zone size / placement /
content_type, `load_fill` deriving a typed `{role: content}` payload model per
pattern (sidecar overrides enforced: the BMC's object items reject plain
strings), and every committed `example_fill` round-tripped by the test gate.
The catalog count is LOCKED at 375 — truncation is a failing test, not a
smaller number. Rendering a filled pattern into v2 pages is the #29 bridge,
deliberately not part of this change. Docs: `docs/patterns-fills.md` (adapted
from the predecessor's AGENTS.md / AUTHORING-FILLS.md guidance). 11 red-first
tests.
## Unreleased — from-markdown: whole documents in, flow documents out (2026-07-02, issue #31)

`sdk.from_markdown(text)` converts a CommonMark/GFM-subset document into a
validated `mode: flow` page — pagination, text fitting and list/table layout
come from the flow engine, and inline forms reuse the existing `md()`
lowering (one inline parser, not two). Hand-rolled line parser, no new
dependency. Covered: headings, paragraphs, lists (model has no nested list —
sub-items fold into the parent as marked continuation lines), GFM tables,
fenced code, blockquotes (`block` with `role: blockquote`), image paragraphs,
thematic breaks → page breaks, YAML front-matter; the ```frameforge pattern
directive degrades to a structured warning until the fill/render bridge
(#29). Output is schema-validated before it is returned (PALS). The CLI
front door accepts `.md` inputs directly and writes the intermediate
`.fg.yaml` next to the render output. 11 red-first tests.
## Unreleased — render front door works PYTHONPATH-free (2026-07-02, issue #35)

Three src-layout refactor casualties in the CLI path, fixed at root:

- `frameforge.sdk.model` falls back to deriving `<repo>/docs` from its own
  location when `models` is not importable (callers with PYTHONPATH win; the
  fallback only appends) — the `ModuleNotFoundError: models` crash is gone
- `frameforge.cli` derives ROOT for the src layout, so default output goes to
  `<repo>/out/render-cli`, not `src/out/`
- new `tooling/frameforge_render.py` launcher: the working front door for the
  virtual project (`uv run python tooling/frameforge_render.py doc --to svg`),
  self-bootstrapping, any CWD, no PYTHONPATH; delegates to `frameforge.cli`.
  The `[project.scripts]` entry stays inert by the §2 packaging decision (the
  session's earlier "working" console script was a stale pre-refactor venv
  artifact). The docker entrypoint's `frameforge-render` verb now maps to the
  module form (the image sets PYTHONPATH)
- pyproject/AGENTS/codebase-standards §2 advice updated; 4 red-first tests

## Unreleased — design-canon SDK modules (2026-07-02)

Two pure-helper modules codify working design rules for document authors
(human or agent), sourced from Chevreul (1839) and Johnston (1906); no schema
change. Surfaced in the SDK guide/API snapshots, the capability manifest, and
the MCP guide's module catalog.

- `frameforge.sdk.chevreul` — the 12-station painter's wheel + `complement`,
  Chevreul tone scales, the six harmonies, WCAG 2.1 `relative_luminance` /
  `contrast_ratio` (the numeric primitives for text-on-ground legibility and
  the #44 diagnostics work), `grey_document` (the tone audit), and
  `closed_palette` with duties + the 62/30/8 area guide emitting a
  `defs.tokens.colors` fragment.
- `frameforge.sdk.canon` — `modular_scale`, Johnston's margin canon
  (`johnston_margins` / recto-verso `content_box`), the 45–75 measure band,
  `caps_tracking`.
- **Canonical fixtures** `tests/fixtures/chevreul-harmonies.fg.yaml` and
  `canon-typography.fg.yaml` — generated from the modules' own output, so a
  regression in either module shows up as a fixture diff.
- **Renderer bugfix (render change)**: `reading_order` no longer reorders SVG
  emission. The old path hoisted listed objects to the *front* of the paint
  stack, so any unlisted background painted over every listed text (found by
  rasterizing the new fixtures). Paint order is now always layer/z/document
  order; the authored order rides on the page group as `data-reading-order`
  for a future tagged export. Pages using `reading_order` with overlapping
  content render differently (correctly) from 2.3.x snapshots; the b1 golden
  corpus is unaffected (no `reading_order` usage).

## Unreleased — per-object truncation diagnostics (2026-07-02, issue #44)

Silent content loss is over: the text-fit containment now NAMES every text
object that materially loses content (id, page, lines kept/dropped, the head
of the dropped text, and whether the clip was explicitly authored).

- renderer: `diagnostics["truncations"]` records material loss only (dropped
  lines; glyph runs cut beyond rounding tolerance; >½ line clipped) — a
  sub-pixel descender trim keeps the clip-path and the aggregate count but is
  not content loss
- `render_fixtures --check-overflow` prints the named listing (capped at 20 in
  default runs); new `--strict-content` fails on any SILENT loss
- MCP render results: records ride `diagnostics.truncations` (and
  `diagnostics.json`); the render warning quotes the first silent ids
- `validate.py --text-fit` (opt-in): advisory `text-truncated` WARN per object
- spec §3.7 gains the diagnosability sentence; `docs/error-codes.md` documents
  the code
- **known state**: the curated fixture corpus currently carries 211 silent
  material losses, now visible in every overflow run — remediation
  (fix boxes vs acknowledge explicitly) is operator-directed follow-up, which
  is why `--strict-content` is not yet wired into `make check`

## Unreleased — dockerized MCP for foreign codebases (2026-07-02)

The container contract now lets any codebase fully interact with the SDK and
MCP surface (2026-07-02 audit findings: stale image, invisible host paths,
ephemeral SDK clients). Gated by `tests/test_docker_contract.py` and
`tests/test_mcp_edit_roots.py`.

- **Edit roots may leave the repo** (behavior change): explicitly configured
  absolute `FRAMEFORGE_MCP_EDIT_ROOTS` entries are honored literally — the
  image sets `/work/clients:/app/static/examples`, so `write_sdk_client` with
  a **bare filename** creates on the persistent volume and survives `--rm`.
  Bare names are searched across roots (a miss is now `FileNotFoundError`,
  not a confinement error); relative paths *with* directories keep the strict
  repo-relative rejection. Out-of-repo paths are reported absolute.
- **Foreign-codebase wiring** (`docker/mcp.docker.json`): the consuming
  project mounts read-only at `/workspace` (tool calls reference
  `/workspace/<path>`), with `FRAMEFORGE_MCP_INPUT_ROOTS=/workspace:/work:/app`
  confining propose inputs.
- **Freshness is detectable**: a `version` entrypoint verb (package +
  `HEAD_VERSION` + build stamp), an OCI version label wired by
  `make docker-build`, and `PYTHONPATH=/app/src:/app/docs` fixing the
  post-refactor in-image imports.
- **Installable consumption skill**: `skills/frameforge-mcp-docker/SKILL.md`.

## Unreleased — src-layout folder refactor (2026-07-02, complete)

Repository reorganisation; rendered output verified byte-identical (the golden
lock's 87 page hashes are unchanged — only its fixture-path keys re-rooted).
Path mapping (older CHANGELOG entries below keep their original paths — read
them through this table):

| Old | New |
|---|---|
| `frameforge/` | `src/frameforge/` |
| `models/`, `schema/`, `grammar/`, `spec/` | `docs/models/`, `docs/schema/`, `docs/grammar/`, `docs/spec/` |
| `fixtures/` | `tests/fixtures/` |
| `examples/` | `static/examples/` |
| `frameforge_to_html.py`, root reports (`FIXTURE-STATUS.md`, `codebase-standards.md`, `request.md`, `architecture-map.*`) | `tooling/`, `docs/` |
| `brand/`, `demo/`, `recipe/`, `POC-*.md` | retired from the tracked tree (regenerate brand assets via `static/examples/frameforge_logo.py`) |

Completion notes (refactor finished 2026-07-02):

- Every path reference rewired: `conftest.py` + per-file test/tooling
  bootstraps (`src/` for the package, `docs/` for the `models` namespace),
  package-internal repo-root derivations (`parents[3]`), MCP subprocess
  `PYTHONPATH`, MCP editable-client roots (`static/examples`), Makefile
  (`FIXTURES_YAML`, schema paths, `PYTHONPATH` for `-m` targets), CI
  version probe, mkdocs (`exclude_docs` for the in-`docs/` sources),
  viewer dev scripts, `.gitignore`, `.mcp.json`.
- **Gates:** `make check` is 12 gates and green. `brand-check` and
  `brand-logo-check` were retired with written justification
  (`docs/codebase-standards.md` §3): brand assets are non-core and stay out
  of the tree by operator direction, so their comparison inputs are no
  longer tracked. The logo generator remains
  (`static/examples/frameforge_logo.py`, now writing to `_tmp/brand/`).
- **Golden determinism fix:** golden renders now pin
  `FRAMEFORGE_MATH_SVG=fallback` (scoped, restored) so lock hashes no longer
  depend on whether the optional node + `viewer/node_modules` MathJax
  toolchain resolves on the machine running the gate.
- mkdocs strict build made meaningful again: repo-file deep links from site
  pages are validated by `docs-linkcheck` (every tracked Markdown file), so
  mkdocs' own not-found warning is downgraded to info.
(Refactor completion generated by Claude Fable 5 via Claude Code.)

## 2.3.0 — full improvement pass, batches A–F + integration (2026-07-01)

One coordinated pass over the whole tree, executed as six parallel batches.
(Generated by Claude Fable 5 via Claude Code.) One line per batch:

- **A — MCP tool surface:** error-envelope consistency, capability/font
  discovery, session ergonomics, and richer tool parameters.
- **B — core model:** typed reuse, schema field descriptions, referential
  integrity in the validator, and tighter value types.
- **C — rendering:** paint/gradient fidelity in the SVG backend, metrics and
  per-object render feedback, export-lane work.
- **D — SDK authoring:** flow/story builders, icon/bullet_list/dimension
  builders, masters/targets/spans ergonomics, target-adjustment validation.
- **E — docs/manifest/hygiene:** generated capability manifest
  (`docs/capability-manifest.json`, ADR-0002 tracking) + error-code reference +
  examples cookbook, `AGENTS.md`, root `conftest.py`, README/CHANGELOG/nav
  refresh, brand-logo regeneration.
- **F — vision/region toolkit:** region-analysis consolidation from root
  scripts into the package, vectorizer routing, SVG round-trip coverage.

## 2.2.0 — MCP measurement layer, coach, region toolkit, Docker runtime (2026-06-25 → 2026-07-01)

Additive `frameforge/mcp/`, `frameforge/vision/`, `frameforge/coach/`, SDK, and
runtime changes; no model or schema change. Retro-documents the feature commits
between 2026-06-25 and 2026-07-01 that previously had no CHANGELOG entry.
(Entry generated by Claude Fable 5 via Claude Code.)

**Coordinate-aware measurement layer (raster → precise vectors), the headline:**
- New MCP tools `measure_image` (grid + rulers + coordinate system + regions +
  landmarks + zoom crops), `mark_points`, `overlay_images`, `workspace` (a
  stateful pin board: pin/nudge/move/snap/transform/pan/zoom/checkpoint+revert,
  persisted per session as `workspace.json`), `construct_vectors`,
  `score_reconstruction` (numeric edge-match convergence: `on_edge_frac` /
  `mean_dist`), and `map_coordinates` (homography / 2D↔3D / warp rectification)
  — commits `091c64b`, `9528faa`, `7e1e8f8`, `77b4a0b`, `a8e04b0`.
- `vectorize_image` auto-trace: `region` (k-means colour → polygons), `outline`
  (edges → polylines), `trace` (potrace Bézier, `d4337b2`), and `layers`
  (AA-aware flat-logo tracer, `9528faa`).
- `compare_images` gains real NCC/RMSE/MAE metrics + zoomed diff panels.

**Image/SVG → draft lane:**
- `propose_from_svg` — ingest an existing SVG (with optional region grade) and
  round-trip it through render (`9f65e8e`, exported at `2e6f6d1`); SVG import
  resolves `url()` gradients and carries `data-*` into `meta` (`792fe17`).

**SDK:**
- Region toolkit: `select_in` / `place_region` / `region_grade` /
  `extract_objects` / `object_bbox` / `gradient_map` (`29f8f71`).

**Coach (`frameforge.coach`):**
- Vector Construction Coach package: style-grammar, layer-order rules,
  silhouette gate (+ MCP flag), SVG ingest/clean, figure-proportion helpers
  (`bc8c3b8`, `a5a39d1`, `991da7e`, `24bde8b`).

**Runtime:**
- Font-rich Docker SDK/MCP runtime image (`Dockerfile` + `docker/`,
  `make docker-*` targets) for font-faithful raster verification (`c25fe38`).

## 2.2.0 — rendering boundary cleanup + MCP render hardening (2026-06-24)

Additive refactor + MCP changes; no model, schema, or core-renderer behaviour change
(golden lock unchanged). (Generated by Claude Opus 4.8 via Claude Code.)

**Rendering boundary (the inverted dependency, tension #1):**
- `normalize_doc` + its legacy-`use`/deck helpers moved verbatim from
  `tooling/render_fixtures.py` to `frameforge/rendering/application/normalize.py`;
  `tooling` re-exports `normalize_doc` for its CLI. With the `Renderer` already relocated
  to `frameforge/rendering/application/renderer.py`, `frameforge/sdk/conform.py` and
  `rendering/infrastructure/latex/document.py` now import from the package, so
  **`frameforge/` no longer imports up into `tooling/`.** `tests/test_package_boundary.py`
  pins it; `make package-check` drops from 4 blockers to 3 (the rest are the deliberate
  virtual-project decisions, §2).

**MCP render hardening:**
- `conform.render_pages_with_stats()` returns page SVGs + the renderer's text-fit
  telemetry; `render_page_svgs()` delegates to it. The MCP render result now carries a
  `text_fit` block and, when text was **clipped** (truncated to its box), an advisory
  `render_warning` — previously that truncation was invisible (`ok:true`, no signal).
- `_render_size_guard` refuses an obviously-oversized document before the in-process
  render thread starts (generous, env-overridable page/object caps), bounding the work
  the un-killable daemon thread can do.
- `FRAMEFORGE_GUIDE` now names the `figure` import lane and `text_style()`; a new test
  pins that the guide names the SDK's headline capabilities so it can't silently drift.

## 2.2.0 — SDK `text_style()` + package-readiness check (2026-06-24)

Additive SDK and tooling changes; no model, schema, or core-renderer change.
(Generated by Claude Opus 4.8 via Claude Code.)

**SDK ergonomics:**
- New `frameforge.sdk.text_style()` constructor — names the ~12 text-relevant fields
  of the ~100-field `Style` bag under ergonomic kwargs and emits the *canonical* CSS
  field for each (`size`→`font_size`, `align`→`text_align`, `italic`→`font_style`),
  mirroring `stroke()`. Splats onto a text primitive or feeds `define_text_style()` /
  `theme()`. Re-exported from `frameforge.sdk` and documented in `docs/sdk-api.md`.

**Tooling:**
- New `tooling/check_package_readiness.py` + `make package-check` — asserts whether the
  tree is ready to emit (build/publish) a package, split into hard *blockers* (a wheel
  would fail to build or import-break) and advisory *gaps* (the §16 `[Target]` ledger).
  Advisory only — deliberately **not** part of `make check`. Verdict today: **NOT READY**
  (FrameForge is a virtual project by design, `[tool.uv] package = false`) — 4 blockers,
  including `frameforge/` importing the top-level `tooling` package, which would not ship
  in a `frameforge` wheel.

**Analysis assets:**
- `architecture-map.svg` (companion to `conceptual-analysis.md`) is now *authored through
  the FrameForge SDK* and rendered by the project's own SVG proxy, replacing the
  hand-written SVG; `examples/architecture_map.py` is the reproducible source.

## 2.2.0 — MCP feedback loop: close the visual-verification gap + hardening

The MCP adapter advertised "rendered artifacts for visual feedback," but a vision
model never actually received a viewable image: SVG was emitted as an `image/svg+xml`
content block (not a vision-decodable media type), PNG rasterization defaulted **off**,
and when it was on but the browser backend was absent it failed **silently**. The loop
was effectively blind. This release closes that gap and hardens the adapter. No model,
schema, or core-renderer change — `frameforge/mcp/` and `frameforge/live/` only.
(Generated by Claude Opus 4.8 via Claude Code.)

**Visual verification (the headline):**
- `mcp_content_blocks` now ships **only raster mimes** (`png`/`jpeg`/`gif`/`webp`) as
  image blocks; SVG stays a resource link / text artifact.
- Render tools default to `raster_png=True`, and `.mcp.json` launches with the
  `vision` + `browser` groups so the advertised surface is functional out of the box.
- When raster is unavailable the result carries an explicit **`render_warning`**
  (naming the missing backend + the `playwright install chromium` fix) instead of a
  silent empty render — the loop tells you it could not be visually verified.

**Correctness & robustness:**
- Rendering is wrapped in a structured guard: a renderer crash returns
  `ok:false` + `error` (validation still reported) rather than a raw traceback, and a
  soft **render timeout** (`FRAMEFORGE_MCP_RENDER_TIMEOUT`, default 30s) bounds response
  latency on pathological documents.
- `propose_from_image` / `propose_from_document` degrade gracefully when the `vision`
  group is absent (friendly `ok:false`, not `ImportError`), and honor an **opt-in**
  `FRAMEFORGE_MCP_INPUT_ROOTS` confinement for hardened deployments.
- `max_pages=0` now explicitly means **all pages** (documented), not "none".
- The code-execution subprocess **strips likely-secret env vars** (`*KEY*`, `*TOKEN*`,
  `*SECRET*`, …) unless `FRAMEFORGE_MCP_KEEP_ENV` is set.
- The `run_sdk_client` fallback that locates a client's output YAML now diffs by
  **content hash**, not mtime, so a fixture merely `touch`-ed by another process is no
  longer mistaken for this run's output.
- The structured JSONL log **rotates** past a size ceiling and **clamps** oversized
  instruction/response strings.

**Ergonomics:** new `list_sessions` / `cleanup_sessions` tools to enumerate and prune
per-session scratch directories (cleanup is a no-op without an explicit selector).

**Verification:** `tests/test_mcp_server.py` gains coverage for SVG-never-an-image-block,
PNG-is, `render_warning` on missing backend, structured render-failure, `max_pages=0`,
env scrubbing, content-hash fallback, log truncation, opt-in input confinement,
missing-vision-group degradation, and session list/cleanup.

---

## 2.2.0 — adopt the authoritative style module (gap #1, for real)

A later batch supplied the two artifacts that were missing when 2.1.0 was cut: the
**authoritative CSS style module** (`frameforge-v2-style.ebnf`) and the **base spec**
(`frameforge-v2-spec.md`). 2.1.0 had *drafted* the style module by harvesting the
renderer; this release **replaces that draft with the real module**, which is richer
and differs in specifics. The architecture did not move — only the styling subsystem.

**What moved (style subsystem only):**
- **`Style` is the authoritative ~80-property bag** (text / box / background / paint /
  effect / transform groups) with **`class`** (named-style composition) and a **`css`**
  raw-CSS escape. New surface now accepted: `box_shadow`, `filter`, `backdrop_filter`,
  `mix_blend_mode`, `clip_path`, `mask`, multi-layer `background`, typed
  `transform`/`FilterFn`, `hyphens`, `white_space`, `word_break`, `writing_mode`,
  `font_stretch`/`font_variant_*`/`font_feature_settings`, `vertical_align`, etc.
- **`TextStyle` and `StrokeStyle` are now projections of `Style`** (`TextStyle =
  StrokeStyle = Style`). `tokens.stroke_styles` entries are Styles using **CSS-named**
  `stroke_width`/`stroke_dasharray`/… (not the old `{width,dash}` bundle).
- **`fill`/`stroke` are `Paint`** (`= none | currentColor | Color | Image`, where
  `Image` covers gradients/patterns/url). `Fill = Paint`.
- **Gradient stops canonicalise on `position`** (was `offset` in 2.1.0 — flipped to
  match the module + the fixtures; `conic`/`repeating`/`from`/`at`/`shape` added;
  `angle`/`from` accept an `Angle` like `"135deg"`).
- **Explicit cascade (spec §8.4):** theme → `style.class` → inline `style` → `css` →
  per-object convenience fields (`fill`/`stroke`/`radius`/`color`), which win on conflict.
- Legacy shorthand (`font`/`size`/`weight`/`italic`/`align`/`v_align`/`radius`/`wrap`) is
  **accepted as sugar** for the canonical CSS names, so existing styles keep validating.
- **Text-fit reconciliation (P2 Part C):** the delivered CSS module mirrored
  `line_clamp`/`text_overflow`/`max_lines` but dropped the two non-CSS FrameForge
  autofit extensions. HEAD restores them on `Style`: `overflow` also accepts
  **`shrink_to_fit`** (beyond the CSS box values), and **`min_font_size`** (the autofit
  floor) is added back. These are the only HEAD additions to the authoritative module;
  without them the deck fixtures (which use `shrink_to_fit`) would not validate.
- Minor flow gaps closed from the authoritative fixtures: `toc.of`, `figure.align`,
  `block.role`/`block.stroke_style`, `bibliography.title`, image
  `preserve_aspect_ratio` (SVG string) and `clip` (shorthand).

**Migration:** additive for authors (richer styling; existing docs validate once the
model matches the module). The codemod gained: gradient `offset → position`, inline
stroke geometry → **CSS-named** `stroke_width`/`stroke_dasharray` in a `stroke_style`
Style, and `tokens.stroke_styles` bundle rewrite. Run:
```bash
python3 tooling/codemod.py your-doc.fg.json --in-place --bump
```

**Verification (asserted by `tests/test_head.py`, 13/13 green):** all **eight
authoritative fixtures validate at 2.2.0** — directly for those without legacy strokes
(`ieee`, `neutron-stars`, `spectral-methods`, `mckinsey-7s`), and after the codemod for
those that carry legacy inline strokes (`amazon-proxy`, `chroma-styling-showcase`,
`wireframing-guide`, `docusign-deck-v2` — **544 strokes migrated**). The schema is
generated-in-sync, and the P3 inline-geometry `stroke` is still rejected.

**Grammar ⇄ models is now gated.** A new `grammar-check` gate
(`tooling/check_grammar_sync.py`, wired into `make check` and CI) introspects the models
and diffs the EBNF, failing on **core-profile** drift — a mismatched object/flow `type`
discriminator or a divergent enum. The out-of-profile superset (charts, the UML zoo,
connectors) is reported as a non-blocking warning (`--strict` demands full parity). It
immediately caught and fixed two real grammar omissions against the models: `Units` was
missing `cm`, and `ImageObject` lacked the `alt`/`actual_text` accessibility fields.

**Two source contradictions adjudicated** (flagged, not hidden): the base core grammar's
`GradientStop` uses `offset` while the authoritative style module uses `position` — the
module wins; and the base grammar still carried `Stroke = string | StrokeStyle` while
base-spec §3.5 says paint-only — already resolved (Stroke = Paint).

### SDK — topology, perspective, fields, lattices & manifolds (additive)

Five solver modules join the Python SDK, each lowering to a single core-model `group`
(so the geometric audit, which does not recurse into groups, stays silent) and each
fully deterministic:

- **`frameforge.sdk.topology`** — `Graph` node-link networks with `circular_layout`,
  `radial_layout`, `layered_layout` (DAG), `grid_layout`, and a seeded
  `spring_layout` (Fruchterman–Reingold). `render()` emits fitted edges, arrowheads
  and labels.
- **`frameforge.sdk.geometry.Camera`** — a `look_at` + field-of-view perspective camera
  composing a view/projection `Mat4` (plus `Mat4.look_at`/`perspective_fov`/`rotate_*`
  and `Camera.orbit`). `Scene3D.render()` now accepts a `Camera` and sorts faces by
  perspective-divided depth.
- **`frameforge.sdk.draw.Material` + Scene3D lighting** — translucent material/style
  fields (`opacity`, blend mode, filters) stay model-native, while optional
  `shading="lambert"` or `"gouraud"` bakes pure-Python light intensity into each
  face's emitted 2D fill.
- **`frameforge.sdk.fields`** — `VectorField` (arrow grids) and `ScalarField`
  (`heatmap` + marching-squares `contours`).
- **`frameforge.sdk.lattices`** — `lattice(kind, …)` for 2D (square/triangular/
  honeycomb) and 3D (cubic/bcc/fcc) crystals with nearest-neighbour bonds, rendered
  through the topology engine.
- **`frameforge.sdk.manifold`** — perspective-ready parametric `Scene3D` surfaces:
  `sphere`, `torus`, `mobius`, `klein_bottle`, `saddle`, and the `wave` interference
  heightfield.
- **`tooling/render_chromium.py`** — optional Headless-Chromium raster path: reuse the
  SVG proxy output, then let browser-native rendering produce PNGs for CSS filters,
  blend/backdrop modes, masks and SVG filter fidelity (`uv sync --group browser`;
  `uv run playwright install chromium`).
- **Filter shader-lite primitives** — typed `FilterFn` now covers SVG procedural and
  lighting primitives (`turbulence`, `displacement_map`, `diffuse_lighting`,
  `specular_lighting`) with a new `filter-lighting.fg.yaml` fixture rendered by the
  Chromium path.

Two demo fixtures cover the surface: `topology-perspective.fg.yaml` (six layout/camera
panels) and `fields-lattices-manifolds.fg.yaml` (eight field/lattice/manifold panels),
both at 0 errors / 0 warnings and passing `--check-overflow`. The generated SDK API and
guide docs (`tooling/gen_docs.py`) now cover all five modules.

---

## 2.1.0 — fold the patch series (P1–P4) + draft gap #1

> Superseded by 2.2.0's adoption of the authoritative style module, but the rest of the
> 2.1.0 record stands.


> Honesty note (unchanged from the bundle's own stance): FrameForge v2 is a
> **proposed, not-yet-conformantly-implemented** format. Everything here is a
> design target to verify, not a shipped standard. What *is* verifiable in this
> release: the schema is generated from the Pydantic models, and the validator +
> codemod run on the real fixtures (see "Verification" below).

---

## What HEAD is

A single, internally-consistent cut of FrameForge v2 that folds the whole patch
series (P1–P4) and resolves the open gaps the complement identified:

- **Models are the source of truth** (`models/frameforge.py`). The **JSON Schema is
  generated** from them (`schema/build_schema.py`), so the two cannot drift.
- The **grammar** (`grammar/frameforge-v2.ebnf`) is one consolidated file =
  base + P1 + P2 + P3 + P4 + the inlined CSS style module. The earlier
  `frameforge-v2-revised.ebnf` (base+P1+P2) and the stray "v2.1" `frameforge-v2.ebnf`
  are **superseded**.
- The **validator** (`tooling/validate.py`) enforces the rules a schema can't
  express; the **codemod** (`tooling/codemod.py`) migrates documents to HEAD.

### Versioning rationale (read this)

The P3 stroke collapse is technically a **breaking** change. Strict semver would
make that a major bump. Because v2 was never released or conformantly implemented,
HEAD folds it into the v2 line as **2.1.0** with a mechanical codemod, rather than
inventing a "3.0.0". This is a deliberate, documented call — not an oversight. If
you have external consumers pinned to a pre-HEAD v2, treat 2.1.0 as breaking for
them and run the codemod.

---

## Breaking changes

### 1. Stroke has a single normative form (P3) — **BREAKING**

- `stroke` is now **paint only** (a `Color`). Stroke **geometry**
  (`width`/`dash`/`linecap`/`linejoin`/`arrow_*`/`opacity`) lives **only** in
  `stroke_style` (a token **or** an inline `StrokeStyle`).
- The inline `stroke: { width, dash, … }` form is **removed**.
- A `stroke_style` bundle's `color` is a default, overridden by an object's `stroke`.

**Migration (automated):**
```bash
python3 tooling/codemod.py your-doc.fg.yaml --in-place
```
The codemod splits each legacy inline `stroke`: `color → stroke` (paint),
geometry → `stroke_style` (inline). A `stroke` that was already a colour string is
unchanged. On the bundled fixtures this rewrote **17 inline strokes** (NYT ×5,
Wordle ×12); afterwards all five core fixtures validate with **0 errors**.

---

## Additive / non-breaking changes

| Change | Patch | Notes |
|---|---|---|
| Nested coordinates + layout box-model (`Layout.align`/`row_gap`/`column_gap`); group opacity composites the subtree as one unit | P1 | §3.6 |
| Text fit/truncation (`overflow:shrink_to_fit`, `min_font_size`, `line_clamp`, `text_overflow`) | P1 | §3.7 |
| `defs.assets` (content-addressed, hashed media); `src` may name an asset key | P2 | §3.5/§9.6 |
| Screen presets `phone`/`tablet`/`web` | P2 | §4 |
| `FlowSection.media: paged \| continuous` | P2 | §3.9 |
| `Pattern` fills (`hatch`/`cross_hatch`/`dots`/`grid`), region-clipped | P2 | §3.8 |
| Rich `Caption` (string or inline runs) + `credit` on image/figure/table | P2 | — |
| `grid_span` + sparse auto-placement; absent `layout` ⇒ `free` | P2 | §3.6e |
| `DimensionObject` (composite anchored dimension + measure pass) | P3 | §3.10 |
| Box-less primitives allowed under `free` (defined) | P3 | §3.6f |
| Geometric audit: containment, scoped non-overlap, tabular-box mandate | P3 | §3.3 |
| Content sizing `sizing: {width,height: fixed\|hug\|fill, grow, min, max}` | P4 | §3.6g |
| `fr`/`%` resolution defined (`1fr ≡ fill grow:1`) | P4 | §3.4 |

## Renames & resolutions

- **`size` → `sizing`** (P4). The content-sizing key collided with `IconObject.size`;
  it is renamed to `sizing` everywhere. `size` on an `icon` (numeric font size) is
  unchanged. The codemod renames content-sizing `size` objects to `sizing`.
- **gap #1 resolved.** The CSS style module is drafted as `Style` (+ `BorderSide`)
  and **inlined into the grammar**. `Style` supersedes the old `TextStyle` for
  `tokens.text_styles` and backs `tokens.styles`. Property names harvested from the
  reference renderer. The grammar has **no remaining dangling references**.
- **Gradient stops** canonicalise on `offset` (was `position` in the renderer);
  `position` is accepted as a deprecated alias and normalised by the codemod.

## Deprecated (accepted, normalised by the codemod)

- Renderer-shortcut primitives `circle` / `polygon` / `curve`(`bezier`) — normative
  forms are `ellipse` / closed `polyline` / `path`. Run
  `codemod.py --normalize-aliases` to rewrite them.
- Top-level `text_contract` — the normative home is a master/page
  `RenderingContract.text`.

---

## Conformance classes (the §8.5 mechanism)

HEAD defines a **core profile** (what the models validate and the schema covers)
and an **extended set** (grammar-allowed, out of the deep profile). A target
declares which it supports; out-of-profile content is a *warning*, never a silent
failure.

- **Core (REQUIRED):** the document envelope; `defs.tokens` (colors, fonts,
  `text_styles`/`styles` via `Style`, `stroke_styles`, `fill_styles`, `glyph_map`),
  `defs.assets`, `defs.masters`; fixed pages with `rect`/`ellipse`/`line`/`polyline`/
  `path`/`text`/`image`/`icon`/`bullet_list`/`dimension`/`table`/`group`; flow
  sections with the `Flowable` set; the box-model, text-fit, sizing, pattern, and
  stroke rules above.
- **OPTIONAL (declarable unsupported):** `media: continuous`, `Pattern` tiling,
  `shrink_to_fit`, the `dimension` measure pass, rich captions/credit, `grid_span`
  spanning, group-opacity isolation. A target that can't do one emits a diagnostic
  and degrades per the spec, never a blank.
- **Out-of-profile (extended):** the UML object family, `bar_chart`/`line_chart`/
  `legend`, `component`/`use`/`symbol`, `connector`, `ontology`/`semantic`. Accepted
  by the grammar; reported by the validator as `out-of-profile`; not modelled at HEAD.

---

## Verification (what actually runs in this release)

```bash
# 1. schema is generated from the models and in sync
python3 schema/build_schema.py --check          # -> "OK: schema is in sync with the models."

# 2. validate the migrated fixtures (core profile)
python3 tooling/validate.py fixtures/*.fg.yaml  # -> 0 errors (advisory warnings only)

# 3. migrate a legacy document to HEAD
python3 tooling/codemod.py legacy.fg.yaml --in-place
```

**Fixture status after migration (in this repo):**

| Fixture | Errors | Note |
|---|---|---|
| calendar-3day, edst1-flange, myfiles-internal, nyt-mideast-live, wordle-how-to-play | **0** | core profile; advisory warnings only (overlap/tabular/containment/alias) |
| anthropic_claude_deck_improved, esfera_improved | **0** | out-of-profile warnings only |
| coopera_polished, coopera_tables | **2 each** | genuine non-conformance: an `image` carries a `stroke` (images have no stroke in the grammar). Not a tooling gap — fix the source (remove the stroke or use a bordered rect / `Style.border`). |

---

## How the three prior documents relate

- `FrameForge-2.0.0-Specification.md` — the reverse-engineered spec (from the
  renderer). **Provenance**; superseded by `spec/frameforge-v2-spec.md` at HEAD.
- `FrameForge-2.0.0-Specification-Complement.md` — the reconciliation that produced
  these recommendations. **Provenance**; its §8 actions are resolved below.
- This release implements those recommendations.

## Recommendation resolution (from the Complement §8)

| # | Recommendation | Resolution at HEAD |
|---|---|---|
| 1 | Draft/promote the CSS style module (gap #1) | **Done.** `Style` + `BorderSide` drafted (harvested from the renderer) and inlined into the grammar + modelled in Pydantic. |
| 2 | One canonical grammar; discard the stray | **Done.** `grammar/frameforge-v2.ebnf` is the single consolidated grammar; revised + stray superseded. |
| 3 | Generate the schema from Pydantic; extend to P3/P4 types | **Done.** Schema generated from the models (`Dimension`, `AssetDef`, `Caption`, `Sizing`, `Style` all present); `build_schema.py --check` enforces sync. |
| 4 | Fold P3 + P4 into the grammar; run the stroke codemod | **Done.** Grammar carries P3/P4; codemod run on fixtures (17 strokes split). |
| 5 | Rename `size` → `sizing` everywhere | **Done.** Models/schema/grammar use `sizing`; codemod renames legacy `size` objects. |
| 6 | Enforce stroke single-form | **Done.** Models reject inline-geometry `stroke` with an actionable message; validator rule `stroke-single-form`. |
| 7 | Font-pinning precondition + defined shaping tolerance | **Done (validator) / specified (shaping).** `FontDef.hash` added; validator errors on content-sized text using an unpinned font (`unpinned-font`). Shaping model + rounding tolerance specified in the spec §9.6 (stated as a tolerance, not pixel-exact). |
| 8 | Pick an implementation of record or mark features OPTIONAL | **Specified.** Conformance classes above; `RENDERER-PATCH.md` specifies the ReportLab renderer's HEAD changes; the proxy renderer is patched in `tooling/render_fg_doc.py`. |
| 9 | Coopera unconverted regions; validate against ReportLab not proxy | **Tracked.** 61 borderless regions remain intentionally unconverted; the 2 residual coopera errors above are real (image+stroke), surfaced by the validator, to fix at source. |
