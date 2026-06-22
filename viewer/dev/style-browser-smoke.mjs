import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = {
  dsl: "FrameGraph",
  version: "2.2.0",
  profile: "deck",
  title: "Style smoke",
  defs: {
    tokens: {
      colors: { ink: "#111111", panel: "#ffeecc", hairline: "#123456" },
      fonts: { sans: { family: "Arial", fallback: ["sans-serif"] } },
      styles: {
        fx: {
          background_color: "panel",
          box_shadow: [{ offset_x: 3, offset_y: 4, blur: 5, color: "rgba(0,0,0,.5)" }],
          filter: [{ fn: "blur", value: "0px" }],
          mix_blend_mode: "multiply",
          opacity: 0.75,
          padding: [4, 6, 8, 10],
          border_radius: 9,
        },
      },
      text_styles: {
        display: {
          font: "sans",
          size: 20,
          weight: 700,
          color: "ink",
          letter_spacing: "2px",
          text_transform: "uppercase",
          text_decoration: "underline",
          font_variant_caps: "small-caps",
          hyphens: "auto",
          wrap: true,
        },
      },
    },
  },
  pages: [{
    mode: "page",
    id: "p1",
    canvas: { size: [400, 240] },
    layers: [{ id: "l1", objects: [
      { type: "rect", id: "styled_rect", box: [40, 40, 180, 80], style: "fx" },
      { type: "text", id: "styled_text", box: [40, 140, 260, 44], style: "display", text: "styled text" },
      { type: "image", id: "styled_image", box: [320, 40, 48, 48], src: "assets/avatar.png", clip: { shape: "ellipse" }, stroke: { color: "hairline", width: 3 } },
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
await page.waitForSelector('[data-framegraph-object="styled_rect"]');

const styles = await page.evaluate(() => {
  const rect = getComputedStyle(document.querySelector('[data-framegraph-object="styled_rect"]'));
  const image = getComputedStyle(document.querySelector('[data-framegraph-object="styled_image"]'));
  const textWrap = getComputedStyle(document.querySelector('[data-framegraph-object="styled_text"]'));
  const textInner = getComputedStyle(document.querySelector('[data-framegraph-object="styled_text"] > div'));
  return {
    rectBg: rect.backgroundColor,
    rectShadow: rect.boxShadow,
    rectFilter: rect.filter,
    rectBlend: rect.mixBlendMode,
    rectOpacity: rect.opacity,
    rectPaddingLeft: rect.paddingLeft,
    rectRadius: rect.borderTopLeftRadius,
    imageRadius: image.borderTopLeftRadius,
    imageBorderColor: image.borderTopColor,
    imageBorderWidth: image.borderTopWidth,
    textLetterSpacing: textInner.letterSpacing,
    textTransform: textInner.textTransform || textWrap.textTransform,
    textDecoration: textInner.textDecorationLine,
    textCaps: textInner.fontVariantCaps,
    textHyphens: textInner.hyphens,
  };
});

const checks = [
  ["rect background_color", styles.rectBg === "rgb(255, 238, 204)"],
  ["rect box_shadow", styles.rectShadow !== "none"],
  ["rect filter", styles.rectFilter !== "none"],
  ["rect mix_blend_mode", styles.rectBlend === "multiply"],
  ["rect opacity", Number(styles.rectOpacity) < 1],
  ["rect padding", styles.rectPaddingLeft === "10px"],
  ["rect border_radius", styles.rectRadius === "9px"],
  ["image object clip ellipse", styles.imageRadius === "50%"],
  ["image stroke color", styles.imageBorderColor === "rgb(18, 52, 86)"],
  ["image stroke width", styles.imageBorderWidth === "3px"],
  ["text letter_spacing", styles.textLetterSpacing === "2px"],
  ["text text_transform", styles.textTransform === "uppercase"],
  ["text text_decoration", styles.textDecoration.includes("underline")],
  ["text font_variant_caps", styles.textCaps === "small-caps"],
  ["text hyphens", styles.textHyphens === "auto"],
];

for (const [name, ok] of checks) if (!ok) failures.push(`${name} not reflected in computed style: ${JSON.stringify(styles)}`);
await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Browser style smoke: computed style assertions passed.");
