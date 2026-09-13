"""Shared pieces for the Board tab directions board: logo variables, faces, marks."""
from __future__ import annotations

import base64
import io
import os

from boardtab_data import GAMES, LIVE, STANDINGS
from weektab_common import BY_NAME, ROOT, TEAMS, e

LOGOS = os.path.join(ROOT, "static", "logos")


def _png(path, px, pixel=False):
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    if pixel:
        im.thumbnail((px, px), Image.LANCZOS)
        # Hard alpha, so the scaled-up sprite has crisp pixel edges rather than soft ones.
        a = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)
        im.putalpha(a)
    else:
        im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def team_ids():
    ids = {p["team_id"] for p in STANDINGS}
    for g in GAMES:
        ids |= {g["away"]["id"], g["home"]["id"]}
    return sorted(ids)


def logo_vars():
    """--lg-<id>: the cut drawn for the school's own disc. --lgd-<id>: the cut for a dark
    ground. --px-<id>: an 18px sprite for the arcade direction, scaled up pixelated."""
    out = []
    for i in team_ids():
        t = TEAMS.get(i, {})
        disc = os.path.join(LOGOS, "%s-dark.png" % i) if t.get("cut") == "dark" else os.path.join(LOGOS, "%s.png" % i)
        dark = os.path.join(LOGOS, "%s-dark.png" % i)
        dark = dark if os.path.exists(dark) else os.path.join(LOGOS, "%s.png" % i)
        out.append("--lg-%s:url(%s);--lgd-%s:url(%s);--px-%s:url(%s);"
                   % (i, _png(disc, 96), i, _png(dark, 96), i, _png(dark, 18, pixel=True)))
    return ":root{%s}" % "".join(out)


def disc(team_id, size, cls="bk-disc"):
    t = TEAMS[team_id]
    n = round(size * 0.72)
    return ('<span class="%s" style="width:%dpx;height:%dpx;background:%s"><i style="width:%dpx;height:%dpx;'
            'background-image:var(--lg-%s)"></i></span>' % (cls, size, size, t["bg"], n, n, team_id))


def face(name, size, cls="bk-disc"):
    return disc(BY_NAME[name]["team_id"], size, cls)


def mark(team_id, size, cls="bk-mark", var="lgd"):
    return ('<i class="%s" style="width:%dpx;height:%dpx;background-image:var(--%s-%s)"></i>'
            % (cls, size, size, var, team_id))


def field(team_id):
    """The louder of a school's two colours, as the Week tab paints a winner."""
    t = TEAMS[team_id]

    def sat(h):
        r, g, b = (int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))
        mx, mn = max(r, g, b), min(r, g, b)
        light = (mx + mn) / 2
        return 0 if mx == mn else (mx - mn) / (1 - abs(2 * light - 1))

    return max((t["bg"], t["alt"]), key=sat)


def _lum(h):
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(h[k:k + 2], 16) / 255) for k in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def panel(team_id, ceiling=0.16):
    """A school colour dark enough to carry white lettering. Colorado's field is a pale
    grey and Kennesaw State's a gold; both get pulled toward black until white reads on them."""
    colour = field(team_id) if team_id in TEAMS else "#444444"
    r, g, b = (int(colour[k:k + 2], 16) for k in (1, 3, 5))
    f = 1.0
    while _lum("#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))) > ceiling and f > 0.05:
        f -= 0.04
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def short(school):
    """Scoreboard names: the school, trimmed the way a board would letter it."""
    fixes = {"Georgia Tech": "GA Tech", "Central Michigan": "C Michigan", "New Mexico": "New Mexico",
             "Western Kentucky": "W Kentucky", "Hawai'i": "Hawaii", "Notre Dame": "Notre Dame"}
    return fixes.get(school, school)


__all__ = ["GAMES", "LIVE", "STANDINGS", "BY_NAME", "TEAMS", "e", "logo_vars", "disc", "face", "mark", "field", "short"]
