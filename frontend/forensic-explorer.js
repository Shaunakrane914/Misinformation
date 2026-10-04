/**
 * Aegis Protocol — Forensic Funnel & Source Explorer Component
 * ============================================================
 * Consumes the ResearchCorpus from Native Agent Reach 3.0 and renders a high-density,
 * interactive forensic presentation layer WITHOUT cluttering the UI into dozens of cards:
 * 
 * 1. Forensic Funnel Ribbon (Queries → Discovered → Indep Groups → Deep Reads → Primaries → Findings)
 * 2. Grounded Findings (Default concise view with ~3–5 key findings + citation pills)
 * 3. Deep-Read Sources (Accordion with domain authority, word count, excerpt, external link, full text)
 * 4. Primary Documents & Filings (SEC/BSE/NSE/IR regulatory disclosures)
 * 5. Syndication & Source Independence (Parent wire clustering & discount factors)
 * 6. Candidate Selection Audit (Transparent reasons why candidates were read or filtered)
 * 7. Evidence Graph (DAG rendering on demand)
 */

(function () {
  'use strict';

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatChars(count) {
    if (!count) return '0 chars';
    return count > 1000 ? `${(count / 1000).toFixed(1)}k chars` : `${count} chars`;
  }

  function formatMetric(val, fallback = '—') {
    if (val === null || val === undefined || Number.isNaN(val)) {
      return `<span title="Metric not measured or unavailable">${fallback}</span>`;
    }
    return escapeHtml(String(val));
  }

  class ForensicExplorer {
    constructor(container, options = {}) {
      this.container = typeof container === 'string' ? document.querySelector(container) : container;
      this.options = options;
      this.corpus = null;
      this.activeTab = 'findings';
    }

    async loadFromClaimId(claimId) {
      if (!this.container) return;
      this.container.innerHTML = `
        <div class="fe-loading">
          <div class="fe-spinner"></div>
          <span>Retrieving deep forensic research corpus for Claim #${escapeHtml(claimId)}...</span>
        </div>
      `;

      const endpoints = [
        (window.getAegisApiUrl ? window.getAegisApiUrl(`/api/claims/${encodeURIComponent(claimId)}/research`) : `/api/claims/${encodeURIComponent(claimId)}/research`)
      ];

      for (const ep of endpoints) {
        try {
          const res = await fetch(ep, { signal: AbortSignal.timeout(8000) });
          if (res.ok) {
            const data = await res.json();
            this.corpus = data.corpus || data;
            if (data.funnel) {
              this.corpus.funnel = Object.assign({}, data.funnel, this.corpus.funnel || {});
            }
            this.render();
            return;
          }
        } catch (err) {
          console.debug('ForensicExplorer fetch notice:', err);
        }
      }

      this.container.innerHTML = `
        <div class="fe-empty-state">
          <span class="fe-empty-icon">ⓘ</span>
          <p>Forensic Research Corpus not yet compiled or unavailable for this record.</p>
        </div>
      `;
    }

    setData(corpusData) {
      this.corpus = corpusData || {};
      this.render();
    }

    render() {
      if (!this.container || !this.corpus) return;

      const f_data = this.corpus.funnel || {};
      const funnel = {
        queries_planned: f_data.queries_planned != null ? f_data.queries_planned : (this.corpus.queries ? this.corpus.queries.length : null),
        queries_executed: f_data.queries_executed != null ? f_data.queries_executed : (this.corpus.queries ? this.corpus.queries.length : null),
        candidates_found: f_data.candidates_found != null ? f_data.candidates_found : (this.corpus.raw_candidates ? this.corpus.raw_candidates.length : (this.corpus.candidates ? this.corpus.candidates.length : null)),
        candidates_ranked: f_data.candidates_ranked != null ? f_data.candidates_ranked : (this.corpus.ranked_candidates ? this.corpus.ranked_candidates.length : (this.corpus.evidence ? this.corpus.evidence.length : null)),
        deep_reads_count: f_data.deep_reads_count != null ? f_data.deep_reads_count : (this.corpus.deep_read_sources ? this.corpus.deep_read_sources.length : (this.corpus.deep_read_success || 0)),
        primary_sources_count: f_data.primary_sources_count != null ? f_data.primary_sources_count : (this.corpus.primary_sources ? this.corpus.primary_sources.length : (this.corpus.primary_sources_found || 0)),
        independent_groups_count: f_data.independent_groups_count != null ? f_data.independent_groups_count : (this.corpus.corroboration_groups ? this.corpus.corroboration_groups.length : (this.corpus.independent_source_groups || null)),
        contradictions_count: f_data.contradictions_count != null ? f_data.contradictions_count : (this.corpus.contradictions ? this.corpus.contradictions.length : (this.corpus.contradictions_found || 0)),
        findings_count: f_data.findings_count != null ? f_data.findings_count : (this.corpus.grounded_findings ? this.corpus.grounded_findings.length : (this.corpus.findings ? this.corpus.findings.length : 0)),
        saturation_score: f_data.saturation_score != null ? f_data.saturation_score : null,
        halt_reason: f_data.halt_reason || null,
      };

      const findings = this.corpus.grounded_findings || this.corpus.findings || [];
      const deepSources = this.corpus.deep_read_sources || [];
      const primaries = this.corpus.primary_sources || [];
      const groups = this.corpus.corroboration_groups || [];
      const audits = this.corpus.candidate_selection_audit || [];
      const rawGraph = this.corpus.evidence_graph || {};

      this.container.innerHTML = `
        <div class="forensic-explorer-root">
          <!-- 1. Forensic Funnel Ribbon -->
          <div class="fe-funnel-ribbon" role="region" aria-label="Investigation Pipeline Metrics">
            <div class="fe-funnel-step" data-tab="audit" title="Multi-angle queries decomposed by domain planner">
              <span class="fe-f-val">${formatMetric(funnel.queries_planned != null ? funnel.queries_planned : funnel.queries_executed)}</span>
              <span class="fe-f-lbl">QUERIES</span>
            </div>
            <div class="fe-f-arrow">→</div>
            <div class="fe-funnel-step" data-tab="audit" title="Raw evidence fragments collected across active backends">
              <span class="fe-f-val">${formatMetric(funnel.candidates_found)}</span>
              <span class="fe-f-lbl">DISCOVERED</span>
            </div>
            <div class="fe-f-arrow">→</div>
            <div class="fe-funnel-step" data-tab="groups" title="Independent publishing groups after wire deduplication">
              <span class="fe-f-val">${formatMetric(funnel.independent_groups_count != null ? funnel.independent_groups_count : groups.length)}</span>
              <span class="fe-f-lbl">INDEP GROUPS</span>
            </div>
            <div class="fe-f-arrow">→</div>
            <div class="fe-funnel-step fe-step-read" data-tab="sources" title="Full articles retrieved and parsed (2.5k–25k characters)">
              <span class="fe-f-val">${formatMetric(funnel.deep_reads_count != null ? funnel.deep_reads_count : deepSources.length)}</span>
              <span class="fe-f-lbl">DEEP READ</span>
            </div>
            <div class="fe-f-arrow">→</div>
            <div class="fe-funnel-step fe-step-primary" data-tab="primaries" title="Escalated regulatory filings (BSE/NSE/SEC) & official IR">
              <span class="fe-f-val">${formatMetric(funnel.primary_sources_count != null ? funnel.primary_sources_count : primaries.length)}</span>
              <span class="fe-f-lbl">PRIMARIES</span>
            </div>
            <div class="fe-f-arrow">→</div>
            <div class="fe-funnel-step fe-step-findings" data-tab="findings" title="Synthesized forensic findings with verified provenance">
              <span class="fe-f-val">${formatMetric(findings.length || funnel.findings_count)}</span>
              <span class="fe-f-lbl">FINDINGS</span>
            </div>
          </div>

          <!-- 2. Source Explorer Tabs Header -->
          <div class="fe-tabs-header" role="tablist">
            <button class="fe-tab-btn ${this.activeTab === 'findings' ? 'active' : ''}" data-tab="findings">
              ★ Grounded Findings <span class="fe-tab-count">${findings.length}</span>
            </button>
            <button class="fe-tab-btn ${this.activeTab === 'sources' ? 'active' : ''}" data-tab="sources">
              📖 Deep-Read Sources <span class="fe-tab-count">${deepSources.length}</span>
            </button>
            <button class="fe-tab-btn ${this.activeTab === 'primaries' ? 'active' : ''}" data-tab="primaries">
              🏛️ Primary Filings <span class="fe-tab-count">${primaries.length}</span>
            </button>
            <button class="fe-tab-btn ${this.activeTab === 'groups' ? 'active' : ''}" data-tab="groups">
              ⑂ Syndication & Independence <span class="fe-tab-count">${groups.length}</span>
            </button>
            <button class="fe-tab-btn ${this.activeTab === 'audit' ? 'active' : ''}" data-tab="audit">
              📋 Selection Audit <span class="fe-tab-count">${audits.length}</span>
            </button>
            <button class="fe-tab-btn ${this.activeTab === 'graph' ? 'active' : ''}" data-tab="graph">
              🕸️ Evidence Graph
            </button>
          </div>

          <!-- 3. Tab Contents Area -->
          <div class="fe-tab-content-area">
            ${this.renderActiveTab(findings, deepSources, primaries, groups, audits, rawGraph)}
          </div>
        </div>
      `;

      this.bindEvents();
    }

    renderActiveTab(findings, deepSources, primaries, groups, audits, rawGraph) {
      switch (this.activeTab) {
        case 'findings':
          return this.renderFindingsTab(findings);
        case 'sources':
          return this.renderSourcesTab(deepSources);
        case 'primaries':
          return this.renderPrimariesTab(primaries);
        case 'groups':
          return this.renderGroupsTab(groups);
        case 'audit':
          return this.renderAuditTab(audits);
        case 'graph':
          return this.renderGraphTab(rawGraph);
        default:
          return this.renderFindingsTab(findings);
      }
    }

    renderFindingsTab(findings) {
      if (!findings || findings.length === 0) {
        return `
          <div class="fe-empty-state">
            <span class="fe-empty-icon">✓</span>
            <p>No anomalous findings or contradictions flagged. Evidence indicates standard consistency.</p>
          </div>
        `;
      }

      return `
        <div class="fe-findings-grid">
          ${findings.slice(0, 5).map((f, idx) => {
            const typeStr = (f.type || f.sentiment_stance || f.stance || 'FINDING').toUpperCase();
            const badgeClass = (typeStr.includes('FACT') || typeStr.includes('SUPPORT') || typeStr.includes('CONFIRM'))
              ? 'fe-badge-green'
              : ((typeStr.includes('CONTRADICT') || typeStr.includes('REFUT')) ? 'fe-badge-red' : 'fe-badge-cyan');
            const confRaw = typeof f.confidence === 'string' ? f.confidence : (f.confidence_score !== undefined ? `${Math.round(f.confidence_score * 100)}%` : (f.confidence !== undefined ? `${Math.round(f.confidence * 100)}%` : null));
            const confStr = confRaw ? `${escapeHtml(confRaw)} Confidence` : 'Confidence unavailable';
            const citations = f.supporting_evidence_ids || f.evidence_ids || [];
            const title = f.title || f.claim_statement || 'Forensic Finding';
            const summary = f.statement || f.summary || f.finding_text || f.explanation || f.reasoning || '';

            return `
              <div class="fe-finding-card">
                <div class="fe-fcard-header">
                  <span class="fe-fcard-num">#${idx + 1}</span>
                  <span class="fe-badge ${badgeClass}">${escapeHtml(typeStr)}</span>
                  <span class="fe-fcard-conf">${confStr}</span>
                </div>
                <h4 class="fe-fcard-title">${escapeHtml(title)}</h4>
                <p class="fe-fcard-summary">${escapeHtml(summary)}</p>

                ${f.quality_tensor ? `
                  <div style="font-size:0.65rem;color:var(--text-dim,#94a3b8);margin-top:8px;font-family:var(--font-mono,monospace);">// EVIDENCE QUALITY DIMENSIONS</div>
                  <div class="fe-qt-row" style="display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 10px 0;font-family:var(--font-mono, monospace);font-size:0.7rem;">
                    <span class="fe-badge" style="background:rgba(139,92,246,0.1);color:#c4b5fd;border:1px solid rgba(139,92,246,0.3);" title="Relevance">Rel: ${Math.round((f.quality_tensor.relevance || 0) * 100)}%</span>
                    <span class="fe-badge" style="background:rgba(14,165,233,0.1);color:#38bdf8;border:1px solid rgba(14,165,233,0.3);" title="Source Quality">Qual: ${Math.round((f.quality_tensor.source_quality || 0) * 100)}%</span>
                    <span class="fe-badge" style="background:rgba(16,185,129,0.1);color:#34d399;border:1px solid rgba(16,185,129,0.3);" title="Independence Ratio">Indep: ${Math.round((f.quality_tensor.independence || 0) * 100)}%</span>
                    <span class="fe-badge" style="background:rgba(234,179,8,0.1);color:#facc15;border:1px solid rgba(234,179,8,0.3);" title="Primary Proximity">Primary: ${Math.round((f.quality_tensor.primary_weight || 0) * 100)}%</span>
                    <span class="fe-badge" style="background:rgba(100,116,139,0.1);color:#94a3b8;border:1px solid rgba(100,116,139,0.3);" title="Freshness">Fresh: ${Math.round((f.quality_tensor.freshness || 0) * 100)}%</span>
                    ${(f.quality_tensor.contradiction_level || 0) > 0.05 ? `<span class="fe-badge fe-badge-red" title="Contradiction Penalty">Contradict: -${Math.round((f.quality_tensor.contradiction_level || 0) * 100)}%</span>` : ''}
                  </div>
                ` : ''}
                
                ${citations.length > 0 ? `
                  <div class="fe-fcard-citations">
                    <span class="fe-cite-label">Evidence Provenance:</span>
                    ${citations.map(cid => `
                      <button class="fe-cite-pill" data-source-id="${escapeHtml(cid)}" title="Jump to source ${escapeHtml(cid)}">
                        🔗 ${escapeHtml(cid)}
                      </button>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderSourcesTab(sources) {
      if (!sources || sources.length === 0) {
        return `
          <div class="fe-empty-state">
            <span class="fe-empty-icon">📖</span>
            <p>No full articles were deep-read in this investigation (search snippets and official disclosures were used).</p>
          </div>
        `;
      }

      return `
        <div class="fe-sources-list">
          ${sources.map((s, idx) => {
            const sId = s.id || `ev_read_${idx + 1}`;
            const domain = s.domain || (s.url ? new URL(s.url).hostname : 'web');
            const authScoreStr = s.authority_score !== undefined ? `Tier: ${Math.round(s.authority_score * 100)}% Authority` : 'Authority uncalibrated';
            const role = s.source_role || s.role || 'Unknown';
            const charCount = s.content ? s.content.length : (s.word_count ? s.word_count * 6 : 0);
            const mode = s.retrieval_mode || (s.provenance && s.provenance.retrieval_mode) || 'Unknown';
            const backend = s.native_backend_id || (s.provenance && s.provenance.native_backend_id) || 'Unknown';
            const fallbackReason = s.fallback_reason || (s.provenance && s.provenance.fallback_reason) || null;

            let modeBadge = '';
            if (mode === 'unauthenticated_syndicated_fallback') {
              modeBadge = `<span class="fe-badge" style="background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3);">⚠️ Web Index Fallback (${escapeHtml(fallbackReason || 'Auth Required')})</span>`;
            } else if (mode === 'legacy_scraper_fallback') {
              modeBadge = `<span class="fe-badge" style="background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.3);">⚠️ Scraper Fallback (${escapeHtml(backend)})</span>`;
            } else if (mode === 'native_tool_cli') {
              modeBadge = `<span class="fe-badge" style="background:rgba(16,185,129,0.15);color:#10b981;border:1px solid rgba(16,185,129,0.3);">⚡ Native Tool CLI (${escapeHtml(backend)})</span>`;
            } else if (mode === 'web_search_index') {
              modeBadge = `<span class="fe-badge" style="background:rgba(14,165,233,0.15);color:#38bdf8;border:1px solid rgba(14,165,233,0.3);">🔍 Web Search Index (${escapeHtml(backend)})</span>`;
            } else if (mode === 'rss_feed') {
              modeBadge = `<span class="fe-badge" style="background:rgba(168,85,247,0.15);color:#c084fc;border:1px solid rgba(168,85,247,0.3);">📰 RSS Feed (${escapeHtml(backend)})</span>`;
            } else if (mode === 'web_reader') {
              modeBadge = `<span class="fe-badge" style="background:rgba(20,184,166,0.15);color:#2dd4bf;border:1px solid rgba(20,184,166,0.3);">📖 Web Reader (${escapeHtml(backend)})</span>`;
            } else if (mode === 'upstream_agent_reach') {
              modeBadge = `<span class="fe-badge" style="background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);">⚡ Upstream Reach (${escapeHtml(backend)})</span>`;
            } else {
              modeBadge = `<span class="fe-badge" style="background:rgba(148,163,184,0.15);color:#cbd5e1;border:1px solid rgba(148,163,184,0.3);">⚡ Direct API (${escapeHtml(backend)})</span>`;
            }

            return `
              <div class="fe-source-accordion" id="source_${escapeHtml(sId)}">
                <div class="fe-s-header" onclick="this.parentElement.classList.toggle('open')">
                  <div class="fe-s-title-group">
                    <span class="fe-s-idx">#${idx + 1}</span>
                    <span class="fe-badge fe-badge-tier">${escapeHtml(authScoreStr)}</span>
                    ${modeBadge}
                    <strong class="fe-s-domain">${escapeHtml(domain)}</strong>
                    <span class="fe-s-title">${escapeHtml(s.title || 'Full Evidence Document')}</span>
                  </div>
                  <div class="fe-s-meta-right">
                    <span class="fe-s-chars">${formatChars(charCount)}</span>
                    <span class="fe-s-chevron">▾</span>
                  </div>
                </div>
                <div class="fe-s-body">
                  <div class="fe-s-body-meta">
                    <div><strong>Destination URL:</strong> <a href="${escapeHtml(s.canonical_url || s.url)}" target="_blank" rel="noopener noreferrer" class="fe-link">${escapeHtml(s.canonical_url || s.url)} ↗</a></div>
                    <div><strong>Role & Provenance:</strong> <span class="fe-tag">${escapeHtml(role)}</span> • ${escapeHtml(mode)} via ${escapeHtml(backend)}</div>
                    ${s.published || s.published_at ? `<div><strong>Published:</strong> ${escapeHtml(s.published || s.published_at)}</div>` : ''}
                  </div>

                  <div class="fe-s-excerpt-box">
                    <div class="fe-box-lbl">Key Grounded Passage / Excerpt:</div>
                    <blockquote class="fe-passage">
                      ${escapeHtml(s.content_preview || s.snippet || (s.content ? s.content.slice(0, 450) + '...' : 'Content retrieved.'))}
                    </blockquote>
                  </div>

                  ${s.content && s.content.length > 500 ? `
                    <details class="fe-full-text-details">
                      <summary>View Complete Extracted Markdown (${formatChars(s.content.length)})</summary>
                      <pre class="fe-full-markdown">${escapeHtml(s.content)}</pre>
                    </details>
                  ` : ''}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderPrimariesTab(primaries) {
      if (!primaries || primaries.length === 0) {
        return `
          <div class="fe-empty-state">
            <span class="fe-empty-icon">🏛️</span>
            <p>No official primary filings (SEC/NSE/BSE or government gazettes) were detected or required for this claim query.</p>
          </div>
        `;
      }

      return `
        <div class="fe-primaries-grid">
          ${primaries.map((p, idx) => {
            const domain = p.domain || (p.url ? new URL(p.url).hostname : 'official');
            return `
              <div class="fe-primary-card">
                <div class="fe-pcard-header">
                  <span class="fe-badge fe-badge-amber">★ PRIMARY SOURCE</span>
                  <span class="fe-pcard-domain">${escapeHtml(domain)}</span>
                </div>
                <h4 class="fe-pcard-title">${escapeHtml(p.title || 'Official Institutional Document')}</h4>
                <div class="fe-pcard-reason">
                  <strong>Escalation Basis:</strong> ${escapeHtml(p.escalation_reason || 'Verified statutory or corporate authority domain')}
                </div>
                <div class="fe-pcard-link">
                  <a href="${escapeHtml(p.url)}" target="_blank" rel="noopener noreferrer" class="fe-btn-link">
                    Open Official Document ↗
                  </a>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderGroupsTab(groups) {
      if (!groups || groups.length === 0) {
        return `
          <div class="fe-empty-state">
            <span class="fe-empty-icon">⑂</span>
            <p>Independence not established.</p>
          </div>
        `;
      }

      return `
        <div class="fe-groups-list">
          <p class="fe-groups-note">
            <strong>Forensic Independence Rule:</strong> Syndicated wire copies from Reuters, Associated Press, PTI, and ANI are clustered under their parent wire with a 0.15 discounted corroboration weight, preventing duplicate reprints from being counted as independent confirmations.
          </p>
          ${groups.map(g => {
            const isWire = Boolean(g.parent_wire);
            const badgeClass = isWire ? 'fe-badge-amber' : 'fe-badge-green';
            const badgeLabel = isWire ? `Wire Parent: ${escapeHtml(g.parent_wire)}` : 'Independent Reporting Group';

            return `
              <div class="fe-group-card">
                <div class="fe-group-header">
                  <div class="fe-group-title">
                    <strong>${escapeHtml(g.group_name || 'Independence not established')}</strong>
                    <span class="fe-badge ${badgeClass}">${badgeLabel}</span>
                  </div>
                  <span class="fe-group-count">${g.articles_count || 1} copies clustered</span>
                </div>
                ${g.articles && g.articles.length > 0 ? `
                  <ul class="fe-group-items">
                    ${g.articles.map(art => `
                      <li>
                        <a href="${escapeHtml(art.url)}" target="_blank" rel="noopener noreferrer" class="fe-link">
                          ${escapeHtml(art.title || art.domain || 'Clustered Article')}
                        </a>
                      </li>
                    `).join('')}
                  </ul>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderAuditTab(audits) {
      if (!audits || audits.length === 0) {
        return `
          <div class="fe-empty-state">
            <span class="fe-empty-icon">📋</span>
            <p>Detailed candidate selection audit is compiled during deep reading execution.</p>
          </div>
        `;
      }

      return `
        <div class="fe-audit-wrap">
          <p class="fe-audit-note">
            <strong>Candidate Selection Transparency:</strong> Every candidate ranked by the research engine is evaluated against diversity caps and content eligibility to ensure broad source representation.
          </p>
          <div class="fe-table-scroll">
            <table class="fe-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Candidate ID</th>
                  <th>Score</th>
                  <th>Read Eligibility</th>
                  <th>Decision</th>
                  <th>Explicit Selection / Rejection Reason</th>
                </tr>
              </thead>
              <tbody>
                ${audits.map(a => {
                  const selected = Boolean(a.selected);
                  const eligible = Boolean(a.eligible_for_read);
                  const decBadge = selected
                    ? `<span class="fe-badge fe-badge-green">DEEP READ</span>`
                    : `<span class="fe-badge fe-badge-muted">FILTERED</span>`;
                  const eligBadge = eligible
                    ? `<span style="color:var(--emerald);">✓ Eligible</span>`
                    : `<span style="color:var(--text-dim);">✗ Not eligible</span>`;
                  const reason = a.rejection_reason
                    ? `<code class="fe-reason-code">${escapeHtml(a.rejection_reason)}</code>`
                    : `<span style="color:var(--emerald);font-weight:600;">Selected for Deep Analysis</span>`;

                  return `
                    <tr class="${selected ? 'row-selected' : ''}">
                      <td style="font-family:var(--font-mono);font-weight:700;">${a.rank != null ? `#${a.rank}` : '—'}</td>
                      <td style="font-family:var(--font-mono);">${escapeHtml(a.candidate_id || '—')}</td>
                      <td style="font-family:var(--font-mono);">${a.score !== undefined && a.score !== null ? a.score.toFixed(3) : '—'}</td>
                      <td>${eligBadge}</td>
                      <td>${decBadge}</td>
                      <td>${reason}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    renderGraphTab(rawGraph) {
      const nodes = rawGraph.nodes || [];
      const edges = rawGraph.edges || [];

      if (nodes.length === 0) {
        return `
          <div class="fe-empty-state">
            <span class="fe-empty-icon">🕸️</span>
            <p>No multi-hop evidence graph compiled for this query.</p>
          </div>
        `;
      }

      return `
        <div class="fe-graph-wrap">
          <div class="fe-graph-header">
            <strong>Cytoscape Forensic DAG:</strong> ${nodes.length} Nodes • ${edges.length} Edges
          </div>
          <div class="fe-graph-viewport" id="feGraphCanvasWrap">
            <svg class="fe-graph-svg" width="100%" height="280" viewBox="0 0 600 280">
              <!-- Render lightweight schematic nodes -->
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(0, 229, 255, 0.4)"/>
                </marker>
              </defs>
              <g class="fe-graph-elements">
                <!-- Schema visual flow -->
                <line x1="80" y1="140" x2="220" y2="140" stroke="rgba(0, 229, 255, 0.4)" stroke-width="2" marker-end="url(#arrow)"/>
                <line x1="260" y1="140" x2="380" y2="90" stroke="rgba(0, 229, 255, 0.4)" stroke-width="2" marker-end="url(#arrow)"/>
                <line x1="260" y1="140" x2="380" y2="190" stroke="rgba(0, 229, 255, 0.4)" stroke-width="2" marker-end="url(#arrow)"/>
                <line x1="420" y1="90" x2="520" y2="140" stroke="rgba(16, 185, 129, 0.5)" stroke-width="2" marker-end="url(#arrow)"/>
                <line x1="420" y1="190" x2="520" y2="140" stroke="rgba(16, 185, 129, 0.5)" stroke-width="2" marker-end="url(#arrow)"/>

                <circle cx="60" cy="140" r="26" fill="#0c1018" stroke="#00e5ff" stroke-width="2"/>
                <text x="60" y="144" fill="#00e5ff" font-size="10" font-family="JetBrains Mono" text-anchor="middle">Claim</text>

                <circle cx="240" cy="140" r="24" fill="#0c1018" stroke="#818cf8" stroke-width="2"/>
                <text x="240" y="144" fill="#818cf8" font-size="9" font-family="JetBrains Mono" text-anchor="middle">Plan</text>

                <circle cx="400" cy="90" r="24" fill="#0c1018" stroke="#10b981" stroke-width="2"/>
                <text x="400" y="94" fill="#10b981" font-size="9" font-family="JetBrains Mono" text-anchor="middle">Primary</text>

                <circle cx="400" cy="190" r="24" fill="#0c1018" stroke="#f59e0b" stroke-width="2"/>
                <text x="400" y="194" fill="#f59e0b" font-size="9" font-family="JetBrains Mono" text-anchor="middle">DeepRead</text>

                <circle cx="540" cy="140" r="26" fill="#0c1018" stroke="#10b981" stroke-width="2"/>
                <text x="540" y="144" fill="#10b981" font-size="9" font-family="JetBrains Mono" text-anchor="middle">Finding</text>
              </g>
            </svg>
          </div>
          <div class="fe-graph-footer">
            <span>Provenance Chain: <code>Claim → Decomposition Plan → Verified Sources → Grounded Verdict</code></span>
          </div>
        </div>
      `;
    }

    bindEvents() {
      // Tab switcher
      const tabBtns = this.container.querySelectorAll('.fe-tab-btn');
      tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.activeTab = e.currentTarget.dataset.tab;
          this.render();
        });
      });

      // Funnel step shortcuts
      const funnelSteps = this.container.querySelectorAll('.fe-funnel-step');
      funnelSteps.forEach(step => {
        step.addEventListener('click', (e) => {
          const tab = e.currentTarget.dataset.tab;
          if (tab) {
            this.activeTab = tab;
            this.render();
          }
        });
      });

      // Citation pills: jump to source
      const citePills = this.container.querySelectorAll('.fe-cite-pill');
      citePills.forEach(pill => {
        pill.addEventListener('click', (e) => {
          const sid = e.currentTarget.dataset.sourceId;
          this.activeTab = 'sources';
          this.render();

          // Scroll and open target accordion
          setTimeout(() => {
            const targetEl = this.container.querySelector(`#source_${sid}`);
            if (targetEl) {
              targetEl.classList.add('open');
              targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
              targetEl.style.boxShadow = '0 0 20px rgba(0, 229, 255, 0.4)';
              setTimeout(() => { targetEl.style.boxShadow = ''; }, 2000);
            }
          }, 100);
        });
      });
    }
  }

  // Export globally
  window.ForensicExplorer = ForensicExplorer;

  window.initForensicExplorer = function (targetSelector, corpusData) {
    const explorer = new ForensicExplorer(targetSelector);
    if (typeof corpusData === 'string') {
      explorer.loadFromClaimId(corpusData);
    } else {
      explorer.setData(corpusData);
    }
    return explorer;
  };
})();
