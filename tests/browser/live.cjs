const {assert, path, base, output, assertResponsive, assertAccessible} = require('./helpers.cjs');

// Live is camera only; the browser runs with a simulated camera (scripts/browser-smoke.cjs).
module.exports = async function live(page) {
  await page.goto(`${base}/live`);
  await page.locator('#options summary').waitFor();
  assert.equal(await page.getByRole('button', {name: 'Upload video', exact: true}).count(), 0);
  const first = page.waitForResponse(response => response.url().endsWith('/api/analysis') && response.status() === 200);
  await page.getByRole('button', {name: 'Start', exact: true}).click();
  const data = await (await first).json();
  assert.equal(data.frame.source, 'camera');
  assert.equal(typeof data.frame.frame_id, 'number');
  await page.locator('#viewer img').waitFor();
  await page.getByRole('button', {name: 'Stop', exact: true}).click();
  assert.match(await page.locator('#frame-label').innerText(), /Stopped/);
  assert.equal(await page.evaluate(() => document.getElementById('camera').srcObject), null);
  await assertResponsive(page, '/live');
  await assertAccessible(page);
  await page.screenshot({path: path.join(output, 'live-desktop.png'), fullPage: true});
  // The frame after Restart must come from the new session, not a late frame from the stopped one.
  const restarted = page.waitForResponse(async response =>
    response.url().endsWith('/api/analysis') &&
    response.status() === 200 &&
    (await response.json()).frame.session_id !== data.frame.session_id);
  await page.getByRole('button', {name: 'Restart', exact: true}).click();
  assert.equal((await (await restarted).json()).frame.source, 'camera');
  await page.getByRole('button', {name: 'Reset', exact: true}).click();
  assert.equal(await page.locator('#viewer').isVisible(), false);
  assert.equal(await page.evaluate(() => document.getElementById('camera').srcObject), null);
  console.log('Live: simulated camera, stop, restart and reset passed.');
};
