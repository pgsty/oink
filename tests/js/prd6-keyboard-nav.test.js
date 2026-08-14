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
    this.id = '';
    this.nodeType = 1;
    this.offsetParent = {};
    this.style = { scrollBehavior: '' };
    this.clicks = 0;
    this.textContent = '';
    this.ownerDocument = null;
  }
  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }
  hasAttribute(name) { return this.attributes.has(name); }
  removeAttribute(name) { this.attributes.delete(name); }
  matches(selector) {
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
    if (selector === '[data-td-theme-toggle]') return this.hasAttribute('data-td-theme-toggle');
    if (selector === '[data-theme-toggle]') return this.hasAttribute('data-theme-toggle');
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
  focus() { if (this.ownerDocument) this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument) this.ownerDocument.activeElement = null; }
  click() { this.clicks += 1; if (this.onclick) this.onclick(); }
  scrollIntoView() {}
  getBoundingClientRect() { return { top: 0 }; }
}

function link(href, className = '') {
  const el = new Element('a', 'td-shell-tree__link ' + className);
  el.setAttribute('href', href);
  return el;
}

// A foldable tree matching the sidebar markup: row + chevron + children div.
// Chevron clicks mimic docs-shell.js (flip aria-expanded, toggle is-open).
function treeItem({ href, className = '', expanded = null, children = [] }) {
  const item = new Element('li', 'td-shell-tree__item ' + className);
  const row = new Element('div', 'td-shell-tree__row');
  const anchor = link(href);
  row.appendChild(anchor);
  item.appendChild(row);
  let childWrap = null;
  if (children.length) {
    childWrap = new Element('div', 'td-shell-tree__children' + (expanded ? ' is-open' : ''));
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
        if (open) childWrap.classList.remove('is-open');
        else childWrap.classList.add('is-open');
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

function setup({
  withTree = true,
  drawerOpener = false,
  sidebarToggle = false,
  registry = null,
  palette = null,
  reducedMotion = true,
  scrollPadding = null,
  scrollMargin = '0px',
  session = {},
  shell = true,
} = {}) {
  const html = new Element('html');
  const root = new Element('body', shell ? 'td-shell-chrome' : '');
  const doc = {
    documentElement: html,
    activeElement: null,
    listeners: new Map(),
    body: root,
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
  const win = {
    scrolled: [],
    scrolledTo: [],
    assigned: [],
    hashes: [],
    location: { href: 'https://example.test/docs/b/one/', pathname: '/docs/b/one/', search: '' },
    scrollBy(x, y) { this.scrolled.push(y); },
    scrollTo(x, y) { this.scrolledTo.push(y); this.scrollY = y; },
    scrollY: 0,
    requestAnimationFrame(callback) { frames.push(callback); },
    matchMedia() { return { matches: reducedMotion }; },
    setTimeout(callback) { timeouts.push(callback); return timeouts.length; },
    clearTimeout() {},
    sessionStorage: memoryStorage(session),
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

  own(root);
  own(html);

  const controller = nav.init({ document: doc, window: win, registry, palette });
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
  const textarea = new Element('textarea');
  const editable = new Element('div');
  editable.closest = (selector) =>
    selector.includes('contenteditable') ? editable : null;
  const plain = new Element('div');
  plain.closest = () => null;
  assert.equal(nav.isTypingTarget(input), true);
  assert.equal(nav.isTypingTarget(textarea), true);
  assert.equal(nav.isTypingTarget(editable), true);
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

  // ------------------------------------------------- activate and escape
  press(fold, { key: ' ' });
  assert.equal(fold.doc.activeElement.clicks, 1, 'Space activates the focused link');
  press(fold, { key: 'g' });
  assert.equal(fold.doc.activeElement.clicks, 2, 'g activates the focused link');
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

  // ---------------------------------------------------------- h zen mode
  const zen = setup();
  press(zen, { key: 'h' });
  assert.equal(zen.html.hasAttribute('data-td-kbd-zen'), true, 'h hides the chrome');
  assert.equal(zen.win.sessionStorage.getItem('td-kbd-zen'), '1', 'zen persists');
  press(zen, { key: 'h' });
  assert.equal(zen.html.hasAttribute('data-td-kbd-zen'), false, 'h restores the chrome');
  assert.equal(zen.win.sessionStorage.getItem('td-kbd-zen'), null, 'zen state clears');

  const zenBack = setup({ session: { 'td-kbd-zen': '1' } });
  assert.equal(
    zenBack.html.hasAttribute('data-td-kbd-zen'),
    true,
    'a previous page\'s zen mode re-applies on load',
  );
  const zenTree = press(zenBack, { key: 's' });
  assert.equal(zenBack.doc.activeElement, null, 'zen mode must not focus its hidden tree');
  assert.notEqual(zenTree.defaultPrevented, true, 'zen mode must not swallow WASD');

  // ------------------------------------------------------------ l and t
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
  };
  const lang = setup({ registry: langRegistry });
  press(lang, { key: 'l' });
  assert.deepEqual(lang.win.assigned, ['/zh/docs/b/one/'], 'l cycles to the next language');

  const singleLang = setup({
    registry: { get: () => ({ available: false, options: [] }) },
  });
  press(singleLang, { key: 'l' });
  assert.deepEqual(singleLang.win.assigned, [], 'a single-language site keeps l silent');

  const themeRuns = [];
  const themeRegistry = {
    get: (id) => (id === 'switch_theme' ? { available: true } : null),
    run(id, context) { themeRuns.push([id, context.value]); return { then() {} }; },
  };
  const theme = setup({ registry: themeRegistry });
  press(theme, { key: 't' });
  assert.deepEqual(themeRuns, [['switch_theme', 'dark']], 'an unset theme flips to dark');
  theme.html.setAttribute('data-bs-theme', 'dark');
  press(theme, { key: 't' });
  assert.deepEqual(themeRuns[1], ['switch_theme', 'light'], 'a dark theme flips to light');

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

  const noPalette = setup();
  const idle = press(noPalette, { key: 'f' });
  assert.notEqual(idle.defaultPrevented, true, 'f without a palette stays inert');

  // ---------------------------------------- global landing-page shortcuts
  const landingRuns = [];
  const landing = setup({
    withTree: false,
    shell: false,
    registry: {
      get(id) {
        if (id === 'switch_theme') return { available: true };
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
    session: { 'td-kbd-zen': '1' },
  });
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
  press(landing, { key: 't' });
  assert.deepEqual(landingRuns, [['switch_theme', 'dark']], 't works outside the shell');
  press(landing, { key: 'l' });
  assert.deepEqual(
    landing.win.assigned,
    ['/', '/zh/'],
    'l works outside the shell',
  );
  const landingScrolls = landing.win.scrolled.length;
  press(landing, { key: 'j' });
  press(landing, { key: 'q' });
  press(landing, { key: 'h' });
  assert.equal(landing.win.scrolled.length, landingScrolls, 'shell navigation stays inert on landing pages');
  assert.equal(landing.html.hasAttribute('data-td-kbd-zen'), false, 'landing pages do not inherit or toggle shell zen mode');

  // A standalone consumer homepage can bridge the same global actions with
  // data attributes, without loading the action registry or palette bundle.
  const bridge = setup({ withTree: false, shell: false });
  const bridgeTheme = new Element('button');
  bridgeTheme.setAttribute('data-theme-toggle', '');
  bridge.root.appendChild(bridgeTheme);
  const bridgeLanguage = new Element('a');
  bridgeLanguage.setAttribute('data-td-language-route', '');
  bridgeLanguage.setAttribute('href', '/zh/');
  bridge.root.appendChild(bridgeLanguage);
  const bridgeSearch = new Element('a');
  bridgeSearch.setAttribute('data-td-keyboard-search-route', '');
  bridgeSearch.setAttribute('href', '/docs/');
  bridge.root.appendChild(bridgeSearch);
  press(bridge, { key: 't' });
  assert.equal(bridgeTheme.clicks, 1, 't clicks a standalone homepage theme bridge');
  press(bridge, { key: 'l' });
  assert.deepEqual(bridge.win.assigned, ['/zh/'], 'l follows a standalone language bridge');
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

  // -------------------------------------------------- collapsed desktop tree
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

  console.log('PRD 6 keyboard navigation checks passed');
})();
