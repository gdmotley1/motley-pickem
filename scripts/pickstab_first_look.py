"""Picks tab, first look: four rough directions on Grant's real Week 1 card.

Each phone shows the two halves of the tab in one scroll: step 1, choosing winners (four
real Saturday games, two picked, 12 of 20 done), then step 2, the points, Grant's real top
five with one game lifted. Rough on purpose; the full board comes after a pick.

    python scripts/pickstab_first_look.py
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
TEAMS = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}
OUT = os.path.join(ROOT, "outputs", "pickstab-first-look.html")
ME_TEAM = next(s["team_id"] for s in LIVE["seats"] if s["name"] == "Grant")

SLATE = {"%s@%s" % (g["away_abbr"], g["home_abbr"]): g for g in LIVE["slate"]}
MINE = {r["game_id"]: r for r in LIVE["board"] if r["player_name"] == "Grant"}

# Step 1: four Saturday games in kickoff order. Two carry Grant's real pick, two are open.
CHOOSE = [("BAY@AUB", True), ("BOIS@ORE", False), ("CLEM@LSU", True), ("WIS@ND", False)]
# Step 2: Grant's real top five. ND is lifted.
RANK = sorted((r for r in LIVE["board"] if r["player_name"] == "Grant"), key=lambda r: -r["confidence"])[:5]
LIFTED = "ND"


def png(path, px):
    from PIL import Image

    im = Image.open(path).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def logo_vars(ids):
    out = []
    for i in sorted(ids):
        base = os.path.join(ROOT, "static", "logos", "%s.png" % i)
        dark = os.path.join(ROOT, "static", "logos", "%s-dark.png" % i)
        dark = dark if os.path.exists(dark) else base
        disc = dark if TEAMS[i].get("cut") == "dark" else base
        out.append("--lg-%s:url(%s);--lgd-%s:url(%s);--lgc-%s:url(%s);" % (i, png(base, 120), i, png(dark, 120), i, png(disc, 96)))
    return ":root{%s}" % "".join(out)


def mark(tid, size, var="lgd", cls="pk-mark"):
    return '<i class="%s" style="width:%dpx;height:%dpx;background-image:var(--%s-%s)"></i>' % (cls, size, size, var, tid)


def face(tid, size, cls="pk-disc"):
    n = round(size * 0.72)
    return ('<span class="%s" style="width:%dpx;height:%dpx;background:%s"><i style="width:%dpx;height:%dpx;'
            'background-image:var(--lgc-%s)"></i></span>' % (cls, size, size, TEAMS[tid]["bg"], n, n, tid))


def sat(h):
    r, g, b = (int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    return 0 if mx == mn else (mx - mn) / (1 - abs(2 * light - 1))


def lum(h):
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(h[k:k + 2], 16) / 255) for k in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def loud(tid):
    t = TEAMS[tid]
    return max((t["bg"], t["alt"]), key=sat)


def darkish(tid, ceiling=0.2):
    c = loud(tid)
    r, g, b = (int(c[k:k + 2], 16) for k in (1, 3, 5))
    f = 1.0
    while lum("#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))) > ceiling and f > 0.05:
        f -= 0.04
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def ink(colour):
    return "#111111" if lum(colour) > 0.42 else "#ffffff"


def kickoff(iso):
    t = datetime.fromisoformat(iso) - timedelta(hours=4)  # EDT through the regular season's September
    return t.strftime("%a ") + t.strftime("%I:%M %p").lstrip("0")


def spread(g):
    return "%s -%g" % (g["favorite_abbr"], abs(float(g["spread_line"])))


def games():
    out = []
    for key, picked in CHOOSE:
        g = SLATE[key]
        mine = MINE[g["game_id"]]["pick_abbr"] if picked else None
        out.append({"g": g, "pick": mine, "when": kickoff(g["kickoff"]), "line": spread(g)})
    return out


def ranks():
    out = []
    by_id = {g["game_id"]: g for g in LIVE["slate"]}
    for r in RANK:
        g = by_id[r["game_id"]]
        home = r["pick_abbr"] == g["home_abbr"]
        out.append({"pts": r["confidence"], "abbr": r["pick_abbr"], "tid": g["home_id"] if home else g["away_id"],
                    "opp": g["away_abbr"] if home else g["home_abbr"], "line": spread(g),
                    "school": g["home_school"] if home else g["away_school"], "lifted": r["pick_abbr"] == LIFTED})
    return out


def sides(g):
    return [(g["away_id"], g["away_abbr"], g["away_school"]), (g["home_id"], g["home_abbr"], g["home_school"])]


def cls(pick, abbr):
    if not pick:
        return ""
    return " is-picked" if pick == abbr else " is-other"


# ------------------------------------------------------------------ 1: jumbotron

def opt_jumbo():
    segs = "".join('<i class="%s"></i>' % ("on" if i < 12 else "") for i in range(20))
    tiles = []
    for x in games():
        g = x["g"]
        rows = "".join(
            '<button class="j1-team%s" style="--t:%s">%s<span class="j1-school">%s</span><span class="j1-tag">Pick</span></button>'
            % (cls(x["pick"], a), darkish(tid), mark(tid, 38), e(s), ) for tid, a, s in sides(g))
        tiles.append('<article class="j1-game%s"><header><span class="j1-when">%s</span><span class="j1-line">%s</span>'
                     '<span class="j1-cta"><span class="j1-shine"></span>Matchup &rsaquo;</span></header>%s</article>'
                     % (" is-done" if x["pick"] else "", e(x["when"]), e(x["line"]), rows))
    rrows = "".join(
        '<div class="j1-rank%s" style="--t:%s"><span class="j1-led j1-pts"><span>%d</span></span>%s'
        '<span class="j1-who"><b>%s</b><span>over %s &middot; %s</span></span><span class="j1-cue">%s</span></div>'
        % (" is-lifted" if r["lifted"] else " is-target", darkish(r["tid"]), r["pts"], mark(r["tid"], 30), e(r["abbr"]),
           e(r["opp"]), e(r["line"]), "Moving" if r["lifted"] else "Here") for r in ranks())
    return (
        '<div class="j1"><header class="j1-hdr"><span class="j1-brand">Motley Pick&rsquo;em</span><span class="j1-me">%s Grant</span></header>'
        '<div class="j1-wall"><div class="j1-strip"><span>Week 1</span><span class="j1-onair">Your card</span>'
        '<span class="j1-count"><span class="j1-led"><span>12</span></span>/20</span></div>'
        '<div class="j1-segs">%s</div>'
        '<h3 class="j1-h">Pick your winners</h3>%s'
        '<h3 class="j1-h">Points <span class="j1-reset">Reset to spread</span></h3><div class="j1-ranks">%s</div></div>'
        '<div class="j1-lift"><span>Moving <b>ND</b>. Tap a row to give it those points.</span><span class="j1-cancel">Cancel</span></div></div>'
        % (face(ME_TEAM, 24), segs, "".join(tiles), rrows))


# ------------------------------------------------------------------ 2: select screen

def opt_select():
    tiles = []
    for x in games():
        g = x["g"]
        panes = []
        for tid, a, s in sides(g):
            panes.append('<button class="s2-side%s" style="--c:%s;--c2:%s">%s<span class="s2-school">%s</span>'
                         '<span class="s2-sel">Selected</span></button>'
                         % (cls(x["pick"], a), darkish(tid, 0.12), loud(tid), mark(tid, 70), e(s)))
        tiles.append('<article class="s2-game%s"><div class="s2-meta"><span>%s</span><span class="s2-line">%s</span>'
                     '<span class="s2-cta"><span class="s2-shine"></span>Matchup</span></div>'
                     '<div class="s2-vs">%s<span class="s2-versus">VS</span>%s</div></article>'
                     % (" is-done" if x["pick"] else "", e(x["when"]), e(x["line"]), panes[0], panes[1]))
    rrows = "".join(
        '<div class="s2-rank%s" style="--c:%s"><span class="s2-pts">%d</span>%s<span class="s2-who"><b>%s</b><span>over %s</span></span>'
        '<span class="s2-line2">%s</span></div>'
        % (" is-lifted" if r["lifted"] else "", loud(r["tid"]), r["pts"], mark(r["tid"], 34), e(r["school"]), e(r["opp"]), e(r["line"]))
        for r in ranks())
    segs = "".join('<i class="%s"></i>' % ("on" if i < 12 else "") for i in range(20))
    return (
        '<div class="s2"><header class="s2-hdr"><span class="s2-brand">Motley Pick&rsquo;em</span><span class="s2-me">%s Grant</span></header>'
        '<div class="s2-top"><span class="s2-mode">Week 1 &middot; Select winners</span><span class="s2-count"><b>12</b>/20</span></div>'
        '<div class="s2-segs">%s</div>%s'
        '<div class="s2-dc"><h3>Depth chart</h3><span>Reset to spread</span></div>'
        '<p class="s2-hint">Tap a team, then tap where it goes</p>%s</div>'
        % (face(ME_TEAM, 24), segs, "".join(tiles), rrows))


# ------------------------------------------------------------------ 3: face-off

def opt_faceoff():
    tiles = []
    for x in games():
        g = x["g"]
        halves = []
        for side, (tid, a, s) in zip(("l", "r"), sides(g)):
            c = loud(tid)
            halves.append('<button class="f3-half f3-%s%s" style="--c:%s;--ink:%s">%s<span class="f3-school">%s</span>'
                          '<span class="f3-stamp">Picked</span></button>'
                          % (side, cls(x["pick"], a), c, ink(c), mark(tid, 58, "lgd" if ink(c) == "#ffffff" else "lg"), e(s)))
        tiles.append('<article class="f3-game"><div class="f3-split">%s%s<span class="f3-at">@</span></div>'
                     '<div class="f3-meta"><span>%s &middot; <b>%s</b></span><span class="f3-cta"><span class="f3-shine"></span>Matchup &rsaquo;</span></div></article>'
                     % (halves[0], halves[1], e(x["when"]), e(x["line"])))
    rrows = "".join(
        '<div class="f3-rank%s" style="--c:%s;--ink:%s"><span class="f3-pts">%d</span>%s<span class="f3-who"><b>%s</b><span>over %s &middot; %s</span></span></div>'
        % (" is-lifted" if r["lifted"] else "", loud(r["tid"]), ink(loud(r["tid"])), r["pts"],
           mark(r["tid"], 34, "lgd" if ink(loud(r["tid"])) == "#ffffff" else "lg"), e(r["school"]), e(r["opp"]), e(r["line"]))
        for r in ranks())
    return (
        '<div class="f3"><header class="f3-hdr"><span class="f3-brand">Motley Pick&rsquo;em</span><span class="f3-me">%s Grant</span></header>'
        '<div class="f3-top"><h2>12 of 20<br>picked</h2><div class="f3-bar"><i style="width:60%%"></i></div></div>%s'
        '<div class="f3-top f3-top2"><h2>Points</h2><span class="f3-reset">Reset to spread</span></div>%s</div>'
        % (face(ME_TEAM, 24), "".join(tiles), rrows))


# ------------------------------------------------------------------ 4: whiteboard

CIRCLE = ('<svg class="w4-circle" viewBox="0 0 200 80" preserveAspectRatio="none" aria-hidden="true"><path d="M112 6 C 176 4, 198 22, 192 42 '
          'C 184 70, 58 78, 16 58 C -6 46, 6 16, 64 8 C 98 3, 140 6, 160 12" fill="none" stroke="#d7261e" stroke-width="4.5" '
          'stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')


def tally(n):
    groups = []
    while n > 0:
        k = min(5, n)
        groups.append('<span class="w4-tg">%s%s</span>' % ("<i></i>" * min(k, 4), "<s></s>" if k == 5 else ""))
        n -= k
    return "".join(groups)


def opt_board():
    tiles = []
    for x in games():
        g = x["g"]
        teams = []
        for tid, a, s in sides(g):
            teams.append('<button class="w4-team%s">%s<span class="w4-school">%s</span>%s</button>'
                         % (cls(x["pick"], a), face(tid, 44, "pk-disc w4-magnet"), e(s), CIRCLE if x["pick"] == a else ""))
        tiles.append('<article class="w4-game"><div class="w4-meta"><span>%s</span><span class="w4-line">%s</span></div>'
                     '<div class="w4-teams">%s<span class="w4-vs">vs</span>%s</div>'
                     '<span class="w4-note">Matchup &rarr;</span></article>' % (e(x["when"]), e(x["line"]), teams[0], teams[1]))
    rrows = "".join(
        '<div class="w4-rank%s"><span class="w4-pts">%d</span>%s<span class="w4-who">%s <small>over %s</small></span><span class="w4-line">%s</span>%s</div>'
        % (" is-lifted" if r["lifted"] else "", r["pts"], face(r["tid"], 34, "pk-disc w4-magnet"), e(r["school"]), e(r["opp"]),
           e(r["line"]), '<span class="w4-arrow">&#8599; moving</span>' if r["lifted"] else "")
        for r in ranks())
    return (
        '<div class="w4"><div class="w4-tray"></div><header class="w4-hdr"><span class="w4-brand">Motley Pick&rsquo;em</span><span class="w4-me">%s Grant</span></header>'
        '<div class="w4-top"><span class="w4-wk">Week 1</span><span class="w4-tally">%s</span><span class="w4-of">12 of 20</span></div>%s'
        '<div class="w4-top"><span class="w4-wk">Depth chart</span><span class="w4-reset">Reset to spread</span></div><div class="w4-ranks">%s</div></div>'
        % (face(ME_TEAM, 30, "pk-disc w4-magnet"), tally(12), "".join(tiles), rrows))


OPTIONS = [
    (1, "Jumbotron", opt_jumbo, "The Board&rsquo;s LED wall, so Picks and Board are one stadium. Each team is a full-width lit panel in its colors; your pick glows gold, the other side goes dark."),
    (2, "Select screen", opt_select, "The college football video game. Every game is a VS team-select screen with big logos; your pick pops forward. Points become the depth chart."),
    (3, "Face-off", opt_faceoff, "Bright and loud. Each game is a split band in both schools&rsquo; colors; the side you pick stays lit and gets stamped, the other goes grey."),
    (4, "Coach&rsquo;s whiteboard", opt_board, "The cartoon one. Team magnets on a whiteboard, your pick circled in red marker, tally marks for progress, a sticky note for the matchup."),
]


def page():
    ids = set()
    for x in games():
        ids |= {x["g"]["home_id"], x["g"]["away_id"]}
    ids |= {r["tid"] for r in ranks()} | {ME_TEAM}
    css = open(os.path.join(ROOT, "scripts", "pickstab_first_look.css"), encoding="utf-8").read()
    fonts = ("https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,400..900;1,62..125,400..900"
             "&family=Big+Shoulders+Display:wght@600;700;800;900&family=Inter:wght@400;500;600;700;800"
             "&family=Saira:ital,wdth,wght@0,50..125,400..900;1,50..125,400..900&family=Permanent+Marker&family=Kalam:wght@400;700&display=swap")
    phones = "".join('<figure class="fl-opt"><figcaption><b>%d</b> %s</figcaption><p>%s</p><div class="pk-phone">%s</div></figure>'
                     % (n, name, what, fn()) for n, name, fn, what in OPTIONS)
    return ('<!doctype html>\n<html lang="en"><meta charset="utf-8"><title>Picks Tab First Look</title>'
            '<link href="%s" rel="stylesheet"><style>%s\n%s</style><div class="fl-row">%s</div>' % (fonts, logo_vars(ids), css, phones))


if __name__ == "__main__":
    open(OUT, "w", encoding="utf-8", newline="").write(page())
    print("wrote", OUT)
    print([(x["g"]["away_abbr"], x["g"]["home_abbr"], x["pick"], x["when"], x["line"]) for x in games()])
    print([(r["pts"], r["abbr"], r["opp"], r["line"]) for r in ranks()])
