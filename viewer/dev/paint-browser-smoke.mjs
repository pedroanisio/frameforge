/**
 * Gate: box-object paint + white-space conformance.
 *
 * Two viewer/engine divergences this pins down, both found on a real 10-page
 * spec whose every rect went unpainted in the viewer while the PDF was correct:
 *
 *  1. `fill` / `stroke` authored in the STYLE BAG (`style: {fill: "#101418"}`)
 *     must paint. Div-backed objects (rect, uml boxes) previously read only the
 *     object-level `o.fill`; the style-bag form reached CSS as the `fill`
 *     property, which is inert on an HTML element, so the box stayed
 *     transparent — a full-bleed band, eight tiles and a panel all vanished.
 *
 *  2. Authored `\n` follows `Style.white_space` (spec §"Authored line breaks
 *     and spacing"): `normal` collapses, `pre*` preserves. The viewer hardcoded
 *     pre-wrap, so it disagreed with every other backend.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const LEDGER = "DS   892bdce5  Design Systems\nHX   ee74dc0b  Human-Centric AI";

const doc = {
  dsl: "FrameForge",
  version: "2.2.0",
  title: "Paint + white-space smoke",
  defs: { tokens: { colors: { band: "#101418" } } },
  pages: [{
    mode: "page",
    id: "p1",
    canvas: { size: [600, 400] },
    rendering: { coordinate_mode: "absolute" },
    layers: [{ id: "l1", objects: [
      // 1 — fill/stroke in the style bag (the form the engine renders correctly)
      { type: "rect", id: "style_fill", box: [0, 0, 600, 90], style: { fill: "#101418" } },
      { type: "rect", id: "style_fill_token", box: [20, 100, 40, 40], style: { fill: "band" } },
      { type: "rect", id: "style_stroke", box: [80, 100, 40, 40],
        style: { fill: "#EFF2F5", stroke: "#0b5ed0", stroke_width: 3 } },
      // regressions — the object-level form must keep working, and a rect with
      // a style bag but no paint must stay transparent and borderless
      { type: "rect", id: "object_fill", box: [140, 100, 40, 40], fill: "#0b5ed0" },
      { type: "rect", id: "no_paint", box: [200, 100, 40, 40], style: { opacity: 0.9 } },
      // 2 — white_space governs authored newlines
      { type: "text", id: "ws_default", box: [20, 160, 560, 60], text: LEDGER,
        style: { font_family: ["monospace"], font_size: 10 } },
      { type: "text", id: "ws_prewrap", box: [20, 240, 560, 60], text: LEDGER,
        style: { font_family: ["monospace"], font_size: 10, white_space: "pre-wrap" } },
      { type: "text", id: "ws_nowrap", box: [20, 320, 560, 60], text: "a b c",
        style: { font_family: ["monospace"], font_size: 10, white_space: "nowrap" } },
    ] }],
  }],
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
const failures = [];
page.on("console", (msg) => { if (msg.type() === "error") failures.push(`console error: ${msg.text()}`); });
page.on("pageerror", (err) => failures.push(`page error: ${err.message}`));

await page.goto(HARNESS, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__FRAMEFORGE_VIEWER__);
await page.evaluate((nextDoc) => window.__FRAMEFORGE_VIEWER__.loadDoc(nextDoc), doc);
await page.waitForSelector('[data-frameforge-object="style_fill"]');

const seen = await page.evaluate(() => {
  const css = (id) => getComputedStyle(document.querySelector(`[data-frameforge-object="${id}"]`));
  const inner = (id) => {
    const node = document.querySelector(`[data-frameforge-object="${id}"] > div`);
    // One client rect per rendered line box — the VISUAL result, which is what
    // has to agree with the engine. (textContent always keeps the authored
    // "\n"; `white-space: normal` collapses it at layout time, not in the DOM.)
    const range = document.createRange();
    range.selectNodeContents(node);
    return { whiteSpace: getComputedStyle(node).whiteSpace, lines: range.getClientRects().length };
  };
  return {
    styleFill: css("style_fill").backgroundColor,
    styleFillToken: css("style_fill_token").backgroundColor,
    styleStrokeFill: css("style_stroke").backgroundColor,
    styleStrokeColor: css("style_stroke").borderTopColor,
    styleStrokeWidth: css("style_stroke").borderTopWidth,
    objectFill: css("object_fill").backgroundColor,
    noPaintBg: css("no_paint").backgroundColor,
    // Tailwind's preflight sets `border-style: solid` on every element, so the
    // "no border" assertion has to read the WIDTH, not the style.
    noPaintBorder: css("no_paint").borderTopWidth,
    wsDefault: inner("ws_default"),
    wsPrewrap: inner("ws_prewrap"),
    wsNowrap: inner("ws_nowrap"),
  };
});

const eq = (label, got, want) => {
  if (got !== want) failures.push(`${label}: expected ${want}, got ${got}`);
};

eq("style.fill paints the band", seen.styleFill, "rgb(16, 20, 24)");
eq("style.fill resolves colour tokens", seen.styleFillToken, "rgb(16, 20, 24)");
eq("style.fill paints alongside a stroke", seen.styleStrokeFill, "rgb(239, 242, 245)");
eq("style.stroke paints a border", seen.styleStrokeColor, "rgb(11, 94, 208)");
eq("style.stroke_width sizes the border", seen.styleStrokeWidth, "3px");
eq("object-level fill still paints", seen.objectFill, "rgb(11, 94, 208)");
eq("a paintless style bag stays transparent", seen.noPaintBg, "rgba(0, 0, 0, 0)");
eq("a paintless style bag draws no border", seen.noPaintBorder, "0px");

// white_space: `normal` collapses newlines AND space runs, exactly as the
// engine's text layout does; `pre-wrap` preserves both.
eq("white_space defaults to collapsing", seen.wsDefault.whiteSpace, "normal");
// The ledger is ~56 collapsed characters at 10px mono in a 560px box, so the
// collapsing default must reflow both authored rows onto ONE line.
eq("white_space normal reflows to one line", seen.wsDefault.lines, 1);
eq("white_space: pre-wrap preserves", seen.wsPrewrap.whiteSpace, "pre-wrap");
if (seen.wsPrewrap.lines < 2)
  failures.push(`white_space pre-wrap: authored break was lost (${seen.wsPrewrap.lines} line box)`);
eq("white_space: nowrap is honoured", seen.wsNowrap.whiteSpace, "nowrap");

await browser.close();

if (failures.length) {
  console.error("paint/white-space smoke FAILED:");
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log("paint/white-space smoke ok — style-bag fill/stroke paint; white_space honoured");
