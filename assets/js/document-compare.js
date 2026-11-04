// Two ordinary documents, one temporary reader. No content cloning or pair URLs.
(function () {
  'use strict';
  const geometry = window.OinkCompareScroll;
  const paneFlag = 'oink_compare_pane';
  let active = null;
  let leavingHistory = false;
  let queuedOpen = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function pageURL(value) {
    try {
      const url = new URL(value, location.href);
      if (url.origin !== location.origin || !/^https?:$/.test(url.protocol)) return null;
      url.searchParams.delete(paneFlag);
      url.hash = '';
      return url;
    } catch (_) { return null; }
  }

  function article(win) { return win.document.querySelector('#td-main-content .td-content'); }
  function headings(win) {
    return [...(article(win)?.querySelectorAll('h2[id], h3[id], h4[id], h5[id], h6[id]') || [])]
      .filter(node => node.getClientRects().length && node.getBoundingClientRect().height > 0 &&
        win.getComputedStyle(node).visibility !== 'hidden')
      .map(node => ({ id: node.id, y: node.getBoundingClientRect().top + win.scrollY }));
  }
  function maxScroll(win) { return Math.max(0, win.document.documentElement.scrollHeight - win.innerHeight); }
  function motionBehavior() {
    return matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth';
  }

  // A heading interval survives reflow when the original page becomes a pane.
  function bookmark(win) {
    const offset = win.OinkComparePane ? 24 :
      (win.document.querySelector('.td-site-header')?.getBoundingClientRect().height || 0) + 24;
    const rows = [{ id: '', y: 0 }, ...headings(win), { id: '', y: win.document.documentElement.scrollHeight }];
    const position = win.scrollY + offset;
    let index = 0;
    while (index < rows.length - 2 && rows[index + 1].y <= position) index++;
    const a = rows[index], b = rows[index + 1];
    return { before: a.id, after: b.id, fraction: geometry.clamp((position - a.y) / Math.max(1, b.y - a.y), 0, 1), top: win.scrollY < 1 };
  }
  function restore(pane, mark) {
    if (!pane.ready || !mark) return;
    const win = pane.frame.contentWindow;
    const rows = new Map(headings(win).map(row => [row.id, row.y]));
    const a = mark.before ? rows.get(mark.before) : 0;
    const b = mark.after ? rows.get(mark.after) : win.document.documentElement.scrollHeight;
    if (a === undefined || b === undefined) return;
    scroll(pane, mark.top ? 0 : a + mark.fraction * (b - a) - 24);
  }
  function scroll(pane, y, behavior = 'instant') {
    const win = pane.frame.contentWindow;
    pane.expected = geometry.clamp(y, 0, maxScroll(win));
    pane.following = behavior === 'smooth';
    win.scrollTo({ top: pane.expected, left: win.scrollX, behavior });
  }

  function close(restoreFocus = true, fromHistory = false) {
    if (!active) return;
    const state = active;
    active = null;
    state.controller.abort();
    state.panes.forEach(pane => pane.dispose?.());
    cancelAnimationFrame(state.pendingScroll);
    cancelAnimationFrame(state.pendingMeasure);
    state.dialog.close();
    state.dialog.remove();
    document.documentElement.classList.remove('td-compare-open');
    window.scrollTo({ top: state.y, left: state.x, behavior: 'instant' });
    if (restoreFocus && state.trigger?.isConnected) state.trigger.focus({ preventScroll: true });
    if (!fromHistory && history.state?.oinkCompareReader === state.token) {
      leavingHistory = true;
      history.back();
    }
  }

  // A restore belongs to one existing history token, including after a lazy
  // load or a queued open. It must never create a new entry after Back.
  function open(config, trigger, options = {}) {
    const resumeToken = options.resumeToken;
    if (resumeToken && history.state?.oinkCompareReader !== resumeToken) return;
    if (active) return;
    if (leavingHistory) {
      // An explicit close is already leaving this entry. Automatic restore
      // must not replace a user's queued reopen while that traversal finishes.
      if (!resumeToken) queuedOpen = { config, trigger, options };
      return;
    }
    const currentURL = pageURL(config.current.url);
    const targets = config.targets.map(target => ({ ...target, parsed: pageURL(target.url) }))
      .filter(target => target.parsed && target.parsed.pathname !== currentURL?.pathname);
    if (!currentURL || !targets.length) return;
    const labels = config.labels;
    const sourceMark = bookmark(window);
    window.OinkSurfaceCoordinator?.closeOthers('document-compare');
    const dialog = element('dialog', 'td-compare');
    dialog.setAttribute('data-td-compare', '');
    dialog.setAttribute('aria-labelledby', 'td-compare-title');
    const toolbar = element('div', 'td-compare__toolbar');
    const title = element('h2', 'td-compare__title', labels.title);
    title.id = 'td-compare-title'; title.tabIndex = -1;
    const syncControl = element('div', 'td-compare__sync-control');
    const syncLabel = element('label', 'td-compare__sync');
    const sync = element('input'); sync.type = 'checkbox'; sync.checked = true; sync.disabled = true;
    sync.setAttribute('data-td-compare-sync', '');
    syncLabel.append(sync, element('span', '', labels.sync));
    const syncWarning = element('span', 'td-compare__sync-warning', '!');
    syncWarning.setAttribute('role', 'img');
    syncWarning.setAttribute('tabindex', '0');
    syncWarning.hidden = true;
    const exit = element('button', 'td-compare__close');
    exit.type = 'button'; exit.setAttribute('data-td-compare-close', '');
    exit.setAttribute('aria-label', labels.close);
    exit.setAttribute('aria-keyshortcuts', 'Escape');
    exit.title = labels.close;
    exit.append(element('i', 'fa-solid fa-xmark', ''));
    syncControl.append(syncLabel, syncWarning);
    toolbar.append(title, syncControl, exit);
    const mobile = element('div', 'td-compare__mobile');
    const panesRoot = element('div', 'td-compare__panes');
    const languageMenu = element('div', 'td-language-selector td-language-selector--menu td-compare__language-menu');
    const languageTrigger = element('button', 'td-language-selector__trigger td-compare__language-trigger');
    languageTrigger.type = 'button';
    languageTrigger.setAttribute('aria-haspopup', 'listbox');
    languageTrigger.setAttribute('aria-expanded', 'false');
    languageTrigger.setAttribute('data-td-compare-language', '');
    languageTrigger.append(element('i', 'fa-solid fa-language'), element('span'));
    const languageList = element('ul', 'td-compare__language-list');
    languageList.id = `td-compare-language-${Date.now()}`;
    languageList.setAttribute('role', 'listbox');
    languageList.setAttribute('aria-label', labels.language);
    languageTrigger.setAttribute('aria-controls', languageList.id);
    const languageOptions = targets.map((target, index) => {
      const item = element('li');
      item.setAttribute('role', 'presentation');
      const option = element('button', 'td-language-selector__item', target.label);
      option.type = 'button';
      option.setAttribute('role', 'option');
      option.setAttribute('data-td-compare-language-option', String(index));
      option.setAttribute('aria-selected', String(index === 0));
      option.setAttribute('lang', target.code || '');
      option.setAttribute('dir', target.direction || 'ltr');
      item.append(option);
      languageList.append(item);
      return option;
    });
    languageMenu.append(languageTrigger, languageList);
    const controller = new AbortController();
    const signal = controller.signal;
    const state = {
      controller, dialog, trigger, x: scrollX, y: scrollY,
      token: resumeToken || `${Date.now()}-${Math.random()}`, panes: [], owner: 0,
      map: null, pendingScroll: 0, pendingMeasure: 0, syncWanted: true, targetIndex: 0,
    };
    active = state;
    const alive = () => active === state;

    function updateLanguageMenu(index) {
      const descriptor = targets[index];
      state.targetIndex = index;
      languageTrigger.querySelector('span').textContent = descriptor.label;
      languageTrigger.setAttribute('lang', descriptor.code || '');
      languageTrigger.setAttribute('dir', descriptor.direction || 'ltr');
      languageTrigger.title = `${labels.language}: ${descriptor.label}`;
      languageOptions.forEach((option, optionIndex) => {
        option.classList.toggle('active', optionIndex === index);
        option.setAttribute('aria-selected', String(optionIndex === index));
      });
    }
    function focusLanguageOption(index) {
      const safeIndex = (index + languageOptions.length) % languageOptions.length;
      languageOptions[safeIndex].focus();
    }
    let languageCloseTimer = 0;
    let suppressLanguageOpen = false;
    let pointerFocusedLanguageTrigger = false;
    let languageOpenedByActivation = false;
    function openLanguageMenu(focusIndex = null, explicit = false) {
      window.clearTimeout(languageCloseTimer);
      if (explicit) languageOpenedByActivation = true;
      languageMenu.classList.add('td-is-open');
      languageTrigger.setAttribute('aria-expanded', 'true');
      if (focusIndex !== null) focusLanguageOption(focusIndex);
    }
    function closeLanguageMenu(returnFocus = false) {
      window.clearTimeout(languageCloseTimer);
      languageOpenedByActivation = false;
      languageMenu.classList.remove('td-is-open');
      languageTrigger.setAttribute('aria-expanded', 'false');
      if (returnFocus) {
        suppressLanguageOpen = true;
        languageTrigger.focus({ preventScroll: true });
      }
    }
    function closeLanguageMenuSoon() {
      window.clearTimeout(languageCloseTimer);
      languageCloseTimer = window.setTimeout(() => closeLanguageMenu(), 140);
    }

    function follow() {
      if (!state.map || !state.map.syncable || !state.syncWanted || !alive()) return;
      const source = state.panes[state.owner], target = state.panes[1 - state.owner];
      if (!source.ready || !target.ready) return;
      scroll(target, geometry.project(state.map, source.frame.contentWindow.scrollY, state.owner), motionBehavior());
      target.mark = bookmark(target.frame.contentWindow);
    }

    function updateSyncState() {
      const map = state.map;
      const usable = Boolean(map?.syncable);
      sync.disabled = !usable;
      sync.checked = usable && state.syncWanted;
      const warning = map && (map.approximate || !map.syncable)
        ? (map.syncable ? labels.approximate : labels.unavailable)
        : '';
      syncWarning.hidden = !warning;
      syncWarning.setAttribute('aria-hidden', String(!warning));
      if (warning) {
        syncWarning.title = warning;
        syncWarning.setAttribute('aria-label', warning);
      } else {
        syncWarning.removeAttribute('title');
        syncWarning.removeAttribute('aria-label');
      }
    }

    function measure(preserve = false) {
      if (!alive() || !state.panes.every(pane => pane.ready)) return;
      if (preserve) state.panes.forEach(pane => restore(pane, pane.mark));
      const wins = state.panes.map(pane => pane.frame.contentWindow);
      state.map = geometry.create(...wins.map(win => headings(win).map(row => ({ id: row.id, y: row.y - 24 }))), ...wins.map(maxScroll));
      updateSyncState();
      follow();
    }
    function scheduleMeasure() {
      if (!alive()) return;
      cancelAnimationFrame(state.pendingMeasure);
      state.pendingMeasure = requestAnimationFrame(() => measure(true));
    }

    function load(pane, descriptor, mark) {
      pane.dispose?.();
      state.map = null; updateSyncState();
      const paneController = new AbortController();
      const paneSignal = paneController.signal;
      let observer, timeout;
      pane.ready = false;
      pane.mark = mark;
      pane.body.replaceChildren();
      pane.body.setAttribute('aria-busy', 'true');
      const frame = element('iframe', 'td-compare__frame');
      frame.title = descriptor.label;
      frame.setAttribute('data-td-compare-frame', String(pane.index));
      pane.frame = frame;
      pane.dispose = () => {
        paneController.abort(); clearTimeout(timeout); observer?.disconnect();
        pane.ready = false; frame.remove();
      };
      function fail() {
        if (!alive() || paneSignal.aborted) return;
        pane.dispose();
        pane.body.removeAttribute('aria-busy');
        const failure = element('div', 'td-compare__failure');
        failure.append(element('p', '', labels.error));
        const link = element('a', '', `${labels.open} · ${descriptor.label}`);
        link.href = descriptor.parsed.href; link.target = '_blank'; link.rel = 'noopener';
        failure.append(link); pane.body.replaceChildren(failure);
        state.map = null; updateSyncState();
      }
      frame.addEventListener('load', () => {
        if (!alive() || paneSignal.aborted) return;
        const win = frame.contentWindow;
        try {
          if (win.location.href === 'about:blank') return;
          const doc = win.document;
          if (win.location.origin !== location.origin || win.location.pathname !== descriptor.parsed.pathname ||
              !win.OinkComparePane || doc.querySelector('meta[name="oink-compare-page"]')?.content !== descriptor.parsed.pathname || !article(win)) {
            fail(); return;
          }
          clearTimeout(timeout);
          pane.ready = true;
          pane.body.removeAttribute('aria-busy');
          restore(pane, mark); pane.mark = bookmark(win);
          const own = () => {
            state.owner = pane.index;
            pane.following = false;
            pane.expected = null;
          };
          for (const type of ['wheel', 'touchstart', 'pointerdown']) {
            doc.addEventListener(type, own, { passive: true, capture: true, signal: paneSignal });
          }
          doc.addEventListener('keydown', event => {
            if (event.defaultPrevented || doc.querySelector('dialog[open]')) return;
            if (event.key === 'Escape') { event.preventDefault(); close(); }
            if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) own();
          }, { signal: paneSignal });
          win.addEventListener('scroll', () => {
            if (!alive() || !pane.ready) return;
            if (pane.following) {
              if (pane.expected !== null && Math.abs(win.scrollY - pane.expected) < 2) {
                pane.following = false;
                pane.expected = null;
              } else return;
            }
            if (pane.expected !== null && Math.abs(win.scrollY - pane.expected) < 2) {
              pane.expected = null; return;
            }
            pane.expected = null;
            pane.mark = bookmark(win);
            if (state.owner !== pane.index) return;
            cancelAnimationFrame(state.pendingScroll);
            state.pendingScroll = requestAnimationFrame(follow);
          }, { passive: true, signal: paneSignal });
          doc.addEventListener('click', event => {
            const link = event.target.closest('a[href]');
            if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || link.hasAttribute('download')) return;
            const url = new URL(link.href, win.location.href);
            url.searchParams.delete(paneFlag);
            if (!/^https?:$/.test(url.protocol)) return;
            if (url.origin === location.origin && url.pathname === win.location.pathname && url.hash) {
              let target;
              try { target = doc.getElementById(decodeURIComponent(url.hash.slice(1))); } catch (_) { return; }
              if (!target) return;
              event.preventDefault(); own();
              target.scrollIntoView({ behavior: 'instant', block: 'start' });
              // replaceState avoids child entries in the joint session history.
              win.history.replaceState(null, '', win.location.pathname + win.location.search + url.hash);
            } else if (url.origin !== location.origin || link.target === '_blank') {
              event.preventDefault(); window.open(url.href, '_blank', 'noopener');
            } else {
              event.preventDefault(); close(false, true);
              // Replace the transient reader entry, leaving the original page
              // immediately behind the destination in browser history.
              location.replace(url.href);
            }
          }, { signal: paneSignal });
          observer = new ResizeObserver(scheduleMeasure);
          observer.observe(article(win));
          doc.addEventListener('load', scheduleMeasure, { capture: true, signal: paneSignal });
          doc.addEventListener('toggle', scheduleMeasure, { capture: true, signal: paneSignal });
          doc.addEventListener('shown.bs.tab', scheduleMeasure, { signal: paneSignal });
          doc.fonts?.ready.then(() => { if (!paneSignal.aborted) scheduleMeasure(); });
          measure();
        } catch (_) { fail(); }
      }, { signal: paneSignal });
      pane.body.append(frame);
      const url = new URL(descriptor.parsed);
      url.searchParams.set(paneFlag, '1');
      // Both initial loading and language changes replace the frame entry.
      frame.contentWindow.location.replace(url.href);
      timeout = setTimeout(fail, 15000);
    }

    [config.current.label, targets[0].label].forEach((label, index) => {
      const panel = element('section', 'td-compare__pane');
      panel.setAttribute('data-td-compare-side', String(index));
      const header = element('div', 'td-compare__pane-heading');
      if (index) header.append(languageMenu);
      else header.append(element('span', '', label));
      const body = element('div', 'td-compare__body');
      panel.append(header, body); panesRoot.append(panel);
      const tab = element('button', 'td-compare__tab', label);
      tab.type = 'button'; tab.setAttribute('aria-pressed', String(index === 0));
      mobile.append(tab);
      state.panes.push({ panel, header, body, tab, index, ready: false, expected: null, following: false });
    });
    const narrow = matchMedia('(max-width: 899px)');
    // Narrow screens hide the pane headings, so the target-language menu moves
    // into the pane switcher row; wide screens keep it above its own pane.
    function updateLayout() {
      const host = narrow.matches ? mobile : state.panes[1].header;
      const focused = languageMenu.contains(document.activeElement) ? document.activeElement : null;
      const wasOpen = languageMenu.classList.contains('td-is-open');
      const wasActivated = languageOpenedByActivation;
      // Capture focus before hiding a pane, and make the destination usable
      // before restoring it. Moving a focused subtree otherwise blurs to body.
      showSide(visibleSide);
      if (languageMenu.parentNode === host) return;
      host.append(languageMenu);
      if (focused) {
        suppressLanguageOpen = true;
        focused.focus({ preventScroll: true });
        suppressLanguageOpen = false;
      }
      window.clearTimeout(languageCloseTimer);
      languageMenu.classList.toggle('td-is-open', wasOpen);
      languageTrigger.setAttribute('aria-expanded', String(wasOpen));
      languageOpenedByActivation = wasActivated;
    }
    let visibleSide = 0;
    function showSide(index) {
      visibleSide = index;
      state.panes.forEach(pane => {
        const hidden = narrow.matches && pane.index !== index;
        pane.panel.classList.toggle('td-compare__pane--hidden', hidden);
        pane.panel.inert = hidden;
        pane.panel.setAttribute('aria-hidden', String(hidden));
        pane.tab.setAttribute('aria-pressed', String(pane.index === index));
      });
    }
    state.panes.forEach(pane => pane.tab.addEventListener('click', () => showSide(pane.index), { signal }));
    narrow.addEventListener('change', () => { updateLayout(); scheduleMeasure(); }, { signal });
    window.addEventListener('resize', scheduleMeasure, { signal });
    function chooseLanguage(index) {
      const descriptor = targets[index];
      if (!descriptor || index === state.targetIndex) {
        closeLanguageMenu(true);
        return;
      }
      updateLanguageMenu(index);
      state.panes[1].tab.textContent = descriptor.label;
      const mark = state.panes[0].ready ? bookmark(state.panes[0].frame.contentWindow) : sourceMark;
      state.owner = 0;
      load(state.panes[1], descriptor, mark);
      closeLanguageMenu(true);
    }
    languageOptions.forEach((option, index) => {
      option.addEventListener('click', () => chooseLanguage(index), { signal });
    });
    languageTrigger.addEventListener('pointerdown', () => {
      pointerFocusedLanguageTrigger = true;
    }, { signal });
    languageTrigger.addEventListener('pointercancel', () => {
      pointerFocusedLanguageTrigger = false;
    }, { signal });
    languageTrigger.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      const focusedByPointer = pointerFocusedLanguageTrigger;
      pointerFocusedLanguageTrigger = false;
      if (languageMenu.classList.contains('td-is-open') && languageOpenedByActivation) closeLanguageMenu();
      else openLanguageMenu(null, focusedByPointer || !languageMenu.classList.contains('td-is-open'));
    }, { signal });
    languageTrigger.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openLanguageMenu(event.key === 'ArrowUp' ? languageOptions.length - 1 : state.targetIndex, true);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        closeLanguageMenu();
      }
    }, { signal });
    languageList.addEventListener('keydown', event => {
      const current = languageOptions.indexOf(document.activeElement);
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        focusLanguageOption(current + (event.key === 'ArrowDown' ? 1 : -1));
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault();
        focusLanguageOption(event.key === 'Home' ? 0 : languageOptions.length - 1);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        closeLanguageMenu(true);
      } else if (event.key === 'Tab') {
        closeLanguageMenu();
      }
    }, { signal });
    languageMenu.addEventListener('pointerenter', event => {
      if (event.pointerType !== 'touch') openLanguageMenu();
    }, { signal });
    languageMenu.addEventListener('pointerleave', event => {
      if (event.pointerType !== 'touch') closeLanguageMenuSoon();
    }, { signal });
    languageMenu.addEventListener('focusin', () => {
      if (suppressLanguageOpen) {
        suppressLanguageOpen = false;
        return;
      }
      if (pointerFocusedLanguageTrigger && document.activeElement === languageTrigger) return;
      openLanguageMenu();
    }, { signal });
    languageMenu.addEventListener('focusout', event => {
      if (!languageMenu.contains(event.relatedTarget)) closeLanguageMenuSoon();
    }, { signal });
    dialog.addEventListener('pointerdown', event => {
      if (!languageMenu.contains(event.target)) closeLanguageMenu();
    }, { signal });
    updateLanguageMenu(0);
    sync.addEventListener('change', () => { state.syncWanted = sync.checked; follow(); }, { signal });
    exit.addEventListener('click', () => close(), { signal });
    dialog.addEventListener('cancel', event => { event.preventDefault(); close(); }, { signal });
    dialog.addEventListener('close', () => { if (!dialog.open) close(); }, { signal });
    dialog.append(toolbar, mobile, panesRoot);
    document.body.append(dialog);
    document.documentElement.classList.add('td-compare-open');
    dialog.showModal();
    title.focus({ preventScroll: true });
    if (!resumeToken) history.pushState({ ...history.state, oinkCompareReader: state.token }, '', location.href);
    updateLayout();
    load(state.panes[0], { ...config.current, parsed: currentURL }, sourceMark);
    load(state.panes[1], targets[0], sourceMark);
  }

  window.addEventListener('popstate', () => {
    leavingHistory = false;
    if (active && history.state?.oinkCompareReader !== active.token) close(true, true);
    const next = queuedOpen;
    queuedOpen = null;
    if (next && !active) queueMicrotask(() => open(next.config, next.trigger, next.options));
  });
  window.addEventListener('beforeprint', () => close(false));
  window.addEventListener('pagehide', () => { queuedOpen = null; close(false, true); });
  window.OinkSurfaceCoordinator?.register('document-compare', close);
  window.OinkCompare = { open, close, isOpen: () => Boolean(active) };
})();
