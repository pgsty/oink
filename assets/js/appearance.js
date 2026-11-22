/**
 * appearance.js -- the reader's visual preset and the Appearance menu.
 *
 * Two independent dimensions share one menu. Style (the visual preset) lives
 * on <html data-td-preset> and in localStorage['td-preset']; this file owns
 * it. Mode (light / dark / system) lives on data-bs-theme and in
 * localStorage['td-color-theme']; dark-mode.js owns it and binds the Light
 * radios. Neither writes the other's key.
 *
 * The server renders the site default on data-td-preset and keeps it on
 * data-td-site-preset. The inline head script has already applied a valid
 * stored choice before first paint; this file handles later changes: radio
 * input, other tabs (the storage event), and restoring
 * the default (choosing the site's default preset removes the stored key so a later
 * change of the site default reaches the reader).
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var KEY = 'td-preset';
  var NARROW = '(max-width: 767.98px)';

  function sitePreset() {
    return root.getAttribute('data-td-site-preset') || root.getAttribute('data-td-preset') || '';
  }

  function presetInputs() {
    return Array.prototype.slice.call(document.querySelectorAll('[data-td-preset-value]'));
  }

  // The presets this page offers, read from the rendered menu (or the action
  // manifest when chrome menus are suppressed), so the runtime never accepts a
  // name the site did not build a choice for.
  function offered() {
    var names = [];
    presetInputs().forEach(function (input) {
      var name = input.getAttribute('data-td-preset-value');
      if (name && names.indexOf(name) < 0) names.push(name);
    });
    if (!names.length && window.OinkActions && typeof window.OinkActions.get === 'function') {
      var action = window.OinkActions.get('switch_preset');
      if (action && Array.isArray(action.options)) {
        action.options.forEach(function (opt) {
          var name = opt && (opt.value || opt.id);
          if (name && names.indexOf(name) < 0) names.push(name);
        });
      }
    }
    return names;
  }

  function readStored() {
    try {
      return window.localStorage.getItem(KEY);
    } catch (_) {
      return null;
    }
  }

  // Returns false when the browser refuses storage; the choice then applies
  // to this page only and the menu says so.
  function remember(name) {
    try {
      if (name === sitePreset()) {
        window.localStorage.removeItem(KEY);
      } else {
        window.localStorage.setItem(KEY, name);
      }
      return true;
    } catch (_) {
      return false;
    }
  }

  function showStorageNote(show) {
    root.toggleAttribute('data-td-preset-unsaved', show);
    document.querySelectorAll('[data-td-appearance-note]').forEach(function (note) {
      note.hidden = !show && !root.hasAttribute('data-td-mode-unsaved');
    });
  }

  function syncInputs() {
    var current = root.getAttribute('data-td-preset');
    presetInputs().forEach(function (input) {
      input.checked = input.getAttribute('data-td-preset-value') === current;
    });
  }

  function updateThemeColor(name) {
    var source = presetInputs().filter(function (input) {
      return input.getAttribute('data-td-preset-value') === name;
    })[0];
    if (!source) return;
    var light = source.getAttribute('data-td-canvas-light');
    var dark = source.getAttribute('data-td-canvas-dark');
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
      meta.setAttribute('data-td-canvas-light', light);
      meta.setAttribute('data-td-canvas-dark', dark);
      var value = root.getAttribute('data-bs-theme') === 'dark' ? dark : light;
      if (value) meta.setAttribute('content', value);
    });
  }

  // The first block still visible at the top of the viewport. Paper's Plex
  // Sans and Slate's Inter set text to different lengths, so without an
  // anchor a switch would silently move the reader to another paragraph.
  function readingAnchor() {
    if (!window.scrollY) return null;
    var scope = document.getElementById('td-main-content') || document.body;
    if (!scope || !scope.querySelectorAll) return null;
    var blocks = scope.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, pre, table, figure, blockquote, dt, dd');
    for (var i = 0; i < blocks.length; i += 1) {
      var rect = blocks[i].getBoundingClientRect();
      if (rect.bottom > 0 && rect.height > 0) return { element: blocks[i], top: rect.top };
    }
    return null;
  }

  function restoreAnchor(anchor) {
    if (!anchor || !anchor.element.isConnected) return;
    var delta = anchor.element.getBoundingClientRect().top - anchor.top;
    // This is layout correction, not reader navigation. CSS smooth scrolling
    // would postpone it and invalidate the font-ready correction below.
    if (Math.abs(delta) >= 1) window.scrollBy({ top: delta, left: 0, behavior: 'instant' });
  }

  function nextFrame(callback) {
    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(callback);
    } else {
      window.setTimeout(callback, 16);
    }
  }

  /**
   * Apply a preset. `store` records the reader's choice; a storage-event or
   * initial sync passes false. Unknown names fall back to the site default.
   */
  function applyPreset(name, store) {
    var names = offered();
    if (!names.length) return null;
    if (names.indexOf(name) < 0) {
      name = sitePreset();
      try { window.localStorage.removeItem(KEY); } catch (_) {}
    }
    if (store) showStorageNote(!remember(name));

    var previous = root.getAttribute('data-td-preset');
    if (previous === name) {
      syncInputs();
      return name;
    }

    var anchor = readingAnchor();
    // One frame without color transitions: the switch lands at once.
    root.setAttribute('data-td-preset-switching', '');
    root.setAttribute('data-td-preset', name);
    syncInputs();
    updateThemeColor(name);
    restoreAnchor(anchor);
    var settled = window.scrollY;
    nextFrame(function () {
      nextFrame(function () {
        root.removeAttribute('data-td-preset-switching');
      });
    });
    // Web fonts for the new preset may still be arriving; once they are in,
    // correct the anchor again unless the reader has scrolled meanwhile.
    if (anchor && document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        if (root.getAttribute('data-td-preset') === name && window.scrollY === settled) restoreAnchor(anchor);
      });
    }

    try {
      window.dispatchEvent(new CustomEvent('td-preset-change', {
        detail: { preset: name, previous: previous, stored: !!store },
      }));
    } catch (_) {
      // The attribute remains the source of truth.
    }
    return name;
  }

  var presetActionRegistered = false;

  function registerPresetAction() {
    if (presetActionRegistered) return;
    if (window.OinkActions && window.OinkActions.get('switch_preset')) {
      presetActionRegistered = true;
      window.OinkActions.registerExecutor('switch_preset', function (context) {
        var value = context && context.value;
        var name = typeof value === 'string' ? value : value && value.value;
        if (offered().indexOf(name) < 0) return Promise.reject(new Error('Unsupported preset'));
        return { preset: applyPreset(name, true) };
      });
    }
  }

  function initPresets() {
    registerPresetAction();
    if (!offered().length) return;
    syncInputs();
    presetInputs().forEach(function (input) {
      input.addEventListener('change', function () {
        if (input.checked) applyPreset(input.getAttribute('data-td-preset-value'), true);
      });
    });
    // Another tab chose or cleared a preset.
    window.addEventListener('storage', function (event) {
      if (event.key !== KEY && event.key !== null) return;
      applyPreset(readStored() || sitePreset(), false);
    });
  }

  // ---- The menu -------------------------------------------------------------

  function initMenu(wrapper, index) {
    var trigger = wrapper.querySelector('[data-td-appearance-trigger]');
    var panel = wrapper.querySelector('dialog');
    if (!trigger || !panel || typeof panel.show !== 'function') return;
    var surface = 'appearance-' + index;
    var coordinator = window.OinkSurfaceCoordinator;

    function asSheet() {
      return wrapper.hasAttribute('data-td-appearance-modal')
        || (typeof window.matchMedia === 'function' && window.matchMedia(NARROW).matches);
    }

    function open() {
      if (panel.open) return;
      if (coordinator) {
        var keep = [];
        if (wrapper.closest('#td-shell-sidebar')) keep.push('drawer');
        if (wrapper.closest('[data-td-landing-menu]')) keep.push('mobile-menu');
        coordinator.closeOthers(surface, keep);
      }
      if (asSheet()) {
        panel.showModal();
      } else {
        panel.show();
      }
      wrapper.classList.add('td-is-open');
      trigger.setAttribute('aria-expanded', 'true');
      var target = panel.querySelector('input:checked') || panel.querySelector('input');
      if (target) target.focus();
    }

    function close(restoreFocus) {
      if (!panel.open) return;
      panel.close();
      if (restoreFocus) trigger.focus();
    }

    panel.addEventListener('close', function () {
      // A previous close event may arrive after the reader reopens the dialog.
      if (panel.open) return;
      wrapper.classList.remove('td-is-open');
      trigger.setAttribute('aria-expanded', 'false');
    });
    panel.addEventListener('cancel', function (event) {
      event.preventDefault();
      close(true);
    });

    trigger.addEventListener('click', function () {
      if (panel.open) {
        close(false);
      } else {
        open();
      }
    });
    trigger.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown' && !panel.open) {
        event.preventDefault();
        open();
      }
    });

    // Escape closes this panel only: a drawer underneath stays open.
    panel.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      close(true);
    });

    var closeButton = panel.querySelector('[data-td-appearance-close]');
    if (closeButton) closeButton.addEventListener('click', function () { close(true); });

    // A modal sheet receives backdrop clicks on the dialog element itself.
    panel.addEventListener('click', function (event) {
      if (event.target !== panel) return;
      var rect = panel.getBoundingClientRect();
      var inside = event.clientX >= rect.left && event.clientX <= rect.right
        && event.clientY >= rect.top && event.clientY <= rect.bottom;
      if (!inside) close(true);
    });

    // The anchored popover closes on an outside press or when focus leaves.
    document.addEventListener('pointerdown', function (event) {
      if (panel.open && !wrapper.contains(event.target)) close(false);
    }, true);
    wrapper.addEventListener('focusout', function (event) {
      if (panel.open && event.relatedTarget && !wrapper.contains(event.relatedTarget)) close(false);
    });

    // Reopen in the correct presentation after a breakpoint change; a
    // desktop non-modal panel must not remain anchored offscreen on a phone.
    if (typeof window.matchMedia === 'function') {
      window.matchMedia(NARROW).addEventListener('change', function () {
        if (panel.open) close(true);
      });
    }

    if (coordinator) coordinator.register(surface, function (restoreFocus) { close(restoreFocus === true); });
  }

  function init() {
    initPresets();
    document.querySelectorAll('[data-td-appearance]').forEach(initMenu);
  }

  registerPresetAction();
  window.OinkAppearance = { applyPreset: applyPreset, offered: offered };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
