/**
 * The record book's arithmetic, checked against the real module.
 *
 * Seventeen entries, all Grant's picks off the 2026-09-12 ballot: eight numbers every
 * player has, eight Hall of fame awards and one Hall of shame award.
 *
 * The fixture is deliberately tiny so every expectation can be worked out on paper: three
 * players, three finished weeks, weekly totals typed in rather than derived. A fixture
 * generated from the implementation agrees with any bug the implementation has.
 *
 * Run by tests/test_records.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)
const { seasonRecords, BADGE_KEYS, NUMBERS, FAME, SHAME } = await load('src/lib/seasonRecords.js')

/* --------------------------------------------------------------- the fixture ---- */

const ROSTER = [
  { id: 1, name: 'Grant', color: '#B85C1F', team_id: '8' },
  { id: 2, name: 'James', color: '#1F6F4A', team_id: '2655' },
  { id: 3, name: 'Nicole', color: '#8A2E4F', team_id: null },
]

/*  wk  Grant          James          Nicole         week winner
 *   1  150, 16/20     120, 14/20     120, 14/20     Grant by 30
 *   2   90, 11/20     140, 15/20     140, 15/20     James and Nicole, shared
 *   3  110, 13/20     100, 12/20     210, 20/20     Nicole by 100, and perfect
 *
 *  season:  Grant 350, 40-20    James 360, 41-19    Nicole 470, 49-11
 */
const week = (wk, pid, points, correct, games = 20) => ({
  player_id: pid, week_no: wk, week_label: `Week ${wk}`, points, correct, games,
})
const SEASON = [
  week(1, 1, 150, 16), week(1, 2, 120, 14), week(1, 3, 120, 14),
  week(2, 1, 90, 11), week(2, 2, 140, 15), week(2, 3, 140, 15),
  week(3, 1, 110, 13), week(3, 2, 100, 12), week(3, 3, 210, 20),
]

/* Four graded games with picks. Confidence 1..4, "h" or "a" for the side taken, in
 * roster order. The favourite is listed; the other side is the underdog.
 *   g  winner  favourite  line   Grant       James       Nicole
 *   1  away    home       -10  c4 away W   c1 home L   c2 away W    +10 dog hits
 *   2  home    home        -3  c3 home W   c4 home W   c1 home W    everybody
 *   3  away    home       -21  c2 away W   c3 home L   c4 home L    +21 dog, Grant alone
 *   4  home    away        -7  c1 home W   c2 away L   c3 away L    +7 dog, Grant alone
 */
function games(list, weekNo = 1) {
  const out = []
  for (const [id, winnerSide, favSide, line, specs] of list) {
    const home = `H${id}`
    const away = `A${id}`
    specs.forEach((spec, i) => {
      if (!spec) return
      out.push({
        week_no: weekNo, week_label: `Week ${weekNo}`,
        game_id: id, kickoff: `2026-09-0${weekNo}T1${id % 10}:00:00Z`,
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
  return out
}
const PICKS = games([
  [1, 'away', 'home', -10, ['a4', 'h1', 'a2']],
  [2, 'home', 'home', -3, ['h3', 'h4', 'h1']],
  [3, 'away', 'home', -21, ['a2', 'h3', 'h4']],
  [4, 'home', 'away', -7, ['h1', 'a2', 'a3']],
])

const book = seasonRecords(SEASON, PICKS, ROSTER)
const num = (b, k) => {
  const r = b.numbers.find((x) => x.key === k)
  assert.ok(r, `no record named ${k}`)
  return r
}
const cell = (b, k, name) => {
  const row = num(b, k).rows.find((r) => r.name === name)
  assert.ok(row, `${name} missing from ${k}`)
  return row
}
const award = (list, k) => {
  const a = list.find((x) => x.key === k)
  assert.ok(a, `no award named ${k}`)
  return a
}
const who = (a) => a.holders.map((h) => (h.count > 1 ? `${h.name} x${h.count}` : h.name)).join(' & ')
const lead = (b, k) => num(b, k).headline

assert.equal(book.weeks, 3)
assert.equal(book.hasPicks, true)
assert.equal(book.numbers.length, 8)
assert.equal(book.fame.length, 8)
assert.equal(book.shame.length, 1)

/* ------------------------------------------------------ everyone's numbers ---- */

assert.equal(cell(book, 'best_week', 'Nicole').display, '210')
assert.equal(cell(book, 'best_week', 'Nicole').detail, 'Week 3')
assert.equal(cell(book, 'best_week', 'James').display, '140')
assert.deepEqual(lead(book, 'best_week').leaders.map((r) => r.name), ['Nicole'])
/* Different weeks, so every bracket stays. */
assert.equal(lead(book, 'best_week').rest, 'Grant 150 (Week 1) · James 140 (Week 2)')

assert.equal(cell(book, 'best_record', 'Nicole').display, '20-0')
assert.equal(cell(book, 'best_record', 'Grant').display, '16-4')
assert.equal(cell(book, 'best_record', 'James').display, '15-5')

/* The one record where the LOWEST number holds it, and holding it is bad news. Grant's 90
   in week 2 is the worst anyone posted. Backwards, this names Nicole, who had the best
   season, and it would look entirely plausible on screen. */
assert.equal(cell(book, 'low_week', 'Grant').display, '90')
assert.equal(cell(book, 'low_week', 'Grant').mark, 'worst')
assert.equal(num(book, 'low_week').rows[0].name, 'Grant', 'lowest must sort first')
assert.equal(num(book, 'low_week').bad, true)
assert.equal(lead(book, 'low_week').rest, 'James 100 (Week 3) · Nicole 120 (Week 1)')

/* Grant won all four in kickoff order; James won only game 2; Nicole won 1 and 2 then lost. */
assert.equal(cell(book, 'streak', 'Grant').display, '4')
assert.equal(cell(book, 'streak', 'James').display, '1')
assert.equal(cell(book, 'streak', 'Nicole').display, '2')
assert.equal(lead(book, 'streak').rest, 'Nicole 2 · James 1')

/* Worst miss is the most confidence on a loser, told as stake and team: "4 on H3". Grant
   never lost, so he has no value at all and must not sit at the bottom on a zero. */
assert.equal(cell(book, 'worst_miss', 'Nicole').display, '4')
assert.equal(cell(book, 'worst_miss', 'Nicole').detail, 'on H3')
assert.equal(cell(book, 'worst_miss', 'James').detail, 'on H3')
assert.equal(cell(book, 'worst_miss', 'Grant').value, null, 'a player who never lost has no worst miss')
assert.equal(cell(book, 'worst_miss', 'Grant').mark, null)
assert.equal(cell(book, 'worst_miss', 'Nicole').mark, 'worst')
assert.equal(lead(book, 'worst_miss').rest, 'James 3 on H3 · Grant no misses yet')

/* Underdog winners: game 1 (+10), game 3 (+21), game 4 (+7). Grant took all three, Nicole
   took game 1, James took none and shows "none yet" rather than a zero. */
assert.equal(cell(book, 'my_upset', 'Grant').display, '+21')
assert.equal(cell(book, 'my_upset', 'Grant').detail, 'A3')
assert.equal(cell(book, 'my_upset', 'Nicole').display, '+10')
assert.equal(cell(book, 'my_upset', 'James').value, null)
assert.equal(lead(book, 'my_upset').rest, 'Nicole +10 A1 · James none yet')

/* Week 2 tied on 140 and ties stand, so it counts for both James and Nicole. */
assert.equal(cell(book, 'weeks_won', 'Nicole').display, '2')
assert.equal(cell(book, 'weeks_won', 'Nicole').detail, 'of 3')
assert.equal(cell(book, 'weeks_won', 'Grant').display, '1')
assert.equal(cell(book, 'weeks_won', 'James').display, '1')
assert.equal(lead(book, 'weeks_won').rest, 'Grant and James 1', 'equal numbers read as one group')

assert.equal(cell(book, 'season_record', 'Nicole').display, '49-11')
assert.equal(cell(book, 'season_record', 'James').display, '41-19')
assert.equal(cell(book, 'season_record', 'Grant').display, '40-20')

/* ------------------------------------------------------------- Hall of fame ---- */

assert.equal(who(award(book.fame, 'season_points')), 'Nicole')
assert.equal(award(book.fame, 'season_points').detail, '470 points')
/* Margin is over the best OTHER player that week. Week 2 was shared, so it has no margin. */
assert.equal(who(award(book.fame, 'margin')), 'Nicole')
assert.equal(award(book.fame, 'margin').detail, 'Won Week 3 by 100')
assert.equal(who(award(book.fame, 'big_upset')), 'Grant')
assert.equal(award(book.fame, 'big_upset').detail, 'A3 +21')
/* Games exactly one player called: 3 and 4, both Grant. Game 1 was Grant and Nicole. */
assert.equal(who(award(book.fame, 'only_one')), 'Grant x2')
assert.equal(award(book.fame, 'only_one').detail, '2 games')
assert.equal(who(award(book.fame, 'three_upsets')), 'Grant')
assert.equal(award(book.fame, 'three_upsets').detail, 'Week 1')
assert.equal(who(award(book.fame, 'two_td_upset')), 'Grant')
/* Grant by 30 in week 1, Nicole by 100 in week 3: both clear 20, in the order earned. */
assert.equal(who(award(book.fame, 'win_by_20')), 'Grant & Nicole')
assert.equal(award(book.fame, 'win_by_20').detail, '2 weeks')
assert.equal(who(award(book.fame, 'perfect_week')), 'Nicole')
assert.equal(award(book.fame, 'perfect_week').detail, 'Week 3')

/* ------------------------------------------------------------ Hall of shame ---- */

/* Every stake in the fixture is 4 or less, so nobody has lost a 20. */
assert.equal(award(book.shame, 'lost_20').claimed, false)
assert.deepEqual(award(book.shame, 'lost_20').holders, [])
assert.equal(award(book.shame, 'lost_20').detail, '')

const shamed = seasonRecords(SEASON, [
  ...PICKS,
  ...games([[9, 'away', 'home', -3, [null, null, 'h20']]], 2),
], ROSTER)
assert.equal(who(award(shamed.shame, 'lost_20')), 'Nicole')
assert.equal(award(shamed.shame, 'lost_20').detail, '20 on H9, Week 2')
assert.equal(cell(shamed, 'worst_miss', 'Nicole').detail, 'on H9', 'the 20 is now her worst miss')

/* ------------------------------------------------ the half-played week bug ---- */

/* 2026-09-12, one game into Week 2: fewest points in a week read 0, and Nicole was
   credited with winning Week 2 after one game. Week 4 here is one game in, Grant 20 and
   the others 0. It must change the live numbers and nothing that says "in a week". */
const partial = seasonRecords([
  ...SEASON, week(4, 1, 20, 1, 1), week(4, 2, 0, 0, 1), week(4, 3, 0, 0, 1),
], PICKS, ROSTER)
assert.equal(partial.weeks, 3, 'a week one game in is not a week in the books')
assert.equal(cell(partial, 'low_week', 'James').display, '100', 'a zero from an unfinished week is not a low week')
assert.equal(cell(partial, 'weeks_won', 'Grant').display, '1', 'leading after one game is not winning the week')
assert.equal(cell(partial, 'weeks_won', 'Nicole').detail, 'of 3')
assert.equal(who(award(partial.fame, 'win_by_20')), 'Grant & Nicole', 'a 20 point lead after one game is not a week won by 20')
assert.equal(cell(partial, 'season_record', 'Grant').display, '41-20', 'but the season record counts it live')
assert.equal(award(partial.fame, 'season_points').detail, '470 points')

/* And the moment a later week has a graded game, week 4 is over: it counts. */
const later = seasonRecords([
  ...SEASON, week(4, 1, 20, 1, 1), week(4, 2, 0, 0, 1), week(4, 3, 0, 0, 1),
  week(5, 1, 5, 1, 1), week(5, 2, 0, 0, 1), week(5, 3, 0, 0, 1),
], PICKS, ROSTER)
assert.equal(later.weeks, 4)
assert.equal(cell(later, 'weeks_won', 'Grant').display, '2')
assert.equal(cell(later, 'weeks_won', 'Grant').detail, 'of 4')
assert.equal(cell(later, 'low_week', 'James').display, '0')
assert.deepEqual(lead(later, 'low_week').leaders.map((r) => r.name), ['James', 'Nicole'],
  'a shared worst week names both')
assert.equal(who(award(later.fame, 'win_by_20')), 'Grant x2 & Nicole')

/* ---------------------------------------------- ties, nothing yet, no picks ---- */

/* One finished week, everybody level. */
const FLAT = ROSTER.map((p) => week(1, p.id, 100, 10))
const flat = seasonRecords(FLAT, null, ROSTER)

assert.equal(flat.hasPicks, false)
assert.equal(lead(flat, 'best_week').leaders.length, 3, 'a three-way tie is three leaders')
assert.equal(lead(flat, 'best_week').rest, '', 'and nobody left over')
assert.equal(num(flat, 'low_week').open, 'Starts once Week 2 is final')
assert.equal(num(flat, 'low_week').headline, null)
assert.equal(award(flat.fame, 'season_points').holders.length, 3)
/* A three-way tie means nobody won by anything. That is unclaimed, not a tie on zero. */
assert.equal(award(flat.fame, 'margin').claimed, false)
assert.equal(award(flat.fame, 'perfect_week').claimed, false)

/* Without the picks, the pick-based entries are ABSENT rather than drawn as unclaimed:
   "up for grabs" would be a claim the book cannot back. */
assert.deepEqual(flat.numbers.map((r) => r.key), NUMBERS.filter((d) => !d.picks).map((d) => d.key))
assert.deepEqual(flat.fame.map((a) => a.key), FAME.filter((d) => !d.picks).map((d) => d.key))
assert.equal(flat.shame.length, 0)

/* Week 1, five games in: nothing is finished, so the week records wait and say until
   when, while the season record is already live. */
const early = seasonRecords(ROSTER.map((p) => week(1, p.id, 30, 3, 5)), PICKS, ROSTER)
assert.equal(early.weeks, 0)
assert.equal(num(early, 'best_week').open, 'Starts once Week 1 is final')
assert.equal(num(early, 'weeks_won').open, 'Starts once Week 1 is final')
assert.equal(num(early, 'low_week').open, 'Starts once Week 2 is final')
assert.equal(num(early, 'season_record').open, null)

/* Empty in, empty out. */
assert.deepEqual(seasonRecords([], null, ROSTER).numbers, [])
assert.deepEqual(seasonRecords(null, null, null).fame, [])

/* -------------------------------------------------------------- the invariants ---- */

/* Plain enough to read cold. The seventeen invented terms Grant threw out are banned by
   name, so nobody can quietly reintroduce one. */
const BANNED = ['anchor', 'fade', 'chalk', 'homer', 'nemesis', 'money team', 'coin flip',
  'slept', 'perfect order', 'sharpest', 'hot streak', 'lone wolf', 'most picked',
  'upset special', 'blowout']
for (const d of [...NUMBERS, ...FAME, ...SHAME]) {
  for (const b of BANNED) {
    assert.ok(!d.label.toLowerCase().includes(b), `"${d.label}" is one of the terms that got cut`)
  }
}

for (const b of [book, partial, later, flat]) {
  for (const r of b.numbers) {
    assert.equal(r.rows.length, ROSTER.length, `${r.key} does not rank everybody`)
    const vals = r.rows.map((x) => x.value)
    const firstNull = vals.indexOf(null)
    if (firstNull >= 0) {
      assert.ok(vals.slice(firstNull).every((v) => v == null), `${r.key} sorts a value below a null`)
    }
    const real = vals.filter((v) => v != null)
    const asc = real.every((v, i) => i === 0 || real[i - 1] <= v)
    const desc = real.every((v, i) => i === 0 || real[i - 1] >= v)
    if (r.key === 'low_week') assert.ok(asc, 'Fewest points in a week must rank LOWEST first')
    else assert.ok(desc, `${r.key} must rank highest first`)
    for (const row of r.rows) {
      if (row.mark) assert.notEqual(row.value, null, `${r.key} is held by somebody it does not apply to`)
      assert.ok(row.display !== '' && row.display != null, `${r.key} leaves ${row.name} with nothing to show`)
    }
  }
  for (const a of [...b.fame, ...b.shame]) {
    assert.equal(a.claimed, a.holders.length > 0)
    if (a.claimed) assert.ok(a.detail, `${a.key} is claimed but says nothing about how`)
  }
}

/* Every entry has Grant's art, and every piece of art is an entry. Walked off the disk,
   not listed, so a new record without a badge fails here instead of drawing a broken
   image on the Season tab. */
const art = fs.readdirSync(path.join(ROOT, 'src', 'assets', 'badges'))
  .filter((f) => f.endsWith('.webp')).map((f) => f.replace(/\.webp$/, '')).sort()
assert.deepEqual([...BADGE_KEYS].sort(), art, 'badge art and record book entries have drifted apart')
assert.equal(new Set(BADGE_KEYS).size, BADGE_KEYS.length, 'two entries share a badge key')

console.log('records ok: %d numbers, %d fame, %d shame, %d badges',
  book.numbers.length, book.fame.length, book.shame.length, art.length)
