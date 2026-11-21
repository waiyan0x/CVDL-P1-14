import assert from 'node:assert/strict';
import test from 'node:test';
import {AnnouncementGate, busAnnouncement, cameraObservation, estimateMetres} from '../../frontend/assets/js/core/bus-announcements.js';

const captured = Date.parse('2026-11-21T00:00:00Z');
function result({panel = [120, 110, 300, 146], source = 'camera'} = {}) {
  return {
    frame: {source, session_id: 'stream-one', captured_at: new Date(captured).toISOString()},
    width: 1280, height: 720,
    results: [{
      fields: {bus_number: {raw: '92B', ocr_confidence: .9}},
      match: {service: '92B', status: 'matched', endpoint: 'Ghim Moh Terminal'},
      screen: {label: 'eds', source: 'model', box: panel},
    }],
  };
}

test('speaks service codes distinctly, with only matched destinations', () => {
  const frame = result();
  assert.equal(busAnnouncement(frame, .25, 30),
    'Bus service 9 2 B, about 30 metres away. Reference destination: Ghim Moh Terminal.');
  frame.results[0].match = {status: 'unmatched', endpoint: 'Unused'};
  assert.equal(busAnnouncement(frame, .25), 'Possible bus service 9 2 B.');
  assert.equal(busAnnouncement(frame, .95), null);
  frame.results[0].fields.bus_number.raw = 'unknown';
  assert.equal(busAnnouncement(frame, .25), null);
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
  assert.doesNotMatch(busAnnouncement(frame, .25, 30), /metres/);
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
