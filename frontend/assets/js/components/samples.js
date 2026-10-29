import {request} from '../core/api.js';
import {el} from '../core/dom.js';

export async function loadSamples(container, onSelect) {
  const samples = await request('/api/samples');
  const buttons = [];
  samples.slice(0, 4).forEach((sample, index) => {
    const button = el('button', {type: 'button', class: 'sample', 'aria-pressed': 'false', onclick: () => {
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      onSelect(sample);
    }}, el('img', {src: sample.url, alt: '', loading: 'lazy'}), el('span', {}, sample.name),
    sample.description ? el('span', {class: 'sample-description'}, sample.description) : null);
    buttons.push(button);
  });
  container.replaceChildren(...buttons);
  return {samples, select(index) { buttons[index]?.click(); }, clear() { buttons.forEach(item => item.setAttribute('aria-pressed', 'false')); }};
}

export function dropFiles(zone, input, callback) {
  input.addEventListener('change', () => { if (input.files[0]) callback(input.files[0]); });
  zone.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('dragging'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
  zone.addEventListener('drop', event => {
    event.preventDefault();
    zone.classList.remove('dragging');
    if (event.dataTransfer.files[0]) callback(event.dataTransfer.files[0]);
  });
}
