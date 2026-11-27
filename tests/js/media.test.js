'use strict';

// Contract of assets/js/media.js: viewport-aware autoplay for muted loop
// videos, and the in-place player for enabled video-platform cards. Real
// playback and iframes belong to the documentation site's browser suite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '../../assets/js/media.js'), 'utf8');

function video() {
  const listeners = new Map();
  const node = {
    paused: true,
    muted: false,
    calls: [],
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    dispatch(type) {
      (listeners.get(type) || []).forEach((handler) => handler({ type }));
    },
    play() {
      node.calls.push('play');
      node.paused = false;
      node.dispatch('play');
      return Promise.resolve();
    },
    pause() {
      node.calls.push('pause');
      node.paused = true;
      node.dispatch('pause');
    },
  };
  return node;
}

// CSSStyleDeclaration's custom-property surface: the card's shape travels as
// --td-media-ratio, which media.css turns into the box ratio and width cap.
function styleMap(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getPropertyValue(name) {
      return values.get(name) || '';
    },
    setProperty(name, value) {
      values.set(name, String(value));
    },
  };
}

function element(tag) {
  const attributes = new Map();
  const node = {
    tag,
    className: '',
    style: styleMap(),
    children: [],
    focused: false,
    setAttribute(name, value) {
      attributes.set(name, String(value));
    },
    getAttribute(name) {
      return attributes.has(name) ? attributes.get(name) : null;
    },
    appendChild(child) {
      node.children.push(child);
      return child;
    },
    focus() {
      node.focused = true;
    },
  };
  return node;
}

function build({ videos = [], reduced = false } = {}) {
  const documentListeners = new Map();
  const timers = [];
  let observerCallback = null;
  const motion = {
    matches: reduced,
    listeners: [],
    addEventListener(type, handler) {
      motion.listeners.push(handler);
    },
  };
  const document = {
    hidden: false,
    querySelectorAll(selector) {
      assert.equal(selector, 'video[data-td-media-autoplay]');
      return videos;
    },
    addEventListener(type, handler) {
      documentListeners.set(type, handler);
    },
    createElement: element,
  };
  const window = {
    matchMedia(query) {
      assert.equal(query, '(prefers-reduced-motion: reduce)');
      return motion;
    },
  };
  function IntersectionObserver(callback) {
    observerCallback = callback;
    this.observe = () => {};
  }
  vm.runInNewContext(SOURCE, {
    window,
    document,
    IntersectionObserver,
    Map,
    setTimeout(callback) {
      timers.push(callback);
    },
  });
  return {
    document,
    motion,
    click(event) {
      documentListeners.get('click')(event);
    },
    visibility() {
      documentListeners.get('visibilitychange')();
    },
    intersect(target, ratio) {
      observerCallback([{ target, isIntersecting: ratio > 0, intersectionRatio: ratio }]);
      timers.splice(0).forEach((callback) => callback());
    },
  };
}

test('autoplay videos play only while half visible and pause when they leave', () => {
  const clip = video();
  const page = build({ videos: [clip] });
  assert.equal(clip.muted, true);
  assert.deepEqual(clip.calls, []);
  page.intersect(clip, 0.3);
  assert.deepEqual(clip.calls, [], 'a sliver in view does not start playback');
  page.intersect(clip, 0.8);
  assert.deepEqual(clip.calls, ['play']);
  page.intersect(clip, 0);
  assert.deepEqual(clip.calls, ['play', 'pause']);
});

test('reduced motion and hidden pages never autoplay', () => {
  const clip = video();
  const page = build({ videos: [clip], reduced: true });
  page.intersect(clip, 1);
  assert.deepEqual(clip.calls, []);

  const other = video();
  const hidden = build({ videos: [other] });
  hidden.document.hidden = true;
  hidden.intersect(other, 1);
  assert.deepEqual(other.calls, []);
});

test("a reader's pause wins until the video leaves the viewport", () => {
  const clip = video();
  const page = build({ videos: [clip] });
  page.intersect(clip, 1);
  assert.deepEqual(clip.calls, ['play']);
  // The reader pauses with the native controls.
  clip.paused = true;
  clip.dispatch('pause');
  page.intersect(clip, 0.9);
  assert.deepEqual(clip.calls, ['play'], 'scrolling within view does not resume it');
  page.intersect(clip, 0);
  page.intersect(clip, 1);
  assert.deepEqual(clip.calls, ['play', 'play'], 'leaving and returning resumes autoplay');
});

function card(src, title = 'Talk') {
  const attributes = { 'data-td-media-embed': src, 'data-td-media-title': title };
  const node = {
    style: styleMap({ '--td-media-ratio': '4 / 3' }),
    replacedWith: null,
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attributes, name) ? attributes[name] : null;
    },
    replaceWith(next) {
      node.replacedWith = next;
    },
  };
  return node;
}

function clickOn(target, extra = {}) {
  const event = {
    defaultPrevented: false,
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    target: { closest: () => target },
    preventDefault() {
      event.defaultPrevented = true;
    },
    ...extra,
  };
  return event;
}

test('a plain click swaps an enabled card for the platform player', () => {
  const page = build();
  const link = card('https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&p=1&autoplay=1&danmaku=0');
  const event = clickOn(link);
  page.click(event);
  assert.equal(event.defaultPrevented, true);
  const holder = link.replacedWith;
  assert.equal(holder.className, 'td-media-player');
  assert.equal(holder.style.getPropertyValue('--td-media-ratio'), '4 / 3');
  const frame = holder.children[0];
  assert.equal(frame.tag, 'iframe');
  assert.equal(frame.src, 'https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&p=1&autoplay=1&danmaku=0');
  assert.equal(frame.title, 'Talk');
  assert.equal(frame.getAttribute('allow'), 'autoplay; picture-in-picture; fullscreen');
  assert.equal(
    frame.getAttribute('sandbox'),
    'allow-scripts allow-same-origin allow-presentation allow-popups allow-popups-to-escape-sandbox',
  );
  assert.equal(frame.getAttribute('referrerpolicy'), 'strict-origin-when-cross-origin');
  assert.equal(frame.getAttribute('allowfullscreen'), '');
  assert.equal(frame.focused, true);

  const vimeo = card('https://player.vimeo.com/video/76979871?autoplay=1&dnt=1&h=abcdef1234#t=90s');
  const vimeoEvent = clickOn(vimeo);
  page.click(vimeoEvent);
  assert.equal(vimeoEvent.defaultPrevented, true);
  assert.equal(vimeo.replacedWith.children[0].src, 'https://player.vimeo.com/video/76979871?autoplay=1&dnt=1&h=abcdef1234#t=90s');
});

test('modified clicks, unknown hosts, and tampered player URLs keep the link', () => {
  const page = build();
  const link = card('https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1');
  const modified = clickOn(link, { metaKey: true });
  page.click(modified);
  assert.equal(modified.defaultPrevented, false);
  assert.equal(link.replacedWith, null);

  for (const bad of [
    'https://evil.example/embed/x',
    'https://www.youtube-nocookie.com/embed/../../watch?v=1',
    'https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&evil=1',
    'https://player.vimeo.com/video/76979871?autoplay=1&dnt=0',
  ]) {
    const foreign = card(bad);
    const plain = clickOn(foreign);
    page.click(plain);
    assert.equal(plain.defaultPrevented, false, `must reject ${bad}`);
    assert.equal(foreign.replacedWith, null, `must not swap ${bad}`);
  }
});

test('async play/pause events, no-op applies, and re-muting stay race-free', async () => {
  const listeners = new Map();
  const queue = [];
  const clip = {
    tagName: 'VIDEO',
    paused: true,
    muted: false,
    calls: [],
    hasAttribute: (name) => name === 'data-td-media-autoplay',
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    dispatch(type) {
      (listeners.get(type) || []).forEach((handler) => handler({ type, target: clip }));
    },
    play() {
      clip.calls.push('play');
      clip.paused = false;
      queue.push('play');
      return Promise.resolve();
    },
    pause() {
      clip.calls.push('pause');
      clip.paused = true;
      queue.push('pause');
    },
  };
  const page = build({ videos: [clip] });
  page.intersect(clip, 0.8);
  assert.deepEqual(clip.calls, ['play']);
  // Rapid scroll-out before the queued play event fires: neither event counts as reader intent.
  page.intersect(clip, 0);
  assert.deepEqual(clip.calls, ['play', 'pause']);
  while (queue.length) clip.dispatch(queue.shift());
  // Re-entering still autoplays and re-mutes if the reader previously unmuted it.
  clip.muted = false;
  page.intersect(clip, 0.8);
  assert.equal(clip.muted, true);
  assert.deepEqual(clip.calls, ['play', 'pause', 'play']);
  while (queue.length) clip.dispatch(queue.shift());
  // A no-op visibilitychange while already playing must not swallow a reader pause.
  page.visibility();
  clip.paused = true;
  clip.dispatch('pause');
  page.intersect(clip, 0.9);
  assert.deepEqual(clip.calls, ['play', 'pause', 'play']);
});
