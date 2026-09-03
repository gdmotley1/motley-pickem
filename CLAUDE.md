# cfb-pickem

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

# rebuild this week's game pool (40 games, best 20 pre-selected)
python scripts/suggest_slate.py --start 2026-09-03 --end 2026-09-06 --out outputs/week01_pool.json

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

Data flows one way: inputs to scripts to outputs. Deleting outputs must never break a
build. Source data is never edited in place.

## Detailed reference

@memory/decisions.md
