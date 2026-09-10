"""Render five ways to sit the Week tab's scoreboard inside a light app.

The scorebug shipped to the Week tab on 2026-09-10 and Grant's note was immediate: every
other thing on that screen is light, so one dark slab reads as a visitor. On the Board it
works, because twenty white game cards underneath make it a graphic laid over a field.
On the Week tab it is followed by light content and has nothing to be laid over.

Real Week 1 final throughout: Grant 186 (16-4), James 179 (16-4), Parker 164 (12-8),
Nicole 147 (10-10), with the real capture percentages under each sample so the light
content it has to live beside is the real light content.

    python scripts/build_weekskin_board.py
"""
from __future__ import annotations

import base64
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAMS = {t["id"]: t for t in json.load(
    open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}

# name, colour, team, points, correct, wrong, captured%
FINAL = [
    ("Grant", "#B85C1F", "2751", 186, 16, 4, 93),
    ("James", "#1F6F4A", "61", 179, 16, 4, 90),
    ("Parker", "#2E5C8A", "338", 164, 12, 8, 94),
    ("Nicole", "#8A2E4F", None, 147, 10, 10, 95),
]
TOTAL = 210
LOGO = {}


def uri(tid, px=52):
    from PIL import Image
    t = TEAMS.get(str(tid)) or {}
    nm = "%s-dark.png" % tid if t.get("cut") == "dark" else "%s.png" % tid
    im = Image.open(os.path.join(ROOT, "static", "logos", nm)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def mark(team, colour, name, size=24, cls="bugrow__mark"):
    if not team:
        return ('<span class="avatar %s" style="width:%dpx;height:%dpx;background:%s;'
                'font-size:%.1fpx">%s</span>' % (cls, size, size, colour, size * .42, name[0]))
    if team not in LOGO:
        LOGO[team] = uri(team)
    t = TEAMS[team]
    n = round(size * .72)
    return ('<span class="avatar avatar--team %s" style="width:%dpx;height:%dpx;'
            'background:%s"><img src="%s" width="%d" height="%d" alt=""></span>'
            % (cls, size, size, t["bg"], LOGO[team], n, n))


def block(team, colour):
    return (TEAMS.get(str(team), {}).get("alt") or colour) if team else colour


def rows(kind):
    best = FINAL[0][3]
    out = []
    for i, (name, colour, team, pts, w, l, _cap) in enumerate(FINAL):
        gap = best - pts
        lead = " is-leader" if gap == 0 else ""
        you = '<span class="%s__you">YOU</span>' % kind if name == "Grant" else ""
        crown = ('<span class="wkrow__crown">Week won</span>'
                 if (kind == "wkrow" and gap == 0) else "")
        rule = ('<span class="bugrule"><i style="width:%.1f%%;background:%s"></i></span>'
                % (100 * pts / TOTAL, colour)) if kind == "bugrow" else ""
        out.append(
            '<div class="%s%s"><span class="%s__block" style="background:%s">'
            '<span class="%s__seed num">%d</span>%s</span>'
            '<span class="%s__name">%s%s</span>'
            '<span class="%s__rec num">%d-%d</span>'
            '<span class="%s__pts num">%d</span>'
            '<span class="%s__gap num">%s</span>%s%s</div>'
            % (kind, lead, kind, block(team, colour), kind, i + 1,
               mark(team, colour, name, 24, kind + "__mark"),
               kind, name.upper(), you, kind, w, l, kind, pts, kind,
               "&mdash;" if gap == 0 else "-%d" % gap, rule, crown))
    return "".join(out)


HDR = ('<div class="apphdr"><span class="apphdr__ttl">Motley Pick\'em</span>'
       '<span class="apphdr__wk">Wk 1</span></div>'
       '<div class="wknav"><span class="wknav__arrow">&lsaquo;</span>'
       '<span class="wknav__mid"><b>Week 1</b><i>final</i></span>'
       '<span class="wknav__arrow">&rsaquo;</span></div>'
       '<div class="screen"><p class="eyebrow">Final</p>'
       '<h1 class="h1">Grant takes it by 7</h1></div>')

CTX = ('<div class="ctx"><h3>Ranking</h3><p>Points banked against the most that ranking '
       'could have been worth.</p></div><div class="bars">'
       + "".join('<div class="bar"><span class="bar__name">%s</span>'
                 '<span class="bar__track"><span class="bar__fill" '
                 'style="width:%d%%;background:%s"></span></span>'
                 '<span class="bar__val num">%d%%</span></div>'
                 % (n, c, col, c) for n, col, _t, _p, _w, _l, c
                 in sorted(FINAL, key=lambda r: -r[6])) + '</div>')


def bug_card(foot="Out of 210. You take it by 7."):
    return ('<div class="bug"><div class="bug__top">'
            '<span class="bug__wk">Week 1 &middot; Final</span>'
            '<span class="bug__of num">20 of 20</span></div>%s'
            '<p class="bug__foot">%s</p></div>' % (rows("bugrow"), foot))


def card_list():
    return ('<div class="wkrows">%s</div>'
            '<p class="wkcap">Out of 210. You take it by 7.</p>' % rows("wkrow"))


def phone(cls, body):
    return '<div class="ph %s">%s%s%s</div>' % (cls, HDR, body, CTX)


OPTIONS = [
    ("now", "Today", "shipped", bug_card,
     "What is live right now. It works on the Board because twenty white game cards "
     "underneath make it a graphic laid over a field. Here it is followed by light "
     "content and has nothing to be laid over, so it reads as a slab that wandered in "
     "from another app."),
    ("wk1", "W1 &middot; Light bug", "same bones, app chrome", bug_card,
     "Every structural thing that makes it a scoreboard survives: the colour block, the "
     "seed, condensed caps, the record, the big tabular score, the progress rule. Only "
     "the chrome flips. <b>The most obviously part of the app</b>, and the one change it "
     "forces is the leader colour: gold is illegible on a light card, so first place "
     "takes the app's blue."),
    ("wk2", "W2 &middot; Dark head", "the band stays a graphic", bug_card,
     "The strip that says which week and how far through stays a broadcast band; the "
     "people underneath are app. <b>Keeps a piece of the bug rather than all or none</b>, "
     "and the dark is doing a job, labelling the block, instead of just being a colour. "
     "It is also the only option that still looks like the Board at a glance."),
    ("wk3", "W3 &middot; Commit to it", "make the page agree", bug_card,
     "The bug does not move at all. Instead every section head below it becomes the same "
     "dark band, so the dark is a device that recurs down the screen rather than one slab. "
     "<b>The only option that keeps gold and the full broadcast look</b>, at the cost of "
     "changing four other blocks on the screen to justify one."),
    ("wk4", "W4 &middot; No frame", "cards, keeping the bones", card_list,
     "The bug shape is what made it a visitor, so the bug shape goes. Four light cards "
     "the same shape as everything else on the screen, keeping the colour block, the "
     "condensed caps and the big score. <b>The most native and the least like "
     "television</b>, and the leader gets the app's existing tinted-card treatment."),
    ("wk5", "W5 &middot; Winner is the graphic", "dark, but earned", card_list,
     "Same four cards, except whoever took the week gets the broadcast treatment: dark, "
     "taller, gold score, a WEEK WON tag. <b>The dark stops being decoration and becomes "
     "the prize.</b> Best on a settled week and worth checking mid-week, when the leader "
     "is provisional and the row will keep moving."),
]


def figure(cls, name, kind, body, note):
    return ('<figure class="opt"><figcaption class="opt__cap">%s</figcaption>'
            '<p class="opt__kind">%s</p>%s<p class="opt__note">%s</p></figure>'
            % (name, kind, phone(cls, body()), note))


HEADER = """<title>The Week Scoreboard, Five Ways</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 10 September 2026</p>
<h1 class="doc__title">The week scoreboard, five ways</h1>
<p class="doc__sub">The scorebug shipped to the Week tab and everything around it is
light. Five ways to fix that, each shown with the Ranking block the real screen puts
underneath, because the mismatch is the whole point and you cannot judge it on the block
alone.</p>

<section>
  <h2 class="sec__h">Why it looks wrong here and not on the Board</h2>
  <div class="callout">
    <p><b>A scorebug is a graphic laid over something.</b> On the Board there are twenty
    white game cards under it, so it reads exactly as it does on television: dark chrome
    over a bright picture. On the Week tab it is followed by Ranking, Your week, Upsets
    and the numbers, all light, and there is nothing for it to be laid over. Same
    component, and the context is doing the opposite job.</p>
    <p><b>Gold is the thing that will not travel.</b> The leader's score is
    <span class="mono">#ffd25a</span>, which measures 10.8:1 on the bug's near-black and
    about 1.5:1 on a light card. Any option that lightens the rows has to give first place
    a different colour, and the app's blue is the only one already in the palette that is
    not already spoken for by right, wrong or live.</p>
    <p><b>There is a third answer nobody asks for.</b> W3 does not lighten anything. It
    makes the rest of the screen darker instead, so the bug stops being an exception. It
    is the most work and the only one that keeps the look you picked intact.</p>
  </div>
</section>

<section>
  <h2 class="sec__h">The five, plus what is live now</h2>
  <p class="sec__lede">Real Week&nbsp;1 final: you 186 on 16-4, James 179 on the same
  record, Parker 164, Nicole 147.</p>
  <div class="row">__OPTS__</div>
</section>

<section>
  <h2 class="sec__h">Recommendation</h2>
  <div class="rec">
    <h3>W2, with W1 if you want it fully settled</h3>
    <p><b>W2 is the one I would build.</b> It keeps the part of the bug that is actually
    carrying information, the band that says Week 1 and 20 of 20, as a broadcast graphic,
    and lets the four people underneath be app. That is a smaller and more defensible
    claim than either extreme: the dark is labelling something rather than decorating.
    It also still reads as a relative of the Board at a glance, which matters when the two
    screens show the same four names.</p>
    <p><b>W1 if you would rather it just be an app component.</b> Nothing structural is
    lost and it will never look out of place. It is also the least exciting of the five,
    and after this much work on the scorebug that is worth saying out loud.</p>
    <p><b>W5 is the one I would actually enjoy.</b> Making the winner the only dark thing
    on the screen turns the chrome into the prize, and on a settled week it is genuinely
    good. Check it mid-week before committing: the leader is provisional then, and a row
    that grows and darkens as the lead changes hands may be more movement than you want.</p>
    <p><b>W3 only if you want the whole app to go this way eventually.</b> Changing four
    other blocks to justify one is the wrong trade on its own, but it is the right first
    step if the dark theme is where you are heading anyway.</p>
    <p><b>W4 is the safe floor.</b> If none of the others feel right, this is the screen
    with the scoreboard idea intact and none of the friction.</p>
    <p class="mono" style="margin-top:14px;color:var(--ink-3)">All five are the same
    markup. W1, W2 and W3 are CSS only against the shipped component; W4 and W5 need a
    second row shape in WeekScore.jsx, behind the same prop the record column already
    uses.</p>
  </div>
</section>
</div>
"""


def main():
    css = open(os.path.join(ROOT, "scripts", "weekskin_board.css"), encoding="utf-8").read()
    doc = (HEADER.replace("__CSS__", css)
           + BODY.replace("__OPTS__", "".join(figure(*o) for o in OPTIONS)))
    out = os.path.join(ROOT, "outputs", "weekskin-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
