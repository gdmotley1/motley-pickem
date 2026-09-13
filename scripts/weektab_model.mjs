/**
 * The finished Week 1 exactly as the app computes it, for the Week tab options board.
 *
 * Runs the real src/lib/weekRecap.js over outputs/harness/week_live.json, which is
 * tests/fixtures/week1_board.json (the real Week 1 slate, board and roster) with each seat
 * re-keyed to the school it wears today. So a board can never show a number the Week tab
 * would not.
 *
 * Three things here are NOT in weekRecap.js yet, and every option on the board uses them.
 * They are marked PROPOSED so the build that follows the pick knows what to add, with
 * assertions, rather than inlining them in a screen:
 *   - the runner-up in each what-if ("James takes it, 196 to 194" needs the 194)
 *   - who had what riding on a game ("all four had GT: James 17, Nicole 12 ...")
 *   - which games everyone got right, by name, where recap.sweeps is only a count
 *
 *   node scripts/weektab_model.mjs          # writes outputs/weektab_model.json
 *
 * Writes the file itself rather than printing, so PowerShell cannot re-decode it.
 */
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..')
const live = JSON.parse(fs.readFileSync(path.join(ROOT, 'outputs', 'harness', 'week_live.json'), 'utf8'))
const { weekRecap, ceiling } = await import(pathToFileURL(path.join(ROOT, 'src', 'lib', 'weekRecap.js')).href)

const { slate, board, seats } = live
const roster = seats.filter((s) => s.claimed)
const recap = weekRecap(slate, board, roster)
if (!recap.complete) throw new Error('the board is built on a finished week')

const gameById = new Map(slate.map((g) => [g.game_id, g]))
const nameOf = new Map(roster.map((p) => [p.id, p.name]))
const byName = new Map(roster.map((p) => [p.name, p]))

const side = (g, which) => ({
  abbr: g[`${which}_abbr`],
  id: g[`${which}_id`],
  school: g[`${which}_school`],
  score: g[`${which}_score`],
})

/** PROPOSED: everyone's pick on one game, biggest wager first. */
function stakes(gameId) {
  const g = gameById.get(gameId)
  return board
    .filter((r) => r.game_id === gameId)
    .map((r) => ({
      name: nameOf.get(r.player_id),
      pick: r.pick_abbr,
      confidence: r.confidence,
      won: r.pick_abbr === g.winner_abbr,
    }))
    .sort((a, b) => b.confidence - a.confidence || a.name.localeCompare(b.name))
}

/** PROPOSED: the whole table with one result reversed, for the runner-up in a what-if. */
function flipped(gameId) {
  const g = gameById.get(gameId)
  const loser = g.winner_abbr === g.home_abbr ? g.away_abbr : g.home_abbr
  const pts = new Map(roster.map((p) => [p.name, 0]))
  for (const r of board) {
    const game = gameById.get(r.game_id)
    const winner = r.game_id === gameId ? loser : game.winner_abbr
    if (r.pick_abbr === winner) pts.set(nameOf.get(r.player_id), pts.get(nameOf.get(r.player_id)) + r.confidence)
  }
  return [...pts.entries()].map(([name, points]) => ({ name, points })).sort((a, b) => b.points - a.points)
}

const players = recap.players.map((p) => ({
  id: p.id,
  name: p.name,
  team_id: p.team_id,
  color: p.color,
  rank: p.rank,
  correct: p.correct,
  wrong: p.wrong,
  points: p.points,
  behind: recap.players[0].points - p.points,
  ceiling: p.ceiling,
  left: p.ceiling - p.points,
}))

/* A what-if that hands the week to someone else outright comes before one that only
   makes it a tie. Both are recomputed; the order is a count, not a judgement. */
const actual = new Set(recap.leaders.map((p) => p.name))
const decisive = recap.decisive
  .map((d) => {
    const g = gameById.get(d.game_id)
    const table = flipped(d.game_id)
    const top = table[0].points
    const leaders = table.filter((t) => t.points === top).map((t) => t.name)
    const next = table.find((t) => t.points < top)
    if (leaders.join() !== d.leaders.join()) throw new Error(`flip disagrees with weekRecap on ${d.label}`)
    return {
      game_id: d.game_id,
      away: side(g, 'away'),
      home: side(g, 'home'),
      winner: d.actual,
      instead: d.instead,
      leaders,
      shared: d.shared,
      points: d.points,
      next: next ? { names: table.filter((t) => t.points === next.points).map((t) => t.name), points: next.points } : null,
      reversal: leaders.every((n) => !actual.has(n)),
      stakes: stakes(d.game_id),
    }
  })
  .sort((a, b) => Number(b.reversal) - Number(a.reversal))

const upsets = recap.upsets.map((u) => {
  const g = gameById.get(u.game_id)
  const all = stakes(u.game_id)
  return {
    game_id: u.game_id,
    away: side(g, 'away'),
    home: side(g, 'home'),
    winner: u.winner,
    loser: g.winner_abbr === g.home_abbr ? g.away_abbr : g.home_abbr,
    line: u.line,
    called: all.filter((s) => s.won),
    stakes: all,
  }
})

/* Points left on the table: the ranking stat, as a count. Lowest first, ties share. */
const left = [...players].sort((a, b) => a.left - b.left || a.name.localeCompare(b.name))
left.forEach((p, i) => {
  p.leftRank = i && p.left === left[i - 1].left ? left[i - 1].leftRank : i + 1
})

const winners = (list) => list.map((g) => g.winner)
const scored = slate.filter((g) => g.winner_abbr)
const sweeps = scored.filter((g) => board.filter((r) => r.game_id === g.game_id).every((r) => r.pick_abbr === g.winner_abbr))
if (sweeps.length !== recap.sweeps) throw new Error('sweep list disagrees with weekRecap')

/* ------------------------------------------------ PROPOSED content options, round 2 */
const kickOrder = [...slate].sort((a, b) => a.kickoff.localeCompare(b.kickoff) || a.game_id - b.game_id)
const pickFor = (name, gameId) => board.find((r) => r.game_id === gameId && nameOf.get(r.player_id) === name)
const teamIdOf = (g, abbr) => (g.home_abbr === abbr ? g.home_id : g.away_id)
const entry = (r) => {
  const g = gameById.get(r.game_id)
  return {
    game_id: r.game_id, pick: r.pick_abbr, pick_id: teamIdOf(g, r.pick_abbr), confidence: r.confidence,
    won: r.pick_abbr === g.winner_abbr, away: side(g, 'away'), home: side(g, 'home'), winner: g.winner_abbr,
    others: board.filter((o) => o.game_id === r.game_id && o.player_id !== r.player_id)
      .map((o) => ({ name: nameOf.get(o.player_id), pick: o.pick_abbr, confidence: o.confidence })),
  }
}
const mineOf = (name) => board.filter((r) => nameOf.get(r.player_id) === name)

/* Biggest miss: the most points anyone had on a pick that lost. */
const misses = players.map((p) => {
  const lost = mineOf(p.name).filter((r) => r.pick_abbr !== gameById.get(r.game_id).winner_abbr)
    .sort((a, b) => b.confidence - a.confidence)
  return { name: p.name, team_id: p.team_id, miss: lost[0] ? entry(lost[0]) : null, lostTotal: lost.reduce((n, r) => n + r.confidence, 0), wrong: lost.length }
}).sort((a, b) => (b.miss?.confidence || 0) - (a.miss?.confidence || 0))

/* Best call: the most points on a right pick that somebody else in the family missed. */
const calls = players.map((p) => {
  const good = mineOf(p.name).filter((r) => {
    const g = gameById.get(r.game_id)
    return r.pick_abbr === g.winner_abbr && board.some((o) => o.game_id === r.game_id && o.pick_abbr !== g.winner_abbr)
  }).sort((a, b) => b.confidence - a.confidence)
  const e0 = good[0] ? entry(good[0]) : null
  return { name: p.name, team_id: p.team_id, call: e0, missedBy: e0 ? e0.others.filter((o) => o.pick !== e0.winner).map((o) => o.name) : [] }
}).sort((a, b) => (b.call?.confidence || 0) - (a.call?.confidence || 0))

/* Where all four agreed, and how that went. */
const agreed = kickOrder.filter((g) => new Set(board.filter((r) => r.game_id === g.game_id).map((r) => r.pick_abbr)).size === 1)
  .map((g) => {
    const rows = board.filter((r) => r.game_id === g.game_id)
    return { pick: rows[0].pick_abbr, pick_id: teamIdOf(g, rows[0].pick_abbr), won: rows[0].pick_abbr === g.winner_abbr,
      away: side(g, 'away'), home: side(g, 'home'), winner: g.winner_abbr, total: rows.reduce((n, r) => n + r.confidence, 0) }
  })

/* Went it alone: the only one in the family on that side. */
const alone = players.map((p) => {
  const solo = mineOf(p.name).filter((r) => board.filter((o) => o.game_id === r.game_id).every((o) => o.player_id === r.player_id || o.pick_abbr !== r.pick_abbr))
    .map(entry).sort((a, b) => b.confidence - a.confidence)
  return { name: p.name, team_id: p.team_id, picks: solo, right: solo.filter((s) => s.won).length }
}).sort((a, b) => b.picks.length - a.picks.length || b.right - a.right)

/* How the week unfolded: running totals in kickoff order, and who led after each game. */
const running = new Map(players.map((p) => [p.name, 0]))
const steps = kickOrder.map((g, i) => {
  for (const r of board.filter((x) => x.game_id === g.game_id)) {
    if (r.pick_abbr === g.winner_abbr) running.set(nameOf.get(r.player_id), running.get(nameOf.get(r.player_id)) + r.confidence)
  }
  const pts = Object.fromEntries(running)
  const top = Math.max(...Object.values(pts))
  return { n: i + 1, label: `${g.away_abbr} at ${g.home_abbr}`, winner: g.winner_abbr, day: g.kickoff.slice(0, 10), kickoff: g.kickoff, points: pts,
    leaders: Object.keys(pts).filter((k) => pts[k] === top) }
})
let changes = 0
let holder = null
for (const s of steps) {
  if (s.leaders.length === 1 && s.leaders[0] !== holder) {
    if (holder !== null) changes += 1
    holder = s.leaders[0]
  }
}
const ledAfter = Object.fromEntries(players.map((p) => [p.name, steps.filter((s) => s.leaders.length === 1 && s.leaders[0] === p.name).length]))
const tookLead = steps.findIndex((s, i) => s.leaders.join() === recap.leaders.map((p) => p.name).join() &&
  steps.slice(i).every((t) => t.leaders.join() === s.leaders.join()))

/* The closest finish and the biggest blowout on the slate. */
const margins = slate.map((g) => ({ away: side(g, 'away'), home: side(g, 'home'), winner: g.winner_abbr, margin: Math.abs(g.home_score - g.away_score),
  picked: board.filter((r) => r.game_id === g.game_id && r.pick_abbr === g.winner_abbr).map((r) => nameOf.get(r.player_id)) }))
  .sort((a, b) => a.margin - b.margin)

/* Your week against the nearest rival: the winner if you did not win, the runner-up if you did. */
const meName = 'Grant'
const meRow = players.find((p) => p.name === meName)
const rival = meRow.rank === 1 ? players.find((p) => p.rank !== 1) : players.find((p) => p.rank === 1)
const h2h = kickOrder.map((g) => {
  const a = pickFor(meName, g.game_id)
  const b = pickFor(rival.name, g.game_id)
  const ea = a && a.pick_abbr === g.winner_abbr ? a.confidence : 0
  const eb = b && b.pick_abbr === g.winner_abbr ? b.confidence : 0
  return { label: `${g.away_abbr} at ${g.home_abbr}`, me: a && { pick: a.pick_abbr, confidence: a.confidence, won: ea > 0 },
    them: b && { pick: b.pick_abbr, confidence: b.confidence, won: eb > 0 }, net: ea - eb,
    pick_id: teamIdOf(g, a ? a.pick_abbr : g.winner_abbr) }
}).filter((x) => x.net !== 0).sort((x, y) => y.net - x.net)

const content = {
  misses, calls, agreed, alone,
  you: { name: meName, rank: meRow.rank, of: players.length, rival: rival.name, net: meRow.points - rival.points,
    gained: h2h.filter((x) => x.net > 0), lost: h2h.filter((x) => x.net < 0).reverse() },
  race: { steps, changes, ledAfter, tookLeadAt: tookLead + 1, leader: recap.leaders.map((p) => p.name) },
  closest: margins[0], blowout: margins[margins.length - 1],
}

const out = path.join(ROOT, 'outputs', 'weektab_model.json')
fs.writeFileSync(out, JSON.stringify({
  source: 'src/lib/weekRecap.js over outputs/harness/week_live.json',
  week: { label: 'Week 1', current: 'Week 2', slate: slate.length, total: (slate.length * (slate.length + 1)) / 2 },
  me: 'Grant',
  leaders: recap.leaders.map((p) => p.name),
  margin: recap.margin,
  players,
  decisive,
  upsets,
  left: left.map(({ name, team_id, points, ceiling: c, left: l, leftRank }) => ({ name, team_id, points, ceiling: c, left: l, rank: leftRank })),
  numbers: {
    chalk: recap.chalk,
    upsets: recap.upsets.length,
    called: recap.upsets.filter((u) => u.calledBy.length).length,
    calledBy: [...new Set(upsets.flatMap((u) => u.called.map((c) => c.name)))],
    sweeps: winners(sweeps.map((g) => ({ winner: g.winner_abbr }))),
    whiffs: recap.whiffs.map((w) => w.winner),
    /* PROPOSED, option 4's "did you know" only: where each player put their 20. */
    twenties: Object.fromEntries(board.filter((r) => r.confidence === slate.length)
      .map((r) => [nameOf.get(r.player_id), { pick: r.pick_abbr, won: r.pick_abbr === gameById.get(r.game_id).winner_abbr }])),
  },
  teams: [...new Set([
    ...roster.map((p) => p.team_id),
    ...[...decisive, ...upsets].flatMap((d) => [d.away.id, d.home.id]),
  ])],
  content,
  check: { ceilingGrant: ceiling(16, 20) },
}, null, 1), 'utf8')
console.log('wrote %s: %d players, %d decisive, %d upsets', out, players.length, decisive.length, upsets.length)
