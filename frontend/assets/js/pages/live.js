import '../components/layout.js';
import {analyse} from '../core/api.js';
import {Camera} from '../core/camera.js';
import {UploadedVideo} from '../core/video.js';
import {FrameSession, SamplingLoop} from '../core/session.js';
import {mediaTime, message, setSegments} from '../core/dom.js';
import {Options} from '../components/options.js';
import {Viewer} from '../components/viewer.js';
import {renderResults} from '../components/results.js';
import {dropFiles} from '../components/samples.js';

const $ = id => document.getElementById(id);
const session = new FrameSession();
const viewer = new Viewer($('viewer'), $('frame-label'));
const camera = new Camera($('camera'));
const video = new UploadedVideo();
let mode = 'camera', running = false, starting = false, startTime = 0, position = 0, minimum = 100, maxBytes;
let firstFrame = true;
const options = new Options($('options'));
const interval = () => Math.max(minimum, Number($('interval').value) || 1000);
const loop = new SamplingLoop(processFrame, interval);

function buttons() {
  $('start').disabled = running || starting || (mode === 'video' && !video.media);
  $('stop').disabled = !running && !starting;
  $('restart').disabled = starting || (mode === 'video' && !video.media);
}

function clearResults() {
  viewer.clear();
  $('legend').hidden = true;
  message($('results'), 'Ready when you are', mode === 'camera' ? 'Start the camera to process its first frame.' : 'Upload a video, then start processing.');
}

function stop(label = 'Stopped') {
  running = false;
  starting = false;
  loop.stop();
  session.reset();
  camera.close();
  $('camera').hidden = !!viewer.last || mode !== 'camera';
  viewer.stopped(label);
  $('results').removeAttribute('aria-busy');
  $('status').textContent = viewer.last ? `${label}. The last completed result is retained.` : `${label}.`;
  buttons();
}

function reset({release = true} = {}) {
  stop();
  position = 0;
  const cleanup = release ? video.clear() : Promise.resolve();
  $('video-file').value = '';
  $('video-zone').classList.remove('compact');
  clearResults();
  $('camera').hidden = mode !== 'camera';
  $('status').textContent = mode === 'camera' ? 'Start the camera to begin.' : 'Choose a video to begin.';
  buttons();
  return cleanup;
}

async function selectMode(next) {
  mode = next;
  setSegments($('modes'), mode);
  $('video-zone').hidden = mode !== 'video';
  await reset();
}

async function chooseVideo(file) {
  const cleanup = reset();
  const generation = session.generation;
  await cleanup;
  if (!session.current(generation) || mode !== 'video') return;
  starting = true;
  $('status').textContent = 'Uploading and validating video…';
  buttons();
  try {
    const media = await video.upload(file, maxBytes);
    if (!media || !session.current(generation)) return;
    $('video-zone').classList.add('compact');
    $('status').textContent = `${media.name} · ${mediaTime(media.duration_ms)} · ${media.width} × ${media.height}. Ready to start.`;
  } catch (error) {
    if (!session.current(generation)) return;
    message($('results'), 'Video could not be opened', error.message, {error: true});
    $('status').textContent = 'Choose another video.';
  } finally {
    if (session.current(generation)) { starting = false; buttons(); }
  }
}

async function start({restart = false} = {}) {
  if (starting) return;
  stop();
  if (restart) { position = 0; clearResults(); }
  const generation = session.generation;
  starting = true;
  buttons();
  $('status').textContent = mode === 'camera' ? 'Opening camera…' : 'Starting video…';
  try {
    if (mode === 'camera') {
      $('camera').hidden = false;
      if (!await camera.open() || !session.current(generation)) return;
    } else if (!video.media) throw new Error('Choose a video before starting.');
    else if (position >= video.media.duration_ms) position = 0;
    if (!session.current(generation)) return;
    startTime = performance.now() - position;
    firstFrame = true;
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
  $('status').textContent = 'Processing stopped. Restart or choose another input.';
}

async function processFrame() {
  const generation = session.generation;
  if (!running) return;
  try {
    const data = await session.run(generation, async () => {
      if (!running || !session.current(generation)) return null;
      // Capture only when admitted; missed intervals are skipped, never queued.
      if (!firstFrame) position = performance.now() - startTime;
      firstFrame = false;
      if (mode === 'video') {
        if (position >= video.media.duration_ms) { stop('Video ended'); return null; }
        return video.frame(position, options.get(), session.metadata('video', position));
      }
      const file = await camera.capture();
      if (!session.current(generation)) return null;
      return analyse({file}, options.get(), session.metadata('camera', position));
    });
    if (!data || !running) return;
    viewer.render(data);
    renderResults($('results'), data);
    $('legend').hidden = !data.detections.length;
    $('status').textContent = `Processing · ${Number(data.processing_fps || 0).toFixed(1)} frames/s for the latest frame`;
    $('results').setAttribute('aria-busy', 'false');
    if (mode === 'camera') $('camera').hidden = true;
  } catch (error) { if (session.current(generation)) fail(error); }
}

$('modes').addEventListener('click', event => { if (event.target.dataset.mode) selectMode(event.target.dataset.mode); });
$('start').addEventListener('click', () => start());
$('stop').addEventListener('click', () => stop());
$('restart').addEventListener('click', () => start({restart: true}));
$('reset').addEventListener('click', () => reset());
$('interval').addEventListener('change', () => { $('interval').value = String(Math.min(10000, interval())); });
dropFiles($('video-zone'), $('video-file'), chooseVideo);
window.addEventListener('pagehide', () => { stop(); video.clear({keepalive: true}); });

options.initialise().then(status => {
  minimum = status.limits?.minimum_sampling_interval_ms || status.limits?.min_interval_ms || 100;
  maxBytes = status.limits?.video_upload_bytes || status.limits?.max_video_bytes || 200 * 1048576;
  $('interval').min = minimum;
  $('interval').value = status.limits?.default_sampling_interval_ms || status.limits?.default_interval_ms || 1000;
  $('video-limit').textContent = `Up to ${Math.round(maxBytes / 1048576)} MB. Video is validated and decoded on the server.`;
  buttons();
}).catch(fail);
buttons();
