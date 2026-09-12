"""Render the options board for fixing the Season tab's record book.

Grant, 2026-09-12: "The icons are fine, but the text under it's weak, and it just says my
name. That's it. So that looks really bad too, and it's tiny text. And the organization
makes no sense."

All three are real, and measuring the live screen found a fourth that is not a design
question at all.

THE TEXT. Under each 74px pin the record's name is 8.5px grey capitals and the holder is
10px grey. What actually reads is a number and "Grant", and Grant holds seven of the
twelve, so the section says his name seven times and little else.

THE ORGANIZATION. Every group holds four records in a grid three across, so every group
ends on one pin alone in its row. The two records nobody wants, fewest points in a week
and worst pick, sit in among the achievements under the same brass headings.

THE BUG. An unfinished week counts as a week. Week 2 was one game in, so the form chart
dived from about 180 to nearly zero for everyone, and the book said Grant held "Fewest
points in a week: 0" and that Nicole had won Week 2. Fixed the same way in every option:
a week is in the books when all twenty games are graded, or once a later week has started.

Nothing here is a mockup of the CSS. theme.css and app.css are embedded verbatim, the pins
are the real markup, and the icons are imported from src/lib/badgeIcons.js through node,
so the board cannot drift from the app it is proposing to change.

    python scripts/build_seasonbook_board.py
"""
from __future__ import annotations

import base64
import html
import io
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "seasonbook-board.html")

# ------------------------------------------------------------------ the season

# The real 2026 season as the database held it on the afternoon of 2026-09-12, run through
# the app's own seasonRecords(): Week 1 final, Week 2 one game graded. TODAY is what the tab
# computes now. FIXED counts only finished weeks for the six week-based records, which
# changes exactly two of them.
SEATS = {
    "Grant": {"team": "8", "color": "#B85C1F"},
    "James": {"team": "2655", "color": "#1F6F4A"},
    "Parker": {"team": "338", "color": "#2E5C8A"},
    "Nicole": {"team": "61", "color": "#8A2E4F"},
}
STANDINGS = [(1, "James", 186), (1, "Grant", 186), (3, "Parker", 165), (4, "Nicole", 160)]

# key, label, value (None = nobody holds it), holders
FIXED = {
    "week_points": ("Most points in a week", "186", ["Grant"]),
    "week_record": ("Best record in a week", "16-4", ["Grant", "James"]),
    "week_low": ("Fewest points in a week", "147", ["Nicole"]),
    "blowout": ("Biggest blowout", "7", ["Grant"]),
    "weeks_won": ("Most weeks won", "1", ["Grant"]),
    "record": ("Best overall record", "17-4", ["James"]),
    "points": ("Most points in a season", "186", ["Grant", "James"]),
    "perfect": ("Perfect week", None, []),
    "streak": ("Longest winning streak", "10", ["James"]),
    "upset": ("Biggest upset called", "+1.5", ["Grant", "Nicole"]),
    "worst_pick": ("Worst pick", "17", ["James"]),
    "lone": ("Only one who called it", None, []),
}
TODAY = dict(FIXED, week_low=("Fewest points in a week", "0", ["Grant"]),
             weeks_won=("Most weeks won", "1", ["Grant", "Nicole"]))

# What each record means, for the two options that have room to say it.
UNIT = {
    "week_points": "points", "week_record": "right", "week_low": "points",
    "blowout": "point margin", "weeks_won": "week", "record": "right",
    "points": "points", "perfect": "", "streak": "right in a row",
    "upset": "point underdog", "worst_pick": "points on a loser", "lone": "",
}

# ---------------------------------------------------------------- app sources


def app_module():
    """ICONS, TIER and ICON_CREDIT straight out of the app's module, via node.

    That module was deleted when Grant's real badge art shipped (2026-09-12). This board
    predates the art; without the module it draws empty medals."""
    path = os.path.join(ROOT, "src", "lib", "badgeIcons.js")
    if not os.path.exists(path):
        return {"icons": {}, "tier": {}, "credit": ""}
    script = (
        "const m = await import(process.argv[1]);"
        "console.log(JSON.stringify({icons: m.ICONS, tier: m.TIER, credit: m.ICON_CREDIT}))"
    )
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


# ------------------------------------------------------------------- pieces


def face(name, size):
    team = TEAMS[SEATS[name]["team"]]
    n = round(size * 0.72)
    return ('<span class="avatar avatar--team" style="width:%dpx;height:%dpx;background:%s">'
            '<i class="mk" style="width:%dpx;height:%dpx;background-image:var(--lg-%s)"></i>'
            '</span>' % (size, size, team["bg"], n, n, team["id"]))


def names(holders):
    if len(holders) <= 1:
        return holders[0] if holders else ""
    return "%s &amp; %s" % (", ".join(holders[:-1]), holders[-1])


def hold(holders, size=20, cls=""):
    """Who holds it: their school mark, then their name, big enough to read."""
    if not holders:
        return '<span class="hold hold--open %s">Up for grabs</span>' % cls
    faces = "".join(face(h, size) for h in holders)
    return ('<span class="hold %s"><span class="hold__faces">%s</span>'
            '<span class="hold__who">%s</span></span>' % (cls, faces, names(holders)))


def pin(key, open_=False, cls=""):
    tier = MOD["tier"].get(key, 1)
    return ('<span class="pin pin--t%d%s %s"><span class="pin__disc"><span class="pin__field">'
            '<svg class="pin__ico" viewBox="0 0 512 512" aria-hidden="true">'
            '<use href="#i-%s"/></svg></span></span></span>'
            % (tier, " is-open" if open_ else "", cls, key))


def symbols():
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>'
            % "".join('<symbol id="i-%s" viewBox="0 0 512 512">%s</symbol>' % (k, v)
                      for k, v in MOD["icons"].items()))


def phone(inner, title="Season"):
    """The book-mode shell the Season tab renders in, cut down to the record book."""
    return ('<div class="bd-phone"><div class="app" data-mode="book"><main class="app__body">'
            '<div class="app__page">%s</div></main></div></div>' % inner)


def heading(text, cls="h2"):
    return '<div class="screen"><h3 class="%s">%s</h3></div>' % (cls, text)


# -------------------------------------------------------------------- today


def today():
    """Exactly what Season.jsx renders now: the three groups, three across, today's data."""
    groups = [("By the week", ["week_points", "week_record", "week_low", "blowout"]),
              ("By the season", ["weeks_won", "record", "points", "perfect"]),
              ("Single games", ["streak", "upset", "worst_pick", "lone"])]
    out = []
    for title, keys in groups:
        tiles = []
        for k in keys:
            label, value, holders = TODAY[k]
            who = "not yet" if value is None else (
                holders[0] if len(holders) == 1 else " and ".join(holders))
            tiles.append(
                '<div class="pin pin--t%d%s"><span class="pin__disc"><span class="pin__field">'
                '<svg class="pin__ico" viewBox="0 0 512 512"><use href="#i-%s"/></svg>'
                '</span></span><p class="pin__k">%s</p><p class="pin__v num">%s</p>'
                '<p class="pin__who">%s</p></div>'
                % (MOD["tier"].get(k, 1), " is-open" if value is None else "", k, label,
                   value or "&mdash;", who))
        out.append(heading(title) + '<div class="recs">%s</div>' % "".join(tiles))
    return phone("".join(out))


# ------------------------------------------------------------------ options


def tile(k, cls="rb-tile"):
    label, value, holders = FIXED[k]
    return ('<div class="%s">%s<p class="rb-tile__k">%s</p><p class="rb-tile__v num">%s</p>%s</div>'
            % (cls, pin(k, value is None), label, value or "&mdash;", hold(holders)))


def option_a():
    """Two across. The same three groups; the text grows up and the orphans go."""
    groups = [("By the week", ["week_points", "week_record", "blowout", "week_low"]),
              ("By the season", ["weeks_won", "points", "record", "perfect"]),
              ("Single games", ["streak", "upset", "lone", "worst_pick"])]
    return phone("".join(heading(t) + '<div class="bkA">%s</div>' % "".join(tile(k) for k in ks)
                         for t, ks in groups))


def row(k, shame=False):
    label, value, holders = FIXED[k]
    return ('<div class="bkB__row%s">%s<div class="bkB__txt"><p class="bkB__k">%s</p>%s</div>'
            '<p class="bkB__v num">%s</p></div>'
            % (" is-shame" if shame else "", pin(k, value is None), label, hold(holders, 18),
               value or "&mdash;"))


def option_b():
    """Trophy rows. One record per line, grouped by what kind of record it is."""
    groups = [("The season", ["weeks_won", "points", "record", "perfect"], False),
              ("Best weeks", ["week_points", "week_record", "blowout"], False),
              ("Big calls", ["streak", "upset", "lone"], False),
              ("Hall of shame", ["week_low", "worst_pick"], True)]
    return phone("".join(
        heading(t, "h2 bkB__hd%s" % (" is-shame" if s else ""))
        + '<div class="bkB">%s</div>' % "".join(row(k, s) for k in ks)
        for t, ks, s in groups))


def option_c():
    """Hall of fame, hall of shame. The loud one."""
    fame = ["weeks_won", "points", "record", "week_points", "week_record", "blowout",
            "streak", "upset", "perfect", "lone"]
    shame = ["week_low", "worst_pick"]
    return phone(
        '<div class="bkC__fame"><p class="bkC__kick">The record book</p>'
        '<h3 class="bkC__title">Hall of fame</h3></div>'
        '<div class="bkA">%s</div>'
        '<section class="bkC__shame"><div class="bkC__shamehd">'
        '<svg viewBox="0 0 512 512" aria-hidden="true"><use href="#i-week_low"/></svg>'
        '<h3>Hall of shame</h3></div><div class="bkA bkC__two">%s</div></section>'
        % ("".join(tile(k) for k in fame), "".join(tile(k, "rb-tile is-shame") for k in shame)))


def option_d():
    """Everyone's shelf. The name is said once, big, with what they hold under it."""
    held = {n: [k for k, (_l, v, h) in FIXED.items() if v is not None and n in h] for n in SEATS}
    order = sorted(SEATS, key=lambda n: (-len(held[n]), [s[1] for s in STANDINGS].index(n)))
    shelves = []
    for n in order:
        ks = held[n]
        if ks:
            minis = "".join(
                '<div class="mini">%s<p class="mini__v num">%s</p><p class="mini__k">%s</p>%s</div>'
                % (pin(k), FIXED[k][1], FIXED[k][0],
                   '<p class="mini__with">with %s</p>' % names([h for h in FIXED[k][2] if h != n])
                   if len(FIXED[k][2]) > 1 else "")
                for k in ks)
            body = '<div class="bkD__pins">%s</div>' % minis
        else:
            body = '<p class="bkD__none">No records yet. Plenty of season left.</p>'
        count = "%d record%s" % (len(ks), "" if len(ks) == 1 else "s")
        shelves.append(
            '<section class="bkD__shelf"><div class="bkD__hd">%s<h3>%s</h3>'
            '<span class="bkD__count">%s</span></div>%s</section>'
            % (face(n, 34), n, count, body))
    grabs = "".join(
        '<div class="mini">%s<p class="mini__v num">&mdash;</p><p class="mini__k">%s</p></div>'
        % (pin(k, True), FIXED[k][0]) for k, (_l, v, _h) in FIXED.items() if v is None)
    shelves.append('<section class="bkD__shelf is-open"><div class="bkD__hd"><h3>Up for grabs</h3>'
                   '</div><div class="bkD__pins">%s</div></section>' % grabs)
    return phone('<div class="bkD">%s</div>' % "".join(shelves))


OPTIONS = [
    ("A", "Two across", option_a,
     "The smallest fix for both notes. Same three groups and the same pins, two to a row "
     "instead of three, so four records make two full rows and nothing is left alone. The "
     "extra width goes to the text: the record's name in 12px capitals in full cream, the "
     "number at 28px in polished brass, and the holder as their school mark and their name.",
     "103px shorter than today, the shortest of the four. The groups still mix good news "
     "and bad: fewest points in a week now sits last in its group, but under the same brass "
     "heading as the achievements."),
    ("B", "Trophy rows", option_b,
     "One record per line: the pin on the left, the record and who holds it in the middle, "
     "the number on the right. The groups say what kind of record it is, and the two nobody "
     "wants get their own at the bottom, with the number in red.",
     "26px shorter than today. The easiest to read by a distance, "
     "and no group size can ever leave a gap. The pins shrink to 54px, so it reads as a list "
     "with trophies on it more than a trophy case."),
    ("C", "Hall of fame, hall of shame", option_c,
     "The loud one. Ten records under a big brass Hall of fame, two across, in order of how "
     "much they matter: weeks won and season points first, unclaimed ones last. Then the "
     "two bad ones in a red panel of their own, with red plating on the pins.",
     "11px taller than today. Ten in one group loses the week and season split, so the "
     "order has to carry it: the season's big three first, single weeks, then big calls."),
    ("D", "Everyone's shelf", option_d,
     "Organized by person instead of by record. Each of you gets a shelf with your school "
     "mark, your name once and big, how many records you hold, and those pins under it. "
     "Shared records show on both shelves with who you share it with. Unclaimed records "
     "sit on their own shelf as empty sockets.",
     "21px taller than today, the tallest of the four. The most personal, and it answers "
     "who is winning the record "
     "book at a glance. Finding a record means scanning four shelves, ties print a pin twice, "
     "Parker's shelf is empty this early, and the two bad-news records sit on James's and "
     "Nicole's shelves looking like trophies."),
]


def build() -> str:
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()
                  for f in ("theme.css", "app.css"))
    board = open(os.path.join(ROOT, "scripts", "seasonbook_board.css"), encoding="utf-8").read()
    body = open(os.path.join(ROOT, "scripts", "seasonbook_board.html"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (s["team"], logo(s["team"]))
                                  for s in SEATS.values())
    opts = "".join(
        '<section class="bd-opt" id="opt-%s"><div class="bd-opt__hd"><span class="bd-opt__k">%s'
        '</span><h2>%s</h2><span class="bd-opt__px" data-measure="%s">&hellip;</span></div>'
        '<div class="bd-opt__grid"><div class="bd-opt__copy"><p>%s</p><p class="bd-opt__cost">'
        '<b>Cost.</b> %s</p></div>%s</div></section>'
        % (k, k, title, k, what, cost, fn()) for k, title, fn, what, cost in OPTIONS)
    return (
        '<title>Season Tab Record Book</title>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
        '&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap"'
        ' rel="stylesheet">\n'
        '<style>%s\n%s\n%s</style>' % (logos, css, board)
        + symbols()
        + body.replace("{{TODAY}}", today()).replace("{{OPTIONS}}", opts)
        .replace("{{CREDIT}}", html.escape(MOD["credit"]))
    )


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    page = build()
    # The standalone copy keeps a doctype so a local render is in standards mode and
    # measures like the app. The Artifact host supplies its own skeleton, so it gets the
    # fragment.
    doc = '<!doctype html>\n<meta charset="utf-8">\n' \
          '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
    for path, text in ((OUT, doc + page), (OUT.replace(".html", ".artifact.html"), page)):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print("wrote %s  (%.0f KB)" % (path, len(text.encode()) / 1024))
