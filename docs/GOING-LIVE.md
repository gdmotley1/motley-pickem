# Going live

The app is complete and deployed, but until these steps are done it runs in mock mode:
every seat, PIN and pick lives in one phone's local storage and nothing is shared.

## 1. Create the database (blocks everything else)

In the Supabase SQL Editor for the **new free project**, run in order:

1. `migrations/001_init.sql` — tables, RLS, the kickoff lock, sign-in
2. `migrations/002_get_pool.sql` — the commissioner's slate builder
3. `migrations/003_get_week.sql` — week metadata

Each is safe to re-run.

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

Then move both workflows into place and push:

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
| Every 15 min, Thu–Sun | Update scores, grade finals, auto-pick the underdog for anyone who missed a kickoff |
| Continuously, on each phone | Live scores pulled straight from ESPN |

The only human step left is your dad opening Setup, swapping any games he wants, and
tapping Publish.

## Running a job by hand

```bash
python scripts/sync_supabase.py --mode slate  --next     # build next week
python scripts/sync_supabase.py --mode scores --current  # refresh scores now
python scripts/sync_supabase.py --mode slate --next --dry-run
```
