/* Measures every phone: height, the smallest text, anything that leaves the phone, and the
   pitch of the repeated rows, so each direction states what twenty games actually cost.
   Retries on a timer and on resize, because fonts and logos land after load. */
(function () {
  'use strict';
  function textCheck(ph) {
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
      if (cs.visibility === 'hidden' || el.closest('[aria-hidden="true"]')) continue;
      var size = parseFloat(cs.fontSize);
      if (size < min) min = size;
      if (el.closest('[class*="crawl"]')) continue;
      range.selectNodeContents(node);
      var rects = range.getClientRects();
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i];
        if (r.width && (r.right > box.right + 0.5 || r.left < box.left - 0.5)) { spills.push(node.textContent.trim().slice(0, 24)); break; }
      }
    }
    return { h: Math.round(box.height), min: min, spills: spills };
  }
  function pitch(ph, sel, i) {
    // Games 2 and 3 share a kickoff day, so no day heading sits between them and inflates the pitch.
    // Points rows 1 and 2 sit above the lifted row, whose tilt would move its box.
    var rows = ph.querySelectorAll(sel);
    if (rows.length < i + 2) return null;
    var a = rows[i].getBoundingClientRect(), b = rows[i + 1].getBoundingClientRect();
    return { row: Math.round(a.height), pitch: Math.round(b.top - a.top) };
  }
  var out = {};
  function run() {
    document.querySelectorAll('.pb-dir[data-key]').forEach(function (sec) {
      var key = sec.dataset.key, res = { phones: {} }, min = 99, spills = [];
      sec.querySelectorAll('.pb-phone[data-screen]').forEach(function (ph) {
        var r = textCheck(ph);
        if (!r) return;
        res.phones[ph.dataset.screen] = r;
        min = Math.min(min, r.min);
        spills = spills.concat(r.spills);
        if (ph.dataset.screen === 'winners') res.game = pitch(ph, '[data-m="game"]', 1);
        if (ph.dataset.screen === 'points') res.rank = pitch(ph, '[data-m="rank"]', 0);
      });
      if (!res.phones.winners) return;
      var parts = [];
      if (res.game) parts.push('a game is ' + res.game.row + ' px, so 20 games alone take about ' + (res.game.pitch * 20).toLocaleString('en-US') + ' px (today 3,120)');
      if (res.rank) parts.push('a points row is ' + res.rank.row + ' px');
      parts.push('smallest text ' + min + ' px');
      parts.push(spills.length ? 'text spills: ' + spills[0] : 'nothing runs off the side');
      var el = sec.querySelector('[data-facts]');
      el.textContent = parts.join(' · ');
      el.classList.toggle('is-bad', spills.length > 0 || min < 13);
      res.min = min; res.spills = spills;
      out[key] = res;
    });
    var pre = document.getElementById('pb-measure');
    if (!pre) { pre = document.createElement('pre'); pre.id = 'pb-measure'; pre.hidden = true; document.body.appendChild(pre); }
    pre.textContent = JSON.stringify(out);
  }
  [120, 900, 2200, 4800].forEach(function (ms) { setTimeout(run, ms); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(run);
  var t = null;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(run, 200); });
})();
