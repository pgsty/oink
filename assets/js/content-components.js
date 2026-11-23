// Runtime for opt-in content components. Included only when a page uses one.
// The page carries this small adapter; the player and chart engines load when
// a component that needs them comes due.
(function () {
  'use strict';

  function configOf(root, selector) {
    var node = root.querySelector(selector);
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      console.error('Invalid component configuration', error);
      return null;
    }
  }

  function currentTheme() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark'
      ? 'dark'
      : 'light';
  }

  function watchTheme(callback) {
    new MutationObserver(function (mutations) {
      if (
        mutations.some(function (item) {
          return item.attributeName === 'data-bs-theme';
        })
      ) {
        callback();
      }
    }).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-bs-theme'],
    });
  }

  // The engines are large pre-built scripts. The page names them without
  // requesting them, and each is fetched once, when the first component that
  // needs it is due. A script a site already loaded itself is used as it is.
  var engines = configOf(document, '[data-td-component-engines]') || {};
  var engineRequests = {};

  function loadEngine(name, ready) {
    if (ready()) return Promise.resolve();
    if (!engineRequests[name]) {
      engineRequests[name] = new Promise(function (resolve, reject) {
        var asset = engines[name];
        if (!asset || !asset.src) {
          reject(new Error(name + ' engine is not published'));
          return;
        }
        var script = document.createElement('script');
        script.src = asset.src;
        if (asset.integrity) {
          script.integrity = asset.integrity;
          script.crossOrigin = 'anonymous';
        }
        script.onload = function () {
          if (ready()) resolve();
          else reject(new Error(name + ' engine did not initialize'));
        };
        script.onerror = function () {
          reject(new Error(name + ' engine could not be loaded'));
        };
        document.head.appendChild(script);
      });
    }
    return engineRequests[name];
  }

  // The static form of a component whose engine is not there: the source the
  // dedicated Print output shows. Returns the way back.
  function showSource(root, kind, text) {
    var canvas = root.querySelector('[data-td-' + kind + '-canvas]');
    var pre = document.createElement('pre');
    var code = document.createElement('code');
    pre.className = 'td-' + kind + '-source';
    code.className = 'language-' + kind;
    code.textContent = text;
    pre.appendChild(code);
    if (canvas) canvas.hidden = true;
    root.appendChild(pre);
    return function () {
      pre.remove();
      if (canvas) canvas.hidden = false;
    };
  }

  // A component is due when it is on screen, within a short scroll below, or
  // anywhere above: mounting one above the reader would move the text being
  // read. Hidden ones (a closed tab or disclosure) are due once shown.
  var unmounted = new Map();
  var observer =
    typeof IntersectionObserver === 'function'
      ? new IntersectionObserver(
          function (entries) {
            entries.forEach(function (entry) {
              if (entry.isIntersecting) begin(entry.target);
            });
          },
          { rootMargin: '1000000px 0px 320px 0px' },
        )
      : null;

  function begin(root) {
    var component = unmounted.get(root);
    if (!component || component.begun) return;
    component.begun = true;
    if (observer) observer.unobserve(root);
    loadEngine(component.engine, component.ready).then(
      function () {
        unmounted.delete(root);
        component.mount(root);
      },
      function (error) {
        unmounted.delete(root);
        console.error(component.engine + ':', error);
        var text = component.source && component.source(root);
        if (text) showSource(root, component.engine, text);
      },
    );
  }

  function defer(root, component) {
    unmounted.set(root, component);
    if (observer) observer.observe(root);
    else begin(root);
  }

  // Browser printing cannot wait for a script. What has mounted prints as it
  // is; the rest prints its source, as it does in the Print output.
  var printRestores = null;

  function beginPrint() {
    if (printRestores) return;
    printRestores = [];
    unmounted.forEach(function (component, root) {
      var text = component.source && component.source(root);
      if (text) printRestores.push(showSource(root, component.engine, text));
    });
  }

  function endPrint() {
    if (!printRestores) return;
    printRestores.forEach(function (restore) {
      restore();
    });
    printRestores = null;
  }

  window.addEventListener('beforeprint', beginPrint);
  window.addEventListener('afterprint', endPrint);
  if (window.matchMedia) {
    var printQuery = window.matchMedia('print');
    if (printQuery.addEventListener) {
      printQuery.addEventListener('change', function (event) {
        if (event.matches) beginPrint();
        else endPrint();
      });
    }
  }

  function initAsciinema(root) {
    if (!window.AsciinemaPlayer) return;
    var config = configOf(root, '[data-td-asciinema-config]');
    var target = root.querySelector('[data-td-asciinema-player]');
    if (!config || !target) return;
    var player;
    var renderId = 0;

    function render() {
      var currentRenderId = ++renderId;
      var options = Object.assign({}, config.options);
      if (config.theme === 'auto') {
        options.theme = currentTheme() === 'dark' ? 'td-dark' : 'td-light';
      } else {
        options.theme = config.theme;
      }
      var fontFamily = getComputedStyle(root)
        .getPropertyValue('--td-asciinema-font-family')
        .trim();
      if (fontFamily) options.terminalFontFamily = fontFamily;

      function mount() {
        if (currentRenderId !== renderId) return;
        if (player) player.dispose();
        player = null;
        target.replaceChildren();
        function fallback(error) {
          if (currentRenderId !== renderId) return;
          const focused = target.contains(document.activeElement);
          console.error('Asciinema:', error);
          if (player) player.dispose();
          player = null;
          const link = document.createElement('a');
          link.href = config.src;
          link.textContent = root.querySelector('.td-asciinema__title')?.textContent || config.src;
          target.replaceChildren(link);
          if (focused) link.focus({ preventScroll: true });
        }
        try {
          player = window.AsciinemaPlayer.create(config.src, target, options);
          // Options can fail synchronously; fetching and parsing the recording
          // fail later. Both paths preserve access to the original recording.
          player.addEventListener('error', fallback);
        } catch (error) {
          fallback(error);
          return;
        }
        var timer = target.querySelector('.ap-timer');
        if (timer && !timer.getAttribute('aria-label')) {
          timer.setAttribute(
            'aria-label',
            root.dataset.tdTimerLabel || 'Playback time',
          );
        }
      }

      // Asciinema measures terminal cells when it mounts. Wait for a custom
      // web font so measurement and playback use the same glyph metrics.
      if (document.fonts && document.fonts.load && fontFamily) {
        try {
          document.fonts.load('1em ' + fontFamily).then(mount, mount);
        } catch (error) {
          mount();
        }
      } else {
        mount();
      }
    }

    render();
    if (config.theme === 'auto') watchTheme(render);
  }

  function replaceFunctions(value) {
    if (typeof value === 'string' && value.indexOf('$fn:') === 0) {
      return (window.OinkEchartsFunctions || {})[value.slice(4)];
    }
    if (Array.isArray(value)) return value.map(replaceFunctions);
    if (value && typeof value === 'object') {
      Object.keys(value).forEach(function (key) {
        value[key] = replaceFunctions(value[key]);
      });
    }
    return value;
  }

  function initEcharts(root) {
    if (!window.echarts) return;
    var options = configOf(root, '[data-td-echarts-options]');
    var target = root.querySelector('[data-td-echarts-canvas]');
    if (!options || !target) return;
    options = replaceFunctions(options);
    var configuredTheme = root.getAttribute('data-theme');
    var chart;

    function render() {
      if (chart) {
        chart.dispose();
        chart = null;
      }
      var theme =
        configuredTheme || (currentTheme() === 'dark' ? 'dark' : null);
      try {
        chart = window.echarts.init(target, theme);
        chart.setOption(options);
      } catch (error) {
        console.error('ECharts:', error);
        if (chart) {
          chart.dispose();
          chart = null;
        }
        target.textContent = 'ECharts: ' + error.message;
        target.setAttribute('role', 'alert');
      }
    }

    var resizeChart = function () {
      if (chart) chart.resize();
    };
    render();
    if (!configuredTheme) watchTheme(render);
    if (window.ResizeObserver) {
      new ResizeObserver(resizeChart).observe(target);
    } else {
      window.addEventListener('resize', resizeChart);
      document.addEventListener('td:tab-shown', resizeChart);
      document.addEventListener('toggle', resizeChart, true);
    }
  }

  var infographicFontsRegistered = false;

  function initInfographic(root) {
    if (!window.AntVInfographic) return;
    var syntax = configOf(root, '[data-td-infographic-syntax]');
    var target = root.querySelector('[data-td-infographic-canvas]');
    if (typeof syntax !== 'string' || !target) return;
    function failed(error) {
      target.textContent = 'Infographic: ' + error.message;
      target.setAttribute('role', 'alert');
    }
    try {
      if (!infographicFontsRegistered) {
        [
          'Alibaba PuHuiTi',
          'Source Han Sans',
          'Source Han Serif',
          'LXGW WenKai',
          '851tegakizatsu',
        ].forEach(function (fontFamily) {
          window.AntVInfographic.registerFont({
            fontFamily: fontFamily,
            baseUrl: '',
            fontWeight: {},
          });
        });
        window.AntVInfographic.setDefaultFont('sans-serif');
        infographicFontsRegistered = true;
      }
      var started = false;
      var observer;
      function renderWhenVisible() {
        if (started || !target.getBoundingClientRect().width) return;
        started = true;
        if (observer) observer.disconnect();
        window.removeEventListener('resize', renderWhenVisible);
        document.removeEventListener('td:tab-shown', renderWhenVisible);
        document.removeEventListener('toggle', renderWhenVisible, true);
        try {
          var selectorId = window.CSS && window.CSS.escape ? window.CSS.escape(target.id) : target.id;
          var chart = new window.AntVInfographic.Infographic({
            container: '#' + selectorId,
            // The viewBox scales with the container, without rerendering the DSL.
            width: '100%',
            height: root.getAttribute('data-td-height') || 'auto',
          });
          chart.on('rendered', function (event) {
            // Keep the authored SVG palette. Transparent default/hand-drawn
            // diagrams need their own light canvas even on a dark article.
            target.style.backgroundColor = event.node.style.backgroundColor || '#fff';
          });
          chart.render(syntax);
        } catch (error) { failed(error); }
      }
      if (window.ResizeObserver) {
        observer = new ResizeObserver(renderWhenVisible);
        observer.observe(target);
      } else {
        window.addEventListener('resize', renderWhenVisible);
        document.addEventListener('td:tab-shown', renderWhenVisible);
        document.addEventListener('toggle', renderWhenVisible, true);
      }
      renderWhenVisible();
    } catch (error) {
      failed(error);
    }
  }

  // An unmounted player is its recording link, which is already its static
  // form. A chart or an infographic has only its declared source.
  document.querySelectorAll('[data-td-asciinema]').forEach(function (root) {
    defer(root, {
      engine: 'asciinema',
      ready: function () {
        return !!window.AsciinemaPlayer;
      },
      mount: initAsciinema,
    });
  });
  document.querySelectorAll('[data-td-echarts]').forEach(function (root) {
    defer(root, {
      engine: 'echarts',
      ready: function () {
        return !!window.echarts;
      },
      mount: initEcharts,
      source: function () {
        var options = configOf(root, '[data-td-echarts-options]');
        return options ? JSON.stringify(options, null, 2) : '';
      },
    });
  });
  document.querySelectorAll('[data-td-infographic]').forEach(function (root) {
    defer(root, {
      engine: 'infographic',
      ready: function () {
        return !!window.AntVInfographic;
      },
      mount: initInfographic,
      source: function () {
        var syntax = configOf(root, '[data-td-infographic-syntax]');
        return typeof syntax === 'string' ? syntax : '';
      },
    });
  });
})();
