"""Render the options board for making the week scoreboard read as a broadcast scorebug.

Grant asked on 2026-09-10 for the week card to look like an ESPN, CBS or NBC scorebug.
Every option keeps what he already chose: layout A's rank, avatar, YOU marker and gap,
and a banked-against-live reading. Only the visual language changes.

The condensed caps come from Archivo's `wdth` axis, which means no new font family: the
app already loads Archivo, and the Google Fonts URL in index.html only has to ask for the
axis. Verified 2026-09-10 that fonts.googleapis.com serves wdth 62..125 for it.

    python scripts/build_scorebug_board.py
"""
from __future__ import annotations

import base64
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = 210

# name, colour, banked, playing, upcoming, lost, rank, avatar key
MID = [
    ("Parker", "#2E5C8A", 128, 17, 50, 15, "1", "kenn"),
    ("Nicole", "#8A2E4F", 128, 18, 45, 19, "1", "nicole"),
    ("James", "#1F6F4A", 124, 21, 48, 17, "3", "uga"),
    ("Grant", "#B85C1F", 117, 19, 59, 15, "4", "wyo"),
]
FINAL = [
    ("Grant", "#B85C1F", 186, 0, 0, 24, "1", "wyo"),
    ("James", "#1F6F4A", 179, 0, 0, 31, "2", "uga"),
    ("Parker", "#2E5C8A", 164, 0, 0, 46, "3", "kenn"),
    ("Nicole", "#8A2E4F", 147, 0, 0, 63, "4", "nicole"),
]


def datauri(rel, px=64):
    from PIL import Image

    im = Image.open(os.path.join(ROOT, rel)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


LOGO = {k: datauri("static/logos/%s.png" % v) for k, v in
        {"kenn": "338", "uga": "61", "wyo": "2751", "colo": "38", "gt": "59"}.items()}
BG = {"kenn": "#fdbb30", "uga": "#ba0c2f", "wyo": "#ffc425", "colo": "#000000",
      "gt": "#b3a369"}


def av(key, size=22):
    if key == "nicole":
        return ('<span class="avatar" style="width:%dpx;height:%dpx;background:#8A2E4F;'
                'font-size:%.1fpx">N</span>' % (size, size, size * 0.42))
    n = round(size * 0.72)
    return ('<span class="avatar avatar--team" style="width:%dpx;height:%dpx;background:%s">'
            '<img src="%s" width="%d" height="%d" alt=""></span>'
            % (size, size, BG[key], LOGO[key], n, n))


def pct(v):
    return 100.0 * v / TOTAL


def rule(p):
    """The thin progress strip a real bug uses for timeouts, doing banked vs live here."""
    _n, c, banked, play, up, _lost, _r, _a = p
    live = play + up
    s = '<span class="bugrule">'
    if live:
        s += ('<i class="is-live" style="width:%.1f%%;background:%s"></i>'
              % (pct(banked + live), c))
    s += '<i style="width:%.1f%%;background:%s"></i>' % (pct(banked), c)
    return s + '</span>'


def bugrow(opt, p, leader):
    name, c, banked, play, up, _lost, rank, akey = p
    gap = leader - banked
    lead = " is-leader" if gap == 0 else ""
    live = play + up
    gap_txt = "&mdash;" if gap == 0 else "-%d" % gap
    you = '<span class="bugrow__you">YOU</span>' if name == "Grant" else ""

    if opt == "S2":
        pos = ('<span class="bugrow__block" style="background:%s">'
               '<span class="bugrow__blockpos">%s</span>%s</span>' % (c, rank, av(akey, 24)))
        return ('<div class="bugrow%s%s">%s<span class="bugrow__name">%s%s</span>'
                '<span class="bugrow__pts num">%d</span>'
                '<span class="bugrow__gap num">%s</span>%s</div>'
                % (lead, " has-live" if play else "", pos, name.upper(), you, banked,
                   gap_txt, rule(p)))

    # The situation panel goes away entirely once there is nothing left to play for,
    # rather than printing FINAL four times down the right edge. A real bug drops down
    # and distance the moment the ball is dead; four identical boxes saying the same
    # word is worse than the space they occupy.
    sit, nosit = "", ""
    if opt == "S3":
        if live:
            v, k = (play, "on now") if play else (live, "to come")
            sit = ('<span class="bugrow__sit"><span class="bugrow__sitv num">+%d</span>'
                   '<span class="bugrow__sitk">%s</span></span>' % (v, k))
        else:
            nosit = " bugrow--nosit"

    return ('<div class="bugrow%s%s%s"><span class="bugrow__seed" style="background:%s">'
            '</span><span class="bugrow__pos num">%s</span>%s'
            '<span class="bugrow__name">%s%s</span>'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span>%s%s</div>'
            % (lead, " has-live" if play else "", nosit, c, rank, av(akey),
               name.upper(), you, banked, gap_txt, sit, rule(p)))


HEAD = ('<div class="screen"><p class="eyebrow">Week 1</p><h1 class="h1">The Board</h1>'
        '<p class="sub">13 of 20 open. The rest unlock as they kick off.</p></div>')
GAME = ('<div class="bgame"><div class="bgame__head"><div class="bgame__score">'
        '<span class="bgame__side">' + av("colo") + 'COLO<span class="bgame__pts num">14'
        '</span></span><span class="bgame__sep">@</span>'
        '<span class="bgame__side is-loser">' + av("gt") + 'GT'
        '<span class="bgame__pts num">13</span></span></div>'
        '<span class="chip">Final</span></div>'
        '<p class="bgame__odds num">GT -6.5<span class="bgame__oddsep">&middot;</span>'
        'O/U 51.5</p></div>')

TODAY = ('<div class="wkbars"><div class="wkbars__head">'
         '<span class="wkbars__ttl">This week</span><span class="wkbars__key">'
         '<i class="is-banked"></i>banked<i class="is-live"></i>still live</span></div>'
         '<div class="wkbars__rows">')


def today_card(data):
    leader = max(p[2] for p in data)
    s = TODAY
    for p in data:
        name, c, banked, play, up, lost, rank, akey = p
        gap = leader - banked
        you = ' <span class="a__me">YOU</span>' if name == "Grant" else ""
        s += ('<div class="wkbar%s"><span class="a__pos num">%s</span>%s'
              '<span class="wkbar__name">%s%s</span>'
              '<span class="wkbar__track">'
              '<span class="wkbar__live" style="width:%.1f%%;background:%s"></span>'
              '<span class="wkbar__fill" style="width:%.1f%%;background:%s"></span></span>'
              '<span class="a__val"><b class="num">%d</b><i class="num">%s</i></span></div>'
              % (" is-leader" if gap == 0 else "", rank, av(akey), name, you,
                 100 - pct(lost), c, pct(banked), c, banked,
                 "LEAD" if gap == 0 else "-%d" % gap))
    return s + ('</div><p class="wkbars__foot">Out of 210. The pale bar is the most you '
                'can still finish the week on.</p></div>')


def bug(opt, data, live_games=2, foot=None):
    leader = max(p[2] for p in data)
    dark = "" if opt == "S4" else " bug--dark"
    if opt == "S4":
        dark = " bug--light"
    top = ('<div class="bug__top"><span class="bug__wk">Week 1 &middot; This week</span>%s'
           '<span class="bug__of">%d of 20</span></div>'
           % ('<span class="bug__live"><i></i>%d live</span>' % live_games
              if live_games else "", 13 if live_games else 20))
    rows = "".join(bugrow(opt, p, leader) for p in data)
    ft = ('<div class="bug__foot">%s</div>' % foot) if foot else ""
    return '<div class="bug%s %s">%s%s%s</div>' % (dark, opt.lower(), top, rows, ft)


NOTES = {
    "cur": ("Today", "shipped",
            "A card, not a bug. Rounded, white, pale blue accent, sentence-case names in "
            "the UI face. It matches the rest of the app and reads as a settings panel."),
    "S1": ("S1", "Bottom line",
           "The ESPN lower-third. Near-black chrome, a colour seed down the left of every "
           "row, <b>condensed caps</b> from Archivo's width axis, and the score set large "
           "in tabular figures. Banked against live survives as the 2px rule along the "
           "bottom of each row, the same place a broadcast bug puts timeouts."),
    "S2": ("S2", "Colour block",
           "The Fox and CBS treatment: a solid block of your colour carrying the seed and "
           "the logo, butted against the dark panel. Loudest of the four and the most "
           "obviously a scoreboard from across a room. Costs 6px a row in height for the "
           "taller block."),
    "S3": ("S3", "With a situation panel",
           "S1 plus the segment a real bug keeps for down and distance, here carrying "
           "<b>what is riding on the games actually in progress</b>. It is the only option "
           "where banked and live are separate readings rather than one bar, and the "
           "panel has something to say for the whole week rather than only Saturday."),
    "S4": ("S4", "Bug in daylight",
           "The same architecture in the app's own light palette. Keeps the condensed "
           "caps, the seed and the big score, and does not turn the top of the Board into "
           "a black slab. The honest question is whether it still reads as broadcast or "
           "just as a tidier version of what is there."),
}
ORDER = ["cur", "S1", "S2", "S3", "S4"]


def figure(opt):
    tag, sub, note = NOTES[opt]
    chip = ('<span class="tag">shipped</span>' if opt == "cur" else "<em>%s</em>" % sub)
    inner = today_card(MID) if opt == "cur" else bug(
        opt, MID, 2, "Out of 210 &middot; you are 11 back with 78 still to play for")
    return ('<figure class="opt"><figcaption class="opt__cap">%s %s</figcaption>'
            '<div class="ph">%s%s%s</div><p class="opt__cost" data-opt="%s"></p>'
            '<p class="opt__note">%s</p></figure>'
            % (tag, chip, HEAD, inner, GAME, opt, note))


def final_figure(opt):
    inner = today_card(FINAL) if opt == "cur" else bug(
        opt, FINAL, 0, "Out of 210 &middot; you take it by 7")
    return ('<figure class="opt" style="width:372px">'
            '<figcaption class="opt__cap">%s</figcaption>'
            '<div class="ph" style="width:auto;padding:10px 0 4px">%s</div></figure>'
            % (NOTES[opt][0], inner))


HEADER = """<title>The Week as a Scorebug</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 10 September 2026</p>
<h1 class="doc__title">The week as a scorebug</h1>
<p class="doc__sub">Four ways to make the week card read like something off a broadcast
rather than out of a settings screen. Everything you have already picked stays: the seed,
the avatar, the YOU marker, the gap, and banked against still live.</p>

<section>
  <h2 class="sec__h">What actually makes a scorebug look like one</h2>
  <div class="callout">
    <p>It is four things, and none of them is the shape of the box. <b>Dark chrome</b> so
    the graphic sits on top of the picture rather than in it. <b>A team colour seed</b> as
    a hard block or stripe, never as a bar you have to measure. <b>Condensed caps</b> for
    names, so ABBREVIATIONS read at a glance. And <b>the number set large in tabular
    figures</b>, right-aligned, bigger than everything around it.</p>
    <p><b>The condensed face is free.</b> Archivo, which the app already loads for display
    type, is a variable font with a width axis. Asking Google Fonts for
    <span class="mono">Archivo:wdth,wght@62..125,400..800</span> in index.html is the whole
    change; no second family, no extra request. Verified against fonts.googleapis.com.</p>
    <p><b>Names go to caps.</b> PARKER and NICOLE are the same length as team
    abbreviations, which is exactly why this works here and would not work on a screen of
    full sentences.</p>
  </div>
</section>

<section>
  <h2 class="sec__h">The options</h2>
  <p class="sec__lede">Real Week&nbsp;1 numbers at the mid-week moment: 13 games kicked
  off, 2 still playing. Over the COLO&nbsp;@&nbsp;GT card, at 390px.</p>
  <div class="row">__OPTS__</div>
</section>

<section>
  <h2 class="sec__h">Once the week is over</h2>
  <p class="sec__lede">No live chip, no situation panel, no progress rule. The bug has to
  still look deliberate when there is nothing left to play for.</p>
  <div class="row">__FINAL__</div>
</section>

<section>
  <h2 class="sec__h">Recommendation</h2>
  <div class="rec">
    <h3>S3, with S1 if the situation panel is a step too far</h3>
    <p><b>S3 is the one I would build.</b> It is the only option where the thing you asked
    about last, banked against still live, becomes a real broadcast element rather than a
    decoration: the panel on the right is where a bug puts 3rd &amp; 7, and here it holds
    the 17 to 21 points riding on the games actually on. It also degrades honestly, since
    on a Tuesday it reads &ldquo;to come&rdquo; instead of &ldquo;on now&rdquo; and at the
    end of the week it drops out entirely.</p>
    <p><b>S1 is the safer version of the same idea.</b> Identical chrome, no extra
    segment, and the banked-versus-live reading lives in the 2px rule along the bottom of
    each row. Quieter, and it gives up the one number that makes the card feel live.</p>
    <p><b>S2 is the most fun and the least practical.</b> Full colour blocks look terrific
    and they push each row to 44px, which is 24px more card above the first game than S1.
    Worth it only if you want the scoreboard to be the point of the screen.</p>
    <p><b>S4 is the hedge.</b> If a black slab at the top of a white Board turns out to
    look like a mistake on your phone rather than on this page, S4 is the same skeleton
    with none of that risk. It is also the least likely to make you say &ldquo;that looks
    like a scoreboard&rdquo;.</p>
    <p class="mono" style="margin-top:16px;color:var(--ink-3)">All four need the one-line
    font change in index.html. S3 additionally needs `weekScore` to keep `open` and
    `total - spent` apart instead of summing them, which is legal: neither says which game
    holds which number.</p>
  </div>
</section>
</div>

<script>
/* The height each option costs above the first game card, measured rather than guessed. */
const box = (f) => f.querySelector('.wkbars,.bug');
const tall = (el) => { const cs = getComputedStyle(el);
  return Math.round(el.getBoundingClientRect().height
    + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom)); };
document.fonts.ready.then(() => {
  const figs = [...document.querySelectorAll('.wrap section')][1]
    .querySelectorAll('figure.opt');
  const h = {};
  for (const f of figs) h[f.querySelector('.opt__cost').dataset.opt] = tall(box(f));
  for (const f of figs) {
    const c = f.querySelector('.opt__cost');
    const v = h[c.dataset.opt], d = v - h.cur;
    const row = c.dataset.opt === 'cur' ? '' :
      ' · ' + (d === 0 ? 'same as A' : (d > 0 ? '+' : '') + d + 'px vs A');
    c.innerHTML = '<b>' + v + 'px</b> tall' + (c.dataset.opt === 'cur' ? ' · option A, the baseline' : row);
  }
});
</script>
"""


def main():
    css = open(os.path.join(ROOT, "scripts", "scorebug_board.css"), encoding="utf-8").read()
    doc = (HEADER.replace("__CSS__", css)
           + BODY.replace("__OPTS__", "".join(figure(o) for o in ORDER))
                 .replace("__FINAL__", "".join(final_figure(o) for o in ORDER)))
    out = os.path.join(ROOT, "outputs", "scorebug-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
