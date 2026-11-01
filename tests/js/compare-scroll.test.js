const test = require('node:test');
const assert = require('node:assert/strict');
const { create, project } = require('../../assets/js/compare-scroll.js');
const rows = (ys, ids = ['intro', 'transactions', 'isolation', 'end']) => ys.map((y, i) => ({ id: ids[i], y }));

test('matched headings, not total height, determine the corresponding passage in either direction', () => {
  const map = create(rows([100, 500, 900]), rows([200, 1000, 1200]), 1400, 2000);
  assert.equal(project(map, 500), 1000);
  assert.equal(project(map, 700), 1100);
  assert.equal(project(map, 1100, 1), 700);
  assert.equal(project(map, -100), 0);
  assert.equal(project(map, 3000), 2000);
});
test('an extra translated section leaves neighboring common headings aligned', () => {
  const map = create(rows([100, 500, 900]), rows([100, 300, 1000, 1300], ['intro', 'extra', 'transactions', 'isolation']), 1800, 2200);
  assert.equal(project(map, 500), 1000);
  assert.equal(project(map, 900), 1300);
});
test('unrelated, duplicate and reordered headings do not silently become a percentage map', () => {
  const unrelated = create(rows([100, 500]), rows([100, 500], ['unrelated', 'other']), 1000, 1000);
  assert.equal(unrelated.syncable, true);
  assert.equal(unrelated.approximate, true);
  assert.equal(project(unrelated, 500), 500);
  const duplicate = create(rows([100, 500]), rows([100, 500], ['intro', 'intro']), 1000, 1000);
  assert.equal(duplicate.syncable, false);
  assert.equal(duplicate.reason, 'invalid-headings');
  const reordered = create(rows([100, 500]), rows([100, 500], ['transactions', 'intro']), 1000, 1000);
  assert.equal(reordered.syncable, false);
  assert.equal(reordered.reason, 'out-of-order-headings');
  const one = create(rows([100]), rows([200]), 1000, 1000);
  assert.equal(one.syncable, true);
  assert.equal(one.approximate, true);
  assert.equal(project(one, 500), 555.5555555555555);
  assert.equal(create(rows([100, 500]), rows([100, 500]), 0, 1000), null);
});
test('heading-less documents use bounded whole-document progress interpolation', () => {
  const map = create([], [], 1000, 1800);
  assert.equal(map.syncable, true);
  assert.equal(map.reason, 'no-headings');
  assert.equal(project(map, 250), 450);
  assert.equal(project(map, 1000), 1800);
});
test('unreachable bottom anchors are clipped without backwards intervals, NaN or runaway feedback', () => {
  const map = create(rows([0, 200, 600, 1400]), rows([0, 400, 500, 1800]), 1000, 1100);
  let previous = -1;
  for (let position = 0; position <= 1000; position += 5) {
    const projected = project(map, position);
    assert.ok(Number.isFinite(projected) && projected >= previous && projected <= 1100);
    assert.ok(Math.abs(project(map, projected, 1) - position) < 1e-8);
    previous = projected;
  }
  assert.deepEqual(map.knots[map.knots.length - 1], [1000, 1100]);
});
