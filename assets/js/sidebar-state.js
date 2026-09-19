/** One committed state for OINK's tree and movable aside disclosures. */
(function () {
  'use strict';
  if (window.OinkSidebar) return;

  var records = new Map();
  var resolveReady;
  var ready = new Promise(function (resolve) { resolveReady = resolve; });

  function commit(id, expanded, options) {
    var record = records.get(id);
    if (!record || typeof expanded !== 'boolean') return false;
    var source = options && options.source;
    if (['user', 'active-path', 'responsive', 'api'].indexOf(source) < 0) source = 'api';
    // A persisted preference must not hide the reader's current location.
    var item = record.button.closest('.td-shell-tree__item');
    if (source === 'api' && item && item.classList.contains('td-active-path')) expanded = true;
    var changed = record.expanded !== expanded;
    if (!expanded && record.target.contains(document.activeElement)) record.button.focus();
    record.button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    record.target.classList.toggle('td-is-open', expanded);
    record.target.inert = !expanded;
    var label = expanded ? record.button.dataset.tdLabelCollapse : record.button.dataset.tdLabelExpand;
    if (label) record.button.setAttribute('aria-label', label);
    record.expanded = expanded;
    if (changed) document.dispatchEvent(new CustomEvent('oink:sidebar-disclosure', {
      detail: { id: id, expanded: expanded, source: source },
    }));
    return true;
  }

  var api = window.OinkSidebar = {
    ready: ready,
    isReady: false,
    setExpanded: commit,
    getState: function (id) {
      var record = records.get(id);
      return record ? { id: id, expanded: record.expanded } : null;
    },
  };

  document.querySelectorAll('[data-td-shell-tree-toggle]').forEach(function (button) {
    var owner = button.closest('#td-shell-sidebar, [data-td-shell-aside]');
    var id = button.getAttribute('aria-controls');
    var target = id && document.getElementById(id);
    if (!owner || !target || !owner.contains(target) || records.has(id)) return;
    records.set(id, { button: button, target: target, expanded: button.getAttribute('aria-expanded') === 'true' });
    commit(id, records.get(id).expanded, { source: 'responsive' });
    button.addEventListener('click', function () {
      commit(id, !records.get(id).expanded, { source: 'user' });
    });
  });

  function finish() {
    // Hydration's DOMContentLoaded listener and shell relocation finish first.
    Promise.resolve().then(function () {
      api.isReady = true;
      resolveReady(api);
      document.dispatchEvent(new CustomEvent('oink:sidebar-ready'));
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', finish, { once: true });
  else finish();
})();
