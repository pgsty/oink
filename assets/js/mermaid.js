(function () {
  'use strict';
  const config = document.querySelector('[data-td-mermaid-config]');
  if (!config || !window.OinkDiagrams) return;
  const asset = JSON.parse(config.textContent);
  const params = {{ with .Site.Params.mermaid }}{{ . | jsonify | safeJS }}{{ else }}{}{{ end }};
  let enginePromise;
  let sequence = 0;
  function engine() {
    if (!enginePromise) enginePromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = asset.src;
      if (asset.integrity) { script.integrity = asset.integrity; script.crossOrigin = 'anonymous'; }
      const timer = setTimeout(() => { script.remove(); reject(new Error('Mermaid loading timed out')); }, 15000);
      script.onload = () => {
        clearTimeout(timer);
        window.mermaid ? resolve(window.mermaid) : reject(new Error('Mermaid did not initialize'));
      };
      script.onerror = () => { clearTimeout(timer); reject(new Error('Mermaid could not be loaded')); };
      document.head.append(script);
    });
    return enginePromise;
  }
  function norm(defaults, input) {
    const result = {};
    for (const key of Object.keys(defaults)) {
      if (!Object.prototype.hasOwnProperty.call(input || {}, key.toLowerCase())) continue;
      result[key] = defaults[key] && typeof defaults[key] === 'object'
        ? norm(defaults[key], input[key.toLowerCase()]) : input[key.toLowerCase()];
    }
    return result;
  }
  async function render(source, dark) {
    const api = await engine();
    const settings = norm(api.mermaidAPI?.defaultConfig || {}, params);
    // Mermaid 12 changes all three defaults. Keep existing diagrams stable;
    // authors can opt into ELK, the new themes and looks explicitly.
    settings.layout ??= 'dagre';
    settings.theme ??= 'default';
    settings.look ??= 'classic';
    settings.startOnLoad = false;
    if (dark) {
      settings.theme = 'dark';
      settings.themeVariables = Object.assign({ edgeLabelBackground: '#404040' }, settings.themeVariables || {});
    }
    api.initialize(settings);
    const id = 'td-mermaid-' + (++sequence);
    try {
      const output = await api.render(id, source);
      const container = document.createElement('div');
      container.innerHTML = output.svg;
      const svg = container.querySelector('svg');
      if (!svg) throw new Error('Mermaid returned no SVG');
      const box = svg.viewBox.baseVal;
      return { node: svg, svg: output.svg, width: box.width || parseFloat(svg.getAttribute('width')) || 640,
        height: box.height || parseFloat(svg.getAttribute('height')) || 480, bind: output.bindFunctions };
    } finally {
      // A parser error can leave the engine's measuring container in the page.
      document.getElementById('d' + id)?.remove();
    }
  }
  document.querySelectorAll('.td-diagram--mermaid').forEach(block => {
    const source = JSON.parse(block.querySelector('[data-td-diagram-source]').textContent);
    window.OinkDiagrams.register({ kind: 'mermaid', block, source, render,
      stage: block.querySelector('[data-td-diagram-stage]'), pre: block.querySelector('pre') });
  });
})();
