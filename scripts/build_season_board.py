"""Render the options board for giving the Season tab football flare.

Grant on 2026-09-11: "I love the scoreboard at the top, but everything below it is
lackluster, especially records... it's cold and techy but some football flare here and
there or background or little animation shit would be very cool."

He settled the content first, which is why this board is only about the skin:
  - unlock the picks, so pick-level records are on the table
  - one shared record book, not a page per player
  - the form chart, week-by-week and ranking bars all survive, restyled

So every option below draws the SAME content in the same order: the shipped standings
block, then the record book with three records and the form chart. The standings are not
up for debate and are therefore identical in all six, which makes the seam between them
and the skin the thing you are actually comparing. An option that only looks good with
the standings cropped off is not an option.

The fixture is six invented weeks. The season is two weeks old, so real data would show
every one of these records at its weakest, and a board built on it would be judging the
season rather than the design.

    python scripts/build_season_board.py
"""
from __future__ import annotations

import base64
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ the fixture ----
# Six invented weeks. Totals below are the sums, checked in main() rather than typed,
# because a standings block that does not add up is the one bug a mockup can ship that
# quietly discredits everything around it.
WEEKS = [
    # week, Grant, James, Parker, Nicole
    (1, 186, 179, 164, 147),
    (2, 141, 158, 172, 133),
    (3, 195, 166, 149, 158),
    (4, 128, 171, 155, 181),
    (5, 163, 152, 188, 144),
    (6, 174, 190, 137, 169),
]
# name, colour, team id or None, correct, wrong
PLAYERS = [
    ("James", "#1F6F4A", "61", 78, 42),
    ("Grant", "#B85C1F", "2751", 76, 44),
    ("Parker", "#2E5C8A", "338", 74, 46),
    ("Nicole", "#8A2E4F", None, 71, 49),
]
# Column of each player in a WEEKS tuple. Spelled out rather than derived from
# PLAYERS, which is sorted by record and would silently re-map every score.
COL = {"Grant": 1, "James": 2, "Parker": 3, "Nicole": 4}

# The three records every option renders. One clean, one ugly, one with a logo on it,
# which between them exercise everything a skin has to survive: a plain number, a
# negative, and somebody else's brand colour sitting inside yours.
#   key, label, value, unit, who, team id for the mark, is it a bad record
RECORDS = [
    ("best", "Best week", "195", "pts", "Grant, Week 3", "2751", False),
    ("bomb", "20-point disaster", "20", "on a loser", "Nicole, MICH, Wk 4", "130", True),
    ("money", "Money team", "+84", "pts banked", "James, Georgia", "61", False),
]


def datauri(rel, px=64):
    from PIL import Image

    im = Image.open(os.path.join(ROOT, rel)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# Every logo inlined. An Artifact's CSP blocks external images and the preview pane loads
# a file as a data: URL, so a src pointing at ESPN renders as a broken box in both.
TEAM = {
    "2751": ("#ffc425", "WYO"),
    "61": ("#ba0c2f", "UGA"),
    "338": ("#fdbb30", "KENN"),
    "130": ("#00274c", "MICH"),
}
LOGO = {k: datauri("static/logos/%s.png" % k) for k in TEAM}


def mark(team_id, cls="mk", size=None):
    """A team disc, or a lettered disc for the seat with no school."""
    if not team_id:
        return ""
    bg, _ = TEAM[team_id]
    px = size or 19
    return ('<span class="avatar %s" style="width:%dpx;height:%dpx;background:%s">'
            '<img src="%s" width="%d" height="%d" alt=""></span>'
            % (cls, px, px, bg, LOGO[team_id], round(px * .72), round(px * .72)))


def avatar(name, colour, team_id, size=36):
    if team_id:
        bg, _ = TEAM[team_id]
        return ('<span class="avatar" style="width:%dpx;height:%dpx;background:%s">'
                '<img src="%s" width="%d" height="%d" alt=""></span>'
                % (size, size, bg, LOGO[team_id], round(size * .72), round(size * .72)))
    return ('<span class="avatar" style="width:%dpx;height:%dpx;background:%s;'
            'font-size:%.1fpx">%s</span>' % (size, size, colour, size * .42, name[0]))


# ------------------------------------------------------------ the shared top ----
def totals():
    out = []
    for name, colour, team, correct, wrong in PLAYERS:
        pts = sum(w[COL[name]] for w in WEEKS)
        out.append((name, colour, team, correct, wrong, pts))
    return sorted(out, key=lambda x: -x[5])


def standings():
    rows = []
    for i, (name, colour, team, correct, wrong, pts) in enumerate(totals()):
        acc = round(100 * correct / (correct + wrong))
        lead = " is-leader" if i == 0 else ""
        rows.append(
            '<div class="srow%s"><span class="srow__pos num">%d</span>%s'
            '<span class="srow__body"><span class="srow__name">%s</span>'
            '<span class="srow__meta num">%d-%d &middot; %d%%</span></span>'
            '<span><span class="srow__pts num">%s</span>'
            '<span class="srow__lbl">pts</span></span></div>'
            % (lead, i + 1, avatar(name, colour, team), name, correct, wrong, acc, pts))
    return ('<div class="scrn"><p class="scrn__eye">Season 2026</p>'
            '<h2 class="scrn__ttl">Season</h2>'
            '<p class="scrn__sub">6 weeks in the books. Ties stand, so a week can be '
            'shared.</p></div><div class="stand">%s</div>'
            '<p class="seam"><i></i>the shipped part ends here<i></i></p>'
            % "".join(rows))


# ----------------------------------------------------------------- the chart ----
def chart(stroke, grid, label, fill=None):
    """Points per week, one line per player, drawn to a shared 0-210 scale.

    Same geometry as formGeometry() in src/lib/seasonStats.js: zero-based, so a lead
    that halves looks like a lead that halves. Colours are the only thing a skin gets
    to change here.
    """
    W, H, padL, padB, padT = 306, 76, 20, 13, 6
    top = 210
    n = len(WEEKS)
    xs = lambda i: padL + i * (W - padL - 4) / (n - 1)
    ys = lambda v: padT + (1 - v / top) * (H - padT - padB)

    parts = []
    for v in (0, 105, 210):
        parts.append('<line x1="%.0f" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" '
                     'stroke-width="1"/>' % (padL, ys(v), W - 2, ys(v), grid))
        parts.append('<text x="%.0f" y="%.1f" fill="%s" font-size="7" text-anchor="end" '
                     'font-family="Archivo,sans-serif">%d</text>'
                     % (padL - 4, ys(v) + 2.5, label, v))
    for i, w in enumerate(WEEKS):
        parts.append('<text x="%.1f" y="%d" fill="%s" font-size="7" text-anchor="middle" '
                     'font-family="Archivo,sans-serif">%d</text>'
                     % (xs(i), H - 3, label, w[0]))
    for name, colour, *_ in PLAYERS:
        pts = " ".join("%.1f,%.1f" % (xs(i), ys(w[COL[name]])) for i, w in enumerate(WEEKS))
        c = stroke.get(name, colour)
        if fill:
            parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="4.5" '
                         'stroke-linejoin="round" stroke-linecap="round" opacity=".22"/>'
                         % (pts, c))
        parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" '
                     'stroke-linejoin="round" stroke-linecap="round"/>' % (pts, c))
        for i, w in enumerate(WEEKS):
            parts.append('<circle cx="%.1f" cy="%.1f" r="2.2" fill="%s"/>'
                         % (xs(i), ys(w[COL[name]]), c))
    return ('<svg class="cw" viewBox="0 0 %d %d" role="img" aria-label="Points per week">'
            '%s</svg>' % (W, H, "".join(parts)))


# On paper the shipped seat colours are the right ones and measure 4.4:1 to 7.9:1.
PLAIN = {}

# On any dark ground they are not. Measured against each option's own chart well:
#
#              S2 #0d1218   S3 #102616   S4 #161c25   S5 #151a21   S6 #0f2f1c
#   Grant          4.11         4.30         3.74         3.82         4.06
#   James          3.07         3.21         2.80         2.86         3.03
#   Parker         2.70         2.83         2.46         2.51         2.67
#   Nicole         2.31         2.42         2.11         2.15         2.29
#
# WCAG 1.4.11 puts a non-text graphic at 3:1 and a 2px polyline is a graphic, so three
# of the four seats fail on every dark option and Nicole fails by more than half. This
# is the same shape of problem as --lead: a colour chosen against one ground does not
# travel to the other. The brightened set below clears 6.3:1 on the worst of the five
# wells while keeping each seat's hue, so nobody's line changes identity.
DARK = {"Grant": "#F2913F", "James": "#3FCB83", "Parker": "#5FA8F2", "Nicole": "#F2739E"}


# ------------------------------------------------------------------ the skins ----
def s1():
    rows = []
    for _k, label, value, unit, who, team, bad in RECORDS:
        rows.append(
            '<div class="r%s"><span class="r__k">%s</span><span class="r__dots"></span>'
            '<span class="r__v num">%s<span class="r__u">%s</span></span>'
            '<span class="r__who">%s%s</span></div>'
            % (" r--bad" if bad else "", label, value, unit, mark(team), who))
    return ('<div class="sk"><p class="sk__kick">Motley Pick&rsquo;em &middot; 2026</p>'
            '<h3 class="sk__hd">The Record Book</h3><hr class="sk__rule">%s'
            '<div class="sk__cw"><p class="sk__ch">Points by week</p>%s</div></div>'
            % ("".join(rows), chart(PLAIN, "rgba(27,24,19,.20)", "#7d6a4e")))


def s2():
    rows = []
    for _k, label, value, unit, who, team, bad in RECORDS:
        rows.append(
            '<div class="r%s"><span class="r__k">%s</span>'
            '<span class="r__v num">%s</span>'
            '<span class="r__who">%s%s</span><span class="r__u">%s</span></div>'
            % (" r--bad" if bad else "", label, value, mark(team), who, unit))
    return ('<div class="sk"><h3 class="sk__hd">Record Board</h3>'
            '<div class="sk__bulbs"></div>%s'
            '<div class="sk__cw"><p class="sk__ch">Points by week</p>%s</div></div>'
            % ("".join(rows), chart(DARK, "rgba(255,176,32,.16)", "#a08a63")))


def s3():
    rows = []
    for _k, label, value, unit, who, team, bad in RECORDS:
        rows.append(
            '<div class="r%s"><span class="r__k">%s</span>'
            '<span class="r__v num">%s</span>'
            '<span class="r__who">%s%s</span><span class="r__u">%s</span></div>'
            % (" r--bad" if bad else "", label, value, mark(team), who, unit))
    return ('<div class="sk"><h3 class="sk__hd">The Record Book</h3>'
            '<p class="sk__sub">Six weeks &middot; 2026</p>%s'
            '<div class="sk__cw"><p class="sk__ch">Points by week</p>%s</div></div>'
            % ("".join(rows), chart(DARK, "rgba(255,255,255,.16)", "#a9c4a5")))


def s4():
    cards = []
    for _k, label, value, unit, who, team, bad in RECORDS:
        c1, _ = TEAM[team]
        c2 = "#7d2010" if bad else "#1b2430"
        cards.append(
            '<div class="card"><div class="card__in" style="--c1:%s;--c2:%s">'
            '<p class="card__k">%s</p><p class="card__v num">%s</p>'
            '<p class="card__u">%s</p>'
            '<p class="card__who">%s%s</p></div></div>'
            % (c1, c2, label, value, unit, mark(team, size=20), who))
    return ('<div class="sk"><h3 class="sk__hd">The Record Book</h3>'
            '<p class="sk__sub">Swipe. One card per record, held until somebody takes it.</p>'
            '<div class="cards">%s</div>'
            '<div class="sk__cw"><p class="sk__ch">Points by week</p>%s</div></div>'
            % ("".join(cards), chart(DARK, "rgba(255,255,255,.10)", "#8391a5")))


def s5():
    rows = []
    for _k, label, value, unit, who, team, bad in RECORDS:
        c1, _ = TEAM[team]
        rows.append(
            '<div class="r%s"><span class="r__blk" style="--c1:%s">%s</span>'
            '<span><span class="r__k">%s</span><span class="r__who">%s</span></span>'
            '<span><span class="r__v num">%s</span><span class="r__u">%s</span></span>'
            '</div>' % (" r--bad" if bad else "", c1, mark(team, size=22), label, who,
                        value, unit))
    return ('<div class="sk"><div class="sk__band"><h3 class="sk__hd">The Record Book</h3>'
            '<p class="sk__sub">Season 2026 &middot; 6 weeks</p></div>%s'
            '<div class="sk__cw"><p class="sk__ch">Points by week</p>%s</div></div>'
            % ("".join(rows), chart(DARK, "rgba(255,255,255,.09)", "#97a5b3")))


def s6():
    rows = []
    for _k, label, value, unit, who, team, bad in RECORDS:
        rows.append(
            '<div class="r%s"><span class="r__k">%s</span>'
            '<span class="r__v num">%s</span>'
            '<span class="r__who">%s%s</span><span class="r__u">%s</span></div>'
            % (" r--bad" if bad else "", label, value, mark(team), who, unit))
    return ('<div class="sk"><h3 class="sk__hd">The Record Book</h3>'
            '<p class="sk__sub">Motley Pick&rsquo;em &middot; 2026</p>%s'
            '<div class="sk__cw"><p class="sk__ch">Points by week</p>%s</div></div>'
            % ("".join(rows), chart(DARK, "rgba(255,255,255,.10)", "#b39a72")))


OPTIONS = [
    ("s1", "S1 &middot; Media guide", "Print", "",
     s1,
     "The back pages of a college media guide. Oat paper, condensed caps, a double rule, "
     "dot leaders running out to the number. <b>The only option that gets its flare from "
     "type and paper rather than from colour,</b> so it is the one that will still look "
     "right in five years. Quiet next to the others, and that is the trade."),
    ("s2", "S2 &middot; Bulb board", "Animated", "",
     s2,
     "An incandescent scoreboard. Near-black, amber, a bulb-dot field behind everything, "
     "and the numbers breathe on a 3.4s cycle. <b>The loudest legible option.</b> Amber "
     "on near-black is the highest contrast on the board, so this is also the easiest to "
     "read outdoors at a tailgate."),
    ("s3", "S3 &middot; Turf and chalk", "Risky", "warn",
     s3,
     "Field green, chalk dashes, hash marks down the left edge. The most literally "
     "football. <b>This is the one that already failed once:</b> v1 painted yard lines "
     "behind the sign-in and they read as wireframe banding on a phone. The mow stripes "
     "here are 2.2% white, about a fifth of that, which is why they read as texture "
     "rather than as lines. Worth checking on your actual screen before you trust it."),
    ("s4", "S4 &middot; Trading cards", "Animated", "",
     s4,
     "Every record is a card in the other team's colours, foil edge, and a shimmer that "
     "sweeps every 4.6s. <b>The most fun and the least dense:</b> three records take the "
     "width the others give six, so the book becomes a swipe rather than a scan. Best if "
     "you want the records to feel collectible and are happy to swipe for them."),
    ("s5", "S5 &middot; Broadcast", "Safest", "",
     s5,
     "The scorebug language you already picked, carried down the page: the block of "
     "school colour, condensed caps, an angled cut, and a blue wipe across the band every "
     "5s. <b>The only option with no seam,</b> because it is the same design system the "
     "top of the app already speaks. Also the least new."),
    ("s6", "S6 &middot; Trophy case", "Loud", "",
     s6,
     "Wood, brass and felt. Each record is an engraved plate, the chart sits in a felt "
     "well. <b>The furthest thing from cold and techy on the board,</b> and the one that "
     "makes holding a record feel like an object. Brass is a lot of gradient on a phone; "
     "it lives or dies on your screen, not on this one."),
]


def figure(cls, name, kind, tag, body, note):
    chip = ' <span class="tag%s">%s</span>' % (
        " tag--warn" if tag == "warn" else "", kind) if kind else ""
    return ('<figure class="opt"><figcaption class="opt__cap">%s%s</figcaption>'
            '<p class="opt__kind">Same standings, same three records, same chart</p>'
            '<div class="ph %s">'
            '<div class="apphdr"><span class="apphdr__ttl">Motley Pick&rsquo;em</span>'
            '<span class="apphdr__wk">Week 7</span></div>%s%s</div>'
            '<p class="opt__note">%s</p></figure>'
            % (name, chip, cls, standings(), body(), note))


HEADER = """<title>The Season Tab, Six Ways</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 11 September 2026</p>
<h1 class="doc__title">The Season tab, six ways</h1>
<p class="doc__sub">You settled the content already: unlock the picks, one shared record
book, and the form chart, week-by-week and ranking bars all survive restyled. So this
board is only about the look. Pick one and I will build the whole tab in it.</p>

<section>
  <h2 class="sec__h">Read the seam, not the skin</h2>
  <div class="callout">
    <p><b>The standings are identical in all six, on purpose.</b> You like them, so they
    are not up for debate, and leaving them in every frame turns the comparison into the
    right one: what happens where the Slate card stops and the flare starts. I have
    marked that line in every option. An option that only looks good with the standings
    cropped off is not an option, and cropping them is exactly how a mockup lies.</p>
    <p><b>This breaks a rule the theme wrote down on purpose.</b> theme.css says depth
    comes from layered surfaces and a hairline, <span class="mono">never from drawn-on
    texture</span>, because v1 painted yard lines behind the sign-in and they read as
    wireframe banding on a phone. You are asking to break that, which is a fine thing to
    ask. It just means S3 in particular has to clear a bar the others do not.</p>
    <p><b>The animations are real and running.</b> S2 breathes, S4 shimmers, S5 wipes.
    None of them start from opacity 0, because a backgrounded tab pauses CSS animations
    and has already stranded an invisible overlay in this app once.</p>
    <p><b>Every dark option costs the form chart its colours, and this was measured, not
    eyeballed.</b> Against each option's own chart well the four seat colours come in at
    <span class="mono">Grant 3.7-4.3, James 2.8-3.2, Parker 2.5-2.8, Nicole 2.1-2.4</span>
    to 1. WCAG puts a non-text graphic at 3:1 and a 2px line is a graphic, so three of the
    four seats fail on every dark option and Nicole fails by more than half. The charts
    below therefore use a brightened set that holds each seat's hue and clears
    <span class="mono">6.3:1</span> on the worst well. This is the same trap as the
    scorebug's gold, which measures 10.8:1 on near-black and 1.5:1 on a light card: a
    colour picked against one ground does not travel. <b>It applies to whichever dark
    option you pick,</b> so it is a cost of going dark rather than a mark against any one
    of them. S1 is the only option that keeps the seat colours untouched.</p>
  </div>
</section>

<section>
  <h2 class="sec__h">The six</h2>
  <p class="sec__lede">Six invented weeks, because the real season is two weeks old and
  every record would show at its weakest. Three records each: one clean, one ugly, one
  carrying another school's colour, which between them is everything a skin has to
  survive.</p>
  <div class="row">__OPTS__</div>
</section>

<section>
  <h2 class="sec__h">Recommendation</h2>
  <div class="rec">
    <h3>S2, and steal S1's dot leaders for the record rows</h3>
    <p><b>S2 is the one I would build.</b> You said cold and techy is the problem, and an
    amber bulb board is warm without being cute: it is the one direction here that is
    unmistakably football, unmistakably loud, and still the highest-contrast thing on the
    board. It also solves the seam better than anything except S5, because a hard cut
    from a light card to near-black reads as deliberate, where a cut to mid-tone brown or
    green reads as a rendering bug.</p>
    <p><b>S1 is the one that is actually a record book.</b> Everything else styles a list
    of records; S1 is the only one that looks like the back of a media guide, and the dot
    leaders do more work than any effect on this page. If you want the record book to feel
    like a book, this is it, and it is the cheapest to build by a distance.</p>
    <p><b>S5 is the safe answer and you should know why I am not leading with it.</b> It
    is the only option with no seam at all, because it is the scorebug language carried
    down the page. It is also the only option that adds nothing you have not already seen,
    and you did not ask for consistent, you asked for flare.</p>
    <p><b>S6 is the one I would enjoy most and trust least.</b> Brass on a 390px phone is
    four gradients per row. It looks superb here on a 27-inch monitor. Look at it on your
    phone before you pick it.</p>
    <p><b>S4 is a different product.</b> Cards are the only option that changes the
    interaction, not just the paint: you swipe a record book instead of scanning one. With
    twenty-odd records that is a lot of swiping. Good as a strip of the top three inside
    another option, which is worth doing whatever you pick.</p>
    <p><b>S3 I would not ship without seeing it on your phone.</b> The turf is a genuine
    football idea and the app has already been burned by exactly this once.</p>
    <p class="mono" style="margin-top:14px;color:var(--ink-3)">All six are CSS only. The
    records behind them are not: they need one new read-only RPC over graded games, which
    is a separate paste and the same for every option here.</p>
  </div>
</section>
</div>
"""


def main():
    # The standings block is generated from WEEKS, so it cannot drift from the chart
    # above it. Assert it anyway: four rows that do not add up would discredit the board.
    for name, _c, _t, _cor, _wr, pts in totals():
        assert pts == sum(w[COL[name]] for w in WEEKS), name
    assert len({p[5] for p in totals()}) == 4, "a tie here would need shared ranks drawn"

    css = open(os.path.join(ROOT, "scripts", "season_board.css"), encoding="utf-8").read()
    doc = (HEADER.replace("__CSS__", css)
           + BODY.replace("__OPTS__", "".join(figure(*o) for o in OPTIONS)))
    out = os.path.join(ROOT, "outputs", "season-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))
    for name, _c, _t, cor, wr, pts in totals():
        print("   %-7s %4d pts  %d-%d" % (name, pts, cor, wr))


if __name__ == "__main__":
    main()
