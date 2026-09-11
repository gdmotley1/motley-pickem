/**
 * The findings from the QA pass on 2026-09-10, each pinned so it cannot come back.
 *
 * Every one was found by driving the real app in a mock build rather than by reading it,
 * which is the point: none of them is visible in the source.
 *
 * Run by tests/test_qa.py under node.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)

const { tvLabel } = await load('src/lib/format.js')
const { NO_SESSION, friendly } = await load('src/lib/errors.js')

let n = 0
const check = (name, fn) => { fn(); n += 1; console.log('  ok  ' + name) }

/* ------------------------------------------------------------ the TV slot */

check('the one network name that overflowed is shortened', () => {
  // 92px of text in a 58px slot, ellipsising to "ACC Netw…", which reads as a bug.
  assert.equal(tvLabel('ACC Network'), 'ACCN')
  assert.equal(tvLabel('SEC Network'), 'SECN')
  assert.equal(tvLabel('Big Ten Network'), 'BTN')
})

check('every other network is left exactly as ESPN sends it', () => {
  for (const t of ['FS1', 'ESPN', 'ABC', 'FOX', 'CBS', 'NBC', 'CW', 'ESPN+', 'ESPNU']) {
    assert.equal(tvLabel(t), t)
  }
})

check('no TV is an empty string rather than undefined', () => {
  assert.equal(tvLabel(null), '')
  assert.equal(tvLabel(undefined), '')
  assert.equal(tvLabel(''), '')
})

/* --------------------------------------------------------- error messages */

check('a dropped signal says what to do, not what threw', () => {
  const m = friendly(new TypeError('Failed to fetch'))
  assert.match(m, /No connection/)
  assert.doesNotMatch(m, /fetch|TypeError/)
})

check('a project URL never reaches the screen', () => {
  const m = friendly(new Error(
    'harness blocked a Supabase call: https://example-project.supabase.co/rest/v1/rpc/save_picks'))
  assert.doesNotMatch(m, /https?:\/\//, 'a URL leaked into the message')
  assert.doesNotMatch(m, /supabase/i)
})

check('a stack frame never reaches the screen', () => {
  assert.doesNotMatch(friendly(new Error('boom at renderRow (index.js:42)')), /\bat\s/)
})

check('a long opaque token never reaches the screen', () => {
  const m = friendly(new Error('JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdefghij'))
  assert.doesNotMatch(m, /eyJ/)
})

check('the two rules a player can actually trip are explained', () => {
  assert.match(friendly(new Error('game has already kicked off')), /kicked off/)
  assert.match(friendly(new Error('JWT expired')), /signed out/)
})

check('a short plain sentence is passed through unchanged', () => {
  // Hiding a real message behind reassurance is how a bug goes unreported.
  assert.equal(friendly(new Error('That week is not published yet.')),
               'That week is not published yet.')
})

check('nothing at all still says something', () => {
  assert.match(friendly(null), /Try again/)
  assert.match(friendly(new Error('')), /Try again/)
})

/* ------------------------------------------------- wording at the sign-in screen */

check('the sign-in screen does not promise picks that do not exist yet', () => {
  const m = friendly(new TypeError('Failed to fetch'), { atSignIn: true })
  assert.match(m, /No connection/)
  assert.doesNotMatch(m, /picks/i, 'nobody has picks on this phone before signing in')
})

check('the sign-in screen does not tell you to tap a name that is not there', () => {
  const m = friendly(new Error('Not signed in'), { atSignIn: true })
  assert.equal(m, NO_SESSION)
  assert.doesNotMatch(m, /at the top/, 'there is no name at the top until you sign in')
})

check('everywhere else, a dead session still points at the name in the header', () => {
  assert.match(friendly(new Error('Not signed in')), /Tap your name at the top/)
  assert.match(friendly(new Error('JWT expired')), /Tap your name at the top/)
})

check("the database's own sign-in sentences are already human, and survive", () => {
  // Written to be read by a family member. friendly() must not replace them.
  for (const m of ['Wrong PIN', 'That seat is already taken', 'Name is required',
                   'That seat has not been claimed yet', 'PIN must be exactly 4 digits',
                   'Too many wrong PINs. Try again in a minute.']) {
    assert.equal(friendly(new Error(m), { atSignIn: true }), m)
  }
})

console.log(`\n${n} checks passed`)
