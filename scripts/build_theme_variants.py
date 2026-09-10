"""Render the theme variants of skin C.

Grant chose skin C on 2026-09-10 and asked to see it in different colour schemes. The
architecture is therefore fixed and only the palette moves: every theme sets the same
fifteen tokens, so choosing one is a data change rather than a rewrite.

Markup comes from build_skin_board so the two boards cannot drift: same scorebug, same
two real Week 1 cards, same tab bar.

    python scripts/build_theme_variants.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from build_skin_board import TABS, bug, game  # noqa: E402

FULL = [
    ("fu-midnight", "Midnight", "deep navy, gold",
     ["#06101d", "#0a1220", "#121e33", "#e8b955", "#ffd25a", "#ff6b57"],
     "Navy all the way down, gold where the blue was. The card lifts off the page and "
     "the strip goes deeper than both, so it still reads as a graphic laid on top rather "
     "than as a hole cut in the screen. <b>The most obviously televised of the five.</b>"),
    ("fu-ink", "Ink", "OLED black",
     ["#000000", "#070707", "#141414", "#ff7b70", "#ffc531", "#ff5647"],
     "True black page, one red. On an OLED phone the page is not drawn at all, which is "
     "the only theme here with a battery argument. <b>The highest contrast by a "
     "distance</b>, and the least like college football: this is a terminal or a "
     "box score, not a broadcast."),
    ("fu-copper", "Copper", "warm dark, burnt orange",
     ["#0d0a08", "#14100d", "#211a15", "#f09a55", "#f0b45c", "#ff6f5c"],
     "Warm charcoal rather than blue-black, with the burnt orange your reports and your "
     "own seat already use. <b>The only one here that is yours rather than a network's</b>, "
     "and warm dark is materially easier to look at for the length of a Saturday than "
     "cool dark is."),
    ("fu-turf", "Turf", "deep forest, gold",
     ["#04100a", "#08150f", "#102118", "#ecc95a", "#f0c419", "#ff6f5c"],
     "Field green and gold. Accent is gold rather than green because green already means "
     "<i>you got this right</i> on every pick row. Darker and far more restrained than "
     "the cream-and-amber palette you replaced in September. <b>The most literally "
     "college football of the five.</b>"),
    ("fu-parchment", "Parchment", "not white, not dark",
     ["#171310", "#ece5d8", "#f7f2e8", "#8a4809", "#e8a33d", "#a82f22"],
     "The other reading of &ldquo;not white&rdquo;. A warm sand ground instead of a dark "
     "one, so the app stops being a white screen without giving up daylight. <b>The only "
     "option here that still works at a tailgate</b>, and the pick washes stay real "
     "washes rather than becoming bars."),
]

THEMES = [
    ("th-slate", "Slate", "what ships today",
     ["#10151c", "#f3f6f8", "#e7ecf1", "#2f6fed", "#ffd25a", "#c33c2c"],
     "The current palette with C's architecture dropped in. Cool blue-grey chrome, a "
     "near-black strip, one confident blue. <b>Nothing to argue about and nothing new "
     "either.</b> Worth seeing because it is the baseline the other four have to beat."),
    ("th-midnight", "Midnight", "prime time",
     ["#0b1526", "#f2f5f9", "#e4eaf3", "#c8912a", "#ffd25a", "#d0392b"],
     "A deep navy strip instead of near-black, and gold where the blue was. The strip "
     "stops reading as <i>off</i> and starts reading as a broadcast graphic, which is "
     "the whole point of C. <b>Closest to a Saturday night telecast</b>, and the gold "
     "already agrees with the leader colour in the scorebug."),
    ("th-ink", "Ink", "box score",
     ["#000000", "#f4f4f4", "#e6e6e6", "#d02418", "#ffc531", "#d02418"],
     "True black on true white with one red. The highest contrast of the five by a "
     "distance, which is the one that matters outdoors. <b>It reads as a newspaper box "
     "score</b> rather than as television, and the red doing double duty as both accent "
     "and live chip means the app has exactly one loud colour."),
    ("th-copper", "Copper", "yours, not a network's",
     ["#14110f", "#f6f3f0", "#e8e1da", "#b85c1f", "#e8a33d", "#c0392b"],
     "Warm charcoal, a warm ground, and the burnt orange your reports already use. It is "
     "also your own player colour, so your row in the bug and the app's accent are the "
     "same thing. <b>The only theme here that is yours rather than borrowed</b>, and the "
     "warm ground takes the clinical edge off eighty pick rows."),
    ("th-turf", "Turf", "the literal one",
     ["#0d1f17", "#f5f4ef", "#e5e3d8", "#a8770f", "#f0c419", "#b8402f"],
     "Field green and gold on a warm off-white. Accent is gold rather than green on "
     "purpose: green already means <i>you got this right</i> on every pick row and the "
     "two cannot be the same colour. <b>Read the history note above before picking "
     "this one.</b>"),
]

SWATCH_KEYS = ["strip", "page", "well", "accent", "lead", "live"]


def phone(theme):
    return ('<div class="ph %s">'
            '<div class="apphdr"><span class="apphdr__ttl">Motley Pick\'em</span>'
            '<span class="apphdr__wk">Wk 1</span></div>'
            '<div class="screen"><p class="eyebrow">Week 1</p>'
            '<h1 class="h1">The Board</h1>'
            '<p class="sub">13 of 20 open. The rest unlock as they kick off.</p></div>'
            '%s%s%s%s</div>'
            % (theme, bug(),
               game(("CLEM", "LSU"), '<span class="chip">Final</span>'),
               game(("COLO", "GT"), '<span class="chip">Final</span>'),
               TABS))


def figure_full(t):
    cls, name, kind, swatches, note = t
    sw = "".join('<i data-k="%s" style="background:%s"></i>' % (k, c)
                 for k, c in zip(["strip", "page", "card", "accent", "lead", "live"],
                                 swatches))
    return ('<figure class="opt"><figcaption class="opt__cap">%s</figcaption>'
            '<p class="opt__kind">%s</p><div class="spec">%s</div>%s'
            '<p class="opt__cost" data-th="%s"></p>'
            '<p class="opt__note">%s</p></figure>'
            % (name, kind, sw, phone(cls + " ph--full"), cls, note))


def figure(t):
    cls, name, kind, swatches, note = t
    sw = "".join('<i data-k="%s" style="background:%s"></i>' % (k, c)
                 for k, c in zip(SWATCH_KEYS, swatches))
    return ('<figure class="opt"><figcaption class="opt__cap">%s</figcaption>'
            '<p class="opt__kind">%s</p><div class="spec">%s</div>%s'
            '<p class="opt__cost" data-th="%s"></p>'
            '<p class="opt__note">%s</p></figure>'
            % (name, kind, sw, phone(cls), cls, note))


HEADER = """<title>The Whole App, Five Themes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = r"""<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 10 September 2026</p>
<h1 class="doc__title">The whole app, five themes</h1>
<p class="doc__sub">Not the strip and the accent this time. The ground, the cards, the
wells, the pick rows: everything that is currently white. Same architecture, same real
Week&nbsp;1 games, same fifteen tokens moved in each.</p>

<section>
  <h2 class="sec__h">What changes when the ground goes too</h2>
  <div class="callout">
    <p><b>The three surfaces have to re-stack.</b> On a light app the strip works because
    it is the dark thing. Once the page is dark it cannot be, so the order inverts: the
    <i>page</i> is deepest, the <i>card</i> lifts off it, and the strip goes deeper again
    so it still reads as a graphic laid on top rather than a hole cut in the screen. Every
    dark theme below sets three distinct tones for exactly that reason.</p>
    <p><b>The green and red washes stop working, and that is the real cost.</b> A pale
    wash is how eighty pick rows a week get read at a glance, and at 8% of a dark ground
    it is a smudge rather than a signal. On all four dark themes it becomes a hard 3px bar
    down the row instead, which survives at any tint. Check the CLEM&nbsp;@&nbsp;LSU card
    in each: two of you were right, two were wrong.</p>
    <p><b>Parchment is here because &ldquo;not white&rdquo; has two readings.</b> Warm
    sand is not white and is not dark, so the app stops being a bright screen without
    giving up the tailgate. It is the only one of the five where the washes stay washes.</p>
  </div>
</section>

<section>
  <h2 class="sec__h">The five</h2>
  <p class="sec__lede">Real Week&nbsp;1, same two games throughout. The number under each
  is its weakest measured contrast pair, because a palette swap is exactly where one
  quietly drops below readable and the eye does not catch it.</p>
  <div class="row">__OPTS__</div>
</section>

<section>
  <h2 class="sec__h">Recommendation</h2>
  <div class="rec">
    <h3>Copper, with Midnight as the safe one</h3>
    <p><b>Copper is the one I would build.</b> Warm dark is materially easier to sit with
    for the length of a Saturday than cool dark, and the burnt orange is already yours: it
    is your report accent and your own seat colour, so the app's highlight and your row in
    the standings become the same thing. On a screen that is mostly eighty small rows, the
    warm ground is the difference between an app and a spreadsheet.</p>
    <p><b>Midnight if you want it to look like television and nothing else.</b> Navy and
    gold is the most straightforwardly broadcast of the five, and the gold agrees with the
    leader colour already in the scorebug rather than adding a second highlight.</p>
    <p><b>Turf is better than it has any right to be.</b> It is close to the palette you
    replaced in September, and the reason it works here is that it is far darker and the
    green never touches the type. If you like it, take it knowingly rather than because it
    is the football-coloured one.</p>
    <p><b>Ink is the outlier and the one with a real argument.</b> True black is not drawn
    at all on an OLED phone, so it is the only theme with a battery case. It also looks
    like a terminal rather than a broadcast, which may be exactly the wrong answer to what
    you asked for.</p>
    <p><b>Parchment is the hedge.</b> If dark turns out to be wrong on your mum's phone in
    the sun, this is the version of &ldquo;not white&rdquo; that survives daylight, and it
    is the only one that keeps the pick washes.</p>
    <p class="mono" style="margin-top:16px;color:var(--ink-3)">Whichever you pick, the
    others stay buildable: each is fifteen tokens in src/theme.css and nothing else. A
    theme switcher later is a data change, not a rewrite.</p>
  </div>
</section>
</div>

<script>
/* Contrast, measured rather than asserted. */
const L = (s) => { const c = s.match(/[\d.]+/g).slice(0, 3).map(Number)
  .map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] };
const R = (a, b) => { const x = L(a) + 0.05, y = L(b) + 0.05;
  return Math.max(x, y) / Math.min(x, y) };
const hex = (h) => { const v = h.replace('#', '');
  return 'rgb(' + [0, 2, 4].map((i) => parseInt(v.substr(i, 2), 16)).join(',') + ')' };
for (const p of document.querySelectorAll('.opt__cost')) {
  const ph = document.querySelector('.' + p.dataset.th);
  const cs = getComputedStyle(ph), g = (k) => hex(cs.getPropertyValue(k).trim());
  const pairs = {
    'strip text': [g('--on-field'), g('--field-deep')],
    'body text': [g('--ink'), g('--page')],
    'muted text': [g('--ink-3'), g('--card')],
    'eyebrow': [g('--accent-deep'), g('--page')],
    'right pick': [g('--good'), g('--good-wash')],
    'wrong pick': [g('--bad'), g('--bad-wash')],
    'leader': [g('--lead'), g('--field-deep')],
  };
  let worst = ['', 99];
  for (const [k, [a, b]] of Object.entries(pairs)) {
    const r = R(a, b);
    if (r < worst[1]) worst = [k, r];
  }
  p.innerHTML = 'weakest pair: <b>' + worst[0] + ' ' + worst[1].toFixed(2) +
    ':1</b> &middot; ' + (worst[1] >= 4.5 ? 'clears AA' : '<b>BELOW AA</b>');
}
</script>
"""


def main():
    css = open(os.path.join(ROOT, "scripts", "theme_variants.css"), encoding="utf-8").read()
    doc = (HEADER.replace("__CSS__", css)
           + BODY.replace("__OPTS__", "".join(figure_full(t) for t in FULL)))
    out = os.path.join(ROOT, "outputs", "theme-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
