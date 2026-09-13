# Handoff: Picks tab redesign

Written 2026-09-12, late, at the end of the session that redid the Week tab and the Board.

## TL;DR

Grant is redesigning the app one tab at a time from boards of rendered mockups. Season,
Week and Board are done and live. **Picks is next.** He asked for "mockups" and moved it to
a fresh chat. Nothing on the Picks tab has been touched yet.

## How he wants the mockups (this is what worked tonight)

1. **Rough first look within about 10 minutes**: three or four directions as one
   screenshot sent with SendUserFile. A 44-minute silent build got "bruh 44 mins?".
2. **Then a published Artifact of several wildly different directions**, each a full phone
   on real data, numbered once across the board. Name them and give an ETA up front, and
   send a progress screenshot every 15 to 20 minutes on a big build.
3. **Loud wins for whole-tab looks.** Week: "Winner's colors" (school color flood, huge
   italic name). Board: the LED "Jumbotron" ("its phenomenal"). He asked for "a million
   dollar job". Keep the data inside plain and uniform.
4. Recommend one, state costs (height, taps, fonts), then build only after he picks.
5. After the build: gate, harness screenshots, and wait for **"push and deploy"**.

Consider a direction that matches the Board's jumbotron (`data-skin="jumbo"`) so Picks and
Board feel like one stadium, but show real alternatives too.

## What the Picks tab is today

`src/screens/Picks.jsx`, about 810 lines, four phases in one screen:

- **choose**: a list of the slate's games, each a `GameRow` with two big `TeamPick`
  buttons and the loud "MATCHUP" pill that opens the preview sheet (`Matchup.jsx`).
- **rank**: confidence points by tap-to-lift, tap-to-place; arrives pre-sorted by the
  spread (`autoRank`), with "Reset to spread".
- **locked**: the read-only ranking once submitted, until you choose to edit.
- **done**: the confirmation with two calls to action (edit, or see the Board).

Data comes from `get_slate` (your own `my_pick` and `my_confidence` ride on each game).
Saving is `save_picks`. Drafts autosave to localStorage under `pickem.draft.v1`.

## Rules that already bind this tab (do not rediscover them)

All in the repo's `memory/ui-patterns.md` and `memory/decisions.md`:

- The choose step is a **list, not a card stack** (the stack was tried and failed).
- Ranking is **tap to lift, tap to place. No dragging.** dnd-kit is uninstalled.
- **Auto-rank by spread** is applied on arrival and is the feature that makes this usable.
- The **ranking is restored from the server** (`my_confidence`) before any local draft.
- The **matchup pill** stays loud; `tests/test_preview_cta.py` pins its 44px target, the
  shimmer clipped by its own wrapper, and transform-only animation.
- **Locking is enforced in Postgres**, never in the browser. Client locks are UX only.
- 13px text floor, 44px tap targets, nothing that scrolls sideways, repeated rows
  pixel-identical, no `AnimatePresence`, fixed overlays through `Portal`, never animate an
  overlay's opacity from 0.

## Where real data for mockups comes from

- `outputs/harness/week_live.json`: the real Week 1 slate, all 80 picks and the four seats
  on today's schools (gitignored; rebuild it from `tests/fixtures/week1_board.json` if
  missing). Grant's own Week 1 winners and confidence values are in it, which covers the
  rank, locked and done phases.
- `tests/fixtures/slate_week01.json` and `outputs/week01_pool.json`: slate rows for a
  choose phase with nothing picked yet.
- Team marks: `static/logos/<id>.png` and `<id>-dark.png`; colors in
  `static/data/teams.json`. `scripts/boardtab_kit.py` already turns them into CSS
  variables and faces for a board.

## Templates to copy

- **Board of directions**: `scripts/build_boardtab_board.py` (+ `boardtab_page.css`,
  `boardtab_page.js` for in-page measuring, one `boardtab_<name>.py/.css` per direction).
  Published as https://claude.ai/code/artifact/4a7c0109-62f3-4961-b6e1-dbe00e33ad26
- **Real screen in a harness, no dev server**: `outputs/harness/board_live.*` and
  `board_stub.js` (stubbed RPCs, scenario switch on the URL hash), built with
  `outputs/harness/vite.harness.config.mjs`, shot with `outputs/harness/tools/shot.ps1`,
  measured with `tools/dump.ps1` reading `<pre id="measure">`. There is an older
  `outputs/harness/picks.html` + `picks.jsx` worth checking first.

## Commands

```bash
python -m pytest tests/ -q          # the gate, 360 passing at handoff
npm run build                       # must stay clean
bash deploy.sh                      # ONLY after Grant says "push and deploy"
```

After a deploy: poll the live `index.html` for the new bundle hash, assert on the served
JS/CSS, and load the live sign-in screen read-only to confirm all four seats.

## Loose ends from the last session

- Commit `3077a19` (session notes in `memory/` and `docs/project-log.md`) is **committed
  but not pushed**. Grant was asked and had not answered.
- A cleanup task chip was offered: remove the unused `WeekScore` scorebug card and its CSS.
  Check whether it ran before editing `src/components/WeekScore.jsx`.
- The 8-bit arcade Board is saved for a theme week in `docs/ideas.md`. Not scheduled.

## Do NOT

- Run `npm run dev` and click around: it reads `.env` and connects to the **live** family
  database. Use a harness built to static files.
- Enter a PIN, sign in to production, or change the localStorage keys `pickem.token` or
  `pickem.draft.v1` (that signs everyone out or loses drafts).
- Reintroduce dragging, a card stack for choosing, or `AnimatePresence`.
- Touch migrations, and never paste 013.
- Deploy without an explicit "push and deploy".
- Use em dashes in anything Grant reads.
