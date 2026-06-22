import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as yaml from "js-yaml";
import { chromium } from "playwright";
import { normalizeFrameGraphDoc } from "../framegraph-normalize.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const VIEWER = path.resolve(__dirname, "..");
const ROOT = path.resolve(VIEWER, "..");
const FIXTURES = path.join(ROOT, "fixtures");
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

function files(dir) {
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...files(p));
    else if (/\.(json|ya?ml)$/i.test(ent.name)) out.push(p);
  }
  return out.sort();
}

function loadDoc(file) {
  const raw = fs.readFileSync(file, "utf8");
  const doc = /\.json$/i.test(file) ? JSON.parse(raw) : yaml.load(raw);
  return normalizeFrameGraphDoc(doc);
}

function hasLayerContent(pageRecord) {
  return (pageRecord.layers || []).some((layer) => (layer.objects || []).length > 0);
}

function hasFlowContent(pageRecord) {
  return (pageRecord.story || pageRecord.sections || []).length > 0;
}

function hasRenderableContent(pageRecord) {
  return hasLayerContent(pageRecord) || (pageRecord.objects || []).length > 0 || hasFlowContent(pageRecord);
}

const docs = files(FIXTURES)
  .map((file) => ({ file, rel: path.relative(ROOT, file), doc: loadDoc(file) }))
  .filter(({ doc }) => doc && doc.dsl === "FrameGraph" && Array.isArray(doc.pages));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1366, height: 820 }, deviceScaleFactor: 1 });
const failures = [];
let renderedPages = 0;
let expandedPages = 0;

page.on("console", (msg) => {
  if (msg.type() === "error") failures.push(`console error: ${msg.text()}`);
});
page.on("pageerror", (err) => failures.push(`page error: ${err.message}`));

await page.goto(HARNESS, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__FRAMEGRAPH_VIEWER__);

for (const { rel, doc } of docs) {
  await page.evaluate((nextDoc) => window.__FRAMEGRAPH_VIEWER__.loadDoc(nextDoc), doc);
  await page.waitForFunction(
    (title) => window.__FRAMEGRAPH_VIEWER__?.state().title === title,
    doc.title,
  );
  const state = await page.evaluate(() => window.__FRAMEGRAPH_VIEWER__.state());
  const sourcePages = doc.pages || [];
  const sourceRenderablePages = sourcePages.map(hasRenderableContent);
  const hasFlow = sourcePages.some((p) => p.mode === "flow" || p.story || p.sections);
  if (state.pageCount < sourcePages.length) {
    failures.push(`${rel}: expanded page count ${state.pageCount} is smaller than source page count ${sourcePages.length}`);
  }
  if (hasFlow && state.pageCount <= sourcePages.length) {
    failures.push(`${rel}: flow document did not expand beyond ${sourcePages.length} source page record(s)`);
  }
  renderedPages += state.pageCount;
  expandedPages += Math.max(0, state.pageCount - sourcePages.length);
  for (let i = 0; i < state.pageCount; i += 1) {
    await page.evaluate((idx) => window.__FRAMEGRAPH_VIEWER__.setPage(idx), i);
    await page.waitForFunction(
      (idx) => window.__FRAMEGRAPH_VIEWER__?.state().pageIndex === idx,
      i,
    );
    await page.waitForTimeout(20);
    const result = await page.locator('[data-framegraph-page="active"]').evaluate((el) => {
      const box = el.getBoundingClientRect();
      const flowRegion = el.querySelector('[data-flow-region="active"]');
      return {
        width: box.width,
        height: box.height,
        elementCount: el.querySelectorAll("*").length,
        textLength: (el.textContent || "").trim().length,
        mode: el.getAttribute("data-page-mode"),
        id: el.getAttribute("data-page-id"),
        flowScrollHeight: flowRegion ? flowRegion.scrollHeight : 0,
        flowClientHeight: flowRegion ? flowRegion.clientHeight : 0,
      };
    });
    if (result.width <= 0 || result.height <= 0) {
      failures.push(`${rel} rendered page ${i + 1}: active canvas has invalid size ${result.width}x${result.height}`);
    }
    const sourceHasContent = i >= sourceRenderablePages.length || sourceRenderablePages[i];
    if (sourceHasContent && result.elementCount === 0 && result.textLength === 0) {
      failures.push(`${rel} rendered page ${i + 1}: active canvas rendered no content`);
    }
    if (result.mode === "flow" && result.flowScrollHeight > result.flowClientHeight + 2) {
      failures.push(`${rel} rendered page ${i + 1}: flow region clips vertically (${result.flowScrollHeight} > ${result.flowClientHeight})`);
    }
  }
}

await browser.close();

if (failures.length) {
  console.error(failures.slice(0, 80).join("\n"));
  if (failures.length > 80) console.error(`... ${failures.length - 80} more failure(s)`);
  process.exit(1);
}

console.log(`Browser smoke: rendered ${docs.length} docs and ${renderedPages} expanded page(s) (${expandedPages} generated from flow).`);
