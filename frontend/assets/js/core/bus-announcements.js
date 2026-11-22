// Service codes: 174, 92B, 851e, and the lettered shuttles in the reference (CW1, LCS1, TS8).
const SERVICE = /^[A-Z]{0,3}[0-9]{1,3}[A-Z]{0,2}$/;

// Abbreviations found in the route reference table (data/bus_information.csv) and in the
// road names the matcher passes on from the route line of a display ("via Upp Serangoon Rd").
// Single letters are left alone: "Exit B" and "Park B" are names, not abbreviations.
const ABBREVIATIONS = {
  Aft: 'After', Ave: 'Avenue', Bef: 'Before', Bet: 'Between', Biz: 'Business', Bkt: 'Bukit',
  Bldg: 'Building', Blk: 'Block', Blvd: 'Boulevard', Bt: 'Bukit', Checkpt: 'Checkpoint', Cir: 'Circle',
  Cl: 'Close', Coll: 'College', Corp: 'Corporation', Cres: 'Crescent', Ctr: 'Centre', Ctrl: 'Central',
  Dr: 'Drive', Gdn: 'Garden', Gdns: 'Gardens', Hosp: 'Hospital', Hts: 'Heights', Ind: 'Industrial',
  Int: 'Interchange', Intl: 'International', Jct: 'Junction', Jln: 'Jalan', Kg: 'Kampong', Ln: 'Lane',
  Lor: 'Lorong', Nth: 'North', Opp: 'Opposite', Pk: 'Park', Pl: 'Place', Pri: 'Primary', Rd: 'Road',
  Sch: 'School', Sec: 'Secondary', Sq: 'Square', St: 'Street', Sth: 'South', Stn: 'Station',
  Ter: 'Terminal', Tg: 'Tanjong', Upp: 'Upper',
};
// Capitalised names that are said as words; other capitals (MRT, SUTD) are spelled out.
const SPOKEN_AS_WORDS = new Set(['ALPS', 'IKEA']);

const spell = code => [...code].join(' ');

// Rewrite a reference place name so speech synthesis reads it as a commuter would say it.
export function spokenPlace(value) {
  return String(value ?? '')
    .replace(/\bSt\.(?=\s+[A-Z])/g, 'Saint')
    // Block numbers are read digit by digit: "Blk 318A/318B" -> "Block 3 1 8 A and 3 1 8 B".
    .replace(/\b(?:Blk|Block)\s+(\d+[A-Z]?(?:\s*\/\s*\d+[A-Z]?)*)\b/g,
      (_, codes) => `Block ${codes.split('/').map(code => spell(code.trim())).join(' and ')}`)
    .replace(/\b([A-Z][a-z]+)\b\.?/g, (word, stem) => ABBREVIATIONS[stem] ?? word)
    .replace(/\b[A-Z]{2,5}\b/g, word => SPOKEN_AS_WORDS.has(word) ? word : spell(word))
    .replace(/\s*\/\s*loop\s*$/i, ' (loop)')
    .replace(/\(\s*loop\s*\)/gi, '(loop service)')
    .replace(/\s*\(([^)]*)\)\s*/g, ', $1, ')
    .replace(/\s*\/\s*/g, ' and ')
    .replace(/\s*,(\s*,)+/g, ',')
    .replace(/[\s,]+$/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function serviceId(value) {
  const code = String(value ?? '').toUpperCase().replace(/\s+/g, '');
  return SERVICE.test(code) ? code : '';
}

// The matcher's one-line message (match.announcement, backend/app/services/announcement.py) states only
// what was confirmed. For speech, the service is spelled out ("Bus 1 7 4") and the destination and the
// "via" road are read as words ("Kampong Bahru Bus Terminal, via Corporation Road").
export function spokenAnnouncement(match) {
  let text = String(match?.announcement ?? '').trim();
  if (!text) return '';
  const service = serviceId(match.service);
  if (service) text = text.replace(new RegExp(`^Bus ${service}\\b`), `Bus ${spell(service)}`);
  // The road first: a spoken destination can itself contain ", via" (Siglap Road ..., via Tomlinson Road).
  text = text.replace(/, via ([^.]+)\./, (_, via) => `, via ${spokenPlace(via)}.`);
  return match.destination ? text.replace(`to ${match.destination}`, `to ${spokenPlace(match.destination)}`) : text;
}

// A confirmed service or destination, or a bus marked not in service.
function confirmed(match) {
  return !!(serviceId(match?.service) || match?.destination || /^Bus not in service\b/.test(match?.announcement ?? ''));
}

function area(result) {
  const boxes = result.screen?.box ? [result.screen.box] : Object.values(result.fields ?? {}).map(field => field.box);
  const [left, top, right, bottom] = boxes.filter(Boolean).reduce((union, box) => [Math.min(union[0], box[0]),
    Math.min(union[1], box[1]), Math.max(union[2], box[2]), Math.max(union[3], box[3])], [Infinity, Infinity, -Infinity, -Infinity]);
  return right > left && bottom > top ? (right - left) * (bottom - top) : 0;
}

// Up to three displays, largest (nearest) first. confirmedOnly leaves out displays where nothing was
// confirmed, so automatic announcements do not repeat "could not be read" for every passing frame.
export function busAnnouncement(data, {distance = null, confirmedOnly = false} = {}) {
  const results = [...data?.results ?? []].sort((a, b) => area(b) - area(a));
  const phrases = [];
  for (const result of results) {
    if (confirmedOnly && !confirmed(result.match)) continue;
    const text = spokenAnnouncement(result.match);
    if (text && !phrases.includes(text)) phrases.push(text);
  }
  if (!phrases.length) return null;
  if (distance !== null && results.length === 1 && serviceId(results[0].match?.service)) {
    phrases[0] += ` About ${distance} metres away.`;
  }
  return phrases.slice(0, 3).join(' ') + (phrases.length > 3 ? ' More readings are on screen.' : '');
}

export function cameraObservation(data, zoom = null, now = Date.now()) {
  const frame = data?.frame;
  if (frame?.source !== 'camera' || !frame.session_id || data.results?.length !== 1) return null;
  const age = now - Date.parse(frame.captured_at);
  if (!Number.isFinite(age) || age < 0 || age > 3500) return null;
  const {screen, match} = data.results[0];
  const service = serviceId(match?.service);
  const {width, height} = data;
  if (!service || screen?.source !== 'model' || screen.label !== 'eds' || !screen.box?.every(Number.isFinite)
      || !Number.isFinite(width) || !Number.isFinite(height)) return null;
  const [left, top, right, bottom] = screen.box;
  const panelWidth = right - left;
  const panelHeight = bottom - top;
  if (left < 2 || top < 2 || right > width - 2 || bottom > height - 2 || panelWidth < 24 || panelHeight < 8) return null;
  return {session: frame.session_id, service, width, height, zoom, scale: panelWidth / width,
    aspect: panelWidth / panelHeight};
}

export function estimateMetres(reference, current) {
  if (!reference || !current || reference.session !== current.session || reference.service !== current.service
      || reference.width !== current.width || reference.height !== current.height || reference.zoom !== current.zoom) return null;
  const aspectRatio = current.aspect / reference.aspect;
  const scaleRatio = reference.scale / current.scale;
  // Inverse apparent width assumes the same panel and comparable viewing angle.
  if (aspectRatio < .8 || aspectRatio > 1.25 || scaleRatio < .5 || scaleRatio > 2) return null;
  const distance = reference.metres * scaleRatio;
  return distance >= 5 && distance <= 100 ? Math.round(distance / 5) * 5 : null;
}

export class AnnouncementGate {
  constructor(delay = 6000) {
    this.delay = delay;
    this.reset();
  }

  reset() {
    this.candidate = null;
    this.consecutive = 0;
    this.last = null;
    this.lastAt = -Infinity;
  }

  ready(text, now) {
    this.consecutive = text === this.candidate ? this.consecutive + 1 : 1;
    this.candidate = text;
    return !!text && this.consecutive >= 2 && text !== this.last && now - this.lastAt >= this.delay;
  }

  announced(text, now) {
    this.last = text;
    this.lastAt = now;
  }
}
