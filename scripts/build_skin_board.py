"""Render the options board for taking the scorebug language across the whole app.

Grant asked on 2026-09-10, after shipping the week scorebug, what the whole app would
look like with an ESPN or CBS feel. Four directions, each rendered as the Board screen at
372px against real Week 1 data: the same header, the same scorebug, the same two game
cards, the same tab bar. Only the skin changes.

Every skin is a set of token overrides on `.ph` plus whatever the token layer genuinely
cannot express. That split is deliberate and is printed under each option: it is the
honest answer to "how much work is this".

    python scripts/build_skin_board.py
"""
from __future__ import annotations

import base64
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEAMS = {t["id"]: t for t in json.load(
    open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}
FIX = json.load(open(os.path.join(ROOT, "outputs", "skin_fixture.json"), encoding="utf-8"))
GAME = {(g["away"], g["home"]): g for g in FIX}

PLAYERS = {
    "Grant": ("#B85C1F", "2751"), "James": ("#1F6F4A", "61"),
    "Parker": ("#2E5C8A", "338"), "Nicole": ("#8A2E4F", None),
}
# banked, live, rank, from the same replay the scorebug board used
STANDINGS = [("James", 124, 88, "1"), ("Grant", 117, 84, "2"),
             ("Parker", 115, 86, "3"), ("Nicole", 105, 87, "4")]
TOTAL = 210


def datauri(team_id, px=56):
    from PIL import Image

    t = TEAMS.get(str(team_id)) or {}
    name = "%s-dark.png" % team_id if t.get("cut") == "dark" else "%s.png" % team_id
    im = Image.open(os.path.join(ROOT, "static", "logos", name)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


LOGO = {}


def mark(team_id, size=21):
    if team_id not in LOGO:
        LOGO[team_id] = datauri(team_id)
    t = TEAMS.get(str(team_id)) or {}
    n = round(size * 0.72)
    return ('<span class="avatar avatar--team" style="width:%dpx;height:%dpx;background:%s">'
            '<img src="%s" width="%d" height="%d" alt=""></span>'
            % (size, size, t.get("bg", "#888"), LOGO[team_id], n, n))


def player_mark(name, size=21):
    color, team = PLAYERS[name]
    if not team:
        return ('<span class="avatar" style="width:%dpx;height:%dpx;background:%s;'
                'font-size:%.1fpx">%s</span>' % (size, size, color, size * 0.42, name[0]))
    return mark(team, size)


def lum(hexv):
    v = (hexv or "#888888").lstrip("#")
    c = [int(v[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def seed_colour(team_id):
    """A colour for the stripe down a card's edge, which is not the same question as a
    colour to put a logo ON.

    Colorado's disc is #eef1f5 and Georgia Tech's is #ffffff, because both marks are dark
    and need a light ground. As a seed on a white card those are nothing: the
    COLO @ GT card had no visible stripe at all in the first render of this board. So a
    seed takes the school's other colour whenever the disc's is too pale or too black to
    be a stripe."""
    t = TEAMS.get(str(team_id)) or {}
    bg = t.get("bg", "#888888")
    return t.get("alt", bg) if (lum(bg) > 0.62 or lum(bg) < 0.02) else bg


def block_colour(name):
    color, team = PLAYERS[name]
    return (TEAMS.get(str(team), {}).get("alt") or color) if team else color


def bug():
    best = max(s[1] for s in STANDINGS)
    rows = []
    for who, pts, live, rank in STANDINGS:
        gap = best - pts
        rows.append(
            '<div class="bugrow%s"><span class="bugrow__block" style="background:%s">'
            '<span class="bugrow__seed num">%s</span>'
            '<span class="bugrow__mark">%s</span></span>'
            '<span class="bugrow__name">%s</span>'
            '<span class="bugrow__pts num">%d</span>'
            '<span class="bugrow__gap num">%s</span>'
            '<span class="bugrule"><i class="is-live" style="width:%.1f%%;background:%s">'
            '</i><i style="width:%.1f%%;background:%s"></i></span></div>'
            % (" is-leader" if gap == 0 else "", block_colour(who), rank,
               player_mark(who, 22), who.upper() +
               ('<span class="bugrow__gap" style="margin-left:6px">YOU</span>'
                if who == "Grant" else ""),
               pts, "&mdash;" if gap == 0 else "-%d" % gap,
               100 * (pts + live) / TOTAL, PLAYERS[who][0],
               100 * pts / TOTAL, PLAYERS[who][0]))
    return ('<div class="bug"><div class="bug__top">'
            '<span class="bug__wk">Week 1 &middot; This week</span>'
            '<span class="bug__live"><i></i>2 live</span></div>%s'
            '<p class="bug__foot">Out of 210. You are 7 back, with 84 still to play for.'
            '</p></div>' % "".join(rows))


def game(key, chip, locked=False):
    g = GAME[key]
    away_won = g["winner"] == g["away"]
    seeds = 'style="--seed-a:%s;--seed-b:%s"' % (
        seed_colour(g["away_id"]), seed_colour(g["home_id"]))
    side = lambda ab, tid, sc, won: (
        '<span class="bgame__side%s">%s%s%s</span>'
        % ("" if (won or locked) else " is-loser", mark(tid), ab,
           "" if locked else '<span class="bgame__pts num">%d</span>' % sc))
    picks = []
    for p in g["picks"]:
        if locked:
            me = p["who"] == "Grant"
            picks.append(
                '<div class="bpick%s">%s<span class="bpick__who">%s</span>'
                '<span class="bpick__team">%s</span>'
                '<span class="bpick__pts num">%s</span></div>'
                % ("" if me else " bpick--hidden", player_mark(p["who"], 20), p["who"],
                   p["pick"] if me else "hidden", p["conf"] if me else "&ndash;"))
        else:
            picks.append(
                '<div class="bpick %s">%s<span class="bpick__who">%s</span>'
                '<span class="bpick__team">%s</span>'
                '<span class="bpick__pts num">%s%d</span></div>'
                % ("is-right" if p["right"] else "is-wrong", player_mark(p["who"], 20),
                   p["who"], p["pick"], "+" if p["right"] else "", p["conf"]))
    odds = ('<p class="bgame__odds num">%s -%s<span class="bgame__oddsep">&middot;</span>'
            'O/U %s</p>' % (g["fav"], ("%g" % g["spread"]), ("%g" % g["ou"])))
    return ('<div class="bgame%s" %s><div class="bgame__head"><div class="bgame__score">'
            '%s<span class="bgame__sep">@</span>%s</div>%s</div>%s'
            '<div class="bpicks">%s</div></div>'
            % (" bgame--locked" if locked else "", seeds,
               side(g["away"], g["away_id"], g["away_score"], away_won),
               side(g["home"], g["home_id"], g["home_score"], not away_won),
               chip, odds, "".join(picks)))


TABS = ('<div class="tabbar"><b><i></i>Picks</b><b class="is-on"><i></i>Board</b>'
        '<b><i></i>Week</b><b><i></i>Season</b></div>')


def phone(skin):
    return ('<div class="ph %s">'
            '<div class="apphdr"><span class="apphdr__ttl">Motley Pick\'em</span>'
            '<span class="apphdr__wk">Wk 1</span></div>'
            '<div class="screen"><p class="eyebrow">Week 1</p>'
            '<h1 class="h1">The Board</h1>'
            '<p class="sub">13 of 20 open. The rest unlock as they kick off.</p></div>'
            '%s%s%s%s</div>'
            % (skin, bug(),
               game(("CLEM", "LSU"), '<span class="chip"><span>Final</span></span>'),
               game(("COLO", "GT"), '<span class="chip"><span>Final</span></span>'),
               TABS))


SWATCH = {
    "sk-a": [("#0d1218", "page"), ("#171f29", "card"), ("#26313e", "well"),
             ("#6a9bf5", "accent"), ("#ffd25a", "lead"), ("#ff6b57", "live")],
    "sk-b": [("#f3f6f8", "page"), ("#f8fafb", "card"), ("#e7ecf1", "well"),
             ("#2f6fed", "accent"), ("#ffd25a", "lead"), ("#c33c2c", "live")],
    "sk-c": [("#f3f6f8", "page"), ("#f8fafb", "card"), ("#10151c", "strip"),
             ("#2f6fed", "accent"), ("#ffd25a", "lead"), ("#c33c2c", "live")],
    "sk-d": [("#0b0f14", "page"), ("#141b24", "card"), ("#232d39", "well"),
             ("#ffc12b", "accent"), ("#ffd25a", "lead"), ("#ff6b57", "live")],
}

NOTES = {
    "sk-a": ("A", "Broadcast Dark", "token swap only",
             "The bug's chrome taken across the page, the cards and the wells. Almost "
             "entirely a palette change. It is what ESPN's own app did, and it makes the "
             "scorebug stop being a visitor on a white screen. <b>The risk is daylight.</b> "
             "This is a phone app used at a tailgate, and a black screen outdoors is the "
             "one thing a light UI is plainly better at."),
    "sk-b": ("B", "Broadcast Bones", "structure, not colour",
             "The light ground stays; only the bones change. Condensed caps everywhere, "
             "4px corners instead of 10, a team-colour seed down every card, and the score "
             "at 21px. This is the CBS Sports web look rather than the broadcast graphic. "
             "<b>Safest of the four</b> and the only one that stays readable in full sun, "
             "at the cost of never quite looking like television."),
    "sk-c": ("C", "Dark Furniture", "the literal broadcast",
             "What a scorebug actually is: a dark graphic composited over a bright "
             "picture. Only the score strip goes dark, run to the card's edge so it reads "
             "as laid on top rather than painted in. The picks stay on white, where the "
             "green and red still mean something. <b>Most faithful to the reference</b>, "
             "and it costs one component's rules rather than a palette."),
    "sk-d": ("D", "Graphics Package", "the full package",
             "Dark, plus the wedge vocabulary: skewed colour seeds, a gold rule under the "
             "header and the tab bar, extra-condensed caps and a 24px score. This is "
             "GameDay rather than a scorebug. <b>Genuinely the most fun and the most "
             "likely to wear out.</b> The skew also fights every circular avatar in the "
             "app, which is why the seeds are the only skewed thing here."),
}
ORDER = ["sk-a", "sk-b", "sk-c", "sk-d"]


def figure(skin):
    tag, name, kind, note = NOTES[skin]
    sw = "".join('<i data-k="%s" style="background:%s"></i>' % (k, c)
                 for c, k in SWATCH[skin])
    return ('<figure class="opt"><figcaption class="opt__cap">%s <span>%s</span>'
            '</figcaption><p class="opt__kind">%s</p>'
            '<div class="specwrap"><div class="spec">%s</div></div>%s'
            '<p class="opt__cost" data-skin="%s"></p>'
            '<p class="opt__note">%s</p></figure>'
            % (tag, name, kind, sw, phone(skin), skin, note))


HEADER = """<title>A Scorebug Feel, App-Wide</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Inter:wght@400;600;700;800&display=swap">
<style>
__CSS__
</style>
"""

BODY = """<div class="wrap">
<p class="doc__eyebrow">Motley Pick'em &middot; 10 September 2026</p>
<h1 class="doc__title">A scorebug feel, app-wide</h1>
<p class="doc__sub">The week card is already a broadcast bug. These are four ways to take
that language to everything else. Same screen, same real Week&nbsp;1 games, same
components in all four: only the skin changes.</p>

<section>
  <h2 class="sec__h">What is actually on the table</h2>
  <div class="callout">
    <p><b>Two decisions, not one.</b> Light or dark is the loud one. The quiet one is
    whether the broadcast feel lives in the <i>palette</i> or in the <i>bones</i>:
    condensed caps, hard corners, colour seeds and oversized tabular numbers do most of
    the work, and they are independent of the ground colour. B is bones without palette,
    A is palette without much else, C and D are both.</p>
    <p><b>The one thing that does not survive going dark.</b> A correct pick is green and
    a wrong one is red on a pale wash, and that wash does real work on the Board: eighty
    pick rows a week get read at a glance by colour alone. On dark it drops to a dim tint,
    so A and D swap it for a colour bar down the row instead. Look at the
    CLEM&nbsp;@&nbsp;LSU card in each, where two of you were right and two were wrong.</p>
    <p><b>And the honest constraint: this is a phone used outdoors.</b> Your family opens
    it at a tailgate and on a couch. Dark is better on a couch and worse in the sun, and
    no amount of design fixes that.</p>
  </div>
</section>

<section>
  <h2 class="sec__h">The four</h2>
  <p class="sec__lede">Real Week&nbsp;1. CLEM&nbsp;@&nbsp;LSU is the card where you and
  James took LSU and Parker and Nicole took Clemson, so every skin has to show a right and
  a wrong pick side by side. COLO&nbsp;@&nbsp;GT is the one all four of you lost.</p>
  <div class="row">__OPTS__</div>
</section>

<section>
  <h2 class="sec__h">Recommendation</h2>
  <div class="rec">
    <h3>C, and B if you want none of the risk</h3>
    <p><b>C is the one I would build.</b> It is the only option that is the reference
    rather than an impression of it: a broadcast is a dark graphic over a bright picture,
    and C puts the dark strip exactly where television puts it, at the top of each game,
    with the human part underneath on white. It also keeps the green and red pick washes
    at full strength, which is the one thing the Board cannot afford to lose. And it is
    the cheapest of the four that changes anything real: one component's rules, no
    palette.</p>
    <p><b>B if you want the look without any argument.</b> Condensed caps, hard corners,
    seeds and big numbers get you most of the way, and the app stays readable in full sun.
    It will never make you say "that looks like TV", which may be fine.</p>
    <p><b>A is the real "ESPN app" answer and the biggest bet.</b> It is also the least
    work of the four, because it is almost purely tokens. It either delights everyone or
    gets you one text from your mum about not being able to see it outside. If you want
    it, ship it as a toggle rather than a replacement.</p>
    <p><b>D is worth seeing and I would not ship it.</b> The wedges look terrific for a
    week. They also fight every circular avatar in the app, the skew has to be undone on
    every child so the text stays upright, and extra-condensed caps at 12.5px start to
    close up on a phone.</p>
    <p class="mono" style="margin-top:16px;color:var(--ink-3)">Costs under each option are
    counted out of the board's own stylesheet at render time: how many tokens the skin
    redefines, and how many extra rules it needs beyond them.</p>
  </div>
</section>
</div>

<script>
/* Count each skin's real cost out of the stylesheet rather than asserting it in prose. */
const css = [...document.styleSheets].flatMap((s) => {
  try { return [...s.cssRules] } catch { return [] }
});
for (const p of document.querySelectorAll('.opt__cost')) {
  const sel = '.' + p.dataset.skin;
  let tokens = 0, rules = 0;
  for (const r of css) {
    if (!r.selectorText) continue;
    if (r.selectorText === sel) {
      tokens = [...r.style].filter((n) => n.startsWith('--')).length;
    } else if (r.selectorText.startsWith(sel + ' ')) {
      rules += 1;
    }
  }
  const ph = document.querySelector(sel);
  p.innerHTML = '<b>' + tokens + '</b> tokens redefined &middot; <b>' + rules +
    '</b> extra rules &middot; ' + Math.round(ph.getBoundingClientRect().height) + 'px tall';
}
</script>
"""


def main():
    css = open(os.path.join(ROOT, "scripts", "skin_board.css"), encoding="utf-8").read()
    doc = (HEADER.replace("__CSS__", css)
           + BODY.replace("__OPTS__", "".join(figure(s) for s in ORDER)))
    out = os.path.join(ROOT, "outputs", "skin-board.html")
    open(out, "w", encoding="utf-8").write(doc)
    print("wrote %s  %.1f KB" % (out, len(doc.encode()) / 1024))


if __name__ == "__main__":
    main()
