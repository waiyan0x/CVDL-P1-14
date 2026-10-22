const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const {spawnSync} = require('node:child_process');
const AxeBuilder = require('@axe-core/playwright').default;

const root = path.resolve(__dirname, '../..');
const base = process.env.EDS_TEST_URL || 'http://127.0.0.1:8000';
const output = path.join(root, '.runtime');

async function assertResponsive(page, route) {
  for (const width of [320, 768, 1024, 1440]) {
    await page.setViewportSize({width, height: 1000});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false,
      `${route} overflows at ${width}px`);
  }
}

async function assertAccessible(page) {
  const report = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  assert.deepEqual(report.violations.map(v => `${v.id}: ${v.help}`), []);
}

function videoFixture() {
  fs.mkdirSync(output, {recursive: true});
  const result = spawnSync(path.join(root, '.venv/bin/python'), ['tests/browser/fixture.py'], {cwd: root, encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr);
  return path.join(output, 'test-still-video.avi');
}

module.exports = {assert, path, root, base, output, assertResponsive, assertAccessible, videoFixture};
