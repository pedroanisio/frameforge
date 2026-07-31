/**
 * Theme smoke — the viewer chrome must ship both a dark and a light bench,
 * follow the OS preference on first paint, flip on the toggle, and never
 * repaint document content when it does.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HARNESS = `file://${path.join(__dirname, "harness.html")}`;

const doc = {
  dsl: "FrameForge",
  version: "2.2.0",
  profile: "deck",
  title: "Theme smoke",
  defs: {
    tokens: {
      colors: { ink: "#111111", paper: "#ffffff" },
      fonts: { sans: { family: "Arial", fallback: ["sans-serif"] } },
      text_styles: { body: { font: "sans", size: 18, color: "ink" } },
    },
  },
  pages: [{
    mode: "page",
    id: "p1",
    canvas: { size: [400, 240] },
    layers: [{ id: "l1", objects: [
      { type: "rect", id: "paper_rect", box: [0, 0, 400, 240], fill: "paper" },
      { type: "text", id: "doc_text", box: [20, 20, 360, 40], style: "body", text: "document ink" },
    ] }],
  }],
};

const failures = [];
const browser = await chromium.launch();

/** Read the chrome state that a reader can actually see. */
const probe = () => ({
  attr: document.documentElement.getAttribute("data-frameforge-theme"),
  reported: window.__FRAMEFORGE_VIEWER__.theme(),
  shellBg: getComputedStyle(document.querySelector("[data-frameforge-theme]")).backgroundColor,
  shellFg: getComputedStyle(document.querySelector("[data-frameforge-theme]")).color,
  headerBg: getComputedStyle(document.querySelector("header")).backgroundColor,
  railBg: getComputedStyle(document.querySelector("nav")).backgroundColor,
  colorScheme: getComputedStyle(document.documentElement).colorScheme,
  docText: getComputedStyle(document.querySelector('[data-frameforge-object="doc_text"] > div')).color,
  docRectFill: document.querySelector('[data-frameforge-object="paper_rect"]')
    ? getComputedStyle(document.querySelector('[data-frameforge-object="paper_rect"]')).backgroundColor
    : null,
});

/** Relative luminance, per WCAG 2.1 §relative-luminance, from an rgb() string. */
function luminance(rgb) {
  const [r, g, b] = rgb.match(/[\d.]+/g).slice(0, 3).map((v) => Number(v) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const contrast = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

async function session(colorScheme) {
  const page = await browser.newPage({ viewport: { width: 1200, height: 760 }, colorScheme });
  page.on("console", (m) => { if (m.type() === "error") failures.push(`[${colorScheme}] console error: ${m.text()}`); });
  page.on("pageerror", (e) => failures.push(`[${colorScheme}] page error: ${e.message}`));
  await page.goto(HARNESS, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__FRAMEFORGE_VIEWER__);
  await page.evaluate((d) => window.__FRAMEFORGE_VIEWER__.loadDoc(d), doc);
  await page.waitForSelector('[data-frameforge-object="doc_text"]');
  return page;
}

/* --- 1. first paint follows the OS preference ------------------------- */
const lightPage = await session("light");
const light = await lightPage.evaluate(probe);
const darkPage = await session("dark");
const dark = await darkPage.evaluate(probe);

/* --- 2. the toggle flips the bench and takes over from the OS ---------- */
await darkPage.click("[data-frameforge-theme-toggle]");
await darkPage.waitForFunction(() => document.documentElement.getAttribute("data-frameforge-theme") === "light");
const toggled = await darkPage.evaluate(probe);

/* --- 3. the programmatic API agrees with the toggle -------------------- */
await darkPage.evaluate(() => window.__FRAMEFORGE_VIEWER__.setTheme("dark"));
await darkPage.waitForFunction(() => document.documentElement.getAttribute("data-frameforge-theme") === "dark");
const viaApi = await darkPage.evaluate(probe);

const checks = [
  ["light OS preference paints the light bench", light.attr === "light" && light.reported.id === "light"],
  ["light bench follows the system on first paint", light.reported.following === true],
  ["dark OS preference paints the dark bench", dark.attr === "dark" && dark.reported.id === "dark"],
  ["dark bench follows the system on first paint", dark.reported.following === true],
  ["light shell is lighter than dark shell", luminance(light.shellBg) > luminance(dark.shellBg)],
  ["light chrome ink is darker than dark chrome ink", luminance(light.shellFg) < luminance(dark.shellFg)],
  ["light header differs from light stage", light.headerBg !== light.shellBg],
  ["dark header differs from dark stage", dark.headerBg !== dark.shellBg],
  ["light rail is a distinct surface", light.railBg !== light.headerBg],
  ["dark rail is a distinct surface", dark.railBg !== dark.headerBg],
  ["light bench declares color-scheme: light", light.colorScheme === "light"],
  ["dark bench declares color-scheme: dark", dark.colorScheme === "dark"],
  ["light chrome text clears WCAG AA on its surface", contrast(light.shellFg, light.shellBg) >= 4.5],
  ["dark chrome text clears WCAG AA on its surface", contrast(dark.shellFg, dark.shellBg) >= 4.5],
  ["toggle flips dark -> light", toggled.attr === "light" && toggled.reported.id === "light"],
  ["toggle stops following the system", toggled.reported.following === false],
  ["toggle repaints the shell", toggled.shellBg === light.shellBg],
  ["setTheme('dark') restores the dark bench", viaApi.attr === "dark" && viaApi.reported.id === "dark"],
  ["setTheme repaints the shell", viaApi.shellBg === dark.shellBg],
  ["document ink is theme-independent", light.docText === dark.docText && toggled.docText === dark.docText],
  ["document paper is theme-independent", light.docRectFill === dark.docRectFill],
  ["state() reports the active theme", viaApi.reported.id === "dark"],
];

for (const [name, ok] of checks) {
  if (!ok) failures.push(`${name} — light=${JSON.stringify(light)} dark=${JSON.stringify(dark)} toggled=${JSON.stringify(toggled)} viaApi=${JSON.stringify(viaApi)}`);
}

await browser.close();

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Browser theme smoke: ${checks.length} dark/light chrome assertions passed.`);
