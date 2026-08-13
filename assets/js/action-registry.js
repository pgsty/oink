/**
 * action-registry.js — shared execution for page actions and the Palette.
 *
 * Page-specific URLs and localized labels arrive as inert JSON. The only
 * executable operations are the built-ins in this file or explicitly
 * registered theme executors; site configuration can never add callbacks.
 */
(function (global) {
  'use strict';

  var BUILTINS = new Set([
    'copy_markdown',
    'open_chatgpt',
    'open_claude',
    'view_markdown',
    'view_history',
    'edit_page',
    'create_child_page',
    'create_issue',
    'create_project_issue',
    'print_section',
    'print',
    'switch_theme',
    'switch_language',
    'switch_version',
    'open_github',
  ]);
  var SAFE_SCHEMES = new Set(['http:', 'https:']);

  function readManifest(documentObject) {
    var node = documentObject.getElementById('oink-action-manifest');
    if (!node) return { version: 1, actions: [], commands: [] };
    try {
      var parsed = JSON.parse(node.textContent || '{}');
      return parsed && parsed.version === 1
        ? parsed
        : { version: 1, actions: [], commands: [] };
    } catch (_) {
      return { version: 1, actions: [], commands: [] };
    }
  }

  function safeUrl(value, base) {
    if (!value || /^\s|\s$/.test(value) || /^[/\\]{2}/.test(value) || /\\/.test(value))
      return null;
    try {
      var parsed = new URL(value, base);
      if (!SAFE_SCHEMES.has(parsed.protocol)) return null;
      return parsed.href;
    } catch (_) {
      return null;
    }
  }

  function create(options) {
    options = options || {};
    var windowObject = options.window || global;
    var documentObject = options.document || windowObject.document;
    var manifest = options.manifest || readManifest(documentObject);
    var fetchApi =
      options.fetch ||
      (windowObject.fetch
        ? windowObject.fetch.bind(windowObject)
        : function () {
            return Promise.reject(new Error('Fetch unavailable'));
          });
    var actions = new Map();
    var commands = [];
    var executors = new Map();
    var markdown = new Map();

    (manifest.actions || []).forEach(function (action) {
      if (BUILTINS.has(action.id) && !actions.has(action.id))
        actions.set(action.id, Object.freeze(action));
    });
    (manifest.commands || []).forEach(function (command) {
      if (!command || !command.id) return;
      if (command.kind === 'builtin') {
        if (!BUILTINS.has(command.action)) return;
      } else if (command.kind === 'url') {
        if (!safeUrl(command.url, windowObject.location.href)) return;
      } else {
        return;
      }
      commands.push(Object.freeze(command));
    });

    function failure(code, action, message) {
      var error = new Error(message || code);
      error.code = code;
      error.action = action || null;
      return error;
    }

    function get(id) {
      return actions.get(id) || null;
    }

    function list(query) {
      query = query || {};
      var placement = query.placement;
      return Array.from(actions.values()).filter(function (action) {
        return !placement || (action.placements && action.placements[placement]);
      });
    }

    function getCommands() {
      return commands.slice();
    }

    function getQuickLinks() {
      return (manifest.quickLinks || []).filter(function (link) {
        return link && link.kind === 'url' && safeUrl(link.url, windowObject.location.href);
      }).slice();
    }

    function getRootOrder() {
      return (manifest.rootOrder || []).map(function (key) {
        return String(key).trim().toLowerCase();
      }).filter(Boolean);
    }

    function fetchMarkdown(url) {
      if (markdown.has(url)) return markdown.get(url);
      var pending = fetchApi(url)
        .then(function (response) {
          if (!response.ok) throw failure('markdown_fetch_failed', null);
          return response.text();
        })
        .catch(function (error) {
          markdown.delete(url);
          throw error;
        });
      markdown.set(url, pending);
      return pending;
    }

    function fallbackCopy(text) {
      return new Promise(function (resolve, reject) {
        var textarea = documentObject.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        documentObject.body.appendChild(textarea);
        textarea.select();
        try {
          if (documentObject.execCommand('copy')) resolve();
          else reject(failure('clipboard_failed', null));
        } catch (error) {
          reject(error);
        }
        textarea.remove();
      });
    }

    function writeClipboard(text) {
      var clipboard = windowObject.navigator && windowObject.navigator.clipboard;
      return clipboard && clipboard.writeText
        ? clipboard.writeText(text)
        : fallbackCopy(text);
    }

    function resolveUrl(actionOrId, value) {
      var action = typeof actionOrId === 'string' ? get(actionOrId) : actionOrId;
      if (!action || action.available === false) return null;
      if (action.id === 'open_chatgpt' || action.id === 'open_claude') {
        if (
          typeof action.promptTemplate !== 'string' ||
          action.promptTemplate.indexOf('%s') < 0
        ) return null;
        var prompt = action.promptTemplate.replace('%s', function () {
          return windowObject.location.href;
        });
        var assistantUrl = action.id === 'open_chatgpt'
          ? 'https://chatgpt.com/?hints=search&prompt=' + encodeURIComponent(prompt)
          : 'https://claude.ai/new?q=' + encodeURIComponent(prompt);
        return safeUrl(assistantUrl, windowObject.location.href);
      }
      var target = value && value.url ? value.url : action.url;
      return safeUrl(target, windowObject.location.href);
    }

    function openUrl(action, value) {
      var url = resolveUrl(action, value);
      if (!url) return Promise.reject(failure('unsafe_url', action));
      if (action.target === 'blank' || (value && value.target === 'blank')) {
        windowObject.open(url, '_blank', 'noopener,noreferrer');
      } else {
        windowObject.location.assign(url);
      }
      return Promise.resolve({ action: action, url: url });
    }

    function run(id, context) {
      var action = get(id);
      context = context || {};
      if (!action) return Promise.reject(failure('unsupported_action', null, id));
      if (!action.available)
        return Promise.reject(
          failure('unavailable', action, action.disabledReason || 'Unavailable'),
        );
      var custom = executors.get(id);
      if (custom) return Promise.resolve().then(function () { return custom(context, action); });
      if (id === 'copy_markdown') {
        if (!action.url) return Promise.reject(failure('unavailable', action));
        return fetchMarkdown(action.url)
          .then(writeClipboard)
          .then(function () { return { action: action }; });
      }
      if (id === 'print') {
        windowObject.print();
        return Promise.resolve({ action: action });
      }
      if (action.kind === 'url') return openUrl(action, context.value);
      if (action.kind === 'choice' && context.value && context.value.url)
        return openUrl(action, context.value);
      return Promise.reject(failure('missing_executor', action));
    }

    function runCommand(id, context) {
      var command = commands.find(function (candidate) { return candidate.id === id; });
      if (!command) return Promise.reject(failure('unsupported_command', null, id));
      if (command.kind === 'builtin') {
        var action = get(command.action);
        if (
          action &&
          action.kind === 'choice' &&
          !(context && context.value)
        ) {
          if (!action.available)
            return Promise.reject(
              failure('unavailable', action, action.disabledReason || 'Unavailable'),
            );
          return Promise.resolve({
            action: action,
            command: command,
            options: (action.options || []).slice(),
            requiresChoice: true,
          });
        }
        return run(command.action, context);
      }
      return openUrl(command, context && context.value);
    }

    function registerExecutor(id, executor) {
      if (!BUILTINS.has(id) || typeof executor !== 'function')
        throw failure('unsupported_executor', get(id), id);
      if (executors.has(id)) throw failure('duplicate_executor', get(id), id);
      executors.set(id, executor);
    }

    function invalidateMarkdown(url) {
      if (url) markdown.delete(url);
      else markdown.clear();
    }

    return Object.freeze({
      get: get,
      list: list,
      commands: getCommands,
      quickLinks: getQuickLinks,
      rootOrder: getRootOrder,
      run: run,
      runCommand: runCommand,
      registerExecutor: registerExecutor,
      preloadMarkdown: fetchMarkdown,
      invalidateMarkdown: invalidateMarkdown,
      resolveUrl: function (id, value) { return resolveUrl(id, value); },
      safeUrl: function (value) { return safeUrl(value, windowObject.location.href); },
    });
  }

  var api = { BUILTINS: BUILTINS, create: create, safeUrl: safeUrl };
  global.OinkActionRegistry = api;
  if (global.document) global.OinkActions = create();
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
