/**
 * The pick nudge's arithmetic, checked against the real modules.
 *
 * The nudge is the first thing in the app that ever asked anyone to do something, so the
 * two ways it can be wrong both matter: telling you to pick a game that has already
 * kicked off, and showing a deadline that is not the next one.
 *
 * Run by tests/test_nudge.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)

const { untilLabel } = await load('src/lib/format.js')

/* PickNudge.jsx is JSX and cannot be imported under bare node, so pendingPicks is read
   out of the file and evaluated on its own. Brittle-looking, but it beats the
   alternatives: duplicating the function here would let the copy drift from the real one,
   which is the exact bug a test like this exists to catch. The extraction fails loudly
   if the function is renamed or reshaped. */
const src = await (await import('node:fs/promises')).readFile(
  path.join(ROOT, 'src/components/PickNudge.jsx'), 'utf8')
const m = src.match(/export function pendingPicks\(games\) \{[\s\S]*?\n\}/)
assert.ok(m, 'pendingPicks not found in PickNudge.jsx in the shape this check expects')
const pendingPicks = new Function(`${m[0].replace('export ', '')}; return pendingPicks`)()

const iso = (h) => new Date(Date.now() + h * 3600e3).toISOString()
const game = (id, hours, { locked = false, pick = null } = {}) =>
  ({ game_id: id, kickoff: iso(hours), locked, my_pick: pick })

let n = 0
const check = (name, fn) => { fn(); n += 1; console.log('  ok  ' + name) }

check('counts only what you can still pick', () => {
  const p = pendingPicks([
    game(1, 5), game(2, 6),
    game(3, -1, { locked: true }),            // kicked off, gone
    game(4, -2, { locked: true, pick: 'UGA' }),
    game(5, 7, { pick: 'LSU' }),              // already done
  ])
  assert.equal(p.count, 2)
})

check('a game that kicked off without a pick is never counted', () => {
  // It is gone. Counting it would only be a reproach, and the auto-pick has it.
  const p = pendingPicks([game(1, -3, { locked: true }), game(2, 4)])
  assert.equal(p.count, 1)
})

check('the deadline is the EARLIEST open kickoff, not the first in the array', () => {
  const p = pendingPicks([game(1, 30), game(2, 4), game(3, 12)])
  assert.equal(p.deadline, iso(4).slice(0, 16) + p.deadline.slice(16))
  const earliest = [30, 4, 12].sort((a, b) => a - b)[0]
  assert.ok(new Date(p.deadline).getTime() - Date.now() < (earliest + 0.1) * 3600e3)
})

check('a locked game never sets the deadline', () => {
  const p = pendingPicks([game(1, -5, { locked: true }), game(2, 9)])
  assert.ok(new Date(p.deadline).getTime() > Date.now(), 'deadline is in the past')
})

check('nothing to do means nothing renders', () => {
  assert.equal(pendingPicks([]), null)
  assert.equal(pendingPicks(null), null)
  assert.equal(pendingPicks([game(1, 4, { pick: 'UGA' })]), null)
  assert.equal(pendingPicks([game(1, -1, { locked: true })]), null)
})

check('started says whether the week is under way', () => {
  assert.equal(pendingPicks([game(1, 4), game(2, 5)]).started, false)
  assert.equal(pendingPicks([game(1, -1, { locked: true }), game(2, 5)]).started, true)
})

/* ------------------------------------------------------------- untilLabel */

check('hours run to 48 rather than rolling into days at 24', () => {
  // The change the nudge needed. Week 2's first kickoff was 24.8 hours out and "in 1d"
  // is not something anyone can act on.
  assert.equal(untilLabel(iso(24.8)), 'in 25h')
  assert.equal(untilLabel(iso(40)), 'in 40h')
  assert.equal(untilLabel(iso(72)), 'in 3d')
})

check('minutes under an hour, and never a zero', () => {
  assert.equal(untilLabel(iso(0.75)), 'in 45m')
  // A countdown that reaches "in 0m" and sits there reads as broken.
  assert.equal(untilLabel(iso(0.004)), 'any moment')
})

check('the past says so', () => {
  assert.equal(untilLabel(iso(-2)), 'kicked off')
  assert.equal(untilLabel('not a date'), '')
})

console.log(`\n${n} checks passed`)
