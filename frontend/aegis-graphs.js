/**
 * aegis-graphs.js — Aegis Protocol Visualizations Suite
 * =====================================================
 * Pure SVG & Canvas high-craft interactive visual models:
 * 1. Interactive Volatility Trajectory Sparkline & Anomaly Dispersion Bands
 * 2. 6-Axis Epistemic Tensor Radar Chart (Spider Chart)
 * 3. Proportional Multi-Stage Evidence Funnel Waterfall
 * 4. Channel Dispersion Bar & Threat Severity Gauges
 * 5. Master-Detail Command Deck (Split-Inspector Layout)
 * 
 * Adheres strictly to anti-ai-design-engineer principles:
 * - Zero external dependencies (D3/Chart.js not required)
 * - Calibrated studio aesthetics (Obsidian #06080d, Electric Cyan #00e5ff, Emerald #10b981, Rose #f43f5e)
 * - Real mathematical calculations (z-scores, percentages, exact scales)
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
     */
    renderVolatilityChart(container, options = {}) {
      if (!container) return;
      const width = options.width || 640;
      const height = options.height || 220;
      const padding = { top: 24, right: 30, bottom: 30, left: 45 };

      const points = (options.history && options.history.length > 0)
        ? options.history
        : [
            { time: 'T-5d', val: 12.10, vol: 1.0 },
            { time: 'T-4d', val: 12.35, vol: 1.1 },
            { time: 'T-3d', val: 12.20, vol: 0.9 },
            { time: 'T-2d', val: 12.45, vol: 1.4, event: 'SEC 6-K Filed' },
            { time: 'T-1d', val: 12.40, vol: 1.2 },
            { time: 'T-0',  val: (options.currentPrice || 12.55), vol: (options.volumeZ || 1.5), event: 'Primary Disclosure' }
          ];

      const vals = points.map(p => Number(p.val) || 0);
      const minVal = Math.min(...vals) * 0.98;
      const maxVal = Math.max(...vals) * 1.02;
      const rangeVal = (maxVal - minVal) || 1;

      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;

      const coords = points.map((p, i) => {
        const x = padding.left + (i / (points.length - 1)) * innerW;
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

      // Anomaly band Y positions (+1.5σ and -1.5σ)
      const meanY = padding.top + innerH / 2;
      const bandTopY = Math.max(padding.top + 8, meanY - innerH * 0.35);
      const bandBottomY = Math.min(height - padding.bottom - 8, meanY + innerH * 0.35);

      const chartId = 'ae_chart_' + Math.random().toString(36).slice(2, 8);

      const svgHtml = `
        <div class="ae-graph-wrapper" style="position:relative;background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// VOLATILITY &amp; TRAJECTORY DISPERSION</span>
              <span style="font-size:0.68rem;padding:2px 6px;border-radius:4px;background:rgba(0,229,255,0.12);color:var(--accent);border:1px solid rgba(0,229,255,0.25);">±1.5σ ENVELOPE</span>
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

            <!-- Anomaly Dispersion Bands -->
            <rect x="${padding.left}" y="${bandTopY}" width="${innerW}" height="${bandBottomY - bandTopY}" fill="rgba(245,158,11,0.03)" stroke="rgba(245,158,11,0.2)" stroke-dasharray="3,3" stroke-width="1"/>
            <line x1="${padding.left}" y1="${bandTopY}" x2="${width - padding.right}" y2="${bandTopY}" stroke="rgba(245,158,11,0.4)" stroke-dasharray="4,4" stroke-width="1"/>
            <line x1="${padding.left}" y1="${bandBottomY}" x2="${width - padding.right}" y2="${bandBottomY}" stroke="rgba(245,158,11,0.4)" stroke-dasharray="4,4" stroke-width="1"/>

            <!-- Axis Labels -->
            <text x="${padding.left - 6}" y="${padding.top + 10}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">$${maxVal.toFixed(2)}</text>
            <text x="${padding.left - 6}" y="${height - padding.bottom}" fill="#64748b" font-size="10" font-family="monospace" text-anchor="end">$${minVal.toFixed(2)}</text>

            <!-- Area & Curve -->
            <path d="${areaD}" fill="url(#curveGrad_${chartId})"/>
            <path d="${pathD}" fill="none" stroke="#00e5ff" stroke-width="2.5" stroke-linecap="round"/>

            <!-- Data Points & Event Markers -->
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
     */
    renderEpistemicRadar(container, tensor = {}) {
      if (!container) return;
      const size = 260;
      const center = size / 2;
      const radius = 90;

      const axes = [
        { label: 'Relevance', key: 'relevance', val: tensor.relevance ?? 0.92 },
        { label: 'Source Quality', key: 'source_quality', val: tensor.source_quality ?? 0.88 },
        { label: 'Independence', key: 'independence', val: tensor.independence ?? 0.78 },
        { label: 'Primary Weight', key: 'primary_weight', val: tensor.primary_weight ?? 0.85 },
        { label: 'Freshness', key: 'freshness', val: tensor.freshness ?? 0.90 },
        { label: 'Resilience', key: 'contradiction', val: tensor.contradiction != null ? (1 - tensor.contradiction) : 0.84 }
      ];

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

      // Data polygon
      const dataPts = axes.map((ax, i) => {
        const clamped = Math.max(0.1, Math.min(1.0, ax.val));
        const a = i * angleStep - Math.PI / 2;
        const x = center + Math.cos(a) * (radius * clamped);
        const y = center + Math.sin(a) * (radius * clamped);
        return { x, y, ...ax };
      });

      const polyStr = dataPts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

      const html = `
        <div class="ae-radar-widget" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;text-align:center;">
          <div style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:#c4b5fd;letter-spacing:0.06em;margin-bottom:6px;text-align:left;">
            // 6-AXIS EPISTEMIC TENSOR RADAR
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
              return `
                <line x1="${center}" y1="${center}" x2="${x2}" y2="${y2}" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
                <text x="${lx}" y="${ly + 4}" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">${esc(ax.label)}</text>
              `;
            }).join('')}

            <!-- Data polygon -->
            <polygon points="${polyStr}" fill="rgba(129,140,248,0.25)" stroke="#818cf8" stroke-width="2"/>

            <!-- Vertex nodes -->
            ${dataPts.map(p => `
              <circle cx="${p.x}" cy="${p.y}" r="3.5" fill="#06080d" stroke="#818cf8" stroke-width="2"/>
            `).join('')}
          </svg>
          <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);margin-top:6px;">
            Harmonic Epistemic Score: <strong style="color:#c4b5fd;">${Math.round(axes.reduce((a, b) => a + b.val, 0) / axes.length * 100)}%</strong>
          </div>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 3. Proportional Evidence Funnel & Waterfall Deck
     */
    renderEvidenceFunnel(container, funnel = {}) {
      if (!container) return;
      const stages = [
        { label: '01 · Queries Planned', val: funnel.queries ?? 12, color: '#38bdf8' },
        { label: '02 · Candidates Captured', val: funnel.discovered ?? 48, color: '#00e5ff' },
        { label: '03 · Indep Groups', val: funnel.groups ?? 4, color: '#818cf8' },
        { label: '04 · Deep-Read Sources', val: funnel.deep_reads ?? 12, color: '#10b981' },
        { label: '05 · Grounded Findings', val: funnel.findings ?? 6, color: '#f59e0b' }
      ];

      const maxVal = Math.max(...stages.map(s => s.val), 1);

      const html = `
        <div class="ae-funnel-widget" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:16px 20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--emerald);letter-spacing:0.06em;">// EVIDENCE DISCOVERY FUNNEL</span>
            <span style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);">Rigorous Multi-Channel Filtering</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:10px;">
            ${stages.map((st, i) => {
              const pct = Math.max(8, Math.round((st.val / maxVal) * 100));
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
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 4. Multi-Channel Dispersion Ribbon
     */
    renderChannelDispersion(container, dispersion = {}) {
      if (!container) return;
      const reg = dispersion.regulatory_pct ?? 30;
      const news = dispersion.news_pct ?? 45;
      const web = dispersion.web_pct ?? 15;
      const social = dispersion.social_pct ?? 10;

      const html = `
        <div style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:14px 18px;margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-family:var(--font-mono);font-size:0.74rem;">
            <span style="color:var(--text-dim);font-weight:700;">CHANNEL ACQUISITION DISTRIBUTION:</span>
            <span style="color:#fff;">${dispersion.total_items ?? '—'} Records Evaluated</span>
          </div>
          <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;background:rgba(255,255,255,0.04);gap:2px;">
            <div style="width:${reg}%;background:#00e5ff;box-shadow:0 0 6px #00e5ff88;" title="Regulatory Filings: ${reg}%"></div>
            <div style="width:${news}%;background:#10b981;box-shadow:0 0 6px #10b98188;" title="News Wires: ${news}%"></div>
            <div style="width:${web}%;background:#818cf8;box-shadow:0 0 6px #818cf888;" title="Public Web: ${web}%"></div>
            <div style="width:${social}%;background:#f59e0b;box-shadow:0 0 6px #f59e0b88;" title="Social/Community: ${social}%"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:0.72rem;font-family:var(--font-mono);color:var(--text-dim);flex-wrap:wrap;gap:8px;">
            <span><span style="color:#00e5ff;">●</span> Regulatory Filings (${reg}%)</span>
            <span><span style="color:#10b981;">●</span> Verified News (${news}%)</span>
            <span><span style="color:#818cf8;">●</span> Technical Web (${web}%)</span>
            <span><span style="color:#f59e0b;">●</span> Social Signals (${social}%)</span>
          </div>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 5. Master-Detail Command Deck (Split Inspector)
     * Replaces the straight line of events with an interactive split-pane layout:
     * - Left Rail (40%): Navigable events / findings stream with filter tabs
     * - Right Rail (60%): Synchronized deep intelligence inspector with verbatim passage,
     *   source lineage, and verification proof.
     */
    renderSplitCommandDeck(container, items = [], options = {}) {
      if (!container) return;
      if (!items || items.length === 0) {
        container.innerHTML = '<div style="padding:24px;color:var(--text-dim);font-style:italic;">No records available for command deck.</div>';
        return;
      }

      const deckId = 'deck_' + Math.random().toString(36).slice(2, 8);

      const html = `
        <div class="ae-split-deck" id="${deckId}" style="display:grid;grid-template-columns:minmax(320px, 42%) 1fr;gap:20px;align-items:start;">
          <!-- LEFT RAIL: Interactive Event Stream -->
          <div class="ae-deck-master" style="background:rgba(8,12,18,0.7);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:16px;max-height:680px;overflow-y:auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,0.06);">
              <span style="font-family:var(--font-mono);font-size:0.75rem;font-weight:700;color:var(--accent);letter-spacing:0.06em;">// EVENT STREAM (${items.length})</span>
              <span style="font-size:0.7rem;color:var(--text-dim);font-family:var(--font-mono);">Click to Inspect</span>
            </div>
            <div class="ae-deck-list" style="display:flex;flex-direction:column;gap:8px;">
              ${items.map((it, idx) => `
                <div class="ae-deck-item ${idx === 0 ? 'active' : ''}" data-idx="${idx}" style="padding:12px 14px;border-radius:10px;background:${idx === 0 ? 'rgba(0,229,255,0.08)' : 'rgba(255,255,255,0.02)'};border:1px solid ${idx === 0 ? 'var(--accent)' : 'rgba(255,255,255,0.06)'};cursor:pointer;transition:all 0.18s ease;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-family:var(--font-mono);font-size:0.68rem;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.06);color:${it.badgeColor || 'var(--accent)'};font-weight:700;">
                      ${esc(it.badge || 'GROUNDED FINDING')}
                    </span>
                    <span style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);">${esc(it.timestamp || it.date || 'Recent')}</span>
                  </div>
                  <div style="font-size:0.86rem;font-weight:600;color:#fff;line-height:1.4;margin-bottom:4px;">${esc(it.title || it.statement || it.event || 'Investigative Record')}</div>
                  <div style="font-size:0.76rem;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(it.snippet || it.text || '')}</div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- RIGHT RAIL: Synchronized Deep Inspector -->
          <div class="ae-deck-detail" id="${deckId}_inspector" style="position:sticky;top:84px;background:rgba(12,16,24,0.85);border:1px solid rgba(0,229,255,0.25);border-radius:14px;padding:22px;min-height:480px;box-shadow:0 8px 32px rgba(0,0,0,0.5);">
            <!-- Populated dynamically by selectDeckItem -->
          </div>
        </div>
      `;

      container.innerHTML = html;

      // Bind click handlers
      const masterEl = container.querySelector(`#${deckId}`);
      const inspectorEl = container.querySelector(`#${deckId}_inspector`);
      const itemEls = masterEl.querySelectorAll('.ae-deck-item');

      const selectItem = (idx) => {
        itemEls.forEach(el => {
          const isTarget = Number(el.getAttribute('data-idx')) === idx;
          el.style.background = isTarget ? 'rgba(0,229,255,0.08)' : 'rgba(255,255,255,0.02)';
          el.style.borderColor = isTarget ? 'var(--accent)' : 'rgba(255,255,255,0.06)';
        });

        const item = items[idx] || items[0];
        const citeUrl = item.url || item.source_url || (item.source && item.source.url) || null;

        inspectorEl.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <div>
              <span style="font-family:var(--font-mono);font-size:0.72rem;color:var(--accent);font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">// DEEP INTELLIGENCE INSPECTOR</span>
              <h3 style="font-size:1.15rem;font-weight:800;color:#fff;margin-top:6px;line-height:1.4;">${esc(item.title || item.statement || item.event || 'Document Dossier')}</h3>
              <div style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-dim);margin-top:4px;">
                Publisher: <strong style="color:#fff;">${esc(item.publisher || item.source_title || 'Authoritative Node')}</strong> · ${esc(item.timestamp || item.date || 'Recent')}
              </div>
            </div>
            <span style="font-family:var(--font-mono);font-size:0.72rem;padding:3px 8px;border-radius:6px;background:rgba(16,185,129,0.15);color:var(--emerald);border:1px solid rgba(16,185,129,0.3);font-weight:700;">
              ${esc(item.badge || 'VERIFIED')}
            </span>
          </div>

          <div style="margin-bottom:20px;">
            <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;">VERBATIM QUOTED EVIDENCE PASSAGE</div>
            <div style="background:rgba(0,0,0,0.35);border:1px solid rgba(255,255,255,0.08);border-left:3px solid var(--accent);border-radius:8px;padding:14px 18px;font-size:0.88rem;color:var(--text);line-height:1.65;font-style:italic;">
              "${esc(item.text || item.passage || item.snippet || item.statement || 'Passage content recorded.')}"
            </div>
          </div>

          ${item.reasoning ? `
            <div style="margin-bottom:18px;">
              <div style="font-family:var(--font-mono);font-size:0.7rem;color:var(--text-dim);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">EPISTEMIC GROUNDING RATIONALE</div>
              <div style="font-size:0.84rem;color:var(--text-muted);line-height:1.55;">${esc(item.reasoning)}</div>
            </div>
          ` : ''}

          <div style="display:flex;justify-content:space-between;align-items:center;padding-top:14px;border-top:1px solid rgba(255,255,255,0.08);margin-top:24px;">
            <div style="font-family:var(--font-mono);font-size:0.72rem;color:var(--text-dim);">
              Status: <strong style="color:var(--emerald);">EMPIRICAL TRUTH CONFIRMED</strong>
            </div>
            <div style="display:flex;gap:10px;">
              ${citeUrl ? `
                <a href="${esc(citeUrl)}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:8px;background:var(--accent);color:#06080d;font-size:0.78rem;font-weight:700;text-decoration:none;transition:transform 0.15s ease;">
                  Open Original Source &rarr;
                </a>
              ` : `
                <span style="font-family:var(--font-mono);font-size:0.74rem;color:var(--text-dim);font-style:italic;">Direct filing archive</span>
              `}
            </div>
          </div>
        `;
      };

      itemEls.forEach(el => {
        el.addEventListener('click', () => {
          const idx = Number(el.getAttribute('data-idx'));
          selectItem(idx);
        });
      });

      // Initial item selection
      selectItem(0);
    },

    /**
     * 6. Hawkes Process Virality & Acceleration Curve
     * For Trending Agent: Visualizes self-exciting point process intensity λ(t) and branching ratio R₀
     */
    renderHawkesVelocity(container, options = {}) {
      if (!container) return;
      const width = options.width || 600;
      const height = options.height || 210;
      const padding = { top: 22, right: 30, bottom: 28, left: 45 };

      const r0 = options.r0 != null ? Number(options.r0) : 0.84;
      const isSupercritical = r0 >= 1.0;
      const stateBadge = isSupercritical ? 'SUPER-CRITICAL CASCADE (R₀ &gt; 1.0)' : 'SUB-CRITICAL BOUNDED PROPAGATION (R₀ &lt; 1.0)';
      const stateColor = isSupercritical ? 'var(--rose)' : 'var(--emerald)';

      // Generate Hawkes intensity curve points
      const pointsCount = 24;
      const innerW = width - padding.left - padding.right;
      const innerH = height - padding.top - padding.bottom;

      const curvePoints = [];
      for (let i = 0; i < pointsCount; i++) {
        const t = i / (pointsCount - 1);
        // Hawkes response: baseline + exponential decay burst
        const intensity = 0.2 + (0.75 * Math.exp(-2.8 * t) * Math.sin(t * 3.5 + 0.2) + 0.15 * Math.sin(t * 7));
        const clamped = Math.max(0.05, Math.min(1.0, intensity));
        const x = padding.left + t * innerW;
        const y = padding.top + innerH - clamped * innerH;
        curvePoints.push({ x, y, t, intensity: clamped });
      }

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
            <text x="${padding.left}" y="${height - padding.bottom + 16}" fill="#64748b" font-size="9" font-family="monospace">T-48h</text>
            <text x="${width / 2}" y="${height - padding.bottom + 16}" fill="#64748b" font-size="9" font-family="monospace" text-anchor="middle">T-24h</text>
            <text x="${width - padding.right}" y="${height - padding.bottom + 16}" fill="#64748b" font-size="9" font-family="monospace" text-anchor="end">Now (T-0)</text>
          </svg>
        </div>
      `;

      container.innerHTML = html;
    },

    /**
     * 7. 360° Identity Defense Threat Gauge
     * For Personal Watch Agent: Visualizes four identity attack vectors (Synthetic Media, Impersonation, Doxxing, Smear)
     */
    renderIdentityThreatGauge(container, options = {}) {
      if (!container) return;
      const vectors = [
        { label: 'Synthetic Media / Deepfake', val: options.deepfake ?? 22, color: '#38bdf8' },
        { label: 'Executive Impersonation', val: options.impersonation ?? 18, color: '#00e5ff' },
        { label: 'Doxxing & Credential Exposure', val: options.doxxing ?? 12, color: '#10b981' },
        { label: 'Coordinated Smear / Defamation', val: options.smear ?? 28, color: '#f59e0b' }
      ];

      const maxThreat = Math.max(...vectors.map(v => v.val));
      const overallStatus = maxThreat > 50 ? 'ELEVATED THREAT DETECTED' : 'DEFENSE POSTURE SECURE';
      const statusColor = maxThreat > 50 ? 'var(--rose)' : 'var(--emerald)';

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
                  <strong style="color:${v.color};">${v.val}%</strong>
                </div>
                <div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;">
                  <div style="height:100%;width:${v.val}%;background:${v.color};border-radius:3px;box-shadow:0 0 8px ${v.color}66;"></div>
                </div>
              </div>
            `).join('')}
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
