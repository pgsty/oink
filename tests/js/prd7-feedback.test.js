'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const feedback = require(path.join(__dirname, '..', '..', 'assets/js/feedback.js'));

function classList() {
  const values = new Set();
  return {
    toggle(value, force) {
      if (force) values.add(value); else values.delete(value);
    },
    contains(value) { return values.has(value); },
  };
}

function control(attributes = {}) {
  const listeners = new Map();
  const values = new Map(Object.entries(attributes));
  return {
    dataset: {},
    classList: classList(),
    disabled: false,
    hidden: false,
    focused: false,
    addEventListener(name, callback) { listeners.set(name, callback); },
    dispatch(name, event = {}) { return listeners.get(name)(event); },
    setAttribute(name, value) { values.set(name, String(value)); },
    getAttribute(name) { return values.has(name) ? values.get(name) : null; },
    focus() { this.focused = true; },
  };
}

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); },
    values,
  };
}

function fixture(storage = memoryStorage(), gtag) {
  const solved = control({ 'data-td-feedback-choice': 'solved' });
  const notSolved = control({ 'data-td-feedback-choice': 'not_solved' });
  const missing = control({ 'data-td-feedback-reason': 'missing_info' });
  const outdated = control({ 'data-td-feedback-reason': 'outdated' });
  const failed = control({ 'data-td-feedback-reason': 'steps_failed' });
  const unclear = control({ 'data-td-feedback-reason': 'unclear' });
  const result = control();
  result.hidden = true;
  const reasons = control();
  reasons.hidden = true;
  const change = control();
  const root = control();
  root.dataset = { pagePath: '/zh/docs/start/', language: 'zh' };
  root.querySelector = (selector) => ({
    '[data-td-feedback-result]': result,
    '[data-td-feedback-reasons]': reasons,
    '[data-td-feedback-change]': change,
  }[selector] || null);
  root.querySelectorAll = (selector) => ({
    '[data-td-feedback-choice]': [solved, notSolved],
    '[data-td-feedback-reason]': [missing, outdated, failed, unclear],
  }[selector] || []);
  const options = { storage };
  if (arguments.length >= 2) options.gtag = gtag;
  const api = feedback.initRoot(root, options);
  return { api, root, solved, notSolved, missing, outdated, failed, unclear,
    result, reasons, change, storage };
}

test('a choice is recorded immediately without a server or free text', () => {
  const events = [];
  const page = fixture(memoryStorage(), (...args) => events.push(args));

  page.notSolved.dispatch('click');
  assert.equal(page.result.hidden, false);
  assert.equal(page.reasons.hidden, false);
  assert.equal(page.notSolved.getAttribute('aria-pressed'), 'true');
  assert.equal(page.solved.disabled, true);
  assert.equal(page.reasons.focused, true);
  assert.deepEqual(events, [[
    'event',
    'docs_feedback',
    { result: 'not_solved', page_path: '/zh/docs/start/', language: 'zh' },
  ]]);
  const stored = JSON.parse(page.storage.values.get(
    'oink-feedback-v2:zh:/zh/docs/start/',
  ));
  assert.deepEqual(stored, { result: 'not_solved' });
});

test('an optional reason refines the structured analytics event once', () => {
  const events = [];
  const page = fixture(memoryStorage(), (...args) => events.push(args));

  page.notSolved.dispatch('click');
  page.missing.dispatch('click');
  page.outdated.dispatch('click');
  assert.equal(page.missing.getAttribute('aria-pressed'), 'true');
  assert.equal(page.outdated.disabled, true, 'a saved reason cannot be double-counted');
  assert.equal(events.length, 2);
  assert.deepEqual(events[1], [
    'event',
    'docs_feedback',
    {
      result: 'not_solved',
      reason: 'missing_info',
      page_path: '/zh/docs/start/',
      language: 'zh',
      refinement: true,
    },
  ]);
});

test('saved feedback restores locally and can be changed', () => {
  const storage = memoryStorage({
    'oink-feedback-v2:zh:/zh/docs/start/': JSON.stringify({
      result: 'not_solved', reason: 'unclear',
    }),
  });
  const restored = fixture(storage);

  assert.equal(restored.result.hidden, false);
  assert.equal(restored.reasons.hidden, false);
  assert.equal(restored.unclear.getAttribute('aria-pressed'), 'true');
  restored.change.dispatch('click');
  assert.equal(restored.result.hidden, true);
  assert.equal(restored.solved.disabled, false);
  assert.equal(restored.solved.focused, true);
  assert.equal(storage.values.size, 0);
});

test('feedback still works when analytics or localStorage is unavailable', () => {
  const page = fixture(null, null);
  assert.equal(page.api.choose('solved'), true);
  assert.equal(page.result.hidden, false);
  assert.equal(page.api.chooseReason('missing_info'), false);
});

test('a failing storage backend cannot leave an already-counted choice open', () => {
  const events = [];
  const storage = {
    getItem() { throw new Error('blocked'); },
    setItem() { throw new Error('quota'); },
    removeItem() { throw new Error('blocked'); },
  };
  const page = fixture(storage, (...args) => events.push(args));

  page.solved.dispatch('click');
  page.solved.dispatch('click');
  assert.equal(page.result.hidden, false);
  assert.equal(page.solved.getAttribute('aria-pressed'), 'true');
  assert.equal(events.length, 1, 'the failed write must not allow a duplicate event');
});

test('analytics may become available after the feedback runtime initializes', () => {
  const events = [];
  const page = fixture(memoryStorage());
  globalThis.gtag = (...args) => events.push(args);
  try {
    page.solved.dispatch('click');
    assert.equal(events[0][1], 'docs_feedback');
  } finally {
    delete globalThis.gtag;
  }
});
