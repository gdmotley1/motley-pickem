/* Everyone's numbers board: the Pick buttons, option 2's rows that open, the saved pick,
   and the measured facts under every phone. Works with no window.claude at all. */
(function () {
  'use strict';

  var state = { numbers: null, note: '' };
  var db = null;
  var timer = null;
  var results = {};
  var noteEl = document.getElementById('pb-note');
  var saveEl = document.querySelector('[data-save]');

  function say(text) { if (saveEl) saveEl.textContent = text; }

  function render() {
    document.querySelectorAll('.pb-opt[data-n]').forEach(function (opt) {
      var on = state.numbers === Number(opt.dataset.n);
      opt.classList.toggle('is-picked', on);
      var btn = opt.querySelector('.pb-pick');
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.textContent = (on ? 'Picked ' : 'Pick ') + opt.dataset.n;
    });
    var b = document.querySelector('[data-bar="numbers"]');
    if (b) b.textContent = state.numbers == null ? '–' : String(state.numbers);
  }

  function save(delay) {
    if (!db) { say('Not saving on this copy. Send me the number.'); return; }
    say('Saving…');
    clearTimeout(timer);
    timer = setTimeout(function () {
      db.doc('picks/grant')
        .set({ numbers: state.numbers, note: state.note, updatedAt: new Date().toISOString() })
        .then(function () { say('Saved. Tell me in chat when you are done.'); },
          function (err) { say('Could not save (' + ((err && err.code) || 'error') + '). Send me the number.'); });
    }, delay);
  }

  function connect() {
    if (!window.claude || typeof window.claude.use !== 'function') { say('Tap Pick under the one you want.'); return; }
    say('Connecting…');
    window.claude.use('db').then(function (d) {
      if (!d) { say('Saving is off here. Send me the number.'); return; }
      db = d;
      return db.doc('picks/grant').get().then(function (snap) {
        if (!snap.exists) { say('Tap Pick under the one you want. It saves as you go.'); return; }
        var v = snap.data() || {};
        if (typeof v.numbers === 'number') state.numbers = v.numbers;
        if (typeof v.note === 'string') { state.note = v.note; if (noteEl) noteEl.value = v.note; }
        render();
        say('Your saved pick is loaded.');
      });
    }).catch(function () { say('Saving is off here. Send me the number.'); });
  }

  function toggleRow(row) {
    if (!row || row.classList.contains('is-open')) return;
    var open = !row.classList.contains('is-expanded');
    row.classList.toggle('is-expanded', open);
    row.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var row = t.closest('.nb2-row');
    if (row) { toggleRow(row); return; }
    var pick = t.closest('.pb-pick');
    if (!pick) return;
    state.numbers = Number(pick.closest('.pb-opt').dataset.n);
    render();
    save(300);
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    var row = ev.target && ev.target.closest && ev.target.closest('.nb2-row');
    if (!row) return;
    ev.preventDefault();
    toggleRow(row);
  });
  if (noteEl) noteEl.addEventListener('input', function () { state.note = noteEl.value; save(900); });

  /* Height, the smallest text, and any text that leaves its cell or the phone, by glyph
     box. Option 2 is measured with every row open, so its worst case is what gets checked. */
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
      var size = parseFloat(getComputedStyle(el).fontSize);
      if (size < min) min = size;
      var fit = (el.closest('[data-fit]') || ph).getBoundingClientRect();
      range.selectNodeContents(node);
      var rects = range.getClientRects();
      for (var i = 0; i < rects.length; i++) {
        var r = rects[i];
        if (r.width && (r.right > fit.right + 0.5 || r.left < fit.left - 0.5)) { spills.push(node.textContent.trim().slice(0, 30)); break; }
      }
    }
    if (ph.scrollWidth > ph.clientWidth + 1) spills.push('the phone scrolls sideways');
    return { h: Math.round(box.height), min: min, spills: spills };
  }

  function measureOne(opt) {
    var ph = opt.querySelector('.pk-phone');
    var chip = opt.querySelector('[data-facts]');
    var rows = [].slice.call(ph.querySelectorAll('.nb2-row:not(.is-open)'));
    var was = rows.map(function (r) { return r.classList.contains('is-expanded'); });
    rows.forEach(function (r) { r.classList.remove('is-expanded'); });
    var closed = check(ph);
    if (!closed) { rows.forEach(function (r, i) { r.classList.toggle('is-expanded', was[i]); }); return; }
    rows.forEach(function (r) { r.classList.add('is-expanded'); });
    var keep = ph.style.width;
    var wide = check(ph);
    ph.style.width = '375px';
    var narrow = check(ph);
    ph.style.width = keep;
    rows.forEach(function (r, i) { r.classList.toggle('is-expanded', was[i]); });
    var spills = wide.spills.concat(narrow ? narrow.spills : []);
    var min = Math.min(wide.min, narrow ? narrow.min : 99);
    var tall = rows.length ? closed.h.toLocaleString('en-US') + ' px tall with every row closed, ' + wide.h.toLocaleString('en-US') + ' with all open'
      : closed.h.toLocaleString('en-US') + ' px tall';
    chip.textContent = tall + ' · smallest text ' + min + ' px · ' +
      (spills.length ? 'text spills: ' + spills[0] : 'fits a 375 or 390 wide phone');
    chip.classList.toggle('is-bad', spills.length > 0 || min < 13);
    results[opt.dataset.n || 'now'] = { h: closed.h, hOpen: rows.length ? wide.h : null, h375: narrow && narrow.h, min: min, spills: spills };
  }

  function remeasure() {
    document.querySelectorAll('.pb-opt').forEach(measureOne);
    var out = document.getElementById('pb-measure');
    if (out) out.textContent = JSON.stringify(results);
  }

  render();
  connect();
  [60, 400, 1500, 4000].forEach(function (ms) { setTimeout(remeasure, ms); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(remeasure);
  var rt = null;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(remeasure, 150); });
})();
