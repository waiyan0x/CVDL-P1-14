import {analyse, request} from '../core/api.js';
import {el, message, milliseconds, percent, setSegments} from '../core/dom.js';
import {busAnnouncement} from '../core/bus-announcements.js';
import {facts} from './research.js';
import {SpeechControls} from './speech.js?v=2';
import {Viewer} from './viewer.js';

const fieldNames = {bus_number: 'Service number', destination: 'Destination', route: 'Route / landmark'};
const timingNames = {detection_ms: 'Detection', ocr_ms: 'OCR', matching_ms: 'Matching', total_ms: 'Total'};

function readout(fields) {
  return el('dl', {class: 'walkthrough-crops'}, ...Object.entries(fieldNames).map(([key, name]) => {
    const field = fields[key];
    return el('div', {},
      el('dt', {}, name),
      el('dd', {},
        field?.crop ? el('img', {class: 'crop', src: field.crop, alt: 'Sign crop for ' + name.toLowerCase()}) : null,
        el('span', {}, field?.raw || 'No text read'),
        Number.isFinite(field?.ocr_confidence)
          ? el('small', {}, 'OCR confidence ' + percent(field.ocr_confidence))
          : null));
  }));
}

export function initModelsWalkthrough() {
  const get = id => document.getElementById('walkthrough-' + id);
  const steps = document.querySelector('.walkthrough-steps');
  const viewer = new Viewer(get('viewer'), get('caption'), {boxesButton: get('boxes')});
  const panel = get('panel');
  const result = get('result');
  const status = get('status');
  const errorBox = get('error');
  const timings = get('timings');
  const speechPanel = get('speech');
  const language = get('language');
  const speech = new SpeechControls({
    read: get('play'), stop: get('stop'), status: get('speech-status'), language,
  });
  const stepsByMode = {
    photo: 'Start with the original bus photo.',
    detect: 'The detector marks the sign and its text regions.',
    read: 'PaddleOCR reads the letters and numbers in the cropped regions.',
    match: 'The service number and destination are checked against the route reference.',
    speak: 'Play the announcement in English or Chinese.',
  };
  let active = 'photo';
  let sample;
  let data;
  let pending = false;

  function render() {
    setSegments(steps, active);
    speechPanel.hidden = active !== 'speak' || !data;
    timings.hidden = active === 'photo' || !data;
    panel.hidden = !sample;
    if (!sample) return;
    if (active === 'detect' && data) viewer.render(data, {label: sample.name, linkResults: false});
    else viewer.preview(sample.url, sample.name);

    let detail;
    if (active === 'photo') {
      detail = el('p', {}, 'This photo shows a close front view of a bus. Select the next step to see where EDS Reader finds its electronic display.');
    } else if (!data) {
      detail = el('p', {}, stepsByMode[active]);
    } else {
      const display = data.results.find(item => item.match?.status === 'matched') ?? data.results[0];
      const match = display?.match;
      if (active === 'detect') {
        const count = data.detections.length;
        const confidence = data.detections.filter(item => item.source === 'model' && Number.isFinite(item.confidence))
          .map(item => item.confidence);
        detail = el('div', {class: 'research-card'}, el('p', {}, count
          ? 'YOLO located ' + count + ' regions. The numbered boxes mark text fields, and EDS marks the whole sign.'
          : 'The detector could not find a sign in this photo.'),
        confidence.length ? facts([['Detection confidence', percent(Math.min(...confidence)) + ' to ' + percent(Math.max(...confidence))]]) : null);
      } else if (active === 'read') {
        detail = el('div', {class: 'research-card'}, el('p', {}, 'Text from the main display.'), readout(display?.fields || {}));
      } else if (active === 'match') {
        const otherDisplays = data.results.filter(item => item !== display && item.match?.announcement);
        detail = el('div', {class: 'research-card'}, facts([
          ['Service number', match?.service || 'Unresolved'],
          ['Destination', match?.endpoint || 'Unresolved'],
          ['Text similarity', percent(match?.similarity)],
        ]), el('p', {}, match?.reason || 'No route match is available for this photo.'),
        ...otherDisplays.map(item => el('p', {}, item.match.announcement)));
      } else {
        const announcement = busAnnouncement(data, {language: speech.language});
        detail = el('p', {lang: speech.language, class: 'walkthrough-transcript'},
          announcement || 'No bus announcement is available for this photo.');
        speechPanel.hidden = !announcement;
      }
    }
    const title = steps.querySelector('[aria-pressed="true"]').textContent;
    result.replaceChildren(el('h3', {}, title), detail);
    if (!timings.hidden) {
      timings.replaceChildren(...Object.entries(timingNames).map(([key, name]) =>
        el('div', {}, el('dt', {}, name), el('dd', {}, milliseconds(data.timings?.[key])))));
    }
  }

  async function run() {
    if (pending || data || !sample) return;
    pending = true;
    errorBox.hidden = true;
    status.textContent = 'Analysing the sample photo…';
    try {
      data = await analyse({sampleId: sample.id}, {backend: 'paddleocr'}, {source: 'sample'});
      speech.update(data);
      render();
      status.textContent = 'Sample analysis complete.';
    } catch (error) {
      status.textContent = 'Sample analysis failed.';
      errorBox.hidden = active === 'photo';
      message(errorBox, 'Could not analyse the photo', error.message, {error: true, retry: run});
    } finally {
      pending = false;
    }
  }

  async function loadSample() {
    errorBox.hidden = true;
    status.textContent = 'Loading the sample photo…';
    try {
      const samples = await request('/api/samples');
      sample = samples.find(item => item.source === 'close-readable-eds.jpg');
      if (!sample) throw new Error('The close-up photo is missing from the sample library.');
      steps.querySelectorAll('button').forEach(button => { button.disabled = false; });
      render();
      status.textContent = '';
    } catch (error) {
      status.textContent = 'Sample photo unavailable.';
      errorBox.hidden = false;
      message(errorBox, 'Could not load the photo', error.message, {error: true, retry: loadSample});
    }
  }

  steps.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    if (active === 'speak' && button.dataset.mode !== 'speak') speech.reset({keepResult: true});
    active = button.dataset.mode;
    render();
    if (active === 'photo' && sample) errorBox.hidden = true;
    if (active !== 'photo') void run();
  });
  language.addEventListener('change', render);
  window.addEventListener('pagehide', () => speech.reset({keepResult: true}));
  void loadSample();
  return speech;
}
