"""Round 2 of the Week tab board: Grant picked 2, Winner's colors. The top stays; these are
the sections that could go under it, each drawn in that style on the real Week 1.

    node scripts/weektab_model.mjs && python scripts/weektab_content.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weektab_common import MODEL, PLAYERS, ROOT, e, face, header, join_names, logo_css, mark  # noqa: E402
import weektab_opt2 as w  # noqa: E402

C = MODEL["content"]
SEAT_ON_DARK = {"Grant": "#ff8f4d", "James": "#4fd08c", "Parker": "#6fb0ff", "Nicole": "#ff78a8"}
OUT = os.path.join(ROOT, "outputs", "weektab-content.html")


def sec(title, inner, help_=""):
    return ('<section class="wc-sec"><h3 class="wc-title">%s</h3>%s%s</section>'
            % (title, '<p class="wc-help">%s</p>' % help_ if help_ else "", inner))


def ladder(rows):
    return '<div class="wc-table">%s</div>' % "".join(
        '<div class="wc-lrow%s"><span class="wc-rank">%d</span>%s<span class="wc-who"><b>%s</b><span>%s</span></span>'
        '<strong>%s</strong></div>' % (" is-lead" if i == 0 else "", i + 1, face(r["name"], 34), e(r["name"]), r["note"], r["value"])
        for i, r in enumerate(rows))


def pick_chip(p):
    return ('<span class="cx-pick%s">%s<b>%s</b><em>%d</em></span>'
            % ("" if p["won"] else " is-lost", mark(p["pick_id"], 22), e(p["pick"]), p["confidence"]))


# --------------------------------------------------------------------------- sections

def race():
    r = C["race"]
    steps = r["steps"]
    W, H, L, R, T, B = 366, 206, 40, 92, 16, 30
    n = len(steps)
    x = lambda i: L + (W - L - R) * (i - 1) / (n - 1)
    row = (H - T - B) / 3
    finals = sorted(PLAYERS, key=lambda p: -p["points"])
    order = {p["name"]: i for i, p in enumerate(finals)}

    def place(s, name):
        """Standings position after this game, ties sharing a row, nudged apart so both show."""
        pts = s["points"]
        rank = 1 + sum(1 for v in pts.values() if v > pts[name])
        tied = sorted((k for k in pts if pts[k] == pts[name]), key=lambda k: order[k])
        nudge = (tied.index(name) - (len(tied) - 1) / 2) * 5
        return T + (rank - 1) * row + nudge

    grid = "".join('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f"/><text x="%d" y="%.1f">%s</text>'
                   % (L, W - R, T + i * row, T + i * row, L - 8, T + i * row + 5, lab)
                   for i, lab in enumerate(("1st", "2nd", "3rd", "4th")))
    lock = r["tookLeadAt"]
    marker = '<line class="cx-lock" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % (x(lock), x(lock), T - 10, H - B + 8)
    lines, labels = [], []
    for p in reversed(finals):
        pts = [(x(s["n"]), place(s, p["name"])) for s in steps]
        lead = p["name"] in r["leader"]
        c = SEAT_ON_DARK[p["name"]]
        lines.append('<polyline points="%s" stroke="%s" stroke-width="%s"/><circle cx="%.1f" cy="%.1f" r="%s" fill="%s"/>'
                     % (" ".join("%.1f,%.1f" % q for q in pts), c, "4.5" if lead else "2.6", pts[-1][0], pts[-1][1],
                        "6" if lead else "4", c))
        labels.append('<text class="cx-end" x="%d" y="%.1f" fill="%s">%s %d</text>'
                      % (W - R + 12, T + order[p["name"]] * row + 5, c, e(p["name"]), p["points"]))
    ticks = ('<text class="cx-x" x="%d" y="%d">Game 1</text><text class="cx-x" x="%d" y="%d" text-anchor="end">20</text>'
             % (L - 4, H - 6, W - R + 4, H - 6))
    svg = ('<svg class="cx-race" viewBox="0 0 %d %d" role="img" aria-label="Standings position after each game">'
           '<g class="cx-grid">%s</g>%s<g fill="none" stroke-linejoin="round" stroke-linecap="round">%s</g>%s%s</svg>'
           % (W, H, grid, marker, "".join(lines), "".join(labels), ticks))
    led = sorted(r["ledAfter"].items(), key=lambda kv: -kv[1])
    facts = ('<div class="cx-facts"><p><strong>%d</strong><span>times the lead changed hands</span></p>'
             '<p><strong>%d</strong><span>%s took the lead for good, at %s</span></p>'
             '<p><strong>%d</strong><span>games %s led, the most of anyone</span></p></div>'
             % (r["changes"], lock, e(r["leader"][0]), e(steps[lock - 1]["label"]), led[0][1], e(led[0][0])))
    return sec("How it unfolded", svg + facts, "Where everyone stood after each game, in kickoff order.")


def misses():
    rows = [{"name": m["name"], "value": m["miss"]["confidence"],
             "note": "on %s, lost to %s" % (e(m["miss"]["pick"]), e(m["miss"]["winner"]))} for m in C["misses"] if m["miss"]]
    return sec("Biggest miss", ladder(rows), "The most points each of you had on a pick that lost.")


def calls():
    rows = [{"name": c["name"], "value": c["call"]["confidence"],
             "note": "on %s, %s missed it" % (e(c["call"]["pick"]), e(join_names(c["missedBy"])))} for c in C["calls"] if c["call"]]
    return sec("Best call", ladder(rows), "The most points on a right pick somebody else missed.")


def you():
    y_ = C["you"]
    me = next(p for p in PLAYERS if p["name"] == y_["name"])

    def item(x):
        mine = ("your %d" % x["me"]["confidence"]) if x["me"]["won"] else "you missed"
        theirs = ("%s %d" % (y_["rival"], x["them"]["confidence"])) if x["them"]["won"] else "%s missed" % y_["rival"]
        return ('<div class="cx-h2h">%s<span class="wc-who"><b>%s</b><span>%s, %s</span></span><strong>+%d</strong></div>'
                % (mark(x["pick_id"], 30), e(x["label"]), mine, e(theirs), abs(x["net"])))

    gained = "".join(item(x) for x in y_["gained"][:2])
    lost = "".join(item(x) for x in y_["lost"][:2])
    head = ('<div class="cx-you">%s<div><p class="cx-you__k">You finished</p><p class="cx-you__v">1st of %d</p>'
            '<p class="cx-you__s">%d-%d &middot; %d points &middot; %d ahead of %s</p></div></div>'
            % (face(me["name"], 56), y_["of"], me["correct"], me["wrong"], me["points"], y_["net"], e(y_["rival"])))
    return sec("Your week", head + '<p class="cx-sub">Where you pulled ahead of %s</p>%s'
               '<p class="cx-sub">Where %s got points back</p>%s' % (e(y_["rival"]), gained, e(y_["rival"]), lost),
               "Only you see this one. It compares you with whoever finished next to you.")


def agreed():
    a = C["agreed"]
    held = [g for g in a if g["won"]]
    burned = [g for g in a if not g["won"]]
    rows = "".join('<div class="cx-agree">%s<span class="wc-who"><b>%s lost</b><span>%d points between you, all gone</span></span></div>'
                   % (mark(g["pick_id"], 36), e(g["pick"]), g["total"]) for g in burned)
    marks = "".join('<span class="cx-held">%s<b>%s</b></span>' % (mark(g["pick_id"], 30), e(g["pick"])) for g in held)
    top = ('<div class="cx-facts cx-facts--row"><p><strong>%d</strong><span>games all four of you picked the same team</span></p></div>'
           % len(a))
    return sec("When you all agreed", top + '<p class="cx-sub">%d held</p><div class="cx-heldrow">%s</div>'
               '<p class="cx-sub">%d didn&rsquo;t</p>%s' % (len(held), marks, len(burned), rows))


def alone():
    out = []
    for a in C["alone"]:
        chips = "".join(pick_chip(p) for p in a["picks"])
        note = ("%d right" % a["right"]) if a["picks"] else "Went with somebody every time"
        out.append('<div class="cx-alone"><div class="cx-alone__hd">%s<span class="wc-who"><b>%s</b><span>%s</span></span>'
                   '<strong>%d</strong></div>%s</div>'
                   % (face(a["name"], 34), e(a["name"]), note, len(a["picks"]),
                      '<div class="cx-chips">%s</div>' % chips if chips else ""))
    return sec("Went it alone", "".join(out), "Picks nobody else in the family made, and how they went.")


def ranked():
    rows = [{"name": p["name"], "value": p["left"], "note": "got %d of a possible %d" % (p["points"], p["ceiling"])} for p in MODEL["left"]]
    first = MODEL["left"][0]
    right = next(p for p in PLAYERS if p["name"] == first["name"])["correct"]
    help_ = ("How many more points you&rsquo;d have had with your biggest numbers on the games you got right. "
             "%s got %d right: ranked perfectly those were worth %d, and %s got %d."
             % (e(first["name"]), right, first["ceiling"], e(first["name"]), first["points"]))
    return sec("Points left on the table", ladder(rows), help_)


OPTIONS = [
    (1, "Decided it", w.decided, "The results that would have flipped the week. On the last board."),
    (2, "Upsets", w.upsets, "Underdogs that won, and who had them. On the last board."),
    (3, "How it unfolded", race, "A race chart: who led as the games went final, and when the winner took over."),
    (4, "Biggest miss", misses, "Everyone&rsquo;s most expensive wrong pick. Plain as it gets."),
    (5, "Best call", calls, "Everyone&rsquo;s best right pick that somebody else missed."),
    (6, "Your week", you, "Just yours: where you gained and lost against whoever finished next to you."),
    (7, "When you all agreed", agreed, "The games all four of you picked the same way, and the ones that burned everyone."),
    (8, "Went it alone", alone, "Picks nobody else made. A little ribbing, all counts."),
    (9, "By the numbers", w.numbers, "Favorites, upsets, games everyone got, games nobody got. On the last board."),
    (10, "Points left on the table", ranked, "The one you asked about, explained. My vote is to cut it."),
]


def stays():
    body = w.hero() + w.standings()
    return '<div class="wt-phone wc" style="--wc-field:%s;--wc-ink:%s">%s%s</div>' % (w.FIELD, w.INK, header("wc-hdr"), body)


def section_card(n, name, fn, what):
    return ('<article class="bd-opt"><header class="bd-opt__hd"><span class="bd-num">%d</span><div><h3>%s</h3><p>%s</p></div></header>'
            '<div class="wt-phone wc bd-sec" style="--wc-field:%s;--wc-ink:%s">%s</div></article>'
            % (n, name, what, w.FIELD, w.INK, fn()))


def read(name):
    return open(os.path.join(ROOT, "scripts", name), encoding="utf-8").read()


def page(standalone):
    fonts = ("https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,400..900;1,62..125,400..900"
             "&family=Inter:wght@400;500;600;700;800&display=swap")
    cards = "".join(section_card(*o) for o in OPTIONS)
    body = """
<header class="bd-top"><div class="bd-wrap">
  <p class="bd-kick">Motley Pick&rsquo;em &middot; Week tab &middot; Round 2</p>
  <h1>What goes under the winner</h1>
  <p class="bd-lede">You picked <b>2, Winner&rsquo;s colors</b>. The top stays the way you saw it: the winner in their
    school&rsquo;s colors, then the final standings. Everything under that is up to you. Every section below is drawn
    in that style on the real Week 1.</p>
  <p class="bd-how">Reply with the numbers you want, in the order you want them. For example: <b>3, 1, 4, 2</b>.</p>
</div></header>
<main class="bd-wrap">
  <section class="bd-part bd-part--stays">
    <div class="bd-stays__copy"><p class="bd-range">Stays</p><h2>The top of the tab</h2>
      <p>Paints itself in the winner&rsquo;s school colors every week: Arkansas red when Grant wins, Tulane green for James,
        Kennesaw gold for Parker, Georgia red for Nicole.</p>
      <p class="bd-take"><b>My pick for under it:</b> 3, 1, 4, 2. How the week went, the what-ifs, everyone&rsquo;s worst
        miss, then the upsets. It reads like a game recap: story first, details after. I&rsquo;d cut 10.</p></div>
    %s
  </section>
  <section class="bd-part">
    <header class="bd-part__hd"><p class="bd-range">Pick any, in order: 1 to 10</p><h2>Sections</h2></header>
    <div class="bd-grid">%s</div>
  </section>
</main>
""" % (stays(), cards)
    doc = '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n' if standalone else ""
    return (doc + '<title>Week Tab Sections</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link href="%s" rel="stylesheet">\n<style>%s\n%s\n%s\n%s\n%s</style>\n%s'
            % (fonts, logo_css(), read("weektab_base.css"), read("weektab_opt2.css"), read("weektab_content.css"),
               read("weektab_content_board.css"), body))


if __name__ == "__main__":
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        html = page(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(html)
        print("wrote %s (%.0f KB)" % (path, len(html.encode()) / 1024))
