/** Pure result-model helpers shared by the Command Palette controller/tests. */
(function (global) {
  'use strict';

  var CJK = /[぀-ヿ㐀-䶿一-鿿豈-﫿]/;

  function lexical(a, b) {
    a = String(a || '');
    b = String(b || '');
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function normalize(value) {
    var string = String(value || '').trim().toLowerCase();
    return string.normalize ? string.normalize('NFKC').replace(/\s+/g, ' ') : string;
  }

  function searchable(record) {
    return [record.title, record.description]
      .concat(record.keywords || [])
      .filter(Boolean)
      .map(normalize)
      .join(' ');
  }

  function score(record, query) {
    var needle = normalize(query);
    if (!needle) return 1;
    var title = normalize(record.title);
    var id = normalize(record.id);
    var keywords = (record.keywords || []).map(normalize);
    var haystack = searchable(record);
    if (title === needle || id === needle) return 1000;
    if (title.indexOf(needle) === 0 || id.indexOf(needle) === 0) return 700;
    var keywordAt = keywords.findIndex(function (keyword) {
      return keyword === needle || keyword.indexOf(needle) === 0;
    });
    if (keywordAt >= 0) return keywords[keywordAt] === needle ? 600 : 500;
    var at = haystack.indexOf(needle);
    if (at >= 0) return 300 - Math.min(at, 200);

    // For Latin text, allow all whitespace-delimited tokens to appear in any
    // order. CJK stays deterministic substring matching like the page engine.
    if (!CJK.test(needle)) {
      var tokens = needle.split(/\s+/).filter(Boolean);
      if (tokens.length > 1 && tokens.every(function (token) {
        return haystack.indexOf(token) >= 0;
      })) return 200;
    }
    return 0;
  }

  function rank(records, query) {
    return (records || [])
      .map(function (record, order) {
        return { record: record, score: score(record, query), order: order };
      })
      .filter(function (item) { return item.score > 0; })
      .sort(function (a, b) {
        return b.score - a.score || lexical(a.record.title, b.record.title) ||
          lexical(a.record.id, b.record.id) || a.order - b.order;
      })
      .map(function (item) { return item.record; });
  }

  function actionRows(registry, query) {
    // Built-in actions lead in manifest order, which mirrors the navbar
    // (version, language, theme, GitHub); configured site commands trail in
    // their configured order (PRD 6).
    var rows = [];
    registry.list({ placement: 'palette' }).forEach(function (action) {
      rows.push({
        id: 'action:' + action.id,
        sourceId: action.id,
        type: 'action',
        title: action.title || action.id,
        description: action.description || '',
        icon: action.icon || 'fa-solid fa-bolt',
        keywords: action.keywords || [],
        available: action.available !== false,
        disabledReason: action.disabledReason || '',
        action: action,
      });
    });
    registry.commands().forEach(function (command) {
      var target = command.action ? registry.get(command.action) : null;
      var available = command.available !== false && (!target || target.available !== false);
      var disabledReason = command.disabledReason || (target && target.disabledReason) || '';
      rows.push({
        id: 'command:' + command.id,
        sourceId: command.id,
        type: 'command',
        title: command.title || command.id,
        description: command.description || '',
        icon: command.icon || 'fa-solid fa-terminal',
        keywords: command.keywords || [],
        available: available,
        disabledReason: disabledReason,
        command: command,
        target: command.target || 'self',
      });
    });
    if (!query) {
      // Browsing modes (empty search and empty command-only) keep manifest
      // order so listings mirror the navbar; ranking is query-driven only.
      // Unavailable entries appear only when they can explain why they
      // cannot run.
      return rows.filter(function (row) {
        return row.available || row.disabledReason;
      });
    }
    return rank(rows, query).filter(function (row) {
      return row.available || row.disabledReason;
    });
  }

  function emptyGroups(registry, labels) {
    var quick = (registry.quickLinks ? registry.quickLinks() : []).map(function (link) {
      return {
        id: 'quick:' + link.id,
        sourceId: link.id,
        type: 'quick',
        title: link.title || link.id,
        description: link.description || '',
        icon: link.icon || 'fa-solid fa-link',
        keywords: link.keywords || [],
        available: link.available !== false,
        disabledReason: link.disabledReason || '',
        url: link.url,
        target: link.target || 'self',
      };
    });
    var actions = actionRows(registry, '');
    // Derived from the descriptor's own placement rather than a hardcoded id
    // list: an action that appears in the page rail belongs to this group, so
    // adding a rail action does not silently land it under "commands".
    var pageActions = actions.filter(function (row) {
      return (
        row.action &&
        row.action.placements &&
        row.action.placements.page === true
      );
    });
    var preferences = actions.filter(function (row) {
      return row.action && row.action.kind === 'choice';
    });
    var commands = actions.filter(function (row) {
      return pageActions.indexOf(row) < 0 && preferences.indexOf(row) < 0;
    });
    return [
      { key: 'quick', label: labels.quickLinks, rows: quick },
      { key: 'page-actions', label: labels.pageActions || labels.actions, rows: pageActions },
      { key: 'preferences', label: labels.preferences || labels.actions, rows: preferences },
      { key: 'commands', label: labels.commands || labels.actions, rows: commands },
    ].filter(function (group) { return group.rows.length; });
  }

  function commandGroups(registry, query, labels) {
    var rows = actionRows(registry, query);
    return rows.length ? [{ key: 'actions', label: labels.actions, rows: rows }] : [];
  }

  function choiceGroup(action, command, labels) {
    var rows = (action.options || []).map(function (option) {
      return {
        id: 'choice:' + action.id + ':' + option.id,
        sourceId: option.id,
        type: 'choice',
        title: option.title || option.id,
        description: option.disabledReason || '',
        icon: action.icon || 'fa-solid fa-list',
        keywords: [],
        available: option.available !== false,
        disabledReason: option.disabledReason || '',
        action: action,
        command: command || null,
        option: option,
      };
    });
    return [{ key: 'choice', label: labels.choose, rows: rows }];
  }

  var api = {
    CJK: CJK,
    actionRows: actionRows,
    choiceGroup: choiceGroup,
    commandGroups: commandGroups,
    emptyGroups: emptyGroups,
    lexical: lexical,
    normalize: normalize,
    rank: rank,
    score: score,
  };
  global.OinkPaletteModel = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
