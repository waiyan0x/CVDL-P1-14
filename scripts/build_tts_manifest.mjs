// Build the spoken-announcement evaluation set from the cleaned route reference.
//
// Each route is announced the way the matcher words a confirmed service and destination
// (backend/app/services/announcement.py: "Bus 174 to Kampong Bahru Bus Terminal."), twice:
//   raw         the matcher message passed straight to speech synthesis;
//   normalised  the same message through spokenAnnouncement (what the app speaks:
//               service spelled out, abbreviations expanded, acronyms spelled).
// Both are scored against the same meaning (the normalised text), so the comparison
// isolates the text clean-up. Routes whose destination spokenPlace leaves unchanged are
// sampled as controls: there only the service wording differs ("174" vs "1 7 4").
// Identical texts share one audio clip.
//
// Usage: node scripts/build_tts_manifest.mjs <out_dir> [controls=60]
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spokenAnnouncement, spokenPlace} from '../frontend/assets/js/core/bus-announcements.js';

const [outDir, controlArg = '60'] = process.argv.slice(2);
if (!outDir) throw new Error('Usage: node scripts/build_tts_manifest.mjs <out_dir> [controls]');
const controls = Number(controlArg);

// The matcher returns reference names from the cleaned table (data/reference/README.md).
// Named shuttles ("Giant/IKEA Bedok") are not codes a display shows, so they are left out.
const csv = readFileSync(new URL('../data/reference/bus_information.cleaned.csv', import.meta.url), 'utf8');
const rows = csv.trim().split(/\r?\n/).slice(1).map(line => {
  const [service, , destination] = line.split(',');
  return {service: service.trim(), destination: destination.trim()};
}).filter(row => /^[A-Z]{0,3}[0-9]{1,3}[A-Z]{0,2}$/i.test(row.service) && row.destination);

// Deterministic sample of unchanged rows, so reruns pick the same controls.
const rank = text => createHash('sha256').update(text).digest('hex');
const seen = new Set();
const items = rows.filter(({service, destination}) => !seen.has(service + destination) && seen.add(service + destination))
  .map(({service, destination}) => {
    const raw = `Bus ${service} to ${destination}.`;
    const normalised = spokenAnnouncement({service, destination, announcement: raw});
    return {service, destination, raw, normalised, changed: spokenPlace(destination) !== destination};
  });
const changed = items.filter(item => item.changed);
const unchanged = items.filter(item => !item.changed)
  .sort((a, b) => rank(a.service + a.destination).localeCompare(rank(b.service + b.destination)))
  .slice(0, controls);

const clipId = text => rank(text).slice(0, 16);
const quote = value => `"${String(value).replaceAll('"', '""')}"`;
const header = ['item_id', 'service', 'destination', 'group', 'condition', 'clip_id', 'text', 'reference'];
const lines = [header.join(',')];
const clips = new Map();
for (const [index, item] of [...changed, ...unchanged].entries()) {
  for (const condition of ['raw', 'normalised']) {
    const text = item[condition];
    clips.set(clipId(text), text);
    lines.push([`r${String(index + 1).padStart(3, '0')}`, item.service, item.destination,
      item.changed ? 'changed' : 'control', condition, clipId(text), text, item.normalised].map(quote).join(','));
  }
}
mkdirSync(outDir, {recursive: true});
writeFileSync(`${outDir}/manifest.csv`, lines.join('\n') + '\n');
writeFileSync(`${outDir}/clips.csv`, ['clip_id,text', ...[...clips].map(([id, text]) => `${id},${quote(text)}`)].join('\n') + '\n');
console.log(`${changed.length} changed + ${unchanged.length} control routes; ${clips.size} unique clips -> ${outDir}`);
