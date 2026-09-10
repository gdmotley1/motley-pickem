"""Render the feature options board: four features, three treatments each.

Grant asked on 2026-09-10 how else to make the app easier and what good features to add,
then asked to see them rather than read a list. Everything is drawn in the app as it
ships TODAY: light Slate, white cards, the scorebug at the top of the Board. Skin C was
chosen and never built, so nothing here assumes it.

Numbers are live, not invented. Week 2 is published with the first kickoff 24.8 hours out
and 0 of 80 picks submitted, which is what justifies the nudge. The head-to-head records
are the real Week 1 picks.

    python scripts/build_feature_board.py
"""
from __future__ import annotations

import base64
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAMS = {t["id"]: t for t in json.load(
    open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}

PLAYERS = {"Grant": ("#B85C1F", "2751"), "James": ("#1F6F4A", "61"),
           "Parker": ("#2E5C8A", "338"), "Nicole": ("#8A2E4F", None)}
LOGO = {}


def uri(tid, px=48):
    from PIL import Image
    t = TEAMS.get(str(tid)) or {}
    nm = "%s-dark.png" % tid if t.get("cut") == "dark" else "%s.png" % tid
    im = Image.open(os.path.join(ROOT, "static", "logos", nm)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def av(who, size=22):
    color, team = PLAYERS[who]
    if not team:
        return ('<span class="avatar" style="width:%dpx;height:%dpx;background:%s;'
                'font-size:%.1fpx">%s</span>' % (size, size, color, size * .42, who[0]))
    if team not in LOGO:
        LOGO[team] = uri(team)
    t = TEAMS[team]
    n = round(size * .72)
    return ('<span class="avatar avatar--team" style="width:%dpx;height:%dpx;background:%s">'
            '<img src="%s" width="%d" height="%d" alt=""></span>'
            % (size, size, t["bg"], LOGO[team], n, n))


def block(who):
    color, team = PLAYERS[who]
    return (TEAMS.get(str(team), {}).get("alt") or color) if team else color


HDR = ('<div class="apphdr"><span class="apphdr__ttl">Motley Pick\'em</span>'
       '<span class="apphdr__wk">Wk 2</span></div>')


def tabs(dot=False):
    d = '<em></em>' if dot else ''
    return ('<div class="tabbar"><b><i></i>Picks%s</b><b class="is-on"><i></i>Board</b>'
            '<b><i></i>Week</b><b><i></i>Season</b></div>' % d)


def screen(title, sub, eyebrow="Week 2"):
    return ('<div class="screen"><p class="eyebrow">%s</p><h1 class="h1">%s</h1>'
            '<p class="sub">%s</p></div>' % (eyebrow, title, sub))


# Real Week 1, replayed at 13 games kicked off with OKST@TLSA and ARST@MEM still on.
# `projected` assumes each live game ends the way it actually did, which is what
# "whoever is ahead right now holds on" means. The drama is real: Nicole is tied for the
# lead on 128 and gains nothing from either game, so she falls from first to last
# without her score changing at all.
# name, banked, still on the table, rank, projected
STAND = [("Parker", 128, 67, "1", 141), ("Nicole", 128, 63, "1", 128),
         ("James", 124, 69, "3", 134), ("Grant", 117, 78, "4", 130)]
TOTAL = 210


def bugrows(mode="plain"):
    best = max(s[1] for s in STAND)
    out = []
    for who, pts, live, rank, proj in STAND:
        gap = best - pts
        val = '<span class="bugrow__pts num">%d</span>' % pts
        if mode == "due":
            # Before the first kickoff nobody has a score, so the bug cannot show one.
            # The shipped Board hides the card entirely until a game locks; this mode is
            # what it would have to render instead if it carried the deadline.
            val = ('<span class="bugrow__pts num" style="color:var(--on-field-2);'
                   'opacity:.55">&mdash;</span>')
        if mode == "proj":
            val = ('<span class="bugrow__pts num proj">%d '
                   '<i>&rarr;</i><b class="num">%d</b></span>' % (pts, proj))
        if mode == "toggle":
            val = '<span class="bugrow__pts num" style="color:var(--lead)">%d</span>' % proj
        caret = ''
        if mode == "caret":
            caret = '<em style="left:%.1f%%"></em>' % (100 * proj / TOTAL)
        out.append(
            '<div class="bugrow%s"><span class="bugrow__block" style="background:%s">'
            '<span class="bugrow__seed num">%s</span>'
            '<span class="bugrow__mark">%s</span></span>'
            '<span class="bugrow__name">%s%s</span>%s'
            '<span class="bugrow__gap num">%s</span>'
            '<span class="bugrule"><i class="is-live" style="width:%.1f%%;background:%s">'
            '</i><i style="width:%.1f%%;background:%s"></i>%s</span></div>'
            % ("" if mode == "due" else (" is-leader" if gap == 0 else ""),
               block(who), rank, av(who, 22),
               who.upper(),
               '<span class="bugrow__you">YOU</span>' if who == "Grant" else "",
               val, "" if mode == "due" else ("&mdash;" if gap == 0 else "-%d" % gap),
               0 if mode == "due" else 100 * (pts + live) / TOTAL, PLAYERS[who][0],
               0 if mode == "due" else 100 * pts / TOTAL, PLAYERS[who][0], caret))
    return "".join(out)


def bug(top, foot, mode="plain"):
    return ('<div class="bug"><div class="bug__top">'
            '<span class="bug__wk">Week 1 &middot; This week</span>%s</div>%s'
            '<p class="bug__foot">%s</p></div>' % (top, bugrows(mode), foot))


LIVE_CHIP = '<span class="bug__live"><i></i>2 live</span>'


# ============================================================ A. THE NUDGE ===
A1 = (HDR + screen("The Board", "Nothing has kicked off yet. "
                   "<b style='color:var(--bad)'>First kickoff Fri 8:00 PM, 20 to pick.</b>")
      + '<div class="bgame"><div class="bgame__head"><div class="bgame__score">'
        '<span class="bgame__side">MIZ</span><span class="bgame__sep">@</span>'
        '<span class="bgame__side">KU</span></div>'
        '<span class="chip">Fri 8:00 PM</span></div></div>' + tabs(dot=True))

A2 = (HDR + screen("The Board", "Nothing has kicked off yet.")
      + '<div class="nudge"><span class="nudge__i">&#9201;</span>'
        '<span class="nudge__t"><span class="nudge__h">20 games to pick</span>'
        '<span class="nudge__s">First kickoff Friday 8:00 PM &middot; in 25 hours</span>'
        '</span><span class="nudge__b">Pick</span></div>'
      + '<div class="bgame" style="margin-top:11px"><div class="bgame__head">'
        '<div class="bgame__score"><span class="bgame__side">MIZ</span>'
        '<span class="bgame__sep">@</span><span class="bgame__side">KU</span></div>'
        '<span class="chip">Fri 8:00 PM</span></div></div>' + tabs())

A3 = (HDR + screen("The Board", "Nothing has kicked off yet.")
      + bug('<span class="bug__due">&#9201; Picks due Fri 8:00 PM</span>',
            "Nobody has scored yet. Points appear as games finish.", "due")
      + tabs(dot=True))

# ================================================== B. IF IT ENDS NOW ========
B1 = (HDR + screen("The Board", "13 of 20 open. 2 games on right now.")
      + bug(LIVE_CHIP,
            "Gold is where you land if the two live games end as they stand.", "proj")
      + tabs())

B2 = (HDR + screen("The Board", "13 of 20 open. 2 games on right now.")
      + bug('<span class="bugtog"><b>Now</b><b class="is-on">If it ends</b></span>',
            "Showing where everyone lands if the two live games finish as they stand.",
            "toggle")
      + tabs())

B3 = (HDR + screen("The Board", "13 of 20 open. 2 games on right now.")
      + bug(LIVE_CHIP,
            "If the two live games end as they stand you move up to 3rd, 11 back of "
            "Parker, and Nicole falls from first to last without losing a point.",
            "caret")
      + tabs())

# ============================================== C. RANKING MADE EASIER =======
RANK_ROWS = [("20", "ALA over WIS", "lock", False), ("19", "UGA over UAB", "", False),
             ("18", "TEX over UTEP", "", False), ("4", "COLO over GT", "", True),
             ("3", "TOL over MSU", "", False)]


def rlist(lifted_idx=None, pad=False):
    out = []
    for i, (n, t, s, lifted) in enumerate(RANK_ROWS):
        on = " is-lifted" if (lifted if lifted_idx is None else i == lifted_idx) else ""
        out.append('<div class="rrow%s"><span class="rrow__n num">%s</span>'
                   '<span class="rrow__t">%s</span>'
                   '<span class="rrow__s">%s</span></div>' % (on, "" if pad else n, t, s))
    return '<div class="rlist">%s</div>' % "".join(out)


C1 = (HDR + '<div class="screen"><h2 class="h2">Most sure at the top</h2>'
      '<p class="sub">COLO over GT is lifted. Drop it anywhere, or jump it.</p></div>'
      + '<div class="jump"><b>&uarr; Send to top</b><b>&darr; Send to bottom</b></div>'
      + rlist() + tabs())

C2 = (HDR + '<div class="screen"><h2 class="h2">COLO over GT</h2>'
      '<p class="sub">How sure are you? Tap a number. 17 of 20 already spent.</p></div>'
      + '<div class="pad">' + "".join(
          '<b class="%s">%d</b>' % (
              "is-next" if n == 4 else ("is-used" if n not in (1, 2, 3, 4) else ""), n)
          for n in range(20, 0, -1)) + '</div>'
      + rlist(pad=True) + tabs())

C3 = (HDR + '<div class="screen"><h2 class="h2">Sort them into three piles</h2>'
      '<p class="sub">Points are handed out inside each pile, top down.</p></div>'
      + '<div class="buck">'
        '<div class="buck__g"><div class="buck__h"><span class="buck__n">Locks</span>'
        '<span class="buck__c">6</span><span class="buck__p">20 &ndash; 15</span></div>'
        '<div class="buck__row"><span>ALA</span><span>UGA</span><span>TEX</span>'
        '<span>OSU</span><span>ORE</span><span>ND</span></div></div>'
        '<div class="buck__g is-over"><div class="buck__h">'
        '<span class="buck__n">Leans</span><span class="buck__c">9</span>'
        '<span class="buck__p">14 &ndash; 6</span></div>'
        '<div class="buck__row"><span>LSU</span><span>MSU</span><span>USC</span>'
        '<span>+6 more</span></div></div>'
        '<div class="buck__g"><div class="buck__h"><span class="buck__n">Coin flips</span>'
        '<span class="buck__c">5</span><span class="buck__p">5 &ndash; 1</span></div>'
        '<div class="buck__row"><span>COLO</span><span>TOL</span><span>+3 more</span>'
        '</div></div></div>' + tabs())

# ================================================== D. HEAD TO HEAD ==========
H2H = [("James", 1, 1), ("Parker", 5, 1), ("Nicole", 6, 0)]


def h2hrows():
    out = []
    for who, w, l in H2H:
        tot = max(w + l, 1)
        cls = "is-up" if w > l else ("is-down" if w < l else "")
        out.append('<div class="h2h__r">%s<span class="h2h__n">vs %s</span>'
                   '<span class="h2h__b"><i style="width:%.0f%%;background:var(--good)">'
                   '</i><i style="width:%.0f%%;background:var(--bad)"></i></span>'
                   '<span class="h2h__s %s num">%d-%d</span></div>'
                   % (av(who, 24), who, 100 * w / tot, 100 * l / tot, cls, w, l))
    return '<div class="h2h">%s</div>' % "".join(out)


D1 = (HDR + '<div class="screen"><p class="eyebrow">Season 2026</p>'
      '<h1 class="h1">Head to head</h1>'
      '<p class="sub">Games where exactly one of you called it right.</p></div>'
      + h2hrows() + tabs())

GRID = ["Grant", "James", "Parker", "Nicole"]
CELLS = {("Grant", "James"): (1, 1), ("Grant", "Parker"): (5, 1),
         ("Grant", "Nicole"): (6, 0), ("James", "Parker"): (4, 0),
         ("James", "Nicole"): (7, 1), ("Parker", "Nicole"): (6, 4)}


def gridtable():
    head = "".join('<th>%s</th>' % n[:3].upper() for n in GRID)
    body = []
    for a in GRID:
        tds = []
        for b in GRID:
            if a == b:
                tds.append('<td class="dash">&ndash;</td>'); continue
            w, l = CELLS.get((a, b)) or tuple(reversed(CELLS[(b, a)]))
            cls = "up" if w > l else ("down" if w < l else "")
            me = " me" if a == "Grant" else ""
            tds.append('<td class="%s"><span class="%s">%d-%d</span></td>' % (me, cls, w, l))
        body.append('<tr><th class="side">%s</th>%s</tr>' % (a[:3].upper(), "".join(tds)))
    return ('<div class="grid"><table><tr><th class="side"></th>%s</tr>%s</table></div>'
            % (head, "".join(body)))


D2 = (HDR + '<div class="screen"><p class="eyebrow">Season 2026</p>'
      '<h1 class="h1">Grant vs Nicole</h1>'
      '<p class="sub">Tapped from the standings.</p></div>'
      + '<div class="sheet"><div class="sheet__h">%s<span class="sheet__vs">You vs Nicole'
        '</span>%s</div><div class="sheet__big"><b style="color:var(--good)">6</b>'
        '<span>&ndash;</span><b style="color:var(--ink-3)">0</b></div>'
        '<p class="sheet__l">Games only you called<b>6</b></p>'
        '<p class="sheet__l">Games only she called<b>0</b></p>'
        '<p class="sheet__l">Both right<b>8</b></p>'
        '<p class="sheet__l">Both wrong<b>6</b></p>'
        '<p class="sheet__l">Points, week 1<b>186 to 147</b></p></div>'
        % (av("Grant", 26), av("Nicole", 26)) + tabs())

D3 = (HDR + '<div class="screen"><p class="eyebrow">Season 2026</p>'
      '<h1 class="h1">Head to head</h1>'
      '<p class="sub">Read across your row. Green means you are ahead.</p></div>'
      + gridtable() + tabs())


FEATURES = [
    ("A", "The nudge", "Nothing in the app has ever asked anyone to pick",
     "<b>Live right now, and this is the whole argument:</b> Week&nbsp;2 is published, the "
     "first kickoff is 24.8 hours away, and <b>0 of 80 picks are in</b>. The app has no "
     "badge, no deadline and no reminder. It also already contains an unused function "
     "called <span class='mono'>untilLabel</span> that returns “in 3h”, whose "
     "comment says it is for “the countdown chip”. The chip was never built.",
     [("A1", "Quiet", A1,
       "A red dot on Picks and one bold clause in the line that is already there. "
       "<b>No new furniture at all</b>, so it costs zero height and can never be in the "
       "way. It is also the easiest to scroll straight past."),
      ("A2", "Banner", A2,
       "A card above everything with the count, the time and a button straight into the "
       "pick flow. <b>Impossible to miss and the only one that is one tap from doing "
       "something.</b> Costs 48px at the top of the Board, and it has to be dismissible "
       "or it becomes wallpaper."),
      ("A3", "In the bug", A3,
       "The scorebug's top strip already has a slot that holds <span class='mono'>2 LIVE"
       "</span> during games. Before kickoff it holds the deadline instead, in gold. "
       "<b>One element doing two jobs, zero new space</b>, and it reuses the one piece of "
       "chrome everybody already looks at.")]),

    ("B", "If it ends now", "The one that makes Saturday worth watching",
     "The app polls ESPN every few minutes and <span class='mono'>liveWinner()</span> in "
     "espn.js already works out who is ahead. It just refuses to answer unless the game "
     "is final. <b>Loosening that single guard gives you a projected table that moves "
     "while you watch.</b> No backend, no new data, no new request. The numbers below "
     "are the real Week&nbsp;1 at the point OKST@TLSA and ARST@MEM were still on, and "
     "they make the case on their own: <b>Nicole is tied for the lead on 128 and has "
     "nothing riding on either game, so she falls from first to last without losing a "
     "single point.</b> Today the app cannot tell her that.",
     [("B1", "Arrow", B1,
       "Banked, then an arrow, then where you land if the live games end as they stand. "
       "<b>Both numbers at once</b>, which is the honest version: nothing pretends the "
       "projection has happened. Busiest of the three, and 19px plus 15px in one cell is "
       "a lot on a 372px phone."),
      ("B2", "Toggle", B2,
       "A <span class='mono'>NOW / IF IT ENDS</span> switch in the header swaps all four "
       "numbers at once. <b>Cleanest rows of the three and the least ambiguous</b>: you "
       "are always looking at exactly one thing. Costs a tap, and someone will leave it "
       "on the wrong setting and misread the week."),
      ("B3", "Caret", B3,
       "The rows do not change at all. A gold tick lands on each row's progress strip "
       "where that player would finish, and the footer says it in words. <b>Quietest, and "
       "the only one that survives a glance</b>: you see the ticks reorder without "
       "reading a single number.")]),

    ("C", "Ranking made easier", "Twenty games, ordered by tap-lift and tap-place",
     "This is the hardest thing anyone does in the app and it happens once a week. Today "
     "you lift a game and place it, which is fine near where it already sits and painful "
     "for a long move: getting game 20 to first place means scrolling the list while "
     "holding it. All three below keep the current flow and add a shortcut.",
     [("C1", "Send to top", C1,
       "While a game is lifted, two buttons appear. <b>Smallest possible change</b>, a "
       "handful of lines, and it fixes the one move that is genuinely awkward. It does "
       "nothing for the other eighteen games."),
      ("C2", "Number pad", C2,
       "Tap a game, tap its number. Spent values grey out, the next free one is "
       "highlighted. <b>Turns ordering into assigning</b>, which is how most people "
       "actually think about confidence points. It is a bigger rewrite and it loses the "
       "at-a-glance sense of the whole running order."),
      ("C3", "Three piles", C3,
       "Drop each game into Locks, Leans or Coin flips, and points are handed out inside "
       "each pile from the top down. <b>Twenty decisions become three</b>, which is by "
       "far the biggest reduction in work here. It also takes fine control away, and "
       "somebody will want to nudge one game inside a pile.")]),

    ("D", "Head to head", "The thing a family pool actually runs on",
     "Every number needed is already in <span class='mono'>picks</span> and the app "
     "cannot answer it. From real Week&nbsp;1: on games where exactly one of you called "
     "it right, <b>you beat Nicole 6-0 and Parker 5-1, and you and James were dead level "
     "at 1-1</b>. That is the table nobody can see.",
     [("D1", "A list", D1,
       "Three rows on the Season tab, one per opponent, with a bar showing the split. "
       "<b>Reads in a second and needs no interaction.</b> It is only ever your own row, "
       "so nobody can see how the others are doing against each other."),
      ("D2", "Tap a player", D2,
       "Tap anyone in the standings and get the full comparison: who called what, both "
       "right, both wrong, points. <b>The most detail and the most fun to actually read</b>, "
       "and it is the only one that gives a reason to tap a name. It is also a whole new "
       "screen rather than a block."),
      ("D3", "The grid", D3,
       "Everyone against everyone, your row tinted. <b>The one that starts arguments</b>, "
       "because James being 4-0 against Parker is right there. Sixteen cells at 11.5px is "
       "tight on a phone and it is the hardest of the three to read cold.")]),
]


def figure(tag, name, html, note):
    return ('<figure class="opt"><figcaption class="opt__cap">%s <span>%s</span>'
            '</figcaption><div class="ph">%s</div>'
            '<p class="opt__note">%s</p></figure>' % (tag, name, html, note))


def section(f):
    key, title, lede, why, opts = f
    return ('<section><p class="sec__k">Feature %s</p><h2 class="sec__h">%s</h2>'
            '<p class="sec__lede">%s</p><p class="sec__why">%s</p>'
            '<div class="row">%s</div></section>'
            % (key, title, lede, why,
               "".join(figure(t, n, h, note) for t, n, h, note in opts)))


HEADER = """<title>Four Features, Twelve Ways</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

TOP = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 10 September 2026</p>
<h1 class="doc__title">Four features, twelve ways</h1>
<p class="doc__sub">Everything is drawn in the app exactly as it ships today, with real
numbers. Pick one per feature, or none. Nothing here is built.</p>
__SECTIONS__
<section>
  <h2 class="sec__h">If you only do two</h2>
  <div class="rec">
    <h3>A3 and B3</h3>
    <p><b>A3, because it costs nothing.</b> The scorebug's top strip already holds a chip
    that says how many games are live. Before kickoff it holds the deadline instead. No
    new element, no height, and it reuses the one piece of chrome everybody already looks
    at. Pair it with the tab dot from A1, which is four lines and independent of which
    treatment you choose.</p>
    <p><b>B3, because it is the one people will talk about.</b> A gold tick sliding along
    four rows on a Saturday afternoon is the whole appeal of a pool, and it needs no
    backend at all: the data is already being polled and the function that works out who
    is winning already exists.</p>
    <p><b>Then D1 when you want it.</b> Head to head is the most fun thing on this page
    and the least urgent, because nothing is broken without it. D1 is an afternoon; D2 is
    a new screen.</p>
    <p><b>C is the honest one to defer.</b> The ranking flow is the hardest thing in the
    app but it is not broken, and all three treatments here are a rewrite of the screen
    that works. Worth doing when somebody complains, not before.</p>
    <p class="mono" style="margin-top:14px;color:var(--ink-3)">One thing I checked and
    would have got wrong: I had an auto-pick notice on this list, on the assumption people
    forget. Across all of Week&nbsp;1, <b>zero picks were auto-filled</b>. Everybody got
    their card in. It is worth building eventually and it is not a problem you have.</p>
  </div>
</section>
</div>
"""


def main():
    css = (open(os.path.join(ROOT, "scripts", "feature_board.css"), encoding="utf-8").read())
    doc = (HEADER.replace("__CSS__", css)
           + TOP.replace("__SECTIONS__", "".join(section(f) for f in FEATURES)))
    out = os.path.join(ROOT, "outputs", "feature-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
