const {assert, path, base, output, assertResponsive, assertAccessible} = require('./helpers.cjs');

module.exports = async function research(page) {
  await page.goto(`${base}/evaluation`);
  await page.locator('#compare:not([disabled])').waitFor();
  const response = page.waitForResponse(response => response.url().endsWith('/api/comparisons') && response.status() === 200);
  await page.getByRole('button', {name: 'Compare pipelines', exact: true}).click();
  const data = await (await response).json();
  assert.deepEqual(data.comparisons.map(item => item.backend), ['easyocr', 'tesseract', 'trocr']);
  assert.equal(data.comparisons.filter(item => item.status === 'success').length, 3);
  await page.locator('#comparison-results .field-card').first().waitFor();
  const text = await page.locator('#comparison-results').innerText();
  for (const name of ['EasyOCR', 'Tesseract', 'TrOCR']) assert.match(text, new RegExp(name));
  assert.match(await page.locator('#evaluation').innerText(), /13/);
  await assertResponsive(page, '/evaluation');
  await assertAccessible(page);
  await page.screenshot({path: path.join(output, 'evaluation-desktop.png'), fullPage: true});
  const ids = await page.locator('[id]').evaluateAll(nodes => nodes.map(node => node.id));
  assert.equal(new Set(ids).size, ids.length, 'Comparison columns must not duplicate DOM IDs.');
  await page.goto(`${base}/models`);
  await page.getByText('YOLO11n', {exact: false}).first().waitFor();
  assert.match(await page.locator('#models').innerText(), /best_v6.pt/);
  await assertResponsive(page, '/models');
  await assertAccessible(page);
  await page.screenshot({path: path.join(output, 'models-desktop.png'), fullPage: true});
  console.log('Evaluation/Models: real comparison, evidence, responsive and accessibility passed.');
};
