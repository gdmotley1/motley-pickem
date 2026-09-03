# Decision Log

Permanent decisions, recorded so they are not re-litigated in a future session.
Each entry states the decision, **Why**, and **How to apply**.

## Scope: family confidence pool, regular season only

20 games a week, straight-up winner, confidence points 1 to 20 each used exactly once.
Pool ends after conference championship weekend. No bowls, no Playoff.

**Why:** Grant's family already runs this on paper and the Notes app. Keeping the slate at
a fixed 20 every week means the confidence range never changes and the data model stays
simple. Postseason was explicitly declined, which removes variable slate sizes entirely.

**How to apply:** Assume exactly 20 games per week. Do not build flexible slate sizing or
bowl handling unless Grant reopens it.

## The spread is displayed, never picked against

Picks are straight-up winners. The Vegas spread is shown on every game for context and is
used by the app for auto-ranking, upset detection, and the underdog auto-pick rule.

**Why:** This is how the family already plays. Against-the-spread would change the game.

**How to apply:** Never grade a pick against the spread. Spread is an input to UX and stats
only.

## Slate is app-suggested, Dad-approved

The app ranks every FBS game for the upcoming week and pre-fills the best 20. Dad opens an
admin screen, swaps any game out, and hits Publish. Nothing is visible to players until he
publishes.

**Why:** Dad picking the 20 is part of the family ritual and he must be able to force in
games the family cares about. Full automation would remove his role; picking from scratch
keeps the busywork this project exists to kill.

**How to apply:** Every week needs an explicit publish step. Never auto-publish a slate.

## Picks lock per game, at that game's kickoff

A game becomes read-only the moment it kicks off. Games later in the week stay editable.

**Why:** Matches how the family already thinks about it. Accepted tradeoff: someone who has
not submitted can see a Thursday result before assigning points.

**How to apply:** Lock must be enforced server-side in a Postgres RLS policy comparing
`now()` to kickoff. Never trust a client-side lock; browser devtools would defeat it.

## Missed picks auto-fill the UNDERDOG at the lowest unused confidence

At kickoff, any game a player has not picked is filled with the Vegas underdog and assigned
the lowest confidence value they have not spent.

**Why:** Grant deliberately overrode the suggested "favorite" default. The underdog is the
lower-probability outcome, so forgetting is genuinely punished, but nobody eats a zero week
and quits.

**How to apply:** Underdog, not favorite. If the game is a pick'em with no favorite, take the
road team. This runs in the sync job at kickoff, not in the browser.

## Picks are hidden until each game locks

You see only your own picks. Everyone else's reveal game by game at kickoff.

**Why:** No copying, no sandbagging.

**How to apply:** RLS must enforce this. A player may select another player's pick row only
where that game's kickoff has passed. Do not filter in the client.

## Ties stand. Co-champions.

No tiebreaker of any kind, weekly or season. Two people can share a week.

**Why:** Grant chose this over both a records-based tiebreak and a total-points guess. It
keeps the submission to winners plus ranking, with no extra required input.

**How to apply:** Never add a tiebreaker field to the pick form. Standings show shared ranks.

## Sign-in is name plus 4-digit PIN

Tap your name on a roster tile, enter a PIN, stay signed in on that phone indefinitely.

**Why:** Works for every age in the family, no email round trip, no password resets.

**How to apply:** PINs are hashed, never stored plain. Session persists in local storage.
This is family-grade auth on a private link, not a security boundary worth hardening further.

## Supabase on a NEW free account, separate from the paid one

Postgres, RLS, realtime, Edge Functions, pg_cron.

**Why:** Grant explicitly does not want this project billed to his existing paid Supabase
plan at $10/month. It must live on its own free-tier account.

**How to apply:** Credentials go in this project's own `.env`. Do NOT reuse `SUPABASE_URL`
or the keys from `comvoy/.env`. That is the paid account.

## Game data comes from the keyless ESPN scoreboard API

`site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard`
gives schedule, kickoff times, consensus spread, live and final scores, and logos.

**Why:** Verified working on 2026-09-03 with no API key and no account. CollegeFootballData
would need a key and adds a signup step for data ESPN already returns.

**How to apply:** ESPN is the source of truth for games, spreads, and scores. `groups=80`
is FBS. Query by `dates=YYYYMMDD`, one call per day, and dedupe. CFBD stays an optional
later enrichment for rankings and records only.

## Hosting: GitHub Pages front end, Supabase back end

Static React build on GitHub Pages, installed to phone home screens as a PWA.

**Why:** Grant's existing pattern (motley-tech, comvoy-fire) and free.

**How to apply:** All secrets that reach the browser must be the Supabase anon key with RLS
doing the real work. The service key never ships to the client.

## Visual direction: Saturday broadcast

Warm and traditional. Deep field greens, cream, serif display headlines, a little
college-football-on-CBS nostalgia. Not a dark neon betting app.

**Why:** Chosen over modern sports app, clean minimal, and family trophy room.

**How to apply:** This project does NOT use the house report style. That style is for Fouts
executive PDFs. Do not import IBM Plex or the burnt-orange accent here.

## Pick UX is the centerpiece and is Claude's call

Grant asked for maximum polish rather than choosing a mechanic: "very slick and nice and
smooth." Shape landed on: swipeable card stack to choose 20 winners, then a drag-to-rank
screen with spring physics and live point recalculation, plus an "auto-rank by spread"
button that pre-orders the 20 by Vegas confidence so only disagreements need tweaking.

**Why:** Ranking 20 games by hand on a phone is the actual chore this project exists to
remove. Auto-rank turns ten minutes into about sixty seconds.

**How to apply:** Treat the pick flow as the highest-quality surface in the app. Drafts
autosave continuously so nothing is ever lost mid-flow.

## Week of 2026-09-05 is backfilled, not played live

The family plays this week on paper. Grant's dad's 20 games and everyone's picks get keyed
in so the site launches with real history and a populated leaderboard.

**Why:** Decided at 1:50 PM ET on 2026-09-03, about five hours before the first game
(Kennesaw State, 7:00 PM ET). Not enough runway to build, deploy, and get the whole family
to install and pick.

**How to apply:** The admin backfill screen is a launch requirement, not a nice-to-have. It
must accept past games with results already known and set picks without tripping lock rules.

## Four self-claimed seats, no auth provider

The app ships with 4 empty seats. First person to open it taps an empty tile, enters a name
and a 4-digit PIN, and that seat is theirs. The device remembers them from then on. If the
session is gone (new phone, cleared data, switching users) they get the 4-name screen and
tap their own tile.

**Why:** Grant asked for exactly this. It gives four distinct identities with zero signup,
zero email, and nothing to reset. Nobody has to be provisioned ahead of time.

**How to apply:** Seed `players` with 4 rows, name and pin_hash NULL. Claiming is an UPDATE
that only succeeds `WHERE name IS NULL`, so a claimed seat can never be taken over. PIN
hashes are never sent to the client; verification happens in a Postgres RPC that returns a
session token. Provide a visible "not you? switch" control on every screen.

## Seats 1 and 2 are admins

Seat 1 is Grant, seat 2 is his dad. Both can build and publish the weekly slate. Seats 3
and 4 are players only.

**Why:** Chosen over a separate commissioner code and over open admin. Two admins means
Grant can fix things without waiting on his dad.

**How to apply:** `is_admin` is a column on the seat, set at seed time, not something a
claimer chooses. Do not let the claim flow grant admin.

## Weekly pool is 40 games, best 20 pre-selected, one-tap swaps

Dad opens the admin screen and sees 20 games already chosen plus 20 alternates. He swaps
what he wants and publishes.

**Why:** Grant's call. It keeps his dad's editorial role while removing the work of
scanning a 90-game schedule. Measured against Dad's real 2026-09-05 slate, the pool of 40
already contained 17 of his 20 and the auto-selected 20 matched 12.

**How to apply:** `suggest_slate.POOL_SIZE` is 40 and `SLATE_SIZE` is 20. If Dad routinely
has to hand-add games, widen the pool rather than retuning the interest score.

## Slate selection order: Georgia, then SEC, then certainty tiers

1. Georgia's game is always in, whatever the spread.
2. Enough more SEC games to reach 5 SEC games total.
3. The rest fill certainty tiers: 3 toss-ups, 7 close, 3 medium, 4 big, 3 blowouts.

**Why:** Grant asked for "always Georgia, the 5 best SEC games, then the top games." The
tier shape is measured from his dad's own slate, which was well balanced. A confidence pool
where every game is a coin flip, or every game is a blowout, makes the points meaningless.

**How to apply:** `ALWAYS_INCLUDE`, `SEC_MINIMUM`, and `TIERS` in `scripts/suggest_slate.py`.
The tier targets are a shape to aim at, not a hard constraint; backfill by interest score
when a light week cannot fill a tier.

## Team logos are vendored into the repo

All 138 FBS teams, light and dark, 276 PNGs, about 12MB in `static/logos/<espn_team_id>.png`.

**Why:** Grant asked for real logos and for every FBS team loaded. Vendoring means instant
render, no hotlinking to ESPN's CDN, and the PWA works offline.

**How to apply:** Reference by ESPN team id. Do NOT precache all 276 in the service worker;
only about 40 teams appear in a given week. Cache on first use.

## Mobile only. There is no desktop layout.

Every screen is designed for a 375-430px phone: single column, bottom nav in thumb reach,
44px minimum targets, safe-area insets, nothing that depends on hover. Wider viewports
centre a phone-width column rather than reflowing.

**Why:** Grant said so directly on 2026-09-03: "this is mobile view strictly." The app is
installed to a home screen; nobody will open it on a laptop.

**How to apply:** Verify at 375x812. Do not add breakpoints that rearrange content for a
wide screen; the only wide-screen rule is centring and a drop shadow.

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

## Verify in the browser, and beware a hidden pane

The Browser pane throttles `setTimeout` when `document.hidden` is true, which made the
sheet look stuck when it was not.

**Why:** Several minutes went into chasing a phantom bug. `document.hidden` was the tell.

**How to apply:** When a timing-dependent check looks wrong, read `document.hidden` first.
Front the tab, use generous waits, and keep browser scripts short: long ones hit the
45-second tool cap once timers are throttled.

## Named "Motley Pick'em", served from gdmotley1.github.io/motley-pickem

Repo `gdmotley1/motley-pickem`, public. Deployed by pushing the built `dist/` to the
`gh-pages` branch with `bash deploy.sh`.

**Why:** GitHub Actions would be the nicer path, but the `gh` CLI token on this machine
lacks the `workflow` scope and the push is rejected with "refusing to allow an OAuth App
to create or update workflow". The branch deploy needs no extra scope and matches the
pattern already used by motley-tech and comvoy-fire.

**How to apply:** `bash deploy.sh` after any change. To move to CI later, run
`gh auth refresh -s workflow`, move `docs/github-pages-workflow.yml.example` to
`.github/workflows/deploy.yml`, push, and switch the Pages source to "GitHub Actions".
The workflow already reads `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` from repo
variables. The repo is public and holds no secrets: with no VITE_ vars set, the build
ships in local mock mode, and the anon key is public by design once added.

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

## Admin is hidden entirely for non-admins, and gated again in SQL

Seats 1 and 2 see a fourth tab, "Setup". Seats 3 and 4 have a three-tab bar with no
Setup tab and no route to it.

**Why:** Hiding the tab is only cosmetic. The real gate is that `publish_slate` and
`get_pool` both raise unless `_player_for(token).is_admin`, so a non-admin calling the
RPC directly is refused whatever the UI shows.

**How to apply:** Never rely on the hidden tab as the permission. Any new admin action
needs its own `is_admin` check inside the SECURITY DEFINER function, and
`test_admin_only_rpcs_check_is_admin` should be extended to cover it.

## Every RPC the client calls must exist in a migration

`test_every_rpc_the_client_calls_exists_in_sql` parses `src/lib/api.js` for `rpc('name')`
and asserts a matching `create or replace function` in `migrations/`.

**Why:** `get_pool` shipped in the mock only. The Setup screen worked perfectly in local
development and would have thrown the moment the app pointed at the real database,
because the function did not exist. Nothing else would have caught it: the mock is what
development runs against, and the migration is never executed locally.

**How to apply:** Add the SQL function in the same change as the client call. The test is
verified to fail when a migration is removed, so trust it.

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
