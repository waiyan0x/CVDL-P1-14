/** Construct interface content without interpreting OCR or API strings as HTML. */
export function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : String(value));
  }
  node.append(...children.flat().filter(child => child !== null && child !== undefined));
  return node;
}

export const percent = value => Number.isFinite(value) ? `${Math.round(value * 100)}%` : '—';
export const milliseconds = value => Number.isFinite(value) ? `${Math.round(value)} ms` : '—';
export const engineName = id => ({easyocr: 'YOLO + EasyOCR', tesseract: 'YOLO + Tesseract', trocr: 'YOLO + fine-tuned TrOCR'}[id] || id);
export const mediaTime = value => {
  const seconds = Math.max(0, Number(value) || 0) / 1000;
  return `${Math.floor(seconds / 60)}:${(seconds % 60).toFixed(1).padStart(4, '0')}`;
};

export function message(container, title, text, {error = false, retry} = {}) {
  const box = el('div', {class: `message${error ? ' error' : ''}`}, el('strong', {}, title), el('span', {}, text));
  if (retry) box.append(el('button', {type: 'button', class: 'button primary', onclick: retry}, 'Try again'));
  container.replaceChildren(box);
}

export function setSegments(container, value) {
  container.querySelectorAll('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === value)));
}
