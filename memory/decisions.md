# Decision Log

Locked calls that are true every session. Each states the decision, **Why**, and
**How to apply**. This file is @-imported by CLAUDE.md, so it stays short: anything
situational belongs in the files below and is read on demand.

- `memory/ui-patterns.md` — how the interface behaves and what not to reach for
- `memory/traps.md` — bugs that already cost time, and the guards added for them

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

**How to apply:** ESPN is the source of truth for games, spreads and scores. `groups=80`
is FBS; query by `dates=YYYYMMDD`, one call per day, and dedupe.

## Weeks follow ESPN's published calendar, never arithmetic

`scripts/cfb_weeks.py` fetches the official regular-season calendar and every other
script takes `--week N`, `--current` or `--next` from it.

**Why:** Grant asked for real CFB weeks because of odd Thursday cutoffs, and the calendar
has four traps a hand-rolled version gets wrong:
1. Week 1 of 2026 runs 22 Aug to 8 Sep, seventeen days, because it absorbs Week 0.
2. Boundaries land about 3am ET Monday, after Sunday night games, so a late Sunday game
   belongs to the week that is ending and a Thursday game to the week that opened Monday.
3. The boundary hour shifts by one when daylight saving ends in November.
4. ESPN ends a week at HH:59 and opens the next at HH+1:00, leaving a 60 second hole.

The app had hard-coded "Week 2" for a slate that is actually Week 1.

**How to apply:** Never compute a week number. `week_for()` snaps the 60 second hole
forward; `date_range()` clamps windows over 9 days to their trailing days, because a
pick'em week is one weekend and Week 1 holds two. The label reaches the UI via `get_week`.

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
