// 看板のポスター（仕上がり）のページ: 返事を送る（このまま印刷してOK か、直してほしいところ。LINE・コピー）・印刷。
// 値段の欄は、まだ決まっていない値段があるときだけ出る（そのときは、送る文面にも入る）。
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // ---- 返事を送る: 書いた内容はこの端末に残す（10案から選んでいたときとは、別の名前で残す）
  var KEY = 'xiii-poster-final-reply', form = $('.sg-send');
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { saved = {}; }
  var priceInputs = form ? $$('input[name^="price_"]', form) : [];
  function save() {
    var data = { prices: {} };
    var ok = $('input[name=ok]:checked', form);
    if (ok) data.ok = ok.value;
    priceInputs.forEach(function (x) { if (x.value.trim()) data.prices[x.name] = x.value; });
    data.note = form.elements.note.value;
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) { /* 残せなくても送れる */ }
  }
  function message() {
    var ok = $('input[name=ok]:checked', form);
    var lines = ['【看板のポスター（仕上がり）への返事】', '', 'この仕上がりで：' + (ok ? ok.value : '（まだ選んでいません）')];
    var prices = priceInputs.filter(function (x) { return x.value.trim(); })
      .map(function (x) { return '・' + x.getAttribute('data-label') + '：' + x.value.trim(); });
    if (prices.length) lines.push('', 'ポスターに入れる値段：', prices.join('\n'));
    if (form.elements.note.value.trim()) lines.push('', '直してほしいところ・ひとこと：', form.elements.note.value.trim());
    lines.push('', '（ダイニングバー XⅢ クロスリー）');
    return lines.join('\n');
  }
  function refresh() {
    var m = message();
    $('.sg-send__preview', form).textContent = m;
    $('.sg-send__line', form).href = 'https://line.me/R/share?text=' + encodeURIComponent(m);
  }
  if (form) {
    if (saved.ok) { var ox = $('input[name=ok][value="' + saved.ok + '"]', form); if (ox) ox.checked = true; }
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
    refresh();
  }

  // ---- 印刷・PDF（印刷用の見た目は style.css の @media print）
  $$('.sg-print').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });
})();
