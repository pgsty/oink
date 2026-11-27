'use strict';

// The map adapter of assets/js/content-components.js against a stub Leaflet:
// reading never zooms the map, markers match the numbered place list, and
// popups and the attribution are built from text, never from author HTML.
// Rendered tiles belong to the documentation site's browser suite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(
  path.join(__dirname, '../../assets/js/content-components.js'),
  'utf8',
);

function element(tag) {
  const node = {
    tag,
    className: '',
    textContent: '',
    hidden: true,
    children: [],
    appendChild(child) {
      node.children.push(child);
      return child;
    },
    get innerHTML() {
      return node.textContent
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    },
  };
  return node;
}

function stubLeaflet(calls) {
  const map = {
    removeLayer() {},
    setView(point, zoom) {
      calls.push(['setView', point, zoom]);
    },
    fitBounds(points) {
      calls.push(['fitBounds', points.length]);
    },
    setZoom(zoom) {
      calls.push(['setZoom', zoom]);
    },
    invalidateSize() {},
  };
  const chain = { addTo: () => chain };
  return {
    map(canvas, options) {
      calls.push(['map', options.scrollWheelZoom]);
      return map;
    },
    control: {
      zoom(options) {
        calls.push(['zoom', options.zoomInTitle, options.zoomOutTitle]);
        return chain;
      },
      attribution() {
        return {
          addTo: () => ({
            addAttribution(text) {
              calls.push(['attribution', text]);
            },
          }),
        };
      },
    },
    tileLayer(url) {
      calls.push(['tiles', url]);
      return chain;
    },
    divIcon: (options) => options,
    marker(point, options) {
      calls.push(['marker', point, options.title, options.icon.html]);
      const marker = {
        bindPopup(popup) {
          calls.push(['popup', popup.children.map((child) => child.textContent)]);
          return marker;
        },
        addTo: () => marker,
      };
      return marker;
    },
    polyline(points) {
      calls.push(['route', points.length]);
      return chain;
    },
  };
}

function mount(source) {
  const calls = [];
  const canvas = element('div');
  const root = {
    querySelector(selector) {
      if (selector === '[data-td-map-source]') return { textContent: JSON.stringify(source) };
      if (selector === '[data-td-map-canvas]') return canvas;
      return null;
    },
  };
  const site = {
    tiles: 'https://tile.example.org/{z}/{x}/{y}.png',
    darkTiles: '',
    attribution: '<b>© Example</b>',
    maxZoom: 19,
    zoomIn: 'Vergrößern',
    zoomOut: 'Verkleinern',
  };
  let intersect = null;
  const document = {
    documentElement: { getAttribute: () => 'light' },
    head: { appendChild() {} },
    createElement: element,
    querySelector(selector) {
      if (selector === '[data-td-component-engines]') return { textContent: '{"leaflet":{"src":"/l.js"}}' };
      if (selector === '[data-td-map-config]') return { textContent: JSON.stringify(site) };
      return null;
    },
    querySelectorAll: (selector) => (selector === '[data-td-map]' ? [root] : []),
    addEventListener() {},
  };
  const window = {
    L: stubLeaflet(calls),
    addEventListener() {},
    matchMedia: () => ({ addEventListener() {} }),
  };
  vm.runInNewContext(SOURCE, {
    window,
    document,
    console: { error() {} },
    MutationObserver: class {
      observe() {}
    },
    ResizeObserver: class {
      observe() {}
    },
    IntersectionObserver: class {
      constructor(callback) {
        intersect = callback;
      }
      observe() {}
      unobserve() {}
    },
    Promise,
    JSON,
    Map,
    Error,
    Object,
    Array,
  });
  return {
    calls,
    canvas,
    due: () => {
      intersect([{ target: root, isIntersecting: true }]);
      return new Promise((resolve) => setImmediate(resolve));
    },
  };
}

test('a due map mounts with numbered markers, a route, and text-only popups', async () => {
  const page = mount({
    places: [
      { name: 'Kinkaku-ji', lat: 35.0394, lng: 135.7292, text: '<img src=x onerror=alert(1)>', thumb: '', href: '' },
      { name: 'Kiyomizu-dera', lat: 34.9949, lng: 135.785, text: '', thumb: '', href: '#day-2' },
    ],
    route: true,
    zoom: 0,
  });
  assert.equal(page.calls.length, 0, 'nothing mounts before the map is due');
  await page.due();
  assert.equal(page.canvas.hidden, false);
  assert.deepEqual(page.calls[0], ['map', false], 'scroll-wheel zoom stays off');
  assert.deepEqual(page.calls[1], ['zoom', 'Vergrößern', 'Verkleinern']);
  assert.deepEqual(page.calls[2], ['attribution', '&lt;b&gt;© Example&lt;/b&gt;']);
  assert.deepEqual(page.calls[3], ['tiles', 'https://tile.example.org/{z}/{x}/{y}.png']);
  const markers = page.calls.filter((call) => call[0] === 'marker');
  assert.deepEqual(markers.map((call) => call[3]), ['<span>1</span>', '<span>2</span>']);
  assert.deepEqual(markers.map((call) => call[2]), ['Kinkaku-ji', 'Kiyomizu-dera']);
  const popups = page.calls.filter((call) => call[0] === 'popup');
  assert.deepEqual(popups[0][1], ['Kinkaku-ji', '<img src=x onerror=alert(1)>'], 'author text stays text');
  assert.deepEqual(page.calls.find((call) => call[0] === 'route'), ['route', 2]);
  assert.deepEqual(page.calls.at(-1), ['fitBounds', 2]);
});

test('a single place centers at the authored zoom', async () => {
  const page = mount({
    places: [{ name: 'Tokyo Station', lat: 35.6812, lng: 139.7671, text: '', thumb: '', href: '' }],
    route: true,
    zoom: 12,
  });
  await page.due();
  assert.equal(page.calls.some((call) => call[0] === 'route'), false, 'one place draws no route');
  // The point array comes from the adapter's own realm; compare its values.
  assert.equal(JSON.stringify(page.calls.at(-1)), JSON.stringify(['setView', [35.6812, 139.7671], 12]));
});
