/**
 * Everyone's numbers exactly as the app computes them, for an options board.
 *
 * Runs the real src/lib/seasonRecords.js over a saved copy of what get_season,
 * get_season_picks and list_seats return (outputs/harness/season_live.json, pulled
 * read-only), so a board can never show a number the Season tab would not.
 *
 *   node scripts/numbers_model.mjs          # writes outputs/numbers_model.json
 *
 * Writes the file itself rather than printing: a PowerShell pipe re-decodes node's output
 * in the console code page and mangles the en dash and middle dot on the way through.
 */
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..')
const live = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'harness', 'season_live.json'), 'utf8'))
const { seasonRecords } = await import(pathToFileURL(path.join(ROOT, 'src', 'lib', 'seasonRecords.js')).href)

const roster = live.seats.filter((s) => s.claimed)
const book = seasonRecords(live.season, live.season_picks, roster)

const out = path.join(ROOT, 'outputs', 'numbers_model.json')
fs.writeFileSync(out, JSON.stringify({
  pulled_at: live.pulled_at,
  weeks: book.weeks,
  roster: roster.map(({ id, name, color, team_id }) => ({ id, name, color, team_id })),
  numbers: book.numbers,
}, null, 1), 'utf8')
console.log('wrote %s: %d records', out, book.numbers.length)
