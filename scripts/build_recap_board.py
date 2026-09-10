# -*- coding: utf-8 -*-
"""Render the Standings-revamp options as real phone screens, in one self-contained page.

Grant asked for the Standings tab to be split (this week vs season) and for the week to
carry a written recap once every game is final. Per memory/ui-patterns.md the way that
decision gets made here is a comparison board, not a description: options labelled A/B/C,
rendered at phone width against the project's own tokens, using data he recognises.

    python scripts/build_recap_board.py                    # -> outputs/recap-board.html
    python scripts/build_recap_board.py --out somewhere.html

Every number on this page is real Week 1 (2026) output, computed from the live database
on 2026-09-10 and pasted in below as literals. The detectors that produced them are the
ones a WeekRecap component would run in the browser; they are listed in STORY so the
board and the eventual implementation cannot describe different statistics.

Same two rules as build_theme_board.py, for the same reasons:

  - Token names match the semantic contract in src/theme.css exactly, so a layout chosen
    here is liftable into src/app.css rather than translated.
  - Logos are inlined as downscaled data URIs, because a published artifact's content
    policy blocks every external image.

The phone interiors are pinned to the light Slate palette regardless of the board's own
theme. The app is light-only; a phone that went dark with the viewer's OS would be
showing a screen that does not exist.
"""
from __future__ import annotations

import argparse
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_theme_board import logo_uri  # noqa: E402  (same directory, same job)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------- the family
# color and team_id are the live players rows; bg is the team's avatar ground from
# static/data/teams.json, which is what Avatar renders behind the mark.
PLAYERS = [
    # name,   color,     team_id, team_bg,   pts, correct
    ("Grant",  "#B85C1F", "2751", "#ffc425", 186, 16),
    ("James",  "#1F6F4A", "61",   "#ba0c2f", 179, 16),
    ("Parker", "#2E5C8A", "338",  "#fdbb30", 164, 12),
    ("Nicole", "#8A2E4F", None,   None,      147, 10),
]

GAMES = 20

# ------------------------------------------------------------------------ the storylines
# Each entry is (detector, headline, body). The detector name is the contract: it is what
# the browser-side function would be called, so nothing here is a fact the app could not
# recompute for week 7 on its own.
STORY = [
    ("wonBy",
     "Grant takes Week 1 by 7",
     "He and James both finished 16-4. The record tied, so the week came down to where "
     "the points were spent."),
    ("headToHead",
     "UNLV at Hawaii decided it",
     "Grant put 10 on UNLV, James put 3. That 7-point edge was the largest gap between "
     "them on any single game, and it is exactly the margin he won by."),
    ("swingGame",
     "Wisconsin at Notre Dame split the family",
     "Nicole was alone on Wisconsin for 2. Everyone else banked 14 to 18 on Notre Dame. "
     "An 18-point spread, the widest of the week."),
    ("upsets",
     "Three dogs got up, one got called",
     "Tulsa over Oklahoma State as a 13.5 dog and Colorado over Georgia Tech as a 6.5 "
     "dog went uncalled by anyone. Only Nevada, +1.5, was called: Grant and Nicole."),
    ("chalk",
     "Favorites went 17-3",
     "An 85% chalk week. The pool rewarded conviction, and the three players who went "
     "5-0 on their top five all finished within 40 points of the lead."),
    ("unanimousMiss",
     "All four fought SMU and lost",
     "SMU was a 2.5 favorite at Florida State and won 27-24. Every single person in "
     "the family took Florida State."),
]

# The four stat tiles used by option B, and again on the season screen.
TILES = [
    ("Swing game", "18", "pts", "WIS at ND"),
    ("Upsets", "3", "of 20", "1 called"),
    ("Chalk", "85", "%", "favorites 17-3"),
    ("Whiffs", "3", "games", "all four wrong"),
]

# Option C's beat sheet: the week in the order it happened, with the running margin
# between the top two. Real per-game head-to-head output.
BEATS = [
    ("Thu", "COLO at GT", "Colorado won outright as a 6.5 dog",
     "James had 17 on Georgia Tech, Grant had 8", "+9", "up"),
    ("Fri", "UNLV at HAW", "UNLV covered and won",
     "Grant 10, James 3", "+7", "up"),
    ("Sat", "BOIS at ORE", "Oregon rolled",
     "James 18, Grant 14", "-4", "down"),
    ("Sat", "WIS at ND", "Notre Dame held on",
     "Nicole alone on Wisconsin for 2", "+2", "up"),
    ("Sat", "OKST at TLSA", "Tulsa stunned Oklahoma State",
     "Nicole lost 15, nobody called it", "0", "flat"),
]

SEASON_WEEKS = [("Week 1", "Grant", "186", True), ("Week 2", "in progress", "-", False)]


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ------------------------------------------------------------------------------ fragments


def avatar(name: str, color: str, team_id, team_bg, size: int = 36) -> str:
    """The real Avatar: a team mark on the team's ground, else initials on the seat colour."""
    if team_id:
        uri = logo_uri(team_id)
        if uri:
            inner = '<img src="%s" alt="" width="%d" height="%d">' % (
                uri, round(size * 0.72), round(size * 0.72))
            return ('<span class="avatar avatar--team" style="width:%dpx;height:%dpx;'
                    'background:%s">%s</span>' % (size, size, esc(team_bg), inner))
    return ('<span class="avatar" style="width:%dpx;height:%dpx;background:%s;'
            'font-size:%.1fpx">%s</span>' % (size, size, esc(color), size * 0.42,
                                             esc(name[0].upper())))


def standing_rows(players, leader_class: bool = True) -> str:
    """The .stand / .srow block, verbatim from src/screens/Standings.jsx."""
    out = []
    last_pts, last_pos = None, 0
    for i, (name, color, tid, bg, pts, cor) in enumerate(players):
        if pts != last_pts:
            last_pos, last_pts = i + 1, pts
        lead = " is-leader" if (leader_class and last_pos == 1) else ""
        pct = round(cor / GAMES * 100)
        out.append(
            '<div class="srow%s"><span class="srow__pos num">%d</span>%s'
            '<span class="srow__body"><span class="srow__name">%s</span>'
            '<span class="srow__meta num">%d-%d &middot; %d%% right</span></span>'
            '<span><span class="srow__pts num">%d</span>'
            '<span class="srow__ptslabel">pts</span></span></div>'
            % (lead, last_pos, avatar(name, color, tid, bg), esc(name),
               cor, GAMES - cor, pct, pts))
    return '<div class="stand">%s</div>' % "".join(out)


def phone(label: str, body: str, tab: str = "week", note: str = "") -> str:
    """One device frame carrying the app's real chrome around a screen body."""
    tabs = [("board", "Board"), ("picks", "Picks"), ("week", "Week"), ("season", "Season")]
    bar = "".join(
        '<span class="tab%s">%s</span>' % (" is-on" if t == tab else "", esc(t_label))
        for t, t_label in tabs)
    return """
<figure class="opt">
  <figcaption class="opt__cap">%s</figcaption>
  <div class="phone">
    <div class="apphdr">
      <span><span class="apphdr__title">Motley Pick'em</span>
      <span class="apphdr__week">Week 1 &middot; final</span></span>
      <span class="apphdr__me">%s<span>Grant</span></span>
    </div>
    <div class="phone__body">%s</div>
    <div class="tabbar">%s</div>
  </div>
  %s
</figure>""" % (esc(label), avatar("Grant", "#B85C1F", "2751", "#ffc425", 24), body, bar,
                ('<p class="opt__note">%s</p>' % note) if note else "")


def screen_head(eyebrow: str, title: str, sub: str = "") -> str:
    return ('<div class="screen"><p class="eyebrow">%s</p><h1 class="h1">%s</h1>%s</div>'
            % (esc(eyebrow), esc(title),
               ('<p class="sub">%s</p>' % esc(sub)) if sub else ""))


# --------------------------------------------------------------------------- the options


def option_a() -> str:
    """Recap leads. The story is the screen; the table is the footnote."""
    beats = "".join(
        '<div class="beat"><p class="beat__h">%s</p><p class="beat__b">%s</p></div>'
        % (esc(h), esc(b)) for _, h, b in STORY[1:4])
    body = (
        screen_head("Week 1 &middot; final", "Grant takes it by 7")
        + '<div class="screen"><div class="recap">'
        '<p class="recap__lede">He and James both finished <b>16-4</b>. The record tied, '
        'so the week came down to where the points were spent.</p>'
        + beats +
        '</div></div>'
        + '<div class="screen"><h3 class="h2">Final</h3></div>'
        + standing_rows(PLAYERS))
    return phone(
        "A &middot; The write-up leads",
        body,
        note="The recap is the screen and the table sits under it. Closest to what you "
             "asked for, and it reads like something worth opening on a Sunday. Costs "
             "about 220px before the first name appears.")


def option_b() -> str:
    """Result first, analysis as tiles."""
    tiles = "".join(
        '<div class="tile"><p class="tile__k">%s</p><p class="tile__v num">%s'
        '<span>%s</span></p><p class="tile__s">%s</p></div>'
        % (esc(k), esc(v), esc(u), esc(s)) for k, v, u, s in TILES)
    body = (
        screen_head("Week 1 &middot; final", "Standings", "Ties stand. Two people can share a week.")
        + standing_rows(PLAYERS)
        + '<div class="screen"><h3 class="h2">The week in four numbers</h3></div>'
        + '<div class="tiles">%s</div>' % tiles
        + '<div class="screen"><button class="linkrow">Read the full write-up'
          '<span>&rsaquo;</span></button></div>')
    return phone(
        "B &middot; Result first, stats as tiles",
        body,
        note="Opens on the answer everyone came for, then four tappable numbers. Most "
             "phone-native and the least reading. The narrative moves behind a tap, "
             "which is the tradeoff.")


def option_c() -> str:
    """The week as it happened, with the lead moving."""
    beats = "".join(
        '<div class="tl__row"><span class="tl__day">%s</span>'
        '<span class="tl__dot tl__dot--%s"></span>'
        '<span class="tl__body"><span class="tl__game">%s</span>'
        '<span class="tl__what">%s</span><span class="tl__why">%s</span></span>'
        '<span class="tl__d num tl__d--%s">%s</span></div>'
        % (esc(d), esc(dirn), esc(g), esc(w), esc(y), esc(dirn), esc(delta))
        for d, g, w, y, delta, dirn in BEATS)
    body = (
        screen_head("Week 1 &middot; final", "How it happened",
                    "Grant 186, James 179. The lead, game by game.")
        + '<div class="tl">%s</div>' % beats
        + '<div class="screen"><h3 class="h2">Final</h3></div>'
        + standing_rows(PLAYERS))
    return phone(
        "C &middot; The week as a timeline",
        body,
        note="Shows the lead actually moving, in kickoff order, with the running margin "
             "between the top two. The most analytical. It only works when the top two "
             "are close, and it says little in a blowout week.")


def season_screen() -> str:
    weeks = "".join(
        '<div class="wk%s"><span class="wk__n">%s</span>'
        '<span class="wk__w">%s</span><span class="wk__p num">%s</span></div>'
        % (" is-done" if done else "", esc(n), esc(w), esc(p))
        for n, w, p, done in SEASON_WEEKS)
    tiles = "".join(
        '<div class="tile"><p class="tile__k">%s</p><p class="tile__v num">%s'
        '<span>%s</span></p><p class="tile__s">%s</p></div>' % (esc(k), esc(v), esc(u), esc(s))
        for k, v, u, s in [
            ("Weeks won", "1", "of 1", "Grant"),
            ("Best week", "186", "pts", "Grant, Week 1"),
            ("Upsets called", "2", "total", "Grant, Nicole"),
            ("Top-5 accuracy", "95", "%", "19 of 20 across the family"),
        ])
    body = (
        screen_head("Season 2026", "Season", "Fifteen weeks. Everything adds up here.")
        + standing_rows(PLAYERS)
        + '<div class="screen"><h3 class="h2">Week by week</h3>'
          '<p class="sub">Who took each week, and on what.</p></div>'
        + '<div class="wks">%s</div>' % weeks
        + '<div class="screen"><h3 class="h2">Season stats</h3></div>'
        + '<div class="tiles">%s</div>' % tiles)
    return phone(
        "The Season tab",
        body,
        tab="season",
        note="Thin after one week, which is honest: it fills in as weeks land. The "
             "week-by-week strip is the part that gets good, and it is the only place "
             "a season total belongs once Standings goes week-only.")


def today_screen() -> str:
    """What is there now, so the redundancy is visible rather than asserted."""
    bars = "".join(
        '<div class="bar"><span class="bar__name">%s</span><span class="bar__track">'
        '<span class="bar__fill" style="width:%.1f%%;background:%s"></span></span>'
        '<span class="bar__val num">%d</span></div>'
        % (esc(n), pts / 186 * 100, esc(c), pts) for n, c, _, _, pts, _ in PLAYERS)
    abars = "".join(
        '<div class="bar"><span class="bar__name">%s</span><span class="bar__track">'
        '<span class="bar__fill" style="width:%.1f%%;background:%s"></span></span>'
        '<span class="bar__val num">%d%%</span></div>'
        % (esc(n), cor / GAMES * 100, esc(c), round(cor / GAMES * 100))
        for n, c, _, _, _, cor in PLAYERS)
    body = (
        screen_head("Season", "Standings", "Ties stand. Two people can share a week.")
        + standing_rows(PLAYERS)
        + '<div class="dupe">points, again</div>'
        + '<div class="screen"><h3 class="h2">Points</h3>'
          '<p class="sub">Total confidence points banked on correct picks.</p></div>'
        + '<div class="bars">%s</div>' % bars
        + '<div class="dupe">the same percentage, again</div>'
        + '<div class="screen"><h3 class="h2">Accuracy</h3>'
          '<p class="sub">Share of picks that came in.</p></div>'
        + '<div class="bars">%s</div>' % abars)
    return phone("Today", body, tab="week",
                 note="Every number on this screen appears twice, and after one week the "
                      "season totals and the week totals are the same four numbers, so "
                      "it reads as three copies of one table.")


# ------------------------------------------------------------------------------ the page

CSS = """
:root{
  --ground:#eceff3; --panel:#ffffff; --panel-2:#f5f7f9; --edge:#d8dfe6;
  --ink:#131a22; --ink-2:#48535e; --ink-3:#5c6873; --mark:#2f6fed; --warn:#b0560f;
}
:root:not([data-theme="light"]){ }
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#11161d; --panel:#1a212a; --panel-2:#202832; --edge:#2c3540;
    --ink:#eef2f6; --ink-2:#b6c1cc; --ink-3:#8c99a6; --mark:#6a9bf5; --warn:#e2934a;
  }
}
:root[data-theme="dark"]{
  --ground:#11161d; --panel:#1a212a; --panel-2:#202832; --edge:#2c3540;
  --ink:#eef2f6; --ink-2:#b6c1cc; --ink-3:#8c99a6; --mark:#6a9bf5; --warn:#e2934a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1300px;margin:0 auto;padding:44px 22px 80px}
h1,h2,h3{font-family:'Archivo','Helvetica Neue',Helvetica,Arial,sans-serif;
  letter-spacing:-0.025em;margin:0;text-wrap:balance}
.doc__eyebrow{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--mark);margin:0 0 10px}
.doc__title{font-size:40px;font-weight:700;line-height:1.08}
.doc__sub{color:var(--ink-2);max-width:64ch;margin:14px 0 0;font-size:16.5px}
section{margin-top:56px}
.sec__h{font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);padding-bottom:9px;border-bottom:1px solid var(--edge);margin-bottom:22px}
.sec__lede{color:var(--ink-2);max-width:66ch;margin:0 0 26px}
.row{display:flex;flex-wrap:wrap;gap:30px;align-items:flex-start}
.opt{margin:0;width:392px;flex:0 0 auto}
.opt__cap{font-family:'Archivo',sans-serif;font-weight:700;font-size:16px;
  margin-bottom:12px;color:var(--ink)}
.opt__note{color:var(--ink-2);font-size:13.5px;line-height:1.55;margin:14px 2px 0}
.callout{background:var(--panel);border:1px solid var(--edge);border-left:3px solid var(--mark);
  border-radius:0 8px 8px 0;padding:16px 18px;margin:0 0 26px;max-width:70ch}
.callout p{margin:0;color:var(--ink-2);font-size:14.5px}
.callout b{color:var(--ink)}
.rec{background:var(--panel);border:1px solid var(--edge);border-radius:10px;padding:22px 24px;
  max-width:74ch}
.rec h3{font-size:19px;margin-bottom:10px}
.rec p{margin:0 0 12px;color:var(--ink-2)}
.rec p:last-child{margin-bottom:0}
.rec b{color:var(--ink)}
.struct{display:flex;flex-wrap:wrap;gap:18px;margin-bottom:26px}
.struct__o{background:var(--panel);border:1px solid var(--edge);border-radius:10px;
  padding:16px 18px;flex:1 1 300px}
.struct__o h4{margin:0 0 6px;font-size:15px;font-family:'Archivo',sans-serif}
.struct__o p{margin:0;font-size:13.5px;color:var(--ink-2)}
.struct__bar{display:flex;gap:5px;margin:12px 0 0}
.struct__bar span{flex:1;text-align:center;font-size:10.5px;font-weight:600;padding:6px 2px;
  border-radius:5px;background:var(--panel-2);color:var(--ink-3);border:1px solid var(--edge)}
.struct__bar span.on{background:var(--mark);color:#fff;border-color:transparent}

/* ---------------------------------------------------------------- the phone: Slate
   Pinned light. The app has no dark theme; rendering one here would be a lie. */
.phone{
  --s-700:#28313d; --s-900:#10151c;
  --c-000:#fff; --c-050:#f8fafb; --c-100:#f3f6f8; --c-150:#eef2f6; --c-200:#e7ecf1;
  --c-300:#c9d2dc; --c-500:#5c6873; --c-700:#48535e; --c-900:#131a22;
  --b-600:#2f6fed; --b-700:#1f56c4; --b-400:#6a9bf5; --b-100:#eaf1fe;
  --gr-600:#177541; --gr-100:#e4f3ea; --rd-600:#c33c2c; --rd-100:#fbeae7;
  --field:var(--s-700); --on-field:#f2f6fa; --on-field-2:#97a5b3;
  --page:var(--c-100); --card:var(--c-050); --surface:var(--c-000); --sunk:var(--c-150);
  --well:var(--c-200); --line:#dde4eb;
  --ink:var(--c-900); --ink-2:var(--c-700); --ink-3:var(--c-500);
  --accent:var(--b-600); --accent-deep:var(--b-700); --accent-bright:var(--b-400);
  --accent-wash:var(--b-100); --good:var(--gr-600); --good-wash:var(--gr-100);
  --bad:var(--rd-600); --bad-wash:var(--rd-100);
  --display:'Archivo','Helvetica Neue',Helvetica,Arial,sans-serif;
  --r-sm:7px; --r-md:8px; --r-lg:10px; --r-pill:999px;
  --sh-1:0 1px 1px rgba(19,26,34,.04), 0 1px 3px rgba(19,26,34,.05);
  width:390px;height:760px;display:flex;flex-direction:column;overflow:hidden;
  background:var(--page);color:var(--ink);border-radius:24px;
  border:1px solid var(--c-300);box-shadow:0 10px 20px rgba(19,26,34,.12),0 32px 64px rgba(19,26,34,.14);
  font-size:15px;line-height:1.5;color-scheme:light}
.phone__body{flex:1;overflow:hidden;padding-bottom:8px}
.phone .apphdr{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:14px 16px 12px;background:var(--field);color:var(--on-field)}
.phone .apphdr__title{font-family:var(--display);font-weight:700;font-size:19px;
  letter-spacing:-.02em;color:var(--on-field)}
.phone .apphdr__week{display:block;font-size:11px;font-weight:600;letter-spacing:.08em;
  text-transform:uppercase;color:var(--on-field-2);margin-top:1px}
.phone .apphdr__me{display:inline-flex;align-items:center;gap:8px;padding:5px 12px 5px 6px;
  min-height:36px;border-radius:var(--r-pill);background:rgba(255,255,255,.12);
  color:var(--on-field);font-size:13px;font-weight:600}
.phone .avatar{display:grid;place-items:center;border-radius:50%;color:#fff;
  font-family:var(--display);font-weight:700;flex:none;line-height:1;overflow:hidden}
.phone .avatar--team img{display:block}
.phone .tabbar{display:grid;grid-template-columns:repeat(4,1fr);background:var(--field);
  padding:9px 0 12px}
.phone .tab{text-align:center;font-size:10.5px;font-weight:700;letter-spacing:.04em;
  color:var(--on-field-2)}
.phone .tab.is-on{color:var(--on-field)}
.phone .screen{padding:16px 14px 4px}
.phone .h1{font-family:var(--display);font-weight:700;font-size:25px;letter-spacing:-.025em;
  margin:0}
.phone .h2{font-family:var(--display);font-weight:700;font-size:19px;letter-spacing:-.02em;
  margin:0}
.phone .eyebrow{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  color:var(--accent-deep);margin:0 0 5px}
.phone .sub{color:var(--ink-3);font-size:13.5px;line-height:1.5;margin:5px 0 0}
.phone .num{font-variant-numeric:tabular-nums}
.phone .stand{padding:0 12px;display:grid;gap:8px}
.phone .srow{display:flex;align-items:center;gap:11px;padding:12px 13px;
  border-radius:var(--r-lg);background:var(--card);border:1px solid var(--line);
  box-shadow:var(--sh-1)}
.phone .srow.is-leader{border-color:var(--accent-bright);
  background:linear-gradient(180deg,var(--accent-wash),var(--card) 62%)}
.phone .srow__pos{font-family:var(--display);font-size:15px;font-weight:700;
  color:var(--ink-3);min-width:20px}
.phone .srow.is-leader .srow__pos{color:var(--accent-deep)}
.phone .srow__body{flex:1;min-width:0}
.phone .srow__name{display:block;font-family:var(--display);font-size:16px;font-weight:700}
.phone .srow__meta{display:block;font-size:11.5px;color:var(--ink-3);margin-top:1px}
.phone .srow__pts{display:block;font-family:var(--display);font-size:25px;font-weight:700;
  color:var(--field);line-height:1;text-align:right}
.phone .srow__ptslabel{display:block;font-size:9.5px;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-3);text-align:right;margin-top:3px}
.phone .bars{padding:2px 14px 0;display:grid;gap:11px}
.phone .bar{display:grid;grid-template-columns:62px 1fr 38px;align-items:center;gap:9px;
  font-size:12.5px}
.phone .bar__name{font-weight:700}
.phone .bar__track{display:block;height:10px;border-radius:var(--r-pill);
  background:var(--well);overflow:hidden}
.phone .bar__fill{display:block;height:100%;border-radius:var(--r-pill)}
.phone .bar__val{text-align:right;font-weight:700;color:var(--ink-2)}

/* the recap block, option A */
.phone .recap{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:15px 16px;box-shadow:var(--sh-1)}
.phone .recap__lede{margin:0 0 14px;font-size:14.5px;line-height:1.55;color:var(--ink-2)}
.phone .recap__lede b{color:var(--ink)}
.phone .beat{padding-top:12px;border-top:1px solid var(--line);margin-top:12px}
.phone .beat:first-of-type{border-top:0;margin-top:0;padding-top:0}
.phone .beat__h{margin:0 0 3px;font-family:var(--display);font-weight:700;font-size:14px;
  letter-spacing:-.01em}
.phone .beat__b{margin:0;font-size:13px;line-height:1.5;color:var(--ink-3)}

/* stat tiles, option B and the season screen */
.phone .tiles{padding:0 12px;display:grid;grid-template-columns:1fr 1fr;gap:8px}
.phone .tile{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:11px 12px;box-shadow:var(--sh-1)}
.phone .tile__k{margin:0;font-size:9.5px;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-3)}
.phone .tile__v{margin:4px 0 1px;font-family:var(--display);font-weight:700;font-size:26px;
  line-height:1;color:var(--field)}
.phone .tile__v span{font-family:'Inter',sans-serif;font-size:11px;font-weight:700;
  color:var(--ink-3);margin-left:4px}
.phone .tile__s{margin:0;font-size:11.5px;color:var(--ink-3)}
.phone .linkrow{width:100%;display:flex;align-items:center;justify-content:space-between;
  padding:13px 14px;border-radius:var(--r-lg);border:1px solid var(--line);
  background:var(--card);font:inherit;font-size:14px;font-weight:700;color:var(--accent-deep);
  box-shadow:var(--sh-1)}

/* timeline, option C */
.phone .tl{padding:4px 14px 0;display:grid;gap:0}
.phone .tl__row{display:grid;grid-template-columns:30px 14px 1fr 34px;align-items:start;
  gap:8px;padding:11px 0;border-bottom:1px solid var(--line)}
.phone .tl__day{font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-3);padding-top:2px}
.phone .tl__dot{width:9px;height:9px;border-radius:50%;margin-top:5px;background:var(--well);
  box-shadow:0 0 0 3px var(--page)}
.phone .tl__dot--up{background:var(--good)}
.phone .tl__dot--down{background:var(--bad)}
.phone .tl__body{min-width:0}
.phone .tl__game{display:block;font-family:var(--display);font-weight:700;font-size:13.5px}
.phone .tl__what{display:block;font-size:12px;color:var(--ink-2);margin-top:1px}
.phone .tl__why{display:block;font-size:11.5px;color:var(--ink-3);margin-top:2px}
.phone .tl__d{font-family:var(--display);font-weight:700;font-size:15px;text-align:right;
  color:var(--ink-3)}
.phone .tl__d--up{color:var(--good)}
.phone .tl__d--down{color:var(--bad)}

/* week-by-week strip, season screen */
.phone .wks{padding:0 12px;display:grid;gap:6px}
.phone .wk{display:flex;align-items:center;gap:10px;padding:11px 13px;
  border-radius:var(--r-md);background:var(--sunk);border:1px solid transparent}
.phone .wk.is-done{background:var(--card);border-color:var(--line)}
.phone .wk__n{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-3);width:56px}
.phone .wk__w{flex:1;font-family:var(--display);font-weight:700;font-size:14.5px}
.phone .wk__p{font-weight:700;color:var(--ink-2);font-size:13.5px}

/* the annotation on the "today" phone */
.dupe{margin:14px 12px 2px;padding:5px 10px;border-radius:var(--r-sm);
  background:var(--bad-wash);color:var(--bad);font-size:10.5px;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;display:inline-block}

@media (max-width:900px){ .doc__title{font-size:31px} .wrap{padding:30px 16px 60px} }
@media (prefers-reduced-motion:reduce){ *{animation:none!important;transition:none!important} }
"""


def build() -> str:
    return """<title>Pick'em Standings Redesign</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Inter:wght@400;600;700&display=swap">
<style>%s</style>

<div class="wrap">
  <p class="doc__eyebrow">Motley Pick'em &middot; design options</p>
  <h1 class="doc__title">Splitting Standings, and writing up the week</h1>
  <p class="doc__sub">Three takes on the new week screen, plus the season tab that comes
  out of it. Every number below is real Week 1 output, so you are reading the actual
  recap the app would have written on Monday morning.</p>

  <section>
    <h2 class="sec__h">What is wrong with it now</h2>
    <div class="callout"><p>The screen prints the same two numbers three times: once in
    the table, once as a points bar, once as an accuracy bar. It is also season-only, so
    after one week the &ldquo;season&rdquo; totals <b>are</b> the week totals. That is
    why it reads as redundant. It is.</p></div>
    <div class="row">%s</div>
  </section>

  <section>
    <h2 class="sec__h">Where the two screens live</h2>
    <p class="sec__lede">You asked for a season tab and a week-only Standings. That is one
    more tab in the bar. Two ways to spend it.</p>
    <div class="struct">
      <div class="struct__o">
        <h4>Two tabs &mdash; recommended</h4>
        <p>Week and Season each get a slot. One tap to either. Admins end up with five
        tabs, which is the practical ceiling on a phone but does fit.</p>
        <div class="struct__bar"><span>Board</span><span>Picks</span><span class="on">Week</span><span>Season</span><span>Setup</span></div>
      </div>
      <div class="struct__o">
        <h4>One tab, segmented toggle</h4>
        <p>Standings keeps its slot and carries a This&nbsp;week / Season switch under the
        title. Bar stays as it is, but the season view is always one extra tap away and
        toggles are easy to miss.</p>
        <div class="struct__bar"><span>Board</span><span>Picks</span><span class="on">Standings</span><span>Setup</span></div>
      </div>
    </div>
  </section>

  <section>
    <h2 class="sec__h">The week screen, three ways</h2>
    <p class="sec__lede">All three show the recap only once every game in the week is
    final. Before that the screen shows the live table alone, because a half-written story
    about a week still in progress would give away picks that have not locked.</p>
    <div class="row">%s%s%s</div>
  </section>

  <section>
    <h2 class="sec__h">The season tab</h2>
    <p class="sec__lede">Same in all three. This is where the cumulative totals go once
    Standings stops carrying them.</p>
    <div class="row">%s</div>
  </section>

  <section>
    <h2 class="sec__h">The recommendation</h2>
    <div class="rec">
      <h3>Two tabs, and option A</h3>
      <p>You quoted the prose back at me, so the prose should be the screen rather than
      something behind a tap. <b>A</b> gives you that and still puts the table one short
      scroll down.</p>
      <p>If you want it to survive a boring week, take <b>A with B&rsquo;s four tiles</b>
      dropped in under the table. The tiles always have something to say; the write-up is
      better when the week actually had a story. That combination is maybe twenty extra
      lines over A on its own.</p>
      <p><b>The one to avoid</b> is C as the only option. A timeline is excellent when the
      top two finish seven points apart, as they just did, and says almost nothing when
      somebody wins by forty. It is a good third section, not a good main screen.</p>
      <p>Worth knowing either way: the recap is computed in the browser from picks and
      results, the same way the board already derives scores. No API, no cost, nothing new
      to run, and it works for Week&nbsp;7 without anyone writing anything.</p>
    </div>
  </section>
</div>
""" % (CSS, today_screen(), option_a(), option_b(), option_c(), season_screen())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "recap-board.html"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote %s (%.0f KB)" % (a.out, os.path.getsize(a.out) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
