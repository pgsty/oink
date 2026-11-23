// Shared scheduling and reader controls for Mermaid and local PlantUML.
// Engines stay separate, pinned assets; all rendering runs serially on the main thread.
(function () {
  'use strict';
  const dialog = document.querySelector('[data-td-diagram-zoom-dialog]');
  if (!dialog) return;
  const labels = JSON.parse(dialog.querySelector('[data-td-diagram-labels]').textContent);
  const entries = [];
  let queue = Promise.resolve();
  let printing = false;
  let frame = 0;
  const mode = () => document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  const hasBox = block => {
    const rect = block.getBoundingClientRect();
    return block.getClientRects().length > 0 && rect.width > 0 && rect.height > 0 &&
      getComputedStyle(block).visibility !== 'hidden';
  };
  const nearby = block => {
    const rect = block.getBoundingClientRect();
    return hasBox(block) && rect.bottom >= -320 && rect.top <= innerHeight + 320;
  };
  const state = (entry, value) => {
    entry.block.setAttribute('data-td-diagram-state', value);
    if (entry.kind === 'plantuml') entry.block.setAttribute('data-td-plantuml-state', value);
  };
  function copy(source, status) {
    status.textContent = '';
    window.OinkClipboard.writeText(source).then(
      () => { status.textContent = labels.copied; },
      () => { status.textContent = labels.copyError; },
    );
  }
  function button(text, action) {
    const node = document.createElement('button');
    node.type = 'button';
    node.className = 'td-diagram__action';
    node.textContent = text;
    node.addEventListener('click', action);
    return node;
  }
  function release(result) {
    if (!result) return;
    result.dispose?.();
    if (result.snapshot) URL.revokeObjectURL(result.snapshot);
  }
  function schedule(entry) {
    const theme = mode();
    if (printing || entry.error || !hasBox(entry.block) ||
        (!nearby(entry.block) && openEntry !== entry) ||
        entry.theme === theme || entry.requested === theme) return;
    entry.requested = theme;
    const revision = ++entry.revision;
    state(entry, 'pending');
    queue = queue.then(async () => {
      // A queued job may have been superseded, scrolled away or hidden.
      if (entry.revision !== revision) return;
      if (printing || mode() !== theme || !hasBox(entry.block) ||
          (!nearby(entry.block) && openEntry !== entry)) {
        entry.requested = null;
        state(entry, entry.result ? 'rendered' : 'idle');
        return;
      }
      let result;
      try {
        await new Promise(resolve => setTimeout(resolve, 0));
        result = await entry.render(entry.source, theme === 'dark');
        if (entry.revision !== revision || mode() !== theme || printing || !hasBox(entry.block)) {
          release(result);
          if (entry.revision === revision) {
            entry.requested = null;
            state(entry, entry.result ? 'rendered' : 'idle');
            wake();
          }
          return;
        }
        const previous = entry.result;
        entry.stage.replaceChildren(result.node);
        result.bind?.(entry.stage);
        entry.result = result;
        entry.theme = theme;
        entry.requested = null;
        entry.block.dataset.tdDiagramRendered = 'true';
        entry.block.dataset.tdDiagramTheme = theme;
        if (entry.kind === 'plantuml') entry.block.setAttribute('data-td-plantuml-theme', theme);
        if (!previous && !entry.sourceTouched) entry.details.open = false;
        state(entry, 'rendered');
        if (openEntry === entry && dialog.open) paint(entry, true);
        release(previous);
      } catch (error) {
        release(result);
        if (entry.revision !== revision) return;
        entry.requested = null;
        if (mode() !== theme) { wake(); return; }
        entry.error = error;
        entry.details.open = true;
        entry.status.textContent = labels.error;
        entry.status.setAttribute('role', 'alert');
        state(entry, 'error');
        if (openEntry === entry) showSource(true);
        console.warn(entry.kind + ':', error);
      }
    }).catch(error => console.warn('Diagram:', error));
  }
  function wake() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      entries.forEach(schedule);
    });
  }
  const intersection = typeof IntersectionObserver === 'function'
    ? new IntersectionObserver(wake, { rootMargin: '320px' }) : null;
  const resize = typeof ResizeObserver === 'function' ? new ResizeObserver(wake) : null;
  const visibility = new MutationObserver(wake);
  const ancestors = new WeakSet();
  function register(entry) {
    Object.assign(entry, { revision: 0, requested: null, theme: null });
    entry.block.classList.add('td-diagram');
    entry.pre.tabIndex = 0;
    entry.details = document.createElement('details');
    entry.details.className = 'td-diagram__source';
    entry.details.open = true;
    // Do not collapse source that a reader is using while an engine loads.
    entry.details.addEventListener('focusin', () => { entry.sourceTouched = true; });
    const summary = document.createElement('summary');
    summary.textContent = labels.source;
    summary.addEventListener('click', () => { entry.sourceTouched = true; });
    entry.status = document.createElement('span');
    entry.status.className = 'td-diagram__status';
    entry.status.setAttribute('role', 'status');
    entry.details.append(summary, button(labels.copy, () => copy(entry.source, entry.status)), entry.pre);
    entry.block.append(entry.details, entry.status);
    let expand = entry.block.querySelector('[data-td-diagram-expand]');
    if (!expand) {
      expand = button(labels.expand, () => open(entry, expand));
      expand.className = 'td-diagram__expand';
      expand.dataset.tdDiagramExpand = '';
      expand.setAttribute('aria-haspopup', 'dialog');
      const icon = document.createElement('i');
      icon.className = 'fa-solid fa-up-right-and-down-left-from-center';
      icon.setAttribute('aria-hidden', 'true');
      const text = document.createElement('span');
      text.className = 'visually-hidden';
      text.textContent = labels.expand;
      expand.replaceChildren(icon, text);
      entry.block.append(expand);
    } else expand.addEventListener('click', () => open(entry, expand));
    expand.hidden = typeof dialog.showModal !== 'function';
    state(entry, 'idle');
    entries.push(entry);
    intersection?.observe(entry.block);
    resize?.observe(entry.block);
    // Watch only ancestors of diagrams, never every mutation in rendered SVG.
    // This also recovers visibility:hidden, closed details and zero-width panels.
    for (let node = entry.block.parentElement; node; node = node.parentElement) {
      if (ancestors.has(node)) continue;
      ancestors.add(node);
      visibility.observe(node, { attributes: true, attributeFilter: ['hidden', 'open', 'class', 'style'] });
    }
    wake();
  }
  new MutationObserver(() => {
    entries.forEach(entry => {
      if (entry.requested && entry.requested !== mode()) {
        ++entry.revision;
        entry.requested = null;
      }
    });
    wake();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });
  // Scroll is also the no-IntersectionObserver fallback and handles layout shifts.
  addEventListener('scroll', wake, { passive: true, capture: true });
  addEventListener('resize', wake, { passive: true });
  document.addEventListener('toggle', wake, true);
  document.addEventListener('td:tab-shown', wake);
  let suppressRestoreFocus = false;
  function beginPrint() {
    if (printing) return;
    printing = true;
    if (dialog.open) {
      suppressRestoreFocus = true;
      dialog.close();
    }
    entries.forEach(entry => {
      entry.printOpen = entry.details.open;
      // Dark Mermaid colors assume a dark canvas. Source is ready synchronously
      // and remains legible even when the browser omits print backgrounds.
      if (!entry.result || (entry.kind === 'mermaid' && entry.theme === 'dark')) entry.details.open = true;
    });
  }
  function endPrint() {
    if (!printing) return;
    printing = false;
    entries.forEach(entry => { entry.details.open = entry.printOpen ?? entry.details.open; });
    wake();
  }
  addEventListener('beforeprint', beginPrint);
  addEventListener('afterprint', endPrint);
  window.matchMedia('print').addEventListener('change', event => event.matches ? beginPrint() : endPrint());
  addEventListener('pagehide', event => {
    if (!event.persisted) entries.forEach(entry => release(entry.result));
  });

  // Serialize a self-contained snapshot. Mermaid labels inherit page CSS, so
  // freeze relevant computed values before detaching them. PlantUML already
  // emits its styling; its parsed document stays detached from the live DOM.
  function snapshot(entry) {
    if (entry.result.snapshot) return entry.result.snapshot;
    const result = entry.result;
    const live = result.node.localName === 'svg' ? result.node : null;
    const svg = live ? live.cloneNode(true)
      : new DOMParser().parseFromString(result.svg, 'image/svg+xml').documentElement;
    if (svg.localName !== 'svg' || svg.querySelector('parsererror')) throw new Error('Invalid SVG');
    if (live) {
      const originals = [live, ...live.querySelectorAll('*')];
      [svg, ...svg.querySelectorAll('*')].forEach((node, index) => {
        const computed = getComputedStyle(originals[index]);
        for (const key of ['color', 'fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-dasharray',
          'font-family', 'font-size', 'font-weight', 'font-style', 'line-height', 'text-align',
          'background-color', 'white-space', 'word-break', 'text-decoration']) {
          node.style?.setProperty(key, computed.getPropertyValue(key));
        }
      });
    }
    svg.querySelectorAll('script, iframe, object, embed, link, audio, video, animate, animateTransform, set').forEach(node => node.remove());
    const localURL = value => value.replace(/url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)/gi, (_, quoted, single, bare) => {
      const url = (quoted ?? single ?? bare).trim();
      if (url.startsWith('#')) return `url(${url})`;
      const parsed = new URL(url, document.baseURI);
      if (parsed.hash && parsed.href.split('#')[0] === document.URL.split('#')[0]) return `url(${parsed.hash})`;
      throw new Error('SVG depends on an external resource');
    });
    for (const node of [svg, ...svg.querySelectorAll('*')]) {
      for (const attr of [...node.attributes]) {
        if (/^on/i.test(attr.name) || attr.name === 'xml:base' || (node.localName === 'a' && /href$/.test(attr.name))) {
          node.removeAttributeNode(attr);
        } else if (attr.localName === 'srcset' || attr.localName === 'poster') {
          throw new Error('SVG depends on an external resource');
        } else if (/^(href|src)$/.test(attr.localName) && attr.value &&
            !attr.value.startsWith('#') && !/^data:image\/(png|jpeg|gif|webp);base64,/i.test(attr.value)) {
          throw new Error('SVG depends on an external resource');
        } else if (/url\(/i.test(attr.value)) attr.value = localURL(attr.value);
      }
      if (node.localName === 'style') {
        if (/@import|\\/i.test(node.textContent)) throw new Error('SVG imports an external stylesheet');
        node.textContent = localURL(node.textContent);
      }
    }
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('width', result.width);
    svg.setAttribute('height', result.height);
    svg.style.maxWidth = 'none';
    svg.style.backgroundColor = getComputedStyle(entry.block).backgroundColor === 'rgba(0, 0, 0, 0)'
      ? getComputedStyle(document.body).backgroundColor : getComputedStyle(entry.block).backgroundColor;
    const serialized = new XMLSerializer().serializeToString(svg);
    const url = URL.createObjectURL(new Blob([serialized], { type: 'image/svg+xml;charset=utf-8' }));
    result.snapshot = url;
    return url;
  }

  const viewport = dialog.querySelector('[data-td-diagram-zoom-viewport]');
  const canvas = dialog.querySelector('[data-td-diagram-zoom-canvas]');
  const sourcePane = dialog.querySelector('[data-td-diagram-zoom-source]');
  const sourceToggle = dialog.querySelector('[data-td-diagram-source-toggle]');
  const status = dialog.querySelector('[data-td-diagram-status]');
  const closeButton = dialog.querySelector('[data-td-diagram-zoom-close]');
  const download = dialog.querySelector('[data-td-diagram-download]');
  const zoomControls = [...dialog.querySelectorAll('[data-td-diagram-zoom-in], [data-td-diagram-zoom-out], [data-td-diagram-zoom-reset]')];
  let openEntry = null;
  let origin = null;
  let paintRevision = 0;
  let minScale = 0.2;
  const view = { scale: 1, x: 0, y: 0 };
  const pointers = new Map();
  let pinchDistance = 0;
  function applyView() {
    canvas.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`;
  }
  function fit(initial = false) {
    if (!openEntry?.result) return;
    const { width, height } = openEntry.result;
    const frame = viewport.getBoundingClientRect();
    const fitted = Math.min(1, Math.max(1, frame.width - 24) / width, Math.max(1, frame.height - 24) / height);
    minScale = Math.min(0.2, fitted);
    view.scale = initial && fitted < 0.5 ? 1 : fitted;
    view.x = Math.max(12, (frame.width - width * view.scale) / 2);
    view.y = Math.max(12, (frame.height - height * view.scale) / 2);
    applyView();
  }
  function zoomBy(factor, x = viewport.clientWidth / 2, y = viewport.clientHeight / 2) {
    const next = Math.min(8, Math.max(minScale, view.scale * factor));
    const ratio = next / view.scale;
    view.x = x - ratio * (x - view.x);
    view.y = y - ratio * (y - view.y);
    view.scale = next;
    applyView();
  }
  function showSource(value) {
    viewport.hidden = value;
    sourcePane.hidden = !value;
    sourceToggle.setAttribute('aria-pressed', String(value));
    zoomControls.forEach(control => { control.disabled = value || !openEntry?.result; });
  }
  async function paint(entry, keep = false) {
    const revision = ++paintRevision;
    download.disabled = !entry.result;
    if (!entry.result) { showSource(true); return; }
    try {
      const img = new Image();
      img.alt = entry.kind === 'plantuml' ? 'PlantUML' : 'Mermaid';
      // Reuse the isolated PlantUML image. Mermaid gets a styled snapshot;
      // neither viewer invokes an engine or inserts untrusted PlantUML markup.
      img.src = entry.kind === 'plantuml' ? entry.result.node.src : snapshot(entry);
      await img.decode();
      if (!dialog.open || openEntry !== entry || revision !== paintRevision) return;
      img.width = entry.result.width;
      img.height = entry.result.height;
      canvas.replaceChildren(img);
      if (!keep) { showSource(false); fit(true); }
      else zoomControls.forEach(control => { control.disabled = viewport.hidden; });
    } catch (error) {
      if (openEntry !== entry || revision !== paintRevision) return;
      status.textContent = labels.error;
      showSource(true);
    }
  }
  window.OinkSurfaceCoordinator?.register('diagram-zoom', restoreFocus => {
    if (!dialog.open) return;
    suppressRestoreFocus = restoreFocus === false;
    dialog.close();
  });
  function open(entry, trigger) {
    window.OinkSurfaceCoordinator?.closeOthers('diagram-zoom');
    origin = trigger;
    openEntry = entry;
    status.textContent = '';
    sourcePane.querySelector('code').textContent = entry.source;
    canvas.replaceChildren();
    dialog.showModal();
    showSource(!entry.result);
    paint(entry);
    schedule(entry);
    closeButton.focus({ preventScroll: true });
  }
  sourceToggle.addEventListener('click', () => {
    showSource(sourcePane.hidden);
    if (!viewport.hidden) fit();
  });
  dialog.querySelector('[data-td-diagram-copy]').addEventListener('click', () => copy(openEntry.source, status));
  download.addEventListener('click', () => {
    status.textContent = '';
    try {
      if (!openEntry?.result) throw new Error('No rendered SVG');
      const anchor = document.createElement('a');
      anchor.href = snapshot(openEntry);
      anchor.download = `${openEntry.kind}-${entries.indexOf(openEntry) + 1}.svg`;
      dialog.append(anchor);
      try { anchor.click(); } finally { anchor.remove(); }
      status.textContent = labels.downloadStarted;
    } catch (error) { status.textContent = labels.downloadError; }
  });
  dialog.querySelector('[data-td-diagram-zoom-in]').addEventListener('click', () => zoomBy(1.25));
  dialog.querySelector('[data-td-diagram-zoom-out]').addEventListener('click', () => zoomBy(1 / 1.25));
  dialog.querySelector('[data-td-diagram-zoom-reset]').addEventListener('click', () => fit());
  closeButton.addEventListener('click', () => dialog.close());
  viewport.addEventListener('dblclick', () => fit());
  addEventListener('resize', () => { if (dialog.open && !viewport.hidden) fit(); });
  viewport.addEventListener('wheel', event => {
    event.preventDefault();
    const rect = viewport.getBoundingClientRect();
    zoomBy(event.deltaY < 0 ? 1.15 : 1 / 1.15, event.clientX - rect.left, event.clientY - rect.top);
  }, { passive: false });
  function spread() {
    const [a, b] = [...pointers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }
  viewport.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 2) pinchDistance = spread();
    viewport.setPointerCapture(event.pointerId);
    viewport.classList.add('is-grabbing');
  });
  viewport.addEventListener('pointermove', event => {
    const previous = pointers.get(event.pointerId);
    if (!previous) return;
    const dx = event.clientX - previous.x;
    const dy = event.clientY - previous.y;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    view.x += dx / pointers.size;
    view.y += dy / pointers.size;
    if (pointers.size === 2 && pinchDistance > 0) {
      const distance = spread();
      const [a, b] = [...pointers.values()];
      const rect = viewport.getBoundingClientRect();
      if (distance) zoomBy(distance / pinchDistance, (a.x + b.x) / 2 - rect.left, (a.y + b.y) / 2 - rect.top);
      pinchDistance = distance;
    }
    applyView();
  });
  function endPointer(event) {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinchDistance = 0;
    if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
    if (!pointers.size) viewport.classList.remove('is-grabbing');
  }
  for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) viewport.addEventListener(name, endPointer);
  dialog.addEventListener('keydown', event => {
    if (!dialog.open || viewport.hidden || event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
    const moves = { ArrowLeft: [48, 0], ArrowRight: [-48, 0], ArrowUp: [0, 48], ArrowDown: [0, -48] };
    if (moves[event.key]) {
      view.x += moves[event.key][0]; view.y += moves[event.key][1]; applyView();
    } else if (['+', '='].includes(event.key)) zoomBy(1.25);
    else if (['-', '_'].includes(event.key)) zoomBy(1 / 1.25);
    else if (event.key === '0') fit();
    else return;
    event.preventDefault();
  });
  let backdropPressed = false;
  dialog.addEventListener('pointerdown', event => { backdropPressed = event.target === dialog; });
  dialog.addEventListener('click', event => {
    if (event.target === dialog && backdropPressed) dialog.close();
    backdropPressed = false;
  });
  dialog.addEventListener('close', () => {
    if (dialog.open) return;
    ++paintRevision;
    canvas.replaceChildren();
    openEntry = null;
    for (const id of pointers.keys()) {
      if (viewport.hasPointerCapture(id)) viewport.releasePointerCapture(id);
    }
    pointers.clear();
    pinchDistance = 0;
    viewport.classList.remove('is-grabbing');
    const shouldRestore = !suppressRestoreFocus;
    suppressRestoreFocus = false;
    const active = document.activeElement;
    if (shouldRestore && origin?.isConnected && (!active || active === document.body || active === dialog || dialog.contains(active))) {
      origin.focus({ preventScroll: true });
    }
    origin = null;
  });
  window.OinkDiagrams = { register };
})();
