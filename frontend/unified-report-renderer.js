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

  if (report.verdict && typeof report.verdict === 'object') {
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
      const citeUrl = safeEvidenceUrl(typeof c === 'string' ? c : (c && c.url));
      const citeTitle = esc(typeof c === 'string' ? c : ((c && c.title) || (c && c.url) || 'Citation'));
      return citeUrl
        ? `<a href="${esc(citeUrl)}" target="_blank" rel="noopener noreferrer" class="ur-decomp-cite">${citeTitle} ↗</a>`
        : `<span class="ur-decomp-cite">${citeTitle}</span>`;
    }).join(' ');
    const reasoning = sub.reasoning ? `<p class="ur-decomp-reason">${esc(sub.reasoning)}</p>` : '';

    return `
      <div class="ur-decomp-card">
        <div class="ur-decomp-head">
          <span class="ur-decomp-pill ${cfg.badgeClass}">${esc(cfg.label)}</span>
          <span class="ur-decomp-conf">Confidence: ${cVal}</span>
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

/** SECTION 2 — KEY FINDINGS */
function renderFindings(report) {
  const content = bulletList(report.findings, 'No significant findings.');
  return section('ur-findings', 'KEY FINDINGS', content);
}

/** SECTION 3 — EVIDENCE (Primary / Independent / Community) */
function renderEvidence(report) {
  const ev = report.evidence || {};
  const primary     = array(ev.primary).filter(item => item && typeof item === 'object');
  const independent = array(ev.independent).filter(item => item && typeof item === 'object');
  const community   = array(ev.community).filter(item => item && typeof item === 'object');

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
    <p class="ur-ev-note">Source grouping is not proof of independent corroboration. Inspect each citation and retrieval path.</p>
    <div class="ur-ev-grid">
      ${renderColumn(primary,     'Primary',     'No primary evidence found.')}
      ${renderColumn(independent, 'Other reporting', 'No other reporting found.')}
      ${renderColumn(community,   'Community',   'No community evidence found.')}
    </div>`;

  return section('ur-evidence', 'EVIDENCE', content);
}

/** Render a single evidence card. */
function renderEvidenceCard(item) {
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

  return `
    <article class="ur-ev-card">
      <div class="ur-ev-card-head">
        ${titleEl}${badge}${authBadge}${relBadge}${noUrl}
      </div>
      ${snippet ? `<p class="ur-ev-snippet">${snippet}</p>` : ''}
      <footer class="ur-ev-card-foot">
        <span class="ur-ev-source">${srcName}</span>
        <span class="ur-ev-ts">${ts}</span>
        ${srcType}${srcDomain}
      </footer>
      ${trace}
    </article>`;
}

/** SECTION 4 — WHAT DISAGREES? (Supports structured 5-dimensional contradictions) */
function renderDisagreements(report) {
  const structured = array(report.contradictions).filter(c => c && typeof c === 'object');

  if (structured.length > 0) {
    const cards = structured.map(c => {
      const typeRaw = c.type || 'CONTRADICTION';
      const type = esc(String(typeRaw).replace(/_/g, ' '));
      const sev = esc(String(c.severity || 'MODERATE').toUpperCase());
      const sevClass = sev === 'CRITICAL' ? 'ur-sev--critical' : (sev === 'MINOR' ? 'ur-sev--minor' : 'ur-sev--moderate');
      const stmtA = esc(c.statement_a || c.statement || PH_STR);
      const srcA = esc(c.source_a || c.source || PH_STR);
      const stmtB = esc(c.statement_b || c.counter_statement || PH_STR);
      const srcB = esc(c.source_b || c.counter_source || PH_STR);
      const expl = c.explanation ? `<p class="ur-contra-expl">${esc(c.explanation)}</p>` : '';

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

  // Scout: Official Filing Comparison & Rumors
  if (intel.filing_comparison && typeof intel.filing_comparison === 'object') {
    const fc = intel.filing_comparison;
    const hasDisc = fc.discrepancy_detected === true;
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">Scout // SEC Statutory Filing Reconciliation</h3>
        <p class="ur-intel-status ${hasDisc ? 'ur-intel-status--alert' : 'ur-intel-status--ok'}">
          ${hasDisc ? '⚠ NUMERICAL DISCREPANCY DETECTED BETWEEN FILING AND REPORTED CLAIMS' : '✓ Official filing metrics reconcile with reported disclosure'}
        </p>
        ${array(fc.discrepancies).length ? `
          <ul class="ur-intel-list">
            ${fc.discrepancies.map(d => `<li><strong>${esc(d.metric || 'Metric')}:</strong> Filing = ${esc(d.filing_value || '—')}, Reported = ${esc(d.reported_value || '—')} (Variance: ${esc(d.variance || '—')})</li>`).join('')}
          </ul>` : ''}
      </div>`);
  }

  // Trending: Bot Amplification & Velocity
  if (intel.bot_amplification || intel.narrative_velocity) {
    const bot = intel.bot_amplification || {};
    const vel = intel.narrative_velocity || {};
    const botScore = typeof bot.bot_risk_score === 'number' ? pct(bot.bot_risk_score) : PH_NUM;
    const velScore = typeof vel.velocity_score === 'number' ? pct(vel.velocity_score) : PH_NUM;
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">Trending // Amplification &amp; Spread Velocity</h3>
        <div class="ur-intel-metrics">
          <div class="ur-intel-metric"><span>Bot Risk Score</span><strong>${botScore}</strong></div>
          <div class="ur-intel-metric"><span>Spread Velocity</span><strong>${velScore}</strong></div>
          ${vel.doubling_time_hours != null ? `<div class="ur-intel-metric"><span>Doubling Time</span><strong>${esc(vel.doubling_time_hours)}h</strong></div>` : ''}
        </div>
        ${array(bot.coordination_patterns).length ? `
          <p class="ur-intel-note">Coordination indicators: ${esc(bot.coordination_patterns.join(', '))}</p>` : ''}
      </div>`);
  }

  // BrandShield: Threat Vectors & Impersonation
  if (intel.executive_impersonation || intel.smear_analysis || intel.counterfeit_domains) {
    const imp = intel.executive_impersonation || {};
    const smear = intel.smear_analysis || {};
    const count = intel.counterfeit_domains || {};
    modules.push(`
      <div class="ur-intel-card">
        <h3 class="ur-intel-head">BrandShield // Threat Vectors &amp; Impersonation Defense</h3>
        <div class="ur-intel-metrics">
          <div class="ur-intel-metric"><span>Impersonation Risk</span><strong>${imp.is_impersonation_suspected ? 'ELEVATED' : 'LOW'}</strong></div>
          <div class="ur-intel-metric"><span>Campaign Classification</span><strong>${esc(smear.classification || 'ORGANIC_CRITICISM')}</strong></div>
        </div>
        ${array(count.counterfeit_domains).length ? `
          <p class="ur-intel-note">Suspicious typosquat domains: ${esc(count.counterfeit_domains.join(', '))}</p>` : ''}
      </div>`);
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
          <div class="ur-intel-metric"><span>Catalog Identity Match</span><strong>${idv.is_identity_matched === true ? 'VERIFIED MATCH' : 'UNCONFIRMED CANDIDATE'}</strong></div>
          <div class="ur-intel-metric"><span>Doxxing Exposure Level</span><strong>${esc(dox.doxxing_risk_level || 'LOW')}</strong></div>
          <div class="ur-intel-metric"><span>Quote Authenticity</span><strong>${esc(q.attribution_status || 'UNASSESSED')}</strong></div>
        </div>
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
  const indText = Number.isSafeInteger(indCount) && indCount >= 0
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

  const html = [
    renderSummary(report),
    renderClaimDecomposition(report),
    renderFindings(report),
    renderEvidence(report),
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

  // Expand/collapse on mobile — toggle .ur-section.collapsed on heading click
  container.querySelectorAll('.ur-heading-button').forEach(button => {
    button.addEventListener('click', () => {
      const sec = button.closest('.ur-section');
      if (!sec) return;
      const isCollapsed = sec.classList.toggle('ur-collapsed');
      button.setAttribute('aria-expanded', String(!isCollapsed));
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
  module.exports = { renderUnifiedReport, fetchAndRenderReport };
}
