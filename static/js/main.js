// ---- Theme toggle (dark by default, light on request) ----
// Initial theme is already applied by an inline script in <head> (before
// first paint, to avoid a flash of the wrong theme). This just wires up
// the toggle buttons and persists the choice.
const htmlEl = document.documentElement;
const themeToggleDesktop = document.getElementById('themeToggleDesktop');
const themeToggleMobile = document.getElementById('themeToggleMobile');

function getCurrentTheme() {
  return htmlEl.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}

function setTheme(theme) {
  htmlEl.setAttribute('data-theme', theme);
  try {
    localStorage.setItem('theme', theme);
  } catch (e) {
    // localStorage unavailable (private browsing, etc.) — theme just
    // won't persist across reloads, which is fine.
  }
}

function toggleTheme() {
  setTheme(getCurrentTheme() === 'dark' ? 'light' : 'dark');
}

[themeToggleDesktop, themeToggleMobile].forEach((btn) => {
  if (btn) btn.addEventListener('click', toggleTheme);
});

// ---- First-visit hint pointing at the theme toggle ----
// Shows the existing hover tooltip once, unprompted, shortly after page
// load, so first-time visitors notice the toggle exists without having to
// stumble onto it. Never shows again once seen (tracked in localStorage).
(function () {
  var HINT_SEEN_KEY = 'themeToggleHintSeen';
  var tip = themeToggleDesktop ? themeToggleDesktop.querySelector('.toggle-tip') : null;
  if (!tip) return;

  var alreadySeen;
  try {
    alreadySeen = localStorage.getItem(HINT_SEEN_KEY);
  } catch (e) {
    alreadySeen = true; // no localStorage (private browsing, etc.) — skip the hint
  }
  if (alreadySeen) return;

  var hideTimer;

  function dismiss() {
    // Fade out first, keeping the hint text/colors in place — only swap
    // .toggle-tip back to its normal hover-driven content (tip-light/
    // tip-dark) once the opacity transition has actually finished, so it
    // never flashes "Switch to light mode" mid-fade.
    tip.classList.add('hint-fading');
    themeToggleDesktop.classList.remove('hint-flash');
    clearTimeout(hideTimer);
    try {
      localStorage.setItem(HINT_SEEN_KEY, '1');
    } catch (e) {
      // can't persist — hint may show again next visit, which is fine.
    }
    setTimeout(function () {
      tip.classList.remove('show-hint', 'hint-fading');
    }, 250);
  }

  setTimeout(function () {
    tip.classList.add('show-hint');
    themeToggleDesktop.classList.add('hint-flash');
    hideTimer = setTimeout(dismiss, 4000);
    themeToggleDesktop.addEventListener('click', dismiss, { once: true });
  }, 1200);
})();

// ---- Hide navbar on scroll down, show on scroll up ----
const siteHeader = document.querySelector('.site-header');

if (siteHeader) {
  let lastScrollY = window.scrollY;
  let ticking = false;

  const updateHeader = () => {
    const currentScrollY = window.scrollY;
    const mobileNavOpen = document.getElementById('mobileNav')?.classList.contains('open');

    if (!mobileNavOpen && currentScrollY > lastScrollY && currentScrollY > 60) {
      siteHeader.classList.add('nav-hidden');
    } else {
      siteHeader.classList.remove('nav-hidden');
    }

    lastScrollY = currentScrollY;
    ticking = false;
  };

  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(updateHeader);
      ticking = true;
    }
  }, { passive: true });
}

// ---- Mobile nav toggle ----
const navToggle = document.getElementById('navToggle');
const mobileNav = document.getElementById('mobileNav');

if (navToggle && mobileNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = mobileNav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });

  mobileNav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      mobileNav.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// ---- Contact form ----
const contactForm = document.getElementById('contactForm');
const formNote = document.getElementById('formNote');
// Basic structural check (something@something.tld) — the form has
// novalidate set (so the "please fill this field" bubbles stay off), which
// also disables the browser's own type="email" format check, so this
// replaces it. Mirrored server-side in main.py's EMAIL_RE, since this check
// can be bypassed by anyone calling /contact directly.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

if (contactForm && formNote) {
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const message = document.getElementById('message').value.trim();
    // Honeypot — invisible to real visitors. If it's filled in, a bot did
    // it; we still send the request so the server can quietly no-op it.
    const company = document.getElementById('company').value.trim();

    if (!name || !email || !message) {
      formNote.textContent = 'Please fill in all fields.';
      formNote.classList.add('show');
      return;
    }

    if (!EMAIL_RE.test(email)) {
      formNote.textContent = 'Please enter a valid email address.';
      formNote.classList.add('show');
      return;
    }

    const submitBtn = contactForm.querySelector('.btn-submit');
    submitBtn.disabled = true;

    try {
      const res = await fetch('/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, message, company }),
      });
      const data = await res.json();

      if (res.ok && data.success) {
        const firstName = name.split(/\s+/)[0];
        formNote.textContent = `Thanks ${firstName} — your message has been sent. I'll get back to you soon.`;
        contactForm.reset();
      } else {
        formNote.textContent = data.error || 'Something went wrong. Please email me directly.';
      }
    } catch (err) {
      formNote.textContent = 'Something went wrong. Please email me directly.';
    } finally {
      formNote.classList.add('show');
      submitBtn.disabled = false;
    }
  });
}

// ---- Footer year ----
document.querySelectorAll('.footer-year').forEach((el) => {
  el.textContent = new Date().getFullYear();
});
