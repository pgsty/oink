// Explicit .expand tables share one native dialog. Move nodes, never clone data.
(function () {
  'use strict';
  const dialog = document.querySelector('[data-td-table-reader]');
  if (!dialog || typeof dialog.showModal !== 'function' || dialog.hasAttribute('data-td-table-reader-ready')) return;
  const body = dialog.querySelector('[data-td-table-body]');
  const title = dialog.querySelector('.td-table-reader__title');
  const trigger = dialog.querySelector('[data-td-table-trigger]');
  const labels = JSON.parse(dialog.querySelector('[data-td-table-labels]').textContent);
  const root = document.documentElement;
  let active = null;

  // Authored references must stay meaningful when the page behind the dialog
  // becomes inert. Book captions have a separate, explicit title handoff below.
  function selfContained(wrapper) {
    return [wrapper, ...wrapper.querySelectorAll('[headers], [aria-labelledby], [aria-describedby]')].every(node =>
      ['headers', 'aria-labelledby', 'aria-describedby'].every(name =>
        (node.getAttribute(name) || '').split(/\s+/).filter(Boolean).every(id =>
          wrapper.contains(document.getElementById(id)),
        ),
      ),
    );
  }

  function restoreAttribute(node, name, value) {
    if (value === null) node.removeAttribute(name);
    else node.setAttribute(name, value);
  }

  function close(restoreFocus = true) {
    if (!active) return;
    const state = active;
    active = null; // Native close events are queued; they must not restore twice.
    const { frame, wrapper, table, button } = state;
    if (frame.isConnected) frame.appendChild(wrapper);
    else (state.article?.isConnected ? state.article : document.body).appendChild(wrapper);
    frame.style.removeProperty('block-size');
    restoreAttribute(table, 'aria-labelledby', state.labelledby);
    restoreAttribute(wrapper, 'aria-label', state.label);
    root.classList.remove('td-table-reader-open');
    if (dialog.open) dialog.close();
    wrapper.scrollLeft = state.left;
    wrapper.scrollTop = state.top;
    window.scrollTo({ left: state.x, top: state.y, behavior: 'instant' });
    if (restoreFocus) {
      const target = button.isConnected ? button : state.article?.querySelector('h1, h2');
      if (target) {
        const tabindex = target.getAttribute('tabindex');
        if (target !== button) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
        if (target !== button) restoreAttribute(target, 'tabindex', tabindex);
      }
    }
  }

  function open(frame, wrapper, table, button) {
    if (!selfContained(wrapper)) return;
    close(false);
    window.OinkSurfaceCoordinator?.closeOthers('table-reader');
    const caption = table.caption || frame.closest('.td-book-figure--tbl')?.querySelector('figcaption');
    const style = getComputedStyle(wrapper);
    active = {
      frame, wrapper, table, button,
      article: frame.closest('.td-content'),
      left: wrapper.scrollLeft, top: wrapper.scrollTop,
      x: window.scrollX, y: window.scrollY,
      labelledby: table.getAttribute('aria-labelledby'),
      label: wrapper.getAttribute('aria-label'),
    };
    try {
      // The inline frame doubles as a placeholder, preserving article geometry.
      frame.style.blockSize = `${frame.getBoundingClientRect().height}px`;
      title.textContent = caption?.textContent.trim() || labels.title;
      body.lang = wrapper.closest('[lang]')?.lang || document.documentElement.lang;
      body.dir = style.direction;
      body.style.fontSize = style.fontSize;
      body.style.lineHeight = style.lineHeight;
      if (!table.caption && !table.hasAttribute('aria-label') && !table.hasAttribute('aria-labelledby')) {
        table.setAttribute('aria-labelledby', title.id);
      }
      wrapper.setAttribute('aria-label', labels.viewport);
      dialog.toggleAttribute('data-td-table-sticky', table.tHead?.rows.length === 1);
      body.appendChild(wrapper);
      root.classList.add('td-table-reader-open');
      dialog.showModal();
      wrapper.scrollLeft = active.left;
      wrapper.scrollTop = active.top;
      title.focus({ preventScroll: true });
    } catch (_) {
      // A failed/unsupported modal must leave the original table usable.
      close();
      button.remove();
    }
  }

  for (const frame of document.querySelectorAll('[data-td-table-expand]')) {
    const wrapper = frame.querySelector(':scope > .td-table-scroll');
    const table = wrapper?.querySelector(':scope > table.expand');
    if (!table || table.querySelector('table') || !selfContained(wrapper)) continue;
    const button = trigger.content.firstElementChild.cloneNode(true);
    button.addEventListener('click', () => open(frame, wrapper, table, button));
    // Reach the action before traversing all cell links with the keyboard.
    frame.prepend(button);
  }
  dialog.setAttribute('data-td-table-reader-ready', '');
  dialog.querySelector('[data-td-table-close]').addEventListener('click', () => close());
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.addEventListener('close', () => { if (!dialog.open) close(); });
  window.OinkSurfaceCoordinator?.register('table-reader', close);
  window.addEventListener('beforeprint', () => close(false));
  window.addEventListener('pagehide', () => close(false));

  // Native modal inertness contains focus. Supplement its end points so Tab
  // never detours to browser chrome, including Shift+Tab from the static title.
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab' || !active) return;
    const stops = [...dialog.querySelectorAll('button, a[href], input, select, textarea, summary, [tabindex]')]
      .filter(node => node.tabIndex >= 0 && !node.disabled && !node.closest('[inert]') &&
        node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden');
    const first = stops[0], last = stops[stops.length - 1];
    if (!first) return;
    const current = document.activeElement;
    if (event.shiftKey && (current === first || current === title || !dialog.contains(current))) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && (current === last || !dialog.contains(current))) {
      event.preventDefault(); first.focus();
    }
  });

  dialog.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (!active || !link || event.defaultPrevented || event.button !== 0 || event.ctrlKey ||
        event.metaKey || event.shiftKey || event.altKey || link.hasAttribute('download') ||
        (link.target && link.target !== '_self')) return;
    const url = new URL(link.href, document.baseURI);
    if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search) return;
    let id;
    try { id = decodeURIComponent(url.hash.slice(1)); } catch (_) { return; }
    if (!active.wrapper.contains(document.getElementById(id))) close(false);
    // Normal fragment navigation runs after restoration, including footnotes.
  });
})();
