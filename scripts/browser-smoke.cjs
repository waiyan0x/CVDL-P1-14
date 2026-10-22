// Uses an isolated installed Chrome and a simulated camera against the local app.
const {chromium} = require('playwright');
const {assert, base} = require('../tests/browser/helpers.cjs');
const detect = require('../tests/browser/detect.cjs');
const live = require('../tests/browser/live.cjs');
const research = require('../tests/browser/research.cjs');
const failures = require('../tests/browser/failures.cjs');
(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true,
    args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream']});
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}, permissions: ['camera']});
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {if (message.type() === 'error') errors.push(message.text());});
    const ready = await context.request.get(`${base}/api/health`);
    assert.equal((await ready.json()).ready, true, 'Start the application before running browser tests.');
    await detect(page);
    await live(page);
    await research(page);
    assert.deepEqual(errors, [], 'Unexpected browser console/page errors.');
    await context.close();
    await failures(browser);
    console.log('Browser checks passed. Screenshots: .runtime/*-desktop.png and detect-mobile.png');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
