/**
 * The leaderboard's "max" number, checked against the real weekScore().
 *
 * Grant asked on 2026-10-05 for the Board's "N in play" to read "N max", taking them for
 * the same number. They are not: in play is what is still undecided, max is banked plus
 * that, which is the week's total minus everything lost so far. This pins the second one
 * so the row can never show the first under the new word.
 *
 * Run by tests/test_board_jumbo.py under node, so `python -m pytest tests/` stays the gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const { weekScore } = await import(pathToFileURL(path.join(process.cwd(), 'src/lib/weekScore.js')).href)

const games = Array.from({ length: 20 }, (_, i) => ({
  game_id: i + 1,
  home_abbr: `H${i + 1}`,
  away_abbr: `A${i + 1}`,
  // 1-10 final (home won), 11-12 kicked off and unfinished, 13-20 not started
  winner_abbr: i < 10 ? `H${i + 1}` : null,
  locked: i < 12,
}))
const roster = [{ id: 1, name: 'Grant' }, { id: 2, name: 'Dad' }]
// Grant: confidence 20..11 on games 1-10, right on the first 7, wrong on 8-10 (13, 12, 11).
// Games 11 and 12 carry 10 and 9 and are still on. Games 13-20 unrevealed.
const rows = []
for (let i = 0; i < 12; i += 1) {
  const conf = 20 - i
  rows.push({ player_id: 1, game_id: i + 1, confidence: conf, pick_abbr: i < 7 ? `H${i + 1}` : `A${i + 1}` })
}
// Dad has picked nothing that has been revealed.
const s = weekScore(games, rows, roster)
const grant = s.players.find((p) => p.id === 1)
const dad = s.players.find((p) => p.id === 2)

let n = 0
const check = (name, fn) => { fn(); n += 1; console.log('  ok  ' + name) }

check('a week is worth 210', () => assert.equal(s.total, 210))
check('banked is the confidence on the games called right', () => {
  assert.equal(grant.points, 20 + 19 + 18 + 17 + 16 + 15 + 14)
  assert.equal(grant.correct, 7)
  assert.equal(grant.played, 10)
})
check('in play is unrevealed plus kicked off and unfinished', () => {
  // unrevealed: 8 games at 1..8 = 36; on now: 10 + 9 = 19
  assert.equal(grant.live, 36 + 19)
})
check('max is banked plus in play, which is 210 minus what was lost', () => {
  assert.equal(grant.max, grant.points + grant.live)
  assert.equal(grant.max, 210 - (13 + 12 + 11))
  assert.notEqual(grant.max, grant.live, 'max and in play must differ once anything is lost')
})
check('nothing revealed yet means max is the whole week', () => {
  assert.equal(dad.points, 0)
  assert.equal(dad.live, 210)
  assert.equal(dad.max, 210)
})
check('max never exceeds the week', () => {
  for (const p of s.players) assert.ok(p.max <= s.total && p.max >= p.points)
})
console.log(`weekscore_check: ${n} checks passed`)
