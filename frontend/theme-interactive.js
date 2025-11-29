/**
 * Theme and Interactive Features
 * Handles dark mode toggle, live clock, and interactive animations
 */

// ============================================================================
// DARK MODE TOGGLE
// ============================================================================

function initThemeToggle() {
  //Check for saved theme preference or default to 'light'
  const currentTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', currentTheme);
  updateThemeIcon(currentTheme);
  updateLogo(currentTheme);

  // Theme toggle button click handler
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const theme = document.documentElement.getAttribute('data-theme');
      const newTheme = theme === 'light' ? 'dark' : 'light';

      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      updateThemeIcon(newTheme);
      updateLogo(newTheme);

      // Add a fast subtle animation to the page
      document.body.style.transition = 'background-color 0.15s ease';
    });
  }
}

function updateThemeIcon(theme) {
  const themeIcon = document.querySelector('.theme-icon');
  if (themeIcon) {
    themeIcon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
}

function updateLogo(theme) {
  const logoImg = document.querySelector('.brand img');
  if (logoImg) {
    const newLogoSrc = theme === 'light' ? '/static/12.png' : '/static/2.png';

    // Super fast transition
    logoImg.style.transition = 'opacity 0.1s ease';
    logoImg.style.opacity = '0';

    setTimeout(() => {
      logoImg.src = newLogoSrc;
      logoImg.style.opacity = '1';
    }, 50);
  }
}

// ============================================================================
// LIVE CLOCK
// ============================================================================

function initClock() {
  updateClock();
  setInterval(updateClock, 1000); // Update every second
}

function updateClock() {
  const clockElement = document.getElementById('clockTime');
  const dateElement = document.getElementById('clockDate');

  if (!clockElement) return;

  const now = new Date();

  // Format time (HH:MM:SS)
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  clockElement.textContent = `${hours}:${minutes}:${seconds}`;

  // Format date (Day, Month DD)
  if (dateElement) {
    const options = { weekday: 'short', month: 'short', day: 'numeric' };
    dateElement.textContent = now.toLocaleDateString('en-US', options);
  }
}

// ============================================================================
// INTERACTIVE CARD ANIMATIONS
// ============================================================================

function initInteractiveCards() {
  // Skip on submit page to avoid interactive textbox
  if (document.getElementById('claimForm')) {
    return;
  }

  const cards = document.querySelectorAll('.card, .claim-card');

  cards.forEach(card => {
    // Add tilt effect on mouse move
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = (y - centerY) / 20;
      const rotateY = (centerX - x) / 20;

      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
    });
  });
}

// ============================================================================
// SMOOTH SCROLL ANIMATIONS
// ============================================================================

function initScrollAnimations() {
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
      }
    });
  }, observerOptions);

  // Observe all cards and sections
  const elements = document.querySelectorAll('.card, section, .stat-card');
  elements.forEach(el => {
    el.classList.add('animate-on-scroll');
    observer.observe(el);
  });
}

// ============================================================================
// BUTTON RIPPLE EFFECT
// ============================================================================

function initRippleEffects() {
  const buttons = document.querySelectorAll('.toggle-btn, .cta, button');

  buttons.forEach(button => {
    button.addEventListener('click', function (e) {
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.classList.add('ripple');

      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });
  });
}

// ============================================================================
// PARALLAX EFFECT FOR HERO SECTION
// ============================================================================

function initParallax() {
  const hero = document.querySelector('.hero');
  if (!hero) return;

  let ticking = false;

  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const scrolled = window.pageYOffset;
        hero.style.transform = `translateY(${scrolled * 0.5}px)`;
        hero.style.opacity = Math.max(0, 1 - (scrolled / 600));
        ticking = false;
      });
      ticking = true;
    }
  });
}

// ============================================================================
// HIDE CTA BUTTONS ON SCROLL (Homepage only)
// ============================================================================

function initCTAScrollHide() {
  const ctaRow = document.querySelector('.cta-row');
  if (!ctaRow) return;

  let ticking = false;
  const hideThreshold = 200; // Hide after scrolling 200px

  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        const scrolled = window.pageYOffset;

        if (scrolled > hideThreshold) {
          ctaRow.classList.add('scroll-hide');
        } else {
          ctaRow.classList.remove('scroll-hide');
        }

        ticking = false;
      });
      ticking = true;
    }
  });
}

// ============================================================================
// INITIALIZE ALL FEATURES
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  console.log('🎨 Initializing theme and interactive features...');

  initThemeToggle();
  initClock();
  initInteractiveCards();
  initScrollAnimations();
  initRippleEffects();
  initParallax();
  initCTAScrollHide();

  console.log('✅ All features initialized!');
});

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
  .animate-on-scroll {
    opacity: 0;
    transform: translateY(30px);
    transition: opacity 0.6s ease, transform 0.6s ease;
  }
  
  .animate-in {
    opacity: 1;
    transform: translateY(0);
  }
  
  .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple-animation 0.6s ease-out;
    pointer-events: none;
  }
  
  @keyframes ripple-animation {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
  
  .card, .claim-card {
    transition: transform 0.3s ease;
  }
`;
document.head.appendChild(style);
