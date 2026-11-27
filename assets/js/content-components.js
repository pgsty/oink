// Runtime for opt-in content components. Included only when a page uses one.
// The page carries this small adapter; the player, chart and map engines load
// when a component that needs them comes due.
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

  // ECharts arrives only when a chart comes due, so a site script has no
  // moment to call registerTheme itself. It names its themes the way it names
  // $fn: functions, and each chart registers them before it draws.
  function registerThemes() {
    var themes = window.OinkEchartsThemes;
    if (!themes || typeof themes !== 'object') return;
    Object.keys(themes).forEach(function (name) {
      var theme = themes[name];
      if (theme && typeof theme === 'object') {
        window.echarts.registerTheme(name, theme);
      }
    });
  }

  function initEcharts(root) {
    if (!window.echarts) return;
    var options = configOf(root, '[data-td-echarts-options]');
    var target = root.querySelector('[data-td-echarts-canvas]');
    if (!options || !target) return;
    options = replaceFunctions(options);
    registerThemes();
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

  // A map fence keeps its numbered place list as the content; the map is an
  // enhancement above it. Popups and the attribution are built from text,
  // never from author HTML. Scroll-wheel zoom stays off so reading never
  // zooms the map; buttons, keyboard and pinch remain.
  function attributionHTML(text, url) {
    var box = document.createElement('div');
    if (url && /^https:\/\//i.test(url)) {
      var link = document.createElement('a');
      link.href = url;
      link.rel = 'external';
      link.textContent = text || '';
      box.appendChild(link);
    } else {
      box.textContent = text || '';
    }
    return box.innerHTML;
  }

  // The hosts a click-to-load map may contact: light and dark tiles alike, with
  // `{s}` shown as `*` because the request rotates through every subdomain.
  // Browsers percent-encode `*` in a parsed hostname, so `{s}` parses as a
  // plain label and becomes `*` afterwards.
  var SUBDOMAIN_LABEL = 'tdsubdomain';
  function tileHosts(site) {
    var hosts = [];
    [site && site.tiles, site && site.darkTiles].forEach(function (template) {
      if (!template) return;
      try {
        var host = new URL(
          String(template).replace(/\{s\}/g, SUBDOMAIN_LABEL).replace(/\{[^{}]*\}/g, '0'),
        ).hostname.split(SUBDOMAIN_LABEL).join('*');
        if (host && hosts.indexOf(host) < 0) hosts.push(host);
      } catch (_) {
        // An unparsable template names no host; the button keeps its label.
      }
    });
    return hosts;
  }

  function safePlaceHref(value) {
    var raw = typeof value === 'string' ? value.trim() : '';
    if (!raw || raw.indexOf('//') === 0 || /[\u0000-\u001f\u007f\\]/.test(raw)) return '';
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(raw) && !/^(?:https?:\/\/|mailto:)/i.test(raw)) return '';
    return raw;
  }

  function safePlaceThumb(value) {
    var raw = typeof value === 'string' ? value.trim() : '';
    if (!raw || raw.indexOf('//') === 0 || /[\u0000-\u001f\u007f\\]/.test(raw)) return '';
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(raw) && !/^https?:\/\//i.test(raw)) return '';
    return raw;
  }

  function mapPopup(place) {
    var box = document.createElement('div');
    box.className = 'td-map__popup';
    var thumb = safePlaceThumb(place.thumb);
    if (thumb) {
      var image = document.createElement('img');
      image.src = thumb;
      image.alt = '';
      image.loading = 'lazy';
      box.appendChild(image);
    }
    var href = safePlaceHref(place.href);
    var name = document.createElement(href ? 'a' : 'strong');
    name.className = 'td-map__popup-name';
    name.textContent = place.name;
    if (href) {
      name.href = href;
      if (/^(?:https?:\/\/|mailto:)/i.test(href)) name.rel = 'external';
    }
    box.appendChild(name);
    if (place.text) {
      var text = document.createElement('p');
      text.textContent = place.text;
      box.appendChild(text);
    }
    return box;
  }

  function initMap(root) {
    var L = window.L;
    var data = configOf(root, '[data-td-map-source]');
    var site = configOf(document, '[data-td-map-config]');
    var canvas = root.querySelector('[data-td-map-canvas]');
    if (!L || !data || !site || !site.tiles || !canvas) return;
    var places = Array.isArray(data.places) ? data.places : [];
    if (!places.length) return;
    canvas.hidden = false;
    if (!site.darkTiles && typeof canvas.setAttribute === 'function') {
      canvas.setAttribute('data-td-map-light-tiles', '');
    }
    var reduced = !!(
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
    var touch = !!(L.Browser && L.Browser.touch);
    var map = L.map(canvas, {
      scrollWheelZoom: false,
      dragging: !touch,
      fadeAnimation: !reduced,
      zoomAnimation: !reduced,
      markerZoomAnimation: !reduced,
      zoomControl: false,
      attributionControl: false,
      maxZoom: site.maxZoom || 19,
    });
    // Leaflet reports touch wherever Pointer Events exist, desktops included,
    // so drag starts off: a finger on the map keeps scrolling the page (two
    // fingers still pinch, zoom and pan). A mouse or a pen turns drag on as it
    // enters or presses the map; a finger turns it off again.
    function dragsMap(event) {
      return event.pointerType === 'mouse' || event.pointerType === 'pen';
    }
    if (touch && map.dragging && typeof canvas.addEventListener === 'function') {
      canvas.addEventListener(
        'pointerdown',
        function (event) {
          if (dragsMap(event)) map.dragging.enable();
          else if (event.pointerType === 'touch') map.dragging.disable();
        },
        true,
      );
      canvas.addEventListener('pointerenter', function (event) {
        if (dragsMap(event)) map.dragging.enable();
      });
    }
    L.control
      .zoom({ zoomInTitle: site.zoomIn || 'Zoom in', zoomOutTitle: site.zoomOut || 'Zoom out' })
      .addTo(map);
    L.control
      .attribution({ prefix: false })
      .addTo(map)
      .addAttribution(attributionHTML(site.attribution, site.attributionUrl));
    var layer = null;
    var hidden = false;
    var darkFailed = false;
    // A layer whose first tiles all fail: dark tiles fall back to the light
    // ones; light tiles hide the canvas and leave the list. Leaflet is still
    // dispatching the failing layer's 'load' when this runs and reads the
    // layer's map afterwards, so removing a layer or the map waits a turn.
    function layerFailed(dark) {
      if (dark) {
        darkFailed = true;
        if (typeof canvas.setAttribute === 'function') {
          canvas.setAttribute('data-td-map-light-tiles', '');
        }
        setTimeout(tiles, 0);
        return;
      }
      hidden = true;
      canvas.hidden = true;
      if (root.classList) root.classList.remove('td-map--mounted');
      setTimeout(function () {
        if (typeof map.remove === 'function') map.remove();
      }, 0);
    }
    function tiles() {
      if (hidden) return;
      var dark = currentTheme() === 'dark' && !!site.darkTiles && !darkFailed;
      if (layer) map.removeLayer(layer);
      var tileOpts = { maxZoom: site.maxZoom || 19 };
      if (site.subdomains) tileOpts.subdomains = site.subdomains;
      var loaded = 0;
      var failed = 0;
      var current = L.tileLayer(dark ? site.darkTiles : site.tiles, tileOpts);
      layer = current;
      if (typeof current.on === 'function') {
        current.on('tileload', function () {
          loaded += 1;
        });
        current.on('tileerror', function () {
          failed += 1;
        });
        current.on('load', function () {
          if (!hidden && current === layer && loaded === 0 && failed > 0) layerFailed(dark);
        });
      }
      current.addTo(map);
    }
    tiles();
    if (site.darkTiles) watchTheme(tiles);
    var points = [];
    var markers = [];
    places.forEach(function (place, index) {
      var point = [place.lat, place.lng];
      points.push(point);
      var markerLabel = index + 1 + '. ' + place.name;
      var marker = L.marker(point, {
        title: place.name,
        alt: place.name,
        icon: L.divIcon({
          className: 'td-map__marker',
          html: '<span aria-hidden="true">' + (index + 1) + '</span>',
          iconSize: [28, 28],
          iconAnchor: [14, 14],
          popupAnchor: [0, -14],
        }),
      }).bindPopup(mapPopup(place));
      // Leaflet creates the divIcon element inside onAdd (which waits for the
      // first setView/fitBounds), so label on 'add' as well as immediately.
      function labelMarker() {
        var markerEl = typeof marker.getElement === 'function' ? marker.getElement() : null;
        if (markerEl && typeof markerEl.setAttribute === 'function') {
          markerEl.setAttribute('aria-label', markerLabel);
        }
      }
      if (typeof marker.on === 'function') marker.on('add', labelMarker);
      marker.addTo(map);
      labelMarker();
      markers.push(marker);
    });
    if (data.route && points.length > 1) {
      L.polyline(points, { className: 'td-map__route', weight: 3, interactive: false }).addTo(map);
    }
    var lastTrigger = null;
    var keyboardOpen = false;
    var closingFromButton = false;
    function popupElement(event) {
      var popup = event && event.popup;
      return popup && typeof popup.getElement === 'function' ? popup.getElement() : null;
    }
    if (typeof map.on === 'function') {
      map.on('popupopen', function (event) {
        var source = event && event.popup && event.popup._source;
        lastTrigger = source && typeof source.getElement === 'function' ? source.getElement() : null;
        var close = canvas.querySelector && canvas.querySelector('.leaflet-popup-close-button');
        if (close && site.closePopup) {
          close.setAttribute('aria-label', site.closePopup);
          close.setAttribute('title', site.closePopup);
        }
        // The popup sits after every marker in the DOM. Opened from the
        // keyboard, it takes focus so its link and close button come next.
        if (!keyboardOpen) return;
        keyboardOpen = false;
        var scope = popupElement(event) || canvas;
        var target =
          (scope.querySelector && scope.querySelector('a.td-map__popup-name')) ||
          (scope.querySelector && scope.querySelector('.leaflet-popup-close-button'));
        if (target && typeof target.focus === 'function') target.focus({ preventScroll: true });
      });
      map.on('popupclose', function () {
        // The close button disappears with its popup and would leave focus
        // on nothing: return it to the marker that opened the popup. Other
        // closes (a map click, another popup) already put focus somewhere.
        if (!closingFromButton) return;
        closingFromButton = false;
        if (lastTrigger && typeof lastTrigger.focus === 'function') lastTrigger.focus({ preventScroll: true });
      });
    }
    if (typeof canvas.addEventListener === 'function') {
      // Capture runs before Leaflet's own handler on the close button, by
      // pointer or by Enter, so the flag is set when 'popupclose' fires.
      canvas.addEventListener(
        'click',
        function (event) {
          var target = event.target;
          if (target && typeof target.closest === 'function' && target.closest('.leaflet-popup-close-button')) {
            closingFromButton = true;
            setTimeout(function () {
              closingFromButton = false;
            }, 0);
          }
        },
        true,
      );
      canvas.addEventListener('keydown', function (event) {
        // Leaflet opens a marker's popup on Enter. Remember that the next
        // popup comes from the keyboard, for this key press only.
        var target = event.target;
        if (event.key === 'Enter' && target && target.classList && target.classList.contains('td-map__marker')) {
          keyboardOpen = true;
          setTimeout(function () {
            keyboardOpen = false;
          }, 0);
        }
        if (
          event.key === 'Escape' &&
          map._popup &&
          (!map._popup.isOpen || map._popup.isOpen()) &&
          typeof map.closePopup === 'function'
        ) {
          event.preventDefault();
          event.stopPropagation();
          map.closePopup();
          if (lastTrigger && typeof lastTrigger.focus === 'function') lastTrigger.focus({ preventScroll: true });
        }
      });
    }
    function frame() {
      if (points.length === 1) {
        map.setView(points[0], data.zoom || 15);
      } else if (data.zoom) {
        var center = typeof L.latLngBounds === 'function' ? L.latLngBounds(points).getCenter() : null;
        if (center) {
          map.setView(center, data.zoom);
        } else {
          map.fitBounds(points, { padding: [32, 32] });
          map.setZoom(data.zoom);
        }
      } else {
        map.fitBounds(points, { padding: [32, 32], maxZoom: 16 });
      }
    }
    function hasBox() {
      return typeof canvas.clientWidth !== 'number' || (canvas.clientWidth > 0 && canvas.clientHeight > 0);
    }
    var framed = false;
    if (hasBox()) {
      frame();
      framed = true;
    }
    var resize = function () {
      if (hidden) return;
      map.invalidateSize();
      if (!framed && hasBox()) {
        frame();
        framed = true;
      }
    };
    if (window.ResizeObserver) {
      new ResizeObserver(resize).observe(canvas);
    } else {
      window.addEventListener('resize', resize);
    }
    document.addEventListener('td:tab-shown', resize);
    document.addEventListener('toggle', resize, true);
    if (root.classList) root.classList.add('td-map--mounted');
    var listItems =
      typeof root.querySelectorAll === 'function' ? root.querySelectorAll('.td-map__places > li') : [];
    markers.forEach(function (marker, index) {
      var item = listItems[index];
      if (!item || typeof item.addEventListener !== 'function') return;
      item.addEventListener('click', function (event) {
        if (hidden) return;
        if (event.target && typeof event.target.closest === 'function' && event.target.closest('a, button')) {
          return;
        }
        if (typeof map.panTo === 'function' && typeof marker.getLatLng === 'function') {
          map.panTo(marker.getLatLng(), { animate: !reduced });
        }
        if (typeof marker.openPopup === 'function') marker.openPopup();
        if (typeof canvas.scrollIntoView === 'function') {
          canvas.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' });
        }
      });
    });
  }

  function registerAll() {
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
    var mapSite = configOf(document, '[data-td-map-config]');
    var mapClickOnly = !!(mapSite && mapSite.loading === 'click');
    var mapHost = mapClickOnly ? tileHosts(mapSite).join(', ') : '';
    document.querySelectorAll('[data-td-map]').forEach(function (root) {
      var component = {
        engine: 'leaflet',
        ready: function () {
          return !!window.L;
        },
        mount: initMap,
      };
      if (mapClickOnly) {
        var canvas = root.querySelector('[data-td-map-canvas]');
        if (!canvas || typeof root.insertBefore !== 'function') return;
        unmounted.set(root, component);
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'td-map__load';
        if (typeof button.setAttribute === 'function') button.setAttribute('data-td-map-load', '');
        var label = (mapSite && mapSite.loadMap) || 'Load map';
        // Hostnames are left-to-right: isolate them (LRI … PDI) so an RTL
        // label cannot move the leading `*` or trailing dots.
        button.textContent = mapHost ? label + ' (\u2066' + mapHost + '\u2069)' : label;
        button.addEventListener('click', function () {
          // The button disappears; keyboard focus moves to the map it loads.
          if (document.activeElement === button) {
            component.mount = function (target) {
              initMap(target);
              if (!canvas.hidden && typeof canvas.focus === 'function') canvas.focus({ preventScroll: true });
            };
          }
          if (typeof button.remove === 'function') button.remove();
          else if (button.parentNode) button.parentNode.removeChild(button);
          begin(root);
        });
        root.insertBefore(button, canvas);
      } else {
        defer(root, component);
      }
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
  }

  // Wait for DOMContentLoaded while parsing so tabs.js (loaded ahead of this
  // chunk) can group and hide inactive panels before IntersectionObserver runs.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerAll, { once: true });
  } else {
    registerAll();
  }
})();
