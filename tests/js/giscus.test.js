'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// No network: an already mounted comment frame records the configuration
// messages it would receive when the reader changes style or mode.
test('Giscus follows preset and mode while explicit author themes remain authoritative', () => {
  const attributes = new Map([['data-td-preset', 'paper'], ['data-bs-theme', 'light']]);
  const root = { getAttribute: key => attributes.get(key) };
  const messages = [];
  const section = {
    dataset: {
      loaded: 'true', theme: 'auto',
      tdThemeLight: '/legacy-light.css', tdThemeDark: '/legacy-dark.css',
      tdPresetThemes: JSON.stringify({
        paper: { light: '/paper-light.css', dark: '/paper-dark.css' },
        slate: { light: '/slate-light.css', dark: '/slate-dark.css' },
      }),
    },
    querySelector: () => ({ contentWindow: { postMessage: (message, origin) => messages.push({ message, origin }) } }),
  };
  let notify;
  const MutationObserver = class {
    constructor(callback) { notify = callback; }
    observe(target, options) {
      assert.equal(target, root);
      assert.deepEqual(Array.from(options.attributeFilter), ['data-bs-theme', 'data-td-preset']);
    }
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../assets/js/giscus.js'), 'utf8'), {
    document: { documentElement: root, querySelectorAll: () => [section] },
    window: { location: { origin: 'https://example.org' }, matchMedia: () => ({ matches: true, addEventListener() {} }) },
    MutationObserver, URL,
  });
  function expectTheme(theme) {
    notify();
    const last = messages.at(-1);
    assert.equal(last.origin, 'https://giscus.app');
    assert.equal(last.message.giscus.setConfig.theme, theme);
  }
  expectTheme('https://example.org/paper-light.css');
  attributes.delete('data-bs-theme');
  expectTheme('https://example.org/paper-light.css');
  attributes.set('data-bs-theme', 'dark');
  expectTheme('https://example.org/paper-dark.css');
  attributes.set('data-td-preset', 'slate');
  expectTheme('https://example.org/slate-dark.css');
  section.dataset.theme = 'dark_high_contrast';
  attributes.set('data-td-preset', 'paper');
  expectTheme('dark_high_contrast');
  section.dataset.theme = '/custom.css';
  expectTheme('https://example.org/custom.css');
  section.dataset.theme = 'auto';
  section.dataset.tdPresetThemes = '{}';
  expectTheme('https://example.org/legacy-dark.css');
});

// When the third-party script is requested. The widget itself is not run.
function comments({ search = '', loading = 'lazy', observer = true } = {}) {
  const scripts = [];
  const observed = new Set();
  let intersect = null;
  let margin = '';
  const section = {
    dataset: { repo: 'pgsty/oink', theme: 'light', loading },
    setAttribute() {},
    querySelector(selector) {
      if (selector === '[data-td-giscus-container]') return { appendChild: script => scripts.push(script) };
      return null;
    },
  };
  const context = {
    document: {
      documentElement: { getAttribute: () => 'light' },
      querySelectorAll: () => [section],
      createElement: () => {
        const attributes = new Map();
        return { attributes, setAttribute: (name, value) => attributes.set(name, value), addEventListener() {} };
      },
    },
    window: { location: { origin: 'https://example.org', search }, matchMedia: () => ({ matches: false, addEventListener() {} }) },
    MutationObserver: class { observe() {} },
    URL,
  };
  if (observer) {
    context.IntersectionObserver = class {
      constructor(callback, options) { intersect = callback; margin = options.rootMargin; }
      observe(target) { observed.add(target); }
      unobserve(target) { observed.delete(target); }
    };
  }
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../assets/js/giscus.js'), 'utf8'), context);
  return {
    scripts, observed, section, margin: () => margin,
    report: isIntersecting => intersect([{ target: section, isIntersecting }]),
  };
}

test('the comment widget is not requested until a reader comes near it', () => {
  const page = comments();
  assert.equal(page.scripts.length, 0);
  assert.ok(page.observed.has(page.section));
  // Within a scroll below, or anywhere above: loading above would move the page.
  assert.equal(page.margin(), '1000000px 0px 600px 0px');
  page.report(false);
  assert.equal(page.scripts.length, 0);
  page.report(true);
  page.report(true);
  assert.equal(page.scripts.length, 1);
  assert.equal(page.scripts[0].attributes.get('src'), 'https://giscus.app/client.js');
  assert.equal(page.scripts[0].attributes.get('data-repo'), 'pgsty/oink');
  assert.equal(page.observed.size, 0);
});

test('a visit returning from sign-in hands its session to the widget at once', () => {
  for (const search of ['?giscus=abc', '?page=2&giscus=abc']) {
    assert.equal(comments({ search }).scripts.length, 1, search);
  }
  // Another parameter that merely ends the same way is not a session.
  assert.equal(comments({ search: '?nogiscus=1' }).scripts.length, 0);
});

test('a site that asks for eager comments, or a browser without the observer, loads at once', () => {
  assert.equal(comments({ loading: 'eager' }).scripts.length, 1);
  assert.equal(comments({ observer: false }).scripts.length, 1);
});
