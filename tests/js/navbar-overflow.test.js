'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

function loadNavbarMenu() {
  const target = path.join(__dirname, '..', '..', 'assets/js/navbar-menu.js');
  delete require.cache[require.resolve(target)];
  require(target);
}

function makeClassList(initial = []) {
  const set = new Set(initial);
  return {
    add(...values) {
      values.forEach((v) => set.add(v));
    },
    remove(...values) {
      values.forEach((v) => set.delete(v));
    },
    contains(value) {
      return set.has(value);
    },
    toggle(value, force) {
      if (force === true) set.add(value);
      else if (force === false) set.delete(value);
      else if (set.has(value)) set.delete(value);
      else set.add(value);
      return set.has(value);
    },
    toString() {
      return Array.from(set).join(' ');
    },
  };
}

function makeNode(tagName, opts = {}) {
  const attrs = new Map(Object.entries(opts.attrs || {}));
  const listeners = new Map();
  const children = [];
  let text = opts.textContent || '';
  const cl = makeClassList(
    opts.className ? String(opts.className).split(/\s+/).filter(Boolean) : [],
  );

  const node = {
    tagName: tagName.toUpperCase(),
    classList: cl,
    get className() {
      return cl.toString();
    },
    set className(value) {
      const next = String(value || '').split(/\s+/).filter(Boolean);
      const current = cl.toString().split(/\s+/).filter(Boolean);
      current.forEach((c) => cl.remove(c));
      next.forEach((c) => cl.add(c));
    },
    dataset: {},
    hidden: Boolean(opts.hidden),
    parentNode: null,
    children,
    get textContent() {
      if (children.length) {
        return children.map((c) => c.textContent).join('');
      }
      return text;
    },
    set textContent(value) {
      text = String(value || '');
      children.forEach((c) => {
        c.parentNode = null;
      });
      children.length = 0;
    },
    appendChild(child) {
      if (child.isFragment) {
        child.children.slice().forEach((c) => node.appendChild(c));
        child.children.length = 0;
        return child;
      }
      if (child.parentNode && child.parentNode.children) {
        const idx = child.parentNode.children.indexOf(child);
        if (idx >= 0) child.parentNode.children.splice(idx, 1);
      }
      child.parentNode = node;
      children.push(child);
      return child;
    },
    cloneNode(deep) {
      const clone = makeNode(node.tagName, {
        className: node.className,
        attrs: Object.fromEntries(attrs.entries()),
        textContent: children.length ? '' : text,
        hidden: node.hidden,
      });
      if (deep) {
        children.forEach((c) => clone.appendChild(c.cloneNode(true)));
      }
      return clone;
    },
    contains(candidate) {
      if (candidate === node) return true;
      return children.some((c) => c.contains(candidate));
    },
    getAttribute(name) {
      return attrs.has(name) ? attrs.get(name) : null;
    },
    hasAttribute(name) {
      return attrs.has(name);
    },
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    removeAttribute(name) {
      attrs.delete(name);
    },
    addEventListener(type, cb) {
      const list = listeners.get(type) || [];
      list.push(cb);
      listeners.set(type, list);
    },
    dispatch(type, event = {}) {
      (listeners.get(type) || []).forEach((cb) => cb(event));
    },
    focus() {
      global.document.activeElement = node;
    },
    getBoundingClientRect() {
      if (typeof opts.getRect === 'function') return opts.getRect(node);
      return { left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0 };
    },
    querySelector(selector) {
      return node.querySelectorAll(selector)[0] || null;
    },
    querySelectorAll(selector) {
      const parts = selector.split(',').map((s) => s.trim());
      const out = [];
      function matchesSingle(el, sel) {
        if (sel === 'a[href]') return el.tagName === 'A' && el.hasAttribute('href');
        if (sel === 'a') return el.tagName === 'A';
        if (sel === 'button:not([disabled])')
          return el.tagName === 'BUTTON' && !el.hasAttribute('disabled');
        if (sel.startsWith('.')) return el.classList.contains(sel.slice(1));
        if (sel.startsWith('[') && sel.endsWith(']')) {
          return el.hasAttribute(sel.slice(1, -1));
        }
        return false;
      }
      function walk(parent) {
        for (const child of parent.children) {
          if (parts.some((sel) => matchesSingle(child, sel))) out.push(child);
          walk(child);
        }
      }
      walk(node);
      return out;
    },
  };
  return node;
}

function makeNavItem({ label, href, hasIcon = true, active = false, fullWidth = 100, iconWidth = 34, navRef, children = null }) {
  function makeLink(cls, lbl, url, iconFlag, isActive, extraAttrs = {}) {
    const a = makeNode('a', {
      className: cls + (isActive ? ' active' : ''),
      attrs: {
        href: url,
        'aria-label': lbl,
        'data-td-navbar-region': 'desktop',
        'data-td-navbar-label': lbl,
        'data-td-navbar-icon': iconFlag ? 'true' : 'false',
        'data-td-navbar-route': '',
        ...extraAttrs,
      },
      getRect() {
        const compact = navRef.el && navRef.el.getAttribute('data-td-nav-compact') === 'icons';
        const w = compact && iconFlag ? iconWidth : fullWidth;
        return { left: 0, right: w, top: 0, bottom: 34, width: w, height: 34 };
      },
    });
    if (iconFlag) {
      a.appendChild(makeNode('i', { className: 'fa-solid fa-book', attrs: { 'aria-hidden': 'true' } }));
    }
    a.appendChild(makeNode('span', { className: 'td-navbar-entry__label', textContent: lbl }));
    return a;
  }

  if (!children) {
    return makeLink('nav-link', label, href, hasIcon, active);
  }
  const menu = makeNode('div', {
    className: 'td-nav-menu',
    attrs: { 'data-td-navbar-menu': '' },
    getRect() {
      const compact = navRef.el && navRef.el.getAttribute('data-td-nav-compact') === 'icons';
      const w = compact && hasIcon ? iconWidth : fullWidth;
      return { left: 0, right: w, top: 0, bottom: 34, width: w, height: 34 };
    },
  });
  menu.appendChild(
    makeLink('nav-link td-nav-menu__parent-link', label, href, hasIcon, active, {
      'aria-controls': 'sub-panel',
      'aria-expanded': 'false',
    }),
  );
  const subPanel = makeNode('div', {
    className: 'td-nav-menu__panel',
    attrs: { id: 'sub-panel', 'data-td-navbar-panel': '' },
    hidden: true,
  });
  children.forEach((child) => {
    subPanel.appendChild(makeLink('td-nav-menu__item-link', child.label, child.href, true, Boolean(child.active)));
  });
  menu.appendChild(subPanel);
  return menu;
}

function setupEnvironment({ navWidth, brandWidth = 120, utilWidth = 280, colGap = 16, gap = 4, sidebarWidth = 0, sidebarCollapsed = false, itemsSpec }) {
  const state = { navWidth, brandWidth, utilWidth, sidebarWidth, sidebarCollapsed };
  const navRef = { el: null };
  const docListeners = new Map();
  const winListeners = new Map();
  const registered = new Map();
  const closedOthers = [];

  const html = makeNode('html');
  if (sidebarCollapsed) html.setAttribute('data-td-shell-sidebar', 'collapsed');

  const brand = makeNode('a', {
    className: 'td-nav-brand',
    getRect: () => ({ left: 16, right: 16 + state.brandWidth, width: state.brandWidth, height: 34 }),
  });
  const util = makeNode('div', {
    className: 'td-nav-links td-nav-util-zone',
    getRect: () => ({ left: state.navWidth - state.utilWidth, right: state.navWidth, width: state.utilWidth, height: 34 }),
  });
  const trigger = makeNode('button', {
    className: 'td-nav-overflow__trigger',
    attrs: {
      'data-td-nav-overflow-toggle': '',
      'aria-expanded': 'false',
      'aria-controls': 'td-nav-overflow-panel',
    },
    getRect: () => ({ left: 0, right: 34, width: 34, height: 34 }),
  });
  const panel = makeNode('div', {
    className: 'td-nav-menu__panel td-nav-overflow__panel',
    attrs: { id: 'td-nav-overflow-panel', 'data-td-nav-overflow-panel': '' },
    hidden: true,
  });
  const overflow = makeNode('div', {
    className: 'td-nav-overflow',
    attrs: { 'data-td-nav-overflow': '' },
    hidden: true,
    getRect: () => ({ left: 0, right: 34, width: 34, height: 34 }),
  });
  overflow.appendChild(trigger);
  overflow.appendChild(panel);

  const zone = makeNode('div', { className: 'td-nav-links td-nav-menu-zone' });
  const nav = makeNode('nav', {
    className: 'td-site-nav',
    getRect: () => ({ left: 16, right: 16 + state.navWidth, width: state.navWidth, height: 50 }),
  });
  navRef.el = nav;

  const items = itemsSpec.map((spec) => makeNavItem({ ...spec, navRef }));
  items.forEach((item) => zone.appendChild(item));
  zone.appendChild(overflow);

  nav.appendChild(brand);
  nav.appendChild(zone);
  nav.appendChild(util);

  let sidebar = null;
  if (sidebarWidth > 0) {
    sidebar = makeNode('aside', {
      className: 'td-shell-sidebar',
      attrs: { id: 'td-shell-sidebar' },
      getRect: () => ({ left: 0, right: state.sidebarWidth, width: state.sidebarWidth, height: 800 }),
    });
    const sbPanel = makeNode('div', {
      className: 'td-shell-sidebar__panel',
      getRect: () => ({ left: 0, right: state.sidebarWidth, width: state.sidebarWidth, height: 800 }),
    });
    sidebar.appendChild(sbPanel);
  }

  global.document = {
    activeElement: null,
    documentElement: html,
    createElement(tag) {
      return makeNode(tag);
    },
    createDocumentFragment() {
      return {
        isFragment: true,
        children: [],
        appendChild(child) {
          this.children.push(child);
          return child;
        },
      };
    },
    getElementById(id) {
      return id === 'td-shell-sidebar' ? sidebar : null;
    },
    addEventListener(type, cb) {
      const list = docListeners.get(type) || [];
      list.push(cb);
      docListeners.set(type, list);
    },
    querySelectorAll(selector) {
      if (selector === '.td-site-nav') return [nav];
      if (selector === '[data-td-navbar-menu]') return items.filter((el) => el.hasAttribute('data-td-navbar-menu'));
      return [];
    },
  };

  global.window = {
    innerWidth: state.navWidth + 32,
    addEventListener(type, cb) {
      const list = winListeners.get(type) || [];
      list.push(cb);
      winListeners.set(type, list);
    },
    requestAnimationFrame(cb) {
      cb();
      return 1;
    },
    setTimeout(cb) {
      cb();
      return 1;
    },
    clearTimeout() {},
    getComputedStyle(el) {
      if (el === nav) return { columnGap: `${colGap}px`, direction: 'ltr', display: 'grid' };
      if (el === zone) return { columnGap: `${gap}px`, gap: `${gap}px`, display: 'flex' };
      return { display: 'flex', visibility: 'visible' };
    },
    matchMedia() {
      return { matches: false };
    },
    OinkSurfaceCoordinator: {
      register(name, close) {
        registered.set(name, close);
      },
      closeOthers(name) {
        closedOthers.push(name);
      },
    },
  };

  loadNavbarMenu();

  return {
    state,
    nav,
    zone,
    overflow,
    trigger,
    panel,
    items,
    html,
    registered,
    closedOthers,
    triggerResize(nextNavWidth) {
      state.navWidth = nextNavWidth;
      global.window.innerWidth = nextNavWidth + 32;
      (winListeners.get('resize') || []).forEach((cb) => cb());
    },
    dispatchDoc(type, event) {
      (docListeners.get(type) || []).forEach((cb) => cb(event));
    },
  };
}

test('navbar progresses smoothly through full -> icon-only -> overflow disclosure and restores when widened', () => {
  const env = setupEnvironment({
    navWidth: 1100, // maxW = 1100 - 120 - 280 - 32 = 668
    itemsSpec: [
      { label: 'Documentation', href: '/docs/', fullWidth: 120, iconWidth: 34 },
      { label: 'Handbook', href: '/book/', fullWidth: 110, iconWidth: 34 },
      { label: 'Tutorials', href: '/tutorials/', fullWidth: 110, iconWidth: 34 },
      {
        label: 'Community',
        href: '/community/',
        fullWidth: 110,
        iconWidth: 34,
        active: true,
        children: [{ label: 'Releases', href: '/community/releases/' }],
      },
      { label: 'Showcase', href: '/case/', fullWidth: 110, iconWidth: 34 },
    ],
  });

  // Stage 1: Full text fits (560 + 16 = 576 <= 668)
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), null);
  assert.equal(env.overflow.hidden, true);
  assert.equal(env.items.every((el) => !el.hasAttribute('data-td-nav-overflowed')), true);

  // Stage 2: Narrow so full labels exceed maxW (maxW = 900 - 432 = 468 < 576), icons fit (5*34 + 16 = 186 <= 468)
  env.triggerResize(900);
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), 'icons');
  assert.equal(env.overflow.hidden, true);
  assert.equal(env.items.every((el) => !el.hasAttribute('data-td-nav-overflowed')), true);

  // Stage 3: Narrow further so even icons exceed maxW (maxW = 580 - 432 = 148 < 186)
  // 3 items + more = 3*34 + 2*4 + 4 + 34 = 148 <= 148 -> items[3], items[4] overflow!
  env.triggerResize(580);
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), 'icons');
  assert.equal(env.overflow.hidden, false);
  assert.equal(env.items[0].hasAttribute('data-td-nav-overflowed'), false);
  assert.equal(env.items[1].hasAttribute('data-td-nav-overflowed'), false);
  assert.equal(env.items[2].hasAttribute('data-td-nav-overflowed'), false);
  assert.equal(env.items[3].hasAttribute('data-td-nav-overflowed'), true);
  assert.equal(env.items[4].hasAttribute('data-td-nav-overflowed'), true);

  // Trigger highlights active state because overflowed item[3] is active.
  assert.equal(env.trigger.classList.contains('active'), true);

  // Projected panel restores full labels & child hierarchy without duplicating region/route/id.
  const projectedLinks = env.panel.querySelectorAll('a[href]');
  assert.deepEqual(
    projectedLinks.map((a) => a.getAttribute('href')),
    ['/community/', '/community/releases/', '/case/'],
  );
  assert.equal(projectedLinks.every((a) => !a.hasAttribute('data-td-navbar-region')), true);
  assert.equal(projectedLinks.every((a) => !a.hasAttribute('data-td-navbar-route')), true);
  assert.equal(projectedLinks.every((a) => !a.hasAttribute('id')), true);

  // Click opens disclosure and notifies coordinator; ArrowDown/Escape navigate cleanly.
  env.trigger.dispatch('click');
  assert.equal(env.panel.hidden, false);
  assert.equal(env.trigger.getAttribute('aria-expanded'), 'true');
  assert.deepEqual(env.closedOthers, ['navbar-overflow-0']);

  const down = { key: 'ArrowDown', preventDefault() { this.defaultPrevented = true; } };
  env.panel.dispatch('keydown', down);
  assert.equal(document.activeElement, projectedLinks[0]);

  const esc = {
    key: 'Escape',
    defaultPrevented: false,
    propagationStopped: false,
    preventDefault() { this.defaultPrevented = true; },
    stopPropagation() { this.propagationStopped = true; },
  };
  env.panel.dispatch('keydown', esc);
  assert.equal(env.panel.hidden, true);
  assert.equal(esc.defaultPrevented, true);
  assert.equal(esc.propagationStopped, true);
  assert.equal(document.activeElement, env.trigger);

  // Clicking a non-focusable part (e.g. scrollbar) emits focusout with null relatedTarget;
  // it must not prematurely dismiss the panel, while outside pointerdown does.
  env.trigger.dispatch('click');
  assert.equal(env.panel.hidden, false);
  env.overflow.dispatch('focusout', { relatedTarget: null });
  assert.equal(env.panel.hidden, false);
  env.dispatchDoc('pointerdown', { target: makeNode('div') });
  assert.equal(env.panel.hidden, true);

  // Widening restores full labels and hides the overflow control.
  env.triggerResize(1100);
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), null);
  assert.equal(env.overflow.hidden, true);
  assert.equal(env.trigger.classList.contains('active'), false);
  assert.equal(env.items.every((el) => !el.hasAttribute('data-td-nav-overflowed')), true);
});

test('iconless entries skip icon collapse and overflow directly into the disclosure', () => {
  const env = setupEnvironment({
    navWidth: 700, // maxW = 700 - 120 - 280 - 32 = 268
    itemsSpec: [
      { label: 'Overview', href: '/overview/', hasIcon: false, fullWidth: 100 },
      { label: 'Reference', href: '/reference/', hasIcon: false, fullWidth: 100 },
      { label: 'Guides', href: '/guides/', hasIcon: false, fullWidth: 100 },
    ],
  });

  // Total is 308 > 268, none have icons -> no data-td-nav-compact, 2 fit + more (204 + 4 + 34 = 242 <= 268).
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), null);
  assert.equal(env.overflow.hidden, false);
  assert.equal(env.items[0].hasAttribute('data-td-nav-overflowed'), false);
  assert.equal(env.items[1].hasAttribute('data-td-nav-overflowed'), false);
  assert.equal(env.items[2].hasAttribute('data-td-nav-overflowed'), true);
});

test('desktop fixed sidebar overlap reduces menu budget until collapsed', () => {
  const env = setupEnvironment({
    navWidth: 960,
    brandWidth: 100,
    utilWidth: 280,
    sidebarWidth: 270, // sidebarOverlap = 270 - 16 = 254, minStart = 262 -> maxW = min(548, 402, 436) = 402
    itemsSpec: [
      { label: 'Docs', href: '/docs/', fullWidth: 110, iconWidth: 34 },
      { label: 'Book', href: '/book/', fullWidth: 110, iconWidth: 34 },
      { label: 'Case', href: '/case/', fullWidth: 110, iconWidth: 34 },
      { label: 'Blog', href: '/blog/', fullWidth: 110, iconWidth: 34 },
    ],
  });

  // Full width = 452 > 402 -> automatically switches to icons while sidebar is open.
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), 'icons');
  assert.equal(env.overflow.hidden, true);

  // Collapsing the sidebar reclaims the full 548px budget -> returns to full text!
  env.html.setAttribute('data-td-shell-sidebar', 'collapsed');
  env.triggerResize(960);
  assert.equal(env.nav.getAttribute('data-td-nav-compact'), null);
  assert.equal(env.overflow.hidden, true);
});
