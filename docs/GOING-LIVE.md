# Going live

**Status: DONE as of 2026-09-03.** The app is live against the real Supabase
project, migrations 001-004 are applied, Week 1 is published with 20 games, and
the scheduled jobs are running. Nothing below is outstanding; it is kept as the
record of how it was set up and how to do it again.

Verified from GitHub Actions into Postgres: the slate build upserts 40 games and
preserves a published slate, and the scores job refreshes all 40. Auto-picks moved
to pg_cron inside Postgres on 2026-09-04 and no longer depend on this job.

The app is complete and deployed, but until these steps are done it runs in mock mode:
every seat, PIN and pick lives in one phone's local storage and nothing is shared.

## 1. Create the database (blocks everything else)

Open [migrations/ALL.sql](../migrations/ALL.sql), copy the whole thing, paste it into the
Supabase SQL Editor for the **new free project**, press Run. That is the entire step.

It is generated from the numbered migrations, so there is nothing to run in order and
nothing to miss:

- [001_init.sql](../migrations/001_init.sql) — tables, RLS, the kickoff lock, sign-in
- [002_get_pool.sql](../migrations/002_get_pool.sql) — the commissioner's slate builder
- [003_get_week.sql](../migrations/003_get_week.sql) — week metadata

Every statement is idempotent, so running it again is harmless. Regenerate after editing
any migration:

```bash
python scripts/build_combined_migration.py
```

## 2. Point the app at it

Add two **repository variables** (Settings → Secrets and variables → Actions → Variables):

| Name | Value |
|---|---|
| `VITE_SUPABASE_URL` | the project URL |
| `VITE_SUPABASE_ANON_KEY` | the anon key |

The anon key is public by design. It can do nothing on its own: every table denies it and
all access runs through SECURITY DEFINER functions.

Then redeploy: `bash deploy.sh`.

## 3. Turn on the scheduled jobs

The `gh` CLI token here cannot create `.github/workflows`. One command fixes that:

```bash
gh auth refresh -s workflow
```

Then move both workflows ([deploy.yml](workflows/deploy.yml),
[sync.yml](workflows/sync.yml)) into place and push:

```bash
mkdir -p .github/workflows
cp docs/workflows/deploy.yml docs/workflows/sync.yml .github/workflows/
git add .github && git commit -m "Add CI workflows" && git push
```

Add two **repository secrets** (not variables) for the sync job:

| Name | Value |
|---|---|
| `SUPABASE_URL` | the project URL |
| `SUPABASE_SERVICE_KEY` | the service_role key |

The service key bypasses RLS. It must never appear in a `VITE_` variable, because
anything prefixed `VITE_` is compiled into the browser bundle.

## What then runs on its own

| When | What |
|---|---|
| Tue, Wed, Thu 8am ET | Build next week's 40-game pool and refresh spreads |
| Every 15 min, Thu–Sun | Update scores and grade finals. GitHub does not honour this schedule; real gaps of 100 minutes have been seen, which is why nothing time-critical depends on it any more |
| Every 5 min, all year (pg_cron) | Auto-pick the favorite for anyone who missed a kickoff. Runs inside Postgres, needs no network |
| Continuously, on each phone | Live scores and live grading pulled straight from ESPN |

The only human step left is your dad opening Setup, swapping any games he wants, and
tapping Publish.

## Running a job by hand

```bash
python scripts/sync_supabase.py --mode slate  --next     # build next week
python scripts/sync_supabase.py --mode scores --current  # refresh scores now
python scripts/sync_supabase.py --mode slate --next --dry-run
```
