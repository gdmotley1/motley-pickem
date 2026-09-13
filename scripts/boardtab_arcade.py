"""Direction 2: 8-bit arcade. A cartridge-era football game's menus on a CRT."""
from __future__ import annotations

from boardtab_data import TOTALS
from boardtab_kit import GAMES, STANDINGS, e, short

NAME = "8-Bit Arcade"
PITCH = ("A 1989 football cartridge on a curved CRT. Pixel windows, a blinking cursor on the live "
         "games, pixel team sprites, and everyone's lead drawn as a life bar.")
BUILT = "Press Start 2P, scanlines and a screen glow in CSS, logos shrunk to 18px sprites and scaled up with hard pixels."

# A 12 by 8 football, one character per pixel: b brown, l lace, . empty.
BALL = [
    "....bbbb....",
    "..bbbbbbbb..",
    ".bbbllllbbb.",
    "bbblblblbbbb",
    "bbbllllllbbb",
    ".bbbllllbbb.",
    "..bbbbbbbb..",
    "....bbbb....",
]


def sprite(rows, px=4, palette=None):
    palette = palette or {"b": "#a0522d", "l": "#fcfcfc"}
    shadows = []
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in palette:
                shadows.append("%dpx %dpx 0 %s" % ((x + 1) * px, (y + 1) * px, palette[c]))
    return ('<i class="ar-sprite" style="width:%dpx;height:%dpx;margin:0 %dpx %dpx 0;box-shadow:%s"></i>'
            % (px, px, len(rows[0]) * px, len(rows) * px, ",".join(shadows)))


def px_logo(team_id, size=36):
    return '<i class="ar-px" style="width:%dpx;height:%dpx;background-image:var(--px-%s)"></i>' % (size, size, team_id)


def bar(points, maximum, cells=12):
    """Points banked against the most this player can still finish on, as a life bar."""
    lit = round(cells * points / maximum) if maximum else 0
    return '<span class="ar-bar">%s</span>' % "".join('<i class="%s"></i>' % ("on" if i < lit else "") for i in range(cells))


def standings():
    out = []
    for s in STANDINGS:
        out.append('<div class="ar-p%s"><span class="ar-p__n">%dP</span>%s<span class="ar-p__name">%s</span>'
                   '<span class="ar-p__pts">%d</span>%s<span class="ar-p__max">MAX %d</span></div>'
                   % (" is-lead" if s["rank"] == 1 else "", s["rank"], px_logo(s["team_id"], 32), e(s["name"].upper()),
                      s["points"], bar(s["points"], s["max"]), s["max"]))
    return "".join(out)


def game(g):
    head = {"final": '<span class="ar-tag is-final">FINAL</span>',
            "live": '<span class="ar-tag is-live">&#9654; %s %s</span>' % (e(g["period"].upper()), e(g["clock"])),
            "soon": '<span class="ar-tag is-soon">SAT 7:30</span>'}[g["state"]]
    lines = []
    for side in ("away", "home"):
        s = g[side]
        lead = g["leader"] == s["abbr"]
        lines.append('<div class="ar-t%s">%s<span class="ar-t__name">%s</span><span class="ar-t__pts">%s</span></div>'
                     % (" is-lead" if lead and g["state"] != "soon" else "", px_logo(s["id"], 36),
                        e(short(s["school"]).upper()), "" if s["score"] is None else s["score"]))
    picks = []
    for p in g["picks"]:
        if p["result"] == "hidden":
            picks.append('<span class="ar-k is-hidden"><b>%s</b><span>???</span></span>' % e(p["name"][:3].upper()))
            continue
        num = ("+%d" % p["confidence"]) if p["result"] == "won" else str(p["confidence"])
        picks.append('<span class="ar-k is-%s"><b>%s</b><span>%s %s</span></span>'
                     % (p["result"], e(p["name"][:3].upper()), e(p["pick"]), num))
    return ('<section class="ar-win ar-game is-%s"><div class="ar-game__hd">%s<span class="ar-line">%s</span></div>%s'
            '<div class="ar-picks">%s</div></section>'
            % (g["state"], head, e(g["line"]), "".join(lines), "".join(picks)))


def build():
    return (
        '<div class="ar"><div class="ar-crt">'
        '<header class="ar-hdr"><span>MOTLEY</span><span class="ar-hdr__me">GRANT</span></header>'
        '<div class="ar-title">%s<h2><span>PICK&rsquo;EM</span><span>BOWL</span></h2><p class="ar-blink">&#9733; WEEK 1 &middot; LIVE &#9733;</p></div>'
        '<section class="ar-win"><h3 class="ar-h">STANDINGS <span>%d/%d FINAL</span></h3>%s</section>'
        '%s'
        '<p class="ar-start"><span class="ar-blink">PRESS START</span></p>'
        '<p class="ar-copy">&copy;2026 MOTLEY SPORTS</p>'
        '</div></div>'
        % (sprite(BALL), TOTALS["final"], TOTALS["slate"], standings(), "".join(game(g) for g in GAMES)))
