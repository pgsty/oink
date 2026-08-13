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
    action('switch_theme', {
      title: 'Switch theme',
      kind: 'choice',
      keywords: ['dark', 'light', '主题'],
      options: [
        { id: 'dark', title: 'Dark', value: 'dark', available: true },
        { id: 'future', title: 'Future', available: false, disabledReason: 'Soon' },
      ],
    }),
    action('switch_language', {
      title: '切换语言',
      kind: 'choice',
      available: false,
      disabledReason: '只有一种语言',
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

  const commands = model.commandGroups(registry(), '', labels)[0].rows;
  assert.ok(commands.some((row) => row.sourceId === 'status'));
  assert.ok(commands.some((row) => row.sourceId === 'copy_markdown'));
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

  console.log('PRD 4 Palette model checks passed');
})();
