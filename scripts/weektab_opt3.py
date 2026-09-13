"""Option 3, banner night: the week's winner hangs a felt banner in the rafters, and the
rest of the tab reads like the Season tab's ladders, on graphite instead of navy."""
from __future__ import annotations

from weektab_common import BY_NAME, MODEL, ME, PLAYERS, e, disc, face, header, join_names, line, mark, phone, tabbar
from weektab_opt1 import chev
from weektab_opt2 import LEAD, field_for

W, H = 262, 322   # the banner, in CSS px; the stitching is drawn to this shape


def stitch():
    i, tail = 10, 36
    pts = "%d,%d %d,%d %d,%d %d,%d %d,%d" % (i, i, W - i, i, W - i, H - i - 2, W // 2, H - tail - i + 2, i, H - i - 2)
    return ('<svg class="bn-stitch" viewBox="0 0 %d %d" width="%d" height="%d" aria-hidden="true">'
            '<polygon points="%s" fill="none"/></svg>' % (W, H, W, H, pts))


def banner():
    p = LEAD[0]
    felt, ink = field_for(p["team_id"])
    runner = next(x for x in PLAYERS if x["rank"] != 1)
    rig = ('<svg class="bn-rig" viewBox="0 0 300 58" width="300" height="58" aria-hidden="true">'
           '<path d="M150 0 L28 48 M150 0 L272 48" /><circle cx="150" cy="2" r="4"/></svg>')
    return ('<section class="bn-rafters">%s<div class="bn-rod"><i></i><i></i></div>'
            '<div class="bn-banner" style="--bn-felt:%s;--bn-letter:%s">%s'
            '<p class="bn-b-wk">Week 1</p><p class="bn-b-champ">Champion</p>%s'
            '<p class="bn-b-name">%s</p><p class="bn-b-pts">%d</p></div>'
            '<p class="bn-under">%d-%d &middot; won by <b>%d</b> over %s</p></section>'
            % (rig, felt, ink, stitch(), disc(p["team_id"], 74, "wt-disc bn-b-disc"), e(p["name"]), p["points"],
               p["correct"], p["wrong"], MODEL["margin"], e(runner["name"])))


def ladder(rows, title, help_=""):
    items = "".join(
        '<li class="bn-rung%s"><span class="bn-rank">%d</span>%s<span class="bn-who"><span class="bn-name">%s</span>'
        '<span class="bn-note">%s</span></span><b class="bn-val">%s</b></li>'
        % (" is-lead" if r["lead"] else "", r["rank"], face(r["name"], 36 if r["lead"] else 30), e(r["name"]),
           r["note"], r["value"])
        for r in rows)
    return ('<section class="bn-sec"><h3 class="bn-title">%s</h3>%s<ol class="bn-ladder">%s</ol></section>'
            % (title, '<p class="bn-help">%s</p>' % help_ if help_ else "", items))


def standings():
    rows = [{"lead": p["rank"] == 1, "rank": p["rank"], "name": p["name"],
             "note": "%d-%d%s" % (p["correct"], p["wrong"], " &middot; you" if p["name"] == ME else ""),
             "value": p["points"]} for p in PLAYERS]
    return ladder(rows, "Final standings")


def chips(stakes):
    return "".join('<span class="bn-chip%s">%s<b>%d</b></span>' % ("" if s["won"] else " is-lost", face(s["name"], 22), s["confidence"])
                   for s in stakes)


def stake_rows(stakes):
    groups = {}
    for s in stakes:
        groups.setdefault((not s["won"], s["pick"]), []).append(s)
    return "".join('<div class="bn-stake"><span>Had %s</span>%s</div>' % (e(pick), chips(rows))
                   for (_l, pick), rows in sorted(groups.items()))


def score_line(g):
    return '<div class="bn-line">%s</div>' % "".join(
        '<span class="bn-team%s">%s<b>%s</b><strong>%d</strong></span>'
        % ("" if s["abbr"] == g["winner"] else " is-loser", mark(s["id"], 30), e(s["abbr"]), s["score"])
        for s in (g["away"], g["home"]))


def decided():
    cards = []
    for d in MODEL["decisive"]:
        if d["shared"]:
            what = 'If <b>%s</b> had won, <b>%s</b> tie on %d.' % (e(d["instead"]), e(join_names(d["leaders"])), d["points"])
        else:
            what = ('If <b>%s</b> had won, <b>%s</b> takes the week, %d to %d.'
                    % (e(d["instead"]), e(d["leaders"][0]), d["points"], d["next"]["points"]))
        cards.append('<article class="bn-card">%s<p class="bn-if">%s</p>%s</article>'
                     % (score_line(d), what, stake_rows(d["stakes"])))
    return '<section class="bn-sec"><h3 class="bn-title">Two results decided it</h3>%s</section>' % "".join(cards)


def upsets():
    cards = []
    for u in MODEL["upsets"]:
        who = ('<div class="bn-stake"><span>Had %s</span>%s</div>' % (e(u["winner"]), chips(u["called"]))
               if u["called"] else '<p class="bn-if bn-if--quiet">Nobody had %s.</p>' % e(u["winner"]))
        cards.append('<article class="bn-card">%s<p class="bn-if"><span class="bn-tag">+%s</span> %s won as the underdog.</p>%s</article>'
                     % (score_line(u), line(u["line"]), e(u["winner"]), who))
    return '<section class="bn-sec"><h3 class="bn-title">Upsets</h3>%s</section>' % "".join(cards)


def left():
    rows = [{"lead": p["rank"] == 1, "rank": p["rank"], "name": p["name"],
             "note": "%d of a possible %d" % (p["points"], p["ceiling"]), "value": p["left"]} for p in MODEL["left"]]
    return ladder(rows, "Points left on the table", "What your right picks were worth, against ranking them perfectly.")


def numbers():
    n = MODEL["numbers"]
    items = [
        ("Favorites won", "of %d games" % n["chalk"]["of"], n["chalk"]["won"]),
        ("Upsets", "%s called %s" % (join_names(n["calledBy"]), join_names(u["winner"] for u in MODEL["upsets"] if u["called"])), n["upsets"]),
        ("All four got it right", ", ".join(n["sweeps"]), len(n["sweeps"])),
        ("Nobody got it right", ", ".join(n["whiffs"]), len(n["whiffs"])),
    ]
    rows = "".join('<li class="bn-rung bn-rung--n"><span class="bn-who"><span class="bn-name">%s</span>'
                   '<span class="bn-note">%s</span></span><b class="bn-val">%d</b></li>' % (e(k), e(s), v)
                   for k, s, v in items)
    return '<section class="bn-sec"><h3 class="bn-title">The week in numbers</h3><ol class="bn-ladder">%s</ol></section>' % rows


def build():
    pager = ('<div class="bn-pager"><span class="bn-arrow">%s</span><span class="bn-mid"><b>Week 1 %s</b>'
             '<span>Final</span></span><span class="bn-arrow">%s</span></div><div class="bn-back">Back to this week</div>'
             % (chev("left"), chev("down", 15), chev("right")))
    body = banner() + standings() + decided() + upsets() + left() + numbers()
    return phone("bn", header("bn-hdr") + pager + body + tabbar("bn-tabs"))
