/**
 * surface-coordinator.js — coordinate mutually exclusive transient UI.
 *
 * A surface registers a close callback and may request that the coordinator
 * close every other registered surface before it opens. The callbacks own
 * their own focus-restoration policy; coordinated closes deliberately do not
 * steal focus from the surface being opened.
 */
(function () {
  'use strict';

  var surfaces = new Map();

  function register(name, close) {
    if (!name || typeof close !== 'function') return function () {};
    var callbacks = surfaces.get(name) || [];
    callbacks.push(close);
    surfaces.set(name, callbacks);
    return function () {
      var current = surfaces.get(name) || [];
      current = current.filter(function (callback) {
        return callback !== close;
      });
      if (current.length) {
        surfaces.set(name, current);
      } else {
        surfaces.delete(name);
      }
    };
  }

  function closeOthers(activeName, keepNames) {
    var keep = new Set(keepNames || []);
    surfaces.forEach(function (callbacks, name) {
      if (name !== activeName && !keep.has(name))
        callbacks.slice().forEach(function (close) {
          close(false);
        });
    });
  }

  function closeAll(restoreFocus) {
    surfaces.forEach(function (callbacks) {
      callbacks.slice().forEach(function (close) {
        close(restoreFocus === true);
      });
    });
  }

  // Return focus to the element a closing surface came from without opening
  // the hover menu around it. base.js opens a [data-td-nav-hover] menu on
  // focusin and on the pointerenter some engines dispatch when an overlay
  // disappears under a resting pointer; focus put back by script must do
  // neither, or closing the palette over the footer "?" button would raise
  // the full shortcut sheet in its place.
  function restoreFocus(target, options) {
    if (!target || typeof target.focus !== 'function') return;
    var host = typeof target.closest === 'function' ? target.closest('[data-td-nav-hover]') : null;
    if (host) {
      host.setAttribute('data-td-suppress-focus-open', '');
      host.setAttribute('data-td-suppress-hover-open', '');
    }
    try {
      target.focus(options);
    } finally {
      if (host) {
        host.removeAttribute('data-td-suppress-focus-open');
        var clearHover = function () { host.removeAttribute('data-td-suppress-hover-open'); };
        if (typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(function () {
            window.requestAnimationFrame(function () { window.setTimeout(clearHover, 60); });
          });
        } else {
          window.setTimeout(clearHover, 100);
        }
      }
    }
  }

  window.OinkSurfaceCoordinator = {
    register: register,
    closeOthers: closeOthers,
    closeAll: closeAll,
    restoreFocus: restoreFocus,
  };
})();
