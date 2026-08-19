'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

const registryModule = require(
  path.join(__dirname, '..', '..', 'assets/js/action-registry.js'),
);

const builtinIds = [
  'copy_markdown',
  'copy_link',
  'open_chatgpt',
  'open_claude',
  'view_markdown',
  'view_history',
  'edit_page',
  'create_child_page',
  'create_issue',
  'create_project_issue',
  'print_section',
  'print',
  'switch_theme',
  'switch_language',
  'switch_version',
  'open_github',
];

function descriptor(id, values = {}) {
  return {
    id,
    title: id,
    description: id,
    icon: 'fa-solid fa-bolt',
    keywords: [id],
    kind: 'invoke',
    available: true,
    disabledReason: '',
    url: '',
    target: 'self',
    placements: { page: true, palette: true },
    options: [],
    ...values,
  };
}

function harness({ actions, commands = [], fetchImpl, clipboard = true } = {}) {
  const events = {
    assigned: [], opened: [], printed: 0, copied: [], fetched: [],
    execCommands: [], fallbackText: [],
  };
  const fakeWindow = {
    location: {
      href: 'https://example.org/preview/en/docs/page/',
      assign(url) {
        events.assigned.push(url);
      },
    },
    open(url, target, features) {
      events.opened.push({ url, target, features });
    },
    print() {
      events.printed += 1;
    },
    navigator: clipboard ? {
      clipboard: {
        writeText(text) {
          events.copied.push(text);
          return Promise.resolve();
        },
      },
    } : {},
  };
  let textarea = null;
  const fakeDocument = {
    getElementById() {
      return null;
    },
    createElement(name) {
      assert.equal(name, 'textarea');
      textarea = {
        value: '', style: {},
        setAttribute() {},
        select() { events.fallbackText.push(this.value); },
        remove() { textarea = null; },
      };
      return textarea;
    },
    body: {
      appendChild(node) { assert.equal(node, textarea); },
    },
    execCommand(command) {
      events.execCommands.push(command);
      return command === 'copy';
    },
  };
  const fetchApi =
    fetchImpl ||
    ((url) => {
      events.fetched.push(url);
      return Promise.resolve({ ok: true, text: () => Promise.resolve('# Page') });
    });
  const registry = registryModule.create({
    window: fakeWindow,
    document: fakeDocument,
    fetch: fetchApi,
    manifest: { version: 1, actions: actions || [], commands },
  });
  return { registry, events, window: fakeWindow };
}

(async () => {
  const actions = builtinIds.map((id) => descriptor(id));
  function replace(id, values) {
    actions[builtinIds.indexOf(id)] = descriptor(id, values);
  }
  replace('copy_markdown', {
    kind: 'copy',
    url: '/preview/en/docs/page/index.md',
  });
  replace('copy_link', {
    kind: 'copy',
    url: 'https://example.org/preview/en/docs/page/',
  });
  replace('open_chatgpt', {
    kind: 'url',
    url: 'https://chatgpt.com/?prompt=build-time',
    promptTemplate: 'Read from %s so I can ask questions about it.',
    target: 'blank',
  });
  replace('open_claude', {
    kind: 'url',
    url: 'https://claude.ai/new?q=build-time',
    promptTemplate: 'Read from %s so I can ask questions about it.',
    target: 'blank',
  });
  replace('view_markdown', {
    kind: 'url',
    url: '/preview/en/docs/page/index.md',
    target: 'blank',
  });
  replace('edit_page', {
    kind: 'url',
    available: false,
    disabledReason: 'Repository unavailable',
  });
  replace('switch_theme', {
    kind: 'choice',
    options: [{ id: 'dark', title: 'Dark', value: 'dark', available: true }],
  });
  replace('switch_language', {
    kind: 'choice',
    options: [{ id: 'zh', title: '中文', url: '/zh/', available: true }],
  });
  replace('switch_version', {
    kind: 'choice',
    options: [{ id: 'v2', title: 'Version 2', url: 'https://v2.example.com/', available: true }],
  });
  const commands = [
    {
      id: 'status',
      kind: 'url',
      url: 'https://status.example.com/',
      target: 'blank',
    },
    { id: 'print_now', kind: 'builtin', action: 'print' },
    { id: 'theme_now', kind: 'builtin', action: 'switch_theme' },
    { id: 'language_now', kind: 'builtin', action: 'switch_language' },
    { id: 'version_now', kind: 'builtin', action: 'switch_version' },
    { id: 'unsafe', kind: 'url', url: 'javascript:alert(1)' },
    { id: 'unknown', kind: 'builtin', action: 'not_real' },
  ];

  // Production does not inject the manifest into create(); the registry reads
  // the inert JSON node that scripts.html emitted before js/actions.js. Keep a
  // direct test of that path so template/script ordering cannot be masked by
  // the convenience injection used by the rest of this unit harness.
  const domManifest = { version: 1, actions, commands, quickLinks: [] };
  const registryFromDOM = registryModule.create({
    window: { location: { href: 'https://example.org/docs/' }, navigator: {} },
    document: {
      getElementById(id) {
        return id === 'td-action-manifest'
          ? { textContent: JSON.stringify(domManifest) }
          : null;
      },
    },
  });
  assert.equal(registryFromDOM.get('copy_markdown').id, 'copy_markdown');
  assert.ok(registryFromDOM.commands().some((command) => command.id === 'status'));

  const { registry, events, window: fakeWindow } = harness({ actions, commands });

  assert.deepEqual(registry.list().map((action) => action.id), builtinIds);
  assert.deepEqual(
    registry.list({ placement: 'page' }).map((action) => action.id),
    builtinIds,
  );
  assert.equal(registry.get('unknown'), null);
  assert.deepEqual(registry.commands().map((command) => command.id), [
    'status',
    'print_now',
    'theme_now',
    'language_now',
    'version_now',
  ]);
  assert.equal(events.fetched.length, 0, 'registry creation caused a request');

  const pending = registry.preloadMarkdown('/preview/en/docs/page/index.md');
  await registry.run('copy_markdown', { source: 'page' });
  await pending;
  await registry.run('copy_markdown', { source: 'palette' });
  assert.equal(events.fetched.length, 1, 'markdown was fetched more than once');
  assert.deepEqual(events.copied, ['# Page', '# Page']);

  // copy_link writes a URL, so it never touches the Markdown output.
  await registry.run('copy_link', { source: 'palette' });
  assert.equal(events.copied[2], 'https://example.org/preview/en/docs/page/');
  await registry.run('copy_link', {
    source: 'page',
    value: { url: '/preview/en/docs/other/' },
  });
  assert.equal(events.copied[3], 'https://example.org/preview/en/docs/other/');
  assert.equal(events.fetched.length, 1, 'copy_link fetched a document');
  await assert.rejects(
    registry.run('copy_link', { value: { url: 'javascript:alert(1)' } }),
    { code: 'unsafe_url' },
  );

  await registry.run('view_markdown');
  assert.deepEqual(events.opened[0], {
    url: 'https://example.org/preview/en/docs/page/index.md',
    target: '_blank',
    features: 'noopener,noreferrer',
  });
  fakeWindow.location.href =
    'https://example.org/preview/en/docs/page/?mode=review&marker=$&#current-heading';
  const expectedPrompt =
    'Read from https://example.org/preview/en/docs/page/?mode=review&marker=$&#current-heading ' +
    'so I can ask questions about it.';
  const chatgptUrl = new URL(registry.resolveUrl('open_chatgpt'));
  assert.equal(chatgptUrl.origin, 'https://chatgpt.com');
  assert.equal(chatgptUrl.searchParams.get('hints'), 'search');
  assert.equal(chatgptUrl.searchParams.get('prompt'), expectedPrompt);
  const claudeUrl = new URL(registry.resolveUrl('open_claude'));
  assert.equal(claudeUrl.origin, 'https://claude.ai');
  assert.equal(claudeUrl.searchParams.get('q'), expectedPrompt);
  await registry.run('open_chatgpt');
  await registry.run('open_claude');
  assert.equal(events.opened[1].url, chatgptUrl.href);
  assert.equal(events.opened[2].url, claudeUrl.href);
  await registry.run('print');
  await registry.runCommand('print_now');
  assert.equal(events.printed, 2);
  await registry.runCommand('status');
  assert.equal(events.opened[3].url, 'https://status.example.com/');
  for (const [command, action] of [
    ['theme_now', 'switch_theme'],
    ['language_now', 'switch_language'],
    ['version_now', 'switch_version'],
  ]) {
    const result = await registry.runCommand(command);
    assert.equal(result.requiresChoice, true, `${command} did not request a choice`);
    assert.equal(result.action.id, action);
    assert.ok(result.options.length > 0);
  }

  await assert.rejects(registry.run('edit_page'), (error) => {
    assert.equal(error.code, 'unavailable');
    assert.equal(error.message, 'Repository unavailable');
    return true;
  });
  assert.equal(
    registry.resolveUrl('edit_page'),
    null,
    'unavailable action resolved a destination URL',
  );
  await assert.rejects(registry.run('not_real'), { code: 'unsupported_action' });
  await assert.rejects(registry.runCommand('unsafe'), {
    code: 'unsupported_command',
  });

  let theme = '';
  registry.registerExecutor('switch_theme', ({ value }) => {
    theme = value.value;
  });
  await registry.run('switch_theme', { value: { value: 'dark' } });
  assert.equal(theme, 'dark');
  assert.throws(
    () => registry.registerExecutor('switch_theme', () => {}),
    { code: 'duplicate_executor' },
  );
  assert.throws(() => registry.registerExecutor('not_real', () => {}), {
    code: 'unsupported_executor',
  });

  assert.equal(
    registry.safeUrl('/preview/en/docs/'),
    'https://example.org/preview/en/docs/',
  );
  for (const unsafe of [
    'javascript:alert(1)',
    'data:text/html,boom',
    '//evil.example/x',
    '\\evil.example\\x',
    ' https://evil.example/',
  ]) {
    assert.equal(registry.safeUrl(unsafe), null, unsafe);
  }

  let attempts = 0;
  const retryHarness = harness({
    actions: [actions[0]],
    fetchImpl() {
      attempts += 1;
      if (attempts === 1) return Promise.resolve({ ok: false });
      return Promise.resolve({ ok: true, text: () => Promise.resolve('# Retry') });
    },
  });
  await assert.rejects(
    retryHarness.registry.preloadMarkdown('/preview/en/docs/page/index.md'),
  );
  await retryHarness.registry.run('copy_markdown');
  assert.equal(attempts, 2, 'failed markdown promise was not invalidated');

  const fallbackHarness = harness({ actions: [actions[0]], clipboard: false });
  await fallbackHarness.registry.run('copy_markdown');
  assert.deepEqual(fallbackHarness.events.execCommands, ['copy']);
  assert.deepEqual(fallbackHarness.events.fallbackText, ['# Page']);

  const malformedAssistant = harness({
    actions: [descriptor('open_chatgpt', {
      kind: 'url',
      url: 'https://chatgpt.com/?prompt=stale',
      target: 'blank',
    })],
  });
  assert.equal(malformedAssistant.registry.resolveUrl('open_chatgpt'), null);
  await assert.rejects(malformedAssistant.registry.run('open_chatgpt'), {
    code: 'unsafe_url',
  });

  const disabledAssistant = harness({
    actions: [descriptor('open_chatgpt', {
      kind: 'url',
      available: false,
      disabledReason: 'Site policy disabled assistant handoff',
      url: '',
      promptTemplate: 'Read from %s so I can ask questions about it.',
      target: 'blank',
    })],
  });
  assert.equal(disabledAssistant.registry.resolveUrl('open_chatgpt'), null);
  await assert.rejects(disabledAssistant.registry.run('open_chatgpt'), {
    code: 'unavailable',
  });

  console.log('action registry behavior checks passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
