// 案09：日本時間で「いま営業中か」を出し、営業時間の表で今日の行に印を付け、住所をコピーできるようにする。
(function () {
  var day = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Tokyo', weekday: 'short' }).format(new Date());

  // 「いま営業中か」は全案共通の計算（assets/notices.js）に任せる。臨時休業・臨時営業のお知らせも見て決める。
  var box = document.querySelector('.status');
  var st = window.xiiiHours && window.xiiiHours.status();
  if (box && st) {
    var title = box.querySelector('b');
    var sub = box.querySelector('.status__text span');
    box.setAttribute('data-state', st.state === 'open' ? 'open' : 'closed');
    var next = st.next ? st.next.label + ' ' + st.next.time + ' から' + (st.next.special ? '臨時営業します' : '営業します') : '';
    if (st.state === 'open') {
      title.textContent = st.notice ? '営業中（臨時営業）' : '営業中';
      sub.textContent = (st.morning ? '朝' : '') + st.until + 'まで開いています';
    } else if (st.state === 'before') {
      title.textContent = st.notice ? '本日は臨時営業' : '準備中';
      sub.textContent = next;
    } else {
      title.textContent = st.why === 'notice' ? '本日は臨時休業' : (st.why === 'regular' ? '本日は定休日' : '本日の営業は終了しました');
      sub.textContent = next;
    }
  }

  var row = document.querySelector('.hours tr[data-day="' + day + '"]');
  if (row) row.classList.add('is-today');

  var copy = document.querySelector('.copy');
  if (copy && navigator.clipboard) {
    copy.addEventListener('click', function () {
      navigator.clipboard.writeText(copy.getAttribute('data-text')).then(function () {
        copy.textContent = 'コピーしました';
        setTimeout(function () { copy.textContent = '住所をコピー'; }, 2000);
      });
    });
  } else if (copy) {
    copy.hidden = true;
  }
})();
