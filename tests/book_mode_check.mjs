/**
 * Book mode, checked against the real modules and the real stylesheet.
 *
 * Two things are worth a gate here and they fail in completely different ways.
 *
 * onDark() is arithmetic: it must lift a colour far enough, must not lift one that is
 * already fine, and must not change the hue, because a chart line that changes hue stops
 * being that person's line.
 *
 * The palette is a contract: theme.css redefines the semantic tokens and app.css consumes
 * them, and the pair that breaks is never the one you were looking at. Slate could assume
 * --ink read on both --page and --card because both were light. Book mode cannot: the
 * page is dark wood and a card is a light brass plate. So every ink token now has exactly
 * one ground it is allowed on, and this file asserts the whole set.
 *
 * The set is WALKED, not listed. GROUNDS below says which ground each ink belongs to, and
 * the last check asserts that every ink-ish token declared in the book block appears in
 * it. Add a token and forget its ground and this fails by name, which is the whole point:
 * a list of five checks passes happily while the sixth token ships invisible text.
 *
 * Run by tests/test_book_mode.py under node, so `python -m pytest tests/` stays the one gate.
 */
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFile } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'

const ROOT = process.cwd()
const load = (rel) => import(pathToFileURL(path.join(ROOT, rel)).href)
const read = (rel) => readFile(path.join(ROOT, rel), 'utf8')

const { onDark, contrast, FELT } = await load('src/lib/onDark.js')

/* ------------------------------------------------------------------ onDark ---- */
const SEATS = { Grant: '#B85C1F', James: '#1F6F4A', Parker: '#2E5C8A', Nicole: '#8A2E4F' }

for (const [name, seat] of Object.entries(SEATS)) {
  const up = onDark(seat)
  assert.ok(
    contrast(up, FELT) >= 3.0,
    `${name}'s lifted colour ${up} is ${contrast(up, FELT).toFixed(2)}:1 on felt, under the 3:1 floor for a graphic`,
  )
}

/* Hue is identity. Lightening is allowed to wash a colour out a little; it is not allowed
   to turn Parker's blue into Grant's orange. 8 degrees is generous and still catches a
   channel swap. */
const hue = (hex) => {
  const h = hex.replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const max = Math.max(r, g, b)
  const d = max - Math.min(r, g, b)
  if (!d) return 0
  const t = max === r ? ((g - b) / d + (g < b ? 6 : 0)) : max === g ? (b - r) / d + 2 : (r - g) / d + 4
  return (t * 60 + 360) % 360
}
for (const [name, seat] of Object.entries(SEATS)) {
  const drift = Math.abs(hue(onDark(seat)) - hue(seat))
  assert.ok(
    Math.min(drift, 360 - drift) <= 8,
    `${name}'s colour moved ${drift.toFixed(1)} degrees of hue; it is meant to be the same person's line`,
  )
}

// All four must still be told apart from one another after the lift.
const lifted = Object.values(SEATS).map((c) => onDark(c))
assert.equal(new Set(lifted).size, 4, 'two seats lifted to the same colour')

// A colour that already reads must come back untouched: change as little as possible.
assert.equal(onDark('#ffd25a'), '#ffd25a', 'onDark lifted a colour that was already legible')
assert.equal(onDark('#ffffff'), '#ffffff', 'onDark altered white')

/* ------------------------------------------------------- the book palette ---- */
const theme = await read('src/theme.css')
const start = theme.indexOf("[data-mode='book'] {")
assert.ok(start > -1, "the [data-mode='book'] block is gone from theme.css")
const block = theme.slice(start, theme.indexOf('\n}', start))

const raw = new Map()
for (const [, k, v] of block.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) raw.set(k, v.trim())

/** Resolve var(--x) chains down to a literal colour. */
function tok(name, seen = new Set()) {
  const v = raw.get(name)
  assert.ok(v !== undefined, `book mode never defines ${name}`)
  const m = /^var\((--[\w-]+)\)$/.exec(v)
  if (!m) return v
  assert.ok(!seen.has(name), `${name} resolves in a circle`)
  return tok(m[1], seen.add(name))
}

const isColour = (v) => /^#[0-9a-f]{3,8}$/i.test(v)

/* Which ground each ink token is allowed on, and the floor it has to clear.
   4.5 for body text, 3.0 for large display type and for anything that is decoration
   carrying a number rather than a sentence. */
const GROUNDS = {
  '--ink': ['--card', 4.5],
  '--ink-2': ['--card', 4.5],
  '--ink-3': ['--card', 4.5],
  '--on-wood': ['--page', 4.5],
  '--on-wood-2': ['--page', 4.5],
  '--on-wood-3': ['--page', 3.0],
  '--on-field': ['--field', 4.5],
  '--on-field-2': ['--field', 4.5],
}

for (const [ink, [ground, floor]] of Object.entries(GROUNDS)) {
  const a = tok(ink)
  const b = tok(ground)
  const r = contrast(a, b)
  assert.ok(
    r >= floor,
    `${ink} (${a}) on ${ground} (${b}) is ${r.toFixed(2)}:1, under ${floor}:1`,
  )
}

/* The eyebrow is the first line on the Season screen and it sits on wood. Slate gives it
   --accent-deep, which in this palette is a dark gold and measures about 2:1 there, so
   app.css overrides it to --accent-bright. If that override is ever removed the first
   thing anyone reads goes invisible. */
assert.ok(
  contrast(tok('--accent-bright'), tok('--page')) >= 4.5,
  `--accent-bright is unreadable on wood: ${contrast(tok('--accent-bright'), tok('--page')).toFixed(2)}:1`,
)
const app = await read('src/app.css')
assert.ok(
  /\[data-mode='book'\]\s+\.eyebrow\s*\{[^}]*--accent-bright/.test(app),
  'the eyebrow no longer takes --accent-bright on wood; it will render at about 2:1',
)

/* Right and wrong still have to be right and wrong, on a brass plate this time. */
for (const t of ['--good', '--bad']) {
  const r = contrast(tok(t), tok('--card'))
  assert.ok(r >= 4.5, `${t} (${tok(t)}) is ${r.toFixed(2)}:1 on a brass plate`)
}

/* First place cannot be gold in a case made of gold: it would say the same thing as the
   frame. Whatever --lead becomes, it has to be tellable from the accent. */
assert.ok(
  contrast(tok('--lead'), tok('--accent')) >= 2.0,
  `--lead (${tok('--lead')}) is too close to --accent (${tok('--accent')}) to mark a leader`,
)

/* THE WALK. Every ink-ish token the book block declares must be in GROUNDS. A guard that
   only checks the tokens it was written for passes while a new one ships invisible. */
const declared = [...raw.keys()].filter(
  (k) => /^--(ink|on-wood|on-field)/.test(k) && isColour(tok(k)),
)
const uncovered = declared.filter((k) => !(k in GROUNDS))
assert.equal(
  uncovered.length,
  0,
  `book mode declares ${uncovered.join(', ')} but nothing says which ground it sits on. ` +
    'Add it to GROUNDS in this file with the surface it is drawn on.',
)
assert.ok(declared.length >= 8, `only found ${declared.length} ink tokens; has the block been gutted?`)

console.log('book mode ok: %d ink tokens walked, %d seat colours lifted', declared.length, lifted.length)
