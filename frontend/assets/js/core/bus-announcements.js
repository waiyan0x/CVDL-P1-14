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

// How a service is said. Numbers and lettered shuttles are spelled out ("1 7 4", "C W 1"). A number
// ending in a letter is left for the voice to read ("63A": "sixty-three A"), with a pause before "to":
// spelled out and run into "to", the letter was misheard ("6 3 A to" as "638", "10 E" as "10 east").
// Measured in evaluation/tts/README.md (service-wording-v3).
function spokenService(service, next) {
  return /^[0-9]+[A-Z]+$/.test(service) ? `${service}${next ? ',' : ''}${next}` : `${spell(service)}${next}`;
}

// The matcher's one-line message (match.announcement, backend/app/services/announcement.py) states only
// what was confirmed. For speech, the service is said as spokenService describes ("Bus 1 7 4 to",
// "Bus 63A, to") and the destination and the "via" road are read as words ("Kampong Bahru Bus
// Terminal, via Corporation Road").
export function spokenAnnouncement(match) {
  let text = String(match?.announcement ?? '').trim();
  if (!text) return '';
  const service = serviceId(match.service);
  if (service) text = text.replace(new RegExp(`^Bus ${service}\\b( to\\b)?`), (_, to = '') => `Bus ${spokenService(service, to)}`);
  // The road first: a spoken destination can itself contain ", via" (Siglap Road ..., via Tomlinson Road).
  text = text.replace(/, via ([^.]+)\./, (_, via) => `, via ${spokenPlace(via)}.`);
  return match.destination ? text.replace(`to ${match.destination}`, `to ${spokenPlace(match.destination)}`) : text;
}

// Mandarin wording of the matcher's message, built from its confirmed service and destination. The six message
// shapes come from build_announcement (backend/app/services/announcement.py). Place and road names stay in
// English, as the reference only has English names and Singapore Mandarin announcements say them that way.
export function chineseAnnouncement(match) {
  const text = String(match?.announcement ?? '').trim();
  if (!text) return '';
  if (/^Bus not in service\b/.test(text)) return '这辆巴士不载客。';
  const service = serviceId(match.service);
  const destination = match.destination ? spokenPlace(match.destination) : '';
  const road = (match.destination ? text.replace(match.destination, '') : text).match(/, via ([^.]+)\./)?.[1];
  const via = road ? `，途经${spokenPlace(road)}` : '';
  const reason = /could not be confirmed/.test(text) ? '无法确认' : '无法识别';
  if (service && destination) return `${service}号巴士，开往${destination}${via}。`;
  if (service) return `${service}号巴士即将到站${via}。终点站${reason}。`;
  if (destination) return `开往${destination}的巴士即将到站${via}。车号${reason}。`;
  return `有一辆巴士即将到站${via}。车号和终点站${reason}。`;
}

// Fixed phrases the app speaks besides announcements: Read result aloud fallbacks, the automatic
// announcements confirmation and the aiming hints (core/aiming.js).
const PHRASES = {
  zh: {
    'No bus display detected.': '没有检测到巴士显示屏。',
    'Could not read the bus display.': '无法读取巴士显示屏。',
    'Automatic bus announcements enabled.': '已开启自动巴士播报。',
    'No bus sign in view.': '画面中没有巴士显示屏。',
    'Sign cut off on the left. Turn slightly left.': '显示屏左边被切掉了。请稍微向左转。',
    'Sign cut off on the right. Turn slightly right.': '显示屏右边被切掉了。请稍微向右转。',
    'Sign cut off at the top. Tilt up slightly.': '显示屏上方被切掉了。请稍微向上倾斜。',
    'Sign cut off at the bottom. Tilt down slightly.': '显示屏下方被切掉了。请稍微向下倾斜。',
    'Sign fills the view. Step back or zoom out.': '显示屏占满了画面。请后退一步或缩小画面。',
    'Bus sign is small. The bus may still be far away.': '巴士显示屏很小。巴士可能还很远。',
  },
};

export function localPhrase(text, language = 'en') {
  return PHRASES[language]?.[text] ?? text;
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
// language 'zh' gives the Mandarin wording (chineseAnnouncement).
export function busAnnouncement(data, {distance = null, confirmedOnly = false, language = 'en'} = {}) {
  const zh = language === 'zh';
  const results = [...data?.results ?? []].sort((a, b) => area(b) - area(a));
  const phrases = [];
  for (const result of results) {
    if (confirmedOnly && !confirmed(result.match)) continue;
    const text = zh ? chineseAnnouncement(result.match) : spokenAnnouncement(result.match);
    if (text && !phrases.includes(text)) phrases.push(text);
  }
  if (!phrases.length) return null;
  if (distance !== null && results.length === 1 && serviceId(results[0].match?.service)) {
    phrases[0] += zh ? `距离大约${distance}米。` : ` About ${distance} metres away.`;
  }
  const more = phrases.length > 3 ? (zh ? '屏幕上还有更多结果。' : ' More readings are on screen.') : '';
  return phrases.slice(0, 3).join(zh ? '' : ' ') + more;
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
