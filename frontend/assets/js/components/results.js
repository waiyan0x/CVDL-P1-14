import {el, message, milliseconds, percent} from '../core/dom.js';
import {fieldNumbers} from './viewer.js';

const titles = {matched: 'Reference endpoint matched', partial: 'Incomplete reading', unreadable: 'Unreadable text', unknown_match: 'Unknown route', no_eds: 'No EDS found'};
const roles = {bus_number: 'Service number', destination: 'Destination'};

function confidence(label, value) { return el('div', {}, el('dt', {}, label), el('dd', {}, percent(value))); }

function fieldCard(field, label, result, number, idPrefix = '') {
  const card = el('article', {class: 'panel field-card', id: `result-${idPrefix}${field.id}`, tabindex: '-1'},
    el('div', {class: 'field-label'}, el('span', {class: 'field-number'}, String(number)), roles[label]));
  if (field.crop) card.append(el('img', {class: 'crop', src: field.crop, alt: `${roles[label]} crop`}));
  const text = el('div', {class: 'field-text'}, el('div', {class: 'raw-text'}, field.raw?.trim() ? `OCR reads ${field.raw}` : 'OCR could not read this region'));
  const match = result.match || {};
  const matched = label === 'bus_number' ? match.service : match.status === 'matched' ? match.endpoint : null;
  const normalise = value => String(value || '').replace(/[^a-z0-9]/gi, '').toUpperCase();
  if (matched && normalise(matched) !== normalise(field.raw)) text.append(el('div', {class: 'matched-text'}, `Matched ${matched}`));
  card.append(text, el('dl', {class: 'scores'},
    confidence('Detection conf.', field.confidence), confidence('OCR conf.', field.ocr_confidence),
    confidence('Match score', label === 'destination' ? match.similarity : null)));
  return card;
}

function routeCard(result) {
  const match = result.match || {};
  const description = result.message || match.reason || 'No reference match is available.';
  const card = el('section', {class: 'panel route-card'}, el('span', {class: 'small muted'}, 'Route match'),
    el('h3', {class: 'matched-text'}, titles[result.status] || 'Reading complete'));
  if (result.status === 'matched') {
    card.append(el('p', {}, 'The observed service and destination agree with a reference endpoint. Travel direction is unverified.'));
  } else if (description !== titles[result.status]) card.append(el('p', {}, description));
  // Service and destination already appear in their field cards.
  return card;
}

export function timingCard(data) {
  const rows = [['Detection', 'detection_ms'], ['Crop & preprocess', 'preprocessing_ms'], ['OCR', 'ocr_ms'], ['Route matching', 'matching_ms']];
  const dl = el('dl');
  for (const [title, key] of rows) dl.append(el('div', {}, el('dt', {}, title), el('dd', {}, milliseconds(data.timings?.[key]))));
  dl.append(el('div', {class: 'total'}, el('dt', {}, 'Total'), el('dd', {}, milliseconds(data.timings?.total_ms))));
  return el('section', {class: 'panel timings', 'aria-label': 'Processing time'}, el('span', {class: 'small muted'}, 'Processing time'), dl);
}

export function renderResults(container, data, {timing = true, numbers = fieldNumbers(data), idPrefix = ''} = {}) {
  const fragment = document.createDocumentFragment();
  if (data.status === 'no_eds' || !data.results.length) {
    const state = el('div');
    message(state, 'No EDS found', data.message || 'Try a closer, front-facing frame or another sample.');
    fragment.append(state);
  }
  data.results.forEach((result, index) => {
    const group = el('section', {class: 'display-group', 'aria-label': `Display ${index + 1}`});
    if (data.results.length > 1) group.append(el('h3', {class: 'display-title'}, `Display ${index + 1}`));
    let fields = 0;
    for (const label of ['bus_number', 'destination']) {
      const field = result.fields?.[label];
      if (!field) continue;
      fields++;
      group.append(fieldCard(field, label, result, numbers.get(field.id), idPrefix));
    }
    if (!fields) {
      const panel = el('div', {class: 'panel field-card'}, el('h3', {}, 'Screen found, text unreadable'));
      if (result.screen?.crop) panel.append(el('img', {src: result.screen.crop, alt: 'Detected EDS screen', class: 'crop screen-crop'}));
      panel.append(el('p', {class: 'small muted'}, result.message || 'No readable service-number or destination region was found inside this screen.'));
      group.append(panel);
    }
    group.append(routeCard(result));
    fragment.append(group);
  });
  if (timing) fragment.append(timingCard(data));
  container.replaceChildren(fragment);
}
