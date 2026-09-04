# UI patterns

How Motley Pick'em's interface behaves, and the library choices that turned out to
be wrong. Read before changing a screen.


## Visual direction: Slate

Cool blue-grey chrome, white cards, one confident blue, Archivo for display. Tight radii
and a hairline rather than soft shadows. Replaced "Saturday broadcast" (deep field green,
cream page, amber accent, Bitter) on 2026-09-04.

**Why:** Grant asked for "a little sharper and looking polished" and picked Slate from a
board of ten rendered as real pick screens. The warm pass was chosen originally over
modern-sports-app and clean-minimal; this is that reversal, made deliberately.

**How to apply:** This project still does NOT use the house report style. That is for
Fouts executive PDFs; do not import IBM Plex or the burnt-orange accent here.

The theme board that produced this choice is an artifact, and the other nine are still
live in it if a future pass wants one:
https://claude.ai/code/artifact/e417012f-a327-4883-b138-d95957d1b31a

## Components name jobs, never colours

`src/app.css` may use only semantic tokens. The palette ramp (`--s-*`, `--c-*`, `--b-*`,
`--gr-*`, `--rd-*`) is private to `src/theme.css`.

**Why:** app.css used to reach into the ramp directly, 97 times, with names like `--g-600`
and `--n-200`. Every one baked "the chrome is green" and "the page is warm" into the
component using it, so switching to Slate meant editing 97 declarations before a single
colour moved. `tests/test_theme.py` now fails if any component names a ramp position, if
a token is used but never defined, or if the display face is not in the font link.

Two pairs are kept apart on purpose, having been one colour under the warm palette:

- `--pick*` is the selection ("you chose this", blue); `--good*` is the result ("this was
  right", green). They collapsed before, and a correct pick briefly rendered blue points
  on a green wash when the palette moved.
- `--on-field` is text on the dark chrome; `--surface` is a raised white surface. Same
  value in a light theme, opposite in a dark one, which is what makes a night mode a
  palette change rather than a rewrite.

**How to apply:** need a colour with no token? Add a semantic one to theme.css named for
its job. Chip modifiers follow the same rule: `.chip--accent`, `.chip--good`, `.chip--bad`,
not `--amber`, `--green`, `--red`. Contrast is measured, not eyeballed: `--ink-3` carries
the 9.5px meta line and was darkened to hold 4.8:1 on a well.

The PWA's install splash and Android status bar are painted from `static/manifest.webmanifest`
and the `theme-color` meta in `index.html`, neither of which is CSS, so both must move with
`--field`. A test asserts all three agree.

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

## The matchup preview is a bottom sheet, opened from a quiet pill

Every game row on the choose step carries a small "Preview" pill at the right of its meta
line. Tapping it opens a `Sheet` with the AP ranks, ESPN's win probability, both records,
each team's last five games and the venue and weather.

**Why:** Grant asked for it on 2026-09-04. The win probability leads because the only
question the sheet exists to answer is how confident to be, and "ESPN says 65%" settles
whether a game is your 20 or your 14 better than any single team statistic.

**How to apply:** the pill is deliberately the quietest thing on the card. The two team
buttons are the point of that row and nothing may compete with them for a thumb, so the
pill is 18px, uses the meta line's existing height, and gets a real 44px tap target from
an absolutely positioned `::after` rather than by growing the row. Data comes from
`src/lib/matchup.js`; the sheet must render with any of win probability, form, weather or
venue missing, because ESPN legitimately returns none of them for a finished game.

**Not available after you submit.** The preview lives in `ChoosePhase`, so once picks are
in, the `Done` screen has no previews and no ranks. That was the scope Grant asked for
("when you're picking games"). Adding it to `Done` and `Board` is a small change if it
ever comes up.

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

## The service worker caches the shell and nothing that talks to a server

`static/sw.js`. Shell and hashed assets cached, logos cached on first use, and every
non-GET or cross-origin request passed straight through untouched.

**Why:** the app had a manifest and icons from the start, so it installed to a home
screen and then behaved like a bookmark: every cold launch re-fetched the bundle and the
logos, and on a weak signal it did not open at all. Added 2026-09-04.

The passthrough is the part that matters. Locking and pick visibility are Postgres RLS
decisions, and a cache is the one thing that could quietly serve a result those policies
already refused. Supabase RPCs are POSTs and ESPN is cross-origin, so two early returns
in the fetch handler keep both out entirely. The cost is deliberate: offline you get the
app instantly and its own error states where data would be, never yesterday's scores
dressed up as today's.

**How to apply:** `tests/test_service_worker.py` asserts the negatives, so a change that
starts caching authenticated data fails the gate. Three details that are easy to undo by
accident:

- The logo cache is NOT versioned. 276 marks, about 12MB, none of which change when the
  app deploys. Tying it to `VERSION` re-downloads a week of logos every time.
- `index.html` is network-first because it carries no content hash. Cache-first on it
  means a deploy is never picked up.
- `skipWaiting` plus `clients.claim` is safe *only* because the build emits one bundle
  with no code splitting, so there is no lazy chunk a swap could miss. Introduce code
  splitting and this needs rethinking.

Registration is production-only, in `src/main.jsx`. In dev the worker would serve cached
modules over the top of an edit, which reads as "my change did nothing", and it would sit
under the `outputs/harness/` pages whose whole purpose is a stubbed network.

## Team logos are vendored into the repo

All 138 FBS teams, light and dark, 276 PNGs, about 12MB in `static/logos/<espn_team_id>.png`.

**Why:** Grant asked for real logos and for every FBS team loaded. Vendoring means instant
render, no hotlinking to ESPN's CDN, and the PWA works offline.

**How to apply:** Reference by ESPN team id. Do NOT precache all 276 in the service worker;
only about 40 teams appear in a given week. Cache on first use.
