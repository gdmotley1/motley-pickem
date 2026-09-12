"""Render the options board for the week scorebug's rows: alignment, and the banked bar.

Grant, 2026-09-12, looking at the live Board on a Saturday morning: "Nicole scored. She's
in first place. It's shifted a little to the left. Also, the bar at the bottom with the
score showing the locked plus potential, you can hardly see it."

Both are real and they are different kinds of problem.

THE SHIFT is a bug. `.bugrow` is its own grid, one per row, and two of its columns are
`auto`. Nicole's 13 is two digits, everyone else's score is one, so her points column is
a digit wider and every column to its LEFT moves. Her record sits inboard of the other
three. Nothing is wrong with the alignment rules; the columns simply are not shared
between rows, because there is no shared grid to share them.

THE BAR is a design problem, and thickening it would not fix it. `.bugrule` is two pixels
carrying banked-against-ceiling on a 0..210 scale, and that scale has no useful range at
either end of a week. This board renders every option at BOTH ends so the range is
visible rather than argued: Saturday noon, where almost nothing has happened, and
Saturday night, where everyone has finished within a few points of everyone else.

Self-contained: no dev server, no network. Logos are inlined as data URIs so the file
renders identically in the preview pane and published as an Artifact.

    python scripts/build_bugrow_board.py
"""
from __future__ import annotations

import base64
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "bugrow-board.html")

# ---------------------------------------------------------------- the numbers

# Real Week 2, both moments run through the app's own weekScore(). NOW is exactly what
# the database held around noon ET on Saturday 2026-09-12, one final and three in
# progress; SATURDAY plays the same twenty games out with four upsets, which is the only
# way to see how a design behaves once a week is nearly done.
NOW = {
    "label": "Week 2",
    "note": "1 of 20",
    "playing": 3,
    "total": 210,
    "when": "Saturday noon, one game final",
    "players": [
        # rank, name, team, points, correct, played, live, colour
        (1, "Nicole", "61", 13, 1, 1, 197, "#8A2E4F"),
        (2, "James", "2655", 7, 1, 1, 203, "#1F6F4A"),
        (3, "Parker", "338", 1, 1, 1, 209, "#2E5C8A"),
        (4, "Grant", "8", 0, 0, 1, 203, "#B85C1F"),
    ],
}
SAT = {
    "label": "Week 2",
    "note": "16 of 20",
    "playing": 4,
    "total": 210,
    "when": "Saturday night, four still on",
    "players": [
        (1, "Parker", "338", 150, 12, 16, 14, "#2E5C8A"),
        (2, "Grant", "8", 125, 12, 16, 44, "#B85C1F"),
        (2, "James", "2655", 125, 11, 16, 41, "#1F6F4A"),
        (4, "Nicole", "61", 114, 9, 16, 44, "#8A2E4F"),
    ],
}

# From static/data/teams.json. `alt` is the block colour, `bg` the disc the mark sits on.
TEAM = {
    "61": {"alt": "#413f3e", "bg": "#ba0c2f"},       # Georgia
    "2655": {"alt": "#006747", "bg": "#418fde"},     # Tulane
    "338": {"alt": "#3c4244", "bg": "#fdbb30"},      # Kennesaw State
    "8": {"alt": "#a32136", "bg": "#ffffff"},        # Arkansas
}


def datauri(team_id: int | str, px: int = 64) -> str:
    from PIL import Image

    im = Image.open(os.path.join(ROOT, "static", "logos", "%s.png" % team_id)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


LOGO = {k: datauri(k) for k in TEAM}


# ------------------------------------------------------------------- pieces


def block(p, size=24):
    """The colour block: seed number, and the school mark on its own disc.

    The mark is a background-image off a custom property rather than an <img>, because
    this board draws the same four logos 56 times and inlining the base64 at each one
    took the file from 26KB to 436KB. Rendered size is identical.
    """
    _rank, _name, team, *_ = p
    t = TEAM[team]
    n = round(size * 0.72)
    return (
        '<span class="bugrow__block" style="background:%s">'
        '<span class="bugrow__seed num">%d</span>'
        '<span class="avatar avatar--team bugrow__mark" style="width:%dpx;height:%dpx;'
        'background:%s"><i class="mk" style="width:%dpx;height:%dpx;'
        'background-image:var(--lg-%s)"></i></span></span>'
        % (t["alt"], p[0], size, size, t["bg"], n, n, team)
    )


def rule(p, total, best_ceiling=None):
    """The banked strip. Solid is in the bank, the pale run is the ceiling."""
    _r, _n, _t, pts, _c, _pl, live, colour = p
    scale = best_ceiling or total
    return (
        '<span class="bugrule">'
        '<i class="is-live" style="width:%.1f%%;background:%s"></i>'
        '<i style="width:%.1f%%;background:%s"></i></span>'
        % (100.0 * (pts + live) / scale, colour, 100.0 * pts / scale, colour)
    )


def row(opt, p, best, total, mine="Grant"):
    """One player row, in whichever option's dialect."""
    rank, name, _team, pts, correct, played, live, colour = p
    gap = best - pts
    lead = " is-leader" if gap == 0 else ""
    you = '<span class="bugrow__you">YOU</span>' if name == mine else ""
    rec = '<span class="bugrow__rec num">%d-%d</span>' % (correct, played - correct)
    gap_txt = "&mdash;" if gap == 0 else "-%d" % gap
    ceiling = pts + live

    if opt == "now":
        # Exactly what ships today, two `auto` columns and all.
        return (
            '<div class="bugrow%s">%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span>%s</div>'
            % (lead, block(p), name, you, rec, pts, gap_txt, rule(p, total))
        )

    if opt == "A":
        return (
            '<div class="bugrow bugrow--A%s">%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span>'
            '<span class="railA"><i class="railA__live" style="width:%.1f%%;background:%s">'
            '</i><i class="railA__bank" style="width:%.1f%%;background:%s"></i></span></div>'
            % (lead, block(p), name, you, rec, pts, gap_txt,
               100.0 * ceiling / total, colour, 100.0 * pts / total, colour)
        )

    if opt == "B":
        return (
            '<div class="bugrow bugrow--B%s">%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="ptsB"><b class="num">%d</b>'
            '<em class="num" style="color:%s">+%d</em></span>'
            '<span class="bugrow__gap num">%s</span></div>'
            % (lead, block(p), name, you, rec, pts, colour, live, gap_txt)
        )

    if opt == "C":
        return (
            '<div class="bugrow bugrow--C%s">%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span></div>'
            % (lead, block(p), name, you, rec, pts, gap_txt)
        )

    if opt == "D":
        return (
            '<div class="bugrow bugrow--C%s">%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span></div>'
            % (lead, block(p), name, you, rec, pts, gap_txt)
        )

    if opt == "E":
        cap = ' is-lead' if gap == 0 else ''
        return (
            '<div class="bugrow bugrow--E%s">%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span>'
            '<span class="railE%s"><i class="railE__live" style="width:%.1f%%;'
            'background-color:%s"></i><i class="railE__bank" style="width:%.1f%%;'
            'background-color:%s;box-shadow:0 0 10px 1px %s"></i></span></div>'
            % (lead, block(p), name, you, rec, pts, gap_txt, cap,
               100.0 * ceiling / total, colour, 100.0 * pts / total, colour, colour)
        )

    if opt == "F":
        return (
            '<div class="bugrow bugrow--F%s">'
            '<span class="washF"><i class="washF__live" style="width:%.1f%%;background:%s">'
            '</i><i class="washF__bank" style="width:%.1f%%;background:%s"></i>'
            '<u style="left:%.1f%%;color:%s"></u></span>'
            '%s<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span></div>'
            % (lead, 100.0 * ceiling / total, colour, 100.0 * pts / total, colour,
               100.0 * pts / total, colour, block(p), name, you, rec, pts, gap_txt)
        )

    raise ValueError(opt)


def track(state):
    """Option D: one shared strip, zoomed to the range that is actually in play.

    Lanes run in row order, so the Nth lane is the Nth row above it. Initials sit in a
    fixed gutter rather than beside each dot: beside the dot they collided whenever two
    players were close, which on a Friday is all four of them.
    """
    ps = state["players"]
    lo = min(p[3] for p in ps)
    hi = max(p[3] + p[6] for p in ps)
    span = max(1, hi - lo)
    best = max(p[3] for p in ps)
    gutter, marks = [], []
    for i, p in enumerate(ps):
        _rank, name, _t, pts, _c, _pl, live, colour = p
        y = 3 + i * 7
        x = 100.0 * (pts - lo) / span
        w = 100.0 * live / span
        gutter.append('<b style="top:%dpx;color:%s">%s</b>' % (y, colour, name[:1]))
        marks.append(
            '<i class="trk__whisk" style="top:%.1fpx;left:%.2f%%;width:%.2f%%;'
            'background-color:%s"></i>'
            '<i class="trk__dot%s" style="top:%dpx;left:%.2f%%;background-color:%s"></i>'
            % (y + 2.5, x, w, colour, " is-lead" if pts == best else "", y, x, colour)
        )
    return (
        '<div class="trk"><div class="trk__plot">'
        '<span class="trk__gut">%s</span>'
        '<span class="trk__well"><span class="trk__in">'
        '<i class="trk__floor" style="left:%.2f%%"></i>%s</span></span></div>'
        '<div class="trk__sc"><span class="num">%d</span>'
        '<span class="trk__note">dot = banked &middot; tail = still live</span>'
        '<span class="num">%d</span></div></div>'
        % ("".join(gutter), 100.0 * (best - lo) / span, "".join(marks), lo, hi)
    )


def top(state):
    live = ('<span class="bug__live"><i></i>%d LIVE</span>' % state["playing"]) if state["playing"] else ""
    return ('<div class="bug__top"><span class="bug__wk">%s</span>%s'
            '<span class="bug__of num">%s</span></div>'
            % (state["label"], live, state["note"]))


def foot(state, opt):
    ps = state["players"]
    best = max(p[3] for p in ps)
    me = [p for p in ps if p[1] == "Grant"][0]
    gap = best - me[3]
    where = "you lead" if gap == 0 else "you are %d back" % gap
    txt = "Out of %d. %s%s, with %d still to play for." % (
        state["total"], where[0].upper(), where[1:], me[6])
    if opt in ("C", "D"):
        return ('<p class="bug__foot bug__foot--big">Out of <b class="num">%d</b>. '
                '%s%s, with <b class="num">%d</b> still to play for.</p>'
                % (state["total"], where[0].upper(), where[1:], me[6]))
    return '<p class="bug__foot">%s</p>' % txt


def bug(opt, state):
    ps = state["players"]
    best = max(p[3] for p in ps)
    rows = "".join(row(opt, p, best, state["total"]) for p in ps)
    # D's track is labelled at both ends and says what the footline says, so the
    # footline goes rather than saying it twice and costing another 22px.
    tail = track(state) if opt == "D" else foot(state, opt)
    return ('<div class="bug bug--light bug--rec bug--%s">%s%s%s</div>'
            % (opt, top(state), rows, tail))


def pair(opt):
    """Every option twice: the week that has barely started, and the one nearly done."""
    return ('<div class="pair">'
            '<div class="pair__half"><div class="pair__when">%s</div>%s</div>'
            '<div class="pair__half"><div class="pair__when">%s</div>%s</div></div>'
            % (NOW["when"], bug(opt, NOW), SAT["when"], bug(opt, SAT)))


# --------------------------------------------------------------------- copy

# key, name, measured change in card height at 366px, what it is, what it costs.
# The heights were read off the rendered cards, not estimated: two estimates made before
# measuring were wrong, D by 18px.
OPTIONS = [
    ("A", "Straighten and thicken", "+24px",
     "The smallest change that answers both notes. The two-pixel hairline becomes a "
     "six-pixel rail with a real track under it, inset to start where the colour block "
     "ends. Nothing else moves.",
     "Six pixels a row. Honest catch: look at the night card. The rail is easy to see "
     "now and still says almost nothing, because four players inside 36 points of each "
     "other, on a 210 scale, draw four solid runs between 54% and 71% of the rail."),
    ("B", "Numbers, not a bar", "+32px",
     "Delete the rail and print the thing it was trying to draw. The score becomes a "
     "two-line stack: points banked, and under it what is still live, in the player's "
     "own colour.",
     "Eight pixels a row. No scale, so nothing to misread, and the only option that is "
     "as useful at noon as it is at night."),
    ("C", "Cut it", "+5px",
     "The rail goes and nothing replaces it. The sentence under the rows already says "
     "it all, so that gets to be readable instead: darker ink, a size up, on the card "
     "rather than in a grey well, with its two numbers set bold.",
     "Each row gives 2px back and the sentence grows. The calmest card, and the one "
     "that admits the bar was never carrying its weight."),
    ("D", "One race track", "+30px",
     "Four rails become one strip under the rows, and it stops measuring against 210. "
     "It zooms to the range actually in play, from the lowest score on the board to the "
     "highest finish anyone can still reach. A dot is what you have banked, its tail is "
     "what is still live, and the black line is the lead: anyone whose tail reaches past "
     "that line is still in it. The sentence under the rows goes, because the gap "
     "column and the tails already say it.",
     "The track adds a strip, the sentence comes out, each row gives 2px back. The only "
     "option whose picture gets <em>more</em> interesting as the week goes on, and the "
     "only one that answers &ldquo;can I still catch her&rdquo; without arithmetic. "
     "Honest catch: at noon it is four dots piled at the left edge, because almost "
     "nothing has happened yet."),
    ("E", "Broadcast rail", "+56px",
     "The loud one. A twelve-pixel rail in a dark well under every row: banked in solid "
     "colour with a glow off its leading edge, what is still live in a striped run after "
     "it, and the leader's rail capped in gold. The stadium version.",
     "Fourteen pixels a row. It has A's scale problem: at night the four solid runs sit "
     "within 17 points of each other, so the rail mostly restates the scores above it, "
     "and at noon it is four stripes. Pick it if you want the card to look like a "
     "broadcast more than you want the bar to tell you something."),
    ("F", "The row is the bar", "+0px",
     "No rail at all. Each row is washed in the player's colour as far as what they "
     "have banked, notched top and bottom where it stops, with a paler wash on to their "
     "ceiling. The name and numbers sit on top.",
     "The card does not grow by a pixel. The risk is the opposite of A's: at noon "
     "Nicole's wash is 6% of the row and the other three have almost none, so the rows "
     "look unfinished rather than empty."),
]

# The standalone file needs a doctype, or the preview pane and headless Edge lay it out
# in quirks mode and every measurement on the board stops matching the app. The Artifact
# host supplies its own skeleton and wants the page without one, so it gets a fragment.
DOC = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
"""
HEAD = """<title>Scoreboard Second Pass</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,600..800&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
"""


def build(standalone: bool = True) -> str:
    opts = []
    for key, title, px, body, cost in OPTIONS:
        opts.append(
            '<section class="opt" id="opt-%s"><div class="opt__hd">'
            '<span class="opt__k">%s</span><h2>%s</h2>'
            '<span class="opt__px" title="Change in card height on a 390px phone">%s</span>'
            '</div><p class="opt__p">%s</p><p class="opt__cost"><b>Cost.</b> %s</p>%s'
            '</section>' % (key, key, title, px, body, cost, pair(key)))

    logos = ":root{%s}" % "".join(
        "--lg-%s:url(%s);" % (k, v) for k, v in LOGO.items())
    return ((DOC if standalone else "") + HEAD
            + "<style>" + logos + chr(10) + CSS + "</style>" + BODY % {
                "today": pair("now"),
                "options": "".join(opts),
            })


CSS = open(os.path.join(ROOT, "scripts", "bugrow_board.css"), encoding="utf-8").read()
BODY = open(os.path.join(ROOT, "scripts", "bugrow_board.html"), encoding="utf-8").read()


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        html = build(standalone)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("wrote %s  (%.0f KB)" % (path, len(html.encode()) / 1024))
    print(json.dumps({"options": [o[0] for o in OPTIONS]}))
