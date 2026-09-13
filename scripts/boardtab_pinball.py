"""Direction 4: pinball. Orange plasma dot-matrix displays under cartoon backglass art."""
from __future__ import annotations

from boardtab_data import TOTALS
from boardtab_kit import GAMES, STANDINGS, e, face
from weektab_bulbs import bulbs

NAME = "Pinball"
PITCH = ("A 1990s pinball machine. The standings and every game glow on orange dot-matrix displays "
         "under loud cartoon backglass art, and each pick is a playfield lamp that lights green, "
         "red, or blinks while its game is still on.")
BUILT = "Bangers for the cartoon lettering, dot-matrix type drawn as real lamps in SVG, a starburst and chrome rails in CSS."


def dmd(inner, cls=""):
    return '<div class="pb-dmd %s"><div class="pb-dmd__glass">%s</div></div>' % (cls, inner)


def standings():
    rows = []
    lead = STANDINGS[0]["points"]
    for s in STANDINGS:
        rows.append('<div class="pb-srow%s">%s%s%s</div>'
                    % (" is-lead" if s["rank"] == 1 else "", bulbs(str(s["rank"]), 24, cols=1),
                       bulbs(s["name"].upper(), 24), bulbs(str(s["points"]), 24, cols=3)))
    headline = bulbs("%s LEADS BY %d" % (STANDINGS[0]["name"].upper(), lead - STANDINGS[1]["points"]), 20)
    return dmd('<div class="pb-head">%s</div>%s' % (headline, "".join(rows)), "pb-dmd--big")


def lamp(p):
    if p["result"] == "hidden":
        return ('<div class="pb-lamp is-hidden"><span class="pb-bulb">?</span><span class="pb-lamp__t"><b>%s</b>'
                '<span>Locked</span></span></div>' % e(p["name"]))
    num = ("+%d" % p["confidence"]) if p["result"] == "won" else str(p["confidence"])
    return ('<div class="pb-lamp is-%s">%s<span class="pb-lamp__t"><b>%s</b><span>%s %s</span></span></div>'
            % (p["result"], '<span class="pb-bulb">%s</span>' % face(p["name"], 26), e(p["name"]), e(p["pick"]), num))


def game(g):
    a, h = g["away"], g["home"]
    if g["state"] == "soon":
        line1 = bulbs("%s AT %s" % (a["abbr"], h["abbr"]), 22)
        line2 = bulbs("SAT 7:30", 22)
    else:
        line1 = '<span class="pb-score">%s%s</span><span class="pb-score">%s%s</span>' % (
            bulbs(a["abbr"], 22), bulbs(str(a["score"]), 22, cols=2), bulbs(h["abbr"], 22), bulbs(str(h["score"]), 22, cols=2))
        line2 = bulbs("FINAL", 22) if g["state"] == "final" else bulbs("%s %s" % (g["period"].upper(), g["clock"]), 22)
    tag = {"final": "Final", "live": "Live!", "soon": "Up next"}[g["state"]]
    return ('<article class="pb-game is-%s"><span class="pb-tag">%s</span>%s<div class="pb-lamps">%s</div></article>'
            % (g["state"], tag, dmd('<div class="pb-l1">%s</div><div class="pb-l2">%s</div>' % (line1, line2)),
               "".join(lamp(p) for p in g["picks"])))


def build():
    return ('<div class="pb"><div class="pb-rails">'
            '<header class="pb-hdr"><span class="pb-hdr__credit">Credits 4</span><span class="pb-hdr__me">%s Grant</span></header>'
            '<div class="pb-glass"><div class="pb-burst" aria-hidden="true"></div>'
            '<h2 class="pb-title"><span>Motley</span><span>Pick&rsquo;em</span></h2>'
            '<p class="pb-ribbon">Week 1 &middot; %d of %d final</p></div>'
            '%s<div class="pb-games">%s</div>'
            '<p class="pb-foot">Match &middot; Tilt &middot; Replay</p>'
            '</div></div>' % (face("Grant", 24), TOTALS["final"], TOTALS["slate"], standings(), "".join(game(g) for g in GAMES)))
