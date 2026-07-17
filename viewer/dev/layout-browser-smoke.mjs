import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = {
  dsl: "FrameForge",
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
      { type: "rect", id: "conn_left", box: [300, 54, 50, 40], fill: "a", ports: { east: [350, 74] } },
      { type: "rect", id: "conn_right", box: [420, 54, 50, 40], fill: "b" },
      { type: "connector", id: "conn_line", from: { object: "conn_left", port: "east" }, to: { object: "conn_right", side: "west" }, stroke: "c", stroke_style: { stroke_width: 2, arrow_end: true } },
      { type: "connector", id: "conn_route", from: { object: "conn_left", side: "south" }, to: { point: [455, 160] }, route: { type: "orthogonal", points: [[325, 145], [455, 145]] }, stroke: "c" },
      { type: "dimension", id: "dim_width", kind: "linear", from: [520, 60], to: [620, 60], offset: 18, text: "100", stroke: "c" },
    ] }],
  }],
};

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
const failures = [];
page.on("console", (msg) => { if (msg.type() === "error") failures.push(`console error: ${msg.text()}`); });
page.on("pageerror", (err) => failures.push(`page error: ${err.message}`));

await page.goto(HARNESS, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__FRAMEFORGE_VIEWER__);
await page.evaluate((nextDoc) => window.__FRAMEFORGE_VIEWER__.loadDoc(nextDoc), doc);
await page.waitForSelector('[data-frameforge-object="grid_d"]');

const boxes = await page.evaluate(() => {
  const box = (id) => {
    const r = document.querySelector(`[data-frameforge-object="${id}"]`).getBoundingClientRect();
    return { left: Math.round(r.left), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height) };
  };
  return {
    rowA: box("row_a"),
    rowB: box("row_b"),
    gridA: box("grid_a"),
    gridB: box("grid_b"),
    gridC: box("grid_c"),
    gridD: box("grid_d"),
    connLine: document.querySelector('[data-frameforge-vector="conn_line"]')?.outerHTML || "",
    connRoute: document.querySelector('[data-frameforge-vector="conn_route"]')?.outerHTML || "",
    dimWidth: document.querySelector('[data-frameforge-vector="dim_width"]')?.closest("svg")?.outerHTML || "",
  };
});

if (!(boxes.rowB.left > boxes.rowA.left + boxes.rowA.width)) failures.push(`row layout overlapped: ${JSON.stringify(boxes)}`);
if (!(boxes.gridB.left > boxes.gridA.left && boxes.gridC.left > boxes.gridB.left)) failures.push(`grid first row did not advance columns: ${JSON.stringify(boxes)}`);
if (!(boxes.gridD.top > boxes.gridA.top + boxes.gridA.height && boxes.gridD.left === boxes.gridA.left)) failures.push(`grid wrap row is wrong: ${JSON.stringify(boxes)}`);
if (!/x1="350" y1="74" x2="420" y2="74"/.test(boxes.connLine)) failures.push(`connector line anchors wrong: ${boxes.connLine}`);
if (!/points="325,94 325,145 455,145 455,160"/.test(boxes.connRoute)) failures.push(`connector route anchors wrong: ${boxes.connRoute}`);
if (!/x1="520" y1="78" x2="620" y2="78"/.test(boxes.dimWidth) || !/>100</.test(boxes.dimWidth)) failures.push(`dimension line wrong: ${boxes.dimWidth}`);

await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Browser layout smoke: row/grid placement assertions passed.");
