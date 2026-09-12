"""Render the awards ballot: what goes on everyone's shelf, what goes in the Hall of fame.

Grant, 2026-09-12, choosing from the record book board: "I like D. Let's add that in for
everybody to have. And then let's also add in C, but make them different awards." Worst
pick "doesn't make sense. All it is is a number. It doesn't say what the pick was or if he
got it right or wrong." Then a verdict on each record, and: "let's brainstorm some new ones
as well as evaluate what we already have and see how meaningful it is."

So this is a ballot, not a mockup. Every record, old and new, is one row: what it means in
a sentence, what it would say about each of the four of them TODAY on the real season, an
honest take, and a Yes / No he can tap on his phone. Taps are saved to the artifact's db
(one document, ballot/grant) so they can be read back rather than retyped by voice.

Every preview was computed from the real season (Week 1 final, Week 2 one game in), with
week-level stats counting finished weeks only. The numbers are what made several ideas
fail: "Nailed your top five" was earned by three of four people in Week 1, "Only one who
got it wrong" would already name Nicole five times, and today's biggest upset called is a
1.5-point underdog.

    python scripts/build_awards_board.py
"""
from __future__ import annotations

import base64
import html
import io
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "awards-board.html")

NAMES = ["Grant", "James", "Parker", "Nicole"]
TEAM = {"Grant": "8", "James": "2655", "Parker": "338", "Nicole": "61"}

# What Grant already said, so the ballot opens with his answers and he only taps the rest.
SAID = "said"

# ---------------------------------------------------------------------- the ballot
# id, name, what it means, preview, my take, default
# A shelf preview is a value per person; an award preview is who has earned it.

SHELF = [
    ("best_week", "Most points in a week", "Your best week.",
     {"Grant": "186 · Week 1", "James": "179 · Week 1", "Parker": "164 · Week 1", "Nicole": "147 · Week 1"},
     "Keep.", SAID),
    ("best_record", "Best record in a week", "The most games you got right in one week.",
     {"Grant": "16-4 · Week 1", "James": "16-4 · Week 1", "Parker": "12-8 · Week 1", "Nicole": "10-10 · Week 1"},
     "Keep.", SAID),
    ("low_week", "Fewest points in a week", "Your worst week.",
     {"Grant": "186 · Week 1", "James": "179 · Week 1", "Parker": "164 · Week 1", "Nicole": "147 · Week 1"},
     "Keep. It matches your best week for everyone until a second week is final, which is "
     "tonight.", SAID),
    ("streak", "Longest winning streak", "The most picks in a row you got right, across weeks.",
     {"Grant": "8 in a row", "James": "10 in a row", "Parker": "4 in a row", "Nicole": "6 in a row"},
     "Keep.", SAID),
    ("worst_pick", "Worst pick", "The most points you put on a team that lost, and the game.",
     {"Grant": "8 on Georgia Tech. Lost to Colorado, 14-13",
      "James": "17 on Georgia Tech. Lost to Colorado, 14-13",
      "Parker": "10 on Georgia Tech. Lost to Colorado, 14-13",
      "Nicole": "15 on Oklahoma St. Lost to Tulsa, 24-10"},
     "Keep, written out like this. The number alone was meaningless.", SAID),
    ("my_upset", "Biggest upset you called", "The biggest underdog you picked that won.",
     {"Grant": "Nevada +1.5 over Western KY", "James": "none yet", "Parker": "none yet",
      "Nicole": "Nevada +1.5 over Western KY"},
     "Yes, but only counting real upsets. See the 7-point question in the Hall of fame. "
     "I read your message as wanting this on the shelf too; tap No if not.", SAID),
    ("weeks_won", "Weeks won", "How many weeks you finished on top. Ties count for both.",
     {"Grant": "1 of 1", "James": "0 of 1", "Parker": "0 of 1", "Nicole": "0 of 1"},
     "Keep. You liked it.", SAID),
    ("season_record", "Season record", "Every pick this season, right and wrong.",
     {"Grant": "16-5", "James": "17-4", "Parker": "13-8", "Nicole": "11-10"},
     "Yes. You did not mention it, and it is the one number the standings no longer show.", None),
    ("twenty", "Your 20-pointers", "How often the pick you were surest of each week won.",
     {"Grant": "1 of 1", "James": "1 of 1", "Parker": "1 of 1", "Nicole": "1 of 1"},
     "Yes. New. All four of you put your 20 on Georgia in Week 1; over a season this is the "
     "fairest test of confidence in a confidence pool.", None),
    ("blowout", "Biggest blowout (as it is now)", "The most points you won a week by.",
     {"Grant": "7 (won Week 1 by 7)", "James": "none", "Parker": "none", "Nicole": "none"},
     "Cut. You said you did not understand it, and a bare 7 cannot say what it is. It comes "
     "back as an award below, Won a week by 20 or more.", "no"),
]

FAME = [
    ("perfect_week", "Perfect week", "Every game right in one week.", [],
     "Yes. You named it.", SAID),
    ("only_one", "Only one who called it", "The only person in the family to pick a winner.", [],
     "Yes. You named it. Each time it happens it shows the game.", SAID),
    ("season_points", "Most points in a season", "The season's top scorer.",
     [("Grant", "186 points"), ("James", "186 points")],
     "Yes. You asked for it here. Until the season ends it is the same person as the top of "
     "the standings.", SAID),
    ("big_upset", "Biggest upset called", "The biggest underdog anyone picked that won.",
     [("Grant", "Nevada +1.5 over Western KY"), ("Nicole", "Nevada +1.5 over Western KY")],
     "Yes. You asked for it here.", SAID),
    ("real_upsets", "Only count real upsets", "An underdog of 7 points or more. Anything less "
     "is a coin flip.", [],
     "Yes. Today the biggest upset called is a 1.5-point underdog that won 49-14. With this "
     "it reads Up for grabs until somebody calls a real one.", None),
    ("ten_in_a_row", "Ten in a row", "Ten picks in a row right.",
     [("James", "10 in a row, Week 1")],
     "Yes. New. Rare, obvious, and James already has it.", None),
    ("win_by_20", "Won a week by 20 or more", "Finished a week 20 or more points ahead of "
     "second place.", [],
     "Yes. New. This is Biggest blowout with a line anyone can understand. Week 1 was won "
     "by 7, so nobody yet.", None),
    ("two_td_upset", "Two-touchdown upset", "Picked a 14-point underdog that won.", [],
     "Yes. New. Nobody yet, which is what makes it an award.", None),
    ("first_1000", "First to 1,000", "The first person to 1,000 points for the season.", [],
     "Yes. New. At about 180 a week, somebody gets it around Week 6.", None),
    ("most_weeks_won", "Most weeks won", "Whoever has won the most weeks.",
     [("Grant", "1 week")],
     "Maybe. If Weeks won is on everyone's shelf, this repeats it for the leader.", None),
    ("three_upsets", "Three upsets in one week", "Three underdogs right in the same week.", [],
     "Maybe. New. Nobody yet, and it might stay that way.", None),
    ("fifteen_right", "15 right in a week", "Fifteen or more games right in one week.",
     [("Grant", "16-4, Week 1"), ("James", "16-4, Week 1")],
     "Skip. Two of the four of you did it in the first week, so it will be common.", None),
    ("top_five", "Nailed your top five", "Your five most confident picks all won in a week.",
     [("Grant", "Week 1"), ("Parker", "Week 1"), ("Nicole", "Week 1")],
     "Skip. Three of the four of you did it in Week 1. Too easy to mean anything.", None),
    ("own_picks", "Made every pick yourself", "No auto-picks all season.",
     [("Grant", "so far"), ("James", "so far"), ("Nicole", "so far")],
     "Skip. It is an award you can only lose, and Parker already lost it to one auto-pick "
     "in Week 2.", None),
]

SHAME = [
    ("hall_of_shame", "Have a Hall of shame at all", "A small red section under the Hall of "
     "fame for the painful ones.", [],
     "Yes, small. Only the two below that are about bad luck rather than a bad week.", None),
    ("heartbreaker", "Heartbreaker", "Lost a pick worth 15 or more by 3 points or fewer.",
     [("James", "17 on Georgia Tech, lost 14-13")],
     "Yes. New. That game is the story of Week 1.", None),
    ("lost_20", "Lost your 20", "The pick you were surest of that week lost.", [],
     "Yes. New. Nobody yet: everyone's 20 was Georgia.", None),
    ("only_wrong", "Only one who got it wrong", "Everybody else picked the winner.",
     [("Nicole", "5 times in Week 1"), ("Parker", "3 times"), ("Grant", "Kansas over Missouri")],
     "Skip. Nicole would already hold it five times after one week. It piles on whoever is "
     "having a bad week.", None),
    ("auto_pick", "Needed an auto-pick", "Forgot to pick and the app picked for you.",
     [("Parker", "Missouri, Week 2")],
     "Skip. It punishes forgetting, which the reminders exist to prevent.", None),
]

LAYOUT = [
    ("shelves_mine_first", "Your shelf open, the others one tap away",
     "Four shelves of eight rows is a long scroll. Yours opens at the top of the section; "
     "tap a name to open theirs.", [],
     "Yes. Everyone mostly wants their own, and all four are still there.", None),
]


# --------------------------------------------------------------------- app sources


def app_module():
    # src/lib/badgeIcons.js was deleted when Grant's real badge art shipped (2026-09-12).
    # This board predates the art; without the module it draws empty medals.
    path = os.path.join(ROOT, "src", "lib", "badgeIcons.js")
    if not os.path.exists(path):
        return {"icons": {}, "tier": {}, "credit": ""}
    script = ("const m = await import(process.argv[1]);"
              "console.log(JSON.stringify({icons: m.ICONS, tier: m.TIER, credit: m.ICON_CREDIT}))")
    url = "file:///" + path.replace(os.sep, "/")
    out = subprocess.run(["node", "--input-type=module", "-e", script, url],
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


MOD = app_module()
TEAMS = {t["id"]: t for t in json.load(
    open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}


def logo(team_id, px=64):
    from PIL import Image

    t = TEAMS[team_id]
    name = "%s-dark" % team_id if t.get("cut") == "dark" else team_id
    im = Image.open(os.path.join(ROOT, "static", "logos", "%s.png" % name)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def face(name, size):
    t = TEAMS[TEAM[name]]
    n = round(size * 0.72)
    return ('<span class="avatar avatar--team" style="width:%dpx;height:%dpx;background:%s">'
            '<i class="bb-mk" style="width:%dpx;height:%dpx;background-image:var(--lg-%s)"></i>'
            '</span>' % (size, size, t["bg"], n, n, t["id"]))


def pin(key, tier=None, open_=False):
    tier = tier or MOD["tier"].get(key, 1)
    return ('<span class="pin pin--t%d%s"><span class="pin__disc"><span class="pin__field">'
            '<svg class="pin__ico" viewBox="0 0 512 512" aria-hidden="true"><use href="#i-%s"/>'
            '</svg></span></span></span>' % (tier, " is-open" if open_ else "", key))


e = html.escape


# ------------------------------------------------------------------------ preview


def preview():
    """How the shape Grant picked would look: his shelf, with the details written out, and
    the top of a Hall of fame. Book mode, the app's own stylesheet."""
    rows = [
        ("week_points", "Most points in a week", "Week 1", "186"),
        ("week_record", "Best record in a week", "Week 1", "16-4"),
        ("week_low", "Fewest points in a week", "Week 1", "186"),
        ("streak", "Longest winning streak", "Week 1", "8"),
        ("worst_pick", "Worst pick", "8 on Georgia Tech. Lost to Colorado, 14-13", "8"),
        ("upset", "Biggest upset you called", "Nevada +1.5 over Western KY", "+1.5"),
    ]
    shelf = "".join(
        '<div class="sh-row">%s<div class="sh-txt"><p class="sh-k">%s</p><p class="sh-d">%s</p>'
        '</div><p class="sh-v num">%s</p></div>' % (pin(k), e(label), e(detail), e(v))
        for k, label, detail, v in rows)
    others = "".join(
        '<div class="sh-closed">%s<span class="sh-closed__name">%s</span><em>Tap to open</em></div>' % (face(n, 26), n)
        for n in ("James", "Parker", "Nicole"))
    awards = [
        ("streak", 2, "Ten in a row", [("James", None)], False),
        ("points", 1, "Most points in a season", [("Grant", None), ("James", None)], False),
        ("perfect", 4, "Perfect week", [], True),
    ]
    fame = "".join(
        '<div class="sh-award">%s<p class="sh-award__k">%s</p>%s</div>'
        % (pin(k, t, open_), e(label),
           '<p class="sh-award__who">Up for grabs</p>' if open_ else
           '<p class="sh-award__who">%s<span>%s</span></p>'
           % ("".join(face(w, 18) for w, _ in who), " &amp; ".join(w for w, _ in who)))
        for k, t, label, who, open_ in awards)
    return (
        '<div class="bb-phone"><div class="app" data-mode="book"><main class="app__body">'
        '<div class="app__page">'
        '<div class="screen"><h3 class="h2">Shelves</h3></div>'
        '<section class="sh-shelf"><div class="sh-hd">%s<h3>Grant</h3>'
        '<span class="sh-count">You</span></div>%s</section>%s'
        '<div class="sh-fame"><p class="sh-fame__kick">The record book</p>'
        '<h3 class="sh-fame__title">Hall of fame</h3></div><div class="sh-awards">%s</div>'
        '</div></main></div></div>' % (face("Grant", 34), shelf, others, fame))


# ------------------------------------------------------------------------- ballot


def item(section, iid, name, means, prev, take, default):
    if isinstance(prev, dict):
        body = "".join('<li>%s<b>%s</b><span>%s</span></li>' % (face(n, 20), n, e(prev[n]))
                       for n in NAMES)
        prev_html = '<ul class="bb-people">%s</ul>' % body
    elif prev:
        prev_html = ('<p class="bb-earned"><span class="bb-earned__k">Earned so far</span>%s</p>'
                     % "".join('<span class="bb-chip">%s<b>%s</b>%s</span>'
                               % (face(n, 18), n, (" · " + e(d)) if d else "") for n, d in prev))
    elif section in ("fame", "shame") and iid not in ("real_upsets", "hall_of_shame"):
        prev_html = '<p class="bb-earned"><span class="bb-earned__k">Earned so far</span>' \
                    '<span class="bb-none">Nobody yet</span></p>'
    else:
        prev_html = ""
    said = default == SAID
    initial = "yes" if said else (default or "")
    return (
        '<article class="bb-item" data-id="%s" data-default="%s">'
        '<div class="bb-item__main"><h3>%s</h3><p class="bb-means">%s</p>%s'
        '<p class="bb-take"><b>%s</b> %s</p></div>'
        '<div class="bb-vote" role="group" aria-label="%s">'
        '<button type="button" class="bb-btn bb-btn--yes" data-v="yes">Yes</button>'
        '<button type="button" class="bb-btn bb-btn--no" data-v="no">No</button></div>'
        '</article>'
        % (iid, initial, e(name), e(means), prev_html,
           "You said yes." if said else ("You said cut." if default == "no" else "My take."),
           e(take), e(name)))


def section(sid, title, lede, items):
    return ('<section class="bb-sec" id="%s"><div class="bb-sec__hd"><h2>%s</h2><p>%s</p>'
            '</div>%s</section>' % (sid, e(title), lede,
                                    "".join(item(sid, *it) for it in items)))


def build(standalone: bool) -> str:
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()
                  for f in ("theme.css", "app.css"))
    board = open(os.path.join(ROOT, "scripts", "awards_board.css"), encoding="utf-8").read()
    body = open(os.path.join(ROOT, "scripts", "awards_board.html"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (t, logo(t)) for t in TEAM.values())
    symbols = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>'
               % "".join('<symbol id="i-%s" viewBox="0 0 512 512">%s</symbol>' % (k, v)
                         for k, v in MOD["icons"].items()))
    sections = (
        section("shelf", "On everyone's shelf",
                "Every one of you gets these, with your own number and what happened.", SHELF)
        + section("fame", "Hall of fame",
                  "Awards. Anybody can earn one, and most start as <b>Up for grabs</b>.", FAME)
        + section("shame", "Hall of shame",
                  "Optional. Worst pick and fewest points are on the shelves now, so these "
                  "would be different ones.", SHAME)
        + section("layout", "One layout question", "Everything else about the look stays as "
                  "you picked it.", LAYOUT))
    doc = ('<!doctype html>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           if standalone else "")
    return (doc + '<title>Record Book Ballot</title>\n'
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
            '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
            '<style>%s\n%s\n%s</style>%s' % (logos, css, board, symbols)
            + body.replace("{{PREVIEW}}", preview()).replace("{{SECTIONS}}", sections)
            .replace("{{CREDIT}}", e(MOD["credit"])))


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        page = build(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(page)
        print("wrote %s  (%.0f KB)" % (path, len(page.encode()) / 1024))
    total = len(SHELF) + len(FAME) + len(SHAME) + len(LAYOUT)
    print("%d items, %d already answered" % (
        total, sum(1 for s in (SHELF, FAME, SHAME, LAYOUT) for it in s if it[5])))
