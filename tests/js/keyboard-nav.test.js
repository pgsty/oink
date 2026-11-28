'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const nav = require(path.join(__dirname, '..', '..', 'assets/js/keyboard-nav.js'));

function classes(initial = '') {
  const values = new Set(initial.split(/\s+/).filter(Boolean));
  return {
    add(...items) { items.forEach((item) => values.add(item)); },
    remove(...items) { items.forEach((item) => values.delete(item)); },
    toggle(item, force) {
      const on = force === undefined ? !values.has(item) : force;
      if (on) values.add(item); else values.delete(item);
    },
    contains(item) { return values.has(item); },
  };
}

class Element {
  constructor(tag = 'div', className = '') {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.attributes = new Map();
    this.dataset = {};
    this.classList = classes(className);
    this._className = className;
    this.id = '';
    this.nodeType = 1;
    this.offsetParent = {};
    this.style = {
      scrollBehavior: '',
      props: {},
      setProperty(name, value) { this.props[name] = String(value); },
      removeProperty(name) { delete this.props[name]; },
    };
    this.clicks = 0;
    this.textContent = '';
    this.ownerDocument = null;
    this.listeners = new Map();
    this.open = false;
  }
  get parentElement() { return this.parentNode && this.parentNode.tagName ? this.parentNode : null; }
  get className() { return this._className; }
  set className(value) {
    this._className = String(value || '');
    this.classList = classes(this._className);
  }
  appendChild(child) {
    child.parentNode = this;
    child.ownerDocument = this.ownerDocument;
    this.children.push(child);
    return child;
  }
  setAttribute(name, value) {
    const str = String(value);
    this.attributes.set(name, str);
    if (name === 'id') this.id = str;
    if (name === 'open') this.open = true;
  }
  getAttribute(name) {
    if (name === 'id' && this.id) return this.id;
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }
  hasAttribute(name) {
    if (name === 'id' && this.id) return true;
    return this.attributes.has(name);
  }
  removeAttribute(name) {
    this.attributes.delete(name);
    if (name === 'id') this.id = '';
    if (name === 'open') this.open = false;
  }
  addEventListener(name, callback) {
    const callbacks = this.listeners.get(name) || [];
    callbacks.push(callback);
    this.listeners.set(name, callbacks);
  }
  dispatchEvent(event) {
    (this.listeners.get(event.type) || []).forEach((fn) => fn(event));
  }
  showModal() {
    this.open = true;
    this.modal = true;
    this.attributes.set('open', '');
  }
  close() {
    this.open = false;
    this.modal = false;
    this.attributes.delete('open');
    this.dispatchEvent({ type: 'close', target: this });
  }
  cloneNode(deep = false) {
    const copy = new Element(this.tagName.toLowerCase(), this._className);
    copy.id = this.id;
    copy.textContent = this.textContent;
    this.attributes.forEach((value, key) => copy.attributes.set(key, value));
    if (deep) {
      this.children.forEach((child) => copy.appendChild(child.cloneNode(true)));
    }
    return copy;
  }
  matches(selector) {
    if (selector.includes(',')) {
      return selector.split(',').some((part) => this.matches(part.trim()));
    }
    if (selector === 'a.td-shell-tree__link') {
      return this.tagName === 'A' && this.classList.contains('td-shell-tree__link');
    }
    if (selector === 'a[href^="#"]') {
      return this.tagName === 'A' && String(this.getAttribute('href') || '').startsWith('#');
    }
    if (selector === '[data-td-shell-tree-toggle]') return this.hasAttribute('data-td-shell-tree-toggle');
    if (selector === '[data-td-shell-drawer-open]') return this.hasAttribute('data-td-shell-drawer-open');
    if (selector === '[data-td-shell-sidebar-toggle]') return this.hasAttribute('data-td-shell-sidebar-toggle');
    if (selector === '[role="dialog"]') return this.getAttribute('role') === 'dialog';
    if (selector === '.td-kbd-focus') return this.classList.contains('td-kbd-focus');
    if (selector === '.td-shell-tree__row') return this.classList.contains('td-shell-tree__row');
    if (selector === ':modal') return this.modal === true;
    if (selector === 'dialog[open]') return this.tagName === 'DIALOG' && this.hasAttribute('open');
    if (selector === '#TableOfContents') return this.id === 'TableOfContents';
    if (selector === 'link[rel="canonical"]') return this.tagName === 'LINK' && this.getAttribute('rel') === 'canonical';
    if (selector === 'link[rel="prev"]') return this.tagName === 'LINK' && this.getAttribute('rel') === 'prev';
    if (selector === 'link[rel="next"]') return this.tagName === 'LINK' && this.getAttribute('rel') === 'next';
    if (selector === '[data-td-pager]') return this.hasAttribute('data-td-pager');
    if (selector === '[data-td-pager-prev][href]') return this.hasAttribute('data-td-pager-prev') && this.hasAttribute('href');
    if (selector === '[data-td-pager-next][href]') return this.hasAttribute('data-td-pager-next') && this.hasAttribute('href');
    if (selector === '[data-td-navbar-route][href]') return this.hasAttribute('data-td-navbar-route') && this.hasAttribute('href');
    if (selector === '[data-td-language-route][href]') return this.hasAttribute('data-td-language-route') && this.hasAttribute('href');
    if (selector === '[data-td-keyboard-search-route][href]') return this.hasAttribute('data-td-keyboard-search-route') && this.hasAttribute('href');
    if (selector === '[data-td-landing]') return this.hasAttribute('data-td-landing');
    if (selector === '[data-td-theme-toggle]') return this.hasAttribute('data-td-theme-toggle');
    if (selector === '.td-shell-keyboard-help') return this.classList.contains('td-shell-keyboard-help');
    if (selector === '.td-shell-keyboard__trigger') return this.classList.contains('td-shell-keyboard__trigger');
    if (selector === '[data-td-nav-hover]') return this.hasAttribute('data-td-nav-hover');
    if (selector === '.td-shell-keyboard-help__section') return this.classList.contains('td-shell-keyboard-help__section');
    if (selector === '.td-shell-keyboard-help__header .td-shell-icon') {
      return this.classList.contains('td-shell-icon') &&
        Boolean(this.parentNode && this.parentNode.classList.contains('td-shell-keyboard-help__header'));
    }
    if (selector === '.td-shell-keyboard-help__header strong') {
      return this.tagName === 'STRONG' &&
        Boolean(this.parentNode && this.parentNode.classList.contains('td-shell-keyboard-help__header'));
    }
    if (selector === 'template[data-td-keyboard-help-source]') {
      return this.tagName === 'TEMPLATE' && this.hasAttribute('data-td-keyboard-help-source');
    }
    if (selector === '[data-td-keyboard-dialog]') return this.hasAttribute('data-td-keyboard-dialog');
    if (selector === '[data-td-keyboard-dialog-close]') return this.hasAttribute('data-td-keyboard-dialog-close');
    if (selector === '[data-td-blog-index-toggle]') return this.hasAttribute('data-td-blog-index-toggle');
    if (selector === '[data-td-expo]') return this.hasAttribute('data-td-expo');
    if (selector === '[data-td-expo-controls]') return this.hasAttribute('data-td-expo-controls');
    if (selector === 'input[data-td-expo-mode]') return this.tagName === 'INPUT' && this.hasAttribute('data-td-expo-mode');
    if (selector === 'input[data-td-expo-size]') return this.tagName === 'INPUT' && this.hasAttribute('data-td-expo-size');
    if (selector === '[data-td-blog-gallery]') return this.hasAttribute('data-td-blog-gallery');
    if (selector === '[data-gallery-controls]') return this.hasAttribute('data-gallery-controls');
    if (selector === 'input[data-gallery-mode]') return this.tagName === 'INPUT' && this.hasAttribute('data-gallery-mode');
    if (selector === 'input[data-gallery-size]') return this.tagName === 'INPUT' && this.hasAttribute('data-gallery-size');
    if (selector === '[data-td-shortcut]') return this.hasAttribute('data-td-shortcut');
    if (selector === '[data-td-shortcut-state]') return this.hasAttribute('data-td-shortcut-state');
    if (selector === '[data-td-map-canvas]') return this.hasAttribute('data-td-map-canvas');
    if (selector === '.td-map__canvas') return this.classList.contains('td-map__canvas');
    if (selector === '[hidden]') return Boolean(this.hidden) || this.hasAttribute('hidden');
    if (selector === '[inert]') return Boolean(this.inert) || this.hasAttribute('inert');
    if (selector === '.td-site-header') return this.classList.contains('td-site-header');
    if (selector === '.td-shell-sidebar__panel') return this.classList.contains('td-shell-sidebar__panel');
    if (selector === '.td-shell-toc__panel') return this.classList.contains('td-shell-toc__panel');
    if (selector === '#td-shell-sidebar') return this.id === 'td-shell-sidebar';
    if (selector === '[data-td-shell-aside]') return this.hasAttribute('data-td-shell-aside');
    if (selector === '.td-shell-article .td-content') {
      return this.classList.contains('td-content') && Boolean(this.closest && this.closest('.td-shell-article'));
    }
    if (selector === '.td-shell-article') return this.classList.contains('td-shell-article');
    if (selector === '.td-shell-main') return this.classList.contains('td-shell-main');
    if (selector === '[data-td-shell-tree-toggle][aria-controls]') {
      return this.hasAttribute('data-td-shell-tree-toggle') && this.hasAttribute('aria-controls');
    }
    if (selector === '[data-td-code].is-collapsible') {
      return this.hasAttribute('data-td-code') && this.classList.contains('is-collapsible');
    }
    if (selector === '[data-td-code-expand]') return this.hasAttribute('data-td-code-expand');
    if (selector === '.td-shell-layout .td-shell-article') return this.classList.contains('td-shell-article');
    if (selector === '[data-td-compare-open]') return this.hasAttribute('data-td-compare-open');
    if (/^[a-z][a-z0-9]*$/.test(selector)) return this.tagName === selector.toUpperCase();
    return false;
  }
  querySelectorAll(selector) {
    const found = [];
    const visit = (node) => {
      if (node.matches && node.matches(selector)) found.push(node);
      (node.children || []).forEach(visit);
    };
    this.children.forEach(visit);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  contains(candidate) {
    return candidate === this ||
      this.children.some((child) => child.contains && child.contains(candidate));
  }
  closest(selector) {
    for (let node = this; node; node = node.parentNode) {
      if (node.matches && node.matches(selector)) return node;
    }
    return null;
  }
  focus() { if (this.ownerDocument) this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument) this.ownerDocument.activeElement = null; }
  click() {
    this.clicks += 1;
    if (this.onclick) this.onclick();
    this.dispatchEvent({ type: 'click', target: this });
  }
  scrollIntoView() {}
  getBoundingClientRect() { return { top: 0 }; }
  getClientRects() { return this.hidden ? [] : [{}]; }
}

function link(href, className = '') {
  const el = new Element('a', 'td-shell-tree__link ' + className);
  el.setAttribute('href', href);
  return el;
}

// A foldable tree matching the sidebar markup: row + chevron + children div.
// Chevron clicks mimic docs-shell.js (flip aria-expanded, toggle td-is-open).
function treeItem({ href, className = '', expanded = null, children = [], groupOnly = false }) {
  const item = new Element('li', 'td-shell-tree__item ' + className);
  const row = new Element('div', 'td-shell-tree__row');
  const anchor = groupOnly ? new Element('span', 'td-shell-tree__link td-shell-tree__group') : link(href);
  row.appendChild(anchor);
  item.appendChild(row);
  let childWrap = null;
  if (children.length) {
    childWrap = new Element('div', 'td-shell-tree__children' + (expanded ? ' td-is-open' : ''));
    const list = new Element('ul');
    children.forEach((child) => list.appendChild(child));
    childWrap.appendChild(list);
  }
  if (expanded !== null) {
    const chevron = new Element('button');
    chevron.setAttribute('data-td-shell-tree-toggle', '');
    chevron.setAttribute('aria-expanded', String(expanded));
    chevron.onclick = () => {
      const open = chevron.getAttribute('aria-expanded') === 'true';
      chevron.setAttribute('aria-expanded', String(!open));
      if (childWrap) {
        if (open) childWrap.classList.remove('td-is-open');
        else childWrap.classList.add('td-is-open');
      }
    };
    row.appendChild(chevron);
  }
  if (childWrap) item.appendChild(childWrap);
  return item;
}

function memoryStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem(key) { return store.has(key) ? store.get(key) : null; },
    setItem(key, value) { store.set(key, String(value)); },
    removeItem(key) { store.delete(key); },
  };
}

function helpPanelFixture(title = 'Keyboard shortcuts', closeLabel = 'Close') {
  const help = new Element('div', 'td-shell-keyboard-help');
  help.setAttribute('aria-label', title);
  help.setAttribute('data-td-close-label', closeLabel);
  help.setAttribute('data-td-unavailable-label', 'unavailable');
  const header = new Element('div', 'td-shell-keyboard-help__header');
  const icon = new Element('i', 'td-shell-icon td-shell-icon--circle-question fa-solid fa-circle-question');
  icon.setAttribute('aria-hidden', 'true');
  const strong = new Element('strong');
  strong.textContent = title;
  header.appendChild(icon);
  header.appendChild(strong);
  help.appendChild(header);
  const groups = {
    navigation: ['tree-move', 'language', 'history', 'home'],
    actions: ['search', 'expand-all', 'print', 'claude'],
    view: ['page-width', 'help'],
  };
  for (const [group, rows] of Object.entries(groups)) {
    const id = 'td-shell-shortcuts-' + group;
    const section = new Element('section', 'td-shell-keyboard-help__section');
    section.setAttribute('aria-labelledby', id);
    const heading = new Element('h3', 'td-shell-keyboard-help__section-title');
    heading.setAttribute('id', id);
    heading.textContent = group;
    section.appendChild(heading);
    const list = new Element('dl');
    for (const shortcut of rows) {
      const row = new Element('div', 'td-shell-keyboard-help__row');
      row.setAttribute('data-td-shortcut', shortcut);
      row.appendChild(new Element('dt'));
      const label = new Element('dd');
      label.textContent = shortcut;
      row.appendChild(label);
      list.appendChild(row);
    }
    section.appendChild(list);
    help.appendChild(section);
  }
  return help;
}

function setup({
  withTree = true,
  drawerOpener = false,
  sidebarToggle = false,
  registry = null,
  palette = null,
  coordinator = null,
  withHelp = false,
  withHelpTemplate = false,
  reducedMotion = true,
  scrollPadding = null,
  scrollMargin = '0px',
  session = {},
  shell = true,
  home = false,
  local = {},
  history = null,
} = {}) {
  const html = new Element('html');
  const root = new Element(
    'body',
    shell ? 'td-shell-chrome' : (home ? 'td-home' : ''),
  );
  const doc = {
    documentElement: html,
    activeElement: null,
    listeners: new Map(),
    body: root,
    createElement(tag) {
      const el = new Element(tag);
      el.ownerDocument = doc;
      return el;
    },
    addEventListener(name, callback) {
      const callbacks = this.listeners.get(name) || [];
      callbacks.push(callback);
      this.listeners.set(name, callbacks);
    },
    getElementById(id) { return findById(root, id); },
    querySelector(selector) { return root.querySelector(selector); },
    querySelectorAll(selector) { return root.querySelectorAll(selector); },
    contains(candidate) { return root.contains(candidate); },
  };
  function findById(node, id) {
    if (node.id === id) return node;
    for (const child of node.children || []) {
      const hit = findById(child, id);
      if (hit) return hit;
    }
    return null;
  }
  const own = (node) => {
    node.ownerDocument = doc;
    (node.children || []).forEach(own);
  };

  const frames = [];
  const timeouts = [];
  const winListeners = new Map();
  const win = {
    scrolled: [],
    scrolledTo: [],
    assigned: [],
    hashes: [],
    printed: 0,
    location: { href: 'https://example.test/docs/b/one/', pathname: '/docs/b/one/', search: '' },
    print() { this.printed += 1; },
    scrollBy(x, y) { this.scrolled.push(y); },
    scrollTo(x, y) { this.scrolledTo.push(y); this.scrollY = y; },
    scrollY: 0,
    requestAnimationFrame(callback) { frames.push(callback); },
    matchMedia() { return { matches: reducedMotion }; },
    setTimeout(callback) { timeouts.push(callback); return timeouts.length; },
    clearTimeout() {},
    addEventListener(name, callback) {
      const callbacks = winListeners.get(name) || [];
      callbacks.push(callback);
      winListeners.set(name, callbacks);
    },
    dispatchEvent(event) {
      (winListeners.get(event.type) || []).forEach((fn) => fn(event));
    },
    sessionStorage: memoryStorage(session),
    localStorage: memoryStorage(local),
    history: { replaceState(state, title, url) { win.hashes.push(url); } },
  };
  win.location.assign = (url) => win.assigned.push(url);
  if (scrollPadding !== null) {
    win.getComputedStyle = (element) => ({
      display: 'block',
      visibility: 'visible',
      getPropertyValue(name) {
        if (element === html && name === 'scroll-padding-top') return scrollPadding;
        if (element === html && name === '--td-shell-nav-h') return '3.5rem';
        if (name === 'scroll-margin-block-start' || name === 'scroll-margin-top') {
          return scrollMargin;
        }
        return '';
      },
    });
  }

  let tree = null;
  if (withTree) {
    const menu = new Element('div');
    menu.id = 'td-sidebar-menu';
    const list = new Element('ul');
    tree = {
      a: treeItem({ href: '/docs/a/' }),
      b: treeItem({
        href: '/docs/b/',
        expanded: true,
        children: [treeItem({ href: '/docs/b/one/' })],
      }),
      c: treeItem({
        href: '/docs/c/',
        expanded: false,
        children: [treeItem({ href: '/docs/c/one/' })],
      }),
      hidden: treeItem({ href: '/docs/d/', className: 'td-shell-tree__item--hidden' }),
    };
    tree.active = tree.b.querySelectorAll('a.td-shell-tree__link')[1];
    tree.active.classList.add('active');
    Object.values(tree).forEach((item) => {
      if (item instanceof Element && item.tagName === 'LI') list.appendChild(item);
    });
    menu.appendChild(list);
    root.appendChild(menu);
    tree.menu = menu;
  }

  if (drawerOpener) {
    const opener = new Element('button');
    opener.setAttribute('data-td-shell-drawer-open', '');
    root.appendChild(opener);
  }

  if (sidebarToggle) {
    const toggle = new Element('button');
    toggle.setAttribute('data-td-shell-sidebar-toggle', '');
    root.appendChild(toggle);
  }

  // The sheet is always template content: the footer only carries a hint.
  if (withHelp || withHelpTemplate) {
    const tpl = new Element('template');
    tpl.setAttribute('data-td-keyboard-help-source', '');
    const fragment = new Element('div');
    fragment.appendChild(withHelpTemplate
      ? helpPanelFixture('键盘快捷键', '关闭')
      : helpPanelFixture());
    tpl.content = fragment;
    root.appendChild(tpl);
  }

  own(root);
  own(html);

  const controller = nav.init({ document: doc, window: win, registry, palette, coordinator, history });
  return { doc, win, html, root, tree, frames, timeouts, controller };
}

function press(harness, values) {
  const event = {
    key: '',
    keyCode: 0,
    isComposing: false,
    metaKey: false,
    ctrlKey: false,
    altKey: false,
    shiftKey: false,
    target: harness.root,
    preventDefault() { this.defaultPrevented = true; },
    ...values,
  };
  (harness.doc.listeners.get('keydown') || []).forEach((fn) => fn(event));
  return event;
}

(() => {
  // ---------------------------------------------------------- typing guard
  const input = new Element('input');
  const textInput = new Element('input');
  textInput.setAttribute('type', 'search');
  const numInput = new Element('input');
  numInput.setAttribute('type', 'number');
  const radioInput = new Element('input');
  radioInput.setAttribute('type', 'radio');
  const rangeInput = new Element('input');
  rangeInput.setAttribute('type', 'range');
  const checkboxInput = new Element('input');
  checkboxInput.setAttribute('type', 'checkbox');
  const textarea = new Element('textarea');
  const select = new Element('select');
  const editable = new Element('div');
  editable.closest = (selector) =>
    selector.includes('contenteditable') ? editable : null;
  const plain = new Element('div');
  plain.closest = () => null;
  assert.equal(nav.isTypingTarget(input), true);
  assert.equal(nav.isTypingTarget(textInput), true);
  assert.equal(nav.isTypingTarget(numInput), true);
  assert.equal(nav.isTypingTarget(textarea), true);
  assert.equal(nav.isTypingTarget(select), true);
  assert.equal(nav.isTypingTarget(editable), true);
  assert.equal(nav.isTypingTarget(radioInput), false);
  assert.equal(nav.isTypingTarget(rangeInput), false);
  assert.equal(nav.isTypingTarget(checkboxInput), false);
  assert.equal(nav.isTypingTarget(plain), false);
  assert.equal(nav.isTypingTarget(null), false);

  // ------------------------------------------------------ flattened links
  const flat = setup();
  const visible = nav.visibleTreeLinks(flat.tree.menu);
  assert.deepEqual(
    visible.map((el) => el.getAttribute('href')),
    ['/docs/a/', '/docs/b/', '/docs/b/one/', '/docs/c/'],
    'visible links must skip collapsed children and hidden items',
  );
  const hiddenMenu = new Element('div', 'd-none');
  assert.deepEqual(nav.visibleTreeLinks(hiddenMenu), [], 'a d-none menu has no links');
  assert.deepEqual(nav.visibleTreeLinks(null), [], 'a missing menu has no links');

  // ------------------------------------------------------------ guards
  const guard = setup({ withTree: false });
  for (const values of [
    { key: 'j', isComposing: true },
    { key: 'j', keyCode: 229 },
    { key: 'j', metaKey: true },
    { key: 'j', ctrlKey: true },
    { key: 'j', altKey: true },
    { key: 'j', shiftKey: true },
    { key: 'j', target: input },
  ]) {
    press(guard, values);
    assert.equal(guard.win.scrolled.length, 0, `guard failed for ${JSON.stringify(values)}`);
  }
  guard.html.setAttribute('data-td-shell-lock', '');
  press(guard, { key: 'j' });
  assert.equal(guard.win.scrolled.length, 0, 'palette lock did not suppress shortcuts');
  guard.html.removeAttribute('data-td-shell-lock');
  const dialog = new Element('dialog');
  dialog.setAttribute('open', '');
  guard.root.appendChild(dialog);
  press(guard, { key: 'j' });
  assert.equal(guard.win.scrolled.length, 0, 'open dialog did not suppress shortcuts');
  guard.root.children.pop();
  press(guard, { key: 'J' });
  assert.equal(guard.win.scrolled.length, 0, 'shifted key must not scroll');

  const ariaDialog = new Element('div');
  ariaDialog.setAttribute('role', 'dialog');
  ariaDialog.offsetParent = null;
  guard.root.appendChild(ariaDialog);
  press(guard, { key: 'j' });
  assert.equal(guard.win.scrolled.length, 0, 'visible ARIA dialog did not suppress shortcuts');
  guard.root.children.pop();

  // -------------------------------------- j/k fall back to plain scrolling
  press(guard, { key: 'j' });
  press(guard, { key: 'k' });
  assert.deepEqual(
    guard.win.scrolled,
    [300, -300],
    'without an outline j/k step-scroll instantly under reduced motion',
  );

  // ------------------------------------------------- j/k outline jumping
  const outline = setup({ withTree: false });
  outline.html.scrollHeight = 4000;
  outline.win.innerHeight = 800;
  const toc = new Element('nav');
  toc.id = 'TableOfContents';
  for (const id of ['first', 'second']) {
    const anchor = new Element('a');
    anchor.setAttribute('href', '#' + id);
    toc.appendChild(anchor);
  }
  const headings = { first: 500, second: 1600 };
  for (const [id, top] of Object.entries(headings)) {
    const heading = new Element('h2');
    heading.id = id;
    heading.getBoundingClientRect = () => ({ top: top - outline.win.scrollY });
    outline.root.appendChild(heading);
  }
  outline.root.appendChild(toc);
  outline.root.children.forEach((node) => { node.ownerDocument = outline.doc; });

  press(outline, { key: 'j' });
  assert.deepEqual(
    outline.win.scrolledTo,
    [476],
    'j glides to the first heading minus the nav margin',
  );
  assert.deepEqual(outline.win.hashes, ['#first'], 'the hash follows the jump');

  const paddedOutline = setup({
    withTree: false,
    scrollPadding: '80px',
  });
  paddedOutline.html.scrollHeight = 4000;
  paddedOutline.win.innerHeight = 800;
  const paddedToc = new Element('nav');
  paddedToc.id = 'TableOfContents';
  const paddedAnchor = new Element('a');
  paddedAnchor.setAttribute('href', '#padded-heading');
  paddedToc.appendChild(paddedAnchor);
  const paddedHeading = new Element('h2');
  paddedHeading.id = 'padded-heading';
  paddedHeading.getBoundingClientRect = () => ({
    top: 500 - paddedOutline.win.scrollY,
  });
  paddedOutline.root.appendChild(paddedHeading);
  paddedOutline.root.appendChild(paddedToc);
  press(paddedOutline, { key: 'j' });
  assert.deepEqual(
    paddedOutline.win.scrolledTo,
    [420],
    'j uses resolved scroll-padding-top instead of parsing a rem navbar token as px',
  );

  press(outline, { key: 'j' });
  assert.equal(outline.win.scrolledTo[1], 1576, 'j continues to the next heading');
  press(outline, { key: 'j' });
  assert.equal(outline.win.scrolledTo.length, 2, 'the last heading dwells');

  outline.win.scrollY = 900; // deep inside the first section
  press(outline, { key: 'k' });
  assert.equal(
    outline.win.scrolledTo[2],
    476,
    'k first re-anchors at the current section start',
  );
  press(outline, { key: 'k' });
  assert.equal(outline.win.scrolledTo[3], 0, 'k from a section start goes to the top');
  assert.equal(
    outline.win.hashes[outline.win.hashes.length - 1],
    '/docs/b/one/',
    'the top jump clears the hash',
  );

  // A normal-motion jump finishes in 100ms regardless of distance. Repeated
  // keys advance the queued outline cursor before the first frame runs.
  const fastOutline = setup({ withTree: false, reducedMotion: false });
  fastOutline.html.scrollHeight = 4000;
  fastOutline.win.innerHeight = 800;
  const fastToc = new Element('nav');
  fastToc.id = 'TableOfContents';
  for (const id of ['fast-first', 'fast-second']) {
    const anchor = new Element('a');
    anchor.setAttribute('href', '#' + id);
    fastToc.appendChild(anchor);
  }
  for (const [id, top] of [['fast-first', 500], ['fast-second', 1600]]) {
    const heading = new Element('h2');
    heading.id = id;
    heading.getBoundingClientRect = () => ({
      top: top - fastOutline.win.scrollY,
    });
    fastOutline.root.appendChild(heading);
  }
  fastOutline.root.appendChild(fastToc);
  fastOutline.root.children.forEach((node) => {
    node.ownerDocument = fastOutline.doc;
  });

  press(fastOutline, { key: 'j' });
  press(fastOutline, { key: 'j' });
  assert.deepEqual(
    fastOutline.win.hashes,
    ['#fast-first', '#fast-second'],
    'rapid j presses advance the queued outline cursor',
  );
  fastOutline.frames.shift()(0);
  fastOutline.html.style.scrollBehavior = 'smooth';
  fastOutline.frames.shift()(50);
  assert.ok(
    fastOutline.win.scrollY > 1300,
    'the cubic ease-out covers most of a long jump in its first 50ms',
  );
  fastOutline.frames.shift()(100);
  assert.equal(
    fastOutline.win.scrollY,
    1576,
    'the queued second-heading jump lands exactly within 100ms',
  );
  assert.equal(
    fastOutline.html.style.scrollBehavior,
    'smooth',
    'the fast glide restores the site scroll behavior after each frame',
  );
  assert.equal(fastOutline.frames.length, 0, 'the fast jump queues no tail frames');

  // ------------------------------------------------- one-step tree focus
  const ws = setup();
  press(ws, { key: 's' });
  assert.equal(
    ws.doc.activeElement && ws.doc.activeElement.getAttribute('href'),
    '/docs/c/',
    'the first s already moves past the active item',
  );
  const focusRows = ws.tree.menu.querySelectorAll('.td-kbd-focus');
  assert.equal(focusRows.length, 1, 'the focused row carries the highlight');
  assert.ok(
    focusRows[0].classList.contains('td-shell-tree__row'),
    'the highlight sits on the row, not the link',
  );
  press(ws, { key: 's' });
  assert.equal(ws.doc.activeElement.getAttribute('href'), '/docs/c/', 'bottom edge dwells');
  press(ws, { key: 'w' });
  press(ws, { key: 'ArrowUp' });
  assert.equal(ws.doc.activeElement.getAttribute('href'), '/docs/b/', 'w and ArrowUp move up');

  const up = setup();
  press(up, { key: 'w' });
  assert.equal(
    up.doc.activeElement.getAttribute('href'),
    '/docs/b/',
    'the first w already moves before the active item',
  );

  // ---------------------------------------- one-step collapse and expand
  const fold = setup();
  press(fold, { key: 'a' });
  assert.equal(
    fold.doc.activeElement.getAttribute('href'),
    '/docs/b/',
    'a from outside lands on the active leaf and jumps to its parent',
  );
  press(fold, { key: 'a' });
  const bChevron = fold.tree.b.querySelector('[data-td-shell-tree-toggle]');
  assert.equal(bChevron.getAttribute('aria-expanded'), 'false', 'a collapses the group');
  press(fold, { key: 'd' });
  assert.equal(bChevron.getAttribute('aria-expanded'), 'true', 'd expands it again');
  press(fold, { key: 'd' });
  assert.equal(
    fold.doc.activeElement.getAttribute('href'),
    '/docs/b/one/',
    'd on an expanded item steps into the first child',
  );

  // Non-link groups participate in focus navigation through their disclosure
  // button, while q/e continue to visit only page links.
  const grouped = setup({ withTree: false });
  const groupedMenu = new Element('div');
  groupedMenu.id = 'td-sidebar-menu';
  const groupedList = new Element('ul');
  const beforeGroup = treeItem({ href: '/docs/before/' });
  const firstGrouped = treeItem({ href: '/docs/group/one/' });
  const secondGrouped = treeItem({ href: '/docs/group/two/' });
  const groupOnly = treeItem({ groupOnly: true, expanded: true, children: [firstGrouped, secondGrouped] });
  const afterGroup = treeItem({ href: '/docs/after/' });
  [beforeGroup, groupOnly, afterGroup].forEach(item => groupedList.appendChild(item));
  groupedMenu.appendChild(groupedList);
  grouped.root.appendChild(groupedMenu);
  (function own(node) {
    node.ownerDocument = grouped.doc;
    node.children.forEach(own);
  })(groupedMenu);
  const groupToggle = groupOnly.querySelector('[data-td-shell-tree-toggle]');
  groupToggle.id = 'group-toggle';
  const groupedFirstLink = firstGrouped.querySelector('a.td-shell-tree__link');
  const groupedSecondLink = secondGrouped.querySelector('a.td-shell-tree__link');
  groupedSecondLink.classList.add('active');
  grouped.win.location.href = 'https://example.test/docs/group/two/';

  for (const [dir, collapseKey, expandKey] of [
    ['ltr', 'ArrowLeft', 'ArrowRight'],
    ['ltr', 'a', 'd'],
    ['rtl', 'ArrowRight', 'ArrowLeft'],
  ]) {
    grouped.html.setAttribute('dir', dir);
    groupedSecondLink.focus();
    press(grouped, { key: collapseKey });
    assert.equal(grouped.doc.activeElement.id, 'group-toggle', `${collapseKey} returns to the direct parent group`);
    press(grouped, { key: collapseKey });
    assert.equal(groupToggle.getAttribute('aria-expanded'), 'false', `${collapseKey} collapses a non-link group`);
    press(grouped, { key: expandKey });
    assert.equal(groupToggle.getAttribute('aria-expanded'), 'true', `${expandKey} expands a non-link group`);
    press(grouped, { key: expandKey });
    assert.equal(grouped.doc.activeElement, groupedFirstLink, `${expandKey} enters the first group child`);
  }
  grouped.html.setAttribute('dir', 'ltr');
  press(grouped, { key: 'w' });
  assert.equal(grouped.doc.activeElement.id, 'group-toggle', 'w visits the non-link group before its first child');
  press(grouped, { key: 'w' });
  assert.equal(grouped.doc.activeElement.getAttribute('href'), '/docs/before/', 'w leaves the group for the preceding row');
  press(grouped, { key: 's' });
  assert.equal(grouped.doc.activeElement.id, 'group-toggle', 's includes the group disclosure in focus order');
  press(grouped, { key: 'ArrowDown' });
  assert.equal(grouped.doc.activeElement, groupedFirstLink, 'ArrowDown enters an expanded group');
  press(grouped, { key: 'ArrowDown' });
  assert.equal(grouped.doc.activeElement, groupedSecondLink, 'ArrowDown preserves child order');
  press(grouped, { key: 'a' });
  press(grouped, { key: 'a' });
  press(grouped, { key: 's' });
  assert.equal(grouped.doc.activeElement.getAttribute('href'), '/docs/after/', 's skips the closed group children');
  press(grouped, { key: 'w' });
  assert.equal(grouped.doc.activeElement.id, 'group-toggle', 'w can reach the collapsed group again');
  press(grouped, { key: 'd' });
  assert.deepEqual(nav.visibleTreeLinks(groupedMenu).map(el => el.getAttribute('href')),
    ['/docs/before/', '/docs/group/one/', '/docs/group/two/', '/docs/after/'],
    'the page chain never includes the group disclosure');
  press(grouped, { key: 'q' });
  press(grouped, { key: 'e' });
  assert.deepEqual(grouped.win.assigned, ['/docs/group/one/', '/docs/after/'],
    'q/e preserve page order even when the non-link group has focus');

  // ------------------------------------------------- activate and escape
  press(fold, { key: ' ' });
  assert.equal(fold.doc.activeElement.clicks, 1, 'Space activates the focused link');
  press(fold, { key: 'g' });
  assert.equal(fold.doc.activeElement.clicks, 1, 'g goes home now and no longer activates the focused link');
  const escTarget = fold.doc.activeElement;
  press(fold, { key: 'Escape' });
  assert.equal(
    fold.tree.menu.querySelectorAll('.td-kbd-focus').length,
    0,
    'Escape clears the highlight',
  );
  assert.notEqual(fold.doc.activeElement, escTarget, 'Escape leaves the tree');

  // Focus moving anywhere outside the highlighted row drops the highlight.
  press(fold, { key: 's' });
  assert.equal(fold.tree.menu.querySelectorAll('.td-kbd-focus').length, 1);
  (fold.doc.listeners.get('focusin') || []).forEach((fn) => fn({ target: fold.root }));
  assert.equal(
    fold.tree.menu.querySelectorAll('.td-kbd-focus').length,
    0,
    'external focus clears the highlight',
  );

  // ---------------------------------------------------------- q/e paging
  const page = setup();
  press(page, { key: 'q' });
  assert.deepEqual(page.win.assigned, ['/docs/b/'], 'q goes to the previous tree link');
  press(page, { key: 'e' });
  assert.deepEqual(
    page.win.assigned,
    ['/docs/b/', '/docs/c/'],
    'e goes to the next tree link',
  );

  const relPage = setup();
  const prev = new Element('link');
  prev.setAttribute('rel', 'prev');
  prev.href = 'https://example.test/docs/from-rel/';
  relPage.root.appendChild(prev);
  press(relPage, { key: 'q' });
  assert.deepEqual(
    relPage.win.assigned,
    ['/docs/b/'],
    'the visible sidebar takes precedence over head rel links',
  );

  const noTree = setup({ withTree: false });
  press(noTree, { key: 'e' });
  assert.deepEqual(noTree.win.assigned, [], 'no target keeps e a silent no-op');
  const pagerRoot = new Element('nav');
  pagerRoot.setAttribute('data-td-pager', '');
  const pager = new Element('a');
  pager.setAttribute('data-td-pager-next', '');
  pager.setAttribute('href', '/blog/next-post/');
  pagerRoot.appendChild(pager);
  noTree.root.appendChild(pagerRoot);
  press(noTree, { key: 'e' });
  assert.deepEqual(
    noTree.win.assigned,
    ['/blog/next-post/'],
    'the blog pager is the fallback when no tree exists',
  );
  press(noTree, { key: 'q' });
  assert.deepEqual(
    noTree.win.assigned,
    ['/blog/next-post/'],
    'a missing pager direction stays empty instead of changing families',
  );

  // Blog paging follows the rendered sidebar across column boundaries:
  // column landing -> its posts -> next column landing -> its first post.
  const blogPage = setup({ withTree: false });
  const blogMenu = new Element('div');
  blogMenu.id = 'td-sidebar-menu';
  const blogList = new Element('ul');
  const lastPostItem = treeItem({ href: '/blog/post/last/' });
  const postSection = treeItem({
    href: '/blog/post/',
    expanded: true,
    children: [lastPostItem],
  });
  const firstReleaseItem = treeItem({ href: '/blog/release/first/' });
  const releaseSection = treeItem({
    href: '/blog/release/',
    expanded: true,
    children: [firstReleaseItem],
  });
  blogList.appendChild(postSection);
  blogList.appendChild(releaseSection);
  blogMenu.appendChild(blogList);
  blogPage.root.appendChild(blogMenu);

  const lastPost = lastPostItem.querySelector('a.td-shell-tree__link');
  const releaseLanding = releaseSection.querySelector('a.td-shell-tree__link');
  const firstRelease = firstReleaseItem.querySelector('a.td-shell-tree__link');
  lastPost.classList.add('active');

  // A conflicting date pager must not change the sidebar sequence.
  const datePager = new Element('nav');
  datePager.setAttribute('data-td-pager', '');
  const dateNext = new Element('a');
  dateNext.setAttribute('data-td-pager-next', '');
  dateNext.setAttribute('href', '/blog/post/by-date/');
  datePager.appendChild(dateNext);
  blogPage.root.appendChild(datePager);

  press(blogPage, { key: 'e' });
  assert.deepEqual(
    blogPage.win.assigned,
    ['/blog/release/'],
    'e leaves the last post through the next column landing page',
  );
  lastPost.classList.remove('active');
  releaseLanding.classList.add('active');
  press(blogPage, { key: 'e' });
  assert.deepEqual(
    blogPage.win.assigned,
    ['/blog/release/', '/blog/release/first/'],
    'the next e enters the first page in that column',
  );
  releaseLanding.classList.remove('active');
  firstRelease.classList.add('active');
  press(blogPage, { key: 'q' });
  assert.equal(
    blogPage.win.assigned.at(-1),
    '/blog/release/',
    'q returns from the first page to its column landing page',
  );
  firstRelease.classList.remove('active');
  releaseLanding.classList.add('active');
  press(blogPage, { key: 'q' });
  assert.equal(
    blogPage.win.assigned.at(-1),
    '/blog/post/last/',
    'the next q returns to the previous column last page',
  );

  const relEdge = setup({ withTree: false });
  const relNext = new Element('link');
  relNext.setAttribute('rel', 'next');
  relNext.href = 'https://example.test/blog/second/';
  relEdge.root.appendChild(relNext);
  press(relEdge, { key: 'q' });
  assert.deepEqual(
    relEdge.win.assigned,
    [],
    'a missing rel direction must not fall through to a different navigation order',
  );
  press(relEdge, { key: 'e' });
  assert.deepEqual(
    relEdge.win.assigned,
    ['https://example.test/blog/second/'],
    'head rel links remain a fallback on pages without a tree or pager',
  );

  const edge = setup();
  edge.win.location.href = 'https://example.test/docs/a/';
  edge.tree.active.classList.remove('active');
  edge.tree.menu.querySelectorAll('a.td-shell-tree__link')[0].classList.add('active');
  const edgePager = new Element('nav');
  edgePager.setAttribute('data-td-pager', '');
  const edgePrev = new Element('a');
  edgePrev.setAttribute('data-td-pager-prev', '');
  edgePrev.setAttribute('href', '/blog/date-previous/');
  edgePager.appendChild(edgePrev);
  edge.root.appendChild(edgePager);
  press(edge, { key: 'q' });
  assert.deepEqual(
    edge.win.assigned,
    [],
    'the first sidebar page keeps q a no-op instead of falling through',
  );

  // Percent-encoded TOC anchors (e.g. CJK headings) and history.state preservation.
  const cjkOutline = setup({ withTree: false });
  cjkOutline.html.scrollHeight = 2000;
  cjkOutline.win.innerHeight = 800;
  cjkOutline.win.history.state = { oinkCompareSession: 'kept' };
  const recordedStates = [];
  cjkOutline.win.history.replaceState = (state, title, url) => {
    recordedStates.push(state);
    cjkOutline.win.hashes.push(url);
  };
  const cjkToc = new Element('nav');
  cjkToc.id = 'TableOfContents';
  const cjkAnchor = new Element('a');
  cjkAnchor.setAttribute('href', '#' + encodeURIComponent('配置说明'));
  cjkToc.appendChild(cjkAnchor);
  const cjkHeading = new Element('h2');
  cjkHeading.id = '配置说明';
  cjkHeading.getBoundingClientRect = () => ({ top: 600 - cjkOutline.win.scrollY });
  cjkOutline.root.appendChild(cjkHeading);
  cjkOutline.root.appendChild(cjkToc);
  press(cjkOutline, { key: 'j' });
  assert.deepEqual(cjkOutline.win.scrolledTo, [576], 'j resolves percent-encoded TOC heading IDs');
  assert.deepEqual(cjkOutline.win.hashes, ['#' + encodeURIComponent('配置说明')]);
  assert.deepEqual(recordedStates, [{ oinkCompareSession: 'kept' }], 'j preserves history.state');

  // External manual_link items in sidebar are skipped by q/e paging.
  const extTree = setup();
  const extItem = treeItem({ href: 'https://external.example/docs/b/one/' });
  extTree.tree.menu.children[0].appendChild(extItem);
  press(extTree, { key: 'e' });
  assert.deepEqual(extTree.win.assigned, ['/docs/c/']);

  // A preview host, a LAN address or a mirror serves the page from another
  // origin than the canonical link names. Before a cached sidebar marks its
  // active link, the canonical path alone still locates the page.
  const mirror = setup();
  mirror.tree.active.classList.remove('active');
  const mirrorCanonical = new Element('link');
  mirrorCanonical.setAttribute('rel', 'canonical');
  mirrorCanonical.href = 'https://www.example.test/docs/b/one/';
  mirror.root.appendChild(mirrorCanonical);
  press(mirror, { key: 'e' });
  assert.deepEqual(mirror.win.assigned, ['/docs/c/'], 'e pages from a canonical link on another origin');

  // --------------------------------------------------------- z zen mode
  const zen = setup();
  press(zen, { key: 'h' });
  assert.equal(zen.html.hasAttribute('data-td-kbd-zen'), false, 'h is browsing history now, not Zen Mode');
  press(zen, { key: 'z' });
  assert.equal(zen.html.hasAttribute('data-td-kbd-zen'), true, 'z hides the chrome');
  assert.equal(zen.win.sessionStorage.getItem('td-kbd-zen'), '1', 'z persists zen mode');
  press(zen, { key: 'z' });
  assert.equal(zen.html.hasAttribute('data-td-kbd-zen'), false, 'z restores the chrome');
  assert.equal(zen.win.sessionStorage.getItem('td-kbd-zen'), null, 'z clears zen persistence');

  const zenBack = setup({ session: { 'td-kbd-zen': '1' } });
  assert.equal(
    zenBack.html.hasAttribute('data-td-kbd-zen'),
    true,
    'a previous page\'s zen mode re-applies on load',
  );
  const zenTree = press(zenBack, { key: 's' });
  assert.equal(zenBack.doc.activeElement, null, 'zen mode must not focus its hidden tree');
  assert.notEqual(zenTree.defaultPrevented, true, 'zen mode must not swallow WASD');

  // ------------------------------------------------------------ x and v
  const langRuns = [];
  const langRegistry = {
    get: (id) => (id === 'switch_language'
      ? {
        available: true,
        options: [
          { id: 'en', url: '/docs/b/one/', active: true, available: true },
          { id: 'zh', url: '/zh/docs/b/one/', active: false, available: true },
        ],
      }
      : null),
    run(id, context) { langRuns.push([id, context.value.url]); return { then() {} }; },
  };
  const lang = setup({ registry: langRegistry });
  const xEvent = press(lang, { key: 'x' });
  assert.deepEqual(langRuns, [['switch_language', '/zh/docs/b/one/']],
    'x runs the next language choice through the registry URL policy');
  assert.equal(xEvent.defaultPrevented, true, 'x swallows the literal character');
  press(lang, { key: 'l' });
  assert.equal(langRuns.length, 1, 'l is the index layout key now, not a language alias');
  press(lang, { key: 'y' });
  assert.equal(langRuns.length, 1, 'y does not switch the language');

  const singleLang = setup({
    registry: { get: () => ({ available: false, options: [] }), run() { throw new Error('ran'); } },
  });
  assert.notEqual(press(singleLang, { key: 'x' }).defaultPrevented, true, 'a single-language site keeps x silent');

  const versionRuns = [];
  const versionRegistry = {
    get: (id) => (id === 'switch_version'
      ? {
        available: true,
        options: [
          { id: 'v1', url: 'https://v1.example.com/', active: true, available: true },
          { id: 'v0', url: '', active: false, available: false },
          { id: 'v2', url: 'https://v2.example.com/', active: false, available: true },
        ],
      }
      : null),
    run(id, context) { versionRuns.push([id, context.value.id]); return { then() {} }; },
  };
  const version = setup({ registry: versionRegistry });
  assert.equal(press(version, { key: 'v' }).defaultPrevented, true, 'v swallows the key when a version is offered');
  assert.deepEqual(versionRuns, [['switch_version', 'v2']], 'v skips unavailable versions and opens the next one');
  const noVersion = setup({ registry: langRegistry });
  assert.notEqual(press(noVersion, { key: 'v' }).defaultPrevented, true, 'v stays inert without versions');

  const themeRuns = [];
  const themeRegistry = {
    get: (id) => (id === 'switch_theme' ? { available: true } : null),
    run(id, context) { themeRuns.push([id, context.value]); return { then() {} }; },
  };
  const theme = setup({ registry: themeRegistry });
  press(theme, { key: 'y' });
  assert.deepEqual(themeRuns, [['switch_theme', 'light']], 'y steps from default auto to light');
  theme.html.setAttribute('data-td-color-mode', 'light');
  press(theme, { key: 'y' });
  assert.deepEqual(themeRuns[1], ['switch_theme', 'dark'], 'y steps from light to dark');
  theme.html.setAttribute('data-td-color-mode', 'dark');
  press(theme, { key: 'y' });
  assert.deepEqual(themeRuns[2], ['switch_theme', 'auto'], 'y steps from dark to system (auto)');
  theme.html.setAttribute('data-td-color-mode', 'auto');
  press(theme, { key: 'y' });
  assert.deepEqual(themeRuns[3], ['switch_theme', 'light'], 'y wraps from system back to light');

  // ------------------------------------------------------- t cycles styles
  const presetRuns = [];
  const presetRegistry = {
    get: (id) => (id === 'switch_preset'
      ? {
        available: true,
        options: [
          { id: 'paper', value: 'paper', available: true },
          { id: 'slate', value: 'slate', available: true },
          { id: 'ink', value: 'ink', available: true },
        ],
      }
      : null),
    run(id, context) { presetRuns.push([id, context.value]); return { then() {} }; },
  };
  const preset = setup({ registry: presetRegistry });
  preset.html.setAttribute('data-td-preset', 'paper');
  press(preset, { key: 't' });
  assert.deepEqual(presetRuns, [['switch_preset', 'slate']], 't steps to the next offered style');
  preset.html.setAttribute('data-td-preset', 'ink');
  press(preset, { key: 't' });
  assert.deepEqual(presetRuns[1], ['switch_preset', 'paper'], 't wraps from the last style to the first');
  press(preset, { key: 'v' });
  assert.equal(presetRuns.length, 2, 'v does not cycle styles');

  // ------------------------------------------------- ' shortcut help modal
  const coordinated = [];
  const registeredSurfaces = new Map();
  const helpCoordinator = {
    register(name, close) { registeredSurfaces.set(name, close); },
    closeOthers(name) { coordinated.push(name); },
  };
  const helpRun = setup({ withHelp: true, coordinator: helpCoordinator, registry: langRegistry });
  const originButton = new Element('button');
  helpRun.root.appendChild(originButton);
  originButton.ownerDocument = helpRun.doc;
  originButton.focus();

  assert.notEqual(press(helpRun, { key: ';' }).defaultPrevented, true, '; is the gallery layout key now, not help');
  const openHelpKey = press(helpRun, { key: "'" });
  assert.equal(openHelpKey.defaultPrevented, true, "' swallows the literal character when opening help");
  assert.deepEqual(coordinated, ['keyboard-help'], 'opening help closes other surfaces');
  assert.equal(registeredSurfaces.has('keyboard-help'), true, 'help dialog registers with surface coordinator');
  const helpDialog = helpRun.root.querySelector('[data-td-keyboard-dialog]');
  assert.ok(helpDialog && helpDialog.open, "' opens the shortcut help dialog");
  const helpClose = helpDialog.querySelector('[data-td-keyboard-dialog-close]');
  assert.equal(helpRun.doc.activeElement, helpClose, 'opening help focuses the close button');
  assert.equal(helpClose.getAttribute('aria-keyshortcuts'), "Escape '");
  const dialogBody = helpDialog.children[0].children[1];
  assert.equal(dialogBody.className, 'td-shell-keyboard-dialog__body');
  assert.equal(dialogBody.getAttribute('tabindex'), '0', 'the scrolling sheet is reachable from the keyboard');
  assert.equal(dialogBody.getAttribute('role'), 'region');
  assert.equal(dialogBody.getAttribute('aria-labelledby'), 'td-shell-keyboard-dialog-title');
  const dialogSections = helpDialog.querySelectorAll('.td-shell-keyboard-help__section');
  assert.deepEqual(
    dialogSections.map((s) => s.getAttribute('aria-labelledby')),
    [
      'td-shell-shortcuts-navigation-dialog',
      'td-shell-shortcuts-actions-dialog',
      'td-shell-shortcuts-view-dialog',
    ],
    'the three groups are cloned with aria-labelledby rewritten to avoid duplicate IDs',
  );
  // Rows this page cannot run stay in the grid, dimmed and explained.
  const helpRow = (id) => helpDialog.querySelectorAll('[data-td-shortcut]')
    .find((row) => row.getAttribute('data-td-shortcut') === id);
  assert.equal(helpRow('language').classList.contains('td-is-unavailable'), false, 'an offered language keeps X live');
  assert.equal(helpRow('tree-move').classList.contains('td-is-unavailable'), false, 'a sidebar keeps WASD live');
  assert.equal(helpRow('print').classList.contains('td-is-unavailable'), false, 'P is always live');
  assert.equal(helpRow('claude').classList.contains('td-is-unavailable'), true, 'Claude without assistant links is dimmed');
  assert.equal(helpRow('page-width').classList.contains('td-is-unavailable'), true, 'no reading column dims the width row');
  const claudeNote = helpRow('claude').querySelector('[data-td-shortcut-state]');
  assert.ok(claudeNote && !claudeNote.hidden, 'a dimmed row carries a screen-reader note');
  assert.equal(claudeNote.textContent, ' (unavailable)');
  assert.equal(helpRow('help').querySelector('[data-td-shortcut-state]'), null, 'a live row has no note');
  assert.equal(
    helpRun.doc.getElementById('td-shell-shortcuts-navigation-dialog') !== null,
    true,
    'cloned section heading carries suffixed dialog ID',
  );

  // While help is open, other single-key shortcuts and key-repeat ' stand down.
  const runsBeforeHelpKeys = langRuns.length;
  press(helpRun, { key: 'x' });
  press(helpRun, { key: 'z' });
  press(helpRun, { key: "'", repeat: true });
  press(helpRun, { key: "'", shiftKey: true });
  press(helpRun, { key: '"', shiftKey: true });
  assert.equal(langRuns.length, runsBeforeHelpKeys, 'other shortcuts stand down while help is open');
  assert.equal(helpRun.html.hasAttribute('data-td-kbd-zen'), false, 'z stands down while help is open');
  assert.equal(helpDialog.open, true, "repeated or modified ' does not dismiss help");

  // Second bare ' closes help and restores focus.
  const closeHelpKey = press(helpRun, { key: "'" });
  assert.equal(closeHelpKey.defaultPrevented, true, "second ' swallows the key");
  assert.equal(helpDialog.open, false, "second ' closes the help dialog");
  assert.equal(helpRun.doc.activeElement, originButton, "closing via ' restores prior focus");

  // Works inside Zen Mode and closes via Escape, close button, and backdrop click.
  press(helpRun, { key: 'z' });
  assert.equal(helpRun.html.hasAttribute('data-td-kbd-zen'), true);
  press(helpRun, { key: "'" });
  assert.equal(helpDialog.open, true, "' opens help even while Zen Mode hides the footer");
  assert.equal(helpRow('tree-move').classList.contains('td-is-unavailable'), true,
    'availability is recomputed at each open: Zen Mode parks WASD');
  press(helpRun, { key: 'Escape' });
  assert.equal(helpDialog.open, false, 'Escape closes the help dialog');
  assert.equal(helpRun.html.hasAttribute('data-td-kbd-zen'), true, 'closing help preserves Zen Mode');

  press(helpRun, { key: "'" });
  helpClose.click();
  assert.equal(helpDialog.open, false, 'close button dismisses the help dialog');

  press(helpRun, { key: "'" });
  helpDialog.dispatchEvent({ type: 'pointerdown', target: helpClose });
  helpDialog.dispatchEvent({ type: 'click', target: helpDialog });
  assert.equal(helpDialog.open, true, 'drag from inside onto backdrop must not dismiss help');
  helpDialog.dispatchEvent({ type: 'pointerdown', target: helpDialog });
  helpDialog.dispatchEvent({ type: 'click', target: helpDialog });
  assert.equal(helpDialog.open, false, 'backdrop click dismisses the help dialog');

  // Coordinator close and beforeprint close without stealing focus.
  press(helpRun, { key: "'" });
  registeredSurfaces.get('keyboard-help')(false);
  assert.equal(helpDialog.open, false, 'surface coordinator can close the help dialog');
  press(helpRun, { key: "'" });
  helpRun.win.dispatchEvent({ type: 'beforeprint' });
  assert.equal(helpDialog.open, false, 'beforeprint closes the help dialog');

  // Clicking the bottom-bar ? trigger promotes to the centered modal dialog and
  // suppresses hover-reopen when restoring focus on close.
  const triggerMenu = new Element('div', 'td-shell-keyboard td-nav-hover-menu');
  triggerMenu.setAttribute('data-td-nav-hover', '');
  const triggerBtn = new Element('button', 'td-shell-iconbtn td-shell-keyboard__trigger');
  const triggerIcon = new Element('i', 'td-shell-icon');
  triggerBtn.appendChild(triggerIcon);
  triggerMenu.appendChild(triggerBtn);
  helpRun.root.appendChild(triggerMenu);
  triggerMenu.ownerDocument = helpRun.doc;
  triggerBtn.ownerDocument = helpRun.doc;
  triggerIcon.ownerDocument = helpRun.doc;
  let focusSuppressedDuringRestore = null;
  triggerBtn.focus = () => {
    focusSuppressedDuringRestore = triggerMenu.hasAttribute('data-td-suppress-focus-open');
    helpRun.doc.activeElement = triggerBtn;
  };
  let clickStopped = false;
  const triggerClickEvent = {
    type: 'click',
    target: triggerIcon,
    button: 0,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() { clickStopped = true; },
  };
  (helpRun.doc.listeners.get('click') || []).forEach((fn) => fn(triggerClickEvent));
  assert.equal(triggerClickEvent.defaultPrevented, true, 'clicking ? prevents default hover toggle');
  assert.equal(clickStopped, true, 'clicking ? stops propagation to base.js hover click handler');
  assert.equal(helpDialog.open, true, 'clicking ? opens the centered shortcut help dialog');
  press(helpRun, { key: 'Escape' });
  assert.equal(helpDialog.open, false, 'Escape closes dialog opened via ? trigger');
  assert.equal(helpRun.doc.activeElement, triggerBtn, 'closing restores focus to ? trigger');
  assert.equal(focusSuppressedDuringRestore, true, 'focus restore suppresses hover popover reopen');
  assert.equal(triggerMenu.hasAttribute('data-td-suppress-focus-open'), false, 'focus suppress attribute cleans up synchronously');
  assert.equal(triggerMenu.hasAttribute('data-td-suppress-hover-open'), true, 'hover suppress attribute guards post-close synthetic pointerenter');
  helpRun.frames.splice(0).forEach((fn) => fn());
  helpRun.frames.splice(0).forEach((fn) => fn());
  helpRun.timeouts.splice(0).forEach((fn) => fn());
  assert.equal(triggerMenu.hasAttribute('data-td-suppress-hover-open'), false, 'hover suppress attribute clears after post-close frames');

  // footer_style: none renders the same template on its own; it still powers '.
  const templateHelp = setup({ withTree: false, withHelpTemplate: true });
  press(templateHelp, { key: "'" });
  const tplDialog = templateHelp.root.querySelector('[data-td-keyboard-dialog]');
  assert.ok(tplDialog && tplDialog.open, "' opens help from the template when the footer is absent");
  assert.equal(
    tplDialog.querySelector('[data-td-keyboard-dialog-close]').getAttribute('aria-label'),
    '关闭',
    'dialog close button carries the localized close label',
  );
  // CJK curly quote also toggles the help dialog even with IME keyCode 229.
  press(templateHelp, { key: '‘', keyCode: 229 });
  assert.equal(tplDialog.open, false, 'CJK quote closes help when not composing');
  press(templateHelp, { key: '’', keyCode: 229 });
  assert.equal(tplDialog.open, true, 'CJK quote opens help when not composing');
  press(templateHelp, { key: 'Process', code: 'Escape', keyCode: 229 });
  assert.equal(tplDialog.open, false, 'Escape closes help via code even with IME Process key');

  // Footer pages render the full sheet directly inside the hover popover (no
  // template needed), dimming unavailable rows immediately and on hover.
  const liveHoverHelp = setup({ withTree: false, registry: langRegistry });
  const hoverMenu = new Element('div', 'td-shell-keyboard td-nav-hover-menu');
  const liveSheet = helpPanelFixture('Keyboard shortcuts', 'Close');
  hoverMenu.appendChild(liveSheet);
  liveHoverHelp.root.appendChild(hoverMenu);
  liveHoverHelp.controller.toggleHelp();
  const hoverDialog = liveHoverHelp.root.querySelector('[data-td-keyboard-dialog]');
  assert.ok(hoverDialog && hoverDialog.open, 'live footer sheet powers the modal dialog directly');
  liveHoverHelp.controller.closeHelp(false);

  // Inert fading overlays must not suppress single-key shortcuts.
  const inertWrap = new Element('div');
  inertWrap.inert = true;
  const fadingDialog = new Element('div');
  fadingDialog.setAttribute('role', 'dialog');
  inertWrap.appendChild(fadingDialog);
  guard.root.appendChild(inertWrap);
  const beforeInertScroll = guard.win.scrolled.length;
  press(guard, { key: 'j' });
  assert.equal(guard.win.scrolled.length, beforeInertScroll + 1, 'inert fading dialog does not suppress shortcuts');
  guard.root.children.pop();

  // Without any help source, ' stays a silent no-op.
  const noHelp = setup({ withTree: false });
  const idleQuote = press(noHelp, { key: "'" });
  assert.notEqual(idleQuote.defaultPrevented, true, "' without a help source stays inert");

  // ----------------------------------------- l switches blog index layout
  const blogLayout = setup({ withTree: false });
  const idleBlogL = press(blogLayout, { key: 'l' });
  assert.notEqual(idleBlogL.defaultPrevented, true, 'l stays inert when no layout toggle exists');
  const layoutBtn = new Element('button');
  layoutBtn.setAttribute('data-td-blog-index-toggle', '');
  layoutBtn.hidden = true;
  blogLayout.root.appendChild(layoutBtn);
  const hiddenBlogL = press(blogLayout, { key: 'l' });
  assert.notEqual(hiddenBlogL.defaultPrevented, true, 'l ignores a hidden layout toggle');
  assert.equal(layoutBtn.clicks, 0);
  layoutBtn.hidden = false;
  assert.equal(press(blogLayout, { key: 'v' }).defaultPrevented, undefined, 'v no longer switches the index layout');
  const activeBlogL = press(blogLayout, { key: 'l' });
  assert.equal(activeBlogL.defaultPrevented, true, 'l swallows the key when cycling index layout');
  assert.equal(layoutBtn.clicks, 1, 'l activates the blog index layout toggle');

  // -------------------------- Expo album shortcuts: ; (mode), ,/< ./> (size)
  const expoPage = setup({ withTree: false });
  assert.notEqual(press(expoPage, { key: 'm' }).defaultPrevented, true, 'm opens Markdown now and needs a markdown action');
  assert.notEqual(press(expoPage, { key: ';' }).defaultPrevented, true, '; stays inert outside Expo');
  assert.notEqual(press(expoPage, { key: ',' }).defaultPrevented, true, ', stays inert outside Expo');
  assert.notEqual(press(expoPage, { key: '.', shiftKey: false }).defaultPrevented, true, '. stays inert outside Expo');
  assert.notEqual(press(expoPage, { key: '<', shiftKey: true }).defaultPrevented, true, '< stays inert outside Expo');
  assert.notEqual(press(expoPage, { key: '>', shiftKey: true }).defaultPrevented, true, '> stays inert outside Expo');

  const expoSection = new Element('section');
  expoSection.setAttribute('data-td-expo', '');
  const expoControls = new Element('div');
  expoControls.setAttribute('data-td-expo-controls', '');
  expoControls.hidden = true;
  const modeEvents = [];
  const modeRadios = ['wall', 'cards', 'seamless'].map((modeName, idx) => {
    const radio = new Element('input');
    radio.setAttribute('type', 'radio');
    radio.setAttribute('data-td-expo-mode', modeName);
    radio.value = modeName;
    radio.checked = idx === 0;
    radio.addEventListener('change', () => modeEvents.push(modeName));
    expoControls.appendChild(radio);
    return radio;
  });
  const sizeEvents = [];
  const sizeSlider = new Element('input');
  sizeSlider.setAttribute('type', 'range');
  sizeSlider.setAttribute('data-td-expo-size', '');
  sizeSlider.setAttribute('min', '160');
  sizeSlider.setAttribute('max', '360');
  sizeSlider.setAttribute('step', '20');
  sizeSlider.value = '240';
  sizeSlider.addEventListener('input', () => sizeEvents.push(sizeSlider.value));
  expoControls.appendChild(sizeSlider);
  expoSection.appendChild(expoControls);
  expoPage.root.appendChild(expoSection);

  // Hidden Expo controls stay inert until expo.js reveals them.
  assert.notEqual(press(expoPage, { key: ';' }).defaultPrevented, true, '; ignores hidden Expo controls');
  assert.notEqual(press(expoPage, { key: '.' }).defaultPrevented, true, '. ignores hidden Expo controls');

  expoControls.hidden = false;
  assert.equal(press(expoPage, { key: ';' }).defaultPrevented, true, '; switches Expo mode');
  assert.deepEqual(modeEvents, ['cards']);
  assert.equal(modeRadios[1].checked, true);
  press(expoPage, { key: ';' });
  press(expoPage, { key: ';' });
  assert.deepEqual(modeEvents, ['cards', 'seamless', 'wall'], '; wraps from seamless back to wall');

  assert.equal(press(expoPage, { key: ',' }).defaultPrevented, true, ', shrinks Expo image size');
  assert.equal(sizeSlider.value, '220');
  assert.equal(press(expoPage, { key: '<', shiftKey: true }).defaultPrevented, true, 'Shift+, (<) shrinks Expo image size');
  assert.equal(sizeSlider.value, '200');
  assert.equal(press(expoPage, { key: '.' }).defaultPrevented, true, '. enlarges Expo image size');
  assert.equal(sizeSlider.value, '220');
  assert.equal(press(expoPage, { key: '>', shiftKey: true }).defaultPrevented, true, 'Shift+. (>) enlarges Expo image size');
  assert.equal(sizeSlider.value, '240');

  // Bounds clamp cleanly without emitting redundant input events.
  sizeSlider.value = '160';
  sizeEvents.length = 0;
  assert.equal(press(expoPage, { key: ',' }).defaultPrevented, true);
  assert.equal(sizeSlider.value, '160');
  assert.deepEqual(sizeEvents, [], 'min bound emits no redundant input');
  sizeSlider.value = '360';
  assert.equal(press(expoPage, { key: '>', shiftKey: true }).defaultPrevented, true);
  assert.equal(sizeSlider.value, '360');
  assert.deepEqual(sizeEvents, [], 'max bound emits no redundant input');

  // Focused Expo toolbar radio or range slider must not block ;/,/. shortcuts.
  sizeSlider.value = '240';
  assert.equal(press(expoPage, { key: ';', target: modeRadios[0] }).defaultPrevented, true, '; still works while a mode radio has focus');
  assert.equal(modeEvents.at(-1), 'cards');
  assert.equal(press(expoPage, { key: '.', target: sizeSlider }).defaultPrevented, true, '. still works while the size slider has focus');
  assert.equal(sizeSlider.value, '260');
  assert.equal(press(expoPage, { key: ',', target: sizeSlider }).defaultPrevented, true, ', still works while the size slider has focus');
  assert.equal(sizeSlider.value, '240');
  // Reset back to wall for following assertions.
  press(expoPage, { key: ';' });
  press(expoPage, { key: ';' });
  assert.equal(modeEvents.at(-1), 'wall');

  // Typing targets and modifiers still guard < and >, while ISO/JIS shifted ;
  // and = work without letting Shift+; (:) slip through.
  sizeSlider.value = '240';
  const beforeGuardedModes = modeEvents.length;
  press(expoPage, { key: '<', shiftKey: true, target: input });
  press(expoPage, { key: '>', shiftKey: true, ctrlKey: true });
  press(expoPage, { key: ':', shiftKey: true });
  assert.equal(sizeSlider.value, '240', 'typing and Ctrl/Meta/Alt guard < and >');
  assert.equal(modeEvents.length, beforeGuardedModes, 'Shift+; (:) stays guarded');
  assert.equal(press(expoPage, { key: ';', shiftKey: true }).defaultPrevented, true, 'ISO/JIS shifted ; cycles Expo mode');
  assert.equal(modeEvents.at(-1), 'cards');
  press(expoPage, { key: ';' });
  press(expoPage, { key: ';' });
  assert.equal(modeEvents.at(-1), 'wall');

  // Open Expo viewer dialog suppresses page-level Expo shortcuts.
  const beforeViewerModes = modeEvents.length;
  const expoViewer = new Element('dialog');
  expoViewer.setAttribute('open', '');
  expoPage.root.appendChild(expoViewer);
  press(expoPage, { key: ';' });
  press(expoPage, { key: '.' });
  assert.equal(sizeSlider.value, '240', 'open viewer dialog suppresses page-level Expo size shortcuts');
  assert.equal(modeEvents.length, beforeViewerModes, 'open viewer dialog suppresses page-level Expo mode shortcut');
  expoPage.root.children.pop();

  // Blog/Case/Release gallery form ([data-td-blog-gallery]) uses the same ; / , / . shortcuts when visible.
  const blogGalleryPage = setup({ withTree: false });
  const blogGallery = new Element('section');
  blogGallery.setAttribute('data-td-blog-gallery', '');
  blogGallery.hidden = true;
  const galleryBar = new Element('div');
  galleryBar.setAttribute('data-gallery-controls', '');
  const bgModes = [];
  ['wall', 'cards', 'seamless'].forEach((name, idx) => {
    const radio = new Element('input');
    radio.setAttribute('data-gallery-mode', '');
    radio.value = name;
    radio.checked = idx === 0;
    radio.addEventListener('change', () => bgModes.push(name));
    galleryBar.appendChild(radio);
  });
  const bgSlider = new Element('input');
  bgSlider.setAttribute('data-gallery-size', '');
  bgSlider.setAttribute('min', '160');
  bgSlider.setAttribute('max', '360');
  bgSlider.setAttribute('step', '20');
  bgSlider.value = '240';
  galleryBar.appendChild(bgSlider);
  blogGallery.appendChild(galleryBar);
  blogGalleryPage.root.appendChild(blogGallery);

  // Hidden blog gallery (e.g. while cards/list/table view is active) stays inert.
  assert.notEqual(press(blogGalleryPage, { key: ';' }).defaultPrevented, true, '; ignores hidden blog gallery');
  assert.notEqual(press(blogGalleryPage, { key: '.' }).defaultPrevented, true, '. ignores hidden blog gallery');
  assert.equal(bgSlider.value, '240');

  // Visible blog gallery responds to ;, ,/<, and ./>.
  blogGallery.hidden = false;
  assert.equal(press(blogGalleryPage, { key: ';' }).defaultPrevented, true, '; switches visible blog gallery mode');
  assert.deepEqual(bgModes, ['cards']);
  assert.equal(press(blogGalleryPage, { key: ',' }).defaultPrevented, true, ', shrinks visible blog gallery size');
  assert.equal(bgSlider.value, '220');
  assert.equal(press(blogGalleryPage, { key: '>', shiftKey: true }).defaultPrevented, true, '> enlarges visible blog gallery size');
  assert.equal(bgSlider.value, '240');

  const fixedRuns = [];
  const fixedPreset = setup({
    registry: {
      get: (id) => (id === 'switch_preset' ? { available: false, options: [] } : null),
      run(id, context) { fixedRuns.push([id, context.value]); },
    },
  });
  press(fixedPreset, { key: 't' });
  assert.deepEqual(fixedRuns, [], 'a site without a style menu keeps t silent');

  // ------------------------------------------------------------- f and c
  const opens = [];
  const paletteStub = {
    commandPrefix: '>',
    instance: { open(event, seed) { opens.push(seed); } },
  };
  const fc = setup({ palette: paletteStub });
  const fEvent = press(fc, { key: 'f' });
  assert.deepEqual(opens, [undefined], 'f opens the palette in search mode');
  assert.equal(fEvent.defaultPrevented, true, 'f swallows the literal character');
  const cEvent = press(fc, { key: 'c' });
  assert.deepEqual(opens, [undefined, '>'], 'c opens the palette in command mode');
  assert.equal(cEvent.defaultPrevented, true, 'c swallows the literal character');

  const fixedDialog = new Element('div');
  fixedDialog.setAttribute('role', 'dialog');
  fixedDialog.offsetParent = null;
  fc.root.appendChild(fixedDialog);
  for (const key of ['f', 'c']) {
    const ignored = press(fc, { key });
    assert.notEqual(ignored.defaultPrevented, true, `${key} stole a fixed dialog's shortcut`);
  }
  assert.equal(opens.length, 2, 'f/c opened the Palette through a fixed dialog');
  fixedDialog.hidden = true;
  press(fc, { key: 'f' });
  assert.equal(opens.length, 3, 'a hidden fixed dialog blocked f');

  const noPalette = setup();
  const idle = press(noPalette, { key: 'f' });
  assert.notEqual(idle.defaultPrevented, true, 'f without a palette stays inert');

  // ---------------------------------------- global landing-page shortcuts
  const landingRuns = [];
  const landing = setup({
    withTree: false,
    shell: false,
    home: true,
    registry: {
      get(id) {
        if (id === 'switch_theme') return { available: true };
        if (id === 'switch_preset') {
          return {
            available: true,
            options: [
              { id: 'paper', value: 'paper', available: true },
              { id: 'slate', value: 'slate', available: true },
            ],
          };
        }
        if (id === 'switch_language') {
          return {
            available: true,
            options: [
              { id: 'en', url: '/', active: true, available: true },
              { id: 'zh', url: '/zh/', active: false, available: true },
            ],
          };
        }
        return null;
      },
      run(id, context) { landingRuns.push([id, context.value]); return { then() {} }; },
    },
    palette: paletteStub,
  });
  landing.html.scrollHeight = 3000;
  landing.win.innerHeight = 800;
  const landingRoot = new Element('div');
  landingRoot.setAttribute('data-td-landing', '');
  for (const [id, top] of [['hero', 0], ['release', 600], ['capabilities', 1400]]) {
    const section = new Element('section');
    section.id = id;
    section.getBoundingClientRect = () => ({ top: top - landing.win.scrollY });
    landingRoot.appendChild(section);
  }
  landing.root.appendChild(landingRoot);
  for (const href of ['/', '/docs/', '/blog/', '/blog/']) {
    const route = new Element('a');
    route.setAttribute('data-td-navbar-route', '');
    route.setAttribute('href', href);
    landing.root.appendChild(route);
  }
  landing.win.location.href = 'https://example.test/docs/guide/';
  landing.win.location.pathname = '/docs/guide/';
  const rEvent = press(landing, { key: 'r' });
  assert.deepEqual(
    landing.win.assigned,
    ['/blog/'],
    'r advances from a nested page to the next unique internal navbar route',
  );
  assert.equal(rEvent.defaultPrevented, true, 'r swallows the literal character');
  landing.win.assigned.length = 0;
  landing.win.location.href = 'https://example.test/blog/post/';
  press(landing, { key: 'r' });
  assert.deepEqual(landing.win.assigned, ['/'], 'r wraps the navbar cycle to home');
  landing.html.setAttribute('data-td-preset', 'paper');
  press(landing, { key: 't' });
  assert.deepEqual(landingRuns, [['switch_preset', 'slate']], 't steps styles outside the shell');
  press(landing, { key: 'x' });
  assert.deepEqual(
    landingRuns.at(-1),
    ['switch_language', { id: 'zh', url: '/zh/', active: false, available: true }],
    'x works outside the shell',
  );
  landing.win.assigned.length = 0;
  press(landing, { key: 'y' });
  assert.deepEqual(landing.win.assigned, [], 'y leaves the language alone outside the shell');
  assert.deepEqual(landingRuns.at(-1), ['switch_theme', 'light'], 'y cycles the color mode outside the shell');
  press(landing, { key: 'j' });
  assert.equal(landing.win.scrolledTo.at(-1), 576, 'homepage j jumps to the next top-level section');
  assert.equal(landing.win.hashes.at(-1), '#release', 'homepage section jump updates the hash');
  press(landing, { key: 'k' });
  assert.equal(landing.win.scrolledTo.at(-1), 0, 'homepage k jumps to the previous top-level section');
  const scrollsBeforeN = landing.win.scrolledTo.length;
  press(landing, { key: 'n' });
  assert.equal(landing.win.scrolledTo.length, scrollsBeforeN, 'n creates a page now; it is no homepage section alias');
  const landingAssignments = landing.win.assigned.length;
  press(landing, { key: 'q' });
  assert.equal(landing.win.assigned.length, landingAssignments, 'homepage q remains shell-only');
  press(landing, { key: 'z' });
  assert.equal(landing.html.hasAttribute('data-td-kbd-zen'), true, 'homepage z hides navbar and footer chrome');
  assert.equal(landing.win.sessionStorage.getItem('td-kbd-zen'), '1', 'homepage z focus mode persists');
  press(landing, { key: 'z' });
  assert.equal(landing.html.hasAttribute('data-td-kbd-zen'), false, 'homepage z restores chrome');
  press(landing, { key: 'h' });
  assert.equal(landing.html.hasAttribute('data-td-kbd-zen'), false, 'homepage h is not a Zen Mode alias');

  const homeBack = setup({
    withTree: false,
    shell: false,
    home: true,
    session: { 'td-kbd-zen': '1' },
  });
  assert.equal(homeBack.html.hasAttribute('data-td-kbd-zen'), true, 'homepage restores focus mode');

  const ordinary = setup({
    withTree: false,
    shell: false,
    session: { 'td-kbd-zen': '1' },
  });
  press(ordinary, { key: 'j' });
  press(ordinary, { key: 'h' });
  press(ordinary, { key: 'z' });
  assert.equal(ordinary.win.scrolled.length, 0, 'ordinary pages keep reading keys inert');
  assert.equal(ordinary.html.hasAttribute('data-td-kbd-zen'), false, 'ordinary pages do not restore focus mode');

  // A standalone consumer homepage can bridge the same global actions with
  // data attributes, without loading the action registry or palette bundle.
  const bridge = setup({ withTree: false, shell: false });
  const bridgeTheme = new Element('button');
  bridgeTheme.setAttribute('data-td-theme-toggle', '');
  bridge.root.appendChild(bridgeTheme);
  const bridgeLanguage = new Element('a');
  bridgeLanguage.setAttribute('data-td-language-route', '');
  bridgeLanguage.setAttribute('href', '/zh/');
  bridge.root.appendChild(bridgeLanguage);
  const bridgeSearch = new Element('a');
  bridgeSearch.setAttribute('data-td-keyboard-search-route', '');
  bridgeSearch.setAttribute('href', '/docs/');
  bridge.root.appendChild(bridgeSearch);
  press(bridge, { key: 'y' });
  assert.equal(bridgeTheme.clicks, 1, 'y clicks a standalone homepage theme bridge');
  press(bridge, { key: 'x' });
  assert.deepEqual(bridge.win.assigned, ['/zh/'], 'x follows a standalone language bridge');
  bridge.win.assigned.length = 0;
  const bridgeF = press(bridge, { key: 'f' });
  assert.deepEqual(bridge.win.assigned, ['/docs/'], 'f leaves a standalone page for its search surface');
  assert.equal(bridge.win.sessionStorage.getItem('td-kbd-palette'), 'search');
  assert.equal(bridgeF.defaultPrevented, true);
  bridge.win.assigned.length = 0;
  press(bridge, { key: 'c' });
  assert.deepEqual(bridge.win.assigned, ['/docs/'], 'c uses the same registered search surface');
  assert.equal(bridge.win.sessionStorage.getItem('td-kbd-palette'), 'command');

  const resumedOpens = [];
  const resumed = setup({
    withTree: false,
    session: { 'td-kbd-palette': 'command' },
    palette: {
      commandPrefix: '>',
      instance: { open(event, seed) { resumedOpens.push(seed); } },
    },
  });
  assert.equal(resumed.win.sessionStorage.getItem('td-kbd-palette'), null, 'a pending palette mode is consumed once');
  resumed.timeouts.splice(0).forEach((callback) => callback());
  assert.deepEqual(resumedOpens, ['>'], 'the destination resumes command mode after its runtime initializes');

  const appearanceKeys = setup({ withTree: false, shell: false });
  const appearanceBridge = new Element('button');
  appearanceBridge.setAttribute('data-td-theme-toggle', '');
  appearanceKeys.root.appendChild(appearanceBridge);
  const appearanceDialog = new Element('dialog', 'td-appearance__panel');
  appearanceDialog.setAttribute('open', '');
  appearanceKeys.root.appendChild(appearanceDialog);
  press(appearanceKeys, { key: 'y' });
  assert.equal(appearanceBridge.clicks, 1, 'nonmodal Appearance blocked reading shortcuts');
  appearanceDialog.modal = true;
  press(appearanceKeys, { key: 'y' });
  assert.equal(appearanceBridge.clicks, 1, 'modal Appearance lost shortcut ownership');
  appearanceDialog.modal = false;
  const secondDialog = new Element('dialog');
  secondDialog.setAttribute('open', '');
  appearanceKeys.root.appendChild(secondDialog);
  press(appearanceKeys, { key: 'y' });
  assert.equal(appearanceBridge.clicks, 1, 'a second native dialog was ignored');

  // ------------------------------------------------------------- g goes home
  const homeRegistry = { get: () => null, home: () => 'https://example.test/' };
  const goHome = setup({ registry: homeRegistry });
  const gEvent = press(goHome, { key: 'g' });
  assert.deepEqual(goHome.win.assigned, ['https://example.test/'], 'g opens the language home');
  assert.equal(gEvent.defaultPrevented, true, 'g swallows the literal character');
  const atHome = setup({ withTree: false, shell: false, home: true, registry: homeRegistry });
  atHome.win.location.href = 'https://example.test/';
  atHome.win.scrollY = 900;
  press(atHome, { key: 'g' });
  assert.deepEqual(atHome.win.assigned, [], 'g on the home page does not reload it');
  assert.deepEqual(atHome.win.scrolledTo, [0], 'g on the home page returns to the top');
  const brandHome = setup({ withTree: false });
  const brand = new Element('a', 'td-nav-brand');
  brand.setAttribute('href', '/');
  brand.href = 'https://example.test/';
  brandHome.root.appendChild(brand);
  brandHome.doc.querySelector = (selector) => (selector === '.td-nav-brand[href], .td-shell-subnav__brand[href]'
    ? brand
    : brandHome.root.querySelector(selector));
  press(brandHome, { key: 'g' });
  assert.deepEqual(brandHome.win.assigned, ['https://example.test/'], 'without a manifest home g follows the brand link');

  // ----------------------------------------------------- h opens history
  const historyOpens = [];
  const withHistory = setup({ history: { instance: { open(event) { historyOpens.push(event.key); } } } });
  const hEvent = press(withHistory, { key: 'h' });
  assert.deepEqual(historyOpens, ['h'], 'h opens the browsing history overlay');
  assert.equal(hEvent.defaultPrevented, true, 'h swallows the literal character');
  assert.notEqual(press(setup(), { key: 'h' }).defaultPrevented, true, 'h without the history runtime stays inert');
  const bareHistory = setup({ history: { instance: { available: false, open() { return false; } } }, withHelp: true });
  assert.notEqual(press(bareHistory, { key: 'h' }).defaultPrevented, true, 'h stays inert when the history overlay is absent');
  press(bareHistory, { key: "'" });
  const bareHistoryRow = bareHistory.root.querySelector('[data-td-keyboard-dialog]').querySelectorAll('[data-td-shortcut]')
    .find((el) => el.getAttribute('data-td-shortcut') === 'history');
  assert.equal(bareHistoryRow.classList.contains('td-is-unavailable'), true, 'help dims h when the history overlay is absent');
  press(bareHistory, { key: 'Escape' });

  // q, e, t and y swallow the key when they act (preventing browser Quick Find)
  // and stay inert when unavailable.
  const qPage = setup();
  assert.equal(press(qPage, { key: 'q' }).defaultPrevented, true, 'q swallows the key when paging back');
  assert.equal(press(qPage, { key: 'e' }).defaultPrevented, true, 'e swallows the key when paging forward');
  assert.notEqual(press(setup({ withTree: false }), { key: 'q' }).defaultPrevented, true, 'q stays inert without a previous page');
  const tyPage = setup({
    withTree: false,
    registry: {
      get: (id) => (id === 'switch_theme'
        ? { available: true }
        : (id === 'switch_preset'
          ? { available: true, options: [{ id: 'paper', value: 'paper' }, { id: 'slate', value: 'slate' }] }
          : null)),
      run: () => ({ then() {} }),
    },
  });
  assert.equal(press(tyPage, { key: 't' }).defaultPrevented, true, 't swallows the key when cycling presets');
  assert.equal(press(tyPage, { key: 'y' }).defaultPrevented, true, 'y swallows the key when cycling color modes');
  assert.notEqual(press(setup({ withTree: false }), { key: 't' }).defaultPrevented, true, 't stays inert with no preset switch');
  assert.notEqual(press(setup({ withTree: false }), { key: 'y' }).defaultPrevented, true, 'y stays inert with no theme toggle');

  // ------------------------------------- page actions run through the registry
  const actionRuns = [];
  const offered = new Set(['edit_page', 'create_child_page', 'create_issue', 'print', 'open_chatgpt',
    'open_claude', 'view_markdown']);
  const actionRegistry = {
    get: (id) => (offered.has(id) ? { id, available: true } : (id === 'view_history' ? { available: false } : null)),
    run(id, context) { actionRuns.push([id, context.source]); return Promise.resolve(); },
  };
  const acting = setup({ registry: actionRegistry });
  for (const [key, id] of [
    ['u', 'edit_page'], ['n', 'create_child_page'], ['i', 'create_issue'], ['p', 'print'],
    ['[', 'open_chatgpt'], [']', 'open_claude'], ['m', 'view_markdown'],
  ]) {
    const event = press(acting, { key });
    assert.equal(event.defaultPrevented, true, `${key} swallows the literal character`);
    assert.deepEqual(actionRuns.at(-1), [id, 'keyboard'], `${key} runs ${id}`);
  }
  offered.delete('open_claude');
  offered.delete('edit_page');
  const runsBeforeMissing = actionRuns.length;
  assert.notEqual(press(acting, { key: ']' }).defaultPrevented, true, 'an unoffered Claude handoff stays inert');
  assert.notEqual(press(acting, { key: '\\' }).defaultPrevented, true, 'backslash belongs to the palette, not keyboard-nav');
  assert.notEqual(press(acting, { key: 'u' }).defaultPrevented, true, 'a page without an edit URL keeps u inert');
  assert.equal(actionRuns.length, runsBeforeMissing, 'unavailable actions never run');
  assert.notEqual(press(acting, { key: '[', target: input }).defaultPrevented, true, '[ yields to a text field');

  // ------------------------------------------------- o folds and unfolds all
  const folding = setup({ withTree: false });
  const sidebarShell = new Element('div');
  sidebarShell.id = 'td-shell-sidebar';
  const toggles = ['one', 'two'].map((name, index) => {
    const button = new Element('button');
    button.setAttribute('data-td-shell-tree-toggle', '');
    button.setAttribute('aria-controls', 'group-' + name);
    button.setAttribute('aria-expanded', index === 0 ? 'true' : 'false');
    button.onclick = () => button.setAttribute('aria-expanded',
      String(button.getAttribute('aria-expanded') !== 'true'));
    sidebarShell.appendChild(button);
    return button;
  });
  const strayToggle = new Element('button');
  strayToggle.setAttribute('data-td-shell-tree-toggle', '');
  strayToggle.setAttribute('aria-controls', 'outside');
  strayToggle.setAttribute('aria-expanded', 'false');
  folding.root.appendChild(sidebarShell);
  folding.root.appendChild(strayToggle);
  const detailsBlocks = [new Element('details'), new Element('details')];
  detailsBlocks[0].open = true;
  detailsBlocks.forEach((el) => folding.root.appendChild(el));
  const codeRoot = new Element('div', 'is-collapsible td-is-collapsed');
  codeRoot.setAttribute('data-td-code', '');
  const codeButton = new Element('button');
  codeButton.setAttribute('data-td-code-expand', '');
  codeButton.onclick = () => {
    if (codeRoot.classList.contains('td-is-collapsed')) codeRoot.classList.remove('td-is-collapsed');
    else codeRoot.classList.add('td-is-collapsed');
  };
  codeRoot.appendChild(codeButton);
  folding.root.appendChild(codeRoot);

  const oEvent = press(folding, { key: 'o' });
  assert.equal(oEvent.defaultPrevented, true, 'o swallows the literal character');
  assert.deepEqual(toggles.map((b) => b.getAttribute('aria-expanded')), ['true', 'true'], 'o expands every sidebar group');
  assert.equal(strayToggle.getAttribute('aria-expanded'), 'false', 'o leaves disclosures outside the rails alone');
  assert.deepEqual(detailsBlocks.map((el) => el.open), [true, true], 'o opens every details block');
  assert.equal(codeRoot.classList.contains('td-is-collapsed'), false, 'o unfolds shortened code blocks');
  assert.equal(folding.html.hasAttribute('data-td-kbd-instant'), true, 'the fold runs in one instant frame');
  folding.frames.splice(0).forEach((fn) => fn());
  assert.equal(folding.html.hasAttribute('data-td-kbd-instant'), false, 'transitions return after the frame');

  press(folding, { key: 'o' });
  assert.deepEqual(toggles.map((b) => b.getAttribute('aria-expanded')), ['false', 'false'], 'a second o collapses the groups');
  assert.deepEqual(detailsBlocks.map((el) => el.open), [false, false], 'a second o closes every details block');
  assert.equal(codeRoot.classList.contains('td-is-collapsed'), true, 'a second o shortens code blocks again');
  // Rapid second press before the first rAF runs: the stale frame must not
  // clear data-td-kbd-instant while the newer fold is still settling.
  press(folding, { key: 'o' });
  assert.equal(folding.frames.length, 2);
  folding.frames.shift()();
  assert.equal(folding.html.hasAttribute('data-td-kbd-instant'), true, 'stale rAF does not clear instant flag early');
  folding.frames.shift()();
  assert.equal(folding.html.hasAttribute('data-td-kbd-instant'), false, 'latest rAF clears instant flag');
  // Collapse back so the following OinkSidebar test starts from collapsed state.
  press(folding, { key: 'o' });
  folding.frames.splice(0).forEach((fn) => fn());

  // With the shared disclosure state, o commits through its API source so the
  // reader's active path stays open on collapse.
  const committed = [];
  global.OinkSidebar = {
    setExpanded(id, expanded, opts) { committed.push([id, expanded, opts.source]); return true; },
  };
  press(folding, { key: 'o' });
  delete global.OinkSidebar;
  assert.deepEqual(committed, [['group-one', true, 'api'], ['group-two', true, 'api']],
    'o commits sidebar groups through OinkSidebar with the api source');
  assert.notEqual(press(setup({ withTree: false }), { key: 'o' }).defaultPrevented, true,
    'o stays inert on a page with nothing to fold');

  // Hidden/collapsed rails and Zen Mode do not hijack o or keep expand-all live.
  const zenFold = setup({ withTree: false, withHelp: true });
  const zenSidebar = new Element('aside');
  zenSidebar.id = 'td-shell-sidebar';
  const zenPanel = new Element('div', 'td-shell-sidebar__panel');
  const zenToggle = new Element('button');
  zenToggle.setAttribute('data-td-shell-tree-toggle', '');
  zenToggle.setAttribute('aria-controls', 'zen-group');
  zenToggle.setAttribute('aria-expanded', 'false');
  zenPanel.appendChild(zenToggle);
  zenSidebar.appendChild(zenPanel);
  zenFold.root.appendChild(zenSidebar);
  const zenDetails = new Element('details');
  zenDetails.open = true;
  const hiddenWrap = new Element('div');
  hiddenWrap.hidden = true;
  const hiddenDetails = new Element('details');
  hiddenDetails.open = false;
  hiddenWrap.appendChild(hiddenDetails);
  zenFold.root.appendChild(zenDetails);
  zenFold.root.appendChild(hiddenWrap);
  // Desktop collapsed sidebar isolates the panel; o ignores its closed toggle
  // and closes the visible open <details> on the first press.
  zenFold.html.setAttribute('data-td-shell-sidebar', 'collapsed');
  zenPanel.setAttribute('aria-hidden', 'true');
  press(zenFold, { key: 'o' });
  assert.equal(zenDetails.open, false, 'o ignores collapsed-rail toggles and closes an open details on the first press');
  assert.equal(zenToggle.getAttribute('aria-expanded'), 'false', 'o does not toggle a collapsed sidebar');
  assert.equal(hiddenDetails.open, false, 'o ignores details inside [hidden]');
  // In Zen Mode with no article foldables, o stays inert and help dims expand-all.
  zenFold.html.removeAttribute('data-td-shell-sidebar');
  zenPanel.removeAttribute('aria-hidden');
  zenFold.root.children = zenFold.root.children.filter((c) => c !== zenDetails && c !== hiddenWrap);
  zenFold.html.setAttribute('data-td-kbd-zen', '');
  assert.notEqual(press(zenFold, { key: 'o' }).defaultPrevented, true,
    'o does nothing in Zen Mode when only hidden rails have foldables');
  press(zenFold, { key: "'" });
  const zenDialog = zenFold.root.querySelector('[data-td-keyboard-dialog]');
  const zenExpandRow = zenDialog.querySelectorAll('[data-td-shortcut]')
    .find((row) => row.getAttribute('data-td-shortcut') === 'expand-all');
  assert.equal(zenExpandRow.classList.contains('td-is-unavailable'), true,
    'help dims expand-all in Zen Mode when no article foldables exist');

  // Anchor preservation scans article blocks (no elementFromPoint required)
  // and compensates scrollY when a <details> above the reading line opens.
  const anchored = setup({ withTree: false });
  anchored.win.scrollY = 400;
  const anchorArticle = new Element('article', 'td-shell-article');
  const anchorContent = new Element('div', 'td-content');
  const anchorFold = new Element('details');
  anchorFold.open = false;
  const anchorList = new Element('li');
  const anchorHeading = new Element('h2');
  let shift = 0;
  anchorList.getBoundingClientRect = () => ({ top: -100 + shift, bottom: 500 + shift, height: 600 });
  anchorHeading.getBoundingClientRect = () => ({ top: 72 + shift, bottom: 108 + shift, height: 36 });
  anchorList.appendChild(anchorHeading);
  anchorContent.appendChild(anchorFold);
  anchorContent.appendChild(anchorList);
  anchorArticle.appendChild(anchorContent);
  anchored.root.appendChild(anchorArticle);
  Object.defineProperty(anchorFold, 'open', {
    get() { return this._open || false; },
    set(value) { this._open = Boolean(value); shift = this._open ? 320 : 0; },
  });
  press(anchored, { key: 'o' });
  assert.equal(anchored.win.scrollY, 720, 'o preserves the deepest visible article block without elementFromPoint');
  anchored.frames.splice(0).forEach((fn) => fn());

  // P falls back to window.print() when no registry owns print, and respects
  // unavailable print descriptors in both the key handler and help dialog.
  const fallbackPrint = setup({ withTree: false });
  assert.equal(press(fallbackPrint, { key: 'p' }).defaultPrevented, true, 'P prints via window.print fallback');
  assert.equal(fallbackPrint.win.printed, 1);
  const blockedPrint = setup({
    withTree: false,
    withHelp: true,
    registry: {
      get(id) { return id === 'print' ? { id: 'print', available: false } : null; },
      run() { throw new Error('must not run unavailable print'); },
    },
  });
  assert.notEqual(press(blockedPrint, { key: 'p' }).defaultPrevented, true,
    'P respects an unavailable print descriptor instead of bypassing the registry');
  assert.equal(blockedPrint.win.printed, 0);
  press(blockedPrint, { key: "'" });
  const blockedPrintRow = blockedPrint.root.querySelector('[data-td-keyboard-dialog]')
    .querySelectorAll('[data-td-shortcut]')
    .find((row) => row.getAttribute('data-td-shortcut') === 'print');
  assert.equal(blockedPrintRow.classList.contains('td-is-unavailable'), true,
    'help dims P when print is unavailable');

  // ------------------------------------------------- - and = page width
  const sized = setup({ withTree: false });
  const shellMain = new Element('div', 'td-shell-main');
  shellMain.clientWidth = 1600;
  const article = new Element('article', 'td-shell-article');
  const natural = () => Math.min(1050, shellMain.clientWidth);
  article.getBoundingClientRect = () => {
    if (!sized.html.hasAttribute('data-td-shell-article-w')) return { top: 0, width: natural() };
    const value = sized.html.style.props['--td-shell-article-w'];
    return { top: 0, width: value === 'none' ? shellMain.clientWidth : Math.min(parseFloat(value), shellMain.clientWidth) };
  };
  shellMain.appendChild(article);
  sized.root.appendChild(shellMain);
  const width = () => article.getBoundingClientRect().width;
  const stored = () => sized.win.localStorage.getItem('td-shell-article-w');

  assert.equal(press(sized, { key: '=' }).defaultPrevented, true, '= swallows the literal character');
  assert.equal(width(), 1150, '= widens the reading column by one step');
  assert.equal(stored(), '1150', 'the reader width persists');
  press(sized, { key: '+', shiftKey: true });
  assert.equal(width(), 1250, '+ (Shift+=) widens as well');
  assert.equal(press(sized, { key: '=', shiftKey: true }).defaultPrevented, true, 'ISO/JIS shifted = widens as well');
  assert.equal(width(), 1350, 'ISO/JIS shifted = steps width up');
  press(sized, { key: '-' });
  assert.equal(width(), 1250, 'return to 1250 for max-step check');
  for (let n = 0; n < 4; n += 1) press(sized, { key: '=' });
  assert.equal(stored(), 'none', 'reaching the container stores "none" so wider screens still fill');
  assert.equal(width(), 1600, 'the column never outgrows its container');
  press(sized, { key: '-' });
  assert.equal(width(), 1500, '- narrows from the rendered width');
  for (let n = 0; n < 4; n += 1) press(sized, { key: '-' });
  assert.equal(width(), 1100);
  press(sized, { key: '-' });
  assert.equal(sized.html.hasAttribute('data-td-shell-article-w'), false, 'a step across the page width returns to it');
  assert.equal(stored(), null, 'returning to the page width forgets the reader width');
  assert.equal(width(), 1050);
  for (let n = 0; n < 6; n += 1) press(sized, { key: '-' });
  assert.equal(width(), 600, 'the column stops at the minimum reading width');
  press(sized, { key: '-' });
  assert.equal(width(), 600, 'the minimum dwells');
  for (let n = 0; n < 4; n += 1) press(sized, { key: '=' });
  assert.equal(width(), 1000);
  press(sized, { key: '=' });
  assert.equal(stored(), null, 'widening onto the page width also returns to it');
  assert.notEqual(press(setup({ withTree: false }), { key: '=' }).defaultPrevented, true,
    '= stays inert without a reading column');
  // A column that already fills its container has nowhere to grow; the press
  // must not leave a "fill" preference that a wider screen would inherit.
  shellMain.clientWidth = 1000;
  press(sized, { key: '=' });
  assert.equal(stored(), null, '= at the container edge records nothing');
  assert.equal(sized.html.hasAttribute('data-td-shell-article-w'), false);
  press(sized, { key: '-' });
  assert.equal(stored(), '900', '- still narrows a full column');

  // Book reading_width: slim constrains .td-content (768px) inside a 1050px
  // .td-shell-article with 96px horizontal padding (effective width 864px).
  const bookSized = setup({ withTree: false });
  const bookMain = new Element('div', 'td-shell-main');
  bookMain.clientWidth = 1320;
  const bookArticle = new Element('article', 'td-shell-article');
  const bookContent = new Element('div', 'td-content');
  bookArticle.appendChild(bookContent);
  bookMain.appendChild(bookArticle);
  bookSized.root.appendChild(bookMain);
  bookSized.win.getComputedStyle = (el) => ({
    display: 'block',
    visibility: 'visible',
    getPropertyValue(name) {
      if (el === bookArticle && (name === 'padding-left' || name === 'padding-right')) return '48px';
      return '';
    },
  });
  bookArticle.getBoundingClientRect = () => {
    if (!bookSized.html.hasAttribute('data-td-shell-article-w')) return { top: 0, width: 1050 };
    const value = bookSized.html.style.props['--td-shell-article-w'];
    return { top: 0, width: value === 'none' ? bookMain.clientWidth : Math.min(parseFloat(value), bookMain.clientWidth) };
  };
  bookContent.getBoundingClientRect = () => {
    const inner = bookArticle.getBoundingClientRect().width - 96;
    return { top: 0, width: bookSized.html.hasAttribute('data-td-shell-article-w') ? inner : Math.min(768, inner) };
  };
  press(bookSized, { key: '-' });
  assert.equal(bookSized.win.localStorage.getItem('td-shell-article-w'), '764',
    '- narrows Book slim from its effective content+padding width (864 -> 764)');
  assert.equal(bookContent.getBoundingClientRect().width, 668,
    '- narrows visible Book slim .td-content by exactly 100px');
  press(bookSized, { key: '=' });
  assert.equal(bookSized.win.localStorage.getItem('td-shell-article-w'), null,
    '= from narrowed Book slim snaps back to Book slim and clears storage');
  assert.equal(bookContent.getBoundingClientRect().width, 768);
  press(bookSized, { key: '=' });
  assert.equal(bookSized.win.localStorage.getItem('td-shell-article-w'), '964',
    '= widens Book slim by exactly 100px instead of jumping past 1050px');
  assert.equal(bookContent.getBoundingClientRect().width, 868);

  // ------------------------------------------------- collapsed desktop tree
  const collapsed = setup({ sidebarToggle: true });
  collapsed.html.setAttribute('data-td-shell-sidebar', 'collapsed');
  const restore = collapsed.root.querySelector('[data-td-shell-sidebar-toggle]');
  press(collapsed, { key: 's' });
  assert.equal(restore.clicks, 1, 'WASD restores a collapsed desktop sidebar');
  assert.equal(
    collapsed.doc.activeElement && collapsed.doc.activeElement.getAttribute('href'),
    '/docs/c/',
    'restoring the sidebar keeps one-step movement semantics',
  );

  // ------------------------------------------------------------- drawer
  const drawer = setup({ drawerOpener: true });
  const opener = drawer.root.querySelector('[data-td-shell-drawer-open]');
  press(drawer, { key: 'w' });
  assert.equal(opener.clicks, 1, 'WASD opens the closed drawer first');
  drawer.frames.splice(0).forEach((fn) => fn());
  drawer.frames.splice(0).forEach((fn) => fn());
  assert.equal(
    drawer.doc.activeElement && drawer.doc.activeElement.getAttribute('href'),
    '/docs/b/one/',
    'the drawer press focuses the active link without moving',
  );
  drawer.html.setAttribute('data-td-shell-drawer', 'open');
  press(drawer, { key: 'Escape' });
  assert.ok(
    drawer.doc.activeElement,
    'Escape with an open drawer is left to docs-shell',
  );

  // ------------------------------------------------ embedded map canvas guard
  const mapHost = setup({ articleWidth: true });
  const mapCanvas = new Element('div', 'td-map__canvas');
  mapCanvas.setAttribute('data-td-map-canvas', '');
  const mapMarker = new Element('div', 'td-map__marker');
  mapCanvas.appendChild(mapMarker);
  mapHost.root.appendChild(mapCanvas);
  for (const key of ['-', '=', '+', 'w', 'j']) {
    const ev = press(mapHost, { key, shiftKey: key === '+', target: mapMarker });
    assert.notEqual(ev.defaultPrevented, true, `key ${key} yields while focus is inside an interactive map`);
  }
  assert.equal(mapHost.html.hasAttribute('data-td-shell-article-w'), false,
    '+ / - inside a map must not resize the reading column');

  // Turning off single-key shortcuts suppresses ' inside shortcut help and
  // updates the dialog close hint; narrow viewports dim page-width.
  helpRun.html.setAttribute('data-td-shortcuts-off', '');
  const offClick = {
    type: 'click',
    target: triggerIcon,
    button: 0,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() {},
  };
  (helpRun.doc.listeners.get('click') || []).forEach((fn) => fn(offClick));
  assert.equal(helpDialog.open, true, 'clicking ? still opens help when single-key shortcuts are off');
  assert.equal(helpClose.getAttribute('aria-keyshortcuts'), 'Escape', 'close button omits apostrophe when shortcuts are off');
  assert.equal(helpClose.getAttribute('title'), 'Close (Esc)', 'close title omits apostrophe when shortcuts are off');
  press(helpRun, { key: "'" });
  assert.equal(helpDialog.open, true, "apostrophe does not close help when single-key shortcuts are off");
  press(helpRun, { key: 'Escape' });
  assert.equal(helpDialog.open, false, 'Escape still closes help when single-key shortcuts are off');
  helpRun.html.removeAttribute('data-td-shortcuts-off');

  const narrowHelp = setup({ withTree: false, withHelp: true });
  const narrowMain = new Element('div', 'td-shell-main');
  narrowMain.clientWidth = 540;
  const narrowArticle = new Element('article', 'td-shell-article');
  narrowMain.appendChild(narrowArticle);
  narrowHelp.root.appendChild(narrowMain);
  press(narrowHelp, { key: "'" });
  const narrowWidthRow = narrowHelp.root.querySelector('[data-td-keyboard-dialog]').querySelectorAll('[data-td-shortcut]')
    .find((el) => el.getAttribute('data-td-shortcut') === 'page-width');
  assert.equal(narrowWidthRow.classList.contains('td-is-unavailable'), true,
    'narrow viewports below the minimum reading width dim page-width');
  press(narrowHelp, { key: 'Escape' });

  console.log('keyboard navigation checks passed');
})();
