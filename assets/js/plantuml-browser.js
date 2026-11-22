// Keep generated SVG inside Blob images; never insert its markup into the live DOM.
const engineURL = {{ .engine | jsonify | safeJS }};
const vizURL = {{ .viz | jsonify | safeJS }};
let enginePromise;
let dependencyError;
function engine() {
  if (!enginePromise) {
    enginePromise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('PlantUML loading timed out')), 15000);
      Promise.all([import(vizURL), import(engineURL)]).then(resolve, reject).finally(() => clearTimeout(timer));
    }).then(([, api]) => {
      // The engine normally injects script tags for themes, sprites and stdlib.
      // This distribution contains only the engine and layout library. Refuse
      // missing resources instead of downloading code or silently losing them.
      globalThis.PLANTUML_STDLIB_LOADER = (name, ok, fail) => {
        dependencyError = new Error(`PlantUML resource is not bundled: ${name}`);
        fail(dependencyError.message);
        return true;
      };
      globalThis.PLANTUML_FILE_LOADER = (name, from, ok, fail) => {
        dependencyError = new Error(`PlantUML include is not available: ${name}`);
        fail(dependencyError.message);
      };
      return api;
    });
  }
  return enginePromise;
}

let broken = false;
async function render(source, dark) {
  const api = await engine();
  if (broken) throw new Error('PlantUML engine stopped after a timeout');
  dependencyError = null;
  const input = /^\s*@start\w+/m.test(source) ? source : `@startuml\n${source}\n@enduml`;
  const svg = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      // The callback API cannot cancel rendering. Never start another job on
      // an engine whose timed-out job might still be running.
      broken = true;
      reject(new Error('PlantUML render timed out'));
    }, 15000);
    try {
      api.renderToString(input.split(/\r\n|\r|\n/), value => {
        clearTimeout(timer);
        dependencyError ? reject(dependencyError) : resolve(value);
      }, error => { clearTimeout(timer); reject(new Error(error)); }, { dark });
    } catch (error) { clearTimeout(timer); reject(error); }
  });
  const parsed = new DOMParser().parseFromString(svg, 'image/svg+xml');
  if (parsed.documentElement.localName !== 'svg' || parsed.querySelector('parsererror')) {
    throw new Error('PlantUML returned invalid SVG');
  }
  if (parsed.querySelector('text[text-decoration="wavy underline"]') &&
      parsed.querySelector('text')?.textContent.startsWith('PlantUML version ')) {
    throw new Error('PlantUML returned a diagnostic image');
  }
  const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
  const image = new Image();
  image.alt = 'PlantUML';
  image.src = url;
  try { await image.decode(); }
  catch (error) { URL.revokeObjectURL(url); throw error; }
  return {
    node: image,
    svg,
    width: image.naturalWidth,
    height: image.naturalHeight,
    bind: stage => {
      stage.tabIndex = 0;
      stage.setAttribute('role', 'region');
      stage.setAttribute('aria-label', 'PlantUML');
    },
    dispose: () => URL.revokeObjectURL(url),
  };
}
if (window.OinkDiagrams) document.querySelectorAll('pre > code.language-plantuml').forEach(code => {
  const pre = code.parentElement;
  const block = document.createElement('figure');
  block.className = 'td-plantuml td-diagram td-diagram--plantuml';
  const stage = document.createElement('div');
  stage.className = 'td-plantuml__image td-diagram__stage';
  pre.before(block);
  block.append(stage, pre);
  window.OinkDiagrams.register({ kind: 'plantuml', block, pre, stage, source: code.textContent, render });
});
