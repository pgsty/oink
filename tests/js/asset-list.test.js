'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const assets = require(path.join(__dirname, '..', '..', 'assets/js/asset-list.js'));

function element(attributes = {}) {
  const values = new Map(Object.entries(attributes));
  return {
    attributes: values,
    disabled: false,
    hidden: true,
    textContent: '',
    setAttribute(name, value) { values.set(name, String(value)); },
    getAttribute(name) { return values.has(name) ? values.get(name) : null; },
    hasAttribute(name) { return values.has(name); },
    querySelector() { return null; },
  };
}

function row(hash, name, binary = false) {
  const item = element({ 'data-td-asset-hash': hash, 'data-td-asset-name': name });
  if (binary) item.setAttribute('data-td-asset-binary', '');
  return item;
}

const first = row('a'.repeat(64), 'pig arm64.rpm');
const second = row('b'.repeat(64), 'pig-amd64.rpm', true);
assert.equal(assets.checksumLine(first), `${'a'.repeat(64)}  pig arm64.rpm`);
assert.equal(assets.checksumLine(second), `${'b'.repeat(64)} *pig-amd64.rpm`);
assert.equal(
  assets.allChecksumLines({ querySelectorAll() { return [first, second]; } }),
  `${'a'.repeat(64)}  pig arm64.rpm\n${'b'.repeat(64)} *pig-amd64.rpm\n`,
);

(async () => {
  const writes = [];
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
  const originalSetTimeout = globalThis.setTimeout;
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: { clipboard: { writeText(text) { writes.push(text); return Promise.resolve(); } } },
  });
  globalThis.setTimeout = () => 1;

  const status = element();
  const icon = element();
  const label = element();
  const root = {
    contains(candidate) { return candidate === button; },
    querySelector(selector) {
      return selector === '[data-td-asset-status]' ? status : null;
    },
    querySelectorAll(selector) {
      return selector === '[data-td-asset]' ? [first, second] : [];
    },
  };
  const button = element({
    'data-td-asset-copy': '',
    'data-td-label-copy': 'Copy checksum',
    'data-td-label-copied': 'Copied',
  });
  button.closest = (selector) => {
    if (selector === '[data-td-asset-list]') return root;
    if (selector === '[data-td-asset]') return first;
    return null;
  };
  button.querySelector = (selector) => {
    if (selector === 'i') return icon;
    if (selector === 'span') return label;
    return null;
  };

  assert.equal(await assets.copyFromControl(button, {}), true);
  assert.deepEqual(writes, [`${'a'.repeat(64)}  pig arm64.rpm\n`]);
  assert.equal(button.getAttribute('data-td-state'), 'success');
  assert.equal(button.getAttribute('aria-label'), 'Copied');
  assert.equal(label.textContent, 'Copied');
  assert.equal(status.textContent, 'Copied');
  assert.equal(icon.className, 'fa-solid fa-check');

  button.disabled = false;
  button.setAttribute('data-td-asset-copy-all', '');
  assert.equal(await assets.copyFromControl(button, {}), true);
  assert.equal(writes[1], assets.allChecksumLines(root));

  const fallbackWrites = [];
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: { clipboard: { writeText() { throw new Error('denied'); } } },
  });
  const textarea = {
    style: {},
    setAttribute() {},
    select() {},
    setSelectionRange() {},
    remove() {},
  };
  const doc = {
    body: { appendChild(node) { fallbackWrites.push(node.value); } },
    createElement(tag) { assert.equal(tag, 'textarea'); return textarea; },
    execCommand(command) { assert.equal(command, 'copy'); return true; },
  };
  await assets.writeClipboard('fallback\n', doc);
  assert.deepEqual(fallbackWrites, ['fallback\n']);

  const controls = [element(), element()];
  const listeners = new Map();
  const initRoot = {
    ready: false,
    hasAttribute(name) { return name === 'data-td-asset-list-ready' && this.ready; },
    setAttribute(name) { if (name === 'data-td-asset-list-ready') this.ready = true; },
    querySelectorAll() { return controls; },
    addEventListener(name, callback) { listeners.set(name, callback); },
  };
  const scope = {
    ownerDocument: {},
    querySelectorAll(selector) {
      assert.equal(selector, '[data-td-asset-list]');
      return [initRoot];
    },
  };
  assert.equal(assets.init(scope), 1);
  assert.equal(controls.every((control) => control.hidden === false), true);
  assert.equal(typeof listeners.get('click'), 'function');
  assert.equal(assets.init(scope), 0);

  globalThis.setTimeout = originalSetTimeout;
  if (originalNavigator) Object.defineProperty(globalThis, 'navigator', originalNavigator);
  else delete globalThis.navigator;
  console.log('asset-list runtime checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
