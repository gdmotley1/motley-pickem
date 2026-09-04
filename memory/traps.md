# Traps

Bugs that already cost real time here, each with the guard that now catches it.
Read when something behaves strangely, especially against the live database.


## Hosting: GitHub Pages front end, Supabase back end

Static React build on GitHub Pages, installed to phone home screens as a PWA.

**Why:** Grant's existing pattern (motley-tech, comvoy-fire) and free.

**How to apply:** All secrets that reach the browser must be the Supabase anon key with RLS
doing the real work. The service key never ships to the client.

## Week of 2026-09-05 is backfilled, not played live

The family plays this week on paper. Grant's dad's 20 games and everyone's picks get keyed
in so the site launches with real history and a populated leaderboard.

**Why:** Decided at 1:50 PM ET on 2026-09-03, about five hours before the first game
(Kennesaw State, 7:00 PM ET). Not enough runway to build, deploy, and get the whole family
to install and pick.

**How to apply:** The admin backfill screen is a launch requirement, not a nice-to-have. It
must accept past games with results already known and set picks without tripping lock rules.

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

## Verify in the browser, and beware a hidden pane

The Browser pane throttles `setTimeout` when `document.hidden` is true, which made the
sheet look stuck when it was not.

**Why:** Several minutes went into chasing a phantom bug. `document.hidden` was the tell.

**How to apply:** When a timing-dependent check looks wrong, read `document.hidden` first.
Front the tab, use generous waits, and keep browser scripts short: long ones hit the
45-second tool cap once timers are throttled.

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

## Every SECURITY DEFINER function pins `search_path = public, extensions`

**Why:** Supabase installs extensions into the `extensions` schema, not `public`. Pinning
to `public` alone made the entire migration fail on the very first function:

    ERROR: 42883: function digest(text, unknown) does not exist

pgcrypto supplies `crypt`, `gen_salt`, `digest` and `gen_random_bytes`, which hash the
PINs and session tokens, so nothing worked. Dropping the pin would have fixed it and
opened a search_path hijack on a SECURITY DEFINER function, so the answer is to name both
schemas. On a plain Postgres where pgcrypto lands in `public`, a missing `extensions`
schema in the search path is silently ignored, so the same line is correct there too.

**How to apply:** Never write `set search_path = public` alone in this project.
`test_security_definer_functions_can_reach_pgcrypto` fails on the bare form, and
`test_search_path_is_always_pinned` fails if a definer function has no pin at all.

## migrations/ALL.sql is what actually gets run

Generated by `scripts/build_combined_migration.py` from the numbered migrations.

**Why:** Setup meant pasting three files in the right order, and the guide referenced them
as plain text with no clickable links, so Grant could not open any of them. One paste is
one chance to get it wrong instead of three.

**How to apply:** Edit a numbered migration, then regenerate. A test compares the file on
disk to a fresh build and fails if it has drifted, so it cannot go stale silently.

## Test data must be cleaned up after live verification

Live checks claim a seat, publish, and save picks. Every one of those ends by deleting
the picks and sessions and resetting the player row so all four seats read unclaimed.

**Why:** the family shares one four-seat roster. A leftover ZZTEST seat is one of only
four, and a leftover pick row would corrupt the standings.

**How to apply:** confirm `list_seats` shows four empty seats and `picks` is empty before
finishing.

## `position: sticky` can never pin anything in this app

`.app__body` is `overflow-y: auto`, so it is the scrollport every sticky descendant
resolves against. It never actually scrolls: `.app` is sized by `min-height: 100dvh`, so
the flex child grows with its content and the **document** is what moves. A sticky element
inside it therefore scrolls away like any static one, silently.

**Why:** the week score bug was built as `position: sticky; top: 0` and looked correct in
the markup. In the browser it scrolled off the top with the games. The same fact is why
`.tabbar` is `position: fixed` rather than sticky. Two further traps stack on top of it:
`fixed` inside the screen wrapper anchors to that motion.div's transform, not the viewport,
so it needs the `Portal` helper; and the header is sticky and opaque at `z-index: 30`, so
anything pinned to `top: 0` sits behind it and is never seen.

**How to apply:** anything that pins goes `Portal` + `position: fixed`, laid out on the
same centred column as `.tabbar` (`left: 50%; translateX(-50%); max-width: 460px`), with
`top` set from the measured header height. `useHeaderOffset` in
`src/components/WeekScore.jsx` does that measurement; do not hard-code the height, it is
padding plus two lines of type plus the safe-area inset.
