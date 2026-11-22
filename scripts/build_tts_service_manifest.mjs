// Build the service-wording evaluation set: how a service code ending in a letter (63A, 92B, 10E)
// should be spoken. announcements-v2 found the spelled-out letter misheard ("6 3 A to" as "638",
// "10 E" as "10, east"). Every lettered route in the cleaned reference is announced four ways,
// with the same destination (as the app speaks it), so only the service wording differs:
//   spelled        Bus 6 3 A to Bishan M R T station.   (the app's wording when v2 was measured)
//   spelled_pause  Bus 6 3 A, to Bishan M R T station.
//   written        Bus 63A to Bishan M R T station.     (the voice reads the code itself)
//   written_pause  Bus 63A, to Bishan M R T station.
// All four are scored against the same meaning.
//
// Usage: node scripts/build_tts_service_manifest.mjs <out_dir>
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spokenPlace} from '../frontend/assets/js/core/bus-announcements.js';

const [outDir] = process.argv.slice(2);
if (!outDir) throw new Error('Usage: node scripts/build_tts_service_manifest.mjs <out_dir>');

const csv = readFileSync(new URL('../data/reference/bus_information.cleaned.csv', import.meta.url), 'utf8');
const seen = new Set();
const routes = csv.trim().split(/\r?\n/).slice(1).map(line => {
  const [service, , destination] = line.split(',');
  return {service: service.trim().toUpperCase(), destination: destination.trim()};
}).filter(({service, destination}) => /^[0-9]{1,3}[A-Z]{1,2}$/.test(service) && destination
  && !seen.has(service + destination) && seen.add(service + destination));

const spell = code => [...code].join(' ');
const wordings = {
  spelled: service => `Bus ${spell(service)} to`,
  spelled_pause: service => `Bus ${spell(service)}, to`,
  written: service => `Bus ${service} to`,
  written_pause: service => `Bus ${service}, to`,
};

const clipId = text => createHash('sha256').update(text).digest('hex').slice(0, 16);
const quote = value => `"${String(value).replaceAll('"', '""')}"`;
const lines = [['item_id', 'service', 'destination', 'group', 'condition', 'clip_id', 'text', 'reference'].join(',')];
const clips = new Map();
for (const [index, {service, destination}] of routes.entries()) {
  const place = spokenPlace(destination);
  const reference = `${wordings.spelled(service)} ${place}.`;
  for (const [condition, word] of Object.entries(wordings)) {
    const text = `${word(service)} ${place}.`;
    clips.set(clipId(text), text);
    lines.push([`s${String(index + 1).padStart(3, '0')}`, service, destination,
      /^[0-9]+A$/.test(service) ? 'suffix A' : 'other suffix', condition, clipId(text), text, reference].map(quote).join(','));
  }
}
mkdirSync(outDir, {recursive: true});
writeFileSync(`${outDir}/manifest.csv`, lines.join('\n') + '\n');
writeFileSync(`${outDir}/clips.csv`, ['clip_id,text', ...[...clips].map(([id, text]) => `${id},${quote(text)}`)].join('\n') + '\n');
console.log(`${routes.length} lettered routes x ${Object.keys(wordings).length} wordings; ${clips.size} unique clips -> ${outDir}`);
