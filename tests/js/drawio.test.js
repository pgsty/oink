'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../../assets/js/drawio.js'), 'utf8');

function editor(server = 'https://editor.example/edit?lang=zh#diagram') {
  const elements = [];
  const messages = [];
  const downloads = [];
  let focused;
  const listeners = new Map();
  function element(tagName) {
    const attributes = new Map();
    const events = new Map();
    const node = {
      tagName, children: [], isConnected: true, classList: { add() {} },
      setAttribute(key, value) { attributes.set(key, value); },
      getAttribute(key) { return attributes.get(key); },
      addEventListener(key, fn) { events.set(key, fn); },
      click() {
        if (tagName === 'a') downloads.push(attributes.get('href'));
        events.get('click')?.({ target: node });
      },
      appendChild(child) { this.children.push(child); child.parentNode = this; },
      insertBefore(child) { this.appendChild(child); },
      removeChild(child) { this.children = this.children.filter(item => item !== child); },
      insertAdjacentHTML() {},
      focus() { focused = this; },
      showModal() { this.open = true; },
      close() { this.open = false; },
      dispatch(type, values = {}) { events.get(type)?.({ preventDefault() {}, ...values }); },
      closest() { return null; },
    };
    if (tagName === 'iframe') node.contentWindow = {
      postMessage(data, origin) { messages.push({ data: JSON.parse(data), origin }); },
    };
    elements.push(node);
    return node;
  }
  const image = element('img');
  image.src = 'https://site.example/diagram.svg';
  const body = element('body');
  body.appendChild(image);
  const document = {
    baseURI: 'https://site.example/docs/', body,
    createElement: element,
    getElementById() { return { textContent: JSON.stringify({ server }) }; },
    querySelectorAll() { return [image]; },
    addEventListener(event, fn) { listeners.set(event, fn); },
  };
  const window = {
    addEventListener(event, fn) { listeners.set(event, fn); },
    removeEventListener(event, fn) { if (listeners.get(event) === fn) listeners.delete(event); },
  };
  vm.runInNewContext(source, {
    document, window, URL,
    XMLHttpRequest: class {
      status = 200;
      response = {};
      open() {}
      addEventListener(event, fn) { this.onload = fn; }
      send() { this.onload(); }
    },
    FileReader: class {
      addEventListener(event, fn) { this.onload = fn; }
      readAsBinaryString() { this.result = '<svg><!-- mxfile --></svg>'; this.onload(); }
      readAsDataURL() { this.result = 'data:image/svg+xml;base64,PHN2Zz4='; this.onload(); }
    },
  });
  listeners.get('DOMContentLoaded')();
  elements.find(node => node.tagName === 'button').click();
  const frame = elements.find(node => node.tagName === 'iframe');
  return {
    frame, messages, downloads,
    dialog: elements.find(node => node.tagName === 'dialog'),
    close: elements.filter(node => node.tagName === 'button').at(-1),
    opener: elements.find(node => node.tagName === 'button'),
    focused() { return focused; },
    mounted() { return body.children.some(node => node.tagName === 'dialog'); },
    send(data, origin = 'https://editor.example', sender = frame.contentWindow) {
      listeners.get('message')?.({ data, origin, source: sender });
    },
    listening() { return listeners.has('message'); },
  };
}

test('Draw.io preserves editor query parameters and fragments', () => {
  for (const server of ['https://editor.example/edit?lang=zh#diagram', '/edit?lang=zh#diagram']) {
    const runtime = editor(server);
    const url = new URL(runtime.frame.getAttribute('src'), 'https://site.example/docs/');
    assert.equal(url.searchParams.get('lang'), 'zh');
    assert.equal(url.searchParams.get('embed'), '1');
    assert.equal(url.searchParams.get('proto'), 'json');
    assert.equal(url.hash, '#diagram');
  }
});

test('Draw.io ignores unrelated, malformed and wrong-origin messages', () => {
  const runtime = editor();
  for (const data of [null, {}, '', 'not json', 'null', '[]']) {
    assert.doesNotThrow(() => runtime.send(data));
    assert.doesNotThrow(() => runtime.send(data, 'https://unrelated.example', {}));
  }
  runtime.send('{"event":"init"}', 'https://unrelated.example');
  runtime.send('{"event":"init"}', 'https://editor.example', {});
  assert.deepEqual(runtime.messages, []);
  runtime.send('{"event":"init"}');
  assert.equal(runtime.messages[0].data.action, 'load');
  assert.equal(runtime.messages[0].origin, 'https://editor.example');
  runtime.send('{"event":"save"}');
  assert.deepEqual(runtime.messages[1], {
    data: { action: 'export', format: 'xmlsvg' }, origin: 'https://editor.example',
  });
});

test('Draw.io downloads image exports only and cleans up its message listener', () => {
  const runtime = editor();
  for (const data of [null, 'javascript:alert(1)', 'https://unrelated.example/file', 'data:text/html,<script>']) {
    runtime.send(JSON.stringify({ event: 'export', data }));
    assert.equal(runtime.listening(), true);
    assert.deepEqual(runtime.downloads, []);
  }
  const data = 'data:image/svg+xml;base64,PHN2Zz4=';
  runtime.send(JSON.stringify({ event: 'export', data }));
  assert.deepEqual(runtime.downloads, [data]);
  assert.equal(runtime.listening(), false);
});

test('Draw.io closes through the host control, backdrop or native cancel and restores focus', () => {
  for (const close of [runtime => runtime.close.click(),
    runtime => runtime.dialog.click(), runtime => runtime.dialog.dispatch('cancel')]) {
    const runtime = editor();
    assert.equal(runtime.dialog.open, true);
    assert.equal(runtime.focused(), runtime.close);
    close(runtime);
    assert.equal(runtime.mounted(), false);
    assert.equal(runtime.listening(), false);
    assert.equal(runtime.focused(), runtime.opener);
    runtime.send('{"event":"init"}');
    assert.deepEqual(runtime.messages, []);
  }
});

// Which images the runtime probes for embedded diagrams. Each image lists its
// ancestors as "tag.class…" strings; closest() matches "tag" or "tag.class…".
function probedSources(images) {
  const requested = [];
  let ready;
  const parse = (simple) => {
    const [tag, ...classes] = simple.split('.');
    return { tag, classes };
  };
  const matches = (ancestor, part) => {
    const node = parse(ancestor);
    const want = parse(part);
    return node.tag === want.tag && want.classes.every(name => node.classes.includes(name));
  };
  const nodes = images.map(({ src, ancestors = [] }) => ({
    tagName: 'img', src,
    closest(selector) {
      const parts = selector.split(',').map(part => part.trim());
      return ancestors.some(ancestor => parts.some(part => matches(ancestor, part))) ? {} : null;
    },
  }));
  vm.runInNewContext(source, {
    document: {
      baseURI: 'https://site.example/docs/',
      getElementById() { return { textContent: JSON.stringify({ server: 'https://editor.example/' }) }; },
      querySelectorAll() { return nodes; },
      addEventListener(event, fn) { if (event === 'DOMContentLoaded') ready = fn; },
    },
    window: { addEventListener() {}, removeEventListener() {} },
    URL,
    XMLHttpRequest: class {
      open(method, src) { requested.push(src); }
      addEventListener() {}
      send() {}
    },
    FileReader: class {},
  });
  ready();
  return requested;
}

test('Draw.io skips video-card posters, social avatars, and map thumbnails but still probes diagrams', () => {
  const requested = probedSources([
    { src: 'https://site.example/talk-poster.png', ancestors: ['a.td-media-card', 'figure.td-media'] },
    { src: 'https://cdn.example/avatar.png', ancestors: ['img.td-social__avatar', 'div.td-social__author'] },
    { src: 'https://site.example/thumb.svg', ancestors: ['img.td-map__thumb', 'li'] },
    { src: 'https://site.example/linked.drawio.png', ancestors: ['a', 'p'] },
    { src: 'https://site.example/zoom.drawio.svg', ancestors: ['button.td-image-zoom__trigger'] },
    { src: 'https://site.example/plain.drawio.svg' },
  ]);
  assert.deepEqual(requested, [
    'https://site.example/linked.drawio.png',
    'https://site.example/zoom.drawio.svg',
    'https://site.example/plain.drawio.svg',
  ]);
});
