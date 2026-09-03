# UI patterns

How Motley Pick'em's interface behaves, and the library choices that turned out to
be wrong. Read before changing a screen.


## Visual direction: Saturday broadcast

Warm and traditional. Deep field greens, cream, serif display headlines, a little
college-football-on-CBS nostalgia. Not a dark neon betting app.

**Why:** Chosen over modern sports app, clean minimal, and family trophy room.

**How to apply:** This project does NOT use the house report style. That style is for Fouts
executive PDFs. Do not import IBM Plex or the burnt-orange accent here.

## Mobile only. There is no desktop layout.

Every screen is designed for a 375-430px phone: single column, bottom nav in thumb reach,
44px minimum targets, safe-area insets, nothing that depends on hover. Wider viewports
centre a phone-width column rather than reflowing.

**Why:** Grant said so directly on 2026-09-03: "this is mobile view strictly." The app is
installed to a home screen; nobody will open it on a laptop.

**How to apply:** Verify at 375x812. Do not add breakpoints that rearrange content for a
wide screen; the only wide-screen rule is centring and a drop shadow.

## Pick UX is the centerpiece and is Claude's call

Grant asked for maximum polish rather than choosing a mechanic: "very slick and nice and
smooth." Shape landed on: swipeable card stack to choose 20 winners, then a drag-to-rank
screen with spring physics and live point recalculation, plus an "auto-rank by spread"
button that pre-orders the 20 by Vegas confidence so only disagreements need tweaking.

**Why:** Ranking 20 games by hand on a phone is the actual chore this project exists to
remove. Auto-rank turns ten minutes into about sixty seconds.

**How to apply:** Treat the pick flow as the highest-quality surface in the app. Drafts
autosave continuously so nothing is ever lost mid-flow.

## The choose step is a list, not a card stack

Picking the 20 winners is a vertical list of game rows, each with two large tap targets.

**Why:** The first build was a one-card-at-a-time swipeable stack. It photographed well and
was wrong in the hand: most of the viewport sat empty, you could not see what was coming,
and twenty sequential screens is slower than one scroll. It also had a real bug, with
AnimatePresence leaving exited cards in the DOM. The list fixed the speed, the dead space
and the bug at once.

**How to apply:** Do not reintroduce a card stack for the 20 winners. Ranking stays a
drag-to-sort list, which is the step that genuinely needs gesture.

## Auto-rank by spread is the feature that makes this worth using

One button orders the 20 picks by how confident Vegas is, biggest favourite first, and
demotes any underdog you took. You then drag only what you disagree with.

**Why:** Ranking twenty games by hand on a phone is the actual chore this app exists to
remove. Verified on the real 2026-09-05 slate: Georgia at -46.5 lands on 20 points, and a
Stanford pick against a 24.5-point line correctly falls to 1.

**How to apply:** `autoRank` in `src/screens/Picks.jsx`. Score is `+line` when the pick is
the favourite and `-line` when it is the underdog. Keep it a suggestion, never forced.

## Confidence points: tap to lift, tap to place. No dragging.

The ranking screen arrives already sorted by the spread. Tapping a game lifts it, every
other row becomes a target labelled "here", and tapping one gives the lifted game that
row's point value. Tapping the lifted game again, or Cancel, puts it back.

**Why:** Drag-to-reorder was unusable on a phone and Grant called it out. Three faults at
once: the whole row was the drag handle so every touch fought the page scroll, the touch
sensor needed a 150ms press-and-hold that read as nothing happening, and the dragged row
was pinned inside a list twice the height of the viewport, which made moving a game from
20th to 1st effectively impossible. Ranking twenty items by drag is a poor interaction
even done well.

The design turns on one observation: the left column already shows the points, so while a
game is lifted, tapping a row reads as "give my game that many points" rather than "move
to that index". People think in points, not positions. Grant expects to move only two to
five games a week, so the flow optimises for one fast, unambiguous move.

**How to apply:** dnd-kit is uninstalled; do not reintroduce dragging. Auto-rank is
applied on arrival rather than behind a button, with "Reset to spread" to get back. The
manual/auto distinction is the `touched` flag in the draft: once a player moves anything,
the spread sort stops re-applying.

## Repeated rows must be pixel-identical, chip or no chip

Any badge inside a list row is fixed at 18px tall and its meta line is fixed to match.

**Why:** Grant spotted uneven rows on the slate builder. Measured: rows without a badge
were 61px and rows with the "ESPN top" badge were 67px, because the chip's vertical
padding grew the line box. The fix keeps the badge, which carries real information.

**How to apply:** `.chip` has `height: 18px` and no vertical padding. `.arow__meta` and
`.grow__meta` set `height` and `line-height` to 18px. When adding any new badge, measure
a list with and without it rather than eyeballing: the difference was only 6px and was
invisible in a screenshot until measured. The Board goes further and renders a row for
every claimed player, so a game card's height never depends on how many people picked.

## The Board lists all twenty games, locked ones included

A game that has not kicked off shows greyed with a lock icon and its kickoff time, your
own pick and points visible, everyone else masked as "hidden".

**Why:** Grant asked for it, and it is better than the empty state it replaced. The board
is the whole week at a glance, you can check your own card against it before kickoff, and
the lock icon makes the reveal rule obvious rather than something to explain.

**How to apply:** Visibility is still the server's decision. `get_board` returns nothing
for an unplayed game; the locked row is drawn from `get_slate`, which only ever contains
the viewer's own pick. Never render another player's pick from a client-side filter.

## The ranking is restored from the server, not just the local draft

On load, `Picks` rebuilds `order` from each game's saved `my_confidence`, falls back to a
local draft when one exists, and only then to the spread sort.

**Why:** Grant reported that picks saved but confidence points did not. The client read
the ranking from the local draft alone, and a successful submit clears that draft, so
reopening the app found nothing and re-applied the spread sort. The confidence values
were correct in Postgres the whole time; the client was discarding them on load.
Verified by moving Georgia from 20 to 11, reloading, and confirming both the app and the
database still read 11.

**How to apply:** `get_slate` already returns `my_confidence`. Anything that rebuilds the
order must prefer it, and must set `orderTouched` so the spread sort cannot overwrite a
saved ranking.

## Do not use framer-motion AnimatePresence in this app

Screen transitions animate in on a fresh `key` with no exit. Sheets and toasts are the
`Sheet` and `Toast` components in `src/components/ui.jsx`, which own their own mount and
unmount with a CSS animation plus an `animationend` handler and a timer as a safety net.

**Why:** Under React 19, AnimatePresence exits did not complete. Two real failures came
from it, both found in the browser rather than by reading code:
1. Tab switching. The tab button flipped to active and the outgoing screen froze at its
   exit transform forever, so the new screen never mounted. Still broken after 2.5s.
2. Bottom sheets. A closed sheet stayed in the DOM, leaving its `position: fixed`
   full-screen scrim over the page and swallowing every subsequent tap.

**How to apply:** Never wrap a screen or an overlay in AnimatePresence here. framer-motion
is still fine for what it does well in this app: `layoutId` on the pick check badge and
simple enter animations. If an overlay ever needs to animate out, extend `Sheet` rather
than reaching for AnimatePresence.

## position: fixed resolves against a transformed ancestor, not the viewport

Overlays (Sheet, Toast, the Moving bar) render through `Portal` in
`src/components/ui.jsx`, which portals to document.body.

**Why:** The screen wrapper is a motion.div that keeps a transform after animating, which
makes it the containing block for any fixed descendant. The Moving bar landed at y=1533
in an 812px viewport, completely off screen.

**How to apply:** Any new fixed overlay goes through `Portal`. Do not assume `position:
fixed` is relative to the screen inside an animated subtree.

## Never animate an overlay's opacity from 0

Entrance animations move the element; they do not fade it in.

**Why:** A hidden or backgrounded tab pauses CSS animations. The Moving bar froze
half-transparent with the list showing through it. `liftbarIn` translates only.

**How to apply:** Keyframes for anything that must stay readable should animate transform
alone, so a paused animation still leaves the element fully opaque.

## Team logos are vendored into the repo

All 138 FBS teams, light and dark, 276 PNGs, about 12MB in `static/logos/<espn_team_id>.png`.

**Why:** Grant asked for real logos and for every FBS team loaded. Vendoring means instant
render, no hotlinking to ESPN's CDN, and the PWA works offline.

**How to apply:** Reference by ESPN team id. Do NOT precache all 276 in the service worker;
only about 40 teams appear in a given week. Cache on first use.
