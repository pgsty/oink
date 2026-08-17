/** OINK release asset checksum copy controls. */
(function (global) {
  'use strict';

  var resetTimers = typeof WeakMap === 'function' ? new WeakMap() : null;

  function checksumLine(row) {
    if (!row) return '';
    var hash = row.getAttribute('data-td-asset-hash') || '';
    var name = row.getAttribute('data-td-asset-name') || '';
    var separator = row.hasAttribute('data-td-asset-binary') ? ' *' : '  ';
    return hash && name ? hash + separator + name : '';
  }

  function allChecksumLines(root) {
    if (!root) return '';
    var lines = Array.prototype.map
      .call(root.querySelectorAll('[data-td-asset]'), checksumLine)
      .filter(Boolean);
    return lines.length ? lines.join('\n') + '\n' : '';
  }

  function fallbackCopy(text, doc) {
    var textarea = doc.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.inset = '-9999px auto auto -9999px';
    doc.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    var copied = false;
    try {
      copied = doc.execCommand('copy');
    } finally {
      textarea.remove();
    }
    if (!copied) throw new Error('clipboard fallback was rejected');
  }

  function writeClipboard(text, doc) {
    var clipboard = global.navigator && global.navigator.clipboard;
    if (clipboard && typeof clipboard.writeText === 'function') {
      try {
        return Promise.resolve(clipboard.writeText(text)).catch(function () {
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

  function setControl(button, state, label) {
    button.setAttribute('data-td-state', state);
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
    var labelNode = button.querySelector('span');
    if (labelNode) labelNode.textContent = label;
    var icon = button.querySelector('i');
    if (icon) {
      icon.className = state === 'success'
        ? 'fa-solid fa-check'
        : state === 'error'
          ? 'fa-solid fa-triangle-exclamation'
          : 'fa-regular fa-copy';
    }
  }

  function resetControl(button) {
    var label = button.getAttribute('data-td-label-copy') || 'Copy';
    setControl(button, 'idle', label);
    button.disabled = false;
  }

  function scheduleReset(button) {
    if (resetTimers) {
      var previous = resetTimers.get(button);
      if (previous) global.clearTimeout(previous);
    }
    var timer = global.setTimeout(function () { resetControl(button); }, 1500);
    if (resetTimers) resetTimers.set(button, timer);
  }

  function copyFromControl(button, doc) {
    if (!button || button.disabled) return Promise.resolve(false);
    var root = button.closest('[data-td-asset-list]');
    if (!root) return Promise.resolve(false);
    var row = button.closest('[data-td-asset]');
    var text = button.hasAttribute('data-td-asset-copy-all')
      ? allChecksumLines(root)
      : checksumLine(row);
    if (!text) return Promise.resolve(false);
    if (!button.hasAttribute('data-td-asset-copy-all')) text += '\n';

    var status = root.querySelector('[data-td-asset-status]');
    button.disabled = true;
    if (status) status.textContent = '';
    return writeClipboard(text, doc).then(function () {
      var label = button.getAttribute('data-td-label-copied') || 'Copied';
      setControl(button, 'success', label);
      if (status) status.textContent = label;
      scheduleReset(button);
      return true;
    }).catch(function (error) {
      var label = button.getAttribute('data-td-label-copy') || 'Copy';
      setControl(button, 'error', label);
      if (status) status.textContent = label;
      button.disabled = false;
      if (global.console && typeof global.console.error === 'function') {
        global.console.error('OINK asset list: unable to copy checksums:', error);
      }
      return false;
    });
  }

  function init(scope) {
    var doc = (scope && scope.ownerDocument) || global.document;
    var target = scope || doc;
    if (!target || typeof target.querySelectorAll !== 'function') return 0;
    var initialized = 0;
    Array.prototype.forEach.call(
      target.querySelectorAll('[data-td-asset-list]'),
      function (root) {
        if (root.hasAttribute('data-td-asset-list-ready')) return;
        root.setAttribute('data-td-asset-list-ready', '');
        Array.prototype.forEach.call(
          root.querySelectorAll('[data-td-asset-copy], [data-td-asset-copy-all]'),
          function (button) { button.hidden = false; },
        );
        root.addEventListener('click', function (event) {
          var button = event.target.closest(
            '[data-td-asset-copy], [data-td-asset-copy-all]',
          );
          if (button && root.contains(button)) copyFromControl(button, doc);
        });
        initialized += 1;
      },
    );
    return initialized;
  }

  var api = {
    allChecksumLines: allChecksumLines,
    checksumLine: checksumLine,
    copyFromControl: copyFromControl,
    init: init,
    writeClipboard: writeClipboard,
  };
  global.OinkAssetList = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (!global.__OINK_ASSET_LIST_MANUAL_INIT__ && global.document) {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', function () { init(); }, { once: true });
    } else {
      init();
    }
  }
})(typeof window === 'object' ? window : globalThis);
