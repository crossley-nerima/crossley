// 看板のポスターの提案のページ: かんたん診断・「気になる」の印・気になる案と値段を送る（LINE・コピー）・印刷。
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // ---- かんたん診断: いちばん大事なこと・好きな色・写真の量から、合いそうな案（3つまで）に印を付ける
  var quiz = $('.sg-quiz'), cards = $$('.sg-g'), result = $('.sg-quiz__result'), reset = $('.sg-quiz__reset');
  var NAMES = {};
  cards.forEach(function (c) { NAMES[c.getAttribute('data-no')] = $('.sg-g__name', c).textContent; });
  function val(name) { var x = $('input[name="' + name + '"]:checked', quiz); return x ? x.value : ''; }
  function diagnose() {
    var priority = val('priority'), tone = val('tone'), photo = val('photo');
    var answered = priority || tone || photo;
    reset.hidden = !answered;
    cards.forEach(function (c) { c.classList.remove('is-match', 'is-dim'); $('.sg-g__match', c).hidden = true; });
    if (!answered) { result.textContent = ''; return; }
    var list = cards.map(function (c) {
      var d = function (k) { return c.getAttribute('data-' + k); };
      // 色の好みは、大事なことの1段階より少し重く見る（好きな色の案が、上位に入るように）
      var score = (priority ? parseFloat(d(priority)) * 10 : 0)
        + (tone && tone !== 'any' && d('tone') === tone ? 12 : 0)
        + (photo && photo !== 'any' && d('photo') === photo ? 5 : 0)
        + (parseFloat(d('notice')) + parseFloat(d('mood')) + parseFloat(d('price'))) / 10;   // 同じ点なら、全体に強い案を先に
      return { el: c, no: d('no'), score: score };
    });
    list.sort(function (a, b) { return b.score - a.score; });
    var top = list.slice(0, 3);
    top.forEach(function (x) { x.el.classList.add('is-match'); $('.sg-g__match', x.el).hidden = false; });
    list.slice(3).forEach(function (x) { x.el.classList.add('is-dim'); });
    result.textContent = '合いそうなのは ' + top.map(function (x) { return '案' + x.no + '「' + NAMES[x.no] + '」'; }).join('・') + ' です。';
  }
  if (quiz) {
    quiz.addEventListener('change', diagnose);
    quiz.addEventListener('reset', function () { setTimeout(diagnose, 0); });
  }

  // ---- 気になる案: 一覧・くわしい説明の「気になる」と、送るフォームのチェックをそろえ、この端末に残す
  var KEY = 'xiii-poster-picks', form = $('.sg-send');
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { saved = {}; }
  var priceInputs = form ? $$('input[name^="price_"]', form) : [];
  function save() {
    var data = { picks: $$('input[name=pick]:checked', form).map(function (x) { return x.value; }), prices: {} };
    var f = $('input[name=frame]:checked', form);
    if (f) data.frame = f.value;
    priceInputs.forEach(function (x) { if (x.value.trim()) data.prices[x.name] = x.value; });
    data.note = form.elements.note.value;
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) { /* 残せなくても送れる */ }
  }
  function syncButtons() {
    var picked = $$('input[name=pick]:checked', form).map(function (x) { return x.value; });
    $$('.sg-pick').forEach(function (b) {
      var on = picked.indexOf(b.getAttribute('data-pick')) >= 0;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      $('.sg-pick__label', b).textContent = on ? '気になる 済' : '気になる';
    });
  }
  function message() {
    var picks = $$('input[name=pick]:checked', form).map(function (x) { return '・' + x.getAttribute('data-label'); });
    var lines = ['【看板のポスターの提案への返事】', '', '気になる案：', picks.length ? picks.join('\n') : '・（まだ選んでいません）'];
    var f = $('input[name=frame]:checked', form);
    if (f) lines.push('', 'スタンドの枠の色：' + f.value);
    var prices = priceInputs.filter(function (x) { return x.value.trim(); })
      .map(function (x) { return '・' + x.getAttribute('data-label') + '：' + x.value.trim(); });
    if (prices.length) lines.push('', 'ポスターに入れる値段：', prices.join('\n'));
    if (form.elements.note.value.trim()) lines.push('', 'ひとこと：' + form.elements.note.value.trim());
    lines.push('', '（ダイニングバー XⅢ クロスリー）');
    return lines.join('\n');
  }
  function refresh() {
    var m = message();
    $('.sg-send__preview', form).textContent = m;
    $('.sg-send__line', form).href = 'https://line.me/R/share?text=' + encodeURIComponent(m);
  }
  if (form) {
    (saved.picks || []).forEach(function (no) { var x = $('input[name=pick][value="' + no + '"]', form); if (x) x.checked = true; });
    if (saved.frame) { var fx = $('input[name=frame][value="' + saved.frame + '"]', form); if (fx) fx.checked = true; }
    priceInputs.forEach(function (x) { x.value = (saved.prices || {})[x.name] || ''; });
    form.elements.note.value = saved.note || '';
    form.addEventListener('input', function () { save(); syncButtons(); refresh(); });
    form.addEventListener('change', function () { save(); syncButtons(); refresh(); });
    $$('.sg-pick').forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.preventDefault();
        var x = $('input[name=pick][value="' + b.getAttribute('data-pick') + '"]', form);
        x.checked = !x.checked;
        save(); syncButtons(); refresh();
      });
    });
    $('.sg-send__copy', form).addEventListener('click', function () {
      var btn = this;
      if (navigator.clipboard) navigator.clipboard.writeText(message()).then(function () {
        btn.textContent = 'コピーしました'; setTimeout(function () { btn.textContent = '文面をコピー'; }, 2000);
      });
    });
    syncButtons(); refresh();
  }

  // ---- 印刷・PDF（印刷用の見た目は style.css の @media print）
  $$('.sg-print').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });
})();
