// Hydrate the active path of a visible cached sidebar without fetching fragments.
(function () {
  'use strict';

  function pathOf(url) {
    try {
      var path = new URL(url, window.location.href).pathname;
      return path.endsWith('/') ? path : path + '/';
    } catch (_) {
      return '';
    }
  }

  function init() {
    var menu = document.getElementById('td-sidebar-menu');
    if (!menu || !menu.hasAttribute('data-td-sidebar-hydrate-active')) return;

    var canonical = document.querySelector('link[rel="canonical"]');
    var current = pathOf(canonical ? canonical.href : window.location.href);
    var active = null;
    var ancestor = null;

    menu.querySelectorAll('a[href]').forEach(function (link) {
      var path = pathOf(link.href);
      if (path === current) active = link;
      if (
        path &&
        current.startsWith(path) &&
        (!ancestor || path.length > pathOf(ancestor.href).length)
      ) {
        ancestor = link;
      }
    });

    var anchor = active || ancestor;
    if (active) {
      active.classList.add('active');
      active.setAttribute('aria-current', 'page');
      var row = active.closest('.td-shell-tree__row');
      if (row) row.classList.add('td-shell-active');
    }

    for (
      var item = anchor && anchor.closest('li');
      item;
      item = item.parentElement && item.parentElement.closest('li')
    ) {
      item.classList.add('td-active-path');
      item.classList.remove('td-shell-tree__item--hidden');
      var toggle = item.querySelector(
        ':scope > .td-shell-tree__row [data-td-shell-tree-toggle]',
      );
      if (toggle) {
        toggle.setAttribute('aria-expanded', 'true');
        if (toggle.dataset.tdLabelCollapse) {
          toggle.setAttribute('aria-label', toggle.dataset.tdLabelCollapse);
        }
        var target = document.getElementById(
          toggle.getAttribute('aria-controls'),
        );
        if (target) target.classList.add('td-is-open');
      }
    }

    menu.removeAttribute('data-td-sidebar-hydrate-active');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
