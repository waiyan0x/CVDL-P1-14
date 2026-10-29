import {el, mediaTime} from '../core/dom.js';

export function fieldNumbers(data) {
  const mapping = new Map();
  let number = 1;
  for (const result of data.results || []) {
    for (const label of ['bus_number', 'destination']) {
      const field = result.fields?.[label];
      if (field) mapping.set(field.id, number++);
    }
  }
  return mapping;
}

export class Viewer {
  constructor(container, caption) { this.container = container; this.caption = caption; this.last = null; }

  clear(text = '') {
    this.last = null;
    this.container.replaceChildren();
    this.container.hidden = true;
    this.caption.textContent = text;
  }

  preview(url, label) {
    this.container.hidden = false;
    this.container.replaceChildren(el('img', {src: url, alt: label}));
    this.caption.textContent = label;
  }

  render(data, {numbers = fieldNumbers(data), state = 'Processed', label = '', idPrefix = ''} = {}) {
    this.last = data;
    this.container.hidden = false;
    const image = el('img', {src: data.image, alt: 'Processed frame with numbered detected regions', width: data.width, height: data.height});
    const fragment = document.createDocumentFragment();
    fragment.append(image);
    const detections = [...data.detections].sort((a, b) => Number(b.label === 'eds') - Number(a.label === 'eds'));
    for (const detection of detections) {
      const [x1, y1, x2, y2] = detection.box;
      const estimated = detection.source === 'field_union';
      const screen = detection.label === 'eds';
      const number = numbers.get(detection.id);
      const box = el(number ? 'a' : 'span', {
        class: `box${estimated ? ' estimated' : ''}${screen ? ' screen' : ''}`,
        href: number ? `#result-${idPrefix}${detection.id}` : null,
        'aria-label': number ? `Region ${number}, ${detection.label === 'bus_number' ? 'service number' : 'destination'}: go to result` : null,
        'aria-hidden': number ? null : 'true',
      }, el('span', {class: 'box-number'}, screen ? `EDS${estimated ? ' · estimated' : ''}` : String(number || '')));
      Object.assign(box.style, {left: `${x1 / data.width * 100}%`, top: `${y1 / data.height * 100}%`, width: `${(x2 - x1) / data.width * 100}%`, height: `${(y2 - y1) / data.height * 100}%`});
      fragment.append(box);
    }
    this.container.replaceChildren(fragment);
    const frame = data.frame || {};
    const timestamp = ['video', 'camera'].includes(frame.source) ? ` · ${mediaTime(frame.source_timestamp_ms)}` : '';
    this.caption.textContent = `${state}${label ? ` · ${label}` : ''} · Frame ${frame.frame_id ?? 0}${timestamp} · ${data.width} × ${data.height}`;
  }

  stopped(label = 'Stopped') {
    if (this.last) this.render(this.last, {state: label});
  }
}
