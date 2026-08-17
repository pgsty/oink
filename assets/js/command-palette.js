/**
 * Command Palette: one dialog for local pages, quick links, and safe actions.
 * Bundled only when shell/search-enabled.html is true.
 */
(function (global) {
  'use strict';

  var html = document.documentElement;
  // Typing this prefix, or pressing "\\" outside a field, restricts the
  // palette to commands. "/" opens the full search surface.
  var COMMAND_PREFIX = '>';
  var TYPING_TAGS = { INPUT: true, TEXTAREA: true, SELECT: true };

  // A bare single-character shortcut must yield to anything the reader could be
  // typing into, including author-supplied editable regions.
  function isTypingTarget(target) {
    if (!target || target.nodeType !== 1) return false;
    if (TYPING_TAGS[target.tagName]) return true;
    return typeof target.closest === 'function'
      ? target.closest('[contenteditable]:not([contenteditable="false"])') !== null
      : false;
  }

  function isRendered(element) {
    if (!element) return false;
    if (typeof element.closest === 'function' && element.closest('[hidden]'))
      return false;
    if (global.getComputedStyle) {
      var style = global.getComputedStyle(element);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
    }
    return element.offsetParent !== null;
  }

  function hasOpenDialog() {
    if (document.querySelector('dialog[open]')) return true;
    return Array.prototype.some.call(
      document.querySelectorAll('[role="dialog"]'),
      isRendered,
    );
  }

  var FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), ' +
    'select:not([disabled]), textarea:not([disabled]), ' +
    '[tabindex]:not([tabindex="-1"])';

  function focusable(container) {
    return Array.prototype.filter.call(
      container.querySelectorAll(FOCUSABLE),
      function (el) {
        return el.offsetParent !== null || el === document.activeElement;
      },
    );
  }

  function tabTrap(container, isActive) {
    return function (event) {
      if (event.key !== 'Tab' || !isActive()) return;
      var items = focusable(container);
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      var active = document.activeElement;
      if (event.shiftKey && (active === first || !container.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
  }

  function initSearch(options) {
    options = options || {};
    var root = options.root || document.getElementById('td-shell-search');
    if (!root) return null;
    var input = root.querySelector('.td-shell-search__input');
    var list = root.querySelector('.td-shell-search__list');
    var panel = root.querySelector('.td-shell-search__panel');
    var status = root.querySelector('[data-td-shell-search-status]');
    if (!input || !list || !panel || !status) return null;

    var registry = options.registry || global.OinkActions;
    var model = options.model || global.OinkPaletteModel;
    var searchApi = options.searchApi || global.OinkSearchEngine;
    if (!registry || !model || !searchApi) return null;

    var engine = null;
    var loading = false;
    var loadFailed = false;
    var indexRequest = 0;
    var rows = [];
    var selected = 0;
    var hideTimer = 0;
    var choiceState = null;
    var composing = false;
    var pendingKey = '';
    var pendingActivation = 0;
    var activationSerial = 0;
    var session = 0;
    var delayedClose = false;
    var logicalOpen = false;
    var maxResults = parseInt(root.dataset.tdMaxResults, 10);
    if (!Number.isFinite(maxResults) || maxResults < 1) maxResults = 10;
    var openers = document.querySelectorAll('[data-td-shell-search-open]');
    var lastOpener = null;
    var labels = {
      actions: root.dataset.tdTActions || 'Actions',
      commands: root.dataset.tdTCommands || 'Commands',
      pageActions: root.dataset.tdTPageActions || 'Page actions',
      preferences: root.dataset.tdTPreferences || 'Preferences',
      choose: root.dataset.tdTChoice || 'Choose an option',
      pages: root.dataset.tdTPages || 'Pages',
      quickLinks: root.dataset.tdTQuickLinks || 'Quick links',
    };

    function isOpen() {
      return logicalOpen;
    }

    function announce(text) {
      status.textContent = '';
      global.requestAnimationFrame(function () { status.textContent = text; });
    }

    function resultMessage(count) {
      return (root.dataset.tdTResults || '{count} results').replace(
        '{count}', String(count),
      );
    }

    function clearRows() {
      list.textContent = '';
      rows = [];
      selected = 0;
      input.removeAttribute('aria-activedescendant');
    }

    function syncBusy() {
      if (loading || pendingKey) list.setAttribute('aria-busy', 'true');
      else list.removeAttribute('aria-busy');
    }

    function clearPending(activation) {
      if (activation && activation !== pendingActivation) return;
      pendingKey = '';
      pendingActivation = 0;
      syncBusy();
    }

    function message(text) {
      clearRows();
      var el = document.createElement('div');
      el.className = 'td-shell-search__empty';
      el.textContent = text;
      list.appendChild(el);
      announce(text);
    }

    function ensureIndex() {
      if (engine || loading) return;
      loadFailed = false;
      loading = true;
      var request = ++indexRequest;
      syncBusy();
      fetch(root.dataset.tdIndexSrc)
        .then(function (response) {
          if (!response.ok) throw new Error('Search index unavailable');
          return response.json();
        })
        .then(function (data) {
          if (request !== indexRequest) return;
          engine = searchApi.create(data, lunr, maxResults);
          loading = false;
          syncBusy();
          if (isOpen()) render(input.value);
        })
        .catch(function () {
          if (request !== indexRequest) return;
          loading = false;
          loadFailed = true;
          syncBusy();
          if (isOpen() && normalQuery(input.value))
            render(input.value, false);
        });
    }

    // `seed` pre-fills the query. Passing the command prefix opens straight
    // into command mode; it is undefined when `open` is used as a listener.
    function open(event, seed) {
      session += 1;
      var openSession = session;
      logicalOpen = true;
      var eventOpener = event && event.currentTarget;
      function canRestoreFocus(candidate) {
        return candidate && candidate !== document &&
          typeof candidate.focus === 'function';
      }
      var opener = canRestoreFocus(eventOpener)
        ? eventOpener
        : document.activeElement;
      if (!canRestoreFocus(opener)) opener = null;
      if (
        opener && opener.closest &&
        opener.closest('#td-shell-sidebar') &&
        html.hasAttribute('data-td-shell-drawer')
      ) {
        var drawerOpeners = document.querySelectorAll('[data-td-shell-drawer-open]');
        opener = Array.prototype.find.call(drawerOpeners, function (candidate) {
          return candidate.offsetParent !== null;
        }) || drawerOpeners[0] || opener;
      }
      if (
        opener && opener.closest && opener.closest('[data-td-mobile-menu]')
      ) {
        opener = document.querySelector('[data-td-menu-toggle]') || opener;
      }
      lastOpener = opener;
      if (global.OinkSurfaceCoordinator)
        global.OinkSurfaceCoordinator.closeOthers('palette');
      global.clearTimeout(hideTimer);
      delayedClose = false;
      root.hidden = false;
      html.setAttribute('data-td-shell-lock', '');
      openers.forEach(function (el) { el.setAttribute('aria-expanded', 'true'); });
      input.setAttribute('aria-expanded', 'true');
      global.requestAnimationFrame(function () {
        if (logicalOpen && openSession === session) root.classList.add('td-is-open');
      });
      choiceState = null;
      clearPending();
      input.focus();
      if (typeof seed === 'string') {
        input.value = seed;
        // Caret after the prefix rather than selecting it, so the next
        // keystroke continues the query instead of replacing the mode.
        try {
          input.setSelectionRange(seed.length, seed.length);
        } catch (e) {
          /* selection is unsupported on some input types */
        }
      } else {
        input.select();
      }
      render(input.value);
      // Empty and command-only modes are immediately useful and must not wait
      // for or trigger the local index request.
      if (normalQuery(input.value)) ensureIndex();
    }

    function close(restoreFocus, preservePending) {
      if (!isOpen() && delayedClose) return;
      delayedClose = true;
      session += 1;
      logicalOpen = false;
      root.classList.remove('td-is-open');
      html.removeAttribute('data-td-shell-lock');
      openers.forEach(function (el) { el.setAttribute('aria-expanded', 'false'); });
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      choiceState = null;
      if (!preservePending) clearPending();
      if (
        restoreFocus !== false && lastOpener &&
        typeof lastOpener.focus === 'function' &&
        root.contains(document.activeElement)
      ) lastOpener.focus();
      var reducedMotion = global.matchMedia &&
        global.matchMedia('(prefers-reduced-motion: reduce)').matches;
      hideTimer = global.setTimeout(function () {
        root.hidden = true;
        delayedClose = false;
      }, reducedMotion ? 0 : 240);
    }
    if (global.OinkSurfaceCoordinator)
      global.OinkSurfaceCoordinator.register('palette', close);

    function normalQuery(value) {
      var query = String(value || '').trim();
      return query && query.charAt(0) !== COMMAND_PREFIX;
    }

    function highlight(text, query) {
      text = String(text || '');
      query = String(query || '').trim();
      var fragment = document.createDocumentFragment();
      var at = query ? text.toLowerCase().indexOf(query.toLowerCase()) : -1;
      if (at < 0) {
        fragment.appendChild(document.createTextNode(text));
        return fragment;
      }
      fragment.appendChild(document.createTextNode(text.slice(0, at)));
      var mark = document.createElement('mark');
      mark.textContent = text.slice(at, at + query.length);
      fragment.appendChild(mark);
      fragment.appendChild(document.createTextNode(text.slice(at + query.length)));
      return fragment;
    }

    function select(index) {
      var options = Array.prototype.slice.call(
        list.querySelectorAll('[role="option"]'),
      );
      if (!options.length) {
        input.removeAttribute('aria-activedescendant');
        return;
      }
      selected = Math.max(0, Math.min(index, options.length - 1));
      options.forEach(function (row, n) {
        row.setAttribute('aria-selected', n === selected ? 'true' : 'false');
      });
      var row = options[selected];
      input.setAttribute('aria-activedescendant', row.id);
      row.scrollIntoView({ block: 'nearest' });
    }

    function pageGroups(results) {
      var order = registry.rootOrder ? registry.rootOrder() : [];
      return searchApi.group(results).map(function (group, sourceOrder) {
        return {
          key: group.key,
          label: group.label || labels.pages,
          rows: group.results.map(function (result) {
            return {
              id: 'page:' + result.doc.ref,
              sourceId: result.doc.ref,
              type: 'page',
              title: result.doc.title || result.doc.ref,
              description: result.excerpt || result.doc.description || '',
              ref: result.doc.ref,
              icon: result.doc.icon || 'fa-regular fa-file-lines',
              available: true,
              page: result,
            };
          }),
          sourceOrder: sourceOrder,
        };
      }).sort(function (a, b) {
        var aIndex = order.indexOf(a.key);
        var bIndex = order.indexOf(b.key);
        aIndex = aIndex < 0 ? Number.MAX_SAFE_INTEGER : aIndex;
        bIndex = bIndex < 0 ? Number.MAX_SAFE_INTEGER : bIndex;
        return aIndex - bIndex || model.lexical(a.label, b.label) ||
          a.sourceOrder - b.sourceOrder;
      });
    }

    function groupsFor(value) {
      if (choiceState)
        return model.choiceGroup(choiceState.action, choiceState.command, labels);
      var raw = String(value || '').trim();
      if (!raw) return model.emptyGroups(registry, labels);
      if (raw.charAt(0) === COMMAND_PREFIX)
        return model.commandGroups(registry, raw.slice(1).trim(), labels);

      var groups = [];
      if (engine) {
        try { groups = pageGroups(engine.query(raw)); } catch (_) { groups = []; }
      }
      var actions = model.actionRows(registry, raw);
      if (actions.length)
        groups.push({ key: 'actions', label: labels.actions, rows: actions });
      return groups;
    }

    function appendIcon(container, icon) {
      if (!icon) return;
      var el = document.createElement('i');
      String(icon).split(/\s+/).filter(Boolean).forEach(function (token) {
        el.classList.add(token);
      });
      el.classList.add('td-shell-search__item-icon');
      el.setAttribute('aria-hidden', 'true');
      container.appendChild(el);
    }

    function renderGroups(groups, query) {
      clearRows();
      groups.forEach(function (group) {
        if (!group.rows || !group.rows.length) return;
        var section = document.createElement('div');
        section.className = 'td-shell-search__group';
        section.setAttribute('role', 'group');

        var heading = document.createElement('div');
        heading.className = 'td-shell-search__group-label';
        heading.id = 'td-shell-search-group-' + group.key;
        heading.textContent = group.label;
        section.setAttribute('aria-labelledby', heading.id);
        section.appendChild(heading);

        group.rows.forEach(function (rowData) {
          var index = rows.length;
          rows.push(rowData);
          var row = document.createElement('div');
          row.className = 'td-shell-search__item';
          row.id = 'td-shell-search-option-' + index;
          row.setAttribute('role', 'option');
          row.setAttribute('aria-selected', 'false');
          row.setAttribute('tabindex', '-1');
          row.dataset.paletteRow = String(index);
          if (!rowData.available) {
            row.classList.add('td-is-disabled');
            row.setAttribute('aria-disabled', 'true');
          }
          if (rowData.option && rowData.option.active)
            row.setAttribute('aria-current', 'true');

          appendIcon(row, rowData.icon);
          var meta = document.createElement('div');
          meta.className = 'td-shell-search__item-meta';
          var title = document.createElement('div');
          title.className = 'td-shell-search__item-title';
          title.appendChild(highlight(rowData.title, query));
          meta.appendChild(title);
          var detail = rowData.disabledReason || rowData.description || rowData.ref;
          if (detail && detail !== rowData.title) {
            var description = document.createElement('div');
            description.id = row.id + '-description';
            description.className = rowData.type === 'page'
              ? 'td-shell-search__item-excerpt'
              : 'td-shell-search__item-ref';
            description.appendChild(highlight(detail, query));
            meta.appendChild(description);
            if (!rowData.available)
              row.setAttribute('aria-describedby', description.id);
          }
          row.appendChild(meta);
          row.addEventListener('pointermove', function (event) {
            if ((!event.pointerType || event.pointerType === 'mouse') && selected !== index)
              select(index);
          });
          row.addEventListener('click', function () { activate(index); });
          section.appendChild(row);
        });
        list.appendChild(section);
      });
      if (rows.length) {
        select(0);
        announce(resultMessage(rows.length));
      }
    }

    function render(value, retryIndex) {
      if (retryIndex === undefined) retryIndex = true;
      var raw = String(value || '').trim();
      var commandOnly = raw.charAt(0) === COMMAND_PREFIX;
      var groups = groupsFor(value);
      var actionCount = groups.reduce(function (total, group) {
        return total + group.rows.length;
      }, 0);

      if (!raw || choiceState || commandOnly || engine || (loadFailed && !retryIndex)) {
        if (!actionCount) {
          message(loadFailed && !retryIndex && !commandOnly
            ? (root.dataset.tdTIndexUnavailable || root.dataset.tdTEmpty || 'Page index unavailable')
            : commandOnly
              ? (root.dataset.tdTNoCommands || root.dataset.tdTEmpty || 'No results')
              : (root.dataset.tdTEmpty || 'No results'));
        } else {
          renderGroups(groups, choiceState ? '' : (commandOnly ? raw.slice(1).trim() : raw));
          if (loadFailed && !retryIndex)
            announce(root.dataset.tdTIndexUnavailable || resultMessage(rows.length));
        }
        return;
      }

      // Normal search can still offer matching actions while the index loads.
      if (actionCount) renderGroups(groups, raw);
      else message(root.dataset.tdTLoading || '…');
      ensureIndex();
    }

    function runRow(row) {
      if (row.type === 'page' || row.type === 'quick') {
        var destination = row.ref || row.url;
        destination = registry.safeUrl ? registry.safeUrl(destination) : null;
        if (!destination)
          return Promise.reject(new Error(root.dataset.tdTActionFailed || 'Unsafe link'));
        if (row.target === 'blank') {
          global.open(destination, '_blank', 'noopener,noreferrer');
          return Promise.resolve();
        }
        global.location.assign(destination);
        return Promise.resolve();
      }
      if (row.type === 'choice') {
        return row.command
          ? registry.runCommand(row.command.id, { source: 'palette', value: row.option })
          : registry.run(row.action.id, { source: 'palette', value: row.option });
      }
      if (row.type === 'command')
        return registry.runCommand(row.sourceId, { source: 'palette' });
      return registry.run(row.sourceId, { source: 'palette' });
    }

    function activate(index) {
      var row = rows[index];
      if (!row) return;
      if (!row.available) {
        announce(row.disabledReason || root.dataset.tdTActionFailed || 'Unavailable');
        return;
      }
      var targetChoice = row.type === 'action' && row.action && row.action.kind === 'choice'
        ? row.action
        : row.type === 'command' && row.command && row.command.action
          ? registry.get(row.command.action)
          : null;
      if (targetChoice && targetChoice.kind === 'choice') {
        choiceState = {
          action: targetChoice,
          command: row.type === 'command' ? row.command : null,
        };
        render(input.value);
        announce(root.dataset.tdTChoice || 'Choose an option');
        return;
      }
      if (pendingKey) return;
      var activationSession = session;
      var activation = ++activationSerial;
      pendingKey = row.id;
      pendingActivation = activation;
      syncBusy();
      var isPrint = row.sourceId === 'print' ||
        (row.command && row.command.action === 'print') ||
        (row.action && row.action.id === 'print');
      if (isPrint) close(true, true);
      runRow(row).then(function (result) {
        clearPending(activation);
        if (activationSession !== session && !isPrint) return;
        if (result && result.requiresChoice) {
          choiceState = { action: result.action, command: result.command || null };
          render(input.value);
          announce(root.dataset.tdTChoice || 'Choose an option');
          return;
        }
        var completedInPlace = result && (
          result.theme ||
          (result.action && result.action.id === 'copy_markdown')
        );
        if (completedInPlace) {
          choiceState = null;
          render(input.value);
          announce(row.title || (result.action && result.action.title) || labels.actions);
        } else if (!isPrint) {
          close(true);
        }
      }).catch(function (error) {
        clearPending(activation);
        if (activationSession !== session) return;
        announce(
          (error && error.message) ||
          row.disabledReason || root.dataset.tdTActionFailed || 'Action failed',
        );
      });
    }

    var debounce = 0;
    input.addEventListener('compositionstart', function () { composing = true; });
    input.addEventListener('compositionend', function () {
      composing = false;
      choiceState = null;
      render(input.value);
    });
    input.addEventListener('input', function () {
      if (composing) return;
      choiceState = null;
      global.clearTimeout(debounce);
      debounce = global.setTimeout(function () { render(input.value); }, 80);
    });
    input.addEventListener('keydown', function (event) {
      if (event.isComposing || composing || event.keyCode === 229) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (rows.length) select(Math.min(selected + 1, rows.length - 1));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (rows.length) select(Math.max(selected - 1, 0));
      } else if (event.key === 'Home' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        if (rows.length) select(0);
      } else if (event.key === 'End' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        if (rows.length) select(rows.length - 1);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        activate(selected);
      }
    });

    document.addEventListener('keydown', tabTrap(panel, isOpen), true);
    document.addEventListener('keydown', function (event) {
      if (event.isComposing || composing || event.keyCode === 229) return;
      if ((event.metaKey || event.ctrlKey) && String(event.key).toLowerCase() === 'k') {
        event.preventDefault();
        if (isOpen()) close();
        else open();
      } else if (
        (event.key === '/' || event.key === '\\') &&
        !event.metaKey && !event.ctrlKey && !event.altKey && !event.shiftKey &&
        !event.defaultPrevented && !isOpen() && !hasOpenDialog() &&
        !isTypingTarget(event.target)
      ) {
        // Slash and backslash are bare shortcuts, so they never steal a
        // character from a field. Slash is full search; backslash is commands.
        event.preventDefault();
        if (event.key === '\\') open(event, COMMAND_PREFIX);
        else open(event);
      } else if (event.key === 'Escape' && isOpen()) {
        event.preventDefault();
        close();
      }
    });
    openers.forEach(function (el) { el.addEventListener('click', open); });
    root.querySelectorAll('[data-td-shell-search-close]').forEach(function (el) {
      el.addEventListener('click', close);
    });

    var apple = /Mac|iPhone|iPad|iPod/.test(
      navigator.platform || navigator.userAgent,
    );
    if (!apple) {
      document.querySelectorAll('[data-td-shell-meta-key]').forEach(function (el) {
        el.textContent = 'Ctrl';
      });
    }

    return Object.freeze({
      activate: activate,
      close: close,
      ensureIndex: ensureIndex,
      isOpen: isOpen,
      open: open,
      render: render,
      rows: function () { return rows.slice(); },
    });
  }

  // Let keyboard-nav.js reuse this instance without duplicating dialog logic.
  global.OinkCommandPalette = {
    init: initSearch,
    commandPrefix: COMMAND_PREFIX,
  };
  if (typeof module === 'object' && module.exports)
    module.exports = global.OinkCommandPalette;
  if (!global.__OINK_PALETTE_MANUAL_INIT__)
    global.OinkCommandPalette.instance = initSearch();
})(typeof window === 'object' ? window : globalThis);
