/* Measures every phone: height, the smallest text, and anything that leaves the phone.
   Retries on a timer and on resize, because fonts and logos land after load. */
(function () {
  'use strict';
  function check(ph) {
    var box = ph.getBoundingClientRect();
    if (box.width < 300) return null;
    var min = 99, spills = [];
    var walker = document.createTreeWalker(ph, NodeFilter.SHOW_TEXT, null);
    var range = document.createRange();
    while (walker.nextNode()) {
      var node = walker.currentNode;
      if (!node.textContent.trim()) continue;
      var el = node.parentElement;
      if (!el || !el.getClientRects().length) continue;
      var cs = getComputedStyle(el);
      if (cs.visibility === 'hidden') continue;
      var size = parseFloat(cs.fontSize);
      if (size < min) min = size;
      if (el.closest('[class*="crawl"], [class*="ticker"]')) continue;
      range.selectNodeContents(node);
      var rects = range.getClientRects();
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i];
        if (r.width && (r.right > box.right + 0.5 || r.left < box.left - 0.5)) { spills.push(node.textContent.trim().slice(0, 24)); break; }
      }
    }
    return { h: Math.round(box.height), top: Math.round(box.top + window.scrollY), left: Math.round(box.left), min: min, spills: spills };
  }
  var out = {};
  function run() {
    document.querySelectorAll('.bb-dir').forEach(function (sec) {
      var ph = sec.querySelector('.bb-phone');
      var r = check(ph);
      if (!r) return;
      var el = sec.querySelector('[data-facts]');
      el.textContent = r.h.toLocaleString('en-US') + ' px tall on a 390 px phone · smallest text ' + r.min + ' px · ' +
        (r.spills.length ? 'text spills: ' + r.spills[0] : 'nothing runs off the side');
      el.classList.toggle('is-bad', r.spills.length > 0 || r.min < 13);
      out[ph.dataset.key] = r;
    });
    var pre = document.getElementById('bb-measure');
    if (!pre) { pre = document.createElement('pre'); pre.id = 'bb-measure'; pre.hidden = true; document.body.appendChild(pre); }
    pre.textContent = JSON.stringify(out);
  }
  [100, 800, 2000, 4500].forEach(function (ms) { setTimeout(run, ms); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(run);
  var t = null;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(run, 200); });
})();
