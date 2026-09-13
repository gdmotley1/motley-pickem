"""Shared pieces for the Week tab options board: the model, team marks, faces, the tab bar.

Every phone on the board reads MODEL, which scripts/weektab_model.mjs builds by running
the app's own src/lib/weekRecap.js over the real Week 1. Nothing here computes a number.
"""
from __future__ import annotations

import base64
import html
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = json.load(open(os.path.join(ROOT, "outputs", "weektab_model.json"), encoding="utf-8"))
TEAMS = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}
e = html.escape

PLAYERS = MODEL["players"]
BY_NAME = {p["name"]: p for p in PLAYERS}
ME = MODEL["me"]


def logo_uri(team_id, px=96):
    """A school's mark, the cut chosen for its own disc colour, as a small PNG data URI."""
    from PIL import Image

    t = TEAMS.get(team_id, {})
    name = "%s-dark" % team_id if t.get("cut") == "dark" else team_id
    im = Image.open(os.path.join(ROOT, "static", "logos", "%s.png" % name)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def plain_uri(team_id, px=160):
    """The normal (light-background) cut, used where a mark is recoloured by a filter."""
    from PIL import Image

    im = Image.open(os.path.join(ROOT, "static", "logos", "%s.png" % team_id)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo_css():
    """One custom property per school, so each mark is embedded once for the whole board."""
    live = json.load(open(os.path.join(ROOT, "outputs", "harness", "week_live.json"), encoding="utf-8"))
    ids = sorted(set(MODEL["teams"]) | {g[k] for g in live["slate"] for k in ("home_id", "away_id")})
    return ":root{%s}" % "".join("--lg-%s:url(%s);" % (i, logo_uri(i)) for i in ids)


def team(team_id):
    return TEAMS[team_id]


def disc(team_id, size, cls="wt-disc"):
    """The app's avatar: the school's disc colour with its mark at 72%."""
    t = TEAMS[team_id]
    n = round(size * 0.72)
    return ('<span class="%s" style="width:%dpx;height:%dpx;background:%s">'
            '<i style="width:%dpx;height:%dpx;background-image:var(--lg-%s)"></i></span>'
            % (cls, size, size, t["bg"], n, n, team_id))


def face(name, size, cls="wt-disc"):
    return disc(BY_NAME[name]["team_id"], size, cls)


def mark(team_id, size, cls="wt-mark"):
    """A school's mark with no disc, for score lines."""
    return ('<i class="%s" style="width:%dpx;height:%dpx;background-image:var(--lg-%s)"></i>'
            % (cls, size, size, team_id))


def join_names(names):
    names = list(names)
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def line(x):
    return ("%g" % x) if x is not None else ""


# ----------------------------------------------------------------- the app chrome

ICONS = {
    "Picks": '<path d="M5 7h14M5 12h14M5 17h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    "Board": ('<rect x="3" y="4" width="18" height="16" rx="2.5" stroke="currentColor" stroke-width="2"/>'
              '<path d="M3 9.5h18M9 9.5V20" stroke="currentColor" stroke-width="2"/>'),
    "Week": ('<path d="M7 4h10v5a5 5 0 0 1-10 0V4Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'
             '<path d="M7 6H4.5v1A3 3 0 0 0 7 10M17 6h2.5v1a3 3 0 0 1-2.5 3M9.5 20h5M12 14v6" '
             'stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'),
    "Season": ('<path d="M4 4v15a1 1 0 0 0 1 1h15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
               '<path d="m8 15 3.5-4 3 2.5L20 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
               'stroke-linejoin="round"/>'),
    "Setup": ('<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>'
              '<path d="M12 2.8v2.6M12 18.6v2.6M2.8 12h2.6M18.6 12h2.6M5.5 5.5l1.8 1.8M16.7 16.7l1.8 1.8'
              'M5.5 18.5l1.8-1.8M16.7 7.3l1.8-1.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'),
}


def header(cls):
    """The app header as it reads while Week 1 is being looked back at from Week 2."""
    return ('<header class="wt-hdr %s"><div><span class="wt-hdr__title">Motley Pick&rsquo;em</span>'
            '<span class="wt-hdr__week">Week 2 &middot; 20 games</span></div>'
            '<span class="wt-hdr__me">%s<span>Grant</span></span></header>' % (cls, face(ME, 24)))


def tabbar(cls):
    tabs = "".join(
        '<span class="wt-tab%s"><svg viewBox="0 0 24 24" width="21" height="21" fill="none" aria-hidden="true">%s</svg>'
        '<span>%s</span></span>' % (" is-on" if k == "Week" else "", v, k)
        for k, v in ICONS.items())
    return '<nav class="wt-tabs %s" aria-label="Tabs">%s</nav>' % (cls, tabs)


def phone(cls, inner):
    return '<div class="wt-phone %s">%s</div>' % (cls, inner)
