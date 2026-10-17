// 提案のときだけ読み込む。「10案を切り替え」の一覧を、外を押したとき・Esc で閉じる（開け閉め自体は details が行う）。
(function () {
  var sw = document.querySelector('.pp-switch');
  if (!sw) return;
  document.addEventListener('click', function (e) {
    if (sw.open && !sw.contains(e.target)) sw.open = false;
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sw.open) {
      sw.open = false;
      sw.querySelector('summary').focus();
    }
  });
})();
