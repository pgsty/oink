/** Bind every rendered `data-td-action` control -- the title split button and
 *  its menu, the share bar's copy control -- to the shared action registry. */
(function () {
  'use strict';
  if (!window.OinkActions) return;

  function announce(root, text) {
    var status = root && root.querySelector('[data-td-page-context-status]');
    if (!status) return;
    status.textContent = '';
    window.requestAnimationFrame(function () { status.textContent = text; });
  }

  function showCopied(button, root) {
    // Every copy control sits inside a context root that carries the confirmed
    // wording, but the flip must survive a control that does not.
    var copied = (root && root.dataset.tdTCopied) || '';
    var label = button.querySelector('[data-td-page-copy-label]');
    button.classList.add('td-is-copied');
    if (label && !label.dataset.original) label.dataset.original = label.textContent;
    if (label && copied) label.textContent = copied;
    announce(root, copied || 'Copied');
    window.setTimeout(function () {
      button.classList.remove('td-is-copied');
      if (label && label.dataset.original) label.textContent = label.dataset.original;
    }, 1400);
  }

  function syncUrl(control, id) {
    var url = window.OinkActions.resolveUrl(id);
    if (url) control.setAttribute('href', url);
  }

  document.querySelectorAll('[data-td-action]').forEach(function (control) {
    var id = control.dataset.tdAction;
    var action = window.OinkActions.get(id);
    if (!action || !action.available) return;
    var root = control.closest('[data-td-page-context]');

    if (id === 'copy_markdown') {
      // Feedback always lands on the visible primary half, so a copy from a
      // menu row flashes the same confirmation.
      // Only a copy primary may carry the flash — on feed pages the primary
      // is the RSS link and must keep its icon.
      var feedback =
        (root &&
          root.querySelector('.td-page-actions__primary[data-td-action="copy_markdown"]')) ||
        control;
      ['pointerenter', 'focus'].forEach(function (eventName) {
        control.addEventListener(eventName, function () {
          window.OinkActions.preloadMarkdown(action.url).catch(function () {});
        }, { once: true });
      });
      control.addEventListener('click', function () {
        window.OinkActions.run(id, { source: 'page' })
          .then(function () { showCopied(feedback, root); })
          .catch(function () {
            announce(root, (root && root.dataset.tdTCopyError) || 'Copy failed');
          });
      });
    } else if (id === 'copy_link') {
      // The share bar's own control. `data-td-url` names the link explicitly;
      // without it the registry falls back to the page's canonical URL, so a
      // control that omits the attribute still copies rather than throwing.
      control.addEventListener('click', function () {
        var url = control.dataset.tdUrl || '';
        window.OinkActions.run(id, {
          source: 'page',
          value: url ? { url: url } : null,
        })
          .then(function () { showCopied(control, root); })
          .catch(function () {
            announce(root, (root && root.dataset.tdTCopyError) || 'Copy failed');
          });
      });
    } else if (id === 'print') {
      control.addEventListener('click', function () {
        window.OinkActions.run(id, { source: 'page' });
      });
    } else if (
      (id === 'open_chatgpt' || id === 'open_claude') &&
      action.kind === 'url' &&
      control.tagName === 'A'
    ) {
      syncUrl(control, id);
      control.addEventListener('click', function () { syncUrl(control, id); });
    }
  });

  /* The caret disclosure beside the title. */
  function initTitleMenu() {
    var root = document.querySelector('[data-td-page-actions]');
    if (!root) return;
    var toggle = root.querySelector('[data-td-page-actions-toggle]');
    var menu = root.querySelector('[data-td-page-actions-menu]');
    if (!toggle || !menu) return;

    function isOpen() {
      return root.classList.contains('td-is-open');
    }

    function open() {
      if (window.OinkSurfaceCoordinator) {
        window.OinkSurfaceCoordinator.closeOthers('page-actions');
      }
      root.classList.add('td-is-open');
      toggle.setAttribute('aria-expanded', 'true');
    }

    function close(restoreFocus) {
      root.classList.remove('td-is-open');
      toggle.setAttribute('aria-expanded', 'false');
      if (restoreFocus) toggle.focus();
    }

    if (window.OinkSurfaceCoordinator) {
      window.OinkSurfaceCoordinator.register('page-actions', function () {
        close(false);
      });
    }

    toggle.addEventListener('click', function () {
      if (isOpen()) close(false); else open();
    });

    // Rows act on activation; links open a new tab, copy and print run their
    // own handlers first in bubble order. Either way the menu closes.
    menu.addEventListener('click', function (event) {
      if (event.target.closest('a, button')) close(false);
    });

    document.addEventListener('pointerdown', function (event) {
      if (isOpen() && !root.contains(event.target)) close(false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isOpen()) {
        event.preventDefault();
        close(true);
        return;
      }
      if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp' &&
          event.key !== 'Home' && event.key !== 'End') return;
      if (!root.contains(document.activeElement)) return;
      var items = Array.prototype.slice.call(menu.querySelectorAll('a, button'));
      if (!items.length) return;
      if (!isOpen()) {
        if (event.key === 'ArrowDown' && document.activeElement === toggle) {
          event.preventDefault();
          open();
          items[0].focus();
        }
        return;
      }
      event.preventDefault();
      var index = items.indexOf(document.activeElement);
      if (event.key === 'Home' || (event.key === 'ArrowDown' && index === -1)) {
        items[0].focus();
      } else if (event.key === 'End') {
        items[items.length - 1].focus();
      } else if (event.key === 'ArrowDown') {
        items[Math.min(index + 1, items.length - 1)].focus();
      } else if (event.key === 'ArrowUp') {
        items[Math.max(index - 1, 0)].focus();
      }
    });
  }

  initTitleMenu();
})();
