/* ILM Docs: phone menu, dropdowns, guide list on phones, video player + steps, screenshot zoom, guide search on the home page. */
(function () {
  'use strict';
  var body = document.body;

  // phone menu + dropdowns opened by click (hover works on desktop)
  var burger = document.querySelector('.ilmd-burger');
  if (burger) {
    burger.addEventListener('click', function () {
      var open = body.classList.toggle('nav-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.innerHTML = open ? '<i class="fa-solid fa-xmark" aria-hidden="true"></i>' : '<i class="fa-solid fa-bars" aria-hidden="true"></i>';
    });
  }
  document.querySelectorAll('.ilmd-nav__item.has-kids > button.ilmd-nav__top').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item = btn.parentNode;
      var open = !item.classList.contains('is-open');
      document.querySelectorAll('.ilmd-nav__item.is-open').forEach(function (o) { o.classList.remove('is-open'); });
      item.classList.toggle('is-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.addEventListener('click', function (ev) {
    if (!ev.target.closest('.ilmd-nav__item')) {
      document.querySelectorAll('.ilmd-nav__item.is-open').forEach(function (o) { o.classList.remove('is-open'); });
    }
  });

  var article = document.querySelector('.ilmd-article');

  // phone: the guide name opens and closes the page list
  var guideLink = document.querySelector('.ilmd-side__guide');
  if (guideLink) {
    guideLink.addEventListener('click', function (ev) {
      if (window.matchMedia('(max-width: 991.98px)').matches) {
        ev.preventDefault();
        body.classList.toggle('tree-open');
      }
    });
  }

  // video page: the YouTube player loads only on a click (no cookies before);
  // the steps jump to their time and the step being played is marked
  var player = document.querySelector('.ilmd-player');
  if (player) {
    var frame = null;
    var stepButtons = Array.prototype.slice.call(document.querySelectorAll('.ilmd-steps button[data-t]'));
    var send = function (func, args) {
      if (frame) { frame.contentWindow.postMessage(JSON.stringify({ event: 'command', func: func, args: args || [] }), '*'); }
    };
    var mark = function (t) {
      var now = null;
      stepButtons.forEach(function (b) { if (+b.getAttribute('data-t') <= t + 0.5) { now = b; } });
      stepButtons.forEach(function (b) { b.classList.toggle('is-now', b === now); });
    };
    var play = function (start) {
      if (frame) { send('seekTo', [start, true]); send('playVideo'); mark(start); return; }
      frame = document.createElement('iframe');
      frame.src = 'https://www.youtube-nocookie.com/embed/' + player.getAttribute('data-yt') +
        '?autoplay=1&rel=0&cc_load_policy=1&enablejsapi=1&origin=' + encodeURIComponent(location.origin) + (start ? '&start=' + start : '') + (player.getAttribute('data-end') ? '&end=' + player.getAttribute('data-end') : '');
      frame.title = player.getAttribute('data-title') || 'Video';
      frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      frame.allowFullscreen = true;
      frame.addEventListener('load', function () {
        frame.contentWindow.postMessage(JSON.stringify({ event: 'listening', id: 1 }), '*');
      });
      player.innerHTML = '';
      player.appendChild(frame);
      mark(start || 0);
    };
    player.querySelector('.ilmd-player__start').addEventListener('click', function () { play(+player.getAttribute('data-start') || 0); });
    stepButtons.forEach(function (b) {
      b.addEventListener('click', function () {
        play(+b.getAttribute('data-t'));
        if (window.matchMedia('(max-width: 1279.98px)').matches) { player.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });
    window.addEventListener('message', function (ev) {
      if (!frame || ev.source !== frame.contentWindow) { return; }
      var data;
      try { data = JSON.parse(ev.data); } catch (e) { return; }
      if (data && data.info && typeof data.info.currentTime === 'number') { mark(data.info.currentTime); }
    });
  }

  // click a screenshot to see it large
  if (article) {
    article.addEventListener('click', function (ev) {
      var img = ev.target.closest('img');
      if (!img || img.closest('a, button') || img.naturalWidth < 500) { return; }
      var layer = document.createElement('div');
      layer.className = 'ilmd-zoom';
      layer.innerHTML = '<img alt="">';
      layer.firstChild.src = img.currentSrc || img.src;
      layer.addEventListener('click', function () { layer.remove(); });
      document.addEventListener('keydown', function esc(e) { if (e.key === 'Escape') { layer.remove(); document.removeEventListener('keydown', esc); } });
      body.appendChild(layer);
    });
  }

  // home page: search the guide pages by title (index printed by the template)
  var box = document.querySelector('[data-ilmd-search]');
  var data = document.getElementById('ilmd-index');
  if (box && data) {
    var pages = [];
    try { pages = JSON.parse(data.textContent); } catch (e) { pages = []; }
    var input = box.querySelector('input');
    var out = document.createElement('div');
    out.className = 'ilmd-search__results';
    out.hidden = true;
    box.appendChild(out);
    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
    input.addEventListener('input', function () {
      var words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
      if (!words.length) { out.hidden = true; return; }
      var hits = pages.filter(function (p) {
        var hay = (p.t + ' ' + p.g + ' ' + (p.k || '')).toLowerCase();
        return words.every(function (w) { return hay.indexOf(w) !== -1; });
      }).slice(0, 12);
      out.innerHTML = hits.length
        ? hits.map(function (p) { return '<a href="' + esc(p.u) + '">' + esc(p.t) + '<span>' + esc(p.g) + '</span></a>'; }).join('')
        : '<p>No page found. Try another word, or write to sales@ilmtech.in.</p>';
      out.hidden = false;
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') {
        var first = out.querySelector('a');
        if (first) { window.location.href = first.href; }
      }
    });
    document.addEventListener('click', function (ev) { if (!box.contains(ev.target)) { out.hidden = true; } });
  }
})();

/* guide search: the box in the sidebar searches the pages of this guide only (titles and text, from /search-index.json) */
(function () {
  'use strict';
  var box = document.querySelector('.ilmd-gsearch');
  if (!box) { return; }
  var prefix = box.getAttribute('data-prefix');
  var input = box.querySelector('input');
  var out = document.createElement('div');
  out.className = 'ilmd-gsearch__results';
  out.hidden = true;
  box.appendChild(out);
  var pages = null;
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var load = function (done) {
    if (pages) { done(); return; }
    fetch('/search-index.json').then(function (r) { return r.json(); }).then(function (all) {
      pages = all.filter(function (p) { return p.u.indexOf(prefix) === 0; });
      done();
    }).catch(function () { pages = []; done(); });
  };
  var snippet = function (text, word) {
    var i = text.toLowerCase().indexOf(word);
    if (i < 0) { return esc(text.slice(0, 90)) + '…'; }
    var start = Math.max(0, i - 40);
    var part = text.slice(start, i + 70);
    var j = part.toLowerCase().indexOf(word);
    return (start ? '…' : '') + esc(part.slice(0, j)) + '<mark>' + esc(part.substr(j, word.length)) + '</mark>' + esc(part.slice(j + word.length)) + '…';
  };
  var run = function () {
    var words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) { out.hidden = true; return; }
    var hits = pages.filter(function (p) {
      var hay = (p.t + ' ' + p.x).toLowerCase();
      return words.every(function (w) { return hay.indexOf(w) !== -1; });
    }).map(function (p) {
      var t = p.t.toLowerCase();
      return { p: p, score: words.filter(function (w) { return t.indexOf(w) !== -1; }).length };
    }).sort(function (a, b) { return b.score - a.score; }).slice(0, 10);
    out.innerHTML = hits.length
      ? hits.map(function (h) { return '<a href="' + esc(h.p.u) + '"><strong>' + esc(h.p.t) + '</strong><span>' + snippet(h.p.x, words[0]) + '</span></a>'; }).join('')
      : '<p>Nothing found in this guide.</p>';
    out.hidden = false;
  };
  input.addEventListener('input', function () { load(run); });
  input.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') { var first = out.querySelector('a'); if (first) { window.location.href = first.href; } }
    if (ev.key === 'Escape') { input.value = ''; out.hidden = true; }
  });
  document.addEventListener('click', function (ev) { if (!box.contains(ev.target)) { out.hidden = true; } });
})();
