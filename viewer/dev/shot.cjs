const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1440, height: 880 }, deviceScaleFactor: 2 });
  const errs = [];
  pg.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
  pg.on('pageerror', e => errs.push('PAGEERR: '+e.message));
  await pg.goto('file://' + __dirname + '/harness.html', { waitUntil: 'networkidle' });
  await pg.waitForTimeout(2500); // fonts + fit measurement
  const shots = [
    { name: 'slide01', idx: 0 },
    { name: 'slide05_palette', idx: 4 },
    { name: 'slide06_type', idx: 5 },
    { name: 'slide08_ui', idx: 7 },
    { name: 'slide11_components', idx: 10 },
  ];
  // navigate via keyboard Home then ArrowRight idx times
  for (const s of shots) {
    await pg.keyboard.press('Home');
    await pg.waitForTimeout(150);
    for (let i=0;i<s.idx;i++){ await pg.keyboard.press('ArrowRight'); await pg.waitForTimeout(60); }
    await pg.waitForTimeout(900);
    await pg.screenshot({ path: `shot_${s.name}.png` });
  }
  console.log('ERRORS:', errs.length ? errs.slice(0,8).join(' | ') : 'none');
  await b.close();
})();
