import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = {
  dsl: "FrameGraph",
  version: "2.2.0",
  profile: "deck",
  title: "Layout smoke",
  defs: { tokens: { colors: { a: "#d33", b: "#3d3", c: "#33d" } } },
  pages: [{
    mode: "page",
    id: "p1",
    canvas: { size: [500, 320] },
    layers: [{ id: "l1", objects: [
      { type: "group", id: "row_group", box: [40, 40, 220, 40], layout: { kind: "row", gap: 10 }, children: [
        { type: "rect", id: "row_a", box: [0, 0, 40, 40], fill: "a" },
        { type: "rect", id: "row_b", box: [0, 0, 40, 40], fill: "b" },
      ] },
      { type: "group", id: "grid_group", box: [40, 120, 150, 90], layout: { kind: "grid", columns: 3, gap: 5 }, children: [
        { type: "rect", id: "grid_a", box: [0, 0, 40, 40], fill: "a" },
        { type: "rect", id: "grid_b", box: [0, 0, 40, 40], fill: "b" },
        { type: "rect", id: "grid_c", box: [0, 0, 40, 40], fill: "c" },
        { type: "rect", id: "grid_d", box: [0, 0, 40, 40], fill: "a" },
      ] },
    ] }],
  }],
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
const failures = [];
page.on("console", (msg) => { if (msg.type() === "error") failures.push(`console error: ${msg.text()}`); });
page.on("pageerror", (err) => failures.push(`page error: ${err.message}`));

await page.goto(HARNESS, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__FRAMEGRAPH_VIEWER__);
await page.evaluate((nextDoc) => window.__FRAMEGRAPH_VIEWER__.loadDoc(nextDoc), doc);
await page.waitForSelector('[data-framegraph-object="grid_d"]');

const boxes = await page.evaluate(() => {
  const box = (id) => {
    const r = document.querySelector(`[data-framegraph-object="${id}"]`).getBoundingClientRect();
    return { left: Math.round(r.left), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height) };
  };
  return {
    rowA: box("row_a"),
    rowB: box("row_b"),
    gridA: box("grid_a"),
    gridB: box("grid_b"),
    gridC: box("grid_c"),
    gridD: box("grid_d"),
  };
});

if (!(boxes.rowB.left > boxes.rowA.left + boxes.rowA.width)) failures.push(`row layout overlapped: ${JSON.stringify(boxes)}`);
if (!(boxes.gridB.left > boxes.gridA.left && boxes.gridC.left > boxes.gridB.left)) failures.push(`grid first row did not advance columns: ${JSON.stringify(boxes)}`);
if (!(boxes.gridD.top > boxes.gridA.top + boxes.gridA.height && boxes.gridD.left === boxes.gridA.left)) failures.push(`grid wrap row is wrong: ${JSON.stringify(boxes)}`);

await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Browser layout smoke: row/grid placement assertions passed.");
