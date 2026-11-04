// The reader and its two documents are loaded only after an explicit action.
(function () {
  'use strict';
  if (window.OinkComparePane || !window.HTMLDialogElement) return;
  const node = document.getElementById('td-compare-config');
  if (!node) return;
  const config = JSON.parse(node.textContent);
  const buttons = [...document.querySelectorAll('[data-td-compare-open]')];
  const status = document.querySelector('[data-td-compare-error]');
  let pending;
  let pendingResumeToken = null;
  function open(trigger, options) {
    if (status) status.textContent = '';
    if (!pending) pending = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = config.src;
      if (config.integrity) { script.integrity = config.integrity; script.crossOrigin = 'anonymous'; }
      script.onload = () => resolve();
      script.onerror = () => { script.remove(); pending = null; reject(new Error(config.labels.error)); };
      document.head.appendChild(script);
    });
    buttons.forEach(button => { button.disabled = true; button.setAttribute('aria-busy', 'true'); });
    return pending.then(() => {
      // A reload can start loading the reader before the user presses Back.
      // Do not turn that completed traversal into a new reader history entry.
      if (options?.resumeToken && history.state?.oinkCompareReader !== options.resumeToken) return;
      return window.OinkCompare.open(config, trigger || buttons[0], options);
    })
      .catch(error => { if (status) status.textContent = config.labels.error; throw error; })
      .finally(() => buttons.forEach(button => { button.disabled = false; button.removeAttribute('aria-busy'); }));
  }
  // A reload or a back/forward restore can land on the reader's own history
  // entry. Reopen the reader there, so Back closes it instead of doing nothing.
  function resume() {
    const token = history.state?.oinkCompareReader;
    if (!token || window.OinkCompare?.isOpen()) {
      if (!token) pendingResumeToken = null;
      return;
    }
    if (pendingResumeToken === token) return;
    pendingResumeToken = token;
    open(buttons[0], { resumeToken: token })
      .catch(() => {})
      .finally(() => {
        if (pendingResumeToken === token) pendingResumeToken = null;
      });
  }
  buttons.forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => { open(button).catch(() => {}); });
  });
  window.OinkActions?.registerExecutor('compare_translations', () => open(buttons[0]));
  // Forward traversal can restore the reader's history entry after the
  // reader itself was closed by Back. Reuse that entry without pushing one.
  window.addEventListener('popstate', () => {
    // Let the reader finish closing or processing a queued user action first.
    window.setTimeout(resume, 0);
  });
  window.addEventListener('pageshow', event => { if (event.persisted) resume(); });
  resume();
})();
