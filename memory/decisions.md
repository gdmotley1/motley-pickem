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
used by the app for auto-ranking, upset detection, and the favorite auto-pick rule.

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

**What actually ships is not quite this.** Since 2026-09-03 (commit f9dee99) the GitHub sync
job's `maybe_publish` publishes the pre-selected 20 when nobody has, 18 hours before the
first kickoff, so the family is never locked out of a week. It never touches a published
week or a slate short of 20. Grant has not ruled on whether that squares with the line
above; it was raised with him on 2026-09-22. Weeks 3 and 4 were published by hand, days
ahead, so it has not been needed lately.

## Picks lock per game, at that game's kickoff

A game becomes read-only the moment it kicks off. Games later in the week stay editable.

**Why:** Matches how the family already thinks about it. Accepted tradeoff: someone who has
not submitted can see a Thursday result before assigning points.

**How to apply:** Lock must be enforced server-side in a Postgres RLS policy comparing
`now()` to kickoff. Never trust a client-side lock; browser devtools would defeat it.

## Missed picks auto-fill the FAVORITE at the lowest unused confidence

At kickoff, any game a player has not picked is filled with the Vegas favorite and assigned
the lowest confidence value they have not spent.

**Why:** Reversed on 2026-09-04. For most of the build this was the underdog, chosen so that
forgetting genuinely cost you something. Grant decided that is not the pool he wants and that
the favorite is fairer. The sting is mild either way, because a missed game still gets the
lowest confidence value left, so it is worth almost nothing whichever side it lands on.

**How to apply:** Favorite, not underdog. This runs in Postgres, in `apply_auto_picks()`,
on a pg_cron schedule every five minutes, so it lands within five minutes of kickoff
without waiting on the GitHub sync job. Never in the browser. See
`migrations/005_autopick_favorite_on_cron.sql`.

Where the favourite comes from, in order, all of it in `fetch_slate._spread`:
ESPN's own favorite flag, then the "ABBR -10.5" details string, then **the moneyline**,
then the home team. The moneyline step was added 2026-09-11 when OU at MICH had its
spread taken off the board while the moneyline stayed at OU -205. Without it the game had
no favourite and every missed pick would have gone to Michigan, the side the market had
at about 37%. It names a favourite only, never a line: with no spread we do not know the
margin, so `spread_line` stays null, the game shows "no line", carries no tier, appears
under no spread filter and auto-ranks mid-table. Inside 4 points of implied probability
it declines to choose, and the home-team fallback takes over.

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

## Reminders are Web Push, and the cadence follows the next kickoff

Four kinds, all chosen by Grant on 2026-09-11: pick reminders, "week is live", Sunday
results, and "someone passed you". Pick reminders are measured against the soonest game
you can still pick, so they re-arm through the week rather than firing once: a heads-up
three hours out and a last call at 45 minutes, capped at two a day, silent once your card
is full.

**Why:** Week 1 went 80 for 80. Week 2 then sat at 0 of 80 with eleven hours to the first
kickoff. The PickNudge was built for exactly this the day before and it did not help,
because a nudge lives inside the app nobody opened. The cadence follows the next kickoff
rather than the week's first, because picks lock per game: someone who picks Friday's
games and leaves Saturday's open still needs telling on Saturday.

**How to apply:** There is no App Store and there never will be. Web Push is a browser
standard; VAPID keys in `.env` are the entire identity story. iOS delivers only to a
Home Screen install, which is how all four of them run it, confirmed 2026-09-11. Who is
due lives in `push_due()` in `migrations/012_push.sql` and nowhere else, so the sender
never decides anything. Every branch needs both a dedupe-ledger guard and a recency
guard: without the second, the first run announces every week ever published.

"Someone passed you" compares against a high-water mark, not your previous rank, which
caps it at three a week in a four-person pool without any counting.

**Nothing sends them on a schedule yet.** The scheduler, an Edge Function on pg_cron that
calls `push_due()` and sends, was never built, so every send has been `send_push.py` by
hand. As of 2026-09-22 the ledger holds one: a `week_live` to seat 1 on 2026-09-11. Weeks 3
and 4 were published with no notification. Seats 1 to 3 have a device subscribed and seat
4 has none. Never describe reminders as running until the scheduler exists.

## A week counts only once it is finished

A week is finished when all 20 of its games are graded, or when a later week has a graded
game. Week records, weeks won and "N weeks in the books" read finished
weeks only. Standings, the season record and season points count every graded game.

**Why:** weeks used to count from their first graded game. On 2026-09-12, one game into
Week 2, the Season tab dived every form line toward zero, called Grant's fewest points in a
week a 0 when it was Nicole's 147, and credited Nicole with winning Week 2 after one game.

**How to apply:** use `finishedWeeks` in `src/lib/seasonStats.js`. Never treat a week as
over because its graded count is above zero. `tests/recap_check.mjs` and
`tests/records_check.mjs` hold both halves.

## A finished week is painted in the winner's colors, with Grant's seven sections

Picked 2026-09-12 off two boards: option 2, "Winner's colors" (the athletic department
FINAL graphic, header included, in the winner's school color on charcoal), then sections
1, 2, 3, 6, 7, 8, 9 in that order: decided it, upsets, how it unfolded, your week, when
you all agreed, went at it alone, by the numbers. Shipped the same night.
"Went at it alone" is Grant's wording from the 2026-09-21 copy audit (below); it was "Went
it alone".

**Why:** he called the old tab "AI slop", the ranking bars unreadable (90 to 95%, fills
within 12px) and the text tiny (8.5px). He did not understand "points left on the table"
even explained, so the ceiling stat is gone from the screen; `ceiling` stays in the lib.

**Its top became the jumbotron final on 2026-09-13** ("lets do 1 but take out the over james
by 7"): the pager and a WINNER panel on the Board's LED wall, the winner's name and points
only, under the black jumbotron header. The seven sections below were kept exactly as they
were and still wear the winner's school color, which App sets on `.app` from `onSkin`.

**How to apply:** the Week tab shows FINISHED weeks only and opens on the newest one
("always have it lag a week", Grant, 2026-09-12); the week being played is the Board's.
`recapWeeks` in `weekNav.js` decides what finished means. Each week repaints its sections in
its own winner's school color (`--wf-field`, set by App from Week's `onSkin`); the header is
the jumbotron's (`data-skin="jumbo"`), and the top never names the runner-up. New recap
numbers go in `weekRecap.js` with checks in `tests/recap_check.mjs`;
`tests/test_week_final.py` holds the section order, the cuts and the lag.

## The Board is the jumbotron, and a pick shows the team picked

Picked 2026-09-12 off a board of six scoreboard directions ("lets do 1 its phenomenal"): a
stadium LED wall with a glowing leaderboard, every game as a tile in the schools' colors,
LED-dot numbers and a crawl of the finals. His one change: a pick chip carries the logo of
the team picked, not the player's avatar, which is a school logo too and read as the pick.

**Why:** he asked for a "real college football scoreboard" look that feels like a "million
dollar job". The 8-bit arcade direction is saved in `docs/ideas.md` for a theme week.

**How to apply:** the skin is `data-skin="jumbo"`, on the Board first and on every tab but
Season since 2026-09-13 (below). Chips name the player beside the picked school's mark. The
leaderboard reads `weekScore` over live ESPN scores, as the Week tab's final table does over
graded ones; `tests/test_board_jumbo.py` holds the chip logo rule and the hidden unplayed
picks.

## The Picks tab is the jumbotron too: one stadium with the Board

Picked 2026-09-13 off a board of six ("lets do 1, build it"): the Board's LED wall carried
onto Picks. Each school is a full-width lit panel, away over home, grouped under its kickoff
day; a pick lights a gold lamp and darkens the other side; points are LED numbers on the
Board's leaderboard rows; the confirmation and the read-only ranking are one Locked in
screen, a marquee with a crawl.

**Why:** Grant asked for a direction that matched the Board "so Picks and Board feel like
one stadium" and took it over five genuinely different looks
(https://claude.ai/code/artifact/e7dffb78-ccd0-42f6-bee7-aade8a65f6e3).

**How to apply:** `const jumbo` in App.jsx puts `data-skin="jumbo"` on both tabs, and since
that evening on every tab but Season. The LED is
one component, `src/components/Led.jsx`, and Picks reuses `.jb`, `.jb-wall`, `.jb-empty` and
`.jb-crawl`. Picks kept its old class names so the old guards still pin the same things
(`tests/test_preview_cta.py`, `tests/test_qa.py`); the new rules are in
`tests/test_picks_jumbo.py`. The Matchup sheet it opens went jumbotron the same day (below).

## The matchup sheet is the jumbotron too, the two teams as trading cards

Picked 2026-09-13 over three rounds. Round one lit each team's box in its school colors and
Grant said "those boxes with the color looks weird. I want the logo bigger and uniform text and
ranking under it. Make it easier to see the spread and over under and channel." Round two: he
called the logo plates best but did not love them. From an artifact of six tops
(https://claude.ai/code/artifact/5a115f17-67e8-4a48-8cbf-51ac2b251978): "lets do 8", trading
cards. Below the cards he kept round one's option 1: big LED win percentages over a bar in
the schools' colors, and this season as a column of chips per team.

**Why:** the sheet was the one light thing left on the jumbotron tabs, and its 14 sizes under
13px went with it (down to 8.5px).

**How to apply:** it passes `flush` to `Sheet` for an edge-to-edge wall (every sheet is dark
since that evening, below). Both cards come from one map in `Cards` in `Matchup.jsx`: logo on a lit
stage, the school on a name bar, AP rank (via `<Rank>`) and record on the foot, your pick the
gold card with a YOUR PICK strip that never moves it. No school color on the cards. Both names
share one size and step down together (25, 22, 19px) when either would wrap. TV, spread and
O/U are three labelled tiles. `tests/test_matchup_jumbo.py` holds all of it.

## Everything but Season's record book is on the jumbotron

Grant, 2026-09-13, after the matchup sheet shipped: the white score strip that pins on the
Board "doesn't fit the theme at all ... fix the setup tab, that little white piece, and
anywhere else that still shows, like, the old theme and design". A sweep of every state
found it in the strip, Setup, sign-in and its PIN keypad, and every sheet. Season's header
was the last old-look title. He saw the restyle and shipped it with the standings below.

**Why:** four tabs and the matchup sheet were already the stadium; everything else read as a
different, older app wrapped around them.

**How to apply:** every tab but Season wears `data-skin="jumbo"` (`const jumbo = tab !==
'season'`), and the header and tab bar are the jumbotron's on every tab, Season included. The
stadium is also a token set in theme.css, applied to the skin and to what lives outside
`.app`: every sheet, sign-in, the toast, the splash. Portalled things (the score strip) name
their own colors. Gold is the selection and always carries dark lettering; primary buttons
are `btn btn--led`. `tests/test_jumbotron_everywhere.py` holds it. Since 2026-09-14 every
sheet also has a round X in a top bar that never scrolls (`memory/ui-patterns.md`,
`tests/test_sheet_close.py`).

## The Season standings are trading cards

Picked 2026-09-13 ("ship the trading card one from before i liked that better") from an
artifact of four (https://claude.ai/code/artifact/0e6b7250-5850-4c20-a5ae-ad82d9816e75) and
then four variants of the podium he asked for and passed on
(https://claude.ai/code/artifact/332b4d4b-0f2f-4d7d-a9b0-39e322f06aee). The rows they
replaced were "dinky compared to everything else".

**Why:** the matchup sheet's cards, which he had just picked, carried onto the standings.

**How to apply:** `Standings` in `Season.jsx` is one map of `.scard`s, two across: rank badge
and logo on a lit stage, the name on a bar, points in LED, and the record and points behind
on the foot, labelled "Record" and "Behind" (a dash for first). First is the gold card, and a tie for first is two gold cards. The wool
and the record book below are unchanged. The form chart that sat under the cards went the
same night: "take the form away dont like it".

## The record book is Grant's seventeen, each with his badge

Eight numbers every player has, eight Hall of fame awards and one Hall of shame award,
chosen off a ballot on 2026-09-12 and laid out by number: the trophy room, the red panel,
and everyone's numbers as ranked ladders, uniform down every card (one number column, one
row height, a note under a name on every row or none).

**Why:** two earlier books failed, one on invented stats he could not read cold ("literally
none of these stats makes sense at all") and one on tiny text.

**How to apply:** never add, rename or drop an entry without asking him. A new entry needs
his art in `inputs/badges/<key>.png`, the key in both `scripts/build_badges.py` and
`src/lib/seasonRecords.js`, and a rebuild. The gate fails if any of the three drift.

**The Hall of fame is lettered as a legends poster** since 2026-09-13, off a board of five
("lets do 5 but drop the record book part"): HALL OF small over a huge slanted gold FAME in
Anton on a burst of light, the award names, holders and Up for grabs in the same type, and no
"The record book" line above it. Anton is in index.html's font link; the Hall of shame keeps
its own lettering. `tests/test_records.py` holds it.

**A trophy-room card is a badge, an award, a name and a detail, and every card on a row
lines those four up.** Grant, 2026-09-25: "can we drop the logo from our team and just put
the players name?", then "try to make everything uniform, like stuff being lined up ... take
off the 'in a week' line on biggest margin of victory so it even", and "only on the big icon
ones not the everyones numbers tabkles". So: no school logo under a badge, because the badge
is the mark that card is about; the Hall of shame and the ladders keep theirs. The award
`margin` is "Biggest margin of victory", the only name that ran to three lines in a 178px
card, and the week it was won is still in the detail under it. Two lines are held open under
every badge so a one-line name does not ride up, and the two cards on a row are one subgrid,
so the name and the detail hold their line even when one name wraps ("Nicole ×2, Grant &
Parker") and the one beside it does not. Measured at 390 and 375: every drift 0.0px.
`tests/test_records.py` holds the label length, the subgrid and both two-line minimums.

## The app's words are the ones Grant marked in the copy audit

Marked 2026-09-14 on a ballot
(https://claude.ai/code/artifact/6a71d168-1c73-4ee4-82d2-dc7239d89ec9), twelve Change it and
one Keep it, and built 2026-09-21 after he found "Went it alone" still live. The session that
published the ballot never got his "done".

**Why:** lines like "Had FAU", "Back" and "2 times" read as broken to the family, and two
were false. By the numbers credited three people with an upset only one had called, and Your
week said who "finished next to you", which was wrong for 3rd and 4th.

**How to apply:** `tests/test_copy_audit.py` bans the old wording from every file under
`src/`. Do not bring a marked line back, or reword one, without asking. Names join with
commas and one ampersand ("Nicole ×2, Grant & Parker"), and three co-winners of a week join
the same way. "Decided it" stays, because he kept it. The lines he left unmarked (Picks,
Board, sign-in, Setup, contractions) were left as they were.
