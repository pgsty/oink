(function () {
  'use strict';

  var shade, iframe, activeHandler, opener;
  var server, closeLabel;

  var closeFrame = function (restoreFocus) {
    if (activeHandler) {
      window.removeEventListener('message', activeHandler);
      activeHandler = undefined;
    }
    if (shade) {
      var dialog = shade;
      shade = undefined;
      iframe = undefined;
      dialog.close();
      if (dialog.parentNode) dialog.parentNode.removeChild(dialog);
      if (restoreFocus !== false && opener && opener.isConnected) opener.focus({ preventScroll: true });
      opener = undefined;
    }
  };

  var insertFrame = function () {
    shade = document.createElement('dialog');
    shade.classList.add('drawioframe');
    shade.setAttribute('aria-label', 'Draw.io');
    var nonBackdropDown = false;
    shade.addEventListener('pointerdown', function (evt) {
      nonBackdropDown = evt.target !== shade;
    });
    shade.addEventListener('click', function (evt) {
      if (evt.target === shade && !nonBackdropDown) closeFrame();
      nonBackdropDown = false;
    });
    shade.addEventListener('cancel', function (evt) {
      evt.preventDefault();
      closeFrame();
    });
    shade.addEventListener('close', function () {
      if (shade === this) closeFrame();
    });
    iframe = document.createElement('iframe');
    iframe.title = 'Draw.io';
    shade.appendChild(iframe);
    // Cross-origin editors own their keyboard events. Keep a host close
    // control next in the Tab order, even when the editor does not send exit.
    var close = document.createElement('button');
    close.type = 'button';
    close.tabIndex = 0; // Keep the host escape route in Safari's Tab sequence.
    close.classList.add('drawioframe__close');
    close.textContent = closeLabel;
    close.addEventListener('click', function () { closeFrame(); });
    shade.appendChild(close);
    document.body.appendChild(shade);
    shade.showModal();
    close.focus();
  };

  var imghandler = function (img, imgdata) {
    var url = new URL(server, document.baseURI);
    var options = {
      embed: '1', ui: 'atlas', spin: '1', modified: 'unsavedChanges',
      proto: 'json', saveAndEdit: '1', noSaveBtn: '1',
    };
    Object.keys(options).forEach(function (key) { url.searchParams.set(key, options[key]); });

    var wrapper = document.createElement('div');
    wrapper.classList.add('drawio');
    // Zoom may already own a button around the image. Wrap that whole control
    // so Edit stays its sibling, never an interactive child of another button.
    var imageControl = img.closest('.td-image-zoom__trigger') || img;
    imageControl.parentNode.insertBefore(wrapper, imageControl);
    wrapper.appendChild(imageControl);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.tabIndex = 0; // Keep Edit in Safari's Tab sequence.
    btn.classList.add('drawiobtn');
    btn.setAttribute('aria-label', 'Draw.io');
    btn.insertAdjacentHTML('beforeend', '<i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>');
    wrapper.appendChild(btn);

    btn.addEventListener('click', function () {
      if (iframe) return;
      if (window.OinkSurfaceCoordinator) window.OinkSurfaceCoordinator.closeOthers('drawio');
      opener = btn;
      insertFrame();
      activeHandler = function (evt) {
        if (!iframe || evt.source !== iframe.contentWindow || evt.origin !== url.origin
          || typeof evt.data !== 'string' || !evt.data) return;
        var wind = iframe.contentWindow;
        var msg;
        try { msg = JSON.parse(evt.data); } catch (_) { return; }
        if (msg && typeof msg === 'object') {

          if (msg.event === 'init') {
            wind.postMessage(JSON.stringify({action: 'load', xml: imgdata}), url.origin);
          } else if (msg.event === 'save') {
            var fmt = imgdata.indexOf('data:image/png') === 0 ? 'xmlpng' : 'xmlsvg';
            wind.postMessage(JSON.stringify({action: 'export', format: fmt}), url.origin);
          } else if (msg.event === 'export') {
            if (typeof msg.data !== 'string'
              || !/^data:image\/(?:png|svg\+xml)(?:;[^,]*)?,/i.test(msg.data)) return;
            const fn = img.src.split(/[?#]/)[0].replace(/^.*?([^/]+)$/, '$1');
            const dl = document.createElement('a');
            dl.setAttribute('href', msg.data);
            dl.setAttribute('download', fn);
            document.body.appendChild(dl);
            dl.click();
            dl.parentNode.removeChild(dl);
          }

          if (msg.event === 'exit' || msg.event === 'export') {
            closeFrame();
          }
        }
      };

      window.addEventListener('message', activeHandler);
      iframe.setAttribute('src', url.href);
    });
  };

  var read = function (blob, method, done) {
    var reader = new FileReader();
    reader.addEventListener('load', function () { done(reader.result); });
    reader[method](blob);
  };

  var initDrawio = function () {
    var config = document.getElementById('td-drawio-config');
    if (!config) return;
    var options = JSON.parse(config.textContent);
    server = options.server;
    closeLabel = options.close || 'Close';
    if (window.OinkSurfaceCoordinator) window.OinkSurfaceCoordinator.register('drawio', closeFrame);
    window.addEventListener('beforeprint', function () { closeFrame(false); });

    var imagesBySource = new Map();
    document.querySelectorAll('main img').forEach(function (img) {
      // A video-platform card's poster is not a diagram, and an Edit button
      // would nest inside the card's link. Other linked images stay eligible.
      if (img.closest && img.closest('a.td-media-card')) return;
      var src = img.currentSrc || img.src;
      if (!/\.(?:png|svg)(?:[?#].*)?$/i.test(src)) return;
      if (!imagesBySource.has(src)) imagesBySource.set(src, []);
      imagesBySource.get(src).push(img);
    });

    imagesBySource.forEach(function (images, src) {
      const xhr = new XMLHttpRequest();
      xhr.responseType = 'blob';
      xhr.open('GET', src);
      xhr.addEventListener("load", function () {
        if (xhr.status < 200 || xhr.status >= 300 || !xhr.response) return;
        read(xhr.response, 'readAsBinaryString', function (source) {
          if (source.indexOf('mxfile') === -1) return;
          read(xhr.response, 'readAsDataURL', function (imgdata) {
            images.forEach(function (img) { imghandler(img, imgdata); });
          });
        });
      });
      xhr.send();
    });
  };
  if (!document.readyState || document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDrawio);
  } else {
    initDrawio();
  }
}());
