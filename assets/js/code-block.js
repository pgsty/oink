// Enhanced code-block Copy and progressive collapse behavior.
(function () {
  'use strict';

  const resetTimers = new WeakMap();
  const observedWidths = new WeakMap();
  const resizeObserver =
    typeof ResizeObserver === 'function'
      ? new ResizeObserver((entries) => {
          for (const entry of entries) {
            const root = entry.target.closest('[data-td-code]');
            if (!root) continue;
            const width = Math.round(entry.contentRect.width);
            if (observedWidths.get(root) === width) continue;
            observedWidths.set(root, width);
            measureCollapse(root);
          }
        })
      : null;

  const resolveRoot = (control) => {
    const target = control.getAttribute('data-td-code-target');
    return target
      ? document.getElementById(target)
      : control.closest('[data-td-code]');
  };

  const findCode = (root) => {
    if (!root) return null;
    return (
      root.querySelector('.lntable .lntd:last-child code[data-lang]') ||
      root.querySelector('code[data-lang]') ||
      root.querySelector('pre code')
    );
  };

  const normalizeCopiedText = (text) =>
    `${String(text || '').replace(/[\r\n]+$/, '')}\n`;

  const extractAll = (code) => {
    const clone = code.cloneNode(true);
    clone.querySelectorAll('.ln, .lnt').forEach((node) => node.remove());
    return normalizeCopiedText(clone.textContent);
  };

  const extractCommands = (code) => {
    const lines = Array.from(code.querySelectorAll('.line'));
    const promptLines = lines.filter((line) => line.querySelector('.gp'));
    if (!promptLines.length) {
      throw new Error('session lexer emitted no GenericPrompt tokens');
    }

    const commands = promptLines.map((line) => {
      const clone = line.cloneNode(true);
      clone
        .querySelectorAll('.ln, .lnt, .gp, .go')
        .forEach((node) => node.remove());
      return String(clone.textContent || '')
        .replace(/\r?\n$/, '')
        .replace(/^[ \t]/, '');
    });
    return normalizeCopiedText(commands.join('\n'));
  };

  const fallbackCopy = (text) => {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.inset = '-9999px auto auto -9999px';
    document.body.append(textarea);
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);
    let copied = false;
    try {
      copied = document.execCommand('copy');
    } finally {
      textarea.remove();
    }
    if (!copied) throw new Error('clipboard fallback was rejected');
  };

  const writeClipboard = async (text) => {
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (_) {
        // Permission or secure-context failures may still allow the fallback.
      }
    }
    fallbackCopy(text);
  };

  const updateCopyControl = (button, state, label) => {
    button.dataset.state = state;
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
    const icon = button.querySelector('i');
    if (icon) {
      icon.className =
        state === 'success'
          ? 'fa-solid fa-check'
          : state === 'error'
            ? 'fa-solid fa-triangle-exclamation'
            : 'fa-regular fa-copy';
    }
  };

  // A floating control (untitled block) is only visible while the block is
  // hovered / keyboard-focused or while it shows a result. Reset must not swap
  // the glyph back to "copy" in front of the reader: if nothing else keeps the
  // control visible, drop the result state first so it fades out still showing
  // the check, and restore the idle glyph once it is gone.
  const controlStaysVisible = (button) => {
    const root = resolveRoot(button);
    if (!root || !button.closest('.td-code__utilities--compact')) return true;
    if (window.matchMedia?.('(hover: none)').matches) return true;
    try {
      return root.matches(':hover') || root.matches(':has(:focus-visible)');
    } catch (_) {
      return root.matches(':hover') || root.matches(':focus-within');
    }
  };

  const resetCopyControl = (button) => {
    const timer = resetTimers.get(button);
    if (timer) window.clearTimeout(timer);
    const label = button.dataset.labelCopy || 'Copy code';
    button.disabled = false;
    if (controlStaysVisible(button)) {
      updateCopyControl(button, 'idle', label);
      return;
    }
    button.dataset.state = 'idle';
    resetTimers.set(
      button,
      window.setTimeout(() => {
        // A new copy may have started during the fade; leave its state alone.
        if (button.dataset.state === 'idle') {
          updateCopyControl(button, 'idle', label);
        }
      }, 240),
    );
  };

  const handleCopy = async (button) => {
    const root = resolveRoot(button);
    const code = findCode(root);
    if (!root || !code || button.disabled) return;

    const status = root.querySelector('[data-td-code-status]');
    button.disabled = true;
    if (status) status.textContent = '';
    try {
      const text =
        button.dataset.copyMode === 'command'
          ? extractCommands(code)
          : extractAll(code);
      await writeClipboard(text);
      const label = button.dataset.labelCopied || 'Copied';
      updateCopyControl(button, 'success', label);
      if (status) status.textContent = label;
    } catch (error) {
      const label = button.dataset.labelError || 'Copy failed';
      updateCopyControl(button, 'error', label);
      if (status) status.textContent = label;
      console.error('OINK code block: unable to copy code:', error);
    }

    resetTimers.set(
      button,
      window.setTimeout(() => resetCopyControl(button), 1500),
    );
  };

  const sourceLines = (root) => {
    const code = findCode(root);
    return code ? Array.from(code.querySelectorAll('.line')) : [];
  };

  const setCollapsedFocus = (root, collapsed) => {
    const limit = Number.parseInt(root.dataset.collapseLines || '', 10);
    if (!limit) return;
    // Keep the complete source in the accessibility tree, but do not leave
    // clipped line anchors in the keyboard tab order.
    sourceLines(root).slice(limit).forEach((line) => {
      if (collapsed) {
        line
          .querySelectorAll(
            'a[href], button, input, select, textarea, [tabindex]',
          )
          .forEach((control) => {
            if (!control.hasAttribute('data-td-code-tabindex')) {
              control.dataset.tdCodeTabindex = control.hasAttribute('tabindex')
                ? control.getAttribute('tabindex')
                : '__none__';
            }
            control.setAttribute('tabindex', '-1');
          });
        return;
      }

      line.querySelectorAll('[data-td-code-tabindex]').forEach((control) => {
        const previousTabindex = control.dataset.tdCodeTabindex;
        if (previousTabindex === '__none__') control.removeAttribute('tabindex');
        else control.setAttribute('tabindex', previousTabindex);
        delete control.dataset.tdCodeTabindex;
      });
    });
  };

  function measureCollapse(root) {
    const limit = Number.parseInt(root.dataset.collapseLines || '', 10);
    const viewport = root.querySelector('[data-td-code-viewport]');
    const button = root.querySelector('[data-td-code-expand]');
    if (!limit || !viewport || !button || root.offsetParent === null) return;

    const lines = sourceLines(root);
    if (lines.length <= limit) return;
    const line = lines[limit - 1];
    const viewportRect = viewport.getBoundingClientRect();
    const lineRect = line.getBoundingClientRect();
    // Preserve the sub-pixel boundary: rounding up exposes the next line's
    // anchor by a fraction of a pixel and leaves it as a false touch target.
    const horizontalScrollbar = Math.max(
      0,
      viewport.offsetHeight - viewport.clientHeight,
    );
    const collapsedHeight =
      lineRect.bottom - viewportRect.top + horizontalScrollbar;
    if (!Number.isFinite(collapsedHeight) || collapsedHeight <= 1) return;

    root.style.setProperty(
      '--td-code-collapsed-height',
      `${collapsedHeight}px`,
    );
    if (root.classList.contains('is-expanded')) {
      root.style.setProperty(
        '--td-code-expanded-height',
        `${viewport.scrollHeight}px`,
      );
      setCollapsedFocus(root, false);
    } else {
      root.classList.add('is-collapsible', 'td-is-collapsed');
      setCollapsedFocus(root, true);
    }
    button.hidden = false;
    resizeObserver?.observe(viewport);
  }

  const setExpanded = (root, expanded) => {
    const viewport = root.querySelector('[data-td-code-viewport]');
    const button = root.querySelector('[data-td-code-expand]');
    if (!viewport || !button || !root.classList.contains('is-collapsible')) {
      return;
    }

    const label = expanded
      ? button.dataset.labelCollapse
      : button.dataset.labelExpand;
    const text = button.querySelector('span');
    if (text && label) text.textContent = label;
    button.setAttribute('aria-expanded', String(expanded));

    if (expanded) {
      setCollapsedFocus(root, false);
      root.style.setProperty(
        '--td-code-expanded-height',
        `${viewport.scrollHeight}px`,
      );
      root.classList.remove('td-is-collapsed');
      root.classList.add('is-expanded');
    } else {
      setCollapsedFocus(root, true);
      root.style.setProperty(
        '--td-code-expanded-height',
        `${viewport.scrollHeight}px`,
      );
      // Force the current pixel height before transitioning to the line limit.
      void viewport.offsetHeight;
      root.classList.remove('is-expanded');
      root.classList.add('td-is-collapsed');
      const rect = root.getBoundingClientRect();
      if (rect.top < 0) {
        root.scrollIntoView({ block: 'start', behavior: 'auto' });
      }
    }
  };

  const expandHashTarget = () => {
    if (!window.location.hash) return;
    let id;
    try {
      id = decodeURIComponent(window.location.hash.slice(1));
    } catch (_) {
      return;
    }
    const target = document.getElementById(id);
    const root = target?.closest('[data-td-code]');
    if (root?.classList.contains('td-is-collapsed')) {
      setExpanded(root, true);
      window.requestAnimationFrame(() =>
        target.scrollIntoView({ block: 'nearest', behavior: 'auto' }),
      );
    }
  };

  const initialize = (scope = document) => {
    scope.querySelectorAll('[data-td-code]').forEach((root) => {
      measureCollapse(root);
    });
    document.querySelectorAll('[data-td-code-copy]').forEach((button) => {
      if (findCode(resolveRoot(button))) button.hidden = false;
    });
    window.requestAnimationFrame(expandHashTarget);
  };

  document.addEventListener('click', (event) => {
    const copy = event.target.closest('[data-td-code-copy]');
    if (copy) {
      handleCopy(copy);
      return;
    }
    const expand = event.target.closest('[data-td-code-expand]');
    if (expand) {
      const root = resolveRoot(expand);
      if (root) setExpanded(root, !root.classList.contains('is-expanded'));
    }
  });

  document.addEventListener('shown.bs.tab', (event) => {
    const selector = event.target.getAttribute('data-bs-target');
    if (!selector) return;
    const panel = document.querySelector(selector);
    if (panel) {
      window.requestAnimationFrame(() => {
        initialize(panel);
        expandHashTarget();
      });
    }
  });
  window.addEventListener('hashchange', () =>
    window.requestAnimationFrame(expandHashTarget),
  );

  const start = () => {
    initialize();
    document.fonts?.ready.then(() => initialize());
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
