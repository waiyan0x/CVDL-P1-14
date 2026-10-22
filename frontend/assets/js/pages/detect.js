import '../components/layout.js';
import {analyse, validateImage} from '../core/api.js';
import {FrameSession} from '../core/session.js';
import {Camera} from '../core/camera.js';
import {message, setSegments} from '../core/dom.js';
import {Options} from '../components/options.js';
import {Viewer} from '../components/viewer.js';
import {renderResults} from '../components/results.js';
import {dropFiles, loadSamples} from '../components/samples.js';

const $ = id => document.getElementById(id);
const session = new FrameSession();
const viewer = new Viewer($('viewer'), $('frame-label'));
const camera = new Camera($('camera'));
let mode = 'samples', input = null, objectURL = null, sampleList, maxBytes;
const options = new Options($('options'), () => { if (input) processInput(); });

function clearInput() {
  session.reset();
  camera.close();
  input = null;
  if (objectURL) URL.revokeObjectURL(objectURL);
  objectURL = null;
  viewer.clear();
  $('legend').hidden = true;
  $('image-file').value = '';
  $('upload-zone').classList.remove('compact');
  $('camera').hidden = false;
  $('open-camera').disabled = false;
  $('capture').disabled = true;
  sampleList?.clear();
  $('results').removeAttribute('aria-busy');
  message($('results'), 'Ready when you are', mode === 'camera' ? 'Open the camera and capture one image.' : 'Choose an image to start.');
}

function selectMode(next) {
  mode = next;
  clearInput();
  setSegments($('modes'), mode);
  $('upload-zone').hidden = mode !== 'upload';
  $('samples').hidden = mode !== 'samples';
  $('camera-panel').hidden = mode !== 'camera';
  $('status').textContent = mode === 'camera' ? 'A snapshot processes one image. Use Live for continuous detection.' : 'Choose an image to start.';
}

async function processInput() {
  if (!input) return;
  const selected = input;
  const generation = session.reset();
  $('results').setAttribute('aria-busy', 'true');
  $('status').textContent = 'Processing image…';
  try {
    const data = await session.run(generation, () => analyse(selected, options.get(), session.metadata(selected.source, selected.timestamp || 0)));
    if (!data) return;
    viewer.render(data, {label: selected.label});
    renderResults($('results'), data);
    $('legend').hidden = !data.detections.length;
    $('status').textContent = 'Analysis complete.';
  } catch (error) {
    if (!session.current(generation)) return;
    viewer.clear();
    $('legend').hidden = true;
    $('status').textContent = 'Processing stopped.';
    message($('results'), 'Processing failed', error.message, {error: true, retry: processInput});
  } finally {
    if (session.current(generation)) $('results').removeAttribute('aria-busy');
  }
}

function selectSample(sample) {
  session.reset();
  input = {sampleId: sample.id, source: 'sample', label: sample.name};
  message($('results'), 'Processing image', 'The result will appear here.');
  viewer.preview(sample.url, sample.name);
  $('legend').hidden = true;
  processInput();
}

function selectFile(file) {
  clearInput();
  try {
    validateImage(file, maxBytes);
    objectURL = URL.createObjectURL(file);
    input = {file, source: 'image', label: file.name};
    $('upload-zone').classList.add('compact');
    viewer.preview(objectURL, file.name);
    processInput();
  } catch (error) {
    message($('results'), 'Image could not be opened', error.message, {error: true});
    $('status').textContent = 'Choose another image.';
  }
}

async function openCamera() {
  clearInput();
  const generation = session.generation;
  $('open-camera').disabled = true;
  $('status').textContent = 'Opening camera…';
  try {
    if (!await camera.open() || !session.current(generation)) return;
    $('capture').disabled = false;
    $('status').textContent = 'Camera ready. Capture an image to analyse it.';
  } catch (error) {
    if (!session.current(generation)) return;
    message($('results'), 'Camera unavailable', error.message, {error: true, retry: openCamera});
    $('status').textContent = 'Camera stopped.';
  } finally { if (session.current(generation)) $('open-camera').disabled = false; }
}

$('capture').addEventListener('click', async () => {
  const generation = session.generation;
  try {
    const file = await camera.capture();
    if (!session.current(generation)) return;
    input = {file, source: 'camera', label: 'Camera snapshot', timestamp: performance.now()};
    camera.close();
    $('camera').hidden = true;
    $('capture').disabled = true;
    processInput();
  } catch (error) {
    if (session.current(generation)) message($('results'), 'Capture failed', error.message, {error: true, retry: openCamera});
  }
});
$('open-camera').addEventListener('click', openCamera);
$('modes').addEventListener('click', event => { if (event.target.dataset.mode) selectMode(event.target.dataset.mode); });
$('reset').addEventListener('click', () => { clearInput(); $('status').textContent = 'Reset complete. Choose a new input.'; });
dropFiles($('upload-zone'), $('image-file'), selectFile);
window.addEventListener('pagehide', () => { session.reset(); camera.close(); if (objectURL) URL.revokeObjectURL(objectURL); });

async function initialise() {
  const generation = session.generation;
  try {
    const [status, samples] = await Promise.all([options.initialise(), loadSamples($('samples'), selectSample)]);
    sampleList = samples;
    maxBytes = status.limits?.image_upload_bytes || status.limits?.max_image_bytes || 16777216;
    $('image-limit').textContent = `JPG, PNG or WebP, up to ${Math.round(maxBytes / 1048576)} MB`;
    if (session.current(generation) && mode === 'samples' && !input) samples.select(0);
  } catch (error) {
    $('status').textContent = 'Application unavailable.';
    message($('results'), 'Could not start', error.message, {error: true, retry: initialise});
  }
}
initialise();
