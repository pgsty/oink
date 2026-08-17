/**
 * Fat-footer collapse: the arrow at the right edge of the copyright line
 * hides or restores the column grid above it. The choice persists across
 * pages in localStorage. Bundled only when the page renders a fat footer.
 */
(function (global) {
  'use strict';

  var KEY = 'td-footer-collapsed';

  function init(options) {
    options = options || {};
    var doc = options.document || (global.document ? global.document : null);
    if (!doc) return null;
    var storage = options.storage || (function () {
      try {
        return global.localStorage;
      } catch (_) {
        return null;
      }
    })();
    var toggle = doc.querySelector('[data-td-footer-toggle]');
    var target = doc.getElementById('td-site-footer');
    if (!toggle || !target) return null;

    function apply(collapsed, persist) {
      target.hidden = collapsed;
      toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      if (toggle.classList) toggle.classList.toggle('td-is-collapsed', collapsed);
      var label = collapsed
        ? toggle.dataset.labelExpand
        : toggle.dataset.labelCollapse;
      if (label) {
        toggle.setAttribute('aria-label', label);
        toggle.setAttribute('title', label);
      }
      if (!persist || !storage) return;
      try {
        if (collapsed) storage.setItem(KEY, '1');
        else storage.removeItem(KEY);
      } catch (_) {
        /* storage may be unavailable */
      }
    }

    try {
      if (storage && storage.getItem(KEY)) apply(true, false);
    } catch (_) {
      /* storage may be unavailable */
    }
    toggle.addEventListener('click', function () {
      apply(!target.hidden, true);
    });

    return Object.freeze({ apply: apply });
  }

  var api = { init: init };
  global.OinkFooterCollapse = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (!global.__OINK_FOOTER_COLLAPSE_MANUAL_INIT__ && global.document) init();
})(typeof window === 'object' ? window : globalThis);
