// Initialize every Swagger UI container on the page. Loaded only when a page
// renders the swagger shortcode, after the vendored bundle and preset.
// validatorUrl stays null: the bundle's default would silently send every
// non-localhost spec URL to the online validator at validator.swagger.io.
(function (global) {
  'use strict';

  var initialized = new WeakSet();

  function init(doc, bundle, preset) {
    if (typeof bundle !== 'function' || !doc || !doc.querySelectorAll) return [];
    var nodes = doc.querySelectorAll('[data-td-swagger]');
    var mounted = [];
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      var url = node.getAttribute('data-td-spec-url');
      if (!url || initialized.has(node)) continue;
      initialized.add(node);
      var presets = [bundle.presets.apis];
      if (typeof preset !== 'undefined') presets.push(preset);
      mounted.push(bundle({
        url: url,
        domNode: node,
        validatorUrl: null,
        presets: presets,
      }));
    }
    return mounted;
  }

  function boot() {
    init(
      global.document,
      global.SwaggerUIBundle,
      global.SwaggerUIStandalonePreset,
    );
  }

  var api = { init: init };
  global.OinkSwaggerInit = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (global.document) {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
      boot();
    }
  }
})(typeof window === 'object' ? window : globalThis);
