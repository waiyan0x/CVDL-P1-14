import '../components/layout.js';
import {analyse} from '../core/api.js';
import {Camera} from '../core/camera.js';
import {FrameSession, SamplingLoop} from '../core/session.js';
import {busAnnouncement, cameraObservation, estimateMetres} from '../core/bus-announcements.js';
import {aimingHint, nearestSign} from '../core/aiming.js';
import {message} from '../core/dom.js';
import {Options} from '../components/options.js';
import {Viewer} from '../components/viewer.js?v=2';
import {renderResults} from '../components/results.js';
import {SpeechControls} from '../components/speech.js?v=2';

// Live reads the camera only. Video upload was removed from this page; the /api/videos endpoints remain.
const $ = id => document.getElementById(id);
const session = new FrameSession();
const viewer = new Viewer($('viewer'), $('frame-label'), {boxesButton: $('detection-boxes')});
const camera = new Camera($('camera'));
let running = false, starting = false, startTime = 0, position = 0, minimum = 100;
let firstFrame = true;
let reference = null, latestFrame = null, freshnessTimer;
let lastSignAt = 0;
const speech = new SpeechControls({read: $('speech-read'), stop: $('speech-stop'), status: $('speech-status'),
  automatic: $('speech-auto'), language: $('speech-language'), currentDistance: () => estimateMetres(reference, currentObservation())});
const options = new Options($('options'));
const interval = () => Math.max(minimum, Number($('interval').value) || 1000);
const loop = new SamplingLoop(processFrame, interval);

function reportStatus(text, announcement = text) {
  $('status').textContent = text;
  if ($('stream-announcement').textContent !== announcement) $('stream-announcement').textContent = announcement;
}

function currentObservation() {
  if (!running) return null;
  const track = camera.stream?.getVideoTracks()[0];
  if (track?.readyState !== 'live') return null;
  return cameraObservation(latestFrame, track.getSettings?.().zoom ?? null);
}

function refreshDistance() {
  const observation = currentObservation();
  const metres = estimateMetres(reference, observation);
  $('calibrate').disabled = !observation;
  $('clear-calibration').disabled = !reference;
  $('distance-reading').hidden = metres === null;
  $('distance-reading').textContent = metres === null ? '' : `Estimated distance: about ${metres} metres.`;
  const status = reference
    ? `Reference set at ${reference.metres} metres for service ${reference.service}.`
    : 'Start the camera and wait for one recognised bus with a full sign.';
  if ($('distance-status').textContent !== status) $('distance-status').textContent = status;
  return metres;
}

function showHint(hint) {
  const node = $('aim-hint');
  node.hidden = !hint;
  node.textContent = hint?.text ?? '';
  node.dataset.side = hint?.side ?? '';
}

// Hints describe how to move the camera.
function updateAim(data) {
  const now = performance.now();
  if (nearestSign(data)) lastSignAt = now;
  const hint = aimingHint(data, {sinceSignMs: now - lastSignAt});
  showHint(hint);
  // A confirmed bus reading is more useful than a hint, so hints are spoken only when nothing was read.
  speech.hint(busAnnouncement(data, {confirmedOnly: true}) ? null : hint?.text ?? null);
}

function buttons() {
  $('start').disabled = running || starting;
  $('stop').disabled = !running && !starting;
  $('restart').disabled = starting;
}

function clearResults() {
  speech.reset();
  showHint(null);
  viewer.clear();
  message($('results'), 'Ready when you are', 'Start the camera to process its first frame.');
}

function stop(label = 'Stopped') {
  running = false;
  starting = false;
  speech.reset({keepResult: true});
  clearTimeout(freshnessTimer);
  latestFrame = null;
  reference = null;
  refreshDistance();
  loop.stop();
  showHint(null);
  session.reset();
  camera.close();
  $('camera').hidden = !!viewer.last;
  viewer.stopped(label);
  $('results').removeAttribute('aria-busy');
  reportStatus(viewer.last ? `${label}. The last completed result is retained.` : `${label}.`);
  buttons();
}

function reset() {
  stop();
  position = 0;
  clearResults();
  $('camera').hidden = false;
  reportStatus('Start the camera to begin.');
  buttons();
}

async function start({restart = false} = {}) {
  if (starting) return;
  stop();
  if (restart) { position = 0; clearResults(); }
  const generation = session.generation;
  starting = true;
  buttons();
  reportStatus('Opening camera…');
  try {
    $('camera').hidden = false;
    if (!await camera.open() || !session.current(generation)) return;
    startTime = performance.now() - position;
    firstFrame = true;
    lastSignAt = performance.now();
    running = true;
    starting = false;
    buttons();
    loop.start();
  } catch (error) { if (session.current(generation)) fail(error); }
}

function fail(error) {
  stop('Processing stopped');
  clearResults();
  message($('results'), 'Processing failed', error.message, {error: true, retry: () => start()});
  reportStatus('Processing stopped. Restart to try again.');
}

async function processFrame() {
  const generation = session.generation;
  if (!running) return;
  const settings = options.get();
  try {
    const data = await session.run(generation, async () => {
      if (!running || !session.current(generation)) return null;
      // Capture only when admitted; missed intervals are skipped, never queued.
      if (!firstFrame) position = performance.now() - startTime;
      firstFrame = false;
      const metadata = session.metadata('camera', position);
      const file = await camera.capture();
      if (!session.current(generation)) return null;
      return analyse({file}, settings, metadata);
    });
    if (!data || !running) return;
    viewer.render(data);
    renderResults($('results'), data);
    latestFrame = data;
    const metres = refreshDistance();
    clearTimeout(freshnessTimer);
    freshnessTimer = setTimeout(refreshDistance,
      Math.max(0, 3501 - (Date.now() - Date.parse(data.frame.captured_at))));
    speech.update(data, metres, {announce: true});
    updateAim(data);
    reportStatus(`Processing · ${Number(data.processing_fps || 0).toFixed(1)} frames/s for the latest frame`, 'Processing frames.');
    $('results').setAttribute('aria-busy', 'false');
    $('camera').hidden = true;
  } catch (error) {
    if (!session.current(generation)) return;
    if (error.code === 'processing_busy') {
      reportStatus('Waiting for the processor. The next frame will be tried automatically.', 'Waiting for the processor.');
      return;
    }
    fail(error);
  }
}

$('distance-form').addEventListener('submit', event => {
  event.preventDefault();
  const metres = $('distance-reference').valueAsNumber;
  const observation = currentObservation();
  if (!observation || !Number.isFinite(metres) || metres < 5 || metres > 100) {
    $('distance-status').textContent = 'Wait for a current, full sign and enter a measured distance from 5 to 100 metres.';
    return;
  }
  reference = {...observation, metres};
  refreshDistance();
});
$('clear-calibration').addEventListener('click', () => {
  reference = null;
  refreshDistance();
});
$('start').addEventListener('click', () => start());
$('stop').addEventListener('click', () => stop());
$('restart').addEventListener('click', () => start({restart: true}));
$('reset').addEventListener('click', () => reset());
$('interval').addEventListener('change', () => { $('interval').value = String(Math.min(10000, interval())); });
window.addEventListener('pagehide', () => stop());

options.initialise().then(status => {
  minimum = status.limits?.minimum_sampling_interval_ms || status.limits?.min_interval_ms || 100;
  $('interval').min = minimum;
  $('interval').value = status.limits?.default_sampling_interval_ms || status.limits?.default_interval_ms || 1000;
  buttons();
}).catch(fail);
buttons();
