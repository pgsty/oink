/**
 * Browsing history: the pages this reader opened on this site, newest first,
 * kept only in this browser's localStorage and never sent anywhere. The list
 * is keyed by the site's base path, so two sites sharing one origin (project
 * pages under one host) keep separate histories. H
 * (keyboard-nav.js) or the Command Palette's "Browsing history" row opens a
 * filterable overlay that reuses the Command Palette surface. Arrow keys move,
 * Enter opens (Ctrl/Cmd+Enter in a new tab), Shift+Delete forgets one page,
 * and the footer button clears everything. Bundled with keyboard-nav.js.
 */
(function (global) {
  'use strict';
  if (typeof window !== 'undefined' && window.OinkComparePane) return;

  var PREFIX = 'td-history:';
  var LIMIT = 100;
  var FOCUSABLE = 'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function localStore(win) {
    try {
      return win.localStorage || null;
    } catch (_) {
      return null;
    }
  }

  // The site's base path ("/" or "/project/"), from the overlay markup.
  function scopeOf(doc) {
    var root = doc.getElementById && doc.getElementById('td-shell-history');
    var scope = root && root.getAttribute('data-td-history-scope');
    return typeof scope === 'string' && scope.charAt(0) === '/' && scope.slice(-1) === '/'
      ? scope
      : '/';
  }

  function keyOf(scope) {
    return PREFIX + scope;
  }

  // Only a path inside this site survives. Anything else in the stored list
  // (another site's path, a protocol-relative URL, a backslash) is dropped
  // rather than repaired, so a tampered entry can never become a link.
  function sanitize(entry, scope) {
    if (!entry || typeof entry !== 'object') return null;
    var url = typeof entry.url === 'string' ? entry.url : '';
    if (url.charAt(0) !== '/' || url.charAt(1) === '/' || url.indexOf('\\') >= 0 ||
        /[\u0000-\u001f]/.test(url) || url.length > 2048) return null;
    if (scope && url.indexOf(scope) !== 0 && url + '/' !== scope) return null;
    var title = typeof entry.title === 'string' ? entry.title.replace(/\s+/g, ' ').trim().slice(0, 300) : '';
    var time = Number(entry.time);
    if (!isFinite(time) || time <= 0) return null;
    return { url: url, title: title, time: time };
  }

  function read(win, scope) {
    var store = localStore(win);
    if (!store) return [];
    try {
      var parsed = JSON.parse(store.getItem(keyOf(scope)) || '[]');
      if (!Array.isArray(parsed)) return [];
      var seen = Object.create(null);
      return parsed.map(function (entry) { return sanitize(entry, scope); }).filter(function (entry) {
        if (!entry || seen[entry.url]) return false;
        seen[entry.url] = true;
        return true;
      }).slice(0, LIMIT);
    } catch (_) {
      return [];
    }
  }

  function write(win, scope, entries) {
    var store = localStore(win);
    if (!store) return false;
    try {
      if (entries.length) store.setItem(keyOf(scope), JSON.stringify(entries.slice(0, LIMIT)));
      else store.removeItem(keyOf(scope));
      return true;
    } catch (_) {
      return false;
    }
  }

  function currentPath(win) {
    return win.location.pathname + (win.location.search || '');
  }

  function pageTitle(doc) {
    var meta = doc.querySelector && doc.querySelector('meta[property="og:title"]');
    var title = (meta && meta.getAttribute('content')) || doc.title || '';
    return String(title).replace(/\s+/g, ' ').trim();
  }

  // The visit lands at the top; an earlier visit of the same address moves
  // up instead of repeating. The fragment is not part of the page identity.
  function record(doc, win, now) {
    if (doc.body && doc.body.classList && doc.body.classList.contains('td-404')) return false;
    var scope = scopeOf(doc);
    var entry = sanitize({ url: currentPath(win), title: pageTitle(doc), time: now() }, scope);
    if (!entry) return false;
    var entries = read(win, scope).filter(function (item) { return item.url !== entry.url; });
    entries.unshift(entry);
    return write(win, scope, entries);
  }

  function normalize(value) {
    var text = String(value || '').toLowerCase();
    return text.normalize ? text.normalize('NFKC') : text;
  }

  function displayPath(url) {
    try {
      return decodeURI(url);
    } catch (_) {
      return url;
    }
  }

  function init(options) {
    options = options || {};
    var doc = options.document || (global.document ? global.document : null);
    if (!doc) return null;
    var win = options.window || global;
    var html = doc.documentElement;
    var now = options.now || function () { return Date.now(); };
    var scope = scopeOf(doc);
    record(doc, win, now);

    var root = doc.getElementById('td-shell-history');
    var input = root && root.querySelector('.td-shell-search__input');
    var list = root && root.querySelector('.td-shell-search__list');
    var panel = root && root.querySelector('.td-shell-search__panel');
    var status = root && root.querySelector('[data-td-history-status]');
    var clearButton = root && root.querySelector('[data-td-history-clear]');
    var empty = root && root.querySelector('[data-td-history-empty]');
    if (!root || !input || !list || !panel) {
      return Object.freeze({
        entries: function () { return read(win, scope); },
        isOpen: function () { return false; },
        open: function () { return false; },
        close: function () {},
      });
    }

    var rows = [];
    var selected = 0;
    var openState = false;
    var returnFocus = null;
    var hideTimer = 0;

    function label(name, fallback) {
      return root.getAttribute('data-td-t-' + name) || fallback;
    }

    function announce(text) {
      if (!status) return;
      status.textContent = '';
      win.requestAnimationFrame(function () { status.textContent = text; });
    }

    function relativeTime(time) {
      var lang = html.getAttribute('lang') || undefined;
      var seconds = (time - now()) / 1000;
      var size = Math.abs(seconds);
      try {
        var format = new Intl.RelativeTimeFormat(lang, { numeric: 'auto' });
        if (size < 60) return format.format(0, 'second');
        if (size < 3600) return format.format(Math.round(seconds / 60), 'minute');
        if (size < 86400) return format.format(Math.round(seconds / 3600), 'hour');
        if (size < 7 * 86400) return format.format(Math.round(seconds / 86400), 'day');
      } catch (_) {
        /* an unknown language tag falls through to the plain date */
      }
      try {
        return new Date(time).toLocaleDateString(lang, { year: 'numeric', month: 'short', day: 'numeric' });
      } catch (_) {
        return '';
      }
    }

    function highlight(text, needles) {
      var fragment = doc.createDocumentFragment();
      var lower = String(text).toLowerCase();
      var ranges = [];
      if (lower.length === text.length) {
        needles.forEach(function (needle) {
          for (var at = lower.indexOf(needle); needle && at >= 0; at = lower.indexOf(needle, at + needle.length))
            ranges.push([at, at + needle.length]);
        });
      }
      ranges.sort(function (a, b) { return a[0] - b[0]; });
      var cursor = 0;
      ranges.forEach(function (range) {
        if (range[1] <= cursor) return;
        var start = Math.max(range[0], cursor);
        fragment.appendChild(doc.createTextNode(text.slice(cursor, start)));
        var mark = doc.createElement('mark');
        mark.textContent = text.slice(start, range[1]);
        fragment.appendChild(mark);
        cursor = range[1];
      });
      fragment.appendChild(doc.createTextNode(text.slice(cursor)));
      return fragment;
    }

    function select(index) {
      var options = Array.prototype.slice.call(list.querySelectorAll('[role="option"]'));
      if (!options.length) {
        input.removeAttribute('aria-activedescendant');
        return;
      }
      selected = Math.max(0, Math.min(index, options.length - 1));
      options.forEach(function (option, n) {
        option.setAttribute('aria-selected', n === selected ? 'true' : 'false');
      });
      input.setAttribute('aria-activedescendant', options[selected].id);
      if (options[selected].scrollIntoView) options[selected].scrollIntoView({ block: 'nearest' });
    }

    // The listbox holds options only; an empty state is its sibling.
    function message(text) {
      if (empty) {
        empty.textContent = text;
        empty.hidden = false;
      }
      announce(text);
    }

    // The page being read is history already; listing it would make the
    // first row useless. Without it, H then Enter returns to the last page.
    function render(keepIndex) {
      var needles = normalize(input.value).split(/\s+/).filter(Boolean);
      var here = currentPath(win);
      var entries = read(win, scope).filter(function (entry) { return entry.url !== here; });
      rows = needles.length
        ? entries.filter(function (entry) {
          var haystack = normalize(entry.title + ' ' + displayPath(entry.url));
          return needles.every(function (needle) { return haystack.indexOf(needle) >= 0; });
        })
        : entries;
      list.textContent = '';
      if (empty) empty.hidden = true;
      input.removeAttribute('aria-activedescendant');
      if (clearButton) clearButton.disabled = read(win, scope).length === 0;
      if (!rows.length) {
        message(entries.length ? label('no-results', 'No results') : label('empty', 'No browsing history yet'));
        return;
      }
      rows.forEach(function (entry, index) {
        var row = doc.createElement('div');
        row.className = 'td-shell-search__item';
        row.id = 'td-shell-history-option-' + index;
        row.setAttribute('role', 'option');
        row.setAttribute('aria-selected', 'false');
        row.setAttribute('tabindex', '-1');
        var icon = doc.createElement('i');
        icon.className = 'td-shell-search__item-icon fa-solid fa-clock-rotate-left';
        icon.setAttribute('aria-hidden', 'true');
        row.appendChild(icon);
        var meta = doc.createElement('div');
        meta.className = 'td-shell-search__item-meta';
        var title = doc.createElement('div');
        title.className = 'td-shell-search__item-title';
        title.appendChild(highlight(entry.title || displayPath(entry.url), needles));
        meta.appendChild(title);
        var detail = doc.createElement('div');
        detail.className = 'td-shell-search__item-ref';
        var when = relativeTime(entry.time);
        detail.appendChild(highlight(displayPath(entry.url), needles));
        if (when) detail.appendChild(doc.createTextNode(' · ' + when));
        meta.appendChild(detail);
        row.appendChild(meta);
        row.addEventListener('pointermove', function (event) {
          if ((!event.pointerType || event.pointerType === 'mouse') && selected !== index) select(index);
        });
        row.addEventListener('click', function (event) {
          activate(index, Boolean(event.metaKey || event.ctrlKey));
        });
        list.appendChild(row);
      });
      select(keepIndex || 0);
      announce(label('results', '{count} results').replace('{count}', String(rows.length)));
    }

    function activate(index, newTab) {
      var entry = rows[index];
      if (!entry) return;
      var target;
      try {
        target = new URL(entry.url, win.location.href);
      } catch (_) {
        return;
      }
      if (target.origin !== win.location.origin) return;
      if (newTab) {
        win.open(target.href, '_blank', 'noopener');
        return;
      }
      close(false);
      win.location.assign(target.href);
    }

    function remove(index) {
      var entry = rows[index];
      if (!entry) return;
      write(win, scope, read(win, scope).filter(function (item) { return item.url !== entry.url; }));
      render(index);
      announce(label('removed', 'Removed from history'));
    }

    function clear() {
      write(win, scope, []);
      render();
      announce(label('cleared', 'Browsing history cleared'));
      try {
        input.focus({ preventScroll: true });
      } catch (_) {
        input.focus();
      }
    }

    function isOpen() {
      return openState;
    }

    function open(event) {
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      if (openState) {
        input.focus();
        return true;
      }
      // Close the palette, menus and the shortcut help first: their close
      // callbacks release the shared lock before this surface claims it.
      var coordinator = options.coordinator || win.OinkSurfaceCoordinator;
      if (coordinator && typeof coordinator.closeOthers === 'function') coordinator.closeOthers('history');
      var active = doc.activeElement;
      returnFocus = active && active !== doc.body && active !== html && !root.contains(active) &&
        typeof active.focus === 'function'
        ? active
        : null;
      openState = true;
      win.clearTimeout(hideTimer);
      root.hidden = false;
      html.setAttribute('data-td-shell-lock', '');
      input.setAttribute('aria-expanded', 'true');
      input.value = '';
      render();
      win.requestAnimationFrame(function () {
        if (openState) root.classList.add('td-is-open');
      });
      try {
        input.focus({ preventScroll: true });
      } catch (_) {
        input.focus();
      }
      return true;
    }

    function close(restoreFocus) {
      if (!openState) return;
      openState = false;
      root.classList.remove('td-is-open');
      html.removeAttribute('data-td-shell-lock');
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      var reduced = win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches;
      hideTimer = win.setTimeout(function () {
        if (!openState) root.hidden = true;
      }, reduced ? 0 : 240);
      var active = doc.activeElement;
      var target = returnFocus;
      returnFocus = null;
      if (
        restoreFocus !== false && target && doc.contains(target) &&
        (!active || active === doc.body || root.contains(active))
      ) {
        try {
          target.focus({ preventScroll: true });
        } catch (_) {
          target.focus();
        }
      }
    }

    function focusable() {
      return Array.prototype.filter.call(panel.querySelectorAll(FOCUSABLE), function (el) {
        return el.offsetParent !== null || el === doc.activeElement;
      });
    }

    input.addEventListener('input', function () { render(); });
    input.addEventListener('keydown', function (event) {
      if (event.isComposing || event.keyCode === 229) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        select(selected + 1);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        select(selected - 1);
      } else if (event.key === 'Home' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        select(0);
      } else if (event.key === 'End' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        select(rows.length - 1);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        activate(selected, Boolean(event.metaKey || event.ctrlKey));
      } else if (event.key === 'Delete' && event.shiftKey) {
        event.preventDefault();
        remove(selected);
      }
    });
    doc.addEventListener('keydown', function (event) {
      if (!openState) return;
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        close(true);
        return;
      }
      if (event.key !== 'Tab') return;
      var items = focusable();
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      var active = doc.activeElement;
      if (event.shiftKey && (active === first || !panel.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !panel.contains(active))) {
        event.preventDefault();
        first.focus();
      }
    }, true);
    Array.prototype.forEach.call(root.querySelectorAll('[data-td-history-close]'), function (el) {
      el.addEventListener('click', function () { close(true); });
    });
    if (clearButton) clearButton.addEventListener('click', clear);

    var coordinator = options.coordinator || win.OinkSurfaceCoordinator;
    if (coordinator && typeof coordinator.register === 'function') {
      coordinator.register('history', function (restoreFocus) { close(restoreFocus === true); });
    }
    if (win.addEventListener) win.addEventListener('pagehide', function () { close(false); });

    var actions = options.registry || win.OinkActions;
    if (actions && typeof actions.registerExecutor === 'function' && actions.get && actions.get('browse_history')) {
      try {
        actions.registerExecutor('browse_history', function () {
          open();
          return { history: true };
        });
      } catch (_) {
        /* a second runtime instance keeps the first executor */
      }
    }

    return Object.freeze({
      clear: clear,
      close: close,
      entries: function () { return read(win, scope); },
      isOpen: isOpen,
      open: open,
      render: render,
    });
  }

  var api = { LIMIT: LIMIT, init: init, keyOf: keyOf, read: read, record: record, sanitize: sanitize };
  global.OinkHistory = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (!global.__OINK_HISTORY_MANUAL_INIT__ && global.document) api.instance = init();
})(typeof window === 'object' ? window : globalThis);
