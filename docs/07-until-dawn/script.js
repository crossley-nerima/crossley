// 案07：スクロールの位置で、空の色・星の明るさ・時計（19:00 → 7:00）を変える。
(function () {
  var root = document.documentElement;
  var timeEl = document.querySelector('.clock__time');
  var labelEl = document.querySelector('.clock__label');
  var barEl = document.querySelector('.clock');
  var dawnAt = document.querySelector('.morning');

  // 空の色の段階（上の色・下の色）。0 が開店、1 が朝7時。
  var stops = [
    [0.00, [58, 34, 96], [224, 122, 95]],
    [0.10, [34, 24, 74], [92, 46, 96]],
    [0.30, [10, 11, 32], [16, 18, 52]],
    [0.62, [6, 7, 18], [12, 15, 38]],
    [0.82, [40, 38, 92], [140, 84, 128]],
    [0.94, [246, 176, 140], [255, 222, 196]],
    [1.00, [255, 236, 214], [255, 246, 236]]
  ];

  function mix(a, b, t) { return a.map(function (v, i) { return Math.round(v + (b[i] - v) * t); }); }
  function color(p, side) {
    for (var i = 1; i < stops.length; i++) {
      if (p <= stops[i][0]) {
        var t = (p - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
        return 'rgb(' + mix(stops[i - 1][side], stops[i][side], t).join(',') + ')';
      }
    }
    return 'rgb(' + stops[stops.length - 1][side].join(',') + ')';
  }

  var ticking = false;
  function update() {
    ticking = false;
    // 朝の案内に入るところを「7:00」にする（そこから下は朝）。
    var end = dawnAt ? dawnAt.offsetTop - window.innerHeight * 0.4 : document.body.scrollHeight - window.innerHeight;
    var p = Math.max(0, Math.min(1, window.scrollY / Math.max(1, end)));
    root.style.setProperty('--sky-top', color(p, 1));
    root.style.setProperty('--sky-bottom', color(p, 2));
    root.style.setProperty('--stars', String(Math.max(0, 1 - Math.abs(p - 0.5) * 2.4).toFixed(2)));
    var minutes = (19 * 60 + Math.round(p * 12 * 60 / 10) * 10) % (24 * 60);
    var h = Math.floor(minutes / 60), m = minutes % 60;
    if (timeEl) timeEl.textContent = h + ':' + (m < 10 ? '0' : '') + m;
    if (labelEl) labelEl.textContent = p >= 1 ? 'CLOSE' : (p < 0.02 ? 'OPEN' : 'TONIGHT');
    if (barEl) barEl.style.setProperty('--p', Math.round(p * 100) + '%');
  }
  function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(update); } }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  update();
})();
