"""Direction 6: split-flap. The mechanical board from a train station, flipping to the score."""
from __future__ import annotations

from boardtab_data import TOTALS
from boardtab_kit import GAMES, STANDINGS, e, face, mark

NAME = "Split-Flap"
PITCH = ("A mechanical flip board, the kind that clatters when it changes. Every letter and number "
         "is its own flap that flips into place when the tab opens, statuses are colored flaps, "
         "and the live clocks flip again every few seconds.")
BUILT = "Barlow Condensed on hinged tiles, a staggered 3D flip in CSS that starts and ends fully readable."

_delay = [0]


def flaps(text, size="m", n=None, align="left", tone=""):
    chars = list(str(text).upper())
    if n is not None and len(chars) < n:
        pad = [" "] * (n - len(chars))
        chars = pad + chars if align == "right" else chars + pad
    out = []
    for ch in chars:
        _delay[0] += 23
        out.append('<span class="fl-c" style="--d:%dms">%s</span>' % (_delay[0] % 1400, "&nbsp;" if ch == " " else e(ch)))
    return '<span class="fl-row fl-%s%s">%s</span>' % (size, " is-%s" % tone if tone else "", "".join(out))


def standings():
    rows = []
    for s in STANDINGS:
        rows.append('<div class="fl-srow%s"><i class="fl-light" aria-hidden="true"></i>%s%s'
                    '<span class="fl-who">%s<span class="fl-note">%d-%d &middot; max %d</span></span>%s</div>'
                    % (" is-lead" if s["rank"] == 1 else "", flaps(s["rank"], "m"), face(s["name"], 30),
                       flaps(s["name"], "m", 6), s["right"], s["wrong"], s["max"], flaps(s["points"], "l", 3, "right")))
    return "".join(rows)


def status(g):
    if g["state"] == "final":
        return '<span class="fl-status">%s</span>' % flaps("FINAL", "s", tone="white")
    if g["state"] == "live":
        return '<span class="fl-status is-live">%s%s</span>' % (flaps(g["period"], "s", 3, tone="red"), flaps(g["clock"], "s", 4, "right", tone="red"))
    return '<span class="fl-status">%s%s</span>' % (flaps("SAT", "s", 3, tone="amber"), flaps("7:30", "s", 4, "right", tone="amber"))


def pick(p):
    if p["result"] == "hidden":
        return '<span class="fl-pick">%s%s%s</span>' % (face(p["name"], 22), flaps("", "s", 4), flaps("--", "s", 2, tone="grey"))
    tone = {"won": "green", "lost": "red", "ahead": "blue", "behind": "amber", "open": "grey"}[p["result"]]
    return '<span class="fl-pick">%s%s%s</span>' % (face(p["name"], 22), flaps(p["pick"], "s", 4), flaps(p["confidence"], "s", 2, "right", tone=tone))


def game(g):
    lines = []
    for side in ("away", "home"):
        s = g[side]
        dim = g["state"] == "final" and g["leader"] != s["abbr"]
        lines.append('<div class="fl-team%s">%s%s%s</div>'
                     % (" is-dim" if dim else "", mark(s["id"], 26), flaps(s["abbr"], "m", 4),
                        flaps("" if s["score"] is None else s["score"], "m", 2, "right")))
    return ('<article class="fl-game"><div class="fl-game__top"><div class="fl-teams">%s</div>%s</div>'
            '<div class="fl-picks">%s</div></article>' % ("".join(lines), status(g), "".join(pick(p) for p in g["picks"])))


def build():
    _delay[0] = 0
    return ('<div class="fl"><header class="fl-hdr"><span class="fl-brand">Motley Pick&rsquo;em</span><span class="fl-me">%s Grant</span></header>'
            '<div class="fl-board"><div class="fl-top">%s<span class="fl-sub">%d of %d final</span></div>'
            '<div class="fl-cols"><span>Player</span><span>Pts</span></div>%s'
            '<div class="fl-cols fl-cols--games"><span>Game</span><span>Status</span></div>%s</div></div>'
            % (face("Grant", 24), flaps("WEEK 1", "l"), TOTALS["final"], TOTALS["slate"], standings(), "".join(game(g) for g in GAMES)))
