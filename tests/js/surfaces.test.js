'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

function load(relative) {
  const target = path.join(__dirname, '..', '..', relative);
  delete require.cache[require.resolve(target)];
  require(target);
}

function testCoordinatorCompatibility() {
  global.window = {};
  load('assets/js/surface-coordinator.js');
  const coordinator = window.OinkSurfaceCoordinator;
  const calls = [];

  const unregisterDrawer = coordinator.register('drawer', (restore) => {
    calls.push(['drawer', restore]);
  });
  coordinator.register('root-menu', (restore) => {
    calls.push(['root-menu', restore]);
  });
  coordinator.register('palette', (restore) => {
    calls.push(['palette', restore]);
  });

  coordinator.closeOthers('root-menu', ['drawer']);
  assert.deepEqual(calls, [['palette', false]]);

  calls.length = 0;
  coordinator.closeOthers('palette');
  assert.deepEqual(calls, [
    ['drawer', false],
    ['root-menu', false],
  ]);

  calls.length = 0;
  unregisterDrawer();
  coordinator.closeAll(true);
  assert.deepEqual(calls, [
    ['root-menu', true],
    ['palette', true],
  ]);
}

function classList() {
  const values = new Set();
  return {
    add(value) {
      values.add(value);
    },
    remove(value) {
      values.delete(value);
    },
    contains(value) {
      return values.has(value);
    },
    toggle(value, force) {
      if (force === true) values.add(value);
      else if (force === false) values.delete(value);
      else if (values.has(value)) values.delete(value);
      else values.add(value);
      return values.has(value);
    },
  };
}

function element(overrides = {}) {
  const attributes = new Map();
  const listeners = new Map();
  return Object.assign(
    {
      classList: classList(),
      dataset: {},
      offsetParent: {},
      textContent: '',
      hidden: false,
      addEventListener(type, callback) {
        const callbacks = listeners.get(type) || [];
        callbacks.push(callback);
        listeners.set(type, callbacks);
      },
      appendChild() {},
      contains(candidate) {
        return candidate === this;
      },
      dispatch(type, event = {}) {
        (listeners.get(type) || []).forEach((callback) => callback(event));
      },
      focus() {
        global.document.activeElement = this;
      },
      getAttribute(name) {
        return attributes.get(name) || null;
      },
      hasAttribute(name) {
        return attributes.has(name);
      },
      querySelector() {
        return null;
      },
      querySelectorAll() {
        return [];
      },
      removeAttribute(name) {
        attributes.delete(name);
      },
      select() {},
      setAttribute(name, value) {
        attributes.set(name, String(value));
      },
    },
    overrides,
  );
}

function keyboardEvent(key) {
  return {
    key,
    defaultPrevented: false,
    preventDefault() {
      this.defaultPrevented = true;
    },
  };
}

function testNavbarHoverPanel() {
  const documentListeners = new Map();
  const first = element();
  const second = element();
  const panel = element({
    hidden: true,
    querySelectorAll() {
      return [first, second];
    },
  });
  const parent = element();
  const menu = element({
    contains(candidate) {
      return candidate === parent || candidate === panel;
    },
    querySelector(selector) {
      return {
        '.td-nav-menu__parent-link': parent,
        '[data-td-navbar-panel]': panel,
      }[selector];
    },
  });
  const registered = new Map();
  const coordinated = [];
  global.document = {
    activeElement: null,
    addEventListener(type, callback) {
      const callbacks = documentListeners.get(type) || [];
      callbacks.push(callback);
      documentListeners.set(type, callbacks);
    },
    querySelector() {
      return null;
    },
    querySelectorAll(selector) {
      return selector === '[data-td-navbar-menu]' ? [menu] : [];
    },
  };
  global.window = {
    requestAnimationFrame(callback) {
      callback();
    },
    // Immediate timers: closeSoon's grace period collapses to a direct close.
    setTimeout(callback) {
      callback();
      return 1;
    },
    clearTimeout() {},
    OinkSurfaceCoordinator: {
      closeOthers(name) {
        coordinated.push(name);
      },
      register(name, close) {
        registered.set(name, close);
      },
    },
  };

  load('assets/js/navbar-menu.js');

  // Touch hover must not open: touch users navigate via the parent link.
  menu.dispatch('pointerenter', { pointerType: 'touch' });
  assert.equal(panel.hidden, true);

  parent.dispatch('focus');
  assert.equal(panel.hidden, false);
  assert.equal(parent.getAttribute('aria-expanded'), 'true');
  registered.get('navbar-menu-0')(false);
  coordinated.length = 0;

  menu.dispatch('pointerenter', { pointerType: 'mouse' });
  assert.equal(panel.hidden, false);
  assert.equal(parent.getAttribute('aria-expanded'), 'true');
  assert.deepEqual(coordinated, ['navbar-menu-0']);

  menu.dispatch('pointerleave', { pointerType: 'mouse' });
  assert.equal(panel.hidden, true);

  const down = keyboardEvent('ArrowDown');
  parent.dispatch('keydown', down);
  assert.equal(down.defaultPrevented, true);
  assert.equal(panel.hidden, false);
  assert.equal(document.activeElement, first);

  const next = keyboardEvent('ArrowDown');
  panel.dispatch('keydown', next);
  assert.equal(document.activeElement, second);

  const escape = keyboardEvent('Escape');
  panel.dispatch('keydown', escape);
  assert.equal(panel.hidden, true);
  assert.equal(document.activeElement, parent);
  assert.equal(parent.getAttribute('aria-expanded'), 'false');

  menu.dispatch('pointerenter', { pointerType: 'mouse' });
  (documentListeners.get('pointerdown') || [])[0]({ target: element() });
  assert.equal(panel.hidden, true);
  menu.dispatch('pointerenter', { pointerType: 'mouse' });
  registered.get('navbar-menu-0')(false);
  assert.equal(panel.hidden, true);
}

function testPaletteFocusFromDrawer() {
  const documentListeners = new Map();
  const htmlAttributes = new Set(['data-td-shell-drawer']);
  const html = element({
    hasAttribute(name) {
      return htmlAttributes.has(name);
    },
    removeAttribute(name) {
      htmlAttributes.delete(name);
    },
    setAttribute(name) {
      htmlAttributes.add(name);
    },
  });
  const externalDrawerOpener = element();
  const internalPaletteOpener = element({
    closest(selector) {
      return selector === '#td-shell-sidebar' ? element() : null;
    },
  });
  const input = element();
  const list = element();
  const panel = element();
  const status = element();
  const root = element({
    dataset: {
      indexSrc: '/search.json',
      maxResults: '10',
      tLoading: 'Loading',
      tEmpty: 'Empty',
    },
    hidden: true,
    contains(candidate) {
      return candidate === input || candidate === panel || candidate === list;
    },
    querySelector(selector) {
      return {
        '.td-shell-search__input': input,
        '.td-shell-search__list': list,
        '.td-shell-search__panel': panel,
        '[data-td-shell-search-status]': status,
      }[selector];
    },
  });

  global.document = {
    activeElement: internalPaletteOpener,
    documentElement: html,
    addEventListener(type, callback) {
      const callbacks = documentListeners.get(type) || [];
      callbacks.push(callback);
      documentListeners.set(type, callbacks);
    },
    createElement() {
      return element();
    },
    getElementById(id) {
      return id === 'td-shell-search' ? root : null;
    },
    querySelectorAll(selector) {
      if (selector === '[data-td-shell-search-open]')
        return [internalPaletteOpener];
      if (selector === '[data-td-shell-drawer-open]')
        return [externalDrawerOpener];
      return [];
    },
  };
  Object.defineProperty(global, 'navigator', {
    configurable: true,
    value: { platform: 'MacIntel', userAgent: '' },
  });
  global.fetch = () => new Promise(() => {});
  global.window = {
    clearTimeout() {},
    requestAnimationFrame(callback) {
      callback();
    },
    setTimeout() {
      return 1;
    },
    OinkActions: {
      commands() { return []; },
      get() { return null; },
      list() { return []; },
      quickLinks() { return []; },
      rootOrder() { return []; },
      safeUrl(value) { return value; },
    },
    OinkPaletteModel: {
      emptyGroups() { return []; },
      commandGroups() { return []; },
      actionRows() { return []; },
      choiceGroup() { return []; },
      lexical(a, b) { return String(a).localeCompare(String(b)); },
    },
    OinkSearchEngine: {
      create() { return { query() { return []; } }; },
      group() { return []; },
    },
    OinkSurfaceCoordinator: {
      closeOthers(name) {
        assert.equal(name, 'palette');
        html.removeAttribute('data-td-shell-drawer');
      },
      register(name, close) {
        assert.equal(name, 'palette');
        this.paletteClose = close;
      },
    },
  };

  load('assets/js/command-palette.js');
  internalPaletteOpener.dispatch('click', {
    currentTarget: internalPaletteOpener,
  });
  assert.equal(document.activeElement, input);
  assert.equal(html.hasAttribute('data-td-shell-drawer'), false);

  const escape = (documentListeners.get('keydown') || []).find((callback) => {
    document.activeElement = input;
    callback({ key: 'Escape', preventDefault() {} });
    return document.activeElement === externalDrawerOpener;
  });
  assert.ok(escape, 'Escape must restore focus to the visible drawer opener');
}

function testHoverTriggerClickAfterFocus() {
  const trigger = element();
  trigger.setAttribute('data-td-nav-hover-open', '');
  const menu = element({
    closest() { return null; },
    querySelector(selector) {
      return selector === '[data-td-nav-hover-trigger], .td-nav-util'
        ? trigger : null;
    },
  });
  global.document = {
    querySelector() { return null; },
    querySelectorAll(selector) {
      return selector === '[data-td-nav-hover]' ? [menu] : [];
    },
  };
  global.window = {
    addEventListener() {},
    clearTimeout() {},
    setTimeout(callback) { callback(); return 1; },
  };

  load('assets/js/base.js');

  // Browser click order is pointerdown, focusin, then click. That first click must not
  // undo the open performed by focusin.
  trigger.dispatch('pointerdown', { pointerType: 'mouse' });
  menu.dispatch('focusin');
  trigger.dispatch('click');
  assert.equal(menu.classList.contains('td-is-open'), true);
  assert.equal(trigger.getAttribute('aria-expanded'), 'true');

  trigger.dispatch('pointerdown', { pointerType: 'mouse' });
  trigger.dispatch('click');
  assert.equal(menu.classList.contains('td-is-open'), false, 'a second mouse click closes the disclosure');

  menu.dispatch('focusin');
  trigger.dispatch('click');
  assert.equal(menu.classList.contains('td-is-open'), true, 'first keyboard activation remains open after focusin');
  trigger.dispatch('click');
  assert.equal(menu.classList.contains('td-is-open'), false, 'second keyboard activation closes the disclosure');

  // Touch keeps normal toggle semantics: first tap opens, second tap closes.
  trigger.dispatch('pointerdown', { pointerType: 'touch' });
  menu.dispatch('focusin');
  trigger.dispatch('click');
  assert.equal(menu.classList.contains('td-is-open'), true);
  trigger.dispatch('pointerdown', { pointerType: 'touch' });
  trigger.dispatch('click');
  assert.equal(menu.classList.contains('td-is-open'), false);
}

function testBootstrapVersionTriggerAfterFocus() {
  const trigger = element();
  const menu = element({
    closest() { return null; },
    querySelector(selector) {
      return selector === '[data-bs-toggle="dropdown"]' ? trigger : null;
    },
  });
  const dropdown = {
    show() { trigger.setAttribute('aria-expanded', 'true'); },
    hide() { trigger.setAttribute('aria-expanded', 'false'); },
  };
  global.document = {
    querySelector() { return null; },
    querySelectorAll(selector) {
      return selector === '[data-td-version-menu]' ? [menu] : [];
    },
  };
  global.bootstrap = {
    Dropdown: { getOrCreateInstance() { return dropdown; } },
  };
  global.window = {
    bootstrap: global.bootstrap,
    addEventListener() {},
    clearTimeout() {},
    setTimeout(callback) { callback(); return 1; },
  };

  load('assets/js/base.js');

  const activation = () => ({
    defaultPrevented: false,
    propagationStopped: false,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() { this.propagationStopped = true; },
  });

  trigger.dispatch('pointerdown', { pointerType: 'touch' });
  menu.dispatch('focusin');
  const first = activation();
  trigger.dispatch('click', first);
  assert.equal(trigger.getAttribute('aria-expanded'), 'true', 'first touch activation remains open');
  assert.equal(first.defaultPrevented, true);
  assert.equal(first.propagationStopped, true, 'Bootstrap delegated click must not toggle it closed');

  trigger.dispatch('pointerdown', { pointerType: 'touch' });
  trigger.dispatch('click', activation());
  assert.equal(trigger.getAttribute('aria-expanded'), 'false', 'second touch activation closes');

  menu.dispatch('focusin');
  trigger.dispatch('click', activation());
  assert.equal(trigger.getAttribute('aria-expanded'), 'true', 'first keyboard activation remains open after focusin');
  trigger.dispatch('click', activation());
  assert.equal(trigger.getAttribute('aria-expanded'), 'false', 'second keyboard activation closes the focused menu');
}

testCoordinatorCompatibility();
testPaletteFocusFromDrawer();
testNavbarHoverPanel();
testHoverTriggerClickAfterFocus();
testBootstrapVersionTriggerAfterFocus();
console.log('surface behavior checks passed');
