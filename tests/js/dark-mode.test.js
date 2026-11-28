'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function classes() {
  const values = new Set();
  return {
    toggle(name, force) { if (force) values.add(name); else values.delete(name); },
    has(name) { return values.has(name); },
  };
}

(() => {
  const storage = new Map();
  const attributes = new Map([['data-td-theme-init', '']]);
  const callbacks = new Map();
  const icon = () => ({
    hidden: false, classList: classes(),
    toggleAttribute(name, value) { assert.equal(name, 'hidden'); this.hidden = value; },
  });
  const themeControl = (paired = true) => ({
    moon: paired ? icon() : null, sun: paired ? icon() : null, legacy: paired ? null : icon(),
    attributes: new Map(), listeners: new Map(),
    setAttribute(name, value) { this.attributes.set(name, value); },
    addEventListener(name, callback) { this.listeners.set(name, callback); },
    querySelector(selector) {
      return selector === '.td-shell-icon--moon' ? this.moon
        : selector === '.td-shell-icon--sun' ? this.sun : this.legacy || this.moon;
    },
  });
  // The Appearance trigger shows the stored choice through the root's
  // `data-td-color-mode`, which its CSS keys on; theme toggles show the
  // resolved mode on their own icons.
  const toggles = [themeControl(), themeControl(false)];
  const assertModeIcons = (dark, choice) => {
    assert.equal(attributes.get('data-td-color-mode'), choice);
    assert.equal(toggles[0].moon.hidden, !dark);
    assert.equal(toggles[0].sun.hidden, dark);
    assert.equal(toggles[0].attributes.get('aria-pressed'), String(dark));
    assert.equal(toggles[1].legacy.classList.has('fa-moon'), dark);
    assert.equal(toggles[1].legacy.classList.has('fa-sun'), !dark);
    assert.equal(toggles[0].moon.classList.has('fa-sun'), false);
  };
  const light = {
    attributes: new Map([['data-bs-theme-value', 'light']]),
    classList: classes(), listeners: new Map(),
    getAttribute(name) { return this.attributes.get(name); },
    setAttribute(name, value) { this.attributes.set(name, value); },
    addEventListener(name, callback) { this.listeners.set(name, callback); },
  };
  let registryExecutor = null;
  // Swagger UI keys its dark theme on `html.dark-mode` and DocSearch on
  // `html[data-theme]`; the runtime mirrors the resolved mode onto both, so the
  // root stub has to carry a class list for that mirror to land on.
  const rootClasses = classes();
  const fakeDocument = {
    documentElement: {
      classList: rootClasses,
      setAttribute(name, value) { attributes.set(name, value); },
      getAttribute(name) { return attributes.get(name); },
      removeAttribute(name) { attributes.delete(name); },
      hasAttribute(name) { return attributes.has(name); },
      toggleAttribute(name, force) { if (force) attributes.set(name, ''); else attributes.delete(name); },
    },
    querySelectorAll(selector) {
      if (selector === '[data-bs-theme-value]') return [light];
      if (selector === '[data-td-theme-toggle]') return toggles;
      return [];
    },
  };
  const media = {
    matches: false,
    addEventListener(name, callback) { callbacks.set(`media:${name}`, callback); },
  };
  const fakeWindow = {
    matchMedia() { return media; },
    addEventListener(name, callback) { callbacks.set(name, callback); },
    OinkActions: {
      get(id) { return id === 'switch_theme' ? { id } : null; },
      registerExecutor(id, executor) {
        assert.equal(id, 'switch_theme');
        registryExecutor = executor;
      },
    },
  };
  const fakeStorage = {
    getItem(key) { return storage.get(key) || null; },
    setItem(key, value) { storage.set(key, value); },
  };
  const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'assets/js/dark-mode.js'),
    'utf8',
  );
  vm.runInNewContext(source, {
    window: fakeWindow,
    document: fakeDocument,
    localStorage: fakeStorage,
    Promise,
  });

  assert.equal(attributes.get('data-bs-theme'), 'light');
  assert.equal(rootClasses.has('dark-mode'), false);
  assert.equal(attributes.get('data-theme'), 'light');
  assert.equal(attributes.has('data-td-theme-init'), false);
  assert.equal(typeof registryExecutor, 'function');
  callbacks.get('DOMContentLoaded')();
  assertModeIcons(false, 'auto');
  light.listeners.get('click')();
  assert.equal(storage.get('td-color-theme'), 'light');
  assert.equal(attributes.get('data-bs-theme'), 'light');
  assert.equal(light.attributes.get('aria-pressed'), 'true');
  assert.equal(light.classList.has('td-is-active'), true);

  registryExecutor({ value: { value: 'dark' } });
  assert.equal(storage.get('td-color-theme'), 'dark');
  assert.equal(attributes.get('data-bs-theme'), 'dark');
  assert.equal(rootClasses.has('dark-mode'), true);
  assert.equal(attributes.get('data-theme'), 'dark');
  assert.equal(light.attributes.get('aria-pressed'), 'false');
  assertModeIcons(true, 'dark');

  storage.set('td-color-theme', 'auto');
  callbacks.get('storage')({ key: 'td-color-theme' });
  assertModeIcons(false, 'auto');
  media.matches = true;
  callbacks.get('media:change')();
  assert.equal(attributes.get('data-bs-theme'), 'dark');
  assert.equal(rootClasses.has('dark-mode'), true);
  assert.equal(attributes.get('data-theme'), 'dark');
  // Following the system, the trigger keeps the system circle in both modes.
  assertModeIcons(true, 'auto');
  media.matches = false;
  callbacks.get('media:change')();
  assertModeIcons(false, 'auto');
  toggles[0].listeners.get('click')();
  assert.equal(attributes.get('data-bs-theme'), 'dark');
  assertModeIcons(true, 'dark');

  console.log('shared theme executor checks passed');
})();
