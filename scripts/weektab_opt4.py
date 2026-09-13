"""Option 4, trading cards: the week is a set. The winner pulls the gold refractor, the other
three are base cards, and the recap is printed on the card backs."""
from __future__ import annotations

from weektab_common import BY_NAME, MODEL, ME, PLAYERS, TEAMS, e, face, header, join_names, line, mark, phone, tabbar
from weektab_opt1 import chev
from weektab_opt2 import field_for


def card(p, big):
    felt, ink = field_for(p["team_id"])
    size = 124 if big else 50
    art = ('<span class="tc-art"><i style="width:%dpx;height:%dpx;background-image:var(--lg-%s)"></i></span>'
           % (size, size, p["team_id"]))
    t = TEAMS[p["team_id"]]
    return ('<div class="tc-card%s" style="--tc-team:%s;--tc-ink:%s;--tc-disc:%s">'
            '<div class="tc-face"><span class="tc-no">%d</span>%s%s'
            '<div class="tc-plate"><b>%s</b><span class="tc-pts"><strong>%d</strong> pts</span></div>'
            '<p class="tc-rec">%d-%d%s</p></div></div>'
            % (" is-gold" if big else "", felt, ink, t["bg"], p["rank"],
               '<span class="tc-parallel">Gold &middot; 1 of 1</span>' if big else "", art, e(p["name"]),
               p["points"], p["correct"], p["wrong"], " &middot; you" if p["name"] == ME else ""))


def pack():
    lead = [p for p in PLAYERS if p["rank"] == 1]
    rest = [p for p in PLAYERS if p["rank"] != 1]
    runner = rest[0]
    return ('<section class="tc-pack"><p class="tc-set"><span>2026 Motley Pick&rsquo;em</span><span>Week 1 &middot; Final</span></p>'
            '%s<p class="tc-by">Won by %d over %s</p><div class="tc-base">%s</div></section>'
            % ("".join(card(p, True) for p in lead), MODEL["margin"], e(runner["name"]),
               "".join(card(p, False) for p in rest)))


def back(no, title, inner):
    return ('<section class="tc-back"><header class="tc-back__hd"><h3>%s</h3><span>No. %d</span></header>%s</section>'
            % (title, no, inner))


def chips(stakes):
    return "".join('<span class="tc-chip%s">%s<b>%d</b></span>' % ("" if s["won"] else " is-lost", face(s["name"], 22), s["confidence"])
                   for s in stakes)


def stake_rows(stakes):
    groups = {}
    for s in stakes:
        groups.setdefault((not s["won"], s["pick"]), []).append(s)
    return "".join('<div class="tc-stake"><span>Had %s</span>%s</div>' % (e(pick), chips(rows))
                   for (_l, pick), rows in sorted(groups.items()))


def score_line(g):
    return '<div class="tc-line">%s</div>' % "".join(
        '<span class="tc-team%s">%s<b>%s</b><strong>%d</strong></span>'
        % ("" if s["abbr"] == g["winner"] else " is-loser", mark(s["id"], 28), e(s["abbr"]), s["score"])
        for s in (g["away"], g["home"]))


def decided():
    rows = []
    for d in MODEL["decisive"]:
        if d["shared"]:
            what = 'If <b>%s</b> had won, <b>%s</b> tie on %d.' % (e(d["instead"]), e(join_names(d["leaders"])), d["points"])
        else:
            what = ('If <b>%s</b> had won, <b>%s</b> takes the week, %d to %d.'
                    % (e(d["instead"]), e(d["leaders"][0]), d["points"], d["next"]["points"]))
        rows.append('<div class="tc-item">%s<p class="tc-if">%s</p>%s</div>' % (score_line(d), what, stake_rows(d["stakes"])))
    return back(2, "Two results decided it", "".join(rows))


def upsets():
    rows = []
    for u in MODEL["upsets"]:
        who = (stake_rows(u["called"]) if u["called"] else '<p class="tc-if">Nobody had %s.</p>' % e(u["winner"]))
        rows.append('<div class="tc-item">%s<p class="tc-if"><span class="tc-tag">+%s</span> %s won as the underdog.</p>%s</div>'
                    % (score_line(u), line(u["line"]), e(u["winner"]), who))
    return back(3, "Upsets", "".join(rows))


def left():
    head = '<div class="tc-stats tc-stats--hd"><span></span><span>Got</span><span>Of</span><span>Left</span></div>'
    rows = "".join(
        '<div class="tc-stats%s">%s<span>%d</span><span>%d</span><b>%d</b></div>'
        % (" is-lead" if p["rank"] == 1 else "",
           '<span class="tc-stats__who">%s%s</span>' % (face(p["name"], 26), e(p["name"])), p["points"], p["ceiling"], p["left"])
        for p in MODEL["left"])
    return back(4, "Points left on the table",
                '<p class="tc-help">What your right picks were worth, against ranking them perfectly.</p>%s%s' % (head, rows))


def numbers():
    n = MODEL["numbers"]
    items = [
        ("Favorites won", "of %d games" % n["chalk"]["of"], n["chalk"]["won"]),
        ("Upsets", "%s called %s" % (join_names(n["calledBy"]), join_names(u["winner"] for u in MODEL["upsets"] if u["called"])), n["upsets"]),
        ("All four got it right", ", ".join(n["sweeps"]), len(n["sweeps"])),
        ("Nobody got it right", ", ".join(n["whiffs"]), len(n["whiffs"])),
    ]
    rows = "".join('<div class="tc-num"><span class="tc-num__who"><b>%s</b><span>%s</span></span><strong>%d</strong></div>'
                   % (e(k), e(s), v) for k, s, v in items)
    picks = {t["pick"] for t in n["twenties"].values()}
    fact = ('<p class="tc-did"><b>Did you know?</b> All four of you put your 20 on %s.</p>' % e(picks.pop())
            if len(n["twenties"]) == len(PLAYERS) and len(picks) == 1 else "")
    return back(5, "The week in numbers", rows + fact)


def build():
    pager = ('<div class="tc-pager"><span class="tc-arrow">%s</span><span class="tc-mid"><b>Week 1 %s</b>'
             '<span>Final</span></span><span class="tc-arrow">%s</span></div><div class="tc-back-link">Back to this week</div>'
             % (chev("left"), chev("down", 15), chev("right")))
    body = pack() + '<div class="tc-backs">%s</div>' % (decided() + upsets() + left() + numbers())
    return phone("tc", header("tc-hdr") + pager + body + tabbar("tc-tabs"))
