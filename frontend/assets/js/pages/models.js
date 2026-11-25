import '../components/layout.js';
import {request} from '../core/api.js';
import {el, message} from '../core/dom.js';
import {initModelsWalkthrough} from '../components/models-walkthrough.js';
import {facts, list, section, table} from '../components/research.js';

const container = document.getElementById('models');
const speech = initModelsWalkthrough();
const sources = 'https://github.com/waiyan0x/CVDL-P1-14/blob/1491f19bfa05270349d85c54a282f5bf1c636f31/';
const benchmarks = [
  ['Detection', '0.327 mAP@50–95', 'YOLO11s on 53 held-out bus photos with annotated sign regions.',
    'evaluation/object_detection/01760a841333/runs/v4-reviewed-01/RESULTS.md#final-held-out-test'],
  ['Text recognition', '82.2% exact match', 'Fine-tuned PaddleOCR on 45 fully legible, manually boxed test crops.',
    'evaluation/OCR_RESULTS.md'],
  ['Route matching', '27 of 28', 'Correct destinations for photos with a reference endpoint in a 40-photo test. One wrong destination was returned across the full set.',
    'docs/REFERENCE_MATCHING.md#7-settings-and-evidence'],
  ['Speech wording', '20.4% → 62.2%', 'Exact destination transcription by Whisper before and after wording changes, measured on 783 clips made with Windows voices.',
    'evaluation/tts/README.md#summary'],
  ['Camera aiming', '57–71%', 'Correct aiming prompt when the sign touched the frame edge or was clipped by up to 20%.',
    'evaluation/guiding_prompts/summary-table.md'],
  ['Processing time', '284 ms', 'Median processing time per frame in a demo test on a two-core CPU.',
    'docs/presentation/DEMO_TEST_CASES.md#0-before-the-demo-5-minutes'],
];

container.append(section('Benchmark results',
  el('div', {class: 'research-grid two model-evidence'}, ...benchmarks.map(([title, value, description, href]) =>
    el('article', {class: 'panel research-card'}, el('h3', {}, title),
      el('p', {class: 'evidence-value'}, value), el('p', {}, description),
      el('a', {class: 'source-link', href: sources + href}, 'Read ' + title.toLowerCase() + ' results'))))));

const modelCards = el('div', {class: 'research-grid two'});
container.append(section('Models in use', modelCards));
container.append(section('Limits', list([
  'Motion blur, distance, glare and low light can make a sign hard to read. OCR also depends on how the sign is cropped.',
  'A reference match identifies a possible endpoint. The bus may be travelling in either direction.',
  'Aiming prompts become less reliable when most of the sign is outside the frame.',
  'The speech wording test used automatic transcription. An ElevenLabs listener study has yet to be run.',
  'EDS Reader is a research prototype. Use official bus information to confirm the service before boarding.',
])));
const technical = el('div', {class: 'stack'});
container.append(section('Technical details', el('details', {class: 'models-details'},
  el('summary', {}, 'Model files, settings and runtime'), technical)));

function renderCards(data, voiceStatus) {
  const available = item => item?.available ? 'Available' : 'Unavailable';
  const ocr = data?.ocr_engines.find(engine => engine.id === 'paddleocr');
  const alternatives = data?.ocr_engines.filter(engine => engine.id !== 'paddleocr') || [];
  const voice = voiceStatus?.available ? 'ElevenLabs with browser fallback'
    : speech.browserVoice ? 'Browser voice' : 'Unavailable';
  const card = (title, description, entries = []) => el('article', {class: 'panel research-card'},
    el('h3', {}, title), el('p', {}, description), entries.length ? facts(entries) : null);
  modelCards.replaceChildren(
    card('Sign detection', 'Fine-tuned YOLO11s finds the whole display, service number, destination and route text.', [
      ['Detector', data ? available(data.detector) : 'Status unavailable'],
    ]),
    card('Text recognition', 'Fine-tuned PaddleOCR reads the sign crops in this walkthrough. Evaluation also compares EasyOCR and fine-tuned TrOCR on the same crops.', [
      ['PaddleOCR', data ? available(ocr) : 'Status unavailable'],
      ...alternatives.map(engine => [engine.name.replace(/^YOLO \+ (fine-tuned )?/, ''), available(engine)]),
    ]),
    card('Route matching', 'The app looks up the exact service number, then checks whether the text resembles a route endpoint in the project’s Singapore bus reference.'),
    card('Spoken announcements', 'English and Mandarin announcements read out the service and destination when available.', [
      ['Current playback', voice],
    ]));
}

function renderTechnical(data) {
  const fragment = document.createDocumentFragment();
  const detector = data.detector;
  const detectorCard = el('div', {class: 'panel research-card'}, el('h3', {}, detector.name || detector.id),
    el('code', {}, detector.path), facts([['Availability', detector.available ? 'Available' : 'Unavailable'], ['Used for', 'Locating sign regions for OCR']]),
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
  if (data.preprocessing) fragment.append(section('Preprocessing', el('div', {class: 'panel research-card'},
    facts(Object.entries(data.preprocessing).map(([key, value]) => [key === 'ocr' ? 'OCR' : 'Detector', value])))));
  const matching = data.matching || {};
  fragment.append(section('Reference matching', el('div', {class: 'panel research-card'},
    el('p', {}, matching.service || 'Service numbers must match the reference exactly.'),
    el('p', {}, matching.destination || ''), el('p', {}, matching.score_definition || ''), list(matching.limitations || []))));
  const screen = data.estimated_screen || {};
  fragment.append(section('Whole EDS screen', el('div', {class: 'panel research-card'},
    el('p', {}, screen.description || ''), el('p', {}, screen.display || ''), el('p', {}, screen.limitation || ''))));
  const hardware = data.runtime_hardware;
  if (hardware) fragment.append(section('Runtime', el('div', {class: 'panel research-card'}, facts([
    ['System', [hardware.system, hardware.release, hardware.machine].filter(Boolean).join(' ')],
    ['Detector device', hardware.detector_device],
    ['Logical CPUs', hardware.logical_cpus],
    ['Torch threads', hardware.torch_threads],
  ]))));
  technical.replaceChildren(fragment);
}

async function load() {
  technical.replaceChildren(el('p', {class: 'notice', role: 'status'}, 'Loading model information…'));
  try {
    const data = await request('/api/models');
    renderTechnical(data);
    renderCards(data, await speech.voiceStatus);
  } catch (error) {
    message(technical, 'Model information unavailable', error.message, {error: true, retry: load});
  }
}
renderCards(null, null);
void load();
