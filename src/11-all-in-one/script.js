// 案11：機能モリモリ版の動き。営業中の表示・一杯診断・メニューの絞り込み・営業カレンダー・予約の文面・写真の拡大・友だちに送る。
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var WEEK = ['日', '月', '火', '水', '木', '金', '土'];
  var json = function (sel, fallback) { var el = $(sel); try { return el ? JSON.parse(el.textContent) : fallback; } catch (e) { return fallback; } };
  var hours = json('#hours-data', { open: '19:00', close: '07:00', closedDays: [0], notices: [] });
  var notices = json('#data-notices', []);  // 見本も入っている（カレンダーで「見本」と出す）
  var pad = function (n) { return ('0' + n).slice(-2); };
  var iso = function (y, m, d) { return y + '-' + pad(m) + '-' + pad(d); };
  var dow = function (d) { return new Date(d + 'T00:00:00Z').getUTCDay(); };
  var fmtDate = function (d) { var a = d.split('-'); return parseInt(a[1], 10) + '月' + parseInt(a[2], 10) + '日（' + WEEK[dow(d)] + '）'; };
  function jstToday() {
    var p = {};
    new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' })
      .formatToParts(new Date()).forEach(function (x) { p[x.type] = x.value; });
    return { y: +p.year, m: +p.month, d: +p.day, date: p.year + '-' + p.month + '-' + p.day };
  }
  function noticeOn(d) {
    for (var i = 0; i < notices.length; i++) {
      var n = notices[i];
      if (n.from <= d && d <= n.until && (n.type === 'closed' || n.type === 'open')) return n;
    }
    return null;
  }
  // その日（の夜）の営業: { state: open / closed / off（臨時休業）/ extra（臨時営業）, sample }
  function dayState(d) {
    var n = noticeOn(d);
    if (n) return { state: n.type === 'closed' ? 'off' : 'extra', sample: n.sample };
    return { state: hours.closedDays.indexOf(dow(d)) >= 0 ? 'closed' : 'open' };
  }
  var today = jstToday();

  // 1. いま営業中か（計算は全案共通の assets/notices.js）
  var box = $('.status'), st = window.xiiiHours && window.xiiiHours.status();
  if (box && st) {
    var next = st.next ? st.next.label + ' ' + st.next.time + ' から' + (st.next.special ? '臨時営業します' : '営業します') : '';
    box.setAttribute('data-state', st.state === 'open' ? 'open' : 'closed');
    $('b', box).textContent = st.state === 'open' ? (st.notice ? '営業中（臨時営業）' : '営業中')
      : st.state === 'before' ? (st.notice ? '本日は臨時営業' : '準備中')
      : st.why === 'notice' ? '本日は臨時休業' : st.why === 'regular' ? '本日は定休日' : '本日の営業は終了しました';
    $('.status__text span', box).textContent = st.state === 'open' ? (st.morning ? '朝' : '') + st.until + 'まで開いています' : next;
  }

  // 2. 今夜の一杯診断
  var guide = json('#data-cocktail_guide', []), ff = $('.finder__form'), out = $('.finder__result');
  function showDrinks() {
    var t = ff.elements.taste.value, s = ff.elements.strength.value;
    out.textContent = '';
    guide.filter(function (g) { return g.taste === t && g.strength === s; }).forEach(function (g) {
      var d = document.createElement('div'), b = document.createElement('b'), sm = document.createElement('small'), p = document.createElement('p');
      d.className = 'drink'; b.textContent = g.name; sm.textContent = 'ベース：' + g.base; p.textContent = g.note;
      d.appendChild(b); d.appendChild(sm); d.appendChild(p); out.appendChild(d);
    });
  }
  if (ff && out) { ff.addEventListener('change', showDrinks); ff.addEventListener('submit', function (e) { e.preventDefault(); }); showDrinks(); }

  // 3. メニューの絞り込み（種類）と検索（名前）
  var menu = $('.menu'), tabs = $('.menu-tabs'), search = $('.menu-search input'), empty = $('.menu-empty');
  if (menu && tabs && search) {
    var cats = $$('.menu__cat', menu), current = 'all';
    var addTab = function (id, label) {
      var b = document.createElement('button');
      b.type = 'button'; b.textContent = label; b.setAttribute('data-cat', id); b.setAttribute('aria-pressed', id === 'all' ? 'true' : 'false');
      tabs.appendChild(b);
    };
    addTab('all', 'すべて');
    cats.forEach(function (c) { addTab(c.id, $('.menu__title', c).firstChild.textContent.trim()); });
    var apply = function () {
      var q = search.value.trim().toLowerCase(), any = false;
      cats.forEach(function (c) {
        var lis = $$('.menu__items li', c), shown = 0;
        var catHit = q && $('.menu__title', c).textContent.toLowerCase().indexOf(q) >= 0;
        lis.forEach(function (li) { var hit = !q || catHit || li.textContent.toLowerCase().indexOf(q) >= 0; li.hidden = !hit; if (hit) shown++; });
        c.hidden = !((current === 'all' || c.id === current) && shown > 0);
        if (!c.hidden) any = true;
      });
      if (empty) empty.hidden = any;
    };
    tabs.addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      current = b.getAttribute('data-cat');
      $$('button', tabs).forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
    search.addEventListener('input', apply);
  }

  // 4. 営業カレンダー（今月から3か月先まで）
  var cal = $('.cal');
  if (cal) {
    var view = { y: today.y, m: today.m }, tbody = $('tbody', cal), title = $('.cal__title', cal), note = $('.cal__note', cal);
    var prev = $('.cal__prev', cal), nextBtn = $('.cal__next', cal);
    var monthsAhead = function () { return (view.y - today.y) * 12 + (view.m - today.m); };
    var LABEL = { off: '臨時休業', extra: '臨時営業', closed: '定休日', open: '' };
    var render = function () {
      title.textContent = view.y + '年' + view.m + '月';
      var days = new Date(Date.UTC(view.y, view.m, 0)).getUTCDate();
      var lead = (new Date(Date.UTC(view.y, view.m - 1, 1)).getUTCDay() + 6) % 7;  // 月曜はじまり
      var html = '', cells = 0;
      for (var i = 0; i < lead; i++, cells++) html += (cells % 7 === 0 ? '<tr>' : '') + '<td class="is-blank"></td>';
      for (var d = 1; d <= days; d++, cells++) {
        var ds = iso(view.y, view.m, d), s = dayState(ds);
        var cls = 'is-' + s.state + (s.sample ? ' is-sample' : '') + (ds === today.date ? ' is-today' : '');
        html += (cells % 7 === 0 ? '<tr>' : '') + '<td class="' + cls + '"><span>' + d + '</span>' + (LABEL[s.state] ? '<small>' + LABEL[s.state] + '</small>' : '') + '</td>' + (cells % 7 === 6 ? '</tr>' : '');
      }
      while (cells % 7) { html += '<td class="is-blank"></td>' + (cells % 7 === 6 ? '</tr>' : ''); cells++; }
      tbody.innerHTML = html;
      prev.disabled = monthsAhead() <= 0;
      nextBtn.disabled = monthsAhead() >= 3;
      var first = iso(view.y, view.m, 1), last = iso(view.y, view.m, days);
      var ns = notices.filter(function (n) { return n.from <= last && n.until >= first; });
      note.textContent = ns.map(function (n) {
        return fmtDate(n.from) + (n.until !== n.from ? '〜' + fmtDate(n.until) : '') + '：' + n.text + (n.sample ? '（見本）' : '');
      }).join('　');
      if (!ns.length) {
        // この月に無ければ、先の月のお知らせを案内する（「›」で進めば見られる）
        var later = notices.filter(function (n) { return n.from > last; })[0];
        if (later) note.textContent = parseInt(later.from.split('-')[1], 10) + '月に臨時休業・臨時営業のお知らせがあります（「›」で進めます）' + (later.sample ? '。いまは見本です' : '');
      }
    };
    prev.addEventListener('click', function () { if (--view.m < 1) { view.m = 12; view.y--; } render(); });
    nextBtn.addEventListener('click', function () { if (++view.m > 12) { view.m = 1; view.y++; } render(); });
    render();
  }

  // 5. 予約リクエスト（文面を作って、SMS・コピー・電話で送る。お店に予約の仕組みがなくても使える）
  var rf = $('.reserve');
  if (rf) {
    var telLink = $('a[href^="tel:"]'), tel = telLink ? telLink.getAttribute('href').slice(4) : '';
    var sel = rf.elements.time;
    for (var mi = 19 * 60; mi <= 29 * 60; mi += 30) {
      var o = document.createElement('option'), h = Math.floor(mi / 60) % 24;
      o.textContent = (mi >= 24 * 60 ? '翌' : '') + h + ':' + pad(mi % 60);
      if (mi === 21 * 60) o.selected = true;
      sel.appendChild(o);
    }
    rf.elements.date.min = today.date;
    var msgEl = $('.reserve__msg', rf), dayEl = $('.reserve__day', rf), sms = $('.reserve__sms', rf), lineBtn = $('.reserve__line', rf);
    var build = function () {
      var dv = rf.elements.date.value, e = rf.elements;
      var day = '';
      if (dv) {
        var s = dayState(dv), sample = s.sample ? '（見本のお知らせ）' : '';
        day = s.state === 'closed' ? 'この日は定休日です。別の日をお選びください。' : s.state === 'off' ? 'この日は臨時休業です' + sample + '。' :
          s.state === 'extra' ? 'この日は臨時営業日です' + sample + '。' : 'この日は営業日です（' + hours.open + '〜翌' + parseInt(hours.close, 10) + ':00）。';
      }
      dayEl.textContent = day;
      var msg = '【予約のお願い】\n日にち：' + (dv ? fmtDate(dv) : '（日にちを選んでください）') + '\n時間：' + e.time.value + '\n人数：' + e.people.value +
        '\nお名前：' + (e.name.value || '') + '\nご要望：' + (e.note.value || 'なし') + '\n\nダイニングバー XⅢ クロスリー 様';
      msgEl.value = msg;
      sms.href = tel ? 'sms:' + tel + '?&body=' + encodeURIComponent(msg) : '#';
      // LINE 公式アカウントの ID が決まっていれば、文面を入れた状態で LINE のトークを開く
      if (lineBtn && lineBtn.getAttribute('data-base')) lineBtn.href = lineBtn.getAttribute('data-base') + encodeURIComponent(msg);
    };
    rf.addEventListener('input', build);
    rf.addEventListener('change', build);
    rf.addEventListener('submit', function (e) { e.preventDefault(); });
    $('.reserve__copy', rf).addEventListener('click', function () {
      var b = this;
      if (navigator.clipboard) navigator.clipboard.writeText(msgEl.value).then(function () { b.textContent = 'コピーしました'; setTimeout(function () { b.textContent = '文面をコピー（InstagramのDMなどに）'; }, 2000); });
    });
    build();
  }

  // 6. 写真を押すと大きく表示
  var lb = $('.lightbox');
  if (lb && lb.showModal) {
    var big = $('img', lb);
    $$('.gallery__item').forEach(function (b) {
      b.addEventListener('click', function () {
        var img = $('img', b), set = (img.getAttribute('srcset') || '').split(',');
        big.src = set.length ? set[set.length - 1].trim().split(' ')[0] : img.src;
        big.alt = img.alt;
        lb.showModal();
      });
    });
    $('.lightbox__close', lb).addEventListener('click', function () { lb.close(); });
    lb.addEventListener('click', function (e) { if (e.target === lb) lb.close(); });
  }

  // 7. 友だちに送る（LINE・リンクのコピー・スマホの共有）
  var url = location.href.split('#')[0];
  var line = $('.share-line');
  if (line) line.href = 'https://social-plugins.line.me/lineit/share?url=' + encodeURIComponent(url);
  var sc = $('.share-copy');
  if (sc) sc.addEventListener('click', function () {
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { sc.textContent = 'コピーしました'; setTimeout(function () { sc.textContent = 'リンクをコピー'; }, 2000); });
  });
  var sn = $('.share-native');
  if (sn && navigator.share) {
    sn.hidden = false;
    sn.addEventListener('click', function () { navigator.share({ title: document.title, url: url }).catch(function () {}); });
  }

  // LINE 公式アカウントの ID が決まるまでは、ボタンはページの中の LINE の欄へ（別のタブでは開かない）
  $$('a[href="#line"]').forEach(function (a) { a.removeAttribute('target'); a.removeAttribute('rel'); });

  // お店の方へ：教えてほしいこと（提案のときだけある）。書いた答えをこの端末に残し、まとめた文面を LINE で送ってもらう。
  var qs = $('.qs');
  if (qs) {
    var KEY = 'xiii-shop-answers', form = $('.qs__form', qs), items = $$('.qs__item', qs);
    var countEl = $('.qs__count', qs), lineA = $('.qs__line', qs);
    var fields = function () { return $$('input, textarea', form); };
    // 1問ぶんの答え（選んだもの＋書き足し、または書いた文）。答えていなければ空。
    var answerOf = function (item) {
      var n = item.getAttribute('data-q');
      var picked = $$('input[name="q' + n + '"]:checked', item).map(function (x) { return x.value; });
      var text = $$('input[name="q' + n + '"][type=text], textarea[name="q' + n + '"]', item).map(function (x) { return x.value.trim(); }).join('');
      var note = $$('input[name="q' + n + 'note"]', item).map(function (x) { return x.value.trim(); }).join('');
      return [picked.join('・'), text, note].filter(Boolean).join('／');
    };
    var message = function () {
      var lines = ['【XⅢ クロスリー ホームページ 確認事項の回答】'], done = 0;
      $$('.qs__group', form).forEach(function (g) {
        var part = [];
        $$('.qs__item', g).forEach(function (item) {
          var a = answerOf(item);
          if (!a) return;
          done++;
          var q = $('.qs__q', item).cloneNode(true);
          $('.qs__no', q).remove();
          part.push('Q' + item.getAttribute('data-q') + '. ' + q.textContent.trim(), 'A. ' + a);
        });
        if (part.length) {
          lines.push('', '■ ' + $('legend', g).textContent);
          Array.prototype.push.apply(lines, part);
        }
      });
      lines.push('', '（' + items.length + '問のうち ' + done + '問に回答）');
      return { text: lines.join('\n'), done: done };
    };
    var refresh = function () {
      var m = message();
      countEl.textContent = '全' + items.length + '問のうち、答えたもの ' + m.done + '問';
      lineA.href = 'https://line.me/R/share?text=' + encodeURIComponent(m.text);
      return m;
    };
    var save = function () {
      var data = {};
      fields().forEach(function (x) {
        if (x.type === 'radio' || x.type === 'checkbox') { if (x.checked) (data[x.name] = data[x.name] || []).push(x.value); }
        else if (x.value) data[x.name] = x.value;
      });
      try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) { /* 残せなくても送れる */ }
    };
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { saved = {}; }
    fields().forEach(function (x) {
      var v = saved[x.name];
      if (v === undefined) return;
      if (x.type === 'radio' || x.type === 'checkbox') x.checked = v.indexOf(x.value) >= 0;
      else x.value = v;
    });
    form.addEventListener('input', function () { save(); refresh(); });
    form.addEventListener('change', function () { save(); refresh(); });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    $('.qs__copy', qs).addEventListener('click', function () {
      var btn = this;
      if (navigator.clipboard) navigator.clipboard.writeText(refresh().text).then(function () {
        btn.textContent = 'コピーしました'; setTimeout(function () { btn.textContent = '回答をコピー'; }, 2000);
      });
    });
    $('.qs__clear', qs).addEventListener('click', function () {
      if (!window.confirm('書いた内容をすべて消しますか？')) return;
      form.reset();
      try { localStorage.removeItem(KEY); } catch (e) { /* 何もしない */ }
      refresh();
    });
    refresh();
  }

  // 8. 住所をコピー
  $$('.copy').forEach(function (b) {
    if (!navigator.clipboard) { b.hidden = true; return; }
    b.addEventListener('click', function () {
      navigator.clipboard.writeText(b.getAttribute('data-text')).then(function () { b.textContent = 'コピーしました'; setTimeout(function () { b.textContent = '住所をコピー'; }, 2000); });
    });
  });
})();
