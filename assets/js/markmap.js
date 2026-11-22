(function () {
  'use strict';
  const config = document.querySelector('[data-td-markmap-config]');
  if (!config) return;
  let engine;
  const loadEngine = () => (engine ??= import(JSON.parse(config.textContent).src));
  const fitLabel = {{ i18n "ui_diagram_fit" | jsonify | safeJS }};
  const detailsLabel = {{ i18n "callout_details" | jsonify | safeJS }};
  const dark = () => document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  let instanceCount = 0;
  function hasOpenModalDialog() {
    return Array.from(document.querySelectorAll('dialog[open]')).some(
      dialog => !dialog.classList.contains('td-appearance__panel') || dialog.matches(':modal'),
    );
  }

  async function enhance(code) {
    const pre = code.parentElement;
    const source = code.textContent;
    let container, map;
    const cleanup = [];
    function listen(target, type, callback, options) {
      target.addEventListener(type, callback, options);
      cleanup.push(() => target.removeEventListener(type, callback, options));
    }
    function fallback(error, focus = false) {
      cleanup.forEach(dispose => dispose());
      map?.destroy();
      container?.replaceWith(pre);
      if (focus) {
        pre.tabIndex = -1;
        pre.focus({ preventScroll: true });
      }
      console.error('Markmap:', error);
    }
    try {
      const api = await loadEngine();
      // Match upstream's whitespace normalization without interpreting HTML.
      const lines = source.split(/\r?\n/);
      const rawIndent = lines.reduce((min, line) => (
        line.trim() ? Math.min(min, line.match(/^\s*/)[0].length) : min
      ), Infinity);
      const indent = Number.isFinite(rawIndent) ? rawIndent : 0;
      const content = lines.map(line => line.slice(indent)).join('\n').trim();
      const parsed = api.parse(content, { plugins: [api.remarkMath] });
      const nodes = new Map();
      api.walkTree(parsed.root, node => {
        const links = new Map();
        function collect(inlines) {
          for (const inline of inlines) {
            if (inline.type === 'link') {
              const href = inline.url.trim();
              const labels = links.get(href) || new Set();
              labels.add(api.toPlainText(inline.children).trim() || href);
              links.set(href, labels);
            }
            if (inline.children) collect(inline.children);
          }
        }
        collect(node.content);
        nodes.set(node.id, { links, label: api.toPlainText(node.content) });
      });
      const resolved = api.resolveViewOptions({ plugins: [...api.defaultContentPlugins, api.mathContent] }, parsed.frontmatter.markmap);
      for (const warning of resolved.warnings) console.warn('Markmap:', warning);
      await document.fonts.ready;
      // Firefox's OffscreenCanvas can resolve system fonts differently from
      // SVG. Measure on a document canvas so wrapping and fit use its fonts.
      const options = { ...resolved.options, colorScheme: dark(),
        measurer: api.createCanvasMeasurer(document.createElement('canvas').getContext('2d')) };
      container = document.createElement('div');
      container.className = 'markmap';
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      const reset = document.createElement('button');
      reset.type = 'button';
      reset.className = 'td-markmap__fit';
      reset.textContent = fitLabel;
      container.append(svg, reset);
      pre.replaceWith(container);
      map = api.Markmap.create(svg, parsed.root, options);
      const surfaceId = 'markmap-note-' + (++instanceCount);
      let manual = false, frame = 0, size = '';
      const initialRect = svg.getBoundingClientRect();
      if (initialRect.width) size = initialRect.width + ':' + initialRect.height;
      function fit() {
        if (svg.getBoundingClientRect().width) {
          map.placed = false;
          map.fit();
        }
      }
      listen(reset, 'click', () => { manual = false; fit(); });
      map.zoomBehavior.on('zoom.oink', event => { if (event.sourceEvent) manual = true; });
      function resize() {
        frame = 0;
        if (window.matchMedia('print').matches) return;
        const rect = svg.getBoundingClientRect();
        const next = rect.width + ':' + rect.height;
        if (!rect.width || size === next) return;
        size = next;
        if (!manual) fit();
      }
      function schedule() { if (!frame) frame = requestAnimationFrame(resize); }
      function nodeId(element) {
        return element.closest('[data-key^="node:"]')?.getAttribute('data-key').slice(5);
      }
      function labelControls() {
        // Upstream draws links as transparent rectangles over separate text.
        // Use the parsed label, including all lines of a wrapped link, for AT.
        for (const link of svg.querySelectorAll('a')) {
          const href = link.getAttribute('href');
          const labels = nodes.get(nodeId(link))?.links.get(href);
          const label = labels ? [...labels].join(' / ') : (href || '');
          if (label && link.getAttribute('aria-label') !== label) link.setAttribute('aria-label', label);
          if (link.getAttribute('target') === '_blank' && !link.hasAttribute('rel')) {
            link.setAttribute('rel', 'noopener');
          }
        }
        for (const note of svg.querySelectorAll('[data-action="notes"]')) {
          const node = nodes.get(nodeId(note));
          const label = node?.label ? detailsLabel + ': ' + node.label : detailsLabel;
          note.setAttribute('role', 'button');
          note.setAttribute('tabindex', '0');
          note.setAttribute('aria-haspopup', 'dialog');
          note.setAttribute('aria-label', label);
        }
      }
      // Animated fold/unfold and deferred math renders populate SVG <g> nodes
      // across animation frames after `render` fires; observe childList updates.
      const svgObserver = new MutationObserver(labelControls);
      svgObserver.observe(svg, { childList: true, subtree: true });
      cleanup.push(() => svgObserver.disconnect());
      map.on('render', () => { labelControls(); if (!manual) fit(); });
      labelControls();
      let noteTrigger, noteNodeId, noteDialog;
      function liveNoteTrigger(id = noteNodeId) {
        if (id) {
          const selector = `[data-key="node:${window.CSS?.escape ? window.CSS.escape(id) : id}"] [data-action="notes"]`;
          const found = svg.querySelector(selector);
          if (found) return found;
        }
        return noteTrigger?.isConnected ? noteTrigger : null;
      }
      window.OinkSurfaceCoordinator?.register(surfaceId, restoreFocus => {
        if (!map?.openNoteId) return;
        const trigger = liveNoteTrigger(map.openNoteId);
        map.closeNotes();
        if (restoreFocus === true) trigger?.focus({ preventScroll: true });
      });
      cleanup.push(() => map?.closeNotes());
      async function openNote(event) {
        const trigger = event.target.closest('[data-action="notes"]');
        if (!trigger || (event.type === 'keydown' && !['Enter', ' '].includes(event.key))) return;
        event.preventDefault();
        event.stopPropagation();
        const id = nodeId(trigger);
        if (map.openNoteId === id) { map.closeNotes(); return; }
        window.OinkSurfaceCoordinator?.closeOthers(surfaceId);
        noteTrigger = trigger;
        noteNodeId = id;
        try {
          // Keyboard focus can start the page's smooth scroll. Finish that
          // movement before opening: the vendor closes notes on page scroll.
          trigger.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'nearest' });
          await new Promise(resolve => requestAnimationFrame(resolve));
          await map.openNotes(id);
          const dialog = map.popover?.popover?.el ||
            (document.activeElement?.classList?.contains('markmap-popover')
              ? document.activeElement
              : document.querySelector('.markmap-popover'));
          if (map.openNoteId === id && dialog?.classList?.contains('markmap-popover')) {
            noteDialog = dialog;
            const label = (liveNoteTrigger(id) || trigger).getAttribute('aria-label');
            if (label) dialog.setAttribute('aria-label', label);
          }
        } catch (error) { fallback(error, true); }
      }
      listen(svg, 'click', openNote, true);
      listen(svg, 'keydown', openNote);
      listen(document, 'keydown', event => {
        if (event.key !== 'Escape' || !map.openNoteId || hasOpenModalDialog()) return;
        const focusInside = noteDialog?.contains(event.target) || noteDialog?.contains(document.activeElement);
        const trigger = liveNoteTrigger(map.openNoteId);
        event.preventDefault();
        event.stopPropagation();
        map.closeNotes();
        if (focusInside) trigger?.focus({ preventScroll: true });
      }, true);
      if (window.ResizeObserver) {
        const observer = new ResizeObserver(schedule);
        observer.observe(container);
        cleanup.push(() => observer.disconnect());
      } else listen(window, 'resize', schedule);
      listen(document, 'td:tab-shown', schedule);
      listen(document, 'toggle', schedule, true);
      let printFocus;
      listen(window, 'beforeprint', () => {
        printFocus = noteDialog?.contains(document.activeElement) ? document.activeElement : null;
      });
      listen(window, 'afterprint', () => {
        schedule();
        if (printFocus) {
          const target = printFocus.isConnected ? printFocus : liveNoteTrigger();
          target?.focus({ preventScroll: true });
          printFocus = null;
        }
      });
      cleanup.push(() => cancelAnimationFrame(frame));
      const themeObserver = new MutationObserver(() => {
        map.applyOptions({ ...options, colorScheme: dark() });
        map.render({ animate: false });
        // Notes live under body and snapshot the map's tokens when opened.
        // Keep an already-open note in sync with the reader's appearance.
        if (noteDialog?.isConnected) {
          for (const [name, value] of Object.entries(map.currentTokens())) {
            noteDialog.style.setProperty('--' + name, value);
          }
        }
      });
      themeObserver.observe(document.documentElement,
        { attributes: true, attributeFilter: ['data-bs-theme', 'data-td-preset'] });
      cleanup.push(() => themeObserver.disconnect());
      schedule();
    } catch (error) {
      fallback(error);
    }
  }
  document.querySelectorAll('pre > code.language-markmap').forEach(enhance);
})();
