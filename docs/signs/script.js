// 看板のポスター（書体の10案）のページ: 書体の案の切り替え・「これがいい」・返事を送る（LINE・コピー）・たたんだ所・印刷。
// 値段の欄は、まだ決まっていない値段があるときだけ出る（そのときは、送る文面にも入る）。
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // ---- 返事を送る: 書いた内容はこの端末に残す（仕上がりへの返事とは、別の名前で残す）
  var KEY = 'xiii-poster-font-reply', form = $('.sg-send');
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { saved = {}; }
  var fontInputs = form ? $$('input[name=font]', form) : [];
  var priceInputs = form ? $$('input[name^="price_"]', form) : [];
  function save() {
    var data = { fonts: [], prices: {} };
    fontInputs.forEach(function (x) { if (x.checked) data.fonts.push(x.value); });
    priceInputs.forEach(function (x) { if (x.value.trim()) data.prices[x.name] = x.value; });
    data.note = form.elements.note.value;
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) { /* 残せなくても送れる */ }
  }
  function message() {
    var picked = fontInputs.filter(function (x) { return x.checked; }).map(function (x) {
      return '・' + (x.value === '00' ? '' : x.value + ' ') + x.getAttribute('data-name');
    });
    var lines = ['【看板のポスター（書体の10案）への返事】', '', '気に入った書体：' + (picked.length ? '' : '（まだ選んでいません）')];
    if (picked.length) lines.push(picked.join('\n'));
    var prices = priceInputs.filter(function (x) { return x.value.trim(); })
      .map(function (x) { return '・' + x.getAttribute('data-label') + '：' + x.value.trim(); });
    if (prices.length) lines.push('', 'ポスターに入れる値段：', prices.join('\n'));
    if (form.elements.note.value.trim()) lines.push('', 'ひとこと：', form.elements.note.value.trim());
    lines.push('', '（ダイニングバー XⅢ クロスリー）');
    return lines.join('\n');
  }
  function refresh() {
    if (!form) return;
    var m = message();
    $('.sg-send__preview', form).textContent = m;
    $('.sg-send__line', form).href = 'https://line.me/R/share?text=' + encodeURIComponent(m);
    syncPicks();
  }
  if (form) {
    fontInputs.forEach(function (x) { x.checked = (saved.fonts || []).indexOf(x.value) >= 0; });
    priceInputs.forEach(function (x) { x.value = (saved.prices || {})[x.name] || ''; });
    form.elements.note.value = saved.note || '';
    form.addEventListener('input', function () { save(); refresh(); });
    form.addEventListener('change', function () { save(); refresh(); });
    $('.sg-send__copy', form).addEventListener('click', function () {
      var btn = this;
      if (navigator.clipboard) navigator.clipboard.writeText(message()).then(function () {
        btn.textContent = 'コピーしました'; setTimeout(function () { btn.textContent = '文面をコピー'; }, 2000);
      });
    });
  }

  // ---- 書体の10案: 「‹ ›」・小さい画像・左右にすべらせる・← → で切り替える。「これがいい」は返事のチェックとつながっている
  var viewer = $('.sg-type');
  var panels = viewer ? $$('.sg-type__panel', viewer) : [];
  var thumbs = viewer ? $$('.sg-type__thumb', viewer) : [];
  function fontOf(i) { return panels[i].id.replace('font-', ''); }
  function syncPicks() {
    var on = {};
    fontInputs.forEach(function (x) { on[x.value] = x.checked; });
    $$('.sg-type__pick').forEach(function (b) { b.setAttribute('aria-pressed', on[b.getAttribute('data-font')] ? 'true' : 'false'); });
    thumbs.forEach(function (t, i) { t.classList.toggle('is-picked', !!on[fontOf(i)]); });
    $$('.sg-whole__item').forEach(function (a) { a.classList.toggle('is-picked', !!on[a.getAttribute('data-font')]); });
  }
  if (viewer && panels.length) {
    var img = $('.sg-type__img', viewer), big = $('.sg-type__big', viewer), now = $('.sg-type__now', viewer);
    var stage = $('.sg-type__stage', viewer), cur = 0;
    var show = function (i) {
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
      [i + 1, i - 1].forEach(function (k) {        // 前後の案の画像を先に読んでおく
        var q = panels[(k + panels.length) % panels.length];
        (new Image()).src = q.getAttribute('data-zoom');
      });
    };
    var fromHash = function () {      // 「#font-05」のようなアドレスで開いたときは、その案を出す
      var m = location.hash.match(/^#font-(\d+)$/);
      return m ? panels.map(function (p) { return p.id; }).indexOf('font-' + m[1]) : -1;
    };
    viewer.classList.add('is-ready');
    show(fromHash() >= 0 ? fromHash() : +(viewer.getAttribute('data-first') || 0));
    window.addEventListener('hashchange', function () { if (fromHash() >= 0) show(fromHash()); });
    $$('.sg-type__step', viewer).forEach(function (b) {
      b.addEventListener('click', function () { show(cur + +b.getAttribute('data-step')); });
    });
    thumbs.forEach(function (t, j) {
      t.addEventListener('click', function (e) {
        e.preventDefault();
        show(j);
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
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) show(cur + (dx < 0 ? 1 : -1));
    }, { passive: true });
    stage.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { show(cur + (e.key === 'ArrowRight' ? 1 : -1)); }
    });
    $$('.sg-type__pick', viewer).forEach(function (b) {
      b.addEventListener('click', function () {
        var x = form && $('input[name=font][value="' + b.getAttribute('data-font') + '"]', form);
        if (!x) return;
        x.checked = !x.checked;
        save(); refresh();
      });
    });
  }
  refresh();

  // ---- たたんだ所（これからの流れ・決まったこと・参考）: 目次などから飛んだときは開く。
  // 「すべて開く」は、決まったこと・参考の中のものだけを開く
  var folds = $$('.sg-fold--group .sg-folds > .sg-fold');
  function openTo(el) {
    for (var d = el.closest ? el.closest('details') : null; d; d = d.parentElement ? d.parentElement.closest('details') : null) d.open = true;
  }
  function openHash(hash) {
    if (!hash || hash.length < 2 || /^#font-/.test(hash)) return;
    var el = null;
    try { el = document.getElementById(decodeURIComponent(hash.slice(1))); } catch (e) { el = null; }
    if (el) openTo(el);
    return el;
  }
  if (openHash(location.hash)) {
    setTimeout(function () { var el = openHash(location.hash); if (el) el.scrollIntoView(); }, 0);
  }
  window.addEventListener('hashchange', function () { openHash(location.hash); });
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
