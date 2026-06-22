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
          background: "panel",
          background_position: "10px 20px",
          background_size: "24px 24px",
          background_repeat: "no-repeat",
          background_blend_mode: "multiply",
          background_color: "panel",
          box_shadow: [{ offset_x: 3, offset_y: 4, blur: 5, color: "rgba(0,0,0,.5)" }],
          filter: [{ fn: "blur", value: "0px" }],
          mix_blend_mode: "multiply",
          isolation: "isolate",
          opacity: 0.75,
          padding: [4, 6, 8, 10],
          border_radius: 9,
          outline: { width: 2, style: "solid", color: "hairline" },
          outline_offset: 3,
          overflow_x: "hidden",
          overflow_y: "auto",
          css: "visibility: visible;",
        },
      },
      text_styles: {
        display: {
          font: "sans",
          size: 20,
          bold: true,
          color: "ink",
          letter_spacing: "2px",
          word_spacing: "3px",
          text_align_last: "center",
          text_transform: "uppercase",
          text_decoration: "underline",
          text_indent: "5px",
          text_shadow: [{ offset_x: 1, offset_y: 2, blur: 0, color: "hairline" }],
          font_variant_caps: "small-caps",
          font_variant_numeric: "tabular-nums",
          font_kerning: "normal",
          hyphens: "auto",
          word_break: "break-word",
          overflow_wrap: "anywhere",
          text_overflow: "ellipsis",
          max_lines: 2,
          direction: "ltr",
          unicode_bidi: "normal",
          wrap: true,
        },
        accent_span: {
          color: "hairline",
          font_size: 14,
          font_weight: 700,
          text_decoration: "underline",
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
      { type: "text", id: "styled_spans", box: [40, 195, 320, 26], style: { font_size: 16, color: "ink" }, spans: ["Prefix ", { text: "styled", style: "accent_span" }, " suffix"] },
      { type: "path", id: "filled_path", d: "M 310 135 l 42 0 l -21 34 z", fill: "panel", fill_opacity: 0.4 },
      { type: "line", id: "faded_line", from: [310, 185], to: [370, 185], stroke: { color: "hairline", width: 4 }, stroke_opacity: 0.35 },
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
  const spanWrap = document.querySelector('[data-framegraph-object="styled_spans"]');
  const span = spanWrap.querySelector('[data-framegraph-span="1"]');
  const spanStyle = getComputedStyle(span);
  const filledPath = document.querySelector('[data-framegraph-vector="filled_path"]');
  const fadedLine = document.querySelector('[data-framegraph-vector="faded_line"]');
  return {
    rectBg: rect.backgroundColor,
    rectShadow: rect.boxShadow,
    rectFilter: rect.filter,
    rectBlend: rect.mixBlendMode,
    rectIsolation: rect.isolation,
    rectOpacity: rect.opacity,
    rectPaddingLeft: rect.paddingLeft,
    rectRadius: rect.borderTopLeftRadius,
    rectBgPosition: rect.backgroundPosition,
    rectBgSize: rect.backgroundSize,
    rectBgRepeat: rect.backgroundRepeat,
    rectBgBlend: rect.backgroundBlendMode,
    rectOutlineColor: rect.outlineColor,
    rectOutlineWidth: rect.outlineWidth,
    rectOutlineOffset: rect.outlineOffset,
    rectOverflowX: rect.overflowX,
    rectOverflowY: rect.overflowY,
    rectVisibility: rect.visibility,
    imageRadius: image.borderTopLeftRadius,
    imageBorderColor: image.borderTopColor,
    imageBorderWidth: image.borderTopWidth,
    textLetterSpacing: textInner.letterSpacing,
    textWordSpacing: textInner.wordSpacing,
    textAlignLast: textInner.textAlignLast,
    textTransform: textInner.textTransform || textWrap.textTransform,
    textDecoration: textInner.textDecorationLine,
    textIndent: textInner.textIndent,
    textShadow: textInner.textShadow,
    textCaps: textInner.fontVariantCaps,
    textNumeric: textInner.fontVariantNumeric,
    textKerning: textInner.fontKerning,
    textHyphens: textInner.hyphens,
    textWordBreak: textInner.wordBreak,
    textOverflowWrap: textInner.overflowWrap,
    textTextOverflow: textInner.textOverflow,
    textLineClamp: textInner.webkitLineClamp,
    textDirection: textInner.direction,
    spanText: spanWrap.textContent,
    spanColor: spanStyle.color,
    spanSize: spanStyle.fontSize,
    spanWeight: spanStyle.fontWeight,
    spanDecoration: spanStyle.textDecorationLine,
    filledPathStroke: filledPath.getAttribute("stroke"),
    filledPathFillOpacity: filledPath.getAttribute("fill-opacity"),
    fadedLineStroke: fadedLine.getAttribute("stroke"),
    fadedLineStrokeWidth: fadedLine.getAttribute("stroke-width"),
    fadedLineStrokeOpacity: fadedLine.getAttribute("stroke-opacity"),
  };
});

const checks = [
  ["rect background_color", styles.rectBg === "rgb(255, 238, 204)"],
  ["rect box_shadow", styles.rectShadow !== "none"],
  ["rect filter", styles.rectFilter !== "none"],
  ["rect mix_blend_mode", styles.rectBlend === "multiply"],
  ["rect isolation", styles.rectIsolation === "isolate"],
  ["rect opacity", Number(styles.rectOpacity) < 1],
  ["rect padding", styles.rectPaddingLeft === "10px"],
  ["rect border_radius", styles.rectRadius === "9px"],
  ["rect background_position", styles.rectBgPosition.includes("10px") && styles.rectBgPosition.includes("20px")],
  ["rect background_size", styles.rectBgSize === "24px 24px"],
  ["rect background_repeat", styles.rectBgRepeat === "no-repeat"],
  ["rect background_blend_mode", styles.rectBgBlend === "multiply"],
  ["rect outline color", styles.rectOutlineColor === "rgb(18, 52, 86)"],
  ["rect outline width", styles.rectOutlineWidth === "2px"],
  ["rect outline offset", styles.rectOutlineOffset === "3px"],
  ["rect overflow_x", styles.rectOverflowX === "hidden"],
  ["rect overflow_y", styles.rectOverflowY === "auto"],
  ["rect css escape", styles.rectVisibility === "visible"],
  ["image object clip ellipse", styles.imageRadius === "50%"],
  ["image stroke color", styles.imageBorderColor === "rgb(18, 52, 86)"],
  ["image stroke width", styles.imageBorderWidth === "3px"],
  ["text letter_spacing", styles.textLetterSpacing === "2px"],
  ["text word_spacing", styles.textWordSpacing === "3px"],
  ["text text_align_last", styles.textAlignLast === "center"],
  ["text text_transform", styles.textTransform === "uppercase"],
  ["text text_decoration", styles.textDecoration.includes("underline")],
  ["text text_indent", styles.textIndent === "5px"],
  ["text text_shadow", styles.textShadow !== "none"],
  ["text font_variant_caps", styles.textCaps === "small-caps"],
  ["text font_variant_numeric", styles.textNumeric === "tabular-nums"],
  ["text font_kerning", styles.textKerning === "normal"],
  ["text hyphens", styles.textHyphens === "auto"],
  ["text word_break", styles.textWordBreak === "break-word"],
  ["text overflow_wrap", styles.textOverflowWrap === "anywhere"],
  ["text text_overflow", styles.textTextOverflow === "ellipsis"],
  ["text max_lines", styles.textLineClamp === "2"],
  ["text direction", styles.textDirection === "ltr"],
  ["mixed string spans", styles.spanText === "Prefix styled suffix"],
  ["span color", styles.spanColor === "rgb(18, 52, 86)"],
  ["span size", styles.spanSize === "14px"],
  ["span weight", Number(styles.spanWeight) >= 700],
  ["span decoration", styles.spanDecoration.includes("underline")],
  ["fill-only vector has no default stroke", styles.filledPathStroke === "none"],
  ["vector fill_opacity", styles.filledPathFillOpacity === "0.4"],
  ["legacy stroke vector color", styles.fadedLineStroke === "#123456" || styles.fadedLineStroke === "rgb(18, 52, 86)"],
  ["legacy stroke vector width", styles.fadedLineStrokeWidth === "4"],
  ["vector stroke_opacity", styles.fadedLineStrokeOpacity === "0.35"],
];

for (const [name, ok] of checks) if (!ok) failures.push(`${name} not reflected in computed style: ${JSON.stringify(styles)}`);
await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Browser style smoke: computed style assertions passed.");
