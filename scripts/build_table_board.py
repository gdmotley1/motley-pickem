"""Render table styles for "Everyone's numbers", the record book's per-player section.

Grant, 2026-09-12, after the three record book layouts: "I like the trophy room. Let's use
that, and I like the up for grabs part." Worst pick becomes worst miss. And for everyone's
numbers, "mix in the head to head where it reads more like a table ... do some mock ups of
what the table style could look like. Maybe with the names and logos of our teams frozen so
you can scroll through or maybe do columns with the colors of ... their alternate colors."

"Frozen so you can scroll through" reads two ways, and both are drawn:
  T1  the four names frozen across the top while you scroll down the records
  T2  the four names frozen down the left while you swipe sideways through the records
Then the colour columns, twice, because the colours he named do not survive contact:
  T3  the alternate colours exactly as the scoreboard uses them. Kennesaw State's and
      Georgia's are #3c4244 and #413f3e, 1.03:1 apart, so Parker and Nicole look the same
  T4  one colour per school with no clash: cardinal, green, gold, and Georgia's black with
      a red stripe (red itself would sit next to Arkansas cardinal)

Every phone is its own scroll container with the app's sticky header in it, so the frozen
parts can actually be tried on the published board. The data, badges and placeholder
medals come from build_recordbook_board.py, which stays the one source for them.

    python scripts/build_table_board.py
"""
from __future__ import annotations

import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_recordbook_board as rb  # noqa: E402

ROOT = rb.ROOT
OUT = os.path.join(ROOT, "outputs", "table-board.html")
e = html.escape
NAMES = rb.NAMES

# The best in each row gets gold; on the two rows where the top number is bad news, the
# holder gets red instead. Fewest points has no holder until two weeks are finished.
LEAD = {"best_week": {"Grant"}, "best_record": {"Grant", "James"}, "streak": {"James"},
        "my_upset": {"Grant", "Nicole"}, "weeks_won": {"Grant"}, "season_record": {"James"}}
WORST = {"worst_miss": {"James"}}

# What a cell says under its number. Anything the row label already says is dropped.
DETAIL = {"best_week": True, "best_record": True, "low_week": True, "streak": False,
          "worst_miss": True, "my_upset": True, "weeks_won": True, "season_record": False}

SCOREBUG = {"Grant": "#a32136", "James": "#006747", "Parker": "#3c4244", "Nicole": "#413f3e"}
SCHOOL = {"Grant": ("#a32136", "#ffffff", None), "James": ("#006747", "#ffffff", None),
          "Parker": ("#fdbb30", "#15181c", None), "Nicole": ("#1f1d1c", "#ffffff", "#ba0c2f")}


def cell(name, rid, colour=None):
    value, detail = rb.SHELF[name][rid]
    cls = "rt-cell"
    if value is None:
        cls += " is-open"
    if name in LEAD.get(rid, ()):
        cls += " is-lead"
    if name in WORST.get(rid, ()):
        cls += " is-worst"
    style = ' style="--col:%s"' % colour if colour else ""
    sub = '<em>%s</em>' % e(detail) if (DETAIL[rid] or value is None) else ""
    return ('<div class="%s" role="cell"%s><b class="num">%s</b>%s</div>'
            % (cls, style, e(value) if value else "&ndash;", sub))


def app_header():
    return ('<header class="apphdr"><div><span class="apphdr__title">Motley Pick&apos;em</span>'
            '<span class="apphdr__week">Week 2 &middot; 20 games</span></div>'
            '<span class="apphdr__me">%s<span class="apphdr__name">Grant</span></span></header>'
            % rb.face("Grant", 24))


def phone(inner, cls=""):
    """A phone that scrolls on its own, with the app's sticky header inside it, so a frozen
    row or column behaves on the board the way it would in the app."""
    return ('<div class="rt-phone %s"><div class="app" data-mode="book">%s<main class="app__body">'
            '<div class="app__page">%s</div></main></div></div>' % (cls, app_header(), inner))


def stub():
    """The last of the Hall of shame, so the table is seen where it sits on the tab."""
    return ('<div class="rt-stub"><p>&hellip; Hall of fame and Hall of shame above</p></div>'
            '<div class="rk-title"><p class="rk-kick">Everyone&apos;s numbers</p>'
            '<h3>The table</h3></div>')


# ------------------------------------------------------------------ T1, T3, T4


def across(colours=None, trim=None, ink=None, cls=""):
    head = []
    for n in NAMES:
        style = ""
        if colours:
            style = ' style="--col:%s;--ink:%s;--trim:%s"' % (
                colours[n], (ink or {}).get(n, "#ffffff"), (trim or {}).get(n) or "transparent")
        head.append('<div class="rt-hcell" role="columnheader"%s>%s<b>%s</b></div>'
                    % (style, rb.face(n, 30), n))
    body = []
    for rid in rb.SHELF_ROWS:
        cells = "".join(cell(n, rid, colours[n] if colours else None) for n in NAMES)
        body.append('<div class="rt-rec" role="rowgroup"><div class="rt-rec__label" role="rowheader">'
                    '%s<span>%s</span></div><div class="rt-row" role="row">%s</div></div>'
                    % (rb.medal(rid, 34), e(rb.BY_ID[rid][2]), cells))
    return ('<div class="rt-across %s" role="table" aria-label="Everyone\'s numbers">'
            '<div class="rt-head" role="row">%s</div><div class="rt-body">%s</div></div>'
            % (cls, "".join(head), "".join(body)))


def t1():
    return phone(stub() + across(cls="is-plain"))


def t3():
    return phone(stub() + across(SCOREBUG, cls="is-colour"))


def t4():
    colours = {n: SCHOOL[n][0] for n in NAMES}
    ink = {n: SCHOOL[n][1] for n in NAMES}
    trim = {n: SCHOOL[n][2] for n in NAMES if SCHOOL[n][2]}
    return phone(stub() + across(colours, trim, ink, cls="is-colour"))


# --------------------------------------------------------------------------- T2


def t2_table(badge=44):
    """The frozen-names table on its own, so the full-page board can reuse it. Badges went
    from 30px to 44px when Grant asked for them "a little bigger"."""
    heads = "".join('<th scope="col">%s<span>%s</span></th>' % (rb.medal(rid, badge), e(rb.BY_ID[rid][2]))
                    for rid in rb.SHELF_ROWS)
    rows = []
    for n in NAMES:
        tds = []
        for rid in rb.SHELF_ROWS:
            value, detail = rb.SHELF[n][rid]
            cls = []
            if value is None:
                cls.append("is-open")
            if n in LEAD.get(rid, ()):
                cls.append("is-lead")
            if n in WORST.get(rid, ()):
                cls.append("is-worst")
            sub = '<em>%s</em>' % e(detail) if (DETAIL[rid] or value is None) else ""
            tds.append('<td class="%s"><b class="num">%s</b>%s</td>'
                       % (" ".join(cls), e(value) if value else "&ndash;", sub))
        rows.append('<tr><th scope="row">%s<span>%s</span></th>%s</tr>'
                    % (rb.face(n, 32), n, "".join(tds)))
    return ('<div class="rt2"><div class="rt2-scroll"><table><thead><tr><th class="rt2-corner" scope="col">'
            '<span>Swipe</span></th>%s</tr></thead><tbody>%s</tbody></table></div>'
            '<p class="rt2-hint">Swipe sideways for all eight &rarr;</p></div>' % (heads, "".join(rows)))


def t2():
    return phone(stub() + t2_table(), "is-short")


OPTIONS = [
    ("T1", "Frozen header", t1,
     "Your four names and schools pinned across the top. Scroll down through the eight "
     "records and the header stays put under the app bar, so you always know whose column "
     "is whose. The best in each row is ringed in gold; on worst miss, the holder is in red.",
     "Scroll the phone to try it. Eight records is about two screens, and the names never "
     "leave."),
    ("T2", "Frozen names, swipe sideways", t2,
     "Turned the other way, like a stats table in the ESPN app. The four of you are pinned "
     "down the left with your schools, and the eight records scroll sideways past you. The "
     "whole thing is only four rows tall.",
     "By far the shortest on the page, but you see three records at a time and have to "
     "swipe for the rest, so nothing is on screen at once."),
    ("T3", "Team colors, as the scoreboard uses them", t3,
     "Each column is headed and tinted in that person's scoreboard color, the same blocks as "
     "the Board: Arkansas cardinal, Tulane green, and the dark blocks for Kennesaw State and "
     "Georgia. Names frozen on top as in T1.",
     "Look at Parker and Nicole: the two dark blocks are #3c4244 and #413f3e, a contrast of "
     "1.03 to 1, so their columns come out the same color."),
    ("T4", "Team colors, one each", t4,
     "The same idea with a color per school that cannot be confused: Arkansas cardinal, "
     "Tulane green, Kennesaw State gold, and Georgia black with a red stripe. Georgia red "
     "itself would sit right next to Arkansas cardinal.",
     "The loudest of the four, and every header is distinct. Two honest catches: Kennesaw "
     "gold is light, so Parker's header takes dark text, and Georgia black barely tints its "
     "column on a dark page, so Nicole's column is found by its header rather than its "
     "shading."),
]


def build(standalone: bool) -> str:
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()
                  for f in ("theme.css", "app.css"))
    rk = open(os.path.join(ROOT, "scripts", "recordbook_board.css"), encoding="utf-8").read()
    board = open(os.path.join(ROOT, "scripts", "table_board.css"), encoding="utf-8").read()
    body = open(os.path.join(ROOT, "scripts", "table_board.html"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (t, rb.logo(t)) for t in rb.TEAM.values())
    symbols = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>'
               % "".join('<symbol id="i-%s" viewBox="0 0 512 512">%s</symbol>' % (k, v)
                         for k, v in rb.MOD["icons"].items()))
    opts = "".join(
        '<section class="bd-opt" id="opt-%s"><div class="bd-opt__hd"><span class="bd-opt__k">%s</span>'
        '<h2>%s</h2><span class="bd-opt__px" data-measure>&hellip;</span></div>'
        '<div class="bd-opt__grid"><div class="bd-opt__copy"><p>%s</p><p class="bd-opt__cost">'
        '<b>Cost.</b> %s</p></div>%s</div></section>'
        % (k, k, e(t), e(what), e(cost), fn()) for k, t, fn, what, cost in OPTIONS)
    doc = ('<!doctype html>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           if standalone else "")
    return (doc + "<title>Everyone's Numbers Tables</title>\n"
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
            '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
            "<style>%s\n%s\n%s\n%s</style>%s" % (logos, css, rk, board, symbols)
            + body.replace("{{OPTIONS}}", opts))


if __name__ == "__main__":
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        page = build(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(page)
        print("wrote %s  (%.0f KB)" % (path, len(page.encode()) / 1024))
