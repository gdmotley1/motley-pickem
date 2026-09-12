"""Render the pick-every-part board for the record book.

Grant on 2026-09-11, after the squares went live: "I want to handpick every part of this
records page. for each section, create three variants. Make them unique and distinct from
each other, not three brothers. Something to break up the gold a little bit too. maybe
some green velvet would be cool."

THE RULE THIS BOARD IS BUILT ON

No two variants in a row may share a MATERIAL. Three shades of brass would be three
brothers, which is the thing he named. So every row offers:

  - one in GREEN VELVET, because he asked and because it is the only material available
    that is dark, warm and not gold, which is exactly the gap in the case
  - one that uses NO PLATE AT ALL, working the wood itself
  - one from a material the case does not own yet: cream ledger stock, glass, a ticket

Five rows, fifteen variants. The standings are deliberately not among them: Grant said on
2026-09-11 that the scoreboard at the top is the part he already likes, and putting three
alternatives to it on this board would invite him to fix something that is not broken.

Everything is drawn on the real wood, because a material only means anything against the
thing next to it. A velvet swatch on a white page looks like every other velvet swatch.

    python scripts/build_records_board.py
"""
from __future__ import annotations

import base64
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def datauri(rel, px=48):
    from PIL import Image

    im = Image.open(os.path.join(ROOT, rel)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


TEAM = {"2633": "#ff8200", "127": "#18453b", "61": "#ba0c2f"}
LOGO = {k: datauri("static/logos/%s.png" % k) for k in TEAM}


def mk(team_id):
    if not team_id:
        return ""
    return ('<span class="mk" style="background:%s"><img src="%s" width="11" height="11" alt="">'
            '</span>' % (TEAM[team_id], LOGO[team_id]))


# Four records, chosen so every row is stress-tested the same way: a plain number, a
# negative, one carrying a team mark, and one whose holder line is a three-way tie.
RECORDS = [
    ("The Anchor", "6-0", "James", None),
    ("The Fade", "-280", "James", None),
    ("Money team", "+75", "Grant and Nicole", "2633"),
    ("Biggest miss", "20", "Grant, Parker and Nicole", None),
]

WEEKS = [("Week 6", "James", "190"), ("Week 5", "Parker", "188"), ("Week 4", "Nicole", "181")]

H2H = [("Grant", [("James", "3-2"), ("Parker", "4-1"), ("Nicole", "3-2")]),
       ("James", [("Grant", "2-3"), ("Parker", "3-2"), ("Nicole", "4-1")]),
       ("Parker", [("Grant", "1-4"), ("James", "2-3"), ("Nicole", "3-2")]),
       ("Nicole", [("Grant", "2-3"), ("James", "1-4"), ("Parker", "2-3")])]

SERIES = [("#3FCB83", [168, 141, 195, 128, 163, 174]),
          ("#F2913F", [179, 158, 166, 171, 152, 190]),
          ("#5FA8F2", [164, 172, 149, 155, 188, 137]),
          ("#F2739E", [147, 133, 158, 181, 144, 169])]


def chart(grid, tick):
    """Six weeks, four lines, on a 0-210 scale. Identical in every variant so the only
    thing being compared is what it is sitting in."""
    W, H, padL, padB, padT = 340, 74, 20, 12, 6
    n = 6
    xs = lambda i: padL + i * (W - padL - 4) / (n - 1)
    ys = lambda v: padT + (1 - v / 210) * (H - padT - padB)
    p = []
    for v in (0, 105, 210):
        p.append('<line x1="%.0f" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1"/>'
                 % (padL, ys(v), W - 2, ys(v), grid))
        p.append('<text x="%.0f" y="%.1f" fill="%s" font-size="7" text-anchor="end" '
                 'font-family="Archivo,sans-serif">%d</text>' % (padL - 4, ys(v) + 2.5, tick, v))
    for c, vals in SERIES:
        pts = " ".join("%.1f,%.1f" % (xs(i), ys(v)) for i, v in enumerate(vals))
        p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2" '
                 'stroke-linejoin="round" stroke-linecap="round"/>' % (pts, c))
        for i, v in enumerate(vals):
            p.append('<circle cx="%.1f" cy="%.1f" r="2.1" fill="%s"/>' % (xs(i), ys(v), c))
    return '<svg class="cw" viewBox="0 0 %d %d">%s</svg>' % (W, H, "".join(p))


# ------------------------------------------------------------------- 1 · squares ----
def squares(cls, tile_cls):
    tiles = []
    for label, value, who, team in RECORDS:
        tiles.append('<div class="t %s"><p class="k">%s</p><p class="v num">%s</p>'
                     '<p class="w">%s<span class="wn">%s</span></p></div>'
                     % (tile_cls, label, value, mk(team), who))
    return '<div class="%s"><div class="grid2">%s</div></div>' % (cls, "".join(tiles))


# ------------------------------------------------------------------ 2 · headings ----
def heads(kind):
    names = ["How you play", "One game, one moment"]
    if kind == "h1":
        body = "".join('<p class="h1v">%s</p>%s' % (n.upper(), squares("r1", "velvet"))
                       for n in names[:1])
        return body + '<p class="h1v">%s</p>%s' % (names[1].upper(), squares("r1", "velvet"))
    if kind == "h2":
        return "".join('<p class="h2b">%s</p>%s' % (n.upper(), squares("r1", "velvet"))
                       for n in names)
    return "".join('<p class="h3w"><span>%s</span><i></i></p>%s' % (n, squares("r1", "velvet"))
                   for n in names)


# --------------------------------------------------------------------- 3 · weeks ----
def weeks(cls, row_cls):
    rows = "".join('<div class="r %s"><span class="n">%s</span><span class="who">%s</span>'
                   '<span class="p num">%s</span></div>' % (row_cls, w, who, p)
                   for w, who, p in WEEKS)
    return '<div class="%s">%s</div>' % (cls, rows)


# --------------------------------------------------------------------- 5 · h2h ----
def h2h(cls, kind):
    rows = "".join(
        '<div class="r"><span class="me">%s</span>%s</div>'
        % (me, "".join('<span class="v">%s<b>%s</b></span>' % (o, r) for o, r in vs))
        for me, vs in H2H)
    if kind == "med":
        meds = "".join(
            '<div class="med"><span class="disc">%s</span><span><span class="nm">%s</span>'
            '<span class="rc">%s</span></span></div>'
            % (me[0], me, " · ".join("%s %s" % (o, r) for o, r in vs[:2]))
            for me, vs in H2H)
        return '<div class="%s"><div class="panel">%s</div></div>' % (cls, meds)
    return ('<div class="%s"><div class="panel"><p class="k">Head to head, by week</p>%s</div>'
            '</div>' % (cls, rows))


def case(inner):
    return '<div class="case">%s</div>' % inner


def opt(name, material, tag, body, note):
    chip = '<span class="tag %s">%s</span>' % (
        {"velvet": "tag--v", "none": "tag--n"}.get(tag, ""), material)
    return ('<figure class="opt"><figcaption class="opt__cap">%s%s</figcaption>'
            '<p class="opt__mat">%s</p>%s<p class="opt__note">%s</p></figure>'
            % (name, chip, material, case(body), note))


ROWS = [
    ("1 &middot; The record square",
     "Seventeen of these are on screen at once, so this is the row that decides what the "
     "page feels like. All three carry the same four records, including the negative and "
     "the three-way tie, because those are what break a tile.",
     [
         ("R1 &middot; Velvet swatch", "Green velvet", "velvet",
          squares("r1", "velvet"),
          "Velvet ground, gold numeral, cream label, gold piping. <b>Breaks up the gold "
          "without leaving the case:</b> the number is still brass, so the page still "
          "reads as a trophy wall, but seventeen of them are green instead of yellow. "
          "The one I would build."),
         ("R2 &middot; Carved", "No plate at all", "none",
          squares("r2", ""),
          "No tile. The number is cut straight into the wood, with one gold hairline "
          "under each. <b>The quietest thing on this board by a distance,</b> and the "
          "only variant where the case itself is the surface. Risk: on a phone in "
          "sunlight, dark-on-dark carving is the first thing to disappear."),
         ("R3 &middot; Ledger card", "Cream stock", "",
          squares("r3", "ledger"),
          "A page from a book rather than an object on a wall: cream stock, a red rule "
          "under the label, condensed black figures, the holder in italic. <b>The most "
          "readable of the three and the most 'record book',</b> and the furthest from "
          "the trophy case you picked."),
     ]),
    ("2 &middot; Section headings",
     "Four of these break the page into groups. Shown with velvet squares under them so "
     "you can see the join, which is the whole job of a heading.",
     [
         ("H1 &middot; Velvet banner", "Green velvet", "velvet",
          heads("h1"),
          "A velvet band running the full width of the case, piped top and bottom. "
          "<b>The strongest divider here:</b> it physically separates the groups rather "
          "than labelling them. Costs the most vertical space, about 30px each."),
         ("H2 &middot; Brass rail", "Brass", "",
          heads("h2"),
          "A thin brass bar with the heading struck into it and a screw at each end. "
          "<b>Most literally a trophy case.</b> It is also more gold, which is the thing "
          "you asked to break up, so it works best paired with velvet squares."),
         ("H3 &middot; Branded", "No plate at all", "none",
          heads("h3"),
          "Burned into the wood, with a gold hairline running out to the right edge. "
          "<b>Takes almost no height and adds no material,</b> which lets the squares do "
          "all the talking. The most restrained option on the board."),
     ]),
    ("3 &middot; Week by week",
     "Six to fifteen rows by the end of the season, so this row is really about height. "
     "Each one is shown at three weeks.",
     [
         ("W1 &middot; Velvet ribbons", "Green velvet", "velvet",
          weeks("w1", "velvet"),
          "Each week a velvet strip with the score in gold. <b>Matches R1 exactly,</b> so "
          "if you take the velvet square this is the row that belongs with it. Softest "
          "block on the page."),
         ("W2 &middot; Ticket stubs", "Cream stock", "",
          weeks("w2", ""),
          "Perforated down the left, like the stub you keep. <b>The only variant on this "
          "whole board with a story attached,</b> and the one your family will notice. "
          "Fifteen stubs by December might be a lot of cream."),
         ("W3 &middot; Brass rails", "Brass", "",
          weeks("w3", ""),
          "Half-height brass bars, tighter than the plates they replace. <b>Fits fifteen "
          "weeks in the space the current six take.</b> The safe answer, and more gold."),
     ]),
    ("4 &middot; The form chart",
     "One chart, six weeks, four lines. The lines are identical in all three: the only "
     "thing changing is what the chart is sitting in.",
     [
         ("F1 &middot; Velvet well", "Green velvet", "velvet",
          '<div class="f1"><div class="well">%s</div></div>' % chart("rgba(201,161,57,.28)", "#9dc4a8"),
          "The felt well you already have, with the nap turned up and gold gridlines. "
          "<b>The smallest change on this board</b> and the one that needs no decision."),
         ("F2 &middot; Under glass", "Glass and brass", "",
          '<div class="f2"><div class="well">%s</div></div>' % chart("rgba(255,255,255,.13)", "#8fa3b5"),
          "A brass frame with a glass sheen across it. <b>Makes the chart the exhibit</b> "
          "rather than a readout. The specular streak is fixed, not animated, because a "
          "moving highlight over data is a distraction you cannot switch off."),
         ("F3 &middot; Graph paper", "Cream stock", "",
          '<div class="f3"><div class="well">%s</div></div>' % chart("rgba(60,110,90,.22)", "#4e5c4e"),
          "Engineering paper mounted flat on the wood. <b>By far the easiest of the three "
          "to actually read a value off,</b> because the lines sit on white. Pairs with "
          "R3 and W2 if you go the whole cream route."),
     ]),
    ("5 &middot; All four of you",
     "The head-to-head grid. Worth saying plainly: this is the one block that is "
     "everyone's scores against everyone, which is the thing you just told me to cut from "
     "the squares. Three ways to keep it, and cutting it is a fair fourth answer.",
     [
         ("A1 &middot; Velvet pinboard", "Green velvet", "velvet",
          h2h("a1", "grid"),
          "The grid on velvet with gold figures. <b>Reads as one object</b> rather than "
          "twelve numbers, which is most of what was wrong with it."),
         ("A2 &middot; Scorecard", "Cream stock", "",
          h2h("a2", "grid"),
          "Ruled cream, fixed row height, like a scorebook page. <b>The most legible and "
          "the most honest about being a table.</b> If the grid stays, this is the "
          "version that earns its space."),
         ("A3 &middot; Medallions", "Brass and velvet", "",
          h2h("a3", "med"),
          "One struck medallion per person with their two closest matchups beside it. "
          "<b>Drops from twelve numbers to eight</b> and stops being a table at all. "
          "Loses the full grid, which may be the point."),
     ]),
]


HEADER = """<title>The Record Book, Part by Part</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 11 September 2026</p>
<h1 class="doc__title">The record book, part by part</h1>
<p class="doc__sub">Five sections, three variants each. Pick one per row and I will build
exactly that; mixing across rows is fine and expected.</p>

<section>
  <h2 class="sec__h">How these were kept apart</h2>
  <div class="callout">
    <p><b>No two variants in a row share a material.</b> Three shades of brass would be
    the three brothers you warned about, so every row has one in green velvet, one that
    uses no plate at all and works the wood itself, and one in a material the case does
    not own yet: cream ledger stock, glass, a ticket.</p>
    <p><b>Velvet is in every row on purpose.</b> It is the only material available that
    is dark, warm and not gold, which is exactly the gap. Its trick is the nap: a flat
    green rectangle reads as paint, so each one carries an off-centre highlight, a dark
    rim on all four sides and a faint diagonal sheen. The gold piping is a 1px inset ring,
    which is how velvet is actually finished.</p>
    <p><b>Everything is on the real wood.</b> A material only means something against the
    thing next to it, and a swatch on a white page would flatter all fifteen equally.</p>
    <p><b>All fifteen were measured, and three of them started out broken.</b> The two
    carve-into-the-wood variants came in at <span class="mono">1.05:1</span> and
    <span class="mono">1.09:1</span>, dark stain on dark stain. That is not a risky
    option, it is an unreadable one, and putting it on the board would have been offering
    you a straw man. A real carve goes THROUGH the stain and exposes pale raw wood, so the
    glyph is light and the shadow sits on its top edge; same idea, now 10.5 and 11.3 to 1.
    The thin brass rail's label was 3.14 because a rail's gradient runs darker under text
    than a full plate's does, which is the third time that exact trap has come up today.
    Worst reading anywhere on the board is now <span class="mono">4.82:1</span>.</p>
    <p><b>The standings are not on this board.</b> You said the scoreboard at the top is
    the part you already like. Offering three alternatives to it would be inviting you to
    fix something that is not broken; say the word and I will draw them.</p>
  </div>
</section>

__ROWS__

<section>
  <h2 class="sec__h">If you want one answer</h2>
  <div class="callout" style="border-left-color:#1c7a45">
    <p><b>R1 velvet squares, H3 branded headings, W3 brass rails, F1 velvet well, A2
    scorecard.</b> That gives you green as the dominant material with gold kept for
    numbers only, which is the "break up the gold" you asked for taken seriously rather
    than sprinkled. Headings cost nothing, the week rows stay compact enough for fifteen
    of them, and the one genuine table on the page is the one thing left in plain cream,
    where a table belongs.</p>
    <p><b>The all-cream route is the real alternative.</b> R3, W2, F3 and A2 together stop
    being a trophy case and become a scrapbook. It is more readable than anything else
    here and it is a different product; worth knowing it exists before you rule it out.</p>
    <p class="mono" style="margin-top:12px;color:var(--ink-3)">All fifteen are CSS. None
    of them touch seasonRecords.js, the records themselves, or migration 015.</p>
  </div>
</section>
</div>
"""


def main():
    out_rows = []
    for title, lede, variants in ROWS:
        out_rows.append(
            '<section><h2 class="sec__h">%s</h2><p class="sec__lede">%s</p>'
            '<div class="row">%s</div></section>'
            % (title, lede, "".join(opt(*v) for v in variants)))

    css = open(os.path.join(ROOT, "scripts", "records_board.css"), encoding="utf-8").read()
    doc = HEADER.replace("__CSS__", css) + BODY.replace("__ROWS__", "".join(out_rows))
    dest = os.path.join(ROOT, "outputs", "records-board.html")
    open(dest, "w", encoding="utf-8").write(doc)
    n = sum(len(v) for _, _, v in ROWS)
    print("wrote %s  %.1f KB  %d sections, %d variants" %
          (dest, len(doc.encode()) / 1024, len(ROWS), n))


if __name__ == "__main__":
    main()
