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

  var PLAYER = /^https:\/\/(?:www\.youtube-nocookie\.com\/embed\/|player\.bilibili\.com\/player\.html\?|player\.vimeo\.com\/video\/)/;
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
    entry.self = true;
    if (play && video.paused) {
      var started = video.play();
      if (started && started.catch) {
        started.catch(function () {
          entry.self = false;
        });
      }
    } else if (!play && !video.paused) {
      video.pause();
    }
    // Media events fire asynchronously; clear the marker after they settle.
    setTimeout(function () {
      entry.self = false;
    }, 0);
  }

  function applyAll() {
    videos.forEach(apply);
  }

  videos.forEach(function (video) {
    var entry = { visible: false, reader: false, self: false };
    state.set(video, entry);
    video.muted = true;
    ['play', 'pause'].forEach(function (type) {
      video.addEventListener(type, function () {
        if (!entry.self) entry.reader = true;
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
    var ratio = card.style.aspectRatio;
    if (ratio) holder.style.aspectRatio = ratio;
    var frame = document.createElement('iframe');
    frame.src = src;
    frame.title = card.getAttribute('data-td-media-title') || '';
    frame.setAttribute(
      'allow',
      'autoplay; encrypted-media; picture-in-picture; fullscreen',
    );
    frame.setAttribute('allowfullscreen', '');
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    holder.appendChild(frame);
    card.replaceWith(holder);
    frame.focus();
  });
})();
