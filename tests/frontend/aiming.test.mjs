import assert from 'node:assert/strict';
import test from 'node:test';
import {HintGate, NO_SIGN_MS, aimingHint, nearestSign} from '../../frontend/assets/js/core/aiming.js';

const frame = (...boxes) => ({
  width: 1280, height: 720,
  results: boxes.map(box => ({screen: {label: 'eds', source: 'model', box}, fields: {}})),
});
const code = (data, options) => aimingHint(data, options)?.code ?? null;

test('a centred, readable-size sign needs no hint', () => {
  assert.equal(code(frame([400, 200, 800, 300])), null);
});

test('a sign touching a frame edge says which way to move', () => {
  assert.deepEqual(aimingHint(frame([0, 200, 300, 300])),
    {code: 'left', side: 'left', text: 'Sign cut off on the left. Turn slightly left.'});
  assert.equal(code(frame([1000, 200, 1280, 300])), 'right');
  assert.equal(code(frame([400, 2, 800, 100])), 'top');
  assert.equal(code(frame([400, 600, 800, 719])), 'bottom');
  assert.equal(code(frame([0, 200, 1280, 400])), 'wide');
});

test('a small sign is reported as far away', () => {
  assert.equal(code(frame([600, 300, 680, 320])), 'small');
});

test('no sign is reported only after five seconds', () => {
  const empty = {width: 1280, height: 720, results: []};
  assert.equal(code(empty, {sinceSignMs: NO_SIGN_MS - 1}), null);
  assert.equal(code(empty, {sinceSignMs: NO_SIGN_MS}), 'none');
});

test('the nearest (largest) display is used, from field boxes when no display box exists', () => {
  const data = {width: 1280, height: 720, results: [
    {screen: {box: [600, 300, 680, 320]}, fields: {}},
    {screen: null, fields: {bus_number: {box: [0, 200, 100, 260]}, destination: {box: [100, 200, 400, 260]}}},
  ]};
  assert.deepEqual(nearestSign(data), [0, 200, 400, 260]);
  assert.equal(code(data), 'left');
});

test('missing frame size gives no hint', () => {
  assert.equal(aimingHint({results: []}, {sinceSignMs: 99999}), null);
});

test('hints are spoken after two matching frames, with a gap and limited repeats', () => {
  const gate = new HintGate({gap: 4000, repeat: 15000});
  assert.equal(gate.ready('A', 0), false);
  assert.equal(gate.ready('A', 1000), true);
  gate.announced('A', 1000);
  assert.equal(gate.ready('A', 3000), false);
  assert.equal(gate.ready('A', 6000), false); // same hint, repeat window not reached
  assert.equal(gate.ready('A', 16000), true);
  assert.equal(gate.ready('B', 21000), false); // a new hint needs a second frame
  assert.equal(gate.ready('B', 22000), true);
  assert.equal(gate.ready(null, 23000), false);
  assert.equal(gate.ready('B', 24000), false); // a frame without the hint restarts the count
});
