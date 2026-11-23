/**
 * navbar-menu.js — one-level desktop hover panel and progressive navbar
 * layout (never wrap -> auto-icon collapse -> trailing overflow disclosure).
 *
 * Parent labels remain ordinary links: click navigates, while hovering or
 * keyboard-focusing the item opens the panel (with a grace timer so crossing
 * the gap below the label never snaps it shut). Touch users navigate directly
 * and rely on the target page's own navigation.
 *
 * When horizontal space cannot fit every top-level entry on one line,
 * initNavbarOverflow() first collapses icon-bearing entries to icon-only mode;
 * if space is still insufficient, trailing entries fold into the trailing "…"
 * disclosure panel with their full icon, label, and child hierarchy.
 */
(function () {
  'use strict';
  if (typeof window !== 'undefined' && window.OinkComparePane) return;

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

  function directIcon(link) {
    if (!link || !link.children) return null;
    for (var i = 0; i < link.children.length; i += 1) {
      var child = link.children[i];
      if (child.tagName && child.tagName.toUpperCase() === 'I') return child;
    }
    return null;
  }

  function itemHasIcon(item) {
    if (!item) return false;
    var link =
      item.tagName && item.tagName.toUpperCase() === 'A'
        ? item
        : item.querySelector('.td-nav-menu__parent-link, a');
    if (!link) return false;
    var attr = link.getAttribute('data-td-navbar-icon');
    if (attr === 'false') return false;
    if (attr === 'true') return true;
    return Boolean(directIcon(link));
  }

  function labelOf(link) {
    var labelEl = link.querySelector('.td-navbar-entry__label');
    if (labelEl && labelEl.textContent) return labelEl.textContent.trim();
    return (
      link.getAttribute('data-td-navbar-label') ||
      link.getAttribute('aria-label') ||
      (link.textContent || '').trim()
    );
  }

  function projectLink(source, className) {
    var link = document.createElement('a');
    var active = source.classList && source.classList.contains('active');
    link.className = className + (active ? ' active' : '');
    var href = source.getAttribute('href');
    if (href !== null) link.setAttribute('href', href);
    var target = source.getAttribute('target');
    if (target) link.setAttribute('target', target);
    var rel = source.getAttribute('rel');
    if (rel) link.setAttribute('rel', rel);
    var current = source.getAttribute('aria-current');
    if (current) link.setAttribute('aria-current', current);

    var icon = directIcon(source);
    if (icon) link.appendChild(icon.cloneNode(true));

    var label = document.createElement('span');
    label.className = 'td-navbar-entry__label';
    label.textContent = labelOf(source);
    link.appendChild(label);

    var external = source.querySelector('.td-navbar-entry__external');
    if (external) link.appendChild(external.cloneNode(true));
    return link;
  }

  function projectSubItems(container, target) {
    var hasActive = false;
    Array.prototype.forEach.call(container.children || [], function (child) {
      if (child.tagName && child.tagName.toUpperCase() === 'A') {
        if (child.classList && child.classList.contains('active')) hasActive = true;
        target.appendChild(projectLink(child, 'td-nav-menu__item-link'));
      } else if (child.classList && child.classList.contains('td-navbar-group')) {
        var group = document.createElement('div');
        group.className = 'td-navbar-group';
        var title = child.querySelector('.td-nav-menu__group-title');
        if (title) {
          if (title.classList && title.classList.contains('active')) hasActive = true;
          group.appendChild(projectLink(title, 'td-nav-menu__group-title'));
        }
        var nested = child.querySelector('.td-navbar-group__items');
        if (nested) {
          var nestedTarget = document.createElement('div');
          nestedTarget.className = 'td-navbar-group__items';
          if (projectSubItems(nested, nestedTarget)) hasActive = true;
          group.appendChild(nestedTarget);
        }
        target.appendChild(group);
      }
    });
    return hasActive;
  }

  function initNavbarOverflow() {
    if (!document.querySelectorAll) return;
    document.querySelectorAll('.td-site-nav').forEach(function (nav, index) {
      var zone = nav.querySelector('.td-nav-menu-zone');
      var overflow = nav.querySelector('[data-td-nav-overflow]');
      var trigger = overflow && overflow.querySelector('[data-td-nav-overflow-toggle]');
      var panel = overflow && overflow.querySelector('[data-td-nav-overflow-panel]');
      if (!zone || !overflow || !trigger || !panel) return;

      var brand = nav.querySelector('.td-nav-brand');
      var util = nav.querySelector('.td-nav-util-zone');
      var surfaceName = 'navbar-overflow-' + index;
      var updating = false;
      var scheduled = false;
      var prevOverflow = [];

      function isOpen() {
        return !panel.hidden;
      }

      function close(restoreFocus) {
        if (!isOpen()) return;
        setDisclosure(trigger, panel, overflow, false);
        if (restoreFocus === true) trigger.focus();
      }

      function open(focusFirst) {
        if (overflow.hidden) return;
        if (window.OinkSurfaceCoordinator)
          window.OinkSurfaceCoordinator.closeOthers(surfaceName);
        setDisclosure(trigger, panel, overflow, true);
        if (focusFirst)
          window.requestAnimationFrame(function () {
            var items = panelItems(panel);
            if (items.length) items[0].focus();
          });
      }

      if (window.OinkSurfaceCoordinator)
        window.OinkSurfaceCoordinator.register(surfaceName, close);

      trigger.addEventListener('click', function () {
        if (isOpen()) close(false);
        else open(false);
      });
      trigger.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowDown') {
          event.preventDefault();
          open(true);
        } else if (event.key === 'Escape' && isOpen()) {
          event.preventDefault();
          if (typeof event.stopPropagation === 'function') event.stopPropagation();
          close(true);
        }
      });
      panel.addEventListener('keydown', function (event) {
        var items = panelItems(panel);
        var current = items.indexOf(document.activeElement);
        var next = current;
        if (event.key === 'Escape') {
          event.preventDefault();
          if (typeof event.stopPropagation === 'function') event.stopPropagation();
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
          if (isOpen() && !overflow.contains(event.target)) close(false);
        },
        true,
      );
      overflow.addEventListener('focusout', function (event) {
        if (isOpen() && event.relatedTarget && !overflow.contains(event.relatedTarget))
          close(false);
      });

      function topLevelItems() {
        return Array.prototype.filter.call(zone.children || [], function (child) {
          return child !== overflow && !child.hasAttribute('data-td-nav-overflow');
        });
      }

      function computeMaxMenuWidth() {
        if (!nav.getBoundingClientRect) return -1;
        var navRect = nav.getBoundingClientRect();
        if (!navRect || navRect.width <= 0) return -1;

        var navWidth = Math.floor(navRect.width);
        var navStyle = window.getComputedStyle ? window.getComputedStyle(nav) : null;
        var colGap = navStyle ? parseFloat(navStyle.columnGap) || 0 : 0;

        var brandRect = brand && brand.getBoundingClientRect ? brand.getBoundingClientRect() : null;
        var brandStyle = brand && window.getComputedStyle ? window.getComputedStyle(brand) : null;
        var brandVisible = Boolean(
          brand &&
            brandRect &&
            brandRect.width > 0 &&
            (!brandStyle ||
              (brandStyle.display !== 'none' && brandStyle.visibility !== 'hidden')),
        );
        var brandWidth =
          brand && brandRect && (!brandStyle || brandStyle.display !== 'none')
            ? Math.ceil(brandRect.width)
            : 0;

        var utilRect = util && util.getBoundingClientRect ? util.getBoundingClientRect() : null;
        var utilStyle = util && window.getComputedStyle ? window.getComputedStyle(util) : null;
        var utilWidth =
          util && utilRect && (!utilStyle || utilStyle.display !== 'none')
            ? Math.ceil(utilRect.width)
            : 0;

        var sidebarOverlap = 0;
        var docEl = document.documentElement;
        var sidebar = document.getElementById ? document.getElementById('td-shell-sidebar') : null;
        var collapsed = docEl && docEl.getAttribute('data-td-shell-sidebar') === 'collapsed';
        if (sidebar && !collapsed) {
          var sbStyle = window.getComputedStyle ? window.getComputedStyle(sidebar) : null;
          if (!sbStyle || (sbStyle.display !== 'contents' && sbStyle.display !== 'none')) {
            var sbPanel = sidebar.querySelector('.td-shell-sidebar__panel') || sidebar;
            var sbRect = sbPanel.getBoundingClientRect ? sbPanel.getBoundingClientRect() : null;
            var sbWidth = Math.ceil((sbRect && sbRect.width) || sbPanel.offsetWidth || 0);
            var rtl =
              (navStyle && navStyle.direction === 'rtl') ||
              (docEl && docEl.getAttribute('dir') === 'rtl');
            var viewportW = (docEl && docEl.clientWidth) || window.innerWidth || navRect.right;
            var navStartInset = rtl
              ? Math.max(0, viewportW - navRect.right)
              : Math.max(0, navRect.left);
            sidebarOverlap = Math.max(0, sbWidth - navStartInset);
          }
        }
        var minStart = sidebarOverlap > 0 ? sidebarOverlap + 8 : 0;

        var symmetric = Boolean(
          window.matchMedia &&
            window.matchMedia('(min-width: 768px) and (max-width: 991.98px)').matches,
        );

        var maxW;
        if (symmetric) {
          var startNeed = Math.max(
            brandVisible ? brandWidth : 0,
            minStart > 0 ? minStart - colGap : 0,
          );
          maxW = navWidth - 2 * colGap - 2 * Math.max(startNeed, utilWidth);
        } else {
          maxW = navWidth - brandWidth - utilWidth - 2 * colGap;
          if (minStart > 0 && brandWidth + colGap < minStart) {
            maxW = Math.min(
              maxW,
              navWidth - utilWidth - colGap - minStart,
              navWidth - 2 * minStart,
            );
          }
        }
        return Math.max(0, Math.floor(maxW));
      }

      function measureRow(items) {
        var zoneStyle = window.getComputedStyle ? window.getComputedStyle(zone) : null;
        var gap = zoneStyle ? parseFloat(zoneStyle.columnGap || zoneStyle.gap) || 0 : 0;
        var widths = items.map(function (item) {
          return item.getBoundingClientRect
            ? Math.ceil(item.getBoundingClientRect().width)
            : 0;
        });
        var total = 0;
        for (var i = 0; i < widths.length; i += 1) {
          total += widths[i];
          if (i > 0) total += gap;
        }
        return { widths: widths, gap: gap, total: total };
      }

      function sameItems(a, b) {
        if (a.length !== b.length) return false;
        for (var i = 0; i < a.length; i += 1) {
          if (a[i] !== b[i]) return false;
        }
        return true;
      }

      function renderOverflowPanel(overflowItems) {
        if (sameItems(prevOverflow, overflowItems)) return;
        prevOverflow = overflowItems.slice();

        var frag = document.createDocumentFragment
          ? document.createDocumentFragment()
          : null;
        var host = frag || panel;
        if (!frag) panel.textContent = '';

        var hasActive = false;
        overflowItems.forEach(function (item) {
          if (item.hasAttribute && item.hasAttribute('data-td-navbar-menu')) {
            var parentLink = item.querySelector('.td-nav-menu__parent-link');
            var subPanel = item.querySelector('[data-td-navbar-panel]');
            if (!parentLink) return;
            if (parentLink.classList && parentLink.classList.contains('active'))
              hasActive = true;
            var isTaxonomy =
              subPanel &&
              subPanel.classList &&
              subPanel.classList.contains('td-nav-menu__panel--taxonomy');
            if (subPanel && !isTaxonomy && (subPanel.children || []).length > 0) {
              var group = document.createElement('div');
              group.className = 'td-navbar-group';
              group.appendChild(projectLink(parentLink, 'td-nav-menu__group-title'));
              var childWrap = document.createElement('div');
              childWrap.className = 'td-navbar-group__items';
              if (projectSubItems(subPanel, childWrap)) hasActive = true;
              group.appendChild(childWrap);
              host.appendChild(group);
            } else {
              host.appendChild(projectLink(parentLink, 'td-nav-menu__item-link'));
            }
          } else {
            if (item.classList && item.classList.contains('active')) hasActive = true;
            host.appendChild(projectLink(item, 'td-nav-menu__item-link'));
          }
        });

        if (frag) {
          panel.textContent = '';
          panel.appendChild(frag);
        }
        trigger.classList.toggle('active', hasActive);
      }

      function clearOverflow() {
        close(false);
        overflow.hidden = true;
        if (prevOverflow.length) {
          prevOverflow = [];
          panel.textContent = '';
          trigger.classList.remove('active');
        }
      }

      function update() {
        if (updating) return;
        updating = true;
        try {
          if (overflow.parentNode !== zone) zone.appendChild(overflow);
          var items = topLevelItems();

          if (!items.length) {
            nav.removeAttribute('data-td-nav-compact');
            clearOverflow();
            return;
          }

          var maxW = computeMaxMenuWidth();
          if (maxW < 0) return;

          nav.removeAttribute('data-td-nav-compact');
          items.forEach(function (item) {
            item.removeAttribute('data-td-nav-overflowed');
          });

          // Stage 1: Full labels (or CSS-compact icons below 992px).
          var row = measureRow(items);
          if (row.total <= maxW) {
            clearOverflow();
            return;
          }

          // Stage 2: Automatically collapse icon-bearing entries to icon-only mode.
          if (items.some(itemHasIcon)) {
            nav.setAttribute('data-td-nav-compact', 'icons');
            var iconRow = measureRow(items);
            if (iconRow.total < row.total) {
              row = iconRow;
              if (row.total <= maxW) {
                clearOverflow();
                return;
              }
            } else {
              // Compact mode did not shrink the row (e.g., CSS <=991.98px
              // already renders icon-only items). Avoid a redundant attribute.
              nav.removeAttribute('data-td-nav-compact');
            }
          }

          // Stage 3: Fold trailing entries into the "…" overflow disclosure.
          overflow.hidden = false;
          var moreWidth = Math.ceil(
            (trigger.getBoundingClientRect && trigger.getBoundingClientRect().width) ||
              (overflow.getBoundingClientRect && overflow.getBoundingClientRect().width) ||
              34,
          );
          var used = 0;
          var visibleCount = 0;
          for (var i = 0; i < items.length - 1; i += 1) {
            var nextUsed = used + (i > 0 ? row.gap : 0) + row.widths[i];
            if (nextUsed + row.gap + moreWidth <= maxW) {
              used = nextUsed;
              visibleCount = i + 1;
            } else {
              break;
            }
          }

          var overflowItems = items.slice(visibleCount);
          overflowItems.forEach(function (item) {
            item.setAttribute('data-td-nav-overflowed', '');
            if (item.classList && item.classList.contains('td-is-open')) {
              var subParent = item.querySelector('.td-nav-menu__parent-link');
              var subPanel = item.querySelector('[data-td-navbar-panel]');
              if (subParent && subPanel)
                setDisclosure(subParent, subPanel, item, false);
            }
          });
          renderOverflowPanel(overflowItems);
        } finally {
          updating = false;
        }
      }

      function scheduleUpdate() {
        if (scheduled) return;
        scheduled = true;
        if (typeof window.requestAnimationFrame === 'function') {
          window.requestAnimationFrame(function () {
            scheduled = false;
            update();
          });
        } else {
          scheduled = false;
          update();
        }
      }

      update();

      if (typeof ResizeObserver === 'function') {
        var ro = new ResizeObserver(function () {
          update();
        });
        ro.observe(nav);
        if (brand) ro.observe(brand);
        if (util) ro.observe(util);
        var sidebar = document.getElementById && document.getElementById('td-shell-sidebar');
        if (sidebar) {
          var sbPanel = sidebar.querySelector('.td-shell-sidebar__panel') || sidebar;
          ro.observe(sbPanel);
        }
      }

      if (typeof MutationObserver === 'function') {
        if (document.documentElement) {
          new MutationObserver(function () {
            scheduleUpdate();
          }).observe(document.documentElement, {
            attributes: true,
            attributeFilter: [
              'data-td-shell-sidebar',
              'data-td-preset',
              'data-td-typography',
              'data-td-kbd-zen',
              'dir',
            ],
          });
        }
        new MutationObserver(function () {
          if (!updating) update();
        }).observe(zone, { childList: true });
      }

      if (typeof window.addEventListener === 'function') {
        window.addEventListener('resize', scheduleUpdate, { passive: true });
      }
      if (document.fonts && document.fonts.ready && typeof document.fonts.ready.then === 'function') {
        document.fonts.ready.then(scheduleUpdate);
      }
    });
  }

  initDesktopMenus();
  initNavbarOverflow();
})();
