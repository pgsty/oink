// Pure geometry shared by the reader and its bounded-position tests.
(function (global) {
  'use strict';
  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

  function result(knots, options = {}) {
    return {
      knots,
      syncable: options.syncable !== false,
      approximate: options.approximate === true,
      reason: options.reason || '',
    };
  }

  function progressMap(leftMax, rightMax, options = {}) {
    return result([[0, 0], [leftMax, rightMax]], {
      approximate: true,
      ...options,
    });
  }

  function create(left, right, leftMax, rightMax) {
    if (!(leftMax > 0 && rightMax > 0)) return null;
    const valid = rows => Array.isArray(rows) && rows.every(row => row.id && Number.isFinite(row.y)) &&
      new Set(rows.map(row => row.id)).size === rows.length;
    if (!valid(left) || !valid(right)) {
      return progressMap(leftMax, rightMax, { syncable: false, reason: 'invalid-headings' });
    }
    const rightByID = new Map(right.map((row, index) => [row.id, { ...row, index }]));
    const pairs = [];
    let lastIndex = -1;
    for (const row of left) {
      const peer = rightByID.get(row.id);
      if (!peer) continue;
      if (peer.index <= lastIndex) {
        return progressMap(leftMax, rightMax, { syncable: false, reason: 'out-of-order-headings' });
      }
      lastIndex = peer.index;
      pairs.push([clamp(row.y, 0, leftMax), clamp(peer.y, 0, rightMax)]);
    }
    // Unreachable edge headings cannot form an interpolation interval. Keep
    // a single top/bottom knot, never divide by zero or reverse near the end.
    const knots = [[0, 0]];
    for (const pair of pairs) {
      if (pair[0] >= leftMax || pair[1] >= rightMax) continue;
      const prev = knots[knots.length - 1];
      if (pair[0] > prev[0] && pair[1] > prev[1]) knots.push(pair);
    }
    const usablePairs = knots.length - 1;
    const reason = pairs.length === 0
      ? (left.length === 0 && right.length === 0 ? 'no-headings' : 'no-common-headings')
      : usablePairs === 0
        ? 'no-usable-headings'
        : pairs.length !== left.length || pairs.length !== right.length
          ? 'partial-headings'
          : usablePairs < 2
            ? 'few-headings'
            : '';

    // A page without headings still has a useful, bounded reading progress.
    // Keep a single common heading when one exists, but mark the estimate so
    // the reader can explain the lower confidence beside the Sync control.
    if (usablePairs === 0) return progressMap(leftMax, rightMax, { reason });
    knots.push([leftMax, rightMax]);
    return result(knots, { approximate: Boolean(reason), reason });
  }

  function project(knots, position, from = 0) {
    const points = Array.isArray(knots) ? knots : knots?.knots;
    if (!points || points.length < 2) return 0;
    const to = 1 - from;
    const value = clamp(position, 0, points[points.length - 1][from]);
    let low = 0, high = points.length - 1;
    while (high - low > 1) {
      const mid = (low + high) >>> 1;
      if (points[mid][from] <= value) low = mid;
      else high = mid;
    }
    const a = points[low], b = points[high];
    const t = (value - a[from]) / (b[from] - a[from]);
    return a[to] + t * (b[to] - a[to]);
  }
  const api = { create, project, clamp };
  global.OinkCompareScroll = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
