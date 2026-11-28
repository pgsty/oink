'use strict';

// Contract of assets/js/media.js: the theme's control row for file players,
// viewport-aware autoplay for muted loop videos, in-place player for enabled
// video-platform cards, and single-active playback across audio/video
// players. Real playback, painting and iframes belong to the documentation
// site's browser suite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '../../assets/js/media.js'), 'utf8');

function media(tagName = 'VIDEO', { autoplay = false, muted = false } = {}) {
  const listeners = new Map();
  const attrs = new Set(autoplay ? ['data-td-media-autoplay'] : []);
  const node = {
    tagName,
    paused: true,
    muted,
    calls: [],
    hasAttribute(name) {
      return attrs.has(name);
    },
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    dispatch(type) {
      (listeners.get(type) || []).forEach((handler) => handler({ type, target: node }));
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

function video(options) {
  return media('VIDEO', { autoplay: true, ...options });
}

function audio(options) {
  return media('AUDIO', options);
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
    removeProperty(name) {
      values.delete(name);
    },
  };
}

// Enough of HTMLElement for the platform player swap and for media.js to
// build and drive a control row of buttons, ranges and time labels.
function element(tag) {
  const attributes = new Map();
  const listeners = new Map();
  const classes = new Set();
  const node = {
    tag,
    tagName: String(tag).toUpperCase(),
    style: styleMap(),
    children: [],
    focused: false,
    textContent: '',
    title: '',
    disabled: false,
    get className() {
      return Array.from(classes).join(' ');
    },
    set className(value) {
      classes.clear();
      String(value).split(/\s+/).filter(Boolean).forEach((name) => classes.add(name));
    },
    classList: {
      add: (name) => classes.add(name),
      contains: (name) => classes.has(name),
      toggle(name, force) {
        if (force === undefined ? !classes.has(name) : force) classes.add(name);
        else classes.delete(name);
      },
    },
    setAttribute(name, value) {
      attributes.set(name, String(value));
    },
    getAttribute(name) {
      return attributes.has(name) ? attributes.get(name) : null;
    },
    removeAttribute(name) {
      attributes.delete(name);
    },
    appendChild(child) {
      node.children.push(child);
      return child;
    },
    append(...kids) {
      kids.forEach((child) => node.children.push(child));
    },
    querySelector(selector) {
      assert.equal(selector, 'i');
      return node.children.find((child) => child.tagName === 'I') || null;
    },
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    dispatch(type, extra = {}) {
      const event = {
        type,
        target: node,
        defaultPrevented: false,
        preventDefault() {
          event.defaultPrevented = true;
        },
        ...extra,
      };
      (listeners.get(type) || []).forEach((handler) => handler(event));
      return event;
    },
    focus() {
      node.focused = true;
    },
  };
  return node;
}

function descendants(node) {
  return (node.children || []).flatMap((child) => [child, ...descendants(child)]);
}

function part(row, name) {
  return descendants(row).find((child) => child.classList && child.classList.contains(`td-media__${name}`));
}

// A local file player inside its figure, with the media state media.js reads.
function filePlayer(tagName, { duration = 8, currentTime = 0, buffered = [], tracks = null, label = null } = {}) {
  const figure = element('figure');
  const player = element(tagName.toLowerCase());
  player.controls = true;
  player.setAttribute('controls', '');
  if (label) player.setAttribute(tagName === 'AUDIO' ? 'aria-labelledby' : 'aria-label', label);
  Object.assign(player, {
    parentElement: figure,
    paused: true,
    ended: false,
    muted: false,
    volume: 1,
    playbackRate: 1,
    error: null,
    duration,
    currentTime,
    calls: [],
    buffered: {
      length: buffered.length,
      start: (i) => buffered[i][0],
      end: (i) => buffered[i][1],
    },
    textTracks: tracks,
    querySelector(selector) {
      assert.equal(selector, 'track');
      return tracks && tracks.length ? {} : null;
    },
    after(row) {
      figure.children.push(row);
    },
    play() {
      player.calls.push('play');
      player.paused = false;
      player.dispatch('play');
      return Promise.resolve();
    },
    pause() {
      player.calls.push('pause');
      player.paused = true;
      player.dispatch('pause');
    },
  });
  figure.children.push(player);
  return player;
}

function rowOf(player) {
  return player.parentElement.children.find((child) => child.classList.contains('td-media__controls'));
}

function build({ videos = [], players = null, reduced = false, files = [], config = null, fullscreen = false } = {}) {
  const documentListeners = new Map();
  const timers = [];
  let observerCallback = null;
  const allPlayers = players || videos;
  const motion = {
    matches: reduced,
    listeners: [],
    addEventListener(type, handler) {
      motion.listeners.push(handler);
    },
  };
  const document = {
    hidden: false,
    fullscreenEnabled: fullscreen,
    querySelector(selector) {
      assert.equal(selector, 'script[data-td-media-config]');
      return config === null ? null : { textContent: config };
    },
    querySelectorAll(selector) {
      if (selector === 'video[data-td-media-autoplay]') return videos;
      if (selector === 'audio, video') return allPlayers;
      if (selector === '.td-media > audio, .td-media > video') return files;
      assert.fail(`unexpected selector: ${selector}`);
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
    play(target) {
      target.paused = false;
      documentListeners.get('play')({ type: 'play', target });
    },
    // Unmuting or changing volume fires volumechange, never play.
    volume(target) {
      documentListeners.get('volumechange')({ type: 'volumechange', target });
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
  const link = card('https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&cid=42&autoplay=1&danmaku=0');
  const event = clickOn(link);
  page.click(event);
  assert.equal(event.defaultPrevented, true);
  const holder = link.replacedWith;
  assert.equal(holder.className, 'td-media-player');
  assert.equal(holder.style.getPropertyValue('--td-media-ratio'), '4 / 3');
  const frame = holder.children[0];
  assert.equal(frame.tag, 'iframe');
  assert.equal(frame.src, 'https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&cid=42&autoplay=1&danmaku=0');
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

test('starting an audio or audible video pauses other active players', () => {
  const first = audio();
  const second = audio();
  const talk = media('VIDEO', { autoplay: false });
  const page = build({ players: [first, second, talk] });

  page.play(first);
  assert.equal(first.paused, false);
  assert.deepEqual(second.calls, []);

  page.play(second);
  assert.equal(first.paused, true);
  assert.deepEqual(first.calls, ['pause']);
  assert.equal(second.paused, false);
  assert.deepEqual(talk.calls, [], 'paused players are not paused again');

  page.play(talk);
  assert.equal(second.paused, true);
  assert.deepEqual(second.calls, ['pause']);
  assert.equal(talk.paused, false);
});

test('silent players stay outside single-active playback until they become audible', () => {
  const clip = audio();
  const clip2 = audio();
  const loop = video({ autoplay: true });
  const gif = media('VIDEO', { muted: true });
  const page = build({ videos: [loop], players: [clip, clip2, loop, gif] });

  page.play(clip);
  assert.equal(clip.paused, false);

  // Viewport autoplay starts the muted loop without interrupting audio.
  page.intersect(loop, 0.8);
  page.play(loop);
  assert.equal(clip.paused, false);
  assert.deepEqual(clip.calls, []);
  assert.equal(loop.paused, false);

  // An author's own muted loop, without the theme marker, is silent too.
  page.play(gif);
  assert.equal(clip.paused, false);
  assert.equal(gif.paused, false);

  // Playing another audio pauses the first and leaves both silent loops running.
  page.play(clip2);
  assert.equal(clip.paused, true);
  assert.equal(loop.paused, false);
  assert.equal(gif.paused, false);

  // Unmuting a loop that is already playing fires volumechange, not play:
  // it becomes audible and pauses the audio.
  loop.muted = false;
  page.volume(loop);
  assert.equal(clip2.paused, true);
  assert.equal(loop.paused, false);
  assert.equal(gif.paused, false);

  // A volume change on a paused player, or a re-mute, silences nobody.
  clip2.paused = true;
  clip2.calls.length = 0;
  page.volume(clip2);
  loop.muted = true;
  page.volume(loop);
  assert.equal(loop.paused, false);
  assert.deepEqual(clip2.calls, []);

  // Zero volume counts as silent.
  const quiet = audio();
  quiet.volume = 0;
  const loud = audio();
  const page2 = build({ players: [quiet, loud] });
  page2.play(loud);
  quiet.paused = false;
  page2.play(quiet);
  assert.equal(loud.paused, false, 'a zero-volume player does not interrupt');

  // Clicking an enabled platform card pauses audible local players before mounting the iframe.
  const narration = audio();
  const ambient = video({ autoplay: true });
  const page3 = build({ videos: [ambient], players: [narration, ambient] });
  page3.play(narration);
  page3.intersect(ambient, 0.8);
  page3.play(ambient);
  const embedCard = card('https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1');
  page3.click(clickOn(embedCard));
  assert.equal(narration.paused, true, 'opening a platform player silences audible local players');
  assert.equal(ambient.paused, false, 'muted autoplay loops keep playing');
});

test('a file player trades its native strip for one labelled control row', () => {
  const player = filePlayer('AUDIO', { duration: 8, currentTime: 3, buffered: [[0, 5.44]], label: 'title-1' });
  const labels = { play: '播放', pause: '暂停', seek: '播放进度', speed: '播放速度', mute: '静音', volume: '音量' };
  build({ files: [player], config: JSON.stringify(labels) });
  const figure = player.parentElement;
  const row = rowOf(player);

  assert.equal(player.controls, false);
  assert.equal(player.getAttribute('controls'), null, 'the markup fallback is removed once the row exists');
  assert.ok(figure.classList.contains('td-media--controlled'));
  assert.ok(figure.classList.contains('td-media--timed'));
  assert.equal(row.getAttribute('role'), 'group');
  assert.equal(row.getAttribute('aria-labelledby'), 'title-1', 'audio rows take the visible title');
  assert.equal(row.getAttribute('dir'), 'ltr', 'media time runs left to right on RTL pages too');
  assert.deepEqual(
    row.children.map((child) => child.className.replace('td-media__button ', '').replace('td-media__range ', '')),
    ['td-media__play', 'td-media__time td-media__time--current', 'td-media__seek', 'td-media__time td-media__time--total', 'td-media__speed', 'td-media__sound'],
    'audio has no captions or full screen button',
  );
  assert.equal(part(row, 'play').getAttribute('aria-label'), '播放');
  assert.equal(part(row, 'seek').getAttribute('aria-label'), '播放进度');
  assert.equal(part(row, 'volume').getAttribute('aria-label'), '音量');
  assert.equal(part(row, 'mute').getAttribute('aria-pressed'), 'false');
  assert.equal(part(row, 'speed').title, '播放速度');
  assert.equal(part(row, 'time--current').textContent, '0:03');
  assert.equal(part(row, 'time--total').textContent, '0:08');
  assert.equal(part(row, 'rate').textContent, '1×');

  // One bar: played time and the buffered spans are layers of the same track.
  assert.equal(figure.style.getPropertyValue('--td-media-played'), '37.500%');
  assert.equal(
    figure.style.getPropertyValue('--td-media-loaded'),
    'linear-gradient(to right, transparent 0.000%, var(--td-media-buffer) 0.000%, var(--td-media-buffer) 68.000%, transparent 68.000%)',
  );
  assert.equal(part(row, 'seek').getAttribute('aria-valuetext'), '0:03 / 0:08');

  // Play and pause follow the media events, whoever started them.
  part(row, 'play').dispatch('click');
  assert.deepEqual(player.calls, ['play']);
  assert.equal(part(row, 'play').getAttribute('aria-label'), '暂停');
  assert.ok(figure.classList.contains('td-media--playing'));
  part(row, 'play').dispatch('click');
  assert.deepEqual(player.calls, ['play', 'pause']);
  assert.equal(part(row, 'play').getAttribute('aria-label'), '播放');

  // Missing labels fall back to English rather than an empty name.
  const plain = filePlayer('AUDIO');
  build({ files: [plain], config: '{not json' });
  assert.equal(part(rowOf(plain), 'play').getAttribute('aria-label'), 'Play');
  assert.equal(part(rowOf(plain), 'captions'), undefined);
});

test('the play button leaves its replay icon when the reader seeks back from the end', () => {
  const player = filePlayer('AUDIO', { duration: 8, currentTime: 8, label: 'title-1' });
  build({ files: [player] });
  const row = rowOf(player);
  const glyph = () => part(row, 'play').querySelector('i').className;
  player.ended = true;
  player.dispatch('ended');
  assert.equal(glyph(), 'fa-solid fa-rotate-right');
  // Seeking from the ended state fires no play or pause event.
  player.ended = false;
  player.currentTime = 2;
  player.dispatch('seeking');
  player.dispatch('seeked');
  assert.equal(glyph(), 'fa-solid fa-play');

  // A reload resets the rate without a ratechange event.
  part(row, 'speed').dispatch('click');
  player.dispatch('ratechange');
  assert.equal(part(row, 'rate').textContent, '1.25×');
  player.playbackRate = 1;
  player.dispatch('emptied');
  assert.equal(part(row, 'rate').textContent, '1×');

  // A second run of the runtime leaves the one row in place.
  build({ files: [player] });
  assert.equal(player.parentElement.children.filter((child) => child.classList && child.classList.contains('td-media__controls')).length, 1);
});

test('the seek bar takes arrow, page, Home and End keys and long durations', () => {
  const player = filePlayer('VIDEO', { duration: 3725, currentTime: 60, label: 'Talk' });
  build({ files: [player] });
  const row = rowOf(player);
  const seek = part(row, 'seek');
  assert.equal(row.getAttribute('aria-label'), 'Talk', 'video rows take the player name');
  assert.equal(part(row, 'time--total').textContent, '1:02:05');
  assert.equal(seek.max, '3725');

  const press = (key, extra) => seek.dispatch('keydown', { key, ...extra });
  assert.ok(press('ArrowRight').defaultPrevented);
  assert.equal(player.currentTime, 65);
  press('ArrowDown');
  assert.equal(player.currentTime, 60);
  press('PageUp');
  assert.equal(player.currentTime, 432.5);
  press('Home');
  assert.equal(player.currentTime, 0);
  press('ArrowLeft');
  assert.equal(player.currentTime, 0, 'seeking clamps at the start');
  press('End');
  assert.equal(player.currentTime, 3725);
  assert.equal(part(row, 'time--current').textContent, '1:02:05');
  assert.equal(press('ArrowLeft', { ctrlKey: true }).defaultPrevented, false, 'modified keys stay with the browser');
  assert.equal(press('Tab').defaultPrevented, false);

  // Dragging writes the time straight through.
  seek.value = '1800';
  seek.dispatch('input');
  assert.equal(player.currentTime, 1800);
  assert.equal(player.parentElement.style.getPropertyValue('--td-media-played'), '48.322%');
});

test('speed cycles, sound restores a zero volume, and captions toggle the track', () => {
  const tracks = [{ kind: 'subtitles', mode: 'showing' }];
  tracks.addEventListener = () => {};
  const player = filePlayer('VIDEO', { tracks, label: 'Tour' });
  build({ files: [player] });
  const row = rowOf(player);
  const figure = player.parentElement;

  for (const expected of [1.25, 1.5, 2, 0.75, 1]) {
    part(row, 'speed').dispatch('click');
    assert.equal(player.playbackRate, expected);
  }
  player.playbackRate = 1.5;
  player.dispatch('ratechange');
  assert.equal(part(row, 'rate').textContent, '1.5×');
  assert.ok(figure.classList.contains('td-media--rate'));

  part(row, 'mute').dispatch('click');
  assert.equal(player.muted, true);
  player.dispatch('volumechange');
  assert.equal(part(row, 'mute').getAttribute('aria-pressed'), 'true');
  assert.equal(figure.style.getPropertyValue('--td-media-volume'), '0.000%');
  player.muted = false;
  player.volume = 0;
  part(row, 'mute').dispatch('click');
  assert.equal(player.volume, 1, 'unmuting a zeroed player gives it sound');
  assert.equal(player.muted, false);
  part(row, 'volume').value = '0';
  part(row, 'volume').dispatch('input');
  assert.equal(player.muted, true, 'the volume bar at zero mutes');

  const captions = part(row, 'captions');
  assert.equal(captions.getAttribute('aria-pressed'), 'true');
  captions.dispatch('click');
  assert.equal(tracks[0].mode, 'hidden');
  assert.equal(captions.getAttribute('aria-pressed'), 'false');
  captions.dispatch('click');
  assert.equal(tracks[0].mode, 'showing');
  assert.equal(part(row, 'fullscreen'), undefined, 'no full screen button without a way to enter it');
});

test('full screen uses the figure, or the native player where only that works', () => {
  const player = filePlayer('VIDEO', { label: 'Tour' });
  let requested = 0;
  player.parentElement.requestFullscreen = () => {
    requested += 1;
    return Promise.resolve();
  };
  build({ files: [player], fullscreen: true });
  const button = part(rowOf(player), 'fullscreen');
  assert.equal(button.getAttribute('aria-pressed'), 'false');
  button.dispatch('click');
  assert.equal(requested, 1);

  const phone = filePlayer('VIDEO', { label: 'Tour' });
  let native = 0;
  phone.webkitEnterFullscreen = () => {
    native += 1;
  };
  build({ files: [phone] });
  part(rowOf(phone), 'fullscreen').dispatch('click');
  assert.equal(native, 1);
});

test('without a usable duration the row stays inert and clears its bar', () => {
  const pending = filePlayer('AUDIO', { duration: NaN });
  build({ files: [pending] });
  const row = rowOf(pending);
  assert.equal(part(row, 'seek').disabled, true);
  assert.equal(part(row, 'time--total').textContent, '-:--');
  assert.equal(pending.parentElement.classList.contains('td-media--timed'), false);
  assert.equal(pending.parentElement.style.getPropertyValue('--td-media-played'), '');
  assert.equal(part(row, 'seek').dispatch('keydown', { key: 'End' }).defaultPrevented, false);

  const broken = filePlayer('AUDIO', { duration: 8, currentTime: 2, buffered: [[0, 8]] });
  build({ files: [broken] });
  assert.equal(broken.parentElement.style.getPropertyValue('--td-media-played'), '25.000%');
  broken.error = { code: 4 };
  broken.dispatch('error');
  assert.equal(part(rowOf(broken), 'play').disabled, true);
  assert.equal(part(rowOf(broken), 'seek').disabled, true);
  assert.equal(broken.parentElement.style.getPropertyValue('--td-media-played'), '');
  assert.equal(broken.parentElement.style.getPropertyValue('--td-media-loaded'), '');
});
