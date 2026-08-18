(function () {
  'use strict';

  var shade, iframe;
  var server;

  var insertFrame = function () {
    shade = document.createElement('div');
    shade.classList.add('drawioframe');
    iframe = document.createElement('iframe');
    iframe.title = 'Draw.io';
    shade.appendChild(iframe);
    document.body.appendChild(shade);
  };

  var closeFrame = function () {
    if (shade) {
      document.body.removeChild(shade);
      shade = undefined;
      iframe = undefined;
    }
  };

  var imghandler = function (img, imgdata) {
    var url = server;
    url += '?embed=1&ui=atlas&spin=1&modified=unsavedChanges&proto=json&saveAndEdit=1&noSaveBtn=1';

    var wrapper = document.createElement('div');
    wrapper.classList.add('drawio');
    img.parentNode.insertBefore(wrapper, img);
    wrapper.appendChild(img);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.classList.add('drawiobtn');
    btn.setAttribute('aria-label', 'Draw.io');
    btn.insertAdjacentHTML('beforeend', '<i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>');
    wrapper.appendChild(btn);

    btn.addEventListener('click', function () {
      if (iframe) return;
      insertFrame();
      var handler = function (evt) {
        var wind = iframe.contentWindow;
        if (evt.data.length > 0 && evt.source === wind) {
          var msg = JSON.parse(evt.data);

          if (msg.event === 'init') {
            wind.postMessage(JSON.stringify({action: 'load', xml: imgdata}), '*');
          } else if (msg.event === 'save') {
            var fmt = imgdata.indexOf('data:image/png') === 0 ? 'xmlpng' : 'xmlsvg';
            wind.postMessage(JSON.stringify({action: 'export', format: fmt}), '*');
          } else if (msg.event === 'export') {
            const fn = img.src.replace(/^.*?([^/]+)$/, '$1');
            const dl = document.createElement('a');
            dl.setAttribute('href', msg.data);
            dl.setAttribute('download', fn);
            document.body.appendChild(dl);
            dl.click();
            dl.parentNode.removeChild(dl);
          }

          if (msg.event === 'exit' || msg.event === 'export') {
            window.removeEventListener('message', handler);
            closeFrame();
          }
        }
      };

      window.addEventListener('message', handler);
      iframe.setAttribute('src', url);
    });
  };

  var read = function (blob, method, done) {
    var reader = new FileReader();
    reader.addEventListener('load', function () { done(reader.result); });
    reader[method](blob);
  };

  document.addEventListener('DOMContentLoaded', function () {
    var config = document.getElementById('td-drawio-config');
    if (!config) return;
    server = JSON.parse(config.textContent).server;

    var imagesBySource = new Map();
    document.querySelectorAll('main img').forEach(function (img) {
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
        read(xhr.response, 'readAsBinaryString', function (source) {
          if (source.indexOf('mxfile') === -1) return;
          read(xhr.response, 'readAsDataURL', function (imgdata) {
            images.forEach(function (img) { imghandler(img, imgdata); });
          });
        });
      });
      xhr.send();
    });
  });
}());
