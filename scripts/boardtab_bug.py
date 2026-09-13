"""Direction 3: the TV score bug. A full broadcast graphics package."""
from __future__ import annotations

from boardtab_data import TOTALS, ticker
from boardtab_kit import GAMES, STANDINGS, e, face, mark, panel

NAME = "TV Score Bug"
PITCH = ("Saturday primetime. Every game is a real broadcast score bug, team slabs, a clock box and a "
         "stat strip carrying all four picks, under a lower-third leaderboard. A light sweep crosses "
         "the live ones and the other scores roll along a ticker.")
BUILT = "Archivo at its condensed width, glass highlights and a light sweep in CSS, and a ticker crawl."


def leaderboard():
    rows = []
    for s in STANDINGS:
        rows.append('<div class="tv-row%s"><span class="tv-rank">%d</span><span class="tv-slab" style="--tv-team:%s">%s</span>'
                    '<span class="tv-who"><b>%s</b><span>%d-%d</span></span>'
                    '<span class="tv-max">%d <small>max</small></span><span class="tv-pts">%d</span></div>'
                    % (" is-lead" if s["rank"] == 1 else "", s["rank"], panel(s["team_id"], 0.22), face(s["name"], 30),
                       e(s["name"]), s["right"], s["wrong"], s["max"], s["points"]))
    return ('<section class="tv-lower"><header class="tv-lower__hd"><span class="tv-brand">Pick&rsquo;em</span>'
            '<span class="tv-lower__t">Week 1 leaderboard</span><span class="tv-live"><i></i>Live</span></header>%s'
            '<footer class="tv-lower__ft">%d of %d final &middot; %d live</footer></section>'
            % ("".join(rows), TOTALS["final"], TOTALS["slate"], TOTALS["live"]))


def slab(g, side):
    s = g[side]
    lead = g["leader"] == s["abbr"] and g["state"] != "soon"
    lose = g["state"] == "final" and not lead
    score = "" if s["score"] is None else str(s["score"])
    return ('<div class="tv-side%s%s" style="--tv-team:%s">%s<b>%s</b><strong>%s</strong>%s</div>'
            % (" is-lead" if lead else "", " is-loser" if lose else "", panel(s["id"], 0.22), mark(s["id"], 30), e(s["abbr"]),
               score, '<i class="tv-poss" aria-hidden="true"></i>' if lead else ""))


def clock(g):
    if g["state"] == "final":
        return '<div class="tv-clock is-final"><b>Final</b></div>'
    if g["state"] == "live":
        return '<div class="tv-clock is-live"><b>%s</b><span>%s</span></div>' % (e(g["period"]), e(g["clock"]))
    return '<div class="tv-clock is-soon"><b>Sat</b><span>7:30</span></div>'


def strip(g):
    cells = []
    for p in g["picks"]:
        if p["result"] == "hidden":
            cells.append('<span class="tv-cell is-hidden">%s<em>&mdash;</em></span>' % face(p["name"], 22))
            continue
        num = ("+%d" % p["confidence"]) if p["result"] == "won" else str(p["confidence"])
        cells.append('<span class="tv-cell is-%s">%s<em>%s</em><b>%s</b></span>' % (p["result"], face(p["name"], 22), e(p["pick"]), num))
    return '<div class="tv-strip">%s</div>' % "".join(cells)


def bug(g):
    return ('<article class="tv-bug is-%s"><div class="tv-bug__main">%s%s%s</div>%s<p class="tv-note">%s</p></article>'
            % (g["state"], slab(g, "away"), slab(g, "home"), clock(g), strip(g), e(g["line"])))


def build():
    crawl = "".join('<span><b>&#9656;</b> %s</span>' % e(t) for t in ticker())
    return ('<div class="tv"><header class="tv-hdr"><span class="tv-hdr__brand">Motley Pick&rsquo;em</span>'
            '<span class="tv-hdr__me">%s Grant</span></header>%s<div class="tv-bugs">%s</div>'
            '<div class="tv-ticker"><span class="tv-ticker__k">Around<br>the slate</span><div class="tv-ticker__win">'
            '<div class="tv-ticker__run">%s%s</div></div></div></div>'
            % (face("Grant", 24), leaderboard(), "".join(bug(g) for g in GAMES), crawl, crawl))
