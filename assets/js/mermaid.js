{{- /* Mermaid runtime.

     Replaces Docsy's `startOnLoad: true` passthrough, which had three
     consequences this file exists to remove:

       * a diagram inside a `display: none` tab panel measured every label as
         zero, and Mermaid baked the resulting `max-width: 16px` into the SVG
         permanently -- revealing the panel never recovered it;
       * a colour-scheme change reloaded the whole page, because the source
         was gone once Mermaid had consumed the `<pre>` that held it;
       * a diagram wider than the column was silently scaled down (Mermaid's
         `useMaxWidth`, not overflow), so `overflow-x` never offered a way
         back and a phone-sized reader was left with 35% type.

     The fence now keeps its source as JSON beside an empty stage, so this
     file owns when a diagram is drawn, redraws it on demand, and can render a
     second copy at natural size into the zoom dialog. */ -}}
(function () {
  'use strict';

  var blocks = Array.prototype.slice.call(
    document.querySelectorAll('[data-td-diagram]'),
  );
  if (!blocks.length) {
    if (window.mermaid) window.mermaid.initialize({ startOnLoad: false });
    return;
  }

  var LABELS = {{ (dict "error" (T "ui_diagram_error")) | jsonify | safeJS }};
  var PARAMS = {{ with .Site.Params.mermaid }}{{ . | jsonify | safeJS }}{{ else }}{}{{ end }};

  // Site params are stored with lowercase keys; look the correct casing up
  // from Mermaid's own default config.
  function norm(defaultConfig, params) {
    var result = {};
    for (var key in defaultConfig) {
      var lower = key.toLowerCase();
      if (
        !Object.prototype.hasOwnProperty.call(defaultConfig, key) ||
        !Object.prototype.hasOwnProperty.call(params, lower)
      ) {
        continue;
      }
      if (defaultConfig[key] !== null && typeof defaultConfig[key] === 'object') {
        result[key] = norm(defaultConfig[key], params[lower]);
      } else {
        result[key] = params[lower];
      }
    }
    return result;
  }

  function settings() {
    var api = window.mermaid.mermaidAPI;
    var value = norm((api && api.defaultConfig) || {}, PARAMS);
    value.startOnLoad = false;
    if (document.documentElement.getAttribute('data-bs-theme') === 'dark') {
      value.theme = 'dark';
    }
    return value;
  }

  var seq = 0;

  // Mermaid 11 re-initializes cleanly, so a theme change is a re-render rather
  // than the page reload the old runtime fell back to.
  function drawInto(target, source, isCurrent) {
    var id = 'td-mermaid-' + (seq += 1);
    return Promise.resolve()
      .then(function () {
        return window.mermaid.render(id, source);
      })
      .then(function (result) {
        // Two renders of one stage can be in flight -- a colour-scheme change
        // during the first. Whichever was asked for last owns the stage, no
        // matter which promise settles first.
        if (isCurrent && !isCurrent()) return null;
        target.innerHTML = result.svg;
        if (typeof result.bindFunctions === 'function') {
          result.bindFunctions(target);
        }
        return target.querySelector('svg');
      })
      .catch(function (error) {
        // A failed render can leave Mermaid's measuring container behind.
        var stray =
          document.getElementById('d' + id) || document.getElementById(id);
        if (stray && stray.parentNode) stray.parentNode.removeChild(stray);
        throw error;
      });
  }

  var entries = [];
  blocks.forEach(function (block) {
    var stage = block.querySelector('[data-td-diagram-stage]');
    var holder = block.querySelector('[data-td-diagram-source]');
    var source = null;
    if (holder) {
      try {
        source = JSON.parse(holder.textContent);
      } catch (error) {
        source = null;
      }
    }
    if (!stage || typeof source !== 'string' || !source) return;
    entries.push({
      block: block,
      stage: stage,
      source: source,
      drawn: false,
      bound: false,
    });
  });
  if (!entries.length) return;

  function showSource(entry) {
    var block = document.createElement('pre');
    var code = document.createElement('code');
    block.className = 'td-mermaid-source';
    code.className = 'language-mermaid';
    code.textContent = entry.source;
    block.appendChild(code);
    entry.stage.replaceChildren(block);
  }

  // The vendored library can fail to arrive. Falling back to the source keeps
  // the diagram readable as text instead of leaving a blank figure behind.
  if (!window.mermaid) {
    entries.forEach(showSource);
    return;
  }

  function hasBox(element) {
    return element.getClientRects().length > 0;
  }

  function fail(entry, error) {
    var box = document.createElement('pre');
    box.className = 'td-diagram__error';
    box.setAttribute('role', 'alert');
    box.textContent =
      LABELS.error +
      '\n\n' +
      ((error && error.message) || String(error)) +
      '\n\n' +
      entry.source;
    entry.stage.replaceChildren(box);
    var button = entry.block.querySelector('[data-td-diagram-expand]');
    if (button) button.hidden = true;
  }

  function render(entry) {
    entry.drawn = true;
    var token = (entry.token || 0) + 1;
    entry.token = token;
    function current() {
      return entry.token === token;
    }
    // Re-rendering empties the stage for a frame. Holding the height it
    // already had keeps a colour-scheme change from collapsing the page and
    // taking the reader's scroll position with it.
    var height = entry.stage.getBoundingClientRect().height;
    if (height > 0) entry.stage.style.minBlockSize = height + 'px';
    function release() {
      entry.stage.style.minBlockSize = '';
    }
    return drawInto(entry.stage, entry.source, current).then(
      function () {
        if (!current()) return;
        release();
        reveal(entry);
      },
      function (error) {
        if (!current()) return;
        release();
        fail(entry, error);
      },
    );
  }

  function schedule(entry) {
    if (hasBox(entry.stage)) {
      render(entry);
      return;
    }
    // The stage has no box: it sits in a `display: none` subtree, where every
    // text measurement returns zero. Wait for it to acquire one -- the same
    // recovery this theme already relies on for ECharts.
    if (typeof ResizeObserver !== 'function') {
      render(entry);
      return;
    }
    var observer = new ResizeObserver(function () {
      if (!hasBox(entry.stage)) return;
      observer.disconnect();
      render(entry);
    });
    observer.observe(entry.stage);
  }

  /* ---------------------------------------------------------------- zoom */

  var dialog = document.querySelector('[data-td-diagram-zoom-dialog]');
  var viewport = dialog && dialog.querySelector('[data-td-diagram-zoom-viewport]');
  var canvas = dialog && dialog.querySelector('[data-td-diagram-zoom-canvas]');
  var closeButton = dialog && dialog.querySelector('[data-td-diagram-zoom-close]');
  var usable = !!(
    dialog &&
    viewport &&
    canvas &&
    closeButton &&
    typeof window.HTMLDialogElement !== 'undefined' &&
    typeof dialog.showModal === 'function'
  );

  function reveal(entry) {
    if (!usable) return;
    var button = entry.block.querySelector('[data-td-diagram-expand]');
    if (!button) return;
    if (!entry.bound) {
      entry.bound = true;
      button.addEventListener('click', function () {
        openDialog(entry, button);
      });
    }
    button.hidden = false;
  }

  var MIN_SCALE = 0.2;
  var MAX_SCALE = 8;
  // Zooming out stops at MIN_SCALE, except that a diagram too big to fit even
  // there must still be reachable whole -- so the floor drops to whatever it
  // takes to see all of it.
  var minScale = MIN_SCALE;
  var view = { scale: 1, x: 0, y: 0 };
  // Where "reset" goes back to: the whole diagram, centred, never enlarged
  // past its natural size. A diagram that already fits opens at 1:1.
  var home = { scale: 1, x: 0, y: 0 };
  var origin = null;
  var openEntry = null;

  function applyView() {
    canvas.style.transform =
      'translate(' + view.x + 'px, ' + view.y + 'px) scale(' + view.scale + ')';
  }

  function fit(svg) {
    home = { scale: 1, x: 0, y: 0 };
    minScale = MIN_SCALE;
    if (svg) {
      var frame = viewport.getBoundingClientRect();
      var width = svg.width && svg.width.baseVal ? svg.width.baseVal.value : 0;
      var height = svg.height && svg.height.baseVal ? svg.height.baseVal.value : 0;
      if (width > 0 && height > 0 && frame.width > 0 && frame.height > 0) {
        var fitted = Math.min(1, frame.width / width, frame.height / height);
        minScale = Math.min(MIN_SCALE, fitted);
        // Fitting a wide diagram into a phone means opening it at the same
        // unreadable scale the page already showed. Below half size, open at
        // the diagram's own size instead and let panning do the work: the
        // point of enlarging is to be able to read the labels.
        var scale = fitted >= 0.5 ? fitted : 1;
        home = {
          scale: scale,
          x: width * scale <= frame.width ? (frame.width - width * scale) / 2 : 0,
          y: height * scale <= frame.height ? (frame.height - height * scale) / 2 : 0,
        };
      }
    }
    resetView();
  }

  function resetView() {
    view.scale = home.scale;
    view.x = home.x;
    view.y = home.y;
    applyView();
  }

  function zoomBy(factor, cx, cy) {
    var next = Math.min(MAX_SCALE, Math.max(minScale, view.scale * factor));
    if (next === view.scale) return;
    if (typeof cx === 'number' && typeof cy === 'number') {
      // Keep the point under the pointer where it is.
      var ratio = next / view.scale;
      view.x = cx - ratio * (cx - view.x);
      view.y = cy - ratio * (cy - view.y);
    }
    view.scale = next;
    applyView();
  }

  function naturalSize(svg) {
    if (!svg) return;
    // The page copy carries `width="100%"` and a `max-width` that fits the
    // column. In the dialog the diagram is finally allowed its own size.
    var box = svg.viewBox && svg.viewBox.baseVal;
    if (box && box.width && box.height) {
      svg.setAttribute('width', String(box.width));
      svg.setAttribute('height', String(box.height));
    }
    svg.style.maxWidth = 'none';
    svg.style.maxHeight = 'none';
  }

  function paint(entry) {
    canvas.replaceChildren();
    function current() {
      return openEntry === entry && dialog.open;
    }
    return drawInto(canvas, entry.source, current).then(function (svg) {
      if (!svg) return null;
      naturalSize(svg);
      fit(svg);
      return svg;
    }, function (error) {
      if (!current()) return;
      var box = document.createElement('pre');
      box.className = 'td-diagram__error';
      box.setAttribute('role', 'alert');
      box.textContent =
        LABELS.error + '\n\n' + ((error && error.message) || String(error));
      canvas.replaceChildren(box);
    });
  }

  function openDialog(entry, button) {
    if (!usable) return;
    origin = button;
    openEntry = entry;
    home = { scale: 1, x: 0, y: 0 };
    resetView();
    dialog.showModal();
    paint(entry);
    closeButton.focus({ preventScroll: true });
  }

  if (usable) {
    var pointers = new Map();
    var pinchDistance = 0;

    function centroid() {
      var xs = 0;
      var ys = 0;
      pointers.forEach(function (point) {
        xs += point.x;
        ys += point.y;
      });
      return { x: xs / pointers.size, y: ys / pointers.size };
    }

    function spread() {
      var list = Array.from(pointers.values());
      return Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y);
    }

    viewport.addEventListener('pointerdown', function (event) {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (pointers.size === 2) pinchDistance = spread();
      viewport.setPointerCapture(event.pointerId);
      viewport.classList.add('is-grabbing');
    });

    viewport.addEventListener('pointermove', function (event) {
      if (!pointers.has(event.pointerId)) return;
      var previous = pointers.get(event.pointerId);
      var dx = event.clientX - previous.x;
      var dy = event.clientY - previous.y;
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (pointers.size === 1) {
        view.x += dx;
        view.y += dy;
        applyView();
        return;
      }
      if (pointers.size === 2 && pinchDistance > 0) {
        var distance = spread();
        if (!distance) return;
        var rect = viewport.getBoundingClientRect();
        var middle = centroid();
        zoomBy(distance / pinchDistance, middle.x - rect.left, middle.y - rect.top);
        pinchDistance = distance;
      }
    });

    function endPointer(event) {
      if (!pointers.has(event.pointerId)) return;
      pointers.delete(event.pointerId);
      if (pointers.size < 2) pinchDistance = 0;
      if (viewport.hasPointerCapture(event.pointerId)) {
        viewport.releasePointerCapture(event.pointerId);
      }
      if (!pointers.size) viewport.classList.remove('is-grabbing');
    }

    viewport.addEventListener('pointerup', endPointer);
    viewport.addEventListener('pointercancel', endPointer);

    viewport.addEventListener(
      'wheel',
      function (event) {
        if (!dialog.open) return;
        event.preventDefault();
        var rect = viewport.getBoundingClientRect();
        zoomBy(
          event.deltaY < 0 ? 1.15 : 1 / 1.15,
          event.clientX - rect.left,
          event.clientY - rect.top,
        );
      },
      { passive: false },
    );

    viewport.addEventListener('dblclick', resetView);

    dialog
      .querySelector('[data-td-diagram-zoom-in]')
      .addEventListener('click', function () {
        zoomBy(1.25);
      });
    dialog
      .querySelector('[data-td-diagram-zoom-out]')
      .addEventListener('click', function () {
        zoomBy(1 / 1.25);
      });
    dialog
      .querySelector('[data-td-diagram-zoom-reset]')
      .addEventListener('click', resetView);
    closeButton.addEventListener('click', function () {
      dialog.close();
    });

    dialog.addEventListener('keydown', function (event) {
      if (!dialog.open) return;
      var step = 48;
      switch (event.key) {
        case 'ArrowLeft':
          view.x += step;
          break;
        case 'ArrowRight':
          view.x -= step;
          break;
        case 'ArrowUp':
          view.y += step;
          break;
        case 'ArrowDown':
          view.y -= step;
          break;
        case '+':
        case '=':
          event.preventDefault();
          zoomBy(1.25);
          return;
        case '-':
        case '_':
          event.preventDefault();
          zoomBy(1 / 1.25);
          return;
        case '0':
          event.preventDefault();
          resetView();
          return;
        default:
          return;
      }
      event.preventDefault();
      applyView();
    });

    var backdropPressed = false;
    dialog.addEventListener('pointerdown', function (event) {
      backdropPressed = event.target === dialog;
    });
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog && backdropPressed) dialog.close();
      backdropPressed = false;
    });
    dialog.addEventListener('close', function () {
      // A queued close event can arrive after another trigger reopened it.
      if (dialog.open) return;
      canvas.replaceChildren();
      openEntry = null;
      pointers.clear();
      pinchDistance = 0;
      viewport.classList.remove('is-grabbing');
      var active = document.activeElement;
      var mayRestore =
        !active ||
        active === document.body ||
        active === document.documentElement ||
        active === dialog ||
        dialog.contains(active);
      if (origin && origin.isConnected && mayRestore) {
        origin.focus({ preventScroll: true });
      }
      origin = null;
    });
  }

  /* --------------------------------------------------------------- start */

  window.mermaid.initialize(settings());
  entries.forEach(schedule);

  new MutationObserver(function (mutations) {
    var changed = mutations.some(function (mutation) {
      return mutation.attributeName === 'data-bs-theme';
    });
    if (!changed) return;
    window.mermaid.initialize(settings());
    entries.forEach(function (entry) {
      if (entry.drawn) render(entry);
    });
    if (openEntry && dialog && dialog.open) {
      var keep = { scale: view.scale, x: view.x, y: view.y };
      paint(openEntry).then(function (svg) {
        if (!svg) return;
        // A colour change is not a reason to lose the reader's place.
        view.scale = keep.scale;
        view.x = keep.x;
        view.y = keep.y;
        applyView();
      });
    }
  }).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-bs-theme'],
  });
})();
