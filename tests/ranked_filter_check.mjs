/**
 * The Setup screen's Ranked filter, checked against the real module.
 *
 * Grant asked on 2026-09-10 for "ranked team as an option like how you can filter by
 * conference". It is deliberately NOT another conference chip: it ANDs with them, so
 * "SEC and ranked" is reachable, which is most of the point on a 91-game pool.
 *
 * Run by tests/test_ranked_filter.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)

/* useRanks.js imports react for the hook. The helpers under test are plain functions in
   the same file, so stub the import rather than pulling react into the check. */
const { hasRankedTeam, rankedCount, rankOf } = await load('src/lib/useRanks.js')
const { inConference } = await load('src/lib/conferences.js')

const ranks = new Map([['61', 1], ['333', 4], ['99', 12]])

const GAMES = [
  { game_id: 1, home_id: '61', away_id: '2', home_conf: 8, away_conf: 8 },   // ranked home
  { game_id: 2, home_id: '2', away_id: '333', home_conf: 8, away_conf: 8 },  // ranked away
  { game_id: 3, home_id: '61', away_id: '99', home_conf: 8, away_conf: 8 },  // both ranked
  { game_id: 4, home_id: '7', away_id: '8', home_conf: 5, away_conf: 5 },    // neither
  { game_id: 5, home_id: '99', away_id: '8', home_conf: 5, away_conf: 8 },   // ranked, Big Ten
]

let n = 0
const check = (name, fn) => {
  fn()
  n += 1
  console.log('  ok  ' + name)
}

check('a ranked home team counts', () => {
  assert.equal(hasRankedTeam(GAMES[0], ranks), true)
})

check('a ranked away team counts', () => {
  assert.equal(hasRankedTeam(GAMES[1], ranks), true)
})

check('two ranked teams still counts once', () => {
  assert.equal(hasRankedTeam(GAMES[2], ranks), true)
  assert.equal(rankedCount([GAMES[2]], ranks), 1)
})

check('an unranked game does not count', () => {
  assert.equal(hasRankedTeam(GAMES[3], ranks), false)
})

check('rank 1 is truthy, which a plain || would get wrong', () => {
  // The reason hasRankedTeam tests `!= null` rather than truthiness: the AP number 1 is
  // a perfectly good rank and would be discarded by a falsy check on 0-adjacent values.
  assert.equal(rankOf(ranks, '61'), 1)
  assert.equal(hasRankedTeam({ home_id: '61', away_id: null }, ranks), true)
})

check('no poll means nothing is ranked, rather than everything', () => {
  assert.equal(hasRankedTeam(GAMES[0], null), false)
  assert.equal(rankedCount(GAMES, null), 0)
})

check('counts what the chip will show', () => {
  assert.equal(rankedCount(GAMES, ranks), 4)
  assert.equal(rankedCount([], ranks), 0)
  assert.equal(rankedCount(null, ranks), 0)
})

check('ranked ANDs with a conference rather than replacing it', () => {
  // What the Setup screen does: conference first, then ranked.
  const sec = GAMES.filter((g) => inConference(g, 8))
  assert.equal(sec.length, 4)
  const secRanked = sec.filter((g) => hasRankedTeam(g, ranks))
  assert.deepEqual(secRanked.map((g) => g.game_id), [1, 2, 3, 5])

  const bigTen = GAMES.filter((g) => inConference(g, 5))
  const bigTenRanked = bigTen.filter((g) => hasRankedTeam(g, ranks))
  assert.deepEqual(bigTenRanked.map((g) => g.game_id), [5], 'game 4 has no ranked team')
})

check('a missing team id is not a crash', () => {
  assert.equal(hasRankedTeam({ home_id: null, away_id: undefined }, ranks), false)
})

console.log(`\n${n} checks passed`)
