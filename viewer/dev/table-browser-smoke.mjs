import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = {
  dsl: "FrameForge",
  version: "2.2.0",
  profile: "deck",
  title: "Table smoke",
  defs: {
    tokens: {
      colors: {
        brand: "#005c46",
        hairline: "#123456",
        white: "#ffffff",
        ink: "#202020",
      },
      text_styles: {
        tbl_head: {
          color: "white",
          font_size: 12,
          font_weight: 700,
          line_height: 1.1,
        },
        tbl_cell: {
          color: "ink",
          font_size: 10,
          line_height: 1.2,
        },
      },
    },
  },
  pages: [{
    mode: "page",
    id: "p1",
    canvas: { size: [520, 280] },
    layers: [{ id: "l1", objects: [{
      type: "table",
      id: "styled_table",
      box: [40, 40, 320, 150],
      columns: [{ width: 140, align: "left" }, { width: 90, align: "right" }],
      header: ["Metric", "Value"],
      rows: [["Coverage", "21"], ["Pages", "231"]],
      cell_padding: 4,
      stroke_style: { color: "hairline", width: 2 },
      style: {
        header_fill: "brand",
        header_text: "tbl_head",
        cell_text: "tbl_cell",
      },
      zebra: true,
    }] }],
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
await page.waitForSelector('[data-frameforge-table="styled_table"]');

const styles = await page.evaluate(() => {
  const head = getComputedStyle(document.querySelector('[data-table-cell="styled_table:h:0:0"]'));
  const cell = getComputedStyle(document.querySelector('[data-table-cell="styled_table:r:0:1"]'));
  const zebra = getComputedStyle(document.querySelector('[data-table-cell="styled_table:r:1:0"]'));
  return {
    headBg: head.backgroundColor,
    headColor: head.color,
    headWeight: head.fontWeight,
    headPadding: head.paddingTop,
    headBorder: head.borderBottomColor,
    headBorderWidth: head.borderBottomWidth,
    cellColor: cell.color,
    cellSize: cell.fontSize,
    cellAlign: cell.textAlign,
    zebraBg: zebra.backgroundColor,
  };
});

const checks = [
  ["header fill", styles.headBg === "rgb(0, 92, 70)"],
  ["header text color", styles.headColor === "rgb(255, 255, 255)"],
  ["header weight", Number(styles.headWeight) >= 700],
  ["numeric padding", styles.headPadding === "4px"],
  ["stroke color", styles.headBorder === "rgb(18, 52, 86)"],
  ["stroke width", styles.headBorderWidth === "2px"],
  ["cell text color", styles.cellColor === "rgb(32, 32, 32)"],
  ["cell text size", styles.cellSize === "10px"],
  ["column align", styles.cellAlign === "right"],
  ["zebra fill", styles.zebraBg !== "rgba(0, 0, 0, 0)" && styles.zebraBg !== "transparent"],
];

for (const [name, ok] of checks) {
  if (!ok) failures.push(`${name} not reflected in computed style: ${JSON.stringify(styles)}`);
}

await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Browser table smoke: table style assertions passed.");
