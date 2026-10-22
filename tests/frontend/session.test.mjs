import test from 'node:test';
import assert from 'node:assert/strict';
import {FrameSession, SamplingLoop} from '../../frontend/assets/js/core/session.js';

const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return {promise, resolve};
};

test('a reset discards an old result and starts a new frame identity', async () => {
  const session = new FrameSession();
  const oldId = session.id;
  const pending = deferred();
  const result = session.run(session.generation, () => pending.promise);
  await Promise.resolve();
  session.reset();
  pending.resolve({service: '3'});
  assert.equal(await result, null);
  const frame = session.metadata('camera', 1200);
  assert.notEqual(frame.session_id, oldId);
  assert.equal(frame.frame_id, 0);
  assert.equal(frame.source_timestamp_ms, 1200);
  assert.equal(session.metadata('camera').frame_id, 1);
});

test('concurrent submissions never overlap inference', async () => {
  const session = new FrameSession();
  const first = deferred();
  let active = 0;
  let maximum = 0;
  const task = async () => {
    maximum = Math.max(maximum, ++active);
    await first.promise;
    active--;
    return 'done';
  };
  const one = session.run(session.generation, task);
  const two = session.run(session.generation, task);
  await new Promise(resolve => setTimeout(resolve, 5));
  first.resolve();
  await Promise.all([one, two]);
  assert.equal(maximum, 1);
});

test('stop and immediate restart do not leave two sampling loops active', async () => {
  const pending = deferred();
  let count = 0;
  const loop = new SamplingLoop(async () => {
    count++;
    if (count === 1) await pending.promise;
  }, () => 15);
  loop.start();
  loop.stop();
  loop.start();
  pending.resolve();
  await new Promise(resolve => setTimeout(resolve, 8));
  loop.stop();
  await new Promise(resolve => setTimeout(resolve, 25));
  assert.equal(count, 2, 'an abandoned tick must not schedule another loop');
});
