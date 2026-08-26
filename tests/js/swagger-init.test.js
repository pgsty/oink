'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const swaggerInit = require(path.join(__dirname, '..', '..', 'assets/js/swagger-init.js'));

function container(url) {
  return {
    dataset: {},
    getAttribute(name) {
      return name === 'data-td-spec-url' ? url : null;
    },
  };
}

function documentOf(nodes) {
  return {
    querySelectorAll(selector) {
      assert.equal(selector, '[data-td-swagger]');
      return nodes;
    },
  };
}

function bundleStub() {
  const calls = [];
  const bundle = function (config) {
    calls.push(config);
    return { config };
  };
  bundle.presets = { apis: 'apis-preset' };
  bundle.calls = calls;
  return bundle;
}

test('every container mounts with its own spec URL and a null validatorUrl', () => {
  const first = container('/spec-a.yaml');
  const second = container('/spec-b.yaml');
  const bundle = bundleStub();

  const mounted = swaggerInit.init(documentOf([first, second]), bundle, 'standalone-preset');

  assert.equal(mounted.length, 2);
  assert.equal(bundle.calls.length, 2);
  assert.deepEqual(bundle.calls.map((call) => call.url), ['/spec-a.yaml', '/spec-b.yaml']);
  for (const call of bundle.calls) {
    // The explicit null is the whole point: an absent key would fall back to
    // the bundle's online validator and leak the spec URL off-origin.
    assert.ok(Object.prototype.hasOwnProperty.call(call, 'validatorUrl'));
    assert.equal(call.validatorUrl, null);
    assert.deepEqual(call.presets, ['apis-preset', 'standalone-preset']);
  }
  assert.equal(bundle.calls[0].domNode, first);
  assert.equal(bundle.calls[1].domNode, second);
});

test('a container never mounts twice and an empty URL is skipped', () => {
  const node = container('/spec-a.yaml');
  const empty = container('');
  const bundle = bundleStub();
  const doc = documentOf([node, empty]);

  swaggerInit.init(doc, bundle, undefined);
  swaggerInit.init(doc, bundle, undefined);

  assert.equal(bundle.calls.length, 1);
  assert.deepEqual(bundle.calls[0].presets, ['apis-preset']);
});

test('a missing bundle or document is a quiet no-op', () => {
  assert.deepEqual(swaggerInit.init(undefined, bundleStub(), undefined), []);
  assert.deepEqual(swaggerInit.init(documentOf([container('/s.yaml')]), undefined, undefined), []);
});
