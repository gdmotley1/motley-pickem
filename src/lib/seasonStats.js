/**
 * The season tab, derived from get_season's one row per player per week.
 *
 * Same rule as weekRecap.js: everything here is a count or a ratio over rows the server
 * returned. Nothing is characterised, and no superlative is claimed that the numbers do
 * not settle outright. Where a stat needs the picks themselves, it is not here, because
 * get_season deliberately does not return them.
 *
 * Ties are first-class throughout, not an edge case. The house rule is that ties stand,
 * so a week has winners rather than a winner, and so does the season.
 */

import { ceiling } from './weekRecap.js'

/** Every week in this pool is twenty games. memory/decisions.md. */
export const SLATE = 20

/** Everyone tied on the best value of `key`. Empty in, empty out. */
function topBy(list, key) {
  if (!list.length) return []
  const best = Math.max(...list.map((x) => x[key]))
  return list.filter((x) => x[key] === best)
}

/**
 * The week numbers that are over.
 *
 * A week is finished when all twenty of its games are graded, or when a later week has
 * graded games, which covers a game that never gets a result.
 *
 * THE BUG THIS EXISTS FOR. Weeks used to count the moment one game was graded. On
 * 2026-09-12, one game into Week 2, the Season tab dived every form line to near zero,
 * named Grant's "fewest points in a week" as 0 when the real answer was Nicole's 147, and
 * credited Nicole with winning Week 2 because she led after a single game. Week records,
 * weeks won, the form chart and "N weeks in the books" all read finished weeks only.
 * Points keep counting live: the standings and season totals include every graded game.
 */
export function finishedWeeks(rows) {
  const graded = new Map()
  for (const r of rows || []) {
    const n = Number(r.week_no)
    graded.set(n, Math.max(graded.get(n) || 0, Number(r.games) || 0))
  }
  const nos = [...graded.keys()].sort((a, b) => a - b)
  return new Set(
    nos.filter((n, i) => graded.get(n) >= SLATE || nos.slice(i + 1).some((m) => graded.get(m) > 0)),
  )
}

/**
 * Group the flat rows into weeks, newest first, each knowing who took it.
 *
 * Every week with a row is listed, so the current one is there while it is played, but
 * only a FINISHED week has winners. Leading after one game of twenty is not winning.
 */
export function weekHistory(rows) {
  const done = finishedWeeks(rows)
  const byWeek = new Map()
  for (const r of rows) {
    if (!byWeek.has(r.week_no)) {
      byWeek.set(r.week_no, { week_no: r.week_no, label: r.week_label, entries: [] })
    }
    byWeek.get(r.week_no).entries.push(r)
  }

  return [...byWeek.values()]
    .map((w) => {
      const graded = Math.max(...w.entries.map((e) => Number(e.games) || 0), 0)
      const finished = done.has(Number(w.week_no))
      const winners = topBy(
        w.entries.map((e) => ({ ...e, points: Number(e.points) })),
        'points',
      )
      return {
        ...w,
        graded,
        finished,
        winners: finished ? winners.map((e) => ({ id: e.player_id, name: e.player_name })) : [],
        best: finished ? Number(winners[0].points) : 0,
        shared: finished && winners.length > 1,
      }
    })
    .sort((a, b) => b.week_no - a.week_no)
}

/**
 * Season totals per player.
 *
 * `captured` is the season's ranking efficiency: points banked over the sum of each
 * week's ceiling. Summing the weekly ceilings is the only correct way to do this, since
 * a ceiling depends on the shape of one week and cannot be recomputed from season
 * totals. See the note in migrations/010_get_season.sql.
 */
export function seasonTotals(rows, roster) {
  const by = new Map()
  for (const p of roster || []) {
    by.set(p.id, {
      id: p.id,
      name: p.name,
      color: p.color,
      team_id: p.team_id,
      points: 0,
      correct: 0,
      games: 0,
      ceiling: 0,
      weeks: 0,
      best: null,
      worst: null,
      weeksWon: 0,
      byWeek: new Map(),
    })
  }

  const done = finishedWeeks(rows)
  for (const r of rows) {
    const s = by.get(r.player_id)
    if (!s) continue
    const points = Number(r.points)
    const correct = Number(r.correct)
    const games = Number(r.games)
    if (!games) continue

    // Live: every graded game counts towards the season, finished week or not.
    s.points += points
    s.correct += correct
    s.games += games
    s.ceiling += ceiling(correct, games)

    // Per-week: only a week that is over. See finishedWeeks.
    if (!done.has(Number(r.week_no))) continue
    s.weeks += 1
    s.byWeek.set(r.week_no, points)

    const week = { week_no: r.week_no, label: r.week_label, points, correct, games }
    if (!s.best || points > s.best.points) s.best = week
    if (!s.worst || points < s.worst.points) s.worst = week
  }

  for (const w of weekHistory(rows)) {
    for (const win of w.winners) {
      const s = by.get(win.id)
      if (s) s.weeksWon += 1
    }
  }

  const players = [...by.values()]
    // Anyone with a graded pick is in the standings, so Week 1 has a leaderboard before
    // its last game. Filtering on finished weeks would blank the tab until Monday.
    .filter((s) => s.games > 0)
    .map((s) => ({
      ...s,
      wrong: s.games - s.correct,
      captured: s.ceiling ? Math.round((s.points / s.ceiling) * 100) : 0,
      accuracy: s.games ? Math.round((s.correct / s.games) * 100) : 0,
    }))
    .sort((a, b) => b.points - a.points || b.correct - a.correct)

  let lastPts = null
  let lastPos = 0
  players.forEach((p, i) => {
    if (p.points !== lastPts) {
      lastPos = i + 1
      lastPts = p.points
    }
    p.rank = lastPos
  })
  return players
}

/**
 * The handful of season facts worth printing, each one settled by the numbers.
 *
 * Every entry names who and how much. A superlative nobody holds outright is shared,
 * never broken by a tiebreak that the house rules do not have.
 */
export function seasonRecords(players, weeks) {
  if (!players.length) return []
  const out = []

  const bestWeeks = players.filter((p) => p.best).map((p) => ({ p, w: p.best }))
  if (bestWeeks.length) {
    const top = Math.max(...bestWeeks.map((x) => x.w.points))
    const holders = bestWeeks.filter((x) => x.w.points === top)
    out.push({
      key: 'bestWeek',
      label: 'Best week',
      value: String(top),
      unit: 'pts',
      who: holders.map((x) => `${x.p.name}, ${x.w.label}`).join(' and '),
    })
  }

  const ranked = topBy(players, 'captured')
  out.push({
    key: 'bestRanker',
    label: 'Best ranking',
    value: String(ranked[0].captured),
    unit: '% of ceiling',
    who: ranked.map((p) => p.name).join(' and '),
  })

  const won = topBy(players, 'weeksWon')
  if (won[0].weeksWon > 0) {
    out.push({
      key: 'weeksWon',
      label: 'Weeks won',
      value: String(won[0].weeksWon),
      unit: `of ${weeks.filter((w) => w.finished).length}`,
      who: won.map((p) => p.name).join(' and '),
    })
  }

  const acc = topBy(players, 'accuracy')
  out.push({
    key: 'accuracy',
    label: 'Most accurate',
    value: String(acc[0].accuracy),
    unit: '%',
    who: acc.map((p) => p.name).join(' and '),
  })

  return out
}

/** One call for the whole tab. */
export function seasonStats(rows, roster) {
  const weeks = weekHistory(rows || [])
  const players = seasonTotals(rows || [], roster || [])
  return {
    players,
    weeks,
    records: seasonRecords(players, weeks),
    played: weeks.filter((w) => w.finished).length,
  }
}
