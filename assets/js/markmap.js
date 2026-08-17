{{ if eq .Site.Params.markmap true }}
(function () {
  'use strict';

  // Replace each fenced markmap block's <pre> wrapper with the container the
  // markmap autoloader renders into, preserving the fence's plain text.
  var needMarkmap = false;
  Array.prototype.forEach.call(
    document.querySelectorAll('.language-markmap'),
    function (code) {
      var pre = code.parentNode;
      if (!pre || !pre.parentNode) return;
      needMarkmap = true;
      var container = document.createElement('div');
      container.className = 'markmap';
      container.textContent = pre.textContent;
      pre.parentNode.replaceChild(container, pre);
    },
  );

  if (needMarkmap) {
    window.markmap.autoLoader.renderAll();
  }
})();
{{ end }}
