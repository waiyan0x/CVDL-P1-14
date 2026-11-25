import {compare, request, validateImage} from '../core/api.js';
import {FrameSession} from '../core/session.js';
import {el, engineName, message, percent} from '../core/dom.js';
import {Options} from '../components/options.js';
import {Viewer, fieldNumbers} from '../components/viewer.js?v=2';
import {renderResults} from '../components/results.js';

// Bundled examples measured at the default settings. Filenames survive gallery reordering.
const demoSources = ['bright-daylight.jpg', 'motion-blur.jpg', 'smrt.jpg', 'night-with-headlight-glare.jpg',
  'dim-covered-interchange.jpg', 'red-pink-led-text.jpg'];
const fieldNames = {bus_number: 'Service number', destination: 'Destination'};

function confidenceSummary(data, numbers) {
  const engines = data.comparisons;
  if (engines.length !== 3 || engines.some(engine => engine.status !== 'success')) return '';

  const detections = new Map(data.detections.map(field => [field.id, field]));
  const readings = new Map();
  for (const engine of engines) {
    for (const display of engine.result.results) {
      for (const field of Object.values(display.fields)) {
        if (!(field.label in fieldNames) || field.ocr_source === 'whole_display_fallback' ||
            !Number.isFinite(field.ocr_confidence) || !detections.has(field.id)) continue;
        if (!readings.has(field.id)) readings.set(field.id, new Map());
        readings.get(field.id).set(engine.backend, field.ocr_confidence);
      }
    }
  }

  let largest;
  for (const [id, byEngine] of readings) {
    if (byEngine.size !== engines.length) continue;
    const low = Math.min(...byEngine.values());
    const high = Math.max(...byEngine.values());
    const gap = high - low;
    if (!largest || gap > largest.gap) largest = {id, low, high, gap};
  }
  if (!largest) return '';
  const {id, low, high} = largest;
  const field = detections.get(id);
  const points = Math.round(100 * high) - Math.round(100 * low);
  const region = numbers.has(id) ? ` (region ${numbers.get(id)})` : '';
  const unit = points === 1 ? 'point' : 'points';
  return `${fieldNames[field.label]}${region}. Detection confidence was ${percent(field.confidence)} in all three pipelines. ` +
    `OCR scores ranged from ${percent(low)} to ${percent(high)}, a gap of ${points} percentage ${unit}.`;
}

export async function initialiseComparison() {
  const $ = id => document.getElementById(id);
  const sampleSelect = $('comparison-sample');
  const confidence = $('comparison-confidence');
  const session = new FrameSession();
  const viewer = new Viewer($('viewer'), $('frame-label'), {boxesButton: $('comparison-boxes')});
  const options = new Options($('options'), clearResults, {comparison: true});
  let input = null, objectURL = null, samples = [], maxBytes;

  function clearResults() {
    session.reset();
    confidence.hidden = true;
    $('comparison-results').replaceChildren();
    $('comparison-results').removeAttribute('aria-busy');
    $('compare').disabled = !input;
    $('status').textContent = input ? 'Ready to compare the selected image.' : 'Choose a sample or image to compare.';
    if (input?.preview) viewer.preview(input.preview, input.label);
  }

  function reset() {
    input = null;
    clearResults();
    viewer.clear();
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = null;
    $('comparison-file').value = '';
    sampleSelect.value = '';
  }

  function selectSample(id) {
    reset();
    const selected = samples.find(sample => String(sample.id) === id);
    if (!selected) return;
    sampleSelect.value = selected.id;
    input = {sampleId: selected.id, source: 'sample', preview: selected.url, label: selected.name};
    clearResults();
  }

  async function run() {
    if (!input) return;
    const generation = session.reset();
    confidence.hidden = true;
    $('compare').disabled = true;
    $('comparison-results').setAttribute('aria-busy', 'true');
    $('status').textContent = 'Comparing pipelines… Fine-tuned TrOCR may take longer on its first run.';
    try {
      const selected = input;
      const data = await session.run(generation, () => compare(selected, options.get(), session.metadata(selected.source)));
      if (!data) return;
      const successful = data.comparisons.find(item => item.result)?.result;
      const numbers = successful ? fieldNumbers(successful) : new Map();
      viewer.render({...data, results: successful?.results || []},
        {numbers, label: selected.label, idPrefix: successful ? `${successful.backend}-` : ''});
      const cards = data.comparisons.map(item => {
        const card = el('section', {class: 'stack tight', 'aria-label': engineName(item.backend)}, el('h3', {}, engineName(item.backend)));
        const body = el('div', {class: 'stack tight'});
        if (item.result) renderResults(body, item.result, {numbers, sign: false, idPrefix: `${item.backend}-`});
        else message(body, item.status === 'unavailable' ? 'Engine unavailable' : 'Processing failed', typeof item.error === 'string' ? item.error : item.error?.message || 'This OCR pipeline could not process the image.', {error: true});
        card.append(body);
        return card;
      });
      $('comparison-results').replaceChildren(...cards);
      confidence.textContent = confidenceSummary(data, numbers);
      confidence.hidden = !confidence.textContent;
      $('status').textContent = 'Comparison complete. These are observed predictions on one image, not an accuracy benchmark.';
    } catch (error) {
      if (!session.current(generation)) return;
      viewer.clear();
      message($('comparison-results'), 'Comparison failed', error.message, {error: true, retry: run});
      $('status').textContent = 'Comparison stopped.';
    } finally {
      if (session.current(generation)) { $('compare').disabled = !input; $('comparison-results').removeAttribute('aria-busy'); }
    }
  }

  sampleSelect.addEventListener('change', () => selectSample(sampleSelect.value));
  $('comparison-file').addEventListener('change', event => {
    const file = event.target.files[0];
    if (!file) return;
    reset();
    try {
      validateImage(file, maxBytes);
      objectURL = URL.createObjectURL(file);
      input = {file, source: 'image', preview: objectURL, label: file.name};
      viewer.preview(objectURL, file.name);
      clearResults();
    } catch (error) { message($('comparison-results'), 'Image could not be opened', error.message, {error: true}); }
  });
  $('compare').addEventListener('click', run);
  $('reset').addEventListener('click', reset);
  window.addEventListener('pagehide', () => { session.reset(); if (objectURL) URL.revokeObjectURL(objectURL); });
  try {
    const [status, available] = await Promise.all([options.initialise(), request('/api/samples')]);
    maxBytes = status.limits?.image_upload_bytes || status.limits?.max_image_bytes || 16777216;
    samples = demoSources.map(source => available.find(sample => sample.source === source)).filter(Boolean);
    sampleSelect.replaceChildren(el('option', {value: ''}, samples.length ? 'Choose a sample' : 'No demo samples available'),
      ...samples.map(sample => el('option', {value: sample.id}, sample.name)));
    sampleSelect.disabled = !samples.length;
    if (samples.length) selectSample(String(samples[0].id));
  } catch (error) { message($('comparison-results'), 'Could not start comparison', error.message, {error: true}); }
}
