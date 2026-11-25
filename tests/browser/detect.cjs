const {assert, path, base, output, uploadSample, assertResponsive, assertAccessible} = require('./helpers.cjs');

module.exports = async function detect(page) {
  await page.goto(`${base}/detect`);
  await page.waitForFunction(() => document.getElementById('status').textContent === 'Analysis complete.');
  assert.match(await page.locator('#results').innerText(), /OCR reads/);
  assert.equal(await page.locator('nav a[aria-current="page"]').innerText(), 'Detect');
  await assertAccessible(page);
  await assertResponsive(page, '/detect');
  await page.screenshot({path: path.join(output, 'detect-desktop.png'), fullPage: true});
  await page.setViewportSize({width: 320, height: 950});
  await page.screenshot({path: path.join(output, 'detect-mobile.png'), fullPage: true});
  await page.setViewportSize({width: 1440, height: 1000});

  await page.getByRole('button', {name: 'Upload image', exact: true}).click();
  await page.locator('#image-file').setInputFiles(uploadSample);
  await page.waitForFunction(() => document.getElementById('status').textContent === 'Analysis complete.');
  await page.getByText('OCR reads 16', {exact: true}).waitFor();
  await page.getByRole('button', {name: 'Reset', exact: true}).click();
  assert.equal(await page.locator('#viewer').isVisible(), false);
  assert.equal(await page.getByText('OCR reads 16', {exact: true}).count(), 0);

  await page.getByRole('button', {name: 'Snapshot', exact: true}).click();
  await page.getByRole('button', {name: 'Open camera', exact: true}).click();
  await page.locator('#capture:not([disabled])').waitFor();
  await page.getByRole('button', {name: 'Capture image', exact: true}).click();
  await page.waitForFunction(() => document.getElementById('status').textContent === 'Analysis complete.');
  assert.equal(await page.evaluate(() => document.getElementById('camera').srcObject), null);
  console.log('Detect: samples, upload, snapshot, reset, responsive and accessibility passed.');
};
