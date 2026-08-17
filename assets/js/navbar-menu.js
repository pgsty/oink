/**
 * navbar-menu.js — one-level desktop hover panel.
 *
 * Parent labels remain ordinary links: click navigates, while hovering or
 * keyboard-focusing the item opens the panel (with a grace timer so crossing
 * the gap below the label never snaps it shut). Touch users navigate directly
 * and rely on the target page's own navigation; the compact navbar keeps the
 * same items as icons, so there is no separate mobile menu.
 */
(function () {
  'use strict';

  function setDisclosure(toggle, panel, owner, open) {
    panel.hidden = !open;
    owner.classList.toggle('td-is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    var label = open
      ? toggle.dataset.tdLabelCollapse
      : toggle.dataset.tdLabelExpand;
    if (label) toggle.setAttribute('aria-label', label);
  }

  function panelItems(panel) {
    return Array.prototype.filter.call(
      panel.querySelectorAll('a[href], button:not([disabled])'),
      function (item) {
        return !item.hasAttribute('hidden');
      },
    );
  }

  function initDesktopMenus() {
    document.querySelectorAll('[data-td-navbar-menu]').forEach(function (menu, index) {
      var parent = menu.querySelector('.td-nav-menu__parent-link');
      var panel = menu.querySelector('[data-td-navbar-panel]');
      var surfaceName = 'navbar-menu-' + index;
      if (!parent || !panel) return;
      var closeTimer = 0;
      var suppressFocusOpen = false;

      function isOpen() {
        return !panel.hidden;
      }
      function close(restoreFocus) {
        window.clearTimeout(closeTimer);
        if (!isOpen()) return;
        setDisclosure(parent, panel, menu, false);
        if (restoreFocus === true) {
          // focus() emits synchronously; do not let the focus-to-open handler
          // undo an Escape close while returning the reader to its trigger.
          suppressFocusOpen = true;
          parent.focus();
          suppressFocusOpen = false;
        }
      }
      function open(focusFirst) {
        window.clearTimeout(closeTimer);
        if (window.OinkSurfaceCoordinator)
          window.OinkSurfaceCoordinator.closeOthers(surfaceName);
        setDisclosure(parent, panel, menu, true);
        if (focusFirst)
          window.requestAnimationFrame(function () {
            var items = panelItems(panel);
            if (items.length) items[0].focus();
          });
      }
      function closeSoon() {
        window.clearTimeout(closeTimer);
        closeTimer = window.setTimeout(function () {
          close(false);
        }, 140);
      }

      if (window.OinkSurfaceCoordinator)
        window.OinkSurfaceCoordinator.register(surfaceName, close);

      parent.addEventListener('focus', function () {
        if (!suppressFocusOpen) open(false);
      });
      menu.addEventListener('pointerenter', function (event) {
        if (event.pointerType !== 'touch') open(false);
      });
      menu.addEventListener('pointerleave', function (event) {
        if (event.pointerType !== 'touch') closeSoon();
      });
      parent.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowDown') {
          event.preventDefault();
          open(true);
        } else if (event.key === 'Escape' && isOpen()) {
          event.preventDefault();
          close(true);
        }
      });
      panel.addEventListener('keydown', function (event) {
        var items = panelItems(panel);
        var current = items.indexOf(document.activeElement);
        var next = current;
        if (event.key === 'Escape') {
          event.preventDefault();
          close(true);
          return;
        } else if (event.key === 'ArrowDown') {
          next = current < 0 ? 0 : Math.min(current + 1, items.length - 1);
        } else if (event.key === 'ArrowUp') {
          next = current < 0 ? items.length - 1 : Math.max(current - 1, 0);
        } else if (event.key === 'Home') {
          next = 0;
        } else if (event.key === 'End') {
          next = items.length - 1;
        } else {
          return;
        }
        if (items.length) {
          event.preventDefault();
          items[next].focus();
        }
      });
      document.addEventListener(
        'pointerdown',
        function (event) {
          if (isOpen() && !menu.contains(event.target)) close(false);
        },
        true,
      );
      menu.addEventListener('focusout', function (event) {
        if (isOpen() && !menu.contains(event.relatedTarget)) close(false);
      });
    });
  }

  initDesktopMenus();
})();
