// One-click documentation feedback. OINK records only structured choices via
// the site's existing Google Analytics integration and never sends free text.
(function (global) {
  'use strict';

  function data(element, key) {
    if (!element) return '';
    if (element.dataset && element.dataset[key] !== undefined)
      return element.dataset[key];
    var dashed = key.replace(/[A-Z]/g, function (letter) {
      return '-' + letter.toLowerCase();
    });
    return element.getAttribute('data-' + dashed) || '';
  }

  function initRoot(root, options) {
    options = options || {};
    var hasStorageOverride = Object.prototype.hasOwnProperty.call(options, 'storage');
    var storage = hasStorageOverride ? options.storage : null;
    if (!hasStorageOverride) {
      try { storage = global.localStorage; } catch (_) { storage = null; }
    }
    var hasAnalyticsOverride = Object.prototype.hasOwnProperty.call(options, 'gtag');
    var analytics = options.gtag;
    var result = root.querySelector('[data-td-feedback-result]');
    var reasons = root.querySelector('[data-td-feedback-reasons]');
    var change = root.querySelector('[data-td-feedback-change]');
    var choices = Array.prototype.slice.call(
      root.querySelectorAll('[data-td-feedback-choice]'),
    );
    var reasonChoices = Array.prototype.slice.call(
      root.querySelectorAll('[data-td-feedback-reason]'),
    );
    var pagePath = data(root, 'tdPagePath') || '/';
    var language = data(root, 'tdLanguage') || 'en';
    var storageKey = 'td-feedback:v2:' + language + ':' + pagePath;
    var response = null;

    if (!result || !change || choices.length !== 2) return null;

    function stored(value) {
      if (!storage) return value === undefined ? null : value;
      try {
        if (value === null) {
          storage.removeItem(storageKey);
          return null;
        }
        if (value !== undefined) {
          storage.setItem(storageKey, JSON.stringify(value));
          return value;
        }
        var parsed = JSON.parse(storage.getItem(storageKey) || 'null');
        if (!parsed || (parsed.result !== 'solved' && parsed.result !== 'not_solved'))
          return null;
        var clean = { result: parsed.result };
        if (parsed.reason && reasonChoices.some(function (button) {
          return data(button, 'tdFeedbackReason') === parsed.reason;
        })) clean.reason = parsed.reason;
        return clean;
      } catch (_) {
        // Persistence is a convenience, not a submission gate. A blocked or
        // quota-exhausted storage backend must not leave the UI unsubmitted
        // after analytics has already counted the click.
        return value === undefined ? null : value;
      }
    }

    function track(eventName, parameters) {
      var sink = analytics;
      if (!hasAnalyticsOverride) {
        try { sink = global.gtag; } catch (_) { sink = null; }
      }
      if (typeof sink !== 'function') return;
      try { sink('event', eventName, parameters); } catch (_) {}
    }

    function render() {
      choices.forEach(function (button) {
        var active = response && data(button, 'tdFeedbackChoice') === response.result;
        button.setAttribute('aria-pressed', String(Boolean(active)));
        button.disabled = Boolean(response);
      });
      reasonChoices.forEach(function (button) {
        var active = response && data(button, 'tdFeedbackReason') === response.reason;
        button.setAttribute('aria-pressed', String(Boolean(active)));
        button.disabled = !response || response.result !== 'not_solved' || Boolean(response.reason);
      });
      result.hidden = !response;
      if (reasons) reasons.hidden = !response || response.result !== 'not_solved';
      root.classList.toggle('td-is-submitted', Boolean(response));
    }

    function choose(value) {
      if (response || (value !== 'solved' && value !== 'not_solved')) return false;
      response = stored({ result: value });
      track('docs_feedback', {
        result: value,
        page_path: pagePath,
        language: language,
      });
      render();
      if (value === 'not_solved' && reasons && typeof reasons.focus === 'function')
        reasons.focus();
      return true;
    }

    function chooseReason(value) {
      if (!response || response.result !== 'not_solved') return false;
      var valid = reasonChoices.some(function (button) {
        return data(button, 'tdFeedbackReason') === value;
      });
      if (!valid || response.reason) return false;
      response.reason = value;
      stored(response);
      track('docs_feedback', {
        result: response.result,
        reason: value,
        page_path: pagePath,
        language: language,
        refinement: true,
      });
      render();
      return true;
    }

    function reset() {
      stored(null);
      response = null;
      render();
      var first = choices[0];
      if (first && typeof first.focus === 'function') first.focus();
    }

    choices.forEach(function (button) {
      button.addEventListener('click', function () {
        choose(data(button, 'tdFeedbackChoice'));
      });
    });
    reasonChoices.forEach(function (button) {
      button.addEventListener('click', function () {
        chooseReason(data(button, 'tdFeedbackReason'));
      });
    });
    change.addEventListener('click', reset);

    response = stored();
    render();

    return Object.freeze({ choose: choose, chooseReason: chooseReason, reset: reset });
  }

  function init(options) {
    options = options || {};
    var doc = options.document || global.document;
    if (!doc || !doc.querySelectorAll) return [];
    return Array.prototype.map.call(
      doc.querySelectorAll('[data-td-feedback]'),
      function (root) { return initRoot(root, options); },
    ).filter(Boolean);
  }

  var api = { init: init, initRoot: initRoot };
  global.OinkFeedback = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (!global.__OINK_FEEDBACK_MANUAL_INIT__ && global.document) init();
})(typeof window === 'object' ? window : globalThis);
