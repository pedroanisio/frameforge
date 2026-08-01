/**
 * Gate: structured path `d` must be lowered to a path-data string.
 *
 * `Path.d` is `string | [[cmd, ...numbers], ...]` (schema $defs.Path.d). The
 * viewer passed `o.d` straight to the SVG attribute, so the structured form was
 * stringified by JS array coercion — `[["M",0,21],["L",64,21]]` became
 * `"M,0,21,L,64,21"`, which is not path data. Chromium rejected the attribute
 * ("Expected number") and the shape did not render at all: 68 such errors across
 * the committed fixture corpus, and `npm run test:browser` exited 1 on them.
 *
 * The lowering must match the engine's (renderer.py, `t == "path"`): commands
 * and numbers joined by single spaces, a no-arg segment (Z) emitting just its
 * command with no trailing space, and a plain string `d` passed through.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = {
  dsl: "FrameForge",
  version: "2.2.0",
  title: "Path d smoke",
  pages: [{
    mode: "page",
    id: "p1",
    canvas: { size: [300, 200] },
    rendering: { coordinate_mode: "absolute" },
    layers: [{ id: "l1", objects: [
      // structured form — list of [cmd, ...numbers]
      { type: "path", id: "structured",
        d: [["M", 0, 21], ["L", 64, 21], ["L", 64, 60], ["Z"]], fill: "#0b5ed0" },
      // the same geometry as a string — the reference rendering
      { type: "path", id: "stringform", d: "M 0 21 L 64 21 L 64 60 Z", fill: "#0b5ed0" },
      // curves + arcs carry more coordinates per segment
      { type: "path", id: "curves",
        d: [["M", 10, 10], ["C", 20, 20, 30, 0, 40, 10], ["A", 5, 5, 0, 0, 1, 50, 10], ["Z"]],
        fill: "none", stroke: "#101418" },
      // fractional coordinates must not be mangled
      { type: "path", id: "fractional",
        d: [["M", 2.9849346218877, 0.5], ["L", 12.25, 30.125]], fill: "none", stroke: "#101418" },
    ] }],
  }],
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
const failures = [];
page.on("console", (msg) => { if (msg.type() === "error") failures.push(`console error: ${msg.text()}`); });
page.on("pageerror", (err) => failures.push(`page error: ${err.message}`));

await page.goto(HARNESS, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__FRAMEFORGE_VIEWER__);
await page.evaluate((nextDoc) => window.__FRAMEFORGE_VIEWER__.loadDoc(nextDoc), doc);
// `attached`, not the default `visible`: a path whose `d` failed to parse has no
// geometry and is never "visible", which would time out instead of reporting.
await page.waitForSelector('[data-frameforge-vector="structured"]', { state: "attached" });

const seen = await page.evaluate(() => {
  const d = (id) => {
    const host = document.querySelector(`[data-frameforge-vector="${id}"]`);
    const node = host.tagName.toLowerCase() === "path" ? host : host.querySelector("path");
    return { d: node.getAttribute("d"), length: node.getTotalLength() };
  };
  return {
    structured: d("structured"),
    stringform: d("stringform"),
    curves: d("curves"),
    fractional: d("fractional"),
  };
});

if (seen.structured.d.includes(","))
  failures.push(`structured d was array-stringified: ${seen.structured.d}`);
if (seen.structured.d !== "M 0 21 L 64 21 L 64 60 Z")
  failures.push(`structured d lowered to ${seen.structured.d} , expected "M 0 21 L 64 21 L 64 60 Z"`);
if (seen.stringform.d !== "M 0 21 L 64 21 L 64 60 Z")
  failures.push(`string d must pass through unchanged, got ${seen.stringform.d}`);
// geometric equivalence, not just string equality
if (Math.abs(seen.structured.length - seen.stringform.length) > 0.01)
  failures.push(`structured and string forms traced different geometry: `
    + `${seen.structured.length} vs ${seen.stringform.length}`);
if (!(seen.structured.length > 0))
  failures.push("structured path has zero length — it did not render");
if (seen.curves.d !== "M 10 10 C 20 20 30 0 40 10 A 5 5 0 0 1 50 10 Z")
  failures.push(`curve/arc segments lowered to ${seen.curves.d}`);
if (seen.fractional.d !== "M 2.985 0.5 L 12.25 30.125")
  failures.push(`fractional coords lowered to ${seen.fractional.d}`);

await browser.close();

if (failures.length) {
  console.error("path-d smoke FAILED:");
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log("path-d smoke ok — structured segments lower to path data, string form passes through");
