// OINK FileTree runtime (docs/content-primitives.md §3.4).
//
// The ```filetree fence renders without JavaScript: folding is native
// <details> and the comment column is aligned at build time. This runtime only
// adds the draggable split between the name column and the comment column
// (`.td-filetree__divider`, role=separator): pointer drag or Left/Right/Home/End
// on the focused divider rewrites `--td-filetree-name-col` on the panel. The
// stylesheet clamps the split to [MIN, MAX] percent of the row width, so a
// stale or out-of-range value can never hide a column. Nothing is persisted.
(function (global) {
  'use strict';

  var MIN = 50;
  var MAX = 70;
  var STEP = 2;
  var READY = 'data-td-filetree-ready';

  function clampPercent(percent) {
    if (typeof percent !== 'number' || isNaN(percent)) return MIN;
    return Math.min(MAX, Math.max(MIN, percent));
  }

  // Row content width = body width minus the two gutters; the CSS variable is
  // written in pixels of that content box so the divider and the grid agree.
  function metrics(tree, body, win) {
    var rect = body.getBoundingClientRect();
    var style = win.getComputedStyle(tree);
    var gutter = parseFloat(style.getPropertyValue('--td-filetree-gutter')) || 0;
    if (gutter && /rem$/.test(style.getPropertyValue('--td-filetree-gutter'))) {
      gutter = gutter * (parseFloat(win.getComputedStyle(win.document.documentElement).fontSize) || 16);
    }
    return {
      left: rect.left,
      width: rect.width,
      gutter: gutter,
      inner: Math.max(1, rect.width - gutter * 2),
      rtl: style.direction === 'rtl',
    };
  }

  function percentFromPointer(clientX, m) {
    var offset = m.rtl ? m.left + m.width - clientX : clientX - m.left;
    return clampPercent(((offset - m.gutter) / m.inner) * 100);
  }

  function applyPercent(tree, divider, percent, m) {
    percent = clampPercent(percent);
    tree.style.setProperty('--td-filetree-name-col', ((percent / 100) * m.inner).toFixed(1) + 'px');
    divider.setAttribute('aria-valuenow', String(Math.round(percent)));
    tree.setAttribute('data-td-filetree-split', String(Math.round(percent)));
    return percent;
  }

  function currentPercent(tree, body, divider, win, m) {
    var rect = divider.getBoundingClientRect();
    var centre = rect.left + rect.width / 2;
    if (!rect.width) return Number(divider.getAttribute('aria-valuenow')) || MIN;
    return percentFromPointer(centre, m);
  }

  function enhance(tree, doc, win) {
    doc = doc || global.document;
    win = win || global;
    if (!tree || tree.hasAttribute(READY)) return null;
    var body = tree.querySelector('.td-filetree__body');
    var divider = tree.querySelector('[data-td-filetree-divider]');
    if (!body || !divider) return null;
    tree.setAttribute(READY, '');
    var m = metrics(tree, body, win);
    var percent = currentPercent(tree, body, divider, win, m);
    divider.setAttribute('aria-valuenow', String(Math.round(clampPercent(percent))));

    var dragging = false;
    divider.addEventListener('pointerdown', function (event) {
      if (event.button !== undefined && event.button !== 0) return;
      dragging = true;
      m = metrics(tree, body, win);
      tree.setAttribute('data-td-filetree-dragging', '');
      if (divider.setPointerCapture) {
        try { divider.setPointerCapture(event.pointerId); } catch (_) { /* ignore */ }
      }
      event.preventDefault();
    });
    divider.addEventListener('pointermove', function (event) {
      if (!dragging) return;
      percent = applyPercent(tree, divider, percentFromPointer(event.clientX, m), m);
    });
    var stop = function () {
      if (!dragging) return;
      dragging = false;
      tree.removeAttribute('data-td-filetree-dragging');
    };
    divider.addEventListener('pointerup', stop);
    divider.addEventListener('pointercancel', stop);
    divider.addEventListener('lostpointercapture', stop);
    divider.addEventListener('keydown', function (event) {
      var key = event.key;
      var next = null;
      m = metrics(tree, body, win);
      var current = clampPercent(Number(divider.getAttribute('aria-valuenow')) || percent);
      var towardsEnd = m.rtl ? 'ArrowLeft' : 'ArrowRight';
      var towardsStart = m.rtl ? 'ArrowRight' : 'ArrowLeft';
      if (key === towardsEnd) next = current + STEP;
      else if (key === towardsStart) next = current - STEP;
      else if (key === 'Home') next = MIN;
      else if (key === 'End') next = MAX;
      if (next === null) return;
      event.preventDefault();
      percent = applyPercent(tree, divider, next, m);
    });
    return { tree: tree, divider: divider };
  }

  function init(doc, win) {
    doc = doc || global.document;
    win = win || global;
    var enhanced = [];
    Array.prototype.forEach.call(doc.querySelectorAll('.td-filetree[data-td-filetree]'), function (tree) {
      var result = enhance(tree, doc, win);
      if (result) enhanced.push(result);
    });
    return enhanced;
  }

  var api = { init: init, enhance: enhance, clampPercent: clampPercent, percentFromPointer: percentFromPointer, MIN: MIN, MAX: MAX, STEP: STEP };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.OinkFileTree = api;

  if (global.document) {
    var start = function () { init(global.document, global); };
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', start, { once: true });
    } else {
      start();
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
