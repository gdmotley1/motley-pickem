"""Direction 5: the bulb board. A 1960s stadium scoreboard: painted steel and amber bulbs."""
from __future__ import annotations

from boardtab_data import TOTALS
from boardtab_kit import GAMES, STANDINGS, e, face, mark
from weektab_bulbs import bulbs
from weektab_common import header, tabbar

NAME = "Bulb Board"
PITCH = ("The old scoreboard at the end of the stadium. Painted steel, every number lit in amber "
         "bulbs in fixed digit modules, a lamp by the leader, and the games laid out like the "
         "out-of-town board, with the live clock in bulbs.")
BUILT = "Bulbs drawn as real 5 by 7 lamps in SVG with a glow, Archivo's condensed cut for the paint."


def well(value, height, cols):
    return '<span class="sb-well">%s</span>' % bulbs(value, height, cols=cols)


def board():
    lead = STANDINGS[0]
    rows = "".join(
        '<div class="sb-row%s"><span class="sb-lamp" aria-hidden="true"></span>%s<span class="sb-name">%s%s</span>%s%s%s</div>'
        % (" is-lead" if s["rank"] == 1 else "", face(s["name"], 28), e(s["name"]), '<em>You</em>' if s["me"] else "",
           well(s["right"], 24, 2), well(s["wrong"], 24, 2), well(s["points"], 24, 3))
        for s in STANDINGS)
    msg = bulbs(lead["name"], 50) + bulbs("LEADS BY %d" % (lead["points"] - STANDINGS[1]["points"]), 26)
    return ('<section class="sb-board"><div class="sb-crown"><span>Week 1</span><span class="sb-final is-live"><i></i>Live</span></div>'
            '<div class="sb-msg">%s</div><div class="sb-score"><div class="sb-score__hd"><span></span><span>W</span><span>L</span>'
            '<span>Pts</span></div>%s</div></section>' % (msg, rows))


def chip(p):
    if p["result"] == "hidden":
        return '<span class="sb-chip is-hidden">%s<b>Locked</b></span>' % face(p["name"], 22)
    num = ("+%d" % p["confidence"]) if p["result"] == "won" else str(p["confidence"])
    cls = {"won": "", "lost": " is-lost", "ahead": " is-ahead", "behind": " is-behind", "open": ""}[p["result"]]
    return '<span class="sb-chip%s">%s<em>%s</em><b>%s</b></span>' % (cls, face(p["name"], 22), e(p["pick"]), num)


def game(g):
    teams = []
    for side in ("away", "home"):
        s = g[side]
        lead = g["leader"] == s["abbr"] and g["state"] != "soon"
        score = well(s["score"], 22, 2) if s["score"] is not None else well("", 22, 2)
        teams.append('<span class="sb-team%s">%s<b>%s</b>%s</span>'
                     % ("" if lead or g["state"] == "soon" else " is-loser", mark(s["id"], 26), e(s["abbr"]), score))
    if g["state"] == "final":
        clock = '<div class="sb-clock"><span class="sb-final"><i></i>Final</span></div>'
    elif g["state"] == "live":
        clock = ('<div class="sb-clock"><span class="sb-final is-live"><i></i>Live</span>%s</div>'
                 % well("%s %s" % (g["period"].upper(), g["clock"]), 20, None))
    else:
        clock = '<div class="sb-clock"><span>Kickoff Sat 7:30 PM</span></div>'
    return ('<div class="sb-game"><div class="sb-line">%s</div>%s<div class="sb-stake"><span class="sb-chips">%s</span></div></div>'
            % ("".join(teams), clock, "".join(chip(p) for p in g["picks"])))


def build():
    return ('<div class="sb">%s<div class="sb-page">%s<section class="sb-panel"><h3 class="sb-title">Around the slate</h3>'
            '<p class="sb-help">%d of %d final &middot; %d on right now</p>%s</section></div></div>'
            % (header("sb-hdr"), board(), TOTALS["final"], TOTALS["slate"], TOTALS["live"], "".join(game(g) for g in GAMES)))
