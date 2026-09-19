'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../assets/js/sidebar-state.js'), 'utf8');

function fixture() {
  const events = [];
  const listeners = {};
  const document = {
    readyState: 'loading', activeElement: null,
    addEventListener(name, fn) { listeners[name] = fn; },
    dispatchEvent(event) { events.push(event); if (listeners[event.type]) listeners[event.type](event); },
  };
  function region(id, owned = true) {
    const classes = new Set();
    const target = {
      classList: { toggle(name, value) { if (value) classes.add(name); else classes.delete(name); } },
      contains(el) { return el === target; },
      classes,
    };
    const attrs = new Map([['aria-controls', id], ['aria-expanded', 'false']]);
    const item = { active: false, classList: { contains() { return item.active; } } };
    const owner = { contains(el) { return owned && el === target; } };
    const handlers = [];
    const button = {
      dataset: { tdLabelExpand: '展开', tdLabelCollapse: '收起' },
      closest(selector) { return selector === '.td-shell-tree__item' ? item : owner; },
      getAttribute(name) { return attrs.get(name); },
      setAttribute(name, value) { attrs.set(name, value); },
      addEventListener(name, fn) { handlers.push(fn); },
      focus() { document.activeElement = button; },
    };
    return { id, target, button, item, attrs, handlers };
  }
  const branch = region('branch');
  const aside = region('toc');
  const foreign = region('foreign', false);
  const regions = [branch, aside, foreign];
  document.querySelectorAll = () => regions.map(r => r.button);
  document.getElementById = id => regions.find(r => r.id === id)?.target;
  const context = vm.createContext({ window: {}, document, Promise, Map,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  vm.runInContext(source, context);
  return { context, document, events, listeners, branch, aside, foreign, api: context.window.OinkSidebar };
}

test('commits state and localized labels before exactly one event; no-op writes stay quiet', () => {
  const f = fixture();
  f.document.addEventListener('oink:sidebar-disclosure', event => {
    const r = event.detail.id === 'branch' ? f.branch : f.aside;
    assert.equal(r.attrs.get('aria-expanded'), String(event.detail.expanded));
    assert.equal(r.target.classes.has('td-is-open'), event.detail.expanded);
    assert.equal(r.target.inert, !event.detail.expanded);
    assert.equal(r.attrs.get('aria-label'), event.detail.expanded ? '收起' : '展开');
  });
  assert.equal(f.api.setExpanded('branch', true), true);
  f.api.setExpanded('branch', true);
  assert.equal(f.events.length, 1);
  assert.equal(f.events[0].detail.source, 'api');
  f.branch.handlers[0]();
  assert.equal(f.events.length, 2);
  assert.equal(f.events[1].detail.source, 'user');
  assert.equal(f.api.getState('branch').expanded, false);
});

test('scopes registered targets, protects the active path during restore, and returns focus before hiding', () => {
  const f = fixture();
  assert.equal(f.api.setExpanded('foreign', true), false);
  assert.equal(f.api.setExpanded('missing', true), false);
  assert.equal(f.api.getState('missing'), null);
  assert.equal(f.api.setExpanded('branch', 'false'), false);
  f.branch.item.active = true;
  f.api.setExpanded('branch', true, { source: 'active-path' });
  f.api.setExpanded('branch', false);
  assert.equal(f.api.getState('branch').expanded, true);
  f.document.activeElement = f.branch.target;
  f.branch.handlers[0]();
  assert.equal(f.api.getState('branch').expanded, false);
  assert.equal(f.document.activeElement, f.branch.button);
  // A movable aside remains registered even after its DOM parent changes.
  f.aside.button.closest = () => null;
  f.api.setExpanded('toc', true, { source: 'responsive' });
  assert.equal(f.events.at(-1).detail.source, 'responsive');
  const state = f.api.getState('toc');
  state.expanded = false;
  assert.equal(f.api.getState('toc').expanded, true);
});

test('readiness is safe for late consumers and duplicate initialization adds no listeners', async () => {
  const f = fixture();
  vm.runInContext(source, f.context);
  assert.equal(f.branch.handlers.length, 1);
  assert.equal(f.api.isReady, false);
  f.listeners.DOMContentLoaded();
  f.api.setExpanded('branch', true, { source: 'active-path' });
  await f.api.ready;
  assert.equal(f.api.isReady, true);
  assert.equal(f.api.getState('branch').expanded, true);
  assert.equal(f.events.filter(e => e.type === 'oink:sidebar-ready').length, 1);
  assert.equal(await f.api.ready, f.api);
});
