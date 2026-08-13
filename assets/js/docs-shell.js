/**
 * docs-shell.js — documentation shell interactions (no framework).
 *
 * Modules: rootMenu (root switcher), drawer (mobile navigation), collapse
 * (desktop sidebar and hover overlay), resize, treeScroll, toc (SVG track,
 * clip-path highlight, and moving dot). The local search/Palette controller
 * lives in command-palette.js so it can be omitted independently.
 *
 * The theme keeps the `td-color-theme` localStorage key and
 * <html data-bs-theme>. The collapsed sidebar state is stored under
 * `td-shell-sidebar-collapsed` and restored by the prepaint script. That
 * script also suppresses first-frame animations; this file re-enables them
 * after two animation frames.
 */
(function () {
  'use strict';

  var html = document.documentElement;
  var MD = '(min-width: 768px)';

  /* ----------------------------------------------------------- focus trap */

  var FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), ' +
    'select:not([disabled]), textarea:not([disabled]), ' +
    '[tabindex]:not([tabindex="-1"])';

  function focusable(container) {
    return Array.prototype.filter.call(
      container.querySelectorAll(FOCUSABLE),
      function (el) {
        return el.offsetParent !== null || el === document.activeElement;
      },
    );
  }

  // Keep Tab inside a modal surface. Returns a handler to attach on keydown;
  // it is inert until `isActive()` reports the surface as open, so the same
  // listener can stay bound for the life of the page.
  function tabTrap(container, isActive) {
    return function (event) {
      if (event.key !== 'Tab' || !isActive()) return;
      var items = focusable(container);
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      var active = document.activeElement;
      if (event.shiftKey && (active === first || !container.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
  }

  /* -------------------------------------------------------- rightCollapse */

  // Collapse the complete right rail and persist the state in localStorage.
  function initRightCollapse() {
    var buttons = document.querySelectorAll('[data-td-shell-right-toggle]');
    if (!buttons.length) return;
    function collapsed() {
      return html.getAttribute('data-td-shell-toc') === 'collapsed';
    }
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var next = !collapsed();
        if (next) {
          html.setAttribute('data-td-shell-toc', 'collapsed');
        } else {
          html.removeAttribute('data-td-shell-toc');
        }
        try {
          localStorage.setItem('td-shell-toc-collapsed', next ? '1' : '0');
        } catch (e) {
          /* ignore */
        }
      });
    });
  }

  /* --------------------------------------------------------- footerOffset */

  // Shorten the fixed sidebar as the footer enters the viewport.
  function initFooterOffset() {
    var footer = document.querySelector('[data-td-shell-footer]');
    var panel = document.querySelector('.td-shell-sidebar__panel');
    if (!footer || !panel) return;
    var frame = 0;

    function update() {
      frame = 0;
      var viewportHeight = window.visualViewport
        ? window.visualViewport.height
        : window.innerHeight;
      var offset = Math.max(
        0,
        viewportHeight - footer.getBoundingClientRect().top,
      );
      if (offset > 0) offset += 1;
      html.style.setProperty('--td-shell-footer-offset', offset + 'px');
    }
    function schedule() {
      if (!frame) frame = window.requestAnimationFrame(update);
    }

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('scroll', schedule, {
        passive: true,
      });
      window.visualViewport.addEventListener('resize', schedule);
    }
    if ('ResizeObserver' in window)
      new ResizeObserver(schedule).observe(footer);
    update();
  }

  /* ------------------------------------------------------------ rootMenu */

  // Root switcher: a 100ms scale popover closed by Escape or an outside click.
  function initRootMenu() {
    var root = document.querySelector('.td-shell-root');
    if (!root) return;
    var btn = root.querySelector('[data-td-shell-root-toggle]');
    var pop = root.querySelector('.td-shell-root__pop');
    var closeTimer = 0;
    if (!btn || !pop) return;

    function close(restoreFocus) {
      if (pop.hidden) return;
      window.clearTimeout(closeTimer);
      pop.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
      closeTimer = window.setTimeout(function () {
        pop.hidden = true;
      }, 100);
      if (restoreFocus === true) btn.focus();
      document.removeEventListener('pointerdown', onOutside, true);
    }
    function open() {
      window.clearTimeout(closeTimer);
      if (window.OinkSurfaceCoordinator)
        window.OinkSurfaceCoordinator.closeOthers('root-menu', ['drawer']);
      pop.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      window.requestAnimationFrame(function () {
        pop.classList.add('is-open');
      });
      document.addEventListener('pointerdown', onOutside, true);
    }
    if (window.OinkSurfaceCoordinator)
      window.OinkSurfaceCoordinator.register('root-menu', function (restoreFocus) {
        close(restoreFocus);
      });
    function onOutside(e) {
      if (!root.contains(e.target)) close(false);
    }
    btn.addEventListener('click', function () {
      if (pop.hidden) {
        open();
      } else {
        close(false);
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !pop.hidden) close(true);
    });
  }

  /* --------------------------------------------------------------- drawer */

  function initDrawer() {
    var sidebar = document.getElementById('td-shell-sidebar');
    if (!sidebar) return;
    var openers = document.querySelectorAll('[data-td-shell-drawer-open]');
    var closeButton = sidebar.querySelector(
      'button[data-td-shell-drawer-close]',
    );
    var lastOpener = null;
    function open(event) {
      if (window.OinkSurfaceCoordinator)
        window.OinkSurfaceCoordinator.closeOthers('drawer');
      lastOpener = event.currentTarget;
      html.setAttribute('data-td-shell-drawer', 'open');
      openers.forEach(function (el) {
        el.setAttribute('aria-expanded', 'true');
      });
      if (closeButton)
        window.requestAnimationFrame(function () {
          closeButton.focus();
        });
    }
    if (window.OinkSurfaceCoordinator)
      window.OinkSurfaceCoordinator.register('drawer', close);
    function close(restoreFocus) {
      var wasOpen = html.hasAttribute('data-td-shell-drawer');
      html.removeAttribute('data-td-shell-drawer');
      openers.forEach(function (el) {
        el.setAttribute('aria-expanded', 'false');
      });
      if (wasOpen && restoreFocus !== false && lastOpener) lastOpener.focus();
    }
    openers.forEach(function (el) {
      el.addEventListener('click', open);
    });
    document
      .querySelectorAll('[data-td-shell-drawer-close]')
      .forEach(function (el) {
        el.addEventListener('click', function () {
          close(true);
        });
      });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && html.hasAttribute('data-td-shell-drawer'))
        close(true);
    });
    // The drawer is modal; keep keyboard focus out of the obscured document.
    document.addEventListener(
      'keydown',
      tabTrap(sidebar, function () {
        return html.hasAttribute('data-td-shell-drawer');
      }),
      true,
    );
    // Clear drawer state across the md breakpoint to avoid a stale scroll lock.
    window.matchMedia(MD).addEventListener('change', function (mq) {
      if (mq.matches) close(false);
    });
  }

  /* ------------------------------------------------------------- collapse */

  function initCollapse() {
    var aside = document.getElementById('td-shell-sidebar');
    if (!aside) return;
    var panel = aside.querySelector('.td-shell-sidebar__panel');
    if (!panel) return;
    var mdQuery = window.matchMedia(MD);
    var lockUntil = 0;
    var closeTimer = 0;

    function collapsed() {
      return html.getAttribute('data-td-shell-sidebar') === 'collapsed';
    }
    function setCollapsed(value) {
      window.clearTimeout(closeTimer);
      aside.classList.remove('td-shell-sidebar--overlay');
      if (value) {
        html.setAttribute('data-td-shell-sidebar', 'collapsed');
      } else {
        html.removeAttribute('data-td-shell-sidebar');
      }
      try {
        localStorage.setItem('td-shell-sidebar-collapsed', value ? '1' : '0');
      } catch (e) {
        /* ignore */
      }
      // Suppress hover-open briefly after an explicit state change.
      lockUntil = performance.now() + 150;
    }

    document
      .querySelectorAll('[data-td-shell-sidebar-toggle]')
      .forEach(function (btn) {
        btn.addEventListener('click', function () {
          setCollapsed(!collapsed());
        });
      });

    // The collapsed panel leaves a 16px transparent hover target.
    panel.addEventListener('pointerenter', function (e) {
      if (e.pointerType === 'touch' || !mdQuery.matches) return;
      if (!collapsed() || performance.now() < lockUntil) return;
      window.clearTimeout(closeTimer);
      aside.classList.add('td-shell-sidebar--overlay');
    });
    panel.addEventListener('pointerleave', function (e) {
      if (e.pointerType === 'touch' || !collapsed()) return;
      // Near a viewport edge, allow extra time for the pointer to return.
      var nearEdge =
        Math.min(e.clientX, document.body.clientWidth - e.clientX) <= 100;
      window.clearTimeout(closeTimer);
      closeTimer = window.setTimeout(
        function () {
          aside.classList.remove('td-shell-sidebar--overlay');
          lockUntil = performance.now() + 150;
        },
        nearEdge ? 500 : 0,
      );
    });

    mdQuery.addEventListener('change', function (mq) {
      if (!mq.matches) aside.classList.remove('td-shell-sidebar--overlay');
    });
  }

  /* --------------------------------------------------------------- resize */

  // Resize the shared sidebar column/panel through --td-shell-sidebar-w and
  // persist it in localStorage. Double-click resets it; min/max come from the
  // site parameters or section cascade on .td-shell-layout.
  function initResize() {
    var aside = document.getElementById('td-shell-sidebar');
    if (!aside) return;
    var handle = aside.querySelector('[data-td-shell-resizer]');
    var panel = aside.querySelector('.td-shell-sidebar__panel');
    var layout = document.querySelector('.td-shell-layout');
    if (!handle || !panel || !layout) return;
    var mdQuery = window.matchMedia(MD);

    function bounds() {
      var cs = getComputedStyle(layout);
      return {
        min: parseFloat(cs.getPropertyValue('--td-shell-sidebar-min')) || 220,
        max: parseFloat(cs.getPropertyValue('--td-shell-sidebar-max')) || 480,
      };
    }

    handle.addEventListener('pointerdown', function (e) {
      if (!mdQuery.matches || e.button !== 0) return;
      e.preventDefault();
      var b = bounds();
      var rect = panel.getBoundingClientRect();
      var rtl = getComputedStyle(panel).direction === 'rtl';
      html.setAttribute('data-td-shell-resizing', '');
      handle.setPointerCapture(e.pointerId);

      function onMove(ev) {
        var raw = rtl ? rect.right - ev.clientX : ev.clientX - rect.left;
        var w = Math.round(Math.min(b.max, Math.max(b.min, raw)));
        html.style.setProperty('--td-shell-sidebar-w', w + 'px');
      }
      function onUp() {
        handle.removeEventListener('pointermove', onMove);
        handle.removeEventListener('pointerup', onUp);
        handle.removeEventListener('pointercancel', onUp);
        html.removeAttribute('data-td-shell-resizing');
        var w = parseFloat(
          getComputedStyle(html).getPropertyValue('--td-shell-sidebar-w'),
        );
        if (w > 0) {
          try {
            localStorage.setItem('td-shell-sidebar-w', String(Math.round(w)));
          } catch (err) {
            /* ignore */
          }
        }
      }
      handle.addEventListener('pointermove', onMove);
      handle.addEventListener('pointerup', onUp);
      handle.addEventListener('pointercancel', onUp);
    });

    // Double-click resets to the breakpoint default (268px or 286px).
    handle.addEventListener('dblclick', function () {
      html.style.removeProperty('--td-shell-sidebar-w');
      try {
        localStorage.removeItem('td-shell-sidebar-w');
      } catch (err) {
        /* ignore */
      }
    });
  }

  /* ---------------------------------------------------------- treeToggles */

  function initTreeToggles() {
    document
      .querySelectorAll('[data-td-shell-tree-toggle]')
      .forEach(function (button) {
        var target = document.getElementById(
          button.getAttribute('aria-controls'),
        );
        if (!target) return;

        function setExpanded(expanded) {
          button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
          target.classList.toggle('is-open', expanded);
          var label = expanded
            ? button.dataset.labelCollapse
            : button.dataset.labelExpand;
          if (label) button.setAttribute('aria-label', label);
        }

        button.addEventListener('click', function () {
          setExpanded(button.getAttribute('aria-expanded') !== 'true');
        });
      });
  }

  /* ------------------------------------------------------------ treeScroll */

  function initTreeScroll() {
    var viewport = document.querySelector('[data-td-shell-sidebar-scroll]');
    if (!viewport) return;
    var key = 'td-shell-sidebar-scroll:' + (html.lang || 'en');

    try {
      var saved = sessionStorage.getItem(key);
      if (saved !== null) viewport.scrollTop = parseInt(saved, 10) || 0;
    } catch (e) {
      /* ignore */
    }

    // Center the active row when a deep link or restored offset placed it outside the viewport.
    var active = viewport.querySelector('.td-shell-tree__row.td-shell-active');
    if (active) {
      var rowRect = active.getBoundingClientRect();
      var boxRect = viewport.getBoundingClientRect();
      if (rowRect.top < boxRect.top || rowRect.bottom > boxRect.bottom) {
        active.scrollIntoView({ block: 'center' });
      }
    }

    var timer = 0;
    function save() {
      try {
        sessionStorage.setItem(key, String(viewport.scrollTop));
      } catch (e) {
        /* ignore */
      }
    }
    viewport.addEventListener(
      'scroll',
      function () {
        window.clearTimeout(timer);
        timer = window.setTimeout(save, 100);
      },
      { passive: true },
    );
    window.addEventListener('pagehide', save);
  }

  /* -------------------------------------------------------- asideRelocate */

  /*
   * Below xl the TOC rail is hidden, which used to take the table of contents
   * and the taxonomy clouds with it. Rather than render a second copy —
   * duplicate ids would break the scrollspy and the disclosure wiring — the
   * single block is moved into a slot in the sidebar drawer and moved back on
   * the way up.
   *
   * The groups follow the context: expanded in the rail, where there is room
   * for them, collapsed in the drawer, where the navigation tree comes first.
   * A group can opt out of the wide expansion when its default is collapsed.
   */
  function initAsideRelocate() {
    var aside = document.querySelector('[data-td-shell-aside]');
    var slot = document.querySelector('[data-td-shell-aside-slot]');
    if (!aside || !slot) return;
    var home = aside.parentElement;
    var wide = window.matchMedia('(min-width: 1200px)');

    function setGroups(expanded) {
      aside
        .querySelectorAll(
          '[data-td-shell-tree-toggle]:not([data-td-shell-aside-keep-open])',
        )
        .forEach(function (button) {
          var target = document.getElementById(
            button.getAttribute('aria-controls'),
          );
          if (!target) return;
          var shouldExpand =
            expanded &&
            !button.hasAttribute('data-td-shell-aside-default-collapsed');
          button.setAttribute(
            'aria-expanded',
            shouldExpand ? 'true' : 'false',
          );
          target.classList.toggle('is-open', shouldExpand);
          var label = shouldExpand
            ? button.dataset.labelCollapse
            : button.dataset.labelExpand;
          if (label) button.setAttribute('aria-label', label);
        });
    }

    function place(isWide) {
      var parent = isWide ? home : slot;
      if (aside.parentElement !== parent) parent.appendChild(aside);
      slot.hidden = isWide;
      setGroups(isWide);
    }

    place(wide.matches);
    wide.addEventListener('change', function (event) {
      place(event.matches);
    });
  }

  /* ------------------------------------------------------------------ toc */

  /*
   * TOC track: each item owns an SVG segment, with cubic Bezier connectors at
   * depth changes. A full-height accent path is clipped to the active range,
   * and a 4px dot moves along that path with CSS motion-path properties.
   * Indents are 20/32/44px and track x positions are 8/16/24px; the 0.5px
   * offset keeps a 1px stroke aligned to device pixels.
   */
  function initToc() {
    var body = document.getElementById('td-shell-toc-body');
    if (!body) return;
    var tocNav = body.querySelector('#TableOfContents');
    var links = Array.prototype.slice.call(
      body.querySelectorAll('#TableOfContents a[href^="#"]'),
    );
    if (!tocNav || !links.length) return;

    var SVG_NS = 'http://www.w3.org/2000/svg';

    // Depth is the number of ancestor <ul> elements plus one (Hugo starts at h2).
    function depthOf(a) {
      var d = 0;
      var el = a.parentElement;
      while (el && el !== tocNav) {
        if (el.tagName === 'UL') d++;
        el = el.parentElement;
      }
      return d + 1;
    }
    function itemOffset(depth) {
      return depth <= 2 ? 20 : depth === 3 ? 32 : 44;
    }
    function lineOffset(depth) {
      return depth <= 2 ? 8 : depth === 3 ? 16 : 24;
    }

    var depths = links.map(depthOf);
    var positions = []; // Per-item [top, bottom], relative to body without padding.
    var overlay = null;
    var dot = null;
    var pathEl = null;
    var pathLength = 0;

    function build() {
      // Rebuild after ResizeObserver reports changed geometry.
      body.querySelectorAll('.td-shell-toc__rail').forEach(function (el) {
        el.remove();
      });
      if (overlay) overlay.remove();
      positions = [];

      var d = '';
      var upperX = 0;
      var upperBottom = 0;
      var maxW = 0;
      var maxH = 0;

      links.forEach(function (a, i) {
        var depth = depths[i];
        a.style.paddingInlineStart = itemOffset(depth) + 'px';

        var l1 = lineOffset(depth);
        var l0 = i === 0 ? l1 : lineOffset(depths[i - 1]);
        var l2 = i === links.length - 1 ? l1 : lineOffset(depths[i + 1]);

        // Per-item muted track segment.
        var rail = document.createElementNS(SVG_NS, 'svg');
        rail.setAttribute(
          'class',
          'td-shell-toc__rail' + (l1 !== l2 ? ' td-shell-toc__rail--cut' : ''),
        );
        rail.setAttribute('aria-hidden', 'true');
        rail.style.width = Math.max(l0, l1) + 9 + 'px';
        if (l0 !== l1) {
          var conn = document.createElementNS(SVG_NS, 'path');
          conn.setAttribute(
            'd',
            'M ' +
              (l0 + 0.5) +
              ' 0 C ' +
              (l0 + 0.5) +
              ' 8 ' +
              (l1 + 0.5) +
              ' 4 ' +
              (l1 + 0.5) +
              ' 12',
          );
          rail.appendChild(conn);
        }
        var seg = document.createElementNS(SVG_NS, 'line');
        seg.setAttribute('x1', String(l1 + 0.5));
        seg.setAttribute('x2', String(l1 + 0.5));
        seg.setAttribute('y1', l0 === l1 ? '6' : '12');
        seg.setAttribute('y2', '100%');
        rail.appendChild(seg);
        a.appendChild(rail);

        // Accent-path nodes relative to the body origin.
        var style = getComputedStyle(a);
        var top = a.offsetTop + parseFloat(style.paddingTop);
        var bottom =
          a.offsetTop + a.clientHeight - parseFloat(style.paddingBottom);
        var x = l1 + 0.5;
        positions.push([top, bottom]);
        if (i === 0) {
          d += 'M' + x + ' ' + top + ' L' + x + ' ' + bottom;
        } else {
          d +=
            ' C ' +
            upperX +
            ' ' +
            (top - 4) +
            ' ' +
            x +
            ' ' +
            (upperBottom + 4) +
            ' ' +
            x +
            ' ' +
            top +
            ' L' +
            x +
            ' ' +
            bottom;
        }
        upperX = x;
        upperBottom = bottom;
        maxW = Math.max(maxW, x + 8);
        maxH = Math.max(maxH, bottom);
      });

      overlay = document.createElement('div');
      overlay.className = 'td-shell-toc__active';
      var svg = document.createElementNS(SVG_NS, 'svg');
      svg.setAttribute('viewBox', '0 0 ' + maxW + ' ' + maxH);
      svg.style.width = maxW + 'px';
      svg.style.height = maxH + 'px';
      pathEl = document.createElementNS(SVG_NS, 'path');
      pathEl.setAttribute('d', d);
      svg.appendChild(pathEl);
      overlay.appendChild(svg);
      dot = document.createElement('span');
      dot.className = 'td-shell-toc__dot';
      dot.style.offsetPath = 'path("' + d + '")';
      overlay.appendChild(dot);
      body.appendChild(overlay);
      pathLength = pathEl.getTotalLength();
    }

    // Binary-search the path distance for a y coordinate; y is monotonic.
    function distanceAtY(y) {
      var lo = 0;
      var hi = pathLength;
      for (var i = 0; i < 24; i++) {
        var mid = (lo + hi) / 2;
        if (pathEl.getPointAtLength(mid).y < y) {
          lo = mid;
        } else {
          hi = mid;
        }
      }
      return (lo + hi) / 2;
    }

    var linkById = new Map();
    links.forEach(function (a) {
      linkById.set(decodeURIComponent(a.hash.slice(1)), a);
    });
    var headings = [];
    linkById.forEach(function (_a, id) {
      var el = document.getElementById(id);
      if (el) headings.push(el);
    });
    if (!headings.length) return;

    var visible = new Set();
    var lastAbove = headings[0];

    function paint() {
      var actives = Array.from(visible);
      if (!actives.length && lastAbove) actives = [lastAbove];
      links.forEach(function (a) {
        a.classList.remove('active');
      });

      var firstIdx = Infinity;
      var lastIdx = -1;
      actives.forEach(function (h) {
        var a = linkById.get(h.id);
        if (!a) return;
        a.classList.add('active');
        var idx = links.indexOf(a);
        if (idx < firstIdx) firstIdx = idx;
        if (idx > lastIdx) lastIdx = idx;
      });

      if (lastIdx < 0 || !overlay) {
        if (overlay) {
          overlay.style.setProperty('--td-shell-track-top', '0px');
          overlay.style.setProperty('--td-shell-track-bottom', '0px');
          overlay.style.setProperty('--td-shell-dot-o', '0');
        }
        return;
      }
      var trackTop = positions[firstIdx][0];
      var trackBottom = positions[lastIdx][1];
      overlay.style.setProperty('--td-shell-track-top', trackTop + 'px');
      overlay.style.setProperty('--td-shell-track-bottom', trackBottom + 'px');
      overlay.style.setProperty('--td-shell-dot-o', '1');
      overlay.style.setProperty(
        '--td-shell-dot-d',
        distanceAtY(trackTop) + 'px',
      );

      // Keep the first active entry visible in a long, scrollable TOC.
      var first = links[firstIdx];
      if (first) {
        var container = body.getBoundingClientRect();
        var link = first.getBoundingClientRect();
        if (link.top < container.top || link.bottom > container.bottom) {
          first.scrollIntoView({ block: 'nearest' });
        }
      }
    }

    build();

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            visible.add(entry.target);
          } else {
            visible.delete(entry.target);
            // Keep the preceding section active between observed headings.
            if (entry.boundingClientRect.top < 100) lastAbove = entry.target;
          }
        });
        paint();
      },
      { rootMargin: '-80px 0px -25% 0px' },
    );
    headings.forEach(function (h) {
      observer.observe(h);
    });

    if ('ResizeObserver' in window) {
      var lastWidth = 0;
      new ResizeObserver(function (entries) {
        var w = entries[0].contentRect.width;
        if (Math.abs(w - lastWidth) > 1) {
          lastWidth = w;
          build();
        }
        paint();
      }).observe(body);
    }
    paint();
  }

  /* ----------------------------------------------------------------- boot */

  initRootMenu();
  initRightCollapse();
  initFooterOffset();
  initDrawer();
  initCollapse();
  initResize();
  initTreeToggles();
  initTreeScroll();
  // Before initToc: the table of contents measures geometry, so it should be
  // built where it will actually live.
  initAsideRelocate();
  initToc();

  // Restore transitions after the first painted frame.
  window.requestAnimationFrame(function () {
    window.requestAnimationFrame(function () {
      html.removeAttribute('data-td-shell-no-anim');
    });
  });
})();
