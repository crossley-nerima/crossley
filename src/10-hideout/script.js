// 案10：照らす丸を、マウス・指の位置に動かす。しばらく触らなければ、ゆっくり漂う。
// 場面（section）が変わったら、後ろの写真を切り替える。「明かりをつける」で全体を明るくする。
(function () {
  var root = document.documentElement;
  var body = document.body;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var lastMove = 0;
  var btn = document.querySelector('.lights');

  function setLights(on) {
    body.classList.toggle('lights-on', on);
    if (btn) {
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.textContent = on ? '明かりを消す' : '明かりをつける';
    }
  }
  if (btn) btn.addEventListener('click', function () { setLights(!body.classList.contains('lights-on')); });
  // 動きを減らす設定の人には、はじめから明かりをつけておく（漂う動きもしない）。
  if (reduce) setLights(true);

  function aim(x, y) {
    root.style.setProperty('--x', x + 'px');
    root.style.setProperty('--y', y + 'px');
    lastMove = performance.now();
  }
  window.addEventListener('pointermove', function (e) { aim(e.clientX, e.clientY); }, { passive: true });
  window.addEventListener('touchmove', function (e) { var t = e.touches[0]; if (t) aim(t.clientX, t.clientY); }, { passive: true });
  window.addEventListener('touchstart', function (e) { var t = e.touches[0]; if (t) aim(t.clientX, t.clientY); }, { passive: true });

  if (!reduce) {
    (function drift(now) {
      if (now - lastMove > 2500) {
        var w = window.innerWidth, h = window.innerHeight, s = now / 1000;
        root.style.setProperty('--x', (w * (0.5 + 0.28 * Math.sin(s * 0.35))) + 'px');
        root.style.setProperty('--y', (h * (0.48 + 0.22 * Math.sin(s * 0.53 + 1))) + 'px');
      }
      requestAnimationFrame(drift);
    })(0);
  }

  var imgs = document.querySelectorAll('.stage img');
  function show(name) {
    imgs.forEach(function (img) { img.classList.toggle('is-on', img.getAttribute('data-scene') === name); });
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) show(en.target.getAttribute('data-scene')); });
    }, { rootMargin: '-45% 0px -45% 0px' });
    document.querySelectorAll('[data-scene]').forEach(function (s) { if (s.tagName !== 'IMG') io.observe(s); });
  }
})();
