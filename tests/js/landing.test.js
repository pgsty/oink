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

const pendingReveal = element();
let revealEntries;
const observed = [];
landing.initReveal({ querySelectorAll() { return [pendingReveal]; } }, {
  matchMedia() { return { matches: false }; },
  IntersectionObserver: class {
    constructor(callback) { revealEntries = callback; }
    observe(target) { observed.push(target); }
    unobserve(target) { observed.splice(observed.indexOf(target), 1); }
  },
});
assert.equal(pendingReveal.hasAttribute('data-td-reveal-pending'), true);
assert.deepEqual(observed, [pendingReveal]);
revealEntries([{ target: pendingReveal, isIntersecting: true }]);
assert.equal(pendingReveal.hasAttribute('data-td-reveal-pending'), false);
assert.equal(pendingReveal.hasAttribute('data-td-revealed'), true);
assert.deepEqual(observed, []);

const count = element({ 'data-td-count': '2189', 'data-td-count-suffix': '+' });
assert.equal(landing.initCounts(
  { querySelectorAll() { return [count]; } },
  { matchMedia() { return { matches: true }; } },
), 1);
assert.match(count.textContent, /^2[,\s.]?189\+$/);
assert.equal(count.hasAttribute('data-td-count-complete'), true);

for (const [value, display] of [['2189', '2.2k'], ['32', '32+'], ['12.50', '$12.50/day']]) {
  const formatted = element({ 'data-td-count': value, 'data-td-count-display': display });
  formatted.textContent = 'intermediate animation value';
  assert.equal(landing.terminalCount(formatted), true);
  assert.equal(formatted.textContent, display, 'terminal count changed the server-authored display');
}

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

  // Download channels switch without a tab library: a click or an arrow key
  // moves the selection, and an unpublished channel is never selected.
  const panels = new Map();
  const events = [];
  const channel = (id, state = {}) => {
    const tab = element({ 'aria-controls': id, 'aria-selected': 'false' });
    tab.id = id + '-tab';
    tab.disabled = Boolean(state.disabled);
    const panel = element();
    panel.hidden = false;
    panel.dispatchEvent = event => events.push([id, event.type, event.bubbles]);
    panels.set(id, panel);
    return tab;
  };
  const script = channel('script');
  const candidate = channel('candidate', { disabled: true });
  const source = channel('source');
  const pending = channel('pending', { disabled: true });
  function product(tabs) {
    const list = { children: tabs, hidden: true, direction: 'ltr' };
    const set = {
      querySelector: selector => selector === ':scope > [role="tablist"]' ? list : null,
      querySelectorAll: selector => selector === ':scope > .tab-content > .tab-pane'
        ? tabs.map(tab => panels.get(tab.getAttribute('aria-controls'))) : [],
    };
    return { set, list };
  }
  const demo = product([script, candidate, source]);
  const unpublished = product([pending]);
  const tabsRoot = {
    querySelector() { return null; },
    querySelectorAll: selector => selector === '[data-td-download-tabs]' ? [demo.set, unpublished.set] : [],
  };
  const tabsDoc = { documentElement: element(), defaultView: { getComputedStyle: list => list } };
  const shown = () => ['script', 'candidate', 'source'].filter(id => !panels.get(id).hidden);
  const key = (name) => ({ key: name, prevented: false, preventDefault() { this.prevented = true; } });

  landing.init(tabsRoot, {}, tabsDoc, {});
  assert.equal(demo.list.hidden, false);
  assert.equal(unpublished.list.hidden, true);
  assert.equal(panels.get('pending').hidden, false);
  assert.deepEqual([script, candidate, source].map((tab) => tab.getAttribute('tabindex')), ['0', '-1', '-1']);
  assert.deepEqual(shown(), ['script']);

  source.dispatch('click');
  assert.deepEqual(shown(), ['source']);
  assert.deepEqual(events, [['source', 'td:tab-shown', true]]);
  assert.equal(source.getAttribute('aria-selected'), 'true');
  assert.equal(script.getAttribute('aria-selected'), 'false');
  assert.equal(script.classList.contains('active'), false);
  assert.equal(source.focused, undefined, 'a click must not move focus by script');

  const right = key('ArrowRight');
  source.dispatch('keydown', right);
  assert.equal(right.prevented, true);
  assert.deepEqual(shown(), ['script'], 'the arrow wraps past the unpublished channel');
  assert.equal(script.focused, true);
  script.dispatch('keydown', key('End'));
  assert.deepEqual(shown(), ['source']);
  source.dispatch('keydown', key('Home'));
  assert.deepEqual(shown(), ['script']);
  demo.list.direction = 'rtl';
  script.dispatch('keydown', key('ArrowLeft'));
  assert.deepEqual(shown(), ['source'], 'right-to-left pages mirror the arrows');
  const other = key('a');
  source.dispatch('keydown', other);
  assert.equal(other.prevented, false);
  candidate.dispatch('click');
  assert.deepEqual(shown(), ['source'], 'an unpublished channel has no listener to select it');
  assert.equal(candidate.getAttribute('tabindex'), '-1');

  console.log('landing runtime checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
