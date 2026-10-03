/**
 * Aegis Protocol — Unified Report Renderer (v3.8.0)
 * ==================================================
 * Renders a ``UnifiedReport`` JSON object (from any agent endpoint)
 * into the standard 8-section investigative layout:
 *
 *   WHAT'S HAPPENING?  →  report.summary
 *   KEY FINDINGS       →  report.findings[]
 *   EVIDENCE           →  report.evidence.{primary, independent, community}[]
 *   WHAT DISAGREES?    →  report.disagreements[]
 *   WHAT CHANGED?      →  report.changes[]
 *   TIMELINE           →  report.timeline[]
 *   WHY TRUST THIS?    →  report.trust.*
 *   NEXT STEPS         →  report.next_steps[]
 *
 * Usage:
 *   import { renderUnifiedReport } from './unified-report-renderer.js';
 *   const container = document.getElementById('reportMount');
 *   renderUnifiedReport(container, apiResponseJson);
 *
 * Missing-data placeholders (exact spec strings):
 *   Missing numeric  → "—"
 *   Missing string   → "Unknown"
 *   Missing URL      → "No source URL"
 *   Missing ID       → "Not available"
 *   Missing source   → "Authority uncalibrated"
 *   Missing count    → "Independence not established"
 *   Missing score    → "Confidence unavailable"
 */

'use strict';

// ─── Placeholder constants ────────────────────────────────────────────────────
const PH_NUM     = '—';
const PH_STR     = 'Unknown';
const PH_URL     = 'No source URL';
const PH_ID      = 'Not available';
const PH_AUTH    = 'Authority uncalibrated';
const PH_IND     = 'Independence not established';
const PH_CONF    = 'Confidence unavailable';

// Tensor axis display labels (exact order per spec)
const TENSOR_AXES = [
  { key: 'relevance',      label: 'Relevance' },
  { key: 'source_quality', label: 'Source Quality' },
  { key: 'independence',   label: 'Independence' },
  { key: 'primary_weight', label: 'Primary Weight' },
  { key: 'freshness',      label: 'Freshness' },
  { key: 'contradiction',  label: 'Contradiction' },
];

// ─── Utility helpers ──────────────────────────────────────────────────────────

/** Escape HTML to prevent XSS when inserting dynamic text. */
function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/** Format a value as a percentage string, or return placeholder. */
function pct(val) {
  if (val === null || val === undefined || val === '') return PH_NUM;
  const n = parseFloat(val);
  if (isNaN(n)) return PH_NUM;
  return `${Math.round(n * 100)}%`;
}

/** Render a section heading <h2> with standardized class. */
function sectionHeading(text) {
  return `<h2 class="ur-heading">${esc(text)}</h2>`;
}

/** Render a section wrapper with ID. */
function section(id, heading, content) {
  return `<section id="${id}" class="ur-section">${sectionHeading(heading)}${content}</section>`;
}

/** Render a <ul> list from an array of strings. Empty → placeholder bullet. */
function bulletList(items, emptyText) {
  if (!items || items.length === 0) {
    return `<ul class="ur-list"><li class="ur-list-empty">${esc(emptyText)}</li></ul>`;
  }
  const lis = items
    .filter(Boolean)
    .map(i => `<li>${esc(String(i))}</li>`)
    .join('');
  return `<ul class="ur-list">${lis}</ul>`;
}

// ─── Section renderers ────────────────────────────────────────────────────────

/** SECTION 1 — WHAT'S HAPPENING? */
function renderSummary(report) {
  const text = report.summary || '<em>No summary available.</em>';
  const content = `<p class="ur-summary">${esc(report.summary) || '<em>No summary available.</em>'}</p>`;
  return section('ur-summary', "WHAT'S HAPPENING?", content);
}

/** SECTION 2 — KEY FINDINGS */
function renderFindings(report) {
  const content = bulletList(report.findings, 'No significant findings.');
  return section('ur-findings', 'KEY FINDINGS', content);
}

/** SECTION 3 — EVIDENCE (Primary / Independent / Community) */
function renderEvidence(report) {
  const ev = report.evidence || {};
  const primary     = ev.primary     || [];
  const independent = ev.independent || [];
  const community   = ev.community   || [];

  const renderColumn = (items, label, emptyMsg) => {
    if (items.length === 0) {
      return `
        <div class="ur-ev-col">
          <h3 class="ur-ev-col-head">${esc(label)}</h3>
          <p class="ur-ev-empty">${esc(emptyMsg)}</p>
        </div>`;
    }
    const cards = items.map(renderEvidenceCard).join('');
    return `
      <div class="ur-ev-col">
        <h3 class="ur-ev-col-head">${esc(label)}</h3>
        <div class="ur-ev-cards">${cards}</div>
      </div>`;
  };

  const content = `
    <div class="ur-ev-grid">
      ${renderColumn(primary,     'Primary',     'No primary evidence found.')}
      ${renderColumn(independent, 'Independent', 'No independent evidence found.')}
      ${renderColumn(community,   'Community',   'No community evidence found.')}
    </div>`;

  return section('ur-evidence', 'EVIDENCE', content);
}

/** Render a single evidence card. */
function renderEvidenceCard(item) {
  const title   = esc(item.title   || PH_STR);
  const snippet = esc(item.snippet || '');
  const url     = item.url || null;
  const ts      = esc(item.timestamp || PH_STR);
  const srcName = esc((item.source && item.source.name) || PH_AUTH);
  const isPrim  = item.source && item.source.is_primary;
  const badge   = isPrim ? `<span class="ur-badge ur-badge--primary">Primary</span>` : '';

  const titleEl = url
    ? `<a class="ur-ev-title" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${title}</a>`
    : `<span class="ur-ev-title">${title}</span>`;

  const noUrl = url ? '' : `<span class="ur-ev-no-url">${PH_URL}</span>`;

  return `
    <article class="ur-ev-card">
      <div class="ur-ev-card-head">
        ${titleEl}${badge}${noUrl}
      </div>
      ${snippet ? `<p class="ur-ev-snippet">${snippet}</p>` : ''}
      <footer class="ur-ev-card-foot">
        <span class="ur-ev-source">${srcName}</span>
        <span class="ur-ev-ts">${ts}</span>
      </footer>
    </article>`;
}

/** SECTION 4 — WHAT DISAGREES? */
function renderDisagreements(report) {
  const items = (report.disagreements || []).map(d => `Contradictory evidence: ${d}`);
  const content = bulletList(items, 'No contradictory evidence detected.');
  return section('ur-disagreements', 'WHAT DISAGREES?', content);
}

/** SECTION 5 — WHAT CHANGED? */
function renderChanges(report) {
  const content = bulletList(report.changes, 'No new changes since last analysis.');
  return section('ur-changes', 'WHAT CHANGED?', content);
}

/** SECTION 6 — TIMELINE */
function renderTimeline(report) {
  const events = report.timeline || [];
  if (events.length === 0) {
    return section('ur-timeline', 'TIMELINE', '<p class="ur-empty">Timeline unavailable.</p>');
  }
  const ols = events
    .map(ev => {
      const ts  = esc(ev.timestamp || PH_STR);
      const desc = esc(ev.description || PH_STR);
      return `<li class="ur-tl-item"><span class="ur-tl-ts">${ts}</span><span class="ur-tl-desc">${desc}</span></li>`;
    })
    .join('');
  return section('ur-timeline', 'TIMELINE', `<ol class="ur-tl-list">${ols}</ol>`);
}

/** SECTION 7 — WHY TRUST THIS? */
function renderTrust(report) {
  const trust = report.trust || {};
  const qt    = trust.quality_tensor || {};
  const indCount = trust.independent_source_count;
  const tel  = trust.query_telemetry || {};

  // Quality tensor bars
  const axisRows = TENSOR_AXES.map(({ key, label }) => {
    const val = qt[key];
    const pctVal = pct(val);
    const barWidth = (val !== null && val !== undefined && !isNaN(parseFloat(val)))
      ? `${Math.round(parseFloat(val) * 100)}%`
      : '0%';
    return `
      <div class="ur-qt-axis quality-axis" data-axis="${esc(key)}">
        <span class="ur-qt-label label">${esc(label)}</span>
        <div class="ur-qt-bar-wrap">
          <div class="ur-qt-bar" style="width:${barWidth}"></div>
        </div>
        <span class="ur-qt-value value">${pctVal}</span>
      </div>`;
  }).join('');

  // Source count
  const indText = indCount !== null && indCount !== undefined
    ? `Evidence collected from <strong>${esc(String(indCount))}</strong> independent publisher${indCount !== 1 ? 's' : ''}.`
    : `<span class="ur-trust-ph">${PH_IND}</span>`;

  // Query telemetry
  const succeeded = tel.queries_succeeded ?? PH_NUM;
  const total     = tel.queries_submitted  ?? PH_NUM;
  const channels  = new Set(
    (tel.execution_log || []).map(q => q.channel).filter(Boolean)
  ).size || PH_NUM;
  const authReq   = tel.queries_auth_required || 0;
  const failed    = tel.queries_failed || 0;

  const telRow = authReq > 0
    ? `<p class="ur-trust-note">(*) ${authReq} unauthenticated lookup(s) used due to missing API credentials.</p>`
    : '';
  const failRow = failed > 0
    ? `<p class="ur-trust-note">⚠ ${failed} quer${failed !== 1 ? 'ies' : 'y'} failed during retrieval.</p>`
    : '';

  const content = `
    <div class="ur-trust-inner">
      <div class="ur-qt-section">
        <h3 class="ur-trust-sub">Quality</h3>
        <div class="ur-qt-axes">${axisRows}</div>
      </div>
      <div class="ur-sources-section">
        <h3 class="ur-trust-sub">Sources</h3>
        <p class="ur-sources-text independence">${indText}</p>
      </div>
      <div class="ur-telemetry-section">
        <h3 class="ur-trust-sub">Query Coverage</h3>
        <p class="ur-tel-text">
          ⚙️ ${esc(String(succeeded))} / ${esc(String(total))} queries succeeded across ${esc(String(channels))} channel${channels !== 1 ? 's' : ''}.
        </p>
        ${telRow}${failRow}
      </div>
    </div>`;

  return section('ur-trust', 'WHY TRUST THIS?', content);
}

/** SECTION 8 — NEXT STEPS */
function renderNextSteps(report) {
  const content = bulletList(report.next_steps, 'No further actions suggested.');
  return section('ur-next-steps', 'NEXT STEPS', content);
}

// ─── Main export ──────────────────────────────────────────────────────────────

/**
 * Render a UnifiedReport into a DOM container element.
 *
 * @param {HTMLElement} container  Target mount point.
 * @param {Object}      report     The JSON report from any agent endpoint.
 */
function renderUnifiedReport(container, report) {
  if (!container) {
    console.warn('[Aegis] renderUnifiedReport: no container element provided');
    return;
  }
  if (!report || typeof report !== 'object') {
    container.innerHTML = `<p class="ur-error">No report data available.</p>`;
    return;
  }

  const html = [
    renderSummary(report),
    renderFindings(report),
    renderEvidence(report),
    renderDisagreements(report),
    renderChanges(report),
    renderTimeline(report),
    renderTrust(report),
    renderNextSteps(report),
  ].join('\n');

  container.innerHTML = `<div class="unified-report">${html}</div>`;

  // Expand/collapse on mobile — toggle .ur-section.collapsed on heading click
  container.querySelectorAll('.ur-heading').forEach(h2 => {
    h2.setAttribute('tabindex', '0');
    h2.setAttribute('role', 'button');
    h2.setAttribute('aria-expanded', 'true');
    h2.addEventListener('click', () => {
      const sec = h2.closest('.ur-section');
      if (!sec) return;
      const isCollapsed = sec.classList.toggle('ur-collapsed');
      h2.setAttribute('aria-expanded', String(!isCollapsed));
    });
    h2.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); h2.click(); }
    });
  });
}

/**
 * Convenience: fetch a report from ``url`` and render it.
 *
 * @param {HTMLElement} container
 * @param {string}      url        Full API URL (e.g. /api/claims/verify?q=…)
 * @param {HTMLElement} [spinner]  Optional spinner element to hide on load.
 */
async function fetchAndRenderReport(container, url, spinner) {
  try {
    if (spinner) spinner.style.display = 'block';
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
      container.innerHTML = `<p class="ur-error">${esc(err.error || `Server error ${res.status}`)}</p>`;
      return;
    }
    const data = await res.json();
    renderUnifiedReport(container, data);
  } catch (e) {
    container.innerHTML = `<p class="ur-error">Failed to load report: ${esc(String(e))}</p>`;
  } finally {
    if (spinner) spinner.style.display = 'none';
  }
}

// ─── Browser / Node Export ───────────────────────────────────────────────────
if (typeof window !== 'undefined') {
  window.renderUnifiedReport = renderUnifiedReport;
  window.fetchAndRenderReport = fetchAndRenderReport;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { renderUnifiedReport, fetchAndRenderReport };
}

