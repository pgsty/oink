'use strict';

// Scheduling contract of the content-component adapter: which engine is
// requested, when, and what a reader is left with when it is not there.
// Rendered charts and players belong to the documentation site's browser suite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(
  path.join(__dirname, '../../assets/js/content-components.js'),
  'utf8',
);

const ENGINES = {
  echarts: { src: '/third_party/echarts/echarts.min.abc.js', integrity: 'sha256-chart' },
  asciinema: { src: '/third_party/asciinema/asciinema-player.min.def.js', integrity: '' },
};

function element(tag) {
  const attrs = new Map();
  const node = {
    tag,
    className: '',
    textContent: '',
    hidden: false,
    children: [],
    parent: null,
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    getAttribute(name) {
      return attrs.has(name) ? attrs.get(name) : null;
    },
    appendChild(child) {
      child.parent = node;
      node.children.push(child);
      return child;
    },
    remove() {
      if (!node.parent) return;
      node.parent.children = node.parent.children.filter((child) => child !== node);
      node.parent = null;
    },
  };
  return node;
}

function build({ observer = true, preloaded = false, themes = null, theme = null, registerThemeError = null } = {}) {
  const requests = [];
  const mounted = [];
  const calls = [];
  const listeners = new Map();
  const observed = new Set();
  let intersect = null;
  let margin = '';

  const chart = (name) => {
    const root = element('div');
    const canvas = element('div');
    root.name = name;
    root.canvas = canvas;
    root.getAttribute = (name) => (name === 'data-theme' ? theme : null);
    root.querySelector = (selector) => {
      if (selector === '[data-td-echarts-options]') {
        return { textContent: '{"series":[{"type":"bar","data":[1,2]}]}' };
      }
      if (selector === '[data-td-echarts-canvas]') return canvas;
      return null;
    };
    return root;
  };
  const charts = [chart('first'), chart('second')];
  const player = element('div');
  player.name = 'player';
  player.querySelector = () => null;

  const echarts = {
    registerTheme(name, value) {
      calls.push(['registerTheme', name, value]);
      if (registerThemeError) throw registerThemeError;
    },
    init(target, chosen) {
      calls.push(['init', chosen]);
      mounted.push(charts.find((root) => root.canvas === target).name);
      return { setOption() {}, resize() {}, dispose() {} };
    },
  };

  const document = {
    documentElement: { getAttribute: () => 'light' },
    head: {
      appendChild(script) {
        requests.push(script);
      },
    },
    createElement: element,
    querySelector(selector) {
      return selector === '[data-td-component-engines]'
        ? { textContent: JSON.stringify(ENGINES) }
        : null;
    },
    querySelectorAll(selector) {
      if (selector === '[data-td-echarts]') return charts;
      if (selector === '[data-td-asciinema]') return [player];
      return [];
    },
    addEventListener() {},
  };
  const window = {
    addEventListener(name, callback) {
      listeners.set(name, callback);
    },
    matchMedia() {
      return { addEventListener() {} };
    },
  };
  if (preloaded) window.echarts = echarts;
  if (themes) window.OinkEchartsThemes = themes;

  const context = {
    window,
    document,
    console: { error() {} },
    MutationObserver: class {
      observe() {}
    },
    Promise,
    JSON,
    Map,
    Error,
    Object,
  };
  if (observer) {
    context.IntersectionObserver = class {
      constructor(callback, options) {
        intersect = callback;
        margin = options.rootMargin;
      }
      observe(target) {
        observed.add(target);
      }
      unobserve(target) {
        observed.delete(target);
      }
    };
  }
  vm.runInNewContext(SOURCE, context);

  return {
    charts,
    player,
    requests,
    mounted,
    calls,
    observed,
    margin: () => margin,
    // Promise reactions of the adapter run before this resolves.
    settle: () => new Promise((resolve) => setImmediate(resolve)),
    due(...roots) {
      intersect(roots.map((target) => ({ target, isIntersecting: true })));
    },
    away(...roots) {
      intersect(roots.map((target) => ({ target, isIntersecting: false })));
    },
    arrive() {
      window.echarts = echarts;
      requests.find((script) => script.src === ENGINES.echarts.src).onload();
    },
    fail() {
      requests.find((script) => script.src === ENGINES.echarts.src).onerror();
    },
    fire(name) {
      listeners.get(name)();
    },
  };
}

const sources = (root) =>
  root.children.filter((child) => child.className === 'td-echarts-source');

test('a page requests no engine until a component is due', () => {
  const page = build();
  assert.equal(page.requests.length, 0);
  assert.deepEqual([...page.observed], [page.player, ...page.charts]);
  // Everything above the reader is due at once; below, a short scroll ahead.
  assert.equal(page.margin(), '1000000px 0px 320px 0px');
  page.away(...page.charts);
  assert.equal(page.requests.length, 0);
});

test('due charts share one engine request, verified, and mount when it arrives', async () => {
  const page = build();
  page.due(page.charts[0]);
  page.due(page.charts[1]);
  page.due(page.charts[0]);
  assert.equal(page.requests.length, 1);
  assert.equal(page.requests[0].src, ENGINES.echarts.src);
  assert.equal(page.requests[0].integrity, 'sha256-chart');
  assert.equal(page.requests[0].crossOrigin, 'anonymous');
  assert.deepEqual(page.mounted, []);
  page.arrive();
  await page.settle();
  assert.deepEqual(page.mounted, ['first', 'second']);
  assert.equal(page.observed.has(page.charts[0]), false);
});

test('one kind of component does not fetch the engine of another', () => {
  const page = build();
  page.due(page.player);
  assert.deepEqual(
    page.requests.map((script) => script.src),
    [ENGINES.asciinema.src],
  );
  // No integrity was published for it, so none is demanded.
  assert.equal(page.requests[0].integrity, undefined);
});

test('an engine that cannot load leaves the declared source in place of the chart', async () => {
  const page = build();
  page.due(page.charts[0]);
  page.fail();
  await page.settle();
  const [source] = sources(page.charts[0]);
  assert.ok(source, 'the reader still sees what the author wrote');
  assert.match(source.children[0].textContent, /"type": "bar"/);
  assert.equal(source.children[0].className, 'language-echarts');
  assert.equal(page.charts[0].canvas.hidden, true);
  assert.deepEqual(page.mounted, []);
});

test('printing shows the source of what has not mounted, then takes it back', async () => {
  const page = build();
  page.due(page.charts[0]);
  page.arrive();
  await page.settle();
  page.fire('beforeprint');
  page.fire('beforeprint');
  assert.equal(sources(page.charts[0]).length, 0, 'a mounted chart prints as it is');
  assert.equal(sources(page.charts[1]).length, 1);
  assert.equal(page.charts[1].canvas.hidden, true);
  page.fire('afterprint');
  assert.equal(sources(page.charts[1]).length, 0);
  assert.equal(page.charts[1].canvas.hidden, false);
  // The chart is still due later, and still mounts.
  page.due(page.charts[1]);
  await page.settle();
  assert.deepEqual(page.mounted, ['first', 'second']);
});

test('an engine the site loaded itself is used without a second request', async () => {
  const page = build({ preloaded: true });
  page.due(page.charts[0]);
  await page.settle();
  assert.equal(page.requests.length, 0);
  assert.deepEqual(page.mounted, ['first']);
});

test('without IntersectionObserver every component is due at load', () => {
  const page = build({ observer: false });
  assert.deepEqual(
    page.requests.map((script) => script.src).sort(),
    [ENGINES.asciinema.src, ENGINES.echarts.src].sort(),
  );
});

test('site themes are registered before a chart draws with one', async () => {
  // ECharts loads only when a chart is due, so the site names its themes on
  // window.OinkEchartsThemes and the adapter registers them first.
  const brand = { color: ['#0b5394'] };
  const page = build({ themes: { brand, broken: 'not a theme' }, theme: 'brand' });
  page.due(page.charts[0]);
  page.arrive();
  await page.settle();
  assert.deepEqual(page.calls, [
    ['registerTheme', 'brand', brand],
    ['init', 'brand'],
  ]);
});

test('without site themes a chart draws with the colour scheme alone', async () => {
  const page = build();
  page.due(page.charts[0]);
  page.arrive();
  await page.settle();
  assert.deepEqual(page.calls, [['init', null]]);
});

test('a throwing site theme degrades into an alert fallback', async () => {
  const page = build({
    themes: { broken: { bad: true } },
    theme: 'broken',
    registerThemeError: new Error('bad theme'),
  });
  page.due(page.charts[0]);
  page.arrive();
  await page.settle();
  assert.equal(page.charts[0].canvas.getAttribute('role'), 'alert');
  assert.equal(page.charts[0].canvas.textContent, 'ECharts: bad theme');
  assert.deepEqual(page.mounted, []);
});
