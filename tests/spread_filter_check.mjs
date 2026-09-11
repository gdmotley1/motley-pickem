/**
 * The Setup screen's spread filter, checked against the real module.
 *
 * Grant asked on 2026-09-10 for a way to filter the pool by spread. It is worth having
 * because of one number: of the 86 games in Week 2's pool, 39 were priced at 21 points
 * or more and the median line was 20.5. Dad scrolls past all of them to find twenty
 * worth ranking.
 *
 * Rewritten on 2026-09-11. The filter used to own three thresholds of its own while the
 * chip on each row printed one of five tier tags, so the two disagreed: a game chipped
 * "toss-up" at 3.5 was hidden by the Toss-up filter, and four of the five tags could not
 * be filtered for at all. It now matches on the tier the database already stored, which
 * is why nearly every case below is about `tier` and not about `spread_line`.
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

/* Spread and tier travel together on a real row, because sync_supabase writes both from
   the same ESPN payload. The helper keeps them consistent so a case cannot accidentally
   assert against a combination the database would never produce. */
const g = (id, spread, tier, conf = 8) => ({
  game_id: id, spread_line: spread, tier, home_conf: conf, away_conf: conf,
})

const POOL = [
  g(1, 2.5, 'toss-up'), g(2, 4, 'toss-up'),
  g(3, 6.5, 'close'), g(4, 10, 'close'),
  g(5, 14.5, 'medium'),
  g(6, 24, 'big'),
  g(7, 31.5, 'blowout', 5),
  g(8, null, null), g(9, undefined, undefined),
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
  // Live right now: OU at MICH, where DraftKings has the spread OFF.
  for (const b of BANDS) {
    assert.equal(inBand(g(99, null, null), b.id), false, b.id)
    assert.equal(inBand(g(99, undefined, undefined), b.id), false, b.id)
  }
})

check('the filter offers exactly the five tags a row can be chipped with', () => {
  assert.deepEqual(BANDS.map((b) => b.id),
                   ['toss-up', 'close', 'medium', 'big', 'blowout'])
})

check('a game matches its own tier and no other', () => {
  // A partition now, where the old bands deliberately overlapped. Tapping "close" must
  // not also return the toss-ups, because the chip on those rows does not say close.
  for (const row of POOL) {
    if (!row.tier) continue
    const hits = BANDS.filter((b) => inBand(row, b.id)).map((b) => b.id)
    assert.deepEqual(hits, [row.tier], `game ${row.game_id}`)
  }
})

check('the tier is read, never re-derived from the spread', () => {
  /* The regression this exists for. A 3.5 point game is tagged toss-up by
     suggest_slate (its cut is 4), while the old filter cut Toss-up at 3 and hid it.
     Feed a row whose tier disagrees with any threshold the filter might invent, and the
     stored tier must still win. */
  assert.equal(inBand(g(1, 3.5, 'toss-up'), 'toss-up'), true,
               'a 3.5 point toss-up is exactly the game the old filter lost')
  assert.equal(inBand(g(1, 99, 'toss-up'), 'toss-up'), true,
               'the stored tier wins even when the number looks nothing like it')
  assert.equal(inBand(g(1, 1, 'blowout'), 'toss-up'), false)
})

check('an unknown band id matches nothing rather than everything', () => {
  assert.equal(inBand(g(1, 3, 'toss-up'), 'nonsense'), false)
  assert.equal(inBand(g(1, 3, 'toss-up'), undefined), false)
})

check('counts are what the chips will show', () => {
  const by = Object.fromEntries(availableBands(POOL).map((b) => [b.id, b.count]))
  assert.deepEqual(by, { 'toss-up': 2, close: 2, medium: 1, big: 1, blowout: 1 })
  assert.equal(unpricedCount(POOL), 2)
})

check('the counts add up to every priced game, exactly once', () => {
  // What being a partition buys: no game is double counted and none is dropped.
  const counted = availableBands(POOL).reduce((sum, b) => sum + b.count, 0)
  assert.equal(counted + unpricedCount(POOL), POOL.length)
})

check('a band with no games is never offered', () => {
  const only = availableBands([g(1, 2, 'toss-up')])
  assert.deepEqual(only.map((b) => b.id), ['toss-up'])
  assert.deepEqual(availableBands([]), [])
  assert.deepEqual(availableBands(null), [])
})

check('bands AND with a conference rather than replacing it', () => {
  const bigTen = POOL.filter((x) => inConference(x, 5))
  assert.deepEqual(bigTen.map((x) => x.game_id), [7])
  assert.deepEqual(bigTen.filter((x) => inBand(x, 'blowout')).map((x) => x.game_id), [7])
  assert.deepEqual(bigTen.filter((x) => inBand(x, 'close')), [],
                   'the only Big Ten game here is a 31.5 point line')
})

check('every band carries a label and a point range for the empty state', () => {
  for (const b of BANDS) {
    assert.ok(b.name && b.name.length, b.id)
    assert.ok(b.hint && /\d/.test(b.hint), b.id + ' needs a number in its hint')
  }
})

console.log(`\n${n} checks passed`)
