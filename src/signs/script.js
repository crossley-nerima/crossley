// 看板のポスター（確定版）のページ: たたんだ所（これから・決まったこと・参考）・書体の10案の切り替え（たたんだ所の中）・印刷。
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // ---- 書体の10案（お店が選んで決まったので、たたんで残している）: 「‹ ›」・小さい画像・左右にすべらせる・← → で切り替える
  var viewer = $('.sg-type');
  var panels = viewer ? $$('.sg-type__panel', viewer) : [];
  var thumbs = viewer ? $$('.sg-type__thumb', viewer) : [];
  var stage = viewer && $('.sg-type__stage', viewer);
  var fromHash = function () { return -1; };
  if (viewer && panels.length) {
    var img = $('.sg-type__img', viewer), big = $('.sg-type__big', viewer), now = $('.sg-type__now', viewer), cur = 0;
    var show = function (i, near) {
      i = (i + panels.length) % panels.length;
      var p = panels[i];
      cur = i;
      panels.forEach(function (x, j) { x.classList.toggle('is-active', j === i); });
      img.src = p.getAttribute('data-zoom');
      img.alt = p.getAttribute('data-alt');
      big.href = p.getAttribute('data-big');
      $('b', now).textContent = p.getAttribute('data-label');
      $('span', now).textContent = p.getAttribute('data-name');
      thumbs.forEach(function (t, j) { if (j === i) t.setAttribute('aria-current', 'true'); else t.removeAttribute('aria-current'); });
      if (near) [i + 1, i - 1].forEach(function (k) {     // 前後の案の画像を先に読んでおく（切り替えたときだけ。初めはたたんであるので読まない）
        var q = panels[(k + panels.length) % panels.length];
        (new Image()).src = q.getAttribute('data-zoom');
      });
    };
    fromHash = function () {      // 「#font-05」のようなアドレスで開いたときは、その案を出す
      var m = location.hash.match(/^#font-(\d+)$/);
      return m ? panels.map(function (p) { return p.id; }).indexOf('font-' + m[1]) : -1;
    };
    viewer.classList.add('is-ready');
    show(fromHash() >= 0 ? fromHash() : +(viewer.getAttribute('data-first') || 0));
    window.addEventListener('hashchange', function () { if (fromHash() >= 0) show(fromHash(), true); });
    $$('.sg-type__step', viewer).forEach(function (b) {
      b.addEventListener('click', function () { show(cur + +b.getAttribute('data-step'), true); });
    });
    thumbs.forEach(function (t, j) {
      t.addEventListener('click', function (e) {
        e.preventDefault();
        show(j, true);
        if (stage.getBoundingClientRect().top < 0) stage.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    var zoom = $('.sg-type__zoom', viewer), sx = null, sy = 0;
    zoom.addEventListener('touchstart', function (e) {
      if (e.touches.length === 1) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }
    }, { passive: true });
    zoom.addEventListener('touchend', function (e) {
      if (sx === null) return;
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      sx = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) show(cur + (dx < 0 ? 1 : -1), true);
    }, { passive: true });
    stage.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { show(cur + (e.key === 'ArrowRight' ? 1 : -1), true); }
    });
  }

  // ---- たたんだ所: 目次などから飛んだときは開く（「#font-05」は、書体の10案を開いて、その案の説明の所へ）。
  // 「すべて開く」は、決まったこと・参考の中のものだけを開く
  var folds = $$('.sg-fold--group .sg-folds > .sg-fold');
  function openTo(el) {
    for (var d = el.closest ? el.closest('details') : null; d; d = d.parentElement ? d.parentElement.closest('details') : null) d.open = true;
  }
  function openHash(hash) {
    if (!hash || hash.length < 2) return null;
    var el = null;
    try { el = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (e) { el = null; }
    if (el) openTo(el);
    return el;
  }
  if (openHash(location.hash)) {
    setTimeout(function () { var el = openHash(location.hash); if (el) el.scrollIntoView(); }, 0);
  }
  window.addEventListener('hashchange', function () { var el = openHash(location.hash); if (el) el.scrollIntoView(); });
  $$('a[href^="#"]').forEach(function (a) {
    if (a.classList.contains('sg-type__thumb')) return;
    a.addEventListener('click', function () { openHash(a.getAttribute('href')); });
  });
  var allBtn = $('.sg-fold-all');
  function syncAll() {
    if (!allBtn) return;
    var all = folds.every(function (d) { return d.open; });
    allBtn.setAttribute('aria-pressed', all ? 'true' : 'false');
    allBtn.textContent = all ? 'すべて閉じる' : 'すべて開く';
  }
  folds.forEach(function (d) { d.addEventListener('toggle', syncAll); });
  if (allBtn) allBtn.addEventListener('click', function () {
    var open = allBtn.getAttribute('aria-pressed') !== 'true';
    folds.forEach(function (d) { d.open = open; });
    syncAll();
  });

  // ---- 印刷: たたんだ所も全部開いて印刷し、終わったら元に戻す（印刷用の見た目は style.css の @media print）
  var wasOpen = null;
  function openAll() {
    if (wasOpen) return;
    var all = $$('details');
    wasOpen = all.map(function (d) { return d.open; });
    all.forEach(function (d) { d.open = true; });
  }
  function restore() {
    if (!wasOpen) return;
    var states = wasOpen;
    wasOpen = null;
    $$('details').forEach(function (d, i) { d.open = states[i]; });
  }
  window.addEventListener('beforeprint', openAll);
  window.addEventListener('afterprint', restore);
  $$('.sg-print').forEach(function (b) { b.addEventListener('click', function () { openAll(); window.print(); }); });
})();
