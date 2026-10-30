const {assert, path, root, base} = require('./helpers.cjs');

module.exports = async function failures(browser) {
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Simulate browser/device failures without touching the user's camera.
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException('Permission denied by test', 'NotAllowedError');
    };
  });
  await page.goto(`${base}/live`);
  await page.locator('#options summary').waitFor();
  await page.getByRole('button', {name: 'Start', exact: true}).click();
  await page.getByText(/Camera permission was denied/).waitFor();
  assert.equal(await page.locator('#start').isDisabled(), false);
  await page.getByRole('button', {name: 'Upload video', exact: true}).click();
  await page.locator('#video-file').setInputFiles({name: 'unsupported.mp4', mimeType: 'video/mp4', buffer: Buffer.from('not a real video')});
  await page.getByText('Video could not be opened', {exact: true}).waitFor();
  assert.equal(await page.locator('#viewer').isVisible(), false);

  await page.goto(`${base}/detect`);
  await page.waitForFunction(() => document.getElementById('status').textContent === 'Analysis complete.');
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let held;
  const heldResponse = new Promise(resolve => { held = resolve; });
  await page.route('**/api/analysis', async route => {
    const response = await route.fetch();
    held();
    await gate;
    await route.fulfill({response});
  });
  await page.getByRole('button', {name: 'Upload image', exact: true}).click();
  await page.locator('#image-file').setInputFiles(path.join(root, 'data/images/test/0c7ddfa8-27d65774-133.jpg'));
  await heldResponse;
  await page.getByRole('button', {name: 'Reset', exact: true}).click();
  const delivered = page.waitForResponse(response => response.url().endsWith('/api/analysis'));
  release();
  await (await delivered).finished();
  await page.waitForFunction(() => !document.getElementById('results').hasAttribute('aria-busy'));
  assert.equal(await page.locator('#viewer').isVisible(), false);
  assert.doesNotMatch(await page.locator('#results').innerText(), /133/);
  assert.match(await page.locator('#status').innerText(), /Reset complete/);
  await page.unroute('**/api/analysis');
  assert.deepEqual(errors, [], 'Failure handling must not cause uncaught errors.');
  await context.close();
  console.log('Failure lifecycle: camera denial, invalid video and delayed-result reset passed.');
};
