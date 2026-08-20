'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

require(path.join(__dirname, '..', '..', 'assets/js/clipboard.js'));
const landing = require(path.join(__dirname, '..', '..', 'assets/js/landing.js'));

function classes() {
  const values = new Set();
  return {
    add(...items) { items.forEach((item) => values.add(item)); },
    remove(...items) { items.forEach((item) => values.delete(item)); },
    toggle(item, enabled) { if (enabled) values.add(item); else values.delete(item); },
    contains(item) { return values.has(item); },
  };
}

function element(attributes = {}) {
  const values = new Map(Object.entries(attributes));
  const listeners = new Map();
  return {
    classList: classes(),
    textContent: '',
    hidden: true,
    style: {},
    setAttribute(name, value) { values.set(name, String(value)); },
    getAttribute(name) { return values.has(name) ? values.get(name) : null; },
    hasAttribute(name) { return values.has(name); },
    removeAttribute(name) { values.delete(name); },
    addEventListener(name, callback) { listeners.set(name, callback); },
    dispatch(name, event = {}) { listeners.get(name)?.(event); },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    focus() { this.focused = true; },
  };
}

const reveal = element();
assert.equal(landing.initReveal(
  { querySelectorAll() { return [reveal]; } },
  { matchMedia() { return { matches: true }; } },
), 1);
assert.equal(reveal.classList.contains('td-is-revealed'), true);
assert.equal(reveal.hasAttribute('data-td-revealed'), true);

const count = element({ 'data-td-count': '2189', 'data-td-count-suffix': '+' });
assert.equal(landing.initCounts(
  { querySelectorAll() { return [count]; } },
  { matchMedia() { return { matches: true }; } },
), 1);
assert.match(count.textContent, /^2[,\s.]?189\+$/);
assert.equal(count.hasAttribute('data-td-count-complete'), true);

(async () => {
  const writes = [];
  const timers = [];
  const button = element({
    'data-td-copy-text': 'curl https://example.test/install | bash',
    'data-td-label-copied': 'Copied!',
    'aria-label': 'Copy',
  });
  const root = { querySelectorAll(selector) { return selector === '[data-td-copy-text]' ? [button] : []; } };
  assert.equal(landing.initCopy(root, { setTimeout(callback) { timers.push(callback); } }, {}, {
    clipboard: { writeText(text) { writes.push(text); return Promise.resolve(); } },
  }), 1);
  button.dispatch('click');
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(writes, ['curl https://example.test/install | bash']);
  assert.equal(button.getAttribute('data-td-copy-state'), 'success');
  assert.equal(button.getAttribute('aria-label'), 'Copied!');
  timers[0]();
  assert.equal(button.getAttribute('aria-label'), 'Copy');

  const lightDark = element({
    src: '/light.png',
    'data-td-theme-src-light': '/light.png',
    'data-td-theme-src-dark': '/dark.png',
  });
  const doc = { documentElement: element({ 'data-bs-theme': 'dark' }) };
  assert.equal(landing.syncThemeImages({ querySelectorAll() { return [lightDark]; } }, doc), 1);
  assert.equal(lightDark.getAttribute('src'), '/dark.png');

  const toggle = element({ 'aria-expanded': 'false' });
  const menuLink = element();
  const menu = element();
  menu.querySelectorAll = () => [menuLink];
  const docListeners = new Map();
  const menuRoot = {
    querySelector(selector) {
      if (selector === '[data-td-landing-menu-toggle]') return toggle;
      if (selector === '[data-td-landing-menu]') return menu;
      return null;
    },
  };
  const coordinatorCalls = [];
  let registeredClose = null;
  const win = {
    OinkSurfaceCoordinator: {
      register(name, close) { coordinatorCalls.push(['register', name]); registeredClose = close; },
      closeOthers(name) { coordinatorCalls.push(['closeOthers', name]); },
    },
  };
  const menuDoc = { addEventListener(name, callback) { docListeners.set(name, callback); } };
  assert.equal(landing.initMobileMenu(menuRoot, win, menuDoc), true);
  toggle.dispatch('click');
  assert.equal(menu.hidden, false);
  assert.deepEqual(coordinatorCalls, [['register', 'mobile-menu'], ['closeOthers', 'mobile-menu']]);
  registeredClose(false);
  assert.equal(menu.hidden, true);
  toggle.dispatch('click');
  docListeners.get('keydown')({ key: 'Escape' });
  assert.equal(toggle.focused, true);

  console.log('landing runtime checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
