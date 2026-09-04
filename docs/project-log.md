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
