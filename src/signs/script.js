// 看板の提案のページ: かんたん診断・「気になる」の印・気になる案を送る（LINE・コピー）・印刷。
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // ---- かんたん診断: 予算・いちばん大事なこと・置ける幅から、合いそうな案（3つまで）に印を付ける
  var quiz = $('.sg-quiz'), cards = $$('.sg-g'), result = $('.sg-quiz__result'), reset = $('.sg-quiz__reset');
  var NAMES = {};
  cards.forEach(function (c) { NAMES[c.getAttribute('data-no')] = $('.sg-g__name', c).textContent; });
  function val(name) { var x = $('input[name="' + name + '"]:checked', quiz); return x ? x.value : ''; }
  function diagnose() {
    var budget = val('budget'), priority = val('priority'), space = val('space');
    var answered = budget || priority || space;
    reset.hidden = !answered;
    cards.forEach(function (c) { c.classList.remove('is-match', 'is-dim'); $('.sg-g__match', c).hidden = true; });
    if (!answered) { result.textContent = ''; return; }
    var list = cards.map(function (c) {
      var d = function (k) { return parseFloat(c.getAttribute('data-' + k)); };
      return { el: c, no: c.getAttribute('data-no'), min: d('min'), width: d('width'),
               score: priority === 'cheap' ? -d('min') : (priority ? d(priority) * 10 - d('min') / 10 : -d('min') / 10) };
    });
    var ok = list.filter(function (x) {
      if (budget && x.min > parseFloat(budget)) return false;      // 相場の下の値が予算を超える案は外す
      if (space === 'narrow' && x.width > 300) return false;       // 狭いときは幅30cmまでの案だけ
      return true;
    });
    ok.sort(function (a, b) { return b.score - a.score; });
    var top = ok.slice(0, 3);
    if (!top.length) {
      result.textContent = 'この条件に合う案は見つかりませんでした。予算か置ける幅を変えてみてください。';
      return;
    }
    top.forEach(function (x) { x.el.classList.add('is-match'); $('.sg-g__match', x.el).hidden = false; });
    list.forEach(function (x) { if (top.indexOf(x) < 0) x.el.classList.add('is-dim'); });
    result.textContent = '合いそうなのは ' + top.map(function (x) { return '案' + x.no + '「' + NAMES[x.no] + '」'; }).join('・') + ' です。' +
      (space === 'unknown' ? '（置ける幅は、入口の前のすき間を測ってから確かめましょう）' : '');
  }
  if (quiz) {
    quiz.addEventListener('change', diagnose);
    quiz.addEventListener('reset', function () { setTimeout(diagnose, 0); });
  }

  // ---- 気になる案: 一覧・くわしい説明の「気になる」と、送るフォームのチェックをそろえ、この端末に残す
  var KEY = 'xiii-sign-picks', form = $('.sg-send');
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { saved = {}; }
  function save() {
    var data = { picks: $$('input[name=pick]:checked', form).map(function (x) { return x.value; }) };
    var b = $('input[name=pick_budget]:checked', form);
    if (b) data.budget = b.value;
    data.space = form.elements.space.value;
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
    var b = $('input[name=pick_budget]:checked', form);
    var lines = ['【看板の提案への返事】', '', '気になる案：', picks.length ? picks.join('\n') : '・（まだ選んでいません）'];
    if (b) lines.push('', '予算：' + b.value);
    if (form.elements.space.value.trim()) lines.push('入口の前に置ける幅：' + form.elements.space.value.trim());
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
    if (saved.budget) { var bx = $('input[name=pick_budget][value="' + saved.budget + '"]', form); if (bx) bx.checked = true; }
    form.elements.space.value = saved.space || '';
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
