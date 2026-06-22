// render-ui-corpus.cjs — render the corpus UI mockups to high-def PNG.
//
// Renders the self-contained, public-domain (CC0) UI source pages under
// fixtures/corpus/ui/_src/*.html to high-DPI PNG rasters under
// fixtures/corpus/ui/. These are the raster-UI expressiveness target (layered
// cards, gradients, shadows, inline-SVG charts). Output bytes are then pinned
// by tooling/fetch_corpus.py (the generated entries) into the corpus lockfile.
//
// Requires Playwright + Chromium. From the repo root:
//   npm --prefix viewer ci          # installs playwright (a viewer devDep)
//   npx --prefix viewer playwright install chromium
//   node viewer/dev/render-ui-corpus.cjs
//
// Honors PLAYWRIGHT_BROWSERS_PATH if the browser lives outside the default cache.
const path = require('path');
const { chromium } = require('playwright');

const UI_DIR = path.resolve(__dirname, '..', '..', 'fixtures', 'corpus', 'ui');
const SRC_DIR = path.join(UI_DIR, '_src');

// One entry per source page: viewport + deviceScaleFactor (the "high-def" knob).
const PAGES = [
  { src: 'mobile-app-feed.html',     out: 'mobile-app-feed.png',     width: 390,  height: 844, dsf: 3 },
  { src: 'analytics-dashboard.html', out: 'analytics-dashboard.png', width: 1440, height: 900, dsf: 2 },
];

(async () => {
  const browser = await chromium.launch();
  for (const p of PAGES) {
    const page = await browser.newPage({
      viewport: { width: p.width, height: p.height },
      deviceScaleFactor: p.dsf,
    });
    const errs = [];
    page.on('pageerror', e => errs.push(e.message));
    await page.goto('file://' + path.join(SRC_DIR, p.src), { waitUntil: 'networkidle' });
    await page.waitForTimeout(400); // settle fonts/layout
    const outPath = path.join(UI_DIR, p.out);
    await page.screenshot({ path: outPath });
    const px = `${p.width * p.dsf}×${p.height * p.dsf}`;
    console.log(`  ${p.out.padEnd(26)} ${px.padStart(11)} px  @${p.dsf}x` +
                (errs.length ? `  [page errors: ${errs.slice(0, 3).join(' | ')}]` : ''));
    await page.close();
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
