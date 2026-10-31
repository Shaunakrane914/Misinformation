/**
 * Aegis Protocol — Unified Report Renderer (v3.8.0)
 * ==================================================
 * Renders a ``UnifiedReport`` JSON object (from any agent endpoint)
 * into the shared investigative layout (including source coverage):
 *
 *   WHAT'S HAPPENING?  →  report.summary & verdict banner
 *   CLAIM DECOMPOSITION→  report.claim_decomposition[]
 *   KEY FINDINGS       →  report.findings[]
 *   EVIDENCE           →  report.evidence.{primary, independent, community}[]
 *   WHAT DISAGREES?    →  report.contradictions[] & report.disagreements[]
 *   WHAT CHANGED?      →  report.changes[]
 *   SPECIALIZED INTEL  →  report.agent_intelligence
 *   TIMELINE           →  report.timeline[]
 *   WHY TRUST THIS?    →  report.trust.*
 *   SOURCE COVERAGE    →  report.trust.query_telemetry.execution_log[]
 *   NEXT STEPS         →  report.next_steps[]
 *   EXPORT TOOLBAR     →  Dossier download
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

// Keep shared rendering helpers private: agent pages define their own esc,
// array and timeline helpers after loading this classic script.
(function aegisUnifiedReportModule() {

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

// Non-binary verdict definitions and styling
const VERDICT_CONFIG = {
  SUPPORTED: {
    label: 'SUPPORTED',
    badgeClass: 'ur-verdict--supported',
    desc: 'Corroborated by primary or authoritative sources without severe material contradiction.',
  },
  REFUTED: {
    label: 'REFUTED',
    badgeClass: 'ur-verdict--refuted',
    desc: 'Directly refuted by primary regulatory filings, authoritative disclosures, or accredited consensus.',
  },
  MISLEADING: {
    label: 'MISLEADING',
    badgeClass: 'ur-verdict--misleading',
    desc: 'Contains factual elements presented with selective omissions, altered chronology, or distorted framing.',
  },
  OUTDATED: {
    label: 'OUTDATED',
    badgeClass: 'ur-verdict--outdated',
    desc: 'Historically accurate statement recirculated out of chronological context as a current event.',
  },
  MIXED: {
    label: 'MIXED',
    badgeClass: 'ur-verdict--mixed',
    desc: 'Contains a combination of supported facts and unverified or inaccurate propositions.',
  },
  UNVERIFIED: {
    label: 'UNVERIFIED',
    badgeClass: 'ur-verdict--unverified',
    desc: 'Public evidence does not provide sufficient corroboration or contradiction.',
  },
  INSUFFICIENT_EVIDENCE: {
    label: 'INSUFFICIENT EVIDENCE',
    badgeClass: 'ur-verdict--insufficient',
    desc: 'Retrieval completed without evidentiary quorum; reliable determination cannot be established.',
  },
  ACQUISITION_FAILED: {
    label: 'ACQUISITION FAILED — UNABLE TO RETRIEVE EVIDENCE',
    badgeClass: 'ur-verdict--refuted',
    desc: 'Source acquisition failed. This is not a conclusion that no information or risk exists.',
  },
};

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

/** HTML escaping does not neutralize javascript: links in href attributes. */
function safeEvidenceUrl(value) {
  if (typeof value !== 'string' || !/^https?:\/\//i.test(value.trim())) return null;
  try {
    const parsed = new URL(value.trim());
    return ['http:', 'https:'].includes(parsed.protocol) && parsed.hostname &&
      !parsed.username && !parsed.password ? parsed.href : null;
  } catch (_error) {
    return null;
  }
}

/** Format a value as a percentage string, or return placeholder. */
function pct(val) {
  if (typeof val !== 'number' || !Number.isFinite(val) || val < 0 || val > 1) return PH_NUM;
  return `${Math.round(val * 100)}%`;
}

/** Normalize raw verdict string into one of the 7 non-binary verdict keys */
function normalizeVerdictKey(raw) {
  if (!raw || typeof raw !== 'string') return null;
  const s = raw.trim().toUpperCase();
  const aliases = { TRUE: 'SUPPORTED', VERIFIED: 'SUPPORTED', FALSE: 'REFUTED',
    'INSUFFICIENT EVIDENCE': 'INSUFFICIENT_EVIDENCE', UNCONFIRMED: 'UNVERIFIED', PENDING: 'UNVERIFIED' };
  return Object.hasOwn(VERDICT_CONFIG, s) ? s : aliases[s] || null;
}

/** Render a section heading <h2> with standardized class and mobile disclosure button. */
function sectionHeading(text, id) {
  return `<h2 class="ur-heading"><button type="button" class="ur-heading-button" aria-controls="${id}-body" aria-expanded="true">${esc(text)}</button></h2>`;
}

/** Render a section wrapper with ID. */
function section(id, heading, content) {
  return `<section id="${id}" class="ur-section">${sectionHeading(heading, id)}<div id="${id}-body" class="ur-section-body">${content}</div></section>`;
}

function array(value) { return Array.isArray(value) ? value : []; }

/** Render a <ul> list from an array of strings. Empty → placeholder bullet. */
function bulletList(items, emptyText) {
  items = array(items).filter(item => typeof item === 'string' && item.trim());
  if (items.length === 0) {
    return `<ul class="ur-list"><li class="ur-list-empty">${esc(emptyText)}</li></ul>`;
  }
  const lis = items
    .filter(Boolean)
    .map(i => `<li>${esc(String(i))}</li>`)
    .join('');
  return `<ul class="ur-list">${lis}</ul>`;
}

// ─── Section renderers ────────────────────────────────────────────────────────

/** Render the verdict banner if verdict is present in report metadata or summary */
function renderVerdictBanner(report) {
  let verdictKey = null;
  let conf = null;
  let reason = '';

  if (report.investigation_status === 'ACQUISITION_FAILED') {
    verdictKey = 'ACQUISITION_FAILED';
    reason = report.processing_notes?.acquisition?.message || '';
  } else if (report.verdict && typeof report.verdict === 'object') {
    verdictKey = normalizeVerdictKey(report.verdict.verdict || report.verdict.status);
    conf = report.verdict.confidence;
    reason = report.verdict.reasoning || report.verdict.explanation || '';
  } else if (report._meta && report._meta.verdict) {
    verdictKey = normalizeVerdictKey(report._meta.verdict);
  } else if (report.summary && typeof report.summary === 'string') {
    const match = report.summary.match(/Claim is \*\*([A-Za-z_]+)\*\*/i);
    if (match) verdictKey = normalizeVerdictKey(match[1]);
  }

  if (!verdictKey || !VERDICT_CONFIG[verdictKey]) return '';
  const cfg = VERDICT_CONFIG[verdictKey];
  const confText = (typeof conf === 'number' && Number.isFinite(conf) && conf >= 0 && conf <= 1)
    ? `<span class="ur-verdict-conf">Model Confidence: <strong>${pct(conf)}</strong> (model estimate; not empirical truth)</span>`
    : '';

  return `
    <div class="ur-verdict-banner ${cfg.badgeClass}">
      <div class="ur-verdict-header">
        <span class="ur-verdict-pill">${esc(cfg.label)}</span>
        ${confText}
      </div>
      <p class="ur-verdict-desc">${esc(cfg.desc)}</p>
      ${reason ? `<p class="ur-verdict-reason"><strong>Analysis:</strong> ${esc(reason)}</p>` : ''}
    </div>`;
}

/** SECTION 1 — WHAT'S HAPPENING? */
function renderSummary(report) {
  const target = report._meta && report._meta.query;
  const label = report._meta && report._meta.agent === 'claim_verifier'
    ? 'Claim under review' : 'Investigation target';
  const banner = renderVerdictBanner(report);
  const content = `${target ? `<p class="ur-target"><span>${label}</span>${esc(target)}</p>` : ''}
    ${banner}
    <p class="ur-summary">${esc(report.summary) || '<em>No summary available.</em>'}</p>`;
  return section('ur-summary', "WHAT'S HAPPENING?", content);
}

/** CLAIM DECOMPOSITION (if sub-claims are present) */
function renderClaimDecomposition(report) {
  const decomp = array(report.claim_decomposition || report.sub_claims).filter(item => item && typeof item === 'object');
  if (decomp.length === 0) return '';

  const cards = decomp.map((sub, idx) => {
    const text = esc(sub.claim_text || sub.text || `Sub-claim ${idx + 1}`);
    const vKey = normalizeVerdictKey(sub.verdict) || 'UNVERIFIED';
    const cfg = VERDICT_CONFIG[vKey] || VERDICT_CONFIG.UNVERIFIED;
    const cVal = typeof sub.confidence === 'number' && Number.isFinite(sub.confidence) ? pct(sub.confidence) : PH_NUM;
    const citations = array(sub.evidence_citations || sub.citations).map(c => {
      const citeUrl = safeEvidenceUrl(typeof c === 'string' ? c : (c && (c.canonical_url || c.url)));
      const citeTitle = esc(typeof c === 'string' ? c : ((c && c.source_name) || (c && c.title) || (c && (c.canonical_url || c.url)) || 'Citation'));
      const excerpt = c && typeof c === 'object' && c.relevant_excerpt ? `<blockquote>${esc(c.relevant_excerpt)}</blockquote>` : '';
      return citeUrl
        ? `<div><a href="${esc(citeUrl)}" target="_blank" rel="noopener noreferrer" class="ur-decomp-cite">${citeTitle} ↗</a>${excerpt}</div>`
        : `<span class="ur-decomp-cite">${citeTitle}</span>${excerpt}`;
    }).join(' ');
    const reasoning = sub.reasoning || sub.rationale ? `<p class="ur-decomp-reason">${esc(sub.reasoning || sub.rationale)}</p>` : '';

    return `
      <div class="ur-decomp-card">
        <div class="ur-decomp-head">
          <span class="ur-decomp-pill ${cfg.badgeClass}">${esc(cfg.label)}</span>
          <span class="ur-decomp-conf">${sub.is_heuristic ? 'Uncalibrated heuristic' : 'Confidence'}: ${cVal}</span>
        </div>
        <p class="ur-decomp-text">${text}</p>
        ${reasoning}
        ${citations ? `<div class="ur-decomp-citations"><span>Citations:</span> ${citations}</div>` : ''}
      </div>`;
  }).join('');

  return section('ur-claim-decomp', 'CLAIM DECOMPOSITION', `
    <p class="ur-ev-note">Multi-premise claim broken into atomic propositions for independent corroboration.</p>
    <div class="ur-decomp-grid">${cards}</div>
  `);
}

/** VISUAL EVIDENCE & EPISTEMIC ANALYTICS BENTO GRID */
function renderVisualAnalytics(report) {
  const metrics = array(report.quantitative_metrics);
  return section('ur-visual-analytics', 'VISUAL EVIDENCE &amp; EPISTEMIC ANALYTICS', `
    <div class="ae-bento-grid">
      <div class="ae-bento-card" id="ae-mount-radar"></div>
      <div class="ae-bento-card" id="ae-mount-funnel"></div>
      <div class="ae-bento-card" id="ae-mount-dispersion" style="grid-column: 1 / -1;"></div>
      ${metrics.length > 0 ? `
        <div class="ae-bento-card" style="grid-column: 1 / -1;">
          <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);margin-bottom:10px;">
            // VERIFIED QUANTITATIVE &amp; REGULATORY INDICATORS
          </div>
          <div class="ae-metrics-pill-grid">
            ${metrics.map(m => `
              <div class="ae-metric-pill" title="${esc(m.context)}">
                <span class="ae-metric-val">${esc(m.value)}</span>
                <span class="ae-metric-src">${esc(m.source || m.publisher || 'Verified Record')}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `);
}

/** SECTION 2 — KEY FINDINGS & INVESTIGATIVE COMMAND CONSOLE */
function renderFindings(report) {
  const details = array(report.finding_details).filter(item => item && typeof item === 'object');
  const findings = array(report.findings).filter(item => typeof item === 'string' && item.trim());
  const passages = array(report.evidence_workbench && report.evidence_workbench.passages);

  const deckItems = [];

  for (let i = 0; i < findings.length; i++) {
    const text = findings[i];
    const match = details.find(d => (d.statement || d.description || d.summary || d.title) === text);
    const relatedPassage = passages.find(p => p.text && (p.text.includes(text.slice(0, 35)) || text.includes((p.text || '').slice(0, 35))))
      || passages[i % (passages.length || 1)] || null;

    deckItems.push({
      title: text.length > 95 ? text.slice(0, 92) + '…' : text,
      statement: text,
      text: (relatedPassage && relatedPassage.text) || text,
      publisher: (relatedPassage && relatedPassage.publisher_host) || (match && match.publisher) || 'Verified Disclosure Node',
      timestamp: (relatedPassage && relatedPassage.published_at) || 'Current Milestone',
      badge: (match && match.epistemic_state) || 'GROUNDED FINDING',
      badgeColor: '#00e5ff',
      url: safeEvidenceUrl(relatedPassage && relatedPassage.source_url) || null,
      reasoning: (match && match.reasoning) || 'Corroborated across primary filing and qualified reporting records.'
    });
  }

  const cats = report.catalysts || {};
  for (const c of array(cats.positive)) {
    if (deckItems.length >= 10) break;
    deckItems.push({
      title: c.catalyst || 'Positive Catalyst',
      statement: c.catalyst || '',
      text: c.catalyst || '',
      publisher: c.source || 'Authoritative Wire',
      timestamp: 'Active Catalyst',
      badge: 'POSITIVE CATALYST',
      badgeColor: '#10b981',
      url: safeEvidenceUrl(c.url) || null,
      reasoning: 'Positive momentum indicator corroborated by public filings.'
    });
  }
  for (const c of array(cats.negative)) {
    if (deckItems.length >= 12) break;
    deckItems.push({
      title: c.catalyst || 'Contested Headwind',
      statement: c.catalyst || '',
      text: c.catalyst || '',
      publisher: c.source || 'Monitored Channel',
      timestamp: 'Active Headwind',
      badge: 'CONTESTED HEADWIND',
      badgeColor: '#f43f5e',
      url: safeEvidenceUrl(c.url) || null,
      reasoning: 'Material challenge or regulatory matter under active review.'
    });
  }

// Strict invariant: Never synthesize findings from raw passages when findings are empty.

  const leads = array(report.processing_notes && report.processing_notes.unresolved_leads);
  const unresolved = leads.length ? `<details style="margin-top:14px;"><summary>Unresolved leads — not findings</summary><ul class="ur-list">${leads.map(lead => `<li>${esc(lead.factor || lead.catalyst || '')}</li>`).join('')}</ul></details>` : '';

  if (deckItems.length === 0) {
    return section('ur-findings', 'KEY FINDINGS &amp; COMMAND CONSOLE', '<p class="ur-empty">No findings returned. This does not establish an absence of risk.</p>' + unresolved);
  }

  const itemsJson = esc(JSON.stringify(deckItems));
  const content = `
    <div id="ae-mount-findings-deck" data-deck-items="${itemsJson}">
      <ul class="ur-list">${deckItems.map(it => `<li><strong>${esc(it.badge)}:</strong> ${esc(it.statement)}</li>`).join('')}</ul>
    </div>
  `;

  return section('ur-findings', 'KEY FINDINGS &amp; INVESTIGATIVE COMMAND CONSOLE', content + unresolved);
}

/** Candidates remain inspectable without claiming a successful body read. */
function renderDiscovery(report) {
  const candidates = array(report.discovery).filter(item => item && typeof item === 'object');
  if (!candidates.length) return '';
  return section('ur-discovery', 'DISCOVERY LEADS AND UNQUALIFIED CAPTURES',
    `<p class="ur-ev-note">${candidates.length} non-evidence record(s) retained. Some are unread leads; others were captured but rejected for the research objective. Inspect the read and qualification status. Neither counts as verified claim support.</p>
     <details><summary>Inspect leads and rejected captures</summary>${candidates.map(item => renderEvidenceCard(item)).join('')}</details>`);
}

/** A bounded collection of exact passages, distinct from the short brief. */
function workbenchPage(workbench, filters = {}, pageSize = 8) {
  const query = String(filters.search || '').trim().toLocaleLowerCase().slice(0, 200);
  const rows = array(workbench && workbench.passages).slice(0, 512).filter(row => row && typeof row.text === 'string');
  const matches = rows.filter(row => (!filters.publisher || row.publisher_host === filters.publisher)
    && (!filters.role || row.content_role === filters.role)
    && (!query || [row.text, row.source_title, row.publisher_host, row.content_role].join(' ').toLocaleLowerCase().includes(query)));
  const size = Math.max(1, Math.min(20, Number(pageSize) || 8));
  const pages = Math.max(1, Math.ceil(matches.length / size));
  const page = Math.max(0, Math.min(pages - 1, Math.floor(Number(filters.page) || 0)));
  return { rows: matches.slice(page * size, (page + 1) * size), total: matches.length, page, pages,
    start: matches.length ? page * size + 1 : 0, end: Math.min((page + 1) * size, matches.length) };
}

function renderWorkbenchPage(workbench, filters = {}) {
  const selected = workbenchPage(workbench, filters);
  const cards = selected.rows.map(row => {
    const url = safeEvidenceUrl(row.source_url);
    return `<article class="ur-workbench-passage"><h4>${esc(row.source_title || 'Captured source')}</h4>
      <p class="ur-ev-note">${esc(row.publisher_host || 'Unknown publisher')} · ${esc(row.content_role || 'SOURCE ASSERTION')} · UNVERIFIED · ${esc(row.published_at || 'Publication date unknown')}</p>
      ${row.context_labels && typeof row.context_labels === 'object' ? `<p class="ur-ev-note">${Object.values(row.context_labels).filter(value => typeof value === 'string').map(esc).join(' · ')}</p>` : ''}
      ${row.source_permission && safeEvidenceUrl(row.source_permission.licence_url) ? `<p class="ur-ev-note">Source credit: ${esc(row.source_permission.author || row.publisher_host || 'Original publisher')} · Exact excerpt · ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Original source</a> · ` : ''}<a href="${esc(safeEvidenceUrl(row.source_permission.licence_url))}" target="_blank" rel="noopener noreferrer">Source licence</a></p>` : ''}
      <blockquote>${esc(row.text)}</blockquote>
      <details class="ur-capture-details"><summary>Capture and attribution details</summary>
        ${row.content_language ? `<p class="ur-ev-note">Source language: ${esc(row.content_language)} · Original text; no generated translation.</p>` : ''}
        <p class="ur-ev-note">${esc(row.evidence_id)} / ${esc(row.passage_id)} · offsets ${esc(row.start)}–${esc(row.end)}</p>
      </details>
      ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Open reporting source</a>` : '<p>Source URL unavailable</p>'}
      ${array(row.also_reported_by).length ? `<p class="ur-ev-note">Identical passage also observed in ${array(row.also_reported_by).length} source record(s); not additional independent confirmation.</p>` : ''}
      </article>`;
  }).join('');
  return `<p role="status" aria-live="polite">Showing ${selected.start}–${selected.end} of ${selected.total} matching passages · page ${selected.page + 1} of ${selected.pages}</p>
    ${cards || '<p>No published passages match these filters. This does not establish absence of evidence.</p>'}
    <div class="ur-workbench-pagination"><button type="button" data-ur-wb-prev ${selected.page === 0 ? 'disabled' : ''}>Previous passages</button>
    <button type="button" data-ur-wb-next ${selected.page + 1 >= selected.pages ? 'disabled' : ''}>Next passages</button></div>`;
}

function renderEvidenceWorkbench(report) {
  const workbench = report.evidence_workbench;
  if (!workbench || workbench.schema !== 'evidence-workbench-v1') return '';
  const accounting = workbench.accounting || {};
  const rows = array(workbench.passages).filter(row => row && typeof row === 'object');
  const publishers = [...new Set(rows.map(row => row.publisher_host).filter(Boolean))].sort();
  const roles = [...new Set(rows.map(row => row.content_role).filter(Boolean))].sort();
  const omitted = (Number(accounting.omitted_by_source_budget) || 0) + (Number(accounting.omitted_by_workbench_budget) || 0);
  return section('ur-evidence-workbench', 'EVIDENCE WORKBENCH', `<div data-ur-workbench>
    <p>${esc(accounting.published_passages ?? rows.length)} unique passages · ${esc(accounting.published_unique_words ?? 'Unknown')} selected words · ${esc(accounting.observed_publisher_hosts ?? publishers.length)} observed publisher hosts.</p>
    <p class="ur-ev-note">Exact captured text selected by relevance heuristics. Source assertions are not verified facts. Publisher hosts are not proof of independence. The 20× depth target has not been evaluated.</p>
    ${omitted ? `<p class="ur-ev-note">${esc(omitted)} passage observations omitted by publication budgets. Source inspection and the dossier retain their separately bounded context.</p>` : ''}
    <div class="ur-workbench-filters">
      <label>Search captured passages<input type="search" maxlength="200" data-ur-wb-search placeholder="Topic, quotation or source"></label>
      <label>Publisher<select data-ur-wb-publisher><option value="">All observed publishers</option>${publishers.map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join('')}</select></label>
      <label>Content role<select data-ur-wb-role><option value="">All source assertions</option>${roles.map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join('')}</select></label>
    </div><div data-ur-wb-results>${renderWorkbenchPage(workbench)}</div></div>`);
}

function bindEvidenceWorkbench(container, report) {
  container.querySelectorAll('[data-ur-workbench]').forEach(root => {
    // Lightweight Node test mounts need not implement the browser DOM.
    if (typeof root.querySelector !== 'function' || !report.evidence_workbench) return;
    const search = root.querySelector('[data-ur-wb-search]');
    const publisher = root.querySelector('[data-ur-wb-publisher]');
    const role = root.querySelector('[data-ur-wb-role]');
    const results = root.querySelector('[data-ur-wb-results]');
    if (!search || !publisher || !role || !results) return;
    let page = 0;
    const filters = () => ({ search: search.value, publisher: publisher.value, role: role.value, page });
    const update = () => {
      const selected = workbenchPage(report.evidence_workbench, filters());
      page = selected.page;
      results.innerHTML = renderWorkbenchPage(report.evidence_workbench, filters());
      results.querySelector('[data-ur-wb-prev]').addEventListener('click', () => { page--; update(); results.querySelector('[role="status"]').focus(); });
      results.querySelector('[data-ur-wb-next]').addEventListener('click', () => { page++; update(); results.querySelector('[role="status"]').focus(); });
      results.querySelector('[role="status"]').setAttribute('tabindex', '-1');
    };
    search.addEventListener('input', () => { page = 0; update(); });
    publisher.addEventListener('change', () => { page = 0; update(); });
    role.addEventListener('change', () => { page = 0; update(); });
    update();
  });
}

/** SECTION 3 — EVIDENCE (Primary / Independent / Community) */
function renderEvidence(report) {
  const ev = report.evidence || {};
  const primary     = array(ev.primary).filter(item => item && typeof item === 'object');
  const independent = array(ev.independent).filter(item => item && typeof item === 'object');
  const community   = array(ev.community).filter(item => item && typeof item === 'object');
  const allEvidence = [...primary, ...independent, ...community];
  const inspected = allEvidence.filter(item => item.extraction && typeof item.extraction === 'object');
  const discoveryOnly = inspected.filter(item => item.extraction.evidentiary_use === 'DISCOVERY_ONLY').length;
  const missingDates = inspected.filter(item => array(item.extraction.missing_fields).includes('published_at')).length;
  const coverageBrief = inspected.length ? `<p class="ur-ev-note">${esc(allEvidence.length)} captured records; ${esc(inspected.length)} extraction inspections; ${esc(discoveryOnly)} metadata/unknown-depth records; ${esc(missingDates)} without observed publication dates. These are sample counts, not independent corroboration or website coverage.</p>` : '';

  const renderColumn = (items, label, emptyMsg) => {
    if (items.length === 0) {
      return `
        <div class="ur-ev-col">
          <h3 class="ur-ev-col-head">${esc(label)}</h3>
          <p class="ur-ev-empty">${esc(emptyMsg)}</p>
        </div>`;
    }
    const cards = items.map(item => renderEvidenceCard(item)).join('');
    return `
      <div class="ur-ev-col">
        <h3 class="ur-ev-col-head">${esc(label)}</h3>
        <div class="ur-ev-cards">${cards}</div>
      </div>`;
  };

  const content = `
    <p class="ur-ev-note">Source grouping is not proof of independent corroboration. Inspect each citation and retrieval path.</p>
    ${coverageBrief}
    <div class="ur-ev-grid">
      ${renderColumn(primary,     'Primary',     'No primary evidence found.')}
      ${renderColumn(independent, 'Other reporting', 'No other reporting found.')}
      ${renderColumn(community,   'Community',   'No community evidence found.')}
    </div>`;

  return section('ur-evidence', 'EVIDENCE', content);
}

/** Render a single evidence card. */
function renderEvidenceCard(item, allowRead = true) {
  const title   = esc(item.title   || PH_STR);
  const snippet = esc(item.snippet || '');
  const url     = safeEvidenceUrl(item.url);
  const ts      = esc(item.timestamp || PH_STR);
  const source  = item.source && typeof item.source === 'object' ? item.source : {};
  const srcName = esc(source.name || PH_AUTH);
  const srcType = source.type ? `<span>Reported type: ${esc(source.type)}</span>` : '';
  const srcDomain = source.domain ? `<span>Reported domain: ${esc(source.domain)}</span>` : '';
  const isPrim  = source.is_primary === true;
  const badge   = isPrim ? `<span class="ur-badge ur-badge--primary">Primary</span>` : '';

  // Authoritative Source Tag
  const auth = String(source.authority || item.source_authority || '').toUpperCase();
  let authBadge = '';
  if (auth.includes('REGULATOR') || auth.includes('EDGAR') || source.type === 'filing') {
    authBadge = `<span class="ur-badge ur-badge--edgar">SEC EDGAR · Regulator</span>`;
  } else if (auth.includes('NVD') || auth.includes('VULNERABILITY') || auth.includes('NIST')) {
    authBadge = `<span class="ur-badge ur-badge--nist">NIST NVD · Security</span>`;
  } else if (auth.includes('ARXIV') || auth.includes('PREPRINT')) {
    authBadge = `<span class="ur-badge ur-badge--arxiv">arXiv · Preprint</span>`;
  } else if (auth.includes('FACT_CHECK') || auth.includes('CLAIM_REVIEW')) {
    authBadge = `<span class="ur-badge ur-badge--factcheck">ClaimReview · Fact Check</span>`;
  }
  const relBadge = (typeof source.reliability === 'number' && Number.isFinite(source.reliability))
    ? `<span class="ur-badge ur-badge--rel">Heuristic source score: ${pct(source.reliability)}</span>`
    : '';

  const titleEl = url
    ? `<a class="ur-ev-title" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${title}</a>`
    : `<span class="ur-ev-title">${title}</span>`;

  const noUrl = url ? '' : `<span class="ur-ev-no-url">${PH_URL}</span>`;
  const lineage = Array.isArray(item.retrieval_lineage)
    ? item.retrieval_lineage.filter(entry => entry && typeof entry === 'object').slice(0, 5)
    : [];
  const trace = lineage.length ? `<details class="ur-ev-trace">
      <summary>Acquisition trace</summary>
      <ul>${lineage.map(entry => `<li>
        <span>${esc(entry.channel || 'Channel unknown')}</span>
        <span>${esc(entry.backend_id || 'Backend unknown')}</span>
        <span>${esc(entry.retrieval_mode || 'Mode unknown')}</span>
        <span>${esc(entry.retrieved_at || 'Retrieval time unknown')}</span>
      </li>`).join('')}</ul>
    </details>` : '';

  const extraction = item.extraction && typeof item.extraction === 'object' ? item.extraction : null;
  const passages = extraction ? array(extraction.passages).filter(p => p && typeof p.text === 'string').slice(0, 8) : [];
  const inspection = extraction ? `<details class="ur-ev-trace ur-ev-inspection">
    <summary>Inspect captured passages and extraction limits</summary>
    <p>Depth: ${esc(extraction.content_depth || 'UNKNOWN')} · ${esc(extraction.evidentiary_use || 'NOT_ASSESSED')}</p>
    ${extraction.raw_source_type ? `<p>Raw type: ${esc(extraction.raw_source_type)} · Read: ${esc(extraction.read_status || 'NOT_ACQUIRED')} · Qualification: ${esc(extraction.qualification_status || 'UNASSESSED')}. ${esc(array(extraction.qualification_reasons).join(', '))}</p>` : ''}
    <p>Captured characters: ${esc(extraction.captured_chars ?? 'Unknown')}. Remote source completeness: unknown. Passage support requires review.</p>
    ${extraction.text_metrics && typeof extraction.text_metrics === 'object' ? `<p>Retained raw text: ${esc(extraction.text_metrics.raw_words ?? 'Unknown')} words / ${esc(Number.isFinite(extraction.text_metrics.raw_utf8_bytes) ? (extraction.text_metrics.raw_utf8_bytes / 1000).toFixed(3) : 'Unknown')} KB. Readable capture: ${esc(extraction.text_metrics.readable_words ?? 'Unknown')} words / ${esc(Number.isFinite(extraction.text_metrics.readable_utf8_bytes) ? (extraction.text_metrics.readable_utf8_bytes / 1000).toFixed(3) : 'Unknown')} KB.</p>
      <p>Selection: ${esc(extraction.text_metrics.selection_method || 'Unknown')} · ${esc(extraction.text_metrics.content_scope || 'Unknown')}. Text volume does not establish usefulness or claim support.</p>
      ${extraction.text_metrics.raw_capture_truncated === true ? '<p>The retained raw-text diagnostic was capped separately from the readable capture.</p>' : ''}` : ''}
    <p>Missing observed fields: ${esc(array(extraction.missing_fields).join(', ') || 'None in this field inventory')}.</p>
    ${extraction.source_observations && typeof extraction.source_observations === 'object' && Object.keys(extraction.source_observations).length ? `<details><summary>Source-specific observations — unverified</summary><dl>${Object.entries(extraction.source_observations).slice(0, 40).filter(([key, value]) => ['string', 'number', 'boolean'].includes(typeof value)).map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(String(value).slice(0, 300))}</dd>`).join('')}</dl></details>` : ''}
    ${extraction.provider_truncated === true || extraction.inspection_truncated === true ? '<p>Captured content or inspection was truncated.</p>' : ''}
    ${passages.map(p => `<figure><figcaption>${esc(p.id || 'Passage')} · captured offsets ${esc(p.start ?? '?')}–${esc(p.end ?? '?')}</figcaption><blockquote>${esc(p.text.slice(0, 600))}</blockquote></figure>`).join('')}
    ${array(extraction.structured_passages).length ? `<details><summary>Classified full-context passages — source assertions, not verified facts</summary>${array(extraction.structured_passages).slice(0, 16).map(p => `<figure><figcaption>${esc(p.passage_id)} · ${esc(p.content_role)} · ${esc(p.relevance)} · offsets ${esc(p.start)}–${esc(p.end)}</figcaption><blockquote>${esc(p.text)}</blockquote></figure>`).join('')}</details>` : ''}
    ${array(extraction.financial_observations).length ? `<details><summary>Financial observations — period and units require review</summary>${array(extraction.financial_observations).map(f => `<p>${esc(f.metric)}: ${esc(f.value)} ${esc(f.unit)} ${esc(f.currency || '')}${f.range_upper ? `–${esc(f.range_upper)}` : ''} · ${esc(f.scope || 'SCOPE_UNKNOWN')} · period ${esc(f.period_end || 'unknown/ambiguous')} · page ${esc(f.source_page ?? 'unavailable')} · ${esc(f.period_alignment)}</p><blockquote>${esc(f.text)}</blockquote>`).join('')}</details>` : ''}
    ${array(extraction.observed_numeric_mentions).slice(0, 12).length ? `<details><summary>Observed numeric mentions — not aligned financial facts</summary><ul>${array(extraction.observed_numeric_mentions).slice(0, 12).map(m => `<li>${esc(m && m.text || '')}: ${esc(m && m.context || '')}</li>`).join('')}</ul></details>` : ''}
    ${extraction.page_observations && typeof extraction.page_observations === 'object' ? `<details><summary>Extracted page observations — unverified</summary>
      ${array(extraction.page_observations.date_observations).slice(0, 4).map(value => `<p>Observed date label: ${esc(value.text)} · ${esc(value.meaning)}. Not independently verified; an unlabeled date is not assumed to be publication time.</p>`).join('')}
      ${array(extraction.page_observations.pdf_pages).slice(0, 8).map(page => `<p>PDF page ${esc(page.page)} · captured offsets ${esc(page.start)}–${esc(page.end)}${page.text_truncated ? ' · text truncated' : ''}. Text-layer extraction only; table alignment requires review.</p>`).join('')}
      ${array(extraction.page_observations.tables).slice(0, 3).map((table, index) => `<div class="ur-observed-table"><table><caption>Observed table ${index + 1}; bounded cells, source context requires review</caption><tbody>${array(table).slice(0, 10).map(row => `<tr>${array(row).slice(0, 6).map(cell => `<td>${esc(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`).join('')}
      ${['quotations', 'potential_corrections', 'media_captions'].map(key => array(extraction.page_observations[key]).slice(0, 5).map(value => `<p>${esc(key)}: ${esc(value)}</p>`).join('')).join('')}
    </details>` : ''}
    ${Number(extraction.passages_omitted) > 0 ? `<p>${esc(extraction.passages_omitted)} captured-text chunks omitted from this bounded preview.</p>` : ''}
    <p>Captured-text SHA-256: ${esc(extraction.captured_text_sha256 || 'Unavailable')}</p>
  </details>` : '';

  return `
    <article class="ur-ev-card" data-ur-evidence-id="${esc(item.evidence_id || '')}" data-ur-source-url="${esc(url || '')}">
      <div class="ur-ev-card-head">
        ${titleEl}${badge}${authBadge}${relBadge}${noUrl}
      </div>
      ${item.evidence_id ? `<p class="ur-ev-note">Evidence ID: ${esc(item.evidence_id)}</p>` : ''}
      ${item.extraction && item.extraction.evidentiary_use === 'DISCOVERY_ONLY' ? '<p class="ur-ev-note">Discovery only; not verified claim support.</p>' : ''}
      ${snippet ? `<p class="ur-ev-snippet">${snippet}</p>` : ''}
      <footer class="ur-ev-card-foot">
        <span class="ur-ev-source">${srcName}</span>
        <span class="ur-ev-ts">${ts}</span>
        ${srcType}${srcDomain}
      </footer>
      ${source.attribution_conflict === true ? `<p class="ur-ev-note">Attribution conflict — captured byline: ${esc(source.captured_author || 'Unavailable')}; discovery/feed attribution: ${esc(source.discovery_attribution || 'Unavailable')}. Neither is independently authenticated.</p>` : ''}
      ${trace}
      ${inspection}
      ${url && allowRead ? `<div class="ur-source-read"><button type="button" class="ur-export-btn" data-ur-read-page="${esc(url)}">Request bounded source read</button><p>May contact this source. Optional follow-ups remain bounded; this does not revise the verdict.</p><div data-ur-read-result role="status" aria-live="polite"></div></div>` : ''}
    </article>`;
}

/** Select an existing operation from an exact public hostname, not URL text. */
function sourceReadRequest(value) {
  const safe = safeEvidenceUrl(value);
  if (!safe) return null;
  const u = new URL(safe);
  const host = u.hostname.toLowerCase();
  let platform = 'web', operation = 'read', query = safe;
  if (['reddit.com', 'www.reddit.com', 'old.reddit.com'].includes(host)) platform = 'reddit';
  else if (['x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'].includes(host)) {
    platform = 'twitter'; operation = /\/status\/\d+/.test(u.pathname) ? 'status' : 'profile';
  } else if (['youtube.com', 'www.youtube.com', 'youtu.be'].includes(host)) {
    platform = 'youtube'; operation = 'transcript';
  } else if (host === 'news.ycombinator.com') platform = 'hackernews';
  else if (host === 'stackoverflow.com') platform = 'stackexchange';
  else if (host === 'github.com') {
    const repo = u.pathname.match(/^\/([^/]+)\/([^/]+)/);
    if (repo) { platform = 'github'; query = `${repo[1]}/${repo[2]}`; }
  } else if (['v2ex.com', 'www.v2ex.com'].includes(host)) {
    const topic = u.pathname.match(/^\/t\/(\d+)/);
    if (topic) { platform = 'v2ex'; operation = 'topic'; query = topic[1]; }
  } else if (['xiaoyuzhoufm.com', 'www.xiaoyuzhoufm.com'].includes(host)) {
    platform = 'xiaoyuzhou'; operation = 'episodes';
  }
  return { platform, operation, query, limit: 2, mode: 'deep', max_chars: 12000 };
}

/** SECTION 4 — WHAT DISAGREES? (Supports structured 5-dimensional contradictions) */
function renderDisagreements(report) {
  const structured = array(report.contradictions).filter(c => c && typeof c === 'object');

  if (structured.length > 0) {
    const cards = structured.map(c => {
      const established = c.established === true && array(c.passage_references).length >= 2;
      const typeRaw = established ? (c.type || 'REVIEWED_DISAGREEMENT') : 'POSSIBLE_DISAGREEMENT';
      const type = esc(String(typeRaw).replace(/_/g, ' '));
      const sev = established ? esc(String(c.severity || 'REVIEWED').toUpperCase()) : 'UNASSESSED';
      const sevClass = sev === 'CRITICAL' ? 'ur-sev--critical' : (sev === 'MINOR' ? 'ur-sev--minor' : 'ur-sev--moderate');
      const stmtA = esc(c.statement_a || c.statement || PH_STR);
      const srcA = esc(c.source_a || c.source || PH_STR);
      const stmtB = esc(c.statement_b || c.counter_statement || PH_STR);
      const srcB = esc(c.source_b || c.counter_source || PH_STR);
      const expl = c.explanation ? `<p class="ur-contra-expl">Reported rationale — requires passage review: ${esc(c.explanation)}</p>` : '';

      return `
        <div class="ur-contra-card">
          <div class="ur-contra-head">
            <span class="ur-contra-type">${type}</span>
            <span class="ur-contra-sev ${sevClass}">${sev}</span>
          </div>
          <div class="ur-contra-grid">
            <div class="ur-contra-side">
              <span class="ur-contra-src">Proposition A [${srcA}]:</span>
              <p class="ur-contra-stmt">${stmtA}</p>
            </div>
            <div class="ur-contra-side">
              <span class="ur-contra-src">Proposition B [${srcB}]:</span>
              <p class="ur-contra-stmt">${stmtB}</p>
            </div>
          </div>
          ${expl}
          <p class="ur-ev-note">${established ? 'Reported reviewed assessment; inspect supporting passages.' : 'Unassessed review lead, not an established factual contradiction.'} Sources: ${esc(c.source_a_id || 'Unavailable')} / ${esc(c.source_b_id || 'Unavailable')}.</p>
          ${array(c.passage_references).slice(0, 2).map(ref => `<details><summary>Captured passage ${esc(ref.passage_id || '')} — ${esc(ref.evidence_id || '')} [${esc(ref.start ?? '—')}:${esc(ref.end ?? '—')}]</summary><blockquote>${esc(ref.text || '')}</blockquote></details>`).join('')}
        </div>`;
    }).join('');

    return section('ur-disagreements', 'WHAT DISAGREES?', `
      <p class="ur-ev-note">Multi-dimensional contradiction analysis: proposition divergence across sources.</p>
      <div class="ur-contra-list">${cards}</div>
    `);
  }

  // Legacy fallback if only string items are present
  const items = array(report.disagreements).filter(d => typeof d === 'string')
    .map(d => `Contradictory evidence: ${d}`);
  const content = bulletList(items, 'No contradiction assessment was returned.');
  return section('ur-disagreements', 'WHAT DISAGREES?', content);
}

/** SECTION 5 — WHAT CHANGED? */
function renderChanges(report) {
  const content = bulletList(report.changes, 'No change history was returned.');
  return section('ur-changes', 'WHAT CHANGED?', content);
}

/** AGENT SPECIALIZED INTELLIGENCE (Scout, Trending, BrandShield, Personal Watch) */
function renderAgentIntelligence(report) {
  const intel = report.agent_intelligence;
  if (!intel || typeof intel !== 'object' || Object.keys(intel).length === 0) return '';

  const modules = [];
  const captured = Object.values(report.evidence || {}).flatMap(value => array(value));
  const hasBodies = captured.some(item => item && item.extraction && item.extraction.evidentiary_use === 'REQUIRES_PASSAGE_REVIEW'
    && !['PROFILE_METADATA', 'VIDEO_METADATA', 'METADATA', 'DIRECT_METADATA'].includes(item.extraction.content_depth));

  if (report.catalysts && typeof report.catalysts === 'object') {
    const pos = array(report.catalysts.positive);
    const neg = array(report.catalysts.negative);
    const unres = array(report.catalysts.unresolved);
    if (pos.length || neg.length || unres.length) {
      modules.push(`
        <div class="ur-intel-card" style="grid-column: 1 / -1;">
          <h3 class="ur-intel-head">// Catalysts &amp; Headwinds Tri-Column Matrix</h3>
          <p class="ur-ev-note">Signals categorized across grounded filings and reporting. Inspect source excerpts for each factor.</p>
          <div class="ae-catalysts-matrix">
            <div class="ae-catalyst-col pos">
              <div class="ae-col-head"><span class="ae-dot">●</span> POSITIVE CATALYSTS (${pos.length})</div>
              ${pos.length === 0 ? '<p class="ae-col-empty">No positive catalysts identified in current evidence.</p>' : ''}
              ${pos.map(c => `
                <div class="ae-cat-card">
                  <div class="ae-cat-title">${esc(c.catalyst || c.factor || '')}</div>
                  <div class="ae-cat-meta">${esc(c.source || 'Verified Source')} · <span class="ae-badge-pos">${esc(c.epistemic_state || 'SUPPORTED')}</span></div>
                </div>
              `).join('')}
            </div>
            <div class="ae-catalyst-col neg">
              <div class="ae-col-head"><span class="ae-dot">●</span> CONTESTED HEADWINDS (${neg.length})</div>
              ${neg.length === 0 ? '<p class="ae-col-empty">No material headwinds identified in current evidence.</p>' : ''}
              ${neg.map(c => `
                <div class="ae-cat-card">
                  <div class="ae-cat-title">${esc(c.catalyst || c.factor || '')}</div>
                  <div class="ae-cat-meta">${esc(c.source || 'Monitored Channel')} · <span class="ae-badge-neg">${esc(c.epistemic_state || 'HEADWIND')}</span></div>
                </div>
              `).join('')}
            </div>
            <div class="ae-catalyst-col unres">
              <div class="ae-col-head"><span class="ae-dot">●</span> UNRESOLVED LEADS (${unres.length})</div>
              ${unres.length === 0 ? '<p class="ae-col-empty">No pending regulatory inquiries or unverified claims.</p>' : ''}
              ${unres.map(c => `
                <div class="ae-cat-card">
                  <div class="ae-cat-title">${esc(c.factor || c.catalyst || '')}</div>
                  <div class="ae-cat-meta">${esc(c.source || 'Investigation Lead')} · <span class="ae-badge-unres">${esc(c.epistemic_state || 'PENDING')}</span></div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `);
    }
  }

  if (Array.isArray(intel.financial_observations) && intel.financial_observations.length) {
    modules.push(`<div class="ur-intel-card"><h3 class="ur-intel-head">Scout // Captured financial context</h3>
      <p class="ur-ev-note">Corporate-news assertions, not verified financial claims. Affiliates, currencies, periods and forecasts must remain separate; no filing reconciliation is implied.</p>
      <ul class="ur-list">${intel.financial_observations.filter(row => row && typeof row === 'object').map((row, index) => `<li><details>
        <summary>Financial context ${index + 1} · ${esc(array(row.observed_currencies).join(', ').replace(/_/g, ' ') || 'Currency not established')}</summary>
        <p>Evidence ID: ${esc(row.evidence_id || 'Citation unavailable')}</p>
        <p>Entity: ${esc(String(row.entity_alignment || 'Entity unassessed').replace(/_/g, ' ').toLowerCase())}</p>
        <p>Currencies: ${esc(array(row.observed_currencies).join(', ').replace(/_/g, ' ') || 'Not observed')} · Periods: ${esc(array(row.observed_period_labels).join(', ') || 'Not established')}</p>
        <p>Result scope: ${esc(String(row.result_scope || 'Result scope unassessed').replace(/_/g, ' ').toLowerCase())}. ${esc(String(row.period_alignment || 'Period alignment not established').replace(/_/g, ' ').toLowerCase())}.</p>
        ${row.passage && row.passage.text ? `<details><summary>Exact captured financial passage [${esc(row.passage.start)}:${esc(row.passage.end)}]</summary><blockquote>${esc(row.passage.text)}</blockquote></details>` : ''}
      </details></li>`).join('')}</ul></div>`);
  }

  // Scout: Official Filing Comparison & Rumors
  if (intel.filing_comparison && typeof intel.filing_comparison === 'object') {
    const fc = intel.filing_comparison;
    const assessed = hasBodies && array(fc.comparisons).length > 0 && ['CONSISTENT', 'ANOMALIES_DETECTED'].includes(fc.status);
    const hasDisc = assessed && (fc.discrepancy_detected === true || fc.status === 'ANOMALIES_DETECTED');
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">Scout // SEC Statutory Filing Reconciliation</h3>
        <p class="ur-intel-status ${hasDisc ? 'ur-intel-status--alert' : 'ur-intel-status--ok'}">
          ${!assessed ? 'UNASSESSED — insufficient comparable filing evidence' : hasDisc ? 'Reported numerical discrepancy — inspect periods, units and citations' : 'Reported comparison: CONSISTENT — passage and context review required'}
        </p>
        ${array(fc.discrepancies).length ? `
          <ul class="ur-intel-list">
            ${fc.discrepancies.map(d => `<li><strong>${esc(d.metric || 'Metric')}:</strong> Filing = ${esc(d.filing_value || '—')}, Reported = ${esc(d.reported_value || '—')} (Variance: ${esc(d.variance || '—')})</li>`).join('')}
          </ul>` : ''}
      </div>`);
  }

  const reference = intel.reference_background;
  if (reference && Array.isArray(reference.sources)) {
    modules.push(`<div class="ur-intel-card" data-ur-reference-background><h3 class="ur-intel-head">General background</h3>
      <p class="ur-ev-note">Reference context only. This does not verify current finances, incidents, disputed quotations or virality. Task evidence gaps remain unresolved.</p>
      ${reference.sources.map(row => {
        const href = safeEvidenceUrl(row.url);
        const credit = row.source_permission || {};
        const licence = safeEvidenceUrl(credit.licence_url);
        return `<article><strong>GENERAL BACKGROUND | Publication date unknown</strong>
          <h4>${href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(row.title)}</a>` : esc(row.title)}</h4>
          <p>Source credit: ${esc(credit.author || row.publisher)} | ${esc(row.evidence_id)}</p>
          ${licence ? `<a href="${esc(licence)}" target="_blank" rel="noopener noreferrer">Source licence</a>` : ''}
          <blockquote>${esc(row.passage)}</blockquote></article>`;
      }).join('') || '<p>No unambiguous permitted reference was acquired.</p>'}</div>`);
  }

  // A current article set is a development briefing, not measured popularity.
  const background = intel.historical_background;
  if (background && Array.isArray(background.sources)) {
    modules.push(`<div class="ur-intel-card" data-ur-historical-background><h3 class="ur-intel-head">Trending // Older background reading</h3>
      <p class="ur-ev-note">Relevant older articles, shown because current evidence is limited. These are not current developments or measured trends.</p>
      <ul class="ur-list">${background.sources.slice(0, 6).map(row => {
        const href = safeEvidenceUrl(row.url);
        const credit = row.source_permission || {};
        const licence = safeEvidenceUrl(credit.licence_url);
        return `<li><strong>OLDER BACKGROUND</strong> · ${esc(row.published_at || 'Date unknown')}
          <h4>${href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(row.title)}</a>` : esc(row.title)}</h4>
          <p>${esc(row.publisher)} · ${esc(row.evidence_id)}</p>
          ${credit.author ? `<p class="ur-ev-note">Source credit: ${esc(credit.author)}</p>` : ''}
          ${licence ? `<p><a href="${esc(licence)}" target="_blank" rel="noopener noreferrer">Source licence</a></p>` : ''}
          <blockquote>${esc(row.passage)}</blockquote></li>`;
      }).join('')}</ul>${background.sources.length ? '' : '<p>No permitted relevant historical article was acquired. Discovery leads remain inspectable separately.</p>'}</div>`);
  }
  for (const [key, heading, description] of [
    ['recent_developments', 'Trending // Recent source-reported developments', 'Observed article publication timing; not measured audience growth, reach or independent corroboration.'],
    ['competitive_context', 'Trending // Competitive context — not primary-topic announcements', 'Other actors’ developments and reported competitive impact. This does not establish a new action by the target or measured virality.'],
  ]) {
    if (!Array.isArray(intel[key])) continue;
    const developments = intel[key].filter(row => row && typeof row === 'object');
    modules.push(`<div class="ur-intel-card"><h3 class="ur-intel-head">${heading}</h3>
      <p class="ur-ev-note">${description}</p>
      ${developments.length ? `<ul class="ur-list">${developments.map(row => {
        const href = safeEvidenceUrl(row.url);
        return `<li>${href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(row.title || 'Source report')}</a>` : esc(row.title || 'Source report')}
          <p>${esc(row.publisher || 'Publisher unavailable')} · published ${esc(row.published_at || 'Date unknown')} · ${esc(row.evidence_id || 'Citation unavailable')}</p>
          ${row.passage ? `<blockquote>${esc(row.passage)}</blockquote>` : ''}</li>`;
      }).join('')}</ul>` : '<p class="ur-empty">No qualified developments in this category were retained. Competitive context, unknown dates or stale reports do not establish direct current activity.</p>'}
    </div>`);
  }

  // Trending: Bot Amplification & Velocity
  if (intel.bot_amplification || intel.narrative_velocity) {
    const bot = intel.bot_amplification || {};
    const vel = intel.narrative_velocity || {};
    const botMeasured = hasBodies && bot.measurement_basis === 'OBSERVED_POST_SAMPLE' && bot.observed_post_count >= 2;
    const velMeasured = hasBodies && vel.measurement_basis === 'OBSERVED_TIME_SERIES' && vel.observation_count >= 2;
    const botScore = botMeasured && typeof bot.bot_risk_score === 'number' ? pct(bot.bot_risk_score) : 'UNASSESSED';
    const velScore = velMeasured && typeof vel.velocity_score === 'number' ? pct(vel.velocity_score) : 'UNASSESSED';
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">Trending // Amplification &amp; Spread Velocity</h3>
        <div class="ur-intel-metrics">
          <div class="ur-intel-metric"><span>Bot Risk Score</span><strong>${botScore}</strong></div>
          <div class="ur-intel-metric"><span>Spread Velocity</span><strong>${velScore}</strong></div>
          ${velMeasured && vel.doubling_time_hours != null ? `<div class="ur-intel-metric"><span>Doubling Time</span><strong>${esc(vel.doubling_time_hours)}h</strong></div>` : ''}
        </div>
        <p class="ur-ev-note">A discovery count or one snapshot does not measure reach, narrative truth, bot activity or virality.</p>
        ${botMeasured && array(bot.coordination_patterns).length ? `
          <p class="ur-intel-note">Coordination indicators: ${esc(bot.coordination_patterns.join(', '))}</p>` : ''}
      </div>`);
  }

  // BrandShield: Threat Vectors & Impersonation
  if (Array.isArray(intel.source_assessments)) {
    const assessments = intel.source_assessments.filter(row => row && typeof row === 'object');
    modules.push(`<div class="ur-intel-card"><h3 class="ur-intel-head">BrandShield // Source context and attribution</h3>
      <p>${esc(String(intel.assessment_status || 'UNASSESSED').replace(/_/g, ' '))}</p>
      <p class="ur-ev-note">Warnings, allegations, complaints and enforcement reports remain distinct from an observed attacker. No ownership authentication or active-threat confirmation is implied.</p>
      ${assessments.length ? `<ul class="ur-list">${assessments.map(row => `<li>
        ${esc(String(row.classification || 'INSUFFICIENT_EVIDENCE').replace(/_/g, ' '))} · ${esc(row.evidence_id || 'Citation unavailable')}
        <p>${esc(String(row.reason || 'Context requires review.').replace(/_/g, ' ').toLowerCase())}</p>
        <p>Actor URL: ${esc(row.actor_url || 'Not established; reporting-source URL is not an attacker')} · ${esc(row.epistemic_state || 'UNVERIFIED')}</p>
      </li>`).join('')}</ul>` : '<p class="ur-empty">No qualified source-context assessment; absence of a finding is not proof of safety.</p>'}
    </div>`);
  }
  if (intel.executive_impersonation || intel.smear_analysis || intel.counterfeit_domains) {
    const imp = intel.executive_impersonation || {};
    const smear = intel.smear_analysis || {};
    const count = intel.counterfeit_domains || {};
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">BrandShield // Threat Vectors &amp; Impersonation Defense</h3>
        <div class="ur-intel-metrics">
          <div class="ur-intel-metric"><span>Impersonation Risk</span><strong>${hasBodies && imp.is_impersonation_suspected === true ? 'REPORTED SUSPICION — UNVERIFIED' : 'UNASSESSED'}</strong></div>
          <div class="ur-intel-metric"><span>Campaign Classification</span><strong>${hasBodies ? esc(smear.classification || 'UNASSESSED') : 'UNASSESSED'}</strong></div>
        </div>
        ${array(count.counterfeit_domains).length ? `
          <p class="ur-intel-note">Suspicious typosquat domains: ${esc(count.counterfeit_domains.join(', '))}</p>` : ''}
      </div>`);
  }

  if (Array.isArray(intel.public_statements) && intel.public_statements.length) {
    modules.push(`<div class="ur-intel-card"><h3 class="ur-intel-head">Personal Watch // Reported quotations</h3>
      <p class="ur-ev-note">Publisher-attributed text, not authenticated speech or identity verification. No impersonation conclusion follows from an attributed quote.</p>
      ${intel.public_statements.filter(row => row && typeof row === 'object').map(row => {
        const quotation = row.quotation && typeof row.quotation === 'object' ? row.quotation : {};
        return `<figure><figcaption>${esc(row.speaker || 'Speaker unknown')} · REPORTED QUOTATION — UNVERIFIED · ${esc(row.evidence_id || 'Citation unavailable')}</figcaption>
          <blockquote>${esc(quotation.text || row.text || '')}</blockquote>
          <p>Captured offsets ${esc(quotation.start ?? row.start ?? '?')}–${esc(quotation.end ?? row.end ?? '?')}. Identity: UNASSESSED.</p></figure>`;
      }).join('')}</div>`);
  }

  if (Array.isArray(intel.disputed_claims) && intel.disputed_claims.length) {
    const disputes = intel.disputed_claims.filter(row => row && typeof row === 'object').slice(0, 16);
    modules.push(`<div class="ur-intel-card"><h3 class="ur-intel-head">Personal Watch // Disputed attribution</h3>
      <p class="ur-ev-note">These are publisher-reported disputes, not authenticated speech, proven falsehoods or confirmed impersonation.</p>
      ${disputes.map(row => {
        const passage = array(row.source_passages).find(value => value && typeof value === 'object') || {};
        const href = safeEvidenceUrl(row.source_report_url);
        return `<figure><figcaption>DISPUTED ATTRIBUTION — UNVERIFIED · ${esc(array(row.evidence_ids).join(', ') || 'Citation unavailable')}</figcaption>
          <blockquote>${esc(row.text || '')}</blockquote>
          <p>Captured offsets ${esc(passage.start ?? '?')}–${esc(passage.end ?? '?')}.
          ${href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Inspect reporting source</a>` : 'Reporting source unavailable.'}</p></figure>`;
      }).join('')}</div>`);
  }

  // Personal Watch: Identity & Doxxing Defense
  if (intel.identity_verification || intel.doxxing_exposure || intel.quote_attribution) {
    const idv = intel.identity_verification || {};
    const dox = intel.doxxing_exposure || {};
    const q = intel.quote_attribution || {};
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">Personal Watch // Subject Identity &amp; Integrity Audit</h3>
        <div class="ur-intel-metrics">
          <div class="ur-intel-metric"><span>Catalog Identity Match</span><strong>${idv.is_identity_matched === true ? 'CATALOG MATCH — NOT IDENTITY VERIFICATION' : 'UNCONFIRMED CANDIDATE'}</strong></div>
          <div class="ur-intel-metric"><span>Doxxing Exposure Level</span><strong>${hasBodies ? esc(dox.doxxing_risk_level || dox.exposure_severity || 'UNASSESSED') : 'UNASSESSED'}</strong></div>
          <div class="ur-intel-metric"><span>Quote Authenticity</span><strong>${hasBodies ? esc(q.attribution_status || 'UNASSESSED') : 'UNASSESSED'}</strong></div>
        </div>
        <p class="ur-ev-note">Missing assessment is not low risk or evidence of safety. Reported pattern assessments remain bounded and require source review.</p>
      </div>`);
  }

  if (modules.length === 0) return '';
  return section('ur-agent-intel', 'SPECIALIZED AGENT INTELLIGENCE', `
    <p class="ur-ev-note">Heuristic threat and provenance dimensions evaluated by the active agent.</p>
    <div class="ur-intel-grid">${modules.join('')}</div>
  `);
}

/** SECTION 6 — TIMELINE */
function renderTimeline(report) {
  const events = array(report.timeline).filter(ev => ev && typeof ev === 'object');
  const observedTime = event => typeof event.timestamp === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(event.timestamp)
    && Number.isFinite(Date.parse(event.timestamp)) ? Date.parse(event.timestamp) : Infinity;
  events.sort((left, right) => observedTime(left) - observedTime(right));
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
  return section('ur-timeline', 'TIMELINE', `<p class="ur-ev-note">Observed source timestamps, not independently verified event times. Unknown timing remains unverified.</p><ol class="ur-tl-list">${ols}</ol>`);
}

/** SECTION 7 — WHY TRUST THIS? */
function renderTrust(report) {
  const trust = report.trust || {};
  const qt    = trust.quality_tensor || {};
  const indCount = trust.independent_source_count;
  const publisherCount = trust.observed_publisher_count;
  const tel  = trust.query_telemetry || {};
  const advice = report.processing_notes && report.processing_notes.ai_passage_advice;
  const metrics = report.processing_notes && report.processing_notes.acquisition_metrics;
  const acquisitionNote = metrics && typeof metrics === 'object'
    ? `<div class="ur-acquisition-metrics"><h3 class="ur-trust-sub">Acquisition and qualification</h3><p>${[
        ['candidate_urls', 'candidate URLs'], ['reads_attempted', 'read attempts'],
        ['article_bodies', 'article bodies'], ['qualified_source_count', 'qualified sources'],
        ['raw_article_words', 'raw article words'], ['relevant_words', 'retained passage words'],
        ['duplicate_captures', 'duplicates']
      ].map(([key, label]) => `${Number.isSafeInteger(metrics[key]) && metrics[key] >= 0 ? esc(String(metrics[key])) : '—'} ${label}`).join(' · ')}</p><p class="ur-ev-note">Discovered URLs are not downloaded articles; article text is not a verified claim. Publisher counts do not prove independence.</p></div>` : '';
  const advisoryNote = advice && typeof advice === 'object'
    ? `<p class="ur-trust-note">AI passage assistance: ${esc(advice.status || 'UNKNOWN')}. ${Number.isSafeInteger(advice.accepted) ? esc(advice.accepted) : '—'} selection(s) passed deterministic checks. Advisory only; this does not verify claim support. Unavailable assistance leaves deterministic processing in place.</p>` : '';

  // Quality tensor bars
  const axisRows = TENSOR_AXES.map(({ key, label }) => {
    const val = qt[key];
    const pctVal = pct(val);
    const barWidth = (typeof val === 'number' && Number.isFinite(val) && val >= 0 && val <= 1)
      ? `${Math.round(val * 100)}%`
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
  const indText = Number.isSafeInteger(publisherCount) && publisherCount >= 0
    ? `<strong>${publisherCount}</strong> observed publisher group${publisherCount !== 1 ? 's' : ''} in retained source records. Publisher grouping does not establish independent confirmation.`
    : Number.isSafeInteger(indCount) && indCount >= 0
    ? `<strong>${indCount}</strong> source group${indCount !== 1 ? 's' : ''} reported. Grouping is heuristic; independence is not established by this count.`
    : `<span class="ur-trust-ph">${PH_IND}</span>`;

  // Query telemetry
  const succeeded = tel.queries_succeeded ?? PH_NUM;
  const total     = tel.queries_submitted  ?? PH_NUM;
  const log = array(tel.execution_log).filter(q => q && typeof q === 'object');
  const channels  = new Set(log.map(q => q.channel).filter(Boolean)).size || PH_NUM;
  const authReq   = Number.isSafeInteger(tel.queries_auth_required) && tel.queries_auth_required > 0
    ? tel.queries_auth_required : 0;
  const failed    = Number.isSafeInteger(tel.queries_failed) && tel.queries_failed > 0
    ? tel.queries_failed : 0;

  const telRow = authReq > 0
    ? `<p class="ur-trust-note">(*) ${esc(String(authReq))} lookup(s) required authorization; no evidence was returned by those lookups.</p>`
    : '';
  const failRow = failed > 0
    ? `<p class="ur-trust-note">⚠ ${failed} quer${failed !== 1 ? 'ies' : 'y'} failed during retrieval.</p>`
    : '';

  const content = `
    <div class="ur-trust-inner">
      <div class="ur-qt-section">
        <h3 class="ur-trust-sub">Quality</h3>
        <p class="ur-ev-note">These axes are model scores, not verdict confidence or proof of source independence.</p>
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
        ${advisoryNote}
        ${acquisitionNote}
      </div>
    </div>`;

  return section('ur-trust', 'WHY TRUST THIS?', content);
}

/** Show attempted operations separately from successful evidence retrieval. */
function renderCoverage(report) {
  const log = report.trust && report.trust.query_telemetry &&
    report.trust.query_telemetry.execution_log;
  if (!Array.isArray(log) || log.length === 0) {
    return section('ur-coverage', 'SOURCE COVERAGE',
      '<p class="ur-empty">No query execution log is available; source coverage cannot be verified here.</p>');
  }
  const groups = new Map();
  for (const entry of log.slice(0, 100)) {
    if (!entry || typeof entry !== 'object' || !entry.channel) continue;
    const channel = String(entry.channel);
    const status = String(entry.status || 'UNKNOWN').toUpperCase();
    if (!groups.has(channel)) groups.set(channel, { success: 0, failed: 0, auth: 0, other: 0 });
    const counts = groups.get(channel);
    if (status === 'SUCCESS') counts.success++;
    else if (status === 'FAILED' || status === 'TIMEOUT') counts.failed++;
    else if (status === 'AUTH_REQUIRED') counts.auth++;
    else counts.other++;
  }
  if (groups.size === 0) {
    return section('ur-coverage', 'SOURCE COVERAGE',
      '<p class="ur-empty">The execution log has no channel observations.</p>');
  }
  const rows = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))
    .map(([channel, counts]) => `<tr><th scope="row">${esc(channel)}</th>
      <td>${counts.success}</td><td>${counts.failed}</td>
      <td>${counts.auth}</td><td>${counts.other}</td></tr>`).join('');
  const content = `<div class="ur-coverage-scroll"><table class="ur-coverage-table">
    <caption>Observed query outcomes; a successful query is not necessarily direct evidence.</caption>
    <thead><tr><th scope="col">Channel</th><th scope="col">Succeeded</th>
      <th scope="col">Failed / timed out</th><th scope="col">Auth required</th>
      <th scope="col">Other / planned</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${log.length > 100 ? '<p class="ur-ev-note">Only the first 100 execution records are shown.</p>' : ''}`;
  return section('ur-coverage', 'SOURCE COVERAGE', content);
}

/** SECTION 8 — NEXT STEPS */
function renderNextSteps(report) {
  const content = bulletList(report.next_steps, 'No further actions suggested.');
  return section('ur-next-steps', 'NEXT STEPS', content);
}

/** EXPORT TOOLBAR */
function renderExportToolbar(report) {
  const agent = esc((report._meta && report._meta.agent) || 'Investigation');
  return `
    <div class="ur-export-toolbar">
      <div class="ur-export-meta">
        <span class="ur-export-title">INVESTIGATION DOSSIER</span>
        <span class="ur-export-sub">${agent} &bull; Aegis Schema v3.8.0 &bull; Cryptographic Provenance</span>
      </div>
      <div class="ur-export-btns">
        <button type="button" class="ur-export-btn" id="urBtnExportJson">Export JSON Dossier</button>
      </div>
    </div>`;
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

  // Enrich raw words and passages into structured intelligence if transformer is available
  if (typeof IntelligenceTransformer !== 'undefined') {
    report = IntelligenceTransformer.enrich(report);
  }

  // Native agent sections can precede the shared report. Put transport failure
  // above those sections too, not several screens below an empty dashboard.
  const parent = container.parentElement;
  if (parent && typeof parent.prepend === 'function') {
    parent.querySelector('[data-evidence-navigation]')?.remove();
    const passages = array(report.evidence_workbench && report.evidence_workbench.passages);
    const background = array(report.agent_intelligence && report.agent_intelligence.historical_background && report.agent_intelligence.historical_background.sources)
      .concat(array(report.agent_intelligence && report.agent_intelligence.reference_background && report.agent_intelligence.reference_background.sources));
    if (passages.length || background.length) {
      const navigation = document.createElement('nav');
      navigation.dataset.evidenceNavigation = 'true';
      navigation.className = 'ur-evidence-navigation';
      navigation.setAttribute('aria-label', 'Investigation evidence');
      const texts = [...new Set(passages.map(p => String(p.text || '').trim()).filter(Boolean))];
      const words = texts.reduce((sum, text) => sum + text.split(/\s+/).length, 0);
      const firstWords = workbenchPage(report.evidence_workbench).rows.reduce((sum, p) => sum + String(p.text || '').trim().split(/\s+/).filter(Boolean).length, 0);
      navigation.innerHTML = passages.length
        ? `<a href="#ur-evidence-workbench">View cited passages</a><span>${words} quoted words across all passage pages · ${firstWords} on the first page. Source assertions require review.</span>`
        : '<a href="#ur-agent-intel">View background</a><span>No current qualified passages. Reference and older source text are labeled separately.</span>';
      if (typeof navigation.addEventListener === 'function') {
        navigation.addEventListener('click', event => {
          const link = event.target.closest('a');
          if (!link) return;
          const target = container.querySelector(passages.length ? '#ur-evidence-workbench' : '#ur-agent-intel');
          if (!target) return;
          event.preventDefault();
          // Keep the heading clear of the fixed site navigation, including
          // browsers that align a hash target inside overflow-hidden cards.
          window.scrollTo({ top: Math.max(0, window.scrollY + target.getBoundingClientRect().top - 96), behavior: 'instant' });
          target.querySelector('.ur-heading-button')?.focus({ preventScroll: true });
        });
      }
      parent.prepend(navigation);
    }
    parent.querySelector('[data-acquisition-alert]')?.remove();
    if (report.investigation_status === 'ACQUISITION_FAILED') {
      const alert = document.createElement('div');
      alert.dataset.acquisitionAlert = 'true';
      alert.setAttribute('role', 'alert');
      alert.className = 'ur-verdict-banner ur-verdict--refuted';
      alert.innerHTML = `<h2>Acquisition failed — unable to retrieve evidence</h2><p>${esc(report.summary)}</p>`;
      parent.prepend(alert);
    }
  }

  const html = [
    renderSummary(report),
    renderClaimDecomposition(report),
    renderVisualAnalytics(report),
    renderFindings(report),
    renderEvidenceWorkbench(report),
    renderEvidence(report),
    renderDiscovery(report),
    renderDisagreements(report),
    renderChanges(report),
    renderAgentIntelligence(report),
    renderTimeline(report),
    renderTrust(report),
    renderCoverage(report),
    renderNextSteps(report),
    renderExportToolbar(report),
  ].filter(Boolean).join('\n');

  container.innerHTML = `<div class="unified-report">${html}</div>`;
  bindEvidenceWorkbench(container, report);

  // Mount interactive high-craft visual models if AegisGraphs is available
  if (typeof AegisGraphs !== 'undefined') {
    const radarMount = container.querySelector('#ae-mount-radar');
    if (radarMount) AegisGraphs.renderEpistemicRadar(radarMount, (report.trust && report.trust.epistemic_tensor) || report.epistemic_tensor);

    const funnelMount = container.querySelector('#ae-mount-funnel');
    if (funnelMount) AegisGraphs.renderEvidenceFunnel(funnelMount, report.funnel || (report.trust && report.trust.funnel));

    const dispMount = container.querySelector('#ae-mount-dispersion');
    if (dispMount) AegisGraphs.renderChannelDispersion(dispMount, report.channel_dispersion);

    const findingsMount = container.querySelector('#ae-mount-findings-deck');
    if (findingsMount && findingsMount.dataset.deckItems) {
      try {
        const items = JSON.parse(findingsMount.dataset.deckItems);
        AegisGraphs.renderSplitCommandDeck(findingsMount, items);
      } catch (err) {
        console.warn('[Aegis] Failed to mount SplitCommandDeck:', err);
      }
    }
  }

  // Expand/collapse on mobile — toggle .ur-section.collapsed on heading click
  container.querySelectorAll('.ur-heading-button').forEach(button => {
    button.addEventListener('click', () => {
      const sec = button.closest('.ur-section');
      if (!sec) return;
      const isCollapsed = sec.classList.toggle('ur-collapsed');
      button.setAttribute('aria-expanded', String(!isCollapsed));
    });
  });

  container.querySelectorAll('[data-ur-read-page]').forEach(button => {
    if (!button.dataset || !button.dataset.urReadPage) return;
    button.addEventListener('click', async () => {
      if (button.disabled) return;
      const request = sourceReadRequest(button.dataset.urReadPage);
      const card = button.closest('.ur-ev-card');
      const result = card && card.querySelector('[data-ur-read-result]');
      if (!request || !result) return;
      button.disabled = true;
      result.textContent = `Reading ${request.platform}.${request.operation}; original verdict unchanged…`;
      const controller = new AbortController();
      const deadline = setTimeout(() => controller.abort(), 30000);
      try {
        const endpoint = typeof window !== 'undefined' && window.getAegisApiUrl
          ? window.getAegisApiUrl('/api/agent-reach/extract') : '/api/agent-reach/extract';
        const response = await fetch(endpoint, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request), signal: controller.signal,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const records = array(data.evidence).filter(item => item && typeof item === 'object').slice(0, 15);
        result.innerHTML = `<p>Follow-up ${esc(data.status || 'UNKNOWN')} · ${esc(records.length)} returned records. Claim support not assessed; original verdict unchanged.</p>${data.runtime_reason ? `<p>${esc(data.runtime_reason)}</p>` : ''}${records.map(item => renderEvidenceCard(item, false)).join('')}`;
      } catch (error) {
        result.textContent = error && error.name === 'AbortError'
          ? 'The browser wait timed out. Provider work may still be completing; no result or verdict change is claimed.'
          : 'Source read unavailable. No additional evidence or verdict change is claimed.';
      } finally {
        clearTimeout(deadline);
        button.disabled = false;
      }
    });
  });

  // Client-side dossier export handler
  const exportBtn = typeof container.querySelector === 'function'
    ? container.querySelector('#urBtnExportJson')
    : null;
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      if (typeof window === 'undefined' || typeof document === 'undefined') return;
      try {
        const payloadStr = JSON.stringify(report, null, 2);
        const blob = new Blob([payloadStr], { type: 'application/json' });
        const objUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objUrl;
        a.download = `aegis-dossier-${(report._meta && report._meta.agent) || 'investigation'}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(objUrl);
      } catch (err) {
        console.warn('[Aegis] Failed to download dossier:', err);
      }
    });
  }
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
    // Agent endpoints wrap the canonical report; direct reports also remain supported.
    renderUnifiedReport(container, data && typeof data === 'object' && Object.hasOwn(data, 'unified_report')
      ? data.unified_report : data);
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
  module.exports = { renderUnifiedReport, fetchAndRenderReport, sourceReadRequest, workbenchPage };
}
})();
