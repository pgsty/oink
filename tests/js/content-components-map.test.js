'use strict';

// The map adapter of assets/js/content-components.js against a stub Leaflet:
// reading never zooms the map, markers match the numbered place list with
// accessible labels, popups and attribution are built from text, dark tiles
// switch live, failing dark tiles fall back to light ones, tile failure hides
// the canvas once Leaflet finishes its event, touch disables single-finger
// dragging until a mouse or pen enters, reduced motion disables animations,
// keyboard-opened popups take and return focus, click-to-load defers engine
// loading until clicked and focuses the map it loads, and hidden containers
// frame once visible.
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

function escapeText(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function escapeAttr(value) {
  return escapeText(value).replace(/"/g, '&quot;');
}

function element(tag) {
  const attrs = new Map();
  const listeners = new Map();
  const classes = new Set();
  const node = {
    tag,
    className: '',
    textContent: '',
    hidden: true,
    href: '',
    rel: '',
    type: '',
    children: [],
    parentNode: null,
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
    },
    setAttribute(name, value) {
      attrs.set(name, String(value));
    },
    getAttribute(name) {
      return attrs.has(name) ? attrs.get(name) : null;
    },
    hasAttribute(name) {
      return attrs.has(name);
    },
    addEventListener(name, fn) {
      const list = listeners.get(name) || [];
      list.push(fn);
      listeners.set(name, list);
    },
    dispatch(name, event) {
      (listeners.get(name) || []).forEach((fn) => fn(event || {}));
    },
    appendChild(child) {
      child.parentNode = node;
      node.children.push(child);
      return child;
    },
    insertBefore(child, before) {
      child.parentNode = node;
      const idx = node.children.indexOf(before);
      if (idx >= 0) node.children.splice(idx, 0, child);
      else node.children.push(child);
      return child;
    },
    removeChild(child) {
      node.children = node.children.filter((item) => item !== child);
      child.parentNode = null;
    },
    remove() {
      if (node.parentNode) node.parentNode.removeChild(node);
    },
    focus() {
      node.focused = true;
    },
    scrollIntoView(opts) {
      node.scrolledWith = opts;
    },
    get innerHTML() {
      if (node.children.length) {
        return node.children
          .map((child) => {
            if (child.tag === 'a') {
              const rel = child.rel ? ` rel="${escapeAttr(child.rel)}"` : '';
              return `<a href="${escapeAttr(child.href)}"${rel}>${escapeText(child.textContent)}</a>`;
            }
            return `<${child.tag}>${child.innerHTML}</${child.tag}>`;
          })
          .join('');
      }
      return escapeText(node.textContent);
    },
  };
  return node;
}

function stubLeaflet(calls, { touch = false } = {}) {
  const mapListeners = new Map();
  let lastTileLayer = null;
  // Leaflet 1.9.4 reads a layer's map again after firing its 'load' event;
  // removing the layer or the map inside that dispatch throws in Leaflet.
  let layerDispatch = 0;
  let draggingEnabled = !touch;
  const map = {
    _popup: null,
    dragging: {
      enable() {
        draggingEnabled = true;
        calls.push(['dragging', true]);
      },
      disable() {
        draggingEnabled = false;
        calls.push(['dragging', false]);
      },
      enabled: () => draggingEnabled,
    },
    on(name, fn) {
      const list = mapListeners.get(name) || [];
      list.push(fn);
      mapListeners.set(name, list);
    },
    fire(name, payload) {
      (mapListeners.get(name) || []).forEach((fn) => fn(payload || {}));
    },
    removeLayer() {
      calls.push(['removeLayer', layerDispatch > 0]);
    },
    remove() {
      calls.push(['mapRemove', layerDispatch > 0]);
    },
    setView(point, zoom) {
      calls.push(['setView', point, zoom]);
      markers.forEach((m) => m._realize && m._realize());
    },
    fitBounds(points) {
      calls.push(['fitBounds', points.length]);
      markers.forEach((m) => m._realize && m._realize());
    },
    setZoom(zoom) {
      calls.push(['setZoom', zoom]);
    },
    panTo(point, opts) {
      calls.push(['panTo', point, opts]);
    },
    closePopup() {
      map._popup = null;
      calls.push(['closePopup']);
    },
    invalidateSize() {
      calls.push(['invalidateSize']);
    },
  };
  const chain = { addTo: () => chain };
  const markers = [];
  const L = {
    Browser: { touch },
    _map: map,
    _markers: markers,
    _lastTileLayer: () => lastTileLayer,
    map(canvas, options) {
      calls.push(['map', options]);
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
    tileLayer(url, options) {
      calls.push(['tiles', url, options]);
      const tileListeners = new Map();
      const layer = {
        on(name, fn) {
          const list = tileListeners.get(name) || [];
          list.push(fn);
          tileListeners.set(name, list);
          return layer;
        },
        fire(name, payload) {
          layerDispatch += 1;
          try {
            (tileListeners.get(name) || []).forEach((fn) => fn(payload || {}));
          } finally {
            layerDispatch -= 1;
          }
        },
        addTo: () => layer,
      };
      lastTileLayer = layer;
      return layer;
    },
    divIcon: (options) => options,
    marker(point, options) {
      calls.push(['marker', point, options.title, options.icon.html]);
      let markerEl = null;
      const listeners = new Map();
      const marker = {
        on(name, fn) {
          const list = listeners.get(name) || [];
          list.push(fn);
          listeners.set(name, list);
          return marker;
        },
        getElement: () => markerEl,
        getLatLng: () => point,
        openPopup() {
          calls.push(['openPopup', options.title]);
          map._popup = { isOpen: () => true, _source: marker };
          map.fire('popupopen', { popup: map._popup });
        },
        bindPopup(popup) {
          calls.push(['popup', popup.children.map((child) => child.textContent)]);
          return marker;
        },
        addTo: () => {
          // Simulate Leaflet 1.9.4 creating the divIcon element only once the
          // map view is initialized (firing 'add' after onAdd).
          marker._realize = () => {
            if (markerEl) return;
            markerEl = element('div');
            (listeners.get('add') || []).forEach((fn) => fn());
          };
          return marker;
        },
      };
      markers.push(marker);
      return marker;
    },
    polyline(points) {
      calls.push(['route', points.length]);
      return chain;
    },
  };
  return L;
}

function mount(source, opts = {}) {
  const calls = [];
  let theme = opts.theme || 'light';
  const canvas = element('div');
  if (typeof opts.clientWidth === 'number') {
    canvas.clientWidth = opts.clientWidth;
    canvas.clientHeight = opts.clientHeight ?? opts.clientWidth;
  }
  const closeBtn = element('a');
  canvas.querySelector = (selector) => (selector === '.leaflet-popup-close-button' ? closeBtn : null);

  const listItems = (source.places || []).map(() => element('li'));
  const root = element('figure');
  root.appendChild(canvas);
  root.querySelector = (selector) => {
    if (selector === '[data-td-map-source]') return { textContent: JSON.stringify(source) };
    if (selector === '[data-td-map-canvas]') return canvas;
    return null;
  };
  root.querySelectorAll = (selector) => (selector === '.td-map__places > li' ? listItems : []);

  const site = {
    tiles: 'https://tile.example.org/{z}/{x}/{y}.png',
    darkTiles: '',
    attribution: '<b>© Example</b>',
    attributionUrl: '',
    subdomains: '',
    maxZoom: 19,
    loading: 'lazy',
    zoomIn: 'Vergrößern',
    zoomOut: 'Verkleinern',
    closePopup: 'Schließen',
    loadMap: 'Karte laden',
    ...(opts.site || {}),
  };

  let intersect = null;
  let observed = false;
  let themeObserver = null;
  const docListeners = new Map();
  const requests = [];
  const L = opts.preload === false ? null : stubLeaflet(calls, { touch: !!opts.touch });

  const document = {
    readyState: opts.readyState,
    activeElement: null,
    documentElement: { getAttribute: () => theme },
    head: {
      appendChild(script) {
        requests.push(script);
      },
    },
    createElement: element,
    querySelector(selector) {
      if (selector === '[data-td-component-engines]') return { textContent: '{"leaflet":{"src":"/l.js"}}' };
      if (selector === '[data-td-map-config]') return { textContent: JSON.stringify(site) };
      return null;
    },
    querySelectorAll: (selector) => (selector === '[data-td-map]' ? [root] : []),
    addEventListener(name, fn) {
      const list = docListeners.get(name) || [];
      list.push(fn);
      docListeners.set(name, list);
    },
  };
  const window = {
    L,
    addEventListener() {},
    matchMedia: (query) => ({
      matches: query === '(prefers-reduced-motion: reduce)' ? !!opts.reducedMotion : false,
      addEventListener() {},
    }),
  };
  vm.runInNewContext(SOURCE, {
    window,
    document,
    URL,
    setTimeout,
    console: { error() {} },
    MutationObserver: class {
      constructor(cb) {
        themeObserver = cb;
      }
      observe() {}
    },
    ResizeObserver: class {
      observe() {}
    },
    IntersectionObserver: class {
      constructor(callback) {
        intersect = callback;
      }
      observe() {
        observed = true;
      }
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
    closeBtn,
    listItems,
    root,
    L,
    requests,
    observed: () => observed,
    setTheme(next) {
      theme = next;
      if (themeObserver) themeObserver([{ attributeName: 'data-bs-theme' }]);
    },
    fireDoc(name) {
      (docListeners.get(name) || []).forEach((fn) => fn());
    },
    due: () => {
      intersect([{ target: root, isIntersecting: true }]);
      return new Promise((resolve) => setImmediate(resolve));
    },
    settle: () => new Promise((resolve) => setImmediate(resolve)),
    tick: () => new Promise((resolve) => setTimeout(resolve, 0)),
    setActive(el) {
      document.activeElement = el;
    },
  };
}

test('a due map mounts with numbered accessible markers, a route, and text-only popups', async () => {
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
  assert.equal(page.canvas.hasAttribute('data-td-map-light-tiles'), true, 'marks light tiles when darkTiles is unset');
  const mapOpts = page.calls[0][1];
  assert.equal(mapOpts.scrollWheelZoom, false, 'scroll-wheel zoom stays off');
  assert.equal(mapOpts.dragging, true, 'desktop dragging stays on');
  assert.deepEqual(page.calls[1], ['zoom', 'Vergrößern', 'Verkleinern']);
  assert.deepEqual(page.calls[2], ['attribution', '&lt;b&gt;© Example&lt;/b&gt;']);
  assert.equal(
    JSON.stringify(page.calls[3]),
    JSON.stringify(['tiles', 'https://tile.example.org/{z}/{x}/{y}.png', { maxZoom: 19 }]),
  );
  const markers = page.calls.filter((call) => call[0] === 'marker');
  assert.deepEqual(
    markers.map((call) => call[3]),
    ['<span aria-hidden="true">1</span>', '<span aria-hidden="true">2</span>'],
  );
  assert.deepEqual(
    page.L._markers.map((m) => m.getElement().getAttribute('aria-label')),
    ['1. Kinkaku-ji', '2. Kiyomizu-dera'],
  );
  const popups = page.calls.filter((call) => call[0] === 'popup');
  assert.deepEqual(popups[0][1], ['Kinkaku-ji', '<img src=x onerror=alert(1)>'], 'author text stays text');
  assert.deepEqual(page.calls.find((call) => call[0] === 'route'), ['route', 2]);
  assert.deepEqual(page.calls.at(-1), ['fitBounds', 2]);
});

test('attribution_url builds an https link safely and ignores non-https URLs', async () => {
  const linked = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    { site: { attribution: '© OSM <x>', attributionUrl: 'https://www.openstreetmap.org/copyright' } },
  );
  await linked.due();
  assert.deepEqual(linked.calls[2], [
    'attribution',
    '<a href="https://www.openstreetmap.org/copyright" rel="external">© OSM &lt;x&gt;</a>',
  ]);

  const unsafe = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    { site: { attribution: '© OSM', attributionUrl: 'javascript:alert(1)' } },
  );
  await unsafe.due();
  assert.deepEqual(unsafe.calls[2], ['attribution', '© OSM']);
});

test('a single place centers at the authored zoom', async () => {
  const page = mount({
    places: [{ name: 'Tokyo Station', lat: 35.6812, lng: 139.7671, text: '', thumb: '', href: '' }],
    route: true,
    zoom: 12,
  });
  await page.due();
  assert.equal(page.calls.some((call) => call[0] === 'route'), false, 'one place draws no route');
  assert.equal(JSON.stringify(page.calls.at(-1)), JSON.stringify(['setView', [35.6812, 139.7671], 12]));
});

test('dark_tiles switches on theme change and passes subdomains to tileLayer', async () => {
  const page = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    {
      site: {
        tiles: 'https://{s}.tile.example.org/light/{z}/{x}/{y}.png',
        darkTiles: 'https://{s}.tile.example.org/dark/{z}/{x}/{y}.png',
        subdomains: '01234567',
      },
    },
  );
  await page.due();
  assert.equal(page.canvas.hasAttribute('data-td-map-light-tiles'), false);
  assert.equal(
    JSON.stringify(page.calls[3]),
    JSON.stringify([
      'tiles',
      'https://{s}.tile.example.org/light/{z}/{x}/{y}.png',
      { maxZoom: 19, subdomains: '01234567' },
    ]),
  );
  page.setTheme('dark');
  const tileCalls = page.calls.filter((call) => call[0] === 'tiles');
  assert.equal(tileCalls.length, 2);
  assert.equal(tileCalls[1][1], 'https://{s}.tile.example.org/dark/{z}/{x}/{y}.png');
});

test('complete tile failure removes the map and hides the canvas', async () => {
  const page = mount({
    places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }],
    route: false,
    zoom: 0,
  });
  await page.due();
  assert.equal(page.canvas.hidden, false);
  const layer = page.L._lastTileLayer();
  layer.fire('tileerror');
  layer.fire('tileerror');
  layer.fire('load');
  assert.equal(page.canvas.hidden, true);
  assert.equal(page.root.classList.contains('td-map--mounted'), false);
  assert.equal(page.calls.some((call) => call[0] === 'mapRemove'), false, 'removal waits for Leaflet to finish the event');
  await page.tick();
  assert.deepEqual(
    page.calls.filter((call) => call[0] === 'mapRemove'),
    [['mapRemove', false]],
    'the map is removed once, outside the layer dispatch',
  );
});

test('failing dark tiles fall back to the light tiles and the map stays', async () => {
  const page = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    {
      theme: 'dark',
      site: {
        tiles: 'https://tile.example.org/light/{z}/{x}/{y}.png',
        darkTiles: 'https://tile.example.net/dark/{z}/{x}/{y}.png',
      },
    },
  );
  await page.due();
  const tileUrls = () => page.calls.filter((call) => call[0] === 'tiles').map((call) => call[1]);
  assert.deepEqual(tileUrls(), ['https://tile.example.net/dark/{z}/{x}/{y}.png']);
  assert.equal(page.canvas.hasAttribute('data-td-map-light-tiles'), false);
  const dark = page.L._lastTileLayer();
  dark.fire('tileerror');
  dark.fire('load');
  await page.tick();
  assert.deepEqual(tileUrls(), [
    'https://tile.example.net/dark/{z}/{x}/{y}.png',
    'https://tile.example.org/light/{z}/{x}/{y}.png',
  ]);
  assert.equal(
    page.calls.some((call) => (call[0] === 'removeLayer' || call[0] === 'mapRemove') && call[1]),
    false,
    'nothing is removed inside a layer dispatch',
  );
  assert.equal(page.canvas.hidden, false);
  assert.equal(page.canvas.hasAttribute('data-td-map-light-tiles'), true, 'light tiles are dimmed in dark mode');
  assert.equal(page.calls.some((call) => call[0] === 'mapRemove'), false);
  // Later theme changes keep the working light tiles.
  page.setTheme('light');
  page.setTheme('dark');
  assert.equal(tileUrls().slice(-1)[0], 'https://tile.example.org/light/{z}/{x}/{y}.png');
  // A stale layer finishing after being replaced is ignored.
  dark.fire('tileerror');
  dark.fire('load');
  await page.tick();
  assert.equal(page.canvas.hidden, false);
});

test('touch devices disable single-finger drag and reduced motion disables animations', async () => {
  const page = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    { touch: true, reducedMotion: true },
  );
  await page.due();
  const mapOpts = page.calls[0][1];
  assert.equal(mapOpts.dragging, false);
  assert.equal(mapOpts.fadeAnimation, false);
  assert.equal(mapOpts.zoomAnimation, false);
  assert.equal(mapOpts.markerZoomAnimation, false);
  page.canvas.dispatch('pointerdown', { pointerType: 'mouse' });
  assert.equal(page.L._map.dragging.enabled(), true);
  page.canvas.dispatch('pointerdown', { pointerType: 'touch' });
  assert.equal(page.L._map.dragging.enabled(), false);
  page.canvas.dispatch('pointerenter', { pointerType: 'pen' });
  assert.equal(page.L._map.dragging.enabled(), true, 'a pen drags the map like a mouse');
  page.canvas.dispatch('pointerdown', { pointerType: 'touch' });
  page.canvas.dispatch('pointerdown', { pointerType: 'pen' });
  assert.equal(page.L._map.dragging.enabled(), true);
});

test('a popup opened from the keyboard takes focus and gives it back when closed from inside', async () => {
  const page = mount({
    places: [{ name: 'Kyoto Station', lat: 34.9858, lng: 135.7589, text: '', thumb: '', href: '' }],
    route: false,
    zoom: 0,
  });
  await page.due();
  const marker = page.L._markers[0];
  const markerEl = marker.getElement();
  markerEl.classList.add('td-map__marker');
  // A pointer-opened popup leaves focus alone.
  marker.openPopup();
  assert.equal(page.closeBtn.focused, undefined);
  // Enter on the marker: Leaflet opens the popup during the same key press.
  page.canvas.dispatch('keydown', { key: 'Enter', target: markerEl });
  marker.openPopup();
  assert.equal(page.closeBtn.focused, true, 'focus moves into the popup');
  // The flag lasts one key press: a later pointer open does not steal focus.
  page.closeBtn.focused = undefined;
  page.canvas.dispatch('keydown', { key: 'Enter', target: markerEl });
  await page.tick();
  marker.openPopup();
  assert.equal(page.closeBtn.focused, undefined);
  // The close button, by pointer or Enter, takes focus away with the popup;
  // it returns to the marker.
  markerEl.focused = false;
  const onCloseButton = { closest: (selector) => (selector === '.leaflet-popup-close-button' ? page.closeBtn : null) };
  page.canvas.dispatch('click', { target: onCloseButton });
  page.L._map.fire('popupclose', { popup: page.L._map._popup });
  assert.equal(markerEl.focused, true);
  // Any other close (a map click, a list click opening another popup) leaves focus alone.
  markerEl.focused = false;
  page.canvas.dispatch('click', { target: { closest: () => null } });
  page.L._map.fire('popupclose', { popup: page.L._map._popup });
  assert.equal(markerEl.focused, false);
  // The flag lasts one click.
  page.canvas.dispatch('click', { target: onCloseButton });
  await page.tick();
  page.L._map.fire('popupclose', { popup: page.L._map._popup });
  assert.equal(markerEl.focused, false);
});

test('Escape closes an open popup, restores focus, and localizes the close button', async () => {
  const page = mount({
    places: [{ name: 'Kyoto Station', lat: 34.9858, lng: 135.7589, text: '', thumb: '', href: '' }],
    route: false,
    zoom: 0,
  });
  await page.due();
  page.L._markers[0].openPopup();
  assert.equal(page.closeBtn.getAttribute('aria-label'), 'Schließen');
  let prevented = false;
  let stopped = false;
  page.canvas.dispatch('keydown', {
    key: 'Escape',
    preventDefault() {
      prevented = true;
    },
    stopPropagation() {
      stopped = true;
    },
  });
  assert.equal(prevented, true);
  assert.equal(stopped, true);
  assert.equal(page.calls.some((call) => call[0] === 'closePopup'), true);
  assert.equal(page.L._markers[0].getElement().focused, true);
});

test('click-to-load mode shows a button with the tile host and defers loading until clicked', async () => {
  const page = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    { site: { loading: 'click', tiles: 'https://{s}.tile.example.org/{z}/{x}/{y}.png' } },
  );
  assert.equal(page.observed(), false, 'click mode does not attach IntersectionObserver');
  assert.equal(page.calls.length, 0);
  const button = page.root.children.find((child) => child.tag === 'button');
  assert.ok(button, 'load button inserted');
  assert.equal(button.textContent, 'Karte laden (\u2066*.tile.example.org\u2069)', '{s} names every subdomain, isolated as LTR');
  button.dispatch('click');
  await page.settle();
  assert.equal(page.canvas.hidden, false);
  assert.equal(page.root.children.includes(button), false, 'button removed after activation');
  assert.equal(page.canvas.focused, undefined, 'a pointer click leaves focus alone');
});

test('activating the load button from the keyboard moves focus to the mounted map', async () => {
  const page = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    { site: { loading: 'click' } },
  );
  const button = page.root.children.find((child) => child.tag === 'button');
  page.setActive(button);
  button.dispatch('click');
  await page.settle();
  assert.equal(page.canvas.hidden, false);
  assert.equal(page.canvas.focused, true);
});

test('click-to-load names the dark tile host as well as the light one', async () => {
  const page = mount(
    { places: [{ name: 'A', lat: 35, lng: 135, text: '', thumb: '', href: '' }], route: false, zoom: 0 },
    {
      site: {
        loading: 'click',
        tiles: 'https://t{s}.light.example.org/{z}/{x}/{-y}{r}.png',
        darkTiles: 'https://dark.example.net/{z}/{x}/{y}.png',
      },
    },
  );
  const button = page.root.children.find((child) => child.tag === 'button');
  assert.equal(button.textContent, 'Karte laden (\u2066t*.light.example.org, dark.example.net\u2069)');
});

test('a map hidden at mount defers framing until shown, and clicking a list item pans to its marker', async () => {
  const page = mount(
    {
      places: [
        { name: 'One', lat: 35.0, lng: 135.0, text: '', thumb: '', href: '' },
        { name: 'Two', lat: 35.1, lng: 135.1, text: '', thumb: '', href: '' },
      ],
      route: false,
      zoom: 0,
    },
    { clientWidth: 0, clientHeight: 0 },
  );
  await page.due();
  assert.equal(page.calls.some((call) => call[0] === 'fitBounds'), false, 'zero-size canvas defers framing');
  page.canvas.clientWidth = 600;
  page.canvas.clientHeight = 400;
  page.fireDoc('td:tab-shown');
  assert.deepEqual(page.calls.at(-1), ['fitBounds', 2]);

  page.listItems[1].dispatch('click', { target: { closest: () => null } });
  assert.equal(JSON.stringify(page.calls.filter((c) => c[0] === 'panTo')[0][1]), JSON.stringify([35.1, 135.1]));
  assert.deepEqual(page.calls.find((c) => c[0] === 'openPopup'), ['openPopup', 'Two']);

  const beforeClicks = page.calls.length;
  page.listItems[0].dispatch('click', { target: { closest: () => ({ tagName: 'A' }) } });
  assert.equal(page.calls.length, beforeClicks, 'clicks on links inside list items stay normal navigation');
});
