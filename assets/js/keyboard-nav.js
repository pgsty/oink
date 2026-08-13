/**
 * PRD 6 keyboard navigation. WASD and arrow keys drive the sidebar tree,
 * q/e page through the tree order, j/k jump between the page outline's
 * sections, h toggles a chrome-free reading mode, l cycles languages,
 * t flips light/dark, and f/c open the Command Palette in search or
 * command mode. Every binding is a bare single-character shortcut, so all
 * of them yield to anything the reader could be typing into and to open
 * overlays. Bundled only when params.ui.keyboard_nav.enable is not false.
 */
(function (global) {
  'use strict';

  var SCROLL_STEP = 300; // px per fallback scroll press
  var SCROLL_EASE = 0.28; // fraction of the remaining distance per frame
  var NAV_MARGIN = 24; // breathing room under the sticky navbar
  var ZEN_KEY = 'td-kbd-zen';

  var TYPING_TAGS = { INPUT: true, TEXTAREA: true, SELECT: true };

  function isTypingTarget(target) {
    if (!target || target.nodeType !== 1) return false;
    if (TYPING_TAGS[target.tagName]) return true;
    return typeof target.closest === 'function'
      ? target.closest('[contenteditable]:not([contenteditable="false"])') !== null
      : false;
  }

  function closestByClass(node, className) {
    for (; node; node = node.parentNode) {
      if (node.classList && node.classList.contains(className)) return node;
    }
    return null;
  }

  // The flattened sequence of tree links the reader can currently see. The
  // same list drives w/s focus movement and q/e paging, so the focus order
  // and the page order can never disagree.
  function visibleTreeLinks(menu) {
    if (!menu || (menu.classList && menu.classList.contains('d-none'))) return [];
    var links = menu.querySelectorAll('a.td-shell-tree__link');
    return Array.prototype.filter.call(links, function (link) {
      for (var node = link.parentNode; node && node !== menu; node = node.parentNode) {
        var list = node.classList;
        if (!list) continue;
        if (list.contains('td-shell-tree__item--hidden')) return false;
        if (
          list.contains('td-shell-tree__children') &&
          !list.contains('is-open') &&
          !list.contains('td-shell-tree__children--static')
        ) return false;
      }
      return true;
    });
  }

  function pathOf(url, base) {
    try {
      var path = new URL(url, base).pathname;
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
    var canonical = doc.querySelector('link[rel="canonical"]');
    var here = pathOf(
      canonical ? canonical.href : win.location.href,
      win.location.href,
    );
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
    return element.offsetParent !== null;
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

    function hasOpenDialog() {
      if (!doc.querySelector) return false;
      if (doc.querySelector('dialog[open]')) return true;
      if (!doc.querySelectorAll) return false;
      return Array.prototype.some.call(
        doc.querySelectorAll('[role="dialog"]'),
        function (dialog) { return isVisible(dialog, win); },
      );
    }

    /* ------------------------------------------------------- scroll engine */

    var scrollTarget = null;
    var scrollAnimating = false;

    function prefersReducedMotion() {
      return win.matchMedia
        ? win.matchMedia('(prefers-reduced-motion: reduce)').matches
        : true;
    }

    function maxScroll() {
      var el = doc.documentElement;
      return Math.max(0, (el.scrollHeight || 0) - (win.innerHeight || 0));
    }

    function animateScroll() {
      if (scrollTarget === null) {
        scrollAnimating = false;
        return;
      }
      var remaining = scrollTarget - win.scrollY;
      if (remaining > -1 && remaining < 1) {
        win.scrollTo(0, scrollTarget);
        scrollTarget = null;
        scrollAnimating = false;
        return;
      }
      win.scrollBy(0, remaining * SCROLL_EASE);
      win.requestAnimationFrame(animateScroll);
    }

    function glideTo(position) {
      var clamped = Math.min(Math.max(position, 0), maxScroll());
      if (prefersReducedMotion()) {
        win.scrollTo(0, clamped);
        return;
      }
      scrollTarget = clamped;
      if (!scrollAnimating) {
        scrollAnimating = true;
        win.requestAnimationFrame(animateScroll);
      }
    }

    // Key repeat accumulates into one target; each frame closes a fixed
    // fraction of the remaining distance, so held keys glide instead of
    // queueing discrete jumps. Reduced motion gets instant steps.
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
    // Palette scroll lock, and open dialogs all take precedence.
    function guarded(event) {
      return Boolean(
        event.isComposing || event.keyCode === 229 ||
        event.metaKey || event.ctrlKey || event.altKey || event.shiftKey ||
        event.defaultPrevented ||
        isTypingTarget(event.target) ||
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
      var links = visibleTreeLinks(menu());
      if (!links.length) return;
      var index = links.indexOf(doc.activeElement);
      if (index < 0) index = currentTreeIndex(links, doc, win);
      var next;
      if (index < 0) {
        next = delta > 0 ? 0 : links.length - 1;
      } else {
        // Dwell at the edges instead of wrapping.
        next = Math.min(Math.max(index + delta, 0), links.length - 1);
      }
      focusLink(links[next]);
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
      var links = visibleTreeLinks(menu());
      var next = links[links.indexOf(link) + 1];
      if (next && item && item.contains(next)) focusLink(next);
    }

    function treeCollapse(link) {
      var chevron = chevronOf(link);
      if (chevron && chevron.getAttribute('aria-expanded') === 'true') {
        chevron.click();
        return;
      }
      // Collapsed or a leaf: move to the parent item's link.
      var item = closestByClass(link, 'td-shell-tree__item');
      var parentItem = item && closestByClass(item.parentNode, 'td-shell-tree__item');
      var parentLink = parentItem &&
        parentItem.querySelector('a.td-shell-tree__link');
      if (parentLink) focusLink(parentLink);
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

    // Targets follow the rendered page outline when one exists, so j/k and
    // the right-rail TOC always agree; heading-less pages fall back to the
    // plain glide scroll.
    function headingTargets() {
      var toc = doc.querySelector('#TableOfContents');
      var targets = [];
      if (toc) {
        Array.prototype.forEach.call(
          toc.querySelectorAll('a[href^="#"]'),
          function (anchor) {
            var id = (anchor.getAttribute('href') || '').slice(1);
            var el = id && doc.getElementById(id);
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

    function navOffset() {
      var raw = win.getComputedStyle
        ? win.getComputedStyle(html).getPropertyValue('--td-shell-nav-h')
        : '';
      var px = parseFloat(raw);
      return (isNaN(px) ? 0 : px) + NAV_MARGIN;
    }

    function jumpHeading(delta) {
      var targets = headingTargets();
      if (!targets.length) return scrollByStep(delta * SCROLL_STEP);
      var offset = navOffset();
      var current = -1;
      for (var i = 0; i < targets.length; i += 1) {
        if (targets[i].getBoundingClientRect().top <= offset + 8) current = i;
        else break;
      }
      var next = current + delta;
      // Deep inside a section, k first re-anchors at the section's own start.
      if (
        delta < 0 && current >= 0 &&
        targets[current].getBoundingClientRect().top < offset - 40
      ) next = current;
      if (next < 0) {
        glideTo(0);
        if (win.history && win.history.replaceState)
          win.history.replaceState(null, '', win.location.pathname + win.location.search);
        return;
      }
      if (next >= targets.length) return;
      var target = targets[next];
      glideTo((win.scrollY || 0) + target.getBoundingClientRect().top - offset);
      if (target.id && win.history && win.history.replaceState)
        win.history.replaceState(null, '', '#' + target.id);
    }

    /* ------------------------------------------------------ paging (q/e) */

    function pageTarget(direction) {
      var rel = doc.querySelector('link[rel="' + direction + '"]');
      if (rel && rel.href) return rel.href;
      var links = visibleTreeLinks(menu());
      if (links.length) {
        var index = currentTreeIndex(links, doc, win);
        if (index >= 0) {
          var neighbor = links[index + (direction === 'next' ? 1 : -1)];
          return neighbor ? neighbor.getAttribute('href') : '';
        }
      }
      var pager = doc.querySelector(
        '[data-td-pager-' + (direction === 'next' ? 'next' : 'prev') + '][href]',
      );
      return pager ? pager.getAttribute('href') : '';
    }

    function goPage(direction) {
      var url = pageTarget(direction);
      if (url) win.location.assign(url);
    }

    /* ---------------------------------------------------------- h/l/t/f/c */

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

    function cycleLanguage() {
      var actions = registry();
      if (!actions || !actions.get) return;
      var action = actions.get('switch_language');
      if (!action || action.available === false) return;
      var choices = action.options || [];
      var active = -1;
      for (var i = 0; i < choices.length; i += 1) {
        if (choices[i].active) active = i;
      }
      for (var step = 1; step <= choices.length; step += 1) {
        var candidate = choices[(active + step + choices.length) % choices.length];
        if (candidate && candidate.available !== false && candidate.url && !candidate.active) {
          win.location.assign(candidate.url);
          return;
        }
      }
    }

    function cycleTheme() {
      var actions = registry();
      if (!actions || !actions.get || !actions.run) return;
      var action = actions.get('switch_theme');
      if (!action || action.available === false) return;
      var next = html.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      var result = actions.run('switch_theme', { value: next });
      if (result && result.then) result.then(null, function () {});
    }

    function openPalette(event, commandMode) {
      var owner = palette();
      var instance = owner && owner.instance;
      if (!instance || typeof instance.open !== 'function') return;
      event.preventDefault();
      instance.open(event, commandMode ? owner.commandPrefix || '>' : undefined);
    }

    /* ------------------------------------------------------------ keymap */

    function onKeydown(event) {
      if (guarded(event)) return;
      var key = event.key;
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
        if (key === ' ' || key === 'g') {
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

      if (key === 'j' || key === 'k') {
        event.preventDefault();
        return jumpHeading(key === 'j' ? 1 : -1);
      }
      if (key === 'q') return goPage('prev');
      if (key === 'e') return goPage('next');
      if (key === 'h') {
        event.preventDefault();
        return setZen(!html.hasAttribute('data-td-kbd-zen'));
      }
      if (key === 'l') return cycleLanguage();
      if (key === 't') return cycleTheme();
      if (key === 'f') return openPalette(event, false);
      if (key === 'c') return openPalette(event, true);
    }

    // Re-apply the chrome-free mode chosen on a previous page.
    try {
      if (win.sessionStorage && win.sessionStorage.getItem(ZEN_KEY))
        html.setAttribute('data-td-kbd-zen', '');
    } catch (_) {
      /* storage may be unavailable */
    }

    doc.addEventListener('keydown', onKeydown);
    doc.addEventListener('focusin', function (event) {
      var ring = doc.querySelector('.td-kbd-focus');
      if (ring && event.target && !ring.contains(event.target)) {
        ring.classList.remove('td-kbd-focus');
      }
    });

    return Object.freeze({
      guarded: guarded,
      jumpHeading: jumpHeading,
      onKeydown: onKeydown,
      pageTarget: pageTarget,
      setZen: setZen,
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
