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
            root.dataset.timerLabel || 'Playback time',
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
      return (window.tdEchartsFunctions || {})[value.slice(4)];
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
        height: root.getAttribute('data-height') || 'auto',
      });
      chart.render(syntax);
    } catch (error) {
      target.textContent = 'Infographic: ' + error.message;
      target.setAttribute('role', 'alert');
    }
  }

  function initFileTree(root) {
    if (root.dataset.tdFiletreeReady === 'true') return;
    var body = root.querySelector('[data-td-filetree-body]');
    var divider = root.querySelector('[data-td-filetree-divider]');
    if (!body || !divider) return;
    root.dataset.tdFiletreeReady = 'true';

    var minimum = Number(divider.getAttribute('aria-valuemin')) || 20;
    var maximum = Number(divider.getAttribute('aria-valuemax')) || 80;
    var initial = Number(divider.getAttribute('aria-valuenow')) || 56;
    var current = initial;
    var activePointer = null;
    var overflowFrame = 0;
    var commentScrolls = Array.from(
      root.querySelectorAll('.td-filetree__comment-scroll'),
    );

    function updateCommentOverflow(scroller) {
      var comment = scroller.closest('.td-filetree__comment');
      if (!comment) return;
      var remaining = scroller.scrollWidth - scroller.clientWidth;
      var position = Math.abs(scroller.scrollLeft);
      comment.toggleAttribute(
        'data-overflow-end',
        remaining > 1 && position < remaining - 1,
      );
    }

    function updateOverflow() {
      overflowFrame = 0;
      commentScrolls.forEach(updateCommentOverflow);
    }

    function scheduleOverflow() {
      if (overflowFrame) window.cancelAnimationFrame(overflowFrame);
      overflowFrame = window.requestAnimationFrame(updateOverflow);
    }

    function setSplit(value) {
      current = Math.max(minimum, Math.min(maximum, value));
      current = Math.round(current * 10) / 10;
      root.style.setProperty('--td-filetree-split', current + '%');
      divider.setAttribute('aria-valuenow', String(Math.round(current)));
      scheduleOverflow();
    }

    function splitFromPointer(event) {
      var rect = body.getBoundingClientRect();
      var rtl = getComputedStyle(body).direction === 'rtl';
      var distance = rtl ? rect.right - event.clientX : event.clientX - rect.left;
      return (distance / rect.width) * 100;
    }

    function stopResize(event) {
      if (activePointer === null) return;
      root.classList.remove('td-filetree--resizing');
      if (event && divider.hasPointerCapture(event.pointerId)) {
        divider.releasePointerCapture(event.pointerId);
      }
      activePointer = null;
    }

    divider.addEventListener('pointerdown', function (event) {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      event.preventDefault();
      divider.focus();
      activePointer = event.pointerId;
      divider.setPointerCapture(event.pointerId);
      root.classList.add('td-filetree--resizing');
      setSplit(splitFromPointer(event));
    });
    window.addEventListener('pointermove', function (event) {
      if (event.pointerId !== activePointer) return;
      setSplit(splitFromPointer(event));
    });
    window.addEventListener('pointerup', stopResize);
    window.addEventListener('pointercancel', stopResize);
    divider.addEventListener('dblclick', function () {
      setSplit(initial);
    });
    divider.addEventListener('keydown', function (event) {
      var rtl = getComputedStyle(body).direction === 'rtl';
      var step = event.shiftKey ? 10 : 2;
      if (event.key === 'Home') setSplit(minimum);
      else if (event.key === 'End') setSplit(maximum);
      else if (event.key === 'ArrowLeft')
        setSplit(current + (rtl ? step : -step));
      else if (event.key === 'ArrowRight')
        setSplit(current + (rtl ? -step : step));
      else return;
      event.preventDefault();
    });

    commentScrolls.forEach(function (scroller) {
      scroller.addEventListener('scroll', function () {
        updateCommentOverflow(scroller);
      });
    });
    if ('ResizeObserver' in window) {
      new ResizeObserver(scheduleOverflow).observe(body);
    } else {
      window.addEventListener('resize', scheduleOverflow);
    }
    setSplit(initial);
  }

  function initCarousel(root) {
    var track = root.querySelector('[data-td-carousel-track]');
    var cards = track ? Array.from(track.children) : [];
    if (!track || !cards.length) return;
    var index = 0;
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    function go(next) {
      index = Math.max(0, Math.min(cards.length - 1, next));
      cards[index].scrollIntoView({
        behavior: reduceMotion.matches ? 'auto' : 'smooth',
        block: 'nearest',
        inline: 'start',
      });
      root
        .querySelectorAll('[data-td-carousel-action]')
        .forEach(function (button) {
          var disabled =
            button.getAttribute('data-td-carousel-action') === 'previous'
              ? index === 0
              : index === cards.length - 1;
          button.disabled = disabled;
        });
    }

    root
      .querySelectorAll('[data-td-carousel-action]')
      .forEach(function (button) {
        button.addEventListener('click', function () {
          go(
            index +
              (button.getAttribute('data-td-carousel-action') === 'previous'
                ? -1
                : 1),
          );
        });
      });
    track.addEventListener('keydown', function (event) {
      var rtl = getComputedStyle(track).direction === 'rtl';
      if (event.key === 'Home') go(0);
      else if (event.key === 'End') go(cards.length - 1);
      else if (event.key === 'ArrowLeft') go(index + (rtl ? 1 : -1));
      else if (event.key === 'ArrowRight') go(index + (rtl ? -1 : 1));
      else return;
      event.preventDefault();
    });
    go(0);
  }

  document.querySelectorAll('[data-td-asciinema]').forEach(initAsciinema);
  document.querySelectorAll('[data-td-filetree]').forEach(initFileTree);
  document.querySelectorAll('[data-td-echarts]').forEach(initEcharts);
  document.querySelectorAll('[data-td-infographic]').forEach(initInfographic);
  document.querySelectorAll('[data-td-carousel]').forEach(initCarousel);
})();
