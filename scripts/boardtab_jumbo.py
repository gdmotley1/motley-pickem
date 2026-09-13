"""Direction 1: the Jumbotron. A modern stadium LED video board."""
from __future__ import annotations

from boardtab_data import TOTALS, ticker
from boardtab_kit import GAMES, STANDINGS, TEAMS, e, face, field, mark, panel, short

NAME = "Jumbotron"
PITCH = ("The big board at a night game. Everything lives on one LED wall: a glowing leaderboard, "
         "every game as a video-board tile in the schools' colors, and a crawl of the other scores "
         "running along the bottom.")
BUILT = "Big Shoulders Display for the lettering, a real LED dot mask over every big number, and a scrolling crawl."


def led(text, cls=""):
    return '<span class="jb-led %s"><span>%s</span></span>' % (cls, e(str(text)))


def status(g):
    if g["state"] == "final":
        return '<span class="jb-pill is-final">Final</span>'
    if g["state"] == "live":
        return '<span class="jb-pill is-live"><i></i>%s &middot; %s</span>' % (e(g["period"]), e(g["clock"]))
    return '<span class="jb-pill is-soon">%s %s</span>' % (e(g["period"]), e(g["clock"]))


def pick(p):
    if p["result"] == "hidden":
        return '<span class="jb-pick is-hidden">%s<span class="jb-pick__t">Locked</span></span>' % face(p["name"], 26)
    num = ("+%d" % p["confidence"]) if p["result"] == "won" else str(p["confidence"])
    return ('<span class="jb-pick is-%s">%s<span class="jb-pick__t">%s</span><b>%s</b></span>'
            % (p["result"], face(p["name"], 26), e(p["pick"]), num))


def team_row(g, side):
    s = g[side]
    colour = panel(s["id"], 0.2)
    lead = g["leader"] == s["abbr"]
    lose = g["state"] == "final" and not lead
    score = "" if s["score"] is None else led(s["score"], "jb-score")
    return ('<div class="jb-team%s%s" style="--jb-team:%s">%s<span class="jb-school">%s</span>'
            '<span class="jb-arrow" aria-hidden="true"></span>%s</div>'
            % (" is-lead" if lead and g["state"] != "soon" else "", " is-loser" if lose else "", colour,
               mark(s["id"], 38), e(short(s["school"])), score))


def game(g):
    return ('<article class="jb-game is-%s"><header class="jb-game__hd">%s<span class="jb-line">%s</span></header>'
            '%s%s<div class="jb-picks">%s</div></article>'
            % (g["state"], status(g), e(g["line"]), team_row(g, "away"), team_row(g, "home"),
               "".join(pick(p) for p in g["picks"])))


def leaderboard():
    rows = []
    for s in STANDINGS:
        rows.append('<div class="jb-row%s" style="--jb-team:%s"><span class="jb-rank">%d</span>%s'
                    '<span class="jb-who"><b>%s</b><span>%d-%d &middot; %d in play</span></span>%s</div>'
                    % (" is-lead" if s["rank"] == 1 else "", panel(s["team_id"], 0.2), s["rank"], face(s["name"], 40),
                       e(s["name"]), s["right"], s["wrong"], s["in_play"], led(s["points"], "jb-pts")))
    return "".join(rows)


def build():
    crawl = " &nbsp;&#9670;&nbsp; ".join(e(t) for t in ticker())
    return (
        '<div class="jb">'
        '<header class="jb-hdr"><span class="jb-brand">Motley Pick&rsquo;em</span><span class="jb-me">%s Grant</span></header>'
        '<div class="jb-wall">'
        '<div class="jb-strip"><span>Week 1</span><span class="jb-onair"><i></i>Live</span><span>%d/%d Final</span></div>'
        '<section class="jb-panel"><h2 class="jb-title"><span>Leaderboard</span></h2>%s</section>'
        '<section class="jb-games">%s</section>'
        '</div>'
        '<div class="jb-crawl"><span class="jb-crawl__k">Final</span><div class="jb-crawl__win"><div class="jb-crawl__run">'
        '<span>%s</span><span aria-hidden="true">%s</span></div></div></div>'
        '</div>'
        % (face("Grant", 24), TOTALS["final"], TOTALS["slate"], leaderboard(), "".join(game(g) for g in GAMES), crawl, crawl))
