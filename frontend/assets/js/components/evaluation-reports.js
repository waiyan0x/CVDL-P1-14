import {el, engineName, milliseconds, percent} from '../core/dom.js';
import {facts, list, table} from './research.js';

function identity(report) {
  const dataset = report.dataset || {};
  return facts([
    ['Run', report.run_id], ['Created', report.created_at], ['Dataset', dataset.id], ['Split', dataset.split],
    ['Images', dataset.image_count ?? dataset.evaluated_images],
  ]);
}

export function detectionReport(report) {
  const card = el('section', {class: 'panel research-card'}, el('h3', {}, 'Measured detector results'));
  card.append(identity(report));
  const detector = report.detector || {};
  card.append(el('p', {}, `Classes ${(detector.classes || []).join(', ')} only. ${report.dataset?.label_review || 'Uses bundled annotations; these annotations have not been independently re-reviewed.'}`));
  if (detector.path) card.append(el('code', {}, detector.path));
  const metrics = report.metrics || {};
  card.append(facts([
    ['Precision', percent(metrics.precision)], ['Recall', percent(metrics.recall)],
    ['mAP@0.50', percent(metrics.map_50)], ['mAP@0.50–0.95', percent(metrics.map_50_95)],
    ['Whole EDS mAP', metrics.whole_eds_map == null ? 'Not measured' : percent(metrics.whole_eds_map)],
  ]));
  if (metrics.speed_ms_per_image) card.append(facts(Object.entries(metrics.speed_ms_per_image).map(([key, value]) => [`${key} / image`, milliseconds(value)])));
  const settings = report.protocol?.settings || {};
  const hardware = report.hardware || {};
  card.append(facts([
    ['Settings', Object.entries(settings).map(([key, value]) => `${key}=${Array.isArray(value) ? value.join(',') : value}`).join(' · ') || 'Recorded in report'],
    ['Hardware', [hardware.system || hardware.platform, hardware.machine, hardware.device || settings.device].filter(Boolean).join(' · ') || 'Recorded in report'],
    ['Excluded images', report.dataset?.excluded?.length ?? 0],
  ]));
  if (report.evidence_status) card.append(el('p', {}, report.evidence_status));
  card.append(list(report.limitations || []));
  return card;
}

export function ocrReport(report) {
  const card = el('section', {class: 'panel research-card'}, el('h3', {}, 'Reviewed transcription benchmark'), identity(report));
  const engines = Object.entries(report.engines || {});
  card.append(table(['Pipeline', 'Status', 'Measured metrics'], engines.map(([engine, result]) => [engineName(engine), result.status,
    result.metrics ? Object.entries(result.metrics).filter(([, value]) => typeof value === 'number').map(([key, value]) => `${key.replaceAll('_', ' ')}: ${Number(value).toFixed(3)}`).join(' · ') : 'Not measured'])));
  if (report.protocol?.latency) card.append(el('p', {}, report.protocol.latency));
  if (report.evidence_status) card.append(el('p', {}, report.evidence_status));
  card.append(list(report.limitations || []));
  return card;
}
