'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

function classes() {
  const values = new Set();
  return {
    add(...items) { items.forEach((item) => values.add(item)); },
    remove(...items) { items.forEach((item) => values.delete(item)); },
    contains(item) { return values.has(item); },
  };
}

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.attributes = new Map();
    this.dataset = {};
    this.listeners = new Map();
    this.classList = classes();
    this.className = '';
    this.hidden = false;
    this.id = '';
    this.offsetParent = {};
    this.style = {};
    this._text = '';
    this.value = '';
    this.nodeType = 1;
    this.selectionStart = 0;
    this.selectionEnd = 0;
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() {
    return this._text + this.children.map((child) => child.textContent || '').join('');
  }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  addEventListener(name, callback) {
    const callbacks = this.listeners.get(name) || [];
    callbacks.push(callback);
    this.listeners.set(name, callbacks);
  }
  dispatch(name, values = {}) {
    const event = {
      key: '', keyCode: 0, pointerType: '', isComposing: false,
      preventDefault() { this.defaultPrevented = true; },
      ...values,
    };
    (this.listeners.get(name) || []).forEach((callback) => callback(event));
    return event;
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) || null; }
  removeAttribute(name) { this.attributes.delete(name); }
  hasAttribute(name) { return this.attributes.has(name); }
  focus() { global.document.activeElement = this; }
  setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; }
  select() {}
  scrollIntoView() {}
  contains(candidate) {
    return candidate === this || this.children.some((child) => child.contains && child.contains(candidate));
  }
  closest(selector) {
    if (selector === '[data-mobile-menu]' && this.inMobile) return this;
    if (selector === '#td-shell-sidebar' && this.inDrawer) return this;
    return this.parentNode && this.parentNode.closest ? this.parentNode.closest(selector) : null;
  }
  querySelectorAll(selector) {
    const found = [];
    const visit = (node) => {
      if (selector === '[role="option"]' && node.getAttribute && node.getAttribute('role') === 'option')
        found.push(node);
      if (selector === '[data-td-shell-search-close]' && node.dataset.searchClose)
        found.push(node);
      if (selector === '[tabindex]:not([tabindex="-1"])' && node.getAttribute && node.getAttribute('tabindex') !== '-1')
        found.push(node);
      (node.children || []).forEach(visit);
    };
    this.children.forEach(visit);
    return found;
  }
  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }
}

function tick() {
  return new Promise((resolve) => setImmediate(resolve));
}

function setup({ controlledAnimationFrame = false } = {}) {
  const listeners = new Map();
  const html = new Element('html');
  const root = new Element();
  const input = new Element('input');
  const list = new Element();
  const panel = new Element();
  const status = new Element();
  const close = new Element('button');
  close.dataset.searchClose = 'true';
  panel.appendChild(input);
  panel.appendChild(list);
  panel.appendChild(close);
  root.appendChild(panel);
  root.hidden = true;
  root.dataset = {
    indexSrc: '/index.json', maxResults: '10',
    tEmpty: 'No results', tLoading: 'Loading', tResults: '{count} results',
    tActions: 'Actions', tPageActions: 'Page actions',
    tPreferences: 'Preferences', tCommands: 'Commands',
    tQuickLinks: 'Quick links', tChoice: 'Choose',
    tNoCommands: 'No commands', tActionFailed: 'Failed', tPages: 'Pages',
  };
  root.querySelector = (selector) => ({
    '.td-shell-search__input': input,
    '.td-shell-search__list': list,
    '.td-shell-search__panel': panel,
    '[data-td-shell-search-status]': status,
  })[selector] || null;
  root.querySelectorAll = (selector) => selector === '[data-td-shell-search-close]' ? [close] : [];

  const opener = new Element('button');
  const mobileOpener = new Element('button');
  mobileOpener.inMobile = true;
  const mobileToggle = new Element('button');
  const fetches = [];
  const assigned = [];
  const opened = [];
  const calls = [];
  const animationFrames = [];
  let fetchBehavior = () => Promise.resolve({
    ok: true,
    json: () => Promise.resolve([{ ref: '/docs/page/', title: 'PostgreSQL Page', root: 'docs' }]),
  });
  let pendingAction = null;

  const actions = [
    {
      id: 'print', title: 'Print', description: '', icon: 'fa-print', keywords: ['paper'],
      kind: 'invoke', available: true, disabledReason: '', placements: { page: true, palette: true }, options: [],
    },
    {
      id: 'edit_page', title: 'Edit page', description: '', icon: 'fa-edit', keywords: [],
      kind: 'url', available: false, disabledReason: 'No repository', placements: { page: true, palette: true }, options: [],
    },
    {
      id: 'open_chatgpt', title: 'Open in ChatGPT', description: '',
      icon: 'fa-brands fa-openai', keywords: ['gpt'], kind: 'url', available: true,
      disabledReason: '', placements: { page: true, palette: true }, options: [],
    },
    {
      id: 'open_claude', title: 'Open in Claude', description: '',
      icon: 'fa-brands fa-claude', keywords: ['anthropic'], kind: 'url', available: true,
      disabledReason: '', placements: { page: true, palette: true }, options: [],
    },
    {
      id: 'switch_theme', title: 'Theme', description: '', icon: 'fa-theme', keywords: ['dark'],
      kind: 'choice', available: true, disabledReason: '', placements: { page: false, palette: true },
      options: [{ id: 'dark', title: 'Dark', value: 'dark', available: true }],
    },
  ];
  const byId = new Map(actions.map((action) => [action.id, action]));
  const commands = [
    { id: 'status', title: 'Service status', keywords: ['uptime'], kind: 'url', url: '/status/', available: true },
    { id: 'theme_now', title: 'Choose theme', keywords: ['dark'], kind: 'builtin', action: 'switch_theme', available: true },
  ];
  const registry = {
    get(id) { return byId.get(id) || null; },
    list() { return actions; },
    commands() { return commands; },
    quickLinks() { return [{ id: 'docs', title: 'Docs', url: '/docs/', available: true }]; },
    rootOrder() { return ['docs', 'blog']; },
    safeUrl(value) {
      if (!value || /^(?:javascript|data):/i.test(value)) return null;
      return new URL(value, 'https://example.test/').href;
    },
    run(id, context) { calls.push(['action', id, context]); return pendingAction || Promise.resolve({}); },
    runCommand(id, context) {
      calls.push(['command', id, context]);
      if (id === 'theme_now' && !context.value)
        return Promise.resolve({ requiresChoice: true, action: byId.get('switch_theme'), command: commands[1], options: byId.get('switch_theme').options });
      return pendingAction || Promise.resolve({});
    },
  };
  const searchApi = {
    create(docs) {
      return {
        query(query) {
          return docs.filter((doc) => doc.title.toLowerCase().includes(query.toLowerCase()))
            .map((doc) => ({ doc, excerpt: doc.title, score: 1 }));
        },
      };
    },
    group(results) {
      return results.length ? [{ key: 'docs', label: 'Documentation', results }] : [];
    },
  };

  global.document = {
    activeElement: opener,
    documentElement: html,
    createElement(tag) { return new Element(tag); },
    createDocumentFragment() { return new Element('fragment'); },
    createTextNode(text) { const node = new Element('text'); node.textContent = text; return node; },
    getElementById(id) { return id === 'td-shell-search' ? root : null; },
    querySelector(selector) { return selector === '[data-menu-toggle]' ? mobileToggle : null; },
    querySelectorAll(selector) {
      if (selector === '[data-td-shell-search-open]') return [opener, mobileOpener];
      return [];
    },
    addEventListener(name, callback) {
      const callbacks = listeners.get(name) || [];
      callbacks.push(callback);
      listeners.set(name, callbacks);
    },
  };
  Object.defineProperty(global, 'navigator', {
    configurable: true,
    value: { platform: 'MacIntel', userAgent: '' },
  });
  global.fetch = (url) => { fetches.push(url); return fetchBehavior(); };
  global.window = {
    __OINK_PALETTE_MANUAL_INIT__: true,
    clearTimeout() {},
    setTimeout(callback) { callback(); return 1; },
    requestAnimationFrame(callback) {
      if (controlledAnimationFrame) animationFrames.push(callback);
      else callback();
    },
    matchMedia() { return { matches: true }; },
    location: { assign(url) { assigned.push(url); } },
    open(url, target, features) { opened.push({ url, target, features }); return null; },
  };
  global.lunr = () => {};
  global.window.lunr = global.lunr;
  const modelPath = path.join(__dirname, '..', '..', 'assets/js/palette-model.js');
  delete require.cache[require.resolve(modelPath)];
  global.window.OinkPaletteModel = require(modelPath);
  const palettePath = path.join(__dirname, '..', '..', 'assets/js/command-palette.js');
  delete require.cache[require.resolve(palettePath)];
  const paletteModule = require(palettePath);
  const controller = paletteModule.init({ root, registry, model: window.OinkPaletteModel, searchApi });

  return {
    controller, root, input, list, status, opener, mobileOpener, mobileToggle,
    fetches, assigned, opened, calls, listeners, animationFrames,
    setFetch(value) { fetchBehavior = value; },
    setPending(value) { pendingAction = value; },
  };
}

(async () => {
  const h = setup();
  h.input.value = '';
  h.opener.dispatch('click', { currentTarget: h.opener });
  assert.equal(h.fetches.length, 0, 'empty open fetched the page index');
  assert.ok(h.controller.rows().some((row) => row.type === 'quick'));
  assert.ok(h.controller.rows().some((row) => row.sourceId === 'print'));
  assert.equal(document.activeElement, h.input);
  const emptyOptions = h.list.querySelectorAll('[role="option"]');
  for (const [sourceId, icon] of [
    ['open_chatgpt', 'fa-openai'],
    ['open_claude', 'fa-claude'],
  ]) {
    const index = h.controller.rows().findIndex((row) => row.sourceId === sourceId);
    assert.ok(index >= 0, `${sourceId} is missing from the Palette`);
    assert.ok(emptyOptions[index].children[0].classList.contains('fa-brands'));
    assert.ok(emptyOptions[index].children[0].classList.contains(icon));
  }

  h.input.value = '> dark';
  h.input.dispatch('input');
  assert.equal(h.fetches.length, 0, 'command mode fetched the page index');
  assert.ok(h.controller.rows().every((row) => row.type === 'command' || row.type === 'action'));
  assert.ok(h.controller.rows().some((row) => row.sourceId === 'theme_now'));

  const themeIndex = h.controller.rows().findIndex((row) => row.sourceId === 'theme_now');
  h.controller.activate(themeIndex);
  await tick();
  assert.ok(h.controller.rows().every((row) => row.type === 'choice'));
  assert.equal(
    h.calls.filter((call) => call[1] === 'theme_now').length,
    0,
    'opening a choice invoked its command',
  );
  h.controller.activate(0);
  await tick();
  assert.equal(h.calls.filter((call) => call[1] === 'theme_now').length, 1);
  assert.equal(h.calls.at(-1)[2].value.id, 'dark');

  h.input.value = '> edit';
  h.input.dispatch('input');
  const disabled = h.controller.rows().findIndex((row) => row.sourceId === 'edit_page');
  h.controller.activate(disabled);
  assert.equal(h.status.textContent, 'No repository');
  assert.equal(h.calls.some((call) => call[1] === 'edit_page'), false);

  h.input.value = 'postgresql';
  h.input.dispatch('input');
  assert.equal(h.fetches.length, 1, 'text mode did not fetch exactly once');
  await tick();
  h.controller.render(h.input.value);
  assert.ok(
    h.controller.rows().some((row) => row.type === 'page'),
    `page rows missing: ${JSON.stringify(h.controller.rows())}`,
  );

  const composedCalls = h.calls.length;
  h.input.dispatch('compositionstart');
  h.input.dispatch('keydown', { key: 'Enter', keyCode: 229, isComposing: true });
  assert.equal(h.calls.length, composedCalls, 'IME Enter activated a row');
  const wasOpenDuringComposition = h.controller.isOpen();
  (h.listeners.get('keydown') || []).forEach((callback) => callback({
    key: 'Escape', keyCode: 229, isComposing: true, preventDefault() {},
  }));
  assert.equal(
    h.controller.isOpen(),
    wasOpenDuringComposition,
    'IME Escape changed the Palette open state',
  );
  h.input.dispatch('compositionend');

  let resolvePending;
  h.setPending(new Promise((resolve) => { resolvePending = resolve; }));
  h.input.value = '> print';
  h.input.dispatch('input');
  const printIndex = h.controller.rows().findIndex((row) => row.sourceId === 'print');
  h.controller.activate(printIndex);
  h.controller.activate(printIndex);
  assert.equal(h.calls.filter((call) => call[1] === 'print').length, 1, 'pending action ran twice');
  assert.equal(h.controller.isOpen(), false, 'print ran beneath the open dialog');
  assert.equal(document.activeElement, h.opener, 'print did not restore invoker focus');
  resolvePending({});
  await tick();

  let resolveOld;
  h.setPending(new Promise((resolve) => { resolveOld = resolve; }));
  h.opener.dispatch('click', { currentTarget: h.opener });
  h.input.value = '> status';
  h.input.dispatch('input');
  let statusIndex = h.controller.rows().findIndex((row) => row.sourceId === 'status');
  h.controller.activate(statusIndex);
  h.controller.close();
  let resolveNew;
  h.setPending(new Promise((resolve) => { resolveNew = resolve; }));
  h.opener.dispatch('click', { currentTarget: h.opener });
  h.input.value = '> status';
  h.input.dispatch('input');
  statusIndex = h.controller.rows().findIndex((row) => row.sourceId === 'status');
  h.controller.activate(statusIndex);
  const statusCalls = h.calls.filter((call) => call[1] === 'status').length;
  resolveOld({});
  await tick();
  h.controller.activate(statusIndex);
  assert.equal(
    h.calls.filter((call) => call[1] === 'status').length,
    statusCalls,
    'an old action Promise unlocked the current activation',
  );
  resolveNew({});
  await tick();

  h.controller.close();
  h.mobileOpener.dispatch('click', { currentTarget: h.mobileOpener });
  h.controller.close();
  assert.equal(document.activeElement, h.mobileToggle, 'focus returned to a hidden mobile opener');

  const failure = setup();
  failure.setFetch(() => Promise.reject(new Error('offline')));
  failure.input.value = 'status';
  failure.opener.dispatch('click', { currentTarget: failure.opener });
  await tick();
  assert.ok(failure.controller.rows().some((row) => row.sourceId === 'status'));
  assert.equal(failure.fetches.length, 1);
  failure.input.value = '> status';
  failure.input.dispatch('input');
  failure.input.value = 'status';
  failure.input.dispatch('input');
  await tick();
  assert.equal(failure.fetches.length, 2, 'normal user input could not retry a failed index');

  const slow = setup();
  let resolveIndex;
  slow.setFetch(() => new Promise((resolve) => { resolveIndex = resolve; }));
  slow.input.value = 'postgresql';
  slow.opener.dispatch('click', { currentTarget: slow.opener });
  assert.equal(slow.fetches.length, 1);
  slow.controller.close();
  slow.opener.dispatch('click', { currentTarget: slow.opener });
  assert.equal(slow.fetches.length, 1, 'reopen duplicated the in-flight index fetch');
  resolveIndex({
    ok: true,
    json: () => Promise.resolve([
      { ref: '/docs/page/', title: 'PostgreSQL Page', root: 'docs' },
    ]),
  });
  await tick();
  assert.ok(
    slow.controller.rows().some((row) => row.type === 'page'),
    'index completion did not redraw a reopened Palette',
  );
  assert.equal(slow.list.getAttribute('aria-busy'), null);

  const beforeFrame = setup({ controlledAnimationFrame: true });
  beforeFrame.input.value = 'postgresql';
  beforeFrame.opener.dispatch('click', { currentTarget: beforeFrame.opener });
  await tick();
  assert.ok(
    beforeFrame.controller.rows().some((row) => row.type === 'page'),
    'index completing before the opening frame did not redraw results',
  );
  beforeFrame.controller.close();
  beforeFrame.animationFrames.forEach((callback) => callback());
  assert.equal(
    beforeFrame.root.classList.contains('is-open'),
    false,
    'a stale opening frame reopened the closed Palette',
  );

  const unsafe = setup();
  unsafe.controller.open({ currentTarget: unsafe.opener });
  unsafe.controller.render('');
  const quick = unsafe.controller.rows().find((row) => row.type === 'quick');
  quick.url = 'javascript:alert(1)';
  const assignedBefore = unsafe.assigned.length;
  unsafe.controller.activate(unsafe.controller.rows().findIndex((row) => row.type === 'quick'));
  await tick();
  assert.equal(unsafe.assigned.length, assignedBefore, 'unsafe result URL navigated');
  assert.equal(unsafe.status.textContent, 'Failed');

  const external = setup();
  external.controller.open({ currentTarget: external.opener });
  external.controller.render('');
  const externalQuick = external.controller.rows().find((row) => row.type === 'quick');
  externalQuick.url = 'https://status.example.test/';
  externalQuick.target = 'blank';
  external.controller.activate(
    external.controller.rows().findIndex((row) => row.type === 'quick'),
  );
  await tick();
  assert.equal(external.opened.length, 1, 'external result opened more than once');
  assert.equal(external.controller.isOpen(), false, 'successful external result left Palette open');

  // Slash opens straight into command mode. It is a bare single-character
  // shortcut, so it must yield to any field the reader may be typing in.
  const slash = setup();
  function pressKey(harness, values) {
    const event = Object.assign(
      {
        key: '', metaKey: false, ctrlKey: false, altKey: false,
        isComposing: false, keyCode: 0, target: harness.root,
        currentTarget: global.document,
        preventDefault() { this.defaultPrevented = true; },
      },
      values,
    );
    (harness.listeners.get('keydown') || []).forEach((fn) => fn(event));
    return event;
  }

  const opened = pressKey(slash, { key: '/' });
  assert.equal(slash.controller.isOpen(), true, 'slash did not open the Palette');
  assert.equal(slash.input.value, '>', 'slash did not seed command mode');
  assert.equal(opened.defaultPrevented, true, 'slash did not prevent the literal character');
  assert.ok(
    slash.controller.rows().every((row) => row.type === 'command' || row.type === 'action'),
    'slash showed page results instead of commands',
  );
  assert.equal(slash.input.selectionStart, 1, 'caret was not placed after the prefix');

  slash.controller.close();
  assert.equal(
    global.document.activeElement,
    slash.opener,
    'slash close did not restore focus to the pre-shortcut element',
  );
  const field = new Element('input');
  const ignoredField = pressKey(slash, { key: '/', target: field });
  assert.equal(slash.controller.isOpen(), false, 'slash opened while typing in a field');
  assert.notEqual(ignoredField.defaultPrevented, true, 'slash stole a literal character');

  const ignoredModifier = pressKey(slash, { key: '/', ctrlKey: true });
  assert.equal(slash.controller.isOpen(), false, 'ctrl+slash opened the Palette');
  assert.notEqual(ignoredModifier.defaultPrevented, true, 'ctrl+slash was swallowed');

  slash.controller.open({ currentTarget: slash.opener });
  slash.input.value = 'already typing';
  pressKey(slash, { key: '/' });
  assert.equal(
    slash.input.value, 'already typing',
    'slash reset a query while the Palette was already open',
  );

  console.log('PRD 4 Command Palette controller checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
