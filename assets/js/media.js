// Media runtime, loaded only on pages with an autoplay video or a video card
// whose platform the site enabled in params.video_embeds.
//
// 1. A video marked data-td-media-autoplay is muted and looped by its markup
//    but carries no autoplay attribute. It plays while at least half of it is
//    visible, the page is visible, and the reader has not asked for reduced
//    motion; it pauses otherwise. A reader's own pause or play wins until the
//    video next leaves the viewport. Native controls always remain.
// 2. A card with data-td-media-embed is an ordinary link to the platform. A
//    plain click replaces it with the platform player, whose URL the theme
//    built from validated IDs; modified clicks keep the link behavior.
(function () {
  'use strict';

  var PLAYER =
    /^https:\/\/(?:www\.youtube-nocookie\.com\/embed\/[A-Za-z0-9_-]{11}\?autoplay=1(?:&start=[0-9]+)?|player\.bilibili\.com\/player\.html\?(?:bvid=BV[0-9A-Za-z]{10}|aid=[0-9]{1,12})&p=[1-9][0-9]{0,3}&autoplay=1&danmaku=0(?:&t=[0-9]+)?|player\.vimeo\.com\/video\/[0-9]{1,12}\?autoplay=1&dnt=1(?:&h=[0-9a-f]{6,20})?(?:#t=[0-9]+s)?)$/;
  var reduce = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

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
})();
