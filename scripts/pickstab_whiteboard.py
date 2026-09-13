"""Direction 6: Whiteboard. The coach's board in the film room."""
from __future__ import annotations

from pickstab_kit import (CARD, LIFTED, PICKED_MIDWEEK, RANKED, days, disc, e, me, rank_badge, state)
from pickstab_kit import ICONS
from pickstab_kit import winners as drawn

NAME = "Whiteboard"
PITCH = ("The cartoon one: the coach&rsquo;s whiteboard. Teams are magnets, your pick gets circled in red marker and the "
         "other side crossed out, progress is tally marks, and the Matchup button is a sticky note taped to the board. "
         "Points become the depth chart, and locking in is the game plan, checked off.")
BUILT = "Permanent Marker for the handwriting and Kalam for the notes, both new. Marker red, marker blue, sticky-note yellow."

CIRCLE = ('<svg class="wb-circle" viewBox="0 0 200 100" preserveAspectRatio="none" aria-hidden="true"><path d="M118 7C178 6 197 28 191 52'
          'C184 84 60 97 18 72C-5 57 5 22 64 10C98 3 142 5 164 13" fill="none" stroke="#d7261e" stroke-width="4.5" stroke-linecap="round" '
          'vector-effect="non-scaling-stroke"/></svg>')
CROSS = ('<svg class="wb-cross" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M14 18C38 40 62 62 88 84M86 16'
         'C62 40 40 62 12 86" fill="none" stroke="#1b2a4a" stroke-width="3.5" stroke-linecap="round" vector-effect="non-scaling-stroke" opacity=".55"/></svg>')
UNDERLINE = ('<svg class="wb-under" viewBox="0 0 120 10" preserveAspectRatio="none" aria-hidden="true"><path d="M3 6C20 3 38 8 58 5S96 3 117 6" '
             'fill="none" stroke="#d7261e" stroke-width="3.5" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')
SQUIGGLE = ('<svg class="wb-squiggle" viewBox="0 0 120 10" preserveAspectRatio="none" aria-hidden="true"><path d="M2 6C12 2 20 9 30 5S48 2 58 6'
            ' 76 9 88 4 108 3 118 6" fill="none" stroke="#1565c0" stroke-width="3" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')
CHECK = ('<svg class="wb-check" viewBox="0 0 120 100" aria-hidden="true"><path d="M8 58C22 66 34 78 44 92C60 58 84 26 114 6" fill="none" '
         'stroke="#1e8a3e" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/></svg>')
ARROW = ('<svg class="wb-arrow" viewBox="0 0 60 40" aria-hidden="true"><path d="M56 30C40 34 22 30 10 14M10 14l2 14M10 14l13 3" fill="none" '
         'stroke="#1565c0" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def magnet(tid, size):
    return disc(tid, size, "pk-disc wb-magnet")


def header():
    return ('<header class="wb-hdr"><div><span class="wb-hdr__title">Motley Pick&rsquo;em</span><span class="wb-hdr__week">Week 1 &middot; 20 games</span></div>'
            '<span class="wb-hdr__me">%s<span>Grant</span></span></header><div class="wb-frame" aria-hidden="true"></div>' % me(30, "pk-disc wb-magnet"))


def tabbar():
    tabs = "".join('<span class="wb-tab%s"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" aria-hidden="true">%s</svg><span>%s</span></span>'
                   % (" is-on" if k == "Picks" else "", v, k) for k, v in ICONS.items())
    return '<nav class="wb-tabs" aria-label="Tabs"><div class="wb-tray" aria-hidden="true"><i></i><i></i><i></i></div>%s</nav>' % tabs


def tally(n):
    groups = []
    while n > 0:
        k = min(5, n)
        groups.append('<span class="wb-tg">%s%s</span>' % ("<i></i>" * min(k, 4), "<s></s>" if k == 5 else ""))
        n -= k
    return "".join(groups)


def team(c, s):
    t = c[s]
    st = state(c, s)
    mark = CIRCLE if st == "is-picked" else CROSS if st == "is-other" else ""
    under = UNDERLINE if st == "is-picked" else ""
    return ('<button class="wb-team %s" aria-pressed="%s">%s<span class="wb-name">%s<span class="wb-school">%s%s</span></span>%s</button>'
            % (st, "true" if st == "is-picked" else "false", magnet(t["id"], 48), rank_badge(t, "wb-rank"), e(t["school"]), under, mark))


def game(c):
    return ('<article class="wb-game" data-m="game"><div class="wb-meta"><span class="wb-note">%s &middot; %s &middot; <b>%s</b></span>'
            '<button class="wb-sticky" aria-label="Matchup preview: %s"><span class="wb-shine" aria-hidden="true"></span>Matchup &rarr;</button></div>'
            '<div class="wb-teams">%s<span class="wb-vs" aria-hidden="true">%s</span>%s</div></article>'
            % (e(c["when"]), e(c["tv"]), e(c["spread"]), e(c["key"]), team(c, "away"), "vs" if c["neutral"] else "@", team(c, "home")))


def winners():
    groups = "".join('<h3 class="wb-day"><span>%s%s</span></h3>%s' % (d, SQUIGGLE, "".join(game(c) for c in rows)) for d, rows in days(drawn()))
    return ('<div class="wb">%s<div class="wb-top"><h2>Week 1 game plan</h2><p class="wb-count"><span class="wb-tally" aria-hidden="true">%s</span>'
            '<span><b>%d</b> of 20 picked</span></p></div>%s'
            '<p class="wb-more">%d more games below &darr;</p><div class="wb-go-wrap"><button class="wb-go" disabled>%d still to pick</button></div>%s</div>'
            % (header(), tally(PICKED_MIDWEEK), PICKED_MIDWEEK, groups, len(CARD) - 6, len(CARD) - PICKED_MIDWEEK, tabbar()))


def points():
    rows = []
    for c in RANKED:
        p = c["pick"]
        lifted = c["key"] == LIFTED
        cue = '<span class="wb-cue is-moving">%smoving</span>' % ARROW if lifted else '<span class="wb-cue">here</span>'
        rows.append('<li class="wb-row%s" data-m="rank"><button class="wb-row__hit"><span class="wb-pts">%d</span>%s'
                    '<span class="wb-who"><b>%s</b><span>over %s &middot; %s</span></span>%s</button></li>'
                    % (" is-lifted" if lifted else "", c["pts"], magnet(p["id"], 36), e(p["school"]), e(c["opp"]["abbr"]), e(c["spread"]), cue))
    lifted = next(c for c in CARD if c["key"] == LIFTED)
    return ('<div class="wb">%s<div class="wb-rankhead"><button class="wb-chip">&larr; Winners</button><button class="wb-chip">Reset to spread</button></div>'
            '<div class="wb-intro"><h2>Depth chart</h2><p>Already sorted by the spread, so the top game is worth <b>20</b> and the bottom '
            '<b>1</b>. Tap a game, then tap where it goes.</p></div><ol class="wb-ranks">%s</ol>'
            '<div class="wb-lift"><span>Moving <b>%s</b>. Tap a row to give it those points.</span><button class="wb-cancel">Cancel</button></div>%s</div>'
            % (header(), "".join(rows), e(lifted["pick"]["school"]), tabbar()))


def locked():
    top = RANKED[0]
    rows = "".join('<li class="wb-sealed"><span class="wb-pts wb-pts--sm">%d</span>%s<span class="wb-who"><b>%s</b><span>over %s &middot; %s</span></span></li>'
                   % (c["pts"], magnet(c["pick"]["id"], 30), e(c["pick"]["school"]), e(c["opp"]["abbr"]), e(c["when"])) for c in RANKED)
    return ('<div class="wb">%s<section class="wb-plan">%s<h2>Game plan<br>set!</h2><p>Saved. Change any game right up until it kicks off.</p>'
            '<div class="wb-coach">%s<span>Coach&rsquo;s note: 20 on %s.</span></div>'
            '<div class="wb-actions"><button class="wb-note-btn wb-note-btn--yellow">See the Board &rarr;</button>'
            '<button class="wb-note-btn wb-note-btn--pink">Change something</button></div></section>'
            '<h3 class="wb-day"><span>Your depth chart%s</span></h3><ol class="wb-sealeds">%s</ol>%s</div>'
            % (header(), CHECK, magnet(top["pick"]["id"], 34), e(top["pick"]["school"]), SQUIGGLE, rows, tabbar()))
