/**
 * aegis-nav.js — Aegis Protocol High-Craft Global Navigation & Command Console
 */
(function() {
  // ── Global XSS Protection Helper ──
  window.escapeHtml = function(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };
  window.sanitizeText = window.escapeHtml;

  // ── 1. Inject SVG Favicon with Bespoke Faceted Prism Emblem ──
  const faviconSvg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 28 28'><defs><linearGradient id='g' x1='0' y1='0' x2='28' y2='28' gradientUnits='userSpaceOnUse'><stop offset='0%' stop-color='%2300f2fe'/><stop offset='100%' stop-color='%23818cf8'/></linearGradient></defs><rect width='28' height='28' rx='6' fill='%2306080d'/><polygon points='14,3 23.5,8 14,14 4.5,8' fill='rgba(0,242,254,0.3)'/><polygon points='4.5,8 14,14 14,24.5 4.5,17' fill='rgba(56,189,248,0.2)'/><polygon points='23.5,8 14,14 14,24.5 23.5,17' fill='rgba(129,140,248,0.25)'/><path d='M14 3L23.5 8V17L14 24.5L4.5 17V8L14 3Z' stroke='url(%23g)' stroke-width='1.4' fill='none'/><path d='M14 3V14M4.5 8L14 14M23.5 8L14 14M14 14V24.5' stroke='url(%23g)' stroke-width='0.9' stroke-opacity='0.6'/><polygon points='14,11.5 16.5,14 14,16.5 11.5,14' fill='%2300f2fe'/></svg>`;
  
  let fav = document.querySelector('link[rel="icon"]');
  if (!fav) {
    fav = document.createElement('link');
    fav.rel = 'icon';
    fav.type = 'image/svg+xml';
    document.head.appendChild(fav);
  }
  fav.href = `data:image/svg+xml,${encodeURIComponent(faviconSvg)}`;

  // ── 2. Top Navigation Bar Definition ──
  const pages = {
    home:      { href: 'index.html',     label: 'Home' },
    agents:    { href: 'agents.html',    label: 'Agents' },
    submit:    { href: 'submit.html',    label: 'Submit Claim' },
    dashboard: { href: 'dashboard.html', label: 'Dashboard' },
    status:    { href: 'status.html',    label: 'Status' },
    about:     { href: 'about.html',     label: 'About' }
  };

  const active = (window.AEGIS_ACTIVE || '').toLowerCase();
  const linksHtml = Object.entries(pages).map(([key, p]) => {
    const isAct = (key === active) || (key === 'submit' && active === 'lab');
    const cls = isAct ? 'ae-nav-link ae-active' : 'ae-nav-link';
    return `<a href="${p.href}" class="${cls}">${p.label}</a>`;
  }).join('');

  const header = document.createElement('header');
  header.className = 'ae-nav-bar';
  header.id = 'aeGlobalNav';
  header.innerHTML = `
    <div class="ae-nav-inner">
      <a href="index.html" class="ae-nav-brand" aria-label="Aegis Protocol">
        <div class="ae-brand-icon-wrap" title="Aegis Protocol">
          <svg viewBox="0 0 28 28" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="ae-nav-stroke" x1="4" y1="2.5" x2="24" y2="25.5" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#00f2fe" />
                <stop offset="50%" stop-color="#38bdf8" />
                <stop offset="100%" stop-color="#818cf8" />
              </linearGradient>
              <linearGradient id="ae-nfac-top" x1="14" y1="2.5" x2="14" y2="14" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#00f2fe" stop-opacity="0.4" />
                <stop offset="100%" stop-color="#00f2fe" stop-opacity="0.05" />
              </linearGradient>
              <linearGradient id="ae-nfac-left" x1="4" y1="7.5" x2="14" y2="25.5" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.22" />
                <stop offset="100%" stop-color="#06090f" stop-opacity="0.85" />
              </linearGradient>
              <linearGradient id="ae-nfac-right" x1="24" y1="7.5" x2="14" y2="25.5" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="#818cf8" stop-opacity="0.28" />
                <stop offset="100%" stop-color="#06090f" stop-opacity="0.85" />
              </linearGradient>
            </defs>
            <polygon points="14,2.5 24,7.5 14,14 4,7.5" fill="url(#ae-nfac-top)" />
            <polygon points="4,7.5 14,14 14,25.5 4,16.5" fill="url(#ae-nfac-left)" />
            <polygon points="24,7.5 14,14 14,25.5 24,16.5" fill="url(#ae-nfac-right)" />
            <path d="M14 2.5 L24 7.5 L24 16.5 L14 25.5 L4 16.5 L4 7.5 Z" stroke="url(#ae-nav-stroke)" stroke-width="1.3" stroke-linejoin="round" />
            <path d="M14 2.5 L14 14 M4 7.5 L14 14 M24 7.5 L14 14 M14 14 L14 25.5" stroke="url(#ae-nav-stroke)" stroke-width="0.9" stroke-opacity="0.65" stroke-linejoin="round" />
            <polygon points="14,11.2 16.8,14 14,16.8 11.2,14" fill="#00f2fe" fill-opacity="0.95" stroke="#ffffff" stroke-width="0.75" />
          </svg>
        </div>
        <div class="ae-brand-text">
          <span class="ae-brand-name">AEGIS</span>
          <span class="ae-brand-sub">PROTOCOL</span>
        </div>
      </a>

      <nav class="ae-nav-links-wrap" aria-label="Main Navigation">
        ${linksHtml}
      </nav>

      <div class="ae-nav-actions">
        <button type="button" class="ae-nav-cmd-trigger" id="aeCmdTrigger" aria-label="Quick Search">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <span>Search</span>
          <kbd style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);padding:1px 4px;border-radius:4px;font-size:0.68rem;">⌘K</kbd>
        </button>
        <a href="submit.html" class="ae-nav-submit-btn">
          <span>Submit Claim</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </a>
      </div>
    </div>
  `;

  // Remove duplicate legacy headers
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('header.navbar, header.ae-nav, .ae-nav-wrapper').forEach(el => {
      if (el !== header) el.remove();
    });
  });

  document.body.prepend(header);

  // ── 3. Command Palette Modal Engine ──
  const cmdPaletteItems = [
    { label: 'Home', href: 'index.html', group: 'Navigation', key: 'Home' },
    { label: 'Agents Overview', href: 'agents.html', group: 'Navigation', key: 'Agents' },
    { label: 'Submit Claim to Verify', href: 'submit.html', group: 'Actions', key: 'Verify' },
    { label: 'Live Dashboard', href: 'dashboard.html', group: 'Navigation', key: 'Dash' },
    { label: 'System Status', href: 'status.html', group: 'System', key: 'Status' },
    { label: 'About Aegis', href: 'about.html', group: 'Information', key: 'About' },
    { label: 'Trending Agent (Viral Social Media)', href: 'trending-agent.html', group: 'Agents', key: 'Trend' },
    { label: 'Scout Agent (Stocks & Financial Markets)', href: 'scout-agent.html', group: 'Agents', key: 'Scout' },
    { label: 'Personal Watch (Defamation & People)', href: 'personal-watch-agent.html', group: 'Agents', key: 'Watch' },
    { label: 'BrandShield (Corporate & Brand Defense)', href: 'brandshield-agent.html', group: 'Agents', key: 'Brand' },
    { label: 'Threat Analysis Matrix', href: 'submit.html#threat-matrix', group: 'Tools', key: 'Matrix' },
    { label: 'Changelog', href: 'changelog.html', group: 'System', key: 'Logs' }
  ];

  function initCommandPalette() {
    let backdrop = document.getElementById('cmdPalette');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'cmdPalette';
      backdrop.className = 'cmd-palette-backdrop';
      backdrop.innerHTML = `
        <div class="cmd-palette-box">
          <div class="cmd-input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-dim)"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <input type="text" class="cmd-input" id="cmdPaletteInput" placeholder="Type a command, tool, or page..." autocomplete="off" spellcheck="false" />
            <kbd style="font-family:var(--font-mono);font-size:0.7rem;background:rgba(255,255,255,0.06);border:1px solid var(--border);padding:2px 6px;border-radius:4px;color:var(--text-dim);">ESC</kbd>
          </div>
          <div class="cmd-list" id="cmdPaletteList"></div>
        </div>
      `;
      document.body.appendChild(backdrop);
    }

    const input = document.getElementById('cmdPaletteInput');
    const list = document.getElementById('cmdPaletteList');
    let selectedIndex = 0;
    let filteredItems = [...cmdPaletteItems];

    function renderList() {
      if (filteredItems.length === 0) {
        list.innerHTML = `<div style="padding:18px 14px;color:var(--text-dim);font-size:0.85rem;text-align:center;">No matching commands found.</div>`;
        return;
      }
      list.innerHTML = filteredItems.map((item, idx) => `
        <a href="${item.href}" class="cmd-item ${idx === selectedIndex ? 'selected' : ''}" data-idx="${idx}">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:0.75rem;color:var(--accent);font-family:var(--font-mono);background:rgba(0,229,255,0.08);border:1px solid rgba(0,229,255,0.18);padding:2px 6px;border-radius:4px;">${item.group}</span>
            <span>${item.label}</span>
          </div>
          <span class="cmd-item-key">${item.key}</span>
        </a>
      `).join('');

      list.querySelectorAll('.cmd-item').forEach(el => {
        el.addEventListener('mouseenter', () => {
          const idx = parseInt(el.dataset.idx, 10);
          selectedIndex = idx;
          updateSelection();
        });
      });
    }

    function updateSelection() {
      list.querySelectorAll('.cmd-item').forEach((el, idx) => {
        el.classList.toggle('selected', idx === selectedIndex);
      });
    }

    function openPalette() {
      backdrop.classList.add('open');
      input.value = '';
      filteredItems = [...cmdPaletteItems];
      selectedIndex = 0;
      renderList();
      setTimeout(() => input.focus(), 50);
    }

    function closePalette() {
      backdrop.classList.remove('open');
      input.blur();
    }

    // Toggle triggers
    const triggerBtn = document.getElementById('aeCmdTrigger');
    if (triggerBtn) {
      triggerBtn.addEventListener('click', e => {
        e.preventDefault();
        openPalette();
      });
    }

    backdrop.addEventListener('click', e => {
      if (e.target === backdrop) closePalette();
    });

    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      filteredItems = cmdPaletteItems.filter(item => 
        item.label.toLowerCase().includes(q) ||
        item.group.toLowerCase().includes(q) ||
        item.key.toLowerCase().includes(q)
      );
      selectedIndex = 0;
      renderList();
    });

    input.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        closePalette();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % filteredItems.length;
        updateSelection();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + filteredItems.length) % filteredItems.length;
        updateSelection();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          window.location.href = filteredItems[selectedIndex].href;
        }
      }
    });

    window.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        if (backdrop.classList.contains('open')) {
          closePalette();
        } else {
          openPalette();
        }
      }
    });
  }

  // ── 4. Card Specular Lighting (Tilt disabled for stability) ──
  function init3DCardTilt() {
    document.querySelectorAll('.bento-card, .ag-card, .instrument-card, .submit-card').forEach(card => {
      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty('--mouse-x', `${e.clientX - rect.left}px`);
        card.style.setProperty('--mouse-y', `${e.clientY - rect.top}px`);
        // No 3D transform or tilt on mousemove - keeps cards stable and normal
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'none';
      });
    });
  }

  // ── 5. Scroll Reveal Observer ──
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.06 });

  function initAll() {
    document.querySelectorAll('.ae-reveal').forEach(el => observer.observe(el));
    init3DCardTilt();
    initCommandPalette();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
