// 案09：日本時間で「いま営業中か」を出し、営業時間の表で今日の行に印を付け、住所をコピーできるようにする。
(function () {
  var parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Tokyo', weekday: 'short', hour: 'numeric', hourCycle: 'h23' })
    .formatToParts(new Date());
  var day = parts.find(function (p) { return p.type === 'weekday'; }).value;
  var hour = parseInt(parts.find(function (p) { return p.type === 'hour'; }).value, 10);

  // 営業は 19:00〜翌7:00、日曜定休。明け方（0〜7時）は前の日の夜の続き。
  // 土曜の夜は日曜の朝7時まで開いている前提（お店に確認中）。
  var openNight = day !== 'Sun' && hour >= 19;
  var openMorning = day !== 'Mon' && hour < 7;
  var isOpen = openNight || openMorning;

  var box = document.querySelector('.status');
  if (box) {
    var title = box.querySelector('b');
    var sub = box.querySelector('.status__text span');
    box.setAttribute('data-state', isOpen ? 'open' : 'closed');
    if (isOpen) {
      title.textContent = '営業中';
      sub.textContent = '朝7:00まで開いています';
    } else if (day === 'Sun' && hour >= 7) {
      title.textContent = '本日は定休日';
      sub.textContent = '月曜 19:00 から営業します';
    } else {
      title.textContent = '準備中';
      sub.textContent = '本日 19:00 から営業します';
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
