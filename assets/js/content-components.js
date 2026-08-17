// Runtime for opt-in content components. Included only when a page uses one.
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
        target.replaceChildren();
        player = window.AsciinemaPlayer.create(config.src, target, options);
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
      if (chart) chart.dispose();
      var theme =
        configuredTheme || (currentTheme() === 'dark' ? 'dark' : null);
      chart = window.echarts.init(target, theme);
      chart.setOption(options);
    }

    render();
    if (!configuredTheme) watchTheme(render);
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        if (chart) chart.resize();
      }).observe(target);
    } else {
      window.addEventListener('resize', function () {
        if (chart) chart.resize();
      });
    }
  }

  function initInfographic(root) {
    if (!window.AntVInfographic) return;
    var syntax = configOf(root, '[data-td-infographic-syntax]');
    var target = root.querySelector('[data-td-infographic-canvas]');
    if (typeof syntax !== 'string' || !target) return;
    try {
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
      var chart = new window.AntVInfographic.Infographic({
        container: '#' + target.id,
        width: target.offsetWidth || '100%',
        height: root.getAttribute('data-td-height') || 'auto',
      });
      chart.render(syntax);
    } catch (error) {
      target.textContent = 'Infographic: ' + error.message;
      target.setAttribute('role', 'alert');
    }
  }

  document.querySelectorAll('[data-td-asciinema]').forEach(initAsciinema);
  document.querySelectorAll('[data-td-echarts]').forEach(initEcharts);
  document.querySelectorAll('[data-td-infographic]').forEach(initInfographic);
})();
