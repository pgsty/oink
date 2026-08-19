'use strict';

// Headless contract tests for the table-of-contents rail in
// assets/js/docs-shell.js: which entry the cursor lands on, which end of the
// lit range the dot parks at, and the pin that rescues entries no scroll can
// reach. A DOM shim covers exactly the calls initToc makes; every other init
// in the file bails on its own missing selector.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(
  path.join(__dirname, '..', '..', 'assets/js/docs-shell.js'),
  'utf8',
);

const VIEWPORT = 800;
const DOC_HEIGHT = 3000;
const MAX_SCROLL = DOC_HEIGHT - VIEWPORT; // 2200
const LINE = 74; // resolved scroll-padding-top, as the shell sets it
const ROW = 32; // one TOC row, 20px line box in 6px of padding

// Document offsets of the headings. The last one sits inside the closing
// screenful: reaching the line would need 2776px of scroll and only 2200 exist.
const HEADINGS = [100, 600, 1100, 1600, 2100, 2850];
const DEPTHS = [2, 2, 3, 2, 2, 2]; // Hugo starts its outline at depth 2.

function styleBag(initial) {
  const props = new Map(Object.entries(initial || {}));
  return {
    setProperty(name, value) {
      props.set(name, String(value));
    },
    getPropertyValue(name) {
      return props.get(name) || '';
    },
    get map() {
      return props;
    },
  };
}

function svgStub() {
  return {
    style: {},
    children: [],
    setAttribute() {},
    appendChild(child) {
      this.children.push(child);
    },
    // Only the accent path is ever measured. Distances map linearly onto the
    // y range so the binary search in distanceAtY stays invertible.
    getTotalLength() {
      return 180;
    },
    getPointAtLength(d) {
      return { y: 18 + d };
    },
  };
}

function build() {
  const scroll = { y: 0 };
  const hash = { value: '' };
  const rafQueue = [];
  const listeners = new Map();
  const registered = [];
  let intersect = null;

  const html = {
    scrollHeight: DOC_HEIGHT,
    clientHeight: VIEWPORT,
    style: styleBag(),
    getAttribute() {
      return null;
    },
    setAttribute() {},
    removeAttribute() {},
    hasAttribute() {
      return false;
    },
  };

  const headings = HEADINGS.map((docTop, i) => ({
    id: 'h' + i,
    getBoundingClientRect() {
      const top = docTop - scroll.y;
      return { top, bottom: top + 40 };
    },
  }));

  const tocNav = { tagName: 'NAV' };
  const rootList = { tagName: 'UL', parentElement: tocNav };
  const links = DEPTHS.map((depth, i) => {
    // depth 2 is nav > ul > li > a; depth 3 adds one more ul/li pair.
    let parent = { tagName: 'LI', parentElement: rootList };
    if (depth === 3) {
      const inner = { tagName: 'UL', parentElement: parent };
      parent = { tagName: 'LI', parentElement: inner };
    }
    const attrs = new Map();
    const classes = new Set();
    return {
      hash: '#h' + i,
      parentElement: parent,
      offsetTop: 12 + i * ROW,
      clientHeight: ROW,
      style: styleBag(),
      classList: {
        toggle(name, force) {
          if (force) classes.add(name);
          else classes.delete(name);
        },
        contains(name) {
          return classes.has(name);
        },
      },
      setAttribute(name, value) {
        attrs.set(name, value);
      },
      removeAttribute(name) {
        attrs.delete(name);
      },
      getAttribute(name) {
        return attrs.has(name) ? attrs.get(name) : null;
      },
      appendChild() {},
      getBoundingClientRect() {
        return { top: 100, bottom: 130 };
      },
    };
  });

  let overlay = null;
  const body = {
    querySelector() {
      return tocNav;
    },
    querySelectorAll(selector) {
      return selector.indexOf('rail') >= 0 ? [] : links.slice();
    },
    appendChild(child) {
      overlay = child;
    },
    getBoundingClientRect() {
      return { top: 0, bottom: 1000 };
    },
  };

  const document = {
    documentElement: html,
    querySelector() {
      return null;
    },
    querySelectorAll() {
      return [];
    },
    addEventListener() {},
    getElementById(id) {
      if (id === 'td-shell-toc-body') return body;
      return headings.find((h) => h.id === id) || null;
    },
    createElement(tag) {
      return {
        tagName: tag.toUpperCase(),
        style: styleBag(),
        children: [],
        appendChild(child) {
          this.children.push(child);
        },
        remove() {},
      };
    },
    createElementNS(_ns, tag) {
      const el = svgStub();
      el.tagName = tag;
      return el;
    },
  };

  const computed = styleBag({ 'scroll-padding-top': LINE + 'px' });
  computed.paddingTop = '6px';
  computed.paddingBottom = '6px';

  const window = {
    get scrollY() {
      return scroll.y;
    },
    get location() {
      return { hash: hash.value };
    },
    getComputedStyle() {
      return computed;
    },
    matchMedia() {
      return { matches: false, addEventListener() {} };
    },
    requestAnimationFrame(cb) {
      rafQueue.push(cb);
      return rafQueue.length;
    },
    addEventListener(name, cb) {
      listeners.set(name, cb);
    },
    CSS: {
      registerProperty(definition) {
        registered.push(definition);
      },
    },
  };

  const context = {
    window,
    document,
    getComputedStyle: () => computed,
    IntersectionObserver: class {
      constructor(cb) {
        intersect = cb;
      }
      observe() {}
    },
  };
  context.globalThis = context;
  vm.runInNewContext(SOURCE, context);

  const flush = () => {
    for (let guard = 0; rafQueue.length && guard < 20; guard += 1) {
      rafQueue.splice(0, rafQueue.length).forEach((cb) => cb());
    }
  };
  flush();

  const state = () => {
    // The range is published as distances along the accent path (dash start
    // and length) plus a 0/1 end selector; the dot's offset is the CSS calc
    // start + lead * length, and the stub's linear 18+d mapping turns path
    // distances back into y.
    const start = parseFloat(
      overlay.style.getPropertyValue('--td-shell-track-start'),
    );
    const length = parseFloat(
      overlay.style.getPropertyValue('--td-shell-track-length'),
    );
    const lead = overlay.style.getPropertyValue('--td-shell-dot-lead');
    const current = links.filter(
      (a) => a.getAttribute('aria-current') === 'location',
    );
    const active = links.filter((a) => a.classList.contains('active'));
    return {
      top: 18 + start,
      bottom: 18 + start + length,
      lead,
      dotY: 18 + start + parseFloat(lead) * length,
      current: current.map((a) => a.hash),
      first: active.length ? links.indexOf(active[0]) : -1,
      last: active.length ? links.indexOf(active[active.length - 1]) : -1,
    };
  };

  return {
    links,
    headings,
    registered,
    state,
    scrollTo(y) {
      scroll.y = Math.min(Math.max(y, 0), MAX_SCROLL);
      listeners.get('scroll')();
      flush();
    },
    setHash(value) {
      hash.value = value;
      listeners.get('hashchange')();
      flush();
    },
    see(indexes) {
      intersect(
        headings.map((el, i) => ({
          target: el,
          isIntersecting: indexes.includes(i),
        })),
      );
    },
  };
}

test('the cursor is the last heading above the scroll line', () => {
  const toc = build();
  // Nothing has crossed the line yet: no entry claims the reader's place.
  assert.deepEqual(toc.state().current, []);

  toc.scrollTo(100); // h0 top is now 0, above the 82px edge
  assert.deepEqual(toc.state().current, ['#h0']);

  toc.scrollTo(600);
  assert.deepEqual(toc.state().current, ['#h1']);

  toc.scrollTo(1100);
  assert.deepEqual(toc.state().current, ['#h2']);

  // Deep inside a section the cursor stays on the heading that opened it.
  toc.scrollTo(1400);
  assert.deepEqual(toc.state().current, ['#h2']);
});

test('exactly one entry carries aria-current, and it is inside the lit range', () => {
  const toc = build();
  toc.scrollTo(1100);
  toc.see([3, 4]); // Two later headings on screen; h2 is the one behind us.
  const s = toc.state();
  assert.equal(s.current.length, 1);
  assert.equal(s.current[0], '#h2');
  assert.equal(s.first, 2, 'the cursor extends the range up to itself');
  assert.equal(s.last, 4);
});

test('the dot leads the range: bottom going down, top going back up', () => {
  const toc = build();
  toc.scrollTo(1100);
  let s = toc.state();
  assert.ok(
    Math.abs(s.dotY - s.bottom) < 0.5,
    'downward parks the dot at the bottom',
  );

  // A nudge is jitter, not a change of direction.
  toc.scrollTo(1090);
  s = toc.state();
  assert.ok(
    Math.abs(s.dotY - s.bottom) < 0.5,
    'a 10px reversal does not flip it',
  );

  toc.scrollTo(1000);
  s = toc.state();
  assert.ok(
    Math.abs(s.dotY - s.top) < 0.5,
    'a real reversal flips it to the top',
  );

  toc.scrollTo(1200);
  s = toc.state();
  assert.ok(
    Math.abs(s.dotY - s.bottom) < 0.5,
    'resuming downward flips it back',
  );
});

test('the animated properties are registered, typed, and inherited', () => {
  // The CSS minifier drops @property rules, so the script registers the
  // three values the overlay transitions; without types they would snap.
  const toc = build();
  const bySyntax = Object.fromEntries(
    toc.registered.map((d) => [d.name, d.syntax]),
  );
  assert.deepEqual(bySyntax, {
    '--td-shell-track-start': '<length>',
    '--td-shell-track-length': '<length>',
    '--td-shell-dot-lead': '<number>',
  });
  assert.ok(
    toc.registered.every((d) => d.inherits === true),
    'the path and the dot read these from the overlay, so they must inherit',
  );
});

test('the script only ever selects an end: the lead factor is 0 or 1', () => {
  // The dot's position is the CSS calc start + lead * length over the same
  // animated values the dash is drawn from, so it caps the lit line by
  // construction — as long as the script confines itself to whole ends.
  const toc = build();
  [400, 1800, 900, 2100, MAX_SCROLL, 0].forEach((y) => {
    toc.scrollTo(y);
    const lead = toc.state().lead;
    assert.ok(
      lead === '0' || lead === '1',
      'lead is ' + lead + ' after scrolling to ' + y,
    );
  });
  toc.see([2, 3]);
  const lead = toc.state().lead;
  assert.ok(lead === '0' || lead === '1', 'lead off an end after a range change');
});

test('an entry no scroll can reach is pinned by the hash, then released', () => {
  const toc = build();
  toc.setHash('#h5'); // The closing heading: 2776px of scroll needed, 2200 exist.
  toc.scrollTo(MAX_SCROLL);
  assert.deepEqual(
    toc.state().current,
    ['#h5'],
    'the request wins where position cannot',
  );

  const s = toc.state();
  assert.ok(
    s.first <= 5 && s.last >= 5,
    'the pinned entry is inside the lit range',
  );

  // Scrolled out of view, the address bar no longer speaks for the reader.
  toc.scrollTo(600);
  assert.deepEqual(toc.state().current, ['#h1']);
});

test('a reachable hash is left to the positional rule', () => {
  const toc = build();
  toc.setHash('#h4'); // 2100 - 74 = 2026, inside the 2200px of available scroll.
  toc.scrollTo(1100);
  assert.deepEqual(toc.state().current, ['#h2'], 'position still decides');
});

test('each entry gets a pill offset that clears its own indent', () => {
  const toc = build();
  const x = (i) => toc.links[i].style.getPropertyValue('--td-shell-toc-pill-x');
  assert.equal(
    x(0),
    '14px',
    'top-level entries indent 20px, so the pill starts at 14',
  );
  assert.equal(
    x(2),
    '26px',
    'nested entries indent 32px, so the pill starts at 26',
  );
});
