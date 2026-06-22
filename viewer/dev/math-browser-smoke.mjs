import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { normalizeFrameGraphDoc } from "../framegraph-normalize.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = normalizeFrameGraphDoc({
  dsl: "FrameGraph",
  version: "2.2.0",
  profile: "report",
  title: "viewer math smoke",
  pages: [{
    mode: "flow",
    id: "p",
    story: [
      {
        type: "paragraph",
        spans: [
          "Inline ",
          {
            kind: "math",
            mathml: "<math><mi>y</mi><mo>=</mo><mn>1</mn></math>",
          },
          " renders.",
        ],
      },
      {
        type: "math",
        mathml: "<math><mi>x</mi><mo>=</mo><msqrt><mn>2</mn></msqrt></math>",
        alt: "x equals square root of two",
      },
    ],
  }],
});

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 700 }, deviceScaleFactor: 1 });
const failures = [];
page.on("console", (msg) => { if (msg.type() === "error") failures.push(`console error: ${msg.text()}`); });
page.on("pageerror", (err) => failures.push(`page error: ${err.message}`));

await page.goto(HARNESS, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__FRAMEGRAPH_VIEWER__);
await page.evaluate((nextDoc) => window.__FRAMEGRAPH_VIEWER__.loadDoc(nextDoc), doc);
await page.waitForFunction(() => window.__FRAMEGRAPH_VIEWER__?.state().title === "viewer math smoke");

const result = await page.locator('[data-framegraph-page="active"]').evaluate((el) => {
  const mathNodes = Array.from(el.querySelectorAll(".fg-mathml math"));
  const text = el.textContent || "";
  return {
    mathNodeCount: mathNodes.length,
    inlineCount: el.querySelectorAll(".fg-math-inline.fg-mathml math").length,
    displayCount: el.querySelectorAll(".fg-math-display.fg-mathml math").length,
    rawXml: text.includes("<math>") || text.includes("&lt;math&gt;"),
    fallback: text.includes("math expression"),
  };
});

if (result.mathNodeCount !== 2) failures.push(`expected 2 MathML nodes, found ${result.mathNodeCount}`);
if (result.inlineCount !== 1) failures.push(`expected 1 inline MathML node, found ${result.inlineCount}`);
if (result.displayCount !== 1) failures.push(`expected 1 display MathML node, found ${result.displayCount}`);
if (result.rawXml) failures.push("raw MathML XML leaked into viewer text");
if (result.fallback) failures.push("valid MathML fell back instead of rendering");

await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Browser math smoke: TeX and MathML rendering assertions passed.");
