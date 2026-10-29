import {el} from '../core/dom.js';

const pages = [['/detect', 'Detect'], ['/live', 'Live'], ['/evaluation', 'Evaluation'], ['/models', 'Models & Method']];
const current = location.pathname === '/' ? '/detect' : location.pathname;
const header = document.querySelector('[data-header]');
if (header) {
  const mark = el('span', {class: 'brand-mark', 'aria-hidden': 'true'});
  mark.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="4.5" y="2" width="15" height="17" rx="3"/><path d="M4.5 10.5h15M7.5 6h5.5M15.5 6h1M7.5 19v2.5M16.5 19v2.5M2.5 8.5v3M21.5 8.5v3"/><circle cx="8" cy="15.5" r="1" fill="white"/><circle cx="16" cy="15.5" r="1" fill="white"/></svg>';
  const nav = el('nav', {class: 'nav', 'aria-label': 'Primary'}, el('a', {class: 'brand', href: '/detect'}, mark, 'EDS Reader'));
  pages.forEach(([href, label]) => nav.append(el('a', {href, 'aria-current': href === current ? 'page' : null}, label)));
  header.replaceChildren(nav);
}
