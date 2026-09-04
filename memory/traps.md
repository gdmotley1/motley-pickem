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

## Weekly pool is EVERY game, best 20 pre-selected, one-tap swaps

Dad opens the admin screen and sees 20 games already chosen plus every other FBS game in
the week, about 70 more. He swaps what he wants and publishes.

**Why:** Grant's call, widened on 2026-09-04. The pool used to stop at the top 40 by
interest and dropped any game with no posted line before that cut. Both filters were
invisible to the one person they affected. The 2026-09-05 week has 91 FBS games, so 50
never reached his screen.

Grant named West Georgia at Kennesaw State as a game Dad would want. Measured against the
saved fixture it ranked **39th of 70 alternates** by interest and only the top 20 made the
pool, so the cap alone put it out of reach, with its line posted at 22.5. The cap was the
whole cause; do not blame the no-line filter for this one. The earlier note here already
said to widen the pool rather than retune the interest score if this happened.

**How to apply:** `suggest_slate.SLATE_SIZE` is 20 and there is no pool cap. `select_slate`
still draws the auto-20 from `usable`, which requires a tier and therefore a line, so a
no-line game is never auto-selected but can always be added by hand. Ninety rows do not
scroll well on a phone, so the Setup screen carries a search box and conference filters;
do not remove them without shrinking the pool again.

## Both sync jobs must freeze odds, and both must split their upserts

`sync_slate` upserted whatever ESPN last said, without `freeze_odds`. ESPN drops the odds
block once a game is final, so rebuilding a week mid-week nulled `spread_line`,
`favorite_abbr` and `over_under` on every game already played.

**Why:** it never bit while the pool was a fixed 40 built once on Monday. Widening the
pool to every game made a mid-week rebuild an ordinary thing to do, and on 2026-09-04
that rebuild would have erased the line on 38 of the 40 week 1 games the family had
already picked against, with 80 picks stored. `sync_scores` has guarded this since
migration 006; `sync_slate` was simply missed. The fix then failed live with
`PGRST102: All object keys must match`, because freezing removes keys from some rows and
not others and PostgREST rejects a bulk insert whose objects differ in shape. That is
exactly why `sync_scores` sends two batches, and the comment saying so was already in the
file, three functions down, unread.

**How to apply:** any new path that upserts `games` needs both halves. Freeze with
`freeze_odds(row, state)`, then send the frozen and unfrozen rows as separate
`sb.upsert` calls. `tests/test_sync.py` now asserts both: that a played game keeps its
line through a rebuild, and that every batch carries identical keys. Read the sibling
function before adding a third one.

**Before touching live data, snapshot it.** The week 1 rebuild was done against a saved
copy of the games and pick counts, then diffed: 40 to 91 games, zero lines lost, zero
`in_slate` changes on the published week, zero graded winners lost, 80 picks unchanged.
That diff is the only reason "nothing was lost" is a fact rather than a hope. See
[[never-wipe-family-data]].

## ESPN has no pre-game player stats on a game summary

The `leaders` block on `summary?event=<id>` is present but EMPTY until the game has been
played. Once it is played it holds that game's box score, not season form.

**Why:** Grant asked for "top players" in the matchup preview on 2026-09-04 and this is
why the sheet does not have them. Checked both ways: a Week 1 upcoming game returned five
named categories with zero leaders in each, and a completed 2025 game returned
"Ryan Browne 10/19, 76 YDS, 1 INT", which is that single game, not a season line. So the
block is worthless as a preview and misleading as a season stat.

**How to apply:** season leaders do exist, at
`sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/<yr>/types/2/teams/<id>/leaders`,
CORS-open with headshots. It is a `$ref` chase: one call for the team plus one per
athlete, so roughly eight requests to fill one matchup sheet. That belongs in
`scripts/sync_supabase.py` writing a column, not on a phone opening a bottom sheet.
Also note nobody has season stats in Week 1, so it would render blank for the first
week or two whatever the source.

## AP rankings are not in the database, and should not be

`get_slate` returns no rank column, so the `#6` that `TeamPick` has always rendered was
dead in the real app and only ever appeared in the offline demo data.

**Why:** found while wiring the matchup preview. Rather than add a column, the phone now
fetches the AP poll itself from `/rankings`, once per session, cached, ~35KB, and maps it
by ESPN **team id**. The poll moves weekly and independently of the sync job, so asking
ESPN is fresher than a stored column, and it is the same call the Board already makes for
live scores in spirit: display data the client can own.

**How to apply:** `fetchRankings()` in `src/lib/matchup.js`. Map by team id, never by
abbreviation. Unranked teams are absent from the map rather than stored as ESPN's 99
sentinel, so `ranks.get(id)` being undefined is the whole check. A failure is swallowed
on purpose: a missing rank is not worth an error message on a pick screen.

## A global `button { min-height: var(--tap) }` overrides every smaller height

`--tap` is 44px and the rule is on the bare `button` selector. `height: 24px` on a class
does not beat it at any specificity, because min-height constrains the used height rather
than competing with `height` as the same property. Only another `min-height` overrides it,
which is why `.adm__tab { min-height: 38px }` works and `.adm__clear { height: 24px }` did
not.

**Why:** cost real time on 2026-09-04 building the Setup screen's filters. Three controls
were written at their intended size and all three silently came out 44px tall. Only one
was visible as a bug: a 24px round clear button inside a 40px search field rendered as a
24x44 grey ellipse standing proud of the field's rounded edge. The other two, a 30px
conference chip and an inline "show all" text link, just quietly grew, and the text link
padded its line out by more than a whole row.

**How to apply:** never assume a height you set on a button is the height you get.
Measure it: `getBoundingClientRect()` in the preview, not the stylesheet. Then pick one of
three deliberate shapes:

- Free-standing on a phone: take the 44px, it is the right size. `.fchip` does.
- Must look small but stay tappable: keep the 44px button invisible and put the visible
  shape in a child (`.adm__clear span`), or pin the visible size with `min-height` and
  expand the touch area with an absolutely positioned `::after` (`.grow__preview`).
- A text link inside a sentence: opt out with `min-height: 0` and say why (`.adm__reset`).

## Early in the week the auto-slate is SHORT, and that is correct

`--mode slate --next` regularly pre-selects fewer than 20 games. On 2026-09-04 week 2 came
back with 86 games in the pool and only **16** pre-selected, and `maybe_publish` refused
with "16 games in the slate, expected 20".

**Why:** `select_slate` draws only from `usable`, which needs a tier, which needs a posted
line. Vegas had priced 16 of week 2's 86 games that far out. Nothing is broken and the fix
is not to loosen the tier rule: a confidence pool needs a certainty gradient, and a game
with no line cannot be placed on one.

**How to apply:** it resolves on its own as the week approaches, so re-run `--mode slate`
closer to the games. The Setup screen already handles it: all 86 are searchable, the CTA
reads "Add 4 more", and Dad can fill the gap by hand. Do not treat a short auto-slate as a
bug, and do not auto-publish around it. Grant's rule stands: every week needs an explicit
publish step.

## A game with no line still has to be pickable

Eleven of the 91 games in the 2026-09-05 week showed no line when checked on 2026-09-04.
They render "no line" where the spread goes and carry no tier chip.

**Why:** Checked, and worth knowing before chasing it: all eleven were `state=post`. None
was a genuinely unpriced upcoming game. ESPN drops the odds block once a game goes final,
which migration 006 already documents, so this is the same behaviour seen from the pool
side. The consequence is real anyway: a pool rebuilt mid-weekend used to lose every game
already played, and now keeps them. Every downstream consumer has to survive a null
`spread_line`, `favorite_abbr`, `underdog_abbr` and `tier`. `api.spreadLabel` already
returned "no line"; `api.totalLabel` already returned null.

**How to apply:** Auto-pick falls back to the home team when there is no favourite, which
is the rule `migrations/005_autopick_favorite_on_cron.sql` already documents. Auto-rank in
`Picks.jsx` scores a no-line game 0, so it lands mid-table rather than at either extreme.
Never render a tier chip for a null tier: `.arow__meta` is a fixed 18px, so an empty chip
element is fine but a missing one must not change the row height.

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

## ESPN deletes a game's odds the moment it goes final

Not "stops updating" and not "returns the closing line": the whole `odds` block is gone.
Checked on 2026-09-04, every completed game from 3 Sep came back with `details: null` and
`overUnder: null`, while all 68 games still in `pre` that day carried both.

**Why:** the scores job upserts whatever ESPN last said, so a game was having its line
erased by its own kickoff. COLO @ GT went into the database at GT -6.5 and was found
after the game with `spread_line`, `favorite_abbr` and `underdog_abbr` all null. Nothing
noticed, because the Board did not show the spread until the total was added alongside it.
The line for that game was only recoverable because `inputs/slate_2026-09-03_2026-09-06.json`
still held the 18:01Z pre-kickoff pull.

**How to apply:** odds are write-once-until-kickoff. `sync_supabase.freeze_odds` drops
every column in `ODDS_COLUMNS` from the payload for any game past `state = 'pre'`, so
Postgres keeps what it has. A new odds column must be added to `ODDS_COLUMNS` as well as
to `game_row`; `test_every_odds_column_the_row_builder_writes_is_frozen_together` fails if
it is not. The odds also go up in their own batch, because PostgREST rejects a bulk insert
whose objects do not all carry the same keys.
