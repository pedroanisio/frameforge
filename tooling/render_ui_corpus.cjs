// Render the CC0 corpus UI mockups to high-definition PNG files.
//
// Requires the FrameForge-owned Node tooling dependencies:
//   npm --prefix tooling ci
//   npx --prefix tooling playwright install chromium
//   node tooling/render_ui_corpus.cjs
//
// Honors PLAYWRIGHT_BROWSERS_PATH when Chromium lives outside the default cache.
const path = require("node:path");
const { chromium } = require("playwright");

const UI_DIR = path.resolve(__dirname, "..", "tests", "fixtures", "corpus", "ui");
const SRC_DIR = path.join(UI_DIR, "_src");

const PAGES = [
  { src: "mobile-app-feed.html", out: "mobile-app-feed.png", width: 390, height: 844, dsf: 3 },
  { src: "analytics-dashboard.html", out: "analytics-dashboard.png", width: 1440, height: 900, dsf: 2 },
];

(async () => {
  const browser = await chromium.launch();
  for (const pageSpec of PAGES) {
    const page = await browser.newPage({
      viewport: { width: pageSpec.width, height: pageSpec.height },
      deviceScaleFactor: pageSpec.dsf,
    });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(`file://${path.join(SRC_DIR, pageSpec.src)}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    const outputPath = path.join(UI_DIR, pageSpec.out);
    await page.screenshot({ path: outputPath });
    const pixels = `${pageSpec.width * pageSpec.dsf}×${pageSpec.height * pageSpec.dsf}`;
    console.log(
      `  ${pageSpec.out.padEnd(26)} ${pixels.padStart(11)} px  @${pageSpec.dsf}x`
      + (errors.length ? `  [page errors: ${errors.slice(0, 3).join(" | ")}]` : ""),
    );
    await page.close();
  }
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
