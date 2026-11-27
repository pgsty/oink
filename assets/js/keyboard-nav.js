/**
 * Keyboard navigation: thirty single-key shortcuts in three groups, matching
 * the 3 x 10 shortcut help.
 *
 * Navigation: W/S and the arrow keys move through the sidebar tree, A/D
 * collapse or expand a section, Enter or Space opens the focused page, Q/E
 * page through the visible sidebar order, K/J jump to the previous/next page
 * outline section, X cycles languages, R cycles internal top-level navbar
 * sections, V cycles versions, H opens the browsing history and G goes home.
 *
 * Actions: F (and "/" in the palette) searches, C (and "`" in the palette)
 * opens commands, U edits the page, N creates a child page, I files an issue,
 * O expands or collapses everything that folds, P prints, and [ ] \ hand the
 * page to ChatGPT, Claude or Gemini.
 *
 * View: B opens the duo view, Z toggles Zen Mode, M opens the Markdown
 * source, T cycles visual styles, Y cycles color modes, L switches index
 * layout forms, ; cycles gallery layouts, , and . (or < >) shrink and enlarge
 * gallery tiles, - and = narrow and widen the reading column, and ' toggles
 * the shortcut help.
 *
 * Every binding is a single-character shortcut, so all of them yield to
 * anything the reader could be typing into and to open overlays. Bundled only
 * when params.ui.keyboard_nav is not false.
 */
(function (global) {
  'use strict';
  if (typeof window !== 'undefined' && window.OinkComparePane) return;

  var SCROLL_STEP = 300; // px per fallback scroll press
  var SCROLL_DURATION = 100; // ms: a short cue, not a leisurely page scroll
  var NAV_MARGIN = 24; // fallback when computed anchor padding is unavailable
  var ZEN_KEY = 'td-kbd-zen';
  var PALETTE_KEY = 'td-kbd-palette';
  var WIDTH_KEY = 'td-shell-article-w';
  var WIDTH_STEP = 100; // px per - or = press
  var WIDTH_MIN = 600; // px: narrower than this stops being a reading column

  var TYPING_TAGS = { TEXTAREA: true, SELECT: true };
  // Non-text <input> controls (such as Expo/gallery layout radios and tile-size
  // sliders) do not consume character keystrokes, so bare shortcuts keep working
  // after a reader clicks a toolbar control.
  var NON_TYPING_INPUT_TYPES = {
    button: true,
    checkbox: true,
    color: true,
    file: true,
    hidden: true,
    image: true,
    radio: true,
    range: true,
    reset: true,
    submit: true,
  };

  function isTypingTarget(target) {
    if (!target || target.nodeType !== 1) return false;
    if (target.tagName === 'INPUT') {
      var inputType = String(
        target.type || (target.getAttribute && target.getAttribute('type')) || 'text',
      ).toLowerCase();
      return !NON_TYPING_INPUT_TYPES[inputType];
    }
    if (TYPING_TAGS[target.tagName]) return true;
    return typeof target.closest === 'function'
      ? target.closest('[contenteditable]:not([contenteditable="false"])') !== null
      : false;
  }

  // Interactive widgets that own their own arrow / +/- / single-key controls
  // (such as an embedded Leaflet map) take priority while focus sits inside.
  function isInteractiveWidget(target) {
    if (!target || target.nodeType !== 1 || typeof target.closest !== 'function') return false;
    return target.closest('[data-td-map-canvas], .td-map__canvas') !== null;
  }

  function closestByClass(node, className) {
    for (; node; node = node.parentNode) {
      if (node.classList && node.classList.contains(className)) return node;
    }
    return null;
  }

  function visibleTreeTarget(target, menu) {
    if (!target) return false;
    for (var node = target.parentNode; node && node !== menu; node = node.parentNode) {
      var list = node.classList;
      if (!list) continue;
      if (list.contains('td-shell-tree__item--hidden')) return false;
      if (
        list.contains('td-shell-tree__children') &&
        !list.contains('td-is-open') &&
        !list.contains('td-shell-tree__children--static')
      ) return false;
    }
    return true;
  }

  // Paging visits only links. Focus navigation shares their order and also
  // stops at the disclosure button of a group without a landing page.
  function visibleTreeLinks(menu) {
    if (!menu || (menu.classList && menu.classList.contains('d-none'))) return [];
    return Array.prototype.filter.call(menu.querySelectorAll('a.td-shell-tree__link'), function (link) {
      return visibleTreeTarget(link, menu);
    });
  }

  function treeRowTarget(row) {
    return row && (row.querySelector('a.td-shell-tree__link') ||
      row.querySelector('[data-td-shell-tree-toggle]'));
  }

  function visibleTreeTargets(menu) {
    if (!menu || (menu.classList && menu.classList.contains('d-none'))) return [];
    return Array.prototype.map.call(menu.querySelectorAll('.td-shell-tree__row'), treeRowTarget)
      .filter(function (target) { return visibleTreeTarget(target, menu); });
  }

  function pathOf(url, base) {
    try {
      var parsed = new URL(url, base);
      var baseParsed = new URL(base);
      if (parsed.origin !== baseParsed.origin) return '';
      var path = parsed.pathname;
      return path.endsWith('/') ? path : path + '/';
    } catch (_) {
      return '';
    }
  }

  function currentTreeIndex(links, doc, win) {
    for (var i = 0; i < links.length; i += 1) {
      if (
        (links[i].classList && links[i].classList.contains('active')) ||
        links[i].getAttribute('aria-current') === 'page'
      ) return i;
    }
    // The canonical link names the configured base URL, another origin on a
    // preview host, a LAN address or a mirror. Its path is still this page.
    var canonical = doc.querySelector('link[rel="canonical"]');
    var own = canonical ? canonical.href : win.location.href;
    var here = pathOf(own, own);
    if (!here) return -1;
    for (var n = 0; n < links.length; n += 1) {
      if (pathOf(links[n].getAttribute('href') || '', win.location.href) === here)
        return n;
    }
    return -1;
  }

  function isVisible(element, win) {
    if (!element) return false;
    if (win.getComputedStyle) {
      var style = win.getComputedStyle(element);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
    }
    return element.getClientRects().length > 0;
  }

  function init(options) {
    options = options || {};
    var doc = options.document || (global.document ? global.document : null);
    if (!doc) return null;
    var win = options.window || global;
    var html = doc.documentElement;
    var previousFocus = null;

    function registry() {
      return options.registry || global.OinkActions || null;
    }

    function palette() {
      return options.palette || global.OinkCommandPalette || null;
    }

    function menu() {
      return doc.getElementById('td-sidebar-menu');
    }

    function isShellPage() {
      return Boolean(
        doc.body && doc.body.classList &&
        doc.body.classList.contains('td-shell-chrome'),
      );
    }

    function isHomePage() {
      return Boolean(
        doc.body && doc.body.classList &&
        doc.body.classList.contains('td-home'),
      );
    }

    function hasReadingShortcuts() {
      return isShellPage() || isHomePage();
    }

    function hasOtherOpenDialog(except) {
      if (!doc.querySelectorAll) return false;
      if (Array.prototype.some.call(doc.querySelectorAll('dialog[open]'), function (dialog) {
        if (dialog === except) return false;
        return !dialog.classList.contains('td-appearance__panel') || dialog.matches(':modal');
      })) return true;
      return Array.prototype.some.call(
        doc.querySelectorAll('[role="dialog"]'),
        function (dialog) { return dialog !== except && isVisible(dialog, win); },
      );
    }

    function hasOpenDialog() {
      return hasOtherOpenDialog(null);
    }

    /* ------------------------------------------------------- scroll engine */

    var scrollTarget = null;
    var scrollAnimating = false;
    var scrollStart = 0;
    var scrollStartedAt = null;
    var outlineCursor = null;

    function prefersReducedMotion() {
      return win.matchMedia
        ? win.matchMedia('(prefers-reduced-motion: reduce)').matches
        : true;
    }

    function maxScroll() {
      var el = doc.documentElement;
      return Math.max(0, (el.scrollHeight || 0) - (win.innerHeight || 0));
    }

    function frameTime(timestamp) {
      if (typeof timestamp === 'number') return timestamp;
      if (win.performance && typeof win.performance.now === 'function')
        return win.performance.now();
      return Date.now();
    }

    // Bootstrap enables root-level smooth scrolling. Disable it only for the
    // synchronous write so the browser does not add a second, slower animation
    // behind our fixed 100ms timeline.
    function setScroll(position) {
      var style = html.style;
      var previous = style ? style.scrollBehavior : '';
      if (style) style.scrollBehavior = 'auto';
      win.scrollTo(0, position);
      if (style) style.scrollBehavior = previous;
    }

    // A fixed-duration cubic ease-out makes a heading jump feel immediate at
    // any distance while preserving just enough motion to show direction.
    function animateScroll(timestamp) {
      if (scrollTarget === null) {
        scrollAnimating = false;
        return;
      }
      var now = frameTime(timestamp);
      if (scrollStartedAt === null || now < scrollStartedAt)
        scrollStartedAt = now;
      var progress = Math.min(
        Math.max((now - scrollStartedAt) / SCROLL_DURATION, 0),
        1,
      );
      var eased = 1 - Math.pow(1 - progress, 3);
      setScroll(scrollStart + (scrollTarget - scrollStart) * eased);
      if (progress >= 1) {
        setScroll(scrollTarget);
        scrollTarget = null;
        scrollAnimating = false;
        scrollStartedAt = null;
        outlineCursor = null;
        return;
      }
      win.requestAnimationFrame(animateScroll);
    }

    function glideTo(position) {
      var clamped = Math.min(Math.max(position, 0), maxScroll());
      if (prefersReducedMotion()) {
        scrollTarget = null;
        scrollAnimating = false;
        scrollStartedAt = null;
        outlineCursor = null;
        setScroll(clamped);
        return;
      }
      scrollStart = typeof win.scrollY === 'number' ? win.scrollY : 0;
      scrollTarget = clamped;
      scrollStartedAt = win.performance && typeof win.performance.now === 'function'
        ? win.performance.now()
        : null;
      if (!scrollAnimating) {
        scrollAnimating = true;
        win.requestAnimationFrame(animateScroll);
      }
    }

    // Key repeat accumulates into one target, so held keys retarget the same
    // short animation instead of queueing discrete jumps. Reduced motion gets
    // instant steps.
    function scrollByStep(delta) {
      if (prefersReducedMotion()) {
        win.scrollBy(0, delta);
        return;
      }
      var current = typeof win.scrollY === 'number' ? win.scrollY : 0;
      var from = scrollTarget === null ? current : scrollTarget;
      glideTo(from + delta);
    }

    /* ------------------------------------------------------------- guards */

    // Bare shortcuts stand down while anything modal is up or the reader is
    // typing: IME composition, editable targets, held modifiers, the Command
    // Palette scroll lock, and open dialogs all take precedence. `<`, `>` and
    // `+` require Shift on standard keyboards, so only those characters (and
    // the unshifted keys under them) may pass with shiftKey held.
    function allowShiftKey(key) {
      return key === ',' || key === '<' || key === '.' || key === '>' || key === '+';
    }

    function keyGuarded(event) {
      return Boolean(
        event.isComposing || event.keyCode === 229 ||
        event.metaKey || event.ctrlKey || event.altKey ||
        (event.shiftKey && !allowShiftKey(event.key)) ||
        event.defaultPrevented ||
        isTypingTarget(event.target) ||
        isInteractiveWidget(event.target),
      );
    }

    function guarded(event) {
      return Boolean(
        keyGuarded(event) ||
        html.hasAttribute('data-td-shell-lock') ||
        hasOpenDialog(),
      );
    }

    /* --------------------------------------------------------- tree focus */

    function clearRing() {
      var previous = doc.querySelector('.td-kbd-focus');
      if (previous && previous.classList) previous.classList.remove('td-kbd-focus');
    }

    // The highlight lives on the row (link plus chevron), tinted like the
    // active pill, so keyboard focus reads as selection rather than a box.
    function focusLink(link) {
      if (!link) return;
      clearRing();
      var row = closestByClass(link, 'td-shell-tree__row');
      if (row && row.classList) row.classList.add('td-kbd-focus');
      try {
        link.focus({ preventScroll: true });
      } catch (_) {
        link.focus();
      }
      if (link.scrollIntoView) link.scrollIntoView({ block: 'nearest' });
    }

    function activeTreeLink() {
      var links = visibleTreeLinks(menu());
      if (!links.length) return null;
      var index = currentTreeIndex(links, doc, win);
      return links[index < 0 ? 0 : index];
    }

    // One-step movement: outside the tree the current page is the implicit
    // focus, so the first press already moves relative to it instead of
    // spending a keystroke on entering the tree.
    function treeMove(delta) {
      var targets = visibleTreeTargets(menu());
      if (!targets.length) return;
      var current = treeRowTarget(closestByClass(doc.activeElement, 'td-shell-tree__row'));
      var index = targets.indexOf(current);
      if (index < 0) {
        var links = visibleTreeLinks(menu());
        index = targets.indexOf(links[currentTreeIndex(links, doc, win)]);
      }
      var next;
      if (index < 0) {
        next = delta > 0 ? 0 : targets.length - 1;
      } else {
        // Dwell at the edges instead of wrapping.
        next = Math.min(Math.max(index + delta, 0), targets.length - 1);
      }
      focusLink(targets[next]);
    }

    function chevronOf(link) {
      var row = closestByClass(link, 'td-shell-tree__row');
      return row ? row.querySelector('[data-td-shell-tree-toggle]') : null;
    }

    function treeExpand(link) {
      var chevron = chevronOf(link);
      if (chevron && chevron.getAttribute('aria-expanded') !== 'true') {
        chevron.click();
        return;
      }
      // Expanded already (or statically open): step into the first child.
      var item = closestByClass(link, 'td-shell-tree__item');
      var targets = visibleTreeTargets(menu());
      var current = treeRowTarget(closestByClass(link, 'td-shell-tree__row'));
      var next = targets[targets.indexOf(current) + 1];
      if (next && item && item.contains(next)) focusLink(next);
    }

    function treeCollapse(link) {
      var chevron = chevronOf(link);
      if (chevron && chevron.getAttribute('aria-expanded') === 'true') {
        chevron.click();
        return;
      }
      // Collapsed or a leaf: use only the parent's own row. A recursive link
      // query would pick the first child of a non-link group, possibly itself.
      var item = closestByClass(link, 'td-shell-tree__item');
      var parentItem = item && closestByClass(item.parentNode, 'td-shell-tree__item');
      while (parentItem) {
        var row = Array.prototype.find.call(parentItem.children, function (child) {
          return child.classList && child.classList.contains('td-shell-tree__row');
        });
        var target = treeRowTarget(row);
        if (target) return focusLink(target);
        parentItem = closestByClass(parentItem.parentNode, 'td-shell-tree__item');
      }
    }

    function treeExit(link) {
      clearRing();
      var target = previousFocus;
      previousFocus = null;
      // body.focus() is a no-op in browsers, so restoring to it (the usual
      // state before the first WASD press) has to blur the link instead.
      if (
        target && target.focus && target !== doc.body &&
        target !== doc.documentElement && doc.contains(target)
      ) {
        target.focus();
        return;
      }
      if (link.blur) link.blur();
    }

    // Below the md breakpoint the tree lives in a closed drawer. WASD's
    // first press then opens it through the shell's own opener so drawer
    // state, focus trapping, and Escape handling stay owned by
    // docs-shell.js; the press lands on the active item without moving.
    function hiddenDrawerOpener() {
      if (html.hasAttribute('data-td-shell-drawer')) return null;
      var openers = doc.querySelectorAll('[data-td-shell-drawer-open]');
      return Array.prototype.find.call(openers, function (candidate) {
        return isVisible(candidate, win);
      }) || null;
    }

    function revealCollapsedSidebar() {
      if (html.getAttribute('data-td-shell-sidebar') !== 'collapsed') return false;
      var buttons = doc.querySelectorAll('[data-td-shell-sidebar-toggle]');
      var button = Array.prototype.find.call(buttons, function (candidate) {
        return isVisible(candidate, win);
      });
      if (!button) return false;
      button.click();
      return true;
    }

    function openDrawer(opener) {
      previousFocus = doc.activeElement;
      opener.click();
      win.requestAnimationFrame(function () {
        win.requestAnimationFrame(function () { focusLink(activeTreeLink()); });
      });
    }

    /* ----------------------------------------------------- outline (j/k) */

    // The homepage advances through its server-rendered top-level sections.
    // Shell targets follow the rendered page outline when one exists, so j/k
    // and the right-rail TOC always agree; heading-less pages fall back to the
    // plain glide scroll.
    function headingTargets() {
      if (isHomePage()) {
        var landing = doc.querySelector('[data-td-landing]');
        if (!landing) return [];
        return Array.prototype.filter.call(
          landing.children || [],
          function (child) {
            return child.tagName === 'SECTION' && Boolean(child.id);
          },
        );
      }
      var toc = doc.querySelector('#TableOfContents');
      var targets = [];
      if (toc) {
        Array.prototype.forEach.call(
          toc.querySelectorAll('a[href^="#"]'),
          function (anchor) {
            var rawId = (anchor.getAttribute('href') || '').slice(1);
            var id = rawId;
            try { id = decodeURIComponent(rawId); } catch (_) {}
            var el = (id && doc.getElementById(id)) || (rawId && doc.getElementById(rawId));
            if (el) targets.push(el);
          },
        );
        return targets;
      }
      var main = doc.querySelector('.td-shell-main');
      if (!main) return targets;
      return Array.prototype.slice.call(
        main.querySelectorAll('h2[id], h3[id], h4[id]'),
      );
    }

    function cssPixels(raw) {
      var value = String(raw || '').trim();
      if (value === '0') return 0;
      var match = /^(-?(?:\d+(?:\.\d+)?|\.\d+))px$/i.exec(value);
      return match ? parseFloat(match[1]) : null;
    }

    // Native hash navigation and clicks in the right-rail TOC use the root
    // scroller's computed scroll-padding plus the target's scroll margin.
    // Read those resolved pixel values directly so j/k lands at exactly the
    // same visual position. In particular, parsing --td-shell-nav-h itself is
    // wrong when its authored value is 3.5rem: parseFloat would treat that as
    // 3.5px and leave the heading underneath the navbar.
    function scrollPaddingOffset() {
      if (!win.getComputedStyle) return NAV_MARGIN;
      var style = win.getComputedStyle(html);
      var px = cssPixels(style.getPropertyValue('scroll-padding-top'));
      return px === null ? NAV_MARGIN : Math.max(0, px);
    }

    function anchorOffset(target) {
      var padding = scrollPaddingOffset();
      if (!target || !win.getComputedStyle) return padding;
      var style = win.getComputedStyle(target);
      var margin = cssPixels(style.getPropertyValue('scroll-margin-block-start'));
      if (margin === null)
        margin = cssPixels(style.getPropertyValue('scroll-margin-top'));
      return Math.max(0, padding + (margin === null ? 0 : margin));
    }

    function jumpHeading(delta) {
      var targets = headingTargets();
      if (!targets.length) return scrollByStep(delta * SCROLL_STEP);
      var queued = scrollAnimating && outlineCursor !== null;
      var current = queued ? outlineCursor : -1;
      if (!queued) {
        for (var i = 0; i < targets.length; i += 1) {
          if (
            targets[i].getBoundingClientRect().top <=
            anchorOffset(targets[i]) + 8
          ) current = i;
          else break;
        }
      }
      var next = current + delta;
      // Deep inside a section, k first re-anchors at the section's own start.
      if (
        !queued && delta < 0 && current >= 0 &&
        targets[current].getBoundingClientRect().top <
          anchorOffset(targets[current]) - 40
      ) next = current;
      if (next < 0) {
        outlineCursor = -1;
        glideTo(0);
        if (win.history && win.history.replaceState)
          win.history.replaceState(win.history.state, '', win.location.pathname + win.location.search);
        return;
      }
      if (next >= targets.length) return;
      var target = targets[next];
      outlineCursor = next;
      glideTo(
        (win.scrollY || 0) + target.getBoundingClientRect().top -
        anchorOffset(target),
      );
      if (target.id && win.history && win.history.replaceState)
        win.history.replaceState(win.history.state, '', '#' + encodeURIComponent(target.id));
    }

    /* ------------------------------------------------------ paging (q/e) */

    function pageTarget(direction) {
      // The rendered sidebar is the authoritative page order whenever it is
      // available. Section landing rows are links too, so a blog column ends
      // at the next column landing page before continuing into its first post.
      // Its empty edges stay empty: never mix the tree with a date-based pager.
      var rawLinks = visibleTreeLinks(menu());
      if (rawLinks.length) {
        var links = rawLinks.filter(function (link) {
          return link.getAttribute('target') !== '_blank' &&
            Boolean(pathOf(link.getAttribute('href') || '', win.location.href));
        });
        if (!links.length) return '';
        var index = currentTreeIndex(links, doc, win);
        if (index >= 0) {
          var neighbor = links[index + (direction === 'next' ? 1 : -1)];
          return neighbor ? neighbor.getAttribute('href') : '';
        }
        return '';
      }

      // Pages without a usable sidebar may opt into one fallback family.
      // Once selected, a missing direction is still an authoritative edge.
      var pagerRoot = doc.querySelector('[data-td-pager]');
      if (pagerRoot) {
        var pager = pagerRoot.querySelector(
          '[data-td-pager-' + (direction === 'next' ? 'next' : 'prev') + '][href]',
        );
        return pager ? pager.getAttribute('href') : '';
      }
      var relPrev = doc.querySelector('link[rel="prev"]');
      var relNext = doc.querySelector('link[rel="next"]');
      if (relPrev || relNext) {
        var rel = direction === 'next' ? relNext : relPrev;
        return rel && rel.href ? rel.href : '';
      }
      return '';
    }

    function goPage(direction) {
      var url = pageTarget(direction);
      if (url) win.location.assign(url);
    }

    /* ------------------------------------------------------ h/l/y/t/r/f/c */

    // Chrome-free reading mode: both rails, the footer, and the floating
    // restore pill disappear. The state survives q/e page flips through
    // sessionStorage.
    function setZen(on) {
      if (on) html.setAttribute('data-td-kbd-zen', '');
      else html.removeAttribute('data-td-kbd-zen');
      try {
        if (on) win.sessionStorage.setItem(ZEN_KEY, '1');
        else win.sessionStorage.removeItem(ZEN_KEY);
      } catch (_) {
        /* storage may be unavailable */
      }
    }

    function actionOf(id) {
      var actions = registry();
      if (!actions || typeof actions.get !== 'function') return null;
      var action = actions.get(id);
      return action && action.available !== false ? action : null;
    }

    // Page actions run through the registry, which owns URL policy and the
    // new-tab handoff; an action the page does not offer is not swallowed.
    function runAction(event, id) {
      var actions = registry();
      if (!actionOf(id) || typeof actions.run !== 'function') return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      var result = actions.run(id, { source: 'keyboard' });
      if (result && result.then) result.then(null, function () {});
      return true;
    }

    // The choice after the active one that can be visited, wrapping at the
    // end; the active choice itself is never a target.
    function nextChoice(id) {
      var action = actionOf(id);
      if (!action) return null;
      var choices = action.options || [];
      var active = -1;
      for (var i = 0; i < choices.length; i += 1) {
        if (choices[i] && choices[i].active) active = i;
      }
      for (var step = 1; step <= choices.length; step += 1) {
        var candidate = choices[(active + step + choices.length) % choices.length];
        if (candidate && candidate.available !== false && candidate.url && !candidate.active)
          return candidate;
      }
      return null;
    }

    function cycleChoice(event, id) {
      var choice = nextChoice(id);
      if (!choice) return false;
      return runChoice(event, id, choice);
    }

    function runChoice(event, id, choice) {
      var actions = registry();
      if (!actions || typeof actions.run !== 'function') return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      var result = actions.run(id, { source: 'keyboard', value: choice });
      if (result && result.then) result.then(null, function () {});
      return true;
    }

    function languageFallback() {
      return doc.querySelector('[data-td-language-route][href]');
    }

    function cycleLanguage(event) {
      if (cycleChoice(event, 'switch_language')) return true;
      var fallback = languageFallback();
      if (!fallback) return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      win.location.assign(fallback.getAttribute('href'));
      return true;
    }

    function homeUrl() {
      var actions = registry();
      var url = actions && typeof actions.home === 'function' ? actions.home() : '';
      if (url) return url;
      var brand = doc.querySelector('.td-nav-brand[href], .td-shell-subnav__brand[href]');
      return brand ? brand.href : '';
    }

    // On the home page itself G returns to the top instead of reloading.
    function goHome(event) {
      var url = homeUrl();
      if (!url) return false;
      event.preventDefault();
      if (pathOf(url, win.location.href) === pathOf(win.location.href, win.location.href)) {
        glideTo(0);
        return true;
      }
      win.location.assign(url);
      return true;
    }

    function historyOwner() {
      var owner = options.history || global.OinkHistory;
      var instance = owner && (owner.instance || owner);
      return instance && typeof instance.open === 'function' ? instance : null;
    }

    function openHistory(event) {
      var owner = historyOwner();
      if (!owner) return false;
      event.preventDefault();
      owner.open(event);
      return true;
    }

    /* -------------------------------------------------------- fold all (o) */

    // Everything the reader can fold: visible sidebar tree and right-rail groups
    // (one committed state in sidebar-state.js), native <details> such as
    // collapsible callouts, file trees and "more" lists, and code blocks
    // shortened to their first lines. Popover menus and hidden or collapsed
    // rails are not targets.
    function railActive(element) {
      if (html.hasAttribute('data-td-kbd-zen')) return false;
      var rail = typeof element.closest === 'function'
        ? element.closest('#td-shell-sidebar, [data-td-shell-aside]')
        : null;
      if (!rail) return false;
      var panel = typeof element.closest === 'function'
        ? element.closest('.td-shell-sidebar__panel, .td-shell-toc__panel')
        : null;
      if (panel && (panel.inert || panel.getAttribute('aria-hidden') === 'true')) return false;
      if (!isVisible(panel || rail, win)) return false;
      if (rail.id === 'td-shell-sidebar') {
        return !(
          html.getAttribute('data-td-shell-sidebar') === 'collapsed' &&
          !(rail.classList && rail.classList.contains('td-shell-sidebar--overlay'))
        );
      }
      return html.getAttribute('data-td-shell-toc') !== 'collapsed';
    }

    function foldableSurfaceVisible(el) {
      if (typeof el.closest === 'function') {
        if (el.closest('dialog, [role="dialog"], [data-td-nav-hover], .td-site-header, template, [hidden], [inert]'))
          return false;
        if (el.closest('#td-shell-sidebar, [data-td-shell-aside]') && !railActive(el))
          return false;
      }
      var outer = el;
      for (var parent = el.parentElement; parent; parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS') outer = parent;
      }
      return isVisible(outer, win);
    }

    function foldables() {
      var tree = Array.prototype.filter.call(
        doc.querySelectorAll('[data-td-shell-tree-toggle][aria-controls]'),
        railActive,
      );
      var details = Array.prototype.filter.call(
        doc.querySelectorAll('details'),
        foldableSurfaceVisible,
      );
      var code = Array.prototype.filter.call(
        doc.querySelectorAll('[data-td-code].is-collapsible'),
        function (root) {
          return Boolean(root.querySelector('[data-td-code-expand]')) &&
            foldableSurfaceVisible(root);
        },
      );
      return { tree: tree, details: details, code: code };
    }

    function hasFoldables() {
      var all = foldables();
      return all.tree.length + all.details.length + all.code.length > 0;
    }

    // Keep the line the reader was on in place while content above it opens
    // or closes; a collapsed anchor hands over to its nearest visible parent.
    // Measure article blocks directly rather than probing a fixed x coordinate,
    // which lands on margins or column padding on wide screens, Zen Mode, Book
    // slim measures, and RTL layouts.
    var ANCHOR_BLOCKS = 'h1, h2, h3, h4, h5, h6, p, li, pre, table, figure, blockquote, summary, dt, dd';

    function readingAnchor() {
      if (!(win.scrollY > 0)) return null;
      var scope = doc.querySelector('.td-shell-article .td-content') ||
        doc.querySelector('.td-shell-article') ||
        doc.querySelector('.td-shell-main') ||
        doc.querySelector('main');
      if (!scope || !scope.querySelectorAll) return null;
      var line = scrollPaddingOffset() + 8;
      var blocks = scope.querySelectorAll(ANCHOR_BLOCKS);
      var best = null;
      for (var i = 0; i < blocks.length; i += 1) {
        var block = blocks[i];
        if (typeof block.closest === 'function' && block.closest('[hidden], [inert]')) continue;
        var rect = block.getBoundingClientRect();
        if (!(rect.height > 0 && rect.bottom > line)) continue;
        if (best && !best.element.contains(block)) break;
        best = { element: block, top: rect.top };
      }
      return best;
    }

    function restoreAnchor(anchor) {
      if (!anchor) return;
      var element = anchor.element;
      while (element && element.getClientRects && !element.getClientRects().length)
        element = element.parentElement;
      if (!element || !element.getBoundingClientRect) return;
      var delta = element.getBoundingClientRect().top - anchor.top;
      if (Math.abs(delta) > 1) setScroll((win.scrollY || 0) + delta);
    }

    function toggleAll(event) {
      var all = foldables();
      var sidebar = global.OinkSidebar;
      var codeFolded = function (root) { return root.classList.contains('td-is-collapsed'); };
      var expand = all.tree.some(function (button) {
        return button.getAttribute('aria-expanded') !== 'true';
      }) || all.details.some(function (el) { return !el.open; }) || all.code.some(codeFolded);
      if (!all.tree.length && !all.details.length && !all.code.length) return false;
      event.preventDefault();
      var anchor = readingAnchor();
      // One instant frame: animated heights would move the anchor after the
      // correction below has already been measured.
      html.setAttribute('data-td-kbd-instant', '');
      all.tree.forEach(function (button) {
        var id = button.getAttribute('aria-controls');
        // The API source keeps the reader's own location open on "collapse".
        if (sidebar && typeof sidebar.setExpanded === 'function' &&
            sidebar.setExpanded(id, expand, { source: 'api' })) return;
        if ((button.getAttribute('aria-expanded') === 'true') !== expand) button.click();
      });
      all.details.forEach(function (el) { el.open = expand; });
      all.code.forEach(function (root) {
        if (codeFolded(root) === expand) root.querySelector('[data-td-code-expand]').click();
      });
      restoreAnchor(anchor);
      win.requestAnimationFrame(function () {
        restoreAnchor(anchor);
        html.removeAttribute('data-td-kbd-instant');
      });
      return true;
    }

    /* ------------------------------------------------- page width (- / =) */

    function articleBox() {
      var article = doc.querySelector('.td-shell-layout .td-shell-article');
      return article && isVisible(article, win) ? article : null;
    }

    function clearWidth() {
      html.removeAttribute('data-td-shell-article-w');
      html.style.removeProperty('--td-shell-article-w');
      try {
        win.localStorage.removeItem(WIDTH_KEY);
      } catch (_) {
        /* storage may be unavailable */
      }
    }

    // Book's reading_width constrains .td-content inside a wider article box.
    // Measure the effective reading column (content plus horizontal article
    // padding) so - and = step smoothly from what the reader actually sees.
    function measuredWidth(article) {
      var width = article.getBoundingClientRect().width;
      if (!win.getComputedStyle || !article.children) return width;
      var content = null;
      for (var i = 0; i < article.children.length; i += 1) {
        if (article.children[i].classList && article.children[i].classList.contains('td-content')) {
          content = article.children[i];
          break;
        }
      }
      if (!content || typeof content.getBoundingClientRect !== 'function') return width;
      var contentWidth = content.getBoundingClientRect().width;
      if (!(contentWidth > 0)) return width;
      var style = win.getComputedStyle(article);
      var pad = (cssPixels(style.getPropertyValue('padding-left')) || 0) +
        (cssPixels(style.getPropertyValue('padding-right')) || 0);
      var effective = contentWidth + pad;
      return effective < width - 1 ? effective : width;
    }

    // The reading column grows or shrinks by one step from its rendered
    // width, never below WIDTH_MIN and never past its container. A step that
    // reaches or crosses the page's own width (its page_width or book
    // measure) stops there and forgets the reader's width, which is the way
    // back to the author's layout. Reaching the container stores "none", so
    // a wider screen later still fills.
    function adjustWidth(event, delta) {
      var article = articleBox();
      var container = article && article.parentElement;
      var available = container ? container.clientWidth : 0;
      if (!article || !available) return false;
      event.preventDefault();
      var current = measuredWidth(article);
      var custom = html.hasAttribute('data-td-shell-article-w');
      var natural = current;
      if (custom) {
        html.removeAttribute('data-td-shell-article-w');
        natural = measuredWidth(article);
        html.setAttribute('data-td-shell-article-w', '');
      }
      var next = Math.round(current + delta * WIDTH_STEP);
      next = Math.max(next, Math.min(WIDTH_MIN, available));
      // At either bound the press changes nothing, so it records nothing: a
      // column that already fills must not leave a "fill" preference behind.
      if (Math.abs(Math.min(next, available) - current) < 1) return true;
      // A stored width the container already reduces to the page's own adds
      // nothing; drop it and take the step from the page's width.
      if (custom && Math.abs(current - natural) < 1) {
        clearWidth();
        custom = false;
      }
      if (custom && (current - natural) * (next - natural) <= 0) {
        clearWidth();
        return true;
      }
      var value = next >= available ? 'none' : String(next);
      html.setAttribute('data-td-shell-article-w', '');
      html.style.setProperty('--td-shell-article-w', value === 'none' ? 'none' : value + 'px');
      try {
        win.localStorage.setItem(WIDTH_KEY, value);
      } catch (_) {
        /* storage may be unavailable; the width still applies to this page */
      }
      return true;
    }

    function openCompare(event) {
      var button = doc.querySelector('[data-td-compare-open]');
      if (!button || button.hidden || button.disabled || typeof button.click !== 'function') return false;
      event.preventDefault();
      button.click();
      return true;
    }

    function cycleBlogLayout(event) {
      var toggle = doc.querySelector && doc.querySelector('[data-td-blog-index-toggle]');
      if (!toggle || toggle.hidden || toggle.disabled || typeof toggle.click !== 'function') return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      toggle.click();
      return true;
    }

    function dispatchControlEvent(target, type) {
      if (!target || typeof target.dispatchEvent !== 'function') return;
      var evt;
      if (typeof win.Event === 'function') {
        evt = new win.Event(type, { bubbles: true });
      } else if (typeof Event === 'function') {
        evt = new Event(type, { bubbles: true });
      } else {
        evt = { type: type, target: target, bubbles: true };
      }
      target.dispatchEvent(evt);
    }

    function galleryControls() {
      var expo = doc.querySelector && doc.querySelector('[data-td-expo]');
      if (expo && expo.querySelector && isVisible(expo, win)) {
        var expoBar = expo.querySelector('[data-td-expo-controls]');
        if (expoBar && !expoBar.hidden && isVisible(expoBar, win)) {
          return {
            controls: expoBar,
            modeSelector: 'input[data-td-expo-mode]',
            sizeSelector: 'input[data-td-expo-size]',
          };
        }
      }
      var blogGallery = doc.querySelector && doc.querySelector('[data-td-blog-gallery]');
      if (blogGallery && blogGallery.querySelector && isVisible(blogGallery, win)) {
        var galleryBar = blogGallery.querySelector('[data-gallery-controls]');
        if (galleryBar && !galleryBar.hidden && isVisible(galleryBar, win)) {
          return {
            controls: galleryBar,
            modeSelector: 'input[data-gallery-mode]',
            sizeSelector: 'input[data-gallery-size]',
          };
        }
      }
      return null;
    }

    function cycleExpoMode(event) {
      var surface = galleryControls();
      if (!surface || !surface.controls.querySelectorAll) return false;
      var inputs = Array.prototype.slice.call(surface.controls.querySelectorAll(surface.modeSelector));
      if (inputs.length < 2) return false;
      var current = -1;
      for (var i = 0; i < inputs.length; i += 1) {
        if (inputs[i].checked) current = i;
      }
      var next = inputs[(current + 1 + inputs.length) % inputs.length];
      if (!next) return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      for (var j = 0; j < inputs.length; j += 1) inputs[j].checked = inputs[j] === next;
      dispatchControlEvent(next, 'change');
      return true;
    }

    function adjustExpoSize(event, delta) {
      var surface = galleryControls();
      if (!surface || !surface.controls.querySelector) return false;
      var slider = surface.controls.querySelector(surface.sizeSelector);
      if (!slider || slider.disabled) return false;
      var min = Number(slider.getAttribute('min'));
      var max = Number(slider.getAttribute('max'));
      var step = Number(slider.getAttribute('step'));
      if (!isFinite(min)) min = 160;
      if (!isFinite(max)) max = 360;
      if (!isFinite(step) || step <= 0) step = 20;
      var current = Number(slider.value);
      if (!isFinite(current)) current = Number(slider.getAttribute('value')) || 240;
      var next = Math.min(max, Math.max(min, current + delta * step));
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      if (next === current) return true;
      slider.value = String(next);
      dispatchControlEvent(slider, 'input');
      return true;
    }

    var COLOR_MODES = ['light', 'dark', 'auto'];

    function currentColorMode() {
      var attr = html.getAttribute('data-td-color-mode');
      if (attr && COLOR_MODES.indexOf(attr) >= 0) return attr;
      if (doc.querySelector) {
        var checked = doc.querySelector('input[data-bs-theme-value]:checked');
        var radio = checked && checked.getAttribute('data-bs-theme-value');
        if (radio && COLOR_MODES.indexOf(radio) >= 0) return radio;
      }
      try {
        var stored = win.localStorage && win.localStorage.getItem('td-color-theme');
        if (stored && COLOR_MODES.indexOf(stored) >= 0) return stored;
      } catch (_) {
        /* storage may be unavailable */
      }
      var resolved = html.getAttribute('data-bs-theme');
      if (resolved === 'light' || resolved === 'dark') return resolved;
      return 'auto';
    }

    /** Step through light, dark, and system (auto) color modes in order. */
    function cycleTheme() {
      var current = currentColorMode();
      var next = COLOR_MODES[(COLOR_MODES.indexOf(current) + 1) % COLOR_MODES.length];
      var actions = registry();
      if (actions && actions.get && actions.run) {
        var action = actions.get('switch_theme');
        if (action && action.available !== false) {
          var result = actions.run('switch_theme', { value: next });
          if (result && result.then) result.then(null, function () {});
          return true;
        }
      }
      if (doc.querySelector) {
        var radio = doc.querySelector('[data-bs-theme-value="' + next + '"]');
        if (radio && typeof radio.click === 'function') {
          radio.click();
          return true;
        }
      }
      var fallback = doc.querySelector('[data-td-theme-toggle]');
      if (!fallback || typeof fallback.click !== 'function') return false;
      fallback.click();
      return true;
    }

    /** Step to the next visual preset the site offers, wrapping at the end.
     *  The Appearance runtime owns the change; without it the menu's own
     *  radios are the fallback. */
    function cyclePreset() {
      var current = html.getAttribute('data-td-preset') || '';
      var actions = registry();
      if (actions && actions.get && actions.run) {
        var action = actions.get('switch_preset');
        if (action && action.available !== false) {
          var names = (action.options || [])
            .filter(function (option) { return option && option.available !== false; })
            .map(function (option) { return option.value || option.id; });
          if (names.length > 1) {
            var result = actions.run('switch_preset', {
              value: names[(names.indexOf(current) + 1) % names.length],
            });
            if (result && result.then) result.then(null, function () {});
            return true;
          }
        }
      }
      if (!doc.querySelectorAll) return false;
      var inputs = Array.prototype.slice.call(doc.querySelectorAll('input[data-td-preset-value]'));
      var seen = [];
      inputs = inputs.filter(function (input) {
        var name = input.getAttribute('data-td-preset-value');
        if (seen.indexOf(name) >= 0) return false;
        seen.push(name);
        return true;
      });
      if (inputs.length < 2) return false;
      var next = inputs[(seen.indexOf(current) + 1) % inputs.length];
      if (typeof next.click !== 'function') return false;
      next.click();
      return true;
    }

    function navbarRoutes() {
      if (!doc.querySelectorAll) return [];
      var seen = Object.create(null);
      return Array.prototype.filter.call(
        doc.querySelectorAll('[data-td-navbar-route][href]'),
        function (link) {
          var href = link.getAttribute('href') || '';
          try {
            var target = new URL(href, win.location.href);
            var current = new URL(win.location.href);
            var key = target.origin + pathOf(target.href, win.location.href);
            if (target.origin !== current.origin || seen[key]) return false;
            seen[key] = true;
            return true;
          } catch (_) {
            return false;
          }
        },
      );
    }

    function cycleNavbar() {
      var routes = navbarRoutes();
      if (routes.length < 2) return false;
      var here = pathOf(win.location.href, win.location.href);
      var current = -1;
      var currentLength = -1;
      for (var i = 0; i < routes.length; i += 1) {
        var route = pathOf(routes[i].getAttribute('href') || '', win.location.href);
        var active = routes[i].getAttribute('aria-current') === 'page' ||
          (routes[i].classList && routes[i].classList.contains('active'));
        var contains = route && (here === route ||
          (route !== '/' && here.indexOf(route) === 0));
        if (active || (contains && route.length > currentLength)) {
          current = i;
          currentLength = active ? Number.MAX_SAFE_INTEGER : route.length;
        }
      }
      var next = routes[(current + 1 + routes.length) % routes.length];
      var url = next && next.getAttribute('href');
      if (!url) return false;
      win.location.assign(url);
      return true;
    }

    function openPalette(event, commandMode) {
      var owner = palette();
      var instance = owner && owner.instance;
      if (instance && typeof instance.open === 'function') {
        event.preventDefault();
        instance.open(event, commandMode ? owner.commandPrefix || '>' : undefined);
        return true;
      }
      // A deliberately standalone consumer homepage may not load the palette
      // or action registry. Move to its registered search surface, then resume
      // the requested mode once the full OINK runtime has initialized there.
      var fallback = doc.querySelector('[data-td-keyboard-search-route][href]');
      if (!fallback) return false;
      event.preventDefault();
      try {
        win.sessionStorage.setItem(PALETTE_KEY, commandMode ? 'command' : 'search');
      } catch (_) {
        /* storage may be unavailable; navigation remains useful */
      }
      win.location.assign(fallback.getAttribute('href'));
      return true;
    }

    function resumePalette() {
      var mode = '';
      try {
        mode = win.sessionStorage.getItem(PALETTE_KEY) || '';
        if (mode) win.sessionStorage.removeItem(PALETTE_KEY);
      } catch (_) {
        return;
      }
      if (!mode) return;
      win.setTimeout(function () {
        var owner = palette();
        var instance = owner && owner.instance;
        if (instance && typeof instance.open === 'function') {
          instance.open(null, mode === 'command' ? owner.commandPrefix || '>' : undefined);
        }
      }, 0);
    }

    /* -------------------------------------------------- shortcut help (') */

    var helpDialog = null;
    var helpCloseButton = null;
    var helpReturnFocus = null;
    var suppressHelpFocus = false;
    var helpBackdropPressed = false;
    var unavailableLabel = 'unavailable';

    function always() {
      return true;
    }

    function hasTree() {
      return Boolean(menu()) && !html.hasAttribute('data-td-kbd-zen');
    }

    function hasSearch() {
      var owner = palette();
      return Boolean(
        (owner && owner.instance && typeof owner.instance.open === 'function') ||
        doc.querySelector('[data-td-keyboard-search-route][href]'),
      );
    }

    function presetCount() {
      var action = actionOf('switch_preset');
      if (action) {
        return (action.options || []).filter(function (option) {
          return option && option.available !== false;
        }).length;
      }
      var names = {};
      Array.prototype.forEach.call(doc.querySelectorAll('input[data-td-preset-value]'), function (input) {
        names[input.getAttribute('data-td-preset-value')] = true;
      });
      return Object.keys(names).length;
    }

    function usableControl(selector) {
      var control = doc.querySelector(selector);
      return Boolean(control && !control.hidden && !control.disabled);
    }

    function galleryModes() {
      var surface = galleryControls();
      return surface && surface.controls.querySelectorAll
        ? surface.controls.querySelectorAll(surface.modeSelector).length
        : 0;
    }

    function gallerySlider() {
      var surface = galleryControls();
      var slider = surface && surface.controls.querySelector
        ? surface.controls.querySelector(surface.sizeSelector)
        : null;
      return Boolean(slider && !slider.disabled);
    }

    function hasAction(id) {
      return function () { return Boolean(actionOf(id)); };
    }

    function canPrint() {
      var actions = registry();
      var action = actions && typeof actions.get === 'function' ? actions.get('print') : null;
      if (action) return action.available !== false;
      return typeof win.print === 'function';
    }

    function printPage(event) {
      if (runAction(event, 'print')) return true;
      var actions = registry();
      var action = actions && typeof actions.get === 'function' ? actions.get('print') : null;
      if (action || typeof win.print !== 'function') return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      win.print();
      return true;
    }

    // One entry per help row. The dialog dims the rows this page cannot run
    // right now, so the 3 x 10 grid keeps its shape and still tells the truth.
    var SHORTCUTS = {
      'tree-move': hasTree,
      'tree-toggle': hasTree,
      'tree-open': hasTree,
      'page-move': function () {
        return isShellPage() && Boolean(pageTarget('prev') || pageTarget('next'));
      },
      'heading-move': function () { return hasReadingShortcuts(); },
      language: function () { return Boolean(nextChoice('switch_language') || languageFallback()); },
      route: function () { return navbarRoutes().length > 1; },
      version: function () { return Boolean(nextChoice('switch_version')); },
      history: function () { return Boolean(historyOwner()); },
      home: function () { return Boolean(homeUrl()); },
      search: hasSearch,
      commands: hasSearch,
      edit: hasAction('edit_page'),
      'new-page': hasAction('create_child_page'),
      issue: hasAction('create_issue'),
      'expand-all': hasFoldables,
      print: canPrint,
      chatgpt: hasAction('open_chatgpt'),
      claude: hasAction('open_claude'),
      gemini: hasAction('open_gemini'),
      duo: function () { return usableControl('[data-td-compare-open]'); },
      zen: function () { return hasReadingShortcuts(); },
      markdown: hasAction('view_markdown'),
      style: function () { return presetCount() > 1; },
      theme: function () {
        return Boolean(actionOf('switch_theme') ||
          doc.querySelector('[data-bs-theme-value], [data-td-theme-toggle]'));
      },
      layout: function () { return usableControl('[data-td-blog-index-toggle]'); },
      gallery: function () { return galleryModes() > 1; },
      'image-size': gallerySlider,
      'page-width': function () { return Boolean(articleBox()); },
      help: always,
    };

    function markAvailability(root) {
      if (!root || !root.querySelectorAll) return;
      Array.prototype.forEach.call(root.querySelectorAll('[data-td-shortcut]'), function (row) {
        var check = SHORTCUTS[row.getAttribute('data-td-shortcut')];
        var available = true;
        try {
          available = !check || Boolean(check());
        } catch (_) {
          available = false;
        }
        if (available) row.classList.remove('td-is-unavailable');
        else row.classList.add('td-is-unavailable');
        var note = row.querySelector('[data-td-shortcut-state]');
        if (!note && !available) {
          var description = row.querySelector('dd');
          if (!description) return;
          note = doc.createElement('span');
          note.className = 'visually-hidden';
          note.setAttribute('data-td-shortcut-state', '');
          note.textContent = ' (' + unavailableLabel + ')';
          description.appendChild(note);
        }
        if (note) note.hidden = available;
      });
    }

    // The full sheet is inert template content: the footer's hover card is
    // only a hint, and pages without a footer carry the same template.
    function helpSource() {
      var tpl = doc.querySelector && doc.querySelector('template[data-td-keyboard-help-source]');
      if (tpl && tpl.content && tpl.content.querySelector) {
        return tpl.content.querySelector('.td-shell-keyboard-help');
      }
      return null;
    }

    function isHelpOpen() {
      return Boolean(
        helpDialog &&
        (helpDialog.open || (helpDialog.hasAttribute && helpDialog.hasAttribute('open'))),
      );
    }

    function suffixDialogIds(node) {
      if (!node || !node.getAttribute) return;
      var id = node.getAttribute('id');
      if (id) node.setAttribute('id', id + '-dialog');
      var labelledBy = node.getAttribute('aria-labelledby');
      if (labelledBy) {
        node.setAttribute(
          'aria-labelledby',
          labelledBy.split(/\s+/).filter(Boolean).map(function (ref) {
            return ref + '-dialog';
          }).join(' '),
        );
      }
      var children = node.children || [];
      for (var i = 0; i < children.length; i += 1) suffixDialogIds(children[i]);
    }

    function suppressTriggerHover(target) {
      var hoverHost = target && typeof target.closest === 'function'
        ? target.closest('[data-td-nav-hover]')
        : null;
      if (!hoverHost || !hoverHost.setAttribute) return null;
      hoverHost.setAttribute('data-td-suppress-focus-open', '');
      hoverHost.setAttribute('data-td-suppress-hover-open', '');
      var clearHover = function () {
        if (hoverHost && hoverHost.removeAttribute) {
          hoverHost.removeAttribute('data-td-suppress-hover-open');
        }
      };
      if (typeof win.requestAnimationFrame === 'function') {
        win.requestAnimationFrame(function () {
          win.requestAnimationFrame(function () {
            if (typeof win.setTimeout === 'function') win.setTimeout(clearHover, 60);
            else clearHover();
          });
        });
      } else if (typeof win.setTimeout === 'function') {
        win.setTimeout(clearHover, 100);
      } else {
        clearHover();
      }
      return hoverHost;
    }

    function finishHelpClose() {
      if (isHelpOpen()) return;
      var target = helpReturnFocus;
      helpReturnFocus = null;
      var shouldRestore = !suppressHelpFocus;
      suppressHelpFocus = false;
      if (!shouldRestore) return;
      var active = doc.activeElement;
      var mayRestore = !active ||
        active === doc.body ||
        active === doc.documentElement ||
        active === helpDialog ||
        (helpDialog && helpDialog.contains && helpDialog.contains(active));
      if (
        mayRestore && target && target.focus &&
        target !== doc.body && target !== doc.documentElement &&
        doc.contains(target)
      ) {
        var hoverHost = suppressTriggerHover(target);
        try {
          target.focus({ preventScroll: true });
        } catch (_) {
          target.focus();
        } finally {
          if (hoverHost && hoverHost.removeAttribute) {
            hoverHost.removeAttribute('data-td-suppress-focus-open');
          }
        }
      }
    }

    function closeHelp(restoreFocus) {
      if (!isHelpOpen()) return;
      suppressHelpFocus = restoreFocus === false;
      // Native dialog.close() synchronously restores focus to the trigger
      // before returning, which would fire focusin on base.js's hover menu.
      // Suppress both that focusin and any post-close synthetic pointerenter.
      var hoverHost = suppressTriggerHover(helpReturnFocus);
      try {
        if (typeof helpDialog.close === 'function') {
          helpDialog.close();
        } else {
          helpDialog.open = false;
          helpDialog.removeAttribute('open');
        }
        finishHelpClose();
      } finally {
        if (hoverHost && hoverHost.removeAttribute) {
          hoverHost.removeAttribute('data-td-suppress-focus-open');
        }
      }
    }

    function buildHelpDialog(source) {
      if (helpDialog) return helpDialog;
      if (!source || !doc.createElement || !doc.body) return null;

      var dialog = doc.createElement('dialog');
      dialog.className = 'td-shell-keyboard-dialog d-print-none';
      dialog.setAttribute('data-td-keyboard-dialog', '');
      dialog.setAttribute('aria-labelledby', 'td-shell-keyboard-dialog-title');

      var surface = doc.createElement('div');
      surface.className = 'td-shell-keyboard-dialog__surface';

      var header = doc.createElement('div');
      header.className = 'td-shell-keyboard-dialog__header';

      var heading = doc.createElement('div');
      heading.className = 'td-shell-keyboard-dialog__heading';

      var sourceIcon = source.querySelector &&
        source.querySelector('.td-shell-keyboard-help__header .td-shell-icon');
      if (sourceIcon && typeof sourceIcon.cloneNode === 'function') {
        heading.appendChild(sourceIcon.cloneNode(true));
      }

      var title = doc.createElement('h2');
      title.className = 'td-shell-keyboard-dialog__title';
      title.id = 'td-shell-keyboard-dialog-title';
      var sourceTitle = source.querySelector &&
        source.querySelector('.td-shell-keyboard-help__header strong');
      title.textContent = (sourceTitle && sourceTitle.textContent) ||
        source.getAttribute('aria-label') ||
        'Shortcut help';
      heading.appendChild(title);

      var closeLabel = source.getAttribute('data-td-close-label') || 'Close';
      var closeBtn = doc.createElement('button');
      closeBtn.type = 'button';
      closeBtn.className = 'td-shell-keyboard-dialog__close';
      closeBtn.setAttribute('data-td-keyboard-dialog-close', '');
      closeBtn.setAttribute('aria-label', closeLabel);
      closeBtn.setAttribute('title', closeLabel + " (Esc / ')");
      closeBtn.setAttribute('aria-keyshortcuts', "Escape '");
      var closeIcon = doc.createElement('i');
      closeIcon.className = 'td-shell-icon td-shell-icon--x fa-solid fa-xmark';
      closeIcon.setAttribute('aria-hidden', 'true');
      closeBtn.appendChild(closeIcon);

      header.appendChild(heading);
      header.appendChild(closeBtn);
      surface.appendChild(header);

      // Thirty rows scroll on a phone and hold nothing focusable, so the
      // body itself is a labelled tab stop that the keyboard can scroll.
      var body = doc.createElement('div');
      body.className = 'td-shell-keyboard-dialog__body';
      body.setAttribute('tabindex', '0');
      body.setAttribute('role', 'region');
      body.setAttribute('aria-labelledby', 'td-shell-keyboard-dialog-title');
      var sections = source.querySelectorAll
        ? Array.prototype.slice.call(source.querySelectorAll('.td-shell-keyboard-help__section'))
        : [];
      unavailableLabel = source.getAttribute('data-td-unavailable-label') || 'unavailable';
      sections.forEach(function (section) {
        var copy = typeof section.cloneNode === 'function' ? section.cloneNode(true) : null;
        if (!copy) return;
        suffixDialogIds(copy);
        body.appendChild(copy);
      });
      surface.appendChild(body);
      dialog.appendChild(surface);
      doc.body.appendChild(dialog);

      if (closeBtn.addEventListener) {
        closeBtn.addEventListener('click', function () { closeHelp(true); });
      }
      if (dialog.addEventListener) {
        dialog.addEventListener('cancel', function (event) {
          event.preventDefault();
          closeHelp(true);
        });
        dialog.addEventListener('close', finishHelpClose);
        dialog.addEventListener('pointerdown', function (event) {
          helpBackdropPressed = event.target === dialog;
        });
        dialog.addEventListener('click', function (event) {
          if (event.target === dialog && helpBackdropPressed) closeHelp(true);
          helpBackdropPressed = false;
        });
      }

      helpDialog = dialog;
      helpCloseButton = closeBtn;
      return dialog;
    }

    function openHelp(event, returnTarget) {
      var source = helpSource();
      if (!source) return false;
      var dialog = buildHelpDialog(source);
      if (!dialog) return false;
      if (event && typeof event.preventDefault === 'function') event.preventDefault();
      markAvailability(dialog);
      helpReturnFocus = returnTarget || doc.activeElement;
      suppressHelpFocus = false;
      var coordinator = options.coordinator || win.OinkSurfaceCoordinator;
      if (coordinator && typeof coordinator.closeOthers === 'function') {
        coordinator.closeOthers('keyboard-help');
      }
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.open = true;
        dialog.setAttribute('open', '');
      }
      if (helpCloseButton && typeof helpCloseButton.focus === 'function') {
        try {
          helpCloseButton.focus({ preventScroll: true });
        } catch (_) {
          helpCloseButton.focus();
        }
      }
      return true;
    }

    function toggleHelp(event) {
      if (isHelpOpen()) {
        if (event && typeof event.preventDefault === 'function') event.preventDefault();
        closeHelp(true);
        return true;
      }
      return openHelp(event);
    }

    // Hovering the bottom-bar ? button previews the cheat sheet; clicking it
    // promotes to the centered modal dialog (same as pressing ;) and stops
    // base.js's hover-menu click handler from reopening the floating card.
    function onTriggerClick(event) {
      var target = event && event.target;
      var trigger = target && typeof target.closest === 'function'
        ? target.closest('.td-shell-keyboard__trigger')
        : null;
      if (!trigger) return;
      if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
      if (event.button && event.button !== 0) return;
      if (openHelp(event, trigger) && typeof event.stopPropagation === 'function') {
        event.stopPropagation();
      }
    }

    /* ------------------------------------------------------------ keymap */

    function onKeydown(event) {
      var key = event.key;
      if (isHelpOpen()) {
        if (key === 'Escape' && !event.defaultPrevented && !hasOtherOpenDialog(helpDialog)) {
          event.preventDefault();
          return closeHelp(true);
        }
        if (
          key === "'" &&
          !event.repeat &&
          !keyGuarded(event) &&
          !html.hasAttribute('data-td-shell-lock') &&
          !hasOtherOpenDialog(helpDialog)
        ) {
          event.preventDefault();
          return closeHelp(true);
        }
        return;
      }
      if (guarded(event)) return;
      var wrap = menu();
      var active = doc.activeElement;
      var inTree = Boolean(wrap && active && wrap.contains(active));
      var rtl = (html.getAttribute('dir') || '') === 'rtl';

      if (inTree) {
        var collapseKey = rtl ? 'ArrowRight' : 'ArrowLeft';
        var expandKey = rtl ? 'ArrowLeft' : 'ArrowRight';
        if (key === 'w' || key === 'ArrowUp') {
          event.preventDefault();
          return treeMove(-1);
        }
        if (key === 's' || key === 'ArrowDown') {
          event.preventDefault();
          return treeMove(1);
        }
        if (key === 'a' || key === collapseKey) {
          event.preventDefault();
          return treeCollapse(active);
        }
        if (key === 'd' || key === expandKey) {
          event.preventDefault();
          return treeExpand(active);
        }
        if (key === ' ') {
          // Enter keeps the link's native activation; Space must not scroll.
          event.preventDefault();
          if (active.click) active.click();
          return;
        }
        if (key === 'Escape') {
          // An open drawer owns Escape (docs-shell closes it).
          if (html.hasAttribute('data-td-shell-drawer')) return;
          event.preventDefault();
          return treeExit(active);
        }
      } else if (key === 'w' || key === 's' || key === 'a' || key === 'd') {
        if (!menu() || html.hasAttribute('data-td-kbd-zen')) {
          // No tree on this page: fall through so nothing is swallowed.
        } else {
          event.preventDefault();
          var opener = hiddenDrawerOpener();
          if (opener) return openDrawer(opener);
          revealCollapsedSidebar();
          previousFocus = doc.activeElement;
          if (key === 'w') return treeMove(-1);
          if (key === 's') return treeMove(1);
          // a/d act on the current page's item in the same press.
          var anchor = activeTreeLink();
          if (!anchor) return;
          focusLink(anchor);
          return key === 'a' ? treeCollapse(anchor) : treeExpand(anchor);
        }
      }

      // Navigation
      if (hasReadingShortcuts() && (key === 'j' || key === 'k')) {
        event.preventDefault();
        return jumpHeading(key === 'k' ? -1 : 1);
      }
      if (isShellPage() && key === 'q') return goPage('prev');
      if (isShellPage() && key === 'e') return goPage('next');
      if (key === 'x') return cycleLanguage(event);
      if (key === 'r') {
        if (cycleNavbar()) event.preventDefault();
        return;
      }
      if (key === 'v') return cycleChoice(event, 'switch_version');
      if (key === 'h') return openHistory(event);
      if (key === 'g') return goHome(event);

      // Actions
      if (key === 'f') return openPalette(event, false);
      if (key === 'c') return openPalette(event, true);
      if (key === 'u') return runAction(event, 'edit_page');
      if (key === 'n') return runAction(event, 'create_child_page');
      if (key === 'i') return runAction(event, 'create_issue');
      if (key === 'o') return toggleAll(event);
      if (key === 'p') return printPage(event);
      if (key === '[') return runAction(event, 'open_chatgpt');
      if (key === ']') return runAction(event, 'open_claude');
      if (key === '\\') return runAction(event, 'open_gemini');

      // View
      if (key === 'b') return openCompare(event);
      if (hasReadingShortcuts() && key === 'z') {
        event.preventDefault();
        return setZen(!html.hasAttribute('data-td-kbd-zen'));
      }
      if (key === 'm') return runAction(event, 'view_markdown');
      if (key === 't') return cyclePreset();
      if (key === 'y') return cycleTheme();
      if (key === 'l') return cycleBlogLayout(event);
      if (key === ';') return cycleExpoMode(event);
      if (key === ',' || key === '<') return adjustExpoSize(event, -1);
      if (key === '.' || key === '>') return adjustExpoSize(event, 1);
      if (key === '-') return adjustWidth(event, -1);
      if (key === '=' || key === '+') return adjustWidth(event, 1);
      if (key === "'" && !event.repeat) return openHelp(event);
    }

    // Re-apply the chrome-free mode chosen on a previous page.
    try {
      if (
        hasReadingShortcuts() && win.sessionStorage &&
        win.sessionStorage.getItem(ZEN_KEY)
      )
        html.setAttribute('data-td-kbd-zen', '');
    } catch (_) {
      /* storage may be unavailable */
    }

    var coordinator = options.coordinator || win.OinkSurfaceCoordinator;
    if (coordinator && typeof coordinator.register === 'function') {
      coordinator.register('keyboard-help', function (restoreFocus) {
        closeHelp(restoreFocus === true);
      });
    }
    if (win.addEventListener) {
      win.addEventListener('beforeprint', function () { closeHelp(false); });
      win.addEventListener('pagehide', function () { closeHelp(false); });
    }

    doc.addEventListener('keydown', onKeydown);
    doc.addEventListener('click', onTriggerClick, true);
    doc.addEventListener('focusin', function (event) {
      var ring = doc.querySelector('.td-kbd-focus');
      if (ring && event.target && !ring.contains(event.target)) {
        ring.classList.remove('td-kbd-focus');
      }
    });
    resumePalette();

    return Object.freeze({
      closeHelp: closeHelp,
      guarded: guarded,
      jumpHeading: jumpHeading,
      onKeydown: onKeydown,
      navbarRoutes: navbarRoutes,
      pageTarget: pageTarget,
      setZen: setZen,
      toggleHelp: toggleHelp,
    });
  }

  var api = {
    init: init,
    isTypingTarget: isTypingTarget,
    visibleTreeLinks: visibleTreeLinks,
    currentTreeIndex: currentTreeIndex,
  };
  global.OinkKeyboardNav = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (!global.__OINK_KEYBOARD_NAV_MANUAL_INIT__ && global.document) init();
})(typeof window === 'object' ? window : globalThis);
