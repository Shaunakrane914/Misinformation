/**
 * aegis-nav.js — Shared navbar + cursor + grid bg for all pages
 * Include this in every page: <script src="aegis-nav.js"></script>
 * Set window.AEGIS_ACTIVE to the current page key before loading.
 */
(function() {
  // ── Inject SVG Favicon ──
  if (!document.querySelector('link[rel="icon"]')) {
    const fav = document.createElement('link');
    fav.rel = 'icon';
    fav.type = 'image/svg+xml';
    fav.href = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 28 28'><rect width='28' height='28' rx='6' fill='%230f1629'/><path d='M14 3L23 7.5V14C23 18.9 19 23.2 14 24.5C9 23.2 5 18.9 5 14V7.5L14 3Z' fill='%231e40af' stroke='%233b82f6' stroke-width='1.5'/><path d='M10.5 14L13 16.5L17.5 11.5' stroke='%233b82f6' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>";
    document.head.appendChild(fav);
  }

  // ── Remove old navbar (prevents double navbar on agent pages) ──
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('header.navbar, header:not(.ae-nav)').forEach(el => {
      if (!el.classList.contains('ae-nav')) el.remove();
    });
  });

  // ── Also remove synchronously in case it's already rendered ──
  setTimeout(() => {
    document.querySelectorAll('header.navbar').forEach(el => el.remove());
  }, 0);


  const cur = document.createElement('div'); cur.id = 'aeCursor';
  const ring = document.createElement('div'); ring.id = 'aeCursorRing';
  document.body.prepend(ring); document.body.prepend(cur);

  // ── Cursor tracking (using CSS custom props for grid glow) ──
  let cx = window.innerWidth / 2, cy = window.innerHeight / 2;
  let rx = cx, ry = cy;

  document.addEventListener('mousemove', e => {
    cx = e.clientX; cy = e.clientY;
    cur.style.left = cx + 'px'; cur.style.top = cy + 'px';
    // Update CSS custom props for grid glow (no canvas, no lag)
    document.body.style.setProperty('--mx', cx + 'px');
    document.body.style.setProperty('--my', cy + 'px');
  });

  function animRing() {
    rx += (cx - rx) * 0.14;
    ry += (cy - ry) * 0.14;
    ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
    requestAnimationFrame(animRing);
  }
  animRing();

  document.addEventListener('mouseover', e => {
    if (e.target.closest('a, button, input, textarea, select, .ae-card, .agent-card')) {
      document.body.classList.add('cursor-hover');
    } else {
      document.body.classList.remove('cursor-hover');
    }
  });

  // ── Navbar HTML ──
  const pages = {
    home:      { href: 'index.html',     label: 'Home' },
    agents:    { href: 'agents.html',    label: 'Agents' },
    about:     { href: 'about.html',     label: 'About' },
    dashboard: { href: 'dashboard.html', label: 'Dashboard' },
    submit:    { href: 'submit.html',    label: 'Submit Claim', cta: true },
  };

  const active = window.AEGIS_ACTIVE || '';
  const links = Object.entries(pages).map(([key, p]) => {
    const cls = (key === active ? ' ae-active' : '') + (p.cta ? ' ae-nav-cta' : '');
    return `<a href="${p.href}" class="${cls.trim()}">${p.label}</a>`;
  }).join('');

  const nav = document.createElement('header');
  nav.className = 'ae-nav';
  nav.innerHTML = `
    <a href="index.html" class="ae-nav-brand">
      <svg viewBox="0 0 28 28" fill="none">
        <path d="M14 2L24 7V15C24 20.5 19.5 25.4 14 26C8.5 25.4 4 20.5 4 15V7L14 2Z"
              stroke="#3b82f6" stroke-width="1.8" fill="rgba(59,130,246,0.1)"/>
        <path d="M10 14L13 17L18 11" stroke="#3b82f6" stroke-width="2"
              stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Aegis Protocol
    </a>
    <nav class="ae-nav-links">${links}</nav>`;

  document.body.prepend(nav);

  // ── Reveal on scroll ──
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
  }, { threshold: 0.08 });

  function observeReveal() {
    document.querySelectorAll('.ae-reveal').forEach(el => observer.observe(el));
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeReveal);
  } else {
    observeReveal();
  }
})();
