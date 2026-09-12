/* Record Book Picks: the Pick buttons, the assembled tab, the saved picks, and the measured
   facts printed under every phone.

   Works with no window.claude at all (a local file): picks still assemble, nothing saves,
   and the bar says to send the numbers instead. */
(function () {
  'use strict';

  var PARTS = ['numbers', 'fame', 'shame'];
  // Fame and shame open on what Grant picked last session. Numbers has no pick yet.
  var state = { numbers: null, fame: 7, shame: 10, note: '' };
  var db = null;
  var timer = null;
  var results = {};
  var noteEl = document.getElementById('pb-note');
  var saveEl = document.querySelector('[data-save]');

  function say(text) {
    if (saveEl) saveEl.textContent = text;
  }

  /* ------------------------------------------------------------------ picks -- */
  function render() {
    document.querySelectorAll('.pb-opt').forEach(function (opt) {
      var on = state[opt.dataset.part] === Number(opt.dataset.n);
      opt.classList.toggle('is-picked', on);
      var btn = opt.querySelector('.pb-pick');
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.textContent = (on ? 'Picked ' : 'Pick ') + opt.dataset.n;
    });
    PARTS.forEach(function (part) {
      var b = document.querySelector('[data-bar="' + part + '"]');
      if (b) b.textContent = state[part] == null ? '–' : String(state[part]);
    });
    assemble();
  }

  /* The last phone is a copy of whichever options are picked, in tab order. */
  function assemble() {
    PARTS.forEach(function (part) {
      var slot = document.querySelector('[data-slot="' + part + '"]');
      if (!slot) return;
      var n = state[part] == null ? 1 : state[part];
      var src = document.querySelector('.pb-opt[data-n="' + n + '"] .app__page');
      slot.textContent = '';
      if (part === 'numbers' && state.numbers == null) {
        var note = document.createElement('p');
        note.className = 'pb-slotnote';
        note.textContent = 'Showing 1, my pick, until you choose.';
        slot.appendChild(note);
      }
      if (src) {
        Array.prototype.forEach.call(src.childNodes, function (c) {
          slot.appendChild(c.cloneNode(true));
        });
      }
    });
    measureFinal();
  }

  function save(delay) {
    if (!db) {
      say('Not saving on this copy. Send me the numbers.');
      return;
    }
    say('Saving…');
    clearTimeout(timer);
    timer = setTimeout(function () {
      db.doc('picks/grant')
        .set({
          numbers: state.numbers,
          fame: state.fame,
          shame: state.shame,
          note: state.note,
          updatedAt: new Date().toISOString(),
        })
        .then(
          function () {
            say('Saved. Tell me in chat when you are done.');
          },
          function (err) {
            say('Could not save (' + ((err && err.code) || 'error') + '). Send me the numbers.');
          }
        );
    }, delay);
  }

  function connect() {
    if (!window.claude || typeof window.claude.use !== 'function') {
      say('Tap Pick under the ones you want.');
      return;
    }
    say('Connecting…');
    window.claude
      .use('db')
      .then(function (d) {
        if (!d) {
          say('Saving is off here. Send me the numbers.');
          return;
        }
        db = d;
        return db
          .doc('picks/grant')
          .get()
          .then(function (snap) {
            if (!snap.exists) {
              say('Tap Pick under the ones you want. It saves as you go.');
              return;
            }
            var v = snap.data() || {};
            PARTS.forEach(function (k) {
              if (typeof v[k] === 'number') state[k] = v[k];
            });
            if (typeof v.note === 'string') {
              state.note = v.note;
              if (noteEl) noteEl.value = v.note;
            }
            render();
            say('Your saved picks are loaded.');
          });
      })
      .catch(function () {
        say('Saving is off here. Send me the numbers.');
      });
  }

  /* One listener for the whole page, so the copies in the assembled phone work too. */
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var tab = t.closest('.pk5-tab');
    if (tab) {
      var root = tab.closest('.pk5');
      root.querySelectorAll('.pk5-tab').forEach(function (b) {
        var on = b === tab;
        b.classList.toggle('is-on', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      root.querySelectorAll('.pk5-panel').forEach(function (p) {
        p.hidden = p.dataset.who !== tab.dataset.who;
      });
      return;
    }
    var pick = t.closest('.pb-pick');
    if (!pick) return;
    var opt = pick.closest('.pb-opt');
    state[opt.dataset.part] = Number(opt.dataset.n);
    render();
    save(300);
  });

  if (noteEl) {
    noteEl.addEventListener('input', function () {
      state.note = noteEl.value;
      save(900);
    });
  }

  /* --------------------------------------------------------------- measuring -- */
  /* Height, the smallest text, and any text that leaves its cell or the phone. Text is
     measured by its glyph boxes, not its element's, because a nowrap number can overflow a
     cell whose own box never changes. */
  function check(ph) {
    var box = ph.getBoundingClientRect();
    if (box.width < 300) return null;
    var min = 99;
    var spills = [];
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
        if (r.width && (r.right > fit.right + 0.5 || r.left < fit.left - 0.5)) {
          spills.push(node.textContent.trim().slice(0, 30));
          break;
        }
      }
    }
    if (ph.scrollWidth > ph.clientWidth + 1) spills.push('the phone scrolls sideways');
    return { h: Math.round(box.height), min: min, spills: spills };
  }

  /* Option 5 hides three of its four people. Check every one of them, not just the first. */
  function checkAllPanels(ph) {
    var panels = ph.querySelectorAll('.pk5-panel');
    if (!panels.length) return check(ph);
    var was = Array.prototype.map.call(panels, function (p) { return p.hidden; });
    var out = null;
    Array.prototype.forEach.call(panels, function (p, i) {
      Array.prototype.forEach.call(panels, function (q, j) { q.hidden = i !== j; });
      var m = check(ph);
      if (!m) return;
      if (!out) out = { h: m.h, min: m.min, spills: [] };
      out.h = i === 0 ? m.h : out.h;
      out.min = Math.min(out.min, m.min);
      out.spills = out.spills.concat(m.spills);
    });
    Array.prototype.forEach.call(panels, function (p, i) { p.hidden = was[i]; });
    return out;
  }

  function write() {
    var out = document.getElementById('pb-measure');
    if (out) out.textContent = JSON.stringify(results);
  }

  function measureAll() {
    document.querySelectorAll('.pb-opt').forEach(function (opt) {
      var ph = opt.querySelector('.pk-phone');
      var chip = opt.querySelector('[data-facts]');
      var wide = checkAllPanels(ph);
      if (!wide) return;
      var keep = ph.style.width;
      ph.style.width = '375px';
      var narrow = checkAllPanels(ph);
      ph.style.width = keep;
      var spills = wide.spills.concat(narrow ? narrow.spills : []);
      chip.textContent =
        wide.h.toLocaleString('en-US') + ' px tall · smallest text ' + wide.min + ' px · ' +
        (spills.length ? 'text spills: ' + spills[0] : 'fits a 375 or 390 wide phone');
      chip.classList.toggle('is-bad', spills.length > 0 || wide.min < 13);
      results[opt.dataset.n] = { h: wide.h, h375: narrow && narrow.h, min: wide.min, spills: spills };
    });
    write();
  }

  function measureFinal() {
    var ph = document.querySelector('.pk-phone--final');
    var chip = document.querySelector('[data-final-facts]');
    if (!ph || !chip) return;
    var m = check(ph);
    if (!m) return;
    chip.textContent =
      'The whole tab: ' + m.h.toLocaleString('en-US') + ' px tall · smallest text ' + m.min + ' px' +
      (m.spills.length ? ' · text spills: ' + m.spills[0] : ' · nothing spills');
    chip.classList.toggle('is-bad', m.spills.length > 0 || m.min < 13);
    results.final = { h: m.h, min: m.min, spills: m.spills };
    write();
  }

  function remeasure() {
    measureAll();
    measureFinal();
  }

  render();
  connect();
  [60, 400, 1500, 4000].forEach(function (ms) { setTimeout(remeasure, ms); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(remeasure);
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(remeasure, 150);
  });
})();
