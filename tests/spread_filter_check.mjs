/**
 * The Setup screen's spread bands, checked against the real module.
 *
 * Grant asked on 2026-09-10 for a way to filter the pool by spread. It is worth having
 * because of one number: of the 86 games in Week 2's pool, 39 were priced at 21 points
 * or more and the median line was 20.5. Dad scrolls past all of them to find twenty
 * worth ranking.
 *
 * Run by tests/test_setup_filters.py under node, so `python -m pytest tests/` stays the
 * one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)

const { BANDS, availableBands, inBand, margin, unpricedCount } =
  await load('src/lib/spreads.js')
const { inConference } = await load('src/lib/conferences.js')

const g = (id, spread, conf = 8) => ({
  game_id: id, spread_line: spread, home_conf: conf, away_conf: conf,
})

const POOL = [
  g(1, 2.5), g(2, 3), g(3, 6.5), g(4, 8), g(5, 10.5),
  g(6, 17), g(7, 24), g(8, 31.5, 5), g(9, null), g(10, undefined),
]

let n = 0
const check = (name, fn) => { fn(); n += 1; console.log('  ok  ' + name) }

check('a line with no sign still measures its size', () => {
  assert.equal(margin({ spread_line: 6.5 }), 6.5)
  assert.equal(margin({ spread_line: -6.5 }), 6.5)
})

check('no line is null, not zero', () => {
  // The distinction that matters: a game nobody has priced is not a pick'em.
  assert.equal(margin({ spread_line: null }), null)
  assert.equal(margin({}), null)
  assert.equal(margin(null), null)
  assert.notEqual(margin({ spread_line: null }), 0)
})

check('a game with no line falls in no band at all', () => {
  for (const b of BANDS) {
    assert.equal(inBand(g(99, null), b.id), false, b.id)
    assert.equal(inBand(g(99, undefined), b.id), false, b.id)
  }
})

check('the thresholds are inclusive at their edge', () => {
  assert.equal(inBand(g(1, 3), 'tossup'), true, '3 is a toss-up')
  assert.equal(inBand(g(1, 3.5), 'tossup'), false)
  assert.equal(inBand(g(1, 8), 'onescore'), true, '8 is one score')
  assert.equal(inBand(g(1, 8.5), 'onescore'), false)
  assert.equal(inBand(g(1, 17), 'lopsided'), true, '17 is lopsided')
  assert.equal(inBand(g(1, 16.5), 'lopsided'), false)
})

check('one score contains every toss-up, on purpose', () => {
  // Thresholds, not buckets. A reader tapping "One score" expects the close games, all
  // of them, rather than a 3.5-to-8 slice.
  const tossups = POOL.filter((x) => inBand(x, 'tossup'))
  const onescore = POOL.filter((x) => inBand(x, 'onescore'))
  assert.ok(tossups.length > 0)
  for (const t of tossups) assert.ok(onescore.includes(t), 'toss-up missing from one score')
})

check('an unknown band id matches nothing rather than everything', () => {
  assert.equal(inBand(g(1, 3), 'nonsense'), false)
})

check('counts are what the chips will show', () => {
  const by = Object.fromEntries(availableBands(POOL).map((b) => [b.id, b.count]))
  assert.deepEqual(by, { tossup: 2, onescore: 4, lopsided: 3 })
  assert.equal(unpricedCount(POOL), 2)
})

check('a band with no games is never offered', () => {
  const only = availableBands([g(1, 2)])
  assert.deepEqual(only.map((b) => b.id), ['tossup', 'onescore'])
  assert.deepEqual(availableBands([]), [])
  assert.deepEqual(availableBands(null), [])
})

check('bands AND with a conference rather than replacing it', () => {
  const bigTen = POOL.filter((x) => inConference(x, 5))
  assert.deepEqual(bigTen.map((x) => x.game_id), [8])
  const bigTenLopsided = bigTen.filter((x) => inBand(x, 'lopsided'))
  assert.deepEqual(bigTenLopsided.map((x) => x.game_id), [8])
  const bigTenClose = bigTen.filter((x) => inBand(x, 'onescore'))
  assert.deepEqual(bigTenClose, [], 'the only Big Ten game here is a 31.5 point line')
})

check('every band carries a label and a threshold for the empty state', () => {
  for (const b of BANDS) {
    assert.ok(b.name && b.name.length, b.id)
    assert.ok(b.hint && /\d/.test(b.hint), b.id + ' needs a number in its hint')
  }
})

console.log(`\n${n} checks passed`)
