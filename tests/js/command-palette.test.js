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
  get firstChild() { return this.children[0] || null; }
  insertBefore(child, before) {
    child.parentNode = this;
    const index = this.children.indexOf(before);
    if (index < 0) this.children.push(child);
    else this.children.splice(index, 0, child);
    return child;
  }
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
    if (selector === '[data-td-mobile-menu]' && this.inMobile) return this;
    if (selector === '#td-shell-sidebar' && this.inDrawer) return this;
    return this.parentNode && this.parentNode.closest ? this.parentNode.closest(selector) : null;
  }
  querySelectorAll(selector) {
    const found = [];
    const visit = (node) => {
      if (selector === '[role="option"]' && node.getAttribute && node.getAttribute('role') === 'option')
        found.push(node);
      if (selector === '[data-td-shell-search-close]' && node.dataset.tdShellSearchClose)
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
  close.dataset.tdShellSearchClose = 'true';
  panel.appendChild(input);
  panel.appendChild(list);
  panel.appendChild(close);
  root.appendChild(panel);
  root.hidden = true;
  root.dataset = {
    tdIndexSrc: '/index.json', tdMaxResults: '10',
    tdTEmpty: 'No results', tdTLoading: 'Loading', tdTResults: '{count} results',
    tdTActions: 'Actions', tdTPageActions: 'Page actions',
    tdTPreferences: 'Preferences', tdTCommands: 'Commands',
    tdTQuickLinks: 'Quick links', tdTChoice: 'Choose',
    tdTNoCommands: 'No commands', tdTActionFailed: 'Failed', tdTPages: 'Pages',
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
    querySelector(selector) { return selector === '[data-td-menu-toggle]' ? mobileToggle : null; },
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
    controller, paletteModule, html, root, input, list, status, opener, mobileOpener, mobileToggle,
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
    beforeFrame.root.classList.contains('td-is-open'),
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

  // Slash opens the full search surface; backslash opens straight into
  // command mode. Both are bare single-character shortcuts, so they must
  // yield to any field the reader may be typing in.
  const slash = setup();
  function pressKey(harness, values) {
    const event = Object.assign(
      {
        key: '', metaKey: false, ctrlKey: false, altKey: false, shiftKey: false,
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
  assert.equal(slash.input.value, '', 'slash seeded a query instead of the full surface');
  assert.equal(opened.defaultPrevented, true, 'slash did not prevent the literal character');
  assert.ok(
    slash.controller.rows().some((row) => row.type === 'quick'),
    'slash did not land on the full empty-state surface',
  );

  slash.controller.close();
  assert.equal(
    global.document.activeElement,
    slash.opener,
    'slash close did not restore focus to the pre-shortcut element',
  );

  const backslashOpened = pressKey(slash, { key: '\\' });
  assert.equal(slash.controller.isOpen(), true, 'backslash did not open the Palette');
  assert.equal(slash.input.value, '>', 'backslash did not seed command mode');
  assert.equal(
    backslashOpened.defaultPrevented, true,
    'backslash did not prevent the literal character',
  );
  assert.ok(
    slash.controller.rows().every((row) => row.type === 'command' || row.type === 'action'),
    'backslash showed page results instead of commands',
  );
  assert.equal(slash.input.selectionStart, 1, 'caret was not placed after the prefix');
  slash.controller.close();

  const field = new Element('input');
  for (const key of ['/', '\\']) {
    const ignoredField = pressKey(slash, { key, target: field });
    assert.equal(slash.controller.isOpen(), false, `${key} opened while typing in a field`);
    assert.notEqual(ignoredField.defaultPrevented, true, `${key} stole a literal character`);

    const ignoredModifier = pressKey(slash, { key, ctrlKey: true });
    assert.equal(slash.controller.isOpen(), false, `ctrl+${key} opened the Palette`);
    assert.notEqual(ignoredModifier.defaultPrevented, true, `ctrl+${key} was swallowed`);

    const ignoredShift = pressKey(slash, { key, shiftKey: true });
    assert.equal(slash.controller.isOpen(), false, `shift+${key} opened the Palette`);
    assert.notEqual(ignoredShift.defaultPrevented, true, `shift+${key} was swallowed`);

    const alreadyHandled = pressKey(slash, { key, defaultPrevented: true });
    assert.equal(slash.controller.isOpen(), false, `handled ${key} opened the Palette`);
    assert.equal(alreadyHandled.defaultPrevented, true);
  }

  const roleDialog = new Element('div');
  roleDialog.setAttribute('role', 'dialog');
  const originalQuerySelectorAll = global.document.querySelectorAll;
  global.document.querySelectorAll = (selector) =>
    selector === '[role="dialog"]'
      ? [roleDialog]
      : originalQuerySelectorAll.call(global.document, selector);
  const blockedByDialog = pressKey(slash, { key: '/' });
  assert.equal(slash.controller.isOpen(), false, 'slash opened over an ARIA dialog');
  assert.notEqual(blockedByDialog.defaultPrevented, true);
  global.document.querySelectorAll = originalQuerySelectorAll;

  slash.controller.open({ currentTarget: slash.opener });
  slash.input.value = 'already typing';
  pressKey(slash, { key: '/' });
  pressKey(slash, { key: '\\' });
  assert.equal(
    slash.input.value, 'already typing',
    'shortcut reset a query while the Palette was already open',
  );

  const extension = setup();
  extension.html.lang = 'zh';
  const contexts = [];
  let activationContext;
  let activationCount = 0;
  let finishActivation;
  const descriptor = { id: 'ask', title: 'Array<T> <script>', description: 'Literal <b>text</b>' };
  const provider = {
    id: 'ask-ai',
    rows(context) { contexts.push(context); return [descriptor]; },
    activate(row, context) {
      activationContext = context;
      activationCount += 1;
      assert.equal(row.title, 'Array<T> <script>');
      return new Promise(resolve => { finishActivation = resolve; });
    },
  };
  const unregister = extension.paletteModule.registerSearchTail(provider);
  assert.throws(() => extension.paletteModule.registerSearchTail(provider), /Duplicate/);
  assert.throws(() => extension.paletteModule.registerSearchTail({ ...provider, id: 'bad:id' }), /Invalid/);
  extension.controller.open();
  extension.input.value = '> theme';
  extension.controller.render(extension.input.value);
  assert.equal(contexts.length, 0, 'empty or command mode called a provider');
  const choice = extension.controller.rows().findIndex(row => row.sourceId === 'switch_theme');
  extension.controller.activate(choice);
  assert.equal(contexts.length, 0, 'choice mode called a provider');
  extension.input.value = ' postgresql ';
  extension.input.dispatch('input');
  assert.equal(contexts.length, 0, 'loading index called a provider');
  await tick();
  assert.equal(contexts.at(-1).query, 'postgresql');
  assert.equal(contexts.at(-1).locale, 'zh');
  assert.equal(contexts.at(-1).phase, 'results');
  assert.equal(contexts.at(-1).pageResultCount, 1);
  assert.ok(Object.isFrozen(contexts.at(-1)));
  assert.equal(extension.controller.rows()[0].type, 'page');
  assert.equal(extension.controller.rows().at(-1).type, 'extension');
  assert.ok(extension.list.textContent.includes('Array<T> <script>'));
  extension.controller.render(extension.input.value);
  assert.equal(extension.controller.rows().filter(row => row.type === 'extension').length, 1);
  descriptor.title = 'Mutated after rendering';
  extension.input.value = 'newer input before debounce';
  const tailIndex = extension.controller.rows().findIndex(row => row.type === 'extension');
  extension.controller.activate(tailIndex);
  extension.controller.activate(tailIndex);
  assert.equal(activationCount, 1);
  assert.equal(activationContext.query, 'postgresql', 'activation rebuilt the query instead of keeping the rendered snapshot');
  assert.equal(extension.list.getAttribute('aria-busy'), 'true');
  unregister();
  assert.equal(activationContext.signal.aborted, true);
  assert.equal(extension.list.getAttribute('aria-busy'), null);
  finishActivation({ requiresChoice: true });
  await tick();
  assert.equal(extension.controller.isOpen(), true, 'unregistered settlement closed the Palette');
  descriptor.title = 'Array<T> <script>';
  const unregisterNew = extension.paletteModule.registerSearchTail(provider);
  unregister();
  extension.input.value = 'absent';
  extension.controller.render(extension.input.value);
  assert.equal(extension.controller.rows().filter(row => row.type === 'extension').length, 1, 'old unregister removed a newer registration');
  assert.equal(contexts.at(-1).phase, 'empty');
  assert.equal(contexts.at(-1).pageResultCount, 0);
  assert.ok(extension.list.textContent.startsWith('No results'), 'extension replaced native empty-state text');
  unregisterNew();
  for (const rows of [
    () => { throw new Error('broken'); },
    () => Promise.resolve([]),
    () => [{ id: 'a', title: 'A' }, { id: 'a', title: 'Duplicate' }],
    () => [{ id: 'unsafe:id', title: 'Unsafe' }],
    () => [{ id: 'a', title: 'A', available: 'yes' }],
    () => [{ id: 'a', title: 'A', description: {} }],
  ]) {
    const remove = extension.paletteModule.registerSearchTail({ id: 'invalid', rows, activate() {} });
    extension.controller.render('absent');
    assert.equal(extension.controller.rows().length, 0, 'invalid provider emitted partial rows');
    remove();
  }
  let action = () => { throw new Error('Private provider failure'); };
  extension.paletteModule.registerSearchTail({ id: 'valid', rows: () => [{ id: 'a', title: 'Valid' }],
    activate(row, context) { activationContext = context; return action(context); } });
  await tick();
  assert.equal(extension.controller.rows().length, 1);
  extension.controller.activate(0);
  await tick();
  assert.equal(extension.status.textContent, 'Failed', 'provider errors bypassed the localized failure message');
  assert.equal(extension.controller.isOpen(), true);
  assert.equal(extension.list.getAttribute('aria-busy'), null);
  action = () => Promise.reject(new Error('Rejected'));
  extension.controller.activate(0);
  await tick();
  assert.equal(extension.list.getAttribute('aria-busy'), null);

  action = () => new Promise(resolve => { finishActivation = resolve; });
  extension.controller.activate(0);
  const oldSignal = activationContext.signal;
  extension.controller.close();
  assert.equal(oldSignal.aborted, true);
  extension.controller.open();
  finishActivation();
  await tick();
  assert.equal(extension.controller.isOpen(), true, 'old-session completion closed the new session');
  extension.controller.activate(0);
  const querySignal = activationContext.signal;
  extension.input.value = 'changed query';
  extension.input.dispatch('input');
  assert.equal(querySignal.aborted, true);
  finishActivation();
  await tick();

  const externalFocus = new Element('button');
  action = context => {
    assert.equal(context.handoff(), true);
    externalFocus.focus();
    return new Promise(resolve => { finishActivation = resolve; });
  };
  extension.controller.activate(0);
  assert.equal(extension.controller.isOpen(), false);
  assert.equal(activationContext.signal.aborted, false, 'successful handoff aborted itself');
  finishActivation({ requiresChoice: true });
  await tick();
  assert.equal(activationContext.signal.aborted, false);
  assert.equal(document.activeElement, externalFocus);
  extension.controller.open();
  action = () => ({ requiresChoice: true, action: {} });
  extension.controller.activate(0);
  await tick();
  assert.equal(extension.controller.isOpen(), false, 'extension fulfillment value was interpreted as a native action');

  const pendingChoice = setup();
  let finishPendingChoice;
  let pendingChoiceContext;
  pendingChoice.paletteModule.registerSearchTail({ id: 'helper',
    rows: () => [{ id: 'ask', title: 'Ask helper' }],
    activate(row, context) {
      pendingChoiceContext = context;
      return new Promise(resolve => { finishPendingChoice = resolve; });
    },
  });
  pendingChoice.input.value = 'dark';
  pendingChoice.controller.open();
  await tick();
  pendingChoice.controller.activate(pendingChoice.controller.rows().findIndex(row => row.type === 'extension'));
  const themeChoiceIndex = pendingChoice.controller.rows().findIndex(row => row.sourceId === 'switch_theme');
  assert.ok(themeChoiceIndex >= 0);
  pendingChoice.controller.activate(themeChoiceIndex);
  assert.equal(pendingChoice.controller.rows().some(row => row.type === 'choice'), false,
    'a pending extension allowed a native choice menu to replace its rows');
  assert.equal(pendingChoiceContext.signal.aborted, false);
  finishPendingChoice();
  await tick();
  pendingChoice.controller.open();
  pendingChoice.controller.activate(pendingChoice.controller.rows().findIndex(row => row.sourceId === 'switch_theme'));
  assert.ok(pendingChoice.controller.rows().some(row => row.type === 'choice'),
    'completed activation left native choices locked');

  const extensionFailure = setup();
  const failedContexts = [];
  extensionFailure.root.dataset.tdTIndexUnavailable = 'Index unavailable';
  extensionFailure.setFetch(() => Promise.reject(new Error('offline')));
  extensionFailure.paletteModule.registerSearchTail({ id: 'fallback',
    rows(context) { failedContexts.push(context); return [{ id: 'a', title: 'Fallback' }]; }, activate() {} });
  extensionFailure.input.value = 'postgresql';
  extensionFailure.controller.open();
  await tick();
  assert.equal(failedContexts.at(-1).phase, 'error');
  assert.equal(failedContexts.at(-1).pageResultCount, 0);
  assert.ok(extensionFailure.list.textContent.startsWith('Index unavailable'));
  extensionFailure.setFetch(() => Promise.resolve({ ok: true, json: () => Promise.resolve([
    { ref: '/docs/page/', title: 'PostgreSQL Page', root: 'docs' },
  ]) }));
  extensionFailure.input.dispatch('input');
  await tick();
  assert.equal(extensionFailure.fetches.length, 2, 'extension disabled native retry');
  assert.equal(failedContexts.at(-1).phase, 'results');

  console.log('Command Palette controller checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
