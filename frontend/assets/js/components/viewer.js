import {el, mediaTime} from '../core/dom.js';

// The legend under the image names each numbered box in words, so a box is identified without the result card
// or colour. Names stay off the boxes themselves, where they would cover a small sign.
const FIELD_NAMES = {bus_number: 'Service', route: 'Route', destination: 'Destination'};

export function fieldNumbers(data) {
  const mapping = new Map();
  let number = 1;
  for (const result of data.results || []) {
    for (const label of ['bus_number', 'route', 'destination']) {
      const field = result.fields?.[label];
      if (field) mapping.set(field.id, number++);
    }
  }
  return mapping;
}

export class Viewer {
  constructor(container, caption, {boxesButton} = {}) {
    this.container = container;
    this.caption = caption;
    this.last = null;
    this.boxesButton = boxesButton;
    this.boxesVisible = true;
    this.legend = el('p', {class: 'box-legend'});
    this.legend.hidden = true;
    container.after(this.legend);
    boxesButton?.addEventListener('click', () => {
      this.boxesVisible = !this.boxesVisible;
      boxesButton.textContent = this.boxesVisible ? 'Hide detection boxes' : 'Show detection boxes';
      this.updateDetectionBoxes();
    });
  }

  updateDetectionBoxes() {
    const boxes = this.container.querySelectorAll('.box');
    if (this.boxesButton) this.boxesButton.hidden = boxes.length === 0;
    this.legend.hidden = !boxes.length || !this.boxesVisible || !this.legend.childElementCount;
    if (!boxes.length) return;
    boxes.forEach(box => { box.hidden = !this.boxesVisible; });
    this.container.querySelector('img').alt = this.boxesVisible ? 'Processed frame with numbered detected regions' : 'Processed frame';
  }

  clear(text = '') {
    this.last = null;
    this.container.replaceChildren();
    this.container.hidden = true;
    this.caption.textContent = text;
    this.updateDetectionBoxes();
  }

  preview(url, label) {
    this.container.hidden = false;
    this.container.replaceChildren(el('img', {src: url, alt: label}));
    this.caption.textContent = label;
    this.updateDetectionBoxes();
  }

  render(data, {numbers = fieldNumbers(data), state = 'Processed', label = '', idPrefix = '', linkResults = true} = {}) {
    this.last = data;
    this.container.hidden = false;
    const image = el('img', {src: data.image, alt: 'Processed frame', width: data.width, height: data.height});
    const fragment = document.createDocumentFragment();
    fragment.append(image);
    const detections = [...data.detections].sort((a, b) => Number(b.label === 'eds') - Number(a.label === 'eds'));
    for (const detection of detections) {
      const [x1, y1, x2, y2] = detection.box;
      const estimated = detection.source === 'field_union';
      const screen = detection.label === 'eds';
      const number = numbers.get(detection.id);
      const linked = linkResults && Boolean(number);
      const box = el(linked ? 'a' : 'span', {
        class: `box${estimated ? ' estimated' : ''}${screen ? ' screen' : ''}`,
        href: linked ? `#result-${idPrefix}${detection.id}` : null,
        'aria-label': linked ? `Region ${number}, ${{bus_number: 'service number', route: 'route or landmark', destination: 'destination'}[detection.label]}: go to result` : null,
        'aria-hidden': linked ? null : 'true',
      }, el('span', {class: 'box-number'}, screen ? `EDS${estimated ? ' · estimated' : ''}` : String(number || '')));
      Object.assign(box.style, {left: `${x1 / data.width * 100}%`, top: `${y1 / data.height * 100}%`, width: `${(x2 - x1) / data.width * 100}%`, height: `${(y2 - y1) / data.height * 100}%`});
      fragment.append(box);
    }
    this.container.replaceChildren(fragment);
    const named = data.detections.filter(d => numbers.get(d.id) && FIELD_NAMES[d.label])
      .sort((a, b) => numbers.get(a.id) - numbers.get(b.id));
    this.legend.replaceChildren(...named.map(d => el('span', {}, el('span', {class: 'box-number'}, String(numbers.get(d.id))), FIELD_NAMES[d.label])),
      ...(detections.some(d => d.label === 'eds') ? [el('span', {}, el('span', {class: 'box-number dark'}, 'EDS'), 'Whole sign')] : []));
    this.updateDetectionBoxes();
    const frame = data.frame || {};
    const timestamp = ['video', 'camera'].includes(frame.source) ? ` · ${mediaTime(frame.source_timestamp_ms)}` : '';
    this.caption.textContent = `${state}${label ? ` · ${label}` : ''} · Frame ${frame.frame_id ?? 0}${timestamp} · ${data.width} × ${data.height}`;
  }

  stopped(label = 'Stopped') {
    if (this.last) this.render(this.last, {state: label});
  }
}
