// Only named groups synchronize, update the hash, and persist selection.
(function (global) {
  'use strict';

  var STORAGE_PREFIX = 'td-tabs:v1:';
  var READY = 'data-td-tabs-ready';

  function storageGet(storage, key) {
    try { return storage ? storage.getItem(key) : null; } catch (_) { return null; }
  }
  function storageSet(storage, key, value) {
    try { if (storage) storage.setItem(key, value); } catch (_) { /* ignore */ }
  }

  function tabsOf(root) {
    return Array.prototype.slice.call(root.querySelectorAll(':scope > .td-tabs__list > [role="tab"]'));
  }
  function panelsOf(root) {
    return Array.prototype.slice.call(root.querySelectorAll(':scope > .td-tabs__panel'));
  }
  function valueOf(element) {
    return element ? element.getAttribute('data-td-tabs-value') || '' : '';
  }
  function groupOf(root) {
    return root.getAttribute('data-td-tabs-group') || '';
  }

  // Show one value in a set. Returns true when the set had that value.
  function activate(root, value, options) {
    options = options || {};
    var tabs = tabsOf(root);
    var panels = panelsOf(root);
    // A peer set that lacks the value stays unchanged (sync must never leave a
    // set without a selected tab).
    if (!tabs.some(function (tab) { return valueOf(tab) === value; })) return false;
    tabs.forEach(function (tab) {
      var active = valueOf(tab) === value;
      tab.setAttribute('aria-selected', active ? 'true' : 'false');
      tab.setAttribute('tabindex', active ? '0' : '-1');
    });
    panels.forEach(function (panel) {
      var active = valueOf(panel) === value;
      if (active) panel.setAttribute('data-td-tabs-active', '');
      else panel.removeAttribute('data-td-tabs-active');
      panel.hidden = !active;
    });
    if (options.focus) {
      var target = tabs.filter(function (tab) { return valueOf(tab) === value; })[0];
      if (target) target.focus();
    }
    return true;
  }

  function currentValue(root) {
    var active = root.querySelector(':scope > .td-tabs__list > [role="tab"][aria-selected="true"]');
    return valueOf(active) || valueOf(tabsOf(root)[0]);
  }

  // Runtime state shared by every set on the page.
  function createController(doc, win, options) {
    options = options || {};
    var storage = Object.prototype.hasOwnProperty.call(options, 'storage')
      ? options.storage
      : (function () { try { return win.localStorage; } catch (_) { return null; } })();
    var sets = [];

    function peers(group) {
      return sets.filter(function (root) { return groupOf(root) === group; });
    }

    function select(root, value, origin) {
      if (!activate(root, value, { focus: origin === 'keyboard' })) return false;
      var group = groupOf(root);
      if (!group) return true;
      if (origin === 'click' || origin === 'keyboard') {
        storageSet(storage, STORAGE_PREFIX + group, value);
        if (win.history && win.history.replaceState && win.location) {
          var next = win.location.pathname + win.location.search + '#' + group + '-' + value;
          try { win.history.replaceState(win.history.state, '', next); } catch (_) { /* ignore */ }
        }
      }
      if (origin !== 'sync') {
        peers(group).forEach(function (peer) {
          if (peer !== root) activate(peer, value);
        });
      }
      return true;
    }

    function onKeydown(root, event) {
      var keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
      if (keys.indexOf(event.key) === -1) return;
      var tabs = tabsOf(root);
      if (!tabs.length) return;
      var index = tabs.indexOf(event.target);
      if (index === -1) return;
      var rtl = (root.closest && root.closest('[dir="rtl"]')) ||
        (doc.documentElement && doc.documentElement.dir === 'rtl');
      var forward = event.key === (rtl ? 'ArrowLeft' : 'ArrowRight');
      var backward = event.key === (rtl ? 'ArrowRight' : 'ArrowLeft');
      var next = index;
      if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = tabs.length - 1;
      else if (forward) next = (index + 1) % tabs.length;
      else if (backward) next = (index - 1 + tabs.length) % tabs.length;
      event.preventDefault();
      select(root, valueOf(tabs[next]), 'keyboard');
    }

    function enhance(root) {
      if (root.hasAttribute(READY)) return;
      var list = root.querySelector(':scope > .td-tabs__list');
      if (!list) return;
      dedupeSetIDs(doc, root);
      list.addEventListener('click', function (event) {
        var tab = event.target && event.target.closest ? event.target.closest('[role="tab"]') : null;
        if (!tab || tab.parentNode !== list) return;
        event.preventDefault();
        select(root, valueOf(tab), 'click');
      });
      list.addEventListener('keydown', function (event) { onKeydown(root, event); });
      sets.push(root);
      var initial = root.getAttribute('data-td-tabs-default') || currentValue(root);
      var group = groupOf(root);
      if (group) {
        var stored = storageGet(storage, STORAGE_PREFIX + group);
        if (stored && tabsOf(root).some(function (tab) { return valueOf(tab) === stored; })) initial = stored;
      }
      activate(root, initial);
      root.setAttribute(READY, '');
    }

    // Hash has priority over storage: #group-value selects that value in
    // every set of the group and scrolls the first one into view.
    function applyHash() {
      if (!win.location || !win.location.hash) return false;
      var id;
      try { id = decodeURIComponent(win.location.hash.slice(1)); } catch (_) { return false; }
      var target = doc.getElementById(id);
      if (!target) return false;
      var panel = target.matches && target.matches('.td-tabs__panel') ? target : (target.closest ? target.closest('.td-tabs__panel') : null);
      if (!panel) return false;
      var root = panel.parentNode;
      if (!root || !root.hasAttribute || !root.hasAttribute('data-td-tabs')) return false;
      var value = valueOf(panel);
      select(root, value, 'hash');
      if (root.scrollIntoView) {
        var reduced = win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches;
        root.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' });
      }
      return true;
    }

    return { enhance: enhance, select: select, applyHash: applyHash, sets: sets, activate: activate };
  }

  // Regroup adjacent `.td-tab-block` siblings (same kind) into `.td-tabs`.
  function groupAdjacentBlocks(doc, blocks) {
    blocks = blocks || Array.prototype.slice.call(doc.querySelectorAll('.td-tab-block[data-td-tab]'));
    var runs = [];
    var seen = new Set();
    blocks.forEach(function (block) {
      if (seen.has(block)) return;
      var run = [block];
      seen.add(block);
      var node = block.nextSibling;
      while (node) {
        if (node.nodeType === 3 && !node.textContent.trim()) { node = node.nextSibling; continue; }
        // A comment node (e.g. <!-- prettier-ignore-end -->) separates runs;
        // so does a block that declares its own group (only the first block of
        // a run may carry `group`).
        if (node.nodeType === 8) break;
        if (node.nodeType === 1 && node.matches && node.matches('.td-tab-block[data-td-tab]') &&
            node.getAttribute('data-td-tab-kind') === block.getAttribute('data-td-tab-kind') &&
            !node.hasAttribute('data-td-tab-group')) {
          run.push(node);
          seen.add(node);
          node = node.nextSibling;
          continue;
        }
        break;
      }
      if (run.length > 1) runs.push(run);
    });

    var built = [];
    runs.forEach(function (run, runIndex) {
      var group = run[0].getAttribute('data-td-tab-group') || '';
      var values = run.map(function (block, i) { return block.getAttribute('data-td-tab-value') || ''; });
      // A grouped run must carry a value on every block; otherwise fall back
      // to a local (ungrouped) set and warn.
      if (group && values.some(function (v) { return !v; })) {
        if (global.console && console.warn) console.warn('OINK tabs: group "' + group + '" needs a value on every block; switching locally.');
        group = '';
      }
      if (!group) values = values.map(function (v, i) { return v || ('tab' + (i + 1)); });
      var duplicates = values.filter(function (v, i) { return values.indexOf(v) !== i; });
      if (duplicates.length) {
        if (global.console && console.warn) console.warn('OINK tabs: duplicate values in an adjacent run: ' + duplicates.join(', '));
        return;
      }
      var base = 'td-tabs-run-' + runIndex + '-' + Math.abs(hashString(values.join('|') + '|' + run.map(function (b) { return b.getAttribute('data-td-tab'); }).join('|')));
      var root = doc.createElement('div');
      root.className = 'td-tabs td-tabs--adjacent td-tabs--' + (run[0].getAttribute('data-td-tab-kind') || 'block');
      root.setAttribute('data-td-tabs', '');
      if (group) root.setAttribute('data-td-tabs-group', group);
      root.setAttribute('data-td-tabs-default', values[0]);
      var list = doc.createElement('div');
      list.className = 'td-tabs__list';
      list.setAttribute('role', 'tablist');
      root.appendChild(list);
      run.forEach(function (block, i) {
        var value = values[i];
        var panelID = uniqueID(doc, group ? group + '-' + value : base + '-' + value);
        var label = block.getAttribute('data-td-tab') || value;
        var tab = doc.createElement('button');
        tab.type = 'button';
        tab.className = 'td-tabs__tab';
        tab.setAttribute('role', 'tab');
        tab.id = panelID + '-tab';
        tab.setAttribute('aria-controls', panelID);
        tab.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
        tab.setAttribute('tabindex', i === 0 ? '0' : '-1');
        tab.setAttribute('data-td-tabs-value', value);
        tab.textContent = label;
        list.appendChild(tab);

        var panel = doc.createElement('div');
        panel.className = 'td-tabs__panel';
        panel.id = panelID;
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', panelID + '-tab');
        panel.setAttribute('tabindex', '0');
        panel.setAttribute('data-td-tabs-value', value);
        var title = block.querySelector(':scope > [data-td-tab-title]');
        if (title) title.parentNode.removeChild(title);
        // Keep a panel title for print / non-enhanced rendering (hidden by CSS
        // once the set is ready), like the tabs shortcode emits.
        var panelTitle = doc.createElement('div');
        panelTitle.className = 'td-tabs__panel-title';
        panelTitle.setAttribute('aria-hidden', 'true');
        panelTitle.textContent = label;
        panel.appendChild(panelTitle);
        // Move the block's remaining children into the panel body.
        var body = doc.createElement('div');
        body.className = 'td-tabs__panel-body';
        while (block.firstChild) body.appendChild(block.firstChild);
        // Embedded code blocks drop their own shell inside the tabs frame.
        Array.prototype.forEach.call(body.querySelectorAll(':scope > .td-code'), function (code) {
          code.classList.add('td-code--embedded');
        });
        panel.appendChild(body);
        root.appendChild(panel);
      });
      run[0].parentNode.insertBefore(root, run[0]);
      run.forEach(function (block) { block.parentNode.removeChild(block); });
      built.push(root);
    });
    return built;
  }

  // Peer sets of one group share `<group>-<value>` ids; keep ids unique in the
  // document (the first occurrence keeps the plain id for deep links).
  function uniqueID(doc, id) {
    if (!doc.getElementById || !doc.getElementById(id)) return id;
    var n = 2;
    while (doc.getElementById(id + '-' + n)) n += 1;
    return id + '-' + n;
  }

  function dedupeSetIDs(doc, root) {
    tabsOf(root).forEach(function (tab) {
      var panelID = tab.getAttribute('aria-controls');
      var panel = panelID ? doc.getElementById(panelID) : null;
      if (!panel || panel.parentNode === root) return; // first owner keeps its ids
      var ownPanel = panelsOf(root).filter(function (p) { return valueOf(p) === valueOf(tab); })[0];
      if (!ownPanel) return;
      var next = uniqueID(doc, panelID);
      ownPanel.id = next;
      tab.id = next + '-tab';
      tab.setAttribute('aria-controls', next);
      ownPanel.setAttribute('aria-labelledby', next + '-tab');
    });
  }

  function hashString(text) {
    var hash = 0;
    for (var i = 0; i < text.length; i += 1) hash = (hash * 31 + text.charCodeAt(i)) | 0;
    return hash;
  }

  function init(doc, win, options) {
    doc = doc || global.document;
    win = win || global;
    var controller = createController(doc, win, options);
    groupAdjacentBlocks(doc);
    Array.prototype.forEach.call(doc.querySelectorAll('.td-tabs[data-td-tabs]'), controller.enhance);
    controller.applyHash();
    if (win.addEventListener) {
      win.addEventListener('hashchange', function () { controller.applyHash(); });
    }
    return controller;
  }

  var api = { init: init, activate: activate, createController: createController, groupAdjacentBlocks: groupAdjacentBlocks };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.OinkTabs = api;

  if (global.document) {
    var start = function () { init(global.document, global); };
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', start, { once: true });
    } else {
      start();
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
