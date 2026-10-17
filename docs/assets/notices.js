// お知らせ（臨時休業・臨時営業）と、「いま営業中か」の計算。全案のページで読む（docs/assets/notices.js）。
// 営業時間・定休日・お知らせは、build.py が site.json から <script id="hours-data"> に入れて渡す。
// 明け方（閉店の時刻まで）は、前の日の夜の営業の続きとして数える。この「前の日」を営業日と呼ぶ。
(function () {
  var el = document.getElementById('hours-data');
  if (!el) return;
  var data = JSON.parse(el.textContent);
  var WEEK = ['日', '月', '火', '水', '木', '金', '土'];

  function jstNow() {
    var p = {};
    new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
    }).formatToParts(new Date()).forEach(function (x) { p[x.type] = x.value; });
    return { date: p.year + '-' + p.month + '-' + p.day, min: parseInt(p.hour, 10) * 60 + parseInt(p.minute, 10) };
  }
  function addDays(d, n) {
    var t = new Date(d + 'T00:00:00Z');
    t.setUTCDate(t.getUTCDate() + n);
    return t.toISOString().slice(0, 10);
  }
  function weekday(d) { return new Date(d + 'T00:00:00Z').getUTCDay(); }
  function toMin(s) { var a = s.split(':'); return parseInt(a[0], 10) * 60 + parseInt(a[1], 10); }
  function fmtTime(min) { var m = min % 1440; return Math.floor(m / 60) + ':' + ('0' + (m % 60)).slice(-2); }
  function fmtDate(d) { var a = d.split('-'); return parseInt(a[1], 10) + '月' + parseInt(a[2], 10) + '日（' + WEEK[weekday(d)] + '）'; }

  // 営業日 d に効くお知らせ（臨時休業・臨時営業）
  function noticeOn(d) {
    for (var i = 0; i < data.notices.length; i++) {
      var n = data.notices[i];
      if (n.from <= d && d <= n.until && (n.type === 'closed' || n.type === 'open')) return n;
    }
    return null;
  }
  // 営業日 d の夜の営業（開く・閉まる時刻を、その日の 0:00 からの分で）。休みなら null。
  function session(d) {
    var n = noticeOn(d);
    if (n && n.type === 'closed') return null;
    if (!n && data.closedDays.indexOf(weekday(d)) >= 0) return null;
    var o = toMin((n && n.open) || data.open), c = toMin((n && n.close) || data.close);
    if (c <= o) c += 1440;
    return { open: o, close: c, notice: n };
  }
  function businessDate(now) { return now.min < toMin(data.close) ? addDays(now.date, -1) : now.date; }

  // いまの状態。state: open（営業中）/ before（きょうこのあと開く）/ closed（きょうは開かない）
  function status() {
    var now = jstNow();
    var sy = session(addDays(now.date, -1)), st = session(now.date);
    if (sy && now.min + 1440 < sy.close) return { state: 'open', until: fmtTime(sy.close), morning: true, notice: sy.notice };
    if (st && now.min >= st.open && now.min < st.close) {
      return { state: 'open', until: fmtTime(st.close), morning: st.close >= 1440, notice: st.notice };
    }
    var today = noticeOn(now.date);
    var why = today && today.type === 'closed' ? 'notice' : (data.closedDays.indexOf(weekday(now.date)) >= 0 ? 'regular' : '');
    for (var i = 0; i < 15; i++) {
      var d = addDays(now.date, i), s = session(d);
      if (s && (i > 0 || now.min < s.open)) {
        return {
          state: i === 0 ? 'before' : 'closed', why: why, notice: i === 0 ? s.notice : today,
          next: { label: i === 0 ? '本日' : (i === 1 ? '明日' : fmtDate(d)), time: fmtTime(s.open), special: !!s.notice }
        };
      }
    }
    return { state: 'closed', why: why, notice: today };
  }

  // 日付が過ぎたお知らせを隠す。1つも残らなければ、お知らせの欄ごと隠す。
  var bd = businessDate(jstNow());
  Array.prototype.forEach.call(document.querySelectorAll('[data-notices]'), function (box) {
    var left = 0;
    Array.prototype.forEach.call(box.querySelectorAll('li'), function (li) {
      var until = li.getAttribute('data-until');  // 見本には付いていないので、消えない
      if (until && until < bd) li.hidden = true; else left++;
    });
    if (!left) box.hidden = true;
  });

  window.xiiiHours = { status: status, noticeOn: noticeOn, fmtDate: fmtDate };
})();
