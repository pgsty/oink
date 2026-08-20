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
      pop.classList.remove('td-is-open');
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
        pop.classList.add('td-is-open');
      });
      document.addEventListener('pointerdown', onOutside, true);
    }
    if (window.OinkSurfaceCoordinator)
      window.OinkSurfaceCoordinator.register(
        'root-menu',
        function (restoreFocus) {
          close(restoreFocus);
        },
      );
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
          target.classList.toggle('td-is-open', expanded);
          var label = expanded
            ? button.dataset.tdLabelCollapse
            : button.dataset.tdLabelExpand;
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
          button.setAttribute('aria-expanded', shouldExpand ? 'true' : 'false');
          target.classList.toggle('td-is-open', shouldExpand);
          var label = shouldExpand
            ? button.dataset.tdLabelCollapse
            : button.dataset.tdLabelExpand;
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

  function initFlowRailAlign() {
    var layout = document.querySelector('.td-shell-layout--toc-flow');
    if (!layout) return;
    var rail = layout.querySelector('.td-shell-toc');
    var lead =
      layout.querySelector('.td-shell-article .td-article-info') ||
      layout.querySelector('.td-shell-article .lead');
    if (!rail || !lead) return;

    var frame = 0;
    function update() {
      frame = 0;
      layout.style.removeProperty('--td-shell-toc-flow-offset');
      var offset = Math.round(
        lead.getBoundingClientRect().top - rail.getBoundingClientRect().top,
      );
      if (offset > 0)
        layout.style.setProperty('--td-shell-toc-flow-offset', offset + 'px');
    }
    function schedule() {
      if (!frame) frame = window.requestAnimationFrame(update);
    }

    update();
    window.addEventListener('resize', schedule);
    if ('ResizeObserver' in window) {
      var article = layout.querySelector('.td-shell-article');
      if (article) new ResizeObserver(schedule).observe(article);
    }
  }

  /* ------------------------------------------------------------------ toc */

  /*
   * TOC track: each item owns an SVG segment, with cubic Bezier connectors at
   * depth changes. A full-height accent path is lit along the active range by
   * its dash pattern, and a 4px dot moves along the same path with CSS
   * motion-path properties. Indents are 20/32/44px and track x positions are
   * 8/16/24px; the 0.5px offset keeps a 1px stroke aligned to device pixels.
   *
   * Two states ride that one path:
   *
   *   range  - every heading currently on screen. A dash along the accent
   *            path lights it, and the dot rides its *leading* end: the
   *            bottom while the reader is moving down the page, the top once
   *            they turn around. The line positions the dot: the script only
   *            hands CSS the dash geometry and a 0/1 end selector, and the
   *            dot's offset is computed from the same animated values the
   *            dash is drawn with, so it caps the lit line at every frame
   *            and a turn is one fast flick along the line to its other end.
   *   cursor - the one heading the reader is standing in, by the same "last
   *            heading above the scroll line" rule keyboard-nav.js uses for
   *            j/k, so a jump always lights the entry it landed on. It is
   *            folded into the range, so its pill can never strand itself off
   *            the lit path, and it stands in for the range mid-section when
   *            no heading is on screen at all.
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
    // Reversing by less than this is scroll jitter, not a change of direction.
    var TURN_SLACK = 24;
    // Only used where getComputedStyle is missing; matches keyboard-nav.js.
    var NAV_MARGIN = 24;

    // The three values the overlay animates, typed so the transitions in
    // _toc.scss interpolate them. Registered here rather than with a CSS
    // @property rule, which the production minifier drops. Without support
    // the rail snaps into place instead of animating, still glued.
    if (window.CSS && window.CSS.registerProperty) {
      try {
        window.CSS.registerProperty({
          name: '--td-shell-track-start',
          syntax: '<length>',
          inherits: true,
          initialValue: '0px',
        });
        window.CSS.registerProperty({
          name: '--td-shell-track-length',
          syntax: '<length>',
          inherits: true,
          initialValue: '0px',
        });
        window.CSS.registerProperty({
          name: '--td-shell-dot-lead',
          syntax: '<number>',
          inherits: true,
          initialValue: '1',
        });
      } catch (e) {
        // Already registered by an earlier boot: the values are compatible.
      }
    }

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
    var indexOf = new Map();
    links.forEach(function (a, i) {
      indexOf.set(a, i);
    });
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
        // Where the cursor pill starts, so it clears this item's own indent
        // instead of cutting across the muted track beside it.
        a.style.setProperty(
          '--td-shell-toc-pill-x',
          itemOffset(depth) - 6 + 'px',
        );

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
      // Malformed hashes must not disable the outline.
      var id;
      try {
        id = decodeURIComponent(a.hash.slice(1));
      } catch (e) {
        id = a.hash.slice(1);
      }
      linkById.set(id, a);
    });
    // Outline entries whose heading actually exists, carrying the link index so
    // the cursor is expressed in the same coordinates as the accent range.
    var targets = [];
    var targetOfLink = new Map();
    linkById.forEach(function (a, id) {
      var el = document.getElementById(id);
      if (!el) return;
      targetOfLink.set(indexOf.get(a), targets.length);
      targets.push({ index: indexOf.get(a), el: el });
    });
    if (!targets.length) return;

    var visible = new Set();
    var cursor = -1; // Positional index into targets; -1 above the first.
    var here = -1; // Cursor actually painted; see trackCursor below.
    var forward = true; // Reading direction the dot leads in.
    var pivot = 0; // Furthest scroll position reached in that direction.
    var scrollLine = NAV_MARGIN; // Resolved scroll-padding-top of the root.

    // Anchor jumps land a heading at the root scroller's computed
    // scroll-padding-top, so read that same resolved value rather than parsing
    // --td-shell-nav-h, whose authored `3.5rem` would parse as 3.5px.
    function readScrollLine() {
      if (!window.getComputedStyle) return NAV_MARGIN;
      var raw = String(
        window.getComputedStyle(html).getPropertyValue('scroll-padding-top') ||
          '',
      ).trim();
      if (raw === '0') return 0;
      var match = /^(-?(?:\d+(?:\.\d+)?|\.\d+))px$/.exec(raw);
      return match ? Math.max(0, parseFloat(match[1])) : NAV_MARGIN;
    }

    // A heading in the closing screenful cannot be scrolled up to the reading
    // line however hard the reader tries, so the positional rule below is
    // structurally unable to select it. Where the reader has asked for one of
    // those by name -- a TOC click, a heading link and a j/k jump all leave the
    // id in location.hash -- honour the request instead, for as long as the
    // heading is still on screen. Scroll it out of view and the pin is gone.
    function strandedTarget() {
      var hash = window.location.hash;
      if (!hash) return -1;
      var id;
      try {
        id = decodeURIComponent(hash.slice(1));
      } catch (e) {
        return -1;
      }
      var a = linkById.get(id);
      if (!a) return -1;
      var t = targetOfLink.get(indexOf.get(a));
      if (t === undefined || t <= cursor) return -1;
      var viewport = html.clientHeight;
      var rect = targets[t].el.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > viewport) return -1;
      // Still reachable: leave it to the positional rule, which will get there.
      var remaining = html.scrollHeight - viewport - (window.scrollY || 0);
      return rect.top - scrollLine > remaining + 1 ? t : -1;
    }

    // Walk from the last known cursor instead of rescanning: scrolling moves it
    // by an entry at a time, so this costs one measurement per frame, and an
    // arbitrary jump or a reflow still converges on the right entry.
    function trackCursor() {
      var edge = scrollLine + 8;
      var i = cursor;
      while (
        i + 1 < targets.length &&
        targets[i + 1].el.getBoundingClientRect().top <= edge
      ) {
        i += 1;
      }
      while (i >= 0 && targets[i].el.getBoundingClientRect().top > edge) i -= 1;
      cursor = i;
      var stranded = strandedTarget();
      var next = stranded >= 0 ? stranded : cursor;
      if (next === here) return false;
      here = next;
      return true;
    }

    // Latch direction off the scroll position rather than off the range, so
    // the dot is sent to the new leading end on the first repaint of a turn.
    function trackDirection() {
      var y = window.scrollY || window.pageYOffset || 0;
      if (forward ? y >= pivot : y <= pivot) {
        pivot = y;
        return false;
      }
      if (Math.abs(y - pivot) <= TURN_SLACK) return false;
      forward = !forward;
      pivot = y;
      return true;
    }

    function paint() {
      var first = Infinity;
      var last = -1;
      visible.forEach(function (h) {
        var a = linkById.get(h.id);
        var i = a ? indexOf.get(a) : undefined;
        if (i === undefined) return;
        if (i < first) first = i;
        if (i > last) last = i;
      });

      var at = here >= 0 ? targets[here].index : -1;
      if (at >= 0) {
        if (at < first) first = at;
        if (at > last) last = at;
      }
      // Above the first heading with nothing on screen: light the opening entry
      // rather than blanking the rail.
      if (last < 0) {
        first = 0;
        last = 0;
      }

      links.forEach(function (a, i) {
        a.classList.toggle('active', i >= first && i <= last);
        if (i === at) a.setAttribute('aria-current', 'location');
        else a.removeAttribute('aria-current');
      });

      if (!overlay) return;
      // The range as distances along the accent path. The dash is drawn from
      // these two values and the dot derives its own place from them in CSS,
      // so the script never positions the dot — it only picks the end.
      var from = distanceAtY(positions[first][0]);
      var to = distanceAtY(positions[last][1]);
      overlay.style.setProperty('--td-shell-track-start', from + 'px');
      overlay.style.setProperty(
        '--td-shell-track-length',
        Math.max(to - from, 0) + 'px',
      );
      overlay.style.setProperty('--td-shell-dot-o', '1');
      overlay.style.setProperty('--td-shell-dot-lead', forward ? '1' : '0');

      // Keep the first active entry visible in a long, scrollable TOC.
      var lead = links[first];
      if (lead) {
        var container = body.getBoundingClientRect();
        var link = lead.getBoundingClientRect();
        if (link.top < container.top || link.bottom > container.bottom) {
          lead.scrollIntoView({ block: 'nearest' });
        }
      }
    }

    scrollLine = readScrollLine();
    pivot = window.scrollY || window.pageYOffset || 0;
    build();
    trackCursor();

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) visible.add(entry.target);
          else visible.delete(entry.target);
        });
        paint();
      },
      { rootMargin: '-80px 0px -25% 0px' },
    );
    targets.forEach(function (t) {
      observer.observe(t.el);
    });

    // The range comes from the observer, but the cursor and the direction are
    // positional, so they need the scroll itself. One rAF per burst, and a
    // repaint only when something actually moved.
    var queued = 0;
    function onScroll() {
      if (queued) return;
      queued = window.requestAnimationFrame(function () {
        queued = 0;
        var moved = trackCursor();
        var turned = trackDirection();
        if (moved || turned) paint();
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    // A click on the closing entry may already be at the end of the document,
    // so the pin above needs a nudge that does not depend on the page moving.
    window.addEventListener('hashchange', onScroll);

    // scroll-padding-top is breakpoint-dependent, so a resize can move the line
    // the cursor is measured against without changing the rail's own geometry.
    window.addEventListener('resize', function () {
      scrollLine = readScrollLine();
      trackCursor();
      paint();
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
  initFlowRailAlign();
  initToc();

  // Restore transitions after the first painted frame.
  window.requestAnimationFrame(function () {
    window.requestAnimationFrame(function () {
      html.removeAttribute('data-td-shell-no-anim');
    });
  });
})();

/* Blog index form ---------------------------------------------------------
   Every form of a blog index is in the document when the site opts in; the
   reader's choice lives on the root element so shell/prepaint.html can apply
   it before the first paint, and CSS does the swapping. The button cycles
   through the forms in one fixed order. It ships hidden and is revealed
   here, so a page with no JavaScript shows no control that cannot work. */
(function () {
  var toggle = document.querySelector('[data-td-blog-index-toggle]');
  var posts = document.querySelector('.td-blog-posts[data-td-blog-default]');
  if (!toggle || !posts) return;

  var root = document.documentElement;
  var FORMS = ['list', 'cards', 'table'];

  // Seed the published default before revealing the control.
  function apply(form) {
    root.setAttribute('data-td-blog-index', form);
  }

  var initial = root.getAttribute('data-td-blog-index')
    || posts.getAttribute('data-td-blog-default')
    || 'list';
  apply(FORMS.indexOf(initial) === -1 ? 'list' : initial);
  toggle.hidden = false;

  toggle.addEventListener('click', function () {
    var current = FORMS.indexOf(root.getAttribute('data-td-blog-index'));
    var next = FORMS[(current + 1) % FORMS.length];
    apply(next);
    try { localStorage.setItem('td-blog-index', next); } catch (_) { /* private mode */ }
  });
})();
