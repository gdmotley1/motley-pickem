"""Direction 4: Gridiron. The Picks tab painted on the field itself."""
from __future__ import annotations

from pickstab_kit import (CARD, LIFTED, PICKED_MIDWEEK, RANKED, days, e, header, more, rank_badge, state, tabbar)
from pickstab_kit import winners as drawn

NAME = "Gridiron"
PITCH = ("The tab is the field. Twenty picks are a hundred-yard drive, so progress is the ball moving downfield. Each game "
         "sits between chalk yard lines, and picking a team paints its end zone in the school&rsquo;s colors. Points are "
         "painted like yard numbers, the lifted game rides the yellow first-down line, and locking in is a touchdown.")
BUILT = "Alfa Slab One, new, for the field numbers and the end zone lettering, over Inter. Turf, chalk, a yellow flag and a goalpost."

BALL = ('<svg class="gd-ball" viewBox="0 0 40 24" aria-hidden="true"><ellipse cx="20" cy="12" rx="18" ry="10" fill="#7a3b14"/>'
        '<path d="M9 12h22M14 9v6M18 9v6M22 9v6M26 9v6" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>')
FLAG = '<svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M3 15V2M3 2.5h9l-2 3 2 3H3" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>'
POSTS = ('<svg class="gd-posts" viewBox="0 0 120 150" aria-hidden="true"><path d="M60 150V86M16 86h88M16 86V6M104 86V6" fill="none" '
         'stroke="#ffd400" stroke-width="8" stroke-linecap="round"/></svg>')


def sticker(tid, size):
    n = round(size * 0.7)
    return ('<span class="gd-sticker" style="width:%dpx;height:%dpx" aria-hidden="true"><i style="width:%dpx;height:%dpx;'
            'background-image:var(--lg-%s)"></i></span>' % (size, size, n, n, tid))


def zone(c, s):
    t = c[s]
    st = state(c, s)
    return ('<button class="gd-zone %s" style="--c:%s;--ink:%s" aria-pressed="%s">%s<span class="gd-name">%s<b>%s</b></span></button>'
            % (st, t["loud"], t["ink"], "true" if st == "is-picked" else "false", sticker(t["id"], 42), rank_badge(t, "gd-rank"), e(t["school"])))


def game(c):
    return ('<article class="gd-game" data-m="game"><div class="gd-meta"><span>%s &middot; %s &middot; <b>%s</b></span>'
            '<button class="gd-cta" aria-label="Matchup preview: %s"><span class="gd-shine" aria-hidden="true"></span>%sMatchup</button></div>'
            '<div class="gd-zones">%s<span class="gd-at" aria-hidden="true">%s</span>%s</div></article>'
            % (e(c["when"]), e(c["tv"]), e(c["spread"]), e(c["key"]), FLAG, zone(c, "away"), "vs" if c["neutral"] else "at", zone(c, "home")))


def drive():
    pct = PICKED_MIDWEEK * 100 // len(CARD)
    lines = "".join('<i style="left:%d%%"></i>' % x for x in range(10, 100, 10))
    return ('<div class="gd-drive"><p><b>%d</b> of 20 picked <span>&middot; %d to go</span></p>'
            '<div class="gd-field" aria-hidden="true"><span class="gd-ez gd-ez--l"></span><div class="gd-play">%s'
            '<span class="gd-gain" style="width:%d%%"></span><span class="gd-marker" style="left:%d%%">%s</span></div>'
            '<span class="gd-ez gd-ez--r">TD</span></div></div>' % (PICKED_MIDWEEK, len(CARD) - PICKED_MIDWEEK, lines, pct, pct, BALL))


def winners():
    groups = "".join('<h3 class="gd-day"><span>%s</span></h3>%s' % (d, "".join(game(c) for c in rows)) for d, rows in days(drawn()))
    return ('<div class="gd">%s%s%s%s<div class="gd-go-wrap"><button class="gd-go" disabled>%d still to pick</button></div>%s</div>'
            % (header("gd"), drive(), groups, more("gd"), len(CARD) - PICKED_MIDWEEK, tabbar("gd")))


def points():
    rows = []
    for c in RANKED:
        p = c["pick"]
        lifted = c["key"] == LIFTED
        cue = '<span class="gd-cue is-moving">Moving</span>' if lifted else '<span class="gd-cue">Here</span>'
        rows.append('<li class="gd-row%s" data-m="rank"><button class="gd-row__hit"><span class="gd-yard"><i aria-hidden="true"></i>%d</span>%s'
                    '<span class="gd-who"><b>%s</b><span>over %s &middot; %s</span></span>%s</button></li>'
                    % (" is-lifted" if lifted else "", c["pts"], sticker(p["id"], 36), e(p["school"]), e(c["opp"]["abbr"]), e(c["spread"]), cue))
    lifted = next(c for c in CARD if c["key"] == LIFTED)
    return ('<div class="gd">%s<div class="gd-rankhead"><button class="gd-chip">&lsaquo; Winners</button><button class="gd-chip">Reset to spread</button></div>'
            '<div class="gd-intro"><h2>Most sure at the top</h2><p>Already sorted by the spread, so the top game is worth <b>20</b> '
            'and the bottom <b>1</b>. Tap a game to move it.</p></div><ol class="gd-ranks">%s</ol>'
            '<div class="gd-lift"><div><span>Moving <b>%s</b>. Tap a row to give it those points.</span><button class="gd-cancel">Cancel</button></div></div>%s</div>'
            % (header("gd"), "".join(rows), e(lifted["pick"]["school"]), tabbar("gd")))


def locked():
    top = RANKED[0]
    p = top["pick"]
    rows = "".join('<li class="gd-sealed"><span class="gd-yard gd-yard--sm"><i aria-hidden="true"></i>%d</span>%s<span class="gd-who"><b>%s</b>'
                   '<span>over %s &middot; %s</span></span></li>'
                   % (c["pts"], sticker(c["pick"]["id"], 30), e(c["pick"]["school"]), e(c["opp"]["abbr"]), e(c["when"])) for c in RANKED)
    return ('<div class="gd">%s<section class="gd-td" style="--c:%s;--ink:%s">%s<p class="gd-td__kick">Touchdown</p>'
            '<h2 class="gd-td__h">Picks<br>are in</h2><p class="gd-td__sub">Saved. Change any game right up until it kicks off. '
            'Your biggest bet: 20 on %s.</p><div class="gd-actions"><button class="gd-btn gd-btn--flag">%sSee the Board</button>'
            '<button class="gd-btn">Change something</button></div></section>'
            '<h3 class="gd-day"><span>Your card</span></h3><ol class="gd-sealeds">%s</ol>%s</div>'
            % (header("gd"), p["loud"], p["ink"], POSTS, e(p["school"]), FLAG, rows, tabbar("gd")))
