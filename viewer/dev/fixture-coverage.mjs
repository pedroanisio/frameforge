import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as yaml from "js-yaml";
import { normalizeFrameGraphDoc } from "../framegraph-normalize.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");
const FIXTURES = path.join(ROOT, "fixtures");
const SCHEMA = JSON.parse(fs.readFileSync(path.join(ROOT, "schema/framegraph-v2.schema.json"), "utf8"));

const PAGE_MODES = new Set(["page", "flow", undefined]);
const ABSOLUTE_TYPES = new Set([
  "rect", "text", "line", "polyline", "polygon", "path", "ellipse", "circle",
  "icon", "image", "bullet_list", "table", "group", "component", "chip_row", "uml.marker_glyph",
  "dimension",
  "uml.classifier_box", "uml.component_box", "uml.state_box", "uml.action",
  "uml.artifact_box", "uml.node_box", "uml.lifeline", "uml.activation_bar",
]);
const FLOW_TYPES = new Set([
  "heading", "paragraph", "list", "bullet_list", "table", "code", "math", "toc",
  "figure", "block", "bibliography", "page_break", "spacer",
]);
const STYLE_KEYS = new Set([...Object.keys(SCHEMA.$defs.Style.properties), "class_"]);
const STYLE_METADATA_KEYS = new Set([
  "cell_text", "header_fill", "header_text", "meta",
]);

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

function walkLayerObject(obj, visit) {
  if (!obj || typeof obj !== "object") return;
  visit(obj);
  for (const child of obj.children || []) walkLayerObject(child, visit);
}

function visitStyleKeys(style, visit) {
  if (!style || typeof style !== "object" || Array.isArray(style)) return;
  for (const key of Object.keys(style)) visit(key);
}

function walkFlowBlock(block, visit) {
  if (!block || typeof block !== "object") return;
  visit(block);
  for (const child of block.children || block.content || []) walkFlowBlock(child, visit);
  if (block.object) walkLayerObject(block.object, visit);
  for (const item of block.items || []) walkFlowBlock(item, visit);
}

const docs = files(FIXTURES).map((file) => ({ file, doc: loadDoc(file) }))
  .filter(({ doc }) => doc && doc.dsl === "FrameGraph" && Array.isArray(doc.pages));

const failures = [];
const objectTypes = new Set();
const styleKeys = new Set();
let pageCount = 0;

for (const { file, doc } of docs) {
  const tokens = doc.defs?.tokens || {};
  for (const group of ["text_styles", "styles", "stroke_styles"]) {
    for (const [name, style] of Object.entries(tokens[group] || {})) {
      visitStyleKeys(style, (key) => {
        styleKeys.add(key);
        if (!STYLE_KEYS.has(key) && !STYLE_METADATA_KEYS.has(key)) {
          failures.push(`${path.relative(ROOT, file)} ${group}.${name}: no style render policy for ${key}`);
        }
      });
    }
  }
  if (doc.pages.length === 0) {
    failures.push(`${path.relative(ROOT, file)}: empty pages[]`);
    continue;
  }
  for (const [pageIndex, page] of doc.pages.entries()) {
    pageCount += 1;
    if (!PAGE_MODES.has(page.mode)) {
      failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: unsupported page mode ${page.mode}`);
    }
    for (const layer of page.layers || []) {
      for (const obj of layer.objects || []) {
        walkLayerObject(obj, (o) => {
          if (!o.type) return;
          visitStyleKeys(o.style, (key) => {
            styleKeys.add(key);
            if (!STYLE_KEYS.has(key) && !STYLE_METADATA_KEYS.has(key)) {
              failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: no inline style render policy for ${key}`);
            }
          });
          objectTypes.add(o.type);
          if (o.type === "use") {
            failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: unexpanded symbol use reached viewer render policy`);
          }
          const covered = ABSOLUTE_TYPES.has(o.type) || o.box || (o.from && o.to) || o.children;
          if (!covered) failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: no absolute render policy for ${o.type}`);
        });
      }
    }
    for (const block of page.story || page.sections || []) {
      walkFlowBlock(block, (o) => {
        if (!o.type) return;
        visitStyleKeys(o.style, (key) => {
          styleKeys.add(key);
          if (!STYLE_KEYS.has(key) && !STYLE_METADATA_KEYS.has(key)) {
            failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: no inline flow style render policy for ${key}`);
          }
        });
        objectTypes.add(o.type);
        if (o.type === "use") {
          failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: unexpanded symbol use reached viewer flow render policy`);
        }
        const covered = FLOW_TYPES.has(o.type) || ABSOLUTE_TYPES.has(o.type) || o.box || (o.from && o.to) || o.children;
        if (!covered) failures.push(`${path.relative(ROOT, file)} page ${pageIndex + 1}: no flow render policy for ${o.type}`);
      });
    }
  }
}

if (docs.length === 0) failures.push("expected at least one FrameGraph fixture doc, found 0");

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Fixture coverage: ${docs.length} docs, ${pageCount} page records, ${objectTypes.size} object/block types, ${styleKeys.size} style keys.`);
