# Motley Pick'em

> Local folder is `cfb-pickem/`; the app, repo and URL are all `motley-pickem`. Only
> `../.claude/launch.json` depends on the folder name. Rename both together or neither.

Live: https://gdmotley1.github.io/motley-pickem/ · repo `gdmotley1/motley-pickem`
Backend is REAL as of 2026-09-03: Supabase project `lugxthfaksdjmvxepryt`, migrations
001-004 applied, Week 1 published. The app is no longer in mock mode.
Deploy with `bash deploy.sh`, which publishes `dist/` to the `gh-pages` branch.

A college football confidence pool for Grant's family. Four people, 20 games a week,
straight-up winners, confidence points 1 to 20 each used exactly once. Replaces writing
picks out on paper and in the Notes app. Installs to a phone home screen as a PWA.

**Audience:** four family members on their phones. Grant and his dad are the two admins;
his dad approves the weekly slate. Non-technical users, all ages. If a screen needs
explaining, it is wrong.

## The rule that outranks everything

**Locking is enforced in the database, never in the browser.** A pick on a game that has
kicked off must be rejected by a Postgres RLS policy comparing `now()` to kickoff. Same for
pick visibility: you may not read another player's pick until that game has started. Anyone
in the family can open devtools, and the anon key ships in the client bundle. Client-side
checks are for UX only.

## Key commands

```bash
python -m pytest tests/ -q                    # the gate. Run before saying anything is done.
npm run dev                                   # app at /motley-pickem/ ; add ?demo=1 for fake
                                              #   opponents, results and a finished week
npm run build                                 # must stay clean

# the CFB week calendar (ESPN's real boundaries, not Monday-to-Sunday)
python scripts/cfb_weeks.py                    # whole season
python scripts/cfb_weeks.py --current          # week in progress

# rebuild a week's game pool (40 games, best 20 pre-selected)
python scripts/suggest_slate.py --current --out outputs/week01_pool.json
python scripts/suggest_slate.py --next         # build next week in advance
python scripts/build_mock_data.py              # refresh the offline demo data

# raw ESPN pull for a date range
python scripts/fetch_slate.py --start 2026-09-03 --end 2026-09-06

# FBS team library + every logo (138 teams, 276 PNGs, ~12MB)
python scripts/fetch_teams.py --out inputs/fbs_teams.json --download static/logos

# turn Dad's handwritten shorthand into real ESPN games
python scripts/resolve_slate.py --slate inputs/week01_dad_slate.txt \
  --games inputs/slate_2026-09-03_2026-09-06.json --out inputs/week01_resolved.json
```

## Things that will bite you

**ESPN returns `conferenceId` as a string.** Comparing it to an int matches nothing and
fails silently. A slate came out with zero SEC games this way. Always coerce through
`suggest_slate.conf_id()` or `fetch_slate.is_fbs()`.

**Do not set a browser User-Agent on ESPN calls.** Grant's sandbox egress proxy 403s
browser-like UA strings while allowing the urllib and curl defaults. `fetch_slate.UA_VARIANTS`
tries several in order. Leave it alone.

**Two different "TUL" teams can appear on the same slate.** Tulane is `TULN`, Tulsa is
`TLSA`. `resolve_slate.AMBIGUOUS` disambiguates by opponent and errors rather than guessing.
Getting this wrong silently assigns picks to the wrong game.

**Never use framer-motion's `AnimatePresence` here.** Its exits do not complete under
React 19: it froze tab switches and left closed bottom sheets in the DOM, where the
full-screen scrim ate every tap. Screens animate in on a fresh key with no exit; overlays
use the `Sheet` / `Toast` components in `src/components/ui.jsx`.

**`position: fixed` is relative to a transformed ancestor.** The screen wrapper is an
animated motion.div, so fixed overlays inside it anchor to the page, not the screen. Use
the `Portal` helper in `src/components/ui.jsx` for anything fixed. Related: never animate
an overlay's opacity from 0, because a backgrounded tab pauses CSS animations and leaves
it half-transparent.

**Week numbers come from ESPN's calendar, never from arithmetic.** Week 1 of 2026 runs
22 Aug to 8 Sep because it absorbs Week 0, boundaries land ~3am ET Monday so Sunday night
games stay in the week that is ending, the boundary hour shifts when DST ends, and there
is a 60 second hole between weeks that `week_for` snaps forward. The app once hard-coded
"Week 2" for a slate that is actually Week 1. See `scripts/cfb_weeks.py`.

**ESPN's featured-games list is a brand list, not a good-games list.** It happily serves
four 40-point spreads. Never feed it to the pool unfiltered. `suggest_slate` reshapes it
into certainty tiers so confidence points stay meaningful.

## Layout

```
cfb-pickem/
  CLAUDE.md      <- you are here, always loaded
  memory/        <- durable truth. decisions.md is @-imported.
  docs/          <- handoffs/ for workstreams, project-log.md for history
  app/           <- backend
  static/        <- frontend, plus logos/ (138 FBS teams, light and dark)
  tests/         <- pytest, the gate. fixtures/ is a saved ESPN week, so tests run offline.
  scripts/       <- fetch_slate, suggest_slate, fetch_teams, resolve_slate
  inputs/        <- source data, read-only
  outputs/       <- generated, disposable
```

## Detailed reference

@memory/decisions.md

Read on demand, not loaded every session:

- `memory/ui-patterns.md` — how each screen behaves, and the libraries that failed here
- `memory/traps.md` — bugs that already cost time, and the guard that now catches each
