---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (Claude Code)"
  date: "2026-07-01"
---

# Requesting work from the FrameGraph agent

How to phrase tasks so the AI agent drives the FrameGraph **SDK** (authoring) and
**MCP tools** (render, verify, measure, reconstruct) effectively. You write in plain
language; the agent picks the tools. This guide shows what to say to get there fast,
with example requests and the tool each one triggers.

Back to the [README](README.md). Deep tool reference: ask the agent to *"show the
`framegraph_guide`"* (the model-facing capability prompt) or read
[framegraph/mcp/README.md](framegraph/mcp/README.md).

---

## The mental model (say what you want in these terms)

FrameGraph has one spine: **author → render → verify.**

1. **Author** a document with the Python SDK (or let the agent propose one from an image).
2. **Render** it — the server validates the model and rasterizes to PNG.
3. **Verify** against the *pixels*, never the YAML alone. All CV/LLM output is unverified
   by default (**PALS's Law**) — so always include a bar ("confirm it renders", "match
   the reference").

For turning a **raster into vectors** there is a second loop:

> **measure** (get a coordinate grid) → **pin** anchors in a **workspace** → **nudge/refine**
> over passes → **construct_vectors** → **compare_images** vs the source → repeat.

If you name these outcomes, the agent maps them to the right tools automatically.

---

## Anatomy of a good request

A strong request names five things (skip any the agent can infer):

| Part | Ask yourself | Example phrasing |
|---|---|---|
| **Goal** | What artifact do I want? | "a 16:9 title slide", "an SVG reconstruction of this logo" |
| **Input** | What does it start from? | "from `ref/logo.png`", "edit `examples/deck.py`", "no input" |
| **Output** | What form + where? | "render to PNG", "write the SDK client", "export a PDF" |
| **Constraints** | Any hard rules? | "use IBM Plex Serif", "palette #0E0F11/#E8EAED", "A4 portrait" |
| **Bar** | When is it done? | "verify it renders with no overflow", "≤2px off the reference" |

**Weak:** "make a diagram of the pipeline."
**Strong:** "Author a FrameGraph deck slide (1280×720) diagramming the auth pipeline as
three boxes + arrows, render it, and show me the PNG. Confirm no text overflows."

---

## Request recipes (by capability)

Each recipe is a request template you can copy, an example, and the tool it drives.

### 1. Author a document (SDK)
> *"Author a `<kind>` (`<size>`) that `<content>`; render it and show the PNG."*

- "Author a one-page diagram, 1000×700, with a titled card and a 3-node flow graph;
  render and show it." → agent writes SDK code → `run_sdk_code`.
- "Add a KPI row to `examples/dashboard.py` and re-render." → `write_sdk_client` +
  `run_sdk_client`.

### 2. Render & see an existing doc
> *"Render `<file>` and show me the pages."* → `render_framegraph_yaml` (YAML) or
  `run_sdk_client` (a `.py` client). PNG is attached by default; ask for `--to pdf` to export.

### 3. Draft from an image / PDF / SVG
> *"Propose a FrameGraph draft from `<image|pdf|svg>`, then render it so I can see how close it is."*

- "Draft a document from `mock/screen.png` and show the render." → `propose_from_image`.
- "Ingest `art/icon.svg` as editable FrameGraph objects." → `propose_from_svg`.
- Drafts are **unverified starting points** — say "then refine the largest errors with the SDK."

### 4. Visual QA (reference vs recreation)
> *"Compare `<reference>` against `<candidate>` and show me where they differ."*

- "Compare `ref/poster.png` with the page I just rendered; zoom the logo and the headline."
  → `compare_images` (pass regions to zoom, or a grid). The pixel-match % is a *hint*;
  judge the panels.

### 5. Measure coordinates on an image
> *"Put a grid + rulers + coordinate system on `<image>` and give me the coordinates of `<regions>`."*

- "Measure `ref/chart.png`, origin bottom-left, and box these regions: axes `[0,0.8,1,0.2]`,
  plot `[0.1,0.1,0.8,0.7]`. Zoom the legend." → `measure_image`.
- Ask for the exact numbers: *"return the spatial JSON"* (also saved to `diagnostics.json`).
- Coordinate **frames** you can request: `image px`, coordinate-system units
  (`origin` = `top-left` / `bottom-left` / `center`), `normalized` (0..1), and `viewport px`
  for a zoom crop (its rulers stay in **source** coordinates).

### 6. Mark points
> *"Mark these points on `<image>` and tell me each one's coordinates in every frame."*

- "Mark the eyes at norm [0.4,0.35] and [0.6,0.35], and a point 8px right of landmark A9;
  connect them." → `mark_points` (accepts `norm` / `px` / `cs` / `{landmark,dx,dy}` /
  `viewport_px`).

### 7. Overlay & landmark alignment
> *"Overlay `<overlay>` onto `<base>` aligned on these landmark pairs, and give me the offsets."*

- "Align `recon.png` onto `ref.png` matching corner→corner (3 pairs); show the composite at
  50% and the per-pair offset + residual." → `overlay_images` (fits scale+translation; large
  residuals flag rotation, which it does not model).

### 8. The coordinate workspace — pin & refine (the "mouse")
This is **stateful**: pins persist across calls under a `session_id`, so refine over passes.
Always name the session so the agent reuses it.

> *"Open a workspace on `<image>` (session `<id>`). Pin `<points>`. Then nudge / zoom / refine."*

- "Open a workspace on `ref/logo.png`, session `logo`. Pin the 4 outer corners and the star tip."
  → `workspace action=open` + `action=pin`.
- "In session `logo`, nudge pin P3 left 0.01 and up 0.01, then re-render." → `workspace action=nudge`
  (`unit` = `norm` / `px` / `viewport`; `dx=-0.01, dy=-0.01`).
- "Zoom the viewport 3× on the star tip and keep it centered." → `action=zoom` (fixed aim).
- "Move the whole `outline` group down 5px." → `action=nudge select={group:outline} unit=px dy=5`.
- Pins are image-anchored, so their coordinates hold as you pan/zoom (coordinate continuity).

### 9. Construct vectors from anchors
> *"Draw `<shapes>` from my pins and render the reconstruction over the source size."*

- "From session `logo`, construct a triangle from pins P1,P2,P3 (red stroke, light fill) and a
  closed region from the outline group; render it." → `construct_vectors` (`pins` or explicit
  `points`).
- Shape kinds: `line`, `path`/`trace`, `curve`, `spline`, `triangle`, `polygon`, `closed`,
  `rect`, `ellipse`, `circle`, `star`.
- Close the loop: *"then compare the reconstruction against `ref/logo.png` and tell me the residual."*

### 10. 2D / 3D mapping
> *"Map these coordinates: `<mode>`."*

- Perspective correction: "Fit a homography from these 4 corner pairs and map the rest." →
  `map_coordinates mode=homography`.
- Lift to 3D: "Put these 2D points on the z=0 plane." → `mode=to_3d`.
- Project 3D→2D: "Project these 3D points through a camera at eye [0,0,5]." → `mode=project`.

### 11. Run in the font-rich container
> *"Build and run the tooling in the Docker image so all fonts resolve."*

- "Build the image and list the font families." → `make docker-build`, `make docker-fonts`.
- "Run the MCP server from the container." → `make docker-mcp` (see
  [docker/README.md](docker/README.md)).

---

## A full worked request (reconstruct a logo from a screenshot)

Paste something like this and let the agent run the loop:

> "I want to reconstruct `ref/logo.png` as clean FrameGraph vectors.
> 1. Measure it (grid + rulers, top-left origin) and show me the coordinate overlay.
> 2. Open a workspace (session `logo`) and pin the key corners and curve endpoints.
> 3. Zoom into each corner and nudge the pins until they sit exactly on the artwork.
> 4. Construct the shapes from the pins (outline as a closed region, mark as a triangle).
> 5. Compare the reconstruction against the source and show me the diff.
> 6. Refine the worst-off pins and rebuild until it's within ~2px.
> Verify every step against the rendered PNG."

The agent will chain `measure_image → workspace(open/pin) → workspace(zoom/nudge) →
construct_vectors → compare_images → workspace(nudge) → construct_vectors`, keeping all
pins in the `logo` session, and stop when the compare panels look right.

---

## Phrasing tips that get better results

- **Name a `session_id`** for anything iterative ("session `logo`") so pins/renders are reused.
- **Ask for the numbers**: "return the spatial JSON" or "read `diagnostics.json`" when you need
  exact coordinates, not just the picture.
- **Iterate in small deltas**: "nudge P3 left 0.01 and re-render" beats "make it better".
- **State the origin/units** when they matter: "bottom-left origin", "nudge in px".
- **Set the bar**: "confirm it renders", "no text overflow", "within 2px of the reference".
- **Big jobs**: say "plan first" for M/L/XL tasks; the agent will outline before executing.
- **Reuse work**: "edit the client you wrote" / "compare against the page from session `logo`".

## Anti-patterns (these slow the agent down)

- No source and no spec ("make it nicer") — say what artifact and from what.
- No verification bar — the agent will still verify, but you get better results if you name the target.
- "Trust the draft / skip the render" — drafts and detected landmarks are **unverified** (PALS's Law);
  the agent will render and check anyway. Anchor to exact geometry (pins, structural landmarks A1–A9).
- Changing many pins at once with no reference — pin, look, adjust in passes.
