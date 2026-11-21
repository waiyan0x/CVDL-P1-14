const SERVICE = /^[0-9]{1,3}[A-Z]{0,2}$/;

// Abbreviations found in the route reference table (data/bus_information.csv).
// Single letters are left alone: "Exit B" and "Park B" are names, not abbreviations.
const ABBREVIATIONS = {
  Aft: 'After', Ave: 'Avenue', Bef: 'Before', Bet: 'Between', Bldg: 'Building', Blk: 'Block',
  Checkpt: 'Checkpoint', Coll: 'College', Corp: 'Corporation', Ctrl: 'Central', Dr: 'Drive',
  Hosp: 'Hospital', Int: 'Interchange', Intl: 'International', Lor: 'Lorong', Nth: 'North',
  Opp: 'Opposite', Pk: 'Park', Pl: 'Place', Pri: 'Primary', Rd: 'Road', Sch: 'School',
  Sq: 'Square', St: 'Street', Stn: 'Station', Ter: 'Terminal',
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

// Recognise only service-shaped OCR that meets the threshold used for this frame.
function serviceId(value) {
  const code = String(value ?? '').toUpperCase().replace(/\s+/g, '');
  return SERVICE.test(code) ? code : '';
}

export function busAnnouncement(data, threshold, distance = null) {
  const phrases = new Set();
  for (const result of data?.results ?? []) {
    const matchedService = serviceId(result.match?.service);
    const field = result.fields?.bus_number;
    const rawService = typeof field?.ocr_confidence === 'number' && field.ocr_confidence >= threshold
      ? serviceId(field.raw) : '';
    const service = matchedService || rawService;
    if (!service) continue;
    const number = [...service].join(' ');
    const estimate = distance !== null && data.results.length === 1 ? `, about ${distance} metres away` : '';
    const endpoint = result.match?.status === 'matched' ? spokenPlace(result.match.endpoint) : '';
    phrases.add(`${matchedService ? 'Bus service' : 'Possible bus service'} ${number}${estimate}.`
      + (endpoint ? ` Reference destination: ${endpoint}.` : ''));
  }
  if (!phrases.size) return null;
  const readings = [...phrases].sort();
  return readings.slice(0, 3).join(' ') + (readings.length > 3 ? ' More readings are on screen.' : '');
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
