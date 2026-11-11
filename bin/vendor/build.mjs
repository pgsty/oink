// Maintainer-only builds. Copy this directory to an external working directory,
// run npm ci --ignore-scripts, then node build.mjs. Hugo never runs this script.
import { build } from 'esbuild';
import { readFile, writeFile, mkdir, readdir, rm } from 'node:fs/promises';
import path from 'node:path';

const common = { bundle: true, minify: true, target: 'es2022', legalComments: 'linked', metafile: true };
await mkdir('out', { recursive: true });
const builds = [
  ['markmap', {
    stdin: { contents: `export { parse } from '@markmap/parse';
export { walkTree, toPlainText } from '@markmap/core';
export { Markmap, resolveViewOptions } from '@markmap/view';
export { defaultContentPlugins, createCanvasMeasurer } from '@markmap/render';
export { mathContent, remarkMath } from '@markmap/plugin-math';`, resolveDir: process.cwd() },
    format: 'esm', splitting: true, outdir: 'out/markmap', entryNames: 'markmap', chunkNames: '[name]-[hash]',
  }],
  ['pako', {
    stdin: { contents: `export { deflateRaw } from 'pako';`, resolveDir: process.cwd() },
    format: 'iife', globalName: 'pako', outfile: 'out/pako/pako_deflate.min.js',
  }],
  ['external-svg-loader', {
    entryPoints: ['node_modules/external-svg-loader/svg-loader.js'],
    format: 'iife', outfile: 'out/external-svg-loader/svg-loader.min.js',
  }],
];
for (const [name, options] of builds) {
  await rm(`out/${name}`, { recursive: true, force: true });
  const result = await build({ ...common, ...options });
  const packages = new Map();
  for (const input of Object.keys(result.metafile.inputs)) {
    const match = input.match(/^(.*node_modules\/(?:@[^/]+\/)?[^/]+)\//);
    if (!match) continue;
    const dir = match[1];
    if (packages.has(dir)) continue;
    const pkg = JSON.parse(await readFile(path.join(dir, 'package.json'), 'utf8'));
    let files = (await readdir(dir)).filter(file => /^(licen[cs]e|copying|notice)(\.|$)/i.test(file)).sort();
    // format publishes its copyright and license reference in the README.
    if (!files.length) files = (await readdir(dir)).filter(file => /^readme(\.|$)/i.test(file));
    if (!files.length && /^@mathjax\/mathjax-.*-font$/.test(pkg.name)) files = ['../src/LICENSE'];
    if (!files.length) throw new Error(`No license for bundled package ${pkg.name}`);
    const licenses = await Promise.all(files.map(async file => `${file}\n${await readFile(path.join(dir, file), 'utf8')}`));
    packages.set(dir, { name: pkg.name, version: pkg.version, license: pkg.license || pkg.licenses?.map(x => x.type).join(' AND '), text: licenses.join('\n') });
  }
  const entries = [...packages.values()].sort((a, b) => a.name.localeCompare(b.name, 'en'));
  await writeFile(`out/${name}/LICENSES.txt`, entries.map(p => `${p.name} ${p.version} (${p.license})\n${p.text}`).join('\n\n'));
  await writeFile(`out/${name}/PACKAGES.json`, JSON.stringify(entries.map(({text, ...p}) => p), null, 2) + '\n');
  console.log(`${name}: ${entries.length} bundled packages, ${Object.keys(result.metafile.outputs).length} files`);
}
