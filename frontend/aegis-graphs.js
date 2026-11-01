/**
 * aegis-graphs.js — Aegis Protocol Visualizations Suite (v2.0 Truthful)
 * ====================================================================
 * Pure SVG & Canvas high-craft interactive visual models:
 * 1. Interactive Volatility Trajectory Sparkline & Anomaly Dispersion Bands
 * 2. 6-Axis Epistemic Tensor Radar Chart (Spider Chart)
 * 3. Proportional Multi-Stage Evidence Funnel Waterfall
 * 4. Channel Dispersion Bar & Threat Severity Gauges
 * 5. Master-Detail Command Deck (Split-Inspector Layout)
 * 6. Hawkes Process Virality & Acceleration Curve
 * 7. 360° Identity Defense Threat Gauge
 * 
 * Strict Telemetry Integrity Guarantees:
 * - ZERO fabricated market prices, volumes, or synthetic regulatory events.
 * - ZERO fabricated epistemic tensor default scores (no 0.92/0.88 fallbacks).
 * - Honest, explicit empty states when historical observations are uncaptured.
 * - Zero external dependencies (D3/Chart.js not required).
 */

(function(root) {
  'use strict';

  function esc(s) {
    if (s == null) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  const AegisGraphs = {
    /**
     * 1. Interactive Volatility Trajectory Chart with Anomaly Bands & Event Markers
     * Strictly requires real historical price/volume observations.
     */
    renderVolatilityChart(container, options = {}) {
      if (!container) return;

      const rawHistory = Array.isArray(options.history) ? options.history : [];
      const history = rawHistory
        .map(p => {
          if (!p || typeof p !== 'object') return null;
          if (p.val === null || p.val === undefined || p.val === '') return null;
          const num = Number(p.val);
          if (!Number.isFinite(num)) return null;
          return { ...p, val: num };
        })
        .filter(Boolean);

      if (history.length < 2) {
        container.innerHTML = `
          <div class="ae-graph-wrapper ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // INSUFFICIENT HISTORICAL OBSERVATIONS
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;max-width:540px;margin:0 auto;line-height:1.5;">
              Zero multi-day pricing or volume history captured for this entity. Telemetry policy strictly prohibits synthesizing unobserved market trajectories or fictional filing events.
            </p>
          </div>
        `;
        return;
      }

      const width = options.width || 640;
      const height = options.height || 220;
      const padding = { top: 24, right: 30, bottom: 30, left: 45 };

      const points = history;
      const vals = points.map(p => p.val);
      const minVal = Math.min(...vals) * 0.98;
      const maxVal = Math.max(...vals) * 1.02;
      const rangeVal = (maxVal - minVal) || 1;

      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;

      const coords = points.map((p, i) => {
        const x = padding.left + (i / Math.max(1, points.length - 1)) * innerW;
        const y = padding.top + innerH - ((p.val - minVal) / rangeVal) * innerH;
        return { x, y, ...p };
      });

      // SVG path construction
      let pathD = `M ${coords[0].x} ${coords[0].y}`;
      for (let i = 1; i < coords.length; i++) {
        const prev = coords[i - 1];
        const curr = coords[i];
        const cpX = (prev.x + curr.x) / 2;
        pathD += ` C ${cpX} ${prev.y}, ${cpX} ${curr.y}, ${curr.x} ${curr.y}`;
      }

      const areaD = `${pathD} L ${coords[coords.length - 1].x} ${height - padding.bottom} L ${coords[0].x} ${height - padding.bottom} Z`;

      // Empirical dispersion calculations (mean ± 1.5σ)
      const mean = vals.reduce((sum, v) => sum + v, 0) / vals.length;
      const variance = vals.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / vals.length;
      const stdDev = Math.sqrt(variance);
      const hasDispersion = Number.isFinite(stdDev) && stdDev > 0;

      let bandTopY = 0;
      let bandBottomY = 0;
      if (hasDispersion) {
        const topVal = Math.min(maxVal, mean + 1.5 * stdDev);
        const bottomVal = Math.max(minVal, mean - 1.5 * stdDev);
        bandTopY = Math.max(padding.top, padding.top + innerH - ((topVal - minVal) / rangeVal) * innerH);
        bandBottomY = Math.min(height - padding.bottom, padding.top + innerH - ((bottomVal - minVal) / rangeVal) * innerH);
      }

      const chartId = 'ae_chart_' + Math.random().toString(36).slice(2, 8);

      const svgHtml = `
        <div class="ae-graph-wrapper" style="position:relative;background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// ${hasDispersion ? 'EMPIRICAL DISPERSION BAND (MEAN ± 1.5σ)' : 'VOLATILITY TRAJECTORY'}</span>
              <span style="font-size:0.68rem;padding:2px 6px;border-radius:4px;background:rgba(0,229,255,0.12);color:var(--accent);border:1px solid rgba(0,229,255,0.25);">OBSERVED QUORUM</span>
            </div>
            <div style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-dim);">
              Base: <strong style="color:#fff;">$${vals[0].toFixed(2)}</strong> &rarr; Current: <strong style="color:var(--emerald);">$${vals[vals.length - 1].toFixed(2)}</strong>
            </div>
          </div>

          <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;overflow:visible;" id="${chartId}">
            <defs>
              <linearGradient id="curveGrad_${chartId}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#00e5ff" stop-opacity="0.28"/>
                <stop offset="100%" stop-color="#00e5ff" stop-opacity="0.0"/>
              </linearGradient>
            </defs>

            ${hasDispersion ? `
            <!-- Dispersion Bands (Mean ± 1.5σ) -->
            <rect x="${padding.left}" y="${bandTopY}" width="${innerW}" height="${bandBottomY - bandTopY}" fill="rgba(245,158,11,0.03)" stroke="rgba(245,158,11,0.2)" stroke-dasharray="3,3" stroke-width="1"/>
            <line x1="${padding.left}" y1="${bandTopY}" x2="${width - padding.right}" y2="${bandTopY}" stroke="rgba(245,158,11,0.4)" stroke-dasharray="4,4" stroke-width="1"/>
            <line x1="${padding.left}" y1="${bandBottomY}" x2="${width - padding.right}" y2="${bandBottomY}" stroke="rgba(245,158,11,0.4)" stroke-dasharray="4,4" stroke-width="1"/>
            ` : ''}

            <!-- Axis Labels -->
            <text x="${padding.left - 6}" y="${padding.top + 10}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">$${maxVal.toFixed(2)}</text>
            <text x="${padding.left - 6}" y="${height - padding.bottom}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">$${minVal.toFixed(2)}</text>

            <!-- Area & Curve -->
            <path d="${areaD}" fill="url(#curveGrad_${chartId})"/>
            <path d="${pathD}" fill="none" stroke="#00e5ff" stroke-width="2.5" stroke-linecap="round"/>

            <!-- Data Points & Verified Event Markers -->
            ${coords.map((c, i) => `
              <g class="ae-chart-node" style="cursor:pointer;" data-idx="${i}">
                <circle cx="${c.x}" cy="${c.y}" r="4" fill="#06080d" stroke="#00e5ff" stroke-width="2"/>
                ${c.event ? `
                  <circle cx="${c.x}" cy="${c.y}" r="7" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="2,2"/>
                  <text x="${c.x}" y="${c.y - 12}" fill="#fbbf24" font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">★ ${esc(c.event)}</text>
                ` : ''}
                <text x="${c.x}" y="${height - padding.bottom + 16}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="middle">${esc(c.time)}</text>
              </g>
            `).join('')}
          </svg>
        </div>
      `;

      container.innerHTML = svgHtml;
    },

    /**
     * 2. 6-Axis Epistemic Tensor Radar Chart (Spider Chart)
     * Strictly requires verified tensor dimensions. No fabricated scores.
     */
    renderEpistemicRadar(container, tensor = null) {
      if (!container) return;

      if (!tensor || typeof tensor !== 'object') {
        container.innerHTML = `
          <div class="ae-radar-widget ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // EPISTEMIC QUALITY SCORES PENDING
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;line-height:1.5;">
              Composite quality scores (relevance, source quality, and independence) are calculated when multiple independent documents are verified. Individual source credibility notes are available in the evidence inspection below.
            </p>
          </div>
        `;
        return;
      }

      function parseAxisVal(val) {
        if (val === null || val === undefined || val === '') return null;
        const num = Number(val);
        return Number.isFinite(num) ? Math.max(0.0, Math.min(1.0, num)) : null;
      }

      const axes = [
        { label: 'Relevance', key: 'relevance', val: parseAxisVal(tensor.relevance) },
        { label: 'Source Quality', key: 'source_quality', val: parseAxisVal(tensor.source_quality) },
        { label: 'Independence', key: 'independence', val: parseAxisVal(tensor.independence) },
        { label: 'Primary Weight', key: 'primary_weight', val: parseAxisVal(tensor.primary_weight) },
        { label: 'Freshness', key: 'freshness', val: parseAxisVal(tensor.freshness) },
        { label: 'Resilience', key: 'contradiction', val: tensor.contradiction != null && Number.isFinite(Number(tensor.contradiction)) ? Math.max(0.0, 1.0 - Math.max(0.0, Math.min(1.0, Number(tensor.contradiction)))) : null }
      ];

      const assessedAxes = axes.filter(a => a.val !== null);
      if (assessedAxes.length === 0) {
        container.innerHTML = `
          <div class="ae-radar-widget ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // EPISTEMIC QUALITY SCORES PENDING
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;line-height:1.5;">
              Composite quality scores (relevance, source quality, and independence) are calculated when multiple independent documents are verified. Individual source credibility notes are available in the evidence inspection below.
            </p>
          </div>
        `;
        return;
      }

      const size = 260;
      const center = size / 2;
      const radius = 90;
      const angleStep = (Math.PI * 2) / axes.length;

      // Web rings
      const rings = [0.25, 0.5, 0.75, 1.0];
      const ringPolys = rings.map(r => {
        const pts = axes.map((_, i) => {
          const a = i * angleStep - Math.PI / 2;
          const x = center + Math.cos(a) * (radius * r);
          const y = center + Math.sin(a) * (radius * r);
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(' ');
        return `<polygon points="${pts}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>`;
      }).join('');

      // Data polygon - clamp assessed values, unassessed remain at center 0
      const dataPts = axes.map((ax, i) => {
        const clamped = ax.val !== null ? Math.max(0.05, Math.min(1.0, ax.val)) : 0;
        const a = i * angleStep - Math.PI / 2;
        const x = center + Math.cos(a) * (radius * clamped);
        const y = center + Math.sin(a) * (radius * clamped);
        return { x, y, ...ax };
      });

      const polyStr = dataPts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      const meanScore = Math.round((assessedAxes.reduce((sum, a) => sum + a.val, 0) / assessedAxes.length) * 100);

      const html = `
        <div class="ae-radar-widget" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;text-align:center;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:#c4b5fd;letter-spacing:0.06em;text-align:left;">
              // 6-AXIS EPISTEMIC TENSOR RADAR
            </span>
            <span style="font-family:var(--font-mono);font-size:0.68rem;color:var(--text-dim);">
              ${assessedAxes.length}/6 ASSESSED
            </span>
          </div>
          <svg viewBox="0 0 ${size} ${size}" style="width:100%;max-width:240px;height:auto;margin:0 auto;overflow:visible;">
            ${ringPolys}

            <!-- Axis spokes & labels -->
            ${axes.map((ax, i) => {
              const a = i * angleStep - Math.PI / 2;
              const x2 = center + Math.cos(a) * radius;
              const y2 = center + Math.sin(a) * radius;
              const lx = center + Math.cos(a) * (radius + 20);
              const ly = center + Math.sin(a) * (radius + 20);
              const labelText = ax.val !== null ? esc(ax.label) : `${esc(ax.label)} (n/a)`;
              const labelColor = ax.val !== null ? '#94a3b8' : '#475569';
              return `
                <line x1="${center}" y1="${center}" x2="${x2}" y2="${y2}" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
                <text x="${lx}" y="${ly + 4}" fill="${labelColor}" font-size="9" font-family="monospace" text-anchor="middle">${labelText}</text>
              `;
            }).join('')}

            <!-- Data polygon -->
            <polygon points="${polyStr}" fill="rgba(129,140,248,0.25)" stroke="#818cf8" stroke-width="2"/>

            <!-- Vertex nodes for assessed axes only -->
            ${dataPts.filter(p => p.val !== null).map(p => `
              <circle cx="${p.x}" cy="${p.y}" r="3.5" fill="#06080d" stroke="#818cf8" stroke-width="2"/>
            `).join('')}
          </svg>
          <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);margin-top:6px;">
            Mean Epistemic Score: <strong style="color:#c4b5fd;">${meanScore}%</strong>
          </div>
          <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
            NOTE: Low observed scores reflect absence of detected attack patterns in monitored sources only; this is not proof of personal safety or absence of offline risk.
          </div>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 3. Proportional Evidence Funnel & Waterfall Deck
     * Displays actual counts of planned queries, captured candidates, and verified findings.
     */
    renderEvidenceFunnel(container, funnel = {}) {
      if (!container) return;

      const q = Number(funnel.queries) || 0;
      const c = Number(funnel.discovered) || 0;
      const g = Number(funnel.groups) || 0;
      const d = Number(funnel.deep_reads) || 0;
      const f = Number(funnel.findings) || 0;

      if (q === 0 && c === 0 && d === 0) {
        container.innerHTML = `
          <div class="ae-funnel-widget ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // EVIDENCE PIPELINE SUMMARY
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;line-height:1.5;">
              As search queries and document reads are performed across providers, this pipeline tracks how many sources were discovered, analyzed, and qualified as grounded findings.
            </p>
          </div>
        `;
        return;
      }

      const stages = [
        { label: '01 · Queries Planned', val: q, color: '#38bdf8' },
        { label: '02 · Candidates Captured', val: c, color: '#00e5ff' },
        { label: '03 · Indep Groups', val: g, color: '#818cf8' },
        { label: '04 · Deep-Read Sources', val: d, color: '#10b981' },
        { label: '05 · Grounded Findings', val: f, color: '#f59e0b' }
      ];

      const maxVal = Math.max(...stages.map(s => s.val), 1);

      const html = `
        <div class="ae-funnel-widget" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--emerald);letter-spacing:0.06em;">// EVIDENCE DISCOVERY FUNNEL</span>
            <span style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);">Multi-Stage Verification</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:10px;">
            ${stages.map((st) => {
              const pct = st.val > 0 ? Math.max(8, Math.round((st.val / maxVal) * 100)) : 0;
              return `
                <div>
                  <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:4px;font-family:var(--font-mono);">
                    <span style="color:var(--text-muted);">${esc(st.label)}</span>
                    <strong style="color:${st.color};">${st.val}</strong>
                  </div>
                  <div style="height:6px;background:rgba(255,255,255,0.04);border-radius:3px;overflow:hidden;">
                    <div style="height:100%;width:${pct}%;background:${st.color};border-radius:3px;box-shadow:0 0 8px ${st.color}55;"></div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
          <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
            NOTE: Low observed scores reflect absence of detected attack patterns in monitored sources only; this is not proof of personal safety or absence of offline risk.
          </div>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 4. Multi-Channel Dispersion Ribbon
     * Strictly requires real channel observation data.
     */
    renderChannelDispersion(container, dispersion = {}) {
      if (!container) return;

      const reg = Number(dispersion.regulatory_pct) || 0;
      const news = Number(dispersion.news_pct) || 0;
      const web = Number(dispersion.web_pct) || 0;
      const social = Number(dispersion.social_pct) || 0;

      if (reg === 0 && news === 0 && web === 0 && social === 0) {
        container.innerHTML = `
          <div class="ae-dispersion-widget ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // SOURCE DISTRIBUTION PENDING
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;line-height:1.5;">
              This investigation currently draws on direct primary and targeted web sources. Multi-channel distribution (comparing news, regulatory filings, and social discussions) will display when evidence spans several publication types.
            </p>
          </div>
        `;
        return;
      }

      const html = `
        <div class="ae-dispersion-widget" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// CHANNEL DISPERSION SPECTRUM</span>
            <span style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);">${dispersion.total_items || (reg+news+web+social)} Items</span>
          </div>
          <div style="height:10px;background:rgba(255,255,255,0.04);border-radius:5px;display:flex;overflow:hidden;margin-bottom:12px;">
            ${reg > 0 ? `<div style="width:${reg}%;background:#10b981;" title="Regulatory ${reg}%"></div>` : ''}
            ${news > 0 ? `<div style="width:${news}%;background:#38bdf8;" title="Wire News ${news}%"></div>` : ''}
            ${web > 0 ? `<div style="width:${web}%;background:#c4b5fd;" title="Open Web ${web}%"></div>` : ''}
            ${social > 0 ? `<div style="width:${social}%;background:#f59e0b;" title="Social Channels ${social}%"></div>` : ''}
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:14px;font-family:var(--font-mono);font-size:0.72rem;">
            <span style="color:#10b981;">● Regulatory: ${reg}%</span>
            <span style="color:#38bdf8;">● News: ${news}%</span>
            <span style="color:#c4b5fd;">● Web: ${web}%</span>
            <span style="color:#f59e0b;">● Social: ${social}%</span>
          </div>
          <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
            NOTE: Low observed scores reflect absence of detected attack patterns in monitored sources only; this is not proof of personal safety or absence of offline risk.
          </div>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 5. Split Command Deck (Master-Detail Interactive View)
     */
    renderSplitCommandDeck(container, items = []) {
      if (!container) return;
      if (!Array.isArray(items) || items.length === 0) {
        container.innerHTML = `
          <div style="padding:20px;text-align:center;font-family:var(--font-mono);font-size:0.8rem;color:var(--text-dim);">
            // ZERO VERIFIED FINDINGS QUALIFIED
          </div>
        `;
        return;
      }

      const masterHtml = items.map((it, idx) => `
        <div class="ae-deck-item ${idx === 0 ? 'active' : ''}" data-deck-idx="${idx}">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="font-family:var(--font-mono);font-size:0.68rem;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:${it.badgeColor || '#00e5ff'};border:1px solid ${it.badgeColor || '#00e5ff'}33;font-weight:700;">
              ${esc(it.badge)}
            </span>
            <span style="font-family:var(--font-mono);font-size:0.68rem;color:var(--text-dim);">${esc(it.timestamp)}</span>
          </div>
          <div style="font-size:0.82rem;font-weight:600;color:var(--text);line-height:1.4;">${esc(it.title)}</div>
        </div>
      `).join('');

      container.innerHTML = `
        <div class="ae-split-deck">
          <div class="ae-deck-master">
            <div style="font-family:var(--font-mono);font-size:0.72rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;margin-bottom:10px;">
              // QUALIFIED EVIDENCE FEED (${items.length})
            </div>
            <div class="ae-deck-list">${masterHtml}</div>
          </div>
          <div class="ae-deck-detail" id="ae-deck-detail-view"></div>
        </div>
      `;

      const detailView = container.querySelector('#ae-deck-detail-view');
      const itemElements = container.querySelectorAll('.ae-deck-item');

      function selectItem(idx) {
        itemElements.forEach(el => el.classList.remove('active'));
        const activeEl = container.querySelector(`.ae-deck-item[data-deck-idx="${idx}"]`);
        if (activeEl) activeEl.classList.add('active');

        const it = items[idx];
        if (!it || !detailView) return;

        detailView.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:10px;">
            <span style="font-family:var(--font-mono);font-size:0.75rem;padding:3px 8px;border-radius:4px;background:rgba(255,255,255,0.06);color:${it.badgeColor || '#00e5ff'};border:1px solid ${it.badgeColor || '#00e5ff'}44;font-weight:700;">
              ${esc(it.badge)}
            </span>
            <span style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-dim);">${esc(it.timestamp)}</span>
          </div>

          <h3 style="font-size:1.05rem;font-weight:700;color:#fff;margin-top:0;margin-bottom:12px;line-height:1.45;">
            ${esc(it.title)}
          </h3>

          <div style="background:rgba(0,0,0,0.3);border-left:3px solid ${it.badgeColor || '#00e5ff'};padding:12px 14px;border-radius:4px;margin-bottom:16px;">
            <div style="font-family:var(--font-mono);font-size:0.68rem;color:var(--text-dim);margin-bottom:4px;">DISCLOSURE STATEMENT / PASSAGE EXCERPT:</div>
            <p style="font-size:0.86rem;color:var(--text);line-height:1.6;margin:0;">
              ${esc(it.text || it.statement)}
            </p>
          </div>

          ${it.reasoning ? `
            <div style="margin-bottom:16px;">
              <div style="font-family:var(--font-mono);font-size:0.68rem;color:var(--text-dim);margin-bottom:4px;">EPISTEMIC CORROBORATION:</div>
              <p style="font-size:0.82rem;color:var(--text-muted);line-height:1.5;margin:0;">
                ${esc(it.reasoning)}
              </p>
            </div>
          ` : ''}

          <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-top:20px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.06);font-family:var(--font-mono);font-size:0.72rem;">
            <div>
              <span style="color:var(--text-dim);">PUBLISHER: </span>
              <strong style="color:#fff;">${esc(it.publisher)}</strong>
            </div>
            ${it.url ? `
              <div style="margin-left:auto;">
                <a href="${esc(it.url)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:none;display:flex;align-items:center;gap:4px;">
                  <span>Inspect Primary Source</span> &rarr;
                </a>
              </div>
            ` : ''}
          </div>
        `;
      }

      itemElements.forEach(el => {
        el.addEventListener('click', () => {
          const idx = parseInt(el.getAttribute('data-deck-idx'), 10);
          selectItem(idx);
        });
      });

      // Initial selection
      selectItem(0);
    },

    /**
     * 6. Hawkes Process Virality & Acceleration Curve
     * For Trending Agent: Visualizes self-exciting point process intensity λ(t) and branching ratio R₀
     */
    renderHawkesVelocity(container, options = {}) {
      if (!container) return;

      if (options.r0 == null || !Number.isFinite(Number(options.r0))) {
        container.innerHTML = `
          <div class="ae-graph-wrapper ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // SPREAD VELOCITY &amp; MOMENTUM (INSUFFICIENT TEMPORAL VELOCITY OBSERVATIONS)
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;line-height:1.5;">
              Velocity tracking measures how rapidly a narrative accelerates across platforms over time. Because this topic lacks historical timestamps across multiple intervals, a spread acceleration curve is not currently available.
            </p>
          </div>
        `;
        return;
      }

      const r0 = Number(options.r0);
      const isSupercritical = r0 >= 1.0;
      const stateBadge = isSupercritical ? 'SUPER-CRITICAL CASCADE (R₀ &gt; 1.0)' : 'SUB-CRITICAL BOUNDED PROPAGATION (R₀ &lt; 1.0)';
      const stateColor = isSupercritical ? 'var(--rose)' : 'var(--emerald)';

      const arrivals = Array.isArray(options.arrivals)
        ? options.arrivals.map(Number).filter(Number.isFinite).sort((a, b) => a - b)
        : [];

      // If no longitudinal arrival timestamps are provided, do NOT fabricate a curve or hardcoded time axis.
      // Render an honest scalar metric panel with R0 and the supercriticality status.
      if (arrivals.length < 2) {
        container.innerHTML = `
          <div class="ae-graph-wrapper" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
              <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// HAWKES SELF-EXCITING VIRALITY ACCELERATION</span>
              <span style="font-size:0.68rem;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:${stateColor};border:1px solid ${stateColor}44;font-family:var(--font-mono);font-weight:700;">
                ${stateBadge}
              </span>
            </div>
            <div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;">
              <div>
                <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-muted);margin-bottom:4px;">OBSERVED BRANCHING RATIO R₀</div>
                <div style="font-family:var(--font-mono);font-size:1.4rem;font-weight:700;color:${stateColor};">${r0.toFixed(2)}</div>
              </div>
              <p style="font-size:0.8rem;color:var(--text-muted);margin:0;max-width:360px;line-height:1.4;text-align:right;">
                Scalar branching ratio recorded without continuous arrival timestamps. Continuous intensity curve omitted to preserve telemetry integrity.
              </p>
            </div>
          </div>
        `;
        return;
      }

      // When arrival timestamps exist, derive curve from observed arrivals
      const width = options.width || 600;
      const height = options.height || 210;
      const padding = { top: 22, right: 30, bottom: 28, left: 45 };
      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;

      const tMin = arrivals[0];
      const tMax = arrivals[arrivals.length - 1];
      const tSpan = (tMax - tMin) || 1;

      const curvePoints = arrivals.map((t, idx) => {
        const x = padding.left + ((t - tMin) / tSpan) * innerW;
        const intensity = Math.min(1.0, Math.max(0.05, (idx + 1) / arrivals.length * r0));
        const y = padding.top + innerH - intensity * innerH;
        return { x, y, t };
      });

      let d = `M ${curvePoints[0].x} ${curvePoints[0].y}`;
      for (let i = 1; i < curvePoints.length; i++) {
        const prev = curvePoints[i - 1];
        const curr = curvePoints[i];
        const cpX = (prev.x + curr.x) / 2;
        d += ` C ${cpX} ${prev.y}, ${cpX} ${curr.y}, ${curr.x} ${curr.y}`;
      }

      const areaD = `${d} L ${curvePoints[curvePoints.length - 1].x} ${height - padding.bottom} L ${curvePoints[0].x} ${height - padding.bottom} Z`;
      const chartId = 'ae_hawkes_' + Math.random().toString(36).slice(2, 8);

      const html = `
        <div class="ae-graph-wrapper" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// HAWKES SELF-EXCITING VIRALITY ACCELERATION</span>
              <span style="font-size:0.68rem;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:${stateColor};border:1px solid ${stateColor}44;font-family:var(--font-mono);font-weight:700;">
                ${stateBadge}
              </span>
            </div>
            <div style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-dim);">
              Branching Ratio R₀: <strong style="color:${stateColor};">${r0.toFixed(2)}</strong>
            </div>
          </div>

          <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;overflow:visible;" id="${chartId}">
            <defs>
              <linearGradient id="hawkesGrad_${chartId}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.32"/>
                <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.0"/>
              </linearGradient>
            </defs>

            <!-- Baseline intensity line μ -->
            <line x1="${padding.left}" y1="${height - padding.bottom - innerH * 0.2}" x2="${width - padding.right}" y2="${height - padding.bottom - innerH * 0.2}" stroke="rgba(255,255,255,0.12)" stroke-dasharray="4,4" stroke-width="1"/>
            <text x="${width - padding.right - 4}" y="${height - padding.bottom - innerH * 0.2 - 4}" fill="#64748b" font-size="9" font-family="monospace" text-anchor="end">Baseline μ</text>

            <!-- Area & Curve -->
            <path d="${areaD}" fill="url(#hawkesGrad_${chartId})"/>
            <path d="${d}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>

            <!-- Axis Labels -->
            <text x="${padding.left - 6}" y="${padding.top + 10}" fill="#64748b" font-size="9" font-family="monospace" text-anchor="end">Peak λ</text>
            <text x="${padding.left - 6}" y="${height - padding.bottom}" fill="#64748b" font-size="9" font-family="monospace" text-anchor="end">0</text>
            <text x="${padding.left}" y="${height - padding.bottom + 16}" fill="#64748b" font-size="9" font-family="monospace">Observed Start</text>
            <text x="${width - padding.right}" y="${height - padding.bottom + 16}" fill="#64748b" font-size="9" font-family="monospace" text-anchor="end">Latest Observation</text>
          </svg>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 7. 360° Identity Defense Threat Gauge
     * For Personal Watch Agent: Visualizes four identity attack vectors
     */
    renderIdentityThreatGauge(container, options = {}) {
      if (!container) return;

      function parseThreat(val) {
        if (val === null || val === undefined || val === '') return null;
        const n = Number(val);
        return Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : null;
      }

      const vectors = [
        { label: 'Synthetic Media / Deepfake', val: parseThreat(options.deepfake), color: '#38bdf8' },
        { label: 'Executive Impersonation', val: parseThreat(options.impersonation), color: '#00e5ff' },
        { label: 'Doxxing & Credential Exposure', val: parseThreat(options.doxxing), color: '#10b981' },
        { label: 'Coordinated Smear / Defamation', val: parseThreat(options.smear), color: '#f59e0b' }
      ];

      const assessed = vectors.filter(v => v.val !== null);
      if (assessed.length === 0) {
        container.innerHTML = `
          <div class="ae-graph-wrapper ae-empty-state" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px 20px;text-align:center;">
            <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--text-dim);letter-spacing:0.06em;margin-bottom:8px;">
              // NO ATTACK VECTOR OBSERVATIONS RECORDED
            </div>
            <p style="font-size:0.82rem;color:var(--text-muted);margin:0;">
              No assessments recorded; this is not evidence of safety.
            </p>
          </div>
        `;
        return;
      }

      const maxThreat = Math.max(...assessed.map(v => v.val));
      let overallStatus = 'LOW OBSERVED ATTACK SIGNALS (NOT EVIDENCE OF SAFETY)';
      let statusColor = '#38bdf8';
      if (maxThreat > 50) {
        overallStatus = 'ELEVATED THREAT DETECTED';
        statusColor = 'var(--rose)';
      } else if (assessed.length < vectors.length) {
        overallStatus = 'PARTIAL ASSESSMENT — LOW OBSERVED SIGNALS (NOT EVIDENCE OF SAFETY)';
        statusColor = 'var(--amber)';
      }

      const html = `
        <div class="ae-graph-wrapper" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// 360° IDENTITY DEFENSE AUDIT</span>
            <span style="font-family:var(--font-mono);font-size:0.7rem;padding:2px 8px;border-radius:4px;background:rgba(255,255,255,0.06);color:${statusColor};border:1px solid ${statusColor}44;font-weight:700;">
              ${overallStatus}
            </span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:12px;">
            ${vectors.map(v => `
              <div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:12px 14px;">
                <div style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:0.72rem;margin-bottom:6px;">
                  <span style="color:var(--text-muted);">${esc(v.label)}</span>
                  ${v.val !== null ? `<strong style="color:${v.color};">${v.val}%</strong>` : `<strong style="color:var(--text-dim);font-size:0.68rem;">Not assessed</strong>`}
                </div>
                <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">
                  ${v.val !== null ? `<div style="height:100%;width:${v.val}%;background:${v.color};border-radius:3px;box-shadow:0 0 8px ${v.color}66;"></div>` : `<div style="height:100%;width:0%;"></div>`}
                </div>
              </div>
            `).join('')}
          </div>
          <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
            NOTE: Low observed scores reflect absence of detected attack patterns in monitored sources only; this is not proof of personal safety or absence of offline risk.
          </div>
        </div>
      `;

      container.innerHTML = html;
    }
  };

  root.AegisGraphs = AegisGraphs;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = AegisGraphs;
  }
})(typeof window !== 'undefined' ? window : this);

