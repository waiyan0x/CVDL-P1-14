import '../components/layout.js';
import {request} from '../core/api.js';
import {el, message, percent} from '../core/dom.js';
import {facts, list, section, table} from '../components/research.js';
import {detectionReport, ocrReport} from '../components/evaluation-reports.js';
import {initialiseComparison} from './comparison.js';

initialiseComparison();
const container = document.getElementById('evaluation');

function render(data) {
  const fragment = document.createDocumentFragment();
  const reports = data.reports || [];
  const accuracy = el('div', {class: 'panel research-card'},
    el('h3', {}, data.accuracy ? 'Verified OCR evaluation' : 'OCR accuracy has not been measured'),
    el('p', {}, data.accuracy_note || 'Reviewed ground-truth transcriptions are required before reporting accuracy or character error rate.'));
  if (data.accuracy) accuracy.append(facts(Object.entries(data.accuracy).filter(([, value]) => typeof value !== 'object')));
  fragment.append(section('OCR benchmark status', accuracy));
  for (const report of reports) fragment.append(ocrReport(report));
  for (const report of data.detection_reports || []) fragment.append(detectionReport(report));
  const historical = data.historical_checkpoint;
  if (historical) {
    const card = el('div', {class: 'panel research-card'}, el('h3', {}, historical.label || 'Saved training-run metrics'),
      el('p', {}, historical.warning || 'Historical checkpoint metadata; not an independent evaluation of this website.'));
    if (historical.metrics) card.append(facts(Object.entries(historical.metrics).map(([key, value]) => [key.replaceAll('_', ' '), percent(value)])));
    card.append(el('p', {}, `Training class filter: ${(historical.training_classes || [1, 2]).join(', ')}. These figures do not establish whole-screen EDS performance.`));
    fragment.append(section('Historical checkpoint', card));
  }
  const dataset = data.dataset || {};
  if (dataset.splits) fragment.append(section('Dataset audit', table(['Split', 'Images', 'Labelled images'], Object.entries(dataset.splits).map(([name, split]) => [name, split.images, split.labelled_images])),
    list([...(dataset.warnings || []), ...(dataset.overlap || []).map(overlap => `${overlap.image_count} shared image(s) between ${(overlap.splits || []).join(' and ')}.`)])));
  if (data.report_warnings?.length) fragment.append(section('Report checks', list(data.report_warnings)));
  fragment.append(section('Limitations', list(data.limitations || [])));
  container.replaceChildren(fragment);
}

async function load() {
  try { render(await request('/api/evaluation')); }
  catch (error) { message(container, 'Evaluation evidence unavailable', error.message, {error: true, retry: load}); }
}
load();
