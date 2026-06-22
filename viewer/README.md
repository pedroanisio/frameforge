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
├── dev/                      Local build + headless-verification harness.
│   ├── entry.jsx             Mounts <App/> into #root.
│   ├── harness.html          Loads Tailwind (CDN) + bundle.js. Open to view without building.
│   ├── bundle.js             Pre-built IIFE bundle (so harness.html works out of the box).
│   ├── shot.cjs              Playwright script that screenshots representative slides.
│   ├── package.json
│   └── package-lock.json
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
cd dev
npm install
cp ../framegraph-viewer.jsx App.jsx     # entry.jsx imports ./App.jsx
./node_modules/.bin/esbuild entry.jsx \
  --bundle --format=iife --jsx=automatic \
  --loader:.jsx=jsx --outfile=bundle.js
# then open harness.html
```

### Re-run visual verification
```bash
cd dev
npm install
npx playwright install chromium
node shot.cjs          # writes shot_*.png next to the script
```

---

## Using your own documents
The app's **JSON** button loads any FrameGraph v2 document in JSON form. YAML isn't parsed
in-app by design (no YAML parser is bundled) — convert first, e.g.
`python3 -c "import yaml,json,sys; json.dump(yaml.safe_load(open(sys.argv[1])), open(sys.argv[2],'w'))" deck.yml deck.json`.

---

## What the renderer supports
Resolved from `defs.tokens`: colors, fonts, text styles, stroke styles, fill styles.
Objects: `rect`, `ellipse`, `line`, `polyline`, `path`, `text` (incl. `spans`/`field`),
`icon`, `group` (with `row`/`column`/`grid`/`free` layout). Fills: solid, `linear`/`radial`
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
