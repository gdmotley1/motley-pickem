"""Shared data and pieces for the Picks tab directions board.

Everything is Grant's real Week 1 card: the slate from outputs/harness/week_live.json, his
real winners and confidence values, and the TV network, AP rank and neutral-site flag for
each game from the saved ESPN week in tests/fixtures/slate_week01.json. Nothing is invented
except the moment each phone is caught at:

- Winners: midweek, 12 of 20 picked. The first six games in kickoff order are drawn; four
  carry Grant's real pick and two are still open.
- Points: all 20 picked, ranked by Grant's real values, with Notre Dame lifted.
- Locked in: the same card, saved.
"""
from __future__ import annotations

import base64
import io
import json
import os
from datetime import datetime, timedelta
from html import escape as e

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = json.load(open(os.path.join(ROOT, "outputs", "harness", "week_live.json"), encoding="utf-8"))
ESPN = {str(g["espn_id"]): g for g in json.load(open(os.path.join(ROOT, "tests", "fixtures", "slate_week01.json"), encoding="utf-8"))["games"]}
TEAMS = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}
LOGOS = os.path.join(ROOT, "static", "logos")

ME = "Grant"
ME_TEAM = next(s["team_id"] for s in LIVE["seats"] if s["name"] == ME)
OPEN_IN_WINNERS = {"TOL@MSU", "ECU@ALA"}   # the two drawn games still unpicked midweek
SHOWN_IN_WINNERS = 6
PICKED_MIDWEEK = 12
LIFTED = "WIS@ND"
DAYS = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}


# ------------------------------------------------------------------ colour

def _sat(h):
    r, g, b = (int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    return 0 if mx == mn else (mx - mn) / (1 - abs(2 * light - 1))


def lum(h):
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(h[k:k + 2], 16) / 255) for k in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _scale(h, f):
    r, g, b = (int(h[k:k + 2], 16) for k in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def loud(tid):
    """The louder of a school's two colours, as the Week tab paints a winner."""
    t = TEAMS[tid]
    return max((t["bg"], t["alt"]), key=_sat)


def deep(tid, ceiling=0.16):
    """A school colour dark enough to carry white lettering."""
    c, f = loud(tid), 1.0
    while lum(_scale(c, f)) > ceiling and f > 0.05:
        f -= 0.04
    return _scale(c, f)


def ink(colour):
    """White or near-black, whichever has the higher contrast against the colour."""
    l = lum(colour)
    return "#ffffff" if 1.05 / (l + 0.05) >= (l + 0.05) / 0.0575 else "#101114"


# ------------------------------------------------------------------ the card

def _when(iso):
    t = datetime.fromisoformat(iso) - timedelta(hours=4)  # Eastern daylight time, all of September
    return t.strftime("%a"), t.strftime("%a ") + t.strftime("%I:%M %p").lstrip("0")


def _side(g, f, side):
    tid = g["%s_id" % side]
    rank = f[side]["rank"] if f else 99
    return {"id": tid, "abbr": g["%s_abbr" % side], "school": g["%s_school" % side], "rank": rank if rank and rank < 26 else None,
            "loud": loud(tid), "deep": deep(tid), "bg": TEAMS[tid]["bg"], "ink": ink(loud(tid))}


def _spread(g):
    n = abs(float(g["spread_line"]))
    return "%s -%s" % (g["favorite_abbr"], ("%d" % n) if n == int(n) else ("%.1f" % n))


def _fcs_colours():
    """FCS opponents are in no FBS list, so teams.json lacks them. ESPN's own colour stands in."""
    for f in ESPN.values():
        for side in ("away", "home"):
            t = f[side]
            tid = t["logo"].rsplit("/", 1)[-1].split(".")[0]
            if tid not in TEAMS and t.get("color"):
                TEAMS[tid] = {"id": tid, "abbr": t["abbr"], "school": t["school"], "bg": "#" + t["color"], "alt": "#ffffff", "cut": "light"}


def _card():
    _fcs_colours()
    mine = {r["game_id"]: r for r in LIVE["board"] if r["player_name"] == ME}
    out = []
    for g in sorted(LIVE["slate"], key=lambda g: (g["kickoff"], g["game_id"])):
        f = ESPN.get(str(g["game_id"]))
        day, when = _when(g["kickoff"])
        r = mine[g["game_id"]]
        away, home = _side(g, f, "away"), _side(g, f, "home")
        picked = home if r["pick_abbr"] == home["abbr"] else away
        out.append({"key": "%s@%s" % (away["abbr"], home["abbr"]), "day": DAYS[day], "when": when,
                    "tv": (f or {}).get("tv") or "", "neutral": bool(f and f["neutral_site"]), "spread": _spread(g),
                    "fav": g["favorite_abbr"], "away": away, "home": home, "pick": picked,
                    "opp": away if picked is home else home, "pts": r["confidence"],
                    "dog": r["pick_abbr"] != g["favorite_abbr"]})
    return out


CARD = _card()
BY_KEY = {c["key"]: c for c in CARD}
RANKED = sorted(CARD, key=lambda c: -c["pts"])
FAVORITES = sum(1 for c in CARD if not c["dog"])
UNDERDOGS = sum(1 for c in CARD if c["dog"])


def winners():
    """The six games the Winners phone draws, each with the pick it has midweek (or None)."""
    out = []
    for c in CARD[:SHOWN_IN_WINNERS]:
        out.append(dict(c, chosen=None if c["key"] in OPEN_IN_WINNERS else c["pick"]["abbr"]))
    return out


def days(rows):
    """Group consecutive rows by kickoff day, keeping order."""
    groups = []
    for r in rows:
        if not groups or groups[-1][0] != r["day"]:
            groups.append((r["day"], []))
        groups[-1][1].append(r)
    return groups


def state(c, side):
    """'' for an open game, 'is-picked' for the chosen side, 'is-other' for the side not chosen."""
    if not c.get("chosen"):
        return ""
    return "is-picked" if c["chosen"] == c[side]["abbr"] else "is-other"


# ------------------------------------------------------------------ marks

def _png(path, px):
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo_vars():
    """--lg-<id> the cut for light grounds, --lgd-<id> for dark grounds, --lgc-<id> for the school's own disc."""
    ids = {ME_TEAM} | {c[s]["id"] for c in CARD for s in ("away", "home")}
    out = []
    for i in sorted(ids):
        base = os.path.join(LOGOS, "%s.png" % i)
        dark = os.path.join(LOGOS, "%s-dark.png" % i)
        dark = dark if os.path.exists(dark) else base
        disc = dark if TEAMS[i].get("cut") == "dark" else base
        out.append("--lg-%s:url(%s);--lgd-%s:url(%s);--lgc-%s:url(%s);" % (i, _png(base, 140), i, _png(dark, 140), i, _png(disc, 96)))
    return ":root{%s}" % "".join(out)


def mark(tid, size, var="lgd", cls="pk-mark"):
    return ('<i class="%s" style="width:%dpx;height:%dpx;background-image:var(--%s-%s)" aria-hidden="true"></i>'
            % (cls, size, size, var, tid))


def disc(tid, size, cls="pk-disc"):
    n = round(size * 0.72)
    return ('<span class="%s" style="width:%dpx;height:%dpx;background:%s"><i style="width:%dpx;height:%dpx;'
            'background-image:var(--lgc-%s)"></i></span>' % (cls, size, size, TEAMS[tid]["bg"], n, n, tid))


def me(size=24, cls="pk-disc"):
    return disc(ME_TEAM, size, cls)


# ------------------------------------------------------------------ chrome

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

GRIP = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true"><path d="M8 7h8M8 12h8M8 17h8" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>'
LOCK = ('<svg viewBox="0 0 24 24" width="%d" height="%d" fill="none" aria-hidden="true"><path d="M8 11V7.6a4 4 0 0 1 8 0V11" stroke="currentColor" '
        'stroke-width="2.3" stroke-linecap="round"/><rect x="4.4" y="10.6" width="15.2" height="10.4" rx="2.4" fill="currentColor"/></svg>')
CHECK = '<svg viewBox="0 0 24 24" width="%d" height="%d" fill="none" aria-hidden="true"><path d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def header(p, title="Motley Pick&rsquo;em", week="Week 1 &middot; 20 games"):
    return ('<header class="%s-hdr"><div><span class="%s-hdr__title">%s</span><span class="%s-hdr__week">%s</span></div>'
            '<span class="%s-hdr__me">%s<span>Grant</span></span></header>' % (p, p, title, p, week, p, me(24)))


def tabbar(p):
    tabs = "".join('<span class="%s-tab%s"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden="true">%s</svg>'
                   '<span>%s</span></span>' % (p, " is-on" if k == "Picks" else "", v, k) for k, v in ICONS.items())
    return '<nav class="%s-tabs" aria-label="Tabs">%s</nav>' % (p, tabs)


def more(p, n=len(CARD) - SHOWN_IN_WINNERS):
    """The honest end of a drawn list: the phone would keep scrolling."""
    return '<p class="%s-more pk-more">%d more games below</p>' % (p, n)


def rank_badge(side, cls):
    return '<span class="%s">#%d</span>' % (cls, side["rank"]) if side["rank"] else ""


__all__ = ["CARD", "BY_KEY", "RANKED", "FAVORITES", "UNDERDOGS", "LIFTED", "PICKED_MIDWEEK", "ME_TEAM", "TEAMS", "e",
           "winners", "days", "state", "logo_vars", "mark", "disc", "me", "header", "tabbar", "more", "rank_badge",
           "GRIP", "LOCK", "CHECK", "loud", "deep", "ink", "lum"]

if __name__ == "__main__":
    for c in CARD:
        print(c["day"][:3], c["when"], c["tv"], c["key"], c["spread"], "neutral" if c["neutral"] else "",
              "| pick", c["pick"]["abbr"], c["pts"], "DOG" if c["dog"] else "", "| ranks", c["away"]["rank"], c["home"]["rank"])
    print("favorites", FAVORITES, "underdogs", UNDERDOGS)
    print([(w["key"], w["chosen"]) for w in winners()])
