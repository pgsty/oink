'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('appearance registers switch_preset once across DOMContentLoaded and falls back to manifest options when chrome is suppressed', () => {
  const attributes = new Map([
    ['data-td-site-preset', 'paper'],
    ['data-td-preset', 'paper'],
  ]);
  const storage = new Map();
  const docListeners = new Map();
  let registered = 0;
  let executor = null;

  const fakeDocument = {
    readyState: 'loading',
    documentElement: {
      getAttribute(name) { return attributes.get(name) || null; },
      setAttribute(name, value) { attributes.set(name, String(value)); },
      removeAttribute(name) { attributes.delete(name); },
      hasAttribute(name) { return attributes.has(name); },
      toggleAttribute(name, force) {
        if (force) attributes.set(name, '');
        else attributes.delete(name);
      },
    },
    addEventListener(name, cb) { docListeners.set(name, cb); },
    querySelectorAll() { return []; },
    getElementById() { return null; },
  };

  const fakeWindow = {
    scrollY: 0,
    localStorage: {
      getItem(k) { return storage.get(k) || null; },
      setItem(k, v) { storage.set(k, String(v)); },
      removeItem(k) { storage.delete(k); },
    },
    addEventListener() {},
    requestAnimationFrame(cb) { cb(); },
    dispatchEvent() {},
    OinkActions: {
      get(id) {
        return id === 'switch_preset'
          ? { id, options: [{ value: 'paper' }, { value: 'slate' }, { value: 'ink' }] }
          : null;
      },
      registerExecutor(id, fn) {
        assert.equal(id, 'switch_preset');
        registered += 1;
        if (registered > 1) throw new Error('duplicate switch_preset registration');
        executor = fn;
      },
    },
  };

  const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'assets/js/appearance.js'),
    'utf8',
  );
  vm.runInNewContext(source, {
    window: fakeWindow,
    document: fakeDocument,
    CustomEvent: function CustomEvent(type, init) {
      this.type = type;
      this.detail = init && init.detail;
    },
    Promise,
    Error,
  });

  assert.equal(registered, 1);
  assert.equal(typeof docListeners.get('DOMContentLoaded'), 'function');
  docListeners.get('DOMContentLoaded')();
  assert.equal(registered, 1);

  assert.deepEqual(Array.from(fakeWindow.OinkAppearance.offered()), ['paper', 'slate', 'ink']);
  const result = executor({ value: 'ink' });
  assert.deepEqual({ preset: result.preset }, { preset: 'ink' });
  assert.equal(attributes.get('data-td-preset'), 'ink');
  assert.equal(storage.get('td-preset'), 'ink');
});

test('appearance syncs and activates in-page [data-td-preset-select] buttons without polluting offered()', () => {
  const attributes = new Map([
    ['data-td-site-preset', 'paper'],
    ['data-td-preset', 'terminal'],
  ]);
  const storage = new Map([['td-preset', 'terminal']]);
  let scrolledBy = null;

  function makeRadio(name) {
    return {
      checked: false,
      getAttribute(k) {
        if (k === 'data-td-preset-value') return name;
        if (k === 'data-td-canvas-light') return '#ffffff';
        if (k === 'data-td-canvas-dark') return '#000000';
        return null;
      },
      addEventListener() {},
    };
  }

  function makeButton(name) {
    const attrs = new Map([
      ['data-td-preset-select', name],
      ['aria-pressed', name === 'paper' ? 'true' : 'false'],
    ]);
    const handlers = new Map();
    let top = 240;
    return {
      isConnected: true,
      getAttribute(k) { return attrs.get(k) || null; },
      setAttribute(k, v) { attrs.set(k, String(v)); },
      addEventListener(type, fn) { handlers.set(type, fn); },
      getBoundingClientRect() { return { top, height: 72 }; },
      setTop(v) { top = v; },
      click() { handlers.get('click')(); },
    };
  }

  const radios = [makeRadio('paper'), makeRadio('slate'), makeRadio('terminal')];
  // Ink has a tile but no radio: a page tile never widens what the menu offers.
  const buttons = [makeButton('paper'), makeButton('slate'), makeButton('terminal'), makeButton('ink')];

  const fakeDocument = {
    readyState: 'complete',
    documentElement: {
      getAttribute(name) { return attributes.get(name) || null; },
      setAttribute(name, value) { attributes.set(name, String(value)); },
      removeAttribute(name) { attributes.delete(name); },
      hasAttribute(name) { return attributes.has(name); },
      toggleAttribute(name, force) {
        if (force) attributes.set(name, '');
        else attributes.delete(name);
      },
    },
    querySelectorAll(sel) {
      if (sel === '[data-td-preset-value]') return radios;
      if (sel === '[data-td-preset-select]') return buttons;
      return [];
    },
    getElementById() { return null; },
  };

  const fakeWindow = {
    scrollY: 400,
    scrollBy(opts) { scrolledBy = opts; },
    localStorage: {
      getItem(k) { return storage.get(k) || null; },
      setItem(k, v) { storage.set(k, String(v)); },
      removeItem(k) { storage.delete(k); },
    },
    addEventListener() {},
    requestAnimationFrame(cb) { cb(); },
    dispatchEvent() {},
  };

  const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'assets/js/appearance.js'),
    'utf8',
  );
  vm.runInNewContext(source, {
    window: fakeWindow,
    document: fakeDocument,
    CustomEvent: function CustomEvent(type, init) {
      this.type = type;
      this.detail = init && init.detail;
    },
    Promise,
    Error,
  });

  // Initial sync follows the root's terminal preset rather than the server's
  // pressed default, Paper.
  assert.deepEqual(Array.from(fakeWindow.OinkAppearance.offered()), ['paper', 'slate', 'terminal']);
  assert.equal(buttons[0].getAttribute('aria-pressed'), 'false');
  assert.equal(buttons[2].getAttribute('aria-pressed'), 'true');
  assert.equal(buttons[3].getAttribute('aria-pressed'), 'false');
  assert.equal(radios[2].checked, true);

  // Clicking Slate switches preset, syncs radios & buttons, persists, and anchors the clicked tile.
  const origSetAttribute = fakeDocument.documentElement.setAttribute;
  fakeDocument.documentElement.setAttribute = (name, value) => {
    origSetAttribute(name, value);
    if (name === 'data-td-preset' && value === 'slate') buttons[1].setTop(268);
  };
  buttons[1].click();
  assert.equal(attributes.get('data-td-preset'), 'slate');
  assert.equal(storage.get('td-preset'), 'slate');
  assert.equal(buttons[1].getAttribute('aria-pressed'), 'true');
  assert.equal(buttons[2].getAttribute('aria-pressed'), 'false');
  assert.equal(radios[1].checked, true);
  assert.deepEqual({ ...scrolledBy }, { top: 28, left: 0, behavior: 'instant' });

  // A tile for a preset the menu does not offer falls back to the site's.
  buttons[3].click();
  assert.equal(attributes.get('data-td-preset'), 'paper');
  assert.equal(buttons[3].getAttribute('aria-pressed'), 'false');
  assert.equal(buttons[0].getAttribute('aria-pressed'), 'true');
});
