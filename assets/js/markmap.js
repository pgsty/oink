(function () {
  'use strict';
  const config = document.querySelector('[data-td-markmap-config]');
  if (!config) return;
  let engine;
  const loadEngine = () => (engine ??= import(JSON.parse(config.textContent).src));
  const fitLabel = {{ i18n "ui_diagram_fit" | jsonify | safeJS }};
  const downloadLabel = {{ i18n "ui_diagram_download" | jsonify | safeJS }};
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
      function makeControl(className, iconClass, label) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'td-markmap__control ' + className;
        button.title = label;
        const icon = document.createElement('i');
        icon.className = iconClass;
        icon.setAttribute('aria-hidden', 'true');
        const text = document.createElement('span');
        text.className = 'visually-hidden';
        text.textContent = label;
        button.append(icon, text);
        return button;
      }
      const controls = document.createElement('div');
      controls.className = 'td-markmap__controls';
      const reset = makeControl('td-markmap__fit', 'fa-solid fa-compress', fitLabel);
      const download = makeControl('td-markmap__download', 'fa-solid fa-download', downloadLabel);
      controls.append(reset, download);
      container.append(svg, controls);
      pre.replaceWith(container);
      map = api.Markmap.create(svg, parsed.root, options);
      const mapIndex = ++instanceCount;
      const surfaceId = 'markmap-note-' + mapIndex;
      let manual = false, frame = 0, size = '';
      const initialRect = svg.getBoundingClientRect();
      if (initialRect.width) size = initialRect.width + ':' + initialRect.height;
      function fit() {
        if (svg.getBoundingClientRect().width) {
          map.placed = false;
          map.fit();
        }
      }
      function exportSvg() {
        const rootGroup = svg.querySelector(':scope > g');
        if (!rootGroup) return;
        const bbox = rootGroup.getBBox();
        if (!bbox.width || !bbox.height) return;
        const pad = 24;
        const width = Math.max(1, Math.ceil(bbox.width + pad * 2));
        const height = Math.max(1, Math.ceil(bbox.height + pad * 2));
        const clone = svg.cloneNode(true);
        clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        clone.setAttribute('viewBox', `${bbox.x - pad} ${bbox.y - pad} ${width} ${height}`);
        clone.setAttribute('width', String(width));
        clone.setAttribute('height', String(height));
        const cloneGroup = clone.querySelector(':scope > g');
        if (cloneGroup) cloneGroup.removeAttribute('transform');
        const tokens = map.currentTokens();
        const resolveVars = value => {
          let current = value;
          for (let pass = 0; pass < 4 && current.includes('var('); pass += 1) {
            const next = current.replace(
              /var\(\s*--([a-z0-9-]+)(?:\s*,\s*([^()]+))?\s*\)/gi,
              (match, name, fallbackValue) => tokens[name] || (fallbackValue ? fallbackValue.trim() : match),
            );
            if (next === current) break;
            current = next;
          }
          return current;
        };
        for (const [name, value] of Object.entries(tokens)) {
          if (value) clone.style.setProperty('--' + name, value);
        }
        const cloneStyle = clone.querySelector(':scope > style');
        if (cloneStyle) cloneStyle.textContent = resolveVars(cloneStyle.textContent);
        for (const node of [clone, ...clone.querySelectorAll('*')]) {
          for (const attr of [...node.attributes]) {
            if (attr.value.includes('var(')) node.setAttribute(attr.name, resolveVars(attr.value));
          }
        }
        const rawBg = tokens['mm-bg'];
        const bg = (rawBg && rawBg !== 'transparent' && rawBg !== 'rgba(0, 0, 0, 0)')
          ? rawBg
          : (getComputedStyle(document.body).backgroundColor || '#fff');
        clone.style.backgroundColor = bg;
        const fontFamily = getComputedStyle(svg).fontFamily;
        if (fontFamily) clone.style.fontFamily = fontFamily;
        const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bgRect.setAttribute('x', String(bbox.x - pad));
        bgRect.setAttribute('y', String(bbox.y - pad));
        bgRect.setAttribute('width', String(width));
        bgRect.setAttribute('height', String(height));
        bgRect.setAttribute('fill', bg);
        if (cloneGroup) clone.insertBefore(bgRect, cloneGroup);
        else clone.prepend(bgRect);
        const serialized = new XMLSerializer().serializeToString(clone);
        const url = URL.createObjectURL(new Blob([serialized], { type: 'image/svg+xml;charset=utf-8' }));
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `markmap-${mapIndex}.svg`;
        container.append(anchor);
        try { anchor.click(); } finally { anchor.remove(); }
        setTimeout(() => URL.revokeObjectURL(url), 10000);
      }
      listen(reset, 'click', () => { manual = false; fit(); });
      listen(download, 'click', exportSvg);
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
      const unregister = window.OinkSurfaceCoordinator?.register(surfaceId, restoreFocus => {
        if (!map?.openNoteId) return;
        const trigger = liveNoteTrigger(map.openNoteId);
        map.closeNotes();
        if (restoreFocus === true) trigger?.focus({ preventScroll: true });
      });
      if (unregister) cleanup.push(unregister);
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
  // The engine is a module graph of a third of a megabyte. A map on screen,
  // within a short scroll below, or anywhere above the reader is drawn at
  // once: drawing one above would move the text being read. One further down
  // keeps its source until the reader approaches, and a hidden one (a closed
  // tab or disclosure) until it is shown.
  const blocks = document.querySelectorAll('pre > code.language-markmap');
  if (typeof IntersectionObserver !== 'function') {
    blocks.forEach(enhance);
    return;
  }
  const due = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      due.unobserve(entry.target);
      const code = entry.target.querySelector(':scope > code.language-markmap');
      if (code) enhance(code);
    }
  }, { rootMargin: '1000000px 0px 320px 0px' });
  blocks.forEach(code => due.observe(code.parentElement));
})();
