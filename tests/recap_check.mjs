/**
 * Offline checks for src/lib/weekRecap.js, driven by tests/test_recap.py.
 *
 * Node rather than pytest because the module under test is JavaScript, and against
 * tests/fixtures/week1_board.json, which is the real 2026 Week 1 slate, board and roster
 * shaped exactly as get_slate, get_board and list_seats return them.
 *
 * A real week is the right fixture here rather than a made-up one. The recap's whole
 * claim is that it describes what happened, so the assertions below are the numbers the
 * family actually saw: Grant 186, James 179, and the three upsets that landed. If a
 * detector drifts, it drifts away from a week somebody remembers.
 *
 * Prints one line per check and exits non-zero on any failure.
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..')
const { ceiling, weekRecap, decisiveGames, upsets, playerBreakdown } = await import(
  pathToFileURL(join(root, 'src', 'lib', 'weekRecap.js')).href
)

const fx = JSON.parse(
  readFileSync(join(root, 'tests', 'fixtures', 'week1_board.json'), 'utf-8'),
)

let failed = 0
const check = (name, cond, detail = '') => {
  if (!cond) failed++
  console.log(`${cond ? 'ok  ' : 'FAIL'} ${name}${detail ? ` :: ${detail}` : ''}`)
}

/* ---------------------------------------------------------------- the ceiling */

check('a perfect week captures the whole pot', ceiling(20, 20) === 210)
check('16 of 20 could have been worth 200', ceiling(16, 20) === 200)
check('10 of 20 could have been worth 155', ceiling(10, 20) === 155)
check('nothing right is worth nothing', ceiling(0, 20) === 0)
check('more correct than played is clamped', ceiling(25, 20) === 210)
check('an empty week has no ceiling', ceiling(3, 0) === 0)

/* ------------------------------------------------------------------ the totals */

const r = weekRecap(fx.slate, fx.board, fx.seats)
const by = Object.fromEntries(r.players.map((p) => [p.name, p]))

check('the week is complete', r.complete === true)
check('all four are ranked', r.players.length === 4)
check('Grant finished on 186', by.Grant.points === 186, String(by.Grant.points))
check('James finished on 179', by.James.points === 179, String(by.James.points))
check('Parker finished on 164', by.Parker.points === 164, String(by.Parker.points))
check('Nicole finished on 147', by.Nicole.points === 147, String(by.Nicole.points))
check('Grant and James both went 16-4', by.Grant.correct === 16 && by.James.correct === 16)
check('Grant won it alone', r.leaders.length === 1 && r.leaders[0].name === 'Grant')
check('the margin was 7', r.margin === 7, String(r.margin))
check('the week was not shared', r.shared === false)
check('nobody was auto-picked', r.players.every((p) => p.autos === 0))

/* ------------------------------------------------------- ranking, not picking

   The point of this stat: Nicole finished last on points and still ranked her week
   better than anyone. If that inverts, the metric has broken. */

check('Grant captured 93% of his ceiling', by.Grant.captured === 93, String(by.Grant.captured))
check('Nicole captured 95% of hers', by.Nicole.captured === 95, String(by.Nicole.captured))
check(
  'the best ranker is not the week winner',
  by.Nicole.captured > by.Grant.captured,
  `Nicole ${by.Nicole.captured} vs Grant ${by.Grant.captured}`,
)
check(
  'captured never exceeds 100',
  r.players.every((p) => p.captured <= 100),
  JSON.stringify(r.players.map((p) => p.captured)),
)
check(
  'the ceiling matches the ceiling function',
  r.players.every((p) => p.ceiling === ceiling(p.correct, p.games)),
)

/* --------------------------------------------------------- the counterfactuals */

const d = decisiveGames(fx.slate, fx.board, new Map(fx.seats.map((s) => [s.id, s.name])))
const labels = d.map((x) => x.label)

check('two results would have changed the week', d.length === 2, labels.join(' | '))
check('Colorado at Georgia Tech is one of them', labels.includes('COLO at GT'), labels.join(' | '))
check('UNLV at Hawaii is the other', labels.includes('UNLV at HAW'), labels.join(' | '))

const colo = d.find((x) => x.label === 'COLO at GT')
const unlv = d.find((x) => x.label === 'UNLV at HAW')
check('flipping Colorado hands it to James alone',
  colo.leaders.length === 1 && colo.leaders[0] === 'James', JSON.stringify(colo.leaders))
check('flipping UNLV makes it a tie', unlv.shared === true && unlv.leaders.length === 2,
  JSON.stringify(unlv.leaders))
check('the tie is Grant and James', unlv.leaders.includes('Grant') && unlv.leaders.includes('James'))
check('every decisive game names what would have happened instead',
  d.every((x) => x.instead && x.actual && x.instead !== x.actual))

/* A week nobody could have swung with one result must come back empty rather than
   inventing a nearest miss. Forty points clear is out of reach of any single game. */
const runaway = fx.board.map((row) =>
  row.player_name === 'Grant' ? row : { ...row, pick_abbr: 'ZZZ' },
)
check('a runaway week has no decisive game',
  decisiveGames(fx.slate, runaway, new Map(fx.seats.map((s) => [s.id, s.name]))).length === 0)

/* ----------------------------------------------------------------- the upsets */

const u = upsets(fx.slate, fx.board)
check('three favourites lost', u.length === 3, u.map((x) => x.label).join(' | '))
check('they are ordered by how big the upset was', u[0].line >= u[1].line && u[1].line >= u[2].line)
check('Tulsa was the biggest at 13.5', u[0].label === 'OKST at TLSA' && u[0].line === 13.5)
check('nobody called Tulsa', u[0].calledBy.length === 0)
check('nobody called Colorado',
  u.find((x) => x.label === 'COLO at GT').calledBy.length === 0)

const nev = u.find((x) => x.label === 'WKU at NEV')
check('two people called Nevada', nev.calledBy.length === 2, nev.calledBy.join(', '))
check('they were Grant and Nicole',
  nev.calledBy.includes('Grant') && nev.calledBy.includes('Nicole'))

/* -------------------------------------------------------- the rest of the week */

check('favourites went 17 of 20', r.chalk.won === 17 && r.chalk.of === 20,
  `${r.chalk.won}/${r.chalk.of}`)
check('the family went 0-for on three games', r.whiffs.length === 3,
  r.whiffs.map((w) => w.label).join(' | '))
check('SMU at Florida State is one of them',
  r.whiffs.some((w) => w.label === 'SMU at FSU'), r.whiffs.map((w) => w.label).join(' | '))
check('six games were unanimous and right', r.sweeps === 6, String(r.sweeps))

/* ------------------------------------------------------------ gained and lost */

const pb = playerBreakdown(fx.slate, fx.board, fx.seats)
const nicole = pb.find((p) => p.name === 'Nicole')
/* Miami at Stanford and Wisconsin at Notre Dame both cost Nicole exactly 16.0 against
   the field. The tie breaks toward the game she committed more to, which is Notre Dame
   at 2 rather than Stanford at 1. Without that rule this flips on kickoff order. */
check('Nicole lost the most ground at Notre Dame', nicole.worst.label === 'WIS at ND',
  nicole.worst && nicole.worst.label)
check('the tie really was a tie', nicole.worst.edge === -16)
check('and it broke toward the bigger commitment', nicole.worst.confidence === 2)
check('and it was a losing pick', nicole.worst.won === false)
check('a gain is positive and a loss is negative',
  pb.every((p) => (!p.best || p.best.edge > 0) && (!p.worst || p.worst.edge < 0)))
check('solo correct picks are counted',
  pb.every((p) => p.soloRight >= 0 && p.soloRight <= p.correct))

/* -------------------------------------------------- a week still being played */

const midweek = fx.slate.map((g, i) => (i < 5 ? g : { ...g, winner_abbr: null }))
const partial = weekRecap(midweek, fx.board, fx.seats)
check('an unfinished week is not complete', partial.complete === false)
check('and it publishes no recap', partial.decisive.length === 0 && partial.upsets.length === 0)
check('but it still ranks everyone', partial.players.length === 4)

/* ==========================================================================
   src/lib/seasonStats.js

   Week 1 is real; weeks 2 and 3 below are invented, and say so. The season maths is
   arithmetic over weekly rows, so a synthetic set is the right fixture for it: it can
   hold a tied week, a week nobody has played yet and a shared record, none of which
   one real week contains. */

const { seasonStats, seasonTotals, weekHistory, formGeometry } = await import(
  pathToFileURL(join(root, 'src', 'lib', 'seasonStats.js')).href
)

const seat = (id) => fx.seats.find((s) => s.id === id)
const row = (id, week_no, label, points, correct, games) => ({
  player_id: id,
  player_name: seat(id).name,
  player_color: seat(id).color,
  player_team: seat(id).team_id,
  week_no,
  week_label: label,
  points,
  correct,
  games,
})

const seasonRows = [
  // Week 1: the real result.
  row(1, 1, 'Week 1', 186, 16, 20),
  row(2, 1, 'Week 1', 179, 16, 20),
  row(3, 1, 'Week 1', 164, 12, 20),
  row(4, 1, 'Week 1', 147, 10, 20),
  // Week 2: invented, and built to exercise the ties. Grant and James finish level on
  // points AND end the season level on record, so both a shared week and a shared
  // season record get rendered.
  row(1, 2, 'Week 2', 150, 13, 20),
  row(2, 2, 'Week 2', 150, 13, 20),
  row(3, 2, 'Week 2', 120, 11, 20),
  row(4, 2, 'Week 2', 140, 12, 20),
  // Week 3: invented, nothing graded yet.
  row(1, 3, 'Week 3', 0, 0, 0),
  row(2, 3, 'Week 3', 0, 0, 0),
  row(3, 3, 'Week 3', 0, 0, 0),
  row(4, 3, 'Week 3', 0, 0, 0),
]

const s = seasonStats(seasonRows, fx.seats)
const sby = Object.fromEntries(s.players.map((p) => [p.name, p]))

check('an ungraded week is not counted as played', s.played === 2, String(s.played))
check('history runs newest week first', s.weeks[0].week_no === 3)
check('a week with nothing graded has no winner', s.weeks[0].winners.length === 0)
check('week 2 was shared', s.weeks.find((w) => w.week_no === 2).shared === true)
check('and shared by Grant and James',
  s.weeks.find((w) => w.week_no === 2).winners.map((x) => x.name).sort().join(',') === 'Grant,James')
check('week 1 was won outright', s.weeks.find((w) => w.week_no === 1).shared === false)

check('season points add up', sby.Grant.points === 336, String(sby.Grant.points))
check('Grant leads the season', sby.Grant.rank === 1 && sby.James.rank === 2)
check('only graded weeks count towards weeks played', sby.Grant.weeks === 2, String(sby.Grant.weeks))
check('a shared week counts for both people who shared it',
  sby.Grant.weeksWon === 2 && sby.James.weeksWon === 1,
  `Grant ${sby.Grant.weeksWon}, James ${sby.James.weeksWon}`)
check('and for nobody else', sby.Nicole.weeksWon === 0 && sby.Parker.weeksWon === 0)
check('weeks won never exceeds weeks graded',
  s.players.every((p) => p.weeksWon <= s.played))

/* The trap this stat exists to avoid. Grant went 16/20 then 13/20, so his season ceiling
   is 200 + 182 = 382, the two weekly ceilings added. Applying the formula to the season
   totals instead gives ceiling(29, 40) = 754, which would report his efficiency as 45%
   and make the whole column meaningless. */
check('the season ceiling is the sum of the weekly ceilings',
  sby.Grant.ceiling === 382 && sby.Grant.ceiling === ceiling(16, 20) + ceiling(13, 20),
  `${sby.Grant.ceiling} vs ${ceiling(16, 20) + ceiling(13, 20)}`)
check('it is not the formula applied to season totals',
  sby.Grant.ceiling !== ceiling(29, 40), String(ceiling(29, 40)))
check('season efficiency reads as a sane percentage',
  sby.Grant.captured === 88, String(sby.Grant.captured))
check('nobody exceeds their season ceiling',
  s.players.every((p) => p.points <= p.ceiling))

check('best and worst week are found', sby.Grant.best.week_no === 1 && sby.Grant.worst.week_no === 2)
check('the form chart has one column per graded week', s.form.weeks.length === 2)
check('and one series per player', s.form.series.length === 4)
check('form runs oldest to newest', s.form.weeks[0].week_no < s.form.weeks[1].week_no)
check('the form scale covers the biggest week', s.form.max === 186, String(s.form.max))

const recs = Object.fromEntries(s.records.map((x) => [x.key, x]))
check('the best week on record is Grant in Week 1', recs.bestWeek.value === '186' &&
  recs.bestWeek.who === 'Grant, Week 1', recs.bestWeek.who)
/* Grant and James both finished 29 of 40. A superlative nobody holds outright is
   shared rather than broken by a tiebreak the house rules do not have. */
check('a tied record names both holders',
  recs.accuracy.who === 'Grant and James', recs.accuracy.who)
check('every record names who holds it', s.records.every((x) => x.who && x.value))

check('an empty season produces nothing rather than throwing',
  seasonStats([], fx.seats).players.length === 0 && seasonTotals([], fx.seats).length === 0)
check('history of nothing is an empty list', weekHistory([]).length === 0)

/* ------------------------------------------------------------- the form chart

   A chart is the one thing on either tab that can look completely plausible and be
   wrong: a point off the top of the viewBox, or a gridline labelled with a value the
   scale never reaches, both render without erroring and without complaint. */

const geo = formGeometry(s.form)
const allPts = geo.series.flatMap((x) => x.points)

check('every point is inside the viewBox',
  allPts.every((p) => p.x >= 0 && p.x <= geo.W && p.y >= 0 && p.y <= geo.H),
  JSON.stringify(allPts.filter((p) => p.y < 0 || p.y > geo.H)))
check('the scale reaches the best week', geo.top >= s.form.max, `${geo.top} vs ${s.form.max}`)
check('the top gridline is the top of the scale', geo.ticks[2].value === geo.top)
check('zero sits at the bottom of the plot',
  geo.ticks[0].value === 0 && geo.ticks[0].y > geo.ticks[2].y)
check('a bigger week plots higher than a smaller one', (() => {
  const grant = geo.series.find((x) => x.name === 'Grant')
  return grant.points[0].value > grant.points[1].value && grant.points[0].y < grant.points[1].y
})())
check('one column per graded week', geo.columns.length === 2)
check('columns run left to right', geo.columns[0].x < geo.columns[1].x)

/* A week somebody has not played is a hole in their line, never a plotted zero. Drawing
   it as zero would show a collapse that did not happen. */
const gap = formGeometry({
  max: 186,
  weeks: s.form.weeks,
  series: [{ id: 1, name: 'Grant', color: '#B85C1F', points: [186, null] }],
})
check('a missing week is a gap, not a zero', gap.series[0].points.length === 1,
  JSON.stringify(gap.series[0].points))

/* One graded week never reaches the chart (Form bails below two), but the geometry must
   still be finite rather than dividing by zero on n-1. */
const single = formGeometry({
  max: 186,
  weeks: [{ week_no: 1, label: 'Week 1' }],
  series: [{ id: 1, name: 'Grant', color: '#B85C1F', points: [186] }],
})
check('a single column is centred and finite',
  Number.isFinite(single.columns[0].x) && single.columns[0].x > 0)
check('an all-zero season still has a scale', formGeometry({
  max: 0, weeks: s.form.weeks, series: [],
}).top === 25)

console.log(failed ? `\n${failed} check(s) failed` : '\nall checks passed')
process.exit(failed ? 1 : 0)
