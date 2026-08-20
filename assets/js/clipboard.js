/** Shared Clipboard API with a local legacy fallback. */
(function (global) {
  'use strict';

  function fallbackCopy(text, doc) {
    var textarea = doc.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.inset = '-9999px auto auto -9999px';
    doc.body.appendChild(textarea);
    textarea.select();
    if (textarea.setSelectionRange) textarea.setSelectionRange(0, text.length);
    var copied = false;
    try {
      copied = doc.execCommand('copy');
    } finally {
      textarea.remove();
    }
    if (!copied) throw new Error('clipboard fallback was rejected');
  }

  function writeText(text, doc, nav) {
    doc = doc || global.document;
    nav = nav || global.navigator;
    var clipboard = nav && nav.clipboard;
    if (clipboard && typeof clipboard.writeText === 'function') {
      return Promise.resolve()
        .then(function () { return clipboard.writeText(text); })
        .catch(function () {
          fallbackCopy(text, doc);
        });
    }
    return Promise.resolve().then(function () {
        fallbackCopy(text, doc);
    });
  }

  var api = { writeText: writeText };
  global.OinkClipboard = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
