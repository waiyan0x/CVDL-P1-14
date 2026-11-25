// Scores responses.jsonl (from run_eval.py) with the app's own guiding prompt and announcement logic.
// Usage: node evaluation/guiding_prompts/score.mjs
import {readFileSync, writeFileSync} from 'node:fs';
import {NO_SIGN_MS, aimingHint, nearestSign} from '../../frontend/assets/js/core/aiming.js';
import {busAnnouncement} from '../../frontend/assets/js/core/bus-announcements.js';

const here = new URL('.', import.meta.url);
const records = readFileSync(new URL('responses.jsonl', here), 'utf8').trim().split('\n').map(line => JSON.parse(line));

// The service the app read on the untouched photo (largest display), used to check reads in each frame.
const services = {};
for (const record of records.filter(r => r.scenario === 'original')) {
  const results = record.response.results.filter(r => r.screen?.box);
  const area = ({screen: {box: b}}) => (b[2] - b[0]) * (b[3] - b[1]);
  services[record.image] = results.sort((a, b) => area(b) - area(a))[0]?.match?.service ?? null;
}

const rows = [];
for (const record of records.filter(r => r.scenario !== 'original')) {
  const data = record.response;
  const detected = !!nearestSign(data);
  const code = aimingHint(data, {sinceSignMs: detected ? 0 : NO_SIGN_MS})?.code ?? null;
  const fieldsOnly = detected && !data.results.some(r => r.screen?.box);
  let outcome;
  if (code === record.expected) outcome = 'correct';
  else if (!detected) outcome = 'sign missed';           // Heard as "No bus sign in view" after 5 s.
  else if (code === null) outcome = 'no prompt';
  else outcome = `wrong: ${code}`;
  const service = services[record.image];
  const read = !!busAnnouncement(data, {confirmedOnly: true});
  const readService = !!service && data.results.some(r => r.match?.service === service);
  rows.push({image: record.image, scenario: record.scenario, expected: record.expected ?? '', code: code ?? '',
    outcome, detected, fieldsOnly, read, readService, hasService: !!service});
}

writeFileSync(new URL('results.csv', here), [Object.keys(rows[0]).join(','),
  ...rows.map(row => Object.values(row).map(v => /[,"]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : v).join(','))].join('\n') + '\n');

const pct = (part, whole) => whole ? `${Math.round(100 * part / whole)}%` : '–';
const order = [...new Set(rows.map(r => r.scenario))];
const lines = ['| Situation | Expected prompt | Frames | Correct prompt | Sign missed | No prompt | Wrong prompt | Bus still read |',
  '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |'];
for (const scenario of order) {
  const group = rows.filter(r => r.scenario === scenario);
  const count = test => group.filter(test).length;
  const wrong = [...new Set(group.filter(r => r.outcome.startsWith('wrong')).map(r => r.code))];
  const withService = group.filter(r => r.hasService);
  lines.push(`| ${scenario} | ${group[0].expected || 'none needed'} | ${group.length} | ${pct(count(r => r.outcome === 'correct'), group.length)}`
    + ` | ${pct(count(r => r.outcome === 'sign missed'), group.length)} | ${pct(count(r => r.outcome === 'no prompt'), group.length)}`
    + ` | ${pct(count(r => r.outcome.startsWith('wrong')), group.length)}${wrong.length ? ` (${wrong.join(', ')})` : ''}`
    + ` | ${pct(withService.filter(r => r.readService).length, withService.length)} |`);
}
writeFileSync(new URL('summary-table.md', here), lines.join('\n') + '\n');
console.log(lines.join('\n'));
console.log(`\n${new Set(rows.map(r => r.image)).size} images, ${rows.length} frames; `
  + `${rows.filter(r => r.fieldsOnly).length} frames placed from field boxes only.`);
