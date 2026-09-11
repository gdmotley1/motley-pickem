/**
 * Offline checks for src/lib/matchup.js, driven by tests/test_matchup.py.
 *
 * Node rather than pytest because the module under test is JavaScript, and against a
 * saved payload rather than live ESPN so the gate keeps working on a plane, the same
 * bargain tests/fixtures/slate_week01.json makes for the Python side.
 *
 * Regenerate the fixture when ESPN changes shape:
 *   python -c "see the docstring in tests/test_matchup.py"
 *
 * Prints one line per check and exits non-zero on the first failure count.
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..')
const { normalise, seasonOf } = await import(
  pathToFileURL(join(root, 'src', 'lib', 'matchup.js')).href
)

const fx = JSON.parse(
  readFileSync(join(root, 'tests', 'fixtures', 'espn_summaries.json'), 'utf-8'),
)

let failed = 0
const check = (name, cond, detail = '') => {
  if (!cond) failed++
  console.log(`${cond ? 'ok  ' : 'FAIL'} ${name}${detail ? ` :: ${detail}` : ''}`)
}

/* UNT @ IU, pre-game. Home Indiana (84), away North Texas (249). */
const IU = '84'
const UNT = '249'
const pre = normalise(fx.pregame, IU, UNT)

check('win probability is read off the predictor', pre.winProb !== null, JSON.stringify(pre.winProb))
check('the home favourite gets the larger share', pre.winProb.home > pre.winProb.away)
check('the two shares sum to 100', Math.abs(pre.winProb.home + pre.winProb.away - 100) < 0.5)
check('records come back for both sides', !!pre.records.home && !!pre.records.away, JSON.stringify(pre.records))
/*
 * Form is THIS SEASON only, as of 2026-09-11.
 *
 * ESPN's last-five window spans seasons, so in September it is mostly last year. This
 * fixture is a week 1 game of the 2026 season whose five "recent" games run from
 * November 2025 to the Playoff final in January 2026. Showing those as current form made
 * Indiana look like five straight wins by a team that has not played yet.
 *
 * So empty is the correct answer here, and it is the whole point: in week 1 nobody has
 * played. The section hides itself rather than printing an empty row.
 */
check('last season is excluded entirely',
  pre.lastFive.home.length === 0 && pre.lastFive.away.length === 0,
  `home ${pre.lastFive.home.length}, away ${pre.lastFive.away.length}`)
check('venue is present', !!pre.venue, pre.venue)
check('weather is present', Number.isFinite(pre.weather?.temp), JSON.stringify(pre.weather))

/*
 * The regression this file exists for.
 *
 * fetchMatchup used to cache the NORMALISED object under the event id alone, so asking
 * for the same game with home and away swapped returned the first call's labels: a
 * caller that disagreed about which team was home got silently mislabelled data instead
 * of an error. Everything is keyed on ESPN team id now, so flipping the arguments has to
 * flip the answer.
 */
const flipped = normalise(fx.pregame, UNT, IU)
check('flipping home/away flips the win probability',
  flipped.winProb.home === pre.winProb.away && flipped.winProb.away === pre.winProb.home,
  `${JSON.stringify(pre.winProb)} -> ${JSON.stringify(flipped.winProb)}`)
check('flipping home/away flips the form',
  JSON.stringify(flipped.lastFive.home) === JSON.stringify(pre.lastFive.away) &&
  JSON.stringify(flipped.lastFive.away) === JSON.stringify(pre.lastFive.home))

/*
 * Ids that match nobody must degrade to nulls. Falling back to positional order here
 * would attach one team's record to the other, which is the TUL/TULN class of bug that
 * scripts/resolve_slate.py already refuses to guess at.
 */
const bogus = normalise(fx.pregame, '999999', '888888')
check('unmatched ids give null rather than another team\'s data',
  bogus.winProb === null && bogus.records.home === null && bogus.lastFive.home.length === 0)

/*
 * WES @ KENN, already final. ESPN drops both the odds and the predictor once a game
 * ends, so this is the shape the sheet has to render without a projection.
 */
const KENN = '338'
const WES = '2698'
const done = normalise(fx.final, KENN, WES)
check('a finished game has no projection', done.winProb === null)
check('a finished game still reports real records',
  done.records.home === '1-0' && done.records.away === '0-2', JSON.stringify(done.records))
// Checked on the FINAL fixture, whose two records differ (1-0 and 0-2). On the pre-game
// fixture both sides are "0-0" in week 1, so the same assertion holds whatever the code
// does and proves nothing. It passed against a deliberately broken build for exactly
// that reason before being moved here.
const doneFlipped = normalise(fx.final, WES, KENN)
check('flipping home/away flips two records that actually differ',
  doneFlipped.records.home === done.records.away &&
    doneFlipped.records.away === done.records.home &&
    done.records.home !== done.records.away,
  `${JSON.stringify(done.records)} -> ${JSON.stringify(doneFlipped.records)}`)
check('a finished game still reports a venue', !!done.venue, done.venue)
check('a missing lastFiveGames block yields empty arrays, not a throw',
  Array.isArray(done.lastFive.home) && done.lastFive.home.length === 0)

/* An empty payload must not throw: a caller should get a blank sheet, never a crash. */
const empty = normalise({}, '1', '2')
check('an empty payload normalises to all-empty',
  empty.winProb === null && empty.venue === null && empty.weather === null &&
    empty.lastFive.home.length === 0)

/*
 * The season filter, driven rather than described.
 *
 * A CFB season labelled Y runs August Y to January Y+1, so the January Playoff belongs to
 * the previous year. Getting that boundary wrong in either direction is the whole bug:
 * one way keeps last season, the other throws away the bowl games of the season you are
 * actually in.
 */
check('August starts a season', seasonOf('2026-08-30T23:00Z') === 2026)
check('September is mid season', seasonOf('2026-09-05T16:00Z') === 2026)
check('December belongs to its own year', seasonOf('2026-12-06T01:00Z') === 2026)
check('January belongs to the year before', seasonOf('2027-01-20T00:30Z') === 2026)
check('July is the previous season, not the coming one', seasonOf('2026-07-04T00:00Z') === 2025)
check('an undateable game does not crash', seasonOf(null) === null && seasonOf('nonsense') === null)

/* And the other half: games inside the season must survive. Same payload, with the dates
   moved into the 2026 season, so the only thing that changed is the year. */
const thisSeason = JSON.parse(JSON.stringify(fx.pregame))
for (const entry of thisSeason.lastFiveGames || []) {
  for (const e of entry.events || []) {
    e.gameDate = e.gameDate.replace(/^2025-11/, '2026-09').replace(/^2025-12/, '2026-09')
                           .replace(/^2026-01/, '2026-09')
  }
}
const kept = normalise(thisSeason, IU, UNT)
check('games inside the season are kept',
  kept.lastFive.home.length === 5 && kept.lastFive.away.length === 5,
  `home ${kept.lastFive.home.length}, away ${kept.lastFive.away.length}`)
check('kept entries still carry a result, a score and an opponent',
  kept.lastFive.home.every((g) => g.result && g.score && g.opponent))

/* A payload with no season stated must not filter everything away. Showing last year is
   a smaller wrong than showing nothing. */
const noSeason = JSON.parse(JSON.stringify(fx.pregame))
delete noSeason.header.season
delete noSeason.header.competitions
const loose = normalise(noSeason, IU, UNT)
check('an unknown season keeps every game rather than none',
  loose.lastFive.home.length === 5)

/*
 * ESPN's preview line, added 2026-09-11 because the sheet looked empty.
 *
 * Headline only, never `description`: that field came back from the live API with a
 * mojibake character leading it, which would put a black diamond on a family's phone.
 */
check('no article means no story, rather than an empty box',
  pre.story === null, JSON.stringify(pre.story))

const withStory = JSON.parse(JSON.stringify(fx.pregame))
withStory.article = {
  headline: 'Ohio State and Texas clash again in title-contender matchup',
  description: '� Across a history of college football that dates to the 1800s',
}
const told = normalise(withStory, IU, UNT)
check('the headline is the story',
  told.story === 'Ohio State and Texas clash again in title-contender matchup', told.story)
check('the description is never used, mojibake and all',
  !String(told.story).includes('�'))

const blank = JSON.parse(JSON.stringify(fx.pregame))
blank.article = { headline: '   ' }
check('a whitespace headline is null, not a blank quote',
  normalise(blank, IU, UNT).story === null)

console.log(failed ? `\n${failed} failed` : '\nall passed')
process.exit(failed ? 1 : 0)
