"""Direction 3: Face-off. Bright, and painted in both schools' colors."""
from __future__ import annotations

from pickstab_kit import (CARD, LIFTED, PICKED_MIDWEEK, RANKED, days, e, header, mark, more, rank_badge, state, tabbar)
from pickstab_kit import winners as drawn

NAME = "Face-off"
PITCH = ("A fight card on a bright page. Every game is one band split down a diagonal between the two schools&rsquo; colors; "
         "the side you take stays lit and gets stamped, the other goes to charcoal. Points are rows painted in the team "
         "you picked, and locking in floods the screen in the color of your biggest bet, like the Week tab&rsquo;s final.")
BUILT = "Archivo italic at its narrowest widths, the Week tab&rsquo;s type, on a cool white page. No new fonts."


def sticker(tid, size):
    """A school's full-colour mark on a white helmet sticker, so it reads on any flood, its own colour included."""
    n = round(size * 0.7)
    return ('<span class="fo-sticker" style="width:%dpx;height:%dpx" aria-hidden="true"><i style="width:%dpx;height:%dpx;'
            'background-image:var(--lg-%s)"></i></span>' % (size, size, n, n, tid))


def inv(t):
    """1 turns a monochrome mark white, 0 leaves it black, matching the lettering on that colour."""
    return 1 if t["ink"] == "#ffffff" else 0


def half(c, s, pos):
    t = c[s]
    st = state(c, s)
    return ('<button class="fo-half fo-%s %s" style="--c:%s;--ink:%s;--inv:%s" aria-pressed="%s">%s<span class="fo-name">%s<b>%s</b></span>'
            '<span class="fo-stamp" aria-hidden="true">Picked</span></button>'
            % (pos, st, t["loud"], t["ink"], inv(t), "true" if st == "is-picked" else "false", sticker(t["id"], 52),
               rank_badge(t, "fo-rank"), e(t["school"])))


def game(c):
    return ('<article class="fo-game" data-m="game"><div class="fo-split">%s%s<span class="fo-at" aria-hidden="true">%s</span></div>'
            '<div class="fo-meta"><span>%s &middot; %s &middot; <b>%s</b></span>'
            '<button class="fo-cta" aria-label="Matchup preview: %s"><span class="fo-shine" aria-hidden="true"></span>Matchup &rsaquo;</button></div></article>'
            % (half(c, "away", "l"), half(c, "home", "r"), "vs" if c["neutral"] else "@", e(c["when"]), e(c["tv"]), e(c["spread"]), e(c["key"])))


def winners():
    notches = "".join('<i class="%s"></i>' % ("on" if i < PICKED_MIDWEEK else "") for i in range(len(CARD)))
    groups = "".join('<h3 class="fo-day"><span>%s</span></h3>%s' % (d, "".join(game(c) for c in rows)) for d, rows in days(drawn()))
    return ('<div class="fo">%s<div class="fo-top"><h2><b>%d</b> of 20<br>picked</h2><div class="fo-bar" aria-hidden="true">%s</div></div>'
            '%s%s<div class="fo-go-wrap"><button class="fo-go" disabled>%d still to pick</button></div>%s</div>'
            % (header("fo"), PICKED_MIDWEEK, notches, groups, more("fo"), len(CARD) - PICKED_MIDWEEK, tabbar("fo")))


def points():
    rows = []
    for c in RANKED:
        p = c["pick"]
        lifted = c["key"] == LIFTED
        rows.append('<li class="fo-row%s" data-m="rank" style="--c:%s;--ink:%s;--inv:%s"><button class="fo-row__hit"><span class="fo-pts">%d</span>%s'
                    '<span class="fo-who"><b>%s</b><span>over %s &middot; %s</span></span><span class="fo-cue">%s</span></button></li>'
                    % (" is-lifted" if lifted else "", p["loud"], p["ink"], inv(p), c["pts"], sticker(p["id"], 38),
                       e(p["school"]), e(c["opp"]["abbr"]), e(c["spread"]), "Moving" if lifted else "Here"))
    lifted = next(c for c in CARD if c["key"] == LIFTED)
    return ('<div class="fo">%s<div class="fo-rankhead"><button class="fo-chip">&lsaquo; Winners</button><button class="fo-chip">Reset to spread</button></div>'
            '<div class="fo-intro"><h2>Points</h2><p>Most sure at the top. Already sorted by the spread, so the top game is worth '
            '<b>20</b> and the bottom <b>1</b>. Tap a game to move it.</p></div><ol class="fo-ranks">%s</ol>'
            '<div class="fo-lift"><span>Moving <b>%s</b>. Tap a row to give it those points.</span><button class="fo-cancel">Cancel</button></div>%s</div>'
            % (header("fo"), "".join(rows), e(lifted["pick"]["school"]), tabbar("fo")))


def locked():
    top = RANKED[0]
    p = top["pick"]
    rows = "".join('<li class="fo-sealed" style="--c:%s;--ink:%s;--inv:%s"><span class="fo-pts fo-pts--sm">%d</span><span class="fo-chipmark">%s</span>'
                   '<span class="fo-who"><b>%s</b><span>over %s &middot; %s</span></span></li>'
                   % (c["pick"]["loud"], c["pick"]["ink"], inv(c["pick"]), c["pts"], sticker(c["pick"]["id"], 32),
                      e(c["pick"]["school"]), e(c["opp"]["abbr"]), e(c["when"])) for c in RANKED)
    return ('<div class="fo">%s<section class="fo-final" style="--c:%s;--ink:%s;--inv:%s"><i class="fo-final__mark" style="background-image:var(--lg-%s)" aria-hidden="true"></i>'
            '<p class="fo-final__kick"><span>Week 1</span> Grant&rsquo;s card</p><h2 class="fo-final__h">Locked<br>in</h2>'
            '<p class="fo-final__bet">20 on %s</p><p class="fo-final__sub">Saved. Change any game right up until it kicks off.</p>'
            '<div class="fo-actions"><button class="fo-btn fo-btn--solid">See the Board</button><button class="fo-btn">Change something</button></div></section>'
            '<h3 class="fo-day fo-day--list"><span>Your card</span></h3><ol class="fo-sealeds">%s</ol>%s</div>'
            % (header("fo"), p["loud"], p["ink"], inv(p), p["id"], e(p["school"]), rows, tabbar("fo")))
