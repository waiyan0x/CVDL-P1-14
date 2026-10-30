import {health} from '../core/api.js';
import {el} from '../core/dom.js';

const defaults = {backend: 'easyocr', detection: .3, ocr_threshold: .25, similarity: .7};
export class Options {
  constructor(container, onChange = () => {}, {comparison = false} = {}) {
    this.values = {...defaults};
    try { Object.assign(this.values, JSON.parse(localStorage.getItem('eds-options') || '{}')); } catch {}
    if (!['easyocr', 'tesseract', 'trocr'].includes(this.values.backend)) this.values.backend = defaults.backend;
    for (const key of ['detection', 'ocr_threshold', 'similarity']) {
      const value = Number(this.values[key]);
      this.values[key] = Number.isFinite(value) ? Math.max(key === 'detection' ? .05 : 0, Math.min(key === 'detection' ? .95 : 1, value)) : defaults[key];
    }
    const details = el('details', {class: 'options'}, el('summary', {}, 'Advanced settings'));
    const grid = el('div', {class: 'options-grid'});
    if (!comparison) {
      this.engine = el('select', {'aria-label': 'OCR engine'});
      [['easyocr', 'EasyOCR'], ['tesseract', 'Tesseract'], ['trocr', 'Fine-tuned TrOCR']].forEach(([id, name]) => this.engine.append(el('option', {value: id}, name)));
      this.engine.value = this.values.backend;
      this.engine.addEventListener('change', () => this.change('backend', this.engine.value, onChange));
      grid.append(el('label', {class: 'control'}, 'OCR engine', this.engine));
    }
    [['detection', 'Detection threshold'], ['ocr_threshold', 'OCR threshold'], ['similarity', 'Matching threshold']].forEach(([name, title]) => {
      const value = el('output', {}, `${Math.round(this.values[name] * 100)}%`);
      const slider = el('input', {type: 'range', min: name === 'detection' ? 5 : 0, max: name === 'detection' ? 95 : 100, step: 1, value: this.values[name] * 100, 'aria-label': title});
      slider.addEventListener('input', () => { value.value = `${slider.value}%`; });
      slider.addEventListener('change', () => this.change(name, Number(slider.value) / 100, onChange));
      grid.append(el('label', {class: 'control'}, el('span', {class: 'range-label'}, title, value), slider));
    });
    details.append(grid);
    container.replaceChildren(details);
  }

  change(name, value, onChange) {
    this.values[name] = value;
    try { localStorage.setItem('eds-options', JSON.stringify(this.values)); } catch {}
    onChange();
  }

  async initialise() {
    const status = await health();
    if (this.engine) {
      [...this.engine.options].forEach(option => {
        option.disabled = !status.backends.includes(option.value);
        if (option.disabled) option.textContent += ' · unavailable';
      });
      if (!status.backends.includes(this.values.backend)) {
        this.values.backend = status.default_backend || status.backends[0];
        this.engine.value = this.values.backend;
      }
    }
    if (!status.ready) throw new Error(status.error || 'Models are still starting. Please try again shortly.');
    return status;
  }

  get() { return {...this.values}; }
}
