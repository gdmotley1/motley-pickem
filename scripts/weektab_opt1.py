"""Option 1, the stadium scoreboard: painted steel, amber bulbs, a lamp for the winner."""
from __future__ import annotations

from weektab_bulbs import bulbs
from weektab_common import (BY_NAME, MODEL, ME, PLAYERS, e, face, header, join_names, line,
                            mark, phone, tabbar)

CHEV = {
    "left": '<path d="M15 5 8 12l7 7" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
    "right": '<path d="m9 5 7 7-7 7" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
    "down": '<path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
}


def chev(d, size=18):
    return '<svg viewBox="0 0 24 24" width="%d" height="%d" fill="none" aria-hidden="true">%s</svg>' % (size, size, CHEV[d])


def well(value, height, cols, cls=""):
    return '<span class="sb-well %s">%s</span>' % (cls, bulbs(value, height, cols=cols))


def chips(stakes):
    return "".join(
        '<span class="sb-chip%s">%s<b>%d</b></span>' % ("" if s["won"] else " is-lost", face(s["name"], 22), s["confidence"])
        for s in stakes)


def stake_rows(stakes):
    """Grouped by the team they took, the side that won first."""
    groups = {}
    for s in stakes:
        groups.setdefault((not s["won"], s["pick"]), []).append(s)
    return "".join(
        '<div class="sb-stake"><span class="sb-k">Had %s</span><span class="sb-chips">%s</span></div>'
        % (e(pick), chips(rows)) for (_lost, pick), rows in sorted(groups.items()))


def score_line(g):
    out = []
    for s in (g["away"], g["home"]):
        won = s["abbr"] == g["winner"]
        out.append('<span class="sb-team%s">%s<b>%s</b>%s</span>'
                   % ("" if won else " is-loser", mark(s["id"], 26), e(s["abbr"]), well(s["score"], 22, 2)))
    return '<div class="sb-line">%s</div>' % "".join(out)


def decided():
    rows = []
    for d in MODEL["decisive"]:
        if d["shared"]:
            what = ('If <b>%s</b> had won, <b>%s</b> tie on <b class="sb-n">%d</b>.'
                    % (e(d["instead"]), e(join_names(d["leaders"])), d["points"]))
        else:
            what = ('If <b>%s</b> had won, <b>%s</b> takes the week, <b class="sb-n">%d</b> to <b class="sb-n">%d</b>.'
                    % (e(d["instead"]), e(d["leaders"][0]), d["points"], d["next"]["points"]))
        rows.append('<div class="sb-game">%s<p class="sb-if">%s</p>%s</div>'
                    % (score_line(d), what, stake_rows(d["stakes"])))
    n = len(rows)
    title = "One result decided it" if n == 1 else "%s results decided it" % {2: "Two", 3: "Three"}.get(n, str(n))
    return '<section class="sb-panel"><h3 class="sb-title">%s</h3>%s</section>' % (title, "".join(rows))


def upsets():
    rows = []
    for u in MODEL["upsets"]:
        if u["called"]:
            who = '<span class="sb-k">Had %s</span><span class="sb-chips">%s</span>' % (e(u["winner"]), chips(u["called"]))
        else:
            who = '<span class="sb-none">Nobody had %s</span>' % e(u["winner"])
        rows.append('<div class="sb-game">%s<div class="sb-stake"><span class="sb-plate">+%s</span>%s</div></div>'
                    % (score_line(u), line(u["line"]), who))
    return '<section class="sb-panel"><h3 class="sb-title">Upsets</h3>%s</section>' % "".join(rows)


def left():
    rows = "".join(
        '<div class="sb-lrow%s">%s<span class="sb-who"><span class="sb-name">%s</span>'
        '<span class="sb-note">%d of a possible %d</span></span>%s</div>'
        % (" is-lead" if p["rank"] == 1 else "", face(p["name"], 30), e(p["name"]), p["points"], p["ceiling"],
           well(p["left"], 26, 2))
        for p in MODEL["left"])
    return ('<section class="sb-panel"><h3 class="sb-title">Points left on the table</h3>'
            '<p class="sb-help">What your right picks were worth, against ranking them perfectly.</p>%s</section>' % rows)


def numbers():
    n = MODEL["numbers"]
    items = [
        ("Favorites won", "of %d games" % n["chalk"]["of"], n["chalk"]["won"]),
        ("Upsets", "%s called %s" % (join_names(n["calledBy"]), join_names(u["winner"] for u in MODEL["upsets"] if u["called"]))
         if n["called"] else "Nobody called one", n["upsets"]),
        ("All four got it right", ", ".join(n["sweeps"]), len(n["sweeps"])),
        ("Nobody got it right", ", ".join(n["whiffs"]), len(n["whiffs"])),
    ]
    rows = "".join(
        '<div class="sb-nrow"><span class="sb-who"><span class="sb-name">%s</span><span class="sb-note">%s</span></span>%s</div>'
        % (e(k), e(s), well(v, 26, 2)) for k, s, v in items)
    return '<section class="sb-panel"><h3 class="sb-title">The week</h3>%s</section>' % rows


def standings():
    lead = [p for p in PLAYERS if p["rank"] == 1]
    rows = "".join(
        '<div class="sb-row%s"><span class="sb-lamp" aria-hidden="true"></span>%s'
        '<span class="sb-name">%s%s</span>%s%s%s</div>'
        % (" is-lead" if p["rank"] == 1 else "", face(p["name"], 28), e(p["name"]),
           '<em>You</em>' if p["name"] == ME else "",
           well(p["correct"], 24, 2), well(p["wrong"], 24, 2), well(p["points"], 24, 3, "sb-well--pts"))
        for p in PLAYERS)
    if len(lead) > 1:
        msg = bulbs("TIED", 50) + bulbs(" & ".join(p["name"] for p in lead).replace("&", "+"), 26)
    else:
        msg = bulbs(lead[0]["name"], 50, "sb-msg__big") + bulbs("WINS BY %d" % MODEL["margin"], 26)
    return ('<section class="sb-board"><div class="sb-crown"><span>Week 1</span><span class="sb-final">'
            '<i></i>Final</span></div><div class="sb-msg">%s</div>'
            '<div class="sb-score"><div class="sb-score__hd"><span></span><span>W</span><span>L</span>'
            '<span>Pts</span></div>%s</div></section>' % (msg, rows))


def build():
    pager = ('<div class="sb-pager"><span class="sb-arrow">%s</span><span class="sb-mid"><b>Week 1 %s</b>'
             '<span>Final</span></span><span class="sb-arrow">%s</span></div>'
             '<div class="sb-back">Back to this week</div>' % (chev("left"), chev("down", 15), chev("right")))
    body = standings() + decided() + upsets() + left() + numbers()
    return phone("sb", header("sb-hdr") + pager + '<div class="sb-page">%s</div>' % body + tabbar("sb-tabs"))
