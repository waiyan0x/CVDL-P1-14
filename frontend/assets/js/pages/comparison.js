import {compare, request, validateImage} from '../core/api.js';
import {FrameSession} from '../core/session.js';
import {el, engineName, message} from '../core/dom.js';
import {Options} from '../components/options.js';
import {Viewer, fieldNumbers} from '../components/viewer.js';
import {renderResults} from '../components/results.js';

export async function initialiseComparison() {
  const $ = id => document.getElementById(id);
  const session = new FrameSession();
  const viewer = new Viewer($('viewer'), $('frame-label'));
  const options = new Options($('options'), clearResults, {comparison: true});
  let input = null, objectURL = null, samples = [], maxBytes;

  function clearResults() {
    session.reset();
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
    $('comparison-sample').value = '';
  }

  function selectSample() {
    reset();
    const selected = samples.find(sample => String(sample.id) === $('comparison-sample').dataset.selected);
    if (!selected) return;
    $('comparison-sample').value = selected.id;
    input = {sampleId: selected.id, source: 'sample', preview: selected.url, label: selected.name};
    viewer.preview(selected.url, selected.name);
    clearResults();
  }

  async function run() {
    if (!input) return;
    const generation = session.reset();
    $('compare').disabled = true;
    $('comparison-results').setAttribute('aria-busy', 'true');
    $('status').textContent = 'Comparing pipelines… Fine-tuned TrOCR may take longer on its first run.';
    try {
      const selected = input;
      const data = await session.run(generation, () => compare(selected, options.get(), session.metadata(selected.source)));
      if (!data) return;
      const successful = data.comparisons.find(item => item.result)?.result;
      const numbers = successful ? fieldNumbers(successful) : new Map();
      viewer.render({...data, results: successful?.results || []}, {numbers, idPrefix: successful ? `${successful.backend}-` : ''});
      const cards = data.comparisons.map(item => {
        const card = el('section', {class: 'stack tight', 'aria-label': engineName(item.backend)}, el('h3', {}, engineName(item.backend)));
        const body = el('div', {class: 'stack tight'});
        if (item.result) renderResults(body, item.result, {numbers, idPrefix: `${item.backend}-`});
        else message(body, item.status === 'unavailable' ? 'Engine unavailable' : 'Processing failed', typeof item.error === 'string' ? item.error : item.error?.message || 'This OCR pipeline could not process the image.', {error: true});
        card.append(body);
        return card;
      });
      $('comparison-results').replaceChildren(...cards);
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

  $('comparison-sample').addEventListener('change', event => { event.target.dataset.selected = event.target.value; selectSample(); });
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
    samples = available;
    $('comparison-sample').replaceChildren(el('option', {value: ''}, 'Choose a sample'), ...samples.map(sample => el('option', {value: sample.id}, sample.name)));
    if (samples.length) { $('comparison-sample').dataset.selected = samples[0].id; selectSample(); }
  } catch (error) { message($('comparison-results'), 'Could not start comparison', error.message, {error: true}); }
}
