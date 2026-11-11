'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const test = require('node:test');

test('vendored Pako exposes the raw-deflate contract used by PlantUML server mode', () => {
  const context = { TextEncoder, TextDecoder, Uint8Array, Uint16Array, Uint32Array };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../assets/third_party/pako/pako_deflate.min.js'), 'utf8'), context);
  for (const source of ['', '@startuml\nAlice -> Bob: 中文 <tag> & "quotes"\n@enduml', 'repeat '.repeat(10000)]) {
    const compressed = context.pako.deflateRaw(source, { level: 9 });
    assert.equal(zlib.inflateRawSync(Buffer.from(compressed)).toString('utf8'), source);
  }
});
