'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const model = require(path.join(__dirname, '..', '..', 'assets/js/palette-model.js'));

function action(id, values = {}) {
  return {
    id,
    title: id,
    description: '',
    keywords: [],
    kind: 'invoke',
    available: true,
    disabledReason: '',
    placements: { page: false, palette: true },
    options: [],
    ...values,
  };
}

function registry() {
  const actions = [
    action('copy_markdown', {
      title: 'Copy Markdown',
      keywords: ['source'],
      placements: { page: true, palette: true },
    }),
    action('edit_page', {
      title: 'Edit page',
      available: false,
      disabledReason: 'Repository unavailable',
      placements: { page: true, palette: true },
    }),
    action('print', {
      title: 'Print',
      placements: { page: true, palette: true },
    }),
    action('open_chatgpt', {
      title: 'Open in ChatGPT',
      icon: 'fa-brands fa-openai',
      placements: { page: true, palette: true },
    }),
    action('open_claude', {
      title: 'Open in Claude',
      icon: 'fa-brands fa-claude',
      placements: { page: true, palette: true },
    }),
    action('switch_version', {
      title: 'Switch version',
      kind: 'choice',
      options: [{ id: 'v1', title: 'v1', url: '/v1/', available: true }],
    }),
    action('switch_language', {
      title: '切换语言',
      kind: 'choice',
      available: false,
      disabledReason: '只有一种语言',
    }),
    action('switch_theme', {
      title: 'Switch theme',
      kind: 'choice',
      keywords: ['dark', 'light', '主题'],
      options: [
        { id: 'dark', title: 'Dark', value: 'dark', available: true },
        { id: 'future', title: 'Future', available: false, disabledReason: 'Soon' },
      ],
    }),
    action('open_github', { title: 'GitHub' }),
  ];
  const byId = new Map(actions.map((record) => [record.id, record]));
  const commands = [
    {
      id: 'status', title: 'Service status', description: 'Current health',
      keywords: ['uptime', '状态'], kind: 'url', available: true,
    },
    {
      id: 'theme_now', title: 'Choose appearance', keywords: ['color'],
      kind: 'builtin', action: 'switch_theme', available: true,
    },
    {
      id: 'language_now', title: '语言设置', keywords: ['中文'],
      kind: 'builtin', action: 'switch_language', available: true,
    },
  ];
  return {
    get(id) { return byId.get(id) || null; },
    list() { return actions; },
    commands() { return commands; },
    quickLinks() {
      return [
        { id: 'docs', title: 'Docs', url: '/docs/', available: true },
        { id: 'blog', title: 'Blog', url: '/blog/', available: true },
      ];
    },
  };
}

(() => {
  assert.equal(model.normalize('  ＤＡＲＫ  mode '), 'dark mode');
  assert.ok(model.score({ title: 'Dark mode' }, 'dark') > model.score({ title: 'Mode dark' }, 'dark'));
  assert.ok(model.score({ title: '主题', keywords: ['深色模式'] }, '深色') > 0);
  assert.equal(model.score({ title: 'Documentation' }, 'foo>bar'), 0);

  const ties = model.rank([
    { id: 'b', title: 'Same', keywords: ['match'] },
    { id: 'a', title: 'Same', keywords: ['match'] },
  ], 'match');
  assert.deepEqual(ties.map((row) => row.id), ['a', 'b']);

  const labels = {
    actions: 'Actions', commands: 'Commands', pageActions: 'Page actions',
    preferences: 'Preferences', quickLinks: 'Quick links', choose: 'Choose',
  };
  const empty = model.emptyGroups(registry(), labels);
  assert.deepEqual(empty.map((group) => group.key), [
    'quick', 'page-actions', 'preferences', 'commands',
  ]);
  assert.deepEqual(empty[0].rows.map((row) => row.title), ['Docs', 'Blog']);
  assert.ok(empty[1].rows.some((row) => row.sourceId === 'copy_markdown'));
  assert.ok(empty[1].rows.some((row) => row.sourceId === 'edit_page'));
  assert.ok(empty[2].rows.some((row) => row.sourceId === 'switch_language'));
  assert.deepEqual(
    empty[2].rows.map((row) => row.sourceId),
    ['switch_version', 'switch_language', 'switch_theme'],
    'preferences must mirror the navbar order',
  );

  assert.deepEqual(
    empty[3].rows.map((row) => row.sourceId),
    ['open_github', 'status', 'theme_now', 'language_now'],
    'commands group must mirror navbar order with configured commands last',
  );

  const commands = model.commandGroups(registry(), '', labels)[0].rows;
  assert.ok(commands.some((row) => row.sourceId === 'status'));
  assert.ok(commands.some((row) => row.sourceId === 'copy_markdown'));
  assert.deepEqual(
    commands.map((row) => row.sourceId),
    [
      'copy_markdown', 'edit_page', 'print', 'open_chatgpt', 'open_claude',
      'switch_version', 'switch_language', 'switch_theme', 'open_github',
      'status', 'theme_now', 'language_now',
    ],
    'empty command mode must keep manifest order, configured commands last',
  );
  assert.equal(
    commands.find((row) => row.sourceId === 'open_chatgpt').icon,
    'fa-brands fa-openai',
  );
  assert.equal(
    commands.find((row) => row.sourceId === 'open_claude').icon,
    'fa-brands fa-claude',
  );
  const language = commands.find((row) => row.sourceId === 'language_now');
  assert.equal(language.available, false, 'alias did not inherit target availability');
  assert.equal(language.disabledReason, '只有一种语言');
  assert.deepEqual(
    model.commandGroups(registry(), '状态', labels)[0].rows.map((row) => row.sourceId),
    ['status'],
  );
  assert.deepEqual(
    model.commandGroups(registry(), 'dark', labels)[0].rows.map((row) => row.sourceId),
    ['switch_theme'],
  );

  const target = registry().get('switch_theme');
  const owner = registry().commands().find((row) => row.id === 'theme_now');
  const choices = model.choiceGroup(target, owner, labels)[0].rows;
  assert.deepEqual(choices.map((row) => row.sourceId), ['dark', 'future']);
  assert.equal(choices[1].available, false);
  assert.equal(choices[1].disabledReason, 'Soon');
  assert.equal(choices[0].command.id, 'theme_now');

  console.log('Palette model checks passed');
})();
