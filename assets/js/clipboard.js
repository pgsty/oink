/** Shared Clipboard API with a local legacy fallback. */
(function (global) {
  'use strict';

  function fallbackCopy(text, doc) {
    var previous = doc.activeElement;
    var fieldSelection = previous && typeof previous.selectionStart === 'number'
      ? [previous.selectionStart, previous.selectionEnd, previous.selectionDirection]
      : null;
    var selection = doc.getSelection ? doc.getSelection() : null;
    var ranges = [];
    if (selection) {
      for (var i = 0; i < selection.rangeCount; i += 1)
        ranges.push(selection.getRangeAt(i).cloneRange());
    }
    var backwardSelection = ranges.length === 1 && !ranges[0].collapsed &&
      selection.anchorNode === ranges[0].endContainer && selection.anchorOffset === ranges[0].endOffset;
    var textarea = doc.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.inset = '-9999px auto auto -9999px';
    // A modal makes the rest of the document inert. A field in the body can
    // report execCommand success while leaving the old clipboard untouched.
    var modal = previous && typeof previous.closest === 'function'
      ? previous.closest('dialog[open]') : null;
    (modal || doc.body).appendChild(textarea);
    var copied = false;
    try {
      textarea.select();
      if (textarea.setSelectionRange) textarea.setSelectionRange(0, text.length);
      copied = doc.execCommand('copy');
    } finally {
      var active = doc.activeElement;
      var restore = active === textarea || active === doc.body || active === doc.documentElement;
      textarea.remove();
      // A copy handler may deliberately focus another control. Restore only
      // focus that the temporary textarea took, never that newer focus.
      if (restore && previous && previous.isConnected && typeof previous.focus === 'function') {
        previous.focus({ preventScroll: true });
        if (fieldSelection && previous.setSelectionRange)
          previous.setSelectionRange.apply(previous, fieldSelection);
        else if (selection && ranges.length) {
          selection.removeAllRanges();
          ranges.forEach(function (range) { selection.addRange(range); });
          if (backwardSelection && selection.setBaseAndExtent)
            selection.setBaseAndExtent(ranges[0].endContainer, ranges[0].endOffset,
              ranges[0].startContainer, ranges[0].startOffset);
        }
      }
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
