'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(
  path.join(__dirname, '..', '..', 'assets/js/page-actions.js'),
  'utf8',
);

function control(id, root, tagName = 'BUTTON') {
  const listeners = new Map();
  const label = { textContent: 'Copy Markdown', dataset: {} };
  const classes = new Set();
  const attributes = new Map();
  return {
    dataset: { tdAction: id },
    tagName,
    listeners,
    label,
    classList: {
      add(value) { classes.add(value); },
      remove(value) { classes.delete(value); },
      contains(value) { return classes.has(value); },
    },
    querySelector(selector) {
      return selector === '[data-td-page-copy-label]' ? label : null;
    },
    closest(selector) {
      return selector === '[data-td-page-context]' ? root : null;
    },
    addEventListener(name, handler, options) {
      listeners.set(name, { handler, options });
    },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.get(name) || null; },
  };
}

/* Scenario 1: registry binding on plain controls (no title menu present). */
async function testBindings() {
  const status = { textContent: '' };
  const root = {
    dataset: { tdTCopied: 'Markdown copied', tdTCopyError: 'Copy failed' },
    querySelector(selector) {
      return selector === '[data-td-page-context-status]' ? status : null;
    },
  };
  const copy = control('copy_markdown', root);
  const print = control('print', root);
  const chatgpt = control('open_chatgpt', root, 'A');
  const claude = control('open_claude', root, 'A');
  const events = { preload: [], run: [], resolve: [], timers: [], current: 'initial' };
  const actions = {
    copy_markdown: { id: 'copy_markdown', available: true, url: '/page.md' },
    print: { id: 'print', available: true },
    open_chatgpt: { id: 'open_chatgpt', kind: 'url', available: true },
    open_claude: { id: 'open_claude', kind: 'url', available: true },
  };
  const fakeWindow = {
    OinkActions: {
      get(id) { return actions[id] || null; },
      preloadMarkdown(url) { events.preload.push(url); return Promise.resolve(); },
      run(id, context) { events.run.push({ id, context }); return Promise.resolve(); },
      resolveUrl(id) {
        events.resolve.push({ id, current: events.current });
        return `https://assistant.example/${id}?page=${events.current}`;
      },
    },
    requestAnimationFrame(callback) { callback(); },
    setTimeout(callback) { events.timers.push(callback); },
  };
  const fakeDocument = {
    querySelectorAll(selector) {
      assert.equal(selector, '[data-td-action]');
      return [copy, print, chatgpt, claude];
    },
    querySelector(selector) {
      assert.equal(selector, '[data-td-page-actions]');
      return null;
    },
  };
  vm.runInNewContext(source, {
    window: fakeWindow,
    document: fakeDocument,
    Promise,
  });

  assert.equal(
    chatgpt.getAttribute('href'),
    'https://assistant.example/open_chatgpt?page=initial',
  );
  assert.equal(
    claude.getAttribute('href'),
    'https://assistant.example/open_claude?page=initial',
  );
  events.current = 'query-and-hash';
  chatgpt.listeners.get('click').handler();
  assert.equal(
    chatgpt.getAttribute('href'),
    'https://assistant.example/open_chatgpt?page=query-and-hash',
  );

  copy.listeners.get('pointerenter').handler();
  copy.listeners.get('focus').handler();
  assert.deepEqual(events.preload, ['/page.md', '/page.md']);
  assert.equal(copy.listeners.get('pointerenter').options.once, true);

  copy.listeners.get('click').handler();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(events.run[0].id, 'copy_markdown');
  assert.equal(events.run[0].context.source, 'page');
  assert.equal(copy.classList.contains('td-is-copied'), true);
  assert.equal(copy.label.textContent, 'Markdown copied');
  assert.equal(status.textContent, 'Markdown copied');
  events.timers[0]();
  assert.equal(copy.classList.contains('td-is-copied'), false);
  assert.equal(copy.label.textContent, 'Copy Markdown');

  print.listeners.get('click').handler();
  assert.equal(events.run[1].id, 'print');
  assert.equal(events.run[1].context.source, 'page');
  assert.deepEqual(events.resolve, [
    { id: 'open_chatgpt', current: 'initial' },
    { id: 'open_claude', current: 'initial' },
    { id: 'open_chatgpt', current: 'query-and-hash' },
  ]);
}

/* Scenario 2: the title split button — disclosure behavior and the copy
   feedback landing on the primary half even for the menu row. */
async function testTitleMenu() {
  const events = { run: [], coordinator: [], timers: [] };
  const status = { textContent: '' };
  const docListeners = new Map();
  const menuListeners = new Map();
  const toggleAttrs = new Map([['aria-expanded', 'false']]);
  const rootClasses = new Set();

  const toggle = {
    focused: 0,
    addEventListener(name, handler) { menuListeners.set(`toggle:${name}`, handler); },
    setAttribute(name, value) { toggleAttrs.set(name, String(value)); },
    getAttribute(name) { return toggleAttrs.get(name) || null; },
    focus() { this.focused += 1; },
  };
  const menu = {
    addEventListener(name, handler) { menuListeners.set(`menu:${name}`, handler); },
    querySelectorAll() { return []; },
  };
  const root = {
    dataset: { tdTCopied: 'Markdown copied', tdTCopyError: 'Copy failed' },
    classList: {
      add(value) { rootClasses.add(value); },
      remove(value) { rootClasses.delete(value); },
      contains(value) { return rootClasses.has(value); },
    },
    contains(target) { return target && target.inside === true; },
    querySelector(selector) {
      if (selector === '[data-td-page-context-status]') return status;
      if (selector === '.td-page-actions__primary[data-td-action="copy_markdown"]') return primary;
      if (selector === '[data-td-page-actions-toggle]') return toggle;
      if (selector === '[data-td-page-actions-menu]') return menu;
      return null;
    },
  };
  const primary = control('copy_markdown', root);
  const menuCopy = control('copy_markdown', root);
  menuCopy.querySelector = () => null; // The menu row has no feedback label.

  const fakeWindow = {
    OinkActions: {
      get(id) {
        return id === 'copy_markdown'
          ? { id, available: true, url: '/page.md' }
          : null;
      },
      preloadMarkdown() { return Promise.resolve(); },
      run(id, context) { events.run.push({ id, context }); return Promise.resolve(); },
      resolveUrl() { return null; },
    },
    OinkSurfaceCoordinator: {
      register(name) { events.coordinator.push(`register:${name}`); },
      closeOthers(name) { events.coordinator.push(`closeOthers:${name}`); },
    },
    requestAnimationFrame(callback) { callback(); },
    setTimeout(callback) { events.timers.push(callback); },
  };
  const fakeDocument = {
    activeElement: toggle,
    querySelectorAll(selector) {
      assert.equal(selector, '[data-td-action]');
      return [primary, menuCopy];
    },
    querySelector(selector) {
      assert.equal(selector, '[data-td-page-actions]');
      return root;
    },
    addEventListener(name, handler) { docListeners.set(name, handler); },
  };
  vm.runInNewContext(source, {
    window: fakeWindow,
    document: fakeDocument,
    Promise,
  });

  assert.deepEqual(events.coordinator, ['register:page-actions']);

  // Toggle opens: coordinator closes other surfaces, state is reflected.
  menuListeners.get('toggle:click')();
  assert.equal(rootClasses.has('td-is-open'), true);
  assert.equal(toggleAttrs.get('aria-expanded'), 'true');
  assert.deepEqual(events.coordinator, [
    'register:page-actions',
    'closeOthers:page-actions',
  ]);

  // Outside pointerdown closes without stealing focus.
  docListeners.get('pointerdown')({ target: { inside: false } });
  assert.equal(rootClasses.has('td-is-open'), false);
  assert.equal(toggle.focused, 0);

  // Escape closes and returns focus to the toggle.
  menuListeners.get('toggle:click')();
  let escapePrevented = false;
  docListeners.get('keydown')({
    key: 'Escape',
    preventDefault() { escapePrevented = true; },
  });
  assert.equal(rootClasses.has('td-is-open'), false);
  assert.equal(toggle.focused, 1);
  assert.equal(escapePrevented, true);

  // Activating any menu row closes the disclosure.
  menuListeners.get('toggle:click')();
  menuListeners.get('menu:click')({ target: { closest: () => menuCopy } });
  assert.equal(rootClasses.has('td-is-open'), false);

  // Copy from the menu row: the confirmation lands on the primary half.
  menuCopy.listeners.get('click').handler();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(events.run[0].id, 'copy_markdown');
  assert.equal(events.run[0].context.source, 'page');
  assert.equal(primary.classList.contains('td-is-copied'), true);
  assert.equal(primary.label.textContent, 'Markdown copied');
  assert.equal(status.textContent, 'Markdown copied');
}

/* Scenario 3: the share bar's copy control — its own context root, its own
   wording, and no dependency on the title menu being present. */
async function testShareCopy() {
  const status = { textContent: '' };
  const root = {
    dataset: { tdTCopied: 'Link copied', tdTCopyError: 'Could not copy the link' },
    querySelector(selector) {
      return selector === '[data-td-page-context-status]' ? status : null;
    },
  };
  const events = { run: [], timers: [] };
  let outcome = Promise.resolve();
  const share = control('copy_link', root);
  share.dataset.tdUrl = 'https://example.org/blog/post/';
  const bare = control('copy_link', null); // no context root, no data-td-url
  const fakeWindow = {
    OinkActions: {
      get(id) {
        return id === 'copy_link'
          ? { id, kind: 'copy', available: true, url: 'https://example.org/blog/post/' }
          : null;
      },
      preloadMarkdown() { return Promise.resolve(); },
      run(id, context) { events.run.push({ id, context }); return outcome; },
      resolveUrl() { return null; },
    },
    requestAnimationFrame(callback) { callback(); },
    setTimeout(callback) { events.timers.push(callback); },
  };
  const fakeDocument = {
    querySelectorAll() { return [share, bare]; },
    querySelector() { return null; },
  };
  vm.runInNewContext(source, { window: fakeWindow, document: fakeDocument, Promise });

  // The control's own URL wins, and the confirmation flips the button itself.
  share.listeners.get('click').handler();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(events.run[0].id, 'copy_link');
  assert.equal(events.run[0].context.source, 'page');
  assert.equal(events.run[0].context.value.url, 'https://example.org/blog/post/');
  assert.equal(share.classList.contains('td-is-copied'), true);
  assert.equal(status.textContent, 'Link copied');
  events.timers[0]();
  assert.equal(share.classList.contains('td-is-copied'), false);

  // No data-td-url and no context root: the registry falls back to the
  // descriptor's URL and nothing throws on the way in or out.
  bare.listeners.get('click').handler();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(events.run[1].id, 'copy_link');
  assert.equal(events.run[1].context.source, 'page');
  assert.equal(events.run[1].context.value, null);
  assert.equal(bare.classList.contains('td-is-copied'), true);

  // A denied clipboard announces the failure wording instead of the success.
  outcome = Promise.reject(new Error('clipboard_failed'));
  status.textContent = '';
  share.listeners.get('click').handler();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(status.textContent, 'Could not copy the link');
}

(async () => {
  await testBindings();
  await testTitleMenu();
  await testShareCopy();
  console.log('page action DOM binding checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
