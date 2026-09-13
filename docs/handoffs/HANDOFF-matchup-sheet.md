# Handoff: the matchup preview sheet, on the jumbotron

> **Status 2026-09-13:** done in the next session. Grant picked the trading cards (8 of an
> artifact of six tops, https://claude.ai/code/artifact/5a115f17-67e8-4a48-8cbf-51ac2b251978)
> and it is built (see `memory/decisions.md` and `docs/project-log.md`). Kept below as the
> record of how the session was set up.

Written 2026-09-13, at the end of the session that rebuilt the Picks tab and the Week tab's
top as the jumbotron.

## TL;DR

Grant: "make the matchup preview sheet match the jumbotron too. but set it up to handoff and
run in new chat." The Board, the Picks tab and the top of the Week tab are all the LED
jumbotron now. The sheet that opens from the red MATCHUP pill on Picks is still the light
Slate sheet from 2026-09-04, so it is the one thing on those tabs that is not in the stadium.
**The direction is decided: match the jumbotron. Nothing has been built.**

## How he wants it run (what worked all week)

1. **Show something within about 10 minutes**: one screenshot via SendUserFile. The look is
   already chosen, so this is the sheet re-skinned, with two or three numbered variants only
   where there is a real layout choice (win probability as two LED bars or two big LED
   percentages, form as lamps or chips). A silent 40 minute build got "bruh 44 mins?" once.
2. He picks by number, often with one change ("lets do 1 but take out ..."). Build that.
3. Gate, then screenshots of the **real sheet** in the harness, then wait for **"push and
   deploy"** (he also says "ship deploy"). Approval covers that change only.
4. After deploy: poll the live `index.html` until it names the new bundle, check the served
   CSS and JS are byte-identical to `dist/`, and load the live sign-in screen read-only to
   confirm all four seats (Grant, James, Parker, Nicole).
5. Loud is right for the look; the numbers inside stay plain and uniform. Nothing under
   13px, nothing that scrolls sideways. No em dashes in anything he reads.

## What the sheet is today

- **`src/components/Matchup.jsx`** (about 210 lines). Header: both teams with logo, AP rank,
  school and record. A line: kickoff, TV, spread, total. Then sections, each hidden when ESPN
  sent nothing: ESPN win probability (two bars, your pick ticked), This season (form tiles),
  ESPN preview (one clamped headline), Where (venue and weather). A spinner while loading,
  one sentence if ESPN is unreachable.
- **Opened from** `ChoosePhase` in `src/screens/Picks.jsx`:
  `<Sheet open={!!preview} ... label="Matchup preview"><Matchup key=... game ranks picked /></Sheet>`.
  Not reachable after picks are locked in (by design, see `memory/ui-patterns.md`).
- **Data**: `fetchMatchup` in `src/lib/matchup.js` (one ESPN summary per game, cached for the
  session, shaped by `normalise`). Ranks come from `useRanks()`.
- **Styles**: `src/app.css`, the section headed `/* ==== matchup preview` (about line 3250):
  `.mu*`, `.pbar*`, `.form*`. The container is the shared `.sheet` (about line 580) with its
  open and close animations (about line 3180).
- **The measured problem to fix on the way**: 14 font sizes under 13px in the sheet's own
  rules, down to 8.5px (`.form__score`), 9.5px (`.form__res`) and 10px (`.pbar__mine`). The
  ratchet in `tests/test_text_floor.py` is `CEILING = 39`; lower it by however many go.

## Rules that already bind it (do not rediscover them)

- **`Sheet` is shared** by the account sheet, Pick your team, Reminders and the Week tab's
  jump list. Only the matchup sheet changes: give `Sheet` an opt-in variant (for example a
  `tone` prop that adds `sheet--jumbo`), never restyle `.sheet` itself.
- **It portals into `document.body`**, so `.app[data-skin='jumbo']` rules and the `.jb`
  variables do not reach it. Put `jb` on the sheet's own root or name the colors in its
  rules, the way `.liftbar` does.
- **Motion**: no `AnimatePresence` (its exits never finish under React 19); the sheet's
  mount and unmount is CSS plus a timer in `ui.jsx`. Anything new animates transform only and
  never starts at opacity 0.
- **`tests/test_matchup.py`**: the preview section stays conditional (`data.story &&`),
  `.mu__story` stays clamped (`-webkit-line-clamp` and `overflow: hidden`), and `.mu__h`
  keeps its margin reset. `tests/matchup_check.mjs` covers `normalise` and `seasonOf`.
- **One rank style**: `<Rank>` and `.aprank` only (`tests/test_theme.py`); a scoped override
  like `.jb-team .aprank` is fine.
- **An `h2`/`h3`/`h4` takes the Slate display face from theme.css**, not from the wall it
  sits on. Name `'Big Shoulders Display'` on any heading that should be LED lettering
  (`memory/traps.md`, 2026-09-13).
- **ESPN**: match teams by id, never abbreviation, and never set a browser User-Agent on an
  ESPN request (the sandbox proxy 403s them).
- **The pill that opens the sheet** is guarded by `tests/test_preview_cta.py`. Leave it be.
- **Reuse the stadium parts**: `src/components/Led.jsx` (`.jb-led`), `schoolPanel` in
  `src/lib/schoolField.js` for a team color under white type, `Mark` for a logo on dark, and
  the jumbotron colors already in use: amber `#ffb020`, gold `#ffd65a`, red `#d7200f`, LED
  black `#030406`, cabinet `#1a1e25`.

## Where real data comes from

- `tests/fixtures/espn_summaries.json`: a pre-game summary (North Texas at Indiana, with a
  predictor) and a final one (no predictor), in exactly the shape `fetchMatchup` reads.
- A fresh summary for a current game: the snippet in the `tests/test_matchup.py` docstring,
  urllib's default User-Agent. A game's id in Postgres is its ESPN event id.
- The real Week 1 slate for the rows under the sheet: `outputs/harness/week_live.json`.

## The harness (no dev server)

- `outputs/harness/tools/picks_shots.ps1` builds `outputs/harness/picks_live.html` (the real
  Picks screen, `get_slate` stubbed, a fake Supabase host, a 390px iframe) and shoots
  `#choose`, `#rank` and `#locked`. It blocks every other request, ESPN included.
- For the sheet, add scenarios there: in `picks_stub.js` answer `summary?event=` from the
  saved fixture, and in `picks_live.jsx` click one `.grow__preview` once the rows render.
  Worth a shot each: pre-game (`#sheet`), a final game with no projection, and ESPN failing.
  Measure the sheet the way `picks_live.html` measures the other scenarios (height, smallest
  text, anything spilling). The sheet is fixed to the viewport, so shoot the frame at a
  phone's 844px height, not the page's full height.
- Headless Edge quirks are in the memory note on verifying in the preview pane. A harness
  page must use `index.html`'s font link verbatim, or it photographs a different app.

## Commands

```bash
python -m pytest tests/ -q          # the gate, 374 passing at handoff
npm run build                       # must stay clean
bash deploy.sh                      # ONLY after "push and deploy"
```

## Loose ends

- **The Picks tab's sticky button may not stick.** In Chromium the document scrolls, not
  `.app__body`, so "8 still to pick" and "Lock in my picks" scroll away with the list. Grant
  was asked whether it stays put on his phone and has not said. Do not change it without his
  screenshot (`memory/traps.md` and the phone-only-bugs memory).
- **`WeekScore`**, the old scorebug card exported from `src/components/WeekScore.jsx` (about
  line 190), looks unused; `ScoreBug` and `useHeaderOffset` in the same file are used by the
  Board. A cleanup was offered on 2026-09-12 and never done.
- At handoff, `main` and the live site are in sync: the Picks jumbotron and the Week tab's
  new top are both shipped and proved live.

## Do NOT

- Run `npm run dev` and click around: it reads `.env` and connects to the **live** family
  database. Use a harness built to static files.
- Enter a PIN, sign in to production, or change `pickem.token` or `pickem.draft.v1` on the
  real site.
- Restyle every sheet, reintroduce `AnimatePresence`, or animate a new overlay from
  opacity 0.
- Touch migrations, and never paste 013.
- Deploy without an explicit "push and deploy".
- Use em dashes in anything Grant reads.
