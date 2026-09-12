/**
 * The record book's arithmetic, checked against the real module.
 *
 * Twelve records, all plain: most points in a week, best record in a week, fewest points,
 * biggest blowout, most weeks won, best overall record, most points in a season, perfect
 * week, longest winning streak, biggest upset called, worst pick, only one who called it.
 *
 * The fixture is deliberately tiny so every expectation can be worked out on paper: three
 * players, three weeks, weekly totals typed in rather than derived. A fixture generated
 * from the implementation agrees with any bug the implementation has.
 *
 * Run by tests/test_records.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)
const { seasonRecords, GROUPS } = await load('src/lib/seasonRecords.js')

/* --------------------------------------------------------------- the fixture ---- */

const ROSTER = [
  { id: 1, name: 'Grant', color: '#B85C1F', team_id: '2751' },
  { id: 2, name: 'James', color: '#1F6F4A', team_id: '61' },
  { id: 3, name: 'Nicole', color: '#8A2E4F', team_id: null },
]

/*  wk  Grant          James          Nicole         week winner
 *   1  150, 16/20     120, 14/20     120, 14/20     Grant by 30
 *   2   90, 11/20     140, 15/20     140, 15/20     James and Nicole, shared
 *   3  110, 13/20     100, 12/20     210, 20/20     Nicole by 100, and perfect
 *
 *  season:  Grant 350, 40-20    James 360, 41-19    Nicole 470, 49-11
 */
const SEASON = [
  [1, 1, 150, 16], [1, 2, 120, 14], [1, 3, 120, 14],
  [2, 1, 90, 11], [2, 2, 140, 15], [2, 3, 140, 15],
  [3, 1, 110, 13], [3, 2, 100, 12], [3, 3, 210, 20],
].map(([wk, pid, points, correct]) => ({
  player_id: pid, week_no: wk, week_label: `Week ${wk}`, points, correct, games: 20,
}))

/* Four graded games with picks, for the last four records. Confidence 1..4, "h" or "a"
 * for the side taken, in roster order.
 *   g  winner  favourite  line   Grant       James       Nicole
 *   1  away    home       -10  c4 away W   c1 home L   c2 away W    a +10 dog hits
 *   2  home    home        -3  c3 home W   c4 home W   c1 home W    everybody
 *   3  away    home       -21  c2 away W   c3 home L   c4 home L    Grant alone
 *   4  home    away        -7  c1 home W   c2 away L   c3 away L    Grant alone
 */
const GAMES = [
  [1, 'away', 'home', -10, ['a4', 'h1', 'a2']],
  [2, 'home', 'home', -3, ['h3', 'h4', 'h1']],
  [3, 'away', 'home', -21, ['a2', 'h3', 'h4']],
  [4, 'home', 'away', -7, ['h1', 'a2', 'a3']],
]
const PICKS = []
for (const [id, winnerSide, favSide, line, specs] of GAMES) {
  const home = `H${id}`
  const away = `A${id}`
  specs.forEach((spec, i) => {
    PICKS.push({
      week_no: 1, week_label: 'Week 1',
      game_id: id, kickoff: `2026-09-05T1${id}:00:00Z`,
      home_abbr: home, away_abbr: away,
      winner_abbr: winnerSide === 'home' ? home : away,
      favorite_abbr: favSide === 'home' ? home : away,
      underdog_abbr: favSide === 'home' ? away : home,
      spread_line: line,
      player_id: i + 1,
      pick_abbr: spec[0] === 'h' ? home : away,
      confidence: parseInt(spec.slice(1), 10),
      auto: false,
    })
  })
}

const book = seasonRecords(SEASON, PICKS, ROSTER)
const get = (k) => {
  const r = book.records.find((x) => x.key === k)
  assert.ok(r, `no record named ${k}`)
  return r
}
const shown = (k, name) => {
  const row = get(k).rows.find((r) => r.name === name)
  assert.ok(row, `${name} missing from ${k}`)
  return row
}

assert.equal(book.weeks, 3)
assert.equal(book.hasPicks, true)
assert.equal(book.records.length, 12, `expected 12 records, got ${book.records.length}`)

/* ------------------------------------------------------------ worked by hand ---- */

// ---- by the week
assert.equal(shown('week_points', 'Nicole').display, '210')
assert.equal(shown('week_points', 'Grant').display, '150')
assert.deepEqual(get('week_points').holders, ['Nicole'])

assert.equal(shown('week_record', 'Nicole').display, '20-0')
assert.equal(shown('week_record', 'Grant').display, '16-4')
assert.deepEqual(get('week_record').holders, ['Nicole'])

/* The one record where the LOWEST number wins it. Grant's 90 in week 2 is the worst
   anyone posted. Backwards, this hands the record to Nicole, who had the best season,
   and it would look entirely plausible on screen. */
assert.equal(shown('week_low', 'Grant').display, '90')
assert.deepEqual(get('week_low').holders, ['Grant'])
assert.equal(get('week_low').rows[0].name, 'Grant', 'lowest must sort first')

/* Blowout is the margin over the best OTHER player that week. Grant took week 1 by 30,
   Nicole took week 3 by 100. James never won outright: week 2 was shared, so his margin
   is 0 and he must not hold this. */
assert.equal(shown('blowout', 'Nicole').display, '100')
assert.equal(shown('blowout', 'Grant').display, '30')
assert.equal(shown('blowout', 'James').display, '0')
assert.deepEqual(get('blowout').holders, ['Nicole'])

// ---- by the season
/* Week 2 tied on 140 and ties stand, so it counts for both James and Nicole. */
assert.equal(shown('weeks_won', 'Nicole').display, '2')
assert.equal(shown('weeks_won', 'Grant').display, '1')
assert.equal(shown('weeks_won', 'James').display, '1')
assert.deepEqual(get('weeks_won').holders, ['Nicole'])

assert.equal(shown('record', 'Nicole').display, '49-11')
assert.equal(shown('record', 'James').display, '41-19')
assert.equal(shown('record', 'Grant').display, '40-20')

assert.equal(shown('points', 'Nicole').display, '470')
assert.equal(shown('points', 'James').display, '360')
assert.equal(shown('points', 'Grant').display, '350')

assert.equal(shown('perfect', 'Nicole').display, '1x')
assert.equal(shown('perfect', 'Grant').display, '0')
assert.deepEqual(get('perfect').holders, ['Nicole'])
assert.equal(get('perfect').unclaimed, false)

// ---- single games
/* Grant won all four in kickoff order, so four. James won only game 2: one. Nicole won
   1 and 2 back to back and then lost: two. */
assert.equal(shown('streak', 'Grant').display, '4')
assert.equal(shown('streak', 'James').display, '1')
assert.equal(shown('streak', 'Nicole').display, '2')

/* Underdog winners are game 1 (+10) and game 3 (+21). Grant took both, Nicole took game 1
   only, James took neither and shows a dash rather than a zero. */
assert.equal(shown('upset', 'Grant').display, '+21')
assert.equal(shown('upset', 'Nicole').display, '+10')
assert.equal(shown('upset', 'James').display, '—')
assert.deepEqual(get('upset').holders, ['Grant'])

/* Worst pick is the most confidence spent on a loser. Grant never lost, so he has no
   value at all and must not sit at the bottom on a fabricated zero. */
assert.equal(shown('worst_pick', 'Grant').value, null, 'a player who never lost has no worst pick')
assert.equal(shown('worst_pick', 'James').display, '3')
assert.equal(shown('worst_pick', 'Nicole').display, '4')
assert.deepEqual(get('worst_pick').holders, ['Nicole'])
assert.equal(get('worst_pick').rows[get('worst_pick').rows.length - 1].name, 'Grant',
  'a null must sort last, never be treated as a zero')

/* Games exactly one player called: 3 and 4, both Grant. Game 1 was Grant and Nicole,
   game 2 was everybody. */
assert.equal(shown('lone', 'Grant').display, '2')
assert.equal(shown('lone', 'James').display, '0')
assert.deepEqual(get('lone').holders, ['Grant'])

/* -------------------------------------------------------------- the invariants ---- */

/* Plain enough to read cold, which is the whole reason this file was rewritten. The
   seventeen invented terms that Grant threw out are banned by name, so nobody can quietly
   reintroduce one. */
const BANNED = ['anchor', 'fade', 'chalk', 'homer', 'nemesis', 'money team', 'coin flip',
  'slept', 'perfect order', 'sharpest', 'hot streak', 'lone wolf', 'most picked',
  'biggest miss', 'upset special']
for (const r of book.records) {
  const l = r.label.toLowerCase()
  for (const b of BANNED) {
    assert.ok(!l.includes(b), `"${r.label}" is one of the invented terms that got cut`)
  }
  assert.ok(r.label.length <= 26, `"${r.label}" will not fit a square`)
}

for (const r of book.records) {
  assert.equal(r.rows.length, ROSTER.length, `${r.key} does not rank everybody`)
  for (const row of r.rows) {
    assert.ok(row.name && row.display !== '' && row.display != null,
      `${r.key} leaves ${row.name} with nothing to show`)
  }
  assert.ok(GROUPS.some(([g]) => g === r.group), `${r.key} is in unrendered group ${r.group}`)
}

/* Sort direction for every record, both ways. */
for (const r of book.records) {
  const vals = r.rows.map((x) => x.value).filter((v) => v != null)
  const sorted = [...vals].sort((a, b) => a - b)
  const asc = JSON.stringify(vals) === JSON.stringify(sorted)
  const desc = JSON.stringify(vals) === JSON.stringify([...sorted].reverse())
  assert.ok(asc || desc, `${r.key} is not sorted`)
  if (r.key === 'week_low') assert.ok(asc, 'Fewest points in a week must rank LOWEST first')
  else assert.ok(desc, `${r.key} must rank highest first`)
}

/* Nulls last, and a null never holds a record. */
for (const r of book.records) {
  const vals = r.rows.map((x) => x.value)
  const firstNull = vals.indexOf(null)
  if (firstNull >= 0) {
    assert.ok(vals.slice(firstNull).every((v) => v == null), `${r.key} sorts a value below a null`)
  }
  for (const h of r.holders) {
    assert.notEqual(shown(r.key, h).value, null,
      `${r.key} is held by somebody it does not apply to`)
  }
}

/* ------------------------------------------------ unclaimed, and no picks ---- */

/* A record nobody has set is UNCLAIMED, not a four-way tie on zero. Same season, flat:
   one week, everybody level, nobody perfect and nobody blowing anybody out. */
const FLAT = ROSTER.map((p) => ({
  player_id: p.id, week_no: 1, week_label: 'Week 1', points: 100, correct: 10, games: 20,
}))
const flat = seasonRecords(FLAT, null, ROSTER)
const f = (k) => flat.records.find((r) => r.key === k)

assert.equal(f('perfect').unclaimed, true, 'nobody has a perfect week; that is not a tie on zero')
assert.deepEqual(f('perfect').holders, [], 'an unclaimed record has no holder')
assert.equal(f('blowout').unclaimed, true, 'a three-way tie means nobody blew anybody out')

/* But a genuine three-way tie on a real number IS a tie and must not read as unclaimed. */
assert.equal(f('points').unclaimed, false)
assert.equal(f('points').holders.length, 3)

/* Without the picks, the eight aggregate records stand and the four pick records are
   ABSENT rather than empty. This is the state between a deploy and pasting 015. */
assert.equal(flat.hasPicks, false)
assert.equal(flat.records.length, 8, 'the eight aggregate records must survive without picks')
assert.ok(!flat.records.some((r) => r.group === 'games'),
  'the Single games group must be absent, not present and empty')

// Empty in, empty out.
assert.deepEqual(seasonRecords([], null, ROSTER).records, [])
assert.deepEqual(seasonRecords(null, null, null).records, [])

console.log('records ok: %d with picks, %d without, %d weeks',
  book.records.length, flat.records.length, book.weeks)
