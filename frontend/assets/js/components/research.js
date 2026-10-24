import {el} from '../core/dom.js';

export function section(title, ...children) {
  return el('section', {class: 'stack', 'aria-label': title}, el('h2', {}, title), ...children);
}

export function facts(entries) {
  return el('dl', {class: 'facts'}, ...entries.flatMap(([key, value]) => [el('dt', {}, key), el('dd', {}, value === null || value === undefined ? 'Not measured' : String(value))]));
}

export function list(values) {
  const items = Array.isArray(values) ? values : values ? [values] : [];
  return el('ul', {class: 'text-list'}, ...items.map(value => el('li', {}, String(value))));
}

export function table(headings, rows) {
  return el('div', {class: 'table-wrap'}, el('table', {},
    el('thead', {}, el('tr', {}, ...headings.map(heading => el('th', {scope: 'col'}, heading)))),
    el('tbody', {}, ...rows.map(row => el('tr', {}, ...row.map(value => el('td', {}, value === null || value === undefined ? 'Not measured' : String(value))))))));
}
