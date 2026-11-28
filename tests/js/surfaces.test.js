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

function testRestoreFocusKeepsHoverMenuClosed() {
  // Focus a closing surface puts back on a hover-menu trigger (the footer "?"
  // after the palette closes) must not raise that menu: base.js opens it on
  // focusin unless data-td-suppress-focus-open is present at that moment.
  const timers = [];
  global.window = {
    requestAnimationFrame(callback) { timers.push(callback); },
    setTimeout(callback) { timers.push(callback); },
  };
  load('assets/js/surface-coordinator.js');
  const attributes = new Map();
  const host = {
    setAttribute(name, value) { attributes.set(name, value); },
    removeAttribute(name) { attributes.delete(name); },
  };
  const seenDuringFocus = [];
  const trigger = {
    closest(selector) { return selector === '[data-td-nav-hover]' ? host : null; },
    focus(options) {
      seenDuringFocus.push([attributes.has('data-td-suppress-focus-open'), options]);
    },
  };
  window.OinkSurfaceCoordinator.restoreFocus(trigger, { preventScroll: true });
  assert.deepEqual(seenDuringFocus, [[true, { preventScroll: true }]]);
  assert.equal(attributes.has('data-td-suppress-focus-open'), false, 'focus suppression outlived the focus call');
  assert.equal(attributes.has('data-td-suppress-hover-open'), true, 'hover stays suppressed until the overlay is gone');
  while (timers.length) timers.shift()();
  assert.equal(attributes.has('data-td-suppress-hover-open'), false);

  const plain = { focused: 0, focus() { this.focused += 1; } };
  window.OinkSurfaceCoordinator.restoreFocus(plain);
  assert.equal(plain.focused, 1, 'an element outside any hover menu is simply focused');
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
      getClientRects() { return this.hidden ? [] : [{}]; },
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
      tdIndexSrc: '/search.json',
      tdMaxResults: '10',
      tdTLoading: 'Loading',
      tdTEmpty: 'Empty',
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
    addEventListener() {},
    removeEventListener() {},
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

// The version lists in the bottom bar and the phone drawer are hover popovers
// like the navbar one: no dropdown library opens, places or dismisses them.
function testHoverMenuDismissal() {
  [false, true].forEach(hoverMenuDismissal);
}

function hoverMenuDismissal(inDrawer) {
  const trigger = element();
  trigger.setAttribute('data-td-nav-hover-open', '');
  const option = element();
  const revealed = [];
  const menu = element({
    closest(selector) { return inDrawer && selector === '.td-site-drawer' ? element() : null; },
    contains(candidate) { return candidate === menu || candidate === trigger || candidate === option; },
    querySelector(selector) {
      return selector === '[data-td-nav-hover-trigger], .td-nav-util' ? trigger : null;
    },
    scrollIntoView(options) { revealed.push(options); },
  });
  const documentListeners = new Map();
  global.document = {
    body: element(),
    addEventListener(type, callback, capture) {
      assert.equal(capture, true);
      if (!documentListeners.has(type)) documentListeners.set(type, new Set());
      documentListeners.get(type).add(callback);
    },
    removeEventListener(type, callback) {
      documentListeners.get(type)?.delete(callback);
    },
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
  const dispatch = (type, event) => documentListeners.get(type)?.forEach((callback) => callback(event));
  const isOpen = () => menu.classList.contains('td-is-open');

  load('assets/js/base.js');
  document.body.focus();
  trigger.dispatch('click');
  assert.equal(isOpen(), true);
  assert.equal(trigger.getAttribute('aria-expanded'), 'true');
  // Only the drawer's list is in the flow and may need scrolling into view.
  assert.deepEqual(revealed, inDrawer ? [{ block: 'nearest', inline: 'nearest' }] : []);

  dispatch('pointerdown', { target: option });
  dispatch('click', { target: option });
  assert.equal(isOpen(), true);
  // A floating list closes on the press, because iOS sends no click for a
  // tap on plain content. The drawer's list waits for the click: closing on
  // the press would move the row the finger is on.
  const outside = element();
  dispatch('pointerdown', { target: outside });
  assert.equal(isOpen(), inDrawer);
  dispatch('click', { target: outside });
  assert.equal(isOpen(), false);
  assert.equal(trigger.getAttribute('aria-expanded'), 'false');
  trigger.dispatch('click');
  assert.equal(isOpen(), true, 'an outside press must reset the toggle state');

  // Escape on an option closes the list, returns focus to the trigger, and
  // stops there: a drawer that holds the menu stays open.
  for (const focused of [document.body, option, outside]) {
    focused.focus();
    menu.dispatch('pointerenter', { pointerType: 'mouse' });
    const escape = { ...keyboardEvent('Escape'), stopPropagation() { this.stopped = true; } };
    dispatch('keydown', escape);
    assert.equal(isOpen(), false);
    assert.equal(document.activeElement, focused === outside ? outside : trigger);
    assert.equal(escape.defaultPrevented, true);
    assert.equal(escape.stopped, true);
    const next = keyboardEvent('Escape');
    dispatch('keydown', next);
    assert.equal(next.defaultPrevented, false, 'the drawer receives the second Escape');
  }
}

testCoordinatorCompatibility();
testRestoreFocusKeepsHoverMenuClosed();
testPaletteFocusFromDrawer();
testNavbarHoverPanel();
testHoverTriggerClickAfterFocus();
testHoverMenuDismissal();
console.log('surface behavior checks passed');
