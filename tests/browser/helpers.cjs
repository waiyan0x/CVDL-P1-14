const assert = require('node:assert/strict');
const path = require('node:path');
const AxeBuilder = require('@axe-core/playwright').default;

const root = path.resolve(__dirname, '../..');
const base = process.env.EDS_TEST_URL || 'http://127.0.0.1:8000';
const output = path.join(root, '.runtime');
const uploadSample = path.join(root, 'data/samples/lighting-and-environment/dim-covered-interchange.jpg');

async function assertResponsive(page, route) {
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({width, height: 1000});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false,
      `${route} overflows at ${width}px`);
  }
}

async function assertAccessible(page) {
  const report = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  const failures = report.violations.flatMap(violation =>
    violation.nodes.map(node => `${violation.id}: ${node.target.join(' ')} (${node.failureSummary})`));
  assert.deepEqual(failures, []);
}

module.exports = {assert, path, root, base, output, uploadSample, assertResponsive, assertAccessible};
