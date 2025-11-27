document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;

  // Ensure exiting class does not persist on back/forward cache restores
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      body.classList.remove('page-exit');
    }
  });

  // Intercept same-origin navigations to create a smooth exit transition
  const localLinks = document.querySelectorAll('a[href]');

  localLinks.forEach((link) => {
    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
      return;
    }

    link.addEventListener('click', (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }

      if (link.target === '_blank') {
        return;
      }

      const destination = new URL(href, window.location.href);
      if (destination.origin !== window.location.origin) {
        return;
      }

      if (destination.pathname === window.location.pathname && destination.search === window.location.search) {
        return;
      }

      event.preventDefault();
      body.classList.add('page-exit');
      setTimeout(() => {
        window.location.href = destination.href;
      }, 250);
    });
  });

  // Intersection observer driven reveal animations
  const revealElements = document.querySelectorAll('[data-reveal]');

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const delay = entry.target.dataset.revealDelay;
            if (delay) {
              entry.target.style.setProperty('--reveal-delay', delay);
            }
            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    revealElements.forEach((el) => observer.observe(el));
  } else {
    revealElements.forEach((el) => el.classList.add('is-visible'));
  }
});


