'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../assets/js/sidebar-nav.js'), 'utf8');

// A cached sidebar as the browser exposes it: every link's href is already
// resolved against the origin that serves the page.
function hydrate({ served, canonical, tree }) {
  const expanded = [];
  const pending = new Set(['data-td-sidebar-hydrate-active']);
  const nodes = {};
  tree.forEach(([href, parent]) => {
    const item = new Set(['td-shell-tree__item--hidden']);
    const row = new Set();
    const link = new Set();
    const attributes = new Map();
    const li = {
      classList: { add(name) { item.add(name); }, remove(name) { item.delete(name); } },
      parentElement: { closest() { return parent ? nodes[parent].li : null; } },
      querySelector() { return { getAttribute() { return href; } }; },
    };
    nodes[href] = {
      li, item, row, link, attributes,
      anchor: {
        href: new URL(href, served + '/').href,
        classList: { add(name) { link.add(name); } },
        setAttribute(name, value) { attributes.set(name, value); },
        closest(selector) {
          return selector === 'li' ? li : { classList: { add(name) { row.add(name); } } };
        },
      },
    };
  });
  const menu = {
    hasAttribute(name) { return pending.has(name); },
    removeAttribute(name) { pending.delete(name); },
    querySelectorAll() { return Object.values(nodes).map(node => node.anchor); },
    getBoundingClientRect() { return {}; },
  };
  vm.runInContext(source, vm.createContext({
    URL,
    window: {
      location: { href: served + new URL(canonical).pathname, origin: served },
      OinkSidebar: { setExpanded(id, open, options) { expanded.push([id, open, options.source]); } },
    },
    document: {
      readyState: 'complete',
      getElementById(id) { return id === 'td-sidebar-menu' ? menu : null; },
      querySelector(selector) { return selector === 'link[rel="canonical"]' ? { href: canonical } : null; },
    },
  }));
  return { nodes, expanded, pending };
}

const DOCS = [
  ['/docs/', null],
  ['/docs/guide/', '/docs/'],
  ['https://elsewhere.example/docs/guide/', null],
];

for (const served of ['https://docs.example.org', 'http://127.0.0.1:1313']) {
  test(`marks the page and opens its branch when served from ${served}`, () => {
    const { nodes, expanded, pending } = hydrate({
      served, canonical: 'https://docs.example.org/docs/guide/', tree: DOCS,
    });
    const page = nodes['/docs/guide/'];
    assert.equal(page.attributes.get('aria-current'), 'page');
    assert.ok(page.link.has('active') && page.row.has('td-shell-active'));
    for (const href of ['/docs/guide/', '/docs/']) {
      assert.ok(nodes[href].item.has('td-active-path'), `${href} is on the active path`);
      assert.ok(!nodes[href].item.has('td-shell-tree__item--hidden'), `${href} is revealed`);
    }
    assert.deepEqual(expanded, [
      ['/docs/guide/', true, 'active-path'],
      ['/docs/', true, 'active-path'],
    ]);
    const external = nodes['https://elsewhere.example/docs/guide/'];
    assert.equal(external.attributes.size, 0, 'a link to another site is not the page');
    assert.ok(!external.item.has('td-active-path'));
    assert.equal(pending.size, 0);
  });
}

test('a link to another site is not an ancestor of a page outside the tree', () => {
  const { nodes, expanded, pending } = hydrate({
    served: 'https://docs.example.org',
    canonical: 'https://docs.example.org/blog/post/',
    tree: [['/docs/', null], ['https://elsewhere.example/', null]],
  });
  for (const node of Object.values(nodes)) {
    assert.ok(!node.item.has('td-active-path'));
    assert.equal(node.attributes.size, 0);
  }
  assert.deepEqual(expanded, []);
  assert.equal(pending.size, 0);
});
