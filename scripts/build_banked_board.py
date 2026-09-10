"""Render the options board for how the week bar shows banked against still live.

Grant chose layout A on 2026-09-10 and asked to see the segment treatment separately, so
every option below is A with only the track swapped. Numbers are real Week 1: the state
is 13 games kicked off with 2 still playing, which is the only state where all four
segments exist at once.

    python scripts/build_banked_board.py

Writes outputs/banked-board.html with the logos inlined as data URIs, because an
Artifact's CSP blocks images from every external host.
"""
from __future__ import annotations

import base64
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = 210

# name, colour, banked, playing, upcoming, lost, rank label, avatar key
MID = [
    ("Parker", "#2E5C8A", 128, 17, 50, 15, "T1", "kenn"),
    ("Nicole", "#8A2E4F", 128, 18, 45, 19, "T1", "nicole"),
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

    raw = open(os.path.join(ROOT, rel), "rb").read()
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
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


def track(opt, p):
    """The bar for one player under one option. Everything else in the row is shared."""
    _, c, banked, play, _up, lost, _r, _a = p
    b, pl = pct(banked), pct(play)
    ceil = 100.0 - pct(lost)

    if opt == "cur":
        return ('<span class="wkbar__track">'
                '<span class="wkbar__live" style="width:%.1f%%;background:%s"></span>'
                '<span class="wkbar__fill" style="width:%.1f%%;background:%s"></span>'
                '</span>' % (ceil, c, b, c))

    if opt == "B1":   # four segments, the whole 210 accounted for
        s = '<span class="wkbar__track seg">'
        s += '<span style="left:0;width:%.1f%%;background:%s"></span>' % (b, c)
        if play:
            s += ('<span class="b1__play" style="left:%.1f%%;width:%.1f%%;background:%s">'
                  '</span>' % (b, pl, c))
        if lost:
            s += ('<span class="b1__lost" style="left:%.1f%%;right:0"></span>' % ceil)
        return s + '</span>'

    if opt == "B2":   # banked solid, still live in stripes of the same colour
        live = 100.0 - b - pct(lost) + pct(lost)   # everything not yet banked or lost
        live = ceil - b
        s = '<span class="wkbar__track seg">'
        if live > 0:
            s += ('<span class="b2__live" style="left:%.1f%%;width:%.1f%%;background:'
                  'repeating-linear-gradient(115deg,%s 0 3px,transparent 3px 6px)">'
                  '</span>' % (b, live, c))
        s += '<span style="left:0;width:%.1f%%;background:%s"></span>' % (b, c)
        return s + '</span>'

    if opt == "B3":   # playing RIGHT NOW split out, in the app's live red
        s = '<span class="wkbar__track seg">'
        s += '<span style="left:0;width:%.1f%%;background:%s"></span>' % (b, c)
        if play:
            s += '<span class="b3__now" style="left:%.1f%%;width:%.1f%%"></span>' % (b, pl)
        if ceil - b - pl > 0:
            s += ('<span class="b3__soon" style="left:%.1f%%;width:%.1f%%;background:%s">'
                  '</span>' % (b + pl, ceil - b - pl, c))
        return s + '</span>'

    if opt == "B4":   # banked only, with a tick where the ceiling is
        s = '<span class="wkbar__track seg">'
        s += '<span style="left:0;width:%.1f%%;background:%s"></span>' % (b, c)
        if ceil < 99.5:
            s += '<span class="b4__cap" style="left:calc(%.1f%% - 1px)"></span>' % ceil
        return s + '</span>'

    if opt == "B5":   # no second bar at all
        return ('<span class="wkbar__track seg">'
                '<span style="left:0;width:%.1f%%;background:%s"></span></span>' % (b, c))
    raise ValueError(opt)


def value(opt, p, leader):
    name, _c, banked, play, up, lost, _r, _a = p
    gap = leader - banked
    if opt == "B5":
        tail = "%d live" % (play + up) if (play + up) else ("won" if gap == 0 else "%d" % -gap)
    else:
        tail = "LEAD" if gap == 0 else "-%d" % gap
    cls = ' class="num"' if tail[0] in "-0123456789" else ""
    return '<span class="a__val"><b class="num">%d</b><i%s>%s</i></span>' % (
        banked, cls, tail)


def rows(opt, data):
    leader = max(p[2] for p in data)
    out = []
    for p in data:
        name, _c, banked, _pl, _up, _lo, rank, akey = p
        lead = " is-leader" if banked == leader else ""
        you = ' <span class="a__me">YOU</span>' if name == "Grant" else ""
        out.append(
            '<div class="wkbar%s"><span class="a__pos num">%s</span>%s'
            '<span class="wkbar__name">%s%s</span>%s%s</div>'
            % (lead, rank, av(akey), name, you, track(opt, p), value(opt, p, leader)))
    return "".join(out)


KEYS = {
    "cur": '<i class="is-banked"></i>banked<i class="is-live"></i>still live',
    "B1": '<i class="is-banked"></i>banked<i class="is-half"></i>live'
          '<i class="is-soon"></i>to come<i class="is-lost"></i>gone',
    "B2": '<i class="is-banked"></i>banked<i class="is-play"></i>still live',
    "B3": '<i class="is-banked"></i>banked<i class="is-now"></i>on now'
          '<i class="is-soon"></i>to come',
    "B4": '<i class="is-banked"></i>banked<i class="is-live"></i>can still reach',
    "B5": '',
}
FOOTS = {
    "cur": "Out of 210. The pale bar is the most you can still finish the week on.",
    "B1": "Out of 210. Solid is banked, the hatched tail is spent on games you lost.",
    "B2": "Out of 210. The striped part is still to be decided.",
    "B3": "Out of 210. Red is riding on the two games on right now.",
    "B4": "Out of 210. The tick is the most you can still finish on.",
    "B5": "Out of 210.",
}

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


def card(opt, title, data, foot=None, head=True, game=True, cls=""):
    key = KEYS[opt]
    k = ('<span class="wkbars__key">%s</span>' % key) if key else ""
    return ('<div class="ph"%s>%s<div class="wkbars %s"><div class="wkbars__head">'
            '<span class="wkbars__ttl">%s</span>%s</div>'
            '<div class="wkbars__rows">%s</div>'
            '<p class="wkbars__foot">%s</p></div>%s</div>'
            % (cls, HEAD if head else "", opt.lower(), title, k, rows(opt, data),
               foot or FOOTS[opt], GAME if game else ""))


NOTES = {
    "cur": ("Today", "shipped",
            "One colour at 22% opacity behind itself. The pale end lands at 91-93% for "
            "all four, because everyone still has most of the week in front of them, so "
            "it separates nobody. And the 15 to 19 points each of you has already thrown "
            "away is drawn as empty track, which reads as though it were still available."),
    "B1": ("B1", "Everything adds to 210",
           "Three visible parts: banked solid, what is still to come as open track, and "
           "what is already <b>gone</b> hatched at the far right. Nothing about the week "
           "is unaccounted for, and the hatched tail is the only treatment here that says "
           "Nicole has spent 19 points on games she lost while Grant has spent 15."),
    "B2": ("B2", "Stripes, not opacity",
           "Smallest change from today. Same two quantities, but still-live is drawn as "
           "diagonal stripes in your own colour instead of a 22% wash, so the boundary is "
           "unmistakable whether your colour is Nicole's plum or Grant's orange. Solves "
           "the legibility problem and none of the others."),
    "B3": ("B3", "Live means live",
           "Splits what today calls \"still live\" into the two very different things it "
           "actually contains: <b>17 to 21 points riding on the two games on right now</b>, "
           "in the same red the app already uses for a live chip, and the 45 to 59 on "
           "games that have not kicked off. The only option that answers \"what is at "
           "stake this minute\"."),
    "B4": ("B4", "A tick, not a bar",
           "Banked is the only bar. A hairline marks the most you can still finish on. "
           "Quietest of the five and the least ink, but the ticks land at 91.0, 91.9, "
           "92.9 and 92.9, which is four marks inside 4px of each other."),
    "B5": ("B5", "Let the number say it",
           "No second bar at all. The bar is banked, full stop, and what is still out "
           "there moves into type under the score. Nothing to misread, and it costs the "
           "gap-to-leader line that you picked option A partly to get."),
}
ORDER = ["cur", "B1", "B2", "B3", "B4", "B5"]


def figure(opt):
    tag, sub, note = NOTES[opt]
    chip = ('<span class="tag tag--flat">shipped</span>' if opt == "cur"
            else '<em>%s</em>' % sub)
    cap = ('<figcaption class="opt__cap">%s %s</figcaption>'
           % (tag, chip if opt == "cur" else '<em>%s</em>' % sub))
    return ('<figure class="opt">%s%s<p class="opt__note">%s</p></figure>'
            % (cap, card(opt, "This week", MID), note))


def final_figure(opt):
    tag = NOTES[opt][0]
    return ('<figure class="opt" style="width:372px">'
            '<figcaption class="opt__cap">%s</figcaption>'
            '<div style="padding:10px 0 4px;background:var(--panel);border:1px solid '
            'var(--edge);border-radius:14px">%s</div></figure>'
            % (tag, card(opt, "Week 1 &middot; final", FINAL,
                         foot="Out of 210. You take it by 7.", head=False, game=False,
                         cls=' style="width:auto;border:0;box-shadow:none;border-radius:0"')))


HEADER = """<title>Banked vs Still Live</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 10 September 2026</p>
<h1 class="doc__title">Banked against still live</h1>
<p class="doc__sub">Layout A everywhere, only the bar changes. Real Week&nbsp;1 numbers at
the one moment all four quantities exist at once: 13 games kicked off, 2 of them still
playing.</p>

<section>
  <h2 class="sec__h">What the week is actually made of</h2>
  <p class="sec__lede">A week is 210 points and every point is in one of four states. The
  bar we have draws two of them and merges the other two into empty track.</p>
  <table class="data">
    <tr><th>Player</th><th>Banked</th><th>Playing now</th><th>Not started</th>
        <th>Gone</th><th>Ceiling</th></tr>
    __TABLE__
  </table>
  <div class="callout">
    <p><b>&ldquo;Still live&rdquo; is two different feelings in one bar.</b> 17 to 21
    points riding on a game that is on television right now is not the same as 45 to 59
    on games that have not kicked off. Today both are the same pale wash.</p>
    <p><b>And the points you have already lost are invisible.</b> Nicole has spent 19 on
    games she got wrong and Grant 15, but both are drawn as plain empty track, which reads
    as room still to grow into. It is the one number the card never shows.</p>
  </div>
</section>

<section>
  <h2 class="sec__h">The options</h2>
  <p class="sec__lede">Each is the real component at 390px, in the layout you picked, over
  the COLO&nbsp;@&nbsp;GT card.</p>
  <div class="row">__OPTS__</div>
</section>

<section>
  <h2 class="sec__h">And once the week is over</h2>
  <p class="sec__lede">Nothing is live and nothing is to come, so each option collapses to
  what it says about the points that are gone. Week&nbsp;1 as it finished.</p>
  <div class="row">__FINAL__</div>
</section>

<section>
  <h2 class="sec__h">Recommendation</h2>
  <div class="rec">
    <h3>B1, or B3 if you want the drama</h3>
    <p><b>B1 is the one I would build.</b> It is the only option where the bar is a
    complete account of the week: everything you have won, everything still to come, and
    everything you have thrown away, adding to 210 with nothing hidden. It is also the
    only one that still says something once the week is final, where the hatched tail
    turns into the real story of Week&nbsp;1: you took it by 7 having wasted 24 points,
    while Nicole wasted 63.</p>
    <p><b>B3 is the more exciting screen and the narrower one.</b> Points riding on a game
    that is on right now is the single most alive number on the card, and red is already
    what the app means by live. The cost is that it only says anything while a game is in
    progress. Saturday afternoon it is the best of the five; Tuesday it is B4 with extra
    steps.</p>
    <p><b>B2 if you want the smallest possible change.</b> It fixes the one thing that is
    plainly broken, a 22% wash of your own colour being unreadable against it, and changes
    nothing else.</p>
    <p><b>B4 and B5 are the quiet ones.</b> B4's ticks sit within 4px of each other for
    all four players, so the mark is honest but says almost nothing. B5 gives up the
    gap-to-leader line, which was half the reason you chose A.</p>
    <p class="mono" style="margin-top:16px;color:var(--ink-3)">All five reuse the existing
    weekScore numbers except B3, which needs `open` and `total - spent` kept apart instead
    of summed. Both halves are already legal to show: neither says which game holds which
    number.</p>
  </div>
</section>
</div>
"""


def main():
    tr = "".join(
        "<tr><td>%s</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>"
        % (p[0], p[2], p[3], p[4], p[5], p[2] + p[3] + p[4]) for p in MID)
    css = open(os.path.join(ROOT, "scripts", "banked_board.css"), encoding="utf-8").read()
    doc = (HEADER.replace("__CSS__", css)
           + BODY.replace("__TABLE__", tr)
                 .replace("__OPTS__", "".join(figure(o) for o in ORDER))
                 .replace("__FINAL__", "".join(final_figure(o) for o in ORDER)))
    out = os.path.join(ROOT, "outputs", "banked-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
