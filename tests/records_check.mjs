/**
 * The record book's arithmetic, checked against the real module.
 *
 * Built on a hand-made season small enough to work out on paper: 3 players, 3 weeks,
 * 4 games a week. Confidence runs 1..4 rather than 1..20 because ceiling() is a function
 * of the week's size, and a four-game week makes The Fade checkable in your head.
 *
 * Every expectation is derived from the table below rather than from a run of the code.
 * A fixture generated from the implementation agrees with any bug the implementation has.
 *
 * Run by tests/test_records.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)
const { seasonRecords } = await load('src/lib/seasonRecords.js')

/* --------------------------------------------------------------- the fixture ---- */

const ROSTER = [
  { id: 1, name: 'Grant', color: '#B85C1F', team_id: '2751' }, // Wyoming
  { id: 2, name: 'James', color: '#1F6F4A', team_id: '61' }, // Georgia
  { id: 3, name: 'Nicole', color: '#8A2E4F', team_id: null }, // no school
]

/* week, id, away, home, awayId, homeId, awayScore, homeScore, winner, favourite, line */
const GAMES = [
  [1, 101, 'WYO', 'UGA', '2751', '61', 10, 31, 'UGA', 'UGA', -21],
  [1, 102, 'TOL', 'MSU', '200', '127', 25, 24, 'TOL', 'MSU', -10],
  [1, 103, 'OU', 'MICH', '201', '130', 14, 17, 'MICH', 'MICH', -3],
  [1, 104, 'LSU', 'CLEM', '99', '228', 28, 14, 'LSU', 'CLEM', -6.5],
  [2, 201, 'UGA', 'BAMA', '61', '333', 20, 17, 'UGA', 'BAMA', -4],
  [2, 202, 'WYO', 'BSU', '2751', '68', 7, 42, 'BSU', 'BSU', -14],
  [2, 203, 'TEX', 'OU', '251', '201', 35, 30, 'TEX', 'TEX', -7],
  [2, 204, 'PITT', 'WVU', '221', '277', 17, 16, 'PITT', 'WVU', -2.5],
  [3, 301, 'UGA', 'FLA', '61', '57', 24, 21, 'UGA', 'UGA', -9],
  [3, 302, 'MICH', 'OSU', '130', '194', 13, 30, 'OSU', 'OSU', -8],
  [3, 303, 'WYO', 'CSU', '2751', '36', 28, 20, 'WYO', 'WYO', -3.5],
  [3, 304, 'AUB', 'LSU', '2', '99', 21, 24, 'LSU', 'LSU', -5],
]

/* Confidence per player per game, in the order above: 1..4 each week, used once.
   A trailing "!" means they took the AWAY side; otherwise the home side. "A" is an
   auto-pick. */
const PICKS = {
  //        101   102  103  104  | 201   202  203   204  | 301   302  303   304
  1: ['4', '1!', '3', '2!', '2!', '4', '3!', '1!', '4', '3', '2!', '1'], // Grant
  2: ['4', '2', '3', '1!', '4!', '3', '2!', '1A', '4!', '2', '1!', '3'], // James
  3: ['3', '1!', '4', '2', '1!', '2', '4!', '3', '2!', '4', '1!', '3'], // Nicole
}

const rows = []
GAMES.forEach((g, i) => {
  const [wk, id, away, home, awayId, homeId, as, hs, winner, fav, line] = g
  for (const p of ROSTER) {
    const spec = PICKS[p.id][i]
    rows.push({
      week_no: wk,
      week_label: `Week ${wk}`,
      game_id: id,
      kickoff: `2026-09-0${wk}T19:${String(i).padStart(2, '0')}:00Z`,
      home_abbr: home,
      away_abbr: away,
      home_id: homeId,
      away_id: awayId,
      home_score: hs,
      away_score: as,
      winner_abbr: winner,
      favorite_abbr: fav,
      underdog_abbr: fav === home ? away : home,
      spread_line: line,
      player_id: p.id,
      pick_abbr: spec.includes('!') ? away : home,
      confidence: parseInt(spec, 10),
      auto: spec.includes('A'),
    })
  }
})

const { records, family, weeks } = seasonRecords(rows, ROSTER)
const get = (k) => {
  const r = records.find((x) => x.key === k)
  assert.ok(r, `no record named ${k}`)
  return r
}
const shown = (k, name) => {
  const row = get(k).rows.find((r) => r.name === name)
  assert.ok(row, `${name} is missing from ${k}`)
  return row
}

assert.equal(weeks, 3, 'expected three weeks in the fixture')

/* ------------------------------------------------------------ worked by hand ---- */

/* The first version of this block was wrong, and how is worth recording: a "4" was read
   as "took the favourite" when it means "took the HOME side", and seven of these twelve
   games are won by the away team. Everything below now comes off this table, built one
   game at a time.
 *
 *     idx  game            winner  side     Grant         James         Nicole
 *      0   101 WYO at UGA   UGA    home   c4 home  W    c4 home  W    c3 home  W
 *      1   102 TOL at MSU   TOL    away   c1 away  W    c2 home  L    c1 away  W
 *      2   103 OU  at MICH  MICH   home   c3 home  W    c3 home  W    c4 home  W
 *      3   104 LSU at CLEM  LSU    away   c2 away  W    c1 away  W    c2 home  L
 *      4   201 UGA at BAMA  UGA    away   c2 away  W    c4 away  W    c1 away  W
 *      5   202 WYO at BSU   BSU    home   c4 home  W    c3 home  W    c2 home  W
 *      6   203 TEX at OU    TEX    away   c3 away  W    c2 away  W    c4 away  W
 *      7   204 PITT at WVU  PITT   away   c1 away  W    c1 home  L*   c3 home  L
 *      8   301 UGA at FLA   UGA    away   c4 home  L    c4 away  W    c2 away  W
 *      9   302 MICH at OSU  OSU    home   c3 home  W    c2 home  W    c4 home  W
 *     10   303 WYO at CSU   WYO    away   c2 away  W    c1 away  W    c1 away  W
 *     11   304 AUB at LSU   LSU    home   c1 home  W    c3 home  W    c3 home  W
 *                                                       * auto-pick
 *
 *   With ceiling(c, 4) = c(9-c)/2, so 4 right is 10 and 3 right is 9:
 *
 *              W1              W2              W3            fade
 *     Grant    4/4, 10, c10    4/4, 10, c10    3/4,  6, c9     -3
 *     James    3/4,  8, c9     3/4,  9, c9     4/4, 10, c10    -1
 *     Nicole   3/4,  8, c9     3/4,  7, c9     4/4, 10, c10    -3
 */

/* The Fade. James left one point behind all season, the other two left three. Lowest
   wins, and getting that direction backwards would crown the worst player, plausibly. */
assert.equal(shown('fade', 'James').display, '-1')
assert.equal(shown('fade', 'Grant').display, '-3')
assert.equal(shown('fade', 'Nicole').display, '-3')
assert.equal(get('fade').rows[0].name, 'James', 'The Fade must rank LOW first')
assert.equal(get('fade').holders.length, 1)

/* Best week, sharpest week and perfect order are three-way ties here: everyone has
   exactly one clean sweep. Ties stand. */
for (const k of ['best', 'sharp', 'order']) {
  assert.equal(get(k).holders.length, 3, `${k} should be shared three ways in this fixture`)
  assert.equal(get(k).shared, true)
}
assert.equal(shown('best', 'Grant').display, '10')
assert.equal(shown('sharp', 'James').display, '4-0')
assert.equal(shown('order', 'Nicole').display, '100%')

/* Worst week: Grant's 6 in week 3 is the lowest anyone posted. Lowest first. */
assert.equal(shown('worst', 'Grant').display, '6')
assert.equal(get('worst').rows[0].name, 'Grant')

/* Hot streak, game by game in kickoff order across weeks. Grant wins 0 through 7, loses
   8, wins 9 to 11: eight. James loses 1 and 7, so his best run is 2 to 6: five. Nicole
   loses 3 and 7, so hers is 8 to 11: four. */
assert.equal(shown('streak', 'Grant').value, 8)
assert.equal(shown('streak', 'James').value, 5)
assert.equal(shown('streak', 'Nicole').value, 4)
assert.equal(get('streak').holders[0], 'Grant')

/* Slept on it. Only James has an auto-pick. Two players on zero must SHARE the record
   rather than one of them winning it on nothing. */
assert.equal(shown('slept', 'James').value, 1)
assert.equal(get('slept').rows[0].value, 0, 'Slept on it must rank LOW first')
assert.equal(get('slept').holders.length, 2)
assert.equal(get('slept').shared, true)

/* The Anchor, each player's confidence-4 picks.
   Grant: index 0 UGA won, 5 BSU won, 8 FLA LOST. 2-1.
   James: 0, 4 and 8, all Georgia, all won. 3-0.
   Nicole: 2 MICH, 6 TEX, 9 OSU, all won. 3-0. */
assert.equal(shown('anchor', 'Grant').display, '2-1')
assert.equal(shown('anchor', 'James').display, '3-0')
assert.equal(shown('anchor', 'Nicole').display, '3-0')
assert.equal(get('anchor').holders.length, 2, 'James and Nicole both went 3-0')

/* Homer. Grant is Wyoming, at index 0, 5 and 10: he took UGA over them, BSU over them,
   then finally backed them at 10 and they won. 1-0, backed 1 of 3.
   James is Georgia, at 0, 4 and 8: took them every time, won every time.
   Nicole has no school, so this must come back NULL rather than zero. A record that does
   not apply to you must never read as you being worst at it. */
assert.equal(shown('homer', 'Grant').display, '1-0')
assert.equal(shown('homer', 'Grant').detail, 'backed them 1 of 3')
assert.equal(shown('homer', 'James').display, '3-0')
assert.equal(shown('homer', 'James').detail, 'backed them 3 of 3')
assert.equal(shown('homer', 'Nicole').value, null)
assert.equal(shown('homer', 'Nicole').display, 'no school')
assert.equal(get('homer').holders[0], 'James')
assert.equal(get('homer').rows[get('homer').rows.length - 1].name, 'Nicole',
  'a null must sort last rather than being treated as a zero')

/* Biggest miss, the most confidence anyone spent on a loser. Grant lost only index 8, at
   4. James lost 1 (c2) and 7 (c1). Nicole lost 3 (c2) and 7 (c3). */
assert.equal(shown('miss', 'Grant').display, '4')
assert.equal(shown('miss', 'Grant').detail, 'FLA over UGA, Week 3')
assert.equal(shown('miss', 'James').display, '2')
assert.equal(shown('miss', 'Nicole').display, '3')

/* Lone wolf. Index 7 is the only game exactly one player called: Grant took PITT while
   both others took WVU. Every other game was got by two or three of them. */
assert.equal(shown('wolf', 'Grant').value, 1)
assert.equal(shown('wolf', 'Grant').detail, 'best: PITT at 1, Week 2')
assert.equal(shown('wolf', 'James').value, 0)
assert.equal(shown('wolf', 'Nicole').value, 0)

/* Upset special. The underdogs that won are TOL +10, LSU +6.5, UGA +4 and PITT +2.5.
   Grant took all four, Nicole took TOL and UGA, James took LSU and UGA. */
assert.equal(shown('upset', 'Grant').display, '+10')
assert.equal(shown('upset', 'Nicole').display, '+10')
assert.equal(shown('upset', 'James').display, '+6.5')
assert.equal(get('upset').holders.length, 2, 'Grant and Nicole both beat a +10')
assert.ok(shown('upset', 'Grant').detail.includes('TOL'))

/* Coin flips. SIX games here are decided by three or fewer, not the four that are
   obvious: 102 by 1, 103 by 3, 201 by 3, 204 by 1, and then 301 (24-21) and 304 (21-24),
   both of which read as ordinary results until you subtract.
   Grant loses only 301 of those six, Nicole only 204, James loses 102 and 204. */
assert.equal(shown('flips', 'Grant').display, '5-1')
assert.equal(shown('flips', 'Nicole').display, '5-1')
assert.equal(shown('flips', 'James').display, '4-2')
assert.equal(shown('flips', 'Grant').detail, '6 one-score games')
assert.equal(get('flips').holders.length, 2, 'Grant and Nicole are both 5-1')

/* Chalk rate. The trap here is that a favourite is often the AWAY team: TEX at index 6,
   UGA at 8 and WYO at 10 are all road favourites, so "took the home side" and "took the
   chalk" are different questions. James and Nicole each took the favourite 10 times in
   12; Grant 7. */
assert.equal(shown('chalk', 'James').display, '83%')
assert.equal(shown('chalk', 'Nicole').display, '83%')
assert.equal(shown('chalk', 'Grant').display, '58%')
assert.equal(get('chalk').holders.length, 2, 'James and Nicole are both on 83%')
assert.equal(shown('chalk', 'James').detail, 'plays the chalk')
assert.equal(shown('chalk', 'Grant').detail, 'mixes it up')

/* Team ledger. James backed Georgia three times, at 4, 4 and 4, and they won every time. */
const jm = shown('money', 'James')
assert.equal(jm.display, '+12')
assert.ok(jm.detail.startsWith('UGA, 3 picks'), `unexpected detail: ${jm.detail}`)
assert.equal(jm.teamId, '61', 'the money team must carry its ESPN id so a logo can render')

/* Head to head, from the weekly totals in the table above.
   W1 Grant 10, James 8, Nicole 8. W2 Grant 10, James 9, Nicole 7. W3 Grant 6, James 10,
   Nicole 10. Ties stand and count for neither side. */
const h2h = (a, b) => family.grid.find((x) => x.name === a).vs.find((y) => y.name === b)
assert.deepEqual({ w: h2h('Grant', 'James').w, l: h2h('Grant', 'James').l }, { w: 2, l: 1 })
assert.deepEqual({ w: h2h('Grant', 'Nicole').w, l: h2h('Grant', 'Nicole').l }, { w: 2, l: 1 })
assert.deepEqual({ w: h2h('James', 'Nicole').w, l: h2h('James', 'Nicole').l }, { w: 1, l: 0 })

/* Eight of the twelve games were called by all three, and none fooled everybody. The
   trap is index 7, which got two of the three. */
assert.equal(family.unanimousRight, 8)
assert.equal(family.unanimousWrong, 0)
assert.equal(family.trap.label, 'PITT at WVU')
assert.equal(family.trap.missed, 2)
assert.equal(family.trap.week, 'Week 2')

/* -------------------------------------------------------------- the invariants ---- */

/* Every record ranks every seat. This is the promise Grant chose on 2026-09-11: holder
   plus the chasing pack, so a record that can only name a winner is a bug. */
for (const r of records) {
  assert.equal(r.rows.length, ROSTER.length,
    `${r.key} ranks ${r.rows.length} players, not ${ROSTER.length}`)
  for (const row of r.rows) {
    assert.ok(row.name, `${r.key} has a row with no name`)
    assert.ok(row.display != null && row.display !== '',
      `${r.key} leaves ${row.name} with nothing to show`)
  }
  assert.ok(r.label && r.blurb, `${r.key} is missing its label or blurb`)
  assert.ok(['personal', 'drama', 'teams', 'classic'].includes(r.group),
    `${r.key} is in group "${r.group}", which no section renders`)
}

/* Sort direction, checked both ways for every record rather than for the three I happen
   to remember. */
for (const r of records) {
  const vals = r.rows.map((x) => x.value).filter((v) => v != null)
  const sorted = [...vals].sort((a, b) => a - b)
  const asc = JSON.stringify(vals) === JSON.stringify(sorted)
  const desc = JSON.stringify(vals) === JSON.stringify([...sorted].reverse())
  assert.ok(asc || desc, `${r.key} is not sorted at all`)
  if (['fade', 'slept', 'worst'].includes(r.key)) {
    assert.ok(asc, `${r.key} must put the LOWEST number first`)
  } else {
    assert.ok(desc, `${r.key} must put the highest number first`)
  }
}

/* Nulls last, always, and a null never holds a record. */
for (const r of records) {
  const idx = r.rows.map((x) => x.value)
  const firstNull = idx.indexOf(null)
  if (firstNull >= 0) {
    assert.ok(idx.slice(firstNull).every((v) => v == null),
      `${r.key} sorts a real value below a null`)
  }
  assert.ok(!r.holders.some((h) => shown(r.key, h).value == null),
    `${r.key} awards the record to somebody it does not apply to`)
}

/* Head to head must be symmetric. An asymmetric grid is the classic bug here and it
   renders as perfectly normal. */
for (const a of family.grid) {
  assert.equal(a.vs.length, ROSTER.length - 1, 'head to head must cover everyone else')
  for (const v of a.vs) {
    const back = family.grid.find((b) => b.id === v.id).vs.find((x) => x.id === a.id)
    assert.equal(v.w, back.l, `${a.name} vs ${v.name} is not symmetric`)
    assert.equal(v.l, back.w, `${a.name} vs ${v.name} is not symmetric`)
    assert.ok(v.w + v.l <= weeks, 'more head-to-head results than there are weeks')
  }
}

/* Empty in, empty out. The Season tab renders before the first week is graded. */
const empty = seasonRecords([], ROSTER)
assert.deepEqual(empty.records, [])
assert.equal(empty.family, null)
assert.equal(seasonRecords(null, null).records.length, 0)

console.log('records ok: %d records over %d weeks, %d players each',
  records.length, weeks, ROSTER.length)
