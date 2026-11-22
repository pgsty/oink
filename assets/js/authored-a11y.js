(function () {
  'use strict';

  document
    .querySelectorAll('.td-content input[type="checkbox"][disabled]')
    .forEach(function (input) {
      if (
        input.hasAttribute('aria-label') ||
        input.hasAttribute('aria-labelledby') ||
        input.getAttribute('aria-hidden') === 'true'
      )
        return;
      var item = input.closest('li');
      var label = '';
      if (item) {
        var clone = item.cloneNode(true);
        clone.querySelectorAll('ul, ol').forEach(function (sub) { sub.remove(); });
        label = clone.textContent.replace(/\s+/g, ' ').trim();
      }
      if (label) input.setAttribute('aria-label', label);
      else input.setAttribute('aria-hidden', 'true');
    });

  document
    .querySelectorAll('.td-content i[class*="fa-"], .td-content span[class*="fa-"]')
    .forEach(function (icon) {
      if (
        icon.textContent.trim() ||
        icon.hasAttribute('aria-label') ||
        icon.hasAttribute('aria-labelledby') ||
        icon.hasAttribute('title') ||
        icon.hasAttribute('aria-hidden') ||
        icon.getAttribute('role') === 'img'
      )
        return;
      icon.setAttribute('aria-hidden', 'true');
    });
})();
