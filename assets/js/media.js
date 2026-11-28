// Shared by pages with a local audio/video player or an enabled platform card.
//
// 0. Every file player gets the theme's control row in place of the browser's:
//    play, elapsed time, one seek bar, duration, speed, mute and volume, plus
//    captions and full screen for video. The seek bar is a single track whose
//    colors tell played, buffered and unloaded time apart (media.css). The
//    markup keeps `controls`, so without this runtime the native player stays.
// 1. A video marked data-td-media-autoplay is muted and looped by its markup
//    but carries no autoplay attribute. It plays while at least half of it is
//    visible, the page is visible, and the reader has not asked for reduced
//    motion; it pauses otherwise. A reader's own pause or play wins until the
//    video next leaves the viewport. The control row can always pause it.
// 2. A card with data-td-media-embed is an ordinary link to the platform. A
//    plain click replaces it with the platform player, whose URL the theme
//    built from validated IDs; modified clicks keep the link behavior.
// 3. A player that becomes audible, by starting with sound or by being
//    unmuted while it plays, pauses every other audible player on the page so
//    samples do not talk over each other. Opening an enabled platform card
//    silences audible local players before mounting the autoplay iframe, though
//    cross-origin iframes cannot be paused by local players later. Silent
//    players (muted or at zero volume), such as autoplay loops, neither
//    interrupt nor get interrupted.
(function () {
  'use strict';

  var PLAYER =
    /^https:\/\/(?:www\.youtube-nocookie\.com\/embed\/[A-Za-z0-9_-]{11}\?autoplay=1(?:&start=[0-9]+)?|player\.bilibili\.com\/player\.html\?(?:bvid=BV[0-9A-Za-z]{10}|aid=[0-9]{1,12})&(?:p=[1-9][0-9]{0,3}|cid=[1-9][0-9]{0,18})&autoplay=1&danmaku=0(?:&t=[0-9]+)?|player\.vimeo\.com\/video\/[0-9]{1,12}\?autoplay=1&dnt=1(?:&h=[0-9a-f]{6,20})?(?:#t=[0-9]+s)?)$/;
  var reduce = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

  var config = {};
  var configNode = document.querySelector('script[data-td-media-config]');
  if (configNode) {
    try {
      config = JSON.parse(configNode.textContent) || {};
    } catch (error) {
      config = {};
    }
  }

  function text(key, fallback) {
    return typeof config[key] === 'string' && config[key] ? config[key] : fallback;
  }

  var LABELS = {
    play: text('play', 'Play'),
    pause: text('pause', 'Pause'),
    seek: text('seek', 'Seek'),
    speed: text('speed', 'Playback speed'),
    captions: text('captions', 'Captions'),
    mute: text('mute', 'Mute'),
    volume: text('volume', 'Volume'),
    fullscreen: text('fullscreen', 'Full screen'),
  };
  var RATES = [1, 1.25, 1.5, 2, 0.75];
  var SEEK_STEP = 5;
  var MAX_RANGES = 8;
  var ICONS = {
    play: 'fa-solid fa-play',
    pause: 'fa-solid fa-pause',
    replay: 'fa-solid fa-rotate-right',
    loud: 'fa-solid fa-volume-high',
    quiet: 'fa-solid fa-volume-low',
    muted: 'fa-solid fa-volume-xmark',
    captions: 'fa-solid fa-closed-captioning',
    enter: 'fa-solid fa-expand',
    exit: 'fa-solid fa-compress',
  };

  function clock(value) {
    var total = Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
    var hours = Math.floor(total / 3600);
    var minutes = Math.floor((total % 3600) / 60);
    var seconds = total % 60;
    var tail = (seconds < 10 ? ':0' : ':') + seconds;
    if (!hours) return minutes + tail;
    return hours + (minutes < 10 ? ':0' : ':') + minutes + tail;
  }

  function percent(fraction) {
    return (Math.min(1, Math.max(0, fraction)) * 100).toFixed(3) + '%';
  }

  function makeButton(name, icon, label) {
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'td-media__button td-media__' + name;
    if (label) {
      button.setAttribute('aria-label', label);
      button.title = label;
    }
    if (icon) {
      var glyph = document.createElement('i');
      glyph.className = icon;
      glyph.setAttribute('aria-hidden', 'true');
      button.appendChild(glyph);
    }
    return button;
  }

  function setIcon(button, icon) {
    var glyph = button.querySelector('i');
    if (glyph && glyph.className !== icon) glyph.className = icon;
  }

  function makeRange(name, label, max, step) {
    var range = document.createElement('input');
    range.type = 'range';
    range.className = 'td-media__range td-media__' + name;
    range.min = '0';
    range.max = String(max);
    range.step = step;
    range.value = '0';
    range.setAttribute('aria-label', label);
    return range;
  }

  function makeTime(name) {
    var time = document.createElement('span');
    time.className = 'td-media__time td-media__time--' + name;
    time.setAttribute('aria-hidden', 'true');
    time.textContent = name === 'total' ? '-:--' : '0:00';
    return time;
  }

  function fullscreenElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || null;
  }

  function enhance(player) {
    var figure = player.parentElement;
    var isVideo = player.tagName === 'VIDEO';
    var row = document.createElement('div');
    row.className = 'td-media__controls';
    row.setAttribute('role', 'group');
    // Media time runs left to right in every script, as on tape and in the
    // native players; the row keeps that order on RTL pages.
    row.setAttribute('dir', 'ltr');
    var named = player.getAttribute('aria-labelledby');
    if (named) row.setAttribute('aria-labelledby', named);
    else if (player.getAttribute('aria-label')) row.setAttribute('aria-label', player.getAttribute('aria-label'));

    var toggle = makeButton('play', ICONS.play, LABELS.play);
    var current = makeTime('current');
    var seek = makeRange('seek', LABELS.seek, 0, 'any');
    var total = makeTime('total');
    var speed = makeButton('speed', '', '');
    var speedLabel = document.createElement('span');
    speedLabel.className = 'visually-hidden';
    speedLabel.textContent = LABELS.speed + ' ';
    var speedValue = document.createElement('span');
    speedValue.className = 'td-media__rate';
    speed.title = LABELS.speed;
    speed.append(speedLabel, speedValue);
    var mute = makeButton('mute', ICONS.loud, LABELS.mute);
    var volume = makeRange('volume', LABELS.volume, 1, '0.05');
    var sound = document.createElement('span');
    sound.className = 'td-media__sound';
    sound.append(mute, volume);
    row.append(toggle, current, seek, total, speed);

    var captions = null;
    var tracks = player.textTracks;
    if (isVideo && tracks && player.querySelector('track')) {
      captions = makeButton('captions', ICONS.captions, LABELS.captions);
      row.append(captions);
    }
    row.append(sound);
    var full = null;
    if (
      isVideo &&
      ((document.fullscreenEnabled && figure.requestFullscreen) ||
        (document.webkitFullscreenEnabled && figure.webkitRequestFullscreen) ||
        player.webkitEnterFullscreen)
    ) {
      full = makeButton('fullscreen', ICONS.enter, LABELS.fullscreen);
      full.setAttribute('aria-pressed', 'false');
      row.append(full);
    }

    player.controls = false;
    player.removeAttribute('controls');
    player.after(row);
    figure.classList.add('td-media--controlled');

    var scrubbing = false;

    function timed() {
      return Number.isFinite(player.duration) && player.duration > 0 && !player.error;
    }

    function syncPlay() {
      var playing = !player.paused && !player.ended;
      var label = playing ? LABELS.pause : LABELS.play;
      figure.classList.toggle('td-media--playing', playing);
      toggle.setAttribute('aria-label', label);
      toggle.title = label;
      setIcon(toggle, playing ? ICONS.pause : player.ended ? ICONS.replay : ICONS.play);
      toggle.disabled = !!player.error;
    }

    function syncBuffer() {
      if (!timed()) {
        figure.style.removeProperty('--td-media-loaded');
        return;
      }
      var ranges = player.buffered;
      var stops = [];
      for (var i = 0; ranges && i < ranges.length && i < MAX_RANGES; i += 1) {
        var from = percent(ranges.start(i) / player.duration);
        var to = percent(ranges.end(i) / player.duration);
        stops.push('transparent ' + from, 'var(--td-media-buffer) ' + from, 'var(--td-media-buffer) ' + to, 'transparent ' + to);
      }
      if (stops.length) {
        figure.style.setProperty('--td-media-loaded', 'linear-gradient(to right, ' + stops.join(', ') + ')');
      } else {
        figure.style.removeProperty('--td-media-loaded');
      }
    }

    function syncTime() {
      var known = timed();
      var now = known ? Math.min(player.duration, Math.max(0, player.currentTime)) : player.currentTime || 0;
      figure.classList.toggle('td-media--timed', known);
      current.textContent = clock(now);
      total.textContent = known ? clock(player.duration) : '-:--';
      seek.disabled = !known;
      if (known) {
        seek.max = String(player.duration);
        if (!scrubbing) seek.value = String(now);
        figure.style.setProperty('--td-media-played', percent(now / player.duration));
      } else {
        seek.max = '0';
        seek.value = '0';
        figure.style.removeProperty('--td-media-played');
      }
      seek.setAttribute('aria-valuetext', clock(now) + ' / ' + (known ? clock(player.duration) : '-:--'));
      syncBuffer();
    }

    function syncVolume() {
      var level = player.muted ? 0 : player.volume;
      mute.setAttribute('aria-pressed', String(level === 0));
      setIcon(mute, level === 0 ? ICONS.muted : level < 0.5 ? ICONS.quiet : ICONS.loud);
      volume.value = String(level);
      volume.setAttribute('aria-valuetext', Math.round(level * 100) + '%');
      figure.style.setProperty('--td-media-volume', percent(level));
    }

    function syncRate() {
      var rate = player.playbackRate || 1;
      speedValue.textContent = (Math.round(rate * 100) / 100) + '×';
      figure.classList.toggle('td-media--rate', rate !== 1);
    }

    function showingTrack() {
      for (var i = 0; i < tracks.length; i += 1) {
        if (tracks[i].mode === 'showing') return tracks[i];
      }
      return null;
    }

    function syncCaptions() {
      if (captions) captions.setAttribute('aria-pressed', String(!!showingTrack()));
    }

    function syncFullscreen() {
      if (!full) return;
      var on = fullscreenElement() === figure;
      figure.classList.toggle('td-media--fullscreen', on);
      full.setAttribute('aria-pressed', String(on));
      setIcon(full, on ? ICONS.exit : ICONS.enter);
    }

    function togglePlay() {
      if (player.paused || player.ended) {
        var started = player.play();
        if (started && started.catch) started.catch(function () {});
      } else {
        player.pause();
      }
    }

    function seekTo(seconds) {
      if (!timed()) return;
      player.currentTime = Math.min(player.duration, Math.max(0, seconds));
      syncTime();
    }

    toggle.addEventListener('click', togglePlay);
    if (isVideo) player.addEventListener('click', togglePlay);

    seek.addEventListener('pointerdown', function () {
      scrubbing = true;
    });
    ['pointerup', 'pointercancel', 'change', 'blur'].forEach(function (type) {
      seek.addEventListener(type, function () {
        scrubbing = false;
      });
    });
    seek.addEventListener('input', function () {
      seekTo(Number(seek.value));
    });
    seek.addEventListener('keydown', function (event) {
      if (!timed() || event.altKey || event.ctrlKey || event.metaKey) return;
      var step = {
        ArrowLeft: -SEEK_STEP,
        ArrowDown: -SEEK_STEP,
        ArrowRight: SEEK_STEP,
        ArrowUp: SEEK_STEP,
        PageDown: -player.duration / 10,
        PageUp: player.duration / 10,
      }[event.key];
      var target = event.key === 'Home' ? 0 : event.key === 'End' ? player.duration : null;
      if (step === undefined && target === null) return;
      event.preventDefault();
      seekTo(target === null ? player.currentTime + step : target);
    });

    speed.addEventListener('click', function () {
      var index = RATES.indexOf(player.playbackRate);
      player.playbackRate = RATES[(index + 1) % RATES.length];
    });

    mute.addEventListener('click', function () {
      if (player.muted || player.volume === 0) {
        if (player.volume === 0) player.volume = 1;
        player.muted = false;
      } else {
        player.muted = true;
      }
    });
    volume.addEventListener('input', function () {
      var level = Number(volume.value);
      player.volume = level;
      player.muted = level === 0;
    });

    if (captions) {
      captions.addEventListener('click', function () {
        var showing = showingTrack();
        for (var i = 0; i < tracks.length; i += 1) {
          if (tracks[i].mode === 'showing') tracks[i].mode = 'hidden';
        }
        if (!showing) {
          for (var j = 0; j < tracks.length; j += 1) {
            if (tracks[j].kind === 'subtitles' || tracks[j].kind === 'captions') {
              tracks[j].mode = 'showing';
              break;
            }
          }
        }
        syncCaptions();
      });
      if (tracks.addEventListener) tracks.addEventListener('change', syncCaptions);
    }

    if (full) {
      full.addEventListener('click', function () {
        if (fullscreenElement() === figure) {
          (document.exitFullscreen || document.webkitExitFullscreen).call(document);
        } else if (document.fullscreenEnabled && figure.requestFullscreen) {
          var entered = figure.requestFullscreen();
          if (entered && entered.catch) entered.catch(function () {});
        } else if (document.webkitFullscreenEnabled && figure.webkitRequestFullscreen) {
          figure.webkitRequestFullscreen();
        } else if (player.webkitEnterFullscreen) {
          player.webkitEnterFullscreen();
        }
      });
      document.addEventListener('fullscreenchange', syncFullscreen);
      document.addEventListener('webkitfullscreenchange', syncFullscreen);
    }

    ['play', 'playing', 'pause', 'ended', 'emptied', 'error'].forEach(function (type) {
      player.addEventListener(type, syncPlay);
    });
    ['loadedmetadata', 'durationchange', 'timeupdate', 'seeking', 'seeked', 'ended', 'emptied', 'error'].forEach(function (type) {
      player.addEventListener(type, syncTime);
    });
    player.addEventListener('progress', syncBuffer);
    player.addEventListener('volumechange', syncVolume);
    player.addEventListener('ratechange', syncRate);
    player.addEventListener('loadedmetadata', syncCaptions);

    syncPlay();
    syncTime();
    syncVolume();
    syncRate();
    syncCaptions();
  }

  document.querySelectorAll('.td-media > audio, .td-media > video').forEach(enhance);

  function motionAllowed() {
    return !(reduce && reduce.matches);
  }

  var videos = Array.prototype.slice.call(
    document.querySelectorAll('video[data-td-media-autoplay]'),
  );
  var state = new Map();

  function apply(video) {
    var entry = state.get(video);
    if (!entry || entry.reader) return;
    var play = entry.visible && motionAllowed() && !document.hidden;
    if (play && video.paused) {
      video.muted = true;
      entry.expect.push('play');
      var started = video.play();
      if (started && started.catch) {
        started.catch(function () {
          var idx = entry.expect.lastIndexOf('play');
          if (idx !== -1) entry.expect.splice(idx, 1);
        });
      }
    } else if (!play && !video.paused) {
      entry.expect.push('pause');
      video.pause();
    }
  }

  function applyAll() {
    videos.forEach(apply);
  }

  videos.forEach(function (video) {
    var entry = { visible: false, reader: false, expect: [] };
    state.set(video, entry);
    video.muted = true;
    ['play', 'pause'].forEach(function (type) {
      video.addEventListener(type, function () {
        if (entry.expect[0] === type) {
          entry.expect.shift();
        } else {
          entry.expect.length = 0;
          entry.reader = true;
        }
      });
    });
  });

  if (videos.length && typeof IntersectionObserver === 'function') {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (item) {
          var entry = state.get(item.target);
          if (!entry) return;
          entry.visible = item.isIntersecting && item.intersectionRatio >= 0.5;
          if (!item.isIntersecting) entry.reader = false;
          apply(item.target);
        });
      },
      { threshold: [0, 0.5] },
    );
    videos.forEach(function (video) {
      observer.observe(video);
    });
    document.addEventListener('visibilitychange', applyAll);
    if (reduce) {
      if (reduce.addEventListener) reduce.addEventListener('change', applyAll);
      else if (reduce.addListener) reduce.addListener(applyAll);
    }
  }

  document.addEventListener('click', function (event) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    var card =
      event.target && event.target.closest
        ? event.target.closest('a[data-td-media-embed]')
        : null;
    if (!card) return;
    var src = card.getAttribute('data-td-media-embed') || '';
    if (!PLAYER.test(src)) return;
    event.preventDefault();
    pauseAudible(null);
    var holder = document.createElement('div');
    holder.className = 'td-media-player';
    // The player keeps the card's shape and its 80vh width cap (media.css).
    var ratio = card.style.getPropertyValue('--td-media-ratio');
    if (ratio) holder.style.setProperty('--td-media-ratio', ratio);
    var frame = document.createElement('iframe');
    frame.src = src;
    frame.title = card.getAttribute('data-td-media-title') || '';
    frame.setAttribute('allow', 'autoplay; picture-in-picture; fullscreen');
    frame.setAttribute(
      'sandbox',
      'allow-scripts allow-same-origin allow-presentation allow-popups allow-popups-to-escape-sandbox',
    );
    frame.setAttribute('allowfullscreen', '');
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    holder.appendChild(frame);
    card.replaceWith(holder);
    frame.focus();
  });

  // A silent player (muted, or at zero volume) never takes part: the theme's
  // autoplay loops and an author's own GIF-like loops play on undisturbed.
  function isMedia(el) {
    return !!el && (el.tagName === 'AUDIO' || el.tagName === 'VIDEO');
  }

  function silent(el) {
    return !!el.muted || el.volume === 0;
  }

  function pauseAudible(except) {
    var players = document.querySelectorAll('audio, video');
    for (var i = 0; i < players.length; i += 1) {
      var other = players[i];
      if (other === except || other.paused || silent(other)) continue;
      other.pause();
    }
  }

  function soloist(target) {
    if (!isMedia(target) || target.paused || silent(target)) return;
    pauseAudible(target);
  }

  // Media events do not bubble, so both listen in the capture phase. A player
  // becomes audible either by starting with sound or, already playing, by
  // being unmuted (volumechange); both silence the others.
  ['play', 'volumechange'].forEach(function (type) {
    document.addEventListener(
      type,
      function (event) {
        soloist(event.target);
      },
      true,
    );
  });
})();
