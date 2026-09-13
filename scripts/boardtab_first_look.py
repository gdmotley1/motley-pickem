"""Board tab, first look: four rough directions on an example Saturday night.

The example is built from Week 1's real picks, frozen after game 15 of 20 in kickoff order
(UNLV at Hawaii): fifteen final, two live with invented in-game scores, three still to
come. Standings at that moment come from weekRecap's race: Grant 151, James 146, Parker
141, Nicole 138.

    node scripts/weektab_model.mjs && python scripts/boardtab_first_look.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weektab_common import BY_NAME, ROOT, TEAMS, e, face, header, logo_css, mark, tabbar  # noqa: E402
from weektab_opt2 import field_for  # noqa: E402

LIVE = json.load(open(os.path.join(ROOT, "outputs", "harness", "week_live.json"), encoding="utf-8"))
MODEL = json.load(open(os.path.join(ROOT, "outputs", "weektab_model.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "outputs", "boardtab-first-look.html")
NAMES = ["Grant", "James", "Parker", "Nicole"]
ME = "Grant"

STEP = MODEL["content"]["race"]["steps"][14]          # after game 15
POINTS = STEP["points"]
ORDER = sorted(NAMES, key=lambda n: -POINTS[n])
SLATE = {f"{g['away_abbr']}@{g['home_abbr']}": g for g in LIVE["slate"]}
BOARD = LIVE["board"]


def picks(key):
    g = SLATE[key]
    rows = [r for r in BOARD if r["game_id"] == g["game_id"]]
    by = {r["player_name"]: r for r in rows}
    return [by[n] for n in NAMES]


# Three sample games: one final, one live (invented in-game score), one still to come.
SAMPLE = [
    {"key": "COLO@GT", "state": "final", "away": 14, "home": 13, "clock": "Final"},
    {"key": "WKU@NEV", "state": "live", "away": 14, "home": 21, "clock": "2nd 1:45"},
    {"key": "WIS@ND", "state": "soon", "clock": "Sat 7:30 PM"},
]


def game_parts(s):
    g = SLATE[s["key"]]
    return g, picks(s["key"])


def spread(g):
    if g.get("spread_line") is None:
        return ""
    return "%s -%g" % (g["favorite_abbr"], abs(float(g["spread_line"])))


# ------------------------------------------------------------------ shared chrome

def standings(cls):
    rows = []
    lead = POINTS[ORDER[0]]
    for i, n in enumerate(ORDER):
        t = TEAMS[BY_NAME[n]["team_id"]]
        rows.append('<div class="%s-row%s"><span class="%s-rank" style="background:%s">%d</span>%s'
                    '<span class="%s-who"><b>%s</b><span>%s</span></span><strong>%d</strong></div>'
                    % (cls, " is-lead" if i == 0 else "", cls, t["alt"], i + 1, face(n, 30), cls, e(n),
                       "leads" if i == 0 else "%d back" % (lead - POINTS[n]), POINTS[n]))
    return "".join(rows)


def status_slab(s, cls):
    kind = {"final": "is-final", "live": "is-live", "soon": "is-soon"}[s["state"]]
    dot = '<i></i>' if s["state"] == "live" else ""
    return '<span class="%s-status %s">%s%s</span>' % (cls, kind, dot, e(s["clock"]))


def chip(r, state, cls, show_pick=True):
    if state == "soon" and r["player_name"] != ME:
        return '<span class="%s-chip is-hidden">%s<b>&#8226;&#8226;&#8226;</b></span>' % (cls, face(r["player_name"], 24))
    won = state == "final" and r["pick_abbr"] == SLATE_WINNER.get(r["game_id"])
    lost = state == "final" and not won
    k = " is-won" if won else " is-lost" if lost else ""
    pick = '<em>%s</em>' % e(r["pick_abbr"]) if show_pick else ""
    num = ("+%d" % r["confidence"]) if won else str(r["confidence"])
    return '<span class="%s-chip%s">%s%s<b>%s</b></span>' % (cls, k, face(r["player_name"], 24), pick, num)


SLATE_WINNER = {g["game_id"]: g["winner_abbr"] for g in LIVE["slate"]}


# ----------------------------------------------------------------- 1: plates

def opt_plates():
    cards = []
    for s in SAMPLE:
        g, ps = game_parts(s)
        sides = []
        for side in ("away", "home"):
            abbr = g["%s_abbr" % side]
            score = s.get(side)
            loser = s["state"] == "final" and abbr != g["winner_abbr"]
            sides.append('<span class="pl-side%s">%s<b>%s</b><strong>%s</strong></span>'
                         % (" is-loser" if loser else "", mark(g["%s_id" % side], 34), e(abbr),
                            "" if score is None else score))
        cards.append('<article class="pl-card"><div class="pl-top">%s%s%s</div><p class="pl-line">%s</p>'
                     '<div class="pl-chips">%s</div></article>'
                     % (sides[0], status_slab(s, "pl"), sides[1], e(spread(g)),
                        "".join(chip(r, s["state"], "pl") for r in ps)))
    return ('<section class="pl-standings"><p class="pl-kick"><span>Week 1</span><span class="pl-livetag"><i></i>2 live</span>'
            '<span class="pl-of">15 of 20 final</span></p>%s</section><div class="pl-games">%s</div>'
            % (standings("pl"), "".join(cards)))


# ----------------------------------------------------------------- 2: the sheet

def opt_sheet():
    head = "".join('<span class="sh-col">%s<b>%s</b><strong>%d</strong></span>' % (face(n, 28), e(n), POINTS[n]) for n in NAMES)
    rows = []
    for s in SAMPLE:
        g, ps = game_parts(s)
        cells = []
        for r in ps:
            if s["state"] == "soon" and r["player_name"] != ME:
                cells.append('<span class="sh-cell is-hidden">&#128274;</span>')
                continue
            winner = SLATE_WINNER.get(r["game_id"])
            k = "" if s["state"] != "final" else (" is-won" if r["pick_abbr"] == winner else " is-lost")
            pid = g["home_id"] if r["pick_abbr"] == g["home_abbr"] else g["away_id"]
            cells.append('<span class="sh-cell%s">%s<b>%d</b></span>' % (k, mark(pid, 24), r["confidence"]))
        score = ("%s %s, %s %s" % (g["away_abbr"], s["away"], g["home_abbr"], s["home"])) if "away" in s else "%s at %s" % (g["away_abbr"], g["home_abbr"])
        rows.append('<div class="sh-row"><span class="sh-game">%s%s<span class="sh-g">%s</span>%s</span>%s</div>'
                    % (mark(g["away_id"], 22), mark(g["home_id"], 22), e(score), status_slab(s, "sh"), "".join(cells)))
    return ('<section class="sh-top"><p class="sh-kick">Week 1 &middot; 15 of 20 final &middot; <span>2 live</span></p></section>'
            '<div class="sh-sheet"><div class="sh-head"><span class="sh-corner">Game</span>%s</div>%s</div>'
            % (head, "".join(rows)))


# ----------------------------------------------------------------- 3: live first

def opt_live_first():
    live = [s for s in SAMPLE if s["state"] == "live"]
    final = [s for s in SAMPLE if s["state"] == "final"]
    soon = [s for s in SAMPLE if s["state"] == "soon"]

    def big(s):
        g, ps = game_parts(s)
        return ('<article class="lf-live"><div class="lf-score"><span>%s<b>%s</b><strong>%s</strong></span>%s'
                '<span>%s<b>%s</b><strong>%s</strong></span></div><div class="lf-chips">%s</div></article>'
                % (mark(g["away_id"], 44), e(g["away_abbr"]), s["away"], status_slab(s, "lf"),
                   mark(g["home_id"], 44), e(g["home_abbr"]), s["home"], "".join(chip(r, "live", "lf") for r in ps)))

    def line(s):
        g, ps = game_parts(s)
        w = g["winner_abbr"]
        wid = g["home_id"] if w == g["home_abbr"] else g["away_id"]
        dots = "".join('<span class="lf-dot %s">%s<b>%s</b></span>'
                       % ("is-won" if r["pick_abbr"] == w else "is-lost", face(r["player_name"], 22),
                          ("+%d" % r["confidence"]) if r["pick_abbr"] == w else r["confidence"]) for r in ps)
        return ('<div class="lf-final">%s<span class="lf-w"><b>%s</b><span>%s %s, %s %s</span></span><div class="lf-dots">%s</div></div>'
                % (mark(wid, 30), e(w), e(g["away_abbr"]), s["away"], e(g["home_abbr"]), s["home"], dots))

    def later(s):
        g, ps = game_parts(s)
        mine = next(r for r in ps if r["player_name"] == ME)
        pid = g["home_id"] if mine["pick_abbr"] == g["home_abbr"] else g["away_id"]
        return ('<div class="lf-soon"><span class="lf-w"><b>%s at %s</b><span>%s</span></span>'
                '<span class="lf-mine">You: %s<b>%s %d</b></span></div>'
                % (e(g["away_abbr"]), e(g["home_abbr"]), e(s["clock"]), mark(pid, 22), e(mine["pick_abbr"]), mine["confidence"]))

    return ('<section class="lf-top">%s</section>'
            '<h3 class="lf-h"><i></i>Live now <span>2</span></h3>%s'
            '<h3 class="lf-h">Final <span>15</span></h3>%s'
            '<h3 class="lf-h">Still to come <span>3</span></h3>%s'
            % (standings("lf"), "".join(big(s) for s in live), "".join(line(s) for s in final), "".join(later(s) for s in soon)))


# ----------------------------------------------------------------- 4: leader's colors

def opt_leader():
    n = ORDER[0]
    field, ink = field_for(BY_NAME[n]["team_id"])
    lead = POINTS[n] - POINTS[ORDER[1]]
    hero = ('<section class="ld-hero" style="--ld-field:%s;--ld-ink:%s"><i class="ld-mark" style="background-image:var(--lg-%s)"></i>'
            '<p class="ld-kick"><span>Week 1</span><span class="ld-live"><i></i>Live &middot; 15 of 20 final</span></p>'
            '<h2 class="ld-name">%s</h2><p class="ld-leads">leads by %d</p>'
            '<div class="ld-mini">%s</div></section>'
            % (field, ink, BY_NAME[n]["team_id"], e(n), lead,
               "".join('<span class="ld-m">%s<b>%s</b><strong>%d</strong></span>' % (face(x, 26), e(x), POINTS[x]) for x in ORDER)))
    return hero + '<div class="pl-games">%s</div>' % opt_plates().split('<div class="pl-games">', 1)[1]


OPTIONS = [
    (1, "Game plates", opt_plates, "The Week tab's look on the live week. Each game is a score plate with a status slab, and all four picks sit in one row of chips, not four stacked rows."),
    (2, "The sheet", opt_sheet, "The old paper pool sheet. Four columns, one per person, pinned at the top with their points; every game is one row showing the team each of you took and the points on it."),
    (3, "Live first", opt_live_first, "Sorted for a Saturday: live games big at the top, finals as one tight line each, and games still to come show only your pick."),
    (4, "Leader's colors", opt_leader, "The loud one. The top of the Board wears the current leader's school colors and flips when the lead changes."),
]


def page():
    css = open(os.path.join(ROOT, "scripts", "boardtab_first_look.css"), encoding="utf-8").read()
    base = open(os.path.join(ROOT, "scripts", "weektab_base.css"), encoding="utf-8").read()
    phones = "".join(
        '<figure class="bf-opt"><figcaption><b>%d</b> %s</figcaption><p>%s</p>'
        '<div class="wt-phone bf">%s%s</div></figure>' % (n, name, what, header("bf-hdr"), fn())
        for n, name, fn, what in OPTIONS)
    fonts = ("https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,400..900;1,62..125,400..900"
             "&family=Inter:wght@400;500;600;700;800&display=swap")
    return ('<!doctype html>\n<html lang="en"><meta charset="utf-8"><title>Board Tab First Look</title>'
            '<link href="%s" rel="stylesheet"><style>%s\n%s\n%s</style>'
            '<div class="bf-row">%s</div>' % (fonts, logo_css(), base, css, phones))


if __name__ == "__main__":
    html = page()
    open(OUT, "w", encoding="utf-8", newline="").write(html)
    print("wrote", OUT, "standings", {n: POINTS[n] for n in ORDER})
