import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {AnnouncementGate, busAnnouncement, cameraObservation, chineseAnnouncement, estimateMetres, localPhrase,
  spokenAnnouncement, spokenPlace}
  from '../../frontend/assets/js/core/bus-announcements.js';

const captured = Date.parse('2026-11-21T00:00:00Z');
function result({panel = [120, 110, 300, 146], source = 'camera'} = {}) {
  return {
    frame: {source, session_id: 'stream-one', captured_at: new Date(captured).toISOString()},
    width: 1280, height: 720,
    results: [{
      fields: {bus_number: {raw: '92B', ocr_confidence: .9}},
      match: {service: '92B', status: 'matched', endpoint: 'Ghim Moh Terminal', destination: 'Ghim Moh Terminal',
        announcement: 'Bus 92B to Ghim Moh Terminal.'},
      screen: {label: 'eds', source: 'model', box: panel},
    }],
  };
}

test('reads the matcher message with the service spoken clearly and places as words', () => {
  const frame = result();
  assert.equal(busAnnouncement(frame), 'Bus 92B, to Ghim Moh Terminal.');
  assert.equal(busAnnouncement(frame, {distance: 30}), 'Bus 92B, to Ghim Moh Terminal. About 30 metres away.');
  const cases = [
    [{service: '174', destination: 'Kampong Bahru Bus Terminal',
      announcement: 'Bus 174 to Kampong Bahru Bus Terminal, via Corporation Rd.'},
     'Bus 1 7 4 to Kampong Bahru Bus Terminal, via Corporation Road.'],
    [{service: '64', destination: null, announcement: 'Bus 64 is approaching. Destination could not be read.'},
     'Bus 6 4 is approaching. Destination could not be read.'],
    [{service: null, destination: 'Hougang Central Bus Interchange',
      announcement: 'A bus to Hougang Central Bus Interchange is approaching, via Upp Serangoon Rd. Bus number could not be confirmed.'},
     'A bus to Hougang Central Bus Interchange is approaching, via Upper Serangoon Road. Bus number could not be confirmed.'],
    [{service: '3A', destination: 'Pasir Ris Drive 12 (Blk 747A)', announcement: 'Bus 3A to Pasir Ris Drive 12 (Blk 747A).'},
     'Bus 3A, to Pasir Ris Drive 12, Block 7 4 7 A.'],
    [{service: '851E', destination: null, announcement: 'Bus 851E is approaching. Destination could not be read.'},
     'Bus 851E is approaching. Destination could not be read.'],
    [{service: '16', destination: 'Siglap Road (Bef Seaside Residences) via Tomlinson Road',
      announcement: 'Bus 16 to Siglap Road (Bef Seaside Residences) via Tomlinson Road, via Bishan MRT.'},
     'Bus 1 6 to Siglap Road, Before Seaside Residences, via Tomlinson Road, via Bishan M R T.'],
    [{service: null, destination: null, announcement: 'Bus not in service.'}, 'Bus not in service.'],
    [{service: null, destination: null, announcement: null}, ''],
  ];
  for (const [match, spoken] of cases) assert.equal(spokenAnnouncement(match), spoken, match.announcement);
});

test('automatic announcements leave out displays where nothing was confirmed', () => {
  const frame = result();
  frame.results[0].match = {service: null, destination: null, status: 'unmatched',
    announcement: 'A bus is approaching. Bus number and destination could not be confirmed.'};
  assert.equal(busAnnouncement(frame), 'A bus is approaching. Bus number and destination could not be confirmed.');
  assert.equal(busAnnouncement(frame, {confirmedOnly: true}), null);
  frame.results[0].match = {service: null, destination: null, announcement: 'Bus not in service.'};
  assert.equal(busAnnouncement(frame, {confirmedOnly: true}), 'Bus not in service.');
  frame.results[0].match = {service: null, destination: null, announcement: null};
  assert.equal(busAnnouncement(frame), null);
});

test('reads the nearest (largest) display first and no distance for several buses', () => {
  const frame = result();
  const far = structuredClone(frame.results[0]);
  far.screen.box = [600, 100, 660, 112];
  far.match = {service: '176', destination: null, announcement: 'Bus 176 is approaching. Destination could not be read.'};
  frame.results.unshift(far);
  assert.equal(busAnnouncement(frame, {distance: 30}),
    'Bus 92B, to Ghim Moh Terminal. Bus 1 7 6 is approaching. Destination could not be read.');
});

test('reads reference destinations as a commuter would say them', () => {
  const cases = {
    'Pasir Ris Drive 12 (Blk 747A)': 'Pasir Ris Drive 12, Block 7 4 7 A',
    'Yishun Ave 5 (Opp Yishun Stn Exit B)': 'Yishun Avenue 5, Opposite Yishun Station Exit B',
    'Upper Changi MRT station / SUTD': 'Upper Changi M R T station and S U T D',
    'Choa Chu Kang MRT/LRT station': 'Choa Chu Kang M R T and L R T station',
    'Kovan Hub (Hougang Street 21) (loop)': 'Kovan Hub, Hougang Street 21, loop service',
    'Siglap Road (Bef Seaside Residences) via Tomlinson Road': 'Siglap Road, Before Seaside Residences, via Tomlinson Road',
    'Yishun Avenue 6 (Bet Blk 318A/318B)': 'Yishun Avenue 6, Between Block 3 1 8 A and 3 1 8 B',
    'Tampines Avenue 10 (IKEA Tampines)': 'Tampines Avenue 10, IKEA Tampines',
    'St. Wilfred Road (loop)': 'Saint Wilfred Road, loop service',
    'Woodlands St 83': 'Woodlands Street 83',
    'Senoko Road/Loop': 'Senoko Road, loop service',
    'Kranji Reservoir Park B (loop)': 'Kranji Reservoir Park B, loop service',
    'Ghim Moh Terminal': 'Ghim Moh Terminal',
  };
  for (const [place, spoken] of Object.entries(cases)) assert.equal(spokenPlace(place), spoken, place);
  const roads = {'Upp Serangoon Rd': 'Upper Serangoon Road', 'Jln Besar': 'Jalan Besar', 'Bt Batok St 11': 'Bukit Batok Street 11',
    'Ang Mo Kio Ind Pk 2': 'Ang Mo Kio Industrial Park 2', 'Kg Bahru Rd': 'Kampong Bahru Road', 'Yishun Ring Rd': 'Yishun Ring Road'};
  for (const [road, spoken] of Object.entries(roads)) assert.equal(spokenPlace(road), spoken, road);
});

test('leaves no symbols, unspelled acronyms or known abbreviations in any reference place', () => {
  const places = new Set();
  // The original table and the cleaned one the matcher reads its names from.
  for (const file of ['../../data/bus_information.csv', '../../data/reference/bus_information.cleaned.csv']) {
    const csv = readFileSync(new URL(file, import.meta.url), 'utf8');
    csv.trim().split(/\r?\n/).slice(1).forEach(row => row.split(',').slice(1, 3).forEach(place => places.add(place)));
  }
  for (const place of places) {
    const spoken = spokenPlace(place);
    assert.doesNotMatch(spoken, /[/()]|\b(?!IKEA\b|ALPS\b)[A-Z]{2,}\b/, place);
    assert.doesNotMatch(spoken, /\b(?:Aft|Ave|Bef|Bet|Bldg|Blk|Opp|Pk|Rd|St|Stn|Ctrl|Nth|Int|Ter)\b/, place);
  }
});

test('uses projected sign width and withholds estimates across camera changes', () => {
  const reference = {...cameraObservation(result(), 1, captured), metres: 20};
  const narrower = cameraObservation(result({panel: [120, 110, 240, 134]}), 1, captured);
  assert.equal(estimateMetres(reference, narrower), 30);
  for (const change of [{session: 'stream-two'}, {service: '3'}, {zoom: 2},
    {width: 640}, {aspect: 2}, {scale: .001}]) {
    assert.equal(estimateMetres(reference, {...narrower, ...change}), null);
  }
});

test('only a recent, single, unclipped model-detected sign qualifies', () => {
  const frame = result();
  assert.equal(cameraObservation(frame, 1, captured + 3600), null);
  assert.equal(cameraObservation(result({source: 'video'}), 1, captured), null);
  assert.equal(cameraObservation(result({panel: [0, 110, 180, 146]}), 1, captured), null);
  frame.results[0].screen.source = 'field_union';
  assert.equal(cameraObservation(frame, 1, captured), null);
  frame.results.push(result().results[0]);
  assert.equal(cameraObservation(frame, 1, captured), null);
  assert.doesNotMatch(busAnnouncement(frame, {distance: 30}), /metres/);
});

test('live announcements stabilise, deduplicate, and respect cooldown and stop', () => {
  const gate = new AnnouncementGate();
  assert.equal(gate.ready('176', 0), false);
  assert.equal(gate.ready('92B', 500), false);
  assert.equal(gate.ready('176', 1000), false);
  assert.equal(gate.ready('176', 1500), true);
  gate.announced('176', 1500);
  assert.equal(gate.ready('176', 8000), false);
  assert.equal(gate.ready('92B', 2000), false);
  assert.equal(gate.ready('92B', 3000), false);
  assert.equal(gate.ready('92B', 7500), true);
  gate.reset();
  assert.equal(gate.ready('92B', 8000), false);
});

test('spells lettered shuttle codes like bus numbers', () => {
  assert.equal(spokenAnnouncement({service: 'CW1', destination: 'Kranji MRT station',
    announcement: 'Bus CW1 to Kranji MRT station.'}), 'Bus C W 1 to Kranji M R T station.');
});

test('Chinese voice: Mandarin wording with English place names', () => {
  const frame = result();
  assert.equal(busAnnouncement(frame, {language: 'zh'}), '92B号巴士，开往Ghim Moh Terminal。');
  assert.equal(busAnnouncement(frame, {language: 'zh', distance: 30}), '92B号巴士，开往Ghim Moh Terminal。距离大约30米。');
  const cases = [
    [{service: '174', destination: 'Kampong Bahru Bus Terminal',
      announcement: 'Bus 174 to Kampong Bahru Bus Terminal, via Corporation Rd.'},
     '174号巴士，开往Kampong Bahru Bus Terminal，途经Corporation Road。'],
    [{service: '64', destination: null, announcement: 'Bus 64 is approaching. Destination could not be read.'},
     '64号巴士即将到站。终点站无法识别。'],
    [{service: '64', destination: null, announcement: 'Bus 64 is approaching, via Jln Besar. Destination could not be confirmed.'},
     '64号巴士即将到站，途经Jalan Besar。终点站无法确认。'],
    [{service: null, destination: 'Ang Mo Kio Int', announcement: 'A bus to Ang Mo Kio Int is approaching. Bus number could not be confirmed.'},
     '开往Ang Mo Kio Interchange的巴士即将到站。车号无法确认。'],
    [{service: null, destination: null, announcement: 'A bus is approaching. Bus number and destination could not be read.'},
     '有一辆巴士即将到站。车号和终点站无法识别。'],
    [{service: null, destination: null, announcement: 'Bus not in service.'}, '这辆巴士不载客。'],
    [{service: null, destination: null, announcement: ''}, ''],
  ];
  for (const [match, expected] of cases) assert.equal(chineseAnnouncement(match), expected);
  assert.equal(localPhrase('No bus sign in view.', 'zh'), '画面中没有巴士显示屏。');
  assert.equal(localPhrase('No bus sign in view.', 'en'), 'No bus sign in view.');
  assert.equal(localPhrase('Bus 92B, to Ghim Moh Terminal.', 'zh'), 'Bus 92B, to Ghim Moh Terminal.');
});

test('every spoken aiming hint has a Chinese phrase', () => {
  const source = readFileSync(new URL('../../frontend/assets/js/core/aiming.js', import.meta.url), 'utf8');
  const hints = [...source.matchAll(/^  \w+: '([^']+)',$/gm)].map(match => match[1]);
  assert.ok(hints.length >= 7);
  for (const hint of hints) assert.notEqual(localPhrase(hint, 'zh'), hint, hint);
});
