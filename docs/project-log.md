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

