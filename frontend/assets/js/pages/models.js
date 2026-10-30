import '../components/layout.js';
import {request} from '../core/api.js';
import {el, message} from '../core/dom.js';
import {facts, list, section, table} from '../components/research.js';

const container = document.getElementById('models');

function render(data) {
  const fragment = document.createDocumentFragment();
  const detector = data.detector;
  const detectorCard = el('div', {class: 'panel research-card'}, el('h3', {}, detector.name || detector.id),
    el('code', {}, detector.path), facts([['Availability', detector.available ? 'Available' : 'Unavailable'], ['Used for', 'Locating sign regions; OCR reads their text']]),
    el('p', {}, detector.confidence_definition));
  fragment.append(section('Detection model', detectorCard,
    table(['Class', 'Label', 'Used in analysis'], (detector.classes || []).map(item => [item.id, item.label, item.used ? 'Yes' : 'No']))));
  const engines = el('div', {class: 'research-grid'}, ...data.ocr_engines.map(engine => {
    const card = el('article', {class: 'panel research-card'}, el('h3', {}, engine.name),
      el('p', {}, engine.description), el('code', {}, engine.path || 'System installation'),
      facts([['Availability', engine.available ? 'Available' : 'Unavailable'], ['Version', engine.version || 'Not reported']]),
      el('p', {}, engine.confidence_definition));
    if (!engine.available && engine.unavailable_reason) card.append(el('p', {}, engine.unavailable_reason));
    if (engine.limitations?.length) card.append(list(engine.limitations));
    return card;
  }));
  fragment.append(section('OCR engines', engines));
  fragment.append(section('Processing pipeline', el('ol', {class: 'pipeline-steps'}, ...(data.pipeline || []).map(step => el('li', {}, el('div', {}, el('h3', {}, step.title), el('p', {}, step.description)))))));
  if (data.preprocessing) fragment.append(section('Preprocessing', el('div', {class: 'panel research-card'}, ...Object.entries(data.preprocessing).map(([key, value]) => el('p', {}, `${key === 'ocr' ? 'OCR' : 'Detector'}: ${value}`)))));
  const matching = data.matching || {};
  fragment.append(section('Reference matching', el('div', {class: 'panel research-card'},
    el('p', {}, matching.service || 'Service numbers must match the reference exactly.'),
    el('p', {}, matching.destination || ''), el('p', {}, matching.score_definition || ''), list(matching.limitations || []))));
  const screen = data.estimated_screen || {};
  fragment.append(section('Whole EDS screen', el('div', {class: 'panel research-card'},
    el('p', {}, screen.description || ''), el('p', {}, screen.display || ''), el('p', {}, screen.limitation || ''))));
  container.replaceChildren(fragment);
}

async function load() {
  try { render(await request('/api/models')); }
  catch (error) { message(container, 'Model information unavailable', error.message, {error: true, retry: load}); }
}
load();
