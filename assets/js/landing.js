/**
 * landing.js — small, data-attribute-driven runtime for landing surfaces.
 * The bundle is included only when a renderer sets Page.Store.hasLanding.
 */
(function (factory) {
  'use strict';
  var api = factory();
  if (typeof window !== 'undefined') window.OinkLanding = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(function () {
  'use strict';

  function reducedMotion(win) {
    return !!(win && win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function revealAll(elements) {
    elements.forEach(function (element) {
      element.classList.add('is-revealed');
      element.setAttribute('data-revealed', '');
    });
  }

  function initReveal(root, win) {
    var elements = Array.from(root.querySelectorAll('[data-reveal]'));
    if (!elements.length) return 0;
    if (reducedMotion(win) || !win || typeof win.IntersectionObserver !== 'function') {
      revealAll(elements);
      return elements.length;
    }
    var observer = new win.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        revealAll([entry.target]);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    elements.forEach(function (element) { observer.observe(element); });
    return elements.length;
  }

  function terminalCount(element) {
    var raw = element.getAttribute('data-count');
    var target = Number(raw);
    if (!Number.isFinite(target)) return false;
    var decimals = Number(element.getAttribute('data-count-decimals') || (String(raw).split('.')[1] || '').length);
    var prefix = element.getAttribute('data-count-prefix') || '';
    var suffix = element.getAttribute('data-count-suffix') || '';
    element.textContent = prefix + target.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }) + suffix;
    element.setAttribute('data-count-complete', '');
    return true;
  }

  function animateCount(element, win, duration) {
    var target = Number(element.getAttribute('data-count'));
    if (!Number.isFinite(target)) return false;
    var start = null;
    function frame(now) {
      if (start === null) start = now;
      var progress = Math.min((now - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var raw = element.getAttribute('data-count');
      var decimals = Number(element.getAttribute('data-count-decimals') || (String(raw).split('.')[1] || '').length);
      var prefix = element.getAttribute('data-count-prefix') || '';
      var suffix = element.getAttribute('data-count-suffix') || '';
      element.textContent = prefix + (target * eased).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }) + suffix;
      if (progress < 1) win.requestAnimationFrame(frame);
      else terminalCount(element);
    }
    win.requestAnimationFrame(frame);
    return true;
  }

  function initCounts(root, win) {
    var elements = Array.from(root.querySelectorAll('[data-count]'));
    if (!elements.length) return 0;
    if (reducedMotion(win) || !win || typeof win.IntersectionObserver !== 'function' || typeof win.requestAnimationFrame !== 'function') {
      elements.forEach(terminalCount);
      return elements.length;
    }
    var observer = new win.IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        animateCount(entry.target, win, Number(entry.target.getAttribute('data-count-duration')) || 1600);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.5 });
    elements.forEach(function (element) { observer.observe(element); });
    return elements.length;
  }

  function fallbackCopy(text, doc) {
    var textarea = doc.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    doc.body.appendChild(textarea);
    textarea.select();
    if (textarea.setSelectionRange) textarea.setSelectionRange(0, text.length);
    var copied = doc.execCommand('copy');
    textarea.remove();
    if (!copied) throw new Error('clipboard fallback was rejected');
  }

  function writeClipboard(text, doc, nav) {
    if (nav && nav.clipboard && typeof nav.clipboard.writeText === 'function') {
      try {
        return Promise.resolve(nav.clipboard.writeText(text)).catch(function () {
          fallbackCopy(text, doc);
        });
      } catch (_) {
        fallbackCopy(text, doc);
        return Promise.resolve();
      }
    }
    fallbackCopy(text, doc);
    return Promise.resolve();
  }

  function flashCopied(button, win) {
    var previous = button.getAttribute('aria-label') || button.getAttribute('title') || '';
    var copied = button.getAttribute('data-label-copied') || 'Copied';
    button.classList.add('is-copied');
    button.setAttribute('data-copy-state', 'success');
    button.setAttribute('aria-label', copied);
    var status = button.querySelector('[data-copy-status]');
    if (status) status.textContent = copied;
    win.setTimeout(function () {
      button.classList.remove('is-copied');
      button.removeAttribute('data-copy-state');
      if (previous) button.setAttribute('aria-label', previous);
      if (status) status.textContent = '';
    }, 1800);
  }

  function initCopy(root, win, doc, nav) {
    var buttons = Array.from(root.querySelectorAll('[data-copy-text]'));
    buttons.forEach(function (button) {
      if (button.hasAttribute('data-copy-ready')) return;
      button.setAttribute('data-copy-ready', '');
      button.addEventListener('click', function () {
        writeClipboard(button.getAttribute('data-copy-text') || '', doc, nav)
          .then(function () { flashCopied(button, win); })
          .catch(function () { button.setAttribute('data-copy-state', 'error'); });
      });
    });
    return buttons.length;
  }

  function resolvedTheme(doc) {
    return doc.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  }

  function syncThemeImages(root, doc) {
    var theme = resolvedTheme(doc);
    var images = Array.from(root.querySelectorAll('[data-theme-src-light][data-theme-src-dark]'));
    images.forEach(function (image) {
      var src = image.getAttribute(theme === 'dark' ? 'data-theme-src-dark' : 'data-theme-src-light');
      if (src && image.getAttribute('src') !== src) image.setAttribute('src', src);
    });
    return images.length;
  }

  function initThemeImages(root, win, doc) {
    var count = syncThemeImages(root, doc);
    if (!count) return 0;
    if (win && typeof win.MutationObserver === 'function') {
      var observer = new win.MutationObserver(function () { syncThemeImages(root, doc); });
      observer.observe(doc.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });
    }
    if (win && win.addEventListener) {
      win.addEventListener('oink-theme-change', function () { syncThemeImages(root, doc); });
    }
    return count;
  }

  function initMobileMenu(root, win, doc) {
    var toggle = root.querySelector('[data-td-landing-menu-toggle]');
    var menu = root.querySelector('[data-td-landing-menu]');
    if (!toggle || !menu) return false;
    function setOpen(open, restoreFocus) {
      menu.hidden = !open;
      menu.classList.toggle('is-open', open);
      toggle.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (!open && restoreFocus) toggle.focus();
    }
    var coordinator = win && win.OinkSurfaceCoordinator;
    if (coordinator && typeof coordinator.register === 'function') {
      coordinator.register('mobile-menu', function (restoreFocus) { setOpen(false, restoreFocus); });
    }
    toggle.addEventListener('click', function () {
      var open = menu.hidden;
      if (open && coordinator && typeof coordinator.closeOthers === 'function') coordinator.closeOthers('mobile-menu');
      setOpen(open, false);
    });
    Array.from(menu.querySelectorAll('a, [data-td-landing-menu-dismiss]')).forEach(function (item) {
      item.addEventListener('click', function () { setOpen(false, false); });
    });
    doc.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !menu.hidden) setOpen(false, true);
    });
    return true;
  }

  function init(root, win, doc, nav) {
    root = root || doc;
    return {
      reveal: initReveal(root, win),
      count: initCounts(root, win),
      copy: initCopy(root, win, doc, nav),
      themeImages: initThemeImages(root, win, doc),
      mobileMenu: initMobileMenu(root, win, doc),
    };
  }

  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    var boot = function () { init(document, window, document, window.navigator); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
  }

  return {
    reducedMotion: reducedMotion,
    terminalCount: terminalCount,
    initReveal: initReveal,
    initCounts: initCounts,
    writeClipboard: writeClipboard,
    flashCopied: flashCopied,
    initCopy: initCopy,
    syncThemeImages: syncThemeImages,
    initThemeImages: initThemeImages,
    initMobileMenu: initMobileMenu,
    init: init,
  };
});
