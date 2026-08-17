'use strict';

// Headless coverage for assets/js/filetree.js: split maths, keyboard steps and
// the pointer drag rewrite `--td-filetree-name-col` in pixels of the row
// content box, clamped to [MIN, MAX] percent (the stylesheet clamps too).

const assert = require('node:assert/strict');
const path = require('node:path');
const filetree = require(path.join(__dirname, '..', '..', 'assets/js/filetree.js'));

assert.equal(filetree.MIN, 50);
assert.equal(filetree.MAX, 70);
assert.equal(filetree.clampPercent(10), 50);
assert.equal(filetree.clampPercent(64.4), 64.4);
assert.equal(filetree.clampPercent(99), 70);
assert.equal(filetree.clampPercent(NaN), 50);

// pointer -> percent of the row content box (gutter on both sides)
const ltr = { left: 100, width: 600, gutter: 12, inner: 576, rtl: false };
assert.equal(filetree.percentFromPointer(100 + 12 + 288, ltr), 50);
assert.equal(Math.round(filetree.percentFromPointer(100 + 12 + 576 * 0.6, ltr)), 60);
assert.equal(filetree.percentFromPointer(0, ltr), 50);
assert.equal(filetree.percentFromPointer(5000, ltr), 70);
const rtl = { left: 100, width: 600, gutter: 12, rtl: true, inner: 576 };
assert.equal(Math.round(filetree.percentFromPointer(700 - 12 - 576 * 0.6, rtl)), 60);

// a fake panel: tree > body > divider, with just enough DOM surface
function fakeElement(extra = {}) {
  const attributes = new Map();
  const listeners = new Map();
  return Object.assign({
    style: {
      props: new Map(),
      setProperty(name, value) { this.props.set(name, value); },
      getPropertyValue(name) { return this.props.get(name) || ''; },
    },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.has(name) ? attributes.get(name) : null; },
    hasAttribute(name) { return attributes.has(name); },
    removeAttribute(name) { attributes.delete(name); },
    addEventListener(type, handler) { listeners.set(type, handler); },
    fire(type, event) { const handler = listeners.get(type); return handler ? handler(event) : undefined; },
    getBoundingClientRect() { return { left: 0, width: 0 }; },
  }, extra);
}

const body = fakeElement({ getBoundingClientRect: () => ({ left: 100, width: 600 }) });
const divider = fakeElement({ getBoundingClientRect: () => ({ left: 100 + 12 + 288 - 6, width: 12 }) });
divider.setAttribute('aria-valuenow', '50');
const tree = fakeElement({
  querySelector(selector) {
    if (selector === '.td-filetree__body') return body;
    if (selector === '[data-td-filetree-divider]') return divider;
    return null;
  },
});
const win = {
  getComputedStyle(node) {
    if (node === tree) {
      return { direction: 'ltr', getPropertyValue: (name) => (name === '--td-filetree-gutter' ? '0.75rem' : '') };
    }
    return { fontSize: '16px', getPropertyValue: () => '' };
  },
  document: { documentElement: {} },
};
const doc = { querySelectorAll: () => [tree] };

const enhanced = filetree.init(doc, win);
assert.equal(enhanced.length, 1);
assert.equal(tree.hasAttribute('data-td-filetree-ready'), true);
assert.equal(divider.getAttribute('aria-valuenow'), '50');
// second init is a no-op (idempotent)
assert.equal(filetree.init(doc, win).length, 0);

// keyboard: ArrowRight steps by 2, End/Home hit the bounds; values are px of the 576px content box
let prevented = 0;
const key = (k) => divider.fire('keydown', { key: k, preventDefault() { prevented += 1; } });
key('ArrowRight');
assert.equal(divider.getAttribute('aria-valuenow'), '52');
assert.equal(tree.style.getPropertyValue('--td-filetree-name-col'), (576 * 0.52).toFixed(1) + 'px');
key('End');
assert.equal(divider.getAttribute('aria-valuenow'), '70');
key('ArrowRight');
assert.equal(divider.getAttribute('aria-valuenow'), '70', 'clamped at MAX');
key('Home');
assert.equal(divider.getAttribute('aria-valuenow'), '50');
key('ArrowLeft');
assert.equal(divider.getAttribute('aria-valuenow'), '50', 'clamped at MIN');
key('Tab');
assert.equal(prevented, 5, 'unrelated keys are not swallowed');

// pointer drag: down, move to 65% of the content box, up
let captured = null;
divider.setPointerCapture = (id) => { captured = id; };
divider.fire('pointerdown', { button: 0, pointerId: 7, preventDefault() {} });
assert.equal(captured, 7);
assert.equal(tree.hasAttribute('data-td-filetree-dragging'), true);
divider.fire('pointermove', { clientX: 100 + 12 + 576 * 0.65 });
assert.equal(divider.getAttribute('aria-valuenow'), '65');
assert.equal(tree.getAttribute('data-td-filetree-split'), '65');
divider.fire('pointerup', {});
assert.equal(tree.hasAttribute('data-td-filetree-dragging'), false);
// moves after release do nothing
divider.fire('pointermove', { clientX: 5000 });
assert.equal(divider.getAttribute('aria-valuenow'), '65');

console.log('filetree runtime: ok');
