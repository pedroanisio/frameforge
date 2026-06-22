# FrameGraph v2 Viewer

A React app that renders **FrameGraph v2** documents — a coordinate-space scene-graph DSL
for decks, diagrams, books, and letters. Ships with the *esfera* style-guide deck (14 slides)
embedded as the live demo. The embedded deck, `demo/esfera.json`/`.yml`, and the prebuilt
`dev/bundle.js` are all **FrameGraph 2.2.0** (migrated with the HEAD codemod).

The viewer renders at the document's native canvas coordinates and then fit-scales, so the
whole UI is built to "speak in coordinates": ruler ticks with px labels, registration
brackets, a canvas-size badge, and a live mouse → canvas-coordinate readout.

---

## Contents

```
framegraph-viewer/
├── framegraph-viewer.jsx     The app. Single-file React component, default export.
├── demo/
│   ├── esfera.json           The demo deck the app renders (canonical, what ships embedded).
│   ├── esfera.yml            Same deck as YAML (regenerated from the JSON — see note below).
│   └── (schema)              See "The schema" section; not redistributed in this bundle.
├── package.json              Project manifest (deps + build/start/verify scripts).
├── Dockerfile                Multi-stage: Node builds the bundle, nginx serves it.
├── docker-compose.yml        `docker compose up` -> browse everything at :8088.
├── docker/                   nginx site config + landing page used by the image.
├── dev/                      Local build + headless-verification harness.
│   ├── entry.jsx             Mounts <App/> into #root (imports ../framegraph-viewer.jsx).
│   ├── harness.html          Loads Tailwind (CDN) + bundle.js. Open to view without building.
│   ├── bundle.js             Pre-built IIFE bundle (so harness.html works out of the box).
│   └── shot.cjs              Playwright script that screenshots representative slides.
└── verification/             Headless-Chromium screenshots used to QA the render output.
    ├── shot_slide01.png            cover
    ├── shot_slide05_palette.png    palette (dark bg + color swatches)
    ├── shot_slide06_type.png       typography (serif vs sans)
    ├── shot_slide08_ui.png         product UI cards
    └── shot_slide11_components.png component-guidance table
```

---

## Run it

### Option A — just look at it (no build)
Open `dev/harness.html` in a browser. It pulls Tailwind from the CDN and loads the
pre-built `dev/bundle.js`. (Loading from `file://` works; some browsers are happier if you
serve the folder, e.g. `npx serve dev`.)

### Option B — use it as a Claude Artifact
`framegraph-viewer.jsx` is written to the Artifact runtime's constraints: default export,
Tailwind **core utilities only** (custom colors via inline styles), no browser storage,
`lucide-react` for icons. Drop it into an Artifact and it renders immediately.

### Option C — rebuild the bundle yourself
```bash
npm install            # run once, from this viewer/ folder
npm run build          # bundles dev/entry.jsx -> dev/bundle.js, then open dev/harness.html
```
For a live dev server with rebuild-on-reload:
```bash
npm start              # serves dev/ at http://127.0.0.1:8000/harness.html
```

### Option D — Docker (browse the whole bundle)
Builds the bundle in a Node stage and serves the **entire** `viewer/` tree (the app, the
demo data, and the verification screenshots) from nginx with directory listing on, so you
can navigate everything from one URL.
```bash
docker compose up --build          # then open http://localhost:8088
# pick a different host port if 8088 is taken:
VIEWER_PORT=9000 docker compose up --build
docker compose down                # stop & remove
```
The landing page links to the app (`/dev/harness.html`) and to the browsable
`dev/`, `demo/`, and `verification/` folders. Source/data files (`.jsx`, `.json`, `.yml`,
`.md`) render in-browser instead of downloading.

### Re-run visual verification
```bash
npm install
npx playwright install chromium
npm test              # static fixture/object/style coverage
npm run test:browser # loads every fixture in Chromium and walks expanded pages
npm run test:style   # computed-style smoke assertions
npm run test:layout  # row/grid layout placement smoke assertions
npm run verify         # runs dev/shot.cjs; writes shot_*.png into dev/
npm run test:all     # build + all of the above gates
```

---

## Using your own documents
The app's **Open** button loads FrameGraph v2 documents in JSON, YAML, or YML form.
The fixture coverage tests parse every checked-in fixture, verify page/object/style policy
coverage, and load every document in Chromium:
```bash
npm test
npm run test:browser
```

---

## What the renderer supports
Resolved from `defs.tokens`: colors, fonts, text styles, stroke styles, fill styles.
Page modes: absolute `page` layers and approximate paginated `flow`/story pages with
master canvas regions and running header/footer objects.
Objects: `rect`, `ellipse`, `circle`, `line`, `polyline`, `polygon`, `path`, `text`
(incl. `spans`/`field`), `image`, `bullet_list`, `table`, `icon`, `group` (with
`row`/`column`/`grid`/`free` layout), plus generic boxed/relation fallbacks for semantic fixture
objects. Flow blocks: `heading`, `paragraph`, `list`, `bullet_list`, `table`, `code`,
`math`, `toc`, `figure`, `block`, `bibliography`, `page_break`, and `spacer`.
Fills: solid, `linear`/`radial`
gradients (stops use `position`), and `hatch`/`cross_hatch`/`dots`/`grid` patterns.
**Strokes (FrameGraph 2.2.0): paint comes from `stroke` (a colour/gradient) and geometry from
`stroke_style` — a named `Style` with CSS-named `stroke_width`/`stroke_dasharray`/`stroke_linecap`/
`stroke_linejoin` (legacy `{color,width,dash}` bundles are still accepted). Arrowheads via
`arrow_start`/`arrow_end`. Plus rotation, opacity (object/fill/stroke), z-ordering across layers and
objects, anchor/port references between objects, and `overflow: shrink_to_fit` text
(font-size is binary-searched against measured overflow — this is what the esfera deck's
"fit-safe label styles" rely on).

---

## Note on the demo data (one correction)
On `slide_05_palette`, the **source deck** places each swatch's name label and its hex code
at an identical `y` origin (e.g. `Esfera Red` and `#D71920` both at `[860, 340, …]`),
differing only in box height. Both text styles default to top alignment, so a *faithful*
renderer superimposes them — the labels render garbled.

The fix lives in the **demo data**, not the renderer: the four hex boxes were shifted down
~30px so they stack beneath their names. The renderer itself is deliberately faithful — it
draws exactly what a document specifies and does **no** auto-separation of overlapping
boxes, because overlap is legitimate in other documents (layered text, effects). The
`demo/esfera.json` and `demo/esfera.yml` in this bundle already contain the corrected
positions and match what the app renders.

`demo/esfera.yml` is regenerated from the JSON, so it preserves content but not the original
file's comments or key ordering.

## The schema
The deliverable was built against a `framegraph-v2_schema.json` contract (top level:
`dsl` (const `"FrameGraph"`), `version`, `profile`, `title`, `defs`, `targets`, `pages`,
`meta`; objects discriminated by `type`). That input schema isn't redistributed in this
bundle. The viewer performs structural resolution at runtime rather than hard JSON-Schema
validation, so it isn't required to run.
