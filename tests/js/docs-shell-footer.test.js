'use strict';

// The footer is shared by two independently optional rails. Exercise the
// real initializer, including event coalescing and footer-height changes;
// rendered rail geometry belongs to the documentation site's browser suite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(
  path.join(__dirname, '..', '..', 'assets/js/docs-shell.js'),
  'utf8',
);

function build({ footer = true, sidebar = true, toc = true, visual = false, top = 1100, observer = true } = {}) {
  const properties = new Map();
  const attrs = new Map();
  const listeners = new Map();
  const documentListeners = new Map();
  const viewportListeners = new Map();
  const frames = new Map();
  const measurements = { top, reads: 0, writes: 0 };
  const footerElement = {
    getBoundingClientRect() {
      measurements.reads += 1;
      return { top: measurements.top };
    },
  };
  const mainElement = {};
  const observed = new Set();
  let resize;
  let frameID = 0;
  const html = {
    style: {
      setProperty(name, value) {
        measurements.writes += 1;
        properties.set(name, value);
      },
    },
    hasAttribute(name) { return attrs.has(name); },
    getAttribute(name) { return attrs.get(name) || null; },
    setAttribute(name, value) { attrs.set(name, value); },
    removeAttribute(name) { attrs.delete(name); },
  };
  const document = {
    documentElement: html,
    querySelector(selector) {
      if (selector === '[data-td-shell-footer]') return footer ? footerElement : null;
      // Return only the rail-presence query used by footer-offset. Other
      // initializers should take their ordinary missing-component exits.
      if (selector === '.td-shell-sidebar__panel') return sidebar ? {} : null;
      if (selector === '.td-shell-sidebar__panel, .td-shell-toc__panel') {
        return sidebar || toc ? {} : null;
      }
      return null;
    },
    querySelectorAll() { return []; },
    getElementById(id) { return id === 'td-main-content' ? mainElement : null; },
    addEventListener(name, callback) { documentListeners.set(name, callback); },
    dispatchEvent(event) {
      const callback = documentListeners.get(event.type);
      if (callback) callback(event);
    },
  };
  const window = {
    innerHeight: 1000,
    addEventListener(name, callback) { listeners.set(name, callback); },
    requestAnimationFrame(callback) {
      frames.set(++frameID, callback);
      return frameID;
    },
    matchMedia() { return { matches: false, addEventListener() {} }; },
    ResizeObserver: class {},
  };
  if (!observer) delete window.ResizeObserver;
  if (visual) {
    window.visualViewport = {
      height: 800,
      offsetTop: 0,
      addEventListener(name, callback) { viewportListeners.set(name, callback); },
    };
  }
  const context = {
    window,
    document,
    ResizeObserver: class {
      constructor(callback) { resize = callback; }
      observe(target) { observed.add(target); }
    },
  };
  vm.runInNewContext(SOURCE, context);
  const flush = () => {
    for (let guard = 0; frames.size && guard < 20; guard += 1) {
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback());
    }
  };
  flush();
  return {
    window, document, measurements, listeners, viewportListeners, flush,
    resize() { assert.ok(observed.has(footerElement)); resize(); },
    reflow() { assert.ok(observed.has(mainElement)); resize(); },
    offset() { return properties.get('--td-shell-footer-offset'); },
  };
}

for (const rails of [
  { sidebar: true, toc: true },
  { sidebar: true, toc: false },
  { sidebar: false, toc: true },
]) {
  test(`footer tracks visible height with ${JSON.stringify(rails)}`, () => {
    const env = build(rails);
    assert.equal(env.offset(), '0px');
    env.measurements.top = 670;
    env.listeners.get('scroll')();
    env.flush();
    assert.equal(env.offset(), '331px');
    env.measurements.top = 1200;
    env.listeners.get('scroll')();
    env.flush();
    assert.equal(env.offset(), '0px');
  });

  test(`tab reflow refreshes the footer boundary without scrolling with ${JSON.stringify(rails)}`, () => {
    const env = build({ ...rails, top: 670 });
    assert.equal(env.offset(), '331px');
    const reads = env.measurements.reads;

    env.measurements.top = 1200;
    env.document.dispatchEvent({ type: 'td:tab-shown' });
    assert.equal(env.measurements.reads, reads);
    env.flush();
    assert.equal(env.offset(), '0px');

    env.measurements.top = 670;
    env.document.dispatchEvent({ type: 'td:tab-shown' });
    env.flush();
    assert.equal(env.offset(), '331px');
  });
}

test('scroll bursts share one measurement and a resized footer is observed', () => {
  const env = build();
  const reads = env.measurements.reads;
  env.measurements.top = 700;
  for (let i = 0; i < 10; i += 1) env.listeners.get('scroll')();
  assert.equal(env.measurements.reads, reads);
  env.flush();
  assert.equal(env.measurements.reads, reads + 1);
  assert.equal(env.offset(), '301px');

  env.measurements.top = 950;
  env.resize();
  env.flush();
  assert.equal(env.offset(), '51px');

  env.window.innerHeight = 900;
  env.listeners.get('resize')();
  env.flush();
  assert.equal(env.offset(), '0px');
});

test('an unchanged boundary is measured but not written to the root again', () => {
  // The footer is off screen for most of a long page. Writing the same
  // custom property to the root on every scroll frame invalidates styles
  // for nothing.
  const env = build();
  assert.equal(env.offset(), '0px');
  const { reads, writes } = env.measurements;
  for (let i = 0; i < 5; i += 1) {
    env.measurements.top = 1100 + i * 40;
    env.listeners.get('scroll')();
    env.flush();
  }
  assert.equal(env.measurements.reads, reads + 5);
  assert.equal(env.measurements.writes, writes);
  env.measurements.top = 700;
  env.listeners.get('scroll')();
  env.flush();
  assert.equal(env.measurements.writes, writes + 1);
  assert.equal(env.offset(), '301px');
});

test('fixed rails use layout coordinates during pinch zoom and visual panning', () => {
  const env = build({ sidebar: false, visual: true, top: 650 });
  assert.equal(env.offset(), '351px');

  env.window.visualViewport.height = 500;
  env.viewportListeners.get('resize')();
  env.flush();
  assert.equal(env.offset(), '351px');

  env.window.visualViewport.offsetTop = 300;
  env.viewportListeners.get('scroll')();
  env.flush();
  assert.equal(env.offset(), '351px');

  env.window.innerHeight = 900;
  env.listeners.get('resize')();
  env.flush();
  assert.equal(env.offset(), '251px');

  env.measurements.top = 1200;
  env.listeners.get('scroll')();
  env.flush();
  assert.equal(env.offset(), '0px');
});

for (const absent of [{ footer: false }, { sidebar: false, toc: false }]) {
  test(`no footer measurements without a consumer: ${JSON.stringify(absent)}`, () => {
    const env = build(absent);
    assert.equal(env.offset(), undefined);
    assert.equal(env.measurements.reads, 0);
    assert.equal(env.listeners.has('scroll'), false);
  });
}

// Scroll restoration may place the footer in view before the first event.
test('TOC-only restored page receives its initial footer boundary', () => {
  const env = build({ sidebar: false, top: 670 });
  assert.equal(env.offset(), '331px');
  assert.equal(env.measurements.reads, 1);
});

test('scroll and resize still update the TOC without ResizeObserver', () => {
  const env = build({ sidebar: false, observer: false });
  env.measurements.top = 700;
  env.listeners.get('scroll')();
  env.flush();
  assert.equal(env.offset(), '301px');
  env.window.innerHeight = 900;
  env.listeners.get('resize')();
  env.flush();
  assert.equal(env.offset(), '201px');
});

test('mixed observer, window and visual viewport events share one frame', () => {
  const env = build({ sidebar: false, visual: true });
  const reads = env.measurements.reads;
  env.measurements.top = 700;
  env.listeners.get('scroll')();
  env.listeners.get('resize')();
  env.viewportListeners.get('scroll')();
  env.viewportListeners.get('resize')();
  env.document.dispatchEvent({ type: 'td:tab-shown' });
  env.resize();
  assert.equal(env.measurements.reads, reads);
  env.flush();
  assert.equal(env.measurements.reads, reads + 1);
  assert.equal(env.offset(), '301px');
});

// Content can move the footer even when its own dimensions remain unchanged.
test('main-content reflow clears and restores the offset without a scroll or tab event', () => {
  const env = build({ sidebar: false, top: 670 });
  const reads = env.measurements.reads;
  assert.equal(env.offset(), '331px');
  env.measurements.top = 3100;
  env.reflow();
  env.reflow();
  assert.equal(env.measurements.reads, reads);
  env.flush();
  assert.equal(env.measurements.reads, reads + 1);
  assert.equal(env.offset(), '0px');
  env.measurements.top = 900;
  env.reflow();
  env.flush();
  assert.equal(env.offset(), '101px');
});
