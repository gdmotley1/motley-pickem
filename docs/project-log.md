# cfb-pickem: project log

History, not instructions. This file is **not** auto-loaded.

Append here: how a conclusion was reached, superseded numbers, build archaeology. Anything
that becomes a standing rule gets promoted to `memory/decisions.md` instead.

New entries at the bottom, with an absolute date.

## 2026-09-03 — went live

### The app went live 2026-09-03 against the real Supabase project

Database created, Week 1 loaded with 40 games and a published slate of 20, and the whole
RPC surface verified end to end from the deployed site.

**Why it matters:** everything before this was a prototype against a localStorage mock.
Three bugs only appeared against real Postgres, and none of them could have been caught
by the mock or by reading the code:
1. `search_path = public` alone could not reach pgcrypto, which Supabase installs in
   `extensions`. The migration failed at the very first function.
2. `whoami` was declared STABLE and writes `sessions.last_seen`. Postgres accepts that
   at creation and refuses at call time, so a seat could be claimed but no session could
   start.
3. `SignIn` only rendered its error when the seat list had not loaded, so bug 2 produced
   a completely silent failure.

**How to apply:** verify against the real database before calling anything done, and
verify a guard by breaking the thing it guards. The first version of the volatility test
used `update\s+\w`, which only matches a one-letter table name, so it passed while
the bug was live.

### The weekly automation is live and verified end to end

`.github/workflows/sync.yml` runs the slate build Tue/Wed/Thu 08:00 ET and the scores
job every 15 minutes Thu-Sun. Repo secrets `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
feed it; `VITE_*` are repo variables.

**Why it took a workaround:** the gh CLI token carries `gist, read:org, repo` and not
`workflow`, so a push touching `.github/workflows/` is rejected, and `gh auth refresh`
needs an interactive browser approval that cannot be automated. Creating the file in
GitHub's web editor sidesteps it entirely, because the web session is not the CLI token.
Grant's own `gh auth refresh` also reported "not logged in": he was in an elevated
PowerShell, which reads a different Windows Credential Manager context.

**How to apply:** to change a workflow, edit `docs/workflows/*.yml` here, then paste it
into the web editor at
`https://github.com/gdmotley1/motley-pickem/new/main?filename=.github/workflows/<name>.yml`.
Trigger a run with `gh workflow run "Sync games" --repo gdmotley1/motley-pickem -f mode=slate`.

**A bug this caught:** the scheduled build originally ran `--next`. On the Tuesday of
Week 3 that resolves to Week 4, whose games are nine days out with no spreads posted, so
no slate could be built at all. The primary is now `--current`, with next week as a
best-effort extra that cannot fail the run.


## 2026-09-04 — Pool widened, matchup preview, Slate theme, service worker

Four changes in one session, each of which surfaced a bug in the last.

**The pool is every game.** It was the top 40 by interest out of ~90, and dropped any
game with no posted line before that cut. Kennesaw State, the example Grant gave, ranked
39th of 70 alternates with its line posted, so the cap alone put it out of Dad's reach.
The Setup screen gained search, conference chips and day sections to make ~91 rows usable
on a phone; migration 007 returns the conference columns get_pool never selected.

**Matchup preview.** A Preview pill on each game row opens a sheet with ESPN's win
probability, AP ranks, records, each team's last five and the venue and weather. It also
revived a dead path: TeamPick had always rendered an AP rank that get_slate never
returned, so the number only ever appeared in the offline demo.

**Slate theme,** chosen from a board of ten rendered as real pick screens. Most of that
work was routing app.css off the colour ramp onto a semantic contract, 97 declarations,
because every ramp token had baked "the chrome is green" into the component using it.

**Service worker.** CLAUDE.md had claimed the app was a PWA since the first commit and
there was no worker, so it installed and then behaved like a bookmark.

**Three bugs the work exposed, all now covered by tests:**

1. `sync_slate` never froze the odds on a played game. Harmless while the pool was built
   once on Monday; with a bigger pool a mid-week rebuild is ordinary, and it would have
   nulled the line on 38 of the 40 week 1 games the family had already picked against.
   The first fix then failed live with PostgREST's "All object keys must match", which
   `sync_scores` had split its batches to avoid all along.
2. A correct pick took its points colour from the selection green. The two had always
   been the same value, so nothing forced them apart until the palette moved.
3. `--ink-3` carries the 9.5px meta line at 3.2:1, under AA, in an app read by every age
   in the family.

**Method worth keeping:** every live write was snapshotted first and diffed after. That
is the only reason "the week 1 rebuild lost nothing" is a fact rather than a hope.

**Open at the end of the session, nothing in flight:**

- Push reminders are the natural next build and need the service worker, which now
  exists. VAPID keys, an edge function, and a pg_cron trigger a couple of hours before
  the week's first kickoff. iOS only delivers to a home-screen install, which is how the
  family uses it.
- Whether `--accent` should stay the same blue as `--pick`. See memory/ui-patterns.md.
- Season story stats: weeks won, best week, head-to-head, streaks. get_standings returns
  points, correct, games and weeks_played, so most of it is a view away.
- Player leaders in the matchup preview, if wanted, belong in sync_supabase writing a
  column rather than on the phone. See memory/traps.md.


## 2026-09-11 — A guard that asserted the reversed rule, and push notifications

**The guard was pointed at dead code.** `test_auto_pick_takes_the_underdog` read
`apply_auto_picks` out of `001_init.sql` and asserted `"favorite_abbr" not in auto`. The
rule was reversed to the favourite on 2026-09-04 and `005` replaced the function. The test
had been green for a week while asserting the exact opposite of what the database runs,
and it was a tripwire besides: anyone who correctly updated 001 would have been failed by
it.

It was not one test. Seven functions are redefined after their first migration, and every
body-reading guard in `test_migration.py` was reading the 001 copy: `apply_auto_picks`
(005), `get_board`, `get_standings`, `list_seats`, `whoami` (009), `get_slate` (006),
`get_pool` (007). `get_board` carries the pick-visibility rule and happened to keep its
gate in 009, but the guard could not have told us either way.
`test_admin_only_rpcs_check_is_admin` had the same flaw from the other direction, taking
`re.search`'s first hit out of the concatenation and so checking the 002 `get_pool`.
There is now a `body()` resolver that walks the numbered migrations, and a structural
guard holding it to that.

**Push notifications, because the nudge was not enough.** Week 1 went 80 for 80. Week 2
then sat at 0 of 80 with eleven hours to the first kickoff, which is the state the
PickNudge shipped for the day before. A nudge lives inside the app nobody opened.

Grant confirmed all four run it from the Home Screen, which is the only thing that makes
this possible on iOS, and chose all four notification kinds plus the cadence that follows
the next kickoff rather than the week's first. Shipped: `012_push.sql` (subscriptions,
per-player prefs, a dedupe ledger, a rank high-water mark, and `push_due()`), push and
notificationclick handlers in the worker, `src/lib/push.js`, a Reminders sheet, and
`send_push.py`.

**Not done, and deliberately:** the scheduler. Production wants a Supabase Edge Function
on pg_cron, for the reason 005 already documented about GitHub cron missing its own
schedule by 103 minutes. `send_push.py` is the manual path and the way to prove the chain
on a real phone first.

**Method worth keeping:** every new guard was broken on purpose before being trusted. It
paid immediately. The origin check in `sameOriginPath` could be deleted with every
assertion still passing, because each hostile URL was also caught by the scope check; it
took a foreign origin whose path is inside our scope to make that assertion real.

**Open at the end of the session:**

- `012_push.sql` is written and NOT pasted. Nothing works until it is.
- The edge function and its pg_cron schedule.
- Week 2 was published at 8:24am ET on the 11th. Nothing records who published, so
  whether that was Dad or the 18 hour `maybe_publish` fallback cannot be told after the
  fact. An `published_by` column would settle it.
- The bundle is 187KB gzipped, over Vite's warning, and framer-motion earns nine
  elements of it.

## 2026-09-11, later — push notifications land, and a day of guards that could not fail

Reminders shipped end to end: 012 and 014 applied, VAPID keys in `.env`, a Reminders sheet,
push and notificationclick handlers in the worker, and `send_push.py` with `--test`,
`--dry-run` and `--nudge`. Grant and James are subscribed; Parker and Nicole are not, and
that is the remaining gap, since a notification only reaches a phone that opted in.

**Still not built: the scheduler.** Production wants a Supabase Edge Function on pg_cron,
for the reason 005 already documented about GitHub cron missing its own schedule by 103
minutes. Every send so far has been by hand.

**Four bugs found by running the thing rather than reading it.**

- `push_due` documented a dedupe ledger it never read. Caught by running the sender twice
  and getting the same notification twice. On a five minute schedule that is about 144
  notifications per phone for `week_live`.
- pywebpush defaults `ttl=0`, so two test pushes were accepted with a 201 and discarded.
- The notification title repeated the app name, which iOS already draws.
- `theme.css` reset `h1, h2, h3` and stopped, so the app's only `<h4>` carried a 15.3px
  default margin above every section of the matchup sheet.

**The through-line, and the thing worth keeping.** In every one of those, something that
looked like a guard was not one. A comment describing a dedupe. A test asserting a table
had a primary key rather than that anything read it. A title check matching `'...'::text`
that missed two of five branches. A CSS audit that read class rules and never opened the
element reset beside them, which produced two confident false positives that Grant acted
on before I checked. Breaking each new guard on purpose caught all of it; the ones I did
not break are the ones that shipped wrong.

**Also this session:** the preview CTA went from an outlined pill nobody tapped to a Slate
pill with a shimmer, via two options boards; the matchup sheet gained ESPN's preview line
and lost last season's form; the Setup filter now matches the tier tags it is drawn from;
the favourite falls back to the moneyline when a spread is off the board; and the app icon
is Grant's blue logo, generated by `scripts/build_icons.py`.

**Open:** the scheduler, Parker and Nicole's subscriptions, and the bundle at 187KB
gzipped with framer-motion earning nine elements of it.

## 2026-09-12: the record book, picked by number

The Season tab's record book went from twelve squares with 8.5px labels to three sections
Grant chose by number: headlines for everyone's numbers (6), the trophy room for the Hall of
fame (7) and the red panel for the Hall of shame (10), drawn with his own 17 badges.

**How it got picked, over two sessions.** The first ran a tappable ballot for the contents
(eight numbers every player has, eight fame awards, one shame award; unmarked meant no) and
five layout boards lettered A/B/C and T1 to T4. He picked T2, a table with the names frozen
down the left, then reversed it on sight once it sat in the assembled tab, because it
scrolled sideways. The second session opened with "I was unclear as to what you were gonna
build. I need specific examples in a one, a two, etcetera." One board of twelve options,
numbered once across the whole board, each phone showing its whole section, the last phone
assembling the picks in tab order. He picked in one voice message.

**The badges.** Seventeen ChatGPT renders of `docs/badge-prompts.md`, which arrived in
Downloads mid-session under generic file names and were matched to their prompts by eye
(`inputs/badges/README.md`). `scripts/build_badges.py` trims each to a 320px WebP, about
39KB against 2MB, in `src/assets/badges/` so Vite fingerprints the names. The game-icons.net
glyphs and their CC BY credit line are gone with them.

**The bug fixed with it.** A week counted as played from its first graded game. One game
into Week 2 the tab dived every form line toward zero, called Grant's fewest points in a
week a 0, and credited Nicole with winning Week 2. The rule is now in
`memory/decisions.md`.

**The transition.** Grant, while picking: "the transition from the season standings to the
hall of fame is really rough." The trophy room was a near-black panel starting on a hard
edge under the last standings row. Its background now starts transparent, darkens over
110px beneath a brass rail with a stud, and fades back out at the bottom.

**Method worth keeping.**

- Checked on the real Season screen with live data, in a harness built to static files
  with no dev server: text 13px or more at 390 and 375 wide, nothing spilling, all 17
  images loaded.
- Every new guard was broken on purpose first. A half-played week counting again, fewest
  points sorted the wrong way, a player who never lost given a zero, and a missing badge
  file each failed the check with the right message.
- The first badge freshness check re-encoded all 17 images and took the gate from 3.6s to
  40s. It compares fingerprints recorded at build time instead.
- A PowerShell `Get-Content -Raw` rewrite read a UTF-8 builder as cp1252 and wrote "â€“"
  into 16 cells of a board. A screenshot caught it. Replacements go through the Edit tool.

**Then the chrome, the same night.** Grant: "fix the tab bar and header tiny text too."
The tab labels went from 10.5px to 13px with the line box tightened to 1.2, so the bar grew
1px (62 to 63) rather than 4, which mattered because the bar is where the iOS gap of
2026-09-10 lived. The header's week line went from 11px to 13px and the header grew 3px;
the Board's pinned scorebug followed on its own because `useHeaderOffset` measures it.
Measured at 393 and 375 through iframes, because headless Edge will not render a viewport
narrower than about 500px and reported 518 for both.

**Open:** 65 declarations under 13px remain on other screens (the Board's scorebug rows,
chips, Setup, sign-in). `tests/test_text_floor.py` holds them as a ceiling that only goes
down, so no new tiny text can land while they wait.

**Everyone's numbers, redone the same night.** Live, the headlines were "a little clunky
and hard to read, like, what the record actually is": the record's name was 13px spaced
capitals under a 21px name and a 25px number, and the rest of the family ran together in
one sentence. A second board of six (`scripts/build_numbers_board.py`, fed by the app's
own record code through `scripts/numbers_model.mjs`) put the live version on top for
comparison. Grant picked 4, ranked ladders, then asked for it "uniform ... no weird text or
spaces. take the of 1 out of week". Measured on the real screen: every number in a card
ends at the same x and every name starts at the same x (0px drift), rows come in two
heights (58 for the holder, 48 otherwise), and a note under a name is on every row or
none, which `tests/records_check.mjs` enforces. The tab is about 1,100px longer than with
headlines, the price of showing all four of you on every record.

## 2026-09-12, night: the Week tab and the Board, redone

**Week tab.** Grant: "It looks like AI slop. Ranking bars look bad. Hard to follow. Small
text." Measured live: smallest text 8.5px with 75 runs under 13px, four ranking bars within
12px of each other (90 to 95%), Nicole's 10-10 wrapping. Five whole-tab looks went to him as
screenshots after he stopped a 44-minute silent build ("bruh 44 mins?"); he picked 2,
Winner's colors, then chose sections 1, 2, 3, 6, 7, 8, 9 off a second board
(https://claude.ai/code/artifact/1e850185-8409-404d-a4f8-de75ca740f5b). Every new number is a
pure function in `weekRecap.js` with checks on the real Week 1. Then: "always have it lag a
week", so the tab shows finished weeks only, each painted in its own winner's school color.

**Board.** A first look of four in about 12 minutes, then an artifact of six scoreboard
directions (https://claude.ai/code/artifact/4a7c0109-62f3-4961-b6e1-dbe00e33ad26) with
progress screenshots on the way. He picked the jumbotron ("its phenomenal") with one
change, the picked team's logo on each pick, and saved the 8-bit arcade in
`docs/ideas.md`. The old game cards went; under-13px declarations 65 to 51 across the night.

**Deploys.** Three, each proved on the served bundle and the four live seats. The Picks tab
is next, in a new chat.

## 2026-09-13: the Picks tab, redone as the jumbotron

A first look of four directions as one screenshot about 12 minutes in, then a published
board of six (https://claude.ai/code/artifact/e7dffb78-ccd0-42f6-bee7-aade8a65f6e3), each as
Winners, Points and Locked in phones on Grant's real Week 1 card, with today's tab on top
from a new harness (`outputs/harness/tools/picks_shots.ps1`). Measured today: 146px a game,
12.5px school names, a 10px Matchup label and a 9.5px TV chip. He picked 1, the Board's
jumbotron: "lets do 1, build it".

Built on the Board's own parts: `Led` moved out of Board.jsx into `src/components/Led.jsx`,
and `data-skin="jumbo"` now covers both tabs. Old class names kept so the Matchup pill
guards hold. Measured on the real screen at 390px: 20 game tiles all 166px (picked or not),
team panels 54px, the pill 32px with a 44px target, points rows 56px, Locked in rows 46px,
smallest text 13px, nothing sideways. Twenty games take about 3,480px, up from 3,120.
Under-13px declarations in app.css 51 to 39. One trap on the way: a class name the team
picker already owned (see memory/traps.md).

Deployed the same night on "push and deploy": the served index-Dzbb43Sl.css and
index-CDTfU-Tz.js are byte-identical to dist and carry the new rules, and the live sign-in
screen, loaded read-only, shows all four seats on the new bundle. That push also carried the
two handoff commits and the night-of-2026-09-12 notes that were committed but not pushed.

## 2026-09-13, later: the Week tab's top

Grant: "i like the week tab except for the top portion. come up with new designs for the top
while keeping the rest below it". Four tops as one screenshot, each stacked on the real rest of
the tab cropped from the live harness shot (`scripts/weektop_first_look.py`): Jumbotron final,
Final score, Trophy, the banner. He picked 1, "but take out the over james by 7". Built as the
pager and a gold-ringed WINNER panel on the Board's wall, name and points in LED, the school
mark bottom right so a six letter name clears it. Measured in the harness on #now, #later
(Parker) and #back: the top is 371px under the header, smallest text 13px, nothing spills,
and each section's rule still wears the winner's color.
Then "remove back to week 2 button pls then ship deploy": the Back to Week N button under the
pager went, with its styles; the right arrow and the jump list already do that job.


## 2026-09-13, afternoon: the matchup sheet goes jumbotron

Started from `docs/handoffs/HANDOFF-matchup-sheet.md` in a new chat. Three rounds, each the
real sheet opened from its pill in the Picks harness on real ESPN data (#8 LSU at #9 Ole
Miss, pulled that morning), never a mockup.

1. The sheet re-skinned, with two lower halves: big LED percentages and chips, or lamp bars
   and lamp tiles. Grant: "Neither I want the logo to be bigger, and it's not very even or
   makes much sense. everything below it's fine, but those boxes with the color looks weird.
   I want the logo bigger and uniform text and ranking under it. Make it easier to see the
   spread and over under and channel."
2. Three tops (logo plates, tale of the tape, marquee spotlights), no school colors, with TV,
   spread and O/U as labelled tiles. "make an artifact. 3 is best but still dont love. new
   choices pls".
3. An artifact of six tops, each on LSU at Ole Miss and on #7 Miami at unranked Wake Forest,
   with the measured height and scroll under each:
   https://claude.ai/code/artifact/5a115f17-67e8-4a48-8cbf-51ac2b251978. Recommended 7
   (broadcast); he said "lets do 8", trading cards.

Built as `Cards` in `Matchup.jsx` with round one's option 1 below, on `Sheet`'s new opt-in
`tone="jumbo"`. Measured at 390px in six harness states (pick away, pick home, no pick with
one team unranked, final with no projection, ESPN down, the longest real name): both cards
244px, names and stats level across the two, the `@` on the logo centreline, smallest text
13px, nothing sideways or clipped, no Supabase traffic. On an 844px phone the sheet scrolls
about 133px. Under-13px declarations in app.css 39 to 25. Guards in
`tests/test_matchup_jumbo.py`, each broken once in a scratch copy to see it fail; two missed
the first time and were fixed (see memory/traps.md for the three traps found on the way).

Deployed the same afternoon on "push deploy makemlive": GitHub Pages named the new bundle
about 10 seconds after `bash deploy.sh`; the served index-BSYgn6gc.css (77,970 bytes) and
index-SW9gr2Ps.js (650,977 bytes) are byte-identical to dist, carry `.sheet.sheet--jumbo`,
`.mu__card.is-mine` and the name-fit rules, and no longer carry `.pbar`, `.form__score` or
`.mu__team`. The live sign-in screen, loaded read-only in a throwaway headless profile,
shows all four seats (Grant, James, Parker, Nicole) on the new bundle.

## 2026-09-13, evening: the rest of the app joins the jumbotron, and the standings become cards

Grant: the white strip that pins while scrolling the Board "doesn't fit the theme at all",
then Setup, "anywhere else that still shows the old theme and design", and the Season
standings, which looked "dinky compared to everything else".

A new harness drives the whole real app in demo mode into eleven states and reports every
light surface (`outputs/harness/tools/sweep_shots.ps1`). It found the strip (portalled out of
reach of the skin, so its jumbotron rules never matched), Setup, sign-in and the PIN keypad,
and every sheet. The fix is mostly one token set in theme.css, the stadium's colors under
Slate's job names, applied to the skin and to what lives outside `.app`, plus the wall's
lettering and lamps where a token cannot say it. Every tab but Season now wears the skin and
every tab the black header. A pixel diff against the shots taken first: Picks and Week
unchanged, the Board only in the strip's band.

The standings went through two boards, four options
(https://claude.ai/code/artifact/0e6b7250-5850-4c20-a5ae-ad82d9816e75, recommended the LED
leaderboard) and then four variants of the podium he asked to see
(https://claude.ai/code/artifact/332b4d4b-0f2f-4d7d-a9b0-39e322f06aee). He passed on all of
them for option 3: "ship the trading card one from before i liked that better".

Under-13px declarations in app.css 25 to 12. The six tests that pinned the old look were
rewritten to the new calls, and `tests/test_jumbotron_everywhere.py` adds eleven guards, each
broken once in a scratch copy (fourteen breaks, all caught). Traps: a skin on `.app` cannot
reach anything portalled, and a button does not inherit the text color (memory/traps.md).

Deployed the same evening on "ship": GitHub Pages named the new bundle about 30 seconds after
`bash deploy.sh`; the served index-BKSbJBRX.css (81,787 bytes) and index-DmGd07T5.js (651,424
bytes) are byte-identical to dist, carry the cards, the strip, the flush sheet and the Setup
and sign-in rules, and no longer carry `.srow`, `.pod__`, `.plaque` or `.sheet--jumbo`. The
live sign-in screen, loaded read-only in a throwaway headless profile, shows all four seats
(Grant, James, Parker, Nicole) on the new bundle.

## 2026-09-13, late: the form chart comes off Season

"take the form away dont like it". The chart, its legend and well, and the geometry in
seasonStats.js that only it used all went, with their checks; the standings cards now run
straight into the Hall of fame, about 240px shorter on a phone. Deployed on "push and deploy":
the served index-COaeGSpu.css and index-B52KFDv_.js are byte-identical to dist and carry no
chart rules, and the live sign-in screen, loaded read-only, shows all four seats.

## 2026-09-13, late: the Hall of fame lettered as a legends poster

"lets make the hall of fame font bigger and better more ledgendary and epic. make options".
A board of five letterings on the real record book
(https://claude.ai/code/artifact/52ee52e7-64dc-4bdd-bc12-a5d99caf301a): engraved trophy
(Cinzel), championship blackletter (UnifrakturCook), varsity (Graduate), gold LED, and a
legends poster (Anton). He took 5, "but drop the record book part". HALL OF small over a
134px slanted gold FAME on a burst of light; award names 22px, holders 24px, Up for grabs
26px, where all of it was 14 to 15px; Anton added to index.html. The Hall of shame kept its
lettering, checked side by side. Deployed on "push and deploy": the served
index-hSkSKokN.css and index-BN54c3qV.js are byte-identical to dist, the live index.html
requests Anton, and the live sign-in screen, loaded read-only, shows all four seats.
